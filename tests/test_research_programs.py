"""Tests for the preregistered experiment protocol catalog (E001-E002).

A protocol is a preregistered experimental design: named metrics, scalar
falsifier gates (metric, comparison operator, threshold), and structured
evidence requirements, all frozen and hashed before any experiment runs.
Preregistration only works if the catalog cannot drift, so these tests pin
it in detail.

The catalog lists E001 and E002 in order, is read-only, and rejects
unknown ids with an explicit error. Every protocol beyond E001 carries its
title, the shared 2026-04-13/2026-07-12 source window, a note that no
result is claimed, and a protocol hash. Two structural rules keep the gate
system honest. Each primary metric must be judged somewhere — by a scalar
falsifier or a mandatory structured requirement. And vector-valued outcomes
(latency percentiles, coverage families, regret panels) get structured
requirements rather than invented scalar thresholds; the per-experiment
tests then pin every gate's exact metric, operator, and threshold, and the
final test confirms nothing irreducible is buried in free-text notes.
"""

import pytest

from gpu_stack.research.e001 import E001_PROTOCOL
from gpu_stack.research.programs import (
    E002_PROTOCOL,
    EXPERIMENT_PROTOCOLS,
    protocol_catalog,
    protocol_for,
)
from gpu_stack.research.protocols import (
    ComparisonOperator,
    EvidenceRequirementSpec,
    ExperimentStage,
)


def _gate(protocol, falsifier_id):
    return next(
        item for item in protocol.falsifiers if item.falsifier_id == falsifier_id
    )


def _requirement(protocol, requirement_id):
    return next(
        item
        for item in protocol.evidence_requirements
        if item.requirement_id == requirement_id
    )


def _assert_gate(
    protocol,
    falsifier_id,
    metric,
    operator,
    threshold,
    upper_threshold=None,
):
    gate = _gate(protocol, falsifier_id)
    assert gate.metric == metric
    assert gate.operator is operator
    assert gate.threshold == threshold
    assert gate.upper_threshold == upper_threshold


def test_catalog_contains_e001_and_e002_in_order_and_reuses_e001():
    assert tuple(EXPERIMENT_PROTOCOLS) == ("E001", "E002")
    assert protocol_catalog() == tuple(EXPERIMENT_PROTOCOLS.values())
    assert protocol_for("E001") is E001_PROTOCOL
    assert protocol_for(" e002 ") is E002_PROTOCOL


def test_catalog_mapping_is_read_only_and_unknown_protocol_is_explicit():
    with pytest.raises(TypeError):
        EXPERIMENT_PROTOCOLS["E007"] = E002_PROTOCOL
    with pytest.raises(KeyError, match="available: E001, E002"):
        protocol_for("E999")


def test_every_new_protocol_has_preregistered_identity_and_no_result_claim():
    expected = {
        "E002": "Shape the Power Waveform",
    }
    for protocol in protocol_catalog()[1:]:
        assert protocol.title == expected[protocol.experiment_id]
        assert protocol.source_window == "2026-04-13/2026-07-12"
        assert any("no experiment result" in note or "no result" in note for note in protocol.notes)
        assert protocol.protocol_hash
        metric_names = {metric.name for metric in protocol.metrics}
        assert {gate.metric for gate in protocol.falsifiers} <= metric_names
        assert protocol.evidence_requirements
        assert all(
            isinstance(requirement, EvidenceRequirementSpec)
            and requirement.mandatory
            for requirement in protocol.evidence_requirements
        )


def test_every_primary_metric_has_a_scalar_or_mandatory_structured_gate():
    for protocol in protocol_catalog()[1:]:
        primary = {metric.name for metric in protocol.metrics if metric.primary}
        scalar = {gate.metric for gate in protocol.falsifiers}
        structured = {
            metric
            for requirement in protocol.evidence_requirements
            if requirement.mandatory
            for metric in requirement.required_metrics
        }
        assert primary <= scalar | structured


def test_integration_audit_requirements_are_exact_and_mandatory():
    expected = {
        "E002": {
            "grid_safety_vector_by_mode",
            "one_dimensional_baseline_vector_dominance",
            "cross_band_no_displacement",
            "full_boundary_nonreversal",
            "equal_useful_work_accounting",
            "withheld_facility_directional_transfer",
            "decision_regret_reported_or_thresholded",
        },
    }
    for protocol in protocol_catalog()[1:]:
        assert {
            requirement.requirement_id
            for requirement in protocol.evidence_requirements
        } == expected[protocol.experiment_id]
        assert all(
            requirement.earliest_resolvable_stage
            in {
                ExperimentStage.VIRTUAL,
                ExperimentStage.SHADOW,
                ExperimentStage.CONTROLLED,
            }
            for requirement in protocol.evidence_requirements
        )


def test_e002_encodes_effect_bounds_semantics_and_model_admission_gates():
    _assert_gate(
        E002_PROTOCOL,
        "e002-spectral-energy",
        "danger_band_spectral_energy_reduction_lower_95_bound",
        ComparisonOperator.GE,
        0.50,
    )
    _assert_gate(
        E002_PROTOCOL,
        "e002-time-to-target",
        "time_to_target_regression_upper_95_bound",
        ComparisonOperator.LE,
        0.02,
    )
    _assert_gate(
        E002_PROTOCOL,
        "e002-admission-capacity",
        "admission_capacity_improvement_lower_95_bound",
        ComparisonOperator.GE,
        0.10,
    )
    _assert_gate(
        E002_PROTOCOL,
        "e002-exact-semantics",
        "committed_optimizer_step_invariant_violations",
        ComparisonOperator.LE,
        0.0,
    )
    _assert_gate(
        E002_PROTOCOL,
        "e002-waveform-admission",
        "held_out_pcc_waveform_nrmse",
        ComparisonOperator.LE,
        0.10,
    )
    _assert_gate(
        E002_PROTOCOL,
        "e002-interval-admission",
        "nominal_90_interval_coverage",
        ComparisonOperator.BETWEEN,
        0.85,
        0.95,
    )
    grid = _requirement(E002_PROTOCOL, "grid_safety_vector_by_mode")
    assert grid.earliest_resolvable_stage is ExperimentStage.VIRTUAL
    assert set(grid.required_metrics) == {
        "maximum_modeled_frequency_deviation",
        "maximum_tie_line_oscillation",
        "operator_threshold_exposure_seconds",
    }
    transfer = _requirement(
        E002_PROTOCOL, "withheld_facility_directional_transfer"
    )
    assert transfer.earliest_resolvable_stage is ExperimentStage.SHADOW
    assert "oracle_decision_regret" in _requirement(
        E002_PROTOCOL, "decision_regret_reported_or_thresholded"
    ).required_metrics


def test_irreducible_gates_are_structured_instead_of_buried_in_notes():
    for protocol in (E002_PROTOCOL,):
        assert not any(
            "scalar schema cannot faithfully encode" in note
            for note in protocol.notes
        )
        assert all(
            requirement.acceptance_rule.strip()
            and requirement.evidence_boundary.strip()
            for requirement in protocol.evidence_requirements
        )
        scalar_metrics = {gate.metric for gate in protocol.falsifiers}
        structured_metrics = {
            metric
            for requirement in protocol.evidence_requirements
            for metric in requirement.required_metrics
        }
        assert structured_metrics - scalar_metrics
