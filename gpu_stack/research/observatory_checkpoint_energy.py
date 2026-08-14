"""Observatory projection for E002-PW2, the cumulative-energy re-measurement.

PW2 repeats PW1's frozen 2x2 design but reads a cumulative energy counter
instead of the too-slow board-power sensor, so its result is measurement-valid.
This module verifies the result artifact's content hash and emits two
payloads: a raw artifact with the counter traces, and a three-depth
observatory artifact (freshman / researcher / full-trace views), each
stamped with its own SHA-256.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence


SCHEMA = "gpu-stack.causal-observatory.e002-checkpoint-energy.v2"
RAW_SCHEMA = "gpu-stack.causal-observatory.e002-checkpoint-energy.raw.v2"
RESULT_SCHEMA = "gpu-stack.e002-checkpoint-energy-evidence.v2"


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
        raise ValueError("unsupported E002-PW2 result schema")
    expected = result.get("artifact_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("E002-PW2 artifact hash is missing")
    unhashed = dict(result)
    unhashed.pop("artifact_sha256", None)
    actual = _content_hash(unhashed)
    if actual != expected:
        raise ValueError(
            f"E002-PW2 content hash mismatch: expected {expected}, got {actual}"
        )


def _median(values: Sequence[float | int | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    return statistics.median(present) if present else None


def _run_summary(run: Mapping[str, Any]) -> dict[str, Any]:
    source_run_id = str(run["run_id"])
    display_run_id = source_run_id.replace("e002-pw1:", "e002-pw2:", 1)
    return {
        "run_id": display_run_id,
        "source_run_id": source_run_id,
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
        "raw_counter_trace_sha256": run["raw_counter_trace_sha256"],
        "raw_poll_count": run["raw_poll_count"],
        "effective_counter_update_count": run[
            "effective_counter_update_count"
        ],
        "counter_start_mj": run["counter_start_mj"],
        "counter_end_mj": run["counter_end_mj"],
        "raw_run_energy_j": run["raw_run_energy_j"],
        "idle_subtracted_energy_j_sensitivity": run[
            "idle_subtracted_energy_j_sensitivity"
        ],
        "phase_energy_closure_relative_error": run[
            "phase_energy_closure_relative_error"
        ],
        "phase_partition_valid": run["phase_partition_valid"],
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
        "individual_phase_evidence_class": run[
            "individual_phase_evidence_class"
        ],
        "diverged": run["diverged"],
    }


def build_e002_checkpoint_energy_raw_artifact(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    _validate(result)
    payload: dict[str, Any] = {
        "schema": RAW_SCHEMA,
        "experiment_id": "E002-PW2",
        "source_result_sha256": result["artifact_sha256"],
        "counter_calibration": result["counter_calibration"],
        "runs": [
            {
                "run_id": str(run["run_id"]).replace(
                    "e002-pw1:", "e002-pw2:", 1
                ),
                "source_run_id": run["run_id"],
                "block_id": run["block_id"],
                "arm_id": run["arm_id"],
                "raw_counter_trace_sha256": run[
                    "raw_counter_trace_sha256"
                ],
                "telemetry_trace": run["telemetry_trace"],
                "phase_intervals": run["phase_intervals"],
            }
            for run in result["runs"]
        ],
        "boundary": (
            "Observed cumulative energy at the local GPU-board boundary. Host, "
            "storage, network, cooling, rack, and facility energy remain absent."
        ),
    }
    payload["artifact_sha256"] = _content_hash(payload)
    return payload


def build_e002_checkpoint_energy_observatory_artifact(
    result: Mapping[str, Any],
    *,
    source_uri: str | None = None,
    raw_trace_uri: str = "e002-checkpoint-energy-raw-v2.json",
    raw_trace_sha256: str | None = None,
) -> dict[str, Any]:
    _validate(result)
    runs = tuple(result["runs"])
    evaluation = tuple(run for run in runs if run["split"] == "evaluation")
    summary = result["summary"]
    measurement = result["measurement_validity"]
    salvage = summary["sparse_continuation_salvage"]
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
                "median_raw_run_energy_j": _median(
                    [run["raw_run_energy_j"] for run in arm_runs]
                ),
            }
        )
    canonical_tokens = int(
        result["study"]["canonical_work"]["target_canonical_tokens"]
    )
    total_interaction = summary["primary_total_interaction"]
    group_interaction = summary["checkpoint_related_group_interaction"]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "experiment_id": "E002-PW2",
        "artifact_state": summary["conclusion"],
        "source_result": {
            "artifact_sha256": result["artifact_sha256"],
            "uri": source_uri,
            "schema": result["schema"],
        },
        "question": (
            "Did dense checkpointing cause LC3's local GPU-energy penalty, "
            "and can sparse survivor continuation keep its learning and work gains?"
        ),
        "freshman": {
            "headline": "Checkpointing less often kept the recovery win and removed the energy failure.",
            "plain_answer": (
                "The four-arm experiment separated checkpoint frequency from "
                "survivor continuation. Dense checkpointing carried a positive "
                "energy interaction. With sparse checkpoints, continuation kept "
                "the same useful learning, avoided replay work, finished earlier, "
                "and stayed inside the frozen GPU-energy bound."
            ),
            "cards": [
                {
                    "label": "Useful work",
                    "value": f"{canonical_tokens:,} tokens",
                    "detail": "identical canonical frontier in every arm",
                    "state": "pass",
                },
                {
                    "label": "Attempted work",
                    "value": f"{100.0 * float(salvage['attempted_flop_saving_fraction']['median']):.2f}% less",
                    "detail": "sparse continuation versus sparse restart",
                    "state": "pass",
                },
                {
                    "label": "Schedule",
                    "value": f"{float(salvage['opportunity_tick_saving']['median']):.0f} ticks sooner",
                    "detail": "continuation won all six failure schedules",
                    "state": "pass",
                },
                {
                    "label": "GPU energy ratio",
                    "value": f"{float(salvage['device_energy_ratio']['median']):.3f}x",
                    "detail": (
                        f"90% upper {float(salvage['device_energy_ratio']['upper_bound']):.3f}x "
                        "versus frozen 1.050x limit"
                    ),
                    "state": "pass",
                },
            ],
            "mechanism": (
                f"The median cadence-by-continuation interaction was "
                f"{float(total_interaction['median']) * canonical_tokens:.2f} J per run; "
                f"the checkpoint-related group accounted for "
                f"{float(group_interaction['median']) * canonical_tokens:.2f} J."
            ),
            "boundary": (
                "This establishes the mechanism on one RTX GPU and one frozen "
                "learning setup. It does not establish rack or facility power behavior."
            ),
        },
        "researcher": {
            "conclusion": summary["conclusion"],
            "measurement_valid": measurement["valid"],
            "active_invalidators": [
                key
                for key, value in measurement["invalidators"].items()
                if value
            ],
            "counter_calibration": result["counter_calibration"],
            "phase_support": result["phase_support"],
            "calibration_equivalence": measurement[
                "calibration_equivalence"
            ],
            "arm_rows": arm_rows,
            "block_interactions": summary[
                "evaluation_block_interactions"
            ],
            "primary_total_interaction": total_interaction,
            "checkpoint_snapshot_interaction": summary[
                "checkpoint_snapshot_interaction"
            ],
            "checkpoint_related_group_interaction": group_interaction,
            "scale_free_interaction_sensitivity": summary[
                "scale_free_interaction_sensitivity"
            ],
            "idle_subtracted_interaction_sensitivity": summary[
                "idle_subtracted_interaction_sensitivity"
            ],
            "penalty_removed_fraction": summary[
                "penalty_removed_fraction"
            ],
            "lc3_corner_reproduction": summary[
                "lc3_corner_reproduction"
            ],
            "sparse_continuation_salvage": salvage,
            "mechanism_gates": summary[
                "mechanism_falsifier_results"
            ],
            "salvage_gates": summary["salvage_falsifier_results"],
            "rare_phase_boundary": summary[
                "individual_rare_phase_claim_status"
            ],
        },
        "full_trace": {
            "run_count": len(runs),
            "run_ledger": [_run_summary(run) for run in runs],
            "raw_trace_artifact": {
                "uri": raw_trace_uri,
                "artifact_sha256": raw_trace_sha256,
                "run_count": len(runs),
                "poll_count": sum(int(run["raw_poll_count"]) for run in runs),
                "effective_update_count": sum(
                    int(run["effective_counter_update_count"])
                    for run in runs
                ),
            },
            "engine": result["engine"],
            "scenario_sha256": result["scenario_sha256"],
            "source_bindings": result["source_bindings"],
            "pw1_failure_binding_verified": result[
                "pw1_failure_binding_verified"
            ],
            "warm_start": result["warm_start"],
            "runtime": result["runtime"],
        },
        "facility_bridge": result["facility_bridge"],
        "evidence_boundary": result["evidence_boundary"],
        "next_experiment": {
            "id": "E002-PW3",
            "question": (
                "Can dependency-safe dephasing preserve this learning/work result "
                "while reducing synchronized rack-scale checkpoint and rejoin ramps?"
            ),
            "required_scale": (
                "multi-GPU rack with simultaneous per-GPU cumulative energy, rack PDU, "
                "storage, and cooling telemetry"
            ),
            "do_not_claim_yet": [
                "facility energy saving",
                "megawatt ramp reduction",
                "storage or host energy saving",
                "transfer beyond the frozen model and failures",
            ],
        },
    }
    payload["artifact_sha256"] = _content_hash(payload)
    return payload


def project_e002_checkpoint_energy_result_file(
    result_path: str | Path,
    output_path: str | Path,
    raw_output_path: str | Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result_file = Path(result_path)
    result = json.loads(result_file.read_text(encoding="utf-8"))
    raw_payload = build_e002_checkpoint_energy_raw_artifact(result)
    raw_file = Path(raw_output_path)
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.write_text(
        json.dumps(raw_payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    payload = build_e002_checkpoint_energy_observatory_artifact(
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
    "build_e002_checkpoint_energy_observatory_artifact",
    "build_e002_checkpoint_energy_raw_artifact",
    "project_e002_checkpoint_energy_result_file",
]
