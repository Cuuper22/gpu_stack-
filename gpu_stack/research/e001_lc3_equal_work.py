"""Equal-canonical-work recovery experiment selected by the LC2 failures."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
from typing import Any, Mapping, Sequence

from . import e001_lc2_quality_target as lc2
from . import e001_learning_calibration as lc1
from .observations import (
    CalibrationEvaluationSplit,
    MeasuredValue,
    MeasurementUncertainty,
    Observation,
    Provenance,
)


SCHEMA = "gpu-stack.e001-equal-work-evidence.v1"
ENGINE_ID = "gpu-stack.e001-lc3-equal-work.v1"

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


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_hash() -> str:
    return _file_hash(Path(__file__))


def _engine_identity() -> dict[str, Any]:
    lc2_path = Path(lc2.__file__)
    lc1_path = Path(lc1.__file__)
    components = {
        "equal_work_engine": _source_hash(),
        "quality_target_runtime": _file_hash(lc2_path),
        "learning_runtime": _file_hash(lc1_path),
    }
    return {
        "engine_id": ENGINE_ID,
        "source_sha256": components["equal_work_engine"],
        "component_source_sha256": components,
        "bundle_sha256": hashlib.sha256(
            _canonical_json(components).encode("utf-8")
        ).hexdigest(),
    }


def _run_equal_work_arm(
    scenario: Mapping[str, Any],
    corpora: Any,
    warm_checkpoint: Any,
    stratum: Mapping[str, Any],
    arm: Mapping[str, Any],
    power_sampler: Any,
    *,
    split: str,
) -> dict[str, Any]:
    _, _, torch, nn, functional = lc1._require_dependencies()
    device = torch.device("cuda:0")
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

    thermal = scenario["thermal_guard"]
    cooldown = power_sampler.wait_until_temperature(
        int(thermal["start_temperature_c_lte"]),
        poll_seconds=float(thermal["poll_seconds"]),
    )
    start_temperature = power_sampler.temperature_c()
    run_started = time.perf_counter()
    meter = lc2._TrainingMeter(torch, power_sampler)
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
        "end_temperature_c": power_sampler.temperature_c(),
        "energy": energy,
        "diverged": divergence,
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
) -> dict[str, Any]:
    np, _, _, _, _ = lc1._require_dependencies()
    calibration_lookup = {
        (str(run["stratum_id"]), str(run["policy_id"])): run
        for run in calibration_runs
    }
    calibration_rows: list[dict[str, Any]] = []
    calibration_equivalent = True
    for stratum in scenario["calibration"]["strata"]:
        stratum_id = str(stratum["stratum_id"])
        fixed = calibration_lookup[(stratum_id, FIXED_POLICY)]
        adaptive = calibration_lookup[(stratum_id, ADAPTIVE_POLICY)]
        same_attempted = fixed["attempted_tokens"] == adaptive["attempted_tokens"]
        same_curve = len(fixed["curve"]) == len(adaptive["curve"]) and all(
            left["wall_tick"] == right["wall_tick"]
            and left["held_out_nll"] == right["held_out_nll"]
            for left, right in zip(
                fixed["curve"], adaptive["curve"], strict=True
            )
        )
        calibration_equivalent = calibration_equivalent and same_attempted and same_curve
        calibration_rows.append(
            {
                "stratum_id": stratum_id,
                "attempted_tokens_equal": same_attempted,
                "curve_exactly_equal": same_curve,
            }
        )

    lookup = {
        (str(run["stratum_id"]), str(run["policy_id"])): run
        for run in evaluation_runs
    }
    nll_effects: list[float] = []
    work_savings: list[float] = []
    tick_savings: list[float] = []
    energy_ratios: list[float] = []
    pairs: list[dict[str, Any]] = []
    paired_target_count = 0
    adaptive_earlier_count = 0
    for stratum in scenario["evaluation_strata"]:
        stratum_id = str(stratum["stratum_id"])
        fixed = lookup[(stratum_id, FIXED_POLICY)]
        adaptive = lookup[(stratum_id, ADAPTIVE_POLICY)]
        complete = bool(fixed["target_reached"] and adaptive["target_reached"])
        nll_effect = None
        work_saving = None
        tick_saving = None
        energy_ratio = None
        if complete:
            paired_target_count += 1
            nll_effect = float(adaptive["final_held_out_nll"]) - float(
                fixed["final_held_out_nll"]
            )
            nll_effects.append(nll_effect)
            fixed_attempted = float(fixed["attempted_compute_flops"])
            work_saving = (
                fixed_attempted - float(adaptive["attempted_compute_flops"])
            ) / fixed_attempted
            work_savings.append(work_saving)
            tick_saving = float(fixed["opportunity_ticks_to_target"]) - float(
                adaptive["opportunity_ticks_to_target"]
            )
            tick_savings.append(tick_saving)
            if tick_saving > 0.0:
                adaptive_earlier_count += 1
            fixed_energy = fixed["energy"]["idle_subtracted_energy_j"]
            adaptive_energy = adaptive["energy"]["idle_subtracted_energy_j"]
            if (
                fixed_energy is not None
                and adaptive_energy is not None
                and float(fixed_energy) > 0.0
            ):
                energy_ratio = float(adaptive_energy) / float(fixed_energy)
                energy_ratios.append(energy_ratio)
        pairs.append(
            {
                "stratum_id": stratum_id,
                "complete_equal_work_pair": complete,
                "adaptive_minus_fixed_final_nll": nll_effect,
                "attempted_flop_saving_fraction": work_saving,
                "opportunity_tick_saving": tick_saving,
                "adaptive_to_fixed_device_energy_ratio": energy_ratio,
                "fixed_final_held_out_nll": fixed["final_held_out_nll"],
                "adaptive_final_held_out_nll": adaptive["final_held_out_nll"],
                "fixed_opportunity_ticks": fixed["opportunity_ticks_to_target"],
                "adaptive_opportunity_ticks": adaptive[
                    "opportunity_ticks_to_target"
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
    nll_interval = _interval(np, nll_effects, scenario, 0)
    work_interval = _interval(np, work_savings, scenario, 1)
    tick_interval = _interval(np, tick_savings, scenario, 2)
    energy_interval = _interval(np, energy_ratios, scenario, 3)
    adaptive_divergence_count = sum(
        bool(run["diverged"])
        for run in evaluation_runs
        if run["policy_id"] == ADAPTIVE_POLICY
    )
    falsifiers = scenario["falsifiers"]
    gates = {
        "all_equal_work_pairs_complete": paired_target_count
        == int(falsifiers["paired_target_count_eq"]),
        "learning_noninferior": (
            nll_interval["upper_bound"] is not None
            and float(nll_interval["upper_bound"])
            <= float(falsifiers["adaptive_minus_fixed_nll_upper_bound_lte"])
        ),
        "attempted_flop_saving_positive": (
            work_interval["lower_bound"] is not None
            and float(work_interval["lower_bound"])
            > float(falsifiers["paired_attempted_flop_savings_lower_bound_gt"])
        ),
        "attempted_flop_saving_material": (
            work_interval["median"] is not None
            and float(work_interval["median"])
            >= float(falsifiers["paired_attempted_flop_savings_median_gte"])
        ),
        "opportunity_tick_saving_material": (
            tick_interval["median"] is not None
            and float(tick_interval["median"])
            >= float(falsifiers["median_opportunity_tick_savings_gte"])
            and adaptive_earlier_count
            == int(falsifiers["adaptive_earlier_strata_count_eq"])
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
        "adaptive_does_not_diverge": adaptive_divergence_count
        == int(falsifiers["adaptive_divergence_count_eq"]),
    }
    survives = all(gates.values())
    return {
        "canonical_target": {
            "logical_ticks": int(
                scenario["optimization"]["canonical_target_ticks"]
            ),
            "canonical_tokens": int(
                scenario["optimization"]["canonical_target_ticks"]
            )
            * 2
            * int(scenario["optimization"]["batch_size_per_site"])
            * int(scenario["model"]["context_length"]),
        },
        "noninferiority_margin_nll": float(
            scenario["calibration"]["noninferiority_margin_nll"]
        ),
        "calibration_equivalence": calibration_rows,
        "evaluation_pairs": pairs,
        "paired_target_count": paired_target_count,
        "paired_adaptive_minus_fixed_nll": nll_interval,
        "paired_attempted_flop_savings": work_interval,
        "paired_opportunity_tick_savings": tick_interval,
        "adaptive_to_fixed_device_energy_ratio": energy_interval,
        "adaptive_earlier_strata_count": adaptive_earlier_count,
        "adaptive_divergence_count": adaptive_divergence_count,
        "falsifier_results": gates,
        "candidate_survives_lc3": survives,
        "conclusion": (
            "candidate_survives_equal_canonical_work"
            if survives
            else "candidate_falsified_equal_canonical_work"
        ),
    }


def _observation(
    run: Mapping[str, Any],
    scenario: Mapping[str, Any],
    dataset_path: Path,
) -> Observation:
    attempted = float(run["attempted_compute_flops"])
    canonical = float(run["canonical_compute_flops"])
    values: dict[str, MeasuredValue] = {
        "held_out_final_nll": MeasuredValue(
            value=float(run["final_held_out_nll"]),
            unit="natural_log_unit_per_byte",
            uncertainty=MeasurementUncertainty(
                standard_deviation=float(
                    run["final_held_out_nll_standard_deviation"]
                ),
                notes="Dispersion across the frozen 64 held-out batches.",
            ),
        ),
        "attempted_compute_flops": MeasuredValue(
            value=attempted,
            unit="FLOP",
            uncertainty=MeasurementUncertainty(
                lower_bound=attempted,
                upper_bound=attempted,
                notes="Modeled exactly from parameter and attempted-token counts.",
            ),
        ),
        "canonical_compute_flops": MeasuredValue(
            value=canonical,
            unit="FLOP",
            uncertainty=MeasurementUncertainty(
                lower_bound=canonical,
                upper_bound=canonical,
                notes="Modeled exactly from the completed canonical-work frontier.",
            ),
        ),
        "opportunity_ticks_to_equal_work": MeasuredValue(
            value=float(run["opportunity_ticks_elapsed"]),
            unit="opportunity_tick",
            uncertainty=MeasurementUncertainty(
                lower_bound=float(run["opportunity_ticks_elapsed"]),
                upper_bound=float(run["opportunity_ticks_elapsed"]),
                notes="Exact simulated opportunity count, not datacenter wall time.",
            ),
        ),
    }
    energy = run["energy"]["idle_subtracted_energy_j"]
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
            "loss": "fixed 64-batch held-out byte-NLL suite",
            "time": "exact simulated opportunity ticks plus local active segments",
            "energy": "training-only NVML board power with idle subtraction",
            "flops": "6 * parameter_count * attempted or canonical tokens",
        },
        provenance=Provenance(
            source="GPUSTACK E001-LC3 local measured training run",
            uri=str(dataset["uri"]),
            checksum=f"sha256:{lc1._sha256_file(dataset_path)}",
            retrieved_at=datetime(2026, 7, 12, tzinfo=timezone.utc),
            notes=(
                "Raw dataset stayed outside the repository.",
                "Serial GPU measurements do not establish simultaneous datacenter performance.",
            ),
        ),
        metadata={
            "split": run["split"],
            "policy_id": run["policy_id"],
            "interrupted": run["interrupted"],
            "equal_work_target_reached": run["target_reached"],
            "warm_checkpoint_sha256": run["warm_checkpoint_sha256"],
            "raw_local_active_seconds": run["local_active_seconds"],
            "raw_training_device_energy_j": energy,
            "raw_harness_metric_boundary": (
                "Point records remain in run data and metadata because no "
                "instrument-calibration uncertainty interval is available."
            ),
        },
    )


def _bridge(
    recovery_result: Mapping[str, Any],
    evaluation_runs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    bridge = lc2._mechanics_bridge(recovery_result, evaluation_runs)
    bridge["plain_boundary"] = (
        "Modeled repeated-trace sensitivity conditioned on the observed LC3 "
        "equal-canonical-work endpoint. Not measured datacenter performance."
    )
    bridge["conditioning"] = "observed_equal_canonical_work_frontier"
    return bridge


def run_e001_lc3_equal_work(
    scenario_path: str | Path,
    dataset_path: str | Path,
) -> dict[str, Any]:
    scenario_file = Path(scenario_path)
    scenario = json.loads(scenario_file.read_text(encoding="utf-8"))
    if scenario.get("schema") != "gpu-stack.e001-equal-work-scenario.v1":
        raise ValueError("unsupported E001-LC3 scenario schema")
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
        raise ValueError("source LC1 result does not match frozen LC3 identity")
    source_recovery = json.loads(
        Path(scenario["source_recovery_result"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    if source_recovery.get("artifact_sha256") != scenario[
        "source_recovery_result"
    ]["artifact_sha256"]:
        raise ValueError("source recovery result does not match frozen LC3 identity")
    source_lc2: list[dict[str, Any]] = []
    for reference in scenario["source_lc2_protocol_results"]:
        payload = json.loads(Path(reference["path"]).read_text(encoding="utf-8"))
        if payload.get("artifact_sha256") != reference["artifact_sha256"]:
            raise ValueError("source LC2 protocol result identity mismatch")
        source_lc2.append(
            {
                "path": reference["path"],
                "artifact_sha256": payload["artifact_sha256"],
                "conclusion": payload["summary"]["conclusion"],
            }
        )

    power_sampler = lc1._PowerSampler()
    warm_checkpoint, warm_summary = lc2._build_warm_checkpoint(
        scenario, corpora, power_sampler
    )
    print(
        "LC3 warm checkpoint completed "
        f"ticks={warm_summary['ticks']} "
        f"state={warm_summary['checkpoint_sha256'][:12]} "
        f"late_gate={warm_summary['late_window']['late_stage_gate_passed']}",
        flush=True,
    )
    if not warm_summary["late_window"]["late_stage_gate_passed"]:
        payload = {
            "schema": SCHEMA,
            "experiment_id": "E001-LC3",
            "scenario_id": scenario["scenario_id"],
            "scenario_sha256": _content_hash(scenario),
            "engine": _engine_identity(),
            "source_lc2_protocol_results": source_lc2,
            "warm_start": warm_summary,
            "runs": [],
            "observations": [],
            "summary": {
                "candidate_survives_lc3": False,
                "conclusion": "protocol_failed_warm_start_not_late_stage",
                "falsifier_results": {"late_stage_warm_start": False},
            },
            "mechanics_bridge": _bridge(source_recovery, []),
        }
        payload["artifact_sha256"] = _content_hash(payload)
        return payload

    calibration_runs: list[dict[str, Any]] = []
    calibration_arms = tuple(scenario["calibration"]["arms"])
    for stratum_index, stratum in enumerate(scenario["calibration"]["strata"]):
        rotation = stratum_index % len(calibration_arms)
        ordered = calibration_arms[rotation:] + calibration_arms[:rotation]
        for arm in ordered:
            run = _run_equal_work_arm(
                scenario,
                corpora,
                warm_checkpoint,
                stratum,
                arm,
                power_sampler,
                split="calibration",
            )
            calibration_runs.append(run)
            print(
                "LC3 calibration completed "
                f"{run['run_id']} nll={run['final_held_out_nll']:.6f}",
                flush=True,
            )

    evaluation_runs: list[dict[str, Any]] = []
    arms = tuple(scenario["evaluation_arms"])
    for stratum_index, stratum in enumerate(scenario["evaluation_strata"]):
        rotation = stratum_index % len(arms)
        ordered = arms[rotation:] + arms[:rotation]
        for arm in ordered:
            run = _run_equal_work_arm(
                scenario,
                corpora,
                warm_checkpoint,
                stratum,
                arm,
                power_sampler,
                split="evaluation",
            )
            evaluation_runs.append(run)
            print(
                "LC3 evaluation completed "
                f"{run['run_id']} wall={run['opportunity_ticks_elapsed']} "
                f"logical={run['logical_ticks_completed']} "
                f"nll={run['final_held_out_nll']:.6f} "
                f"attempted={run['attempted_tokens']} "
                f"energy_j={run['energy']['idle_subtracted_energy_j']}",
                flush=True,
            )

    summary = _summarize(scenario, calibration_runs, evaluation_runs)
    runs = tuple(calibration_runs) + tuple(evaluation_runs)
    observations = tuple(
        _observation(run, scenario, dataset_file) for run in runs
    )
    split = CalibrationEvaluationSplit.from_ids(
        split_id="e001-lc3-calibration-evaluation-v1",
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
            "equal_canonical_work_target": True,
            "shared_warm_checkpoint": warm_summary["checkpoint_sha256"],
            "evaluation_schedules_reused_unchanged_from_lc1": True,
        },
    )
    split.validate_observations(observations, require_complete_partition=True)
    _, _, torch, _, _ = lc1._require_dependencies()
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "experiment_id": "E001-LC3",
        "scenario_id": scenario["scenario_id"],
        "scenario_sha256": _content_hash(scenario),
        "engine": _engine_identity(),
        "source_lc2_protocol_results": source_lc2,
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
            "gpu_compute_capability": list(torch.cuda.get_device_capability(0)),
            "nvml_power_available": power_sampler.available,
            "idle_power_w": power_sampler.idle_power_w,
        },
        "study": {
            "model": scenario["model"],
            "optimization": scenario["optimization"],
            "calibration": scenario["calibration"],
            "evaluation_strata": scenario["evaluation_strata"],
            "evaluation_arms": scenario["evaluation_arms"],
            "falsifiers": scenario["falsifiers"],
        },
        "warm_start": warm_summary,
        "split": split.to_dict(),
        "runs": list(runs),
        "observations": [observation.to_dict() for observation in observations],
        "summary": summary,
        "mechanics_bridge": _bridge(source_recovery, evaluation_runs),
        "result_scope": {
            "overall_e001_status": (
                "candidate_ready_for_transfer_panels"
                if summary["candidate_survives_lc3"]
                else "candidate_falsified_or_redirect_required"
            ),
            "supported": [
                "paired late-stage held-out NLL at equal canonical work",
                "paired attempted work and opportunity ticks across six frozen schedules",
                "local RTX training-only time and sampled device energy",
            ],
            "unsupported": [
                "frontier-scale convergence or capability",
                "real simultaneous multi-site speedup, WAN, or storage performance",
                "measured host, cooling, or facility energy",
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
    "run_e001_lc3_equal_work",
]
