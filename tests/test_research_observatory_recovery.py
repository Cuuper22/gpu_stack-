import hashlib
import json

import pytest

from gpu_stack.research.observatory_recovery import (
    E001_RECOVERY_OBSERVATORY_SCHEMA,
    E001_RECOVERY_RESULT_SCHEMA,
    build_e001_recovery_observatory_artifact,
)


def _digest(payload):
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _run(policy_id, policy_role, elapsed_ns, total_bytes):
    return {
        "policy_id": policy_id,
        "policy_role": policy_role,
        "summary": {
            "start_ns": 0,
            "end_ns": elapsed_ns,
            "terminal_step": 2,
        },
        "metrics": {
            "learning_progress": {
                "status": "unmeasured",
                "evidence_class": "unmeasured",
                "value": None,
                "unit": "1",
                "boundary": "No held-out learning observation is attached.",
            },
            "completion_time_ns": elapsed_ns,
            "total_inter_site_link_bytes": total_bytes,
            "lost_compute_flops": 1.0,
            "recovery_time_ns": elapsed_ns,
            "modeled_energy_j": 1.0,
        },
        "recovery_episodes": [
            {
                "episode_id": f"{policy_id}:recovery-1",
                "physical_failure_ns": 10,
                "failure_observed_at_ns": 10,
                "physical_recovery_at_ns": 20,
                "restore_started_at_ns": 20,
                "restore_completed_at_ns": 30,
                "replay_completed_at_ns": 40,
                "membership_rejoined_at_ns": 50,
                "durable_progress_recovery_ns": elapsed_ns,
            }
        ],
        "decision_batches": [
            {
                "decision_time_ns": 10,
                "boundaries": ["failure_observed"],
            }
        ],
        "work_dispositions": [
            {
                "attempt_id": f"{policy_id}:attempt-1",
                "disposition": "interrupted_lost",
                "attempted_work": 1.0,
            }
        ],
        "checkpoint_lineage": {
            "terminal_checkpoint_id": f"{policy_id}:checkpoint-2",
            "committed_step": 2,
            "manifests": [],
        },
        "link_segments": [
            {
                "segment_id": f"{policy_id}:restore-1",
                "traffic_class": "restore",
                "link_bytes": total_bytes,
            }
        ],
        "state_snapshots": [],
        "falsifiers": [],
        "evidence_requirements": [],
    }


def _source_result():
    payload = {
        "schema": E001_RECOVERY_RESULT_SCHEMA,
        "experiment_id": "E001-RECOVERY-V2",
        "scenario_id": "test-recovery",
        "scenario_hash": "1" * 64,
        "scenario": {"scenario_id": "test-recovery", "outages": []},
        "protocol_hash": "2" * 64,
        "protocol": {"experiment_id": "E001-RECOVERY-V2"},
        "engine": {
            "engine_id": "e001-recovery-transition-engine-v2",
            "source_sha256": "3" * 64,
        },
        "matched_trace": {"trace_id": "trace-1", "failures": []},
        "matched_frontier": {
            "lineage_id": "lineage-1",
            "committed_step": 2,
        },
        "runs": [
            _run("synchronous-wait-restore", "baseline", 150, 300),
            _run("fixed-local-checkpoint-restart", "baseline", 135, 180),
            _run("adaptive-recovery", "candidate", 120, 100),
            _run(
                "future-trace-recovery-oracle",
                "oracle_comparator",
                100,
                80,
            ),
        ],
        "comparison": {
            "same_frontier": True,
            "completion_time_ratio": 0.8,
            "total_inter_site_byte_fraction": 1 / 3,
        },
        "conclusion": {
            "status": "inconclusive_frontier_hypothesis",
            "mechanics_answer": "candidate_better_on_this_trace",
            "plain_answer": "The candidate reached the matched frontier sooner.",
            "hypothesis_policy": "adaptive-recovery",
            "evidence_boundary": "Virtual mechanics only; learning is unmeasured.",
        },
    }
    payload["artifact_sha256"] = _digest(payload)
    return payload


def test_recovery_projection_preserves_runner_values_and_learning_boundary():
    source = _source_result()

    artifact = build_e001_recovery_observatory_artifact(
        source,
        source_uri="result.json",
    )

    assert artifact["schema"] == E001_RECOVERY_OBSERVATORY_SCHEMA
    assert artifact["source_result"]["artifact_sha256"] == source[
        "artifact_sha256"
    ]
    assert artifact["source_result"]["uri"] == "result.json"
    assert artifact["matched_trace"] == source["matched_trace"]
    assert artifact["matched_frontier"] == source["matched_frontier"]
    assert artifact["comparison"] == source["comparison"]
    for metric_name, metric_value in source["runs"][2]["metrics"].items():
        assert artifact["runs"][2]["metrics"][metric_name] == metric_value
    assert artifact["runs"][2]["metrics"][
        "remote_checkpoint_restore_link_bytes"
    ] == source["runs"][2]["metrics"]["total_inter_site_link_bytes"]
    assert artifact["runs"][2]["work_dispositions"] == source["runs"][2][
        "work_dispositions"
    ]
    assert artifact["status"]["held_out_learning_validation"] is False
    assert artifact["semantic_depths"] == [
        "freshman",
        "researcher",
        "full_trace",
    ]
    learning_node = next(
        node
        for node in artifact["causal_graph"]["nodes"]
        if node["node_id"] == "held_out_learning"
    )
    assert learning_node["evidence_class"] == "unmeasured"
    assert len(artifact["artifact_sha256"]) == 64


def test_recovery_projection_rejects_tampered_source_result():
    source = _source_result()
    source["comparison"]["completion_time_ratio"] = 0.1

    with pytest.raises(ValueError, match="artifact_sha256"):
        build_e001_recovery_observatory_artifact(source)


def test_recovery_projection_requires_complete_minimal_two_policy_shape():
    source = _source_result()
    del source["runs"][2]["link_segments"]
    source["artifact_sha256"] = _digest(
        {key: value for key, value in source.items() if key != "artifact_sha256"}
    )

    with pytest.raises(ValueError, match="missing projected fields"):
        build_e001_recovery_observatory_artifact(source)
