"""E002-PW2: the cumulative-energy repeat of the frozen cadence factorial.

PW1 ran the right 2x2 comparison (checkpoint cadence x continuation) but its
board-power sensor updated too slowly to admit the energy readings. PW2
reruns the identical frozen design, this time reading a monotonic cumulative
energy counter, so the energy comparison can finally be measurement-valid.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

from . import e001_lc2_quality_target as lc2
from . import e001_learning_calibration as lc1
from . import e002_checkpoint_power as pw1


SCHEMA = "gpu-stack.e002-checkpoint-energy-evidence.v2"
ENGINE_ID = "gpu-stack.e002-pw2-cumulative-energy.v2"


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
    return hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()


def _engine_identity() -> dict[str, Any]:
    components = {
        "cumulative_energy_engine": _file_hash(Path(__file__)),
        "pw1_factorial_runtime": _file_hash(Path(pw1.__file__)),
        "quality_target_runtime": _file_hash(Path(lc2.__file__)),
        "learning_runtime": _file_hash(Path(lc1.__file__)),
    }
    return {
        "engine_id": ENGINE_ID,
        "source_sha256": components["cumulative_energy_engine"],
        "component_source_sha256": components,
        "bundle_sha256": hashlib.sha256(
            _canonical_json(components).encode("utf-8")
        ).hexdigest(),
    }


class _CumulativeSampler(pw1._TraceSampler):
    def _read(self) -> dict[str, Any]:
        point = super()._read()
        assert self._pynvml is not None and self._handle is not None
        point["total_energy_mj"] = self._safe(
            lambda: int(
                self._pynvml.nvmlDeviceGetTotalEnergyConsumption(
                    self._handle
                )
            )
        )
        return point


def _counter_intervals(trace: Mapping[str, Any]) -> list[dict[str, float]]:
    points = [
        point
        for point in trace["points"]
        if point.get("total_energy_mj") is not None
    ]
    if not points:
        return []
    intervals: list[dict[str, float]] = []
    previous_time = float(points[0]["timestamp"])
    previous_energy = int(points[0]["total_energy_mj"])
    for point in points[1:]:
        energy = int(point["total_energy_mj"])
        if energy == previous_energy:
            continue
        timestamp = float(point["timestamp"])
        if timestamp > previous_time and energy > previous_energy:
            intervals.append(
                {
                    "start": previous_time,
                    "end": timestamp,
                    "energy_j": (energy - previous_energy) / 1000.0,
                    "power_w": (
                        (energy - previous_energy)
                        / 1000.0
                        / (timestamp - previous_time)
                    ),
                }
            )
        previous_time = timestamp
        previous_energy = energy
    return intervals


def _baseline_at(
    timestamp: float,
    active_start: float,
    active_end: float,
    pre_power: float,
    post_power: float,
) -> float:
    if active_end <= active_start:
        return pre_power
    fraction = min(
        1.0,
        max(0.0, (timestamp - active_start) / (active_end - active_start)),
    )
    return pre_power + fraction * (post_power - pre_power)


def _trace_baselines(
    trace: Mapping[str, Any], intervals: Sequence[Mapping[str, float]]
) -> tuple[float | None, float | None, int, int]:
    active_start = float(trace["active_start_seconds"])
    active_end = float(trace["active_end_seconds"])
    pre = [
        float(interval["power_w"])
        for interval in intervals
        if float(interval["end"]) <= active_start
    ]
    post = [
        float(interval["power_w"])
        for interval in intervals
        if float(interval["start"]) >= active_end
    ]
    return (
        statistics.median(pre) if pre else None,
        statistics.median(post) if post else None,
        len(pre),
        len(post),
    )


def _estimate_logger(
    calibration_runs: Sequence[Mapping[str, Any]],
    scenario: Mapping[str, Any],
) -> dict[str, Any]:
    poll_seconds = float(
        scenario["cumulative_meter"]["requested_poll_interval_ms"]
    ) / 1000.0
    all_update_periods: list[float] = []
    update_count = 0
    poll_count = 0
    for run in calibration_runs:
        trace = run["telemetry_trace"]
        intervals = _counter_intervals(trace)
        poll_count += len(trace["points"])
        update_count += len(intervals)
        all_update_periods.extend(
            float(interval["end"]) - float(interval["start"])
            for interval in intervals
        )
    if not all_update_periods:
        raise RuntimeError("cumulative counter produced no calibration updates")
    sorted_periods = sorted(all_update_periods)
    return {
        "selected_lag_seconds": 0.0,
        "selected_correlation": None,
        "allocation_rule": (
            "counter increment supported on interval between adjacent changed readings"
        ),
        "effective_update_period_seconds": statistics.median(
            all_update_periods
        ),
        "effective_update_interval_count": len(all_update_periods),
        "poll_count": poll_count,
        "effective_update_count": update_count,
        "update_gap_seconds": {
            "minimum": sorted_periods[0],
            "median": statistics.median(sorted_periods),
            "maximum": sorted_periods[-1],
        },
        "requested_poll_seconds": poll_seconds,
        "calibration_blocks": sorted(
            {str(run["block_id"]) for run in calibration_runs}
        ),
        "meter": "NVML cumulative GPU energy counter",
        "frozen_before_evaluation": True,
    }


def _analyze_trace(
    trace: Mapping[str, Any], *, logger_lag_seconds: float
) -> dict[str, Any]:
    intervals = _counter_intervals(trace)
    active_start = float(trace["active_start_seconds"])
    active_end = float(trace["active_end_seconds"])
    pre, post, pre_count, post_count = _trace_baselines(trace, intervals)
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
            "phase": window["phase"],
            "start": float(window["start"]) + logger_lag_seconds,
            "end": float(window["end"]) + logger_lag_seconds,
        }
        for window in raw_windows
    ]
    overlap_seconds = sum(
        max(0.0, float(left["end"]) - float(right["start"]))
        for left, right in zip(raw_windows, raw_windows[1:])
    )
    outside_seconds = sum(
        max(0.0, active_start - float(window["start"]))
        + max(0.0, float(window["end"]) - active_end)
        for window in raw_windows
    )
    energies = {phase: 0.0 for phase in pw1.PHASES}
    raw_phase_energies = {phase: 0.0 for phase in pw1.PHASES}
    durations = {phase: 0.0 for phase in pw1.PHASES}
    phase_update_counts = {phase: 0 for phase in pw1.PHASES}
    raw_energy = 0.0
    residual_energy = 0.0
    effective_updates = 0
    if pre is not None and post is not None:
        for interval in intervals:
            interval_start = float(interval["start"])
            interval_end = float(interval["end"])
            start = max(interval_start, active_start)
            end = min(interval_end, active_end)
            if end <= start:
                continue
            effective_updates += 1
            full_duration = interval_end - interval_start
            duration = end - start
            raw_segment = float(interval["energy_j"]) * duration / full_duration
            baseline_energy = 0.5 * (
                _baseline_at(
                    start, active_start, active_end, pre, post
                )
                + _baseline_at(
                    end, active_start, active_end, pre, post
                )
            ) * duration
            residual_segment = raw_segment - baseline_energy
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
                phase_update_counts[phase] += 1
                energies[phase] += residual_segment * overlap / duration
                raw_phase_energies[phase] += raw_segment * overlap / duration
            remainder = max(0.0, duration - covered)
            durations["runtime-control-remainder"] += remainder
            if remainder > 0.0:
                phase_update_counts["runtime-control-remainder"] += 1
            energies["runtime-control-remainder"] += (
                residual_segment * remainder / duration
            )
            raw_phase_energies["runtime-control-remainder"] += (
                raw_segment * remainder / duration
            )
    attributed = sum(energies.values())
    raw_attributed = sum(raw_phase_energies.values())
    closure = abs(raw_attributed - raw_energy) / max(
        1e-9, abs(raw_energy)
    )
    idle_closure = abs(attributed - residual_energy) / max(
        1e-9, abs(residual_energy)
    )
    points = [
        point
        for point in trace["points"]
        if point.get("total_energy_mj") is not None
    ]
    before = [
        point
        for point in points
        if float(point["timestamp"]) <= active_start
    ]
    after = [
        point
        for point in points
        if float(point["timestamp"]) >= active_end
    ]
    counter_start = int(before[-1]["total_energy_mj"]) if before else None
    counter_end = int(after[0]["total_energy_mj"]) if after else None
    return {
        "logger_lag_seconds": logger_lag_seconds,
        "raw_sample_count": len(trace["points"]),
        "effective_counter_update_count": effective_updates,
        "counter_interval_count": len(intervals),
        "pre_idle_update_count": pre_count,
        "post_idle_update_count": post_count,
        "pre_idle_power_w": pre,
        "post_idle_power_w": post,
        "raw_active_energy_j": raw_energy if intervals else None,
        "total_idle_subtracted_energy_j": (
            residual_energy if pre is not None and post is not None else None
        ),
        "raw_phase_energy_j": raw_phase_energies,
        "phase_idle_subtracted_energy_j": energies,
        "phase_duration_seconds": durations,
        "phase_counter_update_counts": phase_update_counts,
        "energy_closure_relative_error": closure,
        "idle_subtracted_energy_closure_relative_error": idle_closure,
        "counter_start_mj": counter_start,
        "counter_end_mj": counter_end,
        "counter_brackets_run": counter_start is not None and counter_end is not None,
        "counter_monotonic": all(
            int(right["total_energy_mj"]) >= int(left["total_energy_mj"])
            for left, right in zip(points, points[1:])
        ),
        "exclusive_phase_overlap_seconds": overlap_seconds,
        "phase_outside_active_window_seconds": outside_seconds,
        "phase_partition_valid": overlap_seconds <= 1e-9
        and outside_seconds <= 1e-6,
    }


def _normalize_counter_trace(run: dict[str, Any]) -> None:
    previous: int | None = None
    for point in run["telemetry_trace"]["points"]:
        energy = point.get("total_energy_mj")
        point["cumulative_gpu_board_energy_mj"] = energy
        point["instantaneous_gpu_board_power_w_ancillary"] = point.get(
            "gpu_board_power_w"
        )
        point["effective_counter_update"] = bool(
            energy is not None
            and previous is not None
            and int(energy) > previous
        )
        if energy is not None:
            previous = int(energy)


def _attach_attribution(
    run: dict[str, Any],
    logger: Mapping[str, Any],
) -> None:
    _normalize_counter_trace(run)
    analysis = _analyze_trace(
        run["telemetry_trace"],
        logger_lag_seconds=float(logger["selected_lag_seconds"]),
    )
    effective_period = max(
        1e-9, float(logger["effective_update_period_seconds"])
    )
    run.update(
        {
            "raw_trace_sha256": _content_hash(run["telemetry_trace"]),
            "raw_counter_trace_sha256": _content_hash(
                run["telemetry_trace"]
            ),
            "raw_sample_count": int(analysis["raw_sample_count"]),
            "raw_poll_count": int(analysis["raw_sample_count"]),
            "effective_power_update_count": int(
                analysis["effective_counter_update_count"]
            ),
            "effective_counter_update_count": int(
                analysis["effective_counter_update_count"]
            ),
            "counter_interval_count": int(
                analysis["counter_interval_count"]
            ),
            "phase_intervals": run["telemetry_trace"]["phase_windows"],
            "phase_metrics": {
                phase: {
                    "duration_seconds": float(
                        analysis["phase_duration_seconds"][phase]
                    ),
                    "energy_j": float(
                        analysis["raw_phase_energy_j"][phase]
                    ),
                    "energy_j_per_canonical_token": float(
                        analysis["raw_phase_energy_j"][phase]
                    )
                    / max(1.0, float(run["canonical_tokens"])),
                    "idle_subtracted_energy_j_sensitivity": float(
                        analysis["phase_idle_subtracted_energy_j"][phase]
                    ),
                    "idle_subtracted_energy_j": float(
                        analysis["raw_phase_energy_j"][phase]
                    ),
                    "idle_subtracted_energy_j_per_canonical_token": float(
                        analysis["raw_phase_energy_j"][phase]
                    )
                    / max(1.0, float(run["canonical_tokens"])),
                    "counter_update_count": int(
                        analysis["phase_counter_update_counts"][phase]
                    ),
                    "pooled_effective_update_equivalents": float(
                        analysis["phase_duration_seconds"][phase]
                    )
                    / effective_period,
                }
                for phase in pw1.PHASES
            },
            "phase_energy_closure_relative_error": float(
                analysis["energy_closure_relative_error"]
            ),
            "total_gpu_board_energy_j": analysis["raw_active_energy_j"],
            "raw_run_energy_j": analysis["raw_active_energy_j"],
            "idle_subtracted_energy_j_sensitivity": analysis[
                "total_idle_subtracted_energy_j"
            ],
            "idle_subtracted_gpu_board_energy_j": analysis[
                "raw_active_energy_j"
            ],
            "counter_start_mj": analysis["counter_start_mj"],
            "counter_end_mj": analysis["counter_end_mj"],
            "counter_brackets_run": analysis["counter_brackets_run"],
            "counter_monotonic": analysis["counter_monotonic"],
            "phase_partition_valid": bool(
                analysis["phase_partition_valid"]
            ),
            "phase_overlap_seconds": float(
                analysis["exclusive_phase_overlap_seconds"]
            ),
            "phase_outside_run_seconds": float(
                analysis["phase_outside_active_window_seconds"]
            ),
            "idle_baseline": {
                "pre_power_w": analysis["pre_idle_power_w"],
                "post_power_w": analysis["post_idle_power_w"],
                "pre_update_count": analysis["pre_idle_update_count"],
                "post_update_count": analysis["post_idle_update_count"],
            },
            "logger_delay_ms": float(logger["selected_lag_seconds"])
            * 1000.0,
            "meter": "NVML cumulative GPU energy counter",
        }
    )


def _summarize(
    scenario: Mapping[str, Any],
    calibration_runs: Sequence[Mapping[str, Any]],
    evaluation_runs: Sequence[Mapping[str, Any]],
    logger: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    compatibility_scenario = json.loads(json.dumps(scenario))
    compatibility_invalidators = compatibility_scenario[
        "measurement_invalidators"
    ]
    compatibility_invalidators.setdefault(
        "minimum_effective_power_updates_per_evaluation_arm",
        compatibility_scenario["phase_support"][
            "minimum_effective_counter_updates_per_evaluation_arm"
        ],
    )
    compatibility_invalidators.setdefault(
        "minimum_pooled_effective_updates_per_cadence_phase",
        compatibility_scenario["phase_support"][
            "minimum_pooled_updates_per_cadence_checkpoint_related_group"
        ],
    )
    compatibility_invalidators.setdefault(
        "maximum_absolute_logger_delay_ms", 0.0
    )
    compatibility_scenario["estimands"].setdefault(
        "checkpoint_related_phases",
        compatibility_scenario["phase_support"][
            "checkpoint_related_group"
        ],
    )
    compatibility_mechanism = compatibility_scenario[
        "mechanism_falsifiers"
    ]
    compatibility_mechanism.setdefault(
        "total_interaction_lower_bound_gt",
        compatibility_mechanism[
            "primary_total_interaction_lower_bound_gt"
        ],
    )
    compatibility_mechanism.setdefault(
        "checkpoint_related_interaction_lower_bound_gt",
        compatibility_mechanism[
            "supported_checkpoint_related_group_interaction_lower_bound_gt"
        ],
    )
    compatibility_salvage = compatibility_scenario["salvage_falsifiers"]
    compatibility_salvage.setdefault(
        "sparse_continue_to_sparse_restart_device_energy_ratio_upper_bound_lte",
        compatibility_salvage[
            "sparse_continue_to_sparse_restart_cumulative_energy_ratio_upper_bound_lte"
        ],
    )
    measurement, summary = pw1._summarize(
        compatibility_scenario,
        calibration_runs,
        evaluation_runs,
        logger,
    )
    all_runs = tuple(calibration_runs) + tuple(evaluation_runs)
    invalidator_spec = scenario["phase_support"]
    minimum_arm_updates = int(
        invalidator_spec[
            "minimum_effective_counter_updates_per_evaluation_arm"
        ]
    )
    evaluation_updates_valid = all(
        int(run["effective_counter_update_count"]) >= minimum_arm_updates
        for run in evaluation_runs
    )
    effective_period = max(
        1e-9, float(logger["effective_update_period_seconds"])
    )
    minimum_pooled = float(
        invalidator_spec[
            "minimum_pooled_updates_per_cadence_checkpoint_related_group"
        ]
    )
    minimum_snapshot = float(
        invalidator_spec[
            "minimum_pooled_updates_per_cadence_checkpoint_snapshot"
        ]
    )
    checkpoint_phases = tuple(
        scenario["phase_support"]["checkpoint_related_group"]
    )
    pooled: dict[str, Any] = {}
    pooled_valid = True
    for cadence in (pw1.SPARSE, pw1.DENSE):
        cadence_runs = [
            run for run in all_runs if run["checkpoint_cadence"] == cadence
        ]
        snapshot_duration = sum(
            float(
                run["phase_metrics"]["checkpoint-snapshot"][
                    "duration_seconds"
                ]
            )
            for run in cadence_runs
        )
        checkpoint_group_duration = sum(
            float(run["phase_metrics"][phase]["duration_seconds"])
            for run in cadence_runs
            for phase in checkpoint_phases
        )
        snapshot_updates = snapshot_duration / effective_period
        group_updates = checkpoint_group_duration / effective_period
        pooled[cadence] = {
            "checkpoint_snapshot_update_equivalents": snapshot_updates,
            "checkpoint_related_group_update_equivalents": group_updates,
            "minimum_snapshot_required": minimum_snapshot,
            "minimum_group_required": minimum_pooled,
            "individual_rare_phase_estimates_are_exploratory": True,
        }
        pooled_valid &= (
            snapshot_updates >= minimum_snapshot
            and group_updates >= minimum_pooled
        )
    individual_support: dict[str, Any] = {}
    individual_floor = float(
        invalidator_spec[
            "individual_phase_causal_support_updates_per_cadence"
        ]
    )
    individual_phases = tuple(
        invalidator_spec["individual_phase_support_scope"]
    )
    for cadence in (pw1.SPARSE, pw1.DENSE):
        cadence_runs = [
            run for run in all_runs if run["checkpoint_cadence"] == cadence
        ]
        individual_support[cadence] = {}
        for phase in individual_phases:
            equivalents = sum(
                float(run["phase_metrics"][phase]["duration_seconds"])
                for run in cadence_runs
            ) / effective_period
            individual_support[cadence][phase] = {
                "effective_update_equivalents": equivalents,
                "minimum_required": individual_floor,
                "evidence_class": (
                    "causal_phase_supported"
                    if equivalents >= individual_floor
                    else invalidator_spec[
                        "individual_phase_below_floor_evidence_class"
                    ]
                ),
            }
    for run in all_runs:
        cadence = str(run["checkpoint_cadence"])
        run["individual_phase_evidence_class"] = {
            phase: individual_support[cadence].get(
                phase,
                {
                    "evidence_class": "group_supported_or_not_primary"
                },
            )["evidence_class"]
            for phase in pw1.PHASES
        }
        run["phase_counter_update_counts"] = {
            phase: int(run["phase_metrics"][phase]["counter_update_count"])
            for phase in pw1.PHASES
        }
        run["phase_energy_j"] = {
            phase: float(run["phase_metrics"][phase]["energy_j"])
            for phase in pw1.PHASES
        }
    measurement["invalidators"][
        "insufficient_evaluation_power_updates"
    ] = not evaluation_updates_valid
    measurement["invalidators"][
        "insufficient_pooled_cadence_phase_updates"
    ] = not pooled_valid
    measurement["cadence_group_effective_update_equivalents"] = pooled
    measurement["individual_phase_support_by_cadence"] = individual_support
    measurement["meter"] = "NVML cumulative GPU energy counter"
    measurement["invalidators"]["counter_not_monotonic"] = not all(
        bool(run["counter_monotonic"]) for run in all_runs
    )
    measurement["invalidators"]["counter_does_not_bracket_run"] = not all(
        bool(run["counter_brackets_run"]) for run in all_runs
    )
    measurement["invalidators"]["run_counter_delta_non_positive"] = not all(
        run["raw_run_energy_j"] is not None
        and float(run["raw_run_energy_j"]) > 0.0
        for run in all_runs
    )
    measurement["valid"] = not any(
        measurement["invalidators"].values()
    )
    mechanism_survives = all(
        summary["mechanism_falsifier_results"].values()
    )
    salvage_survives = all(summary["salvage_falsifier_results"].values())
    lc3_penalty = bool(
        summary["lc3_corner_reproduction"]["penalty_reproduced"]
    )
    if not measurement["valid"]:
        conclusion = "measurement_invalid"
    elif not lc3_penalty:
        conclusion = "lc3_energy_penalty_not_reproduced"
    elif not mechanism_survives:
        conclusion = "continuation_energy_not_attributed_to_checkpoint_cadence"
    elif salvage_survives:
        conclusion = "checkpoint_cadence_attributed_sparse_continuation_survives"
    else:
        conclusion = "checkpoint_cadence_partial_cause_candidate_still_fails"
    summary["checkpoint_cadence_attributed"] = mechanism_survives
    summary["sparse_continuation_survives"] = salvage_survives
    summary["conclusion"] = conclusion
    summary["individual_rare_phase_claim_status"] = (
        "exploratory unless its pooled counter-update support clears the frozen threshold"
    )
    summary["checkpoint_snapshot_interaction"] = summary[
        "phase_interactions"
    ]["checkpoint-snapshot"]
    summary["checkpoint_related_group_interaction"] = summary[
        "checkpoint_related_interaction"
    ]
    np, _, _, _, _ = lc1._require_dependencies()
    evaluation_lookup = {
        (str(run["block_id"]), str(run["arm_code"])): run
        for run in evaluation_runs
    }
    idle_effects: list[float] = []
    for block in scenario["splits"]["evaluation"]["blocks"]:
        block_id = str(block["block_id"])
        values = {
            code: float(
                evaluation_lookup[(block_id, code)][
                    "idle_subtracted_energy_j_sensitivity"
                ]
            )
            / float(evaluation_lookup[(block_id, code)]["canonical_tokens"])
            for code in "ABCD"
        }
        idle_effects.append(
            (values["D"] - values["C"])
            - (values["B"] - values["A"])
        )
    summary["idle_subtracted_interaction_sensitivity"] = pw1._interval(
        np, idle_effects, scenario, 70
    )
    return measurement, summary


def _validate_source_bindings(scenario: Mapping[str, Any]) -> dict[str, Any]:
    checked: dict[str, Any] = {}
    for binding_id, binding in scenario["source_bindings"].items():
        if not isinstance(binding, Mapping) or "path" not in binding:
            continue
        payload = json.loads(
            Path(str(binding["path"])).read_text(encoding="utf-8")
        )
        expected = binding.get("artifact_sha256")
        if expected is None:
            continue
        if payload.get("artifact_sha256") == expected:
            actual = payload["artifact_sha256"]
        else:
            actual = _content_hash(payload)
        if actual != expected:
            raise ValueError(f"E002-PW2 source binding mismatch: {binding_id}")
        checked[binding_id] = {
            "path": binding["path"],
            "artifact_sha256": expected,
        }
    return checked


def run_e002_cumulative_energy(
    scenario_path: str | Path,
    dataset_path: str | Path,
) -> dict[str, Any]:
    scenario_file = Path(scenario_path)
    scenario = json.loads(scenario_file.read_text(encoding="utf-8"))
    if scenario.get("schema") != "gpu-stack.e002-checkpoint-energy-scenario.v2":
        raise ValueError("unsupported E002-PW2 scenario schema")
    bindings = _validate_source_bindings(scenario)
    pw1_binding = scenario["source_bindings"]["pw1_result"]
    pw1_result = json.loads(
        Path(pw1_binding["path"]).read_text(encoding="utf-8")
    )
    pw1_failure_verified = (
        pw1_result["summary"]["conclusion"]
        == scenario["pw1_failure_binding"]["conclusion_must_equal"]
        and len(pw1_result["runs"])
        == int(scenario["pw1_failure_binding"]["completed_run_count"])
    )
    if not pw1_failure_verified:
        raise ValueError("E002-PW2 requires the bound PW1 measurement failure")
    dataset_file = Path(dataset_path)
    runtime_scenario = pw1._runtime_scenario(scenario)
    runtime_scenario["telemetry"] = {
        "idle_baseline": {
            "pre_run_plateau_seconds": float(
                scenario["cumulative_meter"]["idle_plateaus"][
                    "pre_run_seconds"
                ]
            ),
            "post_run_plateau_seconds": float(
                scenario["cumulative_meter"]["idle_plateaus"][
                    "post_run_seconds"
                ]
            ),
        }
    }
    corpora = lc1._load_byte_corpora(dataset_file, scenario["dataset"])
    warm_sampler = lc1._PowerSampler()
    warm_checkpoint, warm_summary = lc2._build_warm_checkpoint(
        runtime_scenario, corpora, warm_sampler
    )
    warm_hash = lc2._checkpoint_hash(warm_checkpoint)
    warm_binding = scenario["warm_start_binding"]
    warm_binding_passed = (
        warm_hash == warm_binding["checkpoint_sha256"]
        and int(warm_summary["ticks"]) == int(warm_binding["ticks"])
        and bool(warm_summary["late_window"]["late_stage_gate_passed"])
    )
    print(
        "E002-PW2 warm checkpoint completed "
        f"ticks={warm_summary['ticks']} state={warm_hash[:12]} "
        f"binding={warm_binding_passed}",
        flush=True,
    )
    if not warm_binding_passed:
        payload = {
            "schema": SCHEMA,
            "experiment_id": "E002-PW2",
            "scenario_id": scenario["scenario_id"],
            "scenario_sha256": _content_hash(scenario),
            "engine": _engine_identity(),
            "source_bindings": bindings,
            "warm_start": {
                **warm_summary,
                "observed_checkpoint_sha256": warm_hash,
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
        scenario["cumulative_meter"]["requested_poll_interval_ms"]
    ) / 1000.0
    sampler = _CumulativeSampler(poll_seconds)
    if not sampler.available:
        raise RuntimeError("E002-PW2 requires NVML")
    capability = sampler._safe(
        lambda: int(
            sampler._pynvml.nvmlDeviceGetTotalEnergyConsumption(
                sampler._handle
            )
        )
    )
    if capability is None:
        raise RuntimeError("NVML cumulative energy counter is not supported")
    arms = {str(arm["arm_id"]): arm for arm in scenario["arms"]}
    order = scenario["execution_order"]
    calibration_runs: list[dict[str, Any]] = []
    for block in scenario["splits"]["calibration"]["blocks"]:
        block_id = str(block["block_id"])
        order_id = str(order["block_assignment"][block_id])
        for position, arm_id in enumerate(order["orders"][order_id], start=1):
            run = pw1._run_arm(
                runtime_scenario,
                corpora,
                warm_checkpoint,
                block,
                arms[str(arm_id)],
                sampler,
                split="calibration",
            )
            run["execution_order_id"] = order_id
            run["execution_position"] = position
            calibration_runs.append(run)
            print(
                "E002-PW2 calibration completed "
                f"{run['run_id']} nll={run['final_held_out_nll']:.6f} "
                f"samples={len(run['telemetry_trace']['points'])}",
                flush=True,
            )
    logger = _estimate_logger(calibration_runs, scenario)
    for run in calibration_runs:
        _attach_attribution(run, logger)
    print(
        "E002-PW2 cumulative logger frozen "
        f"lag_ms={float(logger['selected_lag_seconds']) * 1000.0:.1f} "
        f"effective_ms={float(logger['effective_update_period_seconds']) * 1000.0:.1f}",
        flush=True,
    )

    evaluation_runs: list[dict[str, Any]] = []
    for block in scenario["splits"]["evaluation"]["blocks"]:
        block_id = str(block["block_id"])
        order_id = str(order["block_assignment"][block_id])
        for position, arm_id in enumerate(order["orders"][order_id], start=1):
            run = pw1._run_arm(
                runtime_scenario,
                corpora,
                warm_checkpoint,
                block,
                arms[str(arm_id)],
                sampler,
                split="evaluation",
            )
            run["execution_order_id"] = order_id
            run["execution_position"] = position
            _attach_attribution(run, logger)
            evaluation_runs.append(run)
            print(
                "E002-PW2 evaluation completed "
                f"{run['run_id']} ticks={run['opportunity_ticks_to_target']} "
                f"nll={run['final_held_out_nll']:.6f} "
                f"energy_j={run['idle_subtracted_gpu_board_energy_j']:.3f} "
                f"updates={run['effective_counter_update_count']}",
                flush=True,
            )
    measurement, summary = _summarize(
        scenario, calibration_runs, evaluation_runs, logger
    )
    _, _, torch, _, _ = lc1._require_dependencies()
    runs = tuple(calibration_runs) + tuple(evaluation_runs)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "experiment_id": "E002-PW2",
        "scenario_id": scenario["scenario_id"],
        "scenario_sha256": _content_hash(scenario),
        "engine": _engine_identity(),
        "source_bindings": bindings,
        "pw1_failure_binding_verified": pw1_failure_verified,
        "warm_start": {
            **warm_summary,
            "observed_checkpoint_sha256": warm_hash,
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
            "meter": "NVML cumulative GPU energy counter",
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
        "counter_calibration": {
            "api": scenario["cumulative_meter"]["primary_api"],
            "api_supported": True,
            "requested_poll_interval_ms": float(
                scenario["cumulative_meter"][
                    "requested_poll_interval_ms"
                ]
            ),
            "poll_count": int(logger["poll_count"]),
            "effective_update_count": int(logger["effective_update_count"]),
            "effective_update_period_ms": float(
                logger["effective_update_period_seconds"]
            )
            * 1000.0,
            "update_gap_ms": {
                key: float(value) * 1000.0
                for key, value in logger["update_gap_seconds"].items()
            },
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
        "phase_support": {
            "evaluation_arm_update_floor_passed": not measurement[
                "invalidators"
            ]["insufficient_evaluation_power_updates"],
            "pooled_checkpoint_snapshot_updates_by_cadence": {
                cadence: values[
                    "checkpoint_snapshot_update_equivalents"
                ]
                for cadence, values in measurement[
                    "cadence_group_effective_update_equivalents"
                ].items()
            },
            "pooled_checkpoint_related_updates_by_cadence": {
                cadence: values[
                    "checkpoint_related_group_update_equivalents"
                ]
                for cadence, values in measurement[
                    "cadence_group_effective_update_equivalents"
                ].items()
            },
            "individual_phase_support_by_cadence": measurement[
                "individual_phase_support_by_cadence"
            ],
        },
        "summary": summary,
        "facility_bridge": pw1._facility_bridge(
            scenario, evaluation_runs
        ),
        "evidence_boundary": {
            "observed": scenario["facility_bridge"]["local_observed"],
            "modeled": [
                "facility bridge equations conditioned on cumulative-energy local kernels"
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


__all__ = ["ENGINE_ID", "SCHEMA", "run_e002_cumulative_energy"]
