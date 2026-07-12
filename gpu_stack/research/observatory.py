"""Evidence-preserving projection from experiment artifacts to the UI.

The browser should never recalculate research results or invent a cleaner
conclusion than the experiment artifact supports.  This module condenses E001
into a deterministic causal graph, policy comparison, and event timeline while
retaining evidence class, uncertainty boundary, falsifiers, and missing work.
"""

from __future__ import annotations

import hashlib
import json
from typing import Iterable, Mapping

from .e001 import E001Comparison, E001PolicyKind, E001_RESULT_SCHEMA
from .observations import Observation
from .temporal import EventKind


def _causal_nodes() -> list[dict[str, object]]:
    return [
        {
            "node_id": "site_availability",
            "label": "Site availability",
            "evidence_class": "assumed",
            "freshman": "A site can lose power and stop contributing work.",
            "researcher": "The scenario injects fixed-time site outages that reserve operational resources.",
            "full_trace": "Failure and recovery timestamps are scenario inputs; no fleet incidence model is fitted.",
        },
        {
            "node_id": "membership",
            "label": "Training membership",
            "evidence_class": "unmeasured",
            "freshman": "The run could decide which sites still participate.",
            "researcher": "Reactive membership during an active outage is not implemented in this mechanics screen.",
            "full_trace": "The current runtime has operation-boundary decisions but no resumable mid-operation health callback.",
        },
        {
            "node_id": "sync_cadence",
            "label": "Synchronization cadence",
            "evidence_class": "modeled",
            "freshman": "Sites can train locally for more steps before they talk.",
            "researcher": "The adaptive-cadence policy changes local steps from the previous cycle's communication-phase fraction.",
            "full_trace": "Every decision is recorded as a SyncCadenceIntervention before the next compute epoch is queued.",
        },
        {
            "node_id": "collective_payload",
            "label": "Cross-site collective payload",
            "evidence_class": "modeled",
            "freshman": "Talking less often sends fewer bytes between datacenters.",
            "researcher": "The metric sums one gradient payload per modeled WAN link and synchronization cycle.",
            "full_trace": "This is payload-link bytes, not a complete algorithm-specific all-reduce traffic model.",
        },
        {
            "node_id": "mechanical_elapsed_time",
            "label": "Mechanical elapsed time",
            "evidence_class": "modeled",
            "freshman": "Compute, communication, checkpoints, and interruptions all consume time.",
            "researcher": "Successive epochs enforce compute-before-collective causality and shared-resource contention.",
            "full_trace": "Overlapping failure postpones a whole operation; preemption, lost work, and recovery replay are not modeled yet.",
        },
        {
            "node_id": "learning_progress",
            "label": "Learning progress per FLOP",
            "evidence_class": "prior",
            "freshman": "We do not yet know how much extra local training changes what the model learns.",
            "researcher": "A wide sensitivity prior is seeded by one-step 360M Muon final-loss observations.",
            "full_trace": "The source does not identify progress per FLOP or multi-step transfer, so the learning falsifier is unresolved.",
        },
        {
            "node_id": "time_to_target",
            "label": "Time to a held-out target",
            "evidence_class": "unmeasured",
            "freshman": "The real question stays unanswered until training quality is measured.",
            "researcher": "Prior-projected equivalent-progress time is shown only as sensitivity, never as a falsifier result.",
            "full_trace": "No held-out multi-site learning observation is attached to E001's current artifact.",
        },
    ]


def _causal_edges() -> list[dict[str, str]]:
    return [
        {"source": "site_availability", "target": "membership", "relation": "constrains"},
        {"source": "site_availability", "target": "mechanical_elapsed_time", "relation": "delays"},
        {"source": "membership", "target": "sync_cadence", "relation": "changes feasible policy"},
        {"source": "sync_cadence", "target": "collective_payload", "relation": "controls frequency"},
        {"source": "sync_cadence", "target": "learning_progress", "relation": "changes staleness"},
        {"source": "collective_payload", "target": "mechanical_elapsed_time", "relation": "consumes WAN phase"},
        {"source": "mechanical_elapsed_time", "target": "time_to_target", "relation": "contributes"},
        {"source": "learning_progress", "target": "time_to_target", "relation": "required but unvalidated"},
    ]


def _event_evidence_class(kind: EventKind) -> str:
    if kind in {EventKind.FAILURE, EventKind.RECOVERY}:
        return "assumed"
    return "modeled"


def _policy_timeline(run) -> list[dict[str, object]]:
    events = []
    for epoch_index, epoch in enumerate(run.epochs, start=1):
        for record in epoch.trace.records:
            events.append(
                {
                    "policy": run.policy_kind.value,
                    "epoch_index": epoch_index,
                    "event_id": record.event.event_id,
                    "kind": record.event.kind.value,
                    "evidence_class": _event_evidence_class(record.event.kind),
                    "start_ns": record.start_ns,
                    "end_ns": record.end_ns,
                    "duration_ns": record.event.duration_ns,
                    "wait_ns": record.wait_ns,
                    "location": record.event.location,
                    "metadata": dict(record.event.metadata),
                }
            )
    return sorted(events, key=lambda item: (item["start_ns"], item["end_ns"], item["event_id"]))


def _evidence_counts(nodes: list[Mapping[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in nodes:
        evidence_class = str(node["evidence_class"])
        counts[evidence_class] = counts.get(evidence_class, 0) + 1
    return dict(sorted(counts.items()))


def build_e001_observatory_artifact(
    comparison: E001Comparison,
    observations: Iterable[Observation] = (),
    *,
    source_result: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Condense a complete E001 comparison without changing its conclusion."""

    if not isinstance(comparison, E001Comparison):
        raise TypeError("comparison must be an E001Comparison")
    if source_result is None:
        core_result = comparison.to_dict(include_traces=False)
        source_result_record: dict[str, object] = {
            "schema": core_result["schema"],
            "artifact_sha256": core_result["artifact_sha256"],
            "scenario_sha256": core_result["scenario_hash"],
            "engine_source_sha256": core_result["engine"]["source_sha256"],
            "traces_included": core_result["traces_included"],
            "uri": None,
        }
    else:
        source_result_record = dict(source_result)
    if source_result_record.get("schema") != E001_RESULT_SCHEMA:
        raise ValueError("source_result schema does not match E001 result schema")
    source_hash = source_result_record.get("artifact_sha256")
    if (
        not isinstance(source_hash, str)
        or len(source_hash) != 64
        or any(character not in "0123456789abcdef" for character in source_hash)
    ):
        raise ValueError("source_result artifact_sha256 must be lowercase SHA-256")
    if source_result_record.get("scenario_sha256") != comparison.scenario.scenario_hash:
        raise ValueError("source_result scenario hash does not match comparison")
    if source_result_record.get("engine_source_sha256") != comparison.engine_source_hash:
        raise ValueError("source_result engine hash does not match comparison")
    observation_by_id: dict[str, Observation] = {}
    for observation in observations:
        if not isinstance(observation, Observation):
            raise TypeError("observations must contain Observation values")
        if observation.observation_id in observation_by_id:
            raise ValueError(
                f"duplicate observatory observation {observation.observation_id!r}"
            )
        observation_by_id[observation.observation_id] = observation
    relevant_observation_ids = tuple(
        dict.fromkeys(
            comparison.scenario.learning_prior.seed_observation_ids
            + comparison.scenario.evaluation_observation_ids
        )
    )
    included_observations = [
        observation_by_id[observation_id].to_dict()
        for observation_id in relevant_observation_ids
        if observation_id in observation_by_id
    ]
    missing_observation_ids = [
        observation_id for observation_id in relevant_observation_ids
        if observation_id not in observation_by_id
    ]
    nodes = _causal_nodes()
    artifacts_by_policy = {
        artifact.policy: artifact for artifact in comparison.artifacts
    }
    runs = []
    timeline: dict[str, object] = {}
    for run in (comparison.baseline,) + comparison.candidates:
        summary = run.to_dict(include_traces=False)
        comparison_role = {
            E001PolicyKind.SYNCHRONOUS: "reference_baseline",
            E001PolicyKind.FIXED_LOCAL: "preregistered_baseline",
            E001PolicyKind.ADAPTIVE_CADENCE: "hypothesis_policy",
        }[run.policy_kind]
        summary["comparison_role"] = comparison_role
        artifact = artifacts_by_policy.get(run.policy_kind.value)
        if artifact is not None:
            summary["experiment_artifact"] = artifact.to_dict()
        else:
            summary["experiment_artifact"] = {
                "conclusion": "baseline",
                "evidence_gaps": [
                    "the synchronous run is a comparator, not a tested policy claim"
                ],
            }
        runs.append(summary)
        timeline[run.policy_kind.value] = _policy_timeline(run)

    hypothesis_artifact = artifacts_by_policy.get(
        E001PolicyKind.ADAPTIVE_CADENCE.value
    )
    overall_conclusion = (
        hypothesis_artifact.conclusion
        if hypothesis_artifact is not None
        else "inconclusive"
    )
    payload = {
        "schema": "gpu-stack.causal-observatory.e001.v1",
        "source_result": source_result_record,
        "experiment_id": "E001",
        "title": "Beyond One Datacenter",
        "question": "Can one training run survive across three datacenters?",
        "status": {
            "stage": "virtual_mechanics_screen",
            "conclusion": overall_conclusion,
            "plain_answer": (
                "The engine can compare modeled timing and collective payload. "
                "It cannot answer the learning-efficiency question until held-out "
                "multi-site training observations exist."
            ),
            "held_out_learning_validation": False,
            "hypothesis_policy": E001PolicyKind.ADAPTIVE_CADENCE.value,
        },
        "protocol_hash": comparison.protocol_hash,
        "protocol": comparison.to_dict(include_traces=False)["protocol"],
        "scenario": comparison.scenario.to_dict(),
        "observations": included_observations,
        "missing_observation_ids": missing_observation_ids,
        "semantic_depths": ["freshman", "researcher", "full_trace"],
        "causal_graph": {
            "nodes": nodes,
            "edges": _causal_edges(),
            "evidence_counts": _evidence_counts(nodes),
        },
        "runs": runs,
        "timeline": timeline,
        "result_scope": {
            "supported": [
                "event ordering",
                "resource contention",
                "modeled collective payload-link bytes",
                "modeled elapsed time",
                "site base plus accelerator compute energy",
                "operation-boundary cadence decisions",
            ],
            "unsupported": [
                "held-out learning progress per FLOP",
                "held-out time to loss or capability target",
                "reactive membership during an active outage",
                "preemption, lost work, and checkpoint recovery",
                "complete algorithm-specific collective traffic",
                "dynamic network, checkpoint, storage, host, and cooling energy",
                "site curtailment and recovery power waveform",
            ],
        },
    }
    payload["artifact_sha256"] = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return payload


def e001_observatory_json(
    comparison: E001Comparison,
    observations: Iterable[Observation] = (),
) -> str:
    return json.dumps(
        build_e001_observatory_artifact(comparison, observations),
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )


__all__ = ["build_e001_observatory_artifact", "e001_observatory_json"]
