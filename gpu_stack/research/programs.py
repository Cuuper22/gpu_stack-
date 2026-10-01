"""Machine-readable preregistrations for GPUSTACK research programs E001-E002.

This module holds the scalar and structured evidence gates so runners can
check them in code. Qualitative claims — transfer, vector,
accounting, causal — are deliberately not converted into invented numerical
thresholds; a gate exists here only if the design really states one.
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


EXPERIMENT_PROTOCOLS: Mapping[str, ExperimentProtocol] = MappingProxyType(
    {
        protocol.experiment_id: protocol
        for protocol in (
            E001_PROTOCOL,
            E002_PROTOCOL,
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
    "EXPERIMENT_PROTOCOLS",
    "protocol_catalog",
    "protocol_for",
]
