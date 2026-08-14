"""End-to-end tests for the E001 recovery runner.

``run_e001_recovery_v2`` replays a frozen failure scenario (checked in as
``recovery-scenario-v2.json``) through four recovery policies: a synchronous
wait-and-restore baseline, a fixed local-checkpoint restart, the adaptive
candidate, and a future-trace oracle that peeks at the failure schedule as
an upper bound. Comparing policies is only fair if they end in the same
place, so every run must reach the same matched frontier (committed step 8)
and conserve work exactly — attempted equals committed plus lost.

These tests also check the runner records the physics of recovery, not just
the outcome: interrupted-lost work outcomes, positive inter-site bytes, lost
FLOPs, recovery time, and modeled energy; checkpoint and restore traffic on
the links; and membership churn where the desired site set differs from the
effective one. Finally, the execution must project into the result and
observatory artifacts without recomputation (hashes must agree), and neither
the candidate nor the oracle may spend more collective-traffic bytes than
the synchronous baseline.
"""

from pathlib import Path

from gpu_stack.research.e001_recovery_artifact import (
    E001_RECOVERY_RESULT_SCHEMA,
    build_e001_recovery_result,
)
from gpu_stack.research.e001_recovery_runner import (
    ADAPTIVE_POLICY_ID,
    FIXED_LOCAL_POLICY_ID,
    ORACLE_POLICY_ID,
    POLICY_IDS,
    SYNC_POLICY_ID,
    E001RecoveryScenario,
    run_e001_recovery_v2,
)
from gpu_stack.research.observatory_recovery import (
    E001_RECOVERY_OBSERVATORY_SCHEMA,
    build_e001_recovery_observatory_artifact,
)
from gpu_stack.research.recovery import WorkOutcomeDisposition


SCENARIO_PATH = Path(
    "experiments/e001-beyond-one-datacenter/recovery-scenario-v2.json"
)


def _execution():
    return run_e001_recovery_v2(E001RecoveryScenario.from_json_path(SCENARIO_PATH))


def test_recovery_runner_executes_the_frozen_four_policy_panel_end_to_end():
    execution = _execution()

    assert tuple(item.policy_id for item in execution.policies) == POLICY_IDS
    assert {item.policy_id for item in execution.policies} == {
        SYNC_POLICY_ID,
        FIXED_LOCAL_POLICY_ID,
        ADAPTIVE_POLICY_ID,
        ORACLE_POLICY_ID,
    }
    assert all(
        item.terminal_frontier == execution.matched_frontier == 8
        for item in execution.policies
    )
    assert all(item.exact_work_conservation for item in execution.policies)
    assert all(len(item.recovery_episodes) == 2 for item in execution.policies)
    assert all(
        item.terminal_checkpoint.committed_step == execution.matched_frontier
        for item in execution.policies
    )


def test_recovery_runner_emits_preemption_replay_membership_and_physical_costs():
    execution = _execution()

    for policy in execution.policies:
        payload = policy.to_dict()
        metrics = payload["metrics"]
        dispositions = {
            item.disposition for item in policy.work_ledger.outcomes
        }
        assert WorkOutcomeDisposition.INTERRUPTED_LOST in dispositions
        assert metrics["learning_progress"]["evidence_class"] == "prior"
        assert metrics["total_inter_site_link_bytes"] > 0
        assert metrics["lost_compute_flops"] > 0
        assert metrics["recovery_time_ns"] > 0
        assert metrics["modeled_energy_j"] > 0
        assert {item.traffic_class for item in policy.link_segments} >= {
            "checkpoint",
            "restore",
        }
        assert any(
            batch["desired_membership"] != batch["effective_membership"]
            for batch in payload["decision_batches"]
        )

    assert any(
        WorkOutcomeDisposition.SUPERSEDED
        in {item.disposition for item in policy.work_ledger.outcomes}
        for policy in execution.policies
    )


def test_recovery_execution_projects_without_recomputing_into_result_and_observatory():
    execution = _execution()
    result = build_e001_recovery_result(execution)
    observatory = build_e001_recovery_observatory_artifact(
        result,
        source_uri=str(SCENARIO_PATH),
    )

    assert result["schema"] == E001_RECOVERY_RESULT_SCHEMA
    assert len(result["runs"]) == 4
    assert observatory["schema"] == E001_RECOVERY_OBSERVATORY_SCHEMA
    assert observatory["source_result"]["artifact_sha256"] == result[
        "artifact_sha256"
    ]
    assert len(observatory["runs"]) == 4


def test_candidate_and_oracle_do_not_use_more_collective_bytes_than_sync_baseline():
    execution = _execution()
    by_policy = {item.policy_id: item for item in execution.policies}

    sync_collective = sum(
        segment.link_bytes
        for segment in by_policy[SYNC_POLICY_ID].link_segments
        if segment.traffic_class.endswith("collective")
    )
    for policy_id in (ADAPTIVE_POLICY_ID, ORACLE_POLICY_ID):
        policy_collective = sum(
            segment.link_bytes
            for segment in by_policy[policy_id].link_segments
            if segment.traffic_class.endswith("collective")
        )
        assert policy_collective <= sync_collective
