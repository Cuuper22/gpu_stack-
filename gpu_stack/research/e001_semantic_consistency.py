"""Deterministic two-site semantic-consistency experiment for E001.

The executable policies in this module all consume the same ordered pair of
byte-token commitments for every logical epoch.  They differ only in when a
full AdamW state is shared and in what happens when one site is unavailable.

Two boundaries are deliberate:

* ``periodic_local`` is arithmetic averaging of model and AdamW state.  It is
  not GASLoC, gossip, or any other algorithm whose update rule is not present.
* ``future_trace_oracle`` is not trained as a clairvoyant learner.  It is the
  best-in-hindsight envelope over the five executable whole-policy schedules
  using a frozen infrastructure objective that cannot inspect losses or
  gradients.  It is exposed only as a hindsight whole-policy envelope.

PyTorch, PyArrow, NumPy, and NVML remain optional experiment dependencies.  A
normal ``gpu_stack`` import does not load them.
"""

from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import time
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

from . import e001_learning_calibration as lc1


SCHEMA = "gpu-stack.e001-semantic-consistency-result.v1"
ENGINE_ID = "gpu-stack.e001-semantic-consistency.v1"

SYNCHRONOUS_RESTART = "synchronous_restart"
EXACT_FORWARD_RECOVERY = "exact_forward_recovery"
DELAYED_ONE_STEP = "delayed_one_step"
PERIODIC_LOCAL = "periodic_local"
OBSERVABLE_ADAPTIVE = "observable_adaptive"
FUTURE_TRACE_ORACLE = "future_trace_oracle"

FIXED_POLICIES = (
    SYNCHRONOUS_RESTART,
    EXACT_FORWARD_RECOVERY,
    DELAYED_ONE_STEP,
    PERIODIC_LOCAL,
)
EXECUTABLE_POLICIES = (*FIXED_POLICIES, OBSERVABLE_ADAPTIVE)
POLICY_PANEL = (*EXECUTABLE_POLICIES, FUTURE_TRACE_ORACLE)
SITE_IDS = ("site-a", "site-b")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _content_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _positive_int(value: Any, name: str) -> int:
    result = int(value)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _nonnegative_float(value: Any, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return result


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = copy.deepcopy(dict(base))
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _update_hash(digest: Any, value: Any) -> None:
    if hasattr(value, "detach") and hasattr(value, "dtype"):
        cpu = value.detach().cpu().contiguous()
        digest.update(b"tensor\0")
        digest.update(str(cpu.dtype).encode("utf-8"))
        digest.update(b"\0")
        digest.update(_canonical_json(list(cpu.shape)).encode("utf-8"))
        digest.update(b"\0")
        try:
            raw = cpu.numpy().tobytes()
        except TypeError:
            raw = cpu.view(__import__("torch").uint8).numpy().tobytes()
        digest.update(raw)
        return
    if isinstance(value, Mapping):
        digest.update(b"mapping\0")
        for key in sorted(value, key=lambda item: (type(item).__name__, repr(item))):
            _update_hash(digest, key)
            _update_hash(digest, value[key])
        return
    if isinstance(value, (list, tuple)):
        digest.update(type(value).__name__.encode("ascii"))
        digest.update(b"\0")
        for item in value:
            _update_hash(digest, item)
        return
    digest.update(type(value).__name__.encode("ascii"))
    digest.update(b"\0")
    digest.update(repr(value).encode("utf-8"))
    digest.update(b"\0")


def _state_hash(value: Any) -> str:
    digest = hashlib.sha256()
    _update_hash(digest, value)
    return digest.hexdigest()


def _batch_hash(x: Any, y: Any) -> str:
    digest = hashlib.sha256()
    _update_hash(digest, x)
    _update_hash(digest, y)
    return digest.hexdigest()


def _tree_average(torch: Any, left: Any, right: Any, path: str = "state") -> Any:
    """Arithmetic full-state average used only by delayed/periodic modes."""

    if hasattr(left, "detach") and hasattr(right, "detach"):
        if left.shape != right.shape or left.dtype != right.dtype:
            raise ValueError(f"cannot average incompatible tensors at {path}")
        left_cpu = left.detach().cpu().clone()
        right_cpu = right.detach().cpu()
        if left_cpu.is_floating_point() or left_cpu.is_complex():
            return (left_cpu + right_cpu) * 0.5
        return torch.maximum(left_cpu, right_cpu)
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if set(left) != set(right):
            raise ValueError(f"state keys differ at {path}")
        return {
            key: _tree_average(torch, left[key], right[key], f"{path}.{key}")
            for key in left
        }
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            raise ValueError(f"state list lengths differ at {path}")
        return [
            _tree_average(torch, a, b, f"{path}[{index}]")
            for index, (a, b) in enumerate(zip(left, right, strict=True))
        ]
    if isinstance(left, tuple) and isinstance(right, tuple):
        if len(left) != len(right):
            raise ValueError(f"state tuple lengths differ at {path}")
        return tuple(
            _tree_average(torch, a, b, f"{path}[{index}]")
            for index, (a, b) in enumerate(zip(left, right, strict=True))
        )
    if left != right:
        raise ValueError(f"non-tensor optimizer metadata differs at {path}")
    return copy.deepcopy(left)


def _average_checkpoints(
    torch: Any,
    left: lc1._Checkpoint,
    right: lc1._Checkpoint,
    *,
    logical_epoch: int,
    merge_count: int,
) -> lc1._Checkpoint:
    model_state = _tree_average(torch, left.model_state, right.model_state, "model")
    optimizer_state = _tree_average(
        torch,
        left.optimizer_state,
        right.optimizer_state,
        "optimizer",
    )
    return lc1._Checkpoint(
        model_state=model_state,
        optimizer_state=optimizer_state,
        logical_tick=logical_epoch,
        merge_count=merge_count,
        checkpoint_bytes=lc1._tree_bytes(model_state)
        + lc1._tree_bytes(optimizer_state),
    )


@dataclass
class _Replica:
    site_id: str
    site: lc1._Site
    lineage_id: str
    model_lineage_id: str
    optimizer_lineage_id: str
    lineage_generation: int = 0
    last_merged_logical_epoch: int = 0
    ready: bool = True


@dataclass(frozen=True)
class _StressState:
    wall_epoch: int
    wan_bandwidth_bytes_per_second: float
    wan_latency_seconds: float
    sites: Mapping[str, Mapping[str, Any]]
    source_windows: tuple[str, ...]

    def active(self, site_id: str) -> bool:
        state = self.sites[site_id]
        return (
            bool(state["member"])
            and float(state["compute_rate_factor"]) > 0.0
        )

    def feature_vector(self) -> dict[str, float]:
        return {
            "wan_bandwidth_bytes_per_second": self.wan_bandwidth_bytes_per_second,
            "wan_latency_seconds": self.wan_latency_seconds,
            "site_a_compute_rate_factor": float(
                self.sites["site-a"]["compute_rate_factor"]
            ),
            "site_b_compute_rate_factor": float(
                self.sites["site-b"]["compute_rate_factor"]
            ),
            "active_site_count": float(sum(self.active(site) for site in SITE_IDS)),
        }


def _normalize_site_state(value: Mapping[str, Any], name: str) -> dict[str, Any]:
    member = bool(value.get("member", value.get("membership", True)))
    compute = _nonnegative_float(
        value.get(
            "compute_rate_factor",
            value.get("compute_tokens_per_second", 0.0),
        ),
        f"{name}.compute_rate_factor",
    )
    return {
        "member": member,
        "compute_rate_factor": compute,
        "power_semantics": "modeled consequence encoded by compute_rate_factor",
    }


def _normalize_stress_state(value: Mapping[str, Any], wall_epoch: int, windows: Sequence[str]) -> _StressState:
    sites = _mapping(value.get("sites"), "stress state sites")
    missing = set(SITE_IDS) - set(sites)
    if missing:
        raise ValueError(f"stress state is missing sites: {sorted(missing)}")
    return _StressState(
        wall_epoch=wall_epoch,
        wan_bandwidth_bytes_per_second=_nonnegative_float(
            value.get("wan_bandwidth_bytes_per_second"),
            "wan_bandwidth_bytes_per_second",
        ),
        wan_latency_seconds=_nonnegative_float(
            value.get("wan_latency_seconds", 0.0),
            "wan_latency_seconds",
        ),
        sites={
            site_id: _normalize_site_state(
                _mapping(sites[site_id], f"sites.{site_id}"),
                f"sites.{site_id}",
            )
            for site_id in SITE_IDS
        },
        source_windows=tuple(windows),
    )


def _stress_state(stratum: Mapping[str, Any], wall_epoch: int) -> _StressState:
    if "segments" in stratum:
        segments = list(stratum["segments"])
        if not segments:
            raise ValueError("segments cannot be empty")
        chosen: Mapping[str, Any] | None = None
        chosen_index = -1
        for index, segment_value in enumerate(segments):
            segment = _mapping(segment_value, f"segments[{index}]")
            start = int(segment["start_tick"])
            end = int(segment["end_tick"])
            if end <= start:
                raise ValueError(f"segments[{index}] has an empty interval")
            if start <= wall_epoch < end:
                chosen = segment
                chosen_index = index
                break
        if chosen is None:
            final = _mapping(segments[-1], "segments[-1]")
            if wall_epoch < int(_mapping(segments[0], "segments[0]")["start_tick"]):
                raise ValueError("segments must begin at tick zero")
            chosen = final
            chosen_index = len(segments) - 1
        active = {str(item) for item in chosen["active_sites"]}
        unknown = active - set(SITE_IDS)
        if unknown:
            raise ValueError(f"segment contains unknown active sites: {sorted(unknown)}")
        normalized = {
            "wan_bandwidth_bytes_per_second": chosen[
                "bandwidth_bytes_per_second"
            ],
            "wan_latency_seconds": stratum.get("wan_latency_seconds", 0.0),
            "sites": {
                "site-a": {
                    "member": "site-a" in active,
                    "compute_rate_factor": chosen["site_a_compute_rate"],
                },
                "site-b": {
                    "member": "site-b" in active,
                    "compute_rate_factor": chosen["site_b_compute_rate"],
                },
            },
        }
        return _normalize_stress_state(
            normalized,
            wall_epoch,
            (f"segment-{chosen_index}",),
        )

    if "stress_trace" in stratum:
        trace = list(stratum["stress_trace"])
        if not trace:
            raise ValueError("stress_trace cannot be empty")
        if wall_epoch < len(trace):
            raw = _mapping(trace[wall_epoch], f"stress_trace[{wall_epoch}]")
            return _normalize_stress_state(raw, wall_epoch, ("explicit-trace",))
        after = _mapping(
            stratum.get("stress_after_horizon", trace[-1]),
            "stress_after_horizon",
        )
        return _normalize_stress_state(after, wall_epoch, ("after-horizon",))

    stress = _mapping(stratum.get("stress"), "stratum.stress")
    horizon = _positive_int(stress.get("horizon_epochs"), "stress.horizon_epochs")
    default = _mapping(stress.get("default"), "stress.default")
    if wall_epoch >= horizon:
        after = _mapping(stress.get("after_horizon", default), "stress.after_horizon")
        return _normalize_stress_state(after, wall_epoch, ("after-horizon",))
    raw: Mapping[str, Any] = default
    active_windows: list[str] = []
    for index, window_value in enumerate(stress.get("windows", ())):
        window = _mapping(window_value, f"stress.windows[{index}]")
        start = int(window.get("start_epoch_inclusive", window.get("start_epoch")))
        end = int(window.get("end_epoch_exclusive", window.get("end_epoch")))
        if end <= start:
            raise ValueError(f"stress window {index} has an empty interval")
        if start <= wall_epoch < end:
            override = window.get("overrides")
            if override is None:
                override = {
                    key: item
                    for key, item in window.items()
                    if key
                    not in {
                        "window_id",
                        "start_epoch",
                        "end_epoch",
                        "start_epoch_inclusive",
                        "end_epoch_exclusive",
                    }
                }
            raw = _deep_merge(raw, _mapping(override, "stress window overrides"))
            active_windows.append(str(window.get("window_id", f"window-{index}")))
    return _normalize_stress_state(raw, wall_epoch, active_windows)


def _calibration_envelope(strata: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, float]]:
    values: dict[str, list[float]] = {}
    for stratum in strata:
        if "segments" in stratum:
            horizon = max(int(item["end_tick"]) for item in stratum["segments"])
        elif "stress_trace" in stratum:
            horizon = len(list(stratum["stress_trace"]))
        else:
            horizon = _positive_int(
                _mapping(stratum.get("stress"), "stratum.stress").get(
                    "horizon_epochs"
                ),
                "stress.horizon_epochs",
            )
        for wall_epoch in range(horizon):
            for key, value in _stress_state(stratum, wall_epoch).feature_vector().items():
                values.setdefault(key, []).append(value)
    if not values:
        raise ValueError("calibration requires at least one stress epoch")
    return {
        key: {"minimum": min(items), "maximum": max(items)}
        for key, items in values.items()
    }


def _ood_state(
    state: _StressState,
    envelope: Mapping[str, Mapping[str, float]],
    *,
    split: str,
) -> dict[str, Any]:
    dimensions: list[str] = []
    features = state.feature_vector()
    if split == "evaluation":
        for key, value in features.items():
            bounds = envelope[key]
            if value < float(bounds["minimum"]) or value > float(bounds["maximum"]):
                dimensions.append(key)
    return {
        "is_out_of_distribution": bool(dimensions),
        "dimensions": dimensions,
        "feature_vector": features,
        "reference": "calibration stress envelope" if split == "evaluation" else "calibration split",
    }


def _configure_runtime(torch: Any, optimization: Mapping[str, Any], seed: int) -> Any:
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    deterministic = bool(optimization.get("deterministic_cuda_algorithms", False))
    if hasattr(torch.backends, "cuda"):
        torch.backends.cuda.matmul.allow_tf32 = not deterministic
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.allow_tf32 = not deterministic
    torch.use_deterministic_algorithms(deterministic, warn_only=True)
    return torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


def _autocast_dtype(torch: Any, device: Any, optimization: Mapping[str, Any]) -> Any:
    name = str(optimization.get("autocast", "none")).lower()
    if device.type != "cuda":
        return None
    if name != "bfloat16":
        raise ValueError("semantic consistency currently supports bfloat16 CUDA autocast")
    if not torch.cuda.is_bf16_supported():
        raise RuntimeError("configured CUDA device does not support bfloat16")
    return torch.bfloat16


def _sync_device(torch: Any, device: Any) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def _train_step(
    torch: Any,
    functional: Any,
    site: lc1._Site,
    x: Any,
    y: Any,
    *,
    device: Any,
    autocast_dtype: Any,
    gradient_clip_norm: float,
) -> tuple[float, float]:
    site.model.train()
    site.optimizer.zero_grad(set_to_none=True)
    with torch.autocast(
        device_type="cuda",
        dtype=autocast_dtype or torch.bfloat16,
        enabled=device.type == "cuda",
    ):
        logits = site.model(x)
        loss = functional.cross_entropy(
            logits.reshape(-1, logits.shape[-1]),
            y.reshape(-1),
        )
    loss.backward()
    gradient_norm = torch.nn.utils.clip_grad_norm_(
        site.model.parameters(),
        gradient_clip_norm,
    )
    site.optimizer.step()
    return float(loss.detach().cpu()), float(gradient_norm.detach().cpu())


def _compute_raw_gradient(
    torch: Any,
    functional: Any,
    site: lc1._Site,
    x: Any,
    y: Any,
    *,
    device: Any,
    autocast_dtype: Any,
) -> tuple[float, tuple[Any | None, ...]]:
    """Compute a site gradient without mutating model or optimizer state."""

    site.model.train()
    site.optimizer.zero_grad(set_to_none=True)
    with torch.autocast(
        device_type="cuda",
        dtype=autocast_dtype or torch.bfloat16,
        enabled=device.type == "cuda",
    ):
        logits = site.model(x)
        loss = functional.cross_entropy(
            logits.reshape(-1, logits.shape[-1]),
            y.reshape(-1),
        )
    loss.backward()
    gradients = tuple(
        None if parameter.grad is None else parameter.grad.detach().clone()
        for parameter in site.model.parameters()
    )
    site.optimizer.zero_grad(set_to_none=True)
    return float(loss.detach().cpu()), gradients


def _aggregate_and_clip_gradients(
    torch: Any,
    gradient_sets: Sequence[Sequence[Any | None]],
    *,
    maximum_norm: float,
) -> tuple[tuple[Any | None, ...], float]:
    if not gradient_sets:
        raise ValueError("gradient aggregation requires at least one site")
    width = len(gradient_sets[0])
    if any(len(items) != width for items in gradient_sets):
        raise ValueError("site gradient tuples have different lengths")
    aggregated: list[Any | None] = []
    for index in range(width):
        values = [items[index] for items in gradient_sets]
        present = [value for value in values if value is not None]
        if not present:
            aggregated.append(None)
            continue
        if len(present) != len(values):
            raise ValueError("gradient presence differs across sites")
        total = present[0].detach().clone()
        for value in present[1:]:
            total.add_(value)
        total.mul_(1.0 / len(present))
        aggregated.append(total)
    sum_squares = torch.zeros((), dtype=torch.float64, device="cpu")
    for gradient in aggregated:
        if gradient is not None:
            cpu = gradient.detach().to(dtype=torch.float64, device="cpu")
            sum_squares += (cpu * cpu).sum()
    norm = math.sqrt(float(sum_squares))
    if norm > maximum_norm:
        scale = maximum_norm / (norm + 1e-12)
        for gradient in aggregated:
            if gradient is not None:
                gradient.mul_(scale)
    return tuple(aggregated), norm


def _apply_pending_gradient(site: lc1._Site, gradients: Sequence[Any | None]) -> None:
    site.optimizer.zero_grad(set_to_none=True)
    for parameter, gradient in zip(site.model.parameters(), gradients, strict=True):
        parameter.grad = None if gradient is None else gradient.detach().clone()
    site.optimizer.step()
    site.optimizer.zero_grad(set_to_none=True)


def _new_lineage(
    replica: _Replica,
    *,
    policy_id: str,
    logical_epoch: int,
    action: str,
    parents: Sequence[str],
) -> None:
    replica.lineage_generation += 1
    previous_model_lineage = replica.model_lineage_id
    previous_optimizer_lineage = replica.optimizer_lineage_id
    material = {
        "policy_id": policy_id,
        "site_id": replica.site_id,
        "logical_epoch": logical_epoch,
        "generation": replica.lineage_generation,
        "action": action,
        "parents": list(parents),
    }
    replica.model_lineage_id = _content_hash(
        {
            **material,
            "kind": "model",
            "previous_lineage_id": previous_model_lineage,
        }
    )
    replica.optimizer_lineage_id = _content_hash(
        {
            **material,
            "kind": "optimizer",
            "previous_lineage_id": previous_optimizer_lineage,
        }
    )
    replica.lineage_id = _content_hash(
        {
            **material,
            "model_lineage_id": replica.model_lineage_id,
            "optimizer_lineage_id": replica.optimizer_lineage_id,
        }
    )


def _lineage_snapshot(
    replica: _Replica,
    logical_epoch: int,
    *,
    measure_state_hash: bool,
) -> dict[str, Any]:
    return {
        "site_id": replica.site_id,
        "ready": replica.ready,
        "lineage_id": replica.lineage_id,
        "model_lineage_id": replica.model_lineage_id,
        "optimizer_lineage_id": replica.optimizer_lineage_id,
        "lineage_generation": replica.lineage_generation,
        "state_hash_measured": measure_state_hash,
        "model_state_sha256": (
            _state_hash(replica.site.model.state_dict())
            if measure_state_hash
            else None
        ),
        "optimizer_state_sha256": (
            _state_hash(replica.site.optimizer.state_dict())
            if measure_state_hash
            else None
        ),
        "update_age_ticks": max(
            0,
            logical_epoch - replica.last_merged_logical_epoch,
        ),
    }


def _floating_tensors(value: Any) -> Iterable[Any]:
    if hasattr(value, "detach"):
        if value.is_floating_point() or value.is_complex():
            yield value.detach()
        return
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _floating_tensors(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _floating_tensors(item)


def _rms_difference(left: Any, right: Any) -> dict[str, Any]:
    count = 0
    accumulators: dict[str, dict[str, Any]] = {}
    left_tensors = tuple(_floating_tensors(left))
    right_tensors = tuple(_floating_tensors(right))
    if len(left_tensors) != len(right_tensors):
        raise ValueError("replica states have different floating tensor counts")
    for left_tensor, right_tensor in zip(left_tensors, right_tensors, strict=True):
        if left_tensor.device != right_tensor.device:
            raise ValueError("paired replica tensors occupy different devices")
        if left_tensor.numel() == 0:
            continue
        magnitude = (left_tensor.detach() - right_tensor.detach()).abs().float()
        device_key = str(magnitude.device)
        squared_sum = magnitude.square().sum()
        tensor_maximum = magnitude.max()
        if device_key not in accumulators:
            accumulators[device_key] = {
                "sum_squares": squared_sum,
                "maximum": tensor_maximum,
                "device_type": magnitude.device.type,
            }
        else:
            accumulator = accumulators[device_key]
            accumulator["sum_squares"] = (
                accumulator["sum_squares"] + squared_sum
            )
            accumulator["maximum"] = accumulator["maximum"].maximum(
                tensor_maximum
            )
        count += int(magnitude.numel())
    sum_squares = 0.0
    maximum = 0.0
    accelerator_device_count = 0
    for accumulator in accumulators.values():
        pair = __import__("torch").stack(
            (accumulator["sum_squares"], accumulator["maximum"])
        )
        if accumulator["device_type"] != "cpu":
            accelerator_device_count += 1
        pair_values = pair.detach().cpu().tolist()
        sum_squares += float(pair_values[0])
        maximum = max(maximum, float(pair_values[1]))
    return {
        "rms": math.sqrt(sum_squares / count) if count else 0.0,
        "maximum_absolute": maximum,
        "element_count": count,
        "numeric_precision": "float32 accumulation on each tensor's existing device",
        "scalar_synchronization": (
            "one two-scalar transfer per accelerator device aggregate"
        ),
        "accelerator_device_aggregate_count": accelerator_device_count,
    }


def _replica_disagreement(left: _Replica, right: _Replica) -> dict[str, Any]:
    return {
        "model": _rms_difference(
            left.site.model.state_dict(),
            right.site.model.state_dict(),
        ),
        "optimizer": _rms_difference(
            left.site.optimizer.state_dict(),
            right.site.optimizer.state_dict(),
        ),
    }


def _energy_start(power_sampler: Any, torch: Any, device: Any) -> float:
    _sync_device(torch, device)
    power_sampler.start()
    return time.perf_counter()


def _energy_stop(
    power_sampler: Any,
    torch: Any,
    device: Any,
    started: float,
) -> tuple[float, dict[str, Any]]:
    _sync_device(torch, device)
    duration = time.perf_counter() - started
    result = dict(power_sampler.stop())
    if int(result.get("sample_count") or 0) < 2:
        result["raw_energy_j"] = None
        result["idle_subtracted_energy_j"] = None
        result["availability_reason"] = "fewer than two 10 Hz samples"
    else:
        result["availability_reason"] = None
    result["measurement_scope"] = (
        "descriptive sequence-confounded local training-device action energy; "
        "not used in primary modeled completion"
    )
    result["facility_energy"] = None
    return duration, result


def _combine_energy(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    available = [
        item
        for item in (left, right)
        if item.get("idle_subtracted_energy_j") is not None
    ]
    return {
        "sample_count": sum(int(item.get("sample_count") or 0) for item in (left, right)),
        "raw_energy_j": (
            sum(float(item["raw_energy_j"]) for item in available)
            if available
            else None
        ),
        "idle_subtracted_energy_j": (
            sum(float(item["idle_subtracted_energy_j"]) for item in available)
            if available
            else None
        ),
        "availability_reason": (
            None if available else "no action segment had two 10 Hz samples"
        ),
        "measurement_scope": (
            "descriptive sequence-confounded local training-device action energy; "
            "not used in primary modeled completion"
        ),
        "facility_energy": None,
        "covered_segment_count": len(available),
        "segment_count": 2,
    }


def _sample_commitment(
    torch: Any,
    corpora: Any,
    *,
    seed: int,
    site_id: str,
    logical_epoch: int,
    batch_size: int,
    context_length: int,
    device: Any,
) -> tuple[Any, Any, dict[str, Any]]:
    corpus = corpora.site_a if site_id == "site-a" else corpora.site_b
    x, y = lc1._sample_batch(
        torch,
        corpus,
        seed=seed,
        site_id=site_id,
        logical_tick=logical_epoch,
        stream="semantic-consistency-training",
        batch_size=batch_size,
        context_length=context_length,
        device=device,
    )
    quota_id = f"{site_id}:tick-{logical_epoch}"
    return x, y, {
        "quota_id": quota_id,
        "origin_site_id": site_id,
        "logical_tick": logical_epoch,
        "batch_seed": lc1._batch_seed(
            seed,
            site_id,
            logical_epoch,
            "semantic-consistency-training",
        ),
        "tokens": int(batch_size * context_length),
        "ordered_position": 0 if site_id == "site-a" else 1,
        "token_batch_sha256": _batch_hash(x, y),
    }


def _evaluate_state(
    torch: Any,
    functional: Any,
    evaluation_model: Any,
    replicas: Mapping[str, _Replica],
    corpora: Any,
    *,
    seed: int,
    batch_size: int,
    context_length: int,
    validation_batches: int,
    validation_seed: int,
    device: Any,
    autocast_dtype: Any,
) -> dict[str, Any]:
    ready = [replica for replica in replicas.values() if replica.ready]
    if not ready:
        ready = list(replicas.values())
    if len(ready) == 1:
        lc1._load_evaluation_state(
            torch,
            evaluation_model,
            ready[0].site,
            None,
        )
    else:
        lc1._load_evaluation_state(
            torch,
            evaluation_model,
            ready[0].site,
            ready[1].site,
        )
    mean, standard_deviation, losses = lc1._evaluate(
        torch,
        functional,
        evaluation_model,
        corpora.validation,
        seed=validation_seed + seed,
        batch_size=batch_size,
        context_length=context_length,
        validation_batches=validation_batches,
        device=device,
        autocast_dtype=autocast_dtype or torch.bfloat16,
    )
    return {
        "held_out_nll": mean,
        "held_out_nll_standard_deviation": standard_deviation,
        "validation_batch_nll": list(losses),
        "validation_batches": validation_batches,
        "evaluation_state": (
            "single ready replica" if len(ready) == 1 else "arithmetic model average"
        ),
    }


def _build_warm_checkpoint(
    scenario: Mapping[str, Any],
    corpora: Any,
) -> tuple[lc1._Checkpoint, dict[str, Any]]:
    _, _, torch, nn, functional = lc1._require_dependencies()
    optimization = _mapping(scenario["optimization"], "optimization")
    model_config = _mapping(scenario["model"], "model")
    seed = int(optimization["warm_start_seed"])
    device = _configure_runtime(torch, optimization, seed)
    autocast_dtype = _autocast_dtype(torch, device, optimization)
    model = lc1._build_model(torch, nn, functional, model_config, device)
    site = lc1._Site(model=model, optimizer=None)
    site.optimizer = lc1._optimizer(torch, model, optimization)
    batch_size = _positive_int(
        optimization["batch_size_per_site"],
        "optimization.batch_size_per_site",
    )
    context_length = _positive_int(
        model_config["context_length"],
        "model.context_length",
    )
    warm_ticks = int(optimization.get("warm_start_ticks", 0))
    final_loss: float | None = None
    for logical_tick in range(warm_ticks):
        x_a, y_a, _ = _sample_commitment(
            torch,
            corpora,
            seed=seed,
            site_id="site-a",
            logical_epoch=logical_tick,
            batch_size=batch_size,
            context_length=context_length,
            device=device,
        )
        x_b, y_b, _ = _sample_commitment(
            torch,
            corpora,
            seed=seed,
            site_id="site-b",
            logical_epoch=logical_tick,
            batch_size=batch_size,
            context_length=context_length,
            device=device,
        )
        final_loss, _ = _train_step(
            torch,
            functional,
            site,
            torch.cat((x_a, x_b), dim=0),
            torch.cat((y_a, y_b), dim=0),
            device=device,
            autocast_dtype=autocast_dtype,
            gradient_clip_norm=float(optimization["gradient_clip_norm"]),
        )
    checkpoint = lc1._checkpoint(site, warm_ticks, 0)
    reference_gradient_durations: list[float] = []
    reference_apply_durations: list[float] = []
    for site_id in SITE_IDS:
        lc1._restore(site, checkpoint)
        x, y, _ = _sample_commitment(
            torch,
            corpora,
            seed=seed,
            site_id=site_id,
            logical_epoch=warm_ticks,
            batch_size=batch_size,
            context_length=context_length,
            device=device,
        )
        _sync_device(torch, device)
        started = time.perf_counter()
        _, gradient = _compute_raw_gradient(
            torch,
            functional,
            site,
            x,
            y,
            device=device,
            autocast_dtype=autocast_dtype,
        )
        _sync_device(torch, device)
        reference_gradient_durations.append(time.perf_counter() - started)
        started = time.perf_counter()
        _apply_pending_gradient(site, gradient)
        _sync_device(torch, device)
        reference_apply_durations.append(time.perf_counter() - started)
    lc1._restore(site, checkpoint)
    return checkpoint, {
        "warm_start_ticks": warm_ticks,
        "warm_start_seed": seed,
        "final_training_nll": final_loss,
        "reference_local_site_gradient_seconds": statistics.median(
            reference_gradient_durations
        ),
        "reference_local_optimizer_apply_seconds": statistics.median(
            reference_apply_durations
        ),
        "reference_local_site_quota_step_seconds": (
            statistics.median(reference_gradient_durations)
            + statistics.median(reference_apply_durations)
        ),
        "device_type": device.type,
        "checkpoint_bytes": checkpoint.checkpoint_bytes,
        "checkpoint_sha256": _state_hash(
            {
                "model": checkpoint.model_state,
                "optimizer": checkpoint.optimizer_state,
            }
        ),
    }


def _make_run_state(
    scenario: Mapping[str, Any],
    warm_checkpoint: lc1._Checkpoint,
    warm_checkpoint_sha256: str,
    seed: int,
) -> tuple[Any, Any, Any, Any, dict[str, _Replica], Any]:
    _, _, torch, nn, functional = lc1._require_dependencies()
    optimization = _mapping(scenario["optimization"], "optimization")
    model_config = _mapping(scenario["model"], "model")
    device = _configure_runtime(torch, optimization, seed)
    autocast_dtype = _autocast_dtype(torch, device, optimization)
    replicas: dict[str, _Replica] = {}
    for site_id in SITE_IDS:
        model = lc1._build_model(torch, nn, functional, model_config, device)
        site = lc1._Site(model=model, optimizer=None)
        site.optimizer = lc1._optimizer(torch, model, optimization)
        lc1._restore(site, warm_checkpoint)
        base_hash = _content_hash(
            {
                "warm_checkpoint_sha256": warm_checkpoint_sha256,
                "site_id": site_id,
            }
        )
        replicas[site_id] = _Replica(
            site_id=site_id,
            site=site,
            lineage_id=base_hash,
            model_lineage_id=_content_hash(
                {"base": base_hash, "kind": "model"}
            ),
            optimizer_lineage_id=_content_hash(
                {"base": base_hash, "kind": "optimizer"}
            ),
        )
    evaluation_model = lc1._build_model(
        torch,
        nn,
        functional,
        model_config,
        device,
    )
    evaluation_model.load_state_dict(replicas["site-a"].site.model.state_dict())
    return torch, functional, device, autocast_dtype, replicas, evaluation_model


def _copy_replica(
    source: _Replica,
    target: _Replica,
    *,
    policy_id: str,
    logical_epoch: int,
    action: str,
) -> None:
    parents = (source.lineage_id, target.lineage_id)
    lc1._copy_site(source.site, target.site)
    target.ready = True
    target.last_merged_logical_epoch = logical_epoch
    _new_lineage(
        target,
        policy_id=policy_id,
        logical_epoch=logical_epoch,
        action=action,
        parents=parents,
    )


def _average_replicas(
    torch: Any,
    left: _Replica,
    right: _Replica,
    *,
    policy_id: str,
    logical_epoch: int,
    merge_count: int,
    action: str,
) -> lc1._Checkpoint:
    parents = (left.lineage_id, right.lineage_id)
    checkpoint = _average_checkpoints(
        torch,
        lc1._checkpoint(left.site, logical_epoch, merge_count),
        lc1._checkpoint(right.site, logical_epoch, merge_count),
        logical_epoch=logical_epoch,
        merge_count=merge_count,
    )
    lc1._restore(left.site, checkpoint)
    lc1._restore(right.site, checkpoint)
    for replica in (left, right):
        replica.ready = True
        replica.last_merged_logical_epoch = logical_epoch
        _new_lineage(
            replica,
            policy_id=policy_id,
            logical_epoch=logical_epoch,
            action=action,
            parents=parents,
        )
    return checkpoint


def _prepare_stratum(
    value: Mapping[str, Any],
    *,
    split: str,
    wan_round_trip_seconds: float,
) -> dict[str, Any]:
    prepared = copy.deepcopy(dict(value))
    if split == "evaluation" and "stratum_id" not in prepared:
        prepared["stratum_id"] = str(prepared["family_id"])
    prepared["wan_latency_seconds"] = wan_round_trip_seconds
    return prepared


def _policy_mode(
    policy_id: str,
    state: _StressState,
    *,
    controller: Mapping[str, Any],
    disagreement_rms: float,
    ood: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    active = [site for site in SITE_IDS if state.active(site)]
    abstention_reasons: list[str] = []
    if bool(ood["is_out_of_distribution"]):
        abstention_reasons.append("outside calibration stress envelope")
    if disagreement_rms >= float(
        controller["replica_disagreement_abstain_rms_gte"]
    ):
        abstention_reasons.append("replica disagreement threshold reached")
    if policy_id == SYNCHRONOUS_RESTART:
        mode = "exact_sync" if len(active) == 2 else "synchronous_restart"
    elif policy_id == EXACT_FORWARD_RECOVERY:
        mode = "exact_sync" if len(active) == 2 else "exact_forward_recovery"
    elif policy_id == DELAYED_ONE_STEP:
        mode = "delayed_one_step" if len(active) == 2 else "exact_forward_recovery"
    elif policy_id == PERIODIC_LOCAL:
        mode = "periodic_local"
    elif policy_id == OBSERVABLE_ADAPTIVE:
        if abstention_reasons:
            mode = "exact_forward_recovery"
        elif len(active) < 2:
            mode = str(controller["single_site_action"])
        else:
            bandwidth = state.wan_bandwidth_bytes_per_second
            rates = [float(state.sites[site]["compute_rate_factor"]) for site in active]
            imbalance = max(rates) / max(min(rates), 1e-12)
            if bandwidth <= float(
                controller["bandwidth_low_bytes_per_second_lte"]
            ):
                mode = str(controller["low_bandwidth_action"])
            elif (
                bandwidth
                <= float(controller["bandwidth_medium_bytes_per_second_lte"])
                or imbalance >= float(controller["compute_imbalance_ratio_gte"])
            ):
                mode = str(controller["medium_bandwidth_or_imbalance_action"])
            else:
                mode = str(controller["healthy_action"])
    else:
        raise ValueError(f"unknown executable policy {policy_id!r}")
    return mode, {
        "abstained": bool(abstention_reasons),
        "reasons": abstention_reasons,
        "fallback": (
            controller.get("uncalibrated_state_action")
            if abstention_reasons
            else None
        ),
    }


def _run_policy(
    scenario: Mapping[str, Any],
    corpora: Any,
    warm_checkpoint: lc1._Checkpoint,
    warm_metadata: Mapping[str, Any],
    stratum: Mapping[str, Any],
    *,
    split: str,
    policy_id: str,
    calibration_envelope: Mapping[str, Mapping[str, float]],
) -> dict[str, Any]:
    seed = int(stratum["seed"])
    stratum_id = str(stratum["stratum_id"])
    torch, functional, device, autocast_dtype, replicas, evaluation_model = (
        _make_run_state(
            scenario,
            warm_checkpoint,
            str(warm_metadata["checkpoint_sha256"]),
            seed,
        )
    )
    optimization = _mapping(scenario["optimization"], "optimization")
    model_config = _mapping(scenario["model"], "model")
    work = _mapping(scenario["work_contract"], "work_contract")
    controller = _mapping(scenario["controller"], "controller")
    timing = _mapping(scenario["timing_model"], "timing_model")
    target_ticks = _positive_int(work["canonical_ticks"], "canonical_ticks")
    max_wall_ticks = target_ticks * 4 + int(
        optimization["checkpoint_interval_ticks"]
    )
    batch_size = _positive_int(
        optimization["batch_size_per_site"],
        "batch_size_per_site",
    )
    context_length = _positive_int(model_config["context_length"], "context_length")
    tokens_per_quota = batch_size * context_length
    if tokens_per_quota != int(work["tokens_per_site_quota"]):
        raise ValueError(
            "work_contract.tokens_per_site_quota does not match batch_size * context_length"
        )
    local_period = _positive_int(
        optimization["local_period_ticks"],
        "local_period_ticks",
    )
    checkpoint_interval = _positive_int(
        optimization["checkpoint_interval_ticks"],
        "checkpoint_interval_ticks",
    )
    evaluation_interval = _positive_int(
        optimization["evaluation_interval_ticks"],
        "evaluation_interval_ticks",
    )
    validation_batches = _positive_int(
        optimization["validation_batches"],
        "validation_batches",
    )
    validation_seed = int(optimization["validation_seed"])
    parameter_count = sum(
        int(parameter.numel())
        for parameter in replicas["site-a"].site.model.parameters()
    )
    gradient_payload_bytes = parameter_count * int(
        timing["gradient_payload_bytes_per_parameter"]
    )
    state_payload_bytes = parameter_count * int(
        timing["state_transfer_bytes_per_parameter"]
    )
    gradient_clip_norm = float(optimization["gradient_clip_norm"])
    reference_gradient_seconds = float(
        warm_metadata["reference_local_site_gradient_seconds"]
    )
    reference_apply_seconds = float(
        warm_metadata["reference_local_optimizer_apply_seconds"]
    )
    reference_step_seconds = reference_gradient_seconds + reference_apply_seconds
    if reference_gradient_seconds <= 0.0 or reference_apply_seconds <= 0.0:
        raise ValueError(
            "warm start must provide positive frozen gradient and optimizer-apply references"
        )

    initial_measurement = _evaluate_state(
        torch,
        functional,
        evaluation_model,
        replicas,
        corpora,
        seed=seed,
        batch_size=batch_size,
        context_length=context_length,
        validation_batches=validation_batches,
        validation_seed=validation_seed,
        device=device,
        autocast_dtype=autocast_dtype,
    )
    last_measurement = dict(initial_measurement)
    power_sampler = lc1._PowerSampler()
    logical_tick = 0
    wall_tick = 0
    merge_count = 0
    local_ticks_since_merge = 0
    durable_checkpoint = lc1._checkpoint(replicas["site-a"].site, 0, 0)
    durable_tick = 0
    pending_gradient: tuple[Any | None, ...] | None = None
    pending_gradient_tick: int | None = None
    pending_gradient_hash: str | None = None
    delayed_previous_transfer_seconds = 0.0
    restart_episode_active = False
    previous_active = {
        site for site in SITE_IDS if _stress_state(stratum, 0).active(site)
    }
    attempt_counts: dict[str, int] = {}
    commitment_hashes: dict[str, str] = {}
    sample_violation_count = 0
    lineage_violation_count = 0
    mode_transitions: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    previous_mode: str | None = None
    diverged = False
    divergence_reason: str | None = None

    def wan_event(
        record: MutableMapping[str, Any],
        state: _StressState,
        *,
        kind: str,
        payload_bytes: int,
        semantics: str,
    ) -> None:
        bandwidth = state.wan_bandwidth_bytes_per_second
        if payload_bytes > 0 and bandwidth <= 0.0:
            raise RuntimeError(f"{kind} requires WAN bandwidth")
        seconds = (
            payload_bytes / bandwidth + state.wan_latency_seconds
            if payload_bytes > 0
            else 0.0
        )
        record["wan_events"].append(
            {
                "kind": kind,
                "payload_bytes": payload_bytes,
                "modeled_seconds": seconds,
                "semantics": semantics,
            }
        )

    def restore_durable(record: MutableMapping[str, Any]) -> None:
        nonlocal logical_tick, local_ticks_since_merge, pending_gradient
        nonlocal pending_gradient_tick, pending_gradient_hash
        nonlocal delayed_previous_transfer_seconds
        old_tick = logical_tick
        parents = tuple(replica.lineage_id for replica in replicas.values())
        for replica in replicas.values():
            lc1._restore(replica.site, durable_checkpoint)
            replica.ready = replica.site_id in physical_active
            replica.last_merged_logical_epoch = durable_tick
            _new_lineage(
                replica,
                policy_id=policy_id,
                logical_epoch=durable_tick,
                action="rollback_to_durable_checkpoint",
                parents=parents,
            )
        for prior in trace:
            if (
                int(prior["logical_tick_after"]) > durable_tick
                and prior["commit_outcome"] == "retained"
            ):
                accounting = prior["exact_accounting"]
                accounting["discarded_tokens"] = accounting["useful_tokens"]
                accounting["discarded_flops"] = accounting["useful_flops"]
                accounting["useful_tokens"] = 0
                accounting["useful_flops"] = 0.0
                prior["commit_outcome"] = "rolled_back"
                prior["invalidated_by_wall_tick"] = wall_tick
        logical_tick = durable_tick
        local_ticks_since_merge = 0
        pending_gradient = None
        pending_gradient_tick = None
        pending_gradient_hash = None
        delayed_previous_transfer_seconds = 0.0
        record["recovery_events"].append(
            {
                "kind": "rollback",
                "from_logical_tick": old_tick,
                "to_durable_tick": durable_tick,
                "replay_required_ticks": old_tick - durable_tick,
            }
        )

    def reconcile_ready_replicas(
        record: MutableMapping[str, Any],
        state: _StressState,
        *,
        reason: str,
    ) -> None:
        nonlocal merge_count
        ready = [replica for replica in replicas.values() if replica.ready]
        if len(ready) != 2:
            return
        disagreement = _replica_disagreement(ready[0], ready[1])
        if float(disagreement["model"]["rms"]) == 0.0 and float(
            disagreement["optimizer"]["rms"]
        ) == 0.0:
            return
        wan_event(
            record,
            state,
            kind="full_state_reconciliation",
            payload_bytes=state_payload_bytes,
            semantics="arithmetic model and AdamW-state average; not GASLoC or gossip",
        )
        merge_count += 1
        _average_replicas(
            torch,
            ready[0],
            ready[1],
            policy_id=policy_id,
            logical_epoch=logical_tick,
            merge_count=merge_count,
            action=reason,
        )
        record["merge_events"].append(
            {
                "kind": "arithmetic_full_state_average",
                "reason": reason,
                "merge_count": merge_count,
            }
        )

    def rejoin_if_possible(
        record: MutableMapping[str, Any],
        state: _StressState,
        physical_active: set[str],
    ) -> None:
        ready_survivors = [
            replica
            for site, replica in replicas.items()
            if site in physical_active and replica.ready
        ]
        returning = [
            replica
            for site, replica in replicas.items()
            if site in physical_active and not replica.ready
        ]
        if not returning:
            return
        if not ready_survivors:
            parents = tuple(replica.lineage_id for replica in replicas.values())
            for replica in returning:
                lc1._restore(replica.site, durable_checkpoint)
                replica.ready = True
                replica.last_merged_logical_epoch = durable_tick
                _new_lineage(
                    replica,
                    policy_id=policy_id,
                    logical_epoch=durable_tick,
                    action="all_sites_rejoin_from_durable_checkpoint",
                    parents=parents,
                )
            record["recovery_events"].append(
                {
                    "kind": "all_sites_rejoin_from_durable_checkpoint",
                    "durable_tick": durable_tick,
                }
            )
            return
        if state.wan_bandwidth_bytes_per_second <= 0.0:
            return
        source = ready_survivors[0]
        for target in returning:
            wan_event(
                record,
                state,
                kind="rejoin_state_transfer",
                payload_bytes=state_payload_bytes,
                semantics="survivor model and AdamW state copied to returning replica",
            )
            _copy_replica(
                source,
                target,
                policy_id=policy_id,
                logical_epoch=logical_tick,
                action="explicit_rejoin_state_copy",
            )
            record["recovery_events"].append(
                {
                    "kind": "explicit_rejoin_merge",
                    "source_site_id": source.site_id,
                    "returning_site_id": target.site_id,
                    "logical_tick": logical_tick,
                }
            )

    def flush_pending(
        record: MutableMapping[str, Any],
        state: _StressState,
        physical_active: set[str],
        *,
        reason: str,
    ) -> dict[str, float]:
        nonlocal pending_gradient, pending_gradient_tick, pending_gradient_hash
        if pending_gradient is None:
            return {}
        ready = [
            replicas[site]
            for site in SITE_IDS
            if site in physical_active and replicas[site].ready
        ]
        if not ready:
            return {}
        parents = tuple(replica.lineage_id for replica in ready)
        durations: dict[str, float] = {}
        for replica in ready:
            _sync_device(torch, device)
            started = time.perf_counter()
            _apply_pending_gradient(replica.site, pending_gradient)
            _sync_device(torch, device)
            durations[replica.site_id] = time.perf_counter() - started
            _new_lineage(
                replica,
                policy_id=policy_id,
                logical_epoch=logical_tick,
                action=reason,
                parents=parents,
            )
        for replica in ready:
            replica.last_merged_logical_epoch = logical_tick
        record["merge_events"].append(
            {
                "kind": "apply_one_step_old_aggregate_update",
                "source_logical_tick": pending_gradient_tick,
                "gradient_sha256": pending_gradient_hash,
                "reason": reason,
            }
        )
        pending_gradient = None
        pending_gradient_tick = None
        pending_gradient_hash = None
        return durations

    while logical_tick < target_ticks and wall_tick < max_wall_ticks:
        state = _stress_state(stratum, wall_tick)
        physical_active = {site for site in SITE_IDS if state.active(site)}
        active_reference_step_seconds = (
            max(
                reference_step_seconds
                / max(
                    float(state.sites[site]["compute_rate_factor"]),
                    1e-12,
                )
                for site in physical_active
            )
            if physical_active
            else reference_step_seconds
        )
        departures = sorted(previous_active - physical_active)
        rejoins = sorted(physical_active - previous_active)
        for site_id in departures:
            replicas[site_id].ready = False
        disagreement_before = _replica_disagreement(
            replicas["site-a"], replicas["site-b"]
        )
        ood = _ood_state(state, calibration_envelope, split=split)
        mode, abstention = _policy_mode(
            policy_id,
            state,
            controller=controller,
            disagreement_rms=float(disagreement_before["model"]["rms"]),
            ood=ood,
        )
        transition = None
        if mode != previous_mode:
            transition = {
                "wall_tick": wall_tick,
                "logical_tick": logical_tick,
                "from_mode": previous_mode,
                "to_mode": mode,
                "observable_reason": {
                    "bandwidth_bytes_per_second": state.wan_bandwidth_bytes_per_second,
                    "active_sites": sorted(physical_active),
                    "compute_rate_factors": {
                        site: state.sites[site]["compute_rate_factor"]
                        for site in SITE_IDS
                    },
                    "abstention": abstention,
                },
            }
            mode_transitions.append(transition)
        record: dict[str, Any] = {
            "wall_tick": wall_tick,
            "logical_tick_before": logical_tick,
            "logical_tick_after": logical_tick,
            "policy_id": policy_id,
            "selected_mode": mode,
            "mode_transition": transition,
            "stress": {
                "bandwidth_bytes_per_second": state.wan_bandwidth_bytes_per_second,
                "wan_round_trip_seconds": state.wan_latency_seconds,
                "sites": copy.deepcopy(dict(state.sites)),
                "active_sites": sorted(physical_active),
                "source_segments": list(state.source_windows),
                "power_interpretation": (
                    "compute-rate factors are the frozen modeled consequence of "
                    "available power; no power was measured"
                ),
            },
            "membership_events": {"departures": departures, "rejoins": rejoins},
            "ood_state": ood,
            "abstention_state": abstention,
            "action": None,
            "sample_commitments": [],
            "merge_events": [],
            "recovery_events": [],
            "wan_events": [],
            "training_loss": None,
            "recent_gradient_norm": None,
            "pending_update": None,
            "local_action_seconds": 0.0,
            "local_action_seconds_semantics": (
                "descriptive sequence-confounded local wall time; not used in "
                "primary modeled completion"
            ),
            "modeled_compute_seconds": 0.0,
            "measured_local_device_energy": {
                "sample_count": 0,
                "raw_energy_j": None,
                "idle_subtracted_energy_j": None,
                "availability_reason": "no local training action",
                "measurement_scope": (
                    "descriptive sequence-confounded local training-device action "
                    "energy; not used in primary modeled completion"
                ),
                "facility_energy": None,
            },
            "exact_accounting": {
                "attempted_tokens": 0,
                "useful_tokens": 0,
                "replayed_tokens": 0,
                "discarded_tokens": 0,
                "attempted_flops": 0.0,
                "useful_flops": 0.0,
                "replayed_flops": 0.0,
                "discarded_flops": 0.0,
                "flop_formula": str(optimization["flop_model"]),
            },
            "commit_outcome": "no_attempt",
            "invalidated_by_wall_tick": None,
        }
        preflush_energy: Mapping[str, Any] | None = None
        preflush_modeled_seconds = 0.0

        if policy_id == SYNCHRONOUS_RESTART and len(physical_active) < 2:
            if not restart_episode_active:
                restore_durable(record)
                restart_episode_active = True
            record["action"] = "stall_for_synchronous_membership"
            record["modeled_compute_seconds"] = active_reference_step_seconds
        else:
            if restart_episode_active and len(physical_active) == 2:
                restart_episode_active = False
                record["recovery_events"].append(
                    {"kind": "synchronous_membership_restored"}
                )
            rejoin_if_possible(record, state, physical_active)
            if mode != "delayed_one_step" and pending_gradient is not None:
                preflush_started = _energy_start(power_sampler, torch, device)
                preflush_durations = flush_pending(
                    record,
                    state,
                    physical_active,
                    reason="flush_delayed_update_before_mode_transition",
                )
                preflush_elapsed, preflush_energy = _energy_stop(
                    power_sampler,
                    torch,
                    device,
                    preflush_started,
                )
                record["local_action_seconds"] += preflush_elapsed
                if preflush_durations:
                    preflush_modeled_seconds = max(
                        reference_apply_seconds
                        / max(
                            float(state.sites[site]["compute_rate_factor"]),
                            1e-12,
                        )
                        for site in preflush_durations
                    )
                    preflush_modeled_seconds += delayed_previous_transfer_seconds
                    delayed_previous_transfer_seconds = 0.0
                    record["measured_local_device_energy"] = dict(preflush_energy)
            ready_active = [
                site
                for site in SITE_IDS
                if site in physical_active and replicas[site].ready
            ]
            if not ready_active:
                record["action"] = "stall_no_ready_site"
                record["modeled_compute_seconds"] = active_reference_step_seconds
            elif mode == "synchronous_restart" or (
                mode == "exact_sync" and len(ready_active) < 2
            ):
                record["action"] = "stall_for_exact_sync"
                record["modeled_compute_seconds"] = active_reference_step_seconds
            else:
                if mode in {"exact_sync", "delayed_one_step"}:
                    reconcile_ready_replicas(
                        record,
                        state,
                        reason="mode_requires_common_start_state",
                    )
                x_a, y_a, commitment_a = _sample_commitment(
                    torch,
                    corpora,
                    seed=seed,
                    site_id="site-a",
                    logical_epoch=logical_tick,
                    batch_size=batch_size,
                    context_length=context_length,
                    device=device,
                )
                x_b, y_b, commitment_b = _sample_commitment(
                    torch,
                    corpora,
                    seed=seed,
                    site_id="site-b",
                    logical_epoch=logical_tick,
                    batch_size=batch_size,
                    context_length=context_length,
                    device=device,
                )
                commitments = [commitment_a, commitment_b]
                replayed_tokens = 0
                for commitment in commitments:
                    quota_id = str(commitment["quota_id"])
                    attempt_counts[quota_id] = attempt_counts.get(quota_id, 0) + 1
                    commitment["attempt_number"] = attempt_counts[quota_id]
                    commitment["replayed_attempt"] = attempt_counts[quota_id] > 1
                    if commitment["replayed_attempt"]:
                        replayed_tokens += int(commitment["tokens"])
                    previous_hash = commitment_hashes.setdefault(
                        quota_id,
                        str(commitment["token_batch_sha256"]),
                    )
                    if previous_hash != commitment["token_batch_sha256"]:
                        sample_violation_count += 1
                attempted_tokens = 2 * tokens_per_quota
                flops = 6.0 * parameter_count * attempted_tokens
                replayed_flops = 6.0 * parameter_count * replayed_tokens
                record["exact_accounting"] = {
                    "attempted_tokens": attempted_tokens,
                    "useful_tokens": attempted_tokens,
                    "replayed_tokens": replayed_tokens,
                    "discarded_tokens": 0,
                    "attempted_flops": flops,
                    "useful_flops": flops,
                    "replayed_flops": replayed_flops,
                    "discarded_flops": 0.0,
                    "flop_formula": str(optimization["flop_model"]),
                }
                record["commit_outcome"] = "retained"
                energy_started = _energy_start(power_sampler, torch, device)
                local_durations: dict[str, float] = {}
                losses: list[float] = []
                gradient_norms: list[float] = []
                if mode in {"exact_sync", "exact_forward_recovery"}:
                    executor = ready_active[0]
                    parents = tuple(replica.lineage_id for replica in replicas.values())
                    gradient_sets: list[tuple[Any | None, ...]] = []
                    if len(ready_active) == 2:
                        assignments = (
                            ("site-a", x_a, y_a, commitment_a),
                            ("site-b", x_b, y_b, commitment_b),
                        )
                    else:
                        assignments = (
                            (executor, x_a, y_a, commitment_a),
                            (executor, x_b, y_b, commitment_b),
                        )
                    for assigned_site, x, y, commitment in assignments:
                        commitment["executed_by_site_id"] = assigned_site
                        started = time.perf_counter()
                        loss, gradients = _compute_raw_gradient(
                            torch,
                            functional,
                            replicas[assigned_site].site,
                            x,
                            y,
                            device=device,
                            autocast_dtype=autocast_dtype,
                        )
                        _sync_device(torch, device)
                        duration = time.perf_counter() - started
                        local_durations[assigned_site] = (
                            local_durations.get(assigned_site, 0.0) + duration
                        )
                        losses.append(loss)
                        gradient_sets.append(gradients)
                    aggregate, gradient_norm = _aggregate_and_clip_gradients(
                        torch,
                        gradient_sets,
                        maximum_norm=gradient_clip_norm,
                    )
                    apply_durations: dict[str, float] = {}
                    for site_id in ready_active:
                        started = time.perf_counter()
                        _apply_pending_gradient(replicas[site_id].site, aggregate)
                        _sync_device(torch, device)
                        apply_durations[site_id] = time.perf_counter() - started
                    gradient_norms.append(gradient_norm)
                    for site_id in ready_active:
                        _new_lineage(
                            replicas[site_id],
                            policy_id=policy_id,
                            logical_epoch=logical_tick + 1,
                            action=mode,
                            parents=parents,
                        )
                    if len(ready_active) == 2:
                        for site_id in ready_active:
                            replicas[site_id].last_merged_logical_epoch = logical_tick + 1
                        wan_event(
                            record,
                            state,
                            kind="exact_gradient_synchronization",
                            payload_bytes=gradient_payload_bytes,
                            semantics="FP32 logical aggregate-gradient payload",
                        )
                    if len(ready_active) == 2:
                        record["modeled_compute_seconds"] = max(
                            reference_step_seconds
                            / max(
                                float(state.sites[site]["compute_rate_factor"]),
                                1e-12,
                            )
                            for site in ready_active
                        )
                    else:
                        record["modeled_compute_seconds"] = (
                            2.0 * reference_gradient_seconds
                            + reference_apply_seconds
                        ) / max(
                            float(state.sites[executor]["compute_rate_factor"]),
                            1e-12,
                        )
                    record["action"] = mode
                elif mode == "delayed_one_step":
                    executor = ready_active[0]
                    had_pending_update = pending_gradient is not None
                    prior_transfer_seconds = delayed_previous_transfer_seconds
                    gradient_sets = []
                    if len(ready_active) == 2:
                        assignments = (
                            ("site-a", x_a, y_a, commitment_a),
                            ("site-b", x_b, y_b, commitment_b),
                        )
                    else:
                        assignments = (
                            (executor, x_a, y_a, commitment_a),
                            (executor, x_b, y_b, commitment_b),
                        )
                    for assigned_site, x, y, commitment in assignments:
                        commitment["executed_by_site_id"] = assigned_site
                        started = time.perf_counter()
                        loss, gradients = _compute_raw_gradient(
                            torch,
                            functional,
                            replicas[assigned_site].site,
                            x,
                            y,
                            device=device,
                            autocast_dtype=autocast_dtype,
                        )
                        _sync_device(torch, device)
                        duration = time.perf_counter() - started
                        local_durations[assigned_site] = (
                            local_durations.get(assigned_site, 0.0) + duration
                        )
                        losses.append(loss)
                        gradient_sets.append(gradients)
                    gradients, gradient_norm = _aggregate_and_clip_gradients(
                        torch,
                        gradient_sets,
                        maximum_norm=gradient_clip_norm,
                    )
                    gradient_norms.append(gradient_norm)
                    applied_durations = flush_pending(
                        record,
                        state,
                        physical_active,
                        reason="apply_prior_tick_aggregate_update_after_stale_compute",
                    )
                    pending_gradient = gradients
                    pending_gradient_tick = logical_tick
                    pending_gradient_hash = _state_hash(gradients)
                    if len(ready_active) == 2:
                        wan_event(
                            record,
                            state,
                            kind="one_step_delayed_gradient_payload",
                            payload_bytes=gradient_payload_bytes,
                            semantics="current aggregate update queued for next tick",
                        )
                    gradient_modeled_seconds = (
                        max(
                            reference_gradient_seconds
                            / max(
                                float(state.sites[site]["compute_rate_factor"]),
                                1e-12,
                            )
                            for site in ready_active
                        )
                        if len(ready_active) == 2
                        else (2.0 * reference_gradient_seconds)
                        / max(
                            float(
                                state.sites[ready_active[0]][
                                    "compute_rate_factor"
                                ]
                            ),
                            1e-12,
                        )
                    )
                    apply_modeled_seconds = (
                        max(
                            reference_apply_seconds
                            / max(
                                float(state.sites[site]["compute_rate_factor"]),
                                1e-12,
                            )
                            for site in applied_durations
                        )
                        if applied_durations
                        else 0.0
                    )
                    record["modeled_compute_seconds"] = (
                        gradient_modeled_seconds + apply_modeled_seconds
                    )
                    record["delayed_pipeline"] = {
                        "initial_fill": not had_pending_update,
                        "current_gradient_compute_seconds": gradient_modeled_seconds,
                        "previous_gradient_transfer_seconds": (
                            prior_transfer_seconds if had_pending_update else 0.0
                        ),
                        "previous_optimizer_apply_seconds": apply_modeled_seconds,
                        "critical_path_seconds": (
                            gradient_modeled_seconds
                            if not had_pending_update
                            else max(
                                gradient_modeled_seconds,
                                prior_transfer_seconds,
                            )
                            + apply_modeled_seconds
                        ),
                        "overlap_semantics": (
                            "previous aggregate-gradient transfer overlaps current "
                            "pre-apply gradient computation"
                        ),
                    }
                    record["pending_update"] = {
                        "source_logical_tick": logical_tick,
                        "age_ticks": 1,
                        "gradient_sha256": pending_gradient_hash,
                    }
                    record["action"] = "compute_and_queue_one_step_delayed_update"
                elif mode == "periodic_local":
                    if len(ready_active) == 2:
                        assignments = {
                            "site-a": (x_a, y_a, commitment_a),
                            "site-b": (x_b, y_b, commitment_b),
                        }
                        for site_id in SITE_IDS:
                            x, y, commitment = assignments[site_id]
                            commitment["executed_by_site_id"] = site_id
                            parent = replicas[site_id].lineage_id
                            started = time.perf_counter()
                            loss, gradient_norm = _train_step(
                                torch,
                                functional,
                                replicas[site_id].site,
                                x,
                                y,
                                device=device,
                                autocast_dtype=autocast_dtype,
                                gradient_clip_norm=gradient_clip_norm,
                            )
                            _sync_device(torch, device)
                            local_durations[site_id] = time.perf_counter() - started
                            losses.append(loss)
                            gradient_norms.append(gradient_norm)
                            _new_lineage(
                                replicas[site_id],
                                policy_id=policy_id,
                                logical_epoch=logical_tick + 1,
                                action="independent_local_adamw_step",
                                parents=(parent,),
                            )
                        record["modeled_compute_seconds"] = max(
                            reference_step_seconds
                            / max(float(state.sites[site]["compute_rate_factor"]), 1e-12)
                            for site in SITE_IDS
                        )
                    else:
                        executor = ready_active[0]
                        duration = 0.0
                        for x, y, commitment in (
                            (x_a, y_a, commitment_a),
                            (x_b, y_b, commitment_b),
                        ):
                            commitment["executed_by_site_id"] = executor
                            parent = replicas[executor].lineage_id
                            started = time.perf_counter()
                            loss, gradient_norm = _train_step(
                                torch,
                                functional,
                                replicas[executor].site,
                                x,
                                y,
                                device=device,
                                autocast_dtype=autocast_dtype,
                                gradient_clip_norm=gradient_clip_norm,
                            )
                            _sync_device(torch, device)
                            step_duration = time.perf_counter() - started
                            duration += step_duration
                            losses.append(loss)
                            gradient_norms.append(gradient_norm)
                            _new_lineage(
                                replicas[executor],
                                policy_id=policy_id,
                                logical_epoch=logical_tick + 1,
                                action="survivor_local_adamw_step",
                                parents=(parent,),
                            )
                        local_durations[executor] = duration
                        record["modeled_compute_seconds"] = (
                            2.0 * reference_step_seconds
                        ) / max(
                            float(state.sites[executor]["compute_rate_factor"]),
                            1e-12,
                        )
                    local_ticks_since_merge += 1
                    record["action"] = "periodic_local_updates"
                else:
                    raise RuntimeError(f"unimplemented selected mode {mode!r}")

                local_action_seconds, energy = _energy_stop(
                    power_sampler,
                    torch,
                    device,
                    energy_started,
                )
                record["local_action_seconds"] += local_action_seconds
                record["measured_local_device_energy"] = (
                    _combine_energy(preflush_energy, energy)
                    if preflush_energy is not None
                    else energy
                )
                record["training_loss"] = (
                    statistics.fmean(losses) if losses else None
                )
                record["recent_gradient_norm"] = (
                    statistics.fmean(gradient_norms) if gradient_norms else None
                )
                record["sample_commitments"] = commitments
                logical_tick += 1
                record["logical_tick_after"] = logical_tick

                if mode == "periodic_local" and local_ticks_since_merge >= local_period:
                    ready = [
                        replicas[site]
                        for site in SITE_IDS
                        if site in physical_active and replicas[site].ready
                    ]
                    if len(ready) == 2 and state.wan_bandwidth_bytes_per_second > 0.0:
                        wan_event(
                            record,
                            state,
                            kind="periodic_full_state_average",
                            payload_bytes=state_payload_bytes,
                            semantics=(
                                "arithmetic model and AdamW-state average every "
                                f"{local_period} ticks; not GASLoC or gossip"
                            ),
                        )
                        merge_count += 1
                        _average_replicas(
                            torch,
                            ready[0],
                            ready[1],
                            policy_id=policy_id,
                            logical_epoch=logical_tick,
                            merge_count=merge_count,
                            action="periodic_local_full_state_average",
                        )
                        record["merge_events"].append(
                            {
                                "kind": "periodic_arithmetic_full_state_average",
                                "merge_count": merge_count,
                            }
                        )
                        local_ticks_since_merge = 0
                    else:
                        record["merge_events"].append(
                            {
                                "kind": "periodic_merge_deferred",
                                "reason": "two ready sites and positive WAN required",
                            }
                        )

                if (
                    logical_tick % checkpoint_interval == 0
                    and mode in {"exact_sync", "exact_forward_recovery"}
                ):
                    source = next(
                        (
                            replicas[site]
                            for site in SITE_IDS
                            if replicas[site].ready
                        ),
                        None,
                    )
                    if source is not None:
                        durable_checkpoint = lc1._checkpoint(
                            source.site,
                            logical_tick,
                            merge_count,
                        )
                        durable_tick = logical_tick
                        record["merge_events"].append(
                            {
                                "kind": "durable_checkpoint",
                                "logical_tick": logical_tick,
                                "checkpoint_bytes": durable_checkpoint.checkpoint_bytes,
                            }
                        )

        record["modeled_compute_seconds"] += preflush_modeled_seconds
        wan_seconds = sum(
            float(event["modeled_seconds"]) for event in record["wan_events"]
        )
        record["modeled_wan_seconds"] = wan_seconds
        if "delayed_pipeline" in record:
            current_delayed_transfer = sum(
                float(event["modeled_seconds"])
                for event in record["wan_events"]
                if event["kind"] == "one_step_delayed_gradient_payload"
            )
            blocking_wan = wan_seconds - current_delayed_transfer
            record["delayed_pipeline"]["blocking_wan_seconds"] = blocking_wan
            record["modeled_completion_seconds"] = (
                float(record["delayed_pipeline"]["critical_path_seconds"])
                + blocking_wan
            )
            delayed_previous_transfer_seconds = current_delayed_transfer
        else:
            record["modeled_completion_seconds"] = (
                float(record["modeled_compute_seconds"]) + wan_seconds
            )
        if record["commit_outcome"] == "retained" and (
            logical_tick % evaluation_interval == 0 or logical_tick == target_ticks
        ):
            measurement = _evaluate_state(
                torch,
                functional,
                evaluation_model,
                replicas,
                corpora,
                seed=seed,
                batch_size=batch_size,
                context_length=context_length,
                validation_batches=validation_batches,
                validation_seed=validation_seed,
                device=device,
                autocast_dtype=autocast_dtype,
            )
            last_measurement = measurement
            record["held_out_measurement"] = measurement
            record["held_out_nll"] = measurement["held_out_nll"]
            record["held_out_nll_standard_deviation"] = measurement[
                "held_out_nll_standard_deviation"
            ]
        else:
            record["held_out_measurement"] = None
            record["held_out_nll"] = None
            record["held_out_nll_standard_deviation"] = None
        record["last_measured_held_out_nll"] = last_measurement["held_out_nll"]
        record["replica_disagreement_before"] = disagreement_before
        disagreement_after = _replica_disagreement(
            replicas["site-a"], replicas["site-b"]
        )
        record["replica_disagreement_after"] = disagreement_after
        state_hash_checkpoint = (
            record["held_out_measurement"] is not None
            or logical_tick >= target_ticks
            or any(
                event["kind"]
                in {
                    "arithmetic_full_state_average",
                    "periodic_arithmetic_full_state_average",
                    "durable_checkpoint",
                }
                for event in record["merge_events"]
            )
            or any(
                event["kind"]
                in {
                    "rollback",
                    "explicit_rejoin_merge",
                    "all_sites_rejoin_from_durable_checkpoint",
                }
                for event in record["recovery_events"]
            )
        )
        record["replica_lineages"] = {
            site: _lineage_snapshot(
                replica,
                logical_tick,
                measure_state_hash=state_hash_checkpoint,
            )
            for site, replica in replicas.items()
        }
        if mode == "exact_sync" and len(physical_active) == 2:
            if (
                float(disagreement_after["model"]["maximum_absolute"]) != 0.0
                or float(
                    disagreement_after["optimizer"]["maximum_absolute"]
                )
                != 0.0
            ):
                lineage_violation_count += 1
        finite_values = [
            value
            for value in (
                record["training_loss"],
                record["last_measured_held_out_nll"],
            )
            if value is not None
        ]
        if any(not math.isfinite(float(value)) for value in finite_values):
            diverged = True
            divergence_reason = "nonfinite learning quantity"
        trace.append(record)
        previous_active = physical_active
        previous_mode = mode
        wall_tick += 1
        if diverged:
            break

    if pending_gradient is not None and not diverged:
        state = _stress_state(stratum, wall_tick)
        physical_active = {site for site in SITE_IDS if state.active(site)}
        terminal: dict[str, Any] = {
            "wall_tick": wall_tick,
            "logical_tick_before": logical_tick,
            "logical_tick_after": logical_tick,
            "policy_id": policy_id,
            "selected_mode": "delayed_one_step",
            "mode_transition": None,
            "stress": {
                "bandwidth_bytes_per_second": state.wan_bandwidth_bytes_per_second,
                "wan_round_trip_seconds": state.wan_latency_seconds,
                "sites": copy.deepcopy(dict(state.sites)),
                "active_sites": sorted(physical_active),
                "source_segments": list(state.source_windows),
                "power_interpretation": "compute-rate factor only; no power measurement",
            },
            "membership_events": {"departures": [], "rejoins": []},
            "ood_state": _ood_state(state, calibration_envelope, split=split),
            "abstention_state": {"abstained": False, "reasons": [], "fallback": None},
            "action": "terminal_delayed_update_flush",
            "sample_commitments": [],
            "merge_events": [],
            "recovery_events": [],
            "wan_events": [],
            "training_loss": None,
            "recent_gradient_norm": None,
            "pending_update": None,
            "exact_accounting": {
                "attempted_tokens": 0,
                "useful_tokens": 0,
                "replayed_tokens": 0,
                "discarded_tokens": 0,
                "attempted_flops": 0.0,
                "useful_flops": 0.0,
                "replayed_flops": 0.0,
                "discarded_flops": 0.0,
                "flop_formula": str(optimization["flop_model"]),
            },
            "commit_outcome": "terminal_state_update",
            "invalidated_by_wall_tick": None,
        }
        disagreement_before = _replica_disagreement(
            replicas["site-a"], replicas["site-b"]
        )
        energy_started = _energy_start(power_sampler, torch, device)
        terminal_apply_durations = flush_pending(
            terminal,
            state,
            physical_active,
            reason="terminal_one_step_delay_flush",
        )
        terminal_elapsed, terminal["measured_local_device_energy"] = _energy_stop(
            power_sampler,
            torch,
            device,
            energy_started,
        )
        terminal["local_action_seconds"] = terminal_elapsed
        terminal["local_action_seconds_semantics"] = (
            "descriptive sequence-confounded local wall time; not used in primary "
            "modeled completion"
        )
        terminal["modeled_compute_seconds"] = (
            max(
                reference_apply_seconds
                / max(
                    float(state.sites[site]["compute_rate_factor"]),
                    1e-12,
                )
                for site in terminal_apply_durations
            )
            if terminal_apply_durations
            else 0.0
        )
        terminal["modeled_wan_seconds"] = 0.0
        terminal["delayed_pipeline"] = {
            "terminal_drain": True,
            "final_gradient_transfer_seconds": delayed_previous_transfer_seconds,
            "final_optimizer_apply_seconds": terminal["modeled_compute_seconds"],
            "critical_path_seconds": (
                delayed_previous_transfer_seconds
                + terminal["modeled_compute_seconds"]
            ),
        }
        terminal["modeled_completion_seconds"] = terminal["delayed_pipeline"][
            "critical_path_seconds"
        ]
        delayed_previous_transfer_seconds = 0.0
        last_measurement = _evaluate_state(
            torch,
            functional,
            evaluation_model,
            replicas,
            corpora,
            seed=seed,
            batch_size=batch_size,
            context_length=context_length,
            validation_batches=validation_batches,
            validation_seed=validation_seed,
            device=device,
            autocast_dtype=autocast_dtype,
        )
        terminal["held_out_measurement"] = last_measurement
        terminal["held_out_nll"] = last_measurement["held_out_nll"]
        terminal["held_out_nll_standard_deviation"] = last_measurement[
            "held_out_nll_standard_deviation"
        ]
        terminal["last_measured_held_out_nll"] = last_measurement["held_out_nll"]
        terminal["replica_disagreement_before"] = disagreement_before
        terminal["replica_disagreement_after"] = _replica_disagreement(
            replicas["site-a"], replicas["site-b"]
        )
        terminal["replica_lineages"] = {
            site: _lineage_snapshot(
                replica,
                logical_tick,
                measure_state_hash=True,
            )
            for site, replica in replicas.items()
        }
        trace.append(terminal)

    if logical_tick < target_ticks and not diverged:
        diverged = True
        divergence_reason = (
            f"failed to finish {target_ticks} canonical ticks within engine bound "
            f"of {max_wall_ticks} wall ticks"
        )

    accounting_keys = (
        "attempted_tokens",
        "useful_tokens",
        "replayed_tokens",
        "discarded_tokens",
        "attempted_flops",
        "useful_flops",
        "replayed_flops",
        "discarded_flops",
    )
    accounting = {
        key: sum(float(row["exact_accounting"][key]) for row in trace)
        for key in accounting_keys
    }
    for key in ("attempted_tokens", "useful_tokens", "replayed_tokens", "discarded_tokens"):
        accounting[key] = int(accounting[key])
    expected_tokens = target_ticks * 2 * tokens_per_quota
    work_contract_violations: list[str] = []
    if int(accounting["useful_tokens"]) != expected_tokens:
        work_contract_violations.append(
            f"useful_tokens={accounting['useful_tokens']} expected={expected_tokens}"
        )
    if len(commitment_hashes) != target_ticks * 2:
        work_contract_violations.append(
            f"unique_quota_count={len(commitment_hashes)} expected={target_ticks * 2}"
        )
    if sample_violation_count:
        work_contract_violations.append(
            f"sample_hash_mismatch_count={sample_violation_count}"
        )
    if lineage_violation_count:
        work_contract_violations.append(
            f"exact_sync_lineage_violation_count={lineage_violation_count}"
        )
    wan_bytes = sum(
        int(event["payload_bytes"])
        for row in trace
        for event in row["wan_events"]
    )
    wan_seconds = sum(float(row["modeled_wan_seconds"]) for row in trace)
    compute_seconds = sum(float(row["modeled_compute_seconds"]) for row in trace)
    completion_seconds = sum(
        float(row["modeled_completion_seconds"]) for row in trace
    )
    energy_rows = [
        row["measured_local_device_energy"]
        for row in trace
        if row["measured_local_device_energy"]["idle_subtracted_energy_j"]
        is not None
    ]
    measured_energy = {
        "idle_subtracted_energy_j": (
            sum(float(item["idle_subtracted_energy_j"]) for item in energy_rows)
            if energy_rows
            else None
        ),
        "raw_energy_j": (
            sum(float(item["raw_energy_j"]) for item in energy_rows)
            if energy_rows
            else None
        ),
        "covered_action_epochs": len(energy_rows),
        "total_action_epochs": sum(
            1 for row in trace if int(row["exact_accounting"]["attempted_tokens"]) > 0
        ),
        "scope": (
            "descriptive sequence-confounded sequential local GPU harness only; "
            "not two-site/facility energy and not used in primary modeled completion"
        ),
    }
    final_nll = float(last_measurement["held_out_nll"])
    initial_nll = float(initial_measurement["held_out_nll"])
    return {
        "run_id": f"e001-sc1:{split}:{stratum_id}:{policy_id}",
        "split": split,
        "family_or_stratum_id": stratum_id,
        "seed": seed,
        "policy_id": policy_id,
        "policy_role": "adaptive_candidate" if policy_id == OBSERVABLE_ADAPTIVE else "fixed_baseline",
        "parameter_count": parameter_count,
        "initial_held_out_nll": initial_nll,
        "final_held_out_nll": final_nll,
        "final_held_out_nll_standard_deviation": float(
            last_measurement["held_out_nll_standard_deviation"]
        ),
        "held_out_nll_progress": initial_nll - final_nll,
        "exact_accounting": {
            **accounting,
            "canonical_ticks_completed": logical_tick,
            "canonical_tokens_required": expected_tokens,
            "unique_quota_count": len(commitment_hashes),
            "sample_hash_mismatch_count": sample_violation_count,
            "lineage_violation_count": lineage_violation_count,
            "work_contract_violations": work_contract_violations,
        },
        "modeled_infrastructure": {
            "completion_seconds": completion_seconds,
            "compute_seconds": compute_seconds,
            "wan_seconds": wan_seconds,
            "inter_site_payload_bytes": wan_bytes,
            "gradient_payload_bytes_per_exchange": gradient_payload_bytes,
            "state_payload_bytes_per_exchange": state_payload_bytes,
            "frozen_compute_reference_seconds": {
                "site_gradient": reference_gradient_seconds,
                "optimizer_apply": reference_apply_seconds,
                "site_full_step": reference_step_seconds,
                "source": "single post-warm microbenchmark frozen before policy arms",
            },
            "timing_semantics": (
                "primary virtual compute uses only the frozen post-warm gradient/"
                "optimizer references scaled by scenario compute-rate factors, plus "
                "payload/bandwidth and frozen WAN round trip; delayed mode uses an "
                "explicit one-stage transfer/compute overlap recurrence"
            ),
            "local_action_seconds_role": (
                "descriptive sequence-confounded measurement; excluded from primary "
                "modeled completion"
            ),
            "compute_rate_power_boundary": (
                "input factors model consequences of available power; no power "
                "or facility energy is inferred"
            ),
        },
        "measured_local_device_energy": measured_energy,
        "mode_transitions": mode_transitions,
        "abstention_count": sum(
            bool(row["abstention_state"]["abstained"]) for row in trace
        ),
        "out_of_distribution_epoch_count": sum(
            bool(row["ood_state"]["is_out_of_distribution"]) for row in trace
        ),
        "diverged": diverged,
        "divergence_reason": divergence_reason,
        "epoch_trace": trace,
    }


def _first_decimal(text: str, name: str) -> float:
    match = re.search(r"(?<![\w.])(?:0|[1-9]\d*)(?:\.\d+)?", text)
    if match is None:
        raise ValueError(f"{name} must contain an explicit numeric threshold")
    return float(match.group(0))


def _select_calibration_comparator(
    scenario: Mapping[str, Any],
    calibration_runs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    selection = _mapping(
        scenario["comparator_selection"],
        "comparator_selection",
    )
    candidates = tuple(str(item) for item in selection["candidate_policy_ids"])
    if candidates != FIXED_POLICIES:
        raise ValueError(
            "comparator_selection.candidate_policy_ids must preserve the frozen fixed-policy order"
        )
    margin = _first_decimal(str(selection["eligibility"]), "eligibility")
    grouped = {
        policy_id: [
            run for run in calibration_runs if run["policy_id"] == policy_id
        ]
        for policy_id in candidates
    }
    synchronous = grouped[SYNCHRONOUS_RESTART]
    if not synchronous:
        raise ValueError("calibration is missing synchronous_restart")
    synchronous_median_nll = statistics.median(
        float(run["final_held_out_nll"]) for run in synchronous
    )
    rows: list[dict[str, Any]] = []
    for order, policy_id in enumerate(candidates):
        runs = grouped[policy_id]
        if not runs:
            raise ValueError(f"calibration is missing {policy_id}")
        median_nll = statistics.median(
            float(run["final_held_out_nll"]) for run in runs
        )
        divergence_count = sum(bool(run["diverged"]) for run in runs)
        contract_violation_count = sum(
            bool(run["exact_accounting"]["work_contract_violations"])
            for run in runs
        )
        eligible = (
            median_nll <= synchronous_median_nll + margin
            and divergence_count == 0
            and contract_violation_count == 0
        )
        rows.append(
            {
                "policy_id": policy_id,
                "candidate_order": order,
                "median_final_held_out_nll": median_nll,
                "synchronous_nll_plus_margin": synchronous_median_nll + margin,
                "median_modeled_completion_seconds": statistics.median(
                    float(run["modeled_infrastructure"]["completion_seconds"])
                    for run in runs
                ),
                "median_inter_site_payload_bytes": statistics.median(
                    int(run["modeled_infrastructure"]["inter_site_payload_bytes"])
                    for run in runs
                ),
                "divergence_count": divergence_count,
                "work_contract_violation_count": contract_violation_count,
                "eligible": eligible,
            }
        )
    eligible_rows = [row for row in rows if row["eligible"]]
    if not eligible_rows:
        raise RuntimeError("no fixed calibration policy satisfies the frozen eligibility rule")
    selected = min(
        eligible_rows,
        key=lambda row: (
            float(row["median_modeled_completion_seconds"]),
            float(row["median_inter_site_payload_bytes"]),
            int(row["candidate_order"]),
        ),
    )
    return {
        "selection_split": "calibration_only",
        "uses_evaluation_data": False,
        "candidate_policy_ids": list(candidates),
        "quality_margin_nll": margin,
        "eligibility_rule": str(selection["eligibility"]),
        "primary_order": str(selection["primary_order"]),
        "tie_breakers": list(selection["tie_breakers"]),
        "candidate_rows": rows,
        "selected_policy_id": selected["policy_id"],
        "frozen_before_evaluation": True,
    }


def _paired_interval(
    np: Any,
    values: Sequence[float],
    paired_interval: Mapping[str, Any],
    *,
    seed_offset: int,
    unit: str,
    direction: str,
) -> dict[str, Any]:
    if not values:
        return {
            "available": False,
            "values": [],
            "median": None,
            "lower_bound": None,
            "upper_bound": None,
            "unit": unit,
            "direction": direction,
            "reason": "no complete measured pairs",
        }
    array = np.asarray(values, dtype=np.float64)
    draws = _positive_int(paired_interval["draws"], "paired_interval.draws")
    confidence = float(paired_interval["confidence_level"])
    rng = np.random.default_rng(int(paired_interval["seed"]) + seed_offset)
    indices = rng.integers(0, len(array), size=(draws, len(array)))
    medians = np.median(array[indices], axis=1)
    alpha = (1.0 - confidence) * 0.5
    return {
        "available": True,
        "values": [float(value) for value in array],
        "median": float(np.median(array)),
        "lower_bound": float(np.quantile(medians, alpha)),
        "upper_bound": float(np.quantile(medians, 1.0 - alpha)),
        "confidence_level": confidence,
        "draws": draws,
        "method": "paired percentile bootstrap of the median",
        "unit_of_resampling": str(paired_interval["unit_of_resampling"]),
        "unit": unit,
        "direction": direction,
    }


def _oracle_stress_only_cost(
    run: Mapping[str, Any],
    warm_metadata: Mapping[str, Any],
) -> float:
    gradient_seconds = float(
        warm_metadata["reference_local_site_gradient_seconds"]
    )
    optimizer_seconds = float(
        warm_metadata["reference_local_optimizer_apply_seconds"]
    )
    full_step_seconds = gradient_seconds + optimizer_seconds
    total = 0.0
    pending_delayed_transfer = 0.0
    for epoch in run["epoch_trace"]:
        stress = epoch["stress"]
        active = list(stress["active_sites"])
        rates = [
            float(stress["sites"][site]["compute_rate_factor"])
            for site in active
            if float(stress["sites"][site]["compute_rate_factor"]) > 0.0
        ]
        attempted = int(epoch["exact_accounting"]["attempted_tokens"]) > 0
        wan_seconds = float(epoch["modeled_wan_seconds"])
        current_delayed_transfer = sum(
            float(event["modeled_seconds"])
            for event in epoch["wan_events"]
            if event["kind"] == "one_step_delayed_gradient_payload"
        )
        blocking_wan_seconds = wan_seconds - current_delayed_transfer
        applied = any(
            event["kind"] == "apply_one_step_old_aggregate_update"
            for event in epoch["merge_events"]
        )
        if attempted and epoch["selected_mode"] == "periodic_local":
            if len(rates) == 1:
                compute = (2.0 * full_step_seconds) / max(rates[0], 1e-12)
            else:
                compute = full_step_seconds / max(min(rates), 1e-12)
            if pending_delayed_transfer and applied:
                compute += pending_delayed_transfer + optimizer_seconds / max(
                    min(rates), 1e-12
                )
                pending_delayed_transfer = 0.0
            total += compute + wan_seconds
            continue
        elif attempted and epoch["selected_mode"] == "delayed_one_step":
            gradient_compute = gradient_seconds / max(min(rates), 1e-12)
            apply_compute = (
                optimizer_seconds / max(min(rates), 1e-12) if applied else 0.0
            )
            total += blocking_wan_seconds + (
                gradient_compute
                if not applied
                else max(gradient_compute, pending_delayed_transfer)
                + apply_compute
            )
            pending_delayed_transfer = current_delayed_transfer
            continue
        elif attempted:
            if len(rates) == 1:
                compute = (2.0 * gradient_seconds + optimizer_seconds) / max(
                    rates[0],
                    1e-12,
                )
            else:
                compute = full_step_seconds / max(min(rates), 1e-12)
            if pending_delayed_transfer and applied:
                compute += pending_delayed_transfer + optimizer_seconds / max(
                    min(rates), 1e-12
                )
                pending_delayed_transfer = 0.0
        elif epoch["commit_outcome"] == "terminal_state_update":
            compute = optimizer_seconds / max(min(rates), 1e-12) if rates else 0.0
            total += pending_delayed_transfer + compute + wan_seconds
            pending_delayed_transfer = 0.0
            continue
        else:
            compute = full_step_seconds
        total += compute + wan_seconds
    total += pending_delayed_transfer
    return total


def _evaluation_summary(
    scenario: Mapping[str, Any],
    evaluation_runs: Sequence[Mapping[str, Any]],
    comparator_selection: Mapping[str, Any],
    warm_metadata: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    np, _, _, _, _ = lc1._require_dependencies()
    selected_policy = str(comparator_selection["selected_policy_id"])
    lookup = {
        (str(run["family_or_stratum_id"]), str(run["policy_id"])): run
        for run in evaluation_runs
    }
    family_ids = [str(item["family_id"]) for item in scenario["evaluation_families"]]
    paired_nll: list[float] = []
    paired_payload_ratio: list[float] = []
    paired_completion_ratio: list[float] = []
    paired_attempted_flop_ratio: list[float] = []
    paired_energy_ratio: list[float] = []
    paired_oracle_regret: list[float] = []
    family_results: list[dict[str, Any]] = []
    virtual_oracles: list[dict[str, Any]] = []
    oracle_margin = _first_decimal(
        str(_mapping(scenario["oracle_objective"], "oracle_objective")["constraint"]),
        "oracle_objective.constraint",
    )
    for family_id in family_ids:
        adaptive = lookup[(family_id, OBSERVABLE_ADAPTIVE)]
        fixed = lookup[(family_id, selected_policy)]
        synchronous = lookup[(family_id, SYNCHRONOUS_RESTART)]
        fixed_payload = int(
            fixed["modeled_infrastructure"]["inter_site_payload_bytes"]
        )
        fixed_completion = float(
            fixed["modeled_infrastructure"]["completion_seconds"]
        )
        fixed_flops = float(fixed["exact_accounting"]["attempted_flops"])
        payload_ratio = (
            int(adaptive["modeled_infrastructure"]["inter_site_payload_bytes"])
            / fixed_payload
            if fixed_payload > 0
            else None
        )
        completion_ratio = (
            float(adaptive["modeled_infrastructure"]["completion_seconds"])
            / fixed_completion
            if fixed_completion > 0.0
            else None
        )
        attempted_flop_ratio = (
            float(adaptive["exact_accounting"]["attempted_flops"])
            / fixed_flops
            if fixed_flops > 0.0
            else None
        )
        adaptive_energy = adaptive["measured_local_device_energy"][
            "idle_subtracted_energy_j"
        ]
        fixed_energy = fixed["measured_local_device_energy"][
            "idle_subtracted_energy_j"
        ]
        energy_ratio = (
            float(adaptive_energy) / float(fixed_energy)
            if adaptive_energy is not None
            and fixed_energy is not None
            and float(fixed_energy) > 0.0
            else None
        )
        nll_difference = float(adaptive["final_held_out_nll"]) - float(
            fixed["final_held_out_nll"]
        )
        paired_nll.append(nll_difference)
        if payload_ratio is not None:
            paired_payload_ratio.append(payload_ratio)
        if completion_ratio is not None:
            paired_completion_ratio.append(completion_ratio)
        if attempted_flop_ratio is not None:
            paired_attempted_flop_ratio.append(attempted_flop_ratio)
        if energy_ratio is not None:
            paired_energy_ratio.append(energy_ratio)

        oracle_candidates = [
            lookup[(family_id, policy_id)] for policy_id in EXECUTABLE_POLICIES
        ]
        oracle_cost_rows = [
            {
                "policy_id": run["policy_id"],
                "stress_only_completion_seconds": _oracle_stress_only_cost(
                    run,
                    warm_metadata,
                ),
                "inter_site_payload_bytes": int(
                    run["modeled_infrastructure"]["inter_site_payload_bytes"]
                ),
            }
            for run in oracle_candidates
        ]
        oracle_choice = min(
            oracle_cost_rows,
            key=lambda row: (
                float(row["stress_only_completion_seconds"]),
                int(row["inter_site_payload_bytes"]),
                EXECUTABLE_POLICIES.index(str(row["policy_id"])),
            ),
        )
        oracle_run = lookup[(family_id, str(oracle_choice["policy_id"]))]
        oracle_learning_valid = (
            float(oracle_run["final_held_out_nll"])
            <= float(synchronous["final_held_out_nll"]) + oracle_margin
            and not bool(oracle_run["diverged"])
            and not oracle_run["exact_accounting"]["work_contract_violations"]
        )
        adaptive_stress_cost = _oracle_stress_only_cost(
            adaptive,
            warm_metadata,
        )
        oracle_stress_cost = float(oracle_choice["stress_only_completion_seconds"])
        normalized_regret = (
            (adaptive_stress_cost - oracle_stress_cost) / oracle_stress_cost
            if oracle_learning_valid and oracle_stress_cost > 0.0
            else None
        )
        if normalized_regret is not None:
            paired_oracle_regret.append(normalized_regret)
        oracle_record = {
            "run_id": f"e001-sc1:evaluation:{family_id}:{FUTURE_TRACE_ORACLE}",
            "split": "evaluation",
            "family_or_stratum_id": family_id,
            "seed": int(oracle_run["seed"]),
            "policy_id": FUTURE_TRACE_ORACLE,
            "policy_role": "hindsight_whole_policy_envelope_only",
            "executable_training_run": False,
            "selected_whole_policy_schedule": oracle_choice["policy_id"],
            "selection_used_future_stress_only": True,
            "selection_used_future_gradient_or_loss": False,
            "stress_only_completion_seconds": oracle_stress_cost,
            "post_selection_learning_valid": oracle_learning_valid,
            "normalized_adaptive_regret": normalized_regret,
            "epoch_trace": [],
            "limitation": (
                "best whole executable-policy schedule, not a dynamic per-tick oracle; "
                "learning feasibility is checked after selection and never used to reselect"
            ),
        }
        virtual_oracles.append(oracle_record)
        family_results.append(
            {
                "family_id": family_id,
                "comparator_policy_id": selected_policy,
                "adaptive_run_id": adaptive["run_id"],
                "comparator_run_id": fixed["run_id"],
                "oracle_run_id": oracle_record["run_id"],
                "paired_effects": {
                    "adaptive_minus_comparator_final_nll": nll_difference,
                    "adaptive_to_comparator_inter_site_payload_ratio": payload_ratio,
                    "adaptive_to_comparator_modeled_completion_time_ratio": completion_ratio,
                    "adaptive_to_comparator_attempted_flop_ratio": attempted_flop_ratio,
                    "adaptive_to_comparator_local_device_energy_ratio": energy_ratio,
                    "adaptive_normalized_oracle_regret": normalized_regret,
                },
                "adaptive_abstention_count": adaptive["abstention_count"],
                "adaptive_out_of_distribution_epoch_count": adaptive[
                    "out_of_distribution_epoch_count"
                ],
                "ranking_regions": {
                    "status": "unmeasured",
                    "ordering": None,
                    "reason": (
                        "epistemic bandwidth/compute/RTT corners can change the "
                        "observable controller action; ranking requires a full "
                        "counterfactual rerun and is not inferred from scalar rescaling"
                    ),
                    "envelope": copy.deepcopy(
                        scenario["uncertainty"][
                            "epistemic_infrastructure_envelope"
                        ]
                    ),
                },
                "oracle": oracle_record,
            }
        )

    paired = _mapping(
        _mapping(scenario["uncertainty"], "uncertainty")["paired_interval"],
        "uncertainty.paired_interval",
    )
    intervals = {
        "adaptive_minus_comparator_final_nll": _paired_interval(
            np,
            paired_nll,
            paired,
            seed_offset=0,
            unit="natural_log_unit_per_byte",
            direction="lower_is_better",
        ),
        "adaptive_to_comparator_inter_site_payload_ratio": _paired_interval(
            np,
            paired_payload_ratio,
            paired,
            seed_offset=1,
            unit="ratio",
            direction="lower_is_better",
        ),
        "adaptive_to_comparator_modeled_completion_time_ratio": _paired_interval(
            np,
            paired_completion_ratio,
            paired,
            seed_offset=2,
            unit="ratio",
            direction="lower_is_better",
        ),
        "adaptive_to_comparator_attempted_flop_ratio": _paired_interval(
            np,
            paired_attempted_flop_ratio,
            paired,
            seed_offset=3,
            unit="ratio",
            direction="lower_is_better",
        ),
        "adaptive_to_comparator_local_device_energy_ratio": _paired_interval(
            np,
            paired_energy_ratio,
            paired,
            seed_offset=4,
            unit="ratio",
            direction="lower_is_better",
        ),
        "adaptive_normalized_oracle_regret": _paired_interval(
            np,
            paired_oracle_regret,
            paired,
            seed_offset=5,
            unit="ratio",
            direction="lower_is_better",
        ),
    }
    return family_results, virtual_oracles, intervals


def _falsifier_outcomes(
    scenario: Mapping[str, Any],
    evaluation_runs: Sequence[Mapping[str, Any]],
    family_results: Sequence[Mapping[str, Any]],
    intervals: Mapping[str, Mapping[str, Any]],
    comparator_selection: Mapping[str, Any],
) -> dict[str, Any]:
    definitions = _mapping(scenario["falsifiers"], "falsifiers")
    adaptive_runs = [
        run for run in evaluation_runs if run["policy_id"] == OBSERVABLE_ADAPTIVE
    ]

    def upper(name: str) -> float | None:
        value = intervals[name]["upper_bound"]
        return None if value is None else float(value)

    nll_upper = upper("adaptive_minus_comparator_final_nll")
    payload_upper = upper("adaptive_to_comparator_inter_site_payload_ratio")
    completion_upper = upper(
        "adaptive_to_comparator_modeled_completion_time_ratio"
    )
    regret_upper = upper("adaptive_normalized_oracle_regret")
    outcomes = {
        "paired_evaluation_family_count": len(family_results)
        == int(definitions["paired_evaluation_family_count_eq"]),
        "adaptive_learning_noninferiority": nll_upper is not None
        and nll_upper
        <= float(
            definitions["adaptive_minus_best_fixed_final_nll_upper_bound_lte"]
        ),
        "adaptive_inter_site_payload_ratio": payload_upper is not None
        and payload_upper
        <= float(
            definitions[
                "adaptive_to_best_fixed_inter_site_payload_ratio_upper_bound_lte"
            ]
        ),
        "adaptive_modeled_completion_time_ratio": completion_upper is not None
        and completion_upper
        <= float(
            definitions[
                "adaptive_to_best_fixed_modeled_completion_time_ratio_upper_bound_lte"
            ]
        ),
        "adaptive_normalized_oracle_regret": regret_upper is not None
        and regret_upper
        <= float(definitions["adaptive_normalized_oracle_regret_upper_bound_lte"]),
        "adaptive_zero_divergence": sum(bool(run["diverged"]) for run in adaptive_runs)
        == int(definitions["adaptive_divergence_count_eq"]),
        "adaptive_zero_sample_or_lineage_violations": sum(
            bool(run["exact_accounting"]["work_contract_violations"])
            for run in adaptive_runs
        )
        == int(definitions["adaptive_sample_or_lineage_violation_count_eq"]),
        "comparator_frozen_before_evaluation": bool(
            comparator_selection["frozen_before_evaluation"]
        )
        and not bool(comparator_selection["uses_evaluation_data"]),
    }
    return {
        "definitions": copy.deepcopy(dict(definitions)),
        "outcomes": outcomes,
        "all_pass": all(outcomes.values()),
    }


def _decision_label(
    scenario: Mapping[str, Any],
    falsifiers: Mapping[str, Any],
    evaluation_runs: Sequence[Mapping[str, Any]],
) -> str:
    decisions = _mapping(scenario["decision"], "decision")
    if any(
        int(run["out_of_distribution_epoch_count"]) > 0
        for run in evaluation_runs
        if run["policy_id"] == OBSERVABLE_ADAPTIVE
    ):
        return str(decisions["out_of_distribution"])
    outcomes = falsifiers["outcomes"]
    learning = bool(outcomes["adaptive_learning_noninferiority"])
    system = bool(outcomes["adaptive_inter_site_payload_ratio"]) and bool(
        outcomes["adaptive_modeled_completion_time_ratio"]
    )
    if bool(falsifiers["all_pass"]):
        return str(decisions["all_falsifiers_pass"])
    if learning and not system:
        return str(decisions["learning_passes_but_system_gates_fail"])
    if system and not learning:
        return str(decisions["system_gates_pass_but_learning_fails"])
    if not bool(outcomes["adaptive_normalized_oracle_regret"]):
        return str(decisions["oracle_gap_high"])
    return str(decisions["fixed_policy_matches_adaptive"])


def run_e001_semantic_consistency(
    scenario_path: str | Path,
    dataset_path: str | Path,
) -> dict[str, Any]:
    """Execute the frozen E001 semantic-consistency calibration/evaluation loop."""

    scenario_file = Path(scenario_path)
    dataset_file = Path(dataset_path)
    scenario = json.loads(scenario_file.read_text(encoding="utf-8"))
    if str(scenario.get("schema")) != "gpu-stack.e001-semantic-consistency-scenario.v1":
        raise ValueError("unsupported E001 semantic-consistency scenario schema")
    panel = tuple(str(item["policy_id"]) for item in scenario["policy_panel"])
    if panel != POLICY_PANEL:
        raise ValueError("policy_panel does not match the frozen six-policy order")
    if str(_mapping(scenario["optimization"], "optimization")["optimizer"]) != "AdamW":
        raise ValueError("semantic consistency implements AdamW only; Muon is not present")
    work = _mapping(scenario["work_contract"], "work_contract")
    if tuple(str(item) for item in work["site_ids"]) != SITE_IDS:
        raise ValueError("work_contract.site_ids must be ['site-a', 'site-b']")
    if not bool(work["token_order_frozen_across_policies"]):
        raise ValueError("token order must be frozen across policies")
    if not bool(work["future_gradient_or_loss_visibility_forbidden"]):
        raise ValueError("future gradient/loss visibility must remain forbidden")

    corpora = lc1._load_byte_corpora(dataset_file, scenario["dataset"])
    warm_checkpoint, warm_metadata = _build_warm_checkpoint(scenario, corpora)
    timing = _mapping(scenario["timing_model"], "timing_model")
    wan_round_trip_seconds = float(timing["wan_round_trip_seconds"])
    calibration_strata = [
        _prepare_stratum(
            _mapping(item, "calibration stratum"),
            split="calibration",
            wan_round_trip_seconds=wan_round_trip_seconds,
        )
        for item in scenario["calibration_strata"]
    ]
    evaluation_strata = [
        _prepare_stratum(
            _mapping(item, "evaluation family"),
            split="evaluation",
            wan_round_trip_seconds=wan_round_trip_seconds,
        )
        for item in scenario["evaluation_families"]
    ]
    envelope = _calibration_envelope(calibration_strata)

    calibration_runs = [
        _run_policy(
            scenario,
            corpora,
            warm_checkpoint,
            warm_metadata,
            stratum,
            split="calibration",
            policy_id=policy_id,
            calibration_envelope=envelope,
        )
        for stratum in calibration_strata
        for policy_id in EXECUTABLE_POLICIES
    ]
    comparator_selection = _select_calibration_comparator(
        scenario,
        calibration_runs,
    )
    evaluation_runs = [
        _run_policy(
            scenario,
            corpora,
            warm_checkpoint,
            warm_metadata,
            stratum,
            split="evaluation",
            policy_id=policy_id,
            calibration_envelope=envelope,
        )
        for stratum in evaluation_strata
        for policy_id in EXECUTABLE_POLICIES
    ]
    family_results, virtual_oracles, intervals = _evaluation_summary(
        scenario,
        evaluation_runs,
        comparator_selection,
        warm_metadata,
    )
    falsifiers = _falsifier_outcomes(
        scenario,
        evaluation_runs,
        family_results,
        intervals,
        comparator_selection,
    )
    conclusion = _decision_label(
        scenario,
        falsifiers,
        evaluation_runs,
    )
    _, _, torch, _, _ = lc1._require_dependencies()
    all_runs: list[dict[str, Any]] = [
        *calibration_runs,
        *evaluation_runs,
        *virtual_oracles,
    ]
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "engine_id": ENGINE_ID,
        "experiment_id": str(scenario["experiment_id"]),
        "scenario_id": str(scenario["scenario_id"]),
        "bindings": {
            "scenario": {
                "path": str(scenario_file),
                "sha256": _sha256_file(scenario_file),
            },
            "dataset": {
                "path": str(dataset_file),
                "sha256": _sha256_file(dataset_file),
                "expected_sha256": str(scenario["dataset"]["sha256"]),
            },
            "engine_source": {
                "path": str(Path(__file__)),
                "sha256": _source_hash(),
            },
            "source_bindings": copy.deepcopy(dict(scenario["source_bindings"])),
        },
        "policy_panel": copy.deepcopy(list(scenario["policy_panel"])),
        "work_contract": copy.deepcopy(dict(work)),
        "dataset": {
            **copy.deepcopy(dict(scenario["dataset"])),
            "loaded_train_rows": corpora.train_rows,
            "loaded_validation_rows": corpora.validation_rows,
            "loaded_train_bytes": corpora.train_bytes,
            "loaded_validation_bytes": corpora.validation_bytes,
        },
        "model": copy.deepcopy(dict(scenario["model"])),
        "runtime": {
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "device": (
                torch.cuda.get_device_name(0)
                if torch.cuda.is_available()
                else "cpu"
            ),
            "deterministic_semantics": (
                "sample identity, token order, controller information, and "
                "accounting are deterministic"
            ),
            "bitwise_cuda_reproducibility": (
                "requested"
                if bool(scenario["optimization"]["deterministic_cuda_algorithms"])
                else "not guaranteed by frozen scenario"
            ),
            "warm_start": warm_metadata,
        },
        "calibration": {
            "stratum_ids": [str(item["stratum_id"]) for item in calibration_strata],
            "run_ids": [str(run["run_id"]) for run in calibration_runs],
            "comparator_selection": comparator_selection,
            "evaluation_data_used": False,
        },
        "evaluation": {
            "family_ids": [str(item["stratum_id"]) for item in evaluation_strata],
            "run_ids": [str(run["run_id"]) for run in evaluation_runs],
            "hindsight_envelope_run_ids": [
                str(run["run_id"]) for run in virtual_oracles
            ],
            "family_results": family_results,
            "paired_effects": intervals,
        },
        "comparator_selection": comparator_selection,
        "summary": {
            "selected_comparator_policy_id": comparator_selection[
                "selected_policy_id"
            ],
            "paired_effect_intervals": intervals,
            "oracle_regret_available_family_count": sum(
                row["oracle"]["normalized_adaptive_regret"] is not None
                for row in family_results
            ),
            "conclusion": conclusion,
        },
        "falsifiers": falsifiers,
        "family_results": family_results,
        "runs": all_runs,
        "uncertainty": {
            "paired_effects": intervals,
            "epistemic_infrastructure_envelope": copy.deepcopy(
                scenario["uncertainty"]["epistemic_infrastructure_envelope"]
            ),
            "calibration_stress_envelope": envelope,
            "learning_transfer": str(
                scenario["uncertainty"]["learning_transfer"]
            ),
        },
        "evidence_boundary": {
            "measured_learning": [
                "training loss on executed byte batches",
                "held-out TinyStories byte NLL at frozen evaluation ticks",
                "sequence-confounded local action duration for description only",
                "sequence-confounded local NVIDIA board energy only when NVML sampling is complete",
            ],
            "exact_accounting": [
                "quota identity and ordered token-batch hash",
                "attempted, useful, replayed, and discarded tokens",
                "causal model and AdamW lineage versions every tick",
                "full model and AdamW state hashes at evaluation, state-merge, rejoin, and final checkpoints",
                "mode transitions, update age, disagreement, merges, and rejoins",
            ],
            "modeled_infrastructure": [
                "WAN logical payload bytes and payload/bandwidth transfer time",
                "one frozen post-warm gradient/apply microbenchmark scaled by scenario compute-rate factors",
                "compute-rate factors as modeled consequences of available power",
                "formula FLOPs under the frozen 6 * parameters * tokens convention",
            ],
            "unresolved_frontier_scale_transfer": copy.deepcopy(
                scenario["claim_boundary"]["cannot_resolve"]
            ),
        },
        "assumptions": [
            "Both site quotas are committed in site-a then site-b order at every canonical tick.",
            "Exact synchronization is one AdamW step on the ordered union of both quotas.",
            "One-step delay queues the current aggregate gradient and applies it at the next tick.",
            "Periodic local mode arithmetic-averages model and AdamW state; it is not GASLoC or gossip.",
            "The virtual oracle selects one whole schedule from the five executable policies using future stress/timing cost only; it is not a dynamic oracle.",
            "Oracle learning feasibility is checked after stress-only selection and cannot trigger reselection.",
        ],
        "missing_evidence": copy.deepcopy(scenario["claim_boundary"]["cannot_resolve"]),
    }
    result["artifact_sha256"] = _content_hash(result)
    return result
