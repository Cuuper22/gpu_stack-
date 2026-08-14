"""Machine-readable preregistrations for GPUSTACK research programs E001-E006.

The Markdown experiment documents stay the human-readable source of truth.
This module mirrors just their scalar and structured evidence gates so
runners can check them in code. Qualitative claims — transfer, vector,
accounting, causal — are deliberately not converted into invented numerical
thresholds; a gate exists here only if the document really states one.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping, Tuple

from .e001 import E001_PROTOCOL
from .protocols import (
    ComparisonOperator,
    EvidenceRequirementSpec,
    ExperimentProtocol,
    ExperimentStage,
    FalsifierSpec,
    MetricSpec,
)


E002_PROTOCOL = ExperimentProtocol(
    experiment_id="E002",
    title="Shape the Power Waveform",
    question=(
        "Can a controller coordinate the phase of compute, collectives, "
        "checkpoint I/O, and independent colocated training jobs so that a "
        "large AI datacenter stops injecting dangerous periodic power into "
        "the grid, while preserving the optimizer's learning semantics and "
        "time to a held-out loss target?"
    ),
    hypothesis=(
        "A policy that changes only dependency-safe timing while jointly "
        "controlling microbatch launches, gradient-bucket collectives, "
        "checkpoint I/O, and the relative phase of independent jobs will "
        "satisfy all of the following on held-out workload, facility, and "
        "grid-mode combinations: reduce grid-danger-band spectral energy at "
        "the point of common coupling by at least 50% relative to the same "
        "unshaped workload replay over an equal useful-work horizon; increase "
        "time to the same held-out loss target by no more than 2% relative to "
        "unshaped execution; admit at least 10% more active accelerators under "
        "the identical point-of-common-coupling peak, ramp, modal-response, "
        "cooling, and protection limits than the best feasible one-dimensional "
        "software baseline; and preserve the exact-semantics invariant for "
        "every committed optimizer step."
    ),
    baselines=(
        "unshaped earliest-ready execution",
        "static phase offsets chosen once at admission",
        "per-job iteration-period detuning",
        "facility or accelerator power cap without phase coordination",
        "checkpoint staggering only",
        "rack-level buffering with storage loss and wear",
        "greedy valley filling from current facility power",
        "future-trace oracle joint schedule for regret only",
    ),
    metrics=(
        MetricSpec(
            "danger_band_spectral_energy_reduction_lower_95_bound",
            "1",
            "Lower 95% confidence bound on paired point-of-common-coupling "
            "danger-band spectral-energy reduction over equal useful work.",
            True,
        ),
        MetricSpec(
            "time_to_target_regression_upper_95_bound",
            "1",
            "Upper 95% confidence bound on paired time-to-held-out-loss-target "
            "regression relative to unshaped execution.",
            True,
        ),
        MetricSpec(
            "admission_capacity_improvement_lower_95_bound",
            "1",
            "Lower 95% confidence bound on active-accelerator capacity gain "
            "over the frozen best feasible one-dimensional baseline.",
            True,
        ),
        MetricSpec(
            "committed_optimizer_step_invariant_violations",
            "count",
            "Committed optimizer steps violating any exact-semantics invariant.",
            True,
        ),
        MetricSpec(
            "maximum_modeled_frequency_deviation",
            "Hz",
            "Maximum modeled frequency deviation over preregistered grid modes.",
            True,
        ),
        MetricSpec(
            "maximum_tie_line_oscillation",
            "W",
            "Maximum modeled tie-line oscillation under modal uncertainty.",
            True,
        ),
        MetricSpec(
            "operator_threshold_exposure_seconds",
            "s",
            "Time above the frozen grid-operator response threshold.",
            True,
        ),
        MetricSpec(
            "oracle_decision_regret",
            "1",
            "Decision regret relative to the future-trace oracle schedule.",
            True,
        ),
        MetricSpec(
            "held_out_pcc_waveform_nrmse",
            "1",
            "Normalized RMSE of the held-out point-of-common-coupling waveform.",
        ),
        MetricSpec(
            "nominal_90_interval_coverage",
            "1",
            "Empirical held-out coverage of nominal 90% waveform and outcome "
            "prediction intervals.",
        ),
        MetricSpec(
            "total_facility_energy_j",
            "J",
            "IT, power-conversion, storage, and cooling energy over the common "
            "accounting horizon.",
        ),
        MetricSpec(
            "cooling_energy_j",
            "J",
            "Cooling energy over the common accounting horizon.",
        ),
        MetricSpec(
            "storage_conversion_loss_j",
            "J",
            "Auxiliary-storage conversion loss charged to the intervention.",
        ),
        MetricSpec(
            "checkpoint_deadline_misses",
            "count",
            "Checkpoint writes that miss their frozen recovery deadlines.",
        ),
    ),
    falsifiers=(
        FalsifierSpec(
            "e002-spectral-energy",
            "danger_band_spectral_energy_reduction_lower_95_bound",
            ComparisonOperator.GE,
            0.50,
            description=(
                "The lower 95% bound must clear the preregistered 50% "
                "danger-band spectral-energy reduction."
            ),
        ),
        FalsifierSpec(
            "e002-time-to-target",
            "time_to_target_regression_upper_95_bound",
            ComparisonOperator.LE,
            0.02,
            description=(
                "The upper 95% bound must remain within the 2% time-to-target "
                "noninferiority margin."
            ),
        ),
        FalsifierSpec(
            "e002-admission-capacity",
            "admission_capacity_improvement_lower_95_bound",
            ComparisonOperator.GE,
            0.10,
            description=(
                "The lower 95% bound must clear the 10% admission-capacity "
                "improvement threshold."
            ),
        ),
        FalsifierSpec(
            "e002-exact-semantics",
            "committed_optimizer_step_invariant_violations",
            ComparisonOperator.LE,
            0.0,
            description="No committed optimizer step may violate exact semantics.",
        ),
        FalsifierSpec(
            "e002-waveform-admission",
            "held_out_pcc_waveform_nrmse",
            ComparisonOperator.LE,
            0.10,
            description=(
                "A virtual policy result is inadmissible above 10% held-out "
                "point-of-common-coupling waveform NRMSE."
            ),
        ),
        FalsifierSpec(
            "e002-interval-admission",
            "nominal_90_interval_coverage",
            ComparisonOperator.BETWEEN,
            0.85,
            upper_threshold=0.95,
            description=(
                "Nominal 90% intervals must cover between 85% and 95% of "
                "held-out samples."
            ),
        ),
    ),
    evidence_requirements=(
        EvidenceRequirementSpec(
            requirement_id="grid_safety_vector_by_mode",
            kind="grid_safety_vector",
            description=(
                "Grid response must be evaluated as the complete frequency, "
                "tie-line, and operator-threshold vector for every frozen grid "
                "mode and its modal-parameter uncertainty set."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=(
                "maximum_modeled_frequency_deviation",
                "maximum_tie_line_oscillation",
                "operator_threshold_exposure_seconds",
            ),
            required_panels=(
                "every preregistered grid mode",
                "modal-parameter uncertainty",
                "significant square-wave harmonics",
            ),
            acceptance_rule=(
                "Every component must remain within the frozen operator and "
                "protection limits in every named mode and uncertainty panel; "
                "no aggregate may hide a failed mode."
            ),
            evidence_boundary=(
                "Virtual resolution is model admission only; grid-response and "
                "admission-capacity claims require operator-approved live evidence."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="one_dimensional_baseline_vector_dominance",
            kind="baseline_vector_dominance",
            description=(
                "Joint phase control must not be matched by any single-lever "
                "baseline on the complete primary outcome vector."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "danger_band_spectral_energy_reduction_lower_95_bound",
                "time_to_target_regression_upper_95_bound",
                "admission_capacity_improvement_lower_95_bound",
                "committed_optimizer_step_invariant_violations",
                "maximum_modeled_frequency_deviation",
                "maximum_tie_line_oscillation",
                "operator_threshold_exposure_seconds",
                "oracle_decision_regret",
            ),
            comparison_baselines=(
                "static phase offsets chosen once at admission",
                "per-job iteration-period detuning",
                "facility or accelerator power cap without phase coordination",
                "checkpoint staggering only",
                "rack-level buffering with storage loss and wear",
                "greedy valley filling from current facility power",
            ),
            acceptance_rule=(
                "No one-dimensional baseline may match joint control within "
                "experimental uncertainty on all primary outcomes."
            ),
            evidence_boundary=(
                "Requires matched controlled interventions; a virtual ranking "
                "cannot establish joint-control dominance."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="cross_band_no_displacement",
            kind="spectral_non_displacement",
            description=(
                "A reduction in the preregistered danger band must not displace "
                "energy into another dangerous grid mode or harmonic."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=(
                "danger_band_spectral_energy_reduction_lower_95_bound",
            ),
            required_panels=(
                "preregistered danger bands",
                "adjacent modes",
                "significant harmonics",
            ),
            acceptance_rule=(
                "The full paired spectrum must show no compensating increase in "
                "any other frozen dangerous band or significant harmonic."
            ),
            evidence_boundary=(
                "Only bands frozen before evaluation count; an omitted frequency "
                "region cannot be treated as evidence of non-displacement."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="full_boundary_nonreversal",
            kind="accounting_nonreversal",
            description=(
                "Cooling, storage, recovery risk, and total facility accounting "
                "must not reverse the apparent waveform benefit."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "time_to_target_regression_upper_95_bound",
                "total_facility_energy_j",
                "cooling_energy_j",
                "storage_conversion_loss_j",
                "checkpoint_deadline_misses",
            ),
            required_panels=(
                "IT execution",
                "power conversion and storage",
                "cooling",
                "checkpoint recovery risk",
            ),
            acceptance_rule=(
                "The claimed benefit must retain its direction after every "
                "boundary component and deferred or recovery consequence is charged."
            ),
            evidence_boundary=(
                "Requires complete metered facility and recovery accounting over "
                "the common useful-work horizon."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="equal_useful_work_accounting",
            kind="paired_accounting_identity",
            description=(
                "Policy and baseline spectra, time, and energy must be compared "
                "over equal completed useful work with failed runs retained."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=(
                "danger_band_spectral_energy_reduction_lower_95_bound",
                "time_to_target_regression_upper_95_bound",
                "committed_optimizer_step_invariant_violations",
                "total_facility_energy_j",
            ),
            required_panels=(
                "completed optimizer steps",
                "held-out loss target",
                "failed or invariant-violating runs",
            ),
            acceptance_rule=(
                "Each paired comparison must share the same useful-work endpoint "
                "and include failed or invariant-violating runs rather than "
                "truncating the accounting window."
            ),
            evidence_boundary=(
                "A fixed wall-clock slice with unequal completed work cannot "
                "satisfy this requirement."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="withheld_facility_directional_transfer",
            kind="directional_telemetry_transfer",
            description=(
                "The waveform and grid-response effect must retain direction on "
                "real traces from a withheld facility regime."
            ),
            earliest_resolvable_stage=ExperimentStage.SHADOW,
            required_metrics=(
                "danger_band_spectral_energy_reduction_lower_95_bound",
                "maximum_modeled_frequency_deviation",
                "maximum_tie_line_oscillation",
                "operator_threshold_exposure_seconds",
                "held_out_pcc_waveform_nrmse",
                "nominal_90_interval_coverage",
            ),
            required_panels=(
                "withheld facility",
                "withheld workload",
                "withheld grid operating regime",
            ),
            acceptance_rule=(
                "The signed policy effect and safety-vector ordering must agree "
                "with timestamp-aligned withheld facility telemetry."
            ),
            evidence_boundary=(
                "Shadow evidence can establish directional transfer, not the "
                "multi-megawatt admission-capacity claim."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="decision_regret_reported_or_thresholded",
            kind="decision_quality_completeness",
            description=(
                "Oracle decision regret must be reported for every evaluation "
                "cell, with any pass threshold frozen before evaluation."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=(
                "oracle_decision_regret",
                "held_out_pcc_waveform_nrmse",
                "nominal_90_interval_coverage",
            ),
            required_panels=(
                "every held-out evaluation cell",
                "future-trace oracle action set",
            ),
            acceptance_rule=(
                "Regret and its uncertainty must be reported without selective "
                "cell omission; if regret is used as a pass/fail gate, its "
                "criterion must be preregistered before outcomes are opened."
            ),
            evidence_boundary=(
                "This requirement creates no post hoc scalar regret threshold."
            ),
        ),
    ),
    independent_variables=(
        "phase-control policy",
        "training graph family and measured duty cycle",
        "iteration period",
        "concurrent job count and relative phase",
        "sequence-length distribution",
        "checkpoint cadence",
        "accelerator population and power-profile family",
        "rack power-domain arrangement and caps",
        "rack-buffer capacity and condition",
        "cooling headroom and fault state",
        "execution timing jitter",
        "grid modal frequency, damping, drift, and harmonics",
        "facility power and curtailment envelope",
    ),
    held_out_dimensions=(
        "model or workload family",
        "accelerator power-profile family",
        "collective topology class",
        "facility scale",
        "rack-cap arrangement",
        "grid-mode and damping combination",
        "cooling or buffer stress regime",
        "combination of colocated job phases",
    ),
    real_validation_requirements=(
        "high-rate operation-level power and exact-semantics measurements on 8 to 64 GPUs",
        "paired shaping experiments on 256 to 1,024 GPUs across multiple racks and jobs",
        "shadow prediction at a facility with at least 10,000 active accelerators and timestamped point-of-common-coupling telemetry",
        "operator-approved multi-megawatt A/B intervention outside protection thresholds",
        "repeat at 10,000-plus accelerators in a held-out facility, workload, and grid regime",
    ),
    seed_policy=(
        "Pair each policy and baseline on the same workload graph, sample "
        "order, random seed, exogenous trace, initial thermal state, and grid "
        "snapshot; choose evaluation counts from calibration-only variance "
        "for 90% power at two-sided 5% error with at least 10 independent "
        "workload traces per cell; hash and freeze evaluation traces, seeds, "
        "jobs, and mode snapshots before policy tuning."
    ),
    source_window="2026-04-13/2026-07-12",
    notes=(
        "Status is preregistered design; no experiment result exists.",
        "The public 0.1-second H100 profiles dated 2026-04-08 are an explicitly out-of-window calibration anchor, not millisecond-ramp evidence.",
        "The 50%, 2%, and 10% claims are evaluated with the preregistered confidence-bound statistics, not point estimates.",
        "Bounded-staleness runs are exploratory and cannot support this exact-semantics hypothesis.",
        "Every qualitative, vector-level, accounting, and transfer falsifier is encoded as a mandatory structured evidence requirement; unresolved requirements keep a run inconclusive.",
        "Virtual screening cannot establish the admission-capacity or grid-response claims.",
    ),
)


E003_PROTOCOL = ExperimentProtocol(
    experiment_id="E003",
    title="Semantic Fault Tolerance",
    question=(
        "Can one training system treat fail-stop devices, fail-slow devices, "
        "and silent data corruption according to their counterfactual effect "
        "on the learning trajectory, then spend redundancy and recovery work "
        "only where the predicted semantic harm justifies it?"
    ),
    hypothesis=(
        "On held-out model, topology, training-phase, hardware, and mixed-fault "
        "regimes, a trajectory-sensitivity policy using adaptive canaries and "
        "selective redundancy will satisfy all of the following: the defended "
        "run's primary held-out quality vector is equivalent to its paired "
        "clean-run distribution, with every preregistered metric's 90% "
        "confidence interval inside plus or minus 0.2 clean-run standard "
        "deviations and at least 95% of defended runs inside the corresponding "
        "per-run equivalence region; it intercepts at least 99% of trajectory-"
        "critical injected events before a contaminated optimizer update is "
        "committed while falsely isolating or replaying no more than 1% of "
        "clean optimizer steps; its always-on time-to-target and facility-"
        "energy tax is no more than 2% in clean runs and its total tax remains "
        "no more than 2% at a separately measured production fault incidence; "
        "and it uses at least 50% fewer redundant training FLOPs than uniform "
        "duplicate execution while satisfying the quality and interception "
        "predictions."
    ),
    baselines=(
        "hardware-reported errors only",
        "NaN, infinity, and loss-spike checks",
        "fixed-interval checkpoint and restart",
        "ResiHP-like workload-aware fail-stop and fail-slow reconfiguration",
        "ReCoVer-like stochastic-equivalent fail-stop forward recovery",
        "fixed canaries on the same layers every step",
        "uniform duplicate execution before commit",
        "rule-based union of numerical, timing, and forward-recovery defenses",
        "fault-and-counterfactual oracle for regret and budget bounds only",
    ),
    metrics=(
        MetricSpec(
            "maximum_primary_quality_90ci_excursion_sd",
            "clean_run_standard_deviation",
            "Maximum absolute endpoint of any primary metric's paired 90% "
            "confidence interval, normalized by its frozen clean-run standard "
            "deviation or preregistered near-zero-variance floor.",
            True,
        ),
        MetricSpec(
            "defended_run_equivalence_fraction",
            "1",
            "Fraction of defended runs finishing inside every corresponding "
            "per-run primary-quality equivalence region.",
            True,
        ),
        MetricSpec(
            "critical_event_interception_lower_95_bound",
            "1",
            "Lower 95% confidence bound on oracle-labeled trajectory-critical "
            "events intercepted before contaminated optimizer commit.",
            True,
        ),
        MetricSpec(
            "clean_step_false_action_upper_95_bound",
            "1",
            "Upper 95% confidence bound on clean optimizer steps falsely "
            "isolated, replayed, or otherwise acted upon.",
            True,
        ),
        MetricSpec(
            "clean_time_to_target_tax_upper_95_bound",
            "1",
            "Upper paired 95% bound on always-on clean-run time-to-target tax.",
            True,
        ),
        MetricSpec(
            "clean_facility_energy_tax_upper_95_bound",
            "1",
            "Upper paired 95% bound on always-on clean-run facility-energy tax.",
            True,
        ),
        MetricSpec(
            "production_incidence_time_tax_upper_95_bound",
            "1",
            "Upper paired 95% bound on time-to-target tax at a separately "
            "measured production fault incidence.",
            True,
        ),
        MetricSpec(
            "production_incidence_energy_tax_upper_95_bound",
            "1",
            "Upper paired 95% bound on facility-energy tax at a separately "
            "measured production fault incidence.",
            True,
        ),
        MetricSpec(
            "redundant_flops_fraction_of_uniform_duplicate_upper_95_bound",
            "1",
            "Upper paired 95% bound on redundant training FLOPs relative to "
            "uniform duplicate execution at the same protection level.",
            True,
        ),
        MetricSpec(
            "redundant_flops_per_intercepted_critical_event",
            "FLOP/event",
            "Redundant computation spent per intercepted critical event.",
            True,
        ),
        MetricSpec(
            "protection_fraction_spent_on_oracle_benign_events",
            "1",
            "Fraction of the defense budget spent on oracle-benign events.",
            True,
        ),
        MetricSpec(
            "contaminated_committed_updates",
            "count",
            "Optimizer updates committed with a contaminated contribution.",
        ),
        MetricSpec(
            "semantic_harm_interval_coverage",
            "1",
            "Held-out empirical coverage of predicted semantic-harm intervals.",
            True,
        ),
        MetricSpec(
            "oracle_protection_budget_regret",
            "1",
            "Regret relative to oracle allocation of the same protection budget.",
            True,
        ),
    ),
    falsifiers=(
        FalsifierSpec(
            "e003-quality-vector-equivalence",
            "maximum_primary_quality_90ci_excursion_sd",
            ComparisonOperator.LE,
            0.20,
            description=(
                "The worst normalized endpoint across the complete primary "
                "quality vector must remain inside plus or minus 0.2 clean-run "
                "standard deviations."
            ),
        ),
        FalsifierSpec(
            "e003-run-equivalence",
            "defended_run_equivalence_fraction",
            ComparisonOperator.GE,
            0.95,
            description=(
                "At least 95% of defended runs must finish inside the "
                "corresponding per-run equivalence region."
            ),
        ),
        FalsifierSpec(
            "e003-critical-interception",
            "critical_event_interception_lower_95_bound",
            ComparisonOperator.GE,
            0.99,
            description=(
                "The lower 95% confidence bound on critical-event interception "
                "must be at least 99%."
            ),
        ),
        FalsifierSpec(
            "e003-clean-false-action",
            "clean_step_false_action_upper_95_bound",
            ComparisonOperator.LE,
            0.01,
            description=(
                "The upper 95% confidence bound on clean-step false action must "
                "be no more than 1%."
            ),
        ),
        FalsifierSpec(
            "e003-clean-time-tax",
            "clean_time_to_target_tax_upper_95_bound",
            ComparisonOperator.LE,
            0.02,
            description="Clean-run time-to-target tax must be no more than 2%.",
        ),
        FalsifierSpec(
            "e003-clean-energy-tax",
            "clean_facility_energy_tax_upper_95_bound",
            ComparisonOperator.LE,
            0.02,
            description="Clean-run facility-energy tax must be no more than 2%.",
        ),
        FalsifierSpec(
            "e003-production-time-tax",
            "production_incidence_time_tax_upper_95_bound",
            ComparisonOperator.LE,
            0.02,
            description=(
                "Time-to-target tax at separately measured production fault "
                "incidence must be no more than 2%."
            ),
        ),
        FalsifierSpec(
            "e003-production-energy-tax",
            "production_incidence_energy_tax_upper_95_bound",
            ComparisonOperator.LE,
            0.02,
            description=(
                "Facility-energy tax at separately measured production fault "
                "incidence must be no more than 2%."
            ),
        ),
        FalsifierSpec(
            "e003-redundant-flops",
            "redundant_flops_fraction_of_uniform_duplicate_upper_95_bound",
            ComparisonOperator.LE,
            0.50,
            description=(
                "Redundant training FLOPs must be at most half of uniform "
                "duplicate execution at the same protection level."
            ),
        ),
    ),
    evidence_requirements=(
        EvidenceRequirementSpec(
            requirement_id="complete_quality_vector_equivalence",
            kind="vector_equivalence",
            description=(
                "Trajectory and final-quality equivalence must be resolved on "
                "the complete frozen primary quality vector, not a favorable "
                "loss scalar or geometric summary."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "maximum_primary_quality_90ci_excursion_sd",
                "defended_run_equivalence_fraction",
            ),
            required_panels=(
                "every frozen primary quality metric",
                "paired clean-run distribution",
                "near-zero-variance floor handling",
            ),
            acceptance_rule=(
                "Every component must pass its frozen equivalence region after "
                "family-wise correction, and the complete vector and per-run "
                "equivalence decisions must be reported."
            ),
            evidence_boundary=(
                "Requires paired controlled learning trajectories; a simulator "
                "or endpoint loss alone cannot resolve semantic equivalence."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="baseline_vector_dominance",
            kind="baseline_vector_dominance",
            description=(
                "The joint semantic defense must not be matched by any "
                "preregistered baseline across the complete primary outcome vector."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "maximum_primary_quality_90ci_excursion_sd",
                "defended_run_equivalence_fraction",
                "critical_event_interception_lower_95_bound",
                "clean_step_false_action_upper_95_bound",
                "clean_time_to_target_tax_upper_95_bound",
                "clean_facility_energy_tax_upper_95_bound",
                "production_incidence_time_tax_upper_95_bound",
                "production_incidence_energy_tax_upper_95_bound",
                "redundant_flops_fraction_of_uniform_duplicate_upper_95_bound",
                "redundant_flops_per_intercepted_critical_event",
                "protection_fraction_spent_on_oracle_benign_events",
                "semantic_harm_interval_coverage",
                "oracle_protection_budget_regret",
            ),
            comparison_baselines=(
                "hardware-reported errors only",
                "NaN, infinity, and loss-spike checks",
                "fixed-interval checkpoint and restart",
                "ResiHP-like workload-aware fail-stop and fail-slow reconfiguration",
                "ReCoVer-like stochastic-equivalent fail-stop forward recovery",
                "fixed canaries on the same layers every step",
                "uniform duplicate execution before commit",
                "rule-based union of numerical, timing, and forward-recovery defenses",
            ),
            acceptance_rule=(
                "No baseline may match the joint policy within uncertainty on "
                "all primary outcomes under the same protection and compute budget."
            ),
            evidence_boundary=(
                "Requires matched controlled branches with identical fault "
                "manifestations and complete facility accounting."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="structured_fault_transfer",
            kind="heldout_fault_transfer",
            description=(
                "The defense effect must survive structured, held-out fault "
                "manifestations rather than existing only for independent random "
                "bit flips."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "maximum_primary_quality_90ci_excursion_sd",
                "critical_event_interception_lower_95_bound",
                "clean_step_false_action_upper_95_bound",
            ),
            required_panels=(
                "structured silent corruption",
                "fail-stop",
                "fail-slow",
                "mixed-fault ordering and bursts",
                "held-out hardware-unit manifestation",
            ),
            acceptance_rule=(
                "The signed protection effect and all applicable scalar gates "
                "must survive every frozen structured and mixed-fault panel."
            ),
            evidence_boundary=(
                "Independent random injection is calibration evidence only and "
                "cannot resolve structured-fault transfer."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="harmful_intervention_ranking_transfer",
            kind="decision_ranking_transfer",
            description=(
                "Predicted semantic harm must rank harmful interventions on "
                "held-out hardware, operations, and training phases, with "
                "calibrated intervals and oracle-budget regret reported."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "semantic_harm_interval_coverage",
                "oracle_protection_budget_regret",
                "redundant_flops_per_intercepted_critical_event",
                "protection_fraction_spent_on_oracle_benign_events",
            ),
            required_panels=(
                "held-out hardware",
                "held-out CUDA operation and data type",
                "held-out training phase",
            ),
            acceptance_rule=(
                "The frozen ranking procedure must preserve the harmful-versus-"
                "benign ordering used for protection decisions on every named "
                "held-out panel, with all errors and regret exposed."
            ),
            evidence_boundary=(
                "No post hoc correlation or regret threshold is introduced; "
                "the ranking procedure and adjudication rule must be frozen first."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="long_horizon_optimizer_and_capability_safety",
            kind="long_horizon_semantic_safety",
            description=(
                "Selective replay must not move damage into optimizer state or "
                "long-horizon capability outcomes outside the immediate detector window."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "maximum_primary_quality_90ci_excursion_sd",
                "defended_run_equivalence_fraction",
                "contaminated_committed_updates",
                "clean_time_to_target_tax_upper_95_bound",
                "clean_facility_energy_tax_upper_95_bound",
            ),
            required_panels=(
                "optimizer state",
                "final held-out quality vector",
                "time to capability target",
            ),
            acceptance_rule=(
                "The complete post-intervention trajectory must retain quality "
                "equivalence with no hidden committed contamination or delayed "
                "capability damage."
            ),
            evidence_boundary=(
                "Short-horizon kernel agreement or uncommitted replay traces do "
                "not resolve long-horizon learning safety."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="production_incidence_is_measured",
            kind="incidence_evidence",
            description=(
                "Production-rate overhead claims require an independently "
                "measured production fault incidence."
            ),
            earliest_resolvable_stage=ExperimentStage.SHADOW,
            required_metrics=(
                "production_incidence_time_tax_upper_95_bound",
                "production_incidence_energy_tax_upper_95_bound",
            ),
            required_panels=(
                "fleet observation duration",
                "fault-family incidence",
                "out-of-distribution behavior",
            ),
            acceptance_rule=(
                "The incidence used for overhead weighting must come from a "
                "sufficiently long, preregistered fleet observation and remain "
                "separate by fault family."
            ),
            evidence_boundary=(
                "Accelerated injection and literature manifestation frequencies "
                "are not production arrival-rate evidence."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="real_system_directional_transfer",
            kind="controlled_directional_transfer",
            description=(
                "The virtual or small-scale defense effect must transfer "
                "directionally to a real controlled training system."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "maximum_primary_quality_90ci_excursion_sd",
                "critical_event_interception_lower_95_bound",
                "clean_step_false_action_upper_95_bound",
                "redundant_flops_fraction_of_uniform_duplicate_upper_95_bound",
            ),
            required_panels=(
                "32 to 64 GPU end-to-end training",
                "256 to 512 GPU parallelism-stack comparison",
                "held-out structured and mixed faults",
            ),
            acceptance_rule=(
                "The signed effect and mechanism ordering must agree with the "
                "preregistered controlled real-system interventions."
            ),
            evidence_boundary=(
                "Only the final 10,000-plus-accelerator stage can support the "
                "frontier-training equivalence claim."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="fault_family_power_and_completeness",
            kind="statistical_power_and_panel_completeness",
            description=(
                "Every reported fault family must meet the frozen independent-"
                "event design or be labeled underpowered without post hoc pooling."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=(
                "critical_event_interception_lower_95_bound",
                "clean_step_false_action_upper_95_bound",
                "semantic_harm_interval_coverage",
            ),
            required_panels=(
                "every frozen fault family",
                "at least 100 independent root injection events per reported family",
                "calibration-only power calculation",
            ),
            acceptance_rule=(
                "Counts and confidence procedures must be frozen from calibration; "
                "each family either meets its required independent-root count or "
                "is reported as underpowered and remains inconclusive."
            ),
            evidence_boundary=(
                "Corrupted tensor elements from one root fault are one event and "
                "different fault processes may not be pooled to manufacture power."
            ),
        ),
    ),
    independent_variables=(
        "fault-defense policy",
        "model family and optimizer",
        "training objective and phase",
        "operation and tensor role",
        "numerical format",
        "parallelism topology",
        "accelerator scale",
        "structured silent-corruption manifestation",
        "fail-stop location and timing",
        "compute and communication fail-slow severity",
        "fault persistence and intermittency",
        "mixed-fault ordering and burst structure",
        "measured fault incidence or explicitly rate-free sensitivity regime",
        "canary and redundant-execution budget",
    ),
    held_out_dimensions=(
        "model family and training phase combination",
        "accelerator generation or hardware-unit manifestation family",
        "CUDA operation and data type",
        "parallelism topology and collective pattern",
        "persistent versus transient corruption structure",
        "fail-slow severity and workload-variability regime",
        "mixed-fault ordering and burst structure",
        "facility scale and checkpoint policy",
    ),
    real_validation_requirements=(
        "exact paired kernel and tiny-model counterfactual branches on 1 to 8 GPUs",
        "repeated end-to-end training on 32 to 64 GPUs with held-out structured and mixed faults",
        "comparisons on 256 to 512 GPUs across two parallelism stacks",
        "shadow canaries on a 1,000-plus accelerator fleet long enough to measure false actions, out-of-distribution behavior, and production incidence",
        "controlled 30B to 100B-plus runs on 10,000-plus accelerators with independent held-out evaluation and full facility accounting",
    ),
    seed_policy=(
        "Pair clean, undefended-faulted, and defended branches on the same "
        "checkpoint, sample order, random state, topology, exogenous trace, "
        "and replayed fault manifestation; keep clean seeds, fault seeds, "
        "checkpoints, and evaluation tasks disjoint and content-addressed; "
        "choose counts from calibration-only prevalence and variance for 90% "
        "power at 5% error, with at least 100 independent root injection events "
        "per reported fault family."
    ),
    source_window="2026-04-13/2026-07-12",
    notes=(
        "Status is preregistered design; no experiment result exists.",
        "The quality-vector scalar is a lossless maximum over every preregistered metric's absolute 90% confidence-interval endpoint, with calibration-frozen handling for near-zero variance.",
        "Production-incidence overhead gates are unevaluable until incidence is measured from a sufficiently long fleet observation; accelerated injection is not production-rate evidence.",
        "Structured SDC patterns are conditional manifestation anchors, not a fabricated production arrival rate.",
        "Every vector-equivalence, baseline, structured-fault, long-horizon, incidence, and transfer falsifier is encoded as a mandatory structured evidence requirement; unresolved requirements keep a run inconclusive.",
        "Only the final 10,000-plus-accelerator validation stage can support the frontier-training semantic-equivalence claim.",
    ),
)


E004_PROTOCOL = ExperimentProtocol(
    experiment_id="E004",
    title="Fluid Inference Topology",
    question=(
        "Should an inference fleet choose, per request and over the life of a "
        "request, whether model execution is aggregated or disaggregated, "
        "where prefill runs, where decode runs, where attention and experts "
        "live, which KV state moves, and which precision or speculative path "
        "is used? The stronger question is whether these choices have positive "
        "interaction effects. If they do, a controller that reasons about them "
        "jointly should beat both a fixed topology and a collection of "
        "independently tuned controllers that have access to the same actions."
    ),
    hypothesis=(
        "The joint controller will improve quality- and SLO-constrained service "
        "value per full-facility joule U by at least 20% over the best static "
        "topology selected on the development split and by at least 10% over "
        "an independent-controller ensemble with identical action access and "
        "compute budget. For topology A, state management B, and scheduling C, "
        "the three-way interaction I_ABC = u(ABC) - u(AB) - u(AC) - u(BC) + "
        "u(A) + u(B) + u(C) - u(empty) will be at least 0.05, with its cluster-"
        "bootstrap 95% interval excluding zero. In at least three of four held-"
        "out workload families, aggregated and disaggregated execution will "
        "each account for at least 10% of request-time in at least half of "
        "evaluation traces. Relative to the best static baseline, aggregate "
        "utility will fall by no more than 1% and SLO attainment by no more "
        "than one percentage point in every preregistered workload family."
    ),
    baselines=(
        "best static aggregated topology",
        "best static prefill/decode-disaggregated topology",
        "mechanism-matched HMA-Serve-style topology",
        "mechanism-matched Kairos-style prefill deflection",
        "mechanism-matched KernelFlume-style elastic attention",
        "independent topology, state, precision, and scheduling controllers",
        "myopic one-step optimizer over the full action space",
        "future-arrival-and-failure oracle for regret only",
    ),
    metrics=(
        MetricSpec(
            "joint_vs_static_u_improvement",
            "1",
            "Joint-controller improvement in quality- and SLO-constrained "
            "service value per full-facility joule over the frozen best static "
            "topology.",
            True,
        ),
        MetricSpec(
            "joint_vs_independent_u_improvement",
            "1",
            "Joint-controller U improvement over the equal-access, equal-budget "
            "independent-controller ensemble.",
            True,
        ),
        MetricSpec(
            "three_way_interaction_point_estimate",
            "1",
            "I_ABC = u(ABC)-u(AB)-u(AC)-u(BC)+u(A)+u(B)+u(C)-u(empty).",
            True,
        ),
        MetricSpec(
            "three_way_interaction_lower_95_bound",
            "1",
            "Lower endpoint of the cluster-bootstrap 95% interval for I_ABC.",
            True,
        ),
        MetricSpec(
            "regime_crossing_workload_family_count",
            "family_count",
            "Held-out workload families in which both aggregated and "
            "disaggregated execution each occupy at least 10% of request-time "
            "in at least half of evaluation traces.",
            True,
        ),
        MetricSpec(
            "static_regime_dominated_workload_family_count",
            "family_count",
            "Held-out workload families in which one frozen static regime "
            "accounts for at least 90% of request-time.",
            True,
        ),
        MetricSpec(
            "worst_workload_utility_regression",
            "1",
            "Maximum aggregate-utility regression across preregistered workload "
            "families relative to the best static baseline.",
            True,
        ),
        MetricSpec(
            "worst_workload_slo_decline_percentage_points",
            "percentage_point",
            "Maximum SLO-attainment decline across preregistered workload "
            "families relative to the best static baseline.",
            True,
        ),
        MetricSpec(
            "intervention_regret_fraction_of_oracle_value",
            "1",
            "Intervention decision regret as a fraction of oracle service value.",
            True,
        ),
        MetricSpec(
            "nominal_50_interval_coverage",
            "1",
            "Empirical held-out outcome coverage of nominal 50% intervals.",
            True,
        ),
        MetricSpec(
            "nominal_90_interval_coverage",
            "1",
            "Empirical held-out outcome coverage of nominal 90% intervals.",
            True,
        ),
        MetricSpec(
            "nominal_95_interval_coverage",
            "1",
            "Empirical held-out outcome coverage of nominal 95% intervals.",
            True,
        ),
        MetricSpec(
            "configuration_ranking_correlation",
            "1",
            "Held-out correlation between predicted and observed configuration rankings.",
            True,
        ),
        MetricSpec(
            "p50_ttft_seconds",
            "s",
            "P50 time to first token, reported by workload family.",
            True,
        ),
        MetricSpec(
            "p99_ttft_seconds",
            "s",
            "P99 time to first token, reported by workload family.",
            True,
        ),
        MetricSpec(
            "p50_tpot_seconds_per_token",
            "s/token",
            "P50 time per output token, reported by workload family.",
            True,
        ),
        MetricSpec(
            "p99_tpot_seconds_per_token",
            "s/token",
            "P99 time per output token, reported by workload family.",
            True,
        ),
        MetricSpec(
            "p50_session_completion_latency_seconds",
            "s",
            "P50 session completion latency, reported by workload family.",
            True,
        ),
        MetricSpec(
            "p99_session_completion_latency_seconds",
            "s",
            "P99 session completion latency, reported by workload family.",
            True,
        ),
        MetricSpec(
            "state_movement_bytes",
            "byte",
            "KV, weight, expert, and draft-state movement charged to control.",
        ),
        MetricSpec(
            "facility_energy_j",
            "J",
            "Accelerator, host, network, storage, and cooling energy.",
        ),
    ),
    falsifiers=(
        FalsifierSpec(
            "e004-static-gain",
            "joint_vs_static_u_improvement",
            ComparisonOperator.GE,
            0.20,
            description="Joint control must improve U by at least 20% over static.",
        ),
        FalsifierSpec(
            "e004-independent-gain",
            "joint_vs_independent_u_improvement",
            ComparisonOperator.GE,
            0.10,
            description=(
                "Joint control must improve U by at least 10% over independently "
                "tuned controllers with identical action access and compute budget."
            ),
        ),
        FalsifierSpec(
            "e004-interaction-size",
            "three_way_interaction_point_estimate",
            ComparisonOperator.GE,
            0.05,
            description="The preregistered three-way interaction must be at least 0.05.",
        ),
        FalsifierSpec(
            "e004-interaction-sign",
            "three_way_interaction_lower_95_bound",
            ComparisonOperator.GT,
            0.0,
            description=(
                "The cluster-bootstrap 95% interval must exclude zero on the "
                "positive side."
            ),
        ),
        FalsifierSpec(
            "e004-regime-crossing",
            "regime_crossing_workload_family_count",
            ComparisonOperator.GE,
            3.0,
            description=(
                "At least three of four held-out workload families must satisfy "
                "the complete repeated-regime-crossing statistic."
            ),
        ),
        FalsifierSpec(
            "e004-static-dominance",
            "static_regime_dominated_workload_family_count",
            ComparisonOperator.LE,
            1.0,
            description=(
                "A frozen static regime may not account for at least 90% of "
                "request-time in two or more held-out workload families."
            ),
        ),
        FalsifierSpec(
            "e004-utility-noninferiority",
            "worst_workload_utility_regression",
            ComparisonOperator.LE,
            0.01,
            description="No workload family may lose more than 1% utility.",
        ),
        FalsifierSpec(
            "e004-slo-noninferiority",
            "worst_workload_slo_decline_percentage_points",
            ComparisonOperator.LE,
            1.0,
            description=(
                "No workload family may lose more than one percentage point of "
                "SLO attainment."
            ),
        ),
        FalsifierSpec(
            "e004-decision-regret",
            "intervention_regret_fraction_of_oracle_value",
            ComparisonOperator.LE,
            0.10,
            description="Intervention regret must not exceed 10% of oracle value.",
        ),
        FalsifierSpec(
            "e004-interval-coverage",
            "nominal_90_interval_coverage",
            ComparisonOperator.GE,
            0.80,
            description=(
                "Nominal 90% intervals must cover at least 80% of held-out outcomes."
            ),
        ),
    ),
    evidence_requirements=(
        EvidenceRequirementSpec(
            requirement_id="equal_accounting_baseline_dominance",
            kind="baseline_vector_dominance",
            description=(
                "Joint control must retain its advantage when every baseline "
                "receives identical state-movement, policy-compute, warm-cache, "
                "service-value, and facility-energy accounting."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "joint_vs_static_u_improvement",
                "joint_vs_independent_u_improvement",
                "worst_workload_utility_regression",
                "worst_workload_slo_decline_percentage_points",
                "state_movement_bytes",
                "facility_energy_j",
            ),
            comparison_baselines=(
                "best static aggregated topology",
                "best static prefill/decode-disaggregated topology",
                "mechanism-matched HMA-Serve-style topology",
                "mechanism-matched Kairos-style prefill deflection",
                "mechanism-matched KernelFlume-style elastic attention",
                "independent topology, state, precision, and scheduling controllers",
                "myopic one-step optimizer over the full action space",
            ),
            acceptance_rule=(
                "No baseline may match the joint controller across the complete "
                "primary vector after all policies are charged at the same boundary."
            ),
            evidence_boundary=(
                "Requires controlled matched interventions; unequal cache state, "
                "action access, or energy boundaries invalidate the comparison."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="ranking_transfer_by_named_panel",
            kind="ranking_transfer",
            description=(
                "Configuration rankings and intervention decisions must transfer "
                "across every named held-out hardware, model, workload, fabric, "
                "and compound-stress panel."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=(
                "configuration_ranking_correlation",
                "intervention_regret_fraction_of_oracle_value",
            ),
            required_panels=(
                "hardware family",
                "model family",
                "workload family",
                "fabric-topology class",
                "compound hardware-workload-congestion-power combination",
            ),
            acceptance_rule=(
                "The frozen ranking adjudication must survive every named panel, "
                "with ties, abstentions, errors, and oracle regret reported."
            ),
            evidence_boundary=(
                "No post hoc correlation threshold is introduced; any pass rule "
                "beyond the registered regret gate must be frozen before evaluation."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="controlled_cluster_directional_transfer",
            kind="controlled_directional_transfer",
            description=(
                "Simulated topology choices and mechanism orderings must transfer "
                "directionally to controlled real-cluster interventions."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "joint_vs_static_u_improvement",
                "joint_vs_independent_u_improvement",
                "three_way_interaction_point_estimate",
                "three_way_interaction_lower_95_bound",
            ),
            required_panels=(
                "64 to 256 accelerator topology transitions",
                "network perturbation",
                "rack-power perturbation",
            ),
            acceptance_rule=(
                "The signed intervention effects and mechanism ranking must agree "
                "between the virtual prediction and preregistered controlled cluster."
            ),
            evidence_boundary=(
                "Only guarded live stages can support serving-value claims; "
                "controlled transfer does not establish datacenter-scale value."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="causal_exclusion",
            kind="causal_exclusion",
            description=(
                "The measured benefit must not be explained entirely by extra "
                "replicas, looser admission, or hidden quality degradation."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "joint_vs_static_u_improvement",
                "joint_vs_independent_u_improvement",
                "worst_workload_utility_regression",
                "worst_workload_slo_decline_percentage_points",
            ),
            required_panels=(
                "replica-count-matched intervention",
                "admission-matched intervention",
                "quality-matched intervention",
            ),
            acceptance_rule=(
                "The joint-control effect must retain its direction under each "
                "frozen causal exclusion panel."
            ),
            evidence_boundary=(
                "Requires controlled counterfactuals with one exclusion changed "
                "at a time and the full request population retained."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="workload_family_vector_nondegradation",
            kind="service_vector_nondegradation",
            description=(
                "P50 and P99 TTFT, TPOT, session completion, SLO attainment, and "
                "utility must be reported and adjudicated by workload family."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "worst_workload_utility_regression",
                "worst_workload_slo_decline_percentage_points",
                "p50_ttft_seconds",
                "p99_ttft_seconds",
                "p50_tpot_seconds_per_token",
                "p99_tpot_seconds_per_token",
                "p50_session_completion_latency_seconds",
                "p99_session_completion_latency_seconds",
            ),
            required_panels=(
                "conversational",
                "retrieval-heavy",
                "long-context reasoning",
                "coding-agent",
            ),
            acceptance_rule=(
                "Every workload family must satisfy the registered utility and "
                "SLO gates, and no latency component may be omitted or hidden in "
                "an aggregate average."
            ),
            evidence_boundary=(
                "Token throughput or an all-workload mean cannot resolve the "
                "family-level service vector."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="factorial_action_access_equivalence",
            kind="factorial_design_integrity",
            description=(
                "Factorial and independent-controller comparisons must receive "
                "identical observations, actions, hardware, safety constraints, "
                "and policy-compute budgets."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=(
                "joint_vs_independent_u_improvement",
                "three_way_interaction_point_estimate",
                "three_way_interaction_lower_95_bound",
            ),
            required_panels=(
                "topology action family",
                "state-management action family",
                "scheduling action family",
                "all pairwise combinations",
                "complete three-way combination",
            ),
            comparison_baselines=(
                "independent topology, state, precision, and scheduling controllers",
                "myopic one-step optimizer over the full action space",
            ),
            acceptance_rule=(
                "Every factorial cell and comparison policy must share the frozen "
                "action-access and accounting contract before interaction or joint "
                "gain is admissible."
            ),
            evidence_boundary=(
                "An ablation that removes information, actions, or compute from a "
                "baseline cannot identify a coupling effect."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="interval_family_completeness",
            kind="uncertainty_family_completeness",
            description=(
                "Held-out coverage must be reported for the complete registered "
                "50%, 90%, and 95% prediction-interval family."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=(
                "nominal_50_interval_coverage",
                "nominal_90_interval_coverage",
                "nominal_95_interval_coverage",
            ),
            required_panels=(
                "50% prediction intervals",
                "90% prediction intervals",
                "95% prediction intervals",
                "every held-out outcome family",
            ),
            acceptance_rule=(
                "All registered interval levels and outcome families must be "
                "reported from the same frozen evaluation cells; the 90% scalar "
                "gate must pass and the other levels may not be selectively omitted."
            ),
            evidence_boundary=(
                "This requirement adds no unregistered 50% or 95% scalar threshold."
            ),
        ),
    ),
    independent_variables=(
        "joint, independent, myopic, or static control policy",
        "dense or mixture-of-experts model family and size",
        "accelerator memory and device-family portfolio",
        "starting serving topology",
        "workload family",
        "arrival rate and temporal process",
        "prefix reuse, tool-gap distribution, and expert-popularity drift",
        "fabric oversubscription and congestion",
        "rack and facility power regime",
        "device, fail-slow, and link-failure process",
        "topology, state-management, and scheduling control-family subset",
    ),
    held_out_dimensions=(
        "hardware family",
        "model family",
        "workload family",
        "fabric-topology class",
        "compound hardware-workload-congestion-power combination",
        "complete session, prefix lineage, and contiguous time block",
    ),
    real_validation_requirements=(
        "measured kernels, transfers, queueing, power, and quality curves on 8 to 64 accelerators across at least three device families",
        "controlled topology transitions and factorial ablations on 64 to 256 accelerators",
        "shadow operation on at least two real serving clusters",
        "guarded live experiment on 256 to 1,024 accelerators with production-shaped traffic",
        "confirmatory held-out workload weeks on at least 1,024 accelerators across eight failure and network domains",
    ),
    seed_policy=(
        "Use 30 frozen seeds per stochastic virtual cell, run 24 simulated "
        "hours after a one-hour warm-up, resample by trace-day and failure "
        "domain rather than request, freeze immutable evaluation seeds after "
        "development, and split complete sessions and contiguous trace blocks."
    ),
    source_window="2026-04-13/2026-07-12",
    notes=(
        "Status is designed; no result is reported.",
        "The regime-crossing family count is a lossless machine statistic: a family counts only when both execution regimes each occupy at least 10% of request-time in at least half its evaluation traces.",
        "The separate static-dominance falsifier preserves the Markdown wording at the 90% boundary rather than silently treating it as identical to the regime-crossing statistic.",
        "All rejected, expired, delayed, migrated, and quality-degraded work remains charged to service value and facility energy.",
        "Every equal-accounting, ranking-transfer, causal-exclusion, service-vector, and uncertainty-family falsifier is encoded as a mandatory structured evidence requirement; unresolved requirements keep a run inconclusive.",
        "Only live stages 5 and 6 can support serving-value claims, and only stage 6 can support datacenter-scale interaction and regime crossing.",
    ),
)


E005_PROTOCOL = ExperimentProtocol(
    experiment_id="E005",
    title="Heterogeneous Architecture Co-design",
    question=(
        "Under a fixed facility power envelope and wall-clock training budget, "
        "can a mixed accelerator fleet make a different model architecture "
        "optimal, rather than merely execute the homogeneous-fleet winner more "
        "cheaply? The experiment jointly chooses model sections, conditional "
        "routing, precision, device types, parallelism, and placement. Its "
        "central causal test separates an architecture effect from a placement-"
        "only effect."
    ),
    hypothesis=(
        "Under identical peak facility power and maximum wall-clock budgets, "
        "joint architecture and hardware co-design will improve capability per "
        "facility joule CE by at least 25% over the best architecture co-designed "
        "for any single homogeneous accelerator family. No preregistered task-"
        "family metric will be more than 2% worse than the best homogeneous "
        "design. Let J be the joint design, H the best homogeneous design, and "
        "P the heterogeneous placement of H with its architecture frozen: "
        "CE(J) - CE(P) will be at least 0.5 * (CE(J) - CE(H)). On held-out "
        "candidate designs, the world model will achieve Kendall ranking "
        "correlation of at least 0.70, select a design within 10% of the best "
        "observed CE, and attain 85% to 95% empirical coverage for nominal 90% "
        "intervals. Multi-fidelity search, including failed candidates, will "
        "consume no more than 25% of the facility energy of one target-scale "
        "training run."
    ),
    baselines=(
        "best separately co-designed homogeneous accelerator family",
        "best homogeneous architecture placed on the heterogeneous fleet",
        "joint architecture executed on the best homogeneous fleet",
        "sequential architecture-then-hardware search",
        "fixed compound architecture with Maestro-style section scheduling",
        "heterogeneous placement optimized only for throughput",
        "heterogeneous placement optimized only for accelerator energy",
        "bounded proxy-space exhaustive enumeration for regret only",
    ),
    metrics=(
        MetricSpec(
            "ce_improvement_over_best_homogeneous",
            "1",
            "Capability-per-facility-joule improvement over the best fair "
            "homogeneous co-design at equal peak power and wall-clock limits.",
            True,
        ),
        MetricSpec(
            "worst_task_family_metric_regression",
            "1",
            "Maximum relative regression over every frozen preregistered "
            "task-family capability metric.",
            True,
        ),
        MetricSpec(
            "architecture_attributable_joint_gain_fraction",
            "1",
            "(CE(J)-CE(P))/(CE(J)-CE(H)), where J is joint co-design, H is the "
            "best homogeneous design, and P is heterogeneous placement of H "
            "with its architecture frozen.",
            True,
        ),
        MetricSpec(
            "hardware_classes_at_20pct_training_flops",
            "class_count",
            "Hardware classes each delivering at least 20% of selected-design "
            "training FLOPs.",
            True,
        ),
        MetricSpec(
            "held_out_kendall_ranking_correlation",
            "1",
            "Kendall correlation between predicted and observed CE rankings on "
            "held-out candidate designs.",
            True,
        ),
        MetricSpec(
            "selected_design_regret",
            "1",
            "Relative CE gap between the selected design and best observed "
            "held-out design.",
            True,
        ),
        MetricSpec(
            "nominal_90_interval_coverage",
            "1",
            "Empirical held-out coverage of nominal 90% world-model intervals.",
            True,
        ),
        MetricSpec(
            "search_energy_fraction_of_target_run",
            "1",
            "Multi-fidelity search facility energy, including failed candidates, "
            "divided by one target-scale training run's facility energy.",
            True,
        ),
        MetricSpec(
            "capability_geometric_mean",
            "1",
            "Geometric mean C of frozen normalized task-family metrics, shown "
            "beside every raw component.",
            True,
        ),
        MetricSpec(
            "facility_energy_j",
            "J",
            "IT plus cooling energy from training start through final evaluation, "
            "including failed and repeated work.",
            True,
        ),
        MetricSpec(
            "time_to_capability_target_seconds",
            "s",
            "Wall-clock time to each frozen capability target.",
            True,
        ),
        MetricSpec(
            "out_of_scope_abstention_fraction",
            "1",
            "Fraction of held-out candidates on which the world model abstains "
            "because they are outside calibration scope.",
        ),
        MetricSpec(
            "network_energy_j",
            "J",
            "Fabric energy included in the common facility boundary.",
        ),
        MetricSpec(
            "cooling_energy_j",
            "J",
            "Cooling energy included in the common facility boundary.",
        ),
        MetricSpec(
            "failed_and_repeated_work_energy_j",
            "J",
            "Facility energy consumed by failed candidates and repeated work.",
        ),
    ),
    falsifiers=(
        FalsifierSpec(
            "e005-ce-gain",
            "ce_improvement_over_best_homogeneous",
            ComparisonOperator.GE,
            0.25,
            description="CE must improve by at least 25% over homogeneous co-design.",
        ),
        FalsifierSpec(
            "e005-task-family-noninferiority",
            "worst_task_family_metric_regression",
            ComparisonOperator.LE,
            0.02,
            description="No task-family metric may regress by more than 2%.",
        ),
        FalsifierSpec(
            "e005-architecture-attribution",
            "architecture_attributable_joint_gain_fraction",
            ComparisonOperator.GE,
            0.50,
            description=(
                "At least half of the joint CE gain must remain after subtracting "
                "the placement-only gain."
            ),
        ),
        FalsifierSpec(
            "e005-substantive-heterogeneity",
            "hardware_classes_at_20pct_training_flops",
            ComparisonOperator.GE,
            2.0,
            description=(
                "At least two hardware classes must each deliver at least 20% "
                "of training FLOPs."
            ),
        ),
        FalsifierSpec(
            "e005-ranking",
            "held_out_kendall_ranking_correlation",
            ComparisonOperator.GE,
            0.70,
            description="Held-out Kendall ranking correlation must be at least 0.70.",
        ),
        FalsifierSpec(
            "e005-selection-regret",
            "selected_design_regret",
            ComparisonOperator.LE,
            0.10,
            description="Selected-design regret must be no more than 10% of CE.",
        ),
        FalsifierSpec(
            "e005-interval-coverage",
            "nominal_90_interval_coverage",
            ComparisonOperator.BETWEEN,
            0.85,
            upper_threshold=0.95,
            description=(
                "Nominal 90% intervals must achieve 85% to 95% empirical coverage."
            ),
        ),
        FalsifierSpec(
            "e005-search-energy",
            "search_energy_fraction_of_target_run",
            ComparisonOperator.LE,
            0.25,
            description=(
                "Search, including failed candidates, must consume no more than "
                "25% of one target-scale run's facility energy."
            ),
        ),
    ),
    evidence_requirements=(
        EvidenceRequirementSpec(
            requirement_id="raw_capability_vector_and_frozen_normalization",
            kind="capability_vector_completeness",
            description=(
                "Every raw task-family capability metric and its frozen semantic "
                "normalization anchors must be reported beside composite C."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "capability_geometric_mean",
                "worst_task_family_metric_regression",
                "time_to_capability_target_seconds",
            ),
            required_panels=(
                "every frozen raw task-family metric",
                "frozen semantic floors and ceilings",
                "composite C",
                "each frozen capability target",
            ),
            acceptance_rule=(
                "The complete raw vector, transforms, floors, ceilings, task "
                "weights, composite C, and time to each target must be reported; "
                "every component must satisfy the registered noninferiority gate."
            ),
            evidence_boundary=(
                "Composite C or CE alone cannot resolve capability and may not "
                "hide a task-family collapse."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="equalized_full_search_accounting_nonreversal",
            kind="accounting_nonreversal",
            description=(
                "The architecture gain must survive equalized search budget and "
                "complete facility accounting, including failed work."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "ce_improvement_over_best_homogeneous",
                "facility_energy_j",
                "search_energy_fraction_of_target_run",
                "network_energy_j",
                "cooling_energy_j",
                "failed_and_repeated_work_energy_j",
            ),
            required_panels=(
                "equal search budget",
                "failed-run energy",
                "network energy",
                "cooling energy",
                "complete final evaluation",
            ),
            acceptance_rule=(
                "The signed CE gain must remain after every design is charged "
                "the same search budget and full facility-energy boundary."
            ),
            evidence_boundary=(
                "Accelerator-only energy or successful-candidate-only accounting "
                "cannot resolve architecture efficiency."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="ranking_transfer_by_every_named_panel",
            kind="ranking_transfer",
            description=(
                "The selected architecture must retain its ranking on every "
                "named held-out hardware, model, task, fabric, and compound panel."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=(
                "held_out_kendall_ranking_correlation",
                "selected_design_regret",
                "nominal_90_interval_coverage",
            ),
            required_panels=(
                "hardware family",
                "model or architecture family",
                "data mixture",
                "fabric class",
                "capability-evaluation task set",
                "compound hardware-model-data-power-failure combination",
            ),
            acceptance_rule=(
                "Every named panel must satisfy the registered ranking, regret, "
                "and interval gates without pooling away a failed panel."
            ),
            evidence_boundary=(
                "A pooled aggregate cannot resolve per-panel ranking transfer."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="out_of_scope_abstention_adequacy",
            kind="abstention_admission",
            description=(
                "The world model must abstain when a candidate is outside its "
                "frozen calibration support."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=("out_of_scope_abstention_fraction",),
            required_panels=(
                "frozen calibration-support predicate",
                "held-out out-of-scope candidates",
                "named fallback behavior",
            ),
            acceptance_rule=(
                "Every candidate adjudicated outside the frozen support predicate "
                "must trigger the registered abstention and fallback behavior, "
                "with false abstentions and missed abstentions exposed."
            ),
            evidence_boundary=(
                "The protocol sets no post hoc acceptable abstention rate; the "
                "support predicate and adjudication procedure must be frozen first."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="proxy_to_target_directional_transfer",
            kind="scale_transfer",
            description=(
                "Proxy-scale architecture rankings must transfer directionally "
                "to repeated target-scale training."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "held_out_kendall_ranking_correlation",
                "selected_design_regret",
                "ce_improvement_over_best_homogeneous",
                "capability_geometric_mean",
            ),
            required_panels=(
                "proxy-scale candidates",
                "13B to 30B controlled comparisons",
                "70B dense or 100B-total-parameter MoE target scale",
            ),
            acceptance_rule=(
                "The selected-versus-baseline ordering must agree between proxy "
                "and repeated target-scale runs under the same frozen evaluation set."
            ),
            evidence_boundary=(
                "Only repeated stage-6 target-scale training can support the "
                "datacenter-scale capability and efficiency claim."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="architecture_counterfactual_identified",
            kind="causal_architecture_attribution",
            description=(
                "The architecture effect must be separated from heterogeneous "
                "placement of the frozen homogeneous winner."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "architecture_attributable_joint_gain_fraction",
                "ce_improvement_over_best_homogeneous",
                "hardware_classes_at_20pct_training_flops",
            ),
            required_panels=(
                "joint architecture and placement design J",
                "best homogeneous co-design H",
                "heterogeneous placement of frozen H architecture P",
            ),
            comparison_baselines=(
                "best separately co-designed homogeneous accelerator family",
                "best homogeneous architecture placed on the heterogeneous fleet",
                "joint architecture executed on the best homogeneous fleet",
            ),
            acceptance_rule=(
                "J, H, and P must share peak-power, wall-clock, search-budget, and "
                "evaluation boundaries, and the registered architecture-attribution "
                "gate must pass with a positive observed joint gain."
            ),
            evidence_boundary=(
                "A nonpositive joint-gain denominator is inconclusive and cannot "
                "be presented as surviving architecture attribution."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="failed_candidate_accounting_completeness",
            kind="search_accounting_completeness",
            description=(
                "Failed, repeated, and numerically invalid search candidates must "
                "remain in search time and facility-energy accounting."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=(
                "search_energy_fraction_of_target_run",
                "facility_energy_j",
                "failed_and_repeated_work_energy_j",
            ),
            required_panels=(
                "successful candidates",
                "failed candidates",
                "repeated work",
                "final evaluation",
            ),
            acceptance_rule=(
                "Every attempted candidate must appear exactly once in the "
                "content-addressed search ledger and all consumed facility energy "
                "and wall time must enter the registered search boundary."
            ),
            evidence_boundary=(
                "Successful-candidate-only logs cannot support search efficiency."
            ),
        ),
    ),
    independent_variables=(
        "joint, sequential, placement-only, or homogeneous search policy",
        "model architecture family and section graph",
        "depth, width, expert count, conditional routing, precision, and sparsity",
        "accelerator-class portfolio",
        "section placement and parallelism",
        "model and training scale",
        "fabric class and oversubscription",
        "facility power envelope and optimization constraint",
        "data mixture",
        "device loss, fail-slow, and rack-curtailment regime",
        "candidate-evaluation and proxy-training budget",
    ),
    held_out_dimensions=(
        "hardware family",
        "architecture family",
        "data mixture",
        "fabric class",
        "capability-evaluation task set",
        "compound hardware-model-data-power-failure combination",
        "complete training run and contiguous data block",
    ),
    real_validation_requirements=(
        "exhaustive sub-1B bounded-space validation of ranking, uncertainty, and regret",
        "equal-budget 1B to 7B studies across at least three device classes and five seeds",
        "shadow prediction on two real heterogeneous clusters",
        "repeated 13B to 30B comparisons on 64 to 512 accelerators including frozen-architecture counterfactuals",
        "at least two independent runs per design at 70B dense or 100B-total-parameter MoE scale on at least 1,024 accelerators under the same facility envelope and final evaluation set",
    ),
    seed_policy=(
        "Use five frozen seeds per proxy candidate, at least three seeds for "
        "7B to 30B confirmatory comparisons, and at least two independent "
        "target-scale runs per selected design and baseline; content-address "
        "final task weights, metric transforms, architecture constraints, and "
        "seeds before evaluation, and keep failed candidates in accounting."
    ),
    source_window="2026-04-13/2026-07-12",
    notes=(
        "Status is designed; no result is reported.",
        "The architecture-attributable statistic exactly represents CE(J)-CE(P) >= 0.5*(CE(J)-CE(H)) when the observed joint gain CE(J)-CE(H) is positive; a nonpositive denominator cannot be interpreted as surviving the protocol.",
        "The capability vector, every raw task metric, and its frozen normalization anchors must be reported beside composite C and CE.",
        "Search energy is reported separately and amortized over one, four, and sixteen deployments even though only the one-run ratio is a falsifier.",
        "Every capability-vector, accounting, transfer-panel, abstention, architecture-attribution, and failed-candidate falsifier is encoded as a mandatory structured evidence requirement; unresolved requirements keep a run inconclusive.",
        "Only repeated target-scale stage-6 training can support the datacenter-scale capability and facility-efficiency claim.",
    ),
)


E006_PROTOCOL = ExperimentProtocol(
    experiment_id="E006",
    title="Firm Grid-responsive Inference",
    question=(
        "Can an inference datacenter offer a firm, auditable power-reduction "
        "commitment to the grid while preserving per-request utility and tail "
        "latency, including under bursty arrivals, equipment faults, hot "
        "weather, and repeated dispatch? The question is about contracted "
        "flexibility, not whether average power can be lowered once. A successful "
        "controller must predict how much reduction it can guarantee before the "
        "event, deliver it at the grid meter, and avoid a hidden latency, quality, "
        "rejection, or rebound cost."
    ),
    hypothesis=(
        "A joint controller will provide R_firm equal to at least 20% of the "
        "matched non-dispatch facility load, and its R_firm will be at least "
        "50% greater than that of the best isolated mechanism under identical "
        "service constraints. Relative to matched no-dispatch operation, TTFT "
        "and TPOT SLO attainment will each decline by no more than one percentage "
        "point in any workload family, P99 TTFT and P99 TPOT will remain within "
        "their frozen workload-specific limits, and frozen per-request utility "
        "will decline by no more than 1%. Metered power during the 30 minutes "
        "after an event will not exceed the matched baseline peak by more than "
        "5%, with deferred energy and work not hidden beyond the reporting "
        "window. On held-out events, the controller's nominal 99% delivery "
        "probability will have a lower 95% confidence bound of at least 99%, "
        "using event-level rather than request-level replication. R_firm also "
        "requires at least 90% of the bid within 10 seconds and the full bid "
        "sustained for a 15-minute event."
    ),
    baselines=(
        "no demand-response action",
        "accelerator power-cap or DVFS-only control",
        "quantization and model-switching-only control",
        "batching, admission, and deadline-aware deferral only",
        "geographic request routing and load shifting only",
        "aggregate-load scheduling without request-conditioned utility",
        "independent isolated-lever ensemble with frozen conflict priority",
        "joint controller without calibrated reserve derating",
        "future-arrival-fault-weather oracle for reserve and regret only",
    ),
    metrics=(
        MetricSpec(
            "r_firm_fraction_of_matched_load",
            "1",
            "Largest preregistered reserve bid satisfying delivery, service, "
            "and rebound constraints, divided by matched non-dispatch facility load.",
            True,
        ),
        MetricSpec(
            "joint_to_best_isolated_r_firm_ratio",
            "1",
            "Joint-controller R_firm divided by the best isolated mechanism's "
            "R_firm under identical service constraints.",
            True,
        ),
        MetricSpec(
            "event_delivery_probability_lower_95_bound",
            "1",
            "Event-clustered lower 95% confidence bound on held-out reserve delivery probability.",
            True,
        ),
        MetricSpec(
            "time_to_90pct_delivery_seconds",
            "s",
            "Time from dispatch to delivery of at least 90% of the committed bid.",
            True,
        ),
        MetricSpec(
            "full_delivery_sustained_seconds",
            "s",
            "Duration for which the complete committed bid is sustained.",
            True,
        ),
        MetricSpec(
            "worst_ttft_slo_decline_percentage_points",
            "percentage_point",
            "Largest TTFT SLO-attainment decline across workload families.",
            True,
        ),
        MetricSpec(
            "worst_tpot_slo_decline_percentage_points",
            "percentage_point",
            "Largest TPOT SLO-attainment decline across workload families.",
            True,
        ),
        MetricSpec(
            "worst_p99_ttft_to_frozen_limit_ratio",
            "1",
            "Maximum workload-family P99 TTFT divided by its frozen limit.",
            True,
        ),
        MetricSpec(
            "worst_p99_tpot_to_frozen_limit_ratio",
            "1",
            "Maximum workload-family P99 TPOT divided by its frozen limit.",
            True,
        ),
        MetricSpec(
            "worst_frozen_request_utility_decline",
            "1",
            "Maximum frozen per-request utility decline across workload families.",
            True,
        ),
        MetricSpec(
            "p50_ttft_seconds",
            "s",
            "P50 time to first token, reported by workload family.",
            True,
        ),
        MetricSpec(
            "p50_tpot_seconds_per_token",
            "s/token",
            "P50 time per output token, reported by workload family.",
            True,
        ),
        MetricSpec(
            "post_event_peak_excess_fraction",
            "1",
            "Maximum metered power during the 30 minutes after dispatch minus "
            "matched baseline peak, divided by matched baseline peak.",
            True,
        ),
        MetricSpec(
            "sustained_delivery_error",
            "1",
            "Error between committed and delivered reduction over the event.",
            True,
        ),
        MetricSpec(
            "settlement_interval_tracking_error",
            "1",
            "Tracking error at the preregistered settlement interval.",
            True,
        ),
        MetricSpec(
            "reserve_decision_regret",
            "1",
            "Reserve-bid decision regret relative to the clairvoyant oracle.",
            True,
        ),
        MetricSpec(
            "reserve_prediction_interval_coverage",
            "1",
            "Held-out event coverage of the preregistered reserve and delivery "
            "prediction intervals.",
            True,
        ),
        MetricSpec(
            "deferred_work_units",
            "work_unit",
            "Dispatched work still deferred after the event reporting horizon.",
            True,
        ),
        MetricSpec(
            "deferred_facility_energy_j",
            "J",
            "Facility energy needed to complete deferred work after dispatch.",
            True,
        ),
        MetricSpec(
            "rejected_request_fraction",
            "1",
            "Fraction of offered requests rejected during the full event boundary, "
            "reported by workload family.",
            True,
        ),
        MetricSpec(
            "expired_request_fraction",
            "1",
            "Fraction of offered requests that expire during the full event "
            "boundary, reported by workload family.",
            True,
        ),
        MetricSpec(
            "total_meter_energy_j",
            "J",
            "Full metered facility energy including cooling, host, network, and storage.",
        ),
        MetricSpec(
            "offered_reserve_availability",
            "1",
            "Fraction of eligible events for which the controller commits a reserve bid.",
        ),
    ),
    falsifiers=(
        FalsifierSpec(
            "e006-firm-load-fraction",
            "r_firm_fraction_of_matched_load",
            ComparisonOperator.GE,
            0.20,
            description="R_firm must be at least 20% of matched facility load.",
        ),
        FalsifierSpec(
            "e006-isolated-mechanism-gain",
            "joint_to_best_isolated_r_firm_ratio",
            ComparisonOperator.GE,
            1.50,
            description=(
                "Joint R_firm must be at least 1.5 times the best isolated mechanism."
            ),
        ),
        FalsifierSpec(
            "e006-delivery-confidence",
            "event_delivery_probability_lower_95_bound",
            ComparisonOperator.GE,
            0.99,
            description=(
                "The event-level lower 95% confidence bound on delivery "
                "probability must be at least 99%."
            ),
        ),
        FalsifierSpec(
            "e006-response-time",
            "time_to_90pct_delivery_seconds",
            ComparisonOperator.LE,
            10.0,
            description="At least 90% of the bid must arrive within 10 seconds.",
        ),
        FalsifierSpec(
            "e006-sustained-delivery",
            "full_delivery_sustained_seconds",
            ComparisonOperator.GE,
            900.0,
            description="The complete bid must be sustained for the 15-minute event.",
        ),
        FalsifierSpec(
            "e006-ttft-slo",
            "worst_ttft_slo_decline_percentage_points",
            ComparisonOperator.LE,
            1.0,
            description=(
                "No workload family may lose more than one percentage point of "
                "TTFT SLO attainment."
            ),
        ),
        FalsifierSpec(
            "e006-tpot-slo",
            "worst_tpot_slo_decline_percentage_points",
            ComparisonOperator.LE,
            1.0,
            description=(
                "No workload family may lose more than one percentage point of "
                "TPOT SLO attainment."
            ),
        ),
        FalsifierSpec(
            "e006-p99-ttft",
            "worst_p99_ttft_to_frozen_limit_ratio",
            ComparisonOperator.LE,
            1.0,
            description="Every workload-family P99 TTFT must stay within its frozen limit.",
        ),
        FalsifierSpec(
            "e006-p99-tpot",
            "worst_p99_tpot_to_frozen_limit_ratio",
            ComparisonOperator.LE,
            1.0,
            description="Every workload-family P99 TPOT must stay within its frozen limit.",
        ),
        FalsifierSpec(
            "e006-request-utility",
            "worst_frozen_request_utility_decline",
            ComparisonOperator.LE,
            0.01,
            description="No workload family may lose more than 1% frozen utility.",
        ),
        FalsifierSpec(
            "e006-rebound",
            "post_event_peak_excess_fraction",
            ComparisonOperator.LE,
            0.05,
            description=(
                "The 30-minute post-event metered peak must exceed the matched "
                "baseline peak by no more than 5%."
            ),
        ),
    ),
    evidence_requirements=(
        EvidenceRequirementSpec(
            requirement_id="full_horizon_deferred_work_energy_nonreversal",
            kind="full_horizon_nonreversal",
            description=(
                "Deferred work and its completion energy must remain inside the "
                "reporting horizon and must not erase the time-local grid benefit."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "post_event_peak_excess_fraction",
                "deferred_work_units",
                "deferred_facility_energy_j",
                "total_meter_energy_j",
            ),
            required_panels=(
                "pre-event baseline window",
                "15-minute dispatch event",
                "30-minute rebound window",
                "completion of all deferred work",
            ),
            acceptance_rule=(
                "All deferred work must be completed and charged, and its full "
                "metered energy and rebound must not reverse the delivered benefit."
            ),
            evidence_boundary=(
                "A reporting horizon ending with queued or deferred work cannot "
                "resolve firm flexibility."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="accounting_exclusion_robustness",
            kind="accounting_boundary_robustness",
            description=(
                "The result must survive inclusion of rejected and expired "
                "requests, cooling, host, network, failed events, and pre-event energy."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "rejected_request_fraction",
                "expired_request_fraction",
                "deferred_facility_energy_j",
                "total_meter_energy_j",
                "event_delivery_probability_lower_95_bound",
            ),
            required_panels=(
                "rejected and expired requests",
                "cooling power",
                "host and network power",
                "failed events",
                "pre-event energy",
            ),
            acceptance_rule=(
                "The signed reserve and service result must remain after every "
                "named boundary component is included under matched accounting."
            ),
            evidence_boundary=(
                "Accelerator-only power or accepted-request-only service cannot "
                "support a firm reserve claim."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="ranking_and_confidence_transfer_by_panel",
            kind="shadow_ranking_and_uncertainty_transfer",
            description=(
                "Reserve rankings and confidence behavior must transfer to every "
                "held-out campus, workload, hardware, weather, and compound panel."
            ),
            earliest_resolvable_stage=ExperimentStage.SHADOW,
            required_metrics=(
                "reserve_decision_regret",
                "reserve_prediction_interval_coverage",
                "event_delivery_probability_lower_95_bound",
            ),
            required_panels=(
                "campus",
                "workload family",
                "hardware family",
                "weather regime",
                "compound workload-heat-network-device-failure panel",
            ),
            acceptance_rule=(
                "Every named panel must retain the frozen reserve ordering and "
                "report its event-level confidence behavior and oracle regret; no "
                "failed panel may be pooled away."
            ),
            evidence_boundary=(
                "Shadow telemetry can resolve directional prediction transfer, "
                "not delivered firm reserve."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="non_request_or_isolated_baseline_vector_dominance",
            kind="baseline_vector_dominance",
            description=(
                "A non-request-conditioned or isolated controller must not match "
                "joint control across the complete reserve and service vector."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "r_firm_fraction_of_matched_load",
                "joint_to_best_isolated_r_firm_ratio",
                "event_delivery_probability_lower_95_bound",
                "time_to_90pct_delivery_seconds",
                "full_delivery_sustained_seconds",
                "worst_ttft_slo_decline_percentage_points",
                "worst_tpot_slo_decline_percentage_points",
                "worst_p99_ttft_to_frozen_limit_ratio",
                "worst_p99_tpot_to_frozen_limit_ratio",
                "worst_frozen_request_utility_decline",
                "rejected_request_fraction",
                "expired_request_fraction",
                "post_event_peak_excess_fraction",
            ),
            comparison_baselines=(
                "accelerator power-cap or DVFS-only control",
                "quantization and model-switching-only control",
                "batching, admission, and deadline-aware deferral only",
                "geographic request routing and load shifting only",
                "aggregate-load scheduling without request-conditioned utility",
                "independent isolated-lever ensemble with frozen conflict priority",
            ),
            acceptance_rule=(
                "No comparison controller may match joint control within "
                "uncertainty on all reserve, response, service, rejection, and "
                "rebound outcomes under identical boundaries."
            ),
            evidence_boundary=(
                "Requires matched controlled events and identical service constraints."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="controlled_live_directional_transfer",
            kind="controlled_live_transfer",
            description=(
                "The virtual reserve result must transfer directionally to "
                "controlled live dispatch."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "r_firm_fraction_of_matched_load",
                "event_delivery_probability_lower_95_bound",
                "time_to_90pct_delivery_seconds",
                "full_delivery_sustained_seconds",
                "post_event_peak_excess_fraction",
            ),
            required_panels=(
                "at least 1 MW live inference load",
                "heat stress",
                "arrival burst",
                "equipment loss",
            ),
            acceptance_rule=(
                "The signed reserve, response, duration, and rebound effects must "
                "agree between the virtual prediction and frozen controlled events."
            ),
            evidence_boundary=(
                "Only the 10 MW, two-domain, 300-window confirmatory stage can "
                "support the 99% firm-reserve claim."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="service_vector_by_workload",
            kind="workload_service_vector",
            description=(
                "P50 and P99 TTFT and TPOT, SLO attainment, rejection, expiration, "
                "and frozen request utility must be reported by workload family."
            ),
            earliest_resolvable_stage=ExperimentStage.CONTROLLED,
            required_metrics=(
                "p50_ttft_seconds",
                "p50_tpot_seconds_per_token",
                "worst_p99_ttft_to_frozen_limit_ratio",
                "worst_p99_tpot_to_frozen_limit_ratio",
                "worst_ttft_slo_decline_percentage_points",
                "worst_tpot_slo_decline_percentage_points",
                "rejected_request_fraction",
                "expired_request_fraction",
                "worst_frozen_request_utility_decline",
            ),
            required_panels=(
                "every preregistered workload family",
                "accepted requests",
                "rejected requests",
                "expired requests",
            ),
            acceptance_rule=(
                "Every workload family must pass the registered SLO, P99-limit, "
                "and utility gates, with the complete P50, rejection, and expiration "
                "vector reported rather than hidden in an average."
            ),
            evidence_boundary=(
                "Average token volume cannot substitute for request-level service "
                "and utility outcomes."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="bid_selection_and_interval_method_frozen",
            kind="decision_and_uncertainty_preregistration",
            description=(
                "Reserve-bid selection, delivery adjudication, interval construction, "
                "and regret evaluation must be frozen before held-out events open."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=(
                "event_delivery_probability_lower_95_bound",
                "sustained_delivery_error",
                "settlement_interval_tracking_error",
                "reserve_decision_regret",
                "reserve_prediction_interval_coverage",
            ),
            required_panels=(
                "reserve-bid rule",
                "event delivery adjudication",
                "settlement interval",
                "confidence-interval method",
                "clairvoyant oracle action set",
            ),
            acceptance_rule=(
                "All named methods and action sets must be content-addressed before "
                "evaluation, and every held-out event must report delivery error, "
                "tracking error, interval behavior, and regret."
            ),
            evidence_boundary=(
                "This requirement introduces no post hoc calibration or regret threshold."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="offered_reserve_availability_and_derating",
            kind="offer_availability_accounting",
            description=(
                "Declined and derated events must reduce offered-reserve availability "
                "and cannot be counted as successful delivery."
            ),
            earliest_resolvable_stage=ExperimentStage.SHADOW,
            required_metrics=(
                "offered_reserve_availability",
                "event_delivery_probability_lower_95_bound",
            ),
            required_panels=(
                "offered events",
                "declined events",
                "derated bids",
                "delivered bids",
            ),
            acceptance_rule=(
                "Every eligible event must appear in exactly one frozen offer-state "
                "category, and delivery probability may include only bids actually "
                "offered at their derated commitment."
            ),
            evidence_boundary=(
                "Selective reporting of accepted events overstates firm availability."
            ),
        ),
        EvidenceRequirementSpec(
            requirement_id="event_campus_day_independence_and_power",
            kind="statistical_independence_and_power",
            description=(
                "Replication, confidence bounds, and power must use independent "
                "events and campus-days rather than requests."
            ),
            earliest_resolvable_stage=ExperimentStage.VIRTUAL,
            required_metrics=(
                "event_delivery_probability_lower_95_bound",
                "reserve_prediction_interval_coverage",
                "sustained_delivery_error",
                "settlement_interval_tracking_error",
            ),
            required_panels=(
                "complete dispatch event",
                "complete campus-day",
                "contiguous workload block",
                "non-overlapping confirmatory dispatch windows",
            ),
            acceptance_rule=(
                "All resampling and confidence procedures must cluster by complete "
                "event and campus-day; virtual cells use their 30 frozen seeds and "
                "the firm confirmatory claim requires at least 300 non-overlapping "
                "live dispatch windows. Underpowered panels remain inconclusive."
            ),
            evidence_boundary=(
                "Request-level replication and overlapping event windows cannot "
                "support event-level firmness."
            ),
        ),
    ),
    independent_variables=(
        "joint, isolated, independent-ensemble, or oracle policy",
        "event duration and response requirement",
        "reserve-bid fraction",
        "workload family and mixture",
        "arrival process",
        "model family, size, precision, and quantization",
        "hardware-family composition",
        "single-campus or multi-campus topology and congestion",
        "ambient temperature and cooling condition",
        "device, fail-slow, link, and telemetry-failure process",
        "repeated-event recovery interval",
    ),
    held_out_dimensions=(
        "complete campus-day and contiguous workload block",
        "workload family",
        "model family",
        "hardware family",
        "campus",
        "weather regime",
        "dispatch-shape family",
        "compound workload-heat-network-device-failure panel",
    ),
    real_validation_requirements=(
        "per-model, precision, batching, DVFS, transition, and utility measurements on 8 to 64 accelerators",
        "meter response, cooling lag, and request accounting on a controlled 100 to 500 kW cluster",
        "shadow bids on at least two live inference sites",
        "repeated controlled events on at least 1 MW including heat, burst, and equipment-loss panels",
        "frozen confirmatory protocol on at least 10 MW across two power and failure domains with at least 300 non-overlapping dispatch windows and held-out campus-days",
    ),
    seed_policy=(
        "Use 30 frozen seeds per stochastic virtual cell; aggregate meter and "
        "service outcomes by complete event and campus-day, never request; "
        "split complete campus-days and contiguous workload blocks 60%/20%/20% "
        "before fitting; open evaluation meter data once; and require at least "
        "300 non-overlapping live dispatch windows for the confirmatory claim."
    ),
    source_window="2026-04-13/2026-07-12",
    notes=(
        "Status is designed; no result is reported.",
        "R_firm is the largest preregistered bid whose event-level lower 95% delivery bound is at least 99%, whose response and duration gates pass, and whose service and rebound constraints all pass.",
        "Battery, generation, exported on-site generation, and cooling preconditioning are reported separately and cannot be counted as compute-native reduction.",
        "Declined or derated events reduce offered-reserve availability and cannot be counted as delivery successes.",
        "Every deferred-work, accounting-boundary, transfer-panel, baseline-vector, service, offer-availability, and live-dispatch falsifier is encoded as a mandatory structured evidence requirement; unresolved requirements keep a run inconclusive.",
        "Only the 10 MW, two-domain, 300-window stage-6 protocol can support the 99% firm-reserve claim.",
    ),
)


EXPERIMENT_PROTOCOLS: Mapping[str, ExperimentProtocol] = MappingProxyType(
    {
        protocol.experiment_id: protocol
        for protocol in (
            E001_PROTOCOL,
            E002_PROTOCOL,
            E003_PROTOCOL,
            E004_PROTOCOL,
            E005_PROTOCOL,
            E006_PROTOCOL,
        )
    }
)


def protocol_for(experiment_id: str) -> ExperimentProtocol:
    """Return one protocol by case-insensitive experiment identifier."""
    key = experiment_id.strip().upper()
    try:
        return EXPERIMENT_PROTOCOLS[key]
    except KeyError as exc:
        available = ", ".join(EXPERIMENT_PROTOCOLS)
        raise KeyError(
            f"unknown experiment protocol {experiment_id!r}; available: {available}"
        ) from exc


def protocol_catalog() -> Tuple[ExperimentProtocol, ...]:
    """Return the immutable protocol catalog in experiment-number order."""
    return tuple(EXPERIMENT_PROTOCOLS.values())


__all__ = [
    "E001_PROTOCOL",
    "E002_PROTOCOL",
    "E003_PROTOCOL",
    "E004_PROTOCOL",
    "E005_PROTOCOL",
    "E006_PROTOCOL",
    "EXPERIMENT_PROTOCOLS",
    "protocol_catalog",
    "protocol_for",
]
