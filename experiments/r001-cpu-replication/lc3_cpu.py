"""R001: CPU copy of the E001-LC3 equal-work arm and the LC2/LC3 warm-start builder.

COPIED (not edited in place) from gpu_stack/research/e001_lc3_equal_work.py
(_run_equal_work_arm) and e001_lc2_quality_target.py (_build_warm_checkpoint),
because both hard-code torch.device("cuda:0"), torch.cuda.synchronize and the
NVML energy meter. Changes, and only these:
  * device is CPU; the NVML power sampler, thermal guard and GPU meter are
    removed (CpuMeter keeps wall seconds only; energy is not measured);
  * the held-out evaluation interval is read from the scenario (R001 uses 64
    ticks instead of 8 to save CPU time; the final canonical-tick-256 point is
    always measured, so the primary endpoint is unchanged);
  * the warm builder takes the seed as an argument and skips the meter.
Training, merge, checkpoint, rollback, failure-handling and evaluation logic
is the engines' own, called by import (lc1/lc2 helpers).
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
import time
from typing import Any, Mapping

from cpu_runtime import CpuMeter
from gpu_stack.research import e001_learning_calibration as lc1
from gpu_stack.research import e001_lc2_quality_target as lc2

FIXED_POLICY = lc1.FIXED_POLICY
ADAPTIVE_POLICY = lc1.ADAPTIVE_POLICY


def _run_equal_work_arm(
    scenario: Mapping[str, Any],
    corpora: Any,
    warm_checkpoint: Any,
    stratum: Mapping[str, Any],
    arm: Mapping[str, Any],
    *,
    split: str,
) -> dict[str, Any]:
    _, _, torch, nn, functional = lc1._require_dependencies()
    device = torch.device("cpu")
    optimization = scenario["optimization"]
    model_config = scenario["model"]
    seed = int(stratum["seed"])
    policy_id = str(arm["policy_id"])
    interrupted = bool(arm["interrupted"])
    if policy_id not in {FIXED_POLICY, ADAPTIVE_POLICY}:
        raise ValueError(f"unknown LC3 policy {policy_id!r}")
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
    canonical_target_ticks = int(optimization["canonical_target_ticks"])
    maximum_opportunity_ticks = int(
        optimization["maximum_opportunity_ticks"]
    )
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
    work_target_reached = False
    opportunity_ticks_to_target: int | None = None
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

    curve: list[dict[str, Any]] = []

    def measure(wall_tick: int, *, active_outage: bool) -> None:
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

    cooldown = 0.0
    start_temperature = None
    run_started = time.perf_counter()
    meter = CpuMeter()
    thermal_pause = 0.0
    measure(0, active_outage=False)
    meter.start()

    for wall_tick in range(maximum_opportunity_ticks):
        if logical_tick >= canonical_target_ticks:
            work_target_reached = True
            opportunity_ticks_to_target = elapsed_wall_ticks
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
            cadence = healthy_cadence
            if post_rejoin_remaining > 0:
                cadence = 1
            if steps_since_merge >= cadence:
                lc1._average_sites(torch, site_a, site_b)
                merge_count += 1
                steps_since_merge = 0
                if post_rejoin_remaining > 0:
                    post_rejoin_remaining -= 1
                checkpoint_interval = (
                    fixed_checkpoint_interval
                    if policy_id == FIXED_POLICY
                    else adaptive_checkpoint_interval
                )
                if merge_count % checkpoint_interval == 0:
                    take_checkpoint(site_a)

        elapsed_wall_ticks = wall_tick + 1
        if any(not math.isfinite(value) for value in training_losses[-2:]):
            divergence = True
            break
        if elapsed_wall_ticks % evaluation_interval == 0:
            meter.stop()
            measure(elapsed_wall_ticks, active_outage=active)
            if logical_tick < canonical_target_ticks:
                meter.start()

    if logical_tick >= canonical_target_ticks:
        work_target_reached = True
        opportunity_ticks_to_target = elapsed_wall_ticks
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
    canonical_tokens = logical_tick * 2 * tokens_per_quota
    attempted_flops = 6.0 * parameter_count * attempted_tokens
    canonical_flops = 6.0 * parameter_count * canonical_tokens
    final_point = curve[-1]
    return {
        "run_id": (
            f"e001-lc3:{stratum['stratum_id']}:{policy_id}:"
            f"{'interrupted' if interrupted else 'no-failure'}"
        ),
        "stratum_id": str(stratum["stratum_id"]),
        "split": split,
        "seed": seed,
        "policy_id": policy_id,
        "interrupted": interrupted,
        "failure_schedule": [list(item) for item in failures],
        "warm_checkpoint_sha256": lc2._checkpoint_hash(warm_checkpoint),
        "parameter_count": parameter_count,
        "curve": curve,
        "canonical_target_ticks": canonical_target_ticks,
        "target_reached": work_target_reached,
        "opportunity_ticks_to_target": opportunity_ticks_to_target,
        "logical_ticks_to_target": (
            logical_tick if work_target_reached else None
        ),
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
        "local_active_seconds": max(1e-9, meter.active_seconds),
        "physical_seconds": physical_seconds,
        "thermal_pause_seconds": thermal_pause,
        "cooldown_before_seconds": cooldown,
        "start_temperature_c": start_temperature,
        "end_temperature_c": None,
        "energy": energy,
        "diverged": divergence,
        "completed_at": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    }


def build_warm_checkpoint(
    scenario: Mapping[str, Any],
    corpora: Any,
    seed: int,
    *,
    ticks: int | None = None,
    progress_every: int = 0,
) -> tuple[Any, dict[str, Any]]:
    """Shared warm start: two serial sites, AdamW, average every 8 ticks.

    Same loop as lc2._build_warm_checkpoint (copied; CPU, no meter, seed argument).
    Late-stage gate: held-out NLL improvement over the last 256 ticks <= 0.03.
    """
    _, _, torch, nn, functional = lc1._require_dependencies()
    device = torch.device("cpu")
    optimization = scenario["optimization"]
    ticks = int(optimization["warm_start_ticks"]) if ticks is None else int(ticks)
    late_window_start = max(0, ticks - 256)
    site_a, site_b, evaluation_model = lc2._site_pair(
        torch, nn, functional, scenario, device, seed=seed
    )
    started = time.perf_counter()
    losses: list[float] = []
    steps_since_merge = 0
    late: dict[int, float] = {}
    batch_size = int(optimization["batch_size_per_site"])
    context_length = int(scenario["model"]["context_length"])

    def measure(tick: int) -> None:
        lc1._load_evaluation_state(torch, evaluation_model, site_a, site_b)
        mean, _, _ = lc1._evaluate(
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
        late[tick] = mean

    if late_window_start == 0:
        measure(0)
    for logical_tick in range(ticks):
        for site, site_id in ((site_a, "site-a"), (site_b, "site-b")):
            losses.append(
                lc2._quota(
                    torch, functional, scenario, corpora, site,
                    seed=seed, site_id=site_id, logical_tick=logical_tick, device=device,
                )
            )
        steps_since_merge += 1
        if steps_since_merge >= int(optimization["healthy_local_ticks"]):
            lc1._average_sites(torch, site_a, site_b)
            steps_since_merge = 0
        if any(not math.isfinite(v) for v in losses[-2:]):
            raise RuntimeError("warm start diverged")
        done = logical_tick + 1
        if done in {late_window_start, ticks}:
            measure(done)
        if progress_every and done % progress_every == 0:
            print(
                f"warm seed={seed} tick={done}/{ticks} "
                f"elapsed={time.perf_counter() - started:.0f}s",
                flush=True,
            )
    checkpoint = lc1._checkpoint(site_a, 0, 0)
    parameter_count = sum(p.numel() for p in site_a.model.parameters())
    improvement = late[late_window_start] - late[ticks]
    summary = {
        "seed": seed,
        "ticks": ticks,
        "parameter_count": parameter_count,
        "checkpoint_sha256": lc2._checkpoint_hash(checkpoint),
        "checkpoint_bytes": checkpoint.checkpoint_bytes,
        "physical_seconds": time.perf_counter() - started,
        "late_window": {
            "start_tick": late_window_start,
            "end_tick": ticks,
            "start_held_out_nll": late[late_window_start],
            "end_held_out_nll": late[ticks],
            "nll_improvement": improvement,
            "maximum_nll_improvement": float(
                optimization["warm_start_max_window_nll_improvement"]
            ),
            "late_stage_gate_passed": improvement
            <= float(optimization["warm_start_max_window_nll_improvement"]),
        },
        "final_training_loss_mean_last_16": sum(losses[-16:]) / max(1, len(losses[-16:])),
    }
    return checkpoint, summary

