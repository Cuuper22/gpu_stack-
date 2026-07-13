"""Physical multi-GPU runtime for E002-PW3 recovery-graph dephasing.

PW3 is intentionally a physical experiment rather than a rack-power model.
It launches under ``torchrun``, assigns every disjoint pair of ranks to one
two-site training job, performs real checkpoint and rejoin state movement, and
keeps every electrical conclusion behind the configured rack boundary meters.

The compact result contains the complete paired analysis and enough bounded
trace data to explain the result in the observatory.  Exact event and telemetry
streams remain in atomic, hash-chained JSONL chunks referenced by the result.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from bisect import bisect_left
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import random
import socket
import statistics
import time
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence

from . import e001_learning_calibration as lc1
from .e002_rack_scheduler import (
    EventRecord,
    OperationRequest,
    POLICIES,
    StateFlowLedger,
    VisibleRackState,
    schedule_state_flow_batch,
)
from .e002_rack_telemetry import (
    COOLING_BOUNDARY,
    GPU_BOARD_BOUNDARY,
    RACK_AC_INPUT_BOUNDARY,
    STORAGE_ACTIVITY_BOUNDARY,
    STORAGE_POWER_BOUNDARY,
    ChunkedJsonlWriter,
    ExternalTelemetrySession,
    GpuTelemetrySampler,
    TelemetryConfig,
    TelemetrySessionResult,
    load_telemetry_config,
)


SCHEMA = "gpu-stack.e002-rack-dephasing-evidence.v3"
ENGINE_ID = "gpu-stack.e002-rack-dephasing.v3"
SCENARIO_SCHEMA = "gpu-stack.e002-rack-dephasing-scenario.v3"
EXPERIMENT_ID = "E002-PW3"

_MOVABLE_KINDS = frozenset(
    {
        "checkpoint-capture",
        "checkpoint-persist",
        "state-transfer",
        "communicator-rebuild",
        "rejoin-commit",
    }
)
_STATE_FLOW_KINDS = _MOVABLE_KINDS | {
    "durable-cut-commit",
    "failure-observed",
    "optimizer-merge",
}
_DISPLAY_EVENT_LIMIT = 4096
_DISPLAY_RACK_POINT_LIMIT = 600


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _content_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _percentile(values: Sequence[float], probability: float) -> float | None:
    finite = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not finite:
        return None
    if len(finite) == 1:
        return finite[0]
    position = min(1.0, max(0.0, probability)) * (len(finite) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return finite[lower]
    fraction = position - lower
    return finite[lower] * (1.0 - fraction) + finite[upper] * fraction


def _median(values: Iterable[float | int | None]) -> float | None:
    selected = [float(value) for value in values if value is not None and _finite(value)]
    return statistics.median(selected) if selected else None


def _safe_relative(path: str | Path, root: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    if temporary.exists():
        raise FileExistsError(f"unfinished result exists: {temporary}")
    encoded = (json.dumps(payload, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with temporary.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory_fd: int | None = None
    try:
        directory_fd = os.open(path.parent, os.O_RDONLY)
        os.fsync(directory_fd)
    except OSError:
        # Windows does not expose directory fsync through every filesystem.
        pass
    finally:
        if directory_fd is not None:
            os.close(directory_fd)


def _stable_seed(*parts: object) -> int:
    material = ":".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big") & 0x7FFF_FFFF


def _resolve_binding_path(scenario_path: Path, value: str | Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    cwd_candidate = Path.cwd() / candidate
    if cwd_candidate.exists():
        return cwd_candidate
    repository_root = scenario_path.resolve().parents[2]
    return repository_root / candidate


def _validate_source_bindings(
    scenario: Mapping[str, Any], scenario_path: Path
) -> dict[str, Any]:
    checked: dict[str, Any] = {}
    for binding_id, raw in scenario["source_bindings"].items():
        if not isinstance(raw, Mapping) or "path" not in raw:
            raise ValueError(f"invalid PW3 source binding {binding_id!r}")
        bound_path = _resolve_binding_path(scenario_path, str(raw["path"]))
        expected_artifact = raw.get("artifact_sha256")
        expected_content = raw.get("content_sha256")
        if expected_artifact is not None:
            payload = json.loads(bound_path.read_text(encoding="utf-8"))
            without_hash = dict(payload)
            embedded = without_hash.pop("artifact_sha256", None)
            actual = _content_hash(without_hash)
            if embedded != expected_artifact or actual != expected_artifact:
                raise ValueError(f"PW3 source artifact mismatch: {binding_id}")
            checked[binding_id] = {
                "path": str(raw["path"]),
                "artifact_sha256": str(expected_artifact),
            }
        elif expected_content is not None:
            payload = json.loads(bound_path.read_text(encoding="utf-8"))
            actual = _content_hash(payload)
            if actual != expected_content:
                raise ValueError(f"PW3 source content mismatch: {binding_id}")
            checked[binding_id] = {
                "path": str(raw["path"]),
                "content_sha256": str(expected_content),
            }
        else:
            raise ValueError(f"PW3 source binding {binding_id!r} has no digest")
    return checked


def _validate_primary_telemetry_binding(
    scenario: Mapping[str, Any], config: TelemetryConfig
) -> None:
    """Prove that the configured primary channel is the frozen rack meter."""

    manifests = [
        dict(channel)
        for source in config.sources
        for channel in source.get("channels", ())
    ]
    example_endpoints = [
        str(source.get("endpoint", {}).get("url", ""))
        for source in config.sources
        if ".invalid" in str(source.get("endpoint", {}).get("url", ""))
    ]
    if example_endpoints:
        raise ValueError("PW3 telemetry config still uses an example-only endpoint")
    unresolved_examples = [
        str(channel.get("channel_id"))
        for channel in manifests
        if str(channel.get("channel_id")) in config.required_channels
        and bool(channel.get("metadata", {}).get("example_not_a_measurement_binding"))
    ]
    if unresolved_examples:
        raise ValueError(
            "PW3 telemetry config still contains example-only measurement bindings: "
            + ", ".join(sorted(unresolved_examples))
        )
    channel_id = config.rack_state_channels.get("rack_power_w")
    if not channel_id:
        raise ValueError("PW3 telemetry config must bind rack_state_channels.rack_power_w")
    matches = [
        channel
        for channel in manifests
        if str(channel.get("channel_id")) == str(channel_id)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"PW3 primary rack-PDU binding {channel_id!r} must resolve exactly once"
        )
    manifest = matches[0]
    expected_kind = str(scenario["telemetry"]["rack_pdu_power"]["sample_kind"])
    if (
        str(manifest.get("boundary")) != RACK_AC_INPUT_BOUNDARY
        or str(manifest.get("unit")) != "W"
        or str(manifest.get("sample_kind")) != expected_kind
    ):
        raise ValueError(
            "PW3 primary rack-PDU channel must be rack-ac-input/W/"
            f"{expected_kind}"
        )
    if str(channel_id) not in config.required_channels:
        raise ValueError("PW3 primary rack-PDU channel must be required")
    maximum_period_ns = int(
        float(
            scenario["telemetry"]["rack_pdu_power"][
                "maximum_effective_period_ms"
            ]
        )
        * 1e6
    )
    if int(manifest.get("nominal_period_ns", 0)) > maximum_period_ns:
        raise ValueError("PW3 primary rack-PDU nominal period exceeds the frozen limit")
    if config.poll_period_ns > maximum_period_ns:
        raise ValueError("PW3 telemetry poll period exceeds the frozen rack-PDU limit")

    storage_power = [
        channel
        for channel in manifests
        if str(channel.get("boundary")) == STORAGE_POWER_BOUNDARY
        and str(channel.get("unit")) == "W"
        and str(channel.get("sample_kind")) in {"gauge", "interval_average"}
        and str(channel.get("channel_id")) in config.required_channels
    ]
    if not storage_power:
        raise ValueError("PW3 requires a direct, required storage-power channel in W")
    required_cooling = {
        "cooling_power_w": "W",
        "rack_inlet_temperature_c": "Cel",
        "rack_outlet_temperature_c": "Cel",
    }
    for metric, unit in required_cooling.items():
        matching = [
            channel
            for channel in manifests
            if str(channel.get("boundary")) == COOLING_BOUNDARY
            and str(channel.get("metric")) == metric
            and str(channel.get("unit")) == unit
            and str(channel.get("sample_kind")) in {"gauge", "interval_average"}
            and str(channel.get("channel_id")) in config.required_channels
        ]
        if not matching:
            raise ValueError(
                f"PW3 requires direct cooling channel {metric!r} in {unit}"
            )


def _engine_identity() -> dict[str, Any]:
    directory = Path(__file__).resolve().parent
    components = {
        "runtime": _source_hash(Path(__file__).resolve()),
        "scheduler": _source_hash(directory / "e002_rack_scheduler.py"),
        "telemetry": _source_hash(directory / "e002_rack_telemetry.py"),
        "learning": _source_hash(directory / "e001_learning_calibration.py"),
    }
    return {
        "engine_id": ENGINE_ID,
        "source_sha256": components["runtime"],
        "component_sha256": components,
        "bundle_sha256": _content_hash(components),
    }


@dataclass
class _DistributedRuntime:
    torch: Any
    dist: Any
    rank: int
    world_size: int
    local_rank: int
    job_id: int
    within_job_rank: int
    pair_ranks: tuple[int, int]
    device: Any
    control_group: Any
    pair_control_group: Any
    pair_train_group: Any
    owns_default_group: bool
    discovered_gpu_uuid: str | None = None

    @property
    def is_root(self) -> bool:
        return self.rank == 0

    @property
    def is_job_leader(self) -> bool:
        return self.within_job_rank == 0

    @property
    def job_count(self) -> int:
        return self.world_size // 2


def _initialize_distributed(torch: Any, scenario: Mapping[str, Any]) -> _DistributedRuntime:
    dist = torch.distributed
    for name in ("RANK", "WORLD_SIZE", "LOCAL_RANK"):
        if name not in os.environ:
            raise RuntimeError(f"PW3 must be launched by torchrun; {name} is unset")
    rank = int(os.environ["RANK"])
    world_size = int(os.environ["WORLD_SIZE"])
    local_rank = int(os.environ["LOCAL_RANK"])
    runtime = scenario["runtime"]
    minimum = int(runtime["minimum_world_size"])
    if world_size < minimum:
        raise RuntimeError(f"PW3 requires at least {minimum} ranks, received {world_size}")
    if bool(runtime["world_size_must_be_even"]) and world_size % 2:
        raise RuntimeError("PW3 world size must be even")
    if int(runtime["ranks_per_job"]) != 2:
        raise ValueError("this frozen PW3 runtime requires exactly two ranks per job")
    if not torch.cuda.is_available():
        raise RuntimeError("PW3 requires one CUDA device per torchrun process")
    if local_rank >= torch.cuda.device_count():
        raise RuntimeError(
            f"LOCAL_RANK={local_rank} exceeds visible CUDA devices={torch.cuda.device_count()}"
        )
    torch.cuda.set_device(local_rank)
    device = torch.device("cuda", local_rank)
    owns_default = not dist.is_initialized()
    if owns_default:
        dist.init_process_group(backend=str(runtime["distributed_backend"]))
    if dist.get_rank() != rank or dist.get_world_size() != world_size:
        raise RuntimeError("torchrun environment and initialized process group disagree")

    all_ranks = list(range(world_size))
    control_group = dist.new_group(
        ranks=all_ranks,
        backend=str(runtime["control_backend"]),
    )
    job_id = rank // 2
    pair_train_group = None
    pair_control_group = None
    for first in range(0, world_size, 2):
        ranks = [first, first + 1]
        train_group = dist.new_group(
            ranks=ranks,
            backend=str(runtime["distributed_backend"]),
        )
        pair_control = dist.new_group(
            ranks=ranks,
            backend=str(runtime["control_backend"]),
        )
        if rank in ranks:
            pair_train_group = train_group
            pair_control_group = pair_control
    if pair_train_group is None or pair_control_group is None:
        raise RuntimeError("failed to create the process-local PW3 job pair")
    return _DistributedRuntime(
        torch=torch,
        dist=dist,
        rank=rank,
        world_size=world_size,
        local_rank=local_rank,
        job_id=job_id,
        within_job_rank=rank % 2,
        pair_ranks=(job_id * 2, job_id * 2 + 1),
        device=device,
        control_group=control_group,
        pair_control_group=pair_control_group,
        pair_train_group=pair_train_group,
        owns_default_group=owns_default,
    )


def _destroy_distributed(
    runtime: _DistributedRuntime, *, synchronize: bool = True
) -> None:
    dist = runtime.dist
    if synchronize:
        try:
            dist.barrier(group=runtime.control_group)
        except Exception:
            pass
    for group in (
        runtime.pair_train_group,
        runtime.pair_control_group,
        runtime.control_group,
    ):
        try:
            dist.destroy_process_group(group)
        except Exception:
            pass
    if runtime.owns_default_group:
        try:
            dist.destroy_process_group()
        except Exception:
            pass


def _all_gather_object(runtime: _DistributedRuntime, value: Any) -> list[Any]:
    gathered: list[Any] = [None] * runtime.world_size
    runtime.dist.all_gather_object(gathered, value, group=runtime.control_group)
    return gathered


def _broadcast_object(runtime: _DistributedRuntime, value: Any) -> Any:
    container = [value if runtime.is_root else None]
    runtime.dist.broadcast_object_list(container, src=0, group=runtime.control_group)
    return container[0]


def _pair_gather_object(runtime: _DistributedRuntime, value: Any) -> list[Any]:
    gathered: list[Any] = [None, None]
    runtime.dist.all_gather_object(
        gathered,
        value,
        group=runtime.pair_control_group,
    )
    return gathered


def _sleep_until_utc(target_ns: int) -> None:
    while True:
        remaining = target_ns - time.time_ns()
        if remaining <= 0:
            return
        if remaining > 2_000_000:
            time.sleep((remaining - 1_000_000) / 1_000_000_000)
        else:
            time.sleep(0)


def _configure_torch(torch: Any, seed: int) -> None:
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True, warn_only=True)


def _new_site(
    torch: Any,
    nn: Any,
    functional: Any,
    scenario: Mapping[str, Any],
    runtime: _DistributedRuntime,
    *,
    seed: int,
) -> Any:
    _configure_torch(torch, seed)
    model = lc1._build_model(
        torch,
        nn,
        functional,
        scenario["model"],
        runtime.device,
    )
    optimizer = lc1._optimizer(torch, model, scenario["optimization"])
    return lc1._Site(model=model, optimizer=optimizer)


def _quota(
    torch: Any,
    functional: Any,
    scenario: Mapping[str, Any],
    corpora: Any,
    site: Any,
    *,
    seed: int,
    site_id: str,
    logical_tick: int,
    stream: str,
    device: Any,
) -> float:
    optimization = scenario["optimization"]
    corpus = corpora.site_a if site_id == "site-a" else corpora.site_b
    x, y = lc1._sample_batch(
        torch,
        corpus,
        seed=seed,
        site_id=site_id,
        logical_tick=logical_tick,
        stream=stream,
        batch_size=int(optimization["batch_size_per_rank"]),
        context_length=int(scenario["model"]["context_length"]),
        device=device,
    )
    return lc1._train_step(
        torch,
        functional,
        site,
        x,
        y,
        autocast_dtype=torch.bfloat16,
        gradient_clip_norm=float(optimization["gradient_clip_norm"]),
    )


def _distributed_average_site(runtime: _DistributedRuntime, site: Any) -> None:
    """Reproduce LC1 averaging with one LC1 site resident on each rank."""

    torch = runtime.torch
    dist = runtime.dist
    group = runtime.pair_train_group
    with torch.no_grad():
        for parameter in site.model.parameters():
            dist.all_reduce(parameter.data, op=dist.ReduceOp.SUM, group=group)
            parameter.data.mul_(0.5)
        for buffer in site.model.buffers():
            if buffer.is_floating_point():
                dist.all_reduce(buffer.data, op=dist.ReduceOp.SUM, group=group)
                buffer.data.mul_(0.5)
            else:
                dist.all_reduce(buffer.data, op=dist.ReduceOp.MAX, group=group)

    for parameter in site.model.parameters():
        state = site.optimizer.state.get(parameter, {})
        key_lists = _pair_gather_object(runtime, tuple(sorted(state)))
        if key_lists[0] != key_lists[1]:
            raise RuntimeError("pair optimizer state structure diverged before merge")
        for key in key_lists[0]:
            value = state[key]
            if not torch.is_tensor(value):
                values = _pair_gather_object(runtime, value)
                if values[0] != values[1]:
                    raise RuntimeError(f"non-tensor optimizer state {key!r} diverged")
                continue
            if value.is_floating_point():
                dist.all_reduce(value, op=dist.ReduceOp.SUM, group=group)
                value.mul_(0.5)
            else:
                dist.all_reduce(value, op=dist.ReduceOp.MAX, group=group)


def _broadcast_site_state(runtime: _DistributedRuntime, site: Any) -> int:
    """Transfer the survivor's exact model and Adam state over the pair."""

    torch = runtime.torch
    dist = runtime.dist
    source = runtime.pair_ranks[0]
    transferred = 0
    with torch.no_grad():
        for tensor in site.model.state_dict().values():
            dist.broadcast(tensor, src=source, group=runtime.pair_train_group)
            transferred += int(tensor.numel()) * int(tensor.element_size())
    optimizer_state = site.optimizer.state_dict()
    local_structure: list[tuple[int, tuple[tuple[str, Any], ...]]] = []
    for parameter_id in sorted(optimizer_state["state"]):
        entries: list[tuple[str, Any]] = []
        for key in sorted(optimizer_state["state"][parameter_id]):
            value = optimizer_state["state"][parameter_id][key]
            if torch.is_tensor(value):
                entries.append(
                    (
                        str(key),
                        (tuple(value.shape), str(value.dtype)),
                    )
                )
            else:
                entries.append((str(key), ("scalar", value)))
        local_structure.append((int(parameter_id), tuple(entries)))
    structures = _pair_gather_object(runtime, tuple(local_structure))
    if structures[0] != structures[1]:
        raise RuntimeError("optimizer structure diverged before state transfer")
    for parameter_id in sorted(optimizer_state["state"]):
        for key in sorted(optimizer_state["state"][parameter_id]):
            value = optimizer_state["state"][parameter_id][key]
            if torch.is_tensor(value):
                dist.broadcast(value, src=source, group=runtime.pair_train_group)
                transferred += int(value.numel()) * int(value.element_size())
            else:
                values = [value if runtime.is_job_leader else None]
                dist.broadcast_object_list(
                    values,
                    src=source,
                    group=runtime.pair_control_group,
                )
                optimizer_state["state"][parameter_id][key] = values[0]
    site.optimizer.load_state_dict(optimizer_state)
    return transferred


def _rebuild_pair_communicator(runtime: _DistributedRuntime) -> None:
    """Destroy and recreate the disjoint job's NCCL communicator in place."""

    dist = runtime.dist
    dist.barrier(group=runtime.pair_train_group)
    old_group = runtime.pair_train_group
    dist.destroy_process_group(old_group)
    runtime.pair_train_group = dist.new_group(
        ranks=list(runtime.pair_ranks),
        backend="nccl",
        use_local_synchronization=True,
    )
    dist.barrier(group=runtime.pair_train_group)


def _hash_tensor(hasher: Any, torch: Any, tensor: Any) -> None:
    contiguous = tensor.detach().cpu().contiguous()
    hasher.update(str(contiguous.dtype).encode("ascii"))
    hasher.update(json.dumps(list(contiguous.shape), separators=(",", ":")).encode("ascii"))
    if contiguous.numel():
        hasher.update(contiguous.view(torch.uint8).numpy().tobytes())


def _hash_tree(hasher: Any, torch: Any, value: Any) -> None:
    if torch.is_tensor(value):
        hasher.update(b"tensor:")
        _hash_tensor(hasher, torch, value)
    elif isinstance(value, Mapping):
        hasher.update(b"mapping{")
        for key in sorted(value, key=lambda item: str(item)):
            hasher.update(repr(key).encode("utf-8"))
            _hash_tree(hasher, torch, value[key])
        hasher.update(b"}")
    elif isinstance(value, (tuple, list)):
        hasher.update(b"sequence[")
        for item in value:
            _hash_tree(hasher, torch, item)
        hasher.update(b"]")
    else:
        hasher.update(json.dumps(value, sort_keys=True, default=str).encode("utf-8"))


def _site_state_hash(runtime: _DistributedRuntime, site: Any) -> str:
    digest = hashlib.sha256()
    _hash_tree(digest, runtime.torch, site.model.state_dict())
    _hash_tree(digest, runtime.torch, site.optimizer.state_dict())
    return digest.hexdigest()


@dataclass
class _WarmState:
    checkpoint: Any
    state_sha256: str
    seed: int
    ticks: int
    quota_count: int
    attempted_tokens: int
    losses: tuple[float, ...]


def _build_block_warm_state(
    runtime: _DistributedRuntime,
    scenario: Mapping[str, Any],
    corpora: Any,
    block_id: str,
    torch: Any,
    nn: Any,
    functional: Any,
) -> tuple[Any, _WarmState]:
    seed = _stable_seed(EXPERIMENT_ID, scenario["scenario_id"], block_id, runtime.job_id)
    site = _new_site(torch, nn, functional, scenario, runtime, seed=seed)
    ticks = int(scenario["optimization"]["warmup_ticks"])
    merge_ticks = int(scenario["optimization"]["healthy_merge_ticks"])
    losses: list[float] = []
    for logical_tick in range(ticks):
        site_id = "site-a" if runtime.within_job_rank == 0 else "site-b"
        loss = _quota(
            torch,
            functional,
            scenario,
            corpora,
            site,
            seed=seed,
            site_id=site_id,
            logical_tick=logical_tick,
            stream="pw3-block-warmup",
            device=runtime.device,
        )
        losses.append(loss)
        if not math.isfinite(loss):
            raise RuntimeError(f"PW3 warm state diverged in block {block_id}")
        if (logical_tick + 1) % merge_ticks == 0:
            _distributed_average_site(runtime, site)
    runtime.dist.barrier(group=runtime.pair_train_group)
    state_hash = _site_state_hash(runtime, site)
    pair_hashes = _pair_gather_object(runtime, state_hash)
    if len(set(pair_hashes)) != 1:
        raise RuntimeError(f"PW3 warm state differs within job {runtime.job_id}")
    checkpoint = lc1._checkpoint(site, 0, 0)
    tokens_per_quota = int(scenario["canonical_work"]["tokens_per_rank_quota"])
    warm = _WarmState(
        checkpoint=checkpoint,
        state_sha256=state_hash,
        seed=seed,
        ticks=ticks,
        quota_count=ticks * 2,
        attempted_tokens=ticks * 2 * tokens_per_quota,
        losses=tuple(losses),
    )
    return site, warm


@dataclass
class _OperationModel:
    """Calibration-only online estimates visible to the deployed scheduler."""

    duration_ns: MutableMapping[str, list[int]] = field(default_factory=dict)
    power_delta_w: MutableMapping[str, list[float]] = field(default_factory=dict)

    _DEFAULT_DURATION_NS = {
        "checkpoint-capture": 120_000_000_000,
        "checkpoint-persist": 300_000_000_000,
        "state-transfer": 60_000_000_000,
        "communicator-rebuild": 30_000_000_000,
        "rejoin-commit": 1_000_000_000,
    }
    _DEFAULT_POWER_W = {
        "checkpoint-capture": 80.0,
        "checkpoint-persist": 30.0,
        "state-transfer": 120.0,
        "communicator-rebuild": 60.0,
        "rejoin-commit": 10.0,
    }

    def predict_duration(self, kind: str) -> int:
        observed = self.duration_ns.get(kind, [])
        estimate = _percentile([float(value) for value in observed], 0.90)
        default = self._DEFAULT_DURATION_NS[kind]
        return int(estimate * 1.20) if estimate is not None else default

    def predict_power(self, kind: str) -> float:
        observed = self.power_delta_w.get(kind, [])
        estimate = _median(observed)
        return max(0.0, float(estimate if estimate is not None else self._DEFAULT_POWER_W[kind]))

    def observe(self, kind: str, duration_ns: int, power_delta_w: float | None) -> None:
        self.duration_ns.setdefault(kind, []).append(max(1, int(duration_ns)))
        self.duration_ns[kind] = self.duration_ns[kind][-256:]
        if power_delta_w is not None and _finite(power_delta_w):
            self.power_delta_w.setdefault(kind, []).append(max(0.0, float(power_delta_w)))
            self.power_delta_w[kind] = self.power_delta_w[kind][-256:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "duration_ns": {key: list(value) for key, value in self.duration_ns.items()},
            "power_delta_w": {key: list(value) for key, value in self.power_delta_w.items()},
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "_OperationModel":
        return cls(
            duration_ns={
                str(key): [int(item) for item in values]
                for key, values in value.get("duration_ns", {}).items()
            },
            power_delta_w={
                str(key): [float(item) for item in values]
                for key, values in value.get("power_delta_w", {}).items()
            },
        )


class _HashingWriter:
    """Sequential file adapter used to hash the exact durable torch stream."""

    def __init__(self, handle: Any) -> None:
        self.handle = handle
        self.digest = hashlib.sha256()
        self.bytes_written = 0

    def write(self, value: bytes) -> int:
        written = self.handle.write(value)
        if written != len(value):
            raise OSError("short checkpoint write")
        self.digest.update(value)
        self.bytes_written += written
        return written

    def flush(self) -> None:
        self.handle.flush()

    def tell(self) -> int:
        return self.handle.tell()

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        current = self.handle.tell()
        target = offset if whence == os.SEEK_SET else current + offset
        if whence == os.SEEK_END or target != current:
            raise OSError("PW3 durable writer requires a sequential torch stream")
        return current

    def fileno(self) -> int:
        return self.handle.fileno()

    def writable(self) -> bool:
        return True

    def __getattr__(self, name: str) -> Any:
        return getattr(self.handle, name)


@dataclass
class _CapturedCheckpoint:
    payload: Mapping[str, Any]
    checkpoint_bytes: int
    state_sha256: str
    generation: str
    logical_tick: int


@dataclass
class _DurableCheckpoint:
    path: str
    file_bytes: int
    file_sha256: str
    state_sha256: str
    generation: str
    logical_tick: int
    committed_at_ns: int


def _capture_checkpoint(
    runtime: _DistributedRuntime,
    site: Any,
    *,
    generation: str,
    logical_tick: int,
    merge_count: int,
    quota_ids: Sequence[str],
) -> _CapturedCheckpoint:
    checkpoint = lc1._checkpoint(site, logical_tick, merge_count)
    state_hash = _site_state_hash(runtime, site)
    payload = {
        "schema": "gpu-stack.e002-pw3-durable-checkpoint.v1",
        "experiment_id": EXPERIMENT_ID,
        "job_id": runtime.job_id,
        "generation": generation,
        "logical_tick": logical_tick,
        "merge_count": merge_count,
        "state_sha256": state_hash,
        "quota_ids": list(quota_ids),
        "random_state": {
            "torch_cpu": runtime.torch.get_rng_state(),
            "torch_cuda": runtime.torch.cuda.get_rng_state(runtime.device),
            "sample_generator": "sha256(seed, site_id, logical_tick, stream)",
        },
        "model_state": checkpoint.model_state,
        "optimizer_state": checkpoint.optimizer_state,
    }
    return _CapturedCheckpoint(
        payload=payload,
        checkpoint_bytes=int(checkpoint.checkpoint_bytes),
        state_sha256=state_hash,
        generation=generation,
        logical_tick=logical_tick,
    )


def _persist_checkpoint(
    torch: Any,
    captured: _CapturedCheckpoint,
    directory: Path,
) -> _DurableCheckpoint:
    directory.mkdir(parents=True, exist_ok=True)
    safe_generation = captured.generation.replace(":", "-")
    final_path = directory / f"{safe_generation}.pt"
    temporary = final_path.with_suffix(final_path.suffix + ".part")
    if final_path.exists() or temporary.exists():
        raise FileExistsError(f"refusing to overwrite durable generation {final_path}")
    with temporary.open("xb") as raw:
        writer = _HashingWriter(raw)
        torch.save(captured.payload, writer)
        writer.flush()
        os.fsync(raw.fileno())
        digest = writer.digest.hexdigest()
        byte_count = writer.bytes_written
    os.replace(temporary, final_path)
    directory_fd: int | None = None
    try:
        directory_fd = os.open(directory, os.O_RDONLY)
        os.fsync(directory_fd)
    except OSError:
        pass
    finally:
        if directory_fd is not None:
            os.close(directory_fd)
    if final_path.stat().st_size != byte_count:
        raise OSError("durable checkpoint size changed after atomic commit")
    return _DurableCheckpoint(
        path=str(final_path),
        file_bytes=byte_count,
        file_sha256=digest,
        state_sha256=captured.state_sha256,
        generation=captured.generation,
        logical_tick=captured.logical_tick,
        committed_at_ns=time.time_ns(),
    )


class _ArmFailure(RuntimeError):
    pass


@dataclass
class _JobArmState:
    logical_tick: int = 0
    merge_count: int = 0
    steps_since_merge: int = 0
    post_rejoin_remaining: int = 0
    checkpoint_epoch: int = 0
    attempted_tokens: int = 0
    useful_tokens: int = 0
    local_attempted_tokens: int = 0
    survivor_redistributed_tokens: int = 0
    quota_ids: list[str] = field(default_factory=list)
    losses: list[float] = field(default_factory=list)
    latest_durable: _DurableCheckpoint | None = None
    durable_generations: list[_DurableCheckpoint] = field(default_factory=list)
    latest_cut_event_id: str | None = None
    failure_started_ns: dict[str, int] = field(default_factory=dict)
    recovery_times_s: list[float] = field(default_factory=list)
    durable_cut_violations: list[str] = field(default_factory=list)
    rollback_bound_violations: list[str] = field(default_factory=list)


@dataclass
class _ArmExecution:
    arm_id: str
    block_id: str
    split: str
    policy_id: str
    started_at: str
    started_ns: int
    ended_ns: int
    job_summary: Mapping[str, Any] | None
    gpu_telemetry: Mapping[str, Any]
    external_telemetry: Mapping[str, Any] | None
    event_chunks: Sequence[Mapping[str, Any]]
    events: Sequence[Mapping[str, Any]]
    error: str | None


def _policy_seed(scenario: Mapping[str, Any], policy_id: str) -> int:
    for policy in scenario["policies"]:
        if policy["policy_id"] == policy_id:
            return int(policy.get("seed", 0))
    raise ValueError(f"unknown PW3 policy {policy_id!r}")


def _visible_state(external: ExternalTelemetrySession | None) -> VisibleRackState:
    if external is None:
        return VisibleRackState(
            reference_time_ns=time.time_ns(),
            rack_power_w=None,
            rack_ramp_w_per_s=None,
            storage_write_bytes_per_s=None,
            storage_queue_depth=None,
            clock_uncertainty_ns=2**63 - 1,
            quality="missing",
        )
    value = external.snapshot()["visible_rack_state"]
    return VisibleRackState(
        # Scheduler releases are absolute UTC so every host can obey them.
        reference_time_ns=time.time_ns(),
        rack_power_w=(
            float(value["rack_power_w"])
            if _finite(value.get("rack_power_w"))
            else None
        ),
        rack_ramp_w_per_s=(
            float(value["rack_ramp_w_per_s"])
            if _finite(value.get("rack_ramp_w_per_s"))
            else None
        ),
        storage_write_bytes_per_s=(
            float(value["storage_write_bytes_per_s"])
            if _finite(value.get("storage_write_bytes_per_s"))
            else None
        ),
        storage_queue_depth=(
            float(value["storage_queue_depth"])
            if _finite(value.get("storage_queue_depth"))
            else None
        ),
        clock_uncertainty_ns=int(value.get("clock_uncertainty_ns", 2**63 - 1)),
        quality=str(value.get("quality", "missing")),
    )


def _operation_slack_ns(scenario: Mapping[str, Any], kind: str) -> int:
    checkpointing = scenario["checkpointing"]
    if kind.startswith("checkpoint-"):
        return int(float(checkpointing["maximum_checkpoint_release_slack_ms"]) * 1e6)
    return int(float(checkpointing["maximum_rejoin_release_slack_ms"]) * 1e6)


def _event_deadline_ns(
    scenario: Mapping[str, Any],
    *,
    earliest_ns: int,
    predicted_duration_ns: int,
    kind: str,
) -> int:
    margin = int(float(scenario["checkpointing"]["checkpoint_deadline_margin_ms"]) * 1e6)
    return earliest_ns + _operation_slack_ns(scenario, kind) + predicted_duration_ns + margin


def _event_id(
    arm_id: str,
    job_id: int,
    kind: str,
    checkpoint_epoch: int,
) -> str:
    return f"{arm_id}:job-{job_id}:{kind}:epoch-{checkpoint_epoch}"


def _record_event(
    ledger: StateFlowLedger,
    event_writer: ChunkedJsonlWriter,
    events: list[dict[str, Any]],
    record: EventRecord,
) -> None:
    ledger.record(record)
    serialized = record.to_dict()
    serialized["record_type"] = "state_flow_event"
    event_writer.write(serialized)
    events.append(serialized)


def _record_fixed_event(
    runtime: _DistributedRuntime,
    ledger: StateFlowLedger,
    event_writer: ChunkedJsonlWriter,
    events: list[dict[str, Any]],
    *,
    event_id: str,
    kind: str,
    checkpoint_epoch: int,
    predecessor_ids: Sequence[str],
    generation: str,
    actual_start_ns: int,
    actual_end_ns: int,
    byte_count: int = 0,
) -> Mapping[str, Any] | None:
    if not runtime.is_job_leader:
        return None
    record = EventRecord(
        event_id=event_id,
        job_id=runtime.job_id,
        rank_ids=runtime.pair_ranks,
        kind=kind,
        checkpoint_epoch=checkpoint_epoch,
        predecessor_ids=tuple(predecessor_ids),
        state_generation=generation,
        earliest_start_ns=actual_start_ns,
        scheduled_release_ns=actual_start_ns,
        actual_start_ns=actual_start_ns,
        actual_end_ns=actual_end_ns,
        deadline_ns=max(actual_end_ns, actual_start_ns) + 1,
        bytes=max(0, int(byte_count)),
        outcome="completed",
        policy_id="fixed",
        decision_reason="fixed by frozen learning/recovery semantics",
    )
    _record_event(ledger, event_writer, events, record)
    return record.to_dict()


def _execute_scheduled_operation(
    runtime: _DistributedRuntime,
    scenario: Mapping[str, Any],
    policy_id: str,
    block_id: str,
    arm_id: str,
    operation_model: _OperationModel,
    ledger: StateFlowLedger,
    event_writer: ChunkedJsonlWriter,
    events: list[dict[str, Any]],
    gpu_session: GpuTelemetrySampler,
    external_session: ExternalTelemetrySession | None,
    *,
    kind: str,
    checkpoint_epoch: int,
    predecessor_ids: Sequence[str],
    state_generation: str,
    predicted_bytes: int,
    execute: Callable[[], Mapping[str, Any] | None],
) -> Mapping[str, Any]:
    if kind not in _MOVABLE_KINDS:
        raise ValueError(f"{kind!r} is not a movable PW3 operation")
    if runtime.is_job_leader:
        missing = [item for item in predecessor_ids if not ledger.completed(item)]
        if missing:
            raise _ArmFailure(f"{kind} has incomplete predecessor(s): {missing}")
    earliest_ns = time.time_ns()
    predicted_duration_ns = operation_model.predict_duration(kind)
    storage_rate = (
        float(predicted_bytes) / (predicted_duration_ns / 1e9)
        if kind == "checkpoint-persist" and predicted_bytes > 0
        else 0.0
    )
    request = None
    if runtime.is_job_leader:
        request = OperationRequest(
            event_id=_event_id(arm_id, runtime.job_id, kind, checkpoint_epoch),
            job_id=runtime.job_id,
            rank_ids=runtime.pair_ranks,
            kind=kind,
            checkpoint_epoch=checkpoint_epoch,
            predecessor_ids=tuple(predecessor_ids),
            state_generation=state_generation,
            earliest_start_ns=earliest_ns,
            deadline_ns=_event_deadline_ns(
                scenario,
                earliest_ns=earliest_ns,
                predicted_duration_ns=predicted_duration_ns,
                kind=kind,
            ),
            predicted_duration_ns=predicted_duration_ns,
            predicted_power_delta_w=operation_model.predict_power(kind),
            predicted_storage_bytes_per_s=storage_rate,
            bytes=max(0, int(predicted_bytes)),
        )
    gathered = _all_gather_object(
        runtime,
        request.to_dict() if request is not None else None,
    )
    decisions_payload: list[dict[str, Any]] | None = None
    if runtime.is_root:
        requests = [
            OperationRequest.from_dict(value)
            for rank, value in enumerate(gathered)
            if rank % 2 == 0 and value is not None
        ]
        visible = _visible_state(external_session)
        decisions = schedule_state_flow_batch(
            policy_id,
            requests,
            visible=visible,
            block_id=block_id,
            slot_ns=int(float(scenario["checkpointing"]["cohort_slot_ms"]) * 1e6),
            maximum_delay_ns=_operation_slack_ns(scenario, kind),
            random_seed=_policy_seed(scenario, policy_id),
            maximum_clock_uncertainty_ns=int(
                float(scenario["telemetry"]["maximum_event_clock_uncertainty_ms"]) * 1e6
            ),
        )
        decisions_payload = [decision.to_dict() for decision in decisions]
        if external_session is not None:
            external_session.mark_phase(
                kind,
                "scheduled",
                {
                    "block_id": block_id,
                    "arm_id": arm_id,
                    "policy_id": policy_id,
                    "decision_count": len(decisions_payload),
                },
            )
    decisions_payload = _broadcast_object(runtime, decisions_payload)
    if not isinstance(decisions_payload, list):
        raise _ArmFailure("rank zero did not broadcast scheduler decisions")
    decision_by_event = {
        str(value["event_id"]): value for value in decisions_payload
    }
    local_event_id = _event_id(arm_id, runtime.job_id, kind, checkpoint_epoch)
    decision = decision_by_event.get(local_event_id)
    if decision is None:
        raise _ArmFailure(f"scheduler omitted {local_event_id}")
    _sleep_until_utc(int(decision["scheduled_release_ns"]))
    gpu_session.mark_phase(
        kind,
        "start",
        {
            "event_id": local_event_id,
            "job_id": runtime.job_id,
            "policy_id": policy_id,
        },
    )
    started_ns = time.time_ns()
    local_error: str | None = None
    detail: Mapping[str, Any] = {}
    try:
        returned = execute()
        detail = dict(returned or {})
        runtime.torch.cuda.synchronize(runtime.device)
    except BaseException as error:
        local_error = f"{type(error).__name__}: {error}"
    ended_ns = time.time_ns()
    gpu_session.mark_phase(
        kind,
        "end",
        {"event_id": local_event_id, "outcome": "failed" if local_error else "completed"},
    )
    pair_status = _pair_gather_object(
        runtime,
        {
            "rank": runtime.rank,
            "started_ns": started_ns,
            "ended_ns": ended_ns,
            "error": local_error,
            "bytes": int(detail.get("bytes", 0)),
            "metadata": {
                key: value for key, value in detail.items() if key != "bytes"
            },
        },
    )
    aggregate_start = min(int(value["started_ns"]) for value in pair_status)
    aggregate_end = max(int(value["ended_ns"]) for value in pair_status)
    errors = [str(value["error"]) for value in pair_status if value.get("error")]
    actual_bytes = max(int(value.get("bytes", 0)) for value in pair_status)
    leader_error: str | None = None
    serialized: dict[str, Any] | None = None
    if runtime.is_job_leader:
        assert request is not None
        outcome = "failed" if errors else "completed"
        record = EventRecord(
            event_id=request.event_id,
            job_id=request.job_id,
            rank_ids=request.rank_ids,
            kind=request.kind,
            checkpoint_epoch=request.checkpoint_epoch,
            predecessor_ids=request.predecessor_ids,
            state_generation=request.state_generation,
            earliest_start_ns=request.earliest_start_ns,
            scheduled_release_ns=int(decision["scheduled_release_ns"]),
            actual_start_ns=aggregate_start,
            actual_end_ns=aggregate_end,
            deadline_ns=request.deadline_ns,
            bytes=actual_bytes if actual_bytes else request.bytes,
            outcome=outcome,
            policy_id=policy_id,
            decision_reason=str(decision["reason"]),
        )
        serialized = record.to_dict()
        serialized.update(
            {
                "record_type": "state_flow_event",
                "scheduler_decision": dict(decision),
                "rank_execution": pair_status,
            }
        )
        if errors:
            leader_error = f"{local_event_id} execution failed: {'; '.join(errors)}"
            event_writer.write(serialized)
            events.append(serialized)
        elif aggregate_end > request.deadline_ns:
            serialized["outcome"] = "deadline-missed"
            leader_error = f"{local_event_id} missed its frozen deadline"
            event_writer.write(serialized)
            events.append(serialized)
        else:
            _record_event(ledger, event_writer, events, record)
            # Preserve scheduler and rank timing in the compact/raw event copy.
            events[-1]["scheduler_decision"] = dict(decision)
            events[-1]["rank_execution"] = pair_status
    pair_message = [serialized, leader_error] if runtime.is_job_leader else [None, None]
    runtime.dist.broadcast_object_list(
        pair_message,
        src=runtime.pair_ranks[0],
        group=runtime.pair_control_group,
    )
    global_errors = _all_gather_object(runtime, pair_message[1] if runtime.is_job_leader else None)
    runtime.dist.barrier(group=runtime.control_group)
    failures = [str(value) for value in global_errors if value]
    if failures:
        raise _ArmFailure("; ".join(failures))
    assert pair_message[0] is not None
    return pair_message[0]


def _checkpoint_generation(arm_id: str, job_id: int, epoch: int, tick: int) -> str:
    return f"{arm_id}:job-{job_id}:checkpoint-{epoch}:tick-{tick}"


def _schedule_checkpoint(
    runtime: _DistributedRuntime,
    scenario: Mapping[str, Any],
    policy_id: str,
    block_id: str,
    arm_id: str,
    operation_model: _OperationModel,
    ledger: StateFlowLedger,
    event_writer: ChunkedJsonlWriter,
    events: list[dict[str, Any]],
    gpu_session: GpuTelemetrySampler,
    external_session: ExternalTelemetrySession | None,
    site: Any,
    state: _JobArmState,
    checkpoint_directory: Path,
) -> None:
    state.checkpoint_epoch += 1
    epoch = state.checkpoint_epoch
    generation = _checkpoint_generation(arm_id, runtime.job_id, epoch, state.logical_tick)
    captured: _CapturedCheckpoint | None = None
    durable: _DurableCheckpoint | None = None

    def capture() -> Mapping[str, Any]:
        nonlocal captured
        if not runtime.is_job_leader:
            return {"bytes": 0}
        captured = _capture_checkpoint(
            runtime,
            site,
            generation=generation,
            logical_tick=state.logical_tick,
            merge_count=state.merge_count,
            quota_ids=state.quota_ids,
        )
        return {
            "bytes": captured.checkpoint_bytes,
            "state_sha256": captured.state_sha256,
        }

    capture_event = _execute_scheduled_operation(
        runtime,
        scenario,
        policy_id,
        block_id,
        arm_id,
        operation_model,
        ledger,
        event_writer,
        events,
        gpu_session,
        external_session,
        kind="checkpoint-capture",
        checkpoint_epoch=epoch,
        predecessor_ids=(state.latest_cut_event_id,) if state.latest_cut_event_id else (),
        state_generation=generation,
        predicted_bytes=(
            int(state.latest_durable.file_bytes)
            if state.latest_durable is not None
            else int(lc1._tree_bytes(site.model.state_dict()) + lc1._tree_bytes(site.optimizer.state_dict()))
        ),
        execute=capture,
    )
    capture_id = str(capture_event["event_id"])

    def persist() -> Mapping[str, Any]:
        nonlocal durable
        if not runtime.is_job_leader:
            return {"bytes": 0}
        if captured is None:
            raise RuntimeError("checkpoint persist started without captured state")
        durable = _persist_checkpoint(runtime.torch, captured, checkpoint_directory)
        return {
            "bytes": durable.file_bytes,
            "file_sha256": durable.file_sha256,
            "path": durable.path,
        }

    persist_event = _execute_scheduled_operation(
        runtime,
        scenario,
        policy_id,
        block_id,
        arm_id,
        operation_model,
        ledger,
        event_writer,
        events,
        gpu_session,
        external_session,
        kind="checkpoint-persist",
        checkpoint_epoch=epoch,
        predecessor_ids=(capture_id,),
        state_generation=generation,
        predicted_bytes=(
            captured.checkpoint_bytes
            if captured is not None
            else int(capture_event.get("bytes", 0))
        ),
        execute=persist,
    )
    persist_id = str(persist_event["event_id"])
    cut_started = time.time_ns()
    cut_id = _event_id(arm_id, runtime.job_id, "durable-cut-commit", epoch)
    _record_fixed_event(
        runtime,
        ledger,
        event_writer,
        events,
        event_id=cut_id,
        kind="durable-cut-commit",
        checkpoint_epoch=epoch,
        predecessor_ids=(persist_id,),
        generation=generation,
        actual_start_ns=cut_started,
        actual_end_ns=time.time_ns(),
        byte_count=0,
    )
    durable_payload = None
    if runtime.is_job_leader:
        if durable is None:
            raise _ArmFailure("durable checkpoint disappeared before cut commit")
        durable_payload = asdict(durable)
    pair_container = [durable_payload]
    runtime.dist.broadcast_object_list(
        pair_container,
        src=runtime.pair_ranks[0],
        group=runtime.pair_control_group,
    )
    observed = _DurableCheckpoint(**pair_container[0])
    state.latest_durable = observed
    state.durable_generations.append(observed)
    state.latest_cut_event_id = cut_id


def _record_optimizer_merge(
    runtime: _DistributedRuntime,
    arm_id: str,
    ledger: StateFlowLedger,
    event_writer: ChunkedJsonlWriter,
    events: list[dict[str, Any]],
    state: _JobArmState,
    started_ns: int,
    ended_ns: int,
) -> None:
    merge_id = f"{arm_id}:job-{runtime.job_id}:optimizer-merge:{state.merge_count}"
    _record_fixed_event(
        runtime,
        ledger,
        event_writer,
        events,
        event_id=merge_id,
        kind="optimizer-merge",
        checkpoint_epoch=state.checkpoint_epoch,
        predecessor_ids=(),
        generation=f"{arm_id}:job-{runtime.job_id}:tick-{state.logical_tick}",
        actual_start_ns=started_ns,
        actual_end_ns=ended_ns,
    )


def _failure_windows(scenario: Mapping[str, Any]) -> dict[int, Mapping[str, Any]]:
    windows: dict[int, Mapping[str, Any]] = {}
    for value in scenario["continuation"]["failure_windows"]:
        for tick in range(int(value["start_tick"]), int(value["rejoin_tick"])):
            if tick in windows:
                raise ValueError("overlapping PW3 failure windows are not supported")
            windows[tick] = value
    return windows


def _begin_failure(
    runtime: _DistributedRuntime,
    scenario: Mapping[str, Any],
    arm_id: str,
    failure: Mapping[str, Any],
    ledger: StateFlowLedger,
    event_writer: ChunkedJsonlWriter,
    events: list[dict[str, Any]],
    state: _JobArmState,
) -> None:
    failure_id = str(failure["failure_id"])
    observed_ns = time.time_ns()
    event_id = f"{arm_id}:job-{runtime.job_id}:failure-observed:{failure_id}"
    generation = f"{arm_id}:job-{runtime.job_id}:failure-{failure_id}"
    _record_fixed_event(
        runtime,
        ledger,
        event_writer,
        events,
        event_id=event_id,
        kind="failure-observed",
        checkpoint_epoch=state.checkpoint_epoch,
        predecessor_ids=(),
        generation=generation,
        actual_start_ns=observed_ns,
        actual_end_ns=observed_ns,
    )
    state.failure_started_ns[failure_id] = observed_ns
    if state.latest_durable is None:
        state.rollback_bound_violations.append(
            f"{failure_id}: no globally recoverable generation at failure"
        )
    else:
        rollback_ticks = state.logical_tick - state.latest_durable.logical_tick
        rollback_bound = int(
            scenario["checkpointing"]["healthy_checkpoint_every_ticks"]
        )
        if rollback_ticks > rollback_bound:
            state.rollback_bound_violations.append(
                f"{failure_id}: rollback distance {rollback_ticks} exceeds {rollback_bound}"
            )


def _schedule_rejoin(
    runtime: _DistributedRuntime,
    scenario: Mapping[str, Any],
    policy_id: str,
    block_id: str,
    arm_id: str,
    operation_model: _OperationModel,
    ledger: StateFlowLedger,
    event_writer: ChunkedJsonlWriter,
    events: list[dict[str, Any]],
    gpu_session: GpuTelemetrySampler,
    external_session: ExternalTelemetrySession | None,
    site: Any,
    state: _JobArmState,
    failure: Mapping[str, Any],
) -> None:
    failure_id = str(failure["failure_id"])
    epoch = state.checkpoint_epoch + 1
    generation = f"{arm_id}:job-{runtime.job_id}:rejoin-{failure_id}"
    failure_event_id = f"{arm_id}:job-{runtime.job_id}:failure-observed:{failure_id}"

    transfer_event = _execute_scheduled_operation(
        runtime,
        scenario,
        policy_id,
        block_id,
        arm_id,
        operation_model,
        ledger,
        event_writer,
        events,
        gpu_session,
        external_session,
        kind="state-transfer",
        checkpoint_epoch=epoch,
        predecessor_ids=(failure_event_id,),
        state_generation=generation,
        predicted_bytes=int(
            lc1._tree_bytes(site.model.state_dict())
            + lc1._tree_bytes(site.optimizer.state_dict())
        ),
        execute=lambda: {"bytes": _broadcast_site_state(runtime, site)},
    )
    transfer_id = str(transfer_event["event_id"])
    pair_hashes = _pair_gather_object(runtime, _site_state_hash(runtime, site))
    if len(set(pair_hashes)) != 1:
        raise _ArmFailure(f"state transfer failed exact hash commitment for {failure_id}")

    rebuild_event = _execute_scheduled_operation(
        runtime,
        scenario,
        policy_id,
        block_id,
        arm_id,
        operation_model,
        ledger,
        event_writer,
        events,
        gpu_session,
        external_session,
        kind="communicator-rebuild",
        checkpoint_epoch=epoch,
        predecessor_ids=(transfer_id,),
        state_generation=generation,
        predicted_bytes=0,
        execute=lambda: (_rebuild_pair_communicator(runtime) or {"bytes": 0}),
    )
    rebuild_id = str(rebuild_event["event_id"])

    def commit() -> Mapping[str, Any]:
        runtime.dist.barrier(group=runtime.pair_train_group)
        return {"bytes": 0, "state_sha256": pair_hashes[0]}

    commit_event = _execute_scheduled_operation(
        runtime,
        scenario,
        policy_id,
        block_id,
        arm_id,
        operation_model,
        ledger,
        event_writer,
        events,
        gpu_session,
        external_session,
        kind="rejoin-commit",
        checkpoint_epoch=epoch,
        predecessor_ids=(rebuild_id,),
        state_generation=generation,
        predicted_bytes=0,
        execute=commit,
    )
    state.checkpoint_epoch = epoch
    state.steps_since_merge = 0
    state.post_rejoin_remaining = int(
        scenario["optimization"]["post_rejoin_sync_ticks"]
    )
    started = state.failure_started_ns.get(failure_id)
    if started is None:
        raise _ArmFailure(f"rejoin {failure_id} has no failure observation")
    state.recovery_times_s.append(
        (int(commit_event["actual_end_ns"]) - started) / 1e9
    )


def _sample_midpoint_ns(sample: Mapping[str, Any]) -> int:
    start = int(sample["utc_interval_start_ns"])
    end = int(sample["utc_interval_end_ns"])
    return start + (end - start) // 2


def _channel_samples(
    result: TelemetrySessionResult,
    channel_id: str,
) -> list[dict[str, Any]]:
    selected = [
        dict(sample)
        for sample in result.samples
        if str(sample.get("channel_id")) == channel_id
        and sample.get("quality", {}).get("status") == "observed"
        and _finite(sample.get("value"))
    ]
    selected.sort(key=lambda value: (_sample_midpoint_ns(value), int(value.get("sequence", 0))))
    unique: list[dict[str, Any]] = []
    seen: set[tuple[int, int, float]] = set()
    for sample in selected:
        key = (
            int(sample["utc_interval_start_ns"]),
            int(sample["utc_interval_end_ns"]),
            float(sample["value"]),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(sample)
    return unique


def _channel_samples_in_window(
    result: TelemetrySessionResult,
    channel_id: str,
    *,
    started_ns: int,
    ended_ns: int,
) -> list[dict[str, Any]]:
    return [
        sample
        for sample in _channel_samples(result, channel_id)
        if started_ns <= _sample_midpoint_ns(sample) <= ended_ns
    ]


def _manifest_by_channel(result: TelemetrySessionResult) -> dict[str, dict[str, Any]]:
    return {
        str(value["channel_id"]): dict(value)
        for value in result.channel_manifests
    }


def _effective_period_ms(samples: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    gaps = [
        (_sample_midpoint_ns(right) - _sample_midpoint_ns(left)) / 1e6
        for left, right in zip(samples, samples[1:])
        if _sample_midpoint_ns(right) > _sample_midpoint_ns(left)
    ]
    return {
        "sample_count": len(samples),
        "median_ms": _median(gaps),
        "p95_ms": _percentile(gaps, 0.95),
        "maximum_ms": max(gaps) if gaps else None,
    }


def _effective_counter_period_ms(
    samples: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    updates: list[Mapping[str, Any]] = []
    previous: float | None = None
    for sample in samples:
        value = float(sample["value"])
        if previous is None or value != previous:
            updates.append(sample)
        previous = value
    result = _effective_period_ms(updates)
    result["poll_sample_count"] = len(samples)
    result["effective_update_count"] = len(updates)
    return result


def _gpu_telemetry_compact(
    result: TelemetrySessionResult,
    *,
    started_ns: int,
    ended_ns: int,
) -> dict[str, Any]:
    manifests = _manifest_by_channel(result)
    channel_metrics: dict[str, Any] = {}
    nonmonotone = False
    energy_j = 0.0
    has_energy = False
    gpu_uuid = None
    for channel_id, manifest in manifests.items():
        samples = _channel_samples_in_window(
            result,
            channel_id,
            started_ns=started_ns,
            ended_ns=ended_ns,
        )
        metric = str(manifest["metric"])
        periods = (
            _effective_counter_period_ms(samples)
            if manifest["sample_kind"] == "cumulative_counter"
            else _effective_period_ms(samples)
        )
        entry: dict[str, Any] = {
            "channel_id": channel_id,
            "metric": metric,
            "unit": manifest["unit"],
            "sample_kind": manifest["sample_kind"],
            "period": periods,
        }
        metadata = manifest.get("metadata", {})
        gpu_uuid = gpu_uuid or metadata.get("gpu_uuid")
        if samples:
            entry["first_value"] = float(samples[0]["value"])
            entry["last_value"] = float(samples[-1]["value"])
            entry["minimum"] = min(float(sample["value"]) for sample in samples)
            entry["maximum"] = max(float(sample["value"]) for sample in samples)
        if metric == "gpu_board_energy_total" and len(samples) >= 2:
            values = [float(sample["value"]) for sample in samples]
            if any(right < left for left, right in zip(values, values[1:])):
                nonmonotone = True
            else:
                channel_energy = values[-1] - values[0]
                entry["observed_delta_j"] = channel_energy
                energy_j += channel_energy
                has_energy = True
        channel_metrics[channel_id] = entry
    maximum_uncertainty = max(
        (
            int(record.get("uncertainty_ns", 0))
            for record in result.clock_offsets
        ),
        default=0,
    )
    maximum_uncertainty = max(
        maximum_uncertainty,
        max(
            (
                int(sample.get("quality", {}).get("uncertainty_ns", 0))
                for sample in result.samples
            ),
            default=0,
        ),
    )
    return {
        "session_id": result.session_id,
        "rank": int(result.session_id.rsplit("-", 1)[-1]),
        "gpu_uuid": gpu_uuid,
        "channel_manifests": [dict(value) for value in result.channel_manifests],
        "chunks": [dict(value) for value in result.chunks],
        "channel_metrics": channel_metrics,
        "gpu_board_energy_j": energy_j if has_energy else None,
        "nonmonotone_energy_counter": nonmonotone,
        "missing_required_channel_ids": list(result.missing_required_channel_ids),
        "maximum_clock_uncertainty_ns": maximum_uncertainty,
        "terminal_error": result.terminal_error,
    }


def _external_telemetry_compact(result: TelemetrySessionResult) -> dict[str, Any]:
    maximum_uncertainty = max(
        (
            int(record.get("uncertainty_ns", 0))
            for record in result.clock_offsets
        ),
        default=0,
    )
    maximum_uncertainty = max(
        maximum_uncertainty,
        max(
            (
                int(sample.get("quality", {}).get("uncertainty_ns", 0))
                for sample in result.samples
            ),
            default=0,
        ),
    )
    return {
        "session_id": result.session_id,
        "channel_manifests": [dict(value) for value in result.channel_manifests],
        "chunks": [dict(value) for value in result.chunks],
        "missing_required_channel_ids": list(result.missing_required_channel_ids),
        "maximum_clock_uncertainty_ns": maximum_uncertainty,
        "terminal_error": result.terminal_error,
        "visible_rack_state_at_stop": dict(result.visible_rack_state),
    }


def _chunk_records(
    chunks: Sequence[Mapping[str, Any]],
    *,
    raw_root: Path,
    arm_id: str,
    stream_kind: str,
    rank: int | None = None,
    job_id: int | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for chunk in chunks:
        value = dict(chunk)
        value["path"] = _safe_relative(str(value["path"]), raw_root)
        value.update(
            {
                "arm_id": arm_id,
                "stream_kind": stream_kind,
                "rank": rank,
                "job_id": job_id,
            }
        )
        records.append(value)
    return records


def _evaluate_site(
    runtime: _DistributedRuntime,
    scenario: Mapping[str, Any],
    corpora: Any,
    site: Any,
    torch: Any,
    functional: Any,
) -> tuple[float, float, tuple[float, ...]] | None:
    if not runtime.is_job_leader:
        return None
    return lc1._evaluate(
        torch,
        functional,
        site.model,
        corpora.validation,
        seed=int(scenario["optimization"]["validation_seed"]),
        batch_size=int(scenario["optimization"]["batch_size_per_rank"]),
        context_length=int(scenario["model"]["context_length"]),
        validation_batches=int(scenario["optimization"]["validation_batches"]),
        device=runtime.device,
        autocast_dtype=torch.bfloat16,
    )


def _job_summary(
    runtime: _DistributedRuntime,
    scenario: Mapping[str, Any],
    arm_id: str,
    site: Any,
    state: _JobArmState,
    final_evaluation: tuple[float, float, tuple[float, ...]] | None,
    local_losses: Sequence[float],
    error: str | None,
) -> Mapping[str, Any] | None:
    local_hash = _site_state_hash(runtime, site)
    rank_records = _pair_gather_object(
        runtime,
        {
            "rank": runtime.rank,
            "state_sha256": local_hash,
            "attempted_tokens": state.local_attempted_tokens,
            "training_loss_count": len(local_losses),
            "mean_training_loss": _median(local_losses),
        },
    )
    if not runtime.is_job_leader:
        return None
    expected_ticks = int(scenario["canonical_work"]["logical_ticks"])
    expected_tokens = int(scenario["canonical_work"]["useful_tokens_per_job"])
    expected_quota_count = expected_ticks * int(
        scenario["canonical_work"]["site_quota_count_per_tick"]
    )
    expected_quota_ids = [
        f"site-{letter}:tick-{tick}"
        for tick in range(expected_ticks)
        for letter in ("a", "b")
    ]
    state_hashes = [str(value["state_sha256"]) for value in rank_records]
    quota_hash = hashlib.sha256("\n".join(state.quota_ids).encode("utf-8")).hexdigest()
    expected_quota_hash = hashlib.sha256(
        "\n".join(expected_quota_ids).encode("utf-8")
    ).hexdigest()
    semantic_violations: list[str] = []
    if state.logical_tick != expected_ticks:
        semantic_violations.append(
            f"logical ticks {state.logical_tick} != {expected_ticks}"
        )
    if state.useful_tokens != expected_tokens:
        semantic_violations.append(
            f"useful tokens {state.useful_tokens} != {expected_tokens}"
        )
    if len(state.quota_ids) != expected_quota_count or quota_hash != expected_quota_hash:
        semantic_violations.append("deterministic quota commitment mismatch")
    if len(set(state_hashes)) != 1:
        semantic_violations.append("rank states differ at arm completion")
    if any(not math.isfinite(value) for value in state.losses):
        semantic_violations.append("non-finite training loss")
    semantic_violations.extend(state.durable_cut_violations)
    semantic_violations.extend(state.rollback_bound_violations)
    if error:
        semantic_violations.append(f"arm execution failed: {error}")
    return {
        "job_id": runtime.job_id,
        "rank_ids": list(runtime.pair_ranks),
        "arm_id": arm_id,
        "logical_ticks": state.logical_tick,
        "useful_tokens": state.useful_tokens,
        "attempted_tokens": state.attempted_tokens,
        "attempted_tokens_by_rank": {
            str(value["rank"]): int(value["attempted_tokens"])
            for value in rank_records
        },
        "survivor_redistributed_tokens": state.survivor_redistributed_tokens,
        "quota_count": len(state.quota_ids),
        "quota_commitment_sha256": quota_hash,
        "expected_quota_commitment_sha256": expected_quota_hash,
        "final_state_sha256": state_hashes[0] if len(set(state_hashes)) == 1 else None,
        "rank_state_sha256": {
            str(value["rank"]): value["state_sha256"] for value in rank_records
        },
        "durable_generations": [asdict(value) for value in state.durable_generations],
        "latest_globally_recoverable_generation": (
            asdict(state.latest_durable) if state.latest_durable is not None else None
        ),
        "recovery_times_s": list(state.recovery_times_s),
        "final_held_out_nll": (
            float(final_evaluation[0]) if final_evaluation is not None else None
        ),
        "held_out_nll_standard_deviation": (
            float(final_evaluation[1]) if final_evaluation is not None else None
        ),
        "validation_batch_nll": (
            list(final_evaluation[2]) if final_evaluation is not None else []
        ),
        "training": rank_records,
        "semantic_violations": semantic_violations,
        "semantic_invariant_violations": len(semantic_violations),
        "durable_cut_violations": len(state.durable_cut_violations),
        "rollback_bound_violations": len(state.rollback_bound_violations),
    }


def _run_physical_arm(
    runtime: _DistributedRuntime,
    scenario: Mapping[str, Any],
    corpora: Any,
    site: Any,
    warm: _WarmState,
    block_id: str,
    split: str,
    policy_id: str,
    operation_model: _OperationModel,
    telemetry_config: TelemetryConfig,
    raw_root: Path,
    torch: Any,
    functional: Any,
) -> tuple[dict[str, Any] | None, TelemetrySessionResult | None]:
    arm_id = f"e002-pw3:{block_id}:{policy_id}"
    safe_arm = arm_id.replace(":", "-")
    rank_directory = raw_root / safe_arm / f"rank-{runtime.rank}"
    rank_directory.mkdir(parents=True, exist_ok=True)
    gpu_session = GpuTelemetrySampler(
        runtime.local_rank,
        rank_directory,
        arm_id,
        runtime.rank,
        max(
            1_000_000,
            int(
                scenario["telemetry"]["gpu"]["maximum_effective_period_ms"]
                * 1e6
                * 0.5
            ),
        ),
        expected_uuid=runtime.discovered_gpu_uuid,
    )
    gpu_session.start()
    identities = gpu_session.identities
    if len(identities) != 1:
        raise RuntimeError(f"rank {runtime.rank} did not bind exactly one physical GPU")
    runtime.discovered_gpu_uuid = identities[0].gpu_uuid

    external_session = None
    if runtime.is_root:
        external_directory = raw_root / safe_arm / "external"
        external_session = ExternalTelemetrySession(
            telemetry_config,
            external_directory,
            arm_id,
        )
        external_session.start()
    event_writer = ChunkedJsonlWriter(
        rank_directory,
        stream_id=f"{safe_arm}.job-{runtime.job_id}.events.rank-{runtime.rank}",
        max_records_per_chunk=10_000,
        max_content_bytes_per_chunk=16 * 1024 * 1024,
    )
    lc1._restore(site, warm.checkpoint)
    pair_warm_hashes = _pair_gather_object(runtime, _site_state_hash(runtime, site))
    if len(set(pair_warm_hashes)) != 1 or pair_warm_hashes[0] != warm.state_sha256:
        raise RuntimeError(f"arm {arm_id} did not restore the frozen block warm state")
    runtime.dist.barrier(group=runtime.control_group)
    started_ns = time.time_ns()
    started_at = _utc_now()
    gpu_session.mark_phase("arm", "start", {"block_id": block_id, "policy_id": policy_id})
    if external_session is not None:
        external_session.mark_phase(
            "arm", "start", {"block_id": block_id, "policy_id": policy_id}
        )
    state = _JobArmState()
    ledger = StateFlowLedger()
    events: list[dict[str, Any]] = []
    local_losses: list[float] = []
    arm_error: str | None = None
    checkpoint_directory = raw_root / safe_arm / "durable" / f"job-{runtime.job_id}"
    failure_by_tick = _failure_windows(scenario)
    failure_by_start = {
        int(value["start_tick"]): value
        for value in scenario["continuation"]["failure_windows"]
    }
    failure_by_rejoin = {
        int(value["rejoin_tick"]): value
        for value in scenario["continuation"]["failure_windows"]
    }
    tokens_per_quota = int(scenario["canonical_work"]["tokens_per_rank_quota"])
    healthy_merge = int(scenario["optimization"]["healthy_merge_ticks"])
    reduced_merge = int(scenario["optimization"]["reduced_membership_merge_ticks"])
    healthy_checkpoint = int(
        scenario["checkpointing"]["healthy_checkpoint_every_ticks"]
    )
    reduced_checkpoint = int(
        scenario["checkpointing"]["reduced_membership_checkpoint_every_ticks"]
    )

    try:
        if bool(scenario["checkpointing"]["initial_durable_checkpoint"]):
            _schedule_checkpoint(
                runtime,
                scenario,
                policy_id,
                block_id,
                arm_id,
                operation_model,
                ledger,
                event_writer,
                events,
                gpu_session,
                external_session,
                site,
                state,
                checkpoint_directory,
            )
        for wall_tick in range(int(scenario["canonical_work"]["logical_ticks"])):
            if wall_tick in failure_by_rejoin:
                _schedule_rejoin(
                    runtime,
                    scenario,
                    policy_id,
                    block_id,
                    arm_id,
                    operation_model,
                    ledger,
                    event_writer,
                    events,
                    gpu_session,
                    external_session,
                    site,
                    state,
                    failure_by_rejoin[wall_tick],
                )
            if wall_tick in failure_by_start:
                _begin_failure(
                    runtime,
                    scenario,
                    arm_id,
                    failure_by_start[wall_tick],
                    ledger,
                    event_writer,
                    events,
                    state,
                )
            active_failure = failure_by_tick.get(wall_tick)
            gpu_session.mark_phase(
                "survivor-compute" if active_failure else "healthy-compute",
                "start",
                {"logical_tick": state.logical_tick, "job_id": runtime.job_id},
            )
            if active_failure is not None:
                if runtime.is_job_leader:
                    for site_id in ("site-a", "site-b"):
                        loss = _quota(
                            torch,
                            functional,
                            scenario,
                            corpora,
                            site,
                            seed=warm.seed,
                            site_id=site_id,
                            logical_tick=state.logical_tick,
                            stream="pw3-training",
                            device=runtime.device,
                        )
                        local_losses.append(loss)
                        state.losses.append(loss)
                    state.local_attempted_tokens += 2 * tokens_per_quota
                state.survivor_redistributed_tokens += tokens_per_quota
            else:
                site_id = "site-a" if runtime.within_job_rank == 0 else "site-b"
                loss = _quota(
                    torch,
                    functional,
                    scenario,
                    corpora,
                    site,
                    seed=warm.seed,
                    site_id=site_id,
                    logical_tick=state.logical_tick,
                    stream="pw3-training",
                    device=runtime.device,
                )
                local_losses.append(loss)
                state.losses.append(loss)
                state.local_attempted_tokens += tokens_per_quota
            torch.cuda.synchronize(runtime.device)
            runtime.dist.barrier(group=runtime.pair_control_group)
            gpu_session.mark_phase(
                "survivor-compute" if active_failure else "healthy-compute",
                "end",
                {"logical_tick": state.logical_tick, "job_id": runtime.job_id},
            )
            state.quota_ids.extend(
                (
                    f"site-a:tick-{state.logical_tick}",
                    f"site-b:tick-{state.logical_tick}",
                )
            )
            state.attempted_tokens += 2 * tokens_per_quota
            state.useful_tokens += 2 * tokens_per_quota
            state.logical_tick += 1
            state.steps_since_merge += 1

            if active_failure is not None:
                if state.steps_since_merge >= reduced_merge:
                    merge_start = time.time_ns()
                    # Both quotas already updated one survivor state; this fixed
                    # boundary records the same local-merge commitment as LC1.
                    state.merge_count += 1
                    state.steps_since_merge = 0
                    _record_optimizer_merge(
                        runtime,
                        arm_id,
                        ledger,
                        event_writer,
                        events,
                        state,
                        merge_start,
                        time.time_ns(),
                    )
            else:
                cadence = 1 if state.post_rejoin_remaining > 0 else healthy_merge
                if state.steps_since_merge >= cadence:
                    merge_start = time.time_ns()
                    _distributed_average_site(runtime, site)
                    torch.cuda.synchronize(runtime.device)
                    state.merge_count += 1
                    state.steps_since_merge = 0
                    if state.post_rejoin_remaining > 0:
                        state.post_rejoin_remaining -= 1
                    _record_optimizer_merge(
                        runtime,
                        arm_id,
                        ledger,
                        event_writer,
                        events,
                        state,
                        merge_start,
                        time.time_ns(),
                    )

            checkpoint_cadence = reduced_checkpoint if active_failure else healthy_checkpoint
            if state.logical_tick % checkpoint_cadence == 0:
                _schedule_checkpoint(
                    runtime,
                    scenario,
                    policy_id,
                    block_id,
                    arm_id,
                    operation_model,
                    ledger,
                    event_writer,
                    events,
                    gpu_session,
                    external_session,
                    site,
                    state,
                    checkpoint_directory,
                )
            if local_losses and not math.isfinite(local_losses[-1]):
                raise _ArmFailure(f"non-finite loss at logical tick {state.logical_tick}")
        runtime.dist.barrier(group=runtime.control_group)
    except _ArmFailure:
        # A state-flow failure is not a recoverable measurement condition.
        # Let torchrun terminate every rank instead of allowing one rank to
        # leave a collective and strand the rest of the physical experiment.
        raise

    ended_ns = time.time_ns()
    gpu_session.mark_phase("arm", "end", {"error": arm_error})
    if external_session is not None:
        external_session.mark_phase("arm", "end", {"error": arm_error})
    gpu_result = gpu_session.stop()
    external_result = external_session.stop() if external_session is not None else None
    event_chunks = [value.to_dict() for value in event_writer.close()]

    # Held-out evaluation is an outcome, not part of the rack-control
    # intervention window or useful-token throughput denominator.
    final_evaluation: tuple[float, float, tuple[float, ...]] | None = None
    if arm_error is None:
        evaluation_error: str | None = None
        try:
            final_evaluation = _evaluate_site(
                runtime, scenario, corpora, site, torch, functional
            )
        except BaseException as error:
            evaluation_error = f"{type(error).__name__}: {error}"
        evaluation_errors = _all_gather_object(runtime, evaluation_error)
        failures = sorted({str(value) for value in evaluation_errors if value})
        if failures:
            arm_error = "; ".join(failures)

    job = _job_summary(
        runtime,
        scenario,
        arm_id,
        site,
        state,
        final_evaluation,
        local_losses,
        arm_error,
    )
    local_compact = _gpu_telemetry_compact(
        gpu_result,
        started_ns=started_ns,
        ended_ns=ended_ns,
    )
    local_payload = {
        "rank": runtime.rank,
        "job_id": runtime.job_id,
        "gpu": local_compact,
        "job": job,
        "event_chunks": event_chunks if runtime.is_job_leader else [],
        "events": events if runtime.is_job_leader else [],
        "error": arm_error,
    }
    gathered = _all_gather_object(runtime, local_payload)
    if not runtime.is_root:
        return None, None
    assert external_result is not None
    by_job = [
        dict(value["job"])
        for value in gathered
        if int(value["rank"]) % 2 == 0 and value.get("job") is not None
    ]
    all_events = [
        dict(event)
        for value in gathered
        if int(value["rank"]) % 2 == 0
        for event in value.get("events", [])
    ]
    gpu_compact = [dict(value["gpu"]) for value in gathered]
    raw_references: list[dict[str, Any]] = []
    for value in gathered:
        raw_references.extend(
            _chunk_records(
                value["gpu"]["chunks"],
                raw_root=raw_root,
                arm_id=arm_id,
                stream_kind="gpu-telemetry",
                rank=int(value["rank"]),
                job_id=int(value["job_id"]),
            )
        )
        raw_references.extend(
            _chunk_records(
                value.get("event_chunks", []),
                raw_root=raw_root,
                arm_id=arm_id,
                stream_kind="state-flow-events",
                rank=int(value["rank"]),
                job_id=int(value["job_id"]),
            )
        )
    raw_references.extend(
        _chunk_records(
            external_result.chunks,
            raw_root=raw_root,
            arm_id=arm_id,
            stream_kind="external-telemetry",
        )
    )
    root_errors = sorted(
        {str(value["error"]) for value in gathered if value.get("error")}
    )
    execution = {
        "arm_id": arm_id,
        "block_id": block_id,
        "split": split,
        "policy_id": policy_id,
        "started_at": started_at,
        "started_ns": started_ns,
        "ended_ns": ended_ns,
        "wall_seconds": max(0.0, (ended_ns - started_ns) / 1e9),
        "by_job": by_job,
        "gpu_telemetry": gpu_compact,
        "external_telemetry": _external_telemetry_compact(external_result),
        "events": all_events,
        "raw_trace_refs": raw_references,
        "error": "; ".join(root_errors) if root_errors else None,
    }
    return execution, external_result


def _find_channel(
    manifests: Sequence[Mapping[str, Any]],
    *,
    boundary: str,
    metric_names: Sequence[str],
    unit: str | None = None,
) -> str | None:
    names = {name.lower() for name in metric_names}
    matches = []
    for manifest in manifests:
        metric = str(manifest.get("metric", "")).lower()
        if (
            str(manifest.get("boundary")) == boundary
            and metric in names
            and (unit is None or str(manifest.get("unit")) == unit)
        ):
            matches.append(str(manifest["channel_id"]))
    if len(matches) > 1:
        raise ValueError(
            f"multiple telemetry channels match {boundary}/{sorted(names)}: {matches}"
        )
    return matches[0] if matches else None


def _rack_power_channel(
    result: TelemetrySessionResult,
    config: TelemetryConfig,
) -> str | None:
    configured = config.rack_state_channels.get("rack_power_w")
    if configured is not None:
        matches = [
            manifest
            for manifest in result.channel_manifests
            if str(manifest.get("channel_id")) == str(configured)
        ]
        if len(matches) != 1:
            return None
        manifest = matches[0]
        if (
            str(manifest.get("boundary")) != RACK_AC_INPUT_BOUNDARY
            or str(manifest.get("unit")) != "W"
            or str(manifest.get("sample_kind")) != "interval_average"
        ):
            raise ValueError("observed PW3 rack-PDU manifest violated its frozen binding")
        return str(configured)
    return _find_channel(
        result.channel_manifests,
        boundary=RACK_AC_INPUT_BOUNDARY,
        metric_names=("active_power", "rack_power", "rack_pdu_power", "power", "power_w"),
        unit="W",
    )


def _rack_ramp(samples: Sequence[Mapping[str, Any]]) -> float | None:
    ramps: list[float] = []
    for left, right in zip(samples, samples[1:]):
        interval_s = (_sample_midpoint_ns(right) - _sample_midpoint_ns(left)) / 1e9
        if interval_s <= 0:
            continue
        ramps.append(abs(float(right["value"]) - float(left["value"])) / interval_s)
    return _percentile(ramps, 0.999)


def _native_spectral_energy(
    np: Any,
    samples: Sequence[Mapping[str, Any]],
    *,
    manifest: Mapping[str, Any] | None = None,
    low_hz: float = 0.1,
    high_hz: float = 10.0,
) -> dict[str, Any]:
    if len(samples) < 8:
        return {
            "value_w2": None,
            "frequency_low_hz": low_hz,
            "frequency_high_hz": high_hz,
            "frequency_bin_count": 0,
            "method": "native-window nonuniform weighted periodogram",
        }
    mid_ns = np.asarray([_sample_midpoint_ns(sample) for sample in samples], dtype=np.float64)
    times = (mid_ns - mid_ns[0]) / 1e9
    values = np.asarray([float(sample["value"]) for sample in samples], dtype=np.float64)
    integration_window_ns = int((manifest or {}).get("integration_window_ns", 0))
    if integration_window_ns > 0:
        widths = np.full(len(samples), integration_window_ns / 1e9, dtype=np.float64)
    else:
        widths = np.asarray(
            [
                max(
                    1e-9,
                    (
                        int(sample["reference_interval_end_ns"])
                        - int(sample["reference_interval_start_ns"])
                    )
                    / 1e9,
                )
                for sample in samples
            ],
            dtype=np.float64,
        )
    duration = float(times[-1] - times[0])
    positive_gaps = np.diff(times)
    positive_gaps = positive_gaps[positive_gaps > 0]
    if duration <= 0 or positive_gaps.size == 0:
        return {
            "value_w2": None,
            "frequency_low_hz": low_hz,
            "frequency_high_hz": high_hz,
            "frequency_bin_count": 0,
            "method": "native-window nonuniform weighted periodogram",
        }
    nyquist = 0.5 / float(np.median(positive_gaps))
    upper = min(high_hz, nyquist)
    resolution = 1.0 / duration
    if upper < low_hz or duration < 1.0 / low_hz:
        return {
            "value_w2": None,
            "frequency_low_hz": low_hz,
            "frequency_high_hz": upper,
            "frequency_bin_count": 0,
            "method": "native-window nonuniform weighted periodogram",
        }
    design = np.column_stack((np.ones_like(times), times))
    weighted_design = design * np.sqrt(widths)[:, None]
    weighted_values = values * np.sqrt(widths)
    coefficients, *_ = np.linalg.lstsq(weighted_design, weighted_values, rcond=None)
    detrended = values - design @ coefficients
    window = np.hanning(len(values))
    frequencies = np.arange(low_hz, upper + resolution * 0.5, resolution)
    normalization = float(np.sum((window**2) * widths))
    if normalization <= 0 or frequencies.size < 2:
        return {
            "value_w2": None,
            "frequency_low_hz": low_hz,
            "frequency_high_hz": upper,
            "frequency_bin_count": int(frequencies.size),
            "method": "native-window nonuniform weighted periodogram",
        }
    phase = np.exp(-2j * np.pi * frequencies[:, None] * times[None, :])
    amplitudes = phase @ (detrended * window * widths)
    psd = 2.0 * (np.abs(amplitudes) ** 2) / normalization
    trapezoid = getattr(np, "trapezoid", np.trapz)
    integrated = float(trapezoid(psd, frequencies))
    return {
        "value_w2": integrated,
        "frequency_low_hz": low_hz,
        "frequency_high_hz": upper,
        "frequency_bin_count": int(frequencies.size),
        "method": "native-window nonuniform weighted periodogram",
        "detrending": "weighted linear",
        "window": "Hann",
        "native_sample_count": len(samples),
        "duration_seconds": duration,
    }


def _integrate_power(
    samples: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
) -> float | None:
    if not samples:
        return None
    sample_kind = str(manifest.get("sample_kind", "gauge"))
    if sample_kind in {"interval_average", "interval_total"}:
        energy = 0.0
        integration_window_s = int(manifest.get("integration_window_ns", 0)) / 1e9
        for sample in samples:
            duration_s = integration_window_s
            if duration_s <= 0:
                continue
            value = float(sample["value"])
            energy += value if sample_kind == "interval_total" else value * duration_s
        return energy
    if len(samples) < 2:
        return None
    energy = 0.0
    for left, right in zip(samples, samples[1:]):
        duration_s = (_sample_midpoint_ns(right) - _sample_midpoint_ns(left)) / 1e9
        if duration_s > 0:
            energy += duration_s * (float(left["value"]) + float(right["value"])) * 0.5
    return energy


def _counter_delta(samples: Sequence[Mapping[str, Any]]) -> float | None:
    if len(samples) < 2:
        return None
    values = [float(sample["value"]) for sample in samples]
    if any(right < left for left, right in zip(values, values[1:])):
        return None
    return values[-1] - values[0]


def _state_flow_coincidence(
    events: Sequence[Mapping[str, Any]],
    job_count: int,
) -> dict[str, Any]:
    intervals = [
        event
        for event in events
        if str(event.get("kind")) in _STATE_FLOW_KINDS
        and int(event.get("actual_end_ns", 0)) >= int(event.get("actual_start_ns", 0))
    ]
    boundaries = sorted(
        {
            int(event[key])
            for event in intervals
            for key in ("actual_start_ns", "actual_end_ns")
        }
    )
    maximum_active = 0
    maximum_fraction = 0.0
    overlap_weighted_bytes = 0.0
    overlap_seconds = 0.0
    for left, right in zip(boundaries, boundaries[1:]):
        if right <= left:
            continue
        midpoint = left + (right - left) // 2
        active = [
            event
            for event in intervals
            if int(event["actual_start_ns"]) <= midpoint < int(event["actual_end_ns"])
        ]
        count = len({int(event["job_id"]) for event in active})
        maximum_active = max(maximum_active, count)
        maximum_fraction = max(maximum_fraction, count / max(1, job_count))
        if count > 1:
            duration_s = (right - left) / 1e9
            overlap_seconds += duration_s
            byte_rate = 0.0
            for event in active:
                duration_ns = max(
                    1,
                    int(event["actual_end_ns"]) - int(event["actual_start_ns"]),
                )
                byte_rate += int(event.get("bytes", 0)) / (duration_ns / 1e9)
            overlap_weighted_bytes += byte_rate * duration_s * (count - 1)
    return {
        "maximum_simultaneous_job_count": maximum_active,
        "maximum_simultaneous_active_fraction": maximum_fraction,
        "overlap_weighted_bytes": overlap_weighted_bytes,
        "multi_job_overlap_seconds": overlap_seconds,
        "event_count": len(intervals),
    }


def _bounded_display_events(
    events: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ordered = sorted(
        (
            {
                "event_id": str(event["event_id"]),
                "job_id": int(event["job_id"]),
                "rank_ids": list(event.get("rank_ids", [])),
                "kind": str(event["kind"]),
                "earliest_start_ns": int(event["earliest_start_ns"]),
                "start_ns": int(event["actual_start_ns"]),
                "end_ns": int(event["actual_end_ns"]),
                "scheduled_release_ns": int(event["scheduled_release_ns"]),
                "bytes": int(event.get("bytes", 0)),
                "outcome": str(event.get("outcome", "unknown")),
                "policy_id": str(event.get("policy_id", "fixed")),
                "state_generation": str(event.get("state_generation", "")),
            }
            for event in events
        ),
        key=lambda value: (value["start_ns"], value["job_id"], value["event_id"]),
    )
    if len(ordered) <= _DISPLAY_EVENT_LIMIT:
        return ordered, {
            "source_count": len(ordered),
            "display_count": len(ordered),
            "method": "all state-flow events",
            "limit": _DISPLAY_EVENT_LIMIT,
        }
    indices = {
        round(index * (len(ordered) - 1) / (_DISPLAY_EVENT_LIMIT - 1))
        for index in range(_DISPLAY_EVENT_LIMIT)
    }
    selected = [ordered[index] for index in sorted(indices)]
    return selected, {
        "source_count": len(ordered),
        "display_count": len(selected),
        "method": "deterministic time-order decimation",
        "limit": _DISPLAY_EVENT_LIMIT,
    }


def _display_rack_trace(
    samples: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
    channel_id: str | None,
) -> dict[str, Any]:
    points = [
        {
            "utc_ns": _sample_midpoint_ns(sample),
            "power_w": float(sample["value"]),
            "source_sequence": int(sample.get("sequence", index)),
        }
        for index, sample in enumerate(samples)
    ]
    if len(points) <= _DISPLAY_RACK_POINT_LIMIT:
        return {
            "channel_id": channel_id,
            "unit": "W",
            "source_count": len(points),
            "display_count": len(points),
            "downsampling": {
                "method": "identity",
                "limit": _DISPLAY_RACK_POINT_LIMIT,
                "retained_event_boundary_count": len(
                    {
                        int(event[key])
                        for event in events
                        for key in ("actual_start_ns", "actual_end_ns")
                    }
                ),
                "total_event_boundary_count": len(
                    {
                        int(event[key])
                        for event in events
                        for key in ("actual_start_ns", "actual_end_ns")
                    }
                ),
            },
            "points": points,
        }
    times = [point["utc_ns"] for point in points]
    boundary_times = sorted(
        {
            int(event[key])
            for event in events
            for key in ("actual_start_ns", "actual_end_ns")
        }
    )
    required = {0, len(points) - 1}
    minimum_index = min(range(len(points)), key=lambda index: points[index]["power_w"])
    maximum_index = max(range(len(points)), key=lambda index: points[index]["power_w"])
    required.update((minimum_index, maximum_index))
    boundary_indices: list[int] = []
    for boundary in boundary_times:
        position = bisect_left(times, boundary)
        candidates = [index for index in (position - 1, position) if 0 <= index < len(points)]
        if candidates:
            boundary_indices.append(
                min(candidates, key=lambda index: (abs(times[index] - boundary), index))
            )
    required.update(boundary_indices)
    if len(required) > _DISPLAY_RACK_POINT_LIMIT:
        protected = {0, len(points) - 1, minimum_index, maximum_index}
        available = _DISPLAY_RACK_POINT_LIMIT - len(protected)
        unique_boundaries = sorted(set(boundary_indices) - protected)
        retained_boundaries = {
            unique_boundaries[
                round(index * (len(unique_boundaries) - 1) / max(1, available - 1))
            ]
            for index in range(max(0, available))
        } if unique_boundaries and available > 0 else set()
        required = protected | retained_boundaries
    remaining = _DISPLAY_RACK_POINT_LIMIT - len(required)
    if remaining > 0:
        bin_count = max(1, remaining // 2)
        for bin_index in range(bin_count):
            start = int(bin_index * len(points) / bin_count)
            end = max(start + 1, int((bin_index + 1) * len(points) / bin_count))
            indices = range(start, min(end, len(points)))
            required.add(min(indices, key=lambda index: points[index]["power_w"]))
            required.add(max(indices, key=lambda index: points[index]["power_w"]))
            if len(required) >= _DISPLAY_RACK_POINT_LIMIT:
                break
    if len(required) < _DISPLAY_RACK_POINT_LIMIT:
        candidates = [index for index in range(len(points)) if index not in required]
        needed = _DISPLAY_RACK_POINT_LIMIT - len(required)
        if candidates:
            required.update(
                candidates[
                    round(index * (len(candidates) - 1) / max(1, needed - 1))
                ]
                for index in range(min(needed, len(candidates)))
            )
    selected = [points[index] for index in sorted(required)[:_DISPLAY_RACK_POINT_LIMIT]]
    retained_boundary_count = len(set(boundary_indices) & required)
    return {
        "channel_id": channel_id,
        "unit": "W",
        "source_count": len(points),
        "display_count": len(selected),
        "downsampling": {
            "method": "event-boundary-preserving-minmax-envelope",
            "limit": _DISPLAY_RACK_POINT_LIMIT,
            "retained_event_boundary_count": retained_boundary_count,
            "total_event_boundary_count": len(set(boundary_indices)),
            "global_extrema_retained": True,
        },
        "points": selected,
    }


def _event_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    display, display_meta = _bounded_display_events(events)
    counts: dict[str, int] = {}
    for event in events:
        kind = str(event["kind"])
        counts[kind] = counts.get(kind, 0) + 1
    return {
        "event_count": len(events),
        "counts_by_kind": counts,
        "completed_count": sum(event.get("outcome") == "completed" for event in events),
        "failed_count": sum(event.get("outcome") == "failed" for event in events),
        "deadline_miss_count": sum(event.get("outcome") == "deadline-missed" for event in events),
        "display_events": display,
        "display_event_selection": display_meta,
    }


def _episode_spectral_distribution(
    np: Any,
    samples: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, str], list[Mapping[str, Any]]] = {}
    for event in events:
        if str(event.get("kind")) not in _MOVABLE_KINDS:
            continue
        key = (int(event["job_id"]), str(event["state_generation"]))
        grouped.setdefault(key, []).append(event)
    episodes: list[dict[str, Any]] = []
    for (job_id, generation), selected_events in sorted(grouped.items()):
        start_ns = min(int(event["actual_start_ns"]) for event in selected_events)
        end_ns = max(int(event["actual_end_ns"]) for event in selected_events)
        episode_samples = [
            sample
            for sample in samples
            if start_ns <= _sample_midpoint_ns(sample) <= end_ns
        ]
        analysis = _native_spectral_energy(
            np, episode_samples, manifest=manifest
        )
        episodes.append(
            {
                "job_id": job_id,
                "state_generation": generation,
                "start_ns": start_ns,
                "end_ns": end_ns,
                "event_count": len(selected_events),
                "sample_count": len(episode_samples),
                "spectral_energy_0_1_10_hz_w2": analysis["value_w2"],
                "analysis": analysis,
            }
        )
    return episodes


def _external_adjacent_metrics(
    result: TelemetrySessionResult,
    *,
    started_ns: int,
    ended_ns: int,
) -> dict[str, Any]:
    manifests = _manifest_by_channel(result)
    metrics: dict[str, Any] = {}
    for channel_id, manifest in manifests.items():
        boundary = str(manifest["boundary"])
        if boundary not in {
            STORAGE_ACTIVITY_BOUNDARY,
            STORAGE_POWER_BOUNDARY,
            COOLING_BOUNDARY,
        }:
            continue
        samples = _channel_samples_in_window(
            result,
            channel_id,
            started_ns=started_ns,
            ended_ns=ended_ns,
        )
        entry: dict[str, Any] = {
            "channel_id": channel_id,
            "boundary": boundary,
            "metric": manifest["metric"],
            "unit": manifest["unit"],
            "sample_kind": manifest["sample_kind"],
            "period": _effective_period_ms(samples),
            "sample_count": len(samples),
        }
        if str(manifest["unit"]) == "W":
            entry["integrated_energy_j"] = _integrate_power(samples, manifest)
            entry["peak"] = max((float(value["value"]) for value in samples), default=None)
        elif str(manifest["sample_kind"]) == "cumulative_counter":
            entry["observed_delta"] = _counter_delta(samples)
        elif samples:
            entry["minimum"] = min(float(value["value"]) for value in samples)
            entry["maximum"] = max(float(value["value"]) for value in samples)
            entry["median"] = _median(float(value["value"]) for value in samples)
        metrics[channel_id] = entry
    return metrics


def _arm_telemetry_invalidators(
    scenario: Mapping[str, Any],
    config: TelemetryConfig,
    execution: Mapping[str, Any],
    external: TelemetrySessionResult,
    rack_samples: Sequence[Mapping[str, Any]],
) -> dict[str, bool]:
    manifests = [dict(value) for value in external.channel_manifests]
    boundary_metrics = {
        (str(value.get("boundary")), str(value.get("metric"))): str(value["channel_id"])
        for value in manifests
    }
    started_ns = int(execution["started_ns"])
    ended_ns = int(execution["ended_ns"])

    def window_samples(channel_id: str) -> list[dict[str, Any]]:
        return _channel_samples_in_window(
            external,
            channel_id,
            started_ns=started_ns,
            ended_ns=ended_ns,
        )
    required_storage_activity = {
        str(value) for value in scenario["telemetry"]["storage_activity"]["signals"]
    }
    observed_storage_activity = {
        metric
        for (boundary, metric), channel in boundary_metrics.items()
        if boundary == STORAGE_ACTIVITY_BOUNDARY and window_samples(channel)
    }
    storage_power_channels = [
        channel
        for (boundary, _), channel in boundary_metrics.items()
        if boundary == STORAGE_POWER_BOUNDARY
    ]
    cooling_required = {
        str(value) for value in scenario["telemetry"]["cooling"]["signals"]
    }
    observed_cooling = {
        metric
        for (boundary, metric), channel in boundary_metrics.items()
        if boundary == COOLING_BOUNDARY and window_samples(channel)
    }
    event_times = [
        int(event[key])
        for event in execution["events"]
        for key in ("actual_start_ns", "actual_end_ns")
    ]
    event_window_incomplete = True
    if rack_samples and event_times:
        event_window_incomplete = not (
            int(rack_samples[0]["utc_interval_start_ns"]) <= min(event_times)
            and int(rack_samples[-1]["utc_interval_end_ns"]) >= max(event_times)
        )
    required_window_incomplete = False
    if event_times:
        event_start = min(event_times)
        event_end = max(event_times)
        for channel_id in config.required_channels:
            selected = window_samples(str(channel_id))
            if not selected or not (
                int(selected[0]["utc_interval_start_ns"]) <= event_start
                and int(selected[-1]["utc_interval_end_ns"]) >= event_end
            ):
                required_window_incomplete = True
                break
    else:
        required_window_incomplete = True
    maximum_clock_ns = max(
        int(execution["external_telemetry"]["maximum_clock_uncertainty_ns"]),
        *(int(value["maximum_clock_uncertainty_ns"]) for value in execution["gpu_telemetry"]),
    )
    gpu_maximum_period = float(scenario["telemetry"]["gpu"]["maximum_effective_period_ms"])
    gpu_period_invalid = False
    for rank_gpu in execution["gpu_telemetry"]:
        for channel in rank_gpu["channel_metrics"].values():
            maximum = channel["period"].get("maximum_ms")
            gpu_period_invalid = gpu_period_invalid or (
                maximum is None or float(maximum) > gpu_maximum_period
            )
    rack_period = _effective_period_ms(rack_samples)
    rack_limit = float(
        scenario["telemetry"]["rack_pdu_power"]["maximum_effective_period_ms"]
    )
    storage_period_invalid = False
    cooling_period_invalid = False
    for (boundary, _), channel in boundary_metrics.items():
        period = _effective_period_ms(window_samples(channel))
        maximum = period["maximum_ms"]
        if boundary in {STORAGE_ACTIVITY_BOUNDARY, STORAGE_POWER_BOUNDARY}:
            storage_period_invalid = storage_period_invalid or (
                maximum is None
                or float(maximum)
                > float(
                    scenario["telemetry"][
                        "storage_activity"
                        if boundary == STORAGE_ACTIVITY_BOUNDARY
                        else "storage_power"
                    ]["maximum_effective_period_ms"]
                )
            )
        elif boundary == COOLING_BOUNDARY:
            cooling_period_invalid = cooling_period_invalid or (
                maximum is None
                or float(maximum)
                > float(scenario["telemetry"]["cooling"]["maximum_effective_period_ms"])
            )
    return {
        "missing_primary_rack_pdu_samples": len(rack_samples) < 2,
        "missing_required_storage_activity": not required_storage_activity.issubset(observed_storage_activity),
        "missing_required_storage_power": not any(
            window_samples(channel) for channel in storage_power_channels
        ),
        "missing_required_cooling_channels": not cooling_required.issubset(observed_cooling),
        "declared_required_channel_unavailable": bool(external.missing_required_channel_ids),
        "clock_uncertainty_above_limit": maximum_clock_ns
        > int(float(scenario["telemetry"]["maximum_event_clock_uncertainty_ms"]) * 1e6),
        "nonmonotone_gpu_energy_counter": any(
            bool(value["nonmonotone_energy_counter"])
            for value in execution["gpu_telemetry"]
        ),
        "incomplete_state_flow_event_window": event_window_incomplete,
        "incomplete_required_channel_window": required_window_incomplete,
        "gpu_effective_period_above_limit": gpu_period_invalid,
        "rack_pdu_effective_period_above_limit": (
            rack_period["maximum_ms"] is None
            or float(rack_period["maximum_ms"]) > rack_limit
        ),
        "storage_effective_period_above_limit": storage_period_invalid,
        "cooling_effective_period_above_limit": cooling_period_invalid,
        "telemetry_session_error": bool(external.terminal_error)
        or any(bool(value["terminal_error"]) for value in execution["gpu_telemetry"]),
    }


def _finalize_arm(
    np: Any,
    scenario: Mapping[str, Any],
    telemetry_config: TelemetryConfig,
    execution: dict[str, Any],
    external: TelemetrySessionResult,
) -> dict[str, Any]:
    rack_channel = _rack_power_channel(external, telemetry_config)
    rack_samples = _channel_samples(external, rack_channel) if rack_channel else []
    rack_samples = [
        sample
        for sample in rack_samples
        if int(execution["started_ns"])
        <= _sample_midpoint_ns(sample)
        <= int(execution["ended_ns"])
    ]
    manifests = _manifest_by_channel(external)
    rack_manifest = manifests.get(rack_channel or "", {})
    rack_energy = _integrate_power(rack_samples, rack_manifest) if rack_channel else None
    useful_tokens = sum(int(job["useful_tokens"]) for job in execution["by_job"])
    attempted_tokens = sum(int(job["attempted_tokens"]) for job in execution["by_job"])
    redistributed = sum(
        int(job["survivor_redistributed_tokens"]) for job in execution["by_job"]
    )
    recoveries = [
        float(value)
        for job in execution["by_job"]
        for value in job["recovery_times_s"]
    ]
    nll_values = [
        float(job["final_held_out_nll"])
        for job in execution["by_job"]
        if job.get("final_held_out_nll") is not None
    ]
    semantic_count = sum(
        int(job["semantic_invariant_violations"]) for job in execution["by_job"]
    )
    durable_count = sum(int(job["durable_cut_violations"]) for job in execution["by_job"])
    rollback_count = sum(int(job["rollback_bound_violations"]) for job in execution["by_job"])
    event_summary = _event_summary(execution["events"])
    spectral = _native_spectral_energy(np, rack_samples, manifest=rack_manifest)
    spectral["episode_distribution"] = _episode_spectral_distribution(
        np, rack_samples, execution["events"], rack_manifest
    )
    telemetry_invalidators = _arm_telemetry_invalidators(
        scenario, telemetry_config, execution, external, rack_samples
    )
    semantics = {
        "semantic_invariant_violations": semantic_count,
        "durable_cut_violations": durable_count,
        "rollback_bound_violations": rollback_count,
        "equal_useful_work": useful_tokens
        == int(scenario["canonical_work"]["useful_tokens_per_job"])
        * len(execution["by_job"]),
        "exact_state_commitments": [
            {
                "job_id": int(job["job_id"]),
                "state_sha256": job["final_state_sha256"],
                "quota_commitment_sha256": job["quota_commitment_sha256"],
            }
            for job in execution["by_job"]
        ],
    }
    display_intervals = event_summary["display_events"]
    arm = {
        key: execution[key]
        for key in (
            "arm_id",
            "block_id",
            "split",
            "policy_id",
            "started_at",
            "wall_seconds",
            "by_job",
            "gpu_telemetry",
            "external_telemetry",
            "raw_trace_refs",
            "error",
        )
    }
    arm.update(
        {
            "useful_tokens": useful_tokens,
            "attempted_tokens": attempted_tokens,
            "survivor_redistributed_tokens": redistributed,
            "useful_token_throughput": (
                useful_tokens / float(execution["wall_seconds"])
                if execution["wall_seconds"] > 0
                else None
            ),
            "rack_energy_j": rack_energy,
            "rack_energy_per_useful_token": (
                rack_energy / useful_tokens
                if rack_energy is not None and useful_tokens > 0
                else None
            ),
            "p99_9_rack_ramp_w_per_s": _rack_ramp(rack_samples),
            "rack_spectral_energy_0_1_10_hz": spectral["value_w2"],
            "rack_spectral_analysis": spectral,
            "state_flow_coincidence": _state_flow_coincidence(
                execution["events"], len(execution["by_job"])
            ),
            "recovery_times_s": recoveries,
            "p95_recovery_time_s": _percentile(recoveries, 0.95),
            "final_held_out_nll": _median(nll_values),
            "held_out_nll_by_job": nll_values,
            "semantics": semantics,
            "telemetry_quality": {
                "valid": not any(telemetry_invalidators.values()),
                "invalidators": telemetry_invalidators,
                "rack_power_period": _effective_period_ms(rack_samples),
            },
            "adjacent_boundaries": _external_adjacent_metrics(
                external,
                started_ns=int(execution["started_ns"]),
                ended_ns=int(execution["ended_ns"]),
            ),
            "event_summary": event_summary,
            "display_trace": {
                "rack_pdu": _display_rack_trace(
                    rack_samples, execution["events"], rack_channel
                ),
                "state_flow_intervals": display_intervals,
            },
        }
    )
    return arm


def _update_operation_model(
    model: _OperationModel,
    execution: Mapping[str, Any],
    external: TelemetrySessionResult,
    telemetry_config: TelemetryConfig,
) -> None:
    rack_channel = _rack_power_channel(external, telemetry_config)
    rack_samples = (
        _channel_samples_in_window(
            external,
            rack_channel,
            started_ns=int(execution["started_ns"]),
            ended_ns=int(execution["ended_ns"]),
        )
        if rack_channel
        else []
    )
    baseline = _median(float(sample["value"]) for sample in rack_samples)
    for event in execution["events"]:
        kind = str(event["kind"])
        if kind not in _MOVABLE_KINDS:
            continue
        start_ns = int(event["actual_start_ns"])
        end_ns = int(event["actual_end_ns"])
        duration = max(1, end_ns - start_ns)
        during = [
            float(sample["value"])
            for sample in rack_samples
            if start_ns <= _sample_midpoint_ns(sample) <= end_ns
        ]
        power_delta = None
        if baseline is not None and during:
            power_delta = max(0.0, statistics.fmean(during) - baseline)
        model.observe(kind, duration, power_delta)


_COMPARISON_METRICS: Mapping[str, Mapping[str, str]] = {
    "p99_9_rack_ramp_w_per_s": {
        "effect_kind": "relative_reduction",
        "unit": "fraction",
        "source_unit": "W/s",
    },
    "rack_spectral_energy_0_1_10_hz": {
        "effect_kind": "relative_reduction",
        "unit": "fraction",
        "source_unit": "W^2",
    },
    "state_flow_coincidence.maximum_simultaneous_active_fraction": {
        "effect_kind": "relative_reduction",
        "unit": "fraction",
        "source_unit": "fraction",
    },
    "useful_token_throughput": {
        "effect_kind": "relative_increase",
        "unit": "fraction",
        "source_unit": "tokens/s",
    },
    "rack_energy_per_useful_token": {
        "effect_kind": "relative_increase",
        "unit": "fraction",
        "source_unit": "J/token",
    },
    "p95_recovery_time_s": {
        "effect_kind": "relative_increase",
        "unit": "fraction",
        "source_unit": "s",
    },
    "final_held_out_nll": {
        "effect_kind": "absolute_difference",
        "unit": "nats/token",
        "source_unit": "nats/token",
    },
}


def _metric_value(arm: Mapping[str, Any], path: str) -> float | None:
    value: Any = arm
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return float(value) if _finite(value) else None


def _paired_effect(candidate: float, baseline: float, kind: str) -> float | None:
    if kind == "absolute_difference":
        return abs(candidate - baseline)
    if baseline == 0:
        return None
    if kind == "relative_reduction":
        return 1.0 - candidate / baseline
    if kind == "relative_increase":
        return candidate / baseline - 1.0
    raise ValueError(f"unknown paired effect kind {kind!r}")


def _bootstrap_interval(
    values: Sequence[float],
    scenario: Mapping[str, Any],
    *,
    seed_offset: int,
) -> dict[str, Any]:
    bootstrap = scenario["paired_design"]["paired_bootstrap"]
    confidence = float(bootstrap["confidence_level"])
    draws = int(bootstrap["draws"])
    seed = int(bootstrap["seed"]) + seed_offset
    if not values:
        return {
            "lower": None,
            "upper": None,
            "confidence_level": confidence,
            "draws": draws,
            "seed": seed,
        }
    rng = random.Random(seed)
    statistics_draws = []
    for _ in range(draws):
        sample = [values[rng.randrange(len(values))] for _ in values]
        statistics_draws.append(statistics.median(sample))
    alpha = (1.0 - confidence) * 0.5
    return {
        "lower": _percentile(statistics_draws, alpha),
        "upper": _percentile(statistics_draws, 1.0 - alpha),
        "confidence_level": confidence,
        "draws": draws,
        "seed": seed,
    }


def _comparison(
    scenario: Mapping[str, Any],
    blocks: Sequence[Mapping[str, Any]],
    *,
    candidate_policy: str,
    baseline_policy: str,
    metric: str,
    seed_offset: int,
) -> dict[str, Any]:
    specification = _COMPARISON_METRICS[metric]
    paired: list[dict[str, Any]] = []
    effects: list[float] = []
    for block in blocks:
        if block["split"] != "evaluation":
            continue
        arms = {str(arm["policy_id"]): arm for arm in block["arms"]}
        candidate_arm = arms.get(candidate_policy)
        baseline_arm = arms.get(baseline_policy)
        if candidate_arm is None or baseline_arm is None:
            continue
        candidate = _metric_value(candidate_arm, metric)
        baseline = _metric_value(baseline_arm, metric)
        if candidate is None or baseline is None:
            continue
        effect = _paired_effect(candidate, baseline, specification["effect_kind"])
        if effect is None:
            continue
        paired.append(
            {
                "block_id": block["block_id"],
                "candidate": candidate,
                "baseline": baseline,
                "effect": effect,
            }
        )
        effects.append(effect)
    return {
        "metric": metric,
        "effect_kind": specification["effect_kind"],
        "unit": specification["unit"],
        "source_unit": specification["source_unit"],
        "candidate_policy": candidate_policy,
        "baseline_policy": baseline_policy,
        "paired_values": paired,
        "paired_block_count": len(paired),
        "median_effect": _median(effects),
        "confidence_interval_90": _bootstrap_interval(
            effects, scenario, seed_offset=seed_offset
        ),
    }


def _all_comparisons(
    scenario: Mapping[str, Any],
    blocks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    baselines = (
        "synchronized",
        "random_jitter",
        "throughput_pacing",
        "static_cohorts",
    )
    for baseline_index, baseline in enumerate(baselines):
        label = f"telemetry_feedback_vs_{baseline}"
        result[label] = {}
        for metric_index, metric in enumerate(_COMPARISON_METRICS):
            result[label][metric] = _comparison(
                scenario,
                blocks,
                candidate_policy="telemetry_feedback",
                baseline_policy=baseline,
                metric=metric,
                seed_offset=(baseline_index + 1) * 1000 + metric_index,
            )
    return result


def _policy_metrics(blocks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for policy_id in POLICIES:
        arms = [
            arm
            for block in blocks
            if block["split"] == "evaluation"
            for arm in block["arms"]
            if arm["policy_id"] == policy_id
        ]
        output[policy_id] = {
            "evaluation_arm_count": len(arms),
            **{
                metric: _median(_metric_value(arm, metric) for arm in arms)
                for metric in _COMPARISON_METRICS
            },
            "semantic_invariant_violations": sum(
                int(arm["semantics"]["semantic_invariant_violations"])
                for arm in arms
            ),
            "durable_cut_violations": sum(
                int(arm["semantics"]["durable_cut_violations"])
                for arm in arms
            ),
            "rollback_bound_violations": sum(
                int(arm["semantics"]["rollback_bound_violations"])
                for arm in arms
            ),
        }
    return output


def _gate_lower(
    comparison: Mapping[str, Any], threshold: float, description: str
) -> dict[str, Any]:
    lower = comparison["confidence_interval_90"]["lower"]
    return {
        "description": description,
        "threshold": threshold,
        "comparison": f"{comparison['candidate_policy']}_vs_{comparison['baseline_policy']}",
        "metric": comparison["metric"],
        "effect_kind": comparison["effect_kind"],
        "statistic": "90% paired-bootstrap lower bound",
        "observed": lower,
        "passed": lower is not None and float(lower) >= threshold,
    }


def _gate_upper(
    comparison: Mapping[str, Any], threshold: float, description: str
) -> dict[str, Any]:
    upper = comparison["confidence_interval_90"]["upper"]
    return {
        "description": description,
        "threshold": threshold,
        "comparison": f"{comparison['candidate_policy']}_vs_{comparison['baseline_policy']}",
        "metric": comparison["metric"],
        "effect_kind": comparison["effect_kind"],
        "statistic": "90% paired-bootstrap upper bound",
        "observed": upper,
        "passed": upper is not None and float(upper) <= threshold,
    }


def _summary_gates(
    scenario: Mapping[str, Any],
    comparisons: Mapping[str, Any],
    policies: Mapping[str, Any],
    measurement_valid: bool,
    blocks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    hypothesis = scenario["hypothesis"]
    sync = comparisons["telemetry_feedback_vs_synchronized"]
    jitter = comparisons["telemetry_feedback_vs_random_jitter"]
    feedback = policies["telemetry_feedback"]
    gates: dict[str, Any] = {
        "rack_ramp_vs_synchronized": _gate_lower(
            sync["p99_9_rack_ramp_w_per_s"],
            float(hypothesis["rack_ramp_reduction_vs_synchronized_gte"]),
            "feedback rack-ramp reduction versus synchronized",
        ),
        "rack_spectral_vs_synchronized": _gate_lower(
            sync["rack_spectral_energy_0_1_10_hz"],
            float(hypothesis["rack_spectral_reduction_vs_synchronized_gte"]),
            "feedback 0.1-10 Hz spectral reduction versus synchronized",
        ),
        "rack_ramp_vs_random_jitter": _gate_lower(
            jitter["p99_9_rack_ramp_w_per_s"],
            float(hypothesis["rack_ramp_reduction_vs_random_jitter_gte"]),
            "feedback rack-ramp reduction versus random jitter",
        ),
        "rack_spectral_vs_random_jitter": _gate_lower(
            jitter["rack_spectral_energy_0_1_10_hz"],
            float(hypothesis["rack_spectral_reduction_vs_random_jitter_gte"]),
            "feedback 0.1-10 Hz spectral reduction versus random jitter",
        ),
        "useful_token_throughput": _gate_lower(
            sync["useful_token_throughput"],
            -float(hypothesis["useful_token_throughput_regression_lte"]),
            "feedback useful-token throughput regression versus synchronized",
        ),
        "rack_energy_per_useful_token": _gate_upper(
            sync["rack_energy_per_useful_token"],
            float(hypothesis["rack_energy_per_useful_token_increase_lte"]),
            "feedback rack energy per useful token increase versus synchronized",
        ),
        "p95_recovery_time": _gate_upper(
            sync["p95_recovery_time_s"],
            float(hypothesis["p95_recovery_time_regression_lte"]),
            "feedback p95 recovery-time regression versus synchronized",
        ),
        "held_out_nll": _gate_upper(
            sync["final_held_out_nll"],
            float(hypothesis["held_out_nll_absolute_difference_lte"]),
            "feedback held-out NLL absolute difference versus synchronized",
        ),
        "semantic_invariants": {
            "description": "feedback semantic invariant violations",
            "threshold": int(hypothesis["semantic_invariant_violations_eq"]),
            "statistic": "total evaluation violations",
            "observed": int(feedback["semantic_invariant_violations"]),
            "passed": int(feedback["semantic_invariant_violations"])
            == int(hypothesis["semantic_invariant_violations_eq"]),
        },
        "durable_cuts": {
            "description": "feedback durable-cut violations",
            "threshold": int(hypothesis["durable_cut_violations_eq"]),
            "statistic": "total evaluation violations",
            "observed": int(feedback["durable_cut_violations"]),
            "passed": int(feedback["durable_cut_violations"])
            == int(hypothesis["durable_cut_violations_eq"]),
        },
        "rollback_bound": {
            "description": "feedback rollback-bound violations",
            "threshold": int(hypothesis["rollback_bound_violations_eq"]),
            "statistic": "total evaluation violations",
            "observed": int(feedback["rollback_bound_violations"]),
            "passed": int(feedback["rollback_bound_violations"])
            == int(hypothesis["rollback_bound_violations_eq"]),
        },
    }
    evaluation_feedback_arms = [
        arm
        for block in blocks
        if block["split"] == "evaluation"
        for arm in block["arms"]
        if arm["policy_id"] == "telemetry_feedback"
    ]
    maximum_job_nll_difference = max(
        (
            float(arm["held_out_nll_absolute_difference_vs_synchronized"])
            for arm in evaluation_feedback_arms
            if arm.get("held_out_nll_absolute_difference_vs_synchronized") is not None
        ),
        default=None,
    )
    gates["held_out_nll"]["maximum_job_absolute_difference"] = maximum_job_nll_difference
    gates["held_out_nll"]["maximum_job_threshold"] = float(
        hypothesis["held_out_nll_absolute_difference_lte"]
    )
    gates["held_out_nll"]["passed"] = bool(gates["held_out_nll"]["passed"]) and (
        maximum_job_nll_difference is not None
        and maximum_job_nll_difference
        <= float(hypothesis["held_out_nll_absolute_difference_lte"])
    )
    required = [value["passed"] for value in gates.values()]
    gates["all_required"] = {
        "description": "measurement valid and every preregistered gate passed",
        "measurement_valid": measurement_valid,
        "component_gate_count": len(required),
        "passed_component_count": sum(bool(value) for value in required),
        "passed": measurement_valid and all(required),
    }
    return gates


def _apply_block_semantic_reference(block: MutableMapping[str, Any]) -> None:
    arms = {str(arm["policy_id"]): arm for arm in block["arms"]}
    reference = arms.get("synchronized")
    if reference is None:
        for arm in block["arms"]:
            arm["semantics"]["semantic_invariant_violations"] += len(arm["by_job"])
            arm["semantics"]["missing_synchronized_reference"] = True
        return
    reference_jobs = {int(job["job_id"]): job for job in reference["by_job"]}
    for arm in block["arms"]:
        nll_differences: list[float] = []
        cross_policy_violations = 0
        for job in arm["by_job"]:
            job_id = int(job["job_id"])
            baseline = reference_jobs.get(job_id)
            if baseline is None:
                job["semantic_violations"].append("missing synchronized job reference")
                cross_policy_violations += 1
                continue
            if job["quota_commitment_sha256"] != baseline["quota_commitment_sha256"]:
                job["semantic_violations"].append("sample commitment differs from synchronized")
                cross_policy_violations += 1
            if job["final_state_sha256"] != baseline["final_state_sha256"]:
                job["semantic_violations"].append("final state differs from synchronized")
                cross_policy_violations += 1
            if (
                job.get("final_held_out_nll") is not None
                and baseline.get("final_held_out_nll") is not None
            ):
                nll_differences.append(
                    abs(
                        float(job["final_held_out_nll"])
                        - float(baseline["final_held_out_nll"])
                    )
                )
            job["semantic_invariant_violations"] = len(job["semantic_violations"])
        arm["semantics"]["cross_policy_state_or_sample_violations"] = cross_policy_violations
        arm["semantics"]["semantic_invariant_violations"] = sum(
            int(job["semantic_invariant_violations"]) for job in arm["by_job"]
        )
        arm["held_out_nll_absolute_difference_vs_synchronized"] = (
            max(nll_differences) if nll_differences else None
        )


def _measurement_validity(
    scenario: Mapping[str, Any],
    blocks: Sequence[Mapping[str, Any]],
    *,
    world_size: int,
    runtime_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    all_arms = [arm for block in blocks for arm in block["arms"]]
    evaluation_blocks = [block for block in blocks if block["split"] == "evaluation"]
    expected_evaluation = set(scenario["paired_design"]["evaluation_blocks"])
    completed_evaluation = {
        str(block["block_id"])
        for block in evaluation_blocks
        if len(block["arms"]) == len(POLICIES)
        and all(arm.get("error") is None for arm in block["arms"])
    }
    telemetry_invalidators = [
        arm["telemetry_quality"]["invalidators"] for arm in all_arms
    ]
    expected_work = (
        int(scenario["canonical_work"]["useful_tokens_per_job"])
        * (world_size // 2)
    )
    invalidators = {
        "world_size_below_minimum": world_size
        < int(scenario["runtime"]["minimum_world_size"]),
        "odd_world_size": bool(world_size % 2),
        "one_process_per_stable_gpu_binding_failed": not bool(
            runtime_manifest["one_stable_gpu_per_rank"]
        ),
        "missing_primary_rack_pdu_samples": any(
            value["missing_primary_rack_pdu_samples"] for value in telemetry_invalidators
        ),
        "missing_required_storage_activity": any(
            value["missing_required_storage_activity"] for value in telemetry_invalidators
        ),
        "missing_required_storage_power": any(
            value["missing_required_storage_power"] for value in telemetry_invalidators
        ),
        "missing_required_cooling_channels": any(
            value["missing_required_cooling_channels"] for value in telemetry_invalidators
        ),
        "clock_uncertainty_above_limit": any(
            value["clock_uncertainty_above_limit"] for value in telemetry_invalidators
        ),
        "nonmonotone_gpu_energy_counter": any(
            value["nonmonotone_gpu_energy_counter"] for value in telemetry_invalidators
        ),
        "incomplete_state_flow_event_window": any(
            value["incomplete_state_flow_event_window"] for value in telemetry_invalidators
        ),
        "incomplete_required_channel_window": any(
            value["incomplete_required_channel_window"]
            for value in telemetry_invalidators
        ),
        "insufficient_paired_evaluation_blocks": completed_evaluation != expected_evaluation,
        "unequal_useful_work": any(
            int(arm["useful_tokens"]) != expected_work for arm in all_arms
        ),
        "semantic_invariant_violation": any(
            int(arm["semantics"]["semantic_invariant_violations"]) != 0
            for arm in all_arms
        ),
        "incomplete_durable_cut": any(
            int(arm["semantics"]["durable_cut_violations"]) != 0
            for arm in all_arms
        ),
        "gpu_effective_period_above_limit": any(
            value["gpu_effective_period_above_limit"] for value in telemetry_invalidators
        ),
        "rack_pdu_effective_period_above_limit": any(
            value["rack_pdu_effective_period_above_limit"] for value in telemetry_invalidators
        ),
        "storage_effective_period_above_limit": any(
            value["storage_effective_period_above_limit"]
            for value in telemetry_invalidators
        ),
        "cooling_effective_period_above_limit": any(
            value["cooling_effective_period_above_limit"]
            for value in telemetry_invalidators
        ),
        "telemetry_session_error": any(
            value["telemetry_session_error"] for value in telemetry_invalidators
        ),
        "declared_required_channel_unavailable": any(
            value["declared_required_channel_unavailable"]
            for value in telemetry_invalidators
        ),
        "arm_execution_failure": any(arm.get("error") is not None for arm in all_arms),
    }
    return {
        "valid": not any(invalidators.values()),
        "invalidators": invalidators,
        "completed_evaluation_blocks": sorted(completed_evaluation),
        "required_evaluation_blocks": sorted(expected_evaluation),
        "arm_count": len(all_arms),
    }


def _decision(
    comparisons: Mapping[str, Any],
    gates: Mapping[str, Any],
    measurement: Mapping[str, Any],
) -> str:
    if not measurement["valid"]:
        return "measurement_invalid"
    simple_matches = False
    for baseline in ("throughput_pacing", "static_cohorts"):
        comparison = comparisons[f"telemetry_feedback_vs_{baseline}"]
        ramp = comparison["p99_9_rack_ramp_w_per_s"]["confidence_interval_90"]
        spectral = comparison["rack_spectral_energy_0_1_10_hz"]["confidence_interval_90"]
        ramp_indistinguishable = (
            ramp["lower"] is not None
            and ramp["upper"] is not None
            and float(ramp["lower"]) <= 0 <= float(ramp["upper"])
        )
        spectral_indistinguishable = (
            spectral["lower"] is not None
            and spectral["upper"] is not None
            and float(spectral["lower"]) <= 0 <= float(spectral["upper"])
        )
        simple_matches = simple_matches or (
            ramp_indistinguishable and spectral_indistinguishable
        )
    if gates["all_required"]["passed"] and simple_matches:
        return "reject_closed_loop_novelty"
    if gates["all_required"]["passed"]:
        return "advance_to_multi_pdu_correlated_failure_pw4"
    electrical = (
        gates["rack_ramp_vs_synchronized"]["passed"]
        or gates["rack_spectral_vs_synchronized"]["passed"]
    )
    constraint_keys = (
        "useful_token_throughput",
        "rack_energy_per_useful_token",
        "p95_recovery_time",
        "semantic_invariants",
        "durable_cuts",
        "rollback_bound",
        "held_out_nll",
    )
    if electrical and not all(gates[key]["passed"] for key in constraint_keys):
        return "publish_tradeoff_and_redirect"
    return "reject_semantic_slack_as_rack_control_resource"


def _build_summary(
    scenario: Mapping[str, Any],
    blocks: Sequence[Mapping[str, Any]],
    measurement: Mapping[str, Any],
) -> dict[str, Any]:
    comparisons = _all_comparisons(scenario, blocks)
    policies = _policy_metrics(blocks)
    gates = _summary_gates(
        scenario,
        comparisons,
        policies,
        bool(measurement["valid"]),
        blocks,
    )
    result = {
        "policy_metrics": policies,
        "comparisons": comparisons,
        "gates": gates,
        "decision": _decision(comparisons, gates, measurement),
    }
    return result


def _validate_scenario(scenario: Mapping[str, Any]) -> None:
    if scenario.get("schema") != SCENARIO_SCHEMA:
        raise ValueError(f"unsupported PW3 scenario schema {scenario.get('schema')!r}")
    if scenario.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("PW3 scenario experiment_id is not E002-PW3")
    policies = tuple(str(value["policy_id"]) for value in scenario["policies"])
    if policies != POLICIES:
        raise ValueError(f"PW3 policy order must remain frozen as {POLICIES}")
    all_blocks = tuple(scenario["paired_design"]["calibration_blocks"]) + tuple(
        scenario["paired_design"]["evaluation_blocks"]
    )
    orders = scenario["paired_design"]["orders"]
    for block_id in all_blocks:
        order = tuple(str(value) for value in orders[block_id])
        if set(order) != set(POLICIES) or len(order) != len(POLICIES):
            raise ValueError(f"block {block_id} does not contain every frozen policy once")
    if int(scenario["canonical_work"]["useful_tokens_per_job"]) != (
        int(scenario["canonical_work"]["logical_ticks"])
        * int(scenario["canonical_work"]["site_quota_count_per_tick"])
        * int(scenario["canonical_work"]["tokens_per_rank_quota"])
    ):
        raise ValueError("PW3 canonical useful-token commitment is internally inconsistent")
    movable = frozenset(str(value) for value in scenario["operation_dag"]["movable_kinds"])
    if movable != _MOVABLE_KINDS:
        raise ValueError("PW3 runtime and frozen movable operation kinds disagree")


def _prove_shared_directory(
    runtime: _DistributedRuntime,
    directory: Path,
) -> None:
    token = None
    marker = directory / ".e002-pw3-shared-storage-binding"
    if runtime.is_root:
        directory.mkdir(parents=True, exist_ok=True)
        token = hashlib.sha256(
            f"{time.time_ns()}:{socket.gethostname()}:{os.getpid()}".encode("utf-8")
        ).hexdigest()
        if marker.exists():
            raise FileExistsError(f"stale PW3 shared-storage marker: {marker}")
        with marker.open("x", encoding="utf-8") as handle:
            handle.write(token + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    token = _broadcast_object(runtime, token)
    runtime.dist.barrier(group=runtime.control_group)
    observed = None
    try:
        observed = marker.read_text(encoding="utf-8").strip()
    except OSError:
        observed = None
    observations = _all_gather_object(runtime, observed)
    if runtime.is_root:
        marker.unlink(missing_ok=False)
    runtime.dist.barrier(group=runtime.control_group)
    if any(value != token for value in observations):
        raise RuntimeError(
            "PW3 raw output directory is not one shared filesystem visible to every rank"
        )


def _runtime_manifest(runtime: _DistributedRuntime) -> dict[str, Any] | None:
    properties = runtime.torch.cuda.get_device_properties(runtime.local_rank)
    local = {
        "rank": runtime.rank,
        "local_rank": runtime.local_rank,
        "job_id": runtime.job_id,
        "within_job_rank": runtime.within_job_rank,
        "hostname": socket.gethostname(),
        "gpu_name": properties.name,
        "gpu_uuid": runtime.discovered_gpu_uuid,
        "compute_capability": [int(properties.major), int(properties.minor)],
        "total_memory_bytes": int(properties.total_memory),
    }
    ranks = _all_gather_object(runtime, local)
    if not runtime.is_root:
        return None
    uuids = [str(value["gpu_uuid"]) for value in ranks if value.get("gpu_uuid")]
    return {
        "launcher": "torchrun",
        "world_size": runtime.world_size,
        "job_count": runtime.job_count,
        "ranks_per_job": 2,
        "one_process_per_gpu": True,
        "distributed_backend": "nccl",
        "control_backend": "gloo",
        "distinct_bound_gpu_uuid_count": len(set(uuids)),
        "one_stable_gpu_per_rank": len(uuids) == runtime.world_size
        and len(set(uuids)) == runtime.world_size,
        "ranks": ranks,
        "software": {
            "torch_version": runtime.torch.__version__,
            "cuda_version": runtime.torch.version.cuda,
            "engine_id": ENGINE_ID,
        },
    }


def _sensor_manifest(
    telemetry_config: TelemetryConfig,
    blocks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    channels: dict[str, dict[str, Any]] = {}
    bindings: dict[int, str | None] = {}
    for block in blocks:
        for arm in block["arms"]:
            for manifest in arm["external_telemetry"]["channel_manifests"]:
                channels[str(manifest["channel_id"])] = dict(manifest)
            for gpu in arm["gpu_telemetry"]:
                bindings[int(gpu["rank"])] = gpu.get("gpu_uuid")
                for manifest in gpu["channel_manifests"]:
                    channels[str(manifest["channel_id"])] = dict(manifest)
    return {
        "telemetry_engine_id": "gpu-stack.e002-pw3-rack-telemetry.v1",
        "telemetry_config_sha256": telemetry_config.config_sha256,
        "required_channel_ids": list(telemetry_config.required_channels),
        "rack_state_channels": dict(telemetry_config.rack_state_channels),
        "channels": [channels[key] for key in sorted(channels)],
        "gpu_uuid_by_rank": {str(key): value for key, value in sorted(bindings.items())},
        "modeled_substitution_count": 0,
    }


def _clock_alignment(blocks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    external_uncertainties = [
        int(arm["external_telemetry"]["maximum_clock_uncertainty_ns"])
        for block in blocks
        for arm in block["arms"]
    ]
    gpu_uncertainties = [
        int(gpu["maximum_clock_uncertainty_ns"])
        for block in blocks
        for arm in block["arms"]
        for gpu in arm["gpu_telemetry"]
    ]
    return {
        "event_clock": "UTC wall clock with telemetry-observed host reference offsets",
        "maximum_external_clock_uncertainty_ns": max(external_uncertainties, default=None),
        "maximum_gpu_clock_uncertainty_ns": max(gpu_uncertainties, default=None),
        "future_trace_visible_to_scheduler": False,
    }


def _raw_trace_manifest(
    raw_root: Path,
    blocks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    chunks = [
        dict(chunk)
        for block in blocks
        for arm in block["arms"]
        for chunk in arm["raw_trace_refs"]
    ]
    durable_files = [
        {
            **dict(generation),
            "path": _safe_relative(str(generation["path"]), raw_root),
            "arm_id": arm["arm_id"],
            "block_id": block["block_id"],
            "policy_id": arm["policy_id"],
            "job_id": int(job["job_id"]),
        }
        for block in blocks
        for arm in block["arms"]
        for job in arm["by_job"]
        for generation in job["durable_generations"]
    ]
    return {
        "schema": "gpu-stack.e002-pw3-raw-trace-manifest.v1",
        "root": str(raw_root.resolve()),
        "chunk_count": len(chunks),
        "file_bytes": sum(int(value.get("file_bytes", 0)) for value in chunks),
        "record_count": sum(int(value.get("record_count", 0)) for value in chunks),
        "chunks": chunks,
        "durable_checkpoint_count": len(durable_files),
        "durable_checkpoint_bytes": sum(
            int(value["file_bytes"]) for value in durable_files
        ),
        "durable_checkpoints": durable_files,
        "embedding_policy": "no full telemetry or event stream embedded in result",
    }


def run_e002_rack_dephasing(
    scenario_path: str | Path,
    dataset_path: str | Path,
    output_path: str | Path,
    *,
    telemetry_config_path: str | Path,
    raw_output_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    """Execute the frozen PW3 physical experiment under ``torchrun``.

    Rank zero atomically writes and returns the complete compact result.  Every
    other rank participates in the physical run and returns ``None``.
    """

    scenario_file = Path(scenario_path)
    scenario = json.loads(scenario_file.read_text(encoding="utf-8"))
    _validate_scenario(scenario)
    source_bindings = _validate_source_bindings(scenario, scenario_file)
    telemetry_config = load_telemetry_config(telemetry_config_path)
    _validate_primary_telemetry_binding(scenario, telemetry_config)
    np, _, torch, nn, functional = lc1._require_dependencies()
    runtime = _initialize_distributed(torch, scenario)
    completed = False
    output_file = Path(output_path).resolve()
    raw_root = (
        Path(raw_output_dir).resolve()
        if raw_output_dir is not None
        else output_file.parent / f"{output_file.stem}-raw"
    )
    blocks: list[dict[str, Any]] = []
    operation_model = _OperationModel()
    try:
        _prove_shared_directory(runtime, raw_root)
        corpora = lc1._load_byte_corpora(Path(dataset_path), scenario["dataset"])
        block_splits = [
            ("calibration", str(block_id))
            for block_id in scenario["paired_design"]["calibration_blocks"]
        ] + [
            ("evaluation", str(block_id))
            for block_id in scenario["paired_design"]["evaluation_blocks"]
        ]
        for split, block_id in block_splits:
            site, warm = _build_block_warm_state(
                runtime,
                scenario,
                corpora,
                block_id,
                torch,
                nn,
                functional,
            )
            warm_local = None
            if runtime.is_job_leader:
                warm_local = {
                    "job_id": runtime.job_id,
                    "rank_ids": list(runtime.pair_ranks),
                    "seed": warm.seed,
                    "ticks": warm.ticks,
                    "quota_count": warm.quota_count,
                    "attempted_tokens": warm.attempted_tokens,
                    "state_sha256": warm.state_sha256,
                    "mean_training_loss": _median(warm.losses),
                    "checkpoint_bytes": int(warm.checkpoint.checkpoint_bytes),
                }
            warm_gathered = _all_gather_object(runtime, warm_local)
            arm_order = [
                str(value)
                for value in scenario["paired_design"]["orders"][block_id]
            ]
            block: dict[str, Any] | None = None
            if runtime.is_root:
                block = {
                    "block_id": block_id,
                    "split": split,
                    "warm_state": {
                        "deterministic_per_job": True,
                        "jobs": [
                            value
                            for rank, value in enumerate(warm_gathered)
                            if rank % 2 == 0 and value is not None
                        ],
                    },
                    "arm_order": arm_order,
                    "arms": [],
                }
            for position, policy_id in enumerate(arm_order, start=1):
                execution, external_result = _run_physical_arm(
                    runtime,
                    scenario,
                    corpora,
                    site,
                    warm,
                    block_id,
                    split,
                    policy_id,
                    operation_model,
                    telemetry_config,
                    raw_root,
                    torch,
                    functional,
                )
                if runtime.is_root:
                    assert execution is not None and external_result is not None
                    arm = _finalize_arm(
                        np,
                        scenario,
                        telemetry_config,
                        execution,
                        external_result,
                    )
                    arm["execution_position"] = position
                    assert block is not None
                    block["arms"].append(arm)
                    if split == "calibration":
                        _update_operation_model(
                            operation_model,
                            execution,
                            external_result,
                            telemetry_config,
                        )
                    print(
                        f"E002-PW3 completed {arm['arm_id']} "
                        f"ramp={arm['p99_9_rack_ramp_w_per_s']} "
                        f"spectral={arm['rack_spectral_energy_0_1_10_hz']} "
                        f"error={arm['error']}",
                        flush=True,
                    )
                operation_payload = _broadcast_object(
                    runtime,
                    operation_model.to_dict() if runtime.is_root else None,
                )
                operation_model = _OperationModel.from_dict(operation_payload)
            if runtime.is_root:
                assert block is not None
                _apply_block_semantic_reference(block)
                blocks.append(block)
            del warm
            del site
            torch.cuda.empty_cache()
            runtime.dist.barrier(group=runtime.control_group)

        runtime_description = _runtime_manifest(runtime)
        payload: dict[str, Any] | None = None
        if runtime.is_root:
            assert runtime_description is not None
            measurement = _measurement_validity(
                scenario,
                blocks,
                world_size=runtime.world_size,
                runtime_manifest=runtime_description,
            )
            summary = _build_summary(scenario, blocks, measurement)
            payload = {
                "schema": SCHEMA,
                "experiment_id": EXPERIMENT_ID,
                "scenario_id": scenario["scenario_id"],
                "scenario_sha256": _content_hash(scenario),
                "scenario_file_sha256": _file_hash(scenario_file),
                "source_bindings": source_bindings,
                "engine": _engine_identity(),
                "runtime": runtime_description,
                "sensor_manifest": _sensor_manifest(telemetry_config, blocks),
                "clock_alignment": _clock_alignment(blocks),
                "paired_blocks": blocks,
                "measurement_validity": measurement,
                "summary": summary,
                "evidence_boundary": {
                    "stage": scenario["claim_boundary"]["stage"],
                    "can_resolve": list(scenario["claim_boundary"]["can_resolve"]),
                    "cannot_resolve": list(scenario["claim_boundary"]["cannot_resolve"]),
                    "observed": [
                        "per-GPU cumulative energy and ancillary telemetry",
                        "rack-PDU power",
                        "shared-storage activity and separately measured storage power",
                        "cooling power and rack inlet/outlet temperature",
                        "exact state-flow, sample, optimizer, and durable-cut commitments",
                    ],
                    "modeled_substitutions": [],
                },
                "raw_trace_manifest": _raw_trace_manifest(raw_root, blocks),
                "completed_at": _utc_now(),
            }
            payload["artifact_sha256"] = _content_hash(payload)
            _atomic_json_write(output_file, payload)
        completed = True
        return payload
    finally:
        _destroy_distributed(runtime, synchronize=completed)


__all__ = ["ENGINE_ID", "SCHEMA", "run_e002_rack_dephasing"]
