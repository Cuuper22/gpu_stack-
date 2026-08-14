"""E002-PW1: the checkpoint-cadence x survivor-continuation power experiment.

This runner keeps the LC3 learning frontier fixed on purpose; its new
information is causal. It crosses checkpoint cadence with failure behavior
in a 2x2 factorial and attributes one continuous local GPU-board power
trace to exclusive execution phases, asking which factor drives the energy
cost. Facility-level quantities remain an explicitly modeled bridge, not a
measurement.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import threading
import time
from typing import Any, Iterator, Mapping, Sequence

from . import e001_lc2_quality_target as lc2
from . import e001_lc3_equal_work as lc3
from . import e001_learning_calibration as lc1


SCHEMA = "gpu-stack.e002-checkpoint-power-evidence.v1"
ENGINE_ID = "gpu-stack.e002-pw1-checkpoint-power.v1"

RESTART = "restart"
CONTINUE = "continue"
SPARSE = "sparse"
DENSE = "dense"

PHASES = (
    "canonical-healthy-compute",
    "replay-compute",
    "survivor-redistributed-compute",
    "model-optimizer-merge",
    "checkpoint-snapshot",
    "checkpoint-restore",
    "rejoin-state-transfer",
    "post-rejoin-sync",
    "runtime-control-remainder",
)


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
    canonical_bytes = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(canonical_bytes).hexdigest()


def _matches_source_hash(path: Path, expected: str) -> bool:
    raw = hashlib.sha256(path.read_bytes()).hexdigest()
    normalized = _file_hash(path)
    return expected in {raw, normalized}


def _engine_identity() -> dict[str, Any]:
    components = {
        "checkpoint_power_engine": _file_hash(Path(__file__)),
        "equal_work_runtime": _file_hash(Path(lc3.__file__)),
        "quality_target_runtime": _file_hash(Path(lc2.__file__)),
        "learning_runtime": _file_hash(Path(lc1.__file__)),
    }
    return {
        "engine_id": ENGINE_ID,
        "source_sha256": components["checkpoint_power_engine"],
        "component_source_sha256": components,
        "bundle_sha256": hashlib.sha256(
            _canonical_json(components).encode("utf-8")
        ).hexdigest(),
    }


class _TraceSampler:
    """Poll the locally exposed NVML board signals on a monotonic clock."""

    def __init__(self, poll_seconds: float) -> None:
        self.poll_seconds = poll_seconds
        self.available = False
        self._pynvml = None
        self._handle = None
        self._samples: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        try:
            import pynvml

            pynvml.nvmlInit()
            self._pynvml = pynvml
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self.available = True
        except Exception:
            self.available = False

    def _safe(self, callback) -> int | float | None:
        try:
            return callback()
        except Exception:
            return None

    def _read(self) -> dict[str, Any]:
        assert self._pynvml is not None and self._handle is not None
        pynvml = self._pynvml
        handle = self._handle
        utilization = self._safe(
            lambda: pynvml.nvmlDeviceGetUtilizationRates(handle)
        )
        return {
            "timestamp": time.perf_counter(),
            "power_w": self._safe(
                lambda: float(pynvml.nvmlDeviceGetPowerUsage(handle)) / 1000.0
            ),
            "gpu_utilization_percent": (
                int(utilization.gpu) if utilization is not None else None
            ),
            "memory_utilization_percent": (
                int(utilization.memory) if utilization is not None else None
            ),
            "sm_clock_mhz": self._safe(
                lambda: int(
                    pynvml.nvmlDeviceGetClockInfo(
                        handle, pynvml.NVML_CLOCK_SM
                    )
                )
            ),
            "memory_clock_mhz": self._safe(
                lambda: int(
                    pynvml.nvmlDeviceGetClockInfo(
                        handle, pynvml.NVML_CLOCK_MEM
                    )
                )
            ),
            "temperature_c": self._safe(
                lambda: int(
                    pynvml.nvmlDeviceGetTemperature(
                        handle, pynvml.NVML_TEMPERATURE_GPU
                    )
                )
            ),
            "pstate": self._safe(
                lambda: int(pynvml.nvmlDeviceGetPowerState(handle))
            ),
        }

    def temperature_c(self) -> int | None:
        if not self.available:
            return None
        value = self._read()["temperature_c"]
        return int(value) if value is not None else None

    def power_configuration(self) -> dict[str, Any]:
        if not self.available:
            return {"nvml_available": False}
        assert self._pynvml is not None and self._handle is not None
        pynvml = self._pynvml
        handle = self._handle
        name = self._safe(lambda: pynvml.nvmlDeviceGetName(handle))
        if isinstance(name, bytes):
            name = name.decode("utf-8", errors="replace")
        return {
            "nvml_available": True,
            "device_name": name,
            "power_management_limit_w": self._safe(
                lambda: float(
                    pynvml.nvmlDeviceGetPowerManagementLimit(handle)
                )
                / 1000.0
            ),
            "power_management_default_limit_w": self._safe(
                lambda: float(
                    pynvml.nvmlDeviceGetPowerManagementDefaultLimit(handle)
                )
                / 1000.0
            ),
        }

    def wait_until_temperature(
        self, threshold_c: int, *, poll_seconds: float
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
                point = self._read()
                if point["power_w"] is not None:
                    self._samples.append(point)
                self._stop.wait(self.poll_seconds)

        self._thread = threading.Thread(target=sample, daemon=True)
        self._thread.start()

    def stop(self) -> tuple[dict[str, Any], ...]:
        if not self.available:
            return ()
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        return tuple(self._samples)


class _PhaseTraceMeter:
    """Record one continuous trace and CUDA-bracketed exclusive phases."""

    def __init__(self, torch, sampler: _TraceSampler) -> None:
        self.torch = torch
        self.sampler = sampler
        self.trace_started = 0.0
        self.active_started = 0.0
        self.active_ended = 0.0
        self.windows: list[dict[str, Any]] = []

    def start(self, pre_idle_seconds: float) -> None:
        self.torch.cuda.synchronize()
        self.trace_started = time.perf_counter()
        self.sampler.start()
        time.sleep(pre_idle_seconds)
        self.torch.cuda.synchronize()
        self.active_started = time.perf_counter()

    @contextmanager
    def phase(self, phase: str) -> Iterator[None]:
        if phase not in PHASES or phase == "runtime-control-remainder":
            raise ValueError(f"unsupported explicit E002 phase {phase!r}")
        self.torch.cuda.synchronize()
        started = time.perf_counter()
        try:
            yield
        finally:
            self.torch.cuda.synchronize()
            ended = time.perf_counter()
            self.windows.append(
                {"phase": phase, "start": started, "end": ended}
            )

    def stop(self, post_idle_seconds: float) -> dict[str, Any]:
        self.torch.cuda.synchronize()
        self.active_ended = time.perf_counter()
        time.sleep(post_idle_seconds)
        samples = self.sampler.stop()
        origin = self.trace_started
        return {
            "available": self.sampler.available,
            "poll_seconds": self.sampler.poll_seconds,
            "active_start_seconds": self.active_started - origin,
            "active_end_seconds": self.active_ended - origin,
            "points": [
                {
                    **point,
                    "timestamp": float(point["timestamp"]) - origin,
                    "monotonic_ns": int(
                        (float(point["timestamp"]) - origin) * 1_000_000_000
                    ),
                    "gpu_board_power_w": point["power_w"],
                    "performance_state": point["pstate"],
                }
                for point in samples
            ],
            "phase_windows": [
                {
                    "phase": window["phase"],
                    "start_seconds": float(window["start"]) - origin,
                    "end_seconds": float(window["end"]) - origin,
                }
                for window in self.windows
            ],
        }


def _baseline_at(
    timestamp: float,
    active_start: float,
    active_end: float,
    pre_idle_power: float,
    post_idle_power: float,
) -> float:
    if active_end <= active_start:
        return pre_idle_power
    fraction = min(
        1.0,
        max(0.0, (timestamp - active_start) / (active_end - active_start)),
    )
    return pre_idle_power + fraction * (post_idle_power - pre_idle_power)


def _interpolate(
    left_t: float,
    left_value: float,
    right_t: float,
    right_value: float,
    timestamp: float,
) -> float:
    if right_t <= left_t:
        return left_value
    fraction = (timestamp - left_t) / (right_t - left_t)
    return left_value + fraction * (right_value - left_value)


def _analyze_trace(
    trace: Mapping[str, Any], *, logger_lag_seconds: float
) -> dict[str, Any]:
    points = tuple(trace["points"])
    active_start = float(trace["active_start_seconds"])
    active_end = float(trace["active_end_seconds"])
    pre = [
        float(point["power_w"])
        for point in points
        if float(point["timestamp"]) < active_start
    ]
    post = [
        float(point["power_w"])
        for point in points
        if float(point["timestamp"]) > active_end
    ]
    pre_idle = statistics.fmean(pre) if pre else None
    post_idle = statistics.fmean(post) if post else None
    raw_windows = [
        {
            "phase": str(window["phase"]),
            "start": float(window["start_seconds"]),
            "end": float(window["end_seconds"]),
        }
        for window in trace["phase_windows"]
    ]
    raw_windows.sort(key=lambda value: (value["start"], value["end"]))
    windows = [
        {
            "phase": str(window["phase"]),
            "start": float(window["start_seconds"]) + logger_lag_seconds,
            "end": float(window["end_seconds"]) + logger_lag_seconds,
        }
        for window in trace["phase_windows"]
    ]
    windows.sort(key=lambda value: (value["start"], value["end"]))
    overlap_seconds = sum(
        max(0.0, float(left["end"]) - float(right["start"]))
        for left, right in zip(raw_windows, raw_windows[1:])
    )
    outside_seconds = sum(
        max(0.0, active_start - float(window["start"]))
        + max(0.0, float(window["end"]) - active_end)
        for window in raw_windows
    )
    energies = {phase: 0.0 for phase in PHASES}
    durations = {phase: 0.0 for phase in PHASES}
    raw_energy = 0.0
    residual_energy = 0.0
    if pre_idle is not None and post_idle is not None:
        for left, right in zip(points, points[1:]):
            left_t = float(left["timestamp"])
            right_t = float(right["timestamp"])
            start = max(left_t, active_start)
            end = min(right_t, active_end)
            if end <= start:
                continue
            left_power = _interpolate(
                left_t,
                float(left["power_w"]),
                right_t,
                float(right["power_w"]),
                start,
            )
            right_power = _interpolate(
                left_t,
                float(left["power_w"]),
                right_t,
                float(right["power_w"]),
                end,
            )
            duration = end - start
            raw_segment = 0.5 * (left_power + right_power) * duration
            residual_segment = 0.5 * (
                left_power
                - _baseline_at(
                    start,
                    active_start,
                    active_end,
                    pre_idle,
                    post_idle,
                )
                + right_power
                - _baseline_at(
                    end,
                    active_start,
                    active_end,
                    pre_idle,
                    post_idle,
                )
            ) * duration
            raw_energy += raw_segment
            residual_energy += residual_segment
            covered = 0.0
            for window in windows:
                overlap = max(
                    0.0,
                    min(end, float(window["end"]))
                    - max(start, float(window["start"])),
                )
                if overlap <= 0.0:
                    continue
                phase = str(window["phase"])
                covered += overlap
                durations[phase] += overlap
                energies[phase] += residual_segment * overlap / duration
            remainder = max(0.0, duration - covered)
            durations["runtime-control-remainder"] += remainder
            energies["runtime-control-remainder"] += (
                residual_segment * remainder / duration
            )
    attributed = sum(energies.values())
    closure = abs(attributed - residual_energy) / max(
        1e-9, abs(residual_energy)
    )
    return {
        "logger_lag_seconds": logger_lag_seconds,
        "sample_count": len(points),
        "pre_idle_sample_count": len(pre),
        "post_idle_sample_count": len(post),
        "pre_idle_power_w": pre_idle,
        "post_idle_power_w": post_idle,
        "raw_active_energy_j": raw_energy if points else None,
        "total_idle_subtracted_energy_j": (
            residual_energy if pre_idle is not None and post_idle is not None else None
        ),
        "phase_idle_subtracted_energy_j": energies,
        "phase_duration_seconds": durations,
        "attributed_idle_subtracted_energy_j": attributed,
        "energy_closure_relative_error": closure,
        "exclusive_phase_overlap_seconds": overlap_seconds,
        "phase_outside_active_window_seconds": outside_seconds,
        "phase_partition_valid": overlap_seconds <= 1e-9
        and outside_seconds <= 1e-6,
    }


def _pearson(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) < 3 or len(left) != len(right):
        return float("-inf")
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    numerator = sum(
        (a - left_mean) * (b - right_mean)
        for a, b in zip(left, right, strict=True)
    )
    left_scale = math.sqrt(sum((value - left_mean) ** 2 for value in left))
    right_scale = math.sqrt(sum((value - right_mean) ** 2 for value in right))
    if left_scale <= 0.0 or right_scale <= 0.0:
        return float("-inf")
    return numerator / (left_scale * right_scale)


def _estimate_logger(
    calibration_runs: Sequence[Mapping[str, Any]],
    scenario: Mapping[str, Any],
) -> dict[str, Any]:
    poll_seconds = float(
        scenario["telemetry"]["requested_sample_interval_ms"]
    ) / 1000.0
    maximum_lag = float(
        scenario["telemetry"]["logger_calibration"][
            "maximum_absolute_logger_delay_ms"
        ]
    ) / 1000.0
    candidate_steps = int(maximum_lag // poll_seconds)
    candidates = tuple(
        sorted(
            {
                -maximum_lag,
                0.0,
                maximum_lag,
                *(
                    index * poll_seconds
                    for index in range(-candidate_steps, candidate_steps + 1)
                ),
            }
        )
    )
    correlations: list[dict[str, float]] = []
    for candidate in candidates:
        indicators: list[float] = []
        residuals: list[float] = []
        for run in calibration_runs:
            trace = run["telemetry_trace"]
            points = tuple(trace["points"])
            active_start = float(trace["active_start_seconds"])
            active_end = float(trace["active_end_seconds"])
            pre = [
                float(point["power_w"])
                for point in points
                if float(point["timestamp"]) < active_start
            ]
            post = [
                float(point["power_w"])
                for point in points
                if float(point["timestamp"]) > active_end
            ]
            if not pre or not post:
                continue
            pre_idle = statistics.fmean(pre)
            post_idle = statistics.fmean(post)
            windows = tuple(
                (
                    float(window["start_seconds"]) + candidate,
                    float(window["end_seconds"]) + candidate,
                )
                for window in trace["phase_windows"]
            )
            for point in points:
                timestamp = float(point["timestamp"])
                indicators.append(
                    1.0
                    if any(start <= timestamp <= end for start, end in windows)
                    else 0.0
                )
                residuals.append(
                    float(point["power_w"])
                    - _baseline_at(
                        timestamp,
                        active_start,
                        active_end,
                        pre_idle,
                        post_idle,
                    )
                )
        correlations.append(
            {"lag_seconds": candidate, "correlation": _pearson(indicators, residuals)}
        )
    selected = max(correlations, key=lambda row: row["correlation"])
    update_gaps: list[float] = []
    threshold = float(
        scenario["telemetry"].get(
            "effective_power_change_threshold_w", 0.05
        )
    )
    for run in calibration_runs:
        points = tuple(run["telemetry_trace"]["points"])
        previous_change: float | None = None
        for left, right in zip(points, points[1:]):
            if abs(float(right["power_w"]) - float(left["power_w"])) < threshold:
                continue
            timestamp = float(right["timestamp"])
            if previous_change is not None:
                update_gaps.append(timestamp - previous_change)
            previous_change = timestamp
    effective_period = (
        statistics.median(update_gaps)
        if update_gaps
        else poll_seconds
    )
    return {
        "selected_lag_seconds": selected["lag_seconds"],
        "selected_correlation": selected["correlation"],
        "candidate_correlations": correlations,
        "effective_update_period_seconds": effective_period,
        "effective_update_gap_count": len(update_gaps),
        "calibration_strata": sorted(
            {str(run["stratum_id"]) for run in calibration_runs}
        ),
        "frozen_before_evaluation": True,
    }


def _run_arm(
    scenario: Mapping[str, Any],
    corpora: Any,
    warm_checkpoint: Any,
    stratum: Mapping[str, Any],
    arm: Mapping[str, Any],
    sampler: _TraceSampler,
    *,
    split: str,
) -> dict[str, Any]:
    _, _, torch, nn, functional = lc1._require_dependencies()
    device = torch.device("cuda:0")
    optimization = scenario["optimization"]
    model_config = scenario["model"]
    seed = int(stratum["seed"])
    cadence = str(arm["checkpoint_cadence"])
    continuation = str(arm["survivor_continuation"])
    arm_id = str(arm["arm_id"])
    if cadence not in {SPARSE, DENSE}:
        raise ValueError(f"unknown checkpoint cadence {cadence!r}")
    if continuation not in {RESTART, CONTINUE}:
        raise ValueError(f"unknown continuation level {continuation!r}")
    cadence_level = scenario["factors"]["checkpoint_cadence"]["levels"][cadence]
    site_a, site_b, evaluation_model = lc2._site_pair(
        torch,
        nn,
        functional,
        scenario,
        device,
        seed=seed,
        checkpoint=warm_checkpoint,
    )
    parameter_count = sum(
        parameter.numel() for parameter in site_a.model.parameters()
    )
    batch_size = int(optimization["batch_size_per_site"])
    context_length = int(model_config["context_length"])
    tokens_per_quota = batch_size * context_length
    canonical_target_ticks = int(
        scenario["canonical_work"]["target_logical_ticks"]
    )
    maximum_opportunity_ticks = int(
        scenario["canonical_work"]["maximum_opportunity_ticks"]
    )
    healthy_local_ticks = int(optimization["healthy_merge_ticks"])
    healthy_checkpoint_interval = int(
        cadence_level["checkpoint_every_eligible_merges"]
    )
    reduced_checkpoint_ticks = int(
        cadence_level["effective_reduced_membership_checkpoint_ticks"]
    )
    failures = tuple(tuple(item) for item in stratum["failures"])

    logical_tick = 0
    merge_count = 0
    steps_since_merge = 0
    post_rejoin_remaining = 0
    attempted_tokens = 0
    replayed_tokens = 0
    discarded_tokens = 0
    survivor_redistributed_tokens = 0
    seen_quotas: set[tuple[str, int]] = set()
    training_losses: list[float] = []
    checkpoint_count = 0
    checkpoint_bytes = 0
    checkpoint_copy_seconds = 0.0
    restore_seconds = 0.0
    rejoin_seconds = 0.0
    divergence = False
    target_reached = False
    elapsed_wall_ticks = 0
    thermal_limit_crossed = False
    latest_checkpoint = None

    def train_quota(site: Any, site_id: str, quota_tick: int) -> float:
        nonlocal attempted_tokens, replayed_tokens
        identity = (site_id, quota_tick)
        if identity in seen_quotas:
            replayed_tokens += tokens_per_quota
        else:
            seen_quotas.add(identity)
        loss = lc2._quota(
            torch,
            functional,
            scenario,
            corpora,
            site,
            seed=seed,
            site_id=site_id,
            logical_tick=quota_tick,
            device=device,
        )
        attempted_tokens += tokens_per_quota
        return loss

    def measure() -> tuple[float, float, list[float]]:
        lc1._load_evaluation_state(torch, evaluation_model, site_a, site_b)
        return lc1._evaluate(
            torch,
            functional,
            evaluation_model,
            corpora.validation,
            seed=int(optimization["validation_seed"]),
            batch_size=batch_size,
            context_length=context_length,
            validation_batches=int(optimization["validation_batches"]),
            device=device,
            autocast_dtype=torch.bfloat16,
        )

    initial_mean, initial_sd, initial_losses = measure()
    thermal = scenario["thermal_guard"]
    cooldown = sampler.wait_until_temperature(
        int(thermal["arm_start_temperature_c_lte"]),
        poll_seconds=float(thermal["poll_seconds"]),
    )
    start_temperature = sampler.temperature_c()
    power_configuration_start = sampler.power_configuration()
    meter = _PhaseTraceMeter(torch, sampler)
    meter.start(
        float(
            scenario["telemetry"]["idle_baseline"][
                "pre_run_plateau_seconds"
            ]
        )
    )

    with meter.phase("checkpoint-snapshot"):
        checkpoint_started = time.perf_counter()
        latest_checkpoint = lc1._checkpoint(site_a, 0, 0)
        checkpoint_copy_seconds += time.perf_counter() - checkpoint_started
    checkpoint_count += 1
    checkpoint_bytes += latest_checkpoint.checkpoint_bytes

    def take_checkpoint(source: Any) -> None:
        nonlocal latest_checkpoint, checkpoint_count, checkpoint_bytes
        nonlocal checkpoint_copy_seconds
        with meter.phase("checkpoint-snapshot"):
            started = time.perf_counter()
            latest_checkpoint = lc1._checkpoint(
                source, logical_tick, merge_count
            )
            checkpoint_copy_seconds += time.perf_counter() - started
        checkpoint_count += 1
        checkpoint_bytes += latest_checkpoint.checkpoint_bytes

    for wall_tick in range(maximum_opportunity_ticks):
        if logical_tick >= canonical_target_ticks:
            target_reached = True
            break
        active, starts, ends = lc1._failure_at_tick(failures, wall_tick)
        if ends and continuation == CONTINUE:
            with meter.phase("rejoin-state-transfer"):
                started = time.perf_counter()
                lc1._copy_site(site_b, site_a)
                rejoin_seconds += time.perf_counter() - started
            steps_since_merge = 0
            post_rejoin_remaining = int(
                optimization["post_rejoin_sync_ticks"]
            )
        if starts and continuation == RESTART:
            assert latest_checkpoint is not None
            rolled_back_ticks = max(
                0, logical_tick - latest_checkpoint.logical_tick
            )
            discarded_tokens += rolled_back_ticks * 2 * tokens_per_quota
            with meter.phase("checkpoint-restore"):
                started = time.perf_counter()
                lc1._restore(site_a, latest_checkpoint)
                lc1._restore(site_b, latest_checkpoint)
                restore_seconds += time.perf_counter() - started
            logical_tick = latest_checkpoint.logical_tick
            merge_count = latest_checkpoint.merge_count
            steps_since_merge = 0

        if continuation == RESTART and active:
            pass
        elif continuation == CONTINUE and active:
            with meter.phase("survivor-redistributed-compute"):
                training_losses.append(
                    train_quota(site_b, "site-a", logical_tick)
                )
                training_losses.append(
                    train_quota(site_b, "site-b", logical_tick)
                )
            survivor_redistributed_tokens += tokens_per_quota
            logical_tick += 1
            steps_since_merge += 1
            if steps_since_merge >= reduced_checkpoint_ticks:
                merge_count += 1
                steps_since_merge = 0
                take_checkpoint(site_b)
        else:
            replay = (
                ("site-a", logical_tick) in seen_quotas
                or ("site-b", logical_tick) in seen_quotas
            )
            phase = "replay-compute" if replay else "canonical-healthy-compute"
            with meter.phase(phase):
                training_losses.append(
                    train_quota(site_a, "site-a", logical_tick)
                )
                training_losses.append(
                    train_quota(site_b, "site-b", logical_tick)
                )
            logical_tick += 1
            steps_since_merge += 1
            local_cadence = healthy_local_ticks
            if post_rejoin_remaining > 0:
                local_cadence = 1
            if steps_since_merge >= local_cadence:
                merge_phase = (
                    "post-rejoin-sync"
                    if post_rejoin_remaining > 0
                    else "model-optimizer-merge"
                )
                with meter.phase(merge_phase):
                    lc1._average_sites(torch, site_a, site_b)
                merge_count += 1
                steps_since_merge = 0
                if post_rejoin_remaining > 0:
                    post_rejoin_remaining -= 1
                if merge_count % healthy_checkpoint_interval == 0:
                    take_checkpoint(site_a)

        elapsed_wall_ticks = wall_tick + 1
        if any(not math.isfinite(value) for value in training_losses[-2:]):
            divergence = True
            break
        if elapsed_wall_ticks % healthy_local_ticks == 0:
            temperature = sampler.temperature_c()
            if (
                temperature is not None
                and temperature >= int(thermal["pause_temperature_c_gte"])
            ):
                thermal_limit_crossed = True
                break

    if logical_tick >= canonical_target_ticks:
        target_reached = True
    trace = meter.stop(
        float(
            scenario["telemetry"]["idle_baseline"][
                "post_run_plateau_seconds"
            ]
        )
    )
    physical_seconds = float(trace["active_end_seconds"]) - float(
        trace["active_start_seconds"]
    )
    final_mean, final_sd, final_losses = measure()
    final_checkpoint = lc1._checkpoint(site_a, logical_tick, merge_count)
    canonical_tokens = logical_tick * 2 * tokens_per_quota
    return {
        "run_id": f"e002-pw1:{stratum['block_id']}:{arm_id}",
        "stratum_id": str(stratum["block_id"]),
        "block_id": str(stratum["block_id"]),
        "split": split,
        "seed": seed,
        "arm_id": arm_id,
        "arm_code": str(arm["arm_code"]),
        "checkpoint_cadence": cadence,
        "continuation": continuation,
        "failure_schedule": [list(item) for item in failures],
        "interrupted": bool(failures),
        "warm_checkpoint_sha256": lc2._checkpoint_hash(warm_checkpoint),
        "final_training_state_sha256": lc2._checkpoint_hash(final_checkpoint),
        "parameter_count": parameter_count,
        "canonical_target_ticks": canonical_target_ticks,
        "target_reached": target_reached,
        "opportunity_ticks_to_target": (
            elapsed_wall_ticks if target_reached else None
        ),
        "logical_ticks_completed": logical_tick,
        "initial_held_out_nll": initial_mean,
        "initial_held_out_nll_standard_deviation": initial_sd,
        "initial_validation_batch_nll": list(initial_losses),
        "final_held_out_nll": final_mean,
        "final_held_out_nll_standard_deviation": final_sd,
        "final_validation_batch_nll": list(final_losses),
        "attempted_tokens": attempted_tokens,
        "canonical_tokens": canonical_tokens,
        "replayed_tokens": replayed_tokens,
        "discarded_tokens": discarded_tokens,
        "survivor_redistributed_tokens": survivor_redistributed_tokens,
        "attempted_compute_flops": 6.0 * parameter_count * attempted_tokens,
        "canonical_compute_flops": 6.0 * parameter_count * canonical_tokens,
        "checkpoint_count": checkpoint_count,
        "checkpoint_bytes": checkpoint_bytes,
        "checkpoint_copy_seconds": checkpoint_copy_seconds,
        "restore_seconds": restore_seconds,
        "rejoin_seconds": rejoin_seconds,
        "local_active_seconds": physical_seconds,
        "cooldown_before_seconds": cooldown,
        "start_temperature_c": start_temperature,
        "end_temperature_c": sampler.temperature_c(),
        "power_configuration_start": power_configuration_start,
        "power_configuration_end": sampler.power_configuration(),
        "thermal_limit_crossed": thermal_limit_crossed,
        "diverged": divergence,
        "telemetry_trace": trace,
        "completed_at": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    }


def _interval(
    np,
    values: Sequence[float],
    scenario: Mapping[str, Any],
    seed_offset: int,
) -> dict[str, Any]:
    interval = scenario["estimands"]["paired_interval"]
    if not values:
        return {
            "values": [],
            "median": None,
            "lower_bound": None,
            "upper_bound": None,
            "confidence_level": float(
                interval["confidence_level"]
            ),
            "draws": int(interval["draws"]),
            "method": "not computed because no complete paired values exist",
        }
    return lc1._bootstrap_median_interval(
        np,
        values,
        draws=int(interval["draws"]),
        seed=int(interval["seed"]) + seed_offset,
        confidence_level=float(interval["confidence_level"]),
    )


def _arm_key(cadence: str, continuation: str) -> tuple[str, str]:
    return cadence, continuation


def _attach_attribution(
    run: dict[str, Any],
    logger_calibration: Mapping[str, Any],
    scenario: Mapping[str, Any],
) -> None:
    lag = float(logger_calibration["selected_lag_seconds"])
    effective_period = max(
        1e-9,
        float(logger_calibration["effective_update_period_seconds"]),
    )
    trace = run["telemetry_trace"]
    attribution = _analyze_trace(trace, logger_lag_seconds=lag)
    threshold = float(
        scenario["telemetry"].get(
            "effective_power_change_threshold_w", 0.05
        )
    )
    active_start = float(trace["active_start_seconds"])
    active_end = float(trace["active_end_seconds"])
    active_points = [
        point
        for point in trace["points"]
        if active_start <= float(point["timestamp"]) <= active_end
    ]
    effective_updates = 1 if active_points else 0
    for left, right in zip(active_points, active_points[1:]):
        if abs(float(right["power_w"]) - float(left["power_w"])) >= threshold:
            effective_updates += 1
    phase_metrics = {
        phase: {
            "duration_seconds": float(
                attribution["phase_duration_seconds"][phase]
            ),
            "idle_subtracted_energy_j": float(
                attribution["phase_idle_subtracted_energy_j"][phase]
            ),
            "idle_subtracted_energy_j_per_canonical_token": float(
                attribution["phase_idle_subtracted_energy_j"][phase]
            )
            / max(1.0, float(run["canonical_tokens"])),
            "pooled_effective_update_equivalents": float(
                attribution["phase_duration_seconds"][phase]
            )
            / effective_period,
        }
        for phase in PHASES
    }
    run.update(
        {
            "raw_trace_sha256": _content_hash(trace),
            "raw_sample_count": int(attribution["sample_count"]),
            "effective_power_update_count": effective_updates,
            "phase_intervals": trace["phase_windows"],
            "phase_metrics": phase_metrics,
            "phase_energy_closure_relative_error": float(
                attribution["energy_closure_relative_error"]
            ),
            "total_gpu_board_energy_j": attribution["raw_active_energy_j"],
            "idle_subtracted_gpu_board_energy_j": attribution[
                "total_idle_subtracted_energy_j"
            ],
            "phase_partition_valid": bool(
                attribution["phase_partition_valid"]
            ),
            "phase_overlap_seconds": float(
                attribution["exclusive_phase_overlap_seconds"]
            ),
            "phase_outside_run_seconds": float(
                attribution["phase_outside_active_window_seconds"]
            ),
            "idle_baseline": {
                "pre_power_w": attribution["pre_idle_power_w"],
                "post_power_w": attribution["post_idle_power_w"],
                "pre_sample_count": attribution["pre_idle_sample_count"],
                "post_sample_count": attribution["post_idle_sample_count"],
            },
            "logger_delay_ms": lag * 1000.0,
        }
    )


def _summarize(
    scenario: Mapping[str, Any],
    calibration_runs: Sequence[Mapping[str, Any]],
    evaluation_runs: Sequence[Mapping[str, Any]],
    logger_calibration: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    np, _, _, _, _ = lc1._require_dependencies()
    calibration_lookup = {
        (str(run["block_id"]), str(run["arm_code"])): run
        for run in calibration_runs
    }
    calibration_equivalence: list[dict[str, Any]] = []
    calibration_state_equal = True
    calibration_work_equal = True
    calibration_nll_equal = True
    for block in scenario["splits"]["calibration"]["blocks"]:
        block_id = str(block["block_id"])
        for cadence, restart_code, continue_code in (
            (SPARSE, "A", "C"),
            (DENSE, "B", "D"),
        ):
            restart = calibration_lookup[(block_id, restart_code)]
            continuation = calibration_lookup[(block_id, continue_code)]
            state_equal = (
                restart["final_training_state_sha256"]
                == continuation["final_training_state_sha256"]
            )
            work_equal = all(
                restart[key] == continuation[key]
                for key in (
                    "attempted_tokens",
                    "canonical_tokens",
                    "opportunity_ticks_to_target",
                    "checkpoint_count",
                    "checkpoint_bytes",
                )
            )
            nll_equal = (
                restart["final_held_out_nll"]
                == continuation["final_held_out_nll"]
            )
            calibration_state_equal &= state_equal
            calibration_work_equal &= work_equal
            calibration_nll_equal &= nll_equal
            calibration_equivalence.append(
                {
                    "block_id": block_id,
                    "checkpoint_cadence": cadence,
                    "state_exactly_equal": state_equal,
                    "work_exactly_equal": work_equal,
                    "final_nll_exactly_equal": nll_equal,
                }
            )

    lookup = {
        (str(run["block_id"]), str(run["arm_code"])): run
        for run in evaluation_runs
    }
    interactions: list[dict[str, Any]] = []
    total_interactions: list[float] = []
    phase_interaction_values = {phase: [] for phase in PHASES}
    checkpoint_interactions: list[float] = []
    scale_free: list[float] = []
    removed_fractions: list[float] = []
    salvage_nll: list[float] = []
    salvage_work: list[float] = []
    salvage_ticks: list[float] = []
    salvage_energy_ratio: list[float] = []
    lc3_corner_energy_ratio: list[float] = []
    continuation_earlier = 0
    complete_salvage_pairs = 0
    checkpoint_phases = tuple(
        scenario["estimands"]["checkpoint_related_phases"]
    )
    for block in scenario["splits"]["evaluation"]["blocks"]:
        block_id = str(block["block_id"])
        arm_runs = {code: lookup[(block_id, code)] for code in "ABCD"}
        energies = {
            code: float(run["idle_subtracted_gpu_board_energy_j"])
            / max(1.0, float(run["canonical_tokens"]))
            for code, run in arm_runs.items()
        }
        phase_effects: dict[str, float] = {}
        for phase in PHASES:
            values = {
                code: float(run["phase_metrics"][phase][
                    "idle_subtracted_energy_j_per_canonical_token"
                ])
                for code, run in arm_runs.items()
            }
            effect = (values["D"] - values["C"]) - (
                values["B"] - values["A"]
            )
            phase_effects[phase] = effect
            phase_interaction_values[phase].append(effect)
        total = (energies["D"] - energies["C"]) - (
            energies["B"] - energies["A"]
        )
        checkpoint_total = sum(phase_effects[phase] for phase in checkpoint_phases)
        ratio_of_ratios = None
        if all(energies[code] > 0.0 for code in "ABCD"):
            ratio_of_ratios = math.log(energies["D"] / energies["C"]) - math.log(
                energies["B"] / energies["A"]
            )
            scale_free.append(ratio_of_ratios)
        excess = energies["D"] - energies["A"]
        removed_fraction = None
        if excess > 0.0:
            removed_fraction = (energies["D"] - energies["C"]) / excess
            removed_fractions.append(removed_fraction)
        total_interactions.append(total)
        checkpoint_interactions.append(checkpoint_total)

        restart = arm_runs["A"]
        continuation = arm_runs["C"]
        complete = bool(restart["target_reached"] and continuation["target_reached"])
        nll_delta = None
        work_saving = None
        tick_saving = None
        energy_ratio = None
        if complete:
            complete_salvage_pairs += 1
            nll_delta = float(continuation["final_held_out_nll"]) - float(
                restart["final_held_out_nll"]
            )
            salvage_nll.append(nll_delta)
            fixed_work = float(restart["attempted_compute_flops"])
            work_saving = (
                fixed_work - float(continuation["attempted_compute_flops"])
            ) / fixed_work
            salvage_work.append(work_saving)
            tick_saving = float(restart["opportunity_ticks_to_target"]) - float(
                continuation["opportunity_ticks_to_target"]
            )
            salvage_ticks.append(tick_saving)
            if tick_saving > 0.0:
                continuation_earlier += 1
            restart_energy = float(
                restart["idle_subtracted_gpu_board_energy_j"]
            )
            continuation_energy = float(
                continuation["idle_subtracted_gpu_board_energy_j"]
            )
            if restart_energy > 0.0:
                energy_ratio = continuation_energy / restart_energy
                salvage_energy_ratio.append(energy_ratio)
        anchor_energy = float(arm_runs["A"]["idle_subtracted_gpu_board_energy_j"])
        adaptive_energy = float(arm_runs["D"]["idle_subtracted_gpu_board_energy_j"])
        if anchor_energy > 0.0:
            lc3_corner_energy_ratio.append(adaptive_energy / anchor_energy)
        interactions.append(
            {
                "block_id": block_id,
                "arm_energy_j_per_canonical_token": energies,
                "phase_interactions_j_per_canonical_token": phase_effects,
                "primary_total_interaction_j_per_canonical_token": total,
                "checkpoint_related_interaction_j_per_canonical_token": checkpoint_total,
                "scale_free_log_ratio_of_ratios": ratio_of_ratios,
                "penalty_removed_fraction": removed_fraction,
                "sparse_continuation_salvage": {
                    "complete": complete,
                    "nll_delta": nll_delta,
                    "attempted_flop_saving_fraction": work_saving,
                    "opportunity_tick_saving": tick_saving,
                    "device_energy_ratio": energy_ratio,
                },
            }
        )

    primary_total = _interval(np, total_interactions, scenario, 0)
    phase_intervals = {
        phase: _interval(np, values, scenario, 10 + index)
        for index, (phase, values) in enumerate(
            phase_interaction_values.items()
        )
    }
    checkpoint_interval = _interval(np, checkpoint_interactions, scenario, 30)
    scale_interval = _interval(np, scale_free, scenario, 31)
    removed_interval = _interval(np, removed_fractions, scenario, 32)
    nll_interval = _interval(np, salvage_nll, scenario, 40)
    work_interval = _interval(np, salvage_work, scenario, 41)
    tick_interval = _interval(np, salvage_ticks, scenario, 42)
    energy_interval = _interval(np, salvage_energy_ratio, scenario, 43)
    lc3_interval = _interval(np, lc3_corner_energy_ratio, scenario, 44)

    invalidator_spec = scenario["measurement_invalidators"]
    all_runs = tuple(calibration_runs) + tuple(evaluation_runs)
    energy_present = all(
        run["idle_subtracted_gpu_board_energy_j"] is not None
        for run in all_runs
    )
    trace_present = all(
        bool(run["telemetry_trace"]["points"])
        and bool(run["phase_intervals"])
        for run in all_runs
    )
    partition_valid = all(bool(run["phase_partition_valid"]) for run in all_runs)
    closure_valid = all(
        float(run["phase_energy_closure_relative_error"])
        <= float(
            invalidator_spec["phase_energy_closure_relative_error_lte"]
        )
        for run in all_runs
    )
    evaluation_updates_valid = all(
        int(run["effective_power_update_count"])
        >= int(
            invalidator_spec[
                "minimum_effective_power_updates_per_evaluation_arm"
            ]
        )
        for run in evaluation_runs
    )
    effective_period = max(
        1e-9,
        float(logger_calibration["effective_update_period_seconds"]),
    )
    cadence_phase_updates: dict[str, dict[str, float]] = {}
    checkpoint_update_valid = True
    required_updates = float(
        invalidator_spec["minimum_pooled_effective_updates_per_cadence_phase"]
    )
    for cadence in (SPARSE, DENSE):
        cadence_phase_updates[cadence] = {}
        cadence_runs = [
            run for run in all_runs if run["checkpoint_cadence"] == cadence
        ]
        for phase in checkpoint_phases:
            structural_duration = sum(
                float(run["phase_metrics"][phase]["duration_seconds"])
                for run in cadence_runs
            )
            equivalents = structural_duration / effective_period
            cadence_phase_updates[cadence][phase] = equivalents
            if structural_duration > 0.0 and equivalents < required_updates:
                checkpoint_update_valid = False
    power_stable = all(
        run["power_configuration_start"] == run["power_configuration_end"]
        for run in all_runs
    )
    canonical_identity = all(
        bool(run["target_reached"])
        and int(run["canonical_tokens"])
        == int(scenario["canonical_work"]["target_canonical_tokens"])
        for run in all_runs
    )
    divergence_free = all(not bool(run["diverged"]) for run in all_runs)
    thermal_valid = all(
        not bool(run["thermal_limit_crossed"]) for run in all_runs
    )
    invalidators = {
        "missing_energy": not energy_present,
        "missing_raw_trace_or_phase_ledger": not trace_present,
        "phase_partition_invalid": not partition_valid,
        "phase_energy_closure_failed": not closure_valid,
        "insufficient_evaluation_power_updates": not evaluation_updates_valid,
        "insufficient_pooled_cadence_phase_updates": not checkpoint_update_valid,
        "calibration_state_non_equivalence": not calibration_state_equal,
        "calibration_work_non_equivalence": not calibration_work_equal,
        "calibration_nll_non_equivalence": not calibration_nll_equal,
        "gpu_power_configuration_changed": not power_stable,
        "canonical_work_identity_mismatch": not canonical_identity,
        "divergence": not divergence_free,
        "thermal_limit_crossed": not thermal_valid,
        "logger_delay_out_of_bound": abs(
            float(logger_calibration["selected_lag_seconds"])
        )
        > float(
            invalidator_spec["maximum_absolute_logger_delay_ms"]
        )
        / 1000.0,
    }
    measurement_valid = not any(invalidators.values())

    mechanism_spec = scenario["mechanism_falsifiers"]
    mechanism_gates = {
        "total_interaction_positive": (
            primary_total["lower_bound"] is not None
            and float(primary_total["lower_bound"])
            > float(mechanism_spec["total_interaction_lower_bound_gt"])
        ),
        "checkpoint_related_interaction_positive": (
            checkpoint_interval["lower_bound"] is not None
            and float(checkpoint_interval["lower_bound"])
            > float(
                mechanism_spec[
                    "checkpoint_related_interaction_lower_bound_gt"
                ]
            )
        ),
        "penalty_removed_fraction_material": (
            removed_interval["median"] is not None
            and float(removed_interval["median"])
            >= float(
                mechanism_spec[
                    "penalty_removed_fraction_median_gte"
                ]
            )
        ),
    }
    salvage_spec = scenario["salvage_falsifiers"]
    continuation_divergences = sum(
        bool(run["diverged"])
        for run in evaluation_runs
        if run["arm_code"] == "C"
    )
    cadence_nll_differences = [
        abs(
            float(lookup[(str(block["block_id"]), "D")]["final_held_out_nll"])
            - float(lookup[(str(block["block_id"]), "C")]["final_held_out_nll"])
        )
        for block in scenario["splits"]["evaluation"]["blocks"]
    ]
    salvage_gates = {
        "all_pairs_complete": complete_salvage_pairs
        == int(salvage_spec["paired_target_count_eq"]),
        "learning_noninferior": (
            nll_interval["upper_bound"] is not None
            and float(nll_interval["upper_bound"])
            <= float(
                salvage_spec[
                    "sparse_continue_minus_sparse_restart_nll_upper_bound_lte"
                ]
            )
        ),
        "attempted_work_saving_positive": (
            work_interval["lower_bound"] is not None
            and float(work_interval["lower_bound"])
            > float(
                salvage_spec[
                    "paired_attempted_flop_savings_lower_bound_gt"
                ]
            )
        ),
        "attempted_work_saving_material": (
            work_interval["median"] is not None
            and float(work_interval["median"])
            >= float(
                salvage_spec[
                    "paired_attempted_flop_savings_median_gte"
                ]
            )
        ),
        "opportunity_ticks_saved": (
            tick_interval["median"] is not None
            and float(tick_interval["median"])
            >= float(
                salvage_spec["median_opportunity_tick_savings_gte"]
            )
            and continuation_earlier
            == int(salvage_spec["continuation_earlier_block_count_eq"])
        ),
        "device_energy_bounded": (
            energy_interval["upper_bound"] is not None
            and float(energy_interval["upper_bound"])
            <= float(
                salvage_spec[
                    "sparse_continue_to_sparse_restart_device_energy_ratio_upper_bound_lte"
                ]
            )
        ),
        "continuation_does_not_diverge": continuation_divergences
        == int(salvage_spec["continuation_divergence_count_eq"]),
        "cadence_preserves_learning": max(cadence_nll_differences, default=0.0)
        <= float(
            salvage_spec[
                "cadence_within_continuation_nll_difference_upper_bound_lte"
            ]
        ),
    }
    lc3_penalty_reproduced = (
        lc3_interval["median"] is not None
        and float(lc3_interval["median"]) > 1.0
    )
    mechanism_survives = all(mechanism_gates.values())
    salvage_survives = all(salvage_gates.values())
    if not measurement_valid:
        conclusion = "measurement_invalid"
    elif not lc3_penalty_reproduced:
        conclusion = "lc3_energy_penalty_not_reproduced"
    elif not mechanism_survives:
        conclusion = "continuation_energy_not_attributed_to_checkpoint_cadence"
    elif salvage_survives:
        conclusion = "checkpoint_cadence_attributed_sparse_continuation_survives"
    else:
        conclusion = "checkpoint_cadence_partial_cause_candidate_still_fails"
    measurement = {
        "valid": measurement_valid,
        "invalidators": invalidators,
        "calibration_equivalence": calibration_equivalence,
        "cadence_phase_effective_update_equivalents": cadence_phase_updates,
    }
    summary = {
        "evaluation_block_interactions": interactions,
        "primary_total_interaction": primary_total,
        "phase_interactions": phase_intervals,
        "checkpoint_related_interaction": checkpoint_interval,
        "scale_free_interaction_sensitivity": scale_interval,
        "penalty_removed_fraction": removed_interval,
        "lc3_corner_reproduction": {
            "dense_continue_to_sparse_restart_energy_ratio": lc3_interval,
            "penalty_reproduced": lc3_penalty_reproduced,
        },
        "sparse_continuation_salvage": {
            "nll_difference": nll_interval,
            "attempted_flop_saving_fraction": work_interval,
            "opportunity_tick_saving": tick_interval,
            "device_energy_ratio": energy_interval,
            "continuation_earlier_block_count": continuation_earlier,
        },
        "mechanism_falsifier_results": mechanism_gates,
        "salvage_falsifier_results": salvage_gates,
        "checkpoint_cadence_attributed": mechanism_survives,
        "sparse_continuation_survives": salvage_survives,
        "conclusion": conclusion,
    }
    return measurement, summary


def _facility_bridge(
    scenario: Mapping[str, Any],
    evaluation_runs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    kernels: dict[str, Any] = {}
    for phase in PHASES:
        durations = [
            float(run["phase_metrics"][phase]["duration_seconds"])
            for run in evaluation_runs
            if float(run["phase_metrics"][phase]["duration_seconds"]) > 0.0
        ]
        energies = [
            float(run["phase_metrics"][phase]["idle_subtracted_energy_j"])
            for run in evaluation_runs
            if float(run["phase_metrics"][phase]["duration_seconds"]) > 0.0
        ]
        powers = [
            energy / duration
            for energy, duration in zip(energies, durations, strict=True)
        ]
        kernels[phase] = {
            "observed_run_count": len(powers),
            "median_idle_subtracted_power_w": (
                statistics.median(powers) if powers else None
            ),
            "median_duration_seconds": (
                statistics.median(durations) if durations else None
            ),
            "boundary": "local isolated GPU board only",
        }
    bridge = scenario["facility_bridge"]
    return {
        "evidence_class": "modeled_facility_bridge_conditioned_on_observed_local_phase_kernels",
        "observed_local_phase_kernels": kernels,
        "gpu_kernel_equation": bridge["gpu_kernel_equation"],
        "it_equation": bridge["it_equation"],
        "facility_transform": bridge["facility_transform"],
        "modeled_outputs_not_evaluated_in_pw1": bridge["modeled_outputs"],
        "static_pue_as_waveform_model_forbidden": bridge[
            "static_pue_as_waveform_model_forbidden"
        ],
        "future_observation_requirements": bridge[
            "future_observation_requirements"
        ],
        "facility_claim_allowed": False,
        "plain_boundary": (
            "PW1 identifies local operation kernels. It does not observe rack, "
            "cooling, storage, network, or point-of-common-coupling power."
        ),
    }


def _runtime_scenario(scenario: Mapping[str, Any]) -> dict[str, Any]:
    """Expose the frozen E002 binding through the unchanged LC2 warm runtime."""

    runtime = json.loads(json.dumps(scenario))
    warm = scenario["warm_start_binding"]
    optimization = runtime["optimization"]
    optimization.update(
        {
            "warm_start_ticks": int(warm["ticks"]),
            "warm_start_seed": int(warm["seed"]),
            "warm_start_late_window_start_tick": int(
                warm["late_window_start_tick"]
            ),
            "warm_start_max_window_nll_improvement": float(
                warm["maximum_nll_improvement"]
            ),
            "healthy_local_ticks": int(
                optimization["healthy_merge_ticks"]
            ),
        }
    )
    thermal = runtime["thermal_guard"]
    thermal.update(
        {
            "start_temperature_c_lte": int(
                thermal["arm_start_temperature_c_lte"]
            ),
            "resume_temperature_c_lte": int(
                thermal["resume_temperature_c_lte"]
            ),
        }
    )
    return runtime


def _validate_source_bindings(scenario: Mapping[str, Any]) -> dict[str, Any]:
    bindings = scenario["source_bindings"]
    checked: dict[str, Any] = {}
    for binding_id in (
        "lc3_result",
        "lc1_learning_result",
        "recovery_mechanics_result",
    ):
        binding = bindings[binding_id]
        payload = json.loads(Path(binding["path"]).read_text(encoding="utf-8"))
        actual = payload.get("artifact_sha256")
        expected = binding["artifact_sha256"]
        if actual != expected:
            raise ValueError(
                f"E002 source binding mismatch for {binding_id}: {actual} != {expected}"
            )
        checked[binding_id] = {
            "path": binding["path"],
            "artifact_sha256": expected,
        }
    lc3_scenario_binding = bindings["lc3_scenario"]
    lc3_scenario = json.loads(
        Path(lc3_scenario_binding["path"]).read_text(encoding="utf-8")
    )
    actual_scenario = _content_hash(lc3_scenario)
    if actual_scenario != lc3_scenario_binding["artifact_sha256"]:
        raise ValueError("E002 LC3 scenario content binding mismatch")
    checked["lc3_scenario"] = {
        "path": lc3_scenario_binding["path"],
        "artifact_sha256": actual_scenario,
    }
    bound_lc3 = bindings["lc3_engine"]
    bound_components = {
        "equal_work_engine": bound_lc3["source_sha256"],
        "quality_target_runtime": bound_lc3["component_source_sha256"][
            "quality_target_runtime"
        ],
        "learning_runtime": bound_lc3["component_source_sha256"][
            "learning_runtime"
        ],
    }
    reconstructed_bundle = hashlib.sha256(
        _canonical_json(bound_components).encode("utf-8")
    ).hexdigest()
    source_files_match = (
        _matches_source_hash(
            Path(lc3.__file__), bound_components["equal_work_engine"]
        )
        and _matches_source_hash(
            Path(lc2.__file__), bound_components["quality_target_runtime"]
        )
        and _matches_source_hash(
            Path(lc1.__file__), bound_components["learning_runtime"]
        )
    )
    if not source_files_match or reconstructed_bundle != bound_lc3[
        "bundle_sha256"
    ]:
        raise ValueError("E002 LC3 engine binding mismatch")
    checked["lc3_engine"] = {
        "engine_id": bound_lc3["engine_id"],
        "source_sha256": bound_lc3["source_sha256"],
        "component_source_sha256": bound_components,
        "bundle_sha256": reconstructed_bundle,
        "line_ending_canonicalization": (
            "source identity accepts raw or CRLF-to-LF canonical bytes"
        ),
    }
    return checked


def run_e002_checkpoint_power(
    scenario_path: str | Path,
    dataset_path: str | Path,
) -> dict[str, Any]:
    scenario_file = Path(scenario_path)
    scenario = json.loads(scenario_file.read_text(encoding="utf-8"))
    if scenario.get("schema") != "gpu-stack.e002-checkpoint-power-scenario.v1":
        raise ValueError("unsupported E002-PW1 scenario schema")
    checked_bindings = _validate_source_bindings(scenario)
    dataset_file = Path(dataset_path)
    runtime_scenario = _runtime_scenario(scenario)
    corpora = lc1._load_byte_corpora(dataset_file, scenario["dataset"])
    warm_power_sampler = lc1._PowerSampler()
    warm_checkpoint, warm_summary = lc2._build_warm_checkpoint(
        runtime_scenario, corpora, warm_power_sampler
    )
    observed_warm_hash = lc2._checkpoint_hash(warm_checkpoint)
    warm_binding = scenario["warm_start_binding"]
    warm_binding_passed = (
        observed_warm_hash == warm_binding["checkpoint_sha256"]
        and int(warm_summary["ticks"]) == int(warm_binding["ticks"])
        and bool(warm_summary["late_window"]["late_stage_gate_passed"])
    )
    print(
        "E002 warm checkpoint completed "
        f"ticks={warm_summary['ticks']} state={observed_warm_hash[:12]} "
        f"binding={warm_binding_passed}",
        flush=True,
    )
    if not warm_binding_passed:
        payload = {
            "schema": SCHEMA,
            "experiment_id": "E002-PW1",
            "scenario_id": scenario["scenario_id"],
            "scenario_sha256": _content_hash(scenario),
            "engine": _engine_identity(),
            "source_bindings": checked_bindings,
            "warm_start": {
                **warm_summary,
                "observed_checkpoint_sha256": observed_warm_hash,
                "binding_passed": False,
            },
            "runs": [],
            "measurement_validity": {
                "valid": False,
                "invalidators": {"warm_checkpoint_hash_mismatch": True},
            },
            "summary": {"conclusion": "measurement_invalid"},
        }
        payload["artifact_sha256"] = _content_hash(payload)
        return payload

    poll_seconds = float(
        scenario["telemetry"]["requested_sample_interval_ms"]
    ) / 1000.0
    sampler = _TraceSampler(poll_seconds)
    arms_by_id = {str(arm["arm_id"]): arm for arm in scenario["arms"]}
    order_spec = scenario["execution_order"]
    calibration_runs: list[dict[str, Any]] = []
    for block in scenario["splits"]["calibration"]["blocks"]:
        block_id = str(block["block_id"])
        order_id = str(order_spec["block_assignment"][block_id])
        for position, arm_id in enumerate(
            order_spec["orders"][order_id], start=1
        ):
            run = _run_arm(
                runtime_scenario,
                corpora,
                warm_checkpoint,
                block,
                arms_by_id[str(arm_id)],
                sampler,
                split="calibration",
            )
            run["execution_order_id"] = order_id
            run["execution_position"] = position
            calibration_runs.append(run)
            print(
                "E002 calibration completed "
                f"{run['run_id']} nll={run['final_held_out_nll']:.6f} "
                f"samples={len(run['telemetry_trace']['points'])}",
                flush=True,
            )
    logger = _estimate_logger(calibration_runs, scenario)
    for run in calibration_runs:
        _attach_attribution(run, logger, scenario)
    print(
        "E002 logger calibration frozen "
        f"lag_ms={float(logger['selected_lag_seconds']) * 1000.0:.1f} "
        f"effective_ms={float(logger['effective_update_period_seconds']) * 1000.0:.1f}",
        flush=True,
    )

    evaluation_runs: list[dict[str, Any]] = []
    for block in scenario["splits"]["evaluation"]["blocks"]:
        block_id = str(block["block_id"])
        order_id = str(order_spec["block_assignment"][block_id])
        for position, arm_id in enumerate(
            order_spec["orders"][order_id], start=1
        ):
            run = _run_arm(
                runtime_scenario,
                corpora,
                warm_checkpoint,
                block,
                arms_by_id[str(arm_id)],
                sampler,
                split="evaluation",
            )
            run["execution_order_id"] = order_id
            run["execution_position"] = position
            _attach_attribution(run, logger, scenario)
            evaluation_runs.append(run)
            print(
                "E002 evaluation completed "
                f"{run['run_id']} ticks={run['opportunity_ticks_to_target']} "
                f"nll={run['final_held_out_nll']:.6f} "
                f"energy_j={run['idle_subtracted_gpu_board_energy_j']:.3f}",
                flush=True,
            )

    measurement, summary = _summarize(
        scenario, calibration_runs, evaluation_runs, logger
    )
    _, _, torch, _, _ = lc1._require_dependencies()
    runs = tuple(calibration_runs) + tuple(evaluation_runs)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "experiment_id": "E002-PW1",
        "scenario_id": scenario["scenario_id"],
        "scenario_sha256": _content_hash(scenario),
        "engine": _engine_identity(),
        "source_bindings": checked_bindings,
        "warm_start": {
            **warm_summary,
            "observed_checkpoint_sha256": observed_warm_hash,
            "binding_passed": warm_binding_passed,
        },
        "runtime": {
            "hardware": {
                "gpu": torch.cuda.get_device_name(0),
                "compute_capability": list(
                    torch.cuda.get_device_capability(0)
                ),
            },
            "software": {
                "torch_version": torch.__version__,
                "cuda_version": torch.version.cuda,
                "engine_id": ENGINE_ID,
            },
            "power_configuration": sampler.power_configuration(),
        },
        "logger_calibration": {
            **logger,
            "logger_delay_ms": float(logger["selected_lag_seconds"])
            * 1000.0,
            "effective_update_period_ms": float(
                logger["effective_update_period_seconds"]
            )
            * 1000.0,
        },
        "study": {
            "canonical_work": scenario["canonical_work"],
            "factors": scenario["factors"],
            "arms": scenario["arms"],
            "splits": scenario["splits"],
            "execution_order": scenario["execution_order"],
            "estimands": scenario["estimands"],
            "mechanism_falsifiers": scenario["mechanism_falsifiers"],
            "salvage_falsifiers": scenario["salvage_falsifiers"],
        },
        "runs": list(runs),
        "measurement_validity": measurement,
        "summary": summary,
        "facility_bridge": _facility_bridge(scenario, evaluation_runs),
        "evidence_boundary": {
            "observed": scenario["facility_bridge"]["local_observed"],
            "modeled": [
                "facility bridge equations conditioned on local phase kernels"
            ],
            "unmeasured": scenario["facility_bridge"]["local_unmeasured"],
            "frontier_scale_question": scenario["frontier_scale_question"],
        },
        "completed_at": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    payload["artifact_sha256"] = _content_hash(payload)
    return payload


__all__ = [
    "ENGINE_ID",
    "PHASES",
    "SCHEMA",
    "run_e002_checkpoint_power",
]
