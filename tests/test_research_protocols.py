from dataclasses import replace

import pytest

from gpu_stack.research.protocols import (
    ComparisonOperator,
    EvidenceRequirementResult,
    EvidenceRequirementSpec,
    EvidenceRequirementStatus,
    ExperimentProtocol,
    ExperimentRunArtifact,
    ExperimentStage,
    FalsifierSpec,
    MetricSpec,
)


def _protocol():
    return ExperimentProtocol(
        experiment_id="E001",
        title="Beyond One Datacenter",
        question="Can training span sites?",
        hypothesis="Adaptive control preserves useful progress.",
        baselines=("centralized", "fixed-local"),
        metrics=(
            MetricSpec("progress_ratio", "1", "Progress relative to centralized", True),
            MetricSpec("wan_reduction", "1", "Inter-site byte reduction", True),
        ),
        falsifiers=(
            FalsifierSpec("f1", "progress_ratio", ComparisonOperator.GE, 0.95),
            FalsifierSpec("f2", "wan_reduction", ComparisonOperator.GE, 10.0),
        ),
        independent_variables=("site_count", "local_steps"),
        held_out_dimensions=("hardware_family", "site"),
        real_validation_requirements=("three geographic sites",),
        seed_policy="fixed published seeds",
        source_window="2026-04-13/2026-07-12",
    )


def test_protocol_hash_and_serialization_are_deterministic():
    first = _protocol()
    second = _protocol()
    assert first.protocol_hash == second.protocol_hash
    assert first.canonical_json() == second.canonical_json()
    assert first.schema_version == "2.0"


def test_protocol_evaluates_preregistered_falsifiers():
    protocol = _protocol()
    passed = protocol.evaluate_falsifiers({"progress_ratio": 0.96, "wan_reduction": 11})
    failed = protocol.evaluate_falsifiers({"progress_ratio": 0.90, "wan_reduction": 11})
    assert all(item.survived for item in passed)
    assert failed[0].survived is False


def test_run_artifact_refuses_calibration_evaluation_leakage():
    protocol = _protocol()
    with pytest.raises(ValueError, match="overlap"):
        protocol.build_run_artifact(
            run_id="run-1",
            stage=ExperimentStage.VIRTUAL,
            policy="adaptive",
            scenario_id="scenario",
            metrics={"progress_ratio": 1.0, "wan_reduction": 10.0},
            calibration_observation_ids=("same",),
            evaluation_observation_ids=("same",),
        )


def test_virtual_survival_is_not_labeled_validation():
    protocol = _protocol()
    metrics = {"progress_ratio": 0.97, "wan_reduction": 12.0}
    artifact = protocol.build_run_artifact(
        run_id="run-1",
        stage=ExperimentStage.VIRTUAL,
        policy="adaptive",
        scenario_id="scenario",
        metrics=metrics,
    )
    assert artifact.conclusion == "survived_virtual_screen"
    assert artifact.to_dict()["stage"] == "virtual"
    assert artifact.to_dict()["schema"] == "gpu-stack.experiment-run.v2"


def test_missing_evidence_keeps_a_numerical_virtual_screen_inconclusive():
    protocol = _protocol()
    metrics = {"progress_ratio": 0.97, "wan_reduction": 12.0}
    artifact = protocol.build_run_artifact(
        run_id="run-gap",
        stage=ExperimentStage.VIRTUAL,
        policy="adaptive",
        scenario_id="scenario",
        metrics=metrics,
        evidence_gaps=("no held-out real-cluster observations",),
    )
    assert artifact.conclusion == "inconclusive"
    assert artifact.to_dict()["evidence_gaps"] == [
        "no held-out real-cluster observations"
    ]


def test_failed_virtual_gate_is_not_hidden_by_other_evidence_gaps():
    protocol = _protocol()
    metrics = {"progress_ratio": 0.90, "wan_reduction": 12.0}
    artifact = protocol.build_run_artifact(
        run_id="run-failed-screen",
        stage=ExperimentStage.VIRTUAL,
        policy="adaptive",
        scenario_id="scenario",
        metrics=metrics,
        evidence_gaps=("real-cluster transfer remains unmeasured",),
    )

    assert artifact.conclusion == "failed_virtual_screen"


def test_artifact_snapshot_prevents_omitting_a_preregistered_falsifier():
    protocol = _protocol()
    complete = protocol.build_run_artifact(
        run_id="complete",
        stage=ExperimentStage.VIRTUAL,
        policy="adaptive",
        scenario_id="scenario",
        metrics={"progress_ratio": 0.97, "wan_reduction": 12.0},
    )

    with pytest.raises(ValueError, match="exactly match"):
        ExperimentRunArtifact(
            run_id="truncated",
            protocol_hash=protocol.protocol_hash,
            experiment_id=protocol.experiment_id,
            stage=ExperimentStage.VIRTUAL,
            policy="adaptive",
            scenario_id="scenario",
            metrics={"progress_ratio": 0.97, "wan_reduction": 12.0},
            falsifiers=complete.falsifiers[:1],
            evidence_requirements=(),
            protocol_snapshot_json=protocol.canonical_json(),
        )


def test_mandatory_structured_requirement_is_unresolved_by_default():
    requirement = EvidenceRequirementSpec(
        requirement_id="heldout-vector",
        kind="vector_equivalence",
        description="Resolve the complete held-out outcome vector.",
        earliest_resolvable_stage=ExperimentStage.VIRTUAL,
        required_metrics=("progress_ratio",),
        required_panels=("heldout-model",),
        acceptance_rule="Every held-out panel satisfies the frozen vector rule.",
        evidence_boundary="Requires panel-level evidence.",
    )
    protocol = replace(_protocol(), evidence_requirements=(requirement,))
    metrics = {"progress_ratio": 0.97, "wan_reduction": 12.0}

    unresolved = protocol.build_run_artifact(
        run_id="unresolved",
        stage=ExperimentStage.VIRTUAL,
        policy="adaptive",
        scenario_id="scenario",
        metrics=metrics,
    )
    assert unresolved.conclusion == "inconclusive"
    assert unresolved.evidence_requirements[0].status is (
        EvidenceRequirementStatus.UNRESOLVED
    )

    with pytest.raises(ValueError, match="missing required evidence"):
        protocol.build_run_artifact(
            run_id="missing-panel",
            stage=ExperimentStage.VIRTUAL,
            policy="adaptive",
            scenario_id="scenario",
            metrics=metrics,
            requirement_results=(
                EvidenceRequirementResult(
                    requirement_id="heldout-vector",
                    status=EvidenceRequirementStatus.SATISFIED,
                    reason="claimed complete",
                    evidence_refs=("observation:heldout",),
                ),
            ),
        )

    satisfied = protocol.build_run_artifact(
        run_id="satisfied",
        stage=ExperimentStage.VIRTUAL,
        policy="adaptive",
        scenario_id="scenario",
        metrics=metrics,
        requirement_results=(
            EvidenceRequirementResult(
                requirement_id="heldout-vector",
                status=EvidenceRequirementStatus.SATISFIED,
                reason="panel passed the frozen rule",
                evidence_refs=("observation:heldout",),
                panel_results={"heldout-model": "satisfied"},
            ),
        ),
    )
    assert satisfied.conclusion == "survived_virtual_screen"
