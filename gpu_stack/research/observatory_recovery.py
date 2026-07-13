"""Deterministic observatory projection for the E001 recovery experiment.

The recovery runner owns mechanics and accounting.  This module is deliberately
boring: it validates one persisted research result, preserves every reported
value, and adds only evidence-bound explanatory copy for the browser.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .e001_recovery_artifact import E001_RECOVERY_RESULT_SCHEMA

E001_RECOVERY_OBSERVATORY_SCHEMA = (
    "gpu-stack.causal-observatory.e001-recovery.v2"
)

_HEX = frozenset("0123456789abcdef")
_PROJECTED_RUN_KEYS = (
    "policy_id",
    "policy_role",
    "summary",
    "metrics",
    "recovery_episodes",
    "decision_batches",
    "work_dispositions",
    "checkpoint_lineage",
    "link_segments",
    "state_snapshots",
    "falsifiers",
    "evidence_requirements",
)


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


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value.strip()


def _sha256(value: object, field_name: str) -> str:
    digest = _text(value, field_name)
    if len(digest) != 64 or any(character not in _HEX for character in digest):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return digest


def _json_clone(value: object) -> Any:
    """Return a JSON-only deep copy and reject NaN or custom values."""

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


def _validate_source_result(source: Mapping[str, Any]) -> None:
    if source.get("schema") != E001_RECOVERY_RESULT_SCHEMA:
        raise ValueError("source result schema is not E001 recovery v2")
    claimed_hash = _sha256(source.get("artifact_sha256"), "artifact_sha256")
    hash_payload = dict(source)
    del hash_payload["artifact_sha256"]
    if _artifact_hash(hash_payload) != claimed_hash:
        raise ValueError("source result artifact_sha256 does not match its payload")
    _sha256(source.get("scenario_hash"), "scenario_hash")
    _sha256(source.get("protocol_hash"), "protocol_hash")
    engine = _mapping(source.get("engine"), "engine")
    _text(engine.get("engine_id"), "engine.engine_id")
    _sha256(engine.get("source_sha256"), "engine.source_sha256")
    _mapping(source.get("matched_trace"), "matched_trace")
    _mapping(source.get("matched_frontier"), "matched_frontier")
    _mapping(source.get("comparison"), "comparison")
    _mapping(source.get("conclusion"), "conclusion")
    runs = _array(source.get("runs"), "runs")
    if len(runs) != 4:
        raise ValueError("focused recovery result must contain exactly four runs")
    policy_ids: list[str] = []
    for index, raw_run in enumerate(runs):
        run = _mapping(raw_run, f"runs[{index}]")
        missing = [key for key in _PROJECTED_RUN_KEYS if key not in run]
        if missing:
            raise ValueError(
                f"runs[{index}] is missing projected fields: {missing}"
            )
        policy_ids.append(_text(run.get("policy_id"), f"runs[{index}].policy_id"))
        _text(run.get("policy_role"), f"runs[{index}].policy_role")
        for key in (
            "summary",
            "metrics",
            "checkpoint_lineage",
        ):
            _mapping(run.get(key), f"runs[{index}].{key}")
        for key in (
            "recovery_episodes",
            "decision_batches",
            "work_dispositions",
            "link_segments",
            "state_snapshots",
            "falsifiers",
            "evidence_requirements",
        ):
            _array(run.get(key), f"runs[{index}].{key}")
    if len(policy_ids) != len(set(policy_ids)):
        raise ValueError("recovery run policy_id values must be unique")
    if set(policy_ids) != {
        "synchronous-wait-restore",
        "fixed-local-checkpoint-restart",
        "adaptive-recovery",
        "future-trace-recovery-oracle",
    }:
        raise ValueError("recovery result contains the wrong four-policy panel")


def _causal_graph() -> dict[str, object]:
    nodes = [
        {
            "node_id": "assumed_failure_trace",
            "label": "Matched failure trace",
            "evidence_class": "assumed",
            "freshman": "All four policies face the same simulated failure.",
            "researcher": (
                "Failure occurrence and controller observation are separate "
                "timestamps on one matched exogenous trace."
            ),
            "full_trace": (
                "The trace is a scenario input, not an estimated fleet failure "
                "distribution."
            ),
        },
        {
            "node_id": "observable_decision_boundary",
            "label": "Observable decision boundary",
            "evidence_class": "modeled",
            "freshman": "A policy reacts only after it can see the failure.",
            "researcher": (
                "Each decision batch records the controller-visible snapshot used "
                "for the action."
            ),
            "full_trace": (
                "Engine-private physical state remains post-run evidence and is not "
                "a candidate-policy input."
            ),
        },
        {
            "node_id": "preemption_and_loss",
            "label": "Preemption and lost work",
            "evidence_class": "modeled",
            "freshman": "A failure can erase work that had not become durable.",
            "researcher": (
                "Attempt dispositions separate final-valid, interrupted, invalidated, "
                "superseded, and replayed work."
            ),
            "full_trace": (
                "The serialized work ledger is authoritative; the browser does not "
                "reconstruct conservation totals."
            ),
        },
        {
            "node_id": "checkpoint_lineage",
            "label": "Checkpoint lineage",
            "evidence_class": "modeled",
            "freshman": "Recovery starts from a complete saved state.",
            "researcher": (
                "The restore source binds model, optimizer, random-number, data-cursor, "
                "membership, and shard lineage."
            ),
            "full_trace": (
                "Only an atomically committed manifest may be the recovery frontier."
            ),
        },
        {
            "node_id": "restore_and_replay",
            "label": "Restore and replay",
            "evidence_class": "modeled",
            "freshman": "The run reloads state and repeats lost work.",
            "researcher": (
                "Restore traffic and replay compute remain distinct physical costs."
            ),
            "full_trace": (
                "Every inter-site segment retains one disjoint traffic class and "
                "attempt identity."
            ),
        },
        {
            "node_id": "matched_frontier",
            "label": "Matched durable frontier",
            "evidence_class": "modeled",
            "freshman": "The policies stop after reaching the same saved progress.",
            "researcher": (
                "Completion time and traffic compare one identical terminal durable "
                "frontier under the matched trace."
            ),
            "full_trace": (
                "This is a mechanics estimand, not held-out loss or capability parity."
            ),
        },
        {
            "node_id": "held_out_learning",
            "label": "Held-out learning effect",
            "evidence_class": "unmeasured",
            "freshman": "This run does not prove the recovered model learns equally well.",
            "researcher": (
                "No held-out multi-site convergence or capability observation is "
                "attached to this virtual mechanics comparison."
            ),
            "full_trace": (
                "Mechanical frontier equality cannot resolve progress per FLOP or "
                "quality-preserving recovery."
            ),
        },
    ]
    return {
        "nodes": nodes,
        "edges": [
            {
                "source": "assumed_failure_trace",
                "target": "observable_decision_boundary",
                "relation": "becomes visible at",
            },
            {
                "source": "assumed_failure_trace",
                "target": "preemption_and_loss",
                "relation": "causes",
            },
            {
                "source": "preemption_and_loss",
                "target": "checkpoint_lineage",
                "relation": "selects rollback frontier",
            },
            {
                "source": "checkpoint_lineage",
                "target": "restore_and_replay",
                "relation": "enables",
            },
            {
                "source": "observable_decision_boundary",
                "target": "restore_and_replay",
                "relation": "controls",
            },
            {
                "source": "restore_and_replay",
                "target": "matched_frontier",
                "relation": "reaches",
            },
            {
                "source": "matched_frontier",
                "target": "held_out_learning",
                "relation": "does not establish",
            },
        ],
        "evidence_counts": {
            "assumed": 1,
            "modeled": 5,
            "unmeasured": 1,
        },
    }


def _episode_timeline_records(episode: Mapping[str, Any]) -> list[dict[str, object]]:
    """Project the runner's recovery anchors into explicit visual events."""

    episode_id = _text(episode.get("episode_id"), "recovery episode_id")
    failure_at = int(episode["failure_observed_at_ns"])
    physical_at = int(episode["physical_recovery_at_ns"])
    restore_start = int(episode["restore_started_at_ns"])
    restore_end = int(episode["restore_completed_at_ns"])
    replay_end = int(episode["replay_completed_at_ns"])
    rejoin_at = int(episode["membership_rejoined_at_ns"])
    records = [
        {
            "event_id": f"{episode_id}:failure",
            "recovery_role": "failure",
            "start_ns": failure_at,
            "end_ns": failure_at,
        },
        {
            "event_id": f"{episode_id}:preemption",
            "recovery_role": "preemption",
            "start_ns": failure_at,
            "end_ns": failure_at,
        },
        {
            "event_id": f"{episode_id}:availability",
            "recovery_role": "availability_recovery",
            "start_ns": physical_at,
            "end_ns": physical_at,
        },
        {
            "event_id": f"{episode_id}:restore",
            "recovery_role": "checkpoint_restore",
            "start_ns": restore_start,
            "end_ns": restore_end,
        },
    ]
    if replay_end > restore_end:
        records.append(
            {
                "event_id": f"{episode_id}:replay",
                "recovery_role": "replay",
                "start_ns": restore_end,
                "end_ns": replay_end,
            }
        )
    records.extend(
        (
            {
                "event_id": f"{episode_id}:rejoin",
                "recovery_role": "membership_rejoin",
                "start_ns": rejoin_at,
                "end_ns": rejoin_at,
            },
            {
                "event_id": f"{episode_id}:durable-recovery",
                "recovery_role": "durable_progress_recovery",
                "start_ns": rejoin_at,
                "end_ns": rejoin_at,
            },
        )
    )
    return records


def _project_run(raw_run: Mapping[str, Any]) -> dict[str, object]:
    run = {key: _json_clone(raw_run[key]) for key in _PROJECTED_RUN_KEYS}
    episodes = []
    for raw_episode in _array(run["recovery_episodes"], "recovery_episodes"):
        episode = dict(_mapping(raw_episode, "recovery episode"))
        episode["timeline_records"] = _episode_timeline_records(episode)
        episodes.append(episode)
    run["recovery_episodes"] = episodes

    completed_collective = 0
    aborted_collective = 0
    checkpoint_replication = 0
    checkpoint_restore = 0
    recovery_redistribution = 0
    planned_migration = 0
    for raw_segment in _array(run["link_segments"], "link_segments"):
        segment = _mapping(raw_segment, "link segment")
        link_bytes = int(segment.get("link_bytes", 0))
        traffic_class = segment.get("traffic_class")
        if traffic_class in {"dense_collective", "sparse_collective"}:
            if segment.get("committed") is True:
                completed_collective += link_bytes
            else:
                aborted_collective += link_bytes
        elif traffic_class == "checkpoint":
            checkpoint_replication += link_bytes
        elif traffic_class == "restore":
            checkpoint_restore += link_bytes
        elif traffic_class == "membership_reconfiguration":
            recovery_redistribution += link_bytes
        elif traffic_class == "planned_migration":
            planned_migration += link_bytes
    metrics = dict(_mapping(run["metrics"], "metrics"))
    metrics.update(
        {
            "completed_collective_link_bytes": completed_collective,
            "aborted_collective_link_bytes": aborted_collective,
            "remote_checkpoint_replication_link_bytes": checkpoint_replication,
            "remote_checkpoint_restore_link_bytes": checkpoint_restore,
            "recovery_state_redistribution_link_bytes": recovery_redistribution,
            "planned_state_migration_link_bytes": planned_migration,
        }
    )
    run["metrics"] = metrics
    return run


def build_e001_recovery_observatory_artifact(
    source_result: Mapping[str, Any],
    *,
    source_uri: str | None = None,
) -> dict[str, object]:
    """Project a persisted recovery result without recalculating its evidence."""

    source = _json_clone(_mapping(source_result, "source_result"))
    _validate_source_result(source)
    conclusion = _mapping(source["conclusion"], "conclusion")
    runs = _array(source["runs"], "runs")
    projected_runs = [_project_run(_mapping(run, "run")) for run in runs]
    payload: dict[str, object] = {
        "schema": E001_RECOVERY_OBSERVATORY_SCHEMA,
        "source_result": {
            "schema": source["schema"],
            "artifact_sha256": source["artifact_sha256"],
            "scenario_sha256": source["scenario_hash"],
            "engine_source_sha256": source["engine"]["source_sha256"],
            "traces_included": True,
            "uri": source_uri,
        },
        "experiment_id": source["experiment_id"],
        "title": "Beyond One Datacenter: Recovery",
        "question": (
            "Can an observable-only recovery policy reach the same durable "
            "training frontier with less time or inter-site traffic?"
        ),
        "status": {
            "stage": "virtual_recovery_mechanics",
            "conclusion": conclusion["status"],
            "mechanics_answer": conclusion["mechanics_answer"],
            "plain_answer": conclusion["plain_answer"],
            "held_out_learning_validation": False,
            "hypothesis_policy": conclusion["hypothesis_policy"],
            "evidence_boundary": conclusion["evidence_boundary"],
        },
        "semantic_depths": ["freshman", "researcher", "full_trace"],
        "protocol_hash": source["protocol_hash"],
        "protocol": _json_clone(source["protocol"]),
        "scenario": _json_clone(source["scenario"]),
        "matched_trace": _json_clone(source["matched_trace"]),
        "matched_frontier": _json_clone(source["matched_frontier"]),
        "runs": projected_runs,
        "comparison": _json_clone(source["comparison"]),
        "causal_graph": _causal_graph(),
        "result_scope": {
            "supported": [
                "one matched virtual failure-and-recovery trace",
                "four matched recovery policies including an oracle comparator",
                "observable-only policy decision batches",
                "preempted, invalidated, replayed, and final-valid work dispositions",
                "atomic checkpoint lineage and modeled restore",
                "disjoint physical inter-site link-segment accounting",
                "completion at one identical terminal durable frontier",
            ],
            "unsupported": [
                "held-out learning progress per FLOP",
                "held-out loss, convergence, or capability recovery",
                "generalization beyond the serialized scenario and trace",
                "the remaining preregistered recovery comparators outside this focused four-policy panel",
                "measured datacenter failure, network, storage, or power traces",
            ],
        },
    }
    payload["artifact_sha256"] = _artifact_hash(payload)
    return payload


def e001_recovery_observatory_json(
    source_result: Mapping[str, Any],
    *,
    source_uri: str | None = None,
) -> str:
    return json.dumps(
        build_e001_recovery_observatory_artifact(
            source_result,
            source_uri=source_uri,
        ),
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )


__all__ = [
    "E001_RECOVERY_OBSERVATORY_SCHEMA",
    "E001_RECOVERY_RESULT_SCHEMA",
    "build_e001_recovery_observatory_artifact",
    "e001_recovery_observatory_json",
]
