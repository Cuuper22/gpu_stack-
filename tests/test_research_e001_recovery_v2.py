import json
from pathlib import Path

from gpu_stack.research.e001 import E001_PROTOCOL
from gpu_stack.research.e001_recovery_v2 import (
    E001_PARENT_BASELINE_OBLIGATION_IDS,
    E001_RECOVERY_V2_BASELINE_POLICY_IDS,
    E001_RECOVERY_V2_CANDIDATE_POLICY_ID,
    E001_RECOVERY_V2_COMPARATOR_POLICY_IDS,
    E001_RECOVERY_V2_POLICY_IDS,
    E001_RECOVERY_V2_POLICY_ROLES,
    E001_RECOVERY_V2_PROTOCOL,
)


V1_OBSERVATORY_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "data"
    / "e001-screening-v1.json"
)


def _requirement(requirement_id: str):
    return next(
        item
        for item in E001_RECOVERY_V2_PROTOCOL.evidence_requirements
        if item.requirement_id == requirement_id
    )


def test_recovery_v2_is_separate_from_the_persisted_v1_protocol():
    persisted = json.loads(V1_OBSERVATORY_PATH.read_text(encoding="utf-8"))

    assert persisted["schema"] == "gpu-stack.causal-observatory.e001.v1"
    assert persisted["protocol_hash"] == E001_PROTOCOL.protocol_hash
    assert E001_RECOVERY_V2_PROTOCOL.experiment_id == "E001-RECOVERY-V2"
    assert E001_RECOVERY_V2_PROTOCOL.protocol_hash != E001_PROTOCOL.protocol_hash


def test_recovery_policy_ids_distinguish_candidate_baselines_and_parent_debt():
    assert E001_RECOVERY_V2_POLICY_IDS == (
        "synchronous-wait-restore",
        "fixed-local-checkpoint-restart",
        "fixed-cadence-reactive-membership",
        "power-aware-migration-without-learning-adaptation",
        "adaptive-recovery",
        "future-trace-recovery-oracle",
    )
    assert E001_RECOVERY_V2_CANDIDATE_POLICY_ID not in (
        E001_RECOVERY_V2_BASELINE_POLICY_IDS
    )
    assert E001_RECOVERY_V2_POLICY_ROLES["adaptive-recovery"] == "candidate"
    assert (
        E001_RECOVERY_V2_POLICY_ROLES["future-trace-recovery-oracle"]
        == "oracle_comparator"
    )
    assert {
        role
        for policy_id, role in E001_RECOVERY_V2_POLICY_ROLES.items()
        if policy_id
        not in {"adaptive-recovery", "future-trace-recovery-oracle"}
    } == {"baseline"}
    assert set(E001_RECOVERY_V2_PROTOCOL.baselines) == {
        *E001_RECOVERY_V2_COMPARATOR_POLICY_IDS,
        *E001_PARENT_BASELINE_OBLIGATION_IDS,
    }


def test_total_wan_gate_is_auditable_and_payload_is_diagnostic_only():
    metrics = {item.name: item for item in E001_RECOVERY_V2_PROTOCOL.metrics}
    falsifiers = {
        item.falsifier_id: item for item in E001_RECOVERY_V2_PROTOCOL.falsifiers
    }

    assert metrics["collective_payload_byte_fraction"].primary is False
    assert falsifiers["e001-wan"].metric == "total_inter_site_byte_fraction"
    assert {
        "total_inter_site_link_bytes",
        "synchronous_recovery_baseline_total_inter_site_link_bytes",
        "completed_collective_link_bytes",
        "aborted_collective_link_bytes",
        "remote_checkpoint_replication_link_bytes",
        "remote_checkpoint_restore_link_bytes",
        "recovery_state_redistribution_link_bytes",
        "planned_state_migration_link_bytes",
    } <= set(metrics)


def test_recovery_gates_freeze_exact_panels_without_undefined_regret():
    observable = _requirement("e001-observable-failure-recovery-epochs")
    reactive = _requirement("e001-reactive-membership-without-trace-leakage")
    conservation = _requirement("e001-preemption-replay-conservation")
    checkpoint = _requirement("e001-checkpoint-lineage-and-restore")
    baselines = _requirement("e001-recovery-baseline-completeness")

    assert observable.required_panels == (
        "failure occurrence",
        "failure observation",
        "recovery occurrence",
        "recovery observation",
        "checkpoint commit",
        "restore completion",
        "safe re-entry",
    )
    assert "collective interruption during latency" in conservation.required_panels
    assert "collective interruption during payload" in conservation.required_panels
    assert "delayed failure observation" in reactive.required_panels
    assert "failed local checkpoint storage" in checkpoint.required_panels
    assert "remote durable checkpoint" in checkpoint.required_panels
    assert baselines.required_panels == E001_RECOVERY_V2_POLICY_IDS

    for requirement in (observable, reactive, conservation, checkpoint, baselines):
        assert "policy_decision_regret" not in requirement.required_metrics
