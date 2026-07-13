"""Next-work report item builders.

The scientific queue is intentionally distinct from structural diagnostics.
Root debt and scenario closure remain useful, but they do not outrank missing
observations, held-out evaluation, or an experiment-enabling runtime.
"""

from __future__ import annotations

from .next_work_evidence import _Evidence
from .next_work_models import NextWorkItem
from .next_work_rendering import (
    _format_capability_types,
    _format_families,
    _format_labels,
    _format_large_files,
    _format_roots,
    _missing_family_summary,
)


def _highest_impact(evidence: _Evidence) -> tuple[NextWorkItem, ...]:
    """Return the three highest-leverage scientific priorities."""

    first_screen_complete = (
        not evidence.missing_observation_types
        and not evidence.missing_temporal_types
        and not evidence.missing_intervention_types
        and not evidence.missing_evaluation_types
        and not evidence.missing_e001_execution_symbols
        and evidence.experiment_spec_count >= 6
        and evidence.experiment_result_artifact_count >= 1
        and len(evidence.causal_observatory_markers) == 5
        and evidence.observatory_artifact_present
    )
    if first_screen_complete:
        recovery_contract_symbols = tuple(
            name
            for name in (
                "FailureTrace",
                "CheckpointLedger",
                "WorkLedger",
                "RecoveryPlan",
                "evaluate_work_attempt",
                "plan_recovery",
            )
            if name in evidence.production_symbol_names
        )
        transition_runtime_symbols = tuple(
            name
            for name in (
                "DecisionBoundary",
                "RecoveryRuntime",
                "RuntimeSnapshot",
            )
            if name in evidence.production_symbol_names
        )
        e001_recovery_integration_symbols = tuple(
            name
            for name in (
                "E001RecoveryV2Runner",
                "run_e001_recovery_v2",
            )
            if name in evidence.production_symbol_names
        )
        if "run_e001_recovery_v2" in e001_recovery_integration_symbols:
            return (
                NextWorkItem(
                    title="Measure fixed-local versus adaptive interrupted learning",
                    evidence=(
                        "live recovery scan: persisted experiment results="
                        f"{evidence.experiment_result_artifact_count}, recovery contract "
                        "symbols="
                        f"{', '.join(recovery_contract_symbols) or 'none'}, transition "
                        "runtime symbols="
                        f"{', '.join(transition_runtime_symbols) or 'none'}, recovery "
                        "runner class="
                        f"{'E001RecoveryV2Runner' if 'E001RecoveryV2Runner' in e001_recovery_integration_symbols else 'none'}, "
                        "recovery integration symbols=run_e001_recovery_v2; "
                        "v1_protocol_hash_match="
                        f"{evidence.e001_v1_protocol_hash_matches_persisted}, "
                        "v1_engine_hash_match="
                        f"{evidence.e001_v1_engine_hash_matches_persisted}; the four-policy "
                        "mechanics artifact reaches a matched durable frontier, but "
                        "learning progress remains a shared declared prior. The next "
                        "experiment must observe loss progress per FLOP, joule, and "
                        "wall-clock second for fixed-local and adaptive recovery under "
                        "the same interruptions"
                    ),
                    path="experiments/e001-beyond-one-datacenter/experiment.md",
                ),
                NextWorkItem(
                    title="Evaluate the learning response on held-out runs",
                    evidence=(
                        "live evidence scan: attached observation artifacts="
                        f"{evidence.observation_artifact_count}, held-out evaluation "
                        "observation references="
                        f"{evidence.evaluation_observation_reference_count}, structured "
                        "requirement results="
                        f"{evidence.structured_requirement_result_count}, unresolved="
                        f"{evidence.unresolved_requirement_result_count}; a calibration "
                        "fit cannot choose the policy unless the ranking transfers to "
                        "disjoint interruption and workload runs"
                    ),
                    path="experiments/e001-beyond-one-datacenter/experiment.md",
                ),
                NextWorkItem(
                    title="Put measured learning residuals in the observatory",
                    evidence=(
                        "live product scan: the recovery observatory renders mechanics "
                        "at three semantic depths, while held-out learning observation "
                        "references remain "
                        f"{evidence.evaluation_observation_reference_count}; "
                        "e002_spec_present="
                        f"{evidence.e002_spec_present}, E002 result artifacts="
                        f"{evidence.e002_result_artifact_count}; the next "
                        "artifact must replace the empty learning panel with observed "
                        "progress, residuals, intervals, and provenance without changing "
                        "the mechanical trace"
                    ),
                    path="docs/observatory.html",
                ),
            )

        return (
            NextWorkItem(
                title="Measure held-out E001 learning transfer",
                evidence=(
                    "live evidence scan: attached observation artifacts="
                    f"{evidence.observation_artifact_count}, held-out evaluation "
                    "observation references="
                    f"{evidence.evaluation_observation_reference_count}, structured "
                    "requirement results="
                    f"{evidence.structured_requirement_result_count}, unresolved="
                    f"{evidence.unresolved_requirement_result_count}"
                ),
                path="experiments/e001-beyond-one-datacenter/experiment.md",
            ),
            NextWorkItem(
                title="Integrate transition-driven recovery into E001",
                evidence=(
                    "live mechanics scan: recovery contract symbols="
                    f"{', '.join(recovery_contract_symbols) or 'none'}, transition "
                    "runtime symbols="
                    f"{', '.join(transition_runtime_symbols) or 'none'}, E001 recovery "
                    "integration symbols="
                    f"{', '.join(e001_recovery_integration_symbols) or 'none'}"
                ),
                path="gpu_stack/research/e001_recovery_runner.py",
            ),
            NextWorkItem(
                title="Build E002's measured power-waveform engine",
                evidence=(
                    "live program scan: e002_spec_present="
                    f"{evidence.e002_spec_present}, E002 result artifacts="
                    f"{evidence.e002_result_artifact_count}"
                ),
                path="experiments/e002-power-waveform-shaping/experiment.md",
            ),
        )

    observation_capabilities = _format_capability_types(
        evidence.observation_types,
        evidence.missing_observation_types,
    )
    temporal_capabilities = _format_capability_types(
        evidence.temporal_types,
        evidence.missing_temporal_types,
    )
    intervention_capabilities = _format_capability_types(
        evidence.intervention_types,
        evidence.missing_intervention_types,
    )
    evaluation_capabilities = _format_capability_types(
        evidence.evaluation_types,
        evidence.missing_evaluation_types,
    )
    e001_execution_capabilities = _format_capability_types(
        evidence.e001_execution_symbols,
        evidence.missing_e001_execution_symbols,
    )
    return (
        NextWorkItem(
            title="Establish held-out predictive validity from observations",
            evidence=(
                "live production-definition scan: observation artifacts "
                f"{observation_capabilities}; "
                f"research_contract_present={evidence.research_contract_present}; "
                f"sourced_scenario_packs={evidence.sourced_pack_count} are resolver "
                "inputs, not calibration/evaluation splits or held-out proof"
            ),
            path="RESEARCH.md",
        ),
        NextWorkItem(
            title="Build E001 temporal and intervention substrate",
            evidence=(
                "live source and experiment scan: "
                f"e001_spec_present={evidence.e001_spec_present}; temporal artifacts "
                f"{temporal_capabilities}; "
                "intervention artifacts "
                f"{intervention_capabilities}; "
                f"E001 execution {e001_execution_capabilities}; "
                f"machine-readable experiment results={evidence.experiment_result_artifact_count}"
            ),
            path="experiments/e001-beyond-one-datacenter/experiment.md",
        ),
        NextWorkItem(
            title="Make the causal observatory consume experiment evidence",
            evidence=(
                "live deployable-artifact scan: "
                f"registry_cone_present={evidence.registry_cone_present}; "
                "causal-observatory markers="
                f"{len(evidence.causal_observatory_markers)}/5 "
                f"({', '.join(evidence.causal_observatory_markers) or 'none'}); "
                f"evaluation artifacts "
                f"{evaluation_capabilities}; "
                "the UI cannot honestly render residuals, uncertainty, or "
                "counterfactual interventions before those artifacts exist"
            ),
            path="docs",
        ),
    )


def _best_implementations(evidence: _Evidence) -> tuple[NextWorkItem, ...]:
    """Report current foundations worth preserving during the research reset."""

    pythia = evidence.pythia_report
    dense = evidence.dense_cost_result
    return (
        NextWorkItem(
            title="Symbolic registry remains a coherent causal backbone",
            evidence=(
                "live Registry.stats(): "
                f"{evidence.stats['variables']} variables, "
                f"{evidence.stats['equations']} equations, "
                f"{evidence.stats['root_inputs']} root inputs; "
                f"topological_order_length={evidence.topological_order_length}, "
                f"cycles={evidence.cycle_count}, "
                f"hard_failures={evidence.hard_failure_count}. "
                "live Registry.coverage(): "
                f"non_constant_variables={evidence.coverage['non_constant_variables']}, "
                f"sp_units={evidence.coverage['with_sp_units']}, "
                f"references={evidence.coverage['with_references']}; "
                f"large_project_files={len(evidence.large_project_files)} "
                f"({_format_large_files(evidence.large_project_files)})"
            ),
            command="python -m gpu_stack.cli audit --fail-on-issues",
        ),
        NextWorkItem(
            title="Six frontier programs are preregistered",
            evidence=(
                "live repository scan: "
                f"research_contract_present={evidence.research_contract_present}, "
                f"experiment_specs={evidence.experiment_spec_count}, "
                f"e001_spec_present={evidence.e001_spec_present}; the machine "
                "protocol catalog freezes scalar falsifiers and mandatory structured "
                "requirements without pretending a designed experiment has results"
            ),
            path="experiments/README.md",
        ),
        NextWorkItem(
            title="Scenario reports preserve sourced boundary evidence",
            evidence=(
                "live scenario audit: Pythia resolves "
                f"{getattr(pythia, 'ok_count', 0)} of "
                f"{getattr(pythia, 'target_count', 0)} advertised targets; "
                f"ok labels={_format_labels(getattr(pythia, 'ok_target_labels', ()))}. "
                "This is useful calibration input and provenance, not a held-out "
                "accuracy result"
            ),
            path="gpu_stack/presets/scenarios.py",
        ),
        NextWorkItem(
            title="Resolver traces can seed residual attribution",
            evidence=(
                "live resolver result: dense_training_cost_fixture "
                f"missing={len(getattr(dense, 'missing', ()))}, "
                f"violated_constraints={len(getattr(dense, 'violated_constraints', ()))}, "
                f"trace_steps={len(getattr(dense, 'trace', ()))}; "
                f"registry_cone_present={evidence.registry_cone_present}"
            ),
            path="gpu_stack/core",
        ),
    )


def _bug_risks(evidence: _Evidence) -> tuple[NextWorkItem, ...]:
    """Return ten active risks, omitting metadata categories whose gap is zero."""

    candidates: list[NextWorkItem] = []

    if (
        evidence.e001_v1_protocol_hash_matches_persisted is False
        or evidence.e001_v1_engine_hash_matches_persisted is False
    ):
        candidates.append(
            NextWorkItem(
                title="Persisted E001 v1 identity drifted from its frozen source",
                evidence=(
                    "live v1 identity check: protocol_hash_match="
                    f"{evidence.e001_v1_protocol_hash_matches_persisted}, "
                    "engine_source_hash_match="
                    f"{evidence.e001_v1_engine_hash_matches_persisted}; a v1 artifact "
                    "must not be regenerated under the separate recovery-v2 protocol"
                ),
                path="gpu_stack/research/e001.py",
            )
        )
    temporal_capabilities = _format_capability_types(
        evidence.temporal_types,
        evidence.missing_temporal_types,
    )
    intervention_capabilities = _format_capability_types(
        evidence.intervention_types,
        evidence.missing_intervention_types,
    )
    evaluation_capabilities = _format_capability_types(
        evidence.evaluation_types,
        evidence.missing_evaluation_types,
    )
    e001_execution_capabilities = _format_capability_types(
        evidence.e001_execution_symbols,
        evidence.missing_e001_execution_symbols,
    )

    if "Observation" in evidence.missing_observation_types:
        candidates.append(
            NextWorkItem(
                title="Measured observations cannot enter as typed evidence",
                evidence=(
                    "live production-definition scan: Observation is absent; presets and "
                    "assignments cannot encode timestamp, instrumentation uncertainty, "
                    "topology, workload, software, and provenance as measured evidence"
                ),
                path="RESEARCH.md",
            )
        )

    split_gaps = tuple(
        name
        for name in ("CalibrationSplit", "EvaluationSplit")
        if name in evidence.missing_observation_types
    )
    if split_gaps:
        candidates.append(
            NextWorkItem(
                title="Calibration and evaluation have no hard split boundary",
                evidence=(
                    "live production-definition scan: missing="
                    f"{', '.join(split_gaps)}; a scenario used to tune the engine can "
                    "still be mistaken for evidence that the engine transfers"
                ),
                path="RESEARCH.md",
            )
        )

    if evidence.missing_temporal_types:
        candidates.append(
            NextWorkItem(
                title="E001 temporal event and visible-state substrate is incomplete",
                evidence=(
                    "live production-definition scan: temporal "
                    f"{temporal_capabilities}; "
                    "static equations cannot represent compute, collectives, WAN "
                    "contention, migration, power interruptions, or recovery order"
                ),
                path="experiments/e001-beyond-one-datacenter/experiment.md",
            )
        )

    if evidence.missing_intervention_types:
        candidates.append(
            NextWorkItem(
                title="Policies lack an observation-only intervention boundary",
                evidence=(
                    "live production-definition scan: intervention "
                    f"{intervention_capabilities}; "
                    "a future controller could accidentally read hidden simulator truth "
                    "or evade decision-regret accounting"
                ),
                path="RESEARCH.md",
            )
        )

    if evidence.missing_evaluation_types:
        candidates.append(
            NextWorkItem(
                title="Held-out evaluation and residual contract is incomplete",
                evidence=(
                    "live production-definition scan: evaluation "
                    f"{evaluation_capabilities}; "
                    "a resolved number is not yet an evaluated prediction"
                ),
                path="RESEARCH.md",
            )
        )

    if evidence.missing_e001_execution_symbols:
        candidates.append(
            NextWorkItem(
                title="E001 virtual screening runner is incomplete",
                evidence=(
                    "live production-definition scan: E001 execution "
                    f"{e001_execution_capabilities}; the preregistered comparison "
                    "cannot yet produce a reproducible screening artifact"
                ),
                path="gpu_stack/research",
            )
        )

    if evidence.e001_spec_present and evidence.experiment_result_artifact_count == 0:
        candidates.append(
            NextWorkItem(
                title="E001 is designed but has no persisted result artifact",
                evidence=(
                    "live experiment scan: e001_spec_present=True and "
                    "machine-readable result artifacts=0; no residual, uncertainty "
                    "coverage, falsification status, or policy regret can be reproduced"
                ),
                path="experiments/e001-beyond-one-datacenter",
            )
        )

    if evidence.e001_spec_present:
        candidates.extend(
            (
                NextWorkItem(
                    title="Public-trace replay can be mistaken for cluster validity",
                    evidence=(
                        "live experiment scan: machine-readable result artifacts="
                        f"{evidence.experiment_result_artifact_count}; "
                        "E001 validation-ladder stage 1 requires a reproducible replay "
                        "but only controlled real runs can support a convergence claim"
                    ),
                    path="experiments/e001-beyond-one-datacenter/experiment.md",
                ),
                NextWorkItem(
                    title="Learning-delay surrogate transfer is the critical falsifier",
                    evidence=(
                        "live experiment scan: machine-readable result artifacts="
                        f"{evidence.experiment_result_artifact_count}; "
                        "E001 explicitly falsifies the hypothesis when surrogate "
                        "convergence fails to transfer to held-out real runs"
                    ),
                    path="experiments/e001-beyond-one-datacenter/experiment.md",
                ),
                NextWorkItem(
                    title="Shadow comparison must precede controlled scale claims",
                    evidence=(
                        "live experiment scan: machine-readable result artifacts="
                        f"{evidence.experiment_result_artifact_count}; "
                        "the preregistered ladder requires shadow-mode comparison on "
                        "at least three real clusters before controlled scale-up"
                    ),
                    path="experiments/e001-beyond-one-datacenter/experiment.md",
                ),
                NextWorkItem(
                    title="Oracle policy regret needs a preregistered scalar objective",
                    evidence=(
                        "live experiment scan: machine-readable result artifacts="
                        f"{evidence.experiment_result_artifact_count}; "
                        "E001 names an oracle with future power and failure traces, "
                        "but recovery v2 cannot report regret until objective units, "
                        "horizon, normalization, ties, and oracle actions are frozen"
                    ),
                    path=(
                        "experiments/e001-beyond-one-datacenter/"
                        "recovery-mechanics-v2.md"
                    ),
                ),
            )
        )

    if evidence.unresolved_requirement_result_count:
        candidates.append(
            NextWorkItem(
                title="Mandatory structured evidence gates remain unresolved",
                evidence=(
                    "live persisted-artifact scan: structured requirement results="
                    f"{evidence.structured_requirement_result_count}, unresolved="
                    f"{evidence.unresolved_requirement_result_count}; vector, "
                    "transfer, causal, accounting, and panel gates block survival "
                    "even when one scalar threshold passes"
                ),
                path="experiments/e001-beyond-one-datacenter/experiment.md",
            )
        )

    if (
        evidence.experiment_result_artifact_count
        and "run_e001_recovery_v2" not in evidence.production_symbol_names
    ):
        candidates.append(
            NextWorkItem(
                title="Recovery substrate is not yet an E001 execution path",
                evidence=(
                    "live E001 artifact exists, but no E001 recovery-v2 runner symbol "
                    "exists; recovery mechanics therefore cannot change the result"
                ),
                path="gpu_stack/research/e001_recovery_runner.py",
            )
        )

    if evidence.experiment_result_artifact_count:
        candidates.extend(
            (
                NextWorkItem(
                    title="Modeled link bytes are not measured WAN traffic",
                    evidence=(
                        "recovery v2 separates completed and aborted collectives, "
                        "checkpoint replication, restore, redistribution, and migration, "
                        "but sizes and timing remain scenario constants without measured "
                        "collective stages, retries, congestion, or transfer curves"
                    ),
                    path="gpu_stack/research/e001_recovery_runner.py",
                ),
                NextWorkItem(
                    title="Partial energy accounting can reverse the policy ranking",
                    evidence=(
                        "recovery v2 reports modeled compute plus network energy, but "
                        "checkpoint storage, host, cooling, facility conversion, and "
                        "curtailment-waveform energy remain outside the boundary"
                    ),
                    path="gpu_stack/research/e001_recovery_runner.py",
                ),
            )
        )

    if evidence.e002_spec_present and evidence.e002_result_artifact_count == 0:
        candidates.append(
            NextWorkItem(
                title="E002 has no measured waveform result artifact",
                evidence=(
                    "live program scan: e002_spec_present=True, E002 result "
                    "artifacts=0; spectral, grid-mode, learning-semantics, and "
                    "full-boundary energy claims are designed but unevaluated"
                ),
                path="experiments/e002-power-waveform-shaping/experiment.md",
            )
        )

    if len(evidence.causal_observatory_markers) < 5:
        candidates.append(
            NextWorkItem(
                title="Current visual surface explains equations, not experiments",
                evidence=(
                    "live docs application scan: causal-observatory markers="
                    f"{len(evidence.causal_observatory_markers)}/5 and "
                    f"experiment_results={evidence.experiment_result_artifact_count}; "
                    "the existing registry cone has no evidence-backed event timeline, "
                    "counterfactual, uncertainty, or residual view"
                ),
                path="docs",
            )
        )

    if evidence.sourced_pack_count:
        candidates.append(
            NextWorkItem(
                title="Scenario resolution can be misread as predictive validation",
                evidence=(
                    "live scenario inventory: "
                    f"sourced_pack_count={evidence.sourced_pack_count}; scenario audits "
                    "check resolvability and provenance but do not measure held-out "
                    "prediction error, interval coverage, ranking regret, or transfer"
                ),
                path="gpu_stack/presets/scenarios.py",
            )
        )

    candidates.append(
        NextWorkItem(
            title="Synthetic dense fixtures cannot validate real-cluster predictions",
            evidence=(
                "live resolver fixture: dense_training_cost_fixture remains an explicit "
                "composition/regression anchor; its successful trace is internal "
                "consistency evidence, not an external observation"
            ),
            path="gpu_stack/presets/scenarios.py",
        )
    )

    # Metadata categories participate only while their measured gap is nonzero.
    # This prevents a fully covered category from being presented as an active bug.
    metadata_risks = (
        (
            evidence.missing_variable_units,
            "Variable unit metadata has an active gap",
            "non-constant variables lack sp_units",
        ),
        (
            evidence.missing_variable_references,
            "Variable provenance metadata has an active gap",
            "non-constant variables lack references",
        ),
        (
            evidence.missing_equation_references,
            "Equation provenance metadata has an active gap",
            "equations lack references",
        ),
        (
            evidence.missing_equation_unit_checks,
            "Equation unit checking has an active gap",
            "equations lack unit checks",
        ),
    )
    for gap, title, description in metadata_risks:
        if gap <= 0:
            continue
        candidates.append(
            NextWorkItem(
                title=title,
                evidence=f"live Registry.coverage(): gap={gap}; {description}",
                path="gpu_stack/scopes",
            )
        )

    if evidence.multi_definition_count:
        candidates.append(
            NextWorkItem(
                title="Variant-sensitive variables can invalidate comparisons",
                evidence=(
                    "live registry introspection: "
                    f"multi_definition_variables={evidence.multi_definition_count}; "
                    "held-out runs must freeze variant selectors across every baseline"
                ),
                path="gpu_stack/core",
            )
        )

    if evidence.large_project_files:
        candidates.append(
            NextWorkItem(
                title="Large Python files remain an active maintenance risk",
                evidence=(
                    "live project scan at 700-line threshold: "
                    f"large_project_files={len(evidence.large_project_files)}; "
                    f"{_format_large_files(evidence.large_project_files)}"
                ),
                command="python -m gpu_stack.cli audit --details",
            )
        )

    if evidence.hard_failure_count:
        candidates.append(
            NextWorkItem(
                title="Graph integrity failures invalidate downstream research",
                evidence=(
                    "live graph audit: "
                    f"hard_failures={evidence.hard_failure_count}, "
                    f"cycles={evidence.cycle_count}, "
                    f"topological_order_length={evidence.topological_order_length}"
                ),
                command="python -m gpu_stack.cli audit --fail-on-issues",
            )
        )

    if len(candidates) < 10:
        raise RuntimeError(
            "next-work research risk inventory produced fewer than 10 active risks"
        )
    return tuple(candidates[:10])


def _legacy_diagnostics(evidence: _Evidence) -> tuple[NextWorkItem, ...]:
    """Keep structural debt visible without ranking it as scientific impact."""

    cost_target = evidence.pythia_cost_target
    top_family = evidence.root_debt_families[0]
    top_families = evidence.root_debt_families[:3]
    return (
        NextWorkItem(
            title="Close the sourced Pythia cost frontier",
            evidence=(
                "classification=legacy scenario diagnostic; live scenario audit: "
                "pythia_70m_dgx_h100_us_2024_industrial_power "
                f"cost_per_token has {getattr(cost_target, 'missing_count', 0)} "
                f"missing inputs; {_missing_family_summary(cost_target)}"
            ),
            command=(
                "python -m gpu_stack.cli scenario-audit --preset "
                "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power "
                "--target cost_per_token=econ.cost.per_token --missing-families"
            ),
            path="gpu_stack/presets/scenarios.py",
        ),
        NextWorkItem(
            title="Pay down the heaviest root-debt family",
            evidence=(
                "classification=legacy structural diagnostic; live root-debt scan: "
                f"Registry.roots()={evidence.stats['root_inputs']}; "
                f"top family {top_family.family} has "
                f"total_weight={top_family.total_weight} across "
                f"{top_family.root_count} roots; top roots "
                f"{_format_roots(top_family.roots)}; top families "
                f"{_format_families(top_families)}. Promote only when tied to an "
                "observed residual, uncertainty contribution, or experiment dependency"
            ),
            command="python -m gpu_stack.cli root-debt --families --limit 10",
        ),
    )
