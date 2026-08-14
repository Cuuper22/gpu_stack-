"""Observatory projection for E002-PW3, the physical rack-dephasing experiment.

Verifies the PW3 result artifact's content hash and required sections, then
condenses it into a three-depth payload (freshman / researcher / full-trace
views) for the UI. Values and verdicts pass through from the source
artifact unchanged; the output is stamped with its own SHA-256.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA = "gpu-stack.causal-observatory.e002-rack-dephasing.v3"
RESULT_SCHEMA = "gpu-stack.e002-rack-dephasing-evidence.v3"


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
        raise ValueError("unsupported E002-PW3 result schema")
    if result.get("experiment_id") != "E002-PW3":
        raise ValueError("E002-PW3 result experiment_id is inconsistent")
    expected = result.get("artifact_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("E002-PW3 artifact hash is missing")
    unhashed = dict(result)
    unhashed.pop("artifact_sha256", None)
    actual = _content_hash(unhashed)
    if actual != expected:
        raise ValueError(
            f"E002-PW3 content hash mismatch: expected {expected}, got {actual}"
        )
    for key in (
        "sensor_manifest",
        "clock_alignment",
        "paired_blocks",
        "measurement_validity",
        "summary",
        "raw_trace_manifest",
        "evidence_boundary",
    ):
        if key not in result:
            raise ValueError(f"E002-PW3 result is missing {key}")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return value
    return ()


def _measurement_valid(measurement: Mapping[str, Any]) -> bool:
    if isinstance(measurement.get("valid"), bool):
        return bool(measurement["valid"])
    return measurement.get("status") == "valid"


def _active_invalidators(measurement: Mapping[str, Any]) -> list[str]:
    invalidators = measurement.get("invalidators")
    if isinstance(invalidators, Mapping):
        return [str(key) for key, active in invalidators.items() if active]
    if isinstance(invalidators, Sequence) and not isinstance(
        invalidators, (str, bytes, bytearray)
    ):
        return [str(item) for item in invalidators]
    active = measurement.get("active_invalidators")
    if isinstance(active, Sequence) and not isinstance(
        active, (str, bytes, bytearray)
    ):
        return [str(item) for item in active]
    return []


def _decision_id(summary: Mapping[str, Any]) -> str:
    decision = summary.get("decision")
    if isinstance(decision, Mapping):
        for key in ("conclusion", "decision", "status", "id"):
            value = decision.get(key)
            if isinstance(value, str) and value:
                return value
    if isinstance(decision, str):
        return decision
    return "unresolved"


def _next_experiment(decision: str, valid: bool) -> dict[str, Any]:
    if not valid or decision == "measurement_invalid":
        experiment_id = "E002-PW3"
        question = (
            "Can the same frozen blocks produce a complete physical measurement "
            "after the named sensor or clock failure is corrected?"
        )
    elif decision == "advance_to_multi_pdu_correlated_failure_pw4":
        experiment_id = "E002-PW4"
        question = (
            "Does the rack mechanism survive multiple PDU domains and correlated failures?"
        )
    elif decision == "reject_closed_loop_novelty":
        experiment_id = "E002-PW4"
        question = (
            "Does the simplest matching open-loop policy preserve the measured rack "
            "benefit across multiple PDU domains and correlated failures?"
        )
    elif decision == "publish_tradeoff_and_redirect":
        experiment_id = "E002-PW3B"
        question = (
            "Which measured systems cost caused the tradeoff, and can that cost be "
            "removed while preserving the observed electrical benefit?"
        )
    else:
        experiment_id = "E002-PW4-TOPOLOGY"
        question = (
            "Do topology-level synchronization events, rather than recovery slack, "
            "dominate the physical rack transient?"
        )
    return {
        "id": experiment_id,
        "question": question,
        "do_not_claim_yet": [
            "facility energy saving",
            "point-of-common-coupling spectral safety",
            "admission-capacity gain",
            "transfer to another rack, model, or failure family",
        ],
    }


def _comparison_metric(
    summary: Mapping[str, Any],
    comparison_id: str,
    metric_ids: Sequence[str],
) -> Mapping[str, Any]:
    comparisons = _mapping(summary.get("comparisons"))
    comparison = _mapping(comparisons.get(comparison_id))
    metrics = _mapping(comparison.get("metrics")) or comparison
    for metric_id in metric_ids:
        metric = metrics.get(metric_id)
        if isinstance(metric, Mapping):
            return metric
    return {}


def _effect_text(metric: Mapping[str, Any]) -> tuple[str, str]:
    value = metric.get("median_effect")
    interval = metric.get("confidence_interval_90")
    if not isinstance(value, (int, float)):
        return "unresolved", "no admissible paired estimate"
    kind = str(metric.get("effect_kind", "absolute_difference"))
    unit = str(metric.get("unit", ""))
    if kind == "relative_reduction":
        label = f"{100.0 * float(value):.1f}% lower"
    elif kind in {"relative_increase", "relative_change", "relative_regression"}:
        label = f"{100.0 * float(value):+.1f}%"
    else:
        label = f"{float(value):+.4g}{(' ' + unit) if unit else ''}"
    lower: float | None = None
    upper: float | None = None
    if isinstance(interval, Mapping):
        if isinstance(interval.get("lower"), (int, float)) and isinstance(
            interval.get("upper"), (int, float)
        ):
            lower = float(interval["lower"])
            upper = float(interval["upper"])
    elif isinstance(interval, Sequence) and len(interval) == 2 and all(
        isinstance(item, (int, float)) for item in interval
    ):
        lower, upper = float(interval[0]), float(interval[1])
    if lower is not None and upper is not None:
        if kind in {
            "relative_reduction",
            "relative_increase",
            "relative_change",
            "relative_regression",
        }:
            detail = f"90% interval {100.0 * lower:.1f}% to {100.0 * upper:.1f}%"
        else:
            suffix = f" {unit}" if unit else ""
            detail = f"90% interval {lower:.4g} to {upper:.4g}{suffix}"
    else:
        detail = "90% paired interval unavailable"
    return label, detail


def _semantic_violation_count(blocks: Sequence[Any]) -> int | None:
    values: list[int] = []
    for block in blocks:
        for arm in _sequence(_mapping(block).get("arms")):
            semantics = _mapping(_mapping(arm).get("semantics"))
            for key, value in semantics.items():
                if (
                    "violation" in str(key)
                    and not isinstance(value, bool)
                    and isinstance(value, (int, float))
                ):
                    values.append(int(value))
    return sum(values) if values else None


def _arm_projection(
    arm: Mapping[str, Any],
    *,
    include_display: bool = True,
) -> dict[str, Any]:
    event_summary = _mapping(arm.get("event_summary"))
    return {
        "arm_id": arm.get("arm_id"),
        "block_id": arm.get("block_id"),
        "split": arm.get("split"),
        "policy_id": arm.get("policy_id"),
        "started_at": arm.get("started_at"),
        "wall_seconds": arm.get("wall_seconds"),
        "useful_tokens": arm.get("useful_tokens"),
        "attempted_tokens": arm.get("attempted_tokens"),
        "survivor_redistributed_tokens": arm.get(
            "survivor_redistributed_tokens"
        ),
        "useful_token_throughput": arm.get("useful_token_throughput"),
        "rack_energy_j": arm.get("rack_energy_j"),
        "rack_energy_per_useful_token": arm.get(
            "rack_energy_per_useful_token"
        ),
        "p99_9_rack_ramp_w_per_s": arm.get("p99_9_rack_ramp_w_per_s"),
        "rack_spectral_energy_0_1_10_hz": arm.get(
            "rack_spectral_energy_0_1_10_hz"
        ),
        "state_flow_coincidence": arm.get("state_flow_coincidence"),
        "p95_recovery_time_s": arm.get("p95_recovery_time_s"),
        "final_held_out_nll": arm.get("final_held_out_nll"),
        "by_job": arm.get("by_job"),
        "semantics": arm.get("semantics"),
        "telemetry_quality": arm.get("telemetry_quality"),
        "event_summary": {
            "event_count": event_summary.get("event_count"),
            "counts_by_kind": event_summary.get("counts_by_kind"),
            "completed_count": event_summary.get("completed_count"),
            "failed_count": event_summary.get("failed_count"),
            "deadline_miss_count": event_summary.get("deadline_miss_count"),
            "display_events": (
                list(_sequence(event_summary.get("display_events")))
                if include_display
                else []
            ),
        },
        "display_trace": arm.get("display_trace") if include_display else None,
        "raw_trace_refs": arm.get("raw_trace_refs"),
    }


def _block_projection(
    block: Mapping[str, Any],
    *,
    include_display: bool = True,
) -> dict[str, Any]:
    return {
        "block_id": block.get("block_id"),
        "split": block.get("split"),
        "warm_state": block.get("warm_state"),
        "arm_order": block.get("arm_order"),
        "arms": [
            _arm_projection(_mapping(arm), include_display=include_display)
            for arm in _sequence(block.get("arms"))
        ],
    }


def _freshman_copy(
    *,
    valid: bool,
    decision: str,
    invalidators: Sequence[str],
) -> tuple[str, str]:
    if not valid:
        reason = ", ".join(invalidators) or "the required physical evidence was incomplete"
        return (
            "The rack experiment did not produce an admissible answer.",
            "The training run may have completed, but the rack claim is withheld "
            f"because {reason}. Missing rack evidence is not replaced by summed GPU power.",
        )
    normalized = decision.lower()
    if "pass" in normalized or "advance" in normalized:
        return (
            "Recovery work was separated without changing the work, and the rack waveform improved.",
            "The controller moved only dependency-safe checkpoint and rejoin work. "
            "The same useful tokens and learning commitments were preserved while the "
            "physical rack meter recorded the preregistered electrical improvement.",
        )
    if "simpler" in normalized or "closed_loop" in normalized:
        return (
            "The rack improved, but live feedback did not beat the simpler schedule.",
            "Timing recovery work helped, yet static cohorts or storage-only pacing "
            "matched the feedback controller. The physical result supports the simpler mechanism.",
        )
    if "reject" in normalized or "fail" in normalized or "fals" in normalized:
        return (
            "Legal recovery timing did not deliver the claimed rack benefit.",
            "The physical experiment kept the work and recovery obligations fixed, "
            "but the preregistered electrical or systems constraints failed. That is the result.",
        )
    return (
        "The physical rack evidence is complete, but the frontier claim remains unresolved.",
        "The observatory keeps the measured electrical effects beside learning, recovery, "
        "energy, and semantic constraints so the unresolved decision is visible.",
    )


def build_e002_rack_dephasing_observatory_artifact(
    result: Mapping[str, Any],
    *,
    source_uri: str | None = None,
) -> dict[str, Any]:
    _validate(result)
    measurement = _mapping(result["measurement_validity"])
    summary = _mapping(result["summary"])
    blocks = list(_sequence(result["paired_blocks"]))
    valid = _measurement_valid(measurement)
    invalidators = _active_invalidators(measurement)
    decision = _decision_id(summary)
    headline, plain_answer = _freshman_copy(
        valid=valid,
        decision=decision,
        invalidators=invalidators,
    )
    sync_comparison_id = "telemetry_feedback_vs_synchronized"
    ramp_metric = _comparison_metric(
        summary,
        sync_comparison_id,
        (
            "rack_ramp",
            "rack_ramp_reduction",
            "p99_9_rack_ramp_w_per_s",
        ),
    )
    spectral_metric = _comparison_metric(
        summary,
        sync_comparison_id,
        (
            "rack_spectral_energy",
            "rack_spectral_reduction",
            "rack_spectral_energy_0_1_10_hz",
        ),
    )
    throughput_metric = _comparison_metric(
        summary,
        sync_comparison_id,
        ("useful_token_throughput", "useful_token_throughput_regression"),
    )
    ramp_value, ramp_interval = _effect_text(ramp_metric)
    spectral_value, spectral_interval = _effect_text(spectral_metric)
    throughput_value, throughput_interval = _effect_text(throughput_metric)
    semantic_violations = _semantic_violation_count(blocks)
    semantic_gate = _mapping(
        _mapping(summary.get("gates")).get("semantic_invariants")
    )
    semantic_gate_raw = _mapping(summary.get("gates")).get(
        "semantic_invariants"
    )
    if semantic_violations is None and (
        semantic_gate.get("passed") is True or semantic_gate_raw is True
    ):
        semantic_violations = 0
    evaluation_blocks = [
        block for block in blocks if _mapping(block).get("split") == "evaluation"
    ]
    arm_count = sum(
        len(_sequence(_mapping(block).get("arms"))) for block in blocks
    )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "experiment_id": "E002-PW3",
        "artifact_state": decision,
        "source_result": {
            "artifact_sha256": result["artifact_sha256"],
            "uri": source_uri,
            "schema": result["schema"],
        },
        "question": (
            "Can dependency-safe timing of checkpoint and recovery work reduce "
            "physical rack ramps and 0.1-10 Hz energy without changing learning?"
        ),
        "freshman": {
            "headline": headline,
            "plain_answer": plain_answer,
            "cards": [
                {
                    "label": "Rack ramp",
                    "value": ramp_value,
                    "detail": ramp_interval,
                    "metric": ramp_metric,
                },
                {
                    "label": "0.1-10 Hz energy",
                    "value": spectral_value,
                    "detail": spectral_interval,
                    "metric": spectral_metric,
                },
                {
                    "label": "Useful-token rate",
                    "value": throughput_value,
                    "detail": throughput_interval,
                    "metric": throughput_metric,
                },
                {
                    "label": "Semantic violations",
                    "value": (
                        str(semantic_violations)
                        if semantic_violations is not None
                        else "unresolved"
                    ),
                    "detail": "state, sample, optimizer, durable-cut, and rollback obligations",
                },
            ],
            "measurement_valid": valid,
            "active_invalidators": invalidators,
            "boundary": (
                "This is a physical rack mechanism result. It does not establish "
                "facility or point-of-common-coupling transfer."
            ),
        },
        "researcher": {
            "measurement_valid": valid,
            "active_invalidators": invalidators,
            "sensor_manifest": result["sensor_manifest"],
            "clock_alignment": result["clock_alignment"],
            "policy_metrics": summary.get("policy_metrics"),
            "comparisons": summary.get("comparisons"),
            "gates": summary.get("gates"),
            "decision": summary.get("decision"),
            "waveform_blocks": [
                _block_projection(_mapping(block), include_display=True)
                for block in evaluation_blocks
            ],
        },
        "full_trace": {
            "block_count": len(blocks),
            "evaluation_block_count": len(evaluation_blocks),
            "arm_count": arm_count,
            "blocks": [
                _block_projection(_mapping(block), include_display=False)
                for block in blocks
            ],
            "raw_trace_manifest": result["raw_trace_manifest"],
            "engine": result.get("engine"),
            "runtime": result.get("runtime"),
            "scenario_sha256": result.get("scenario_sha256"),
            "source_bindings": result.get("source_bindings"),
        },
        "evidence_boundary": result["evidence_boundary"],
        "next_experiment": _next_experiment(decision, valid),
    }
    payload["artifact_sha256"] = _content_hash(payload)
    return payload


def project_e002_rack_dephasing_result_file(
    result_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    result_file = Path(result_path)
    result = json.loads(result_file.read_text(encoding="utf-8"))
    payload = build_e002_rack_dephasing_observatory_artifact(
        result,
        source_uri=result_file.as_posix(),
    )
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return payload


__all__ = [
    "RESULT_SCHEMA",
    "SCHEMA",
    "build_e002_rack_dephasing_observatory_artifact",
    "project_e002_rack_dephasing_result_file",
]
