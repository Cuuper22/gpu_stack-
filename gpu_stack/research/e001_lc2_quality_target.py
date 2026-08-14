"""E001-LC2: the measured late-stage quality-to-target experiment.

LC1 asked about learning progress per FLOP; LC2 asks the sharper question of
who reaches a fixed loss target first. It reuses the frozen LC1 model and
recovery semantics without editing the content-addressed LC1 engine: build
one shared warm model/AdamW state, pick the loss target from synchronous
calibration runs only, then stop each held-out arm at the first observation
that reaches that same target.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
from typing import Any, Mapping, Sequence

from . import e001_learning_calibration as lc1
from .observations import (
    CalibrationEvaluationSplit,
    MeasuredValue,
    MeasurementUncertainty,
    Observation,
    Provenance,
)


SCHEMA = "gpu-stack.e001-quality-target-evidence.v1"
ENGINE_ID = "gpu-stack.e001-lc2-quality-target.v1"

SYNC_POLICY = lc1.SYNC_POLICY
FIXED_POLICY = lc1.FIXED_POLICY
ADAPTIVE_POLICY = lc1.ADAPTIVE_POLICY


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


def _checkpoint_hash(checkpoint: Any) -> str:
    digest = hashlib.sha256()

    def visit(value: Any, path: str) -> None:
        digest.update(path.encode("utf-8"))
        if hasattr(value, "detach") and hasattr(value, "dtype"):
            tensor = value.detach().cpu().contiguous()
            digest.update(str(tensor.dtype).encode("ascii"))
            digest.update(str(tuple(tensor.shape)).encode("ascii"))
            raw = tensor.reshape(-1).view(lc1._require_dependencies()[2].uint8)
            digest.update(raw.numpy().tobytes())
            return
        if isinstance(value, Mapping):
            for key in sorted(value, key=lambda item: str(item)):
                visit(value[key], f"{path}/{key}")
            return
        if isinstance(value, (tuple, list)):
            for index, item in enumerate(value):
                visit(item, f"{path}/{index}")
            return
        digest.update(repr(value).encode("utf-8"))

    visit(checkpoint.model_state, "model")
    visit(checkpoint.optimizer_state, "optimizer")
    return digest.hexdigest()


class _TrainingMeter:
    """Accumulate only training/recovery segments, excluding evaluation/cooldown."""

    def __init__(self, torch, power_sampler: Any) -> None:
        self.torch = torch
        self.power_sampler = power_sampler
        self.running = False
        self.started_at = 0.0
        self.active_seconds = 0.0
        self.sample_count = 0
        self.raw_energy_j = 0.0
        self.idle_subtracted_energy_j = 0.0
        self.energy_available = bool(power_sampler.available)

    def start(self) -> None:
        if self.running:
            return
        self.power_sampler.start()
        self.started_at = time.perf_counter()
        self.running = True

    def stop(self) -> None:
        if not self.running:
            return
        self.torch.cuda.synchronize()
        self.active_seconds += time.perf_counter() - self.started_at
        segment = self.power_sampler.stop()
        self.sample_count += int(segment["sample_count"] or 0)
        if segment["raw_energy_j"] is not None:
            self.raw_energy_j += float(segment["raw_energy_j"])
        if segment["idle_subtracted_energy_j"] is not None:
            self.idle_subtracted_energy_j += float(
                segment["idle_subtracted_energy_j"]
            )
        self.running = False

    def result(self) -> dict[str, float | int | None]:
        self.stop()
        return {
            "sample_count": self.sample_count,
            "idle_power_w": self.power_sampler.idle_power_w,
            "raw_energy_j": (
                self.raw_energy_j if self.energy_available else None
            ),
            "idle_subtracted_energy_j": (
                self.idle_subtracted_energy_j
                if self.energy_available
                else None
            ),
        }


def _configure_torch(torch, seed: int, optimization: Mapping[str, Any]) -> None:
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    deterministic = bool(
        optimization.get("deterministic_cuda_algorithms", False)
    )
    torch.backends.cuda.matmul.allow_tf32 = not deterministic
    torch.backends.cudnn.allow_tf32 = not deterministic
    torch.use_deterministic_algorithms(deterministic, warn_only=True)


def _site_pair(
    torch,
    nn,
    functional,
    scenario: Mapping[str, Any],
    device,
    *,
    seed: int,
    checkpoint: Any | None = None,
) -> tuple[Any, Any, Any]:
    _configure_torch(torch, seed, scenario["optimization"])
    site_a = lc1._Site(
        model=lc1._build_model(
            torch,
            nn,
            functional,
            scenario["model"],
            device,
        ),
        optimizer=None,
    )
    site_a.optimizer = lc1._optimizer(
        torch,
        site_a.model,
        scenario["optimization"],
    )
    site_b = lc1._Site(
        model=lc1._build_model(
            torch,
            nn,
            functional,
            scenario["model"],
            device,
        ),
        optimizer=None,
    )
    site_b.optimizer = lc1._optimizer(
        torch,
        site_b.model,
        scenario["optimization"],
    )
    if checkpoint is None:
        site_b.model.load_state_dict(site_a.model.state_dict())
    else:
        lc1._restore(site_a, checkpoint)
        lc1._restore(site_b, checkpoint)
    evaluation_model = lc1._build_model(
        torch,
        nn,
        functional,
        scenario["model"],
        device,
    )
    evaluation_model.load_state_dict(site_a.model.state_dict())
    return site_a, site_b, evaluation_model


def _quota(
    torch,
    functional,
    scenario: Mapping[str, Any],
    corpora: Any,
    site: Any,
    *,
    seed: int,
    site_id: str,
    logical_tick: int,
    device,
) -> float:
    optimization = scenario["optimization"]
    model = scenario["model"]
    corpus = corpora.site_a if site_id == "site-a" else corpora.site_b
    x, y = lc1._sample_batch(
        torch,
        corpus,
        seed=seed,
        site_id=site_id,
        logical_tick=logical_tick,
        stream="training",
        batch_size=int(optimization["batch_size_per_site"]),
        context_length=int(model["context_length"]),
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


def _build_warm_checkpoint(
    scenario: Mapping[str, Any],
    corpora: Any,
    power_sampler: Any,
) -> tuple[Any, dict[str, Any]]:
    _, _, torch, nn, functional = lc1._require_dependencies()
    if not torch.cuda.is_available():
        raise RuntimeError("E001-LC2 requires a CUDA-capable PyTorch runtime")
    if not torch.cuda.is_bf16_supported():
        raise RuntimeError("configured LC2 harness requires bfloat16 support")
    device = torch.device("cuda:0")
    optimization = scenario["optimization"]
    seed = int(optimization["warm_start_seed"])
    site_a, site_b, evaluation_model = _site_pair(
        torch,
        nn,
        functional,
        scenario,
        device,
        seed=seed,
    )
    thermal = scenario["thermal_guard"]
    cooldown = power_sampler.wait_until_temperature(
        int(thermal["start_temperature_c_lte"]),
        poll_seconds=float(thermal["poll_seconds"]),
    )
    start_temperature = power_sampler.temperature_c()
    started = time.perf_counter()
    meter = _TrainingMeter(torch, power_sampler)
    meter.start()
    thermal_pause = 0.0
    ticks = int(optimization["warm_start_ticks"])
    late_window_start = int(
        optimization["warm_start_late_window_start_tick"]
    )
    training_losses: list[float] = []
    steps_since_merge = 0
    late_window_nll: dict[int, float] = {}
    for logical_tick in range(ticks):
        training_losses.append(
            _quota(
                torch,
                functional,
                scenario,
                corpora,
                site_a,
                seed=seed,
                site_id="site-a",
                logical_tick=logical_tick,
                device=device,
            )
        )
        training_losses.append(
            _quota(
                torch,
                functional,
                scenario,
                corpora,
                site_b,
                seed=seed,
                site_id="site-b",
                logical_tick=logical_tick,
                device=device,
            )
        )
        steps_since_merge += 1
        if steps_since_merge >= int(optimization["healthy_local_ticks"]):
            lc1._average_sites(torch, site_a, site_b)
            steps_since_merge = 0
        if any(not math.isfinite(value) for value in training_losses[-2:]):
            raise RuntimeError("shared LC2 warm start diverged")
        completed_tick = logical_tick + 1
        if completed_tick in {late_window_start, ticks}:
            meter.stop()
            lc1._load_evaluation_state(
                torch,
                evaluation_model,
                site_a,
                site_b,
            )
            mean, _, _ = lc1._evaluate(
                torch,
                functional,
                evaluation_model,
                corpora.validation,
                seed=int(optimization["validation_seed"]),
                batch_size=int(optimization["batch_size_per_site"]),
                context_length=int(scenario["model"]["context_length"]),
                validation_batches=int(optimization["validation_batches"]),
                device=device,
                autocast_dtype=torch.bfloat16,
            )
            late_window_nll[completed_tick] = mean
            if completed_tick != ticks:
                meter.start()
        if (logical_tick + 1) % int(optimization["healthy_local_ticks"]) == 0:
            temperature = power_sampler.temperature_c()
            if (
                temperature is not None
                and temperature >= int(thermal["pause_temperature_c_gte"])
            ):
                meter.stop()
                thermal_pause += power_sampler.wait_until_temperature(
                    int(thermal["resume_temperature_c_lte"]),
                    poll_seconds=float(thermal["poll_seconds"]),
                )
                if completed_tick != ticks:
                    meter.start()
    meter.stop()
    physical_seconds = time.perf_counter() - started
    energy = meter.result()
    checkpoint = lc1._checkpoint(site_a, 0, 0)
    parameter_count = sum(
        parameter.numel() for parameter in site_a.model.parameters()
    )
    tokens_per_quota = int(optimization["batch_size_per_site"]) * int(
        scenario["model"]["context_length"]
    )
    summary = {
        "seed": seed,
        "ticks": ticks,
        "attempted_tokens": ticks * 2 * tokens_per_quota,
        "attempted_compute_flops": (
            6.0 * parameter_count * ticks * 2 * tokens_per_quota
        ),
        "checkpoint_sha256": _checkpoint_hash(checkpoint),
        "checkpoint_bytes": checkpoint.checkpoint_bytes,
        "parameter_count": parameter_count,
        "local_active_seconds": max(1e-9, meter.active_seconds),
        "physical_seconds": physical_seconds,
        "thermal_pause_seconds": thermal_pause,
        "cooldown_before_seconds": cooldown,
        "start_temperature_c": start_temperature,
        "end_temperature_c": power_sampler.temperature_c(),
        "energy": energy,
        "late_window": {
            "start_tick": late_window_start,
            "end_tick": ticks,
            "start_held_out_nll": late_window_nll[late_window_start],
            "end_held_out_nll": late_window_nll[ticks],
            "nll_improvement": (
                late_window_nll[late_window_start] - late_window_nll[ticks]
            ),
            "maximum_nll_improvement": float(
                optimization["warm_start_max_window_nll_improvement"]
            ),
            "late_stage_gate_passed": (
                late_window_nll[late_window_start] - late_window_nll[ticks]
                <= float(
                    optimization["warm_start_max_window_nll_improvement"]
                )
            ),
        },
    }
    return checkpoint, summary


def _run_arm(
    scenario: Mapping[str, Any],
    corpora: Any,
    warm_checkpoint: Any,
    stratum: Mapping[str, Any],
    arm: Mapping[str, Any],
    power_sampler: Any,
    *,
    split: str,
    maximum_ticks: int,
    target_nll: float | None,
) -> dict[str, Any]:
    _, _, torch, nn, functional = lc1._require_dependencies()
    device = torch.device("cuda:0")
    optimization = scenario["optimization"]
    model_config = scenario["model"]
    seed = int(stratum["seed"])
    policy_id = str(arm["policy_id"])
    interrupted = bool(arm["interrupted"])
    if policy_id not in {SYNC_POLICY, FIXED_POLICY, ADAPTIVE_POLICY}:
        raise ValueError(f"unknown LC2 policy {policy_id!r}")
    site_a, site_b, evaluation_model = _site_pair(
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
    healthy_cadence = int(optimization["healthy_local_ticks"])
    reduced_cadence = int(
        optimization["reduced_membership_checkpoint_ticks"]
    )
    evaluation_interval = int(optimization["evaluation_interval_ticks"])
    fixed_checkpoint_interval = int(
        optimization["fixed_checkpoint_merge_interval"]
    )
    adaptive_checkpoint_interval = int(
        optimization["adaptive_checkpoint_merge_interval"]
    )
    failures = tuple(stratum["failures"]) if interrupted else ()

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
    divergence = False
    target_reached = False
    target_wall_tick: int | None = None
    target_logical_tick: int | None = None
    elapsed_wall_ticks = 0

    checkpoint_started = time.perf_counter()
    latest_checkpoint = lc1._checkpoint(site_a, 0, 0)
    checkpoint_copy_seconds += time.perf_counter() - checkpoint_started
    checkpoint_count += 1
    checkpoint_bytes += latest_checkpoint.checkpoint_bytes

    def take_checkpoint(source: Any) -> None:
        nonlocal latest_checkpoint, checkpoint_count, checkpoint_bytes
        nonlocal checkpoint_copy_seconds
        started = time.perf_counter()
        latest_checkpoint = lc1._checkpoint(source, logical_tick, merge_count)
        checkpoint_copy_seconds += time.perf_counter() - started
        checkpoint_count += 1
        checkpoint_bytes += latest_checkpoint.checkpoint_bytes

    def train_quota(site: Any, site_id: str, quota_tick: int) -> float:
        nonlocal attempted_tokens, replayed_tokens
        identity = (site_id, quota_tick)
        if identity in seen_quotas:
            replayed_tokens += tokens_per_quota
        else:
            seen_quotas.add(identity)
        loss = _quota(
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

    curve: list[dict[str, Any]] = []

    def measure(wall_tick: int, *, active_outage: bool) -> bool:
        nonlocal target_reached, target_wall_tick, target_logical_tick
        canonical_b = (
            None
            if active_outage and policy_id == ADAPTIVE_POLICY
            else site_b
        )
        lc1._load_evaluation_state(
            torch,
            evaluation_model,
            site_b if canonical_b is None else site_a,
            canonical_b,
        )
        mean, standard_deviation, losses = lc1._evaluate(
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
        curve.append(
            {
                "wall_tick": wall_tick,
                "logical_tick": logical_tick,
                "attempted_tokens": attempted_tokens,
                "canonical_tokens": logical_tick * 2 * tokens_per_quota,
                "replayed_tokens": replayed_tokens,
                "discarded_tokens": discarded_tokens,
                "held_out_nll": mean,
                "held_out_nll_standard_deviation": standard_deviation,
                "validation_batch_nll": list(losses),
            }
        )
        if target_nll is not None and mean <= target_nll:
            target_reached = True
            target_wall_tick = wall_tick
            target_logical_tick = logical_tick
        return target_reached

    thermal = scenario["thermal_guard"]
    cooldown = power_sampler.wait_until_temperature(
        int(thermal["start_temperature_c_lte"]),
        poll_seconds=float(thermal["poll_seconds"]),
    )
    start_temperature = power_sampler.temperature_c()
    run_started = time.perf_counter()
    meter = _TrainingMeter(torch, power_sampler)
    thermal_pause = 0.0
    measure(0, active_outage=False)
    if not target_reached:
        meter.start()

    for wall_tick in range(maximum_ticks):
        if target_reached:
            break
        active, starts, ends = lc1._failure_at_tick(failures, wall_tick)
        if ends and policy_id == ADAPTIVE_POLICY:
            restore_started = time.perf_counter()
            lc1._copy_site(site_b, site_a)
            restore_seconds += time.perf_counter() - restore_started
            steps_since_merge = 0
            post_rejoin_remaining = int(
                optimization["post_rejoin_sync_ticks"]
            )

        if policy_id == FIXED_POLICY and starts:
            rolled_back_ticks = max(
                0,
                logical_tick - latest_checkpoint.logical_tick,
            )
            discarded_tokens += rolled_back_ticks * 2 * tokens_per_quota
            restore_started = time.perf_counter()
            lc1._restore(site_a, latest_checkpoint)
            lc1._restore(site_b, latest_checkpoint)
            restore_seconds += time.perf_counter() - restore_started
            logical_tick = latest_checkpoint.logical_tick
            merge_count = latest_checkpoint.merge_count
            steps_since_merge = 0

        if policy_id == FIXED_POLICY and active:
            pass
        elif policy_id == ADAPTIVE_POLICY and active:
            training_losses.append(
                train_quota(site_b, "site-a", logical_tick)
            )
            training_losses.append(
                train_quota(site_b, "site-b", logical_tick)
            )
            survivor_redistributed_tokens += tokens_per_quota
            logical_tick += 1
            steps_since_merge += 1
            if steps_since_merge >= reduced_cadence:
                merge_count += 1
                steps_since_merge = 0
                take_checkpoint(site_b)
        else:
            training_losses.append(
                train_quota(site_a, "site-a", logical_tick)
            )
            training_losses.append(
                train_quota(site_b, "site-b", logical_tick)
            )
            logical_tick += 1
            steps_since_merge += 1
            cadence = 1 if policy_id == SYNC_POLICY else healthy_cadence
            if post_rejoin_remaining > 0:
                cadence = 1
            if steps_since_merge >= cadence:
                lc1._average_sites(torch, site_a, site_b)
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

        elapsed_wall_ticks = wall_tick + 1
        if any(not math.isfinite(value) for value in training_losses[-2:]):
            divergence = True
            break
        if elapsed_wall_ticks % evaluation_interval == 0:
            meter.stop()
            if measure(elapsed_wall_ticks, active_outage=active):
                break
            meter.start()
        if elapsed_wall_ticks % healthy_cadence == 0:
            temperature = power_sampler.temperature_c()
            if (
                temperature is not None
                and temperature >= int(thermal["pause_temperature_c_gte"])
            ):
                meter.stop()
                thermal_pause += power_sampler.wait_until_temperature(
                    int(thermal["resume_temperature_c_lte"]),
                    poll_seconds=float(thermal["poll_seconds"]),
                )
                if not target_reached:
                    meter.start()

    meter.stop()
    if not divergence and curve[-1]["wall_tick"] != elapsed_wall_ticks:
        active = False
        if elapsed_wall_ticks:
            active, _, _ = lc1._failure_at_tick(
                failures,
                elapsed_wall_ticks - 1,
            )
        measure(elapsed_wall_ticks, active_outage=active)
    physical_seconds = time.perf_counter() - run_started
    energy = meter.result()
    active_seconds = max(1e-9, meter.active_seconds)
    canonical_tokens = logical_tick * 2 * tokens_per_quota
    attempted_flops = 6.0 * parameter_count * attempted_tokens
    canonical_flops = 6.0 * parameter_count * canonical_tokens
    final_point = curve[-1]
    return {
        "run_id": (
            f"e001-lc2:{stratum['stratum_id']}:{policy_id}:"
            f"{'interrupted' if interrupted else 'no-failure'}"
        ),
        "stratum_id": str(stratum["stratum_id"]),
        "split": split,
        "seed": seed,
        "policy_id": policy_id,
        "interrupted": interrupted,
        "failure_schedule": [list(item) for item in failures],
        "warm_checkpoint_sha256": _checkpoint_hash(warm_checkpoint),
        "parameter_count": parameter_count,
        "curve": curve,
        "target_held_out_nll": target_nll,
        "target_reached": target_reached,
        "opportunity_ticks_to_target": target_wall_tick,
        "logical_ticks_to_target": target_logical_tick,
        "opportunity_ticks_elapsed": elapsed_wall_ticks,
        "logical_ticks_completed": logical_tick,
        "initial_held_out_nll": float(curve[0]["held_out_nll"]),
        "final_held_out_nll": float(final_point["held_out_nll"]),
        "final_held_out_nll_standard_deviation": float(
            final_point["held_out_nll_standard_deviation"]
        ),
        "attempted_tokens": attempted_tokens,
        "canonical_tokens": canonical_tokens,
        "replayed_tokens": replayed_tokens,
        "discarded_tokens": discarded_tokens,
        "survivor_redistributed_tokens": survivor_redistributed_tokens,
        "attempted_compute_flops": attempted_flops,
        "canonical_compute_flops": canonical_flops,
        "checkpoint_count": checkpoint_count,
        "checkpoint_bytes": checkpoint_bytes,
        "checkpoint_copy_seconds": checkpoint_copy_seconds,
        "restore_seconds": restore_seconds,
        "local_active_seconds": active_seconds,
        "physical_seconds": physical_seconds,
        "thermal_pause_seconds": thermal_pause,
        "cooldown_before_seconds": cooldown,
        "start_temperature_c": start_temperature,
        "end_temperature_c": power_sampler.temperature_c(),
        "energy": energy,
        "diverged": divergence,
        "completed_at": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    }


def _interval_or_missing(
    np,
    values: Sequence[float],
    *,
    scenario: Mapping[str, Any],
    seed_offset: int,
) -> dict[str, Any]:
    if not values:
        return {
            "values": [],
            "median": None,
            "lower_bound": None,
            "upper_bound": None,
            "confidence_level": float(
                scenario["bootstrap"]["confidence_level"]
            ),
            "draws": int(scenario["bootstrap"]["draws"]),
            "method": "not computed because no complete paired values exist",
        }
    return lc1._bootstrap_median_interval(
        np,
        values,
        draws=int(scenario["bootstrap"]["draws"]),
        seed=int(scenario["bootstrap"]["seed"]) + seed_offset,
        confidence_level=float(
            scenario["bootstrap"]["confidence_level"]
        ),
    )


def _summarize(
    scenario: Mapping[str, Any],
    calibration_runs: Sequence[Mapping[str, Any]],
    evaluation_runs: Sequence[Mapping[str, Any]],
    target_nll: float,
) -> dict[str, Any]:
    np, _, _, _, _ = lc1._require_dependencies()
    lookup = {
        (
            str(run["stratum_id"]),
            str(run["policy_id"]),
            bool(run["interrupted"]),
        ): run
        for run in evaluation_runs
    }
    work_savings: list[float] = []
    canonical_ratios: list[float] = []
    energy_ratios: list[float] = []
    tick_savings: list[float] = []
    paired_rows: list[dict[str, Any]] = []
    paired_target_count = 0
    adaptive_earlier_count = 0
    for item in scenario["evaluation_strata"]:
        stratum_id = str(item["stratum_id"])
        fixed = lookup[(stratum_id, FIXED_POLICY, True)]
        adaptive = lookup[(stratum_id, ADAPTIVE_POLICY, True)]
        fixed_tick = fixed["opportunity_ticks_to_target"]
        adaptive_tick = adaptive["opportunity_ticks_to_target"]
        work_saving = None
        tick_saving = None
        canonical_ratio = None
        energy_ratio = None
        if fixed_tick is not None and adaptive_tick is not None:
            paired_target_count += 1
            if float(adaptive_tick) < float(fixed_tick):
                adaptive_earlier_count += 1
            tick_saving = float(fixed_tick) - float(adaptive_tick)
            tick_savings.append(tick_saving)
            fixed_attempted = float(fixed["attempted_compute_flops"])
            adaptive_attempted = float(adaptive["attempted_compute_flops"])
            work_saving = (
                (fixed_attempted - adaptive_attempted) / fixed_attempted
                if fixed_attempted > 0.0
                else 0.0
            )
            work_savings.append(work_saving)
            fixed_canonical = float(fixed["canonical_tokens"])
            canonical_ratio = (
                float(adaptive["canonical_tokens"]) / fixed_canonical
                if fixed_canonical > 0.0
                else None
            )
            if canonical_ratio is not None:
                canonical_ratios.append(canonical_ratio)
            fixed_energy = fixed["energy"]["idle_subtracted_energy_j"]
            adaptive_energy = adaptive["energy"][
                "idle_subtracted_energy_j"
            ]
            if (
                fixed_energy is not None
                and adaptive_energy is not None
                and float(fixed_energy) > 0.0
            ):
                energy_ratio = float(adaptive_energy) / float(fixed_energy)
                energy_ratios.append(energy_ratio)
        paired_rows.append(
            {
                "stratum_id": stratum_id,
                "fixed_target_tick": fixed_tick,
                "adaptive_target_tick": adaptive_tick,
                "opportunity_tick_saving": tick_saving,
                "attempted_flop_saving_fraction": work_saving,
                "adaptive_to_fixed_canonical_token_ratio": canonical_ratio,
                "adaptive_to_fixed_device_energy_ratio": energy_ratio,
                "fixed_final_held_out_nll": fixed["final_held_out_nll"],
                "adaptive_final_held_out_nll": adaptive[
                    "final_held_out_nll"
                ],
                "fixed_attempted_tokens": fixed["attempted_tokens"],
                "adaptive_attempted_tokens": adaptive["attempted_tokens"],
                "fixed_canonical_tokens": fixed["canonical_tokens"],
                "adaptive_canonical_tokens": adaptive["canonical_tokens"],
                "fixed_replayed_tokens": fixed["replayed_tokens"],
                "adaptive_replayed_tokens": adaptive["replayed_tokens"],
                "fixed_discarded_tokens": fixed["discarded_tokens"],
                "adaptive_discarded_tokens": adaptive["discarded_tokens"],
            }
        )
    work_interval = _interval_or_missing(
        np,
        work_savings,
        scenario=scenario,
        seed_offset=0,
    )
    canonical_interval = _interval_or_missing(
        np,
        canonical_ratios,
        scenario=scenario,
        seed_offset=1,
    )
    energy_interval = _interval_or_missing(
        np,
        energy_ratios,
        scenario=scenario,
        seed_offset=2,
    )
    tick_interval = _interval_or_missing(
        np,
        tick_savings,
        scenario=scenario,
        seed_offset=3,
    )
    calibration_lookup = {
        (str(run["stratum_id"]), str(run["policy_id"])): run
        for run in calibration_runs
    }
    calibration_equivalent = True
    calibration_equivalence_rows: list[dict[str, Any]] = []
    for item in scenario["calibration_strata"]:
        stratum_id = str(item["stratum_id"])
        fixed_clean = calibration_lookup[(stratum_id, FIXED_POLICY)]
        adaptive_clean = calibration_lookup[(stratum_id, ADAPTIVE_POLICY)]
        same_attempted = (
            fixed_clean["attempted_tokens"] == adaptive_clean["attempted_tokens"]
        )
        fixed_curve = fixed_clean["curve"]
        adaptive_curve = adaptive_clean["curve"]
        same_curve = len(fixed_curve) == len(adaptive_curve) and all(
            fixed_point["wall_tick"] == adaptive_point["wall_tick"]
            and fixed_point["held_out_nll"]
            == adaptive_point["held_out_nll"]
            for fixed_point, adaptive_point in zip(
                fixed_curve,
                adaptive_curve,
                strict=True,
            )
        )
        calibration_equivalent = (
            calibration_equivalent and same_attempted and same_curve
        )
        calibration_equivalence_rows.append(
            {
                "stratum_id": stratum_id,
                "attempted_tokens_equal": same_attempted,
                "curve_exactly_equal": same_curve,
            }
        )
    adaptive_interrupted = [
        run
        for run in evaluation_runs
        if run["policy_id"] == ADAPTIVE_POLICY and run["interrupted"]
    ]
    adaptive_target_count = sum(
        bool(run["target_reached"]) for run in adaptive_interrupted
    )
    adaptive_divergence_count = sum(
        bool(run["diverged"])
        for run in evaluation_runs
        if run["policy_id"] == ADAPTIVE_POLICY
    )
    falsifiers = scenario["falsifiers"]
    gates = {
        "all_paired_targets_reached": paired_target_count
        == int(falsifiers["paired_target_count_eq"]),
        "attempted_flop_saving_positive": (
            len(work_savings) == int(falsifiers["paired_target_count_eq"])
            and work_interval["lower_bound"] is not None
            and float(work_interval["lower_bound"])
            > float(
                falsifiers[
                    "paired_attempted_flop_savings_lower_bound_gt"
                ]
            )
        ),
        "attempted_flop_saving_material": (
            work_interval["median"] is not None
            and float(work_interval["median"])
            >= float(
                falsifiers[
                    "paired_attempted_flop_savings_median_gte"
                ]
            )
        ),
        "canonical_work_ratio_bounded": (
            len(canonical_ratios) == int(falsifiers["paired_target_count_eq"])
            and canonical_interval["upper_bound"] is not None
            and float(canonical_interval["upper_bound"])
            <= float(
                falsifiers[
                    "adaptive_to_fixed_canonical_token_ratio_upper_bound_lte"
                ]
            )
        ),
        "opportunity_tick_saving_material": (
            tick_interval["median"] is not None
            and float(tick_interval["median"])
            >= float(falsifiers["median_opportunity_tick_savings_gte"])
            and adaptive_earlier_count
            >= int(falsifiers["adaptive_earlier_strata_count_gte"])
        ),
        "device_energy_ratio_bounded": (
            len(energy_ratios) == int(falsifiers["paired_target_count_eq"])
            and energy_interval["upper_bound"] is not None
            and float(energy_interval["upper_bound"])
            <= float(
                falsifiers[
                    "adaptive_to_fixed_device_energy_ratio_upper_bound_lte"
                ]
            )
        ),
        "calibration_no_failure_exact_equivalence": calibration_equivalent
        is bool(falsifiers["calibration_no_failure_exact_equivalence"]),
        "adaptive_reaches_all_targets": adaptive_target_count
        == int(falsifiers["adaptive_target_attainment_count_eq"]),
        "adaptive_does_not_diverge": adaptive_divergence_count
        == int(falsifiers["adaptive_divergence_count_eq"]),
    }
    survives = all(gates.values())
    calibration_initial = statistics.median(
        float(run["initial_held_out_nll"])
        for run in calibration_runs
        if run["policy_id"] == FIXED_POLICY
    )
    calibration_final = statistics.median(
        float(run["final_held_out_nll"])
        for run in calibration_runs
        if run["policy_id"] == FIXED_POLICY
    )
    return {
        "target": {
            "held_out_nll": target_nll,
            "calibration_initial_median_nll": calibration_initial,
            "calibration_fixed_final_median_nll": calibration_final,
            "selected_ticks": scenario["target"]["calibration_target_ticks"],
            "selected_from": [
                run["run_id"]
                for run in calibration_runs
                if run["policy_id"] == FIXED_POLICY
            ],
        },
        "evaluation_pairs": paired_rows,
        "paired_target_count": paired_target_count,
        "paired_attempted_flop_savings": work_interval,
        "adaptive_to_fixed_canonical_token_ratio": canonical_interval,
        "adaptive_to_fixed_device_energy_ratio": energy_interval,
        "paired_opportunity_tick_savings": tick_interval,
        "adaptive_earlier_strata_count": adaptive_earlier_count,
        "calibration_equivalence": calibration_equivalence_rows,
        "adaptive_target_attainment_count": adaptive_target_count,
        "adaptive_divergence_count": adaptive_divergence_count,
        "falsifier_results": gates,
        "candidate_survives_lc2": survives,
        "conclusion": (
            "candidate_survives_late_stage_quality_target"
            if survives
            else "candidate_falsified_late_stage_quality_target"
        ),
    }


def _mechanics_bridge(
    recovery_result: Mapping[str, Any],
    evaluation_runs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    recovery_by_policy = {
        str(run["policy_id"]): run for run in recovery_result["runs"]
    }
    mappings = {
        FIXED_POLICY: "fixed-local-checkpoint-restart",
        ADAPTIVE_POLICY: "adaptive-recovery",
    }
    densities: dict[str, dict[str, Any]] = {}
    for learning_policy, recovery_policy in mappings.items():
        run = recovery_by_policy[recovery_policy]
        frontier = int(run["summary"]["terminal_frontier"]["committed_step"])
        if frontier <= 0:
            raise ValueError("recovery bridge requires a positive durable frontier")
        densities[learning_policy] = {
            "learning_policy_id": learning_policy,
            "recovery_policy_proxy": recovery_policy,
            "durable_frontier_units": frontier,
            "modeled_elapsed_ns_per_frontier_unit": float(
                run["summary"]["elapsed_ns"]
            )
            / frontier,
            "modeled_inter_site_link_bytes_per_frontier_unit": float(
                run["metrics"]["total_inter_site_link_bytes"]
            )
            / frontier,
            "modeled_energy_j_per_frontier_unit": float(
                run["metrics"]["modeled_energy_j"]
            )
            / frontier,
            "modeled_lost_compute_flops_per_frontier_unit": float(
                run["metrics"]["lost_compute_flops"]
            )
            / frontier,
            "traffic_by_class": run["metrics"]["traffic_by_class"],
        }
    projected: list[dict[str, Any]] = []
    for run in evaluation_runs:
        policy_id = str(run["policy_id"])
        if not run["interrupted"] or policy_id not in mappings:
            continue
        logical_ticks = run["logical_ticks_to_target"]
        density = densities[policy_id]
        values = None
        if logical_ticks is not None:
            scale = float(logical_ticks)
            values = {
                "modeled_elapsed_ns": scale
                * float(density["modeled_elapsed_ns_per_frontier_unit"]),
                "modeled_inter_site_link_bytes": scale
                * float(
                    density[
                        "modeled_inter_site_link_bytes_per_frontier_unit"
                    ]
                ),
                "modeled_energy_j": scale
                * float(density["modeled_energy_j_per_frontier_unit"]),
                "modeled_lost_compute_flops": scale
                * float(
                    density[
                        "modeled_lost_compute_flops_per_frontier_unit"
                    ]
                ),
            }
        projected.append(
            {
                "run_id": run["run_id"],
                "stratum_id": run["stratum_id"],
                "learning_policy_id": policy_id,
                "observed_opportunity_ticks_to_target": run[
                    "opportunity_ticks_to_target"
                ],
                "observed_logical_ticks_to_target": logical_ticks,
                "observed_attempted_compute_flops": run[
                    "attempted_compute_flops"
                ],
                "observed_canonical_compute_flops": run[
                    "canonical_compute_flops"
                ],
                "sensitivity_projection": values,
            }
        )
    return {
        "evidence_class": "modeled_bridge_sensitivity",
        "plain_boundary": (
            "Modeled repeated-trace sensitivity conditioned on observed LC2 "
            "target crossing. Not measured datacenter performance."
        ),
        "source_recovery_artifact_sha256": recovery_result[
            "artifact_sha256"
        ],
        "policy_mapping": mappings,
        "densities": densities,
        "projections": projected,
        "assumptions": [
            "one LC2 logical tick is treated as one recovery-v2 durable-frontier unit",
            "the recovery-v2 two-failure trace is repeated linearly",
            "adaptive-recovery is a mechanical proxy for adaptive-survivor-continuation",
        ],
        "non_comparabilities": [
            "recovery-v2 failures are absolute-time events, not the LC2 schedules",
            "modeled energy is constant-coefficient compute plus network energy, not measured device or facility energy",
            "modeled lost FLOP is not observed replayed or discarded LC2 tokens",
            "simultaneous datacenter throughput remains unmeasured",
        ],
    }


def _observation(
    run: Mapping[str, Any],
    scenario: Mapping[str, Any],
    dataset_path: Path,
) -> Observation:
    exact_attempted = float(run["attempted_compute_flops"])
    exact_canonical = float(run["canonical_compute_flops"])
    values: dict[str, MeasuredValue] = {
        "held_out_final_nll": MeasuredValue(
            value=float(run["final_held_out_nll"]),
            unit="natural_log_unit_per_byte",
            uncertainty=MeasurementUncertainty(
                standard_deviation=float(
                    run["final_held_out_nll_standard_deviation"]
                ),
                notes="Dispersion across the frozen held-out validation batches.",
            ),
        ),
        "attempted_compute_flops": MeasuredValue(
            value=exact_attempted,
            unit="FLOP",
            uncertainty=MeasurementUncertainty(
                lower_bound=exact_attempted,
                upper_bound=exact_attempted,
                notes="Modeled exactly as 6*N*attempted tokens.",
            ),
        ),
        "canonical_compute_flops": MeasuredValue(
            value=exact_canonical,
            unit="FLOP",
            uncertainty=MeasurementUncertainty(
                lower_bound=exact_canonical,
                upper_bound=exact_canonical,
                notes="Modeled exactly as 6*N*canonical tokens.",
            ),
        ),
        "local_active_time": MeasuredValue(
            value=float(run["local_active_seconds"]),
            unit="second",
            uncertainty=MeasurementUncertainty(
                notes="Local serial RTX harness time; not datacenter wall time."
            ),
        ),
    }
    target_tick = run["opportunity_ticks_to_target"]
    if target_tick is not None:
        cadence = float(
            scenario["optimization"]["evaluation_interval_ticks"]
        )
        values["opportunity_ticks_to_target"] = MeasuredValue(
            value=float(target_tick),
            unit="opportunity_tick",
            uncertainty=MeasurementUncertainty(
                lower_bound=max(0.0, float(target_tick) - cadence),
                upper_bound=float(target_tick),
                notes="Target crossing is interval-censored by evaluation cadence.",
            ),
        )
    energy = run["energy"]["idle_subtracted_energy_j"]
    if energy is not None:
        values["training_device_energy"] = MeasuredValue(
            value=float(energy),
            unit="joule",
            uncertainty=MeasurementUncertainty(
                notes=(
                    "NVML board-energy integral after idle subtraction; no "
                    "instrument-calibration interval is claimed."
                )
            ),
        )
    dataset = scenario["dataset"]
    return Observation(
        observation_id=str(run["run_id"]),
        measured_values=values,
        timestamp=datetime.fromisoformat(
            str(run["completed_at"]).replace("Z", "+00:00")
        ),
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
        software={"framework": "pytorch", "engine_id": ENGINE_ID},
        instrumentation={
            "loss": "frozen held-out byte-NLL batches",
            "time": "opportunity ticks plus time.perf_counter local harness time",
            "energy": "NVML sampled GPU board power with idle subtraction",
            "flops": "6 * parameter_count * attempted or canonical tokens",
        },
        provenance=Provenance(
            source="GPUSTACK E001-LC2 local measured training run",
            uri=str(dataset["uri"]),
            checksum=f"sha256:{lc1._sha256_file(dataset_path)}",
            retrieved_at=datetime(2026, 7, 12, tzinfo=timezone.utc),
            notes=(
                "Raw dataset stayed outside the repository.",
                "One serial GPU measures learning response, not simultaneous datacenter performance.",
            ),
        ),
        metadata={
            "split": run["split"],
            "policy_id": run["policy_id"],
            "interrupted": run["interrupted"],
            "target_reached": run["target_reached"],
            "warm_checkpoint_sha256": run["warm_checkpoint_sha256"],
        },
    )


def run_e001_lc2_quality_target(
    scenario_path: str | Path,
    dataset_path: str | Path,
) -> dict[str, Any]:
    """Execute the frozen LC2 calibration and held-out matrix."""

    scenario_file = Path(scenario_path)
    scenario = json.loads(scenario_file.read_text(encoding="utf-8"))
    if scenario.get("schema") != "gpu-stack.e001-quality-target-scenario.v1":
        raise ValueError("unsupported E001-LC2 scenario schema")
    dataset_file = Path(dataset_path)
    corpora = lc1._load_byte_corpora(dataset_file, scenario["dataset"])
    source_learning = json.loads(
        Path(scenario["source_learning_result"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    if source_learning.get("artifact_sha256") != scenario[
        "source_learning_result"
    ]["artifact_sha256"]:
        raise ValueError("source LC1 result does not match frozen LC2 identity")
    source_recovery = json.loads(
        Path(scenario["source_recovery_result"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    if source_recovery.get("artifact_sha256") != scenario[
        "source_recovery_result"
    ]["artifact_sha256"]:
        raise ValueError(
            "source recovery result does not match frozen LC2 identity"
        )

    power_sampler = lc1._PowerSampler()
    warm_checkpoint, warm_summary = _build_warm_checkpoint(
        scenario,
        corpora,
        power_sampler,
    )
    print(
        "LC2 warm checkpoint completed "
        f"ticks={warm_summary['ticks']} "
        f"state={warm_summary['checkpoint_sha256'][:12]} "
        f"active_s={warm_summary['local_active_seconds']:.2f}",
        flush=True,
    )

    if not warm_summary["late_window"]["late_stage_gate_passed"]:
        payload = {
            "schema": SCHEMA,
            "experiment_id": "E001-LC2",
            "scenario_id": scenario["scenario_id"],
            "scenario_sha256": _content_hash(scenario),
            "engine": {
                "engine_id": ENGINE_ID,
                "source_sha256": _source_hash(),
            },
            "source_learning_result": {
                "schema": source_learning["schema"],
                "artifact_sha256": source_learning["artifact_sha256"],
                "path": scenario["source_learning_result"]["path"],
            },
            "source_recovery_result": {
                "schema": source_recovery["schema"],
                "artifact_sha256": source_recovery["artifact_sha256"],
                "path": scenario["source_recovery_result"]["path"],
            },
            "warm_start": warm_summary,
            "runs": [],
            "observations": [],
            "summary": {
                "candidate_survives_lc2": False,
                "conclusion": "protocol_failed_warm_start_not_late_stage",
                "falsifier_results": {"late_stage_warm_start": False},
            },
            "mechanics_bridge": _mechanics_bridge(source_recovery, []),
            "result_scope": {
                "overall_e001_status": "protocol_failure_before_evaluation",
                "supported": ["measured warm-start loss-window improvement"],
                "unsupported": ["any LC2 policy comparison"],
            },
        }
        payload["artifact_sha256"] = _content_hash(payload)
        return payload

    calibration_runs: list[dict[str, Any]] = []
    calibration_arms = tuple(scenario["calibration_arms"])
    for stratum_index, stratum in enumerate(scenario["calibration_strata"]):
        rotation = stratum_index % len(calibration_arms)
        ordered_arms = calibration_arms[rotation:] + calibration_arms[:rotation]
        for arm in ordered_arms:
            run = _run_arm(
                scenario,
                corpora,
                warm_checkpoint,
                stratum,
                arm,
                power_sampler,
                split="calibration",
                maximum_ticks=int(
                    scenario["optimization"]["calibration_ticks"]
                ),
                target_nll=None,
            )
            calibration_runs.append(run)
            print(
                "LC2 calibration completed "
                f"{run['run_id']} nll={run['final_held_out_nll']:.6f}",
                flush=True,
            )
    target_ticks = {
        int(value) for value in scenario["target"]["calibration_target_ticks"]
    }
    target_values = [
        float(point["held_out_nll"])
        for run in calibration_runs
        if run["policy_id"] == FIXED_POLICY
        for point in run["curve"]
        if int(point["wall_tick"]) in target_ticks
    ]
    expected_target_values = (
        len(scenario["calibration_strata"]) * len(target_ticks)
    )
    if len(target_values) != expected_target_values:
        raise RuntimeError("LC2 calibration target ticks are missing")
    target_nll = statistics.median(target_values)
    calibration_first_crossings: dict[str, int | None] = {}
    for run in calibration_runs:
        first = next(
            (
                int(point["wall_tick"])
                for point in run["curve"]
                if float(point["held_out_nll"]) <= target_nll
            ),
            None,
        )
        run["target_held_out_nll"] = target_nll
        run["target_reached"] = first is not None
        run["opportunity_ticks_to_target"] = first
        run["logical_ticks_to_target"] = first
        calibration_first_crossings[run["run_id"]] = first
    calibration_lookup = {
        (str(run["stratum_id"]), str(run["policy_id"])): run
        for run in calibration_runs
    }
    exact_equivalence = True
    for stratum in scenario["calibration_strata"]:
        stratum_id = str(stratum["stratum_id"])
        fixed = calibration_lookup[(stratum_id, FIXED_POLICY)]
        adaptive = calibration_lookup[(stratum_id, ADAPTIVE_POLICY)]
        exact_equivalence = exact_equivalence and (
            fixed["attempted_tokens"] == adaptive["attempted_tokens"]
            and len(fixed["curve"]) == len(adaptive["curve"])
            and all(
                left["wall_tick"] == right["wall_tick"]
                and left["held_out_nll"] == right["held_out_nll"]
                for left, right in zip(
                    fixed["curve"],
                    adaptive["curve"],
                    strict=True,
                )
            )
        )
    minimum_crossing = int(
        scenario["target"]["required_first_crossing_tick_min"]
    )
    maximum_crossing = int(
        scenario["target"]["required_first_crossing_tick_max"]
    )
    fixed_crossings = [
        run["opportunity_ticks_to_target"]
        for run in calibration_runs
        if run["policy_id"] == FIXED_POLICY
    ]
    target_window_valid = all(
        crossing is not None
        and minimum_crossing <= int(crossing) <= maximum_crossing
        for crossing in fixed_crossings
    )
    if not exact_equivalence or not target_window_valid:
        payload = {
            "schema": SCHEMA,
            "experiment_id": "E001-LC2",
            "scenario_id": scenario["scenario_id"],
            "scenario_sha256": _content_hash(scenario),
            "engine": {
                "engine_id": ENGINE_ID,
                "source_sha256": _source_hash(),
            },
            "source_learning_result": {
                "schema": source_learning["schema"],
                "artifact_sha256": source_learning["artifact_sha256"],
                "path": scenario["source_learning_result"]["path"],
            },
            "source_recovery_result": {
                "schema": source_recovery["schema"],
                "artifact_sha256": source_recovery["artifact_sha256"],
                "path": scenario["source_recovery_result"]["path"],
            },
            "warm_start": warm_summary,
            "runs": calibration_runs,
            "observations": [],
            "summary": {
                "candidate_survives_lc2": False,
                "conclusion": "protocol_failed_calibration_validity",
                "target": {"held_out_nll": target_nll},
                "calibration_first_crossings": calibration_first_crossings,
                "falsifier_results": {
                    "target_window_valid": target_window_valid,
                    "calibration_no_failure_exact_equivalence": exact_equivalence,
                },
            },
            "mechanics_bridge": _mechanics_bridge(source_recovery, []),
            "result_scope": {
                "overall_e001_status": "protocol_failure_before_evaluation",
                "supported": ["measured LC2 calibration controls"],
                "unsupported": ["any held-out LC2 policy comparison"],
            },
        }
        payload["artifact_sha256"] = _content_hash(payload)
        return payload
    print(f"LC2 frozen target held_out_nll={target_nll:.9f}", flush=True)

    evaluation_runs: list[dict[str, Any]] = []
    arms = tuple(scenario["evaluation_arms"])
    for stratum_index, stratum in enumerate(scenario["evaluation_strata"]):
        rotation = stratum_index % len(arms)
        ordered_arms = arms[rotation:] + arms[:rotation]
        for arm in ordered_arms:
            run = _run_arm(
                scenario,
                corpora,
                warm_checkpoint,
                stratum,
                arm,
                power_sampler,
                split="evaluation",
                maximum_ticks=int(
                    scenario["optimization"]["maximum_evaluation_ticks"]
                ),
                target_nll=target_nll,
            )
            evaluation_runs.append(run)
            print(
                "LC2 evaluation completed "
                f"{run['run_id']} target_tick="
                f"{run['opportunity_ticks_to_target']} "
                f"nll={run['final_held_out_nll']:.6f} "
                f"attempted={run['attempted_tokens']} "
                f"active_s={run['local_active_seconds']:.2f}",
                flush=True,
            )

    summary = _summarize(
        scenario,
        calibration_runs,
        evaluation_runs,
        target_nll,
    )
    runs = tuple(calibration_runs) + tuple(evaluation_runs)
    observations = tuple(
        _observation(run, scenario, dataset_file) for run in runs
    )
    split = CalibrationEvaluationSplit.from_ids(
        split_id="e001-lc2-calibration-evaluation-v1",
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
            "shared_warm_checkpoint": warm_summary["checkpoint_sha256"],
            "evaluation_schedules_frozen_before_execution": True,
        },
    )
    split.validate_observations(observations, require_complete_partition=True)

    _, _, torch, _, _ = lc1._require_dependencies()
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "experiment_id": "E001-LC2",
        "scenario_id": scenario["scenario_id"],
        "scenario_sha256": _content_hash(scenario),
        "engine": {"engine_id": ENGINE_ID, "source_sha256": _source_hash()},
        "source_learning_result": {
            "schema": source_learning["schema"],
            "artifact_sha256": source_learning["artifact_sha256"],
            "path": scenario["source_learning_result"]["path"],
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
            "gpu_compute_capability": list(
                torch.cuda.get_device_capability(0)
            ),
            "nvml_power_available": power_sampler.available,
            "idle_power_w": power_sampler.idle_power_w,
        },
        "study": {
            "model": scenario["model"],
            "optimization": scenario["optimization"],
            "target": scenario["target"],
            "calibration_strata": scenario["calibration_strata"],
            "calibration_arms": scenario["calibration_arms"],
            "evaluation_strata": scenario["evaluation_strata"],
            "evaluation_arms": scenario["evaluation_arms"],
            "falsifiers": scenario["falsifiers"],
        },
        "warm_start": warm_summary,
        "split": split.to_dict(),
        "runs": list(runs),
        "observations": [
            observation.to_dict() for observation in observations
        ],
        "summary": summary,
        "mechanics_bridge": _mechanics_bridge(
            source_recovery,
            evaluation_runs,
        ),
        "result_scope": {
            "overall_e001_status": (
                "candidate_ready_for_transfer_panels"
                if summary["candidate_survives_lc2"]
                else "candidate_falsified_or_redirect_required"
            ),
            "supported": [
                "late-stage byte-level TinyStories quality-to-target response",
                "paired opportunity-tick effect across six frozen evaluation strata",
                "attempted and canonical work to the same held-out quality",
                "local RTX harness time and sampled device energy",
            ],
            "unsupported": [
                "frontier-scale convergence or capability",
                "real simultaneous multi-site speedup or WAN performance",
                "measured checkpoint-service, host, cooling, or facility energy",
                "transfer beyond the frozen model, data, optimizer, and failures",
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
    "run_e001_lc2_quality_target",
]
