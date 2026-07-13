"""Measured small-model learning calibration for E001 recovery policies.

This module is intentionally optional-runtime code.  Importing GPUSTACK does
not require PyTorch, PyArrow, or NVML; the LC1 command loads them only when the
real training experiment is executed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import copy
import hashlib
import json
import math
from pathlib import Path
import statistics
import threading
import time
from typing import Any, Iterable, Mapping, Sequence

from .observations import (
    CalibrationEvaluationSplit,
    MeasuredValue,
    MeasurementUncertainty,
    Observation,
    Provenance,
)


SCHEMA = "gpu-stack.e001-recovery-learning-evidence.v1"
ENGINE_ID = "gpu-stack.e001-learning-calibration.v1"

SYNC_POLICY = "synchronous-reference"
FIXED_POLICY = "fixed-local-checkpoint-restart"
ADAPTIVE_POLICY = "adaptive-survivor-continuation"


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _content_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _source_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_dependencies():
    try:
        import numpy as np
        import pyarrow.parquet as parquet
        import torch
        from torch import nn
        import torch.nn.functional as functional
    except ImportError as exc:  # pragma: no cover - exercised by real experiment env
        raise RuntimeError(
            "E001-LC1 requires the optional experiment runtime: torch, numpy, "
            "and pyarrow"
        ) from exc
    return np, parquet, torch, nn, functional


@dataclass(frozen=True)
class _ByteCorpora:
    site_a: Any
    site_b: Any
    validation: Any
    train_rows: int
    validation_rows: int
    train_bytes: int
    validation_bytes: int


def _load_byte_corpora(dataset_path: Path, dataset: Mapping[str, Any]) -> _ByteCorpora:
    _, parquet, torch, _, _ = _require_dependencies()
    expected_hash = str(dataset["sha256"]).lower()
    actual_hash = _sha256_file(dataset_path)
    if actual_hash != expected_hash:
        raise ValueError(
            f"dataset SHA-256 mismatch: expected {expected_hash}, got {actual_hash}"
        )

    train_rows = int(dataset["train_rows"])
    validation_start = int(dataset["validation_start_row"])
    validation_rows = int(dataset["validation_rows"])
    required_rows = validation_start + validation_rows
    site_buffers = (bytearray(), bytearray())
    validation_buffer = bytearray()
    seen = 0
    parquet_file = parquet.ParquetFile(dataset_path)
    for batch in parquet_file.iter_batches(batch_size=4096, columns=["text"]):
        texts = batch.column(0).to_pylist()
        for text in texts:
            if seen >= required_rows:
                break
            encoded = str(text).encode("utf-8", errors="replace")
            if seen < train_rows:
                site_buffers[seen % 2].extend(encoded)
                site_buffers[seen % 2].append(int(dataset["separator_byte"]))
            elif validation_start <= seen < required_rows:
                validation_buffer.extend(encoded)
                validation_buffer.append(int(dataset["separator_byte"]))
            seen += 1
        if seen >= required_rows:
            break
    if seen < required_rows:
        raise ValueError(
            f"dataset shard exposes {seen} usable rows, requires {required_rows}"
        )

    def as_tensor(buffer: bytearray):
        return torch.frombuffer(buffer, dtype=torch.uint8).clone()

    return _ByteCorpora(
        site_a=as_tensor(site_buffers[0]),
        site_b=as_tensor(site_buffers[1]),
        validation=as_tensor(validation_buffer),
        train_rows=train_rows,
        validation_rows=validation_rows,
        train_bytes=len(site_buffers[0]) + len(site_buffers[1]),
        validation_bytes=len(validation_buffer),
    )


def _batch_seed(seed: int, site_id: str, logical_tick: int, stream: str) -> int:
    material = f"{seed}:{site_id}:{logical_tick}:{stream}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _sample_batch(
    torch,
    corpus,
    *,
    seed: int,
    site_id: str,
    logical_tick: int,
    stream: str,
    batch_size: int,
    context_length: int,
    device,
):
    if int(corpus.numel()) <= context_length + 1:
        raise ValueError("byte corpus is too short for configured context length")
    generator = torch.Generator(device="cpu")
    generator.manual_seed(_batch_seed(seed, site_id, logical_tick, stream))
    starts = torch.randint(
        0,
        int(corpus.numel()) - context_length - 1,
        (batch_size,),
        generator=generator,
    )
    offsets = torch.arange(context_length + 1)
    windows = corpus[starts[:, None] + offsets[None, :]].to(torch.long)
    x = windows[:, :-1].to(device=device, non_blocking=True)
    y = windows[:, 1:].to(device=device, non_blocking=True)
    return x, y


def _build_model(torch, nn, functional, config: Mapping[str, Any], device):
    width = int(config["width"])
    heads = int(config["heads"])
    head_dim = width // heads
    if width % heads:
        raise ValueError("model width must be divisible by attention heads")

    class _Block(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.norm_1 = nn.LayerNorm(width)
            self.qkv = nn.Linear(width, 3 * width, bias=False)
            self.projection = nn.Linear(width, width, bias=False)
            self.norm_2 = nn.LayerNorm(width)
            self.mlp = nn.Sequential(
                nn.Linear(width, int(config["mlp_width"]), bias=False),
                nn.GELU(),
                nn.Linear(int(config["mlp_width"]), width, bias=False),
            )

        def forward(self, x):
            residual = x
            hidden = self.norm_1(x)
            batch, sequence, _ = hidden.shape
            qkv = self.qkv(hidden).view(batch, sequence, 3, heads, head_dim)
            q, k, v = qkv.permute(2, 0, 3, 1, 4).unbind(0)
            attended = functional.scaled_dot_product_attention(
                q,
                k,
                v,
                dropout_p=0.0,
                is_causal=True,
            )
            attended = attended.transpose(1, 2).contiguous().view(
                batch, sequence, width
            )
            x = residual + self.projection(attended)
            return x + self.mlp(self.norm_2(x))

    class _ByteDecoder(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            vocab_size = int(config["vocab_size"])
            context = int(config["context_length"])
            self.token_embedding = nn.Embedding(vocab_size, width)
            self.position_embedding = nn.Embedding(context, width)
            self.blocks = nn.ModuleList(
                [_Block() for _ in range(int(config["layers"]))]
            )
            self.final_norm = nn.LayerNorm(width)
            self.output = nn.Linear(width, vocab_size, bias=False)
            if bool(config.get("tie_embeddings", False)):
                self.output.weight = self.token_embedding.weight
            self.apply(self._initialize)

        @staticmethod
        def _initialize(module) -> None:
            if isinstance(module, (nn.Linear, nn.Embedding)):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)

        def forward(self, tokens):
            sequence = tokens.shape[1]
            positions = torch.arange(sequence, device=tokens.device)
            hidden = self.token_embedding(tokens) + self.position_embedding(
                positions
            )
            for block in self.blocks:
                hidden = block(hidden)
            return self.output(self.final_norm(hidden))

    return _ByteDecoder().to(device)


def _optimizer(torch, model, optimization: Mapping[str, Any]):
    return torch.optim.AdamW(
        model.parameters(),
        lr=float(optimization["learning_rate"]),
        betas=(float(optimization["beta1"]), float(optimization["beta2"])),
        weight_decay=float(optimization["weight_decay"]),
    )


def _tree_to_cpu(value: Any) -> Any:
    if hasattr(value, "detach") and hasattr(value, "cpu"):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {key: _tree_to_cpu(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_tree_to_cpu(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_tree_to_cpu(item) for item in value)
    return copy.deepcopy(value)


def _tree_bytes(value: Any) -> int:
    if hasattr(value, "numel") and hasattr(value, "element_size"):
        return int(value.numel()) * int(value.element_size())
    if isinstance(value, Mapping):
        return sum(_tree_bytes(item) for item in value.values())
    if isinstance(value, (tuple, list)):
        return sum(_tree_bytes(item) for item in value)
    return 0


@dataclass
class _Checkpoint:
    model_state: dict[str, Any]
    optimizer_state: dict[str, Any]
    logical_tick: int
    merge_count: int
    checkpoint_bytes: int


@dataclass
class _Site:
    model: Any
    optimizer: Any


def _checkpoint(site: _Site, logical_tick: int, merge_count: int) -> _Checkpoint:
    model_state = _tree_to_cpu(site.model.state_dict())
    optimizer_state = _tree_to_cpu(site.optimizer.state_dict())
    return _Checkpoint(
        model_state=model_state,
        optimizer_state=optimizer_state,
        logical_tick=logical_tick,
        merge_count=merge_count,
        checkpoint_bytes=_tree_bytes(model_state) + _tree_bytes(optimizer_state),
    )


def _restore(site: _Site, checkpoint: _Checkpoint) -> None:
    site.model.load_state_dict(checkpoint.model_state)
    site.optimizer.load_state_dict(copy.deepcopy(checkpoint.optimizer_state))


def _copy_site(source: _Site, target: _Site) -> None:
    target.model.load_state_dict(source.model.state_dict())
    target.optimizer.load_state_dict(copy.deepcopy(source.optimizer.state_dict()))


def _average_sites(torch, site_a: _Site, site_b: _Site) -> None:
    with torch.no_grad():
        for parameter_a, parameter_b in zip(
            site_a.model.parameters(), site_b.model.parameters(), strict=True
        ):
            average = (parameter_a.data + parameter_b.data) * 0.5
            parameter_a.data.copy_(average)
            parameter_b.data.copy_(average)
        for buffer_a, buffer_b in zip(
            site_a.model.buffers(), site_b.model.buffers(), strict=True
        ):
            if buffer_a.is_floating_point():
                average = (buffer_a.data + buffer_b.data) * 0.5
                buffer_a.data.copy_(average)
                buffer_b.data.copy_(average)

    parameters_a = tuple(site_a.model.parameters())
    parameters_b = tuple(site_b.model.parameters())
    for parameter_a, parameter_b in zip(parameters_a, parameters_b, strict=True):
        state_a = site_a.optimizer.state.get(parameter_a, {})
        state_b = site_b.optimizer.state.get(parameter_b, {})
        for key in sorted(set(state_a) | set(state_b)):
            if key not in state_a:
                state_a[key] = _tree_to_cpu(state_b[key])
                if hasattr(state_a[key], "to"):
                    state_a[key] = state_a[key].to(parameter_a.device)
            if key not in state_b:
                state_b[key] = _tree_to_cpu(state_a[key])
                if hasattr(state_b[key], "to"):
                    state_b[key] = state_b[key].to(parameter_b.device)
            value_a = state_a[key]
            value_b = state_b[key]
            if hasattr(value_a, "is_floating_point") and value_a.is_floating_point():
                average = (value_a + value_b) * 0.5
                value_a.copy_(average)
                value_b.copy_(average)
            elif hasattr(value_a, "copy_"):
                maximum = torch.maximum(value_a, value_b)
                value_a.copy_(maximum)
                value_b.copy_(maximum)


class _PowerSampler:
    def __init__(self) -> None:
        self.available = False
        self.idle_power_w = None
        self._handle = None
        self._pynvml = None
        self._samples: list[tuple[float, float]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        try:
            import pynvml

            pynvml.nvmlInit()
            self._pynvml = pynvml
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self.available = True
            idle = []
            for _ in range(20):
                idle.append(self._read_power())
                time.sleep(0.05)
            self.idle_power_w = statistics.fmean(idle)
        except Exception:
            self.available = False

    def _read_power(self) -> float:
        assert self._pynvml is not None and self._handle is not None
        return float(self._pynvml.nvmlDeviceGetPowerUsage(self._handle)) / 1000.0

    def temperature_c(self) -> int | None:
        if not self.available:
            return None
        assert self._pynvml is not None and self._handle is not None
        try:
            return int(
                self._pynvml.nvmlDeviceGetTemperature(
                    self._handle,
                    self._pynvml.NVML_TEMPERATURE_GPU,
                )
            )
        except Exception:
            return None

    def wait_until_temperature(
        self,
        threshold_c: int,
        *,
        poll_seconds: float,
    ) -> float:
        started = time.perf_counter()
        while True:
            temperature = self.temperature_c()
            if temperature is None or temperature <= threshold_c:
                return time.perf_counter() - started
            time.sleep(poll_seconds)

    def start(self) -> None:
        if not self.available:
            return
        self._samples = []
        self._stop.clear()

        def sample() -> None:
            while not self._stop.is_set():
                try:
                    self._samples.append((time.perf_counter(), self._read_power()))
                except Exception:
                    pass
                self._stop.wait(0.1)

        self._thread = threading.Thread(target=sample, daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, float | int | None]:
        if not self.available:
            return {
                "sample_count": 0,
                "idle_power_w": None,
                "raw_energy_j": None,
                "idle_subtracted_energy_j": None,
            }
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        samples = tuple(self._samples)
        if len(samples) < 2:
            raw = 0.0
            duration = 0.0
        else:
            raw = sum(
                (right[0] - left[0]) * (left[1] + right[1]) * 0.5
                for left, right in zip(samples, samples[1:])
            )
            duration = samples[-1][0] - samples[0][0]
        idle = float(self.idle_power_w or 0.0) * duration
        return {
            "sample_count": len(samples),
            "idle_power_w": self.idle_power_w,
            "raw_energy_j": raw,
            "idle_subtracted_energy_j": max(0.0, raw - idle),
        }


def _train_step(
    torch,
    functional,
    site: _Site,
    x,
    y,
    *,
    autocast_dtype,
    gradient_clip_norm: float,
) -> float:
    site.model.train()
    site.optimizer.zero_grad(set_to_none=True)
    with torch.autocast(
        device_type="cuda",
        dtype=autocast_dtype,
        enabled=x.device.type == "cuda",
    ):
        logits = site.model(x)
        loss = functional.cross_entropy(
            logits.reshape(-1, logits.shape[-1]), y.reshape(-1)
        )
    loss.backward()
    torch.nn.utils.clip_grad_norm_(site.model.parameters(), gradient_clip_norm)
    site.optimizer.step()
    return float(loss.detach().cpu())


def _load_evaluation_state(torch, evaluation_model, site_a: _Site, site_b: _Site | None):
    if site_b is None:
        evaluation_model.load_state_dict(site_a.model.state_dict())
        return
    state_a = site_a.model.state_dict()
    state_b = site_b.model.state_dict()
    averaged: dict[str, Any] = {}
    for key in state_a:
        value_a = state_a[key]
        value_b = state_b[key]
        if value_a.is_floating_point():
            averaged[key] = ((value_a + value_b) * 0.5).detach()
        else:
            averaged[key] = value_a.detach()
    evaluation_model.load_state_dict(averaged)


def _evaluate(
    torch,
    functional,
    evaluation_model,
    corpus,
    *,
    seed: int,
    batch_size: int,
    context_length: int,
    validation_batches: int,
    device,
    autocast_dtype,
) -> tuple[float, float, tuple[float, ...]]:
    evaluation_model.eval()
    losses: list[float] = []
    with torch.no_grad():
        for index in range(validation_batches):
            x, y = _sample_batch(
                torch,
                corpus,
                seed=seed,
                site_id="validation",
                logical_tick=index,
                stream="held-out",
                batch_size=batch_size,
                context_length=context_length,
                device=device,
            )
            with torch.autocast(
                device_type="cuda",
                dtype=autocast_dtype,
                enabled=device.type == "cuda",
            ):
                logits = evaluation_model(x)
                loss = functional.cross_entropy(
                    logits.reshape(-1, logits.shape[-1]), y.reshape(-1)
                )
            losses.append(float(loss.detach().cpu()))
    return (
        statistics.fmean(losses),
        statistics.stdev(losses) if len(losses) > 1 else 0.0,
        tuple(losses),
    )


def _failure_at_tick(failures: Sequence[Sequence[int]], wall_tick: int) -> tuple[bool, bool, bool]:
    active = False
    starts = False
    ends = False
    for start, duration in failures:
        start = int(start)
        end = start + int(duration)
        active = active or start <= wall_tick < end
        starts = starts or wall_tick == start
        ends = ends or wall_tick == end
    return active, starts, ends


def _arm_id(policy_id: str, interrupted: bool) -> str:
    return f"{policy_id}:{'interrupted' if interrupted else 'no-failure'}"


def _run_arm(
    scenario: Mapping[str, Any],
    corpora: _ByteCorpora,
    stratum: Mapping[str, Any],
    arm: Mapping[str, Any],
    power_sampler: _PowerSampler,
) -> dict[str, Any]:
    _, _, torch, nn, functional = _require_dependencies()
    if not torch.cuda.is_available():
        raise RuntimeError("E001-LC1 requires a CUDA-capable PyTorch runtime")
    device = torch.device("cuda:0")
    model_config = scenario["model"]
    optimization = scenario["optimization"]
    seed = int(stratum["seed"])
    policy_id = str(arm["policy_id"])
    interrupted = bool(arm["interrupted"])
    if policy_id not in {SYNC_POLICY, FIXED_POLICY, ADAPTIVE_POLICY}:
        raise ValueError(f"unknown LC1 policy {policy_id!r}")

    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    deterministic_algorithms = bool(
        optimization.get("deterministic_cuda_algorithms", False)
    )
    torch.backends.cuda.matmul.allow_tf32 = not deterministic_algorithms
    torch.backends.cudnn.allow_tf32 = not deterministic_algorithms
    torch.use_deterministic_algorithms(deterministic_algorithms, warn_only=True)

    site_a = _Site(
        model=_build_model(torch, nn, functional, model_config, device),
        optimizer=None,
    )
    site_a.optimizer = _optimizer(torch, site_a.model, optimization)
    site_b = _Site(
        model=_build_model(torch, nn, functional, model_config, device),
        optimizer=None,
    )
    site_b.model.load_state_dict(site_a.model.state_dict())
    site_b.optimizer = _optimizer(torch, site_b.model, optimization)
    evaluation_model = _build_model(torch, nn, functional, model_config, device)
    evaluation_model.load_state_dict(site_a.model.state_dict())

    parameter_count = sum(parameter.numel() for parameter in site_a.model.parameters())
    batch_size = int(optimization["batch_size_per_site"])
    context_length = int(model_config["context_length"])
    tokens_per_quota = batch_size * context_length
    total_wall_ticks = int(optimization["opportunity_ticks"])
    healthy_cadence = int(optimization["healthy_local_ticks"])
    reduced_cadence = int(optimization["reduced_membership_checkpoint_ticks"])
    fixed_checkpoint_interval = int(
        optimization["fixed_checkpoint_merge_interval"]
    )
    adaptive_checkpoint_interval = int(
        optimization["adaptive_checkpoint_merge_interval"]
    )
    evaluation_interval = int(optimization["evaluation_interval_ticks"])
    validation_batches = int(optimization["validation_batches"])
    gradient_clip_norm = float(optimization["gradient_clip_norm"])
    autocast_name = str(optimization["autocast"])
    if autocast_name != "bfloat16":
        raise ValueError("LC1 currently freezes bfloat16 autocast")
    if not torch.cuda.is_bf16_supported():
        raise RuntimeError("configured RTX harness does not support bfloat16")
    autocast_dtype = torch.bfloat16

    failures = tuple(stratum["failures"]) if interrupted else ()
    logical_tick = 0
    merge_count = 0
    steps_since_merge = 0
    post_rejoin_remaining = 0
    checkpoint_count = 0
    checkpoint_bytes = 0
    checkpoint_copy_seconds = 0.0
    restore_seconds = 0.0
    attempted_tokens = 0
    replayed_tokens = 0
    discarded_tokens = 0
    survivor_redistributed_tokens = 0
    training_losses: list[float] = []
    seen_quotas: set[tuple[str, int]] = set()
    divergence = False

    start_checkpoint_at = time.perf_counter()
    latest_checkpoint = _checkpoint(site_a, logical_tick, merge_count)
    checkpoint_copy_seconds += time.perf_counter() - start_checkpoint_at
    checkpoint_count += 1
    checkpoint_bytes += latest_checkpoint.checkpoint_bytes

    def take_checkpoint(source: _Site) -> None:
        nonlocal latest_checkpoint, checkpoint_count, checkpoint_bytes
        nonlocal checkpoint_copy_seconds
        started = time.perf_counter()
        latest_checkpoint = _checkpoint(source, logical_tick, merge_count)
        checkpoint_copy_seconds += time.perf_counter() - started
        checkpoint_count += 1
        checkpoint_bytes += latest_checkpoint.checkpoint_bytes

    def quota(site: _Site, site_id: str, quota_tick: int) -> float:
        nonlocal attempted_tokens, replayed_tokens
        identity = (site_id, quota_tick)
        if identity in seen_quotas:
            replayed_tokens += tokens_per_quota
        else:
            seen_quotas.add(identity)
        corpus = corpora.site_a if site_id == "site-a" else corpora.site_b
        x, y = _sample_batch(
            torch,
            corpus,
            seed=seed,
            site_id=site_id,
            logical_tick=quota_tick,
            stream="training",
            batch_size=batch_size,
            context_length=context_length,
            device=device,
        )
        loss = _train_step(
            torch,
            functional,
            site,
            x,
            y,
            autocast_dtype=autocast_dtype,
            gradient_clip_norm=gradient_clip_norm,
        )
        attempted_tokens += tokens_per_quota
        return loss

    curve: list[dict[str, Any]] = []

    def measure(wall_tick: int, *, active_outage: bool) -> None:
        canonical_b = None if active_outage and policy_id == ADAPTIVE_POLICY else site_b
        _load_evaluation_state(
            torch,
            evaluation_model,
            site_b if canonical_b is None else site_a,
            canonical_b,
        )
        mean, std, losses = _evaluate(
            torch,
            functional,
            evaluation_model,
            corpora.validation,
            seed=seed,
            batch_size=batch_size,
            context_length=context_length,
            validation_batches=validation_batches,
            device=device,
            autocast_dtype=autocast_dtype,
        )
        curve.append(
            {
                "wall_tick": wall_tick,
                "logical_tick": logical_tick,
                "attempted_tokens": attempted_tokens,
                "held_out_nll": mean,
                "held_out_nll_standard_deviation": std,
                "validation_batch_nll": list(losses),
            }
        )

    thermal_guard = scenario["thermal_guard"]
    cooldown_before_seconds = power_sampler.wait_until_temperature(
        int(thermal_guard["start_temperature_c_lte"]),
        poll_seconds=float(thermal_guard["poll_seconds"]),
    )
    start_temperature_c = power_sampler.temperature_c()
    power_sampler.start()
    run_started = time.perf_counter()
    thermal_pause_seconds = 0.0
    measure(0, active_outage=False)
    for wall_tick in range(total_wall_ticks):
        active, starts, ends = _failure_at_tick(failures, wall_tick)
        if ends and policy_id == ADAPTIVE_POLICY:
            restore_started = time.perf_counter()
            _copy_site(site_b, site_a)
            restore_seconds += time.perf_counter() - restore_started
            steps_since_merge = 0
            post_rejoin_remaining = int(optimization["post_rejoin_sync_ticks"])

        if policy_id == FIXED_POLICY and starts:
            rolled_back_ticks = max(0, logical_tick - latest_checkpoint.logical_tick)
            discarded_tokens += rolled_back_ticks * 2 * tokens_per_quota
            restore_started = time.perf_counter()
            _restore(site_a, latest_checkpoint)
            _restore(site_b, latest_checkpoint)
            restore_seconds += time.perf_counter() - restore_started
            logical_tick = latest_checkpoint.logical_tick
            merge_count = latest_checkpoint.merge_count
            steps_since_merge = 0

        if policy_id == FIXED_POLICY and active:
            pass
        elif policy_id == ADAPTIVE_POLICY and active:
            training_losses.append(quota(site_b, "site-a", logical_tick))
            training_losses.append(quota(site_b, "site-b", logical_tick))
            survivor_redistributed_tokens += tokens_per_quota
            logical_tick += 1
            steps_since_merge += 1
            if steps_since_merge >= reduced_cadence:
                merge_count += 1
                steps_since_merge = 0
                take_checkpoint(site_b)
        else:
            training_losses.append(quota(site_a, "site-a", logical_tick))
            training_losses.append(quota(site_b, "site-b", logical_tick))
            logical_tick += 1
            steps_since_merge += 1
            cadence = 1 if policy_id == SYNC_POLICY else healthy_cadence
            if post_rejoin_remaining > 0:
                cadence = 1
            if steps_since_merge >= cadence:
                _average_sites(torch, site_a, site_b)
                merge_count += 1
                steps_since_merge = 0
                if post_rejoin_remaining > 0:
                    post_rejoin_remaining -= 1
                checkpoint_interval = (
                    None
                    if policy_id == SYNC_POLICY
                    else fixed_checkpoint_interval
                    if policy_id == FIXED_POLICY
                    else adaptive_checkpoint_interval
                )
                if (
                    checkpoint_interval is not None
                    and merge_count % checkpoint_interval == 0
                ):
                    take_checkpoint(site_a)

        if any(not math.isfinite(value) for value in training_losses[-2:]):
            divergence = True
            break
        if (wall_tick + 1) % evaluation_interval == 0:
            measure(wall_tick + 1, active_outage=active)
        if (wall_tick + 1) % healthy_cadence == 0:
            temperature = power_sampler.temperature_c()
            if (
                temperature is not None
                and temperature >= int(thermal_guard["pause_temperature_c_gte"])
            ):
                thermal_pause_seconds += power_sampler.wait_until_temperature(
                    int(thermal_guard["resume_temperature_c_lte"]),
                    poll_seconds=float(thermal_guard["poll_seconds"]),
                )

    if not curve or curve[-1]["wall_tick"] != total_wall_ticks:
        active, _, _ = _failure_at_tick(failures, total_wall_ticks - 1)
        measure(total_wall_ticks, active_outage=active)
    torch.cuda.synchronize()
    physical_wall_seconds = time.perf_counter() - run_started
    run_wall_seconds = max(1e-9, physical_wall_seconds - thermal_pause_seconds)
    energy = power_sampler.stop()
    end_temperature_c = power_sampler.temperature_c()

    canonical_tokens = logical_tick * 2 * tokens_per_quota
    attempted_flops = 6.0 * parameter_count * attempted_tokens
    canonical_flops = 6.0 * parameter_count * canonical_tokens
    initial_loss = float(curve[0]["held_out_nll"])
    final_loss = float(curve[-1]["held_out_nll"])
    progress = initial_loss - final_loss
    idle_subtracted_energy = energy["idle_subtracted_energy_j"]
    return {
        "run_id": (
            f"e001-lc1:{stratum['stratum_id']}:{policy_id}:"
            f"{'interrupted' if interrupted else 'no-failure'}"
        ),
        "stratum_id": str(stratum["stratum_id"]),
        "split": "calibration"
        if str(stratum["stratum_id"]).startswith("C")
        else "evaluation",
        "seed": seed,
        "policy_id": policy_id,
        "interrupted": interrupted,
        "failure_schedule": [list(item) for item in failures],
        "parameter_count": parameter_count,
        "curve": curve,
        "initial_held_out_nll": initial_loss,
        "final_held_out_nll": final_loss,
        "final_held_out_nll_standard_deviation": float(
            curve[-1]["held_out_nll_standard_deviation"]
        ),
        "held_out_loss_progress": progress,
        "attempted_tokens": attempted_tokens,
        "canonical_tokens": canonical_tokens,
        "replayed_tokens": replayed_tokens,
        "discarded_tokens": discarded_tokens,
        "survivor_redistributed_tokens": survivor_redistributed_tokens,
        "attempted_compute_flops": attempted_flops,
        "canonical_compute_flops": canonical_flops,
        "progress_per_flop": progress / attempted_flops if attempted_flops else 0.0,
        "progress_per_second": progress / run_wall_seconds
        if run_wall_seconds
        else 0.0,
        "progress_per_joule": (
            progress / float(idle_subtracted_energy)
            if idle_subtracted_energy is not None
            and float(idle_subtracted_energy) > 0.0
            else None
        ),
        "logical_ticks_completed": logical_tick,
        "merge_count": merge_count,
        "checkpoint_count": checkpoint_count,
        "checkpoint_bytes": checkpoint_bytes,
        "checkpoint_copy_seconds": checkpoint_copy_seconds,
        "restore_seconds": restore_seconds,
        "local_wall_clock_seconds": run_wall_seconds,
        "physical_wall_clock_seconds": physical_wall_seconds,
        "thermal_pause_seconds": thermal_pause_seconds,
        "cooldown_before_seconds": cooldown_before_seconds,
        "start_temperature_c": start_temperature_c,
        "end_temperature_c": end_temperature_c,
        "energy": energy,
        "diverged": divergence,
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _first_target_tick(run: Mapping[str, Any], target_loss: float) -> int | None:
    for point in run["curve"]:
        if float(point["held_out_nll"]) <= target_loss:
            return int(point["wall_tick"])
    return None


def _bootstrap_median_interval(
    np,
    values: Sequence[float],
    *,
    draws: int,
    seed: int,
    confidence_level: float,
) -> dict[str, Any]:
    if not values:
        raise ValueError("bootstrap interval requires at least one value")
    array = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(draws, len(array)))
    draws_array = np.median(array[indices], axis=1)
    alpha = (1.0 - confidence_level) * 0.5
    return {
        "values": [float(value) for value in array],
        "median": float(np.median(array)),
        "lower_bound": float(np.quantile(draws_array, alpha)),
        "upper_bound": float(np.quantile(draws_array, 1.0 - alpha)),
        "confidence_level": confidence_level,
        "draws": draws,
        "method": "paired percentile bootstrap of the median",
    }


def _run_lookup(runs: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str, bool], Mapping[str, Any]]:
    return {
        (str(run["stratum_id"]), str(run["policy_id"]), bool(run["interrupted"])): run
        for run in runs
    }


def _summarize(
    scenario: Mapping[str, Any], runs: list[dict[str, Any]]
) -> dict[str, Any]:
    np, _, _, _, _ = _require_dependencies()
    lookup = _run_lookup(runs)
    synchronous_calibration = [
        run
        for run in runs
        if run["split"] == "calibration"
        and run["policy_id"] == SYNC_POLICY
        and not run["interrupted"]
    ]
    if not synchronous_calibration:
        raise RuntimeError("LC1 target requires synchronous calibration controls")
    initial_loss = statistics.median(
        float(run["initial_held_out_nll"]) for run in synchronous_calibration
    )
    synchronous_final = statistics.median(
        float(run["final_held_out_nll"]) for run in synchronous_calibration
    )
    fraction = float(
        scenario["target"]["calibration_fraction_of_synchronous_improvement"]
    )
    target_loss = initial_loss - fraction * (initial_loss - synchronous_final)
    for run in runs:
        target_tick = _first_target_tick(run, target_loss)
        run["target_held_out_nll"] = target_loss
        run["logical_ticks_to_target"] = target_tick
        run["target_reached"] = target_tick is not None

    evaluation_ids = [
        str(item["stratum_id"]) for item in scenario["evaluation_strata"]
    ]
    tau: list[float] = []
    direct: list[float] = []
    adaptive_retained: list[float] = []
    no_failure_relative_difference: list[float] = []
    adaptive_vs_synchronous: list[float] = []
    adaptive_ticks: list[float] = []
    fixed_ticks: list[float] = []
    paired_rows: list[dict[str, Any]] = []
    for stratum_id in evaluation_ids:
        fixed_clean = lookup[(stratum_id, FIXED_POLICY, False)]
        fixed_interrupted = lookup[(stratum_id, FIXED_POLICY, True)]
        adaptive_clean = lookup[(stratum_id, ADAPTIVE_POLICY, False)]
        adaptive_interrupted = lookup[(stratum_id, ADAPTIVE_POLICY, True)]
        synchronous = lookup[(stratum_id, SYNC_POLICY, False)]
        fc = float(fixed_clean["progress_per_flop"])
        fi = float(fixed_interrupted["progress_per_flop"])
        ac = float(adaptive_clean["progress_per_flop"])
        ai = float(adaptive_interrupted["progress_per_flop"])
        sync = float(synchronous["progress_per_flop"])
        tau_value = (ai - ac) - (fi - fc)
        tau.append(tau_value)
        direct.append(ai - fi)
        adaptive_retained.append(ai / ac if ac else float("-inf"))
        no_failure_relative_difference.append(abs(ac - fc) / abs(fc) if fc else math.inf)
        adaptive_vs_synchronous.append(ai / sync if sync else float("-inf"))
        adaptive_tick = adaptive_interrupted["logical_ticks_to_target"]
        fixed_tick = fixed_interrupted["logical_ticks_to_target"]
        if adaptive_tick is not None:
            adaptive_ticks.append(float(adaptive_tick))
        if fixed_tick is not None:
            fixed_ticks.append(float(fixed_tick))
        paired_rows.append(
            {
                "stratum_id": stratum_id,
                "fixed_no_failure_progress_per_flop": fc,
                "fixed_interrupted_progress_per_flop": fi,
                "adaptive_no_failure_progress_per_flop": ac,
                "adaptive_interrupted_progress_per_flop": ai,
                "synchronous_progress_per_flop": sync,
                "tau": tau_value,
                "direct_interrupted_difference": ai - fi,
                "adaptive_retained_ratio": ai / ac if ac else None,
                "adaptive_vs_synchronous_ratio": ai / sync if sync else None,
                "fixed_ticks_to_target": fixed_tick,
                "adaptive_ticks_to_target": adaptive_tick,
            }
        )

    bootstrap = scenario["bootstrap"]
    confidence_level = float(bootstrap["confidence_level"])
    draws = int(bootstrap["draws"])
    bootstrap_seed = int(bootstrap["seed"])
    tau_interval = _bootstrap_median_interval(
        np,
        tau,
        draws=draws,
        seed=bootstrap_seed,
        confidence_level=confidence_level,
    )
    direct_interval = _bootstrap_median_interval(
        np,
        direct,
        draws=draws,
        seed=bootstrap_seed + 1,
        confidence_level=confidence_level,
    )
    retained_interval = _bootstrap_median_interval(
        np,
        adaptive_retained,
        draws=draws,
        seed=bootstrap_seed + 2,
        confidence_level=confidence_level,
    )
    no_failure_interval = _bootstrap_median_interval(
        np,
        no_failure_relative_difference,
        draws=draws,
        seed=bootstrap_seed + 3,
        confidence_level=confidence_level,
    )
    synchronous_interval = _bootstrap_median_interval(
        np,
        adaptive_vs_synchronous,
        draws=draws,
        seed=bootstrap_seed + 4,
        confidence_level=confidence_level,
    )
    falsifiers = scenario["falsifiers"]
    adaptive_divergence_count = sum(
        1
        for run in runs
        if run["split"] == "evaluation"
        and run["policy_id"] == ADAPTIVE_POLICY
        and bool(run["diverged"])
    )
    fixed_median_ticks = statistics.median(fixed_ticks) if fixed_ticks else None
    adaptive_median_ticks = (
        statistics.median(adaptive_ticks) if adaptive_ticks else None
    )
    gates = {
        "paired_tau_positive": (
            tau_interval["lower_bound"]
            > float(falsifiers["paired_tau_lower_bound_gt"])
        ),
        "adaptive_retains_progress_per_flop": (
            retained_interval["lower_bound"]
            >= float(
                falsifiers[
                    "adaptive_retained_progress_per_flop_ratio_lower_bound_gte"
                ]
            )
        ),
        "no_failure_learning_equivalence": (
            no_failure_interval["upper_bound"]
            <= float(
                falsifiers[
                    "no_failure_policy_progress_per_flop_relative_difference_lte"
                ]
            )
        ),
        "adaptive_vs_synchronous_progress_per_flop": (
            synchronous_interval["lower_bound"]
            >= float(falsifiers["adaptive_progress_per_flop_vs_synchronous_gte"])
        ),
        "adaptive_reaches_target_sooner": (
            adaptive_median_ticks is not None
            and fixed_median_ticks is not None
            and adaptive_median_ticks < fixed_median_ticks
        ),
        "adaptive_does_not_diverge": adaptive_divergence_count
        == int(falsifiers["adaptive_divergence_count_eq"]),
    }
    survives = all(gates.values())
    return {
        "target": {
            "held_out_nll": target_loss,
            "calibration_initial_median_nll": initial_loss,
            "calibration_synchronous_final_median_nll": synchronous_final,
            "fraction_of_synchronous_improvement": fraction,
            "selected_from": [run["run_id"] for run in synchronous_calibration],
        },
        "evaluation_pairs": paired_rows,
        "paired_tau": tau_interval,
        "direct_interrupted_contrast": direct_interval,
        "adaptive_retained_progress_per_flop": retained_interval,
        "no_failure_relative_difference": no_failure_interval,
        "adaptive_vs_synchronous_progress_per_flop": synchronous_interval,
        "fixed_interrupted_median_ticks_to_target": fixed_median_ticks,
        "adaptive_interrupted_median_ticks_to_target": adaptive_median_ticks,
        "adaptive_divergence_count": adaptive_divergence_count,
        "falsifier_results": gates,
        "candidate_survives_lc1": survives,
        "conclusion": (
            "candidate_survives_small_model_calibration"
            if survives
            else "candidate_falsified_small_model_calibration"
        ),
    }


def _bounded_uncertainty(value: float, fraction: float, notes: str) -> MeasurementUncertainty:
    radius = max(abs(value) * fraction, 1e-15)
    return MeasurementUncertainty(
        lower_bound=value - radius,
        upper_bound=value + radius,
        notes=notes,
    )


def _observation(
    run: Mapping[str, Any],
    scenario: Mapping[str, Any],
    dataset_path: Path,
) -> Observation:
    progress = float(run["held_out_loss_progress"])
    loss_std = float(run["final_held_out_nll_standard_deviation"])
    flops = float(run["attempted_compute_flops"])
    seconds = float(run["local_wall_clock_seconds"])
    progress_per_flop = float(run["progress_per_flop"])
    progress_per_second = float(run["progress_per_second"])
    exact = MeasurementUncertainty(
        lower_bound=flops,
        upper_bound=flops,
        notes="Modeled from exact parameter and attempted-token counts using 6*N*T.",
    )
    values: dict[str, MeasuredValue] = {
        "held_out_final_nll": MeasuredValue(
            value=float(run["final_held_out_nll"]),
            unit="natural_log_unit_per_byte",
            uncertainty=MeasurementUncertainty(
                standard_deviation=loss_std,
                notes="Standard deviation across frozen held-out validation batches.",
            ),
        ),
        "held_out_loss_progress": MeasuredValue(
            value=progress,
            unit="natural_log_unit_per_byte",
            uncertainty=MeasurementUncertainty(
                standard_deviation=math.sqrt(2.0) * loss_std,
                notes="Conservative propagation from held-out batch dispersion.",
            ),
        ),
        "attempted_compute_flops": MeasuredValue(
            value=flops,
            unit="FLOP",
            uncertainty=exact,
        ),
        "local_wall_clock_time": MeasuredValue(
            value=seconds,
            unit="second",
            uncertainty=_bounded_uncertainty(
                seconds, 1e-4, "perf_counter timing bound; local serial harness only."
            ),
        ),
        "progress_per_flop": MeasuredValue(
            value=progress_per_flop,
            unit="natural_log_unit_per_byte_per_FLOP",
            uncertainty=_bounded_uncertainty(
                progress_per_flop,
                max(1e-6, loss_std / max(abs(progress), 1e-12)),
                "Derived from held-out loss dispersion and modeled attempted FLOP.",
            ),
        ),
        "progress_per_second": MeasuredValue(
            value=progress_per_second,
            unit="natural_log_unit_per_byte_per_second",
            uncertainty=_bounded_uncertainty(
                progress_per_second,
                max(1e-4, loss_std / max(abs(progress), 1e-12)),
                "Local RTX harness metric, not modeled datacenter time.",
            ),
        ),
    }
    energy = run["energy"]["idle_subtracted_energy_j"]
    if energy is not None and float(energy) > 0.0:
        energy_value = float(energy)
        values["training_device_energy"] = MeasuredValue(
            value=energy_value,
            unit="joule",
            uncertainty=_bounded_uncertainty(
                energy_value,
                0.05,
                "Five-percent instrumentation bound on sampled NVML board power; "
                "idle baseline subtracted.",
            ),
        )
        progress_per_joule = float(run["progress_per_joule"])
        values["progress_per_joule"] = MeasuredValue(
            value=progress_per_joule,
            unit="natural_log_unit_per_byte_per_joule",
            uncertainty=_bounded_uncertainty(
                progress_per_joule,
                max(0.05, loss_std / max(abs(progress), 1e-12)),
                "Derived from held-out loss and sampled device energy.",
            ),
        )
    target_tick = run["logical_ticks_to_target"]
    if target_tick is not None:
        target_value = float(target_tick)
        values["logical_ticks_to_target"] = MeasuredValue(
            value=target_value,
            unit="opportunity_tick",
            uncertainty=MeasurementUncertainty(
                lower_bound=max(0.0, target_value - 32.0),
                upper_bound=target_value,
                notes="Target crossing is interval-censored by 32-tick evaluation cadence.",
            ),
        )
    dataset = scenario["dataset"]
    return Observation(
        observation_id=str(run["run_id"]),
        measured_values=values,
        timestamp=datetime.fromisoformat(str(run["completed_at"]).replace("Z", "+00:00")),
        topology={
            "physical_gpu_count": 1,
            "logical_site_count": 2,
            "gpu": "NVIDIA GeForce RTX 3060 Laptop GPU",
            "execution": "serial logical-site emulation",
        },
        workload={
            "dataset_id": dataset["dataset_id"],
            "dataset_sha256": dataset["sha256"],
            "model": scenario["model"],
            "optimization": scenario["optimization"],
            "stratum_id": run["stratum_id"],
            "failure_schedule": run["failure_schedule"],
        },
        software={
            "framework": "pytorch",
            "engine_id": ENGINE_ID,
        },
        instrumentation={
            "loss": "frozen held-out byte-NLL batches",
            "time": "time.perf_counter",
            "energy": "NVML sampled GPU board power with idle subtraction",
            "flops": "6 * parameter_count * attempted_tokens",
        },
        provenance=Provenance(
            source="GPUSTACK E001-LC1 local measured training run",
            uri=str(dataset["uri"]),
            checksum=f"sha256:{_sha256_file(dataset_path)}",
            retrieved_at=datetime(2026, 7, 12, tzinfo=timezone.utc),
            notes=(
                "Raw dataset stayed outside the repository.",
                "This observation is small-model calibration evidence, not a real "
                "multi-datacenter observation.",
            ),
        ),
        metadata={
            "split": run["split"],
            "policy_id": run["policy_id"],
            "interrupted": run["interrupted"],
            "source_recovery_result_artifact_sha256": scenario[
                "source_recovery_result"
            ]["artifact_sha256"],
        },
    )


def run_e001_learning_calibration(
    scenario_path: str | Path,
    dataset_path: str | Path,
) -> dict[str, Any]:
    """Execute the frozen LC1 matrix and return a content-addressed sidecar."""

    scenario_file = Path(scenario_path)
    scenario = json.loads(scenario_file.read_text(encoding="utf-8"))
    if scenario.get("schema") != "gpu-stack.e001-learning-calibration-scenario.v1":
        raise ValueError("unsupported E001-LC1 scenario schema")
    dataset_file = Path(dataset_path)
    corpora = _load_byte_corpora(dataset_file, scenario["dataset"])
    power_sampler = _PowerSampler()

    strata = tuple(scenario["calibration_strata"]) + tuple(
        scenario["evaluation_strata"]
    )
    arms = tuple(scenario["arms"])
    runs: list[dict[str, Any]] = []
    for stratum_index, stratum in enumerate(strata):
        rotation = stratum_index % len(arms)
        ordered_arms = arms[rotation:] + arms[:rotation]
        for arm in ordered_arms:
            run = _run_arm(scenario, corpora, stratum, arm, power_sampler)
            runs.append(run)
            print(
                "LC1 completed "
                f"{run['run_id']} nll={run['final_held_out_nll']:.6f} "
                f"progress/flop={run['progress_per_flop']:.6e} "
                f"active_s={run['local_wall_clock_seconds']:.2f} "
                f"thermal_pause_s={run['thermal_pause_seconds']:.2f}",
                flush=True,
            )

    summary = _summarize(scenario, runs)
    observations = tuple(_observation(run, scenario, dataset_file) for run in runs)
    split = CalibrationEvaluationSplit.from_ids(
        split_id="e001-lc1-calibration-evaluation-v1",
        calibration_ids=tuple(
            observation.observation_id
            for observation in observations
            if observation.metadata["split"] == "calibration"
        ),
        evaluation_ids=tuple(
            observation.observation_id
            for observation in observations
            if observation.metadata["split"] == "evaluation"
        ),
        metadata={
            "target_selected_from_calibration_only": True,
            "evaluation_strata_frozen_before_execution": True,
        },
    )
    split.validate_observations(observations, require_complete_partition=True)

    source_recovery_path = Path(scenario["source_recovery_result"]["path"])
    source_recovery = json.loads(source_recovery_path.read_text(encoding="utf-8"))
    expected_recovery_hash = scenario["source_recovery_result"]["artifact_sha256"]
    if source_recovery.get("artifact_sha256") != expected_recovery_hash:
        raise ValueError("source recovery result does not match frozen LC1 identity")

    _, _, torch, _, _ = _require_dependencies()
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "experiment_id": "E001-LC1",
        "scenario_id": scenario["scenario_id"],
        "scenario_sha256": _content_hash(scenario),
        "engine": {
            "engine_id": ENGINE_ID,
            "source_sha256": _source_hash(),
        },
        "source_recovery_result": {
            "schema": source_recovery["schema"],
            "artifact_sha256": source_recovery["artifact_sha256"],
            "scenario_hash": source_recovery["scenario_hash"],
            "protocol_hash": source_recovery["protocol_hash"],
            "path": scenario["source_recovery_result"]["path"],
        },
        "dataset": {
            **scenario["dataset"],
            "local_path_not_persisted": True,
            "loaded_train_rows": corpora.train_rows,
            "loaded_validation_rows": corpora.validation_rows,
            "loaded_train_bytes": corpora.train_bytes,
            "loaded_validation_bytes": corpora.validation_bytes,
        },
        "runtime": {
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0),
            "gpu_compute_capability": list(torch.cuda.get_device_capability(0)),
            "nvml_power_available": power_sampler.available,
            "idle_power_w": power_sampler.idle_power_w,
        },
        "study": {
            "model": scenario["model"],
            "optimization": scenario["optimization"],
            "calibration_strata": scenario["calibration_strata"],
            "evaluation_strata": scenario["evaluation_strata"],
            "arms": scenario["arms"],
            "falsifiers": scenario["falsifiers"],
        },
        "split": split.to_dict(),
        "runs": runs,
        "observations": [observation.to_dict() for observation in observations],
        "summary": summary,
        "result_scope": {
            "overall_e001_status": "inconclusive_frontier_hypothesis",
            "supported": [
                "measured byte-level TinyStories held-out learning response",
                "paired interruption effect across six frozen evaluation strata",
                "local RTX harness time and sampled device energy",
            ],
            "unsupported": [
                "frontier-scale convergence or capability",
                "real multi-site speedup, WAN, or facility energy",
                "failure detector, hybrid parallelism, or migration performance",
                "transfer beyond the frozen model, dataset, optimizer, and failures",
            ],
        },
    }
    payload["artifact_sha256"] = _content_hash(payload)
    return payload


__all__ = [
    "ADAPTIVE_POLICY",
    "ENGINE_ID",
    "FIXED_POLICY",
    "SCHEMA",
    "SYNC_POLICY",
    "run_e001_learning_calibration",
]
