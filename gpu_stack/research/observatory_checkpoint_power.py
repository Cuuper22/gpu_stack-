"""Observatory projection for E002-PW1, the checkpoint-power experiment.

Verifies the PW1 result artifact's content hash, then emits two payloads:
a raw artifact carrying the unprocessed GPU-board telemetry traces, and a
three-depth observatory artifact (freshman / researcher / full-trace views).
The projection preserves the experiment's own verdict — including the fact
that the power sensor's effective update rate invalidated the energy
comparison — and stamps each payload with its SHA-256.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence


SCHEMA = "gpu-stack.causal-observatory.e002-checkpoint-power.v1"
RAW_SCHEMA = "gpu-stack.causal-observatory.e002-checkpoint-power.raw.v1"
RESULT_SCHEMA = "gpu-stack.e002-checkpoint-power-evidence.v1"


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _content_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _validate(result: Mapping[str, Any]) -> None:
    if result.get("schema") != RESULT_SCHEMA:
        raise ValueError("unsupported E002-PW1 result schema")
    expected = result.get("artifact_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("E002-PW1 artifact hash is missing")
    unhashed = dict(result)
    unhashed.pop("artifact_sha256", None)
    actual = _content_hash(unhashed)
    if actual != expected:
        raise ValueError(
            f"E002-PW1 content hash mismatch: expected {expected}, got {actual}"
        )


def _median(values: Sequence[float | int | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    return statistics.median(present) if present else None


def _run_summary(run: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "run_id": run["run_id"],
        "block_id": run["block_id"],
        "split": run["split"],
        "arm_id": run["arm_id"],
        "arm_code": run["arm_code"],
        "checkpoint_cadence": run["checkpoint_cadence"],
        "continuation": run["continuation"],
        "execution_order_id": run["execution_order_id"],
        "execution_position": run["execution_position"],
        "failure_schedule": run["failure_schedule"],
        "warm_checkpoint_sha256": run["warm_checkpoint_sha256"],
        "final_training_state_sha256": run["final_training_state_sha256"],
        "raw_trace_sha256": run["raw_trace_sha256"],
        "raw_sample_count": run["raw_sample_count"],
        "effective_power_update_count": run[
            "effective_power_update_count"
        ],
        "phase_energy_closure_relative_error": run[
            "phase_energy_closure_relative_error"
        ],
        "phase_partition_valid": run["phase_partition_valid"],
        "total_gpu_board_energy_j": run["total_gpu_board_energy_j"],
        "idle_subtracted_gpu_board_energy_j": run[
            "idle_subtracted_gpu_board_energy_j"
        ],
        "checkpoint_count": run["checkpoint_count"],
        "checkpoint_bytes": run["checkpoint_bytes"],
        "checkpoint_copy_seconds": run["checkpoint_copy_seconds"],
        "restore_seconds": run["restore_seconds"],
        "rejoin_seconds": run["rejoin_seconds"],
        "attempted_tokens": run["attempted_tokens"],
        "canonical_tokens": run["canonical_tokens"],
        "replayed_tokens": run["replayed_tokens"],
        "discarded_tokens": run["discarded_tokens"],
        "survivor_redistributed_tokens": run[
            "survivor_redistributed_tokens"
        ],
        "opportunity_ticks_to_target": run[
            "opportunity_ticks_to_target"
        ],
        "final_held_out_nll": run["final_held_out_nll"],
        "phase_metrics": run["phase_metrics"],
        "idle_baseline": run["idle_baseline"],
        "temperature": {
            "start_c": run["start_temperature_c"],
            "end_c": run["end_temperature_c"],
        },
        "diverged": run["diverged"],
    }


def build_e002_checkpoint_power_raw_artifact(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    _validate(result)
    payload: dict[str, Any] = {
        "schema": RAW_SCHEMA,
        "experiment_id": "E002-PW1",
        "source_result_sha256": result["artifact_sha256"],
        "logger_calibration": result["logger_calibration"],
        "runs": [
            {
                "run_id": run["run_id"],
                "block_id": run["block_id"],
                "arm_id": run["arm_id"],
                "raw_trace_sha256": run["raw_trace_sha256"],
                "telemetry_trace": run["telemetry_trace"],
                "phase_intervals": run["phase_intervals"],
            }
            for run in result["runs"]
        ],
        "boundary": (
            "Raw local RTX GPU-board telemetry. Host, memory-rail, storage, "
            "cooling, rack, and facility power were not observed."
        ),
    }
    payload["artifact_sha256"] = _content_hash(payload)
    return payload


def build_e002_checkpoint_power_observatory_artifact(
    result: Mapping[str, Any],
    *,
    source_uri: str | None = None,
    raw_trace_uri: str = "e002-checkpoint-power-raw-v1.json",
    raw_trace_sha256: str | None = None,
) -> dict[str, Any]:
    _validate(result)
    runs = tuple(result["runs"])
    evaluation = tuple(run for run in runs if run["split"] == "evaluation")
    measurement = result["measurement_validity"]
    summary = result["summary"]
    invalidators = [
        key for key, failed in measurement["invalidators"].items() if failed
    ]
    arm_rows: list[dict[str, Any]] = []
    for arm_code in "ABCD":
        arm_runs = [run for run in evaluation if run["arm_code"] == arm_code]
        arm_rows.append(
            {
                "arm_code": arm_code,
                "arm_id": arm_runs[0]["arm_id"],
                "checkpoint_cadence": arm_runs[0]["checkpoint_cadence"],
                "continuation": arm_runs[0]["continuation"],
                "run_count": len(arm_runs),
                "median_final_held_out_nll": _median(
                    [run["final_held_out_nll"] for run in arm_runs]
                ),
                "median_opportunity_ticks": _median(
                    [run["opportunity_ticks_to_target"] for run in arm_runs]
                ),
                "median_attempted_tokens": _median(
                    [run["attempted_tokens"] for run in arm_runs]
                ),
                "median_checkpoint_count": _median(
                    [run["checkpoint_count"] for run in arm_runs]
                ),
                "median_checkpoint_bytes": _median(
                    [run["checkpoint_bytes"] for run in arm_runs]
                ),
                "median_idle_subtracted_gpu_board_energy_j": _median(
                    [run["idle_subtracted_gpu_board_energy_j"] for run in arm_runs]
                ),
                "energy_admissible": False,
            }
        )
    requested_ms = float(
        result["study"].get("requested_sample_interval_ms", 20.0)
        if "requested_sample_interval_ms" in result["study"]
        else 20.0
    )
    effective_ms = float(
        result["logger_calibration"]["effective_update_period_ms"]
    )
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "experiment_id": "E002-PW1",
        "artifact_state": "measurement_invalid",
        "source_result": {
            "artifact_sha256": result["artifact_sha256"],
            "uri": source_uri,
            "schema": result["schema"],
        },
        "question": (
            "Is LC3's energy failure caused by survivor continuation itself, "
            "or by the denser checkpoint cadence coupled to it?"
        ),
        "freshman": {
            "headline": "We ran the right comparison, but the power sensor was too slow to answer it.",
            "plain_answer": (
                "All 32 planned GPU runs completed from the exact LC3 warm "
                "state. Polling every 20 ms did not create 20 ms evidence: "
                f"the board-power reading effectively changed about every {effective_ms:.0f} ms. "
                "The frozen rules therefore reject the energy comparison."
            ),
            "cards": [
                {
                    "label": "Factorial matrix",
                    "value": "32 / 32",
                    "detail": "four cadence-by-continuation arms across eight frozen blocks",
                    "state": "pass",
                },
                {
                    "label": "Warm-state identity",
                    "value": "matched",
                    "detail": result["warm_start"]["observed_checkpoint_sha256"][:12],
                    "state": "pass",
                },
                {
                    "label": "Requested polling",
                    "value": f"{requested_ms:.0f} ms",
                    "detail": "host requested sample interval",
                    "state": "neutral",
                },
                {
                    "label": "Effective sensor update",
                    "value": f"{effective_ms:.0f} ms",
                    "detail": f"{effective_ms / requested_ms:.1f}x coarser than requested",
                    "state": "fail",
                },
            ],
            "decision": (
                "Do not advance sparse continuation from these energy numbers. "
                "Move the same frozen design to an external or cumulative-energy meter."
            ),
        },
        "researcher": {
            "conclusion": summary["conclusion"],
            "measurement_valid": measurement["valid"],
            "invalidators": invalidators,
            "logger": {
                "requested_poll_ms": requested_ms,
                "selected_delay_ms": result["logger_calibration"][
                    "logger_delay_ms"
                ],
                "effective_update_period_ms": effective_ms,
                "selected_correlation": result["logger_calibration"][
                    "selected_correlation"
                ],
                "boundary_hit": abs(
                    float(result["logger_calibration"]["logger_delay_ms"])
                )
                >= 250.0,
            },
            "calibration_equivalence": measurement[
                "calibration_equivalence"
            ],
            "cadence_phase_effective_updates": measurement[
                "cadence_phase_effective_update_equivalents"
            ],
            "arm_rows": arm_rows,
            "block_interactions": summary[
                "evaluation_block_interactions"
            ],
            "raw_inadmissible_signals": {
                "primary_total_interaction": summary[
                    "primary_total_interaction"
                ],
                "checkpoint_related_interaction": summary[
                    "checkpoint_related_interaction"
                ],
                "lc3_corner_reproduction": summary[
                    "lc3_corner_reproduction"
                ],
                "sparse_continuation_salvage": summary[
                    "sparse_continuation_salvage"
                ],
                "label": (
                    "descriptive only; frozen measurement invalidators take precedence"
                ),
            },
            "mechanism_gates": summary[
                "mechanism_falsifier_results"
            ],
            "salvage_gates": summary["salvage_falsifier_results"],
        },
        "full_trace": {
            "run_count": len(runs),
            "run_ledger": [_run_summary(run) for run in runs],
            "raw_trace_artifact": {
                "uri": raw_trace_uri,
                "artifact_sha256": raw_trace_sha256,
                "run_count": len(runs),
                "point_count": sum(
                    int(run["raw_sample_count"]) for run in runs
                ),
            },
            "engine": result["engine"],
            "scenario_sha256": result["scenario_sha256"],
            "source_bindings": result["source_bindings"],
            "warm_start": result["warm_start"],
            "runtime": result["runtime"],
        },
        "facility_bridge": result["facility_bridge"],
        "evidence_boundary": result["evidence_boundary"],
        "next_experiment": {
            "id": "E002-PW2",
            "question": (
                "Does the same frozen 2x2 result survive phase-aligned external "
                "or cumulative GPU energy measurement with enough effective updates?"
            ),
            "do_not_change": [
                "LC3 warm checkpoint",
                "four arms",
                "six evaluation failure schedules",
                "equal canonical-work frontier",
                "learning, work, tick, and energy gates",
            ],
            "required_new_evidence": [
                "external high-rate GPU input power or supported cumulative energy counter",
                "simultaneous monotonic phase markers",
                "pre-registered minimum effective updates per arm and phase",
            ],
        },
    }
    payload["artifact_sha256"] = _content_hash(payload)
    return payload


def project_e002_checkpoint_power_result_file(
    result_path: str | Path,
    output_path: str | Path,
    raw_output_path: str | Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result_file = Path(result_path)
    result = json.loads(result_file.read_text(encoding="utf-8"))
    raw_payload = build_e002_checkpoint_power_raw_artifact(result)
    raw_file = Path(raw_output_path)
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.write_text(
        json.dumps(raw_payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    payload = build_e002_checkpoint_power_observatory_artifact(
        result,
        source_uri=result_file.as_posix(),
        raw_trace_uri=raw_file.name,
        raw_trace_sha256=raw_payload["artifact_sha256"],
    )
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return payload, raw_payload


__all__ = [
    "RAW_SCHEMA",
    "SCHEMA",
    "build_e002_checkpoint_power_observatory_artifact",
    "build_e002_checkpoint_power_raw_artifact",
    "project_e002_checkpoint_power_result_file",
]
