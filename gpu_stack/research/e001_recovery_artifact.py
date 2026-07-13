"""Persisted research artifact for the focused E001 recovery comparison."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .e001_recovery_v2 import E001_RECOVERY_V2_PROTOCOL
from .protocols import EvidenceRequirementResult, EvidenceRequirementStatus


E001_RECOVERY_RESULT_SCHEMA = "gpu-stack.e001-recovery-comparison.v2"
_POLICY_ROLES = {
    "synchronous-wait-restore": "baseline",
    "fixed-local-checkpoint-restart": "baseline",
    "adaptive-recovery": "candidate",
    "future-trace-recovery-oracle": "oracle_comparator",
}


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _array(value: object, field_name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
        value, Sequence
    ):
        raise TypeError(f"{field_name} must be an array")
    return value


def _json_clone(value: object) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def _artifact_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _plain_sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a SHA-256 string")
    digest = value[7:] if value.startswith("sha256:") else value
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return digest


def _frontier_record(value: object, field_name: str) -> dict[str, object]:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be an integer or mapping")
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f"{field_name} must be non-negative")
        return {"committed_step": value}
    return dict(_mapping(value, field_name))


def _execution_payload(execution: object) -> Mapping[str, Any]:
    if isinstance(execution, Mapping):
        return _mapping(_json_clone(execution), "execution")
    serializer = getattr(execution, "to_dict", None)
    if not callable(serializer):
        raise TypeError("execution must be a mapping or expose to_dict()")
    return _mapping(_json_clone(serializer()), "execution")


def _unresolved_requirements() -> list[dict[str, object]]:
    """Bind every preregistered gate without upgrading one trace to a panel."""

    reasons = {
        "e001-observable-failure-recovery-epochs": (
            "This run exercises two failures with preemption, restore, replay, and "
            "re-entry; the full preregistered transition panel is not executed."
        ),
        "e001-reactive-membership-without-trace-leakage": (
            "The candidate uses serialized observable snapshots on this trace; "
            "future-prefix and delayed-observation panels remain unexecuted."
        ),
        "e001-preemption-replay-conservation": (
            "The emitted ledger is conserved for this path; collective-phase and "
            "repeated-interruption panels remain unexecuted."
        ),
        "e001-checkpoint-lineage-and-restore": (
            "The executed restore binds one complete manifest; partial, tied, failed-"
            "storage, and genesis checkpoint panels remain unexecuted."
        ),
        "e001-recovery-baseline-completeness": (
            "This focused experiment executes four recovery policies, not the frozen "
            "six-policy comparator vector."
        ),
    }
    results = []
    for spec in E001_RECOVERY_V2_PROTOCOL.evidence_requirements:
        reason = reasons.get(
            spec.requirement_id,
            "This focused virtual recovery run does not resolve the full preregistered requirement.",
        )
        results.append(
            EvidenceRequirementResult(
                requirement_id=spec.requirement_id,
                status=EvidenceRequirementStatus.UNRESOLVED,
                reason=reason,
            ).to_dict()
        )
    return results


def _policy_run(
    raw_run: Mapping[str, Any],
    *,
    comparison: Mapping[str, Any],
) -> dict[str, object]:
    policy_id = raw_run.get("policy_id")
    if policy_id not in _POLICY_ROLES:
        raise ValueError(f"unexpected minimal recovery policy {policy_id!r}")
    policy_role = _POLICY_ROLES[policy_id]
    metrics = dict(_mapping(raw_run.get("metrics"), f"{policy_id}.metrics"))
    required_metrics = {
        "learning_progress",
        "total_inter_site_link_bytes",
        "lost_compute_flops",
        "recovery_time_ns",
        "modeled_energy_j",
    }
    missing_metrics = sorted(required_metrics - set(metrics))
    if missing_metrics:
        raise ValueError(
            f"{policy_id}.metrics is missing required fields: {missing_metrics}"
        )
    learning_progress = _mapping(
        metrics["learning_progress"],
        f"{policy_id}.metrics.learning_progress",
    )
    if learning_progress.get("evidence_class") not in {
        "measured",
        "modeled",
        "assumed",
        "prior",
        "unmeasured",
    }:
        raise ValueError(
            f"{policy_id}.metrics.learning_progress has invalid evidence_class"
        )
    traffic_by_class = metrics.get("traffic_by_class", {})
    if traffic_by_class is not None:
        traffic_by_class = _mapping(
            traffic_by_class,
            f"{policy_id}.metrics.traffic_by_class",
        )
        for traffic_class, link_bytes in traffic_by_class.items():
            metrics.setdefault(str(traffic_class), link_bytes)
    if policy_role == "candidate":
        if "completion_time_ratio" in comparison:
            metrics["completion_time_ratio"] = comparison[
                "completion_time_ratio"
            ]
        if "total_inter_site_byte_fraction" in comparison:
            metrics["total_inter_site_byte_fraction"] = comparison[
                "total_inter_site_byte_fraction"
            ]
        falsifiers = [
            item.to_dict()
            for item in E001_RECOVERY_V2_PROTOCOL.evaluate_falsifiers(metrics)
        ]
        requirements = _unresolved_requirements()
    else:
        falsifiers = []
        requirements = []

    work_ledger = _mapping(
        raw_run.get("work_ledger"),
        f"{policy_id}.work_ledger",
    )
    terminal_frontier = _frontier_record(
        raw_run.get("terminal_frontier"),
        f"{policy_id}.terminal_frontier",
    )
    checkpoint_manifests = _array(
        raw_run.get("checkpoint_manifests"),
        f"{policy_id}.checkpoint_manifests",
    )
    terminal_checkpoint = _mapping(
        raw_run.get("terminal_checkpoint"),
        f"{policy_id}.terminal_checkpoint",
    )
    summary = {
        "start_ns": raw_run.get("start_ns"),
        "end_ns": raw_run.get("end_ns"),
        "elapsed_ns": raw_run.get("elapsed_ns"),
        "mechanical_completion_ns": raw_run.get("elapsed_ns"),
        "terminal_time_ns": raw_run.get("end_ns"),
        "durable_frontier_reached_at_ns": raw_run.get(
            "durable_frontier_reached_at_ns"
        ),
        "recovery_debt_ns": metrics.get("recovery_debt_ns"),
        "terminal_frontier": _json_clone(terminal_frontier),
        "terminal_checkpoint_id": terminal_checkpoint.get("checkpoint_id"),
    }
    return {
        "policy_id": policy_id,
        "policy_role": policy_role,
        "summary": summary,
        "metrics": _json_clone(metrics),
        "recovery_episodes": _json_clone(
            _array(
                raw_run.get("recovery_episodes"),
                f"{policy_id}.recovery_episodes",
            )
        ),
        "decision_batches": _json_clone(
            _array(
                raw_run.get("decision_batches"),
                f"{policy_id}.decision_batches",
            )
        ),
        "work_dispositions": _json_clone(
            _array(work_ledger.get("outcomes"), f"{policy_id}.work_ledger.outcomes")
        ),
        "checkpoint_lineage": {
            "terminal_checkpoint": _json_clone(terminal_checkpoint),
            "manifests": _json_clone(checkpoint_manifests),
        },
        "link_segments": _json_clone(
            _array(raw_run.get("link_segments"), f"{policy_id}.link_segments")
        ),
        "state_snapshots": _json_clone(
            _array(raw_run.get("snapshots"), f"{policy_id}.snapshots")
        ),
        "falsifiers": falsifiers,
        "evidence_requirements": requirements,
    }


def _conclusion(comparison: Mapping[str, Any]) -> dict[str, object]:
    hypothesis_supported = comparison.get("hypothesis_supported")
    if not isinstance(hypothesis_supported, bool):
        raise TypeError("comparison.hypothesis_supported must be bool")
    mechanics_answer = (
        "candidate_better_on_this_trace"
        if hypothesis_supported
        else "candidate_not_better_on_this_trace"
    )
    plain_answer = (
        "The adaptive policy reached the same durable frontier with lower "
        "mechanical completion time and fewer inter-site link bytes on this trace."
        if hypothesis_supported
        else (
            "The adaptive policy did not jointly reduce mechanical completion time "
            "and inter-site link bytes at the same durable frontier on this trace."
        )
    )
    return {
        "status": "inconclusive_frontier_hypothesis",
        "mechanics_answer": mechanics_answer,
        "plain_answer": plain_answer,
        "hypothesis_policy": "adaptive-recovery",
        "evidence_boundary": (
            "This is one deterministic virtual recovery-mechanics comparison. "
            "Held-out learning quality and the complete six-policy baseline vector "
            "remain unresolved."
        ),
    }


def build_e001_recovery_result(execution: object) -> dict[str, object]:
    """Normalize one runner execution into the content-addressed result schema."""

    raw = _execution_payload(execution)
    scenario = _mapping(raw.get("scenario"), "scenario")
    comparison = dict(_mapping(raw.get("comparison"), "comparison"))
    if "same_frontier" not in comparison and "equal_terminal_frontier" in comparison:
        comparison["same_frontier"] = comparison["equal_terminal_frontier"]
    if (
        "total_inter_site_byte_fraction" not in comparison
        and "total_inter_site_link_bytes_ratio" in comparison
    ):
        comparison["total_inter_site_byte_fraction"] = comparison[
            "total_inter_site_link_bytes_ratio"
        ]
    raw_runs = _array(raw.get("policies"), "policies")
    if len(raw_runs) != 4:
        raise ValueError("focused E001 recovery execution must contain four policies")
    runs = [
        _policy_run(_mapping(item, f"policies[{index}]"), comparison=comparison)
        for index, item in enumerate(raw_runs)
    ]
    if {item["policy_id"] for item in runs} != set(_POLICY_ROLES):
        raise ValueError("focused recovery execution has the wrong policy panel")
    matched_frontier = _frontier_record(
        raw.get("matched_frontier"),
        "matched_frontier",
    )
    matched_frontier["equal_across_policies"] = comparison.get("same_frontier")
    scenario_hash = _plain_sha256(raw.get("scenario_hash"), "scenario_hash")
    engine_source_hash = _plain_sha256(
        raw.get("engine_source_hash"),
        "engine_source_hash",
    )
    payload: dict[str, object] = {
        "schema": E001_RECOVERY_RESULT_SCHEMA,
        "experiment_id": E001_RECOVERY_V2_PROTOCOL.experiment_id,
        "scenario_id": scenario.get("scenario_id"),
        "scenario_hash": scenario_hash,
        "scenario": _json_clone(scenario),
        "protocol_hash": E001_RECOVERY_V2_PROTOCOL.protocol_hash,
        "protocol": E001_RECOVERY_V2_PROTOCOL.to_dict(),
        "engine": {
            "engine_id": raw.get("engine_id"),
            "source_sha256": engine_source_hash,
        },
        "matched_trace": _json_clone(
            _mapping(raw.get("failure_trace"), "failure_trace")
        ),
        "matched_frontier": _json_clone(matched_frontier),
        "runs": runs,
        "comparison": _json_clone(comparison),
        "conclusion": _conclusion(comparison),
    }
    payload["artifact_sha256"] = _artifact_hash(payload)
    return payload


def e001_recovery_result_json(execution: object) -> str:
    return json.dumps(
        build_e001_recovery_result(execution),
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )


__all__ = [
    "E001_RECOVERY_RESULT_SCHEMA",
    "build_e001_recovery_result",
    "e001_recovery_result_json",
]
