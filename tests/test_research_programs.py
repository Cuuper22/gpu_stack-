import pytest

from gpu_stack.research.e001 import E001_PROTOCOL
from gpu_stack.research.programs import (
    E002_PROTOCOL,
    E003_PROTOCOL,
    E004_PROTOCOL,
    E005_PROTOCOL,
    E006_PROTOCOL,
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


def test_catalog_contains_e001_through_e006_in_order_and_reuses_e001():
    assert tuple(EXPERIMENT_PROTOCOLS) == (
        "E001",
        "E002",
        "E003",
        "E004",
        "E005",
        "E006",
    )
    assert protocol_catalog() == tuple(EXPERIMENT_PROTOCOLS.values())
    assert protocol_for("E001") is E001_PROTOCOL
    assert protocol_for(" e006 ") is E006_PROTOCOL


def test_catalog_mapping_is_read_only_and_unknown_protocol_is_explicit():
    with pytest.raises(TypeError):
        EXPERIMENT_PROTOCOLS["E007"] = E006_PROTOCOL
    with pytest.raises(KeyError, match="available: E001, E002, E003, E004, E005, E006"):
        protocol_for("E999")


def test_every_new_protocol_has_preregistered_identity_and_no_result_claim():
    expected = {
        "E002": "Shape the Power Waveform",
        "E003": "Semantic Fault Tolerance",
        "E004": "Fluid Inference Topology",
        "E005": "Heterogeneous Architecture Co-design",
        "E006": "Firm Grid-responsive Inference",
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


def test_vector_outcomes_gain_structure_without_invented_scalar_thresholds():
    structured_only = {
        "E003": {
            "redundant_flops_per_intercepted_critical_event",
            "protection_fraction_spent_on_oracle_benign_events",
            "semantic_harm_interval_coverage",
            "oracle_protection_budget_regret",
        },
        "E004": {
            "p50_ttft_seconds",
            "p99_ttft_seconds",
            "p50_tpot_seconds_per_token",
            "p99_tpot_seconds_per_token",
            "p50_session_completion_latency_seconds",
            "p99_session_completion_latency_seconds",
            "nominal_50_interval_coverage",
            "nominal_95_interval_coverage",
        },
        "E005": {
            "capability_geometric_mean",
            "facility_energy_j",
            "time_to_capability_target_seconds",
        },
        "E006": {
            "p50_ttft_seconds",
            "p50_tpot_seconds_per_token",
            "sustained_delivery_error",
            "settlement_interval_tracking_error",
            "reserve_decision_regret",
            "reserve_prediction_interval_coverage",
            "deferred_work_units",
            "deferred_facility_energy_j",
            "rejected_request_fraction",
            "expired_request_fraction",
        },
    }
    for protocol in protocol_catalog()[2:]:
        scalar = {gate.metric for gate in protocol.falsifiers}
        structured = {
            metric
            for requirement in protocol.evidence_requirements
            for metric in requirement.required_metrics
        }
        expected = structured_only[protocol.experiment_id]
        assert not expected & scalar
        assert expected <= structured


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
        "E003": {
            "complete_quality_vector_equivalence",
            "baseline_vector_dominance",
            "structured_fault_transfer",
            "harmful_intervention_ranking_transfer",
            "long_horizon_optimizer_and_capability_safety",
            "production_incidence_is_measured",
            "real_system_directional_transfer",
            "fault_family_power_and_completeness",
        },
        "E004": {
            "equal_accounting_baseline_dominance",
            "ranking_transfer_by_named_panel",
            "controlled_cluster_directional_transfer",
            "causal_exclusion",
            "workload_family_vector_nondegradation",
            "factorial_action_access_equivalence",
            "interval_family_completeness",
        },
        "E005": {
            "raw_capability_vector_and_frozen_normalization",
            "equalized_full_search_accounting_nonreversal",
            "ranking_transfer_by_every_named_panel",
            "out_of_scope_abstention_adequacy",
            "proxy_to_target_directional_transfer",
            "architecture_counterfactual_identified",
            "failed_candidate_accounting_completeness",
        },
        "E006": {
            "full_horizon_deferred_work_energy_nonreversal",
            "accounting_exclusion_robustness",
            "ranking_and_confidence_transfer_by_panel",
            "non_request_or_isolated_baseline_vector_dominance",
            "controlled_live_directional_transfer",
            "service_vector_by_workload",
            "bid_selection_and_interval_method_frozen",
            "offered_reserve_availability_and_derating",
            "event_campus_day_independence_and_power",
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


def test_e003_reduces_vector_equivalence_to_the_exact_worst_case_statistic():
    metric = next(
        item
        for item in E003_PROTOCOL.metrics
        if item.name == "maximum_primary_quality_90ci_excursion_sd"
    )
    assert "Maximum absolute endpoint of any primary metric" in metric.description
    _assert_gate(
        E003_PROTOCOL,
        "e003-quality-vector-equivalence",
        "maximum_primary_quality_90ci_excursion_sd",
        ComparisonOperator.LE,
        0.20,
    )
    _assert_gate(
        E003_PROTOCOL,
        "e003-run-equivalence",
        "defended_run_equivalence_fraction",
        ComparisonOperator.GE,
        0.95,
    )
    _assert_gate(
        E003_PROTOCOL,
        "e003-critical-interception",
        "critical_event_interception_lower_95_bound",
        ComparisonOperator.GE,
        0.99,
    )
    _assert_gate(
        E003_PROTOCOL,
        "e003-clean-false-action",
        "clean_step_false_action_upper_95_bound",
        ComparisonOperator.LE,
        0.01,
    )
    for gate_id, metric_name in (
        ("e003-clean-time-tax", "clean_time_to_target_tax_upper_95_bound"),
        ("e003-clean-energy-tax", "clean_facility_energy_tax_upper_95_bound"),
        (
            "e003-production-time-tax",
            "production_incidence_time_tax_upper_95_bound",
        ),
        (
            "e003-production-energy-tax",
            "production_incidence_energy_tax_upper_95_bound",
        ),
    ):
        _assert_gate(
            E003_PROTOCOL,
            gate_id,
            metric_name,
            ComparisonOperator.LE,
            0.02,
        )
    _assert_gate(
        E003_PROTOCOL,
        "e003-redundant-flops",
        "redundant_flops_fraction_of_uniform_duplicate_upper_95_bound",
        ComparisonOperator.LE,
        0.50,
    )
    primary = {metric.name for metric in E003_PROTOCOL.metrics if metric.primary}
    assert {
        "redundant_flops_per_intercepted_critical_event",
        "protection_fraction_spent_on_oracle_benign_events",
        "semantic_harm_interval_coverage",
        "oracle_protection_budget_regret",
    } <= primary
    quality_vector = _requirement(
        E003_PROTOCOL, "complete_quality_vector_equivalence"
    )
    assert quality_vector.earliest_resolvable_stage is ExperimentStage.CONTROLLED
    assert "every frozen primary quality metric" in quality_vector.required_panels
    incidence = _requirement(E003_PROTOCOL, "production_incidence_is_measured")
    assert incidence.earliest_resolvable_stage is ExperimentStage.SHADOW
    assert set(incidence.required_metrics) == {
        "production_incidence_time_tax_upper_95_bound",
        "production_incidence_energy_tax_upper_95_bound",
    }


def test_e004_encodes_interaction_regime_crossing_and_family_worst_cases():
    _assert_gate(
        E004_PROTOCOL,
        "e004-static-gain",
        "joint_vs_static_u_improvement",
        ComparisonOperator.GE,
        0.20,
    )
    _assert_gate(
        E004_PROTOCOL,
        "e004-independent-gain",
        "joint_vs_independent_u_improvement",
        ComparisonOperator.GE,
        0.10,
    )
    _assert_gate(
        E004_PROTOCOL,
        "e004-interaction-size",
        "three_way_interaction_point_estimate",
        ComparisonOperator.GE,
        0.05,
    )
    _assert_gate(
        E004_PROTOCOL,
        "e004-interaction-sign",
        "three_way_interaction_lower_95_bound",
        ComparisonOperator.GT,
        0.0,
    )
    _assert_gate(
        E004_PROTOCOL,
        "e004-regime-crossing",
        "regime_crossing_workload_family_count",
        ComparisonOperator.GE,
        3.0,
    )
    _assert_gate(
        E004_PROTOCOL,
        "e004-static-dominance",
        "static_regime_dominated_workload_family_count",
        ComparisonOperator.LE,
        1.0,
    )
    _assert_gate(
        E004_PROTOCOL,
        "e004-utility-noninferiority",
        "worst_workload_utility_regression",
        ComparisonOperator.LE,
        0.01,
    )
    _assert_gate(
        E004_PROTOCOL,
        "e004-slo-noninferiority",
        "worst_workload_slo_decline_percentage_points",
        ComparisonOperator.LE,
        1.0,
    )
    _assert_gate(
        E004_PROTOCOL,
        "e004-decision-regret",
        "intervention_regret_fraction_of_oracle_value",
        ComparisonOperator.LE,
        0.10,
    )
    _assert_gate(
        E004_PROTOCOL,
        "e004-interval-coverage",
        "nominal_90_interval_coverage",
        ComparisonOperator.GE,
        0.80,
    )
    primary = {metric.name for metric in E004_PROTOCOL.metrics if metric.primary}
    assert {
        "p50_ttft_seconds",
        "p99_ttft_seconds",
        "p50_tpot_seconds_per_token",
        "p99_tpot_seconds_per_token",
        "p50_session_completion_latency_seconds",
        "p99_session_completion_latency_seconds",
        "nominal_50_interval_coverage",
        "nominal_90_interval_coverage",
        "nominal_95_interval_coverage",
    } <= primary
    interval_family = _requirement(E004_PROTOCOL, "interval_family_completeness")
    assert interval_family.earliest_resolvable_stage is ExperimentStage.VIRTUAL
    assert set(interval_family.required_metrics) == {
        "nominal_50_interval_coverage",
        "nominal_90_interval_coverage",
        "nominal_95_interval_coverage",
    }
    service_vector = _requirement(
        E004_PROTOCOL, "workload_family_vector_nondegradation"
    )
    assert service_vector.earliest_resolvable_stage is ExperimentStage.CONTROLLED
    assert "p99_session_completion_latency_seconds" in service_vector.required_metrics


def test_e005_encodes_architecture_attribution_and_search_quality():
    _assert_gate(
        E005_PROTOCOL,
        "e005-ce-gain",
        "ce_improvement_over_best_homogeneous",
        ComparisonOperator.GE,
        0.25,
    )
    _assert_gate(
        E005_PROTOCOL,
        "e005-task-family-noninferiority",
        "worst_task_family_metric_regression",
        ComparisonOperator.LE,
        0.02,
    )
    _assert_gate(
        E005_PROTOCOL,
        "e005-architecture-attribution",
        "architecture_attributable_joint_gain_fraction",
        ComparisonOperator.GE,
        0.50,
    )
    _assert_gate(
        E005_PROTOCOL,
        "e005-substantive-heterogeneity",
        "hardware_classes_at_20pct_training_flops",
        ComparisonOperator.GE,
        2.0,
    )
    _assert_gate(
        E005_PROTOCOL,
        "e005-ranking",
        "held_out_kendall_ranking_correlation",
        ComparisonOperator.GE,
        0.70,
    )
    _assert_gate(
        E005_PROTOCOL,
        "e005-selection-regret",
        "selected_design_regret",
        ComparisonOperator.LE,
        0.10,
    )
    _assert_gate(
        E005_PROTOCOL,
        "e005-interval-coverage",
        "nominal_90_interval_coverage",
        ComparisonOperator.BETWEEN,
        0.85,
        0.95,
    )
    _assert_gate(
        E005_PROTOCOL,
        "e005-search-energy",
        "search_energy_fraction_of_target_run",
        ComparisonOperator.LE,
        0.25,
    )
    capability = _requirement(
        E005_PROTOCOL, "raw_capability_vector_and_frozen_normalization"
    )
    assert capability.earliest_resolvable_stage is ExperimentStage.CONTROLLED
    assert set(capability.required_metrics) == {
        "capability_geometric_mean",
        "worst_task_family_metric_regression",
        "time_to_capability_target_seconds",
    }
    assert {
        "every frozen raw task-family metric",
        "frozen semantic floors and ceilings",
        "composite C",
    } <= set(capability.required_panels)
    failed = _requirement(
        E005_PROTOCOL, "failed_candidate_accounting_completeness"
    )
    assert failed.earliest_resolvable_stage is ExperimentStage.VIRTUAL
    assert "failed_and_repeated_work_energy_j" in failed.required_metrics


def test_e006_encodes_firm_delivery_service_and_rebound_constraints():
    expected = (
        (
            "e006-firm-load-fraction",
            "r_firm_fraction_of_matched_load",
            ComparisonOperator.GE,
            0.20,
        ),
        (
            "e006-isolated-mechanism-gain",
            "joint_to_best_isolated_r_firm_ratio",
            ComparisonOperator.GE,
            1.50,
        ),
        (
            "e006-delivery-confidence",
            "event_delivery_probability_lower_95_bound",
            ComparisonOperator.GE,
            0.99,
        ),
        (
            "e006-response-time",
            "time_to_90pct_delivery_seconds",
            ComparisonOperator.LE,
            10.0,
        ),
        (
            "e006-sustained-delivery",
            "full_delivery_sustained_seconds",
            ComparisonOperator.GE,
            900.0,
        ),
        (
            "e006-ttft-slo",
            "worst_ttft_slo_decline_percentage_points",
            ComparisonOperator.LE,
            1.0,
        ),
        (
            "e006-tpot-slo",
            "worst_tpot_slo_decline_percentage_points",
            ComparisonOperator.LE,
            1.0,
        ),
        (
            "e006-p99-ttft",
            "worst_p99_ttft_to_frozen_limit_ratio",
            ComparisonOperator.LE,
            1.0,
        ),
        (
            "e006-p99-tpot",
            "worst_p99_tpot_to_frozen_limit_ratio",
            ComparisonOperator.LE,
            1.0,
        ),
        (
            "e006-request-utility",
            "worst_frozen_request_utility_decline",
            ComparisonOperator.LE,
            0.01,
        ),
        (
            "e006-rebound",
            "post_event_peak_excess_fraction",
            ComparisonOperator.LE,
            0.05,
        ),
    )
    for gate_id, metric, operator, threshold in expected:
        _assert_gate(E006_PROTOCOL, gate_id, metric, operator, threshold)

    primary = {metric.name for metric in E006_PROTOCOL.metrics if metric.primary}
    assert {
        "p50_ttft_seconds",
        "p50_tpot_seconds_per_token",
        "rejected_request_fraction",
        "expired_request_fraction",
        "deferred_work_units",
        "deferred_facility_energy_j",
        "reserve_prediction_interval_coverage",
    } <= primary
    service = _requirement(E006_PROTOCOL, "service_vector_by_workload")
    assert service.earliest_resolvable_stage is ExperimentStage.CONTROLLED
    assert {
        "p50_ttft_seconds",
        "p50_tpot_seconds_per_token",
        "rejected_request_fraction",
        "expired_request_fraction",
    } <= set(service.required_metrics)
    transfer = _requirement(
        E006_PROTOCOL, "ranking_and_confidence_transfer_by_panel"
    )
    assert transfer.earliest_resolvable_stage is ExperimentStage.SHADOW
    assert "reserve_prediction_interval_coverage" in transfer.required_metrics
    independence = _requirement(
        E006_PROTOCOL, "event_campus_day_independence_and_power"
    )
    assert independence.earliest_resolvable_stage is ExperimentStage.VIRTUAL


def test_irreducible_gates_are_structured_instead_of_buried_in_notes():
    for protocol in (
        E002_PROTOCOL,
        E003_PROTOCOL,
        E004_PROTOCOL,
        E005_PROTOCOL,
        E006_PROTOCOL,
    ):
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
