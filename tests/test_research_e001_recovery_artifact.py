from gpu_stack.research.e001_recovery_artifact import (
    E001_RECOVERY_RESULT_SCHEMA,
    build_e001_recovery_result,
)


def _execution_run(policy_id, *, elapsed_ns, total_bytes):
    terminal_checkpoint = {
        "checkpoint_id": f"{policy_id}:checkpoint-2",
        "committed_step": 2,
    }
    return {
        "policy_id": policy_id,
        "start_ns": 0,
        "end_ns": elapsed_ns,
        "elapsed_ns": elapsed_ns,
        "terminal_frontier": {"lineage_id": "lineage-1", "committed_step": 2},
        "terminal_checkpoint": terminal_checkpoint,
        "recovery_episodes": [],
        "decision_batches": [],
        "work_ledger": {
            "accounting": {
                "attempted_work": 3.0,
                "committed_work": 2.0,
                "lost_work": 1.0,
            },
            "outcomes": [],
        },
        "checkpoint_manifests": [terminal_checkpoint],
        "link_segments": [],
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
            "attempted_compute_flops": 3.0,
            "valid_final_state_compute_flops": 2.0,
            "lost_compute_flops": 1.0,
            "recovery_time_ns": elapsed_ns,
            "modeled_energy_j": 1.0,
        },
        "snapshots": [],
    }


def _execution():
    frontier = {"lineage_id": "lineage-1", "committed_step": 2}
    return {
        "scenario": {"scenario_id": "recovery-test", "outages": []},
        "scenario_hash": "1" * 64,
        "engine_id": "e001-recovery-transition-engine-v2",
        "engine_source_hash": "2" * 64,
        "failure_trace": {"trace_id": "trace-1", "failures": []},
        "matched_frontier": frontier,
        "policies": [
            _execution_run(
                "synchronous-wait-restore",
                elapsed_ns=200,
                total_bytes=400,
            ),
            _execution_run(
                "fixed-local-checkpoint-restart",
                elapsed_ns=180,
                total_bytes=250,
            ),
            _execution_run(
                "adaptive-recovery",
                elapsed_ns=150,
                total_bytes=100,
            ),
            _execution_run(
                "future-trace-recovery-oracle",
                elapsed_ns=125,
                total_bytes=80,
            ),
        ],
        "comparison": {
            "same_frontier": True,
            "completion_time_ratio": 0.75,
            "total_inter_site_byte_fraction": 0.25,
            "work_conservation": True,
            "hypothesis_supported": True,
        },
    }


def test_recovery_result_binds_real_execution_ledgers_and_matched_comparison():
    result = build_e001_recovery_result(_execution())

    assert result["schema"] == E001_RECOVERY_RESULT_SCHEMA
    assert result["matched_frontier"]["committed_step"] == 2
    assert result["comparison"]["hypothesis_supported"] is True
    assert [run["policy_id"] for run in result["runs"]] == [
        "synchronous-wait-restore",
        "fixed-local-checkpoint-restart",
        "adaptive-recovery",
        "future-trace-recovery-oracle",
    ]
    candidate = result["runs"][2]
    assert candidate["metrics"]["completion_time_ratio"] == 0.75
    assert candidate["metrics"]["total_inter_site_byte_fraction"] == 0.25
    falsifiers = {item["falsifier_id"]: item for item in candidate["falsifiers"]}
    assert falsifiers["e001-progress"]["survived"] is None
    assert falsifiers["e001-wan"]["survived"] is False
    assert falsifiers["e001-time"]["survived"] is True
    assert {
        item["status"] for item in candidate["evidence_requirements"]
    } == {"unresolved"}
    assert result["conclusion"]["mechanics_answer"] == (
        "candidate_better_on_this_trace"
    )
    assert result["conclusion"]["status"] == (
        "inconclusive_frontier_hypothesis"
    )
    assert len(result["artifact_sha256"]) == 64
