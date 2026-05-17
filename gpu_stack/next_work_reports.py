"""Next-work report item builders."""

from __future__ import annotations

from .next_work_evidence import _Evidence
from .next_work_models import NextWorkItem
from .next_work_rendering import (
    _format_families,
    _format_labels,
    _format_large_files,
    _format_roots,
    _missing_family_summary,
)


def _highest_impact(evidence: _Evidence) -> tuple[NextWorkItem, ...]:
    top_family = evidence.root_debt_families[0]
    cost_target = evidence.pythia_cost_target
    cost_missing = getattr(cost_target, "missing_count", 0)
    family_summary = _missing_family_summary(cost_target)
    return (
        NextWorkItem(
            title="Close the sourced Pythia cost frontier",
            evidence=(
                "live scenario audit: "
                "pythia_70m_dgx_h100_us_2024_industrial_power "
                f"cost_per_token has {cost_missing} missing inputs; "
                f"{family_summary}"
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
                "live root-debt scan: "
                f"Registry.roots()={evidence.stats['root_inputs']}; "
                f"top family {top_family.family} has "
                f"total_weight={top_family.total_weight} across "
                f"{top_family.root_count} roots; top roots "
                f"{_format_roots(top_family.roots)}"
            ),
            command="python -m gpu_stack.cli root-debt --families --limit 10",
        ),
        NextWorkItem(
            title="Finish metadata coverage before widening scenarios",
            evidence=(
                "live Registry.coverage(): "
                f"{evidence.missing_variable_units} variables lack sp_units, "
                f"{evidence.missing_variable_references} variables lack references, "
                f"{evidence.missing_equation_references} equations lack references, "
                f"{evidence.missing_equation_unit_checks} equations lack unit checks"
            ),
            command="python -m gpu_stack.cli audit --details",
            path="gpu_stack/scopes",
        ),
    )


def _best_implementations(evidence: _Evidence) -> tuple[NextWorkItem, ...]:
    pythia = evidence.pythia_report
    euv = evidence.euv_report
    dense = evidence.dense_cost_result
    return (
        NextWorkItem(
            title="Registry import graph is currently coherent",
            evidence=(
                "live Registry.stats(): "
                f"{evidence.stats['variables']} variables, "
                f"{evidence.stats['equations']} equations, "
                f"{evidence.stats['root_inputs']} root inputs; "
                f"topological_order_length={evidence.topological_order_length}, "
                f"cycles={evidence.cycle_count}, "
                f"hard_failures={evidence.hard_failure_count}"
            ),
            command="python -m gpu_stack.cli audit --fail-on-issues",
        ),
        NextWorkItem(
            title="Pythia sourced pack resolves the non-cost targets",
            evidence=(
                "live scenario audit: "
                f"{getattr(pythia, 'ok_count', 0)} of "
                f"{getattr(pythia, 'target_count', 0)} advertised targets are ok; "
                f"ok labels={_format_labels(getattr(pythia, 'ok_target_labels', ()))}"
            ),
            path="gpu_stack/presets/scenarios.py",
        ),
        NextWorkItem(
            title="EUV tin120 assumption pack is cleanly bounded",
            evidence=(
                "live scenario audit: "
                "euv_tin120_lpp_source_context_assumption "
                f"status={getattr(euv, 'status', 'missing')} with "
                f"{getattr(euv, 'ok_count', 0)} of "
                f"{getattr(euv, 'target_count', 0)} targets ok"
            ),
            path="gpu_stack/presets/scenarios.py",
        ),
        NextWorkItem(
            title="Dense cost fixture still exercises the full rollup",
            evidence=(
                "live resolver result: dense_training_cost_fixture "
                f"cost_per_token missing={len(getattr(dense, 'missing', ()))}, "
                "violated_constraints="
                f"{len(getattr(dense, 'violated_constraints', ()))}, "
                f"trace_steps={len(getattr(dense, 'trace', ()))}"
            ),
            command=(
                "python -m pytest tests/test_scenarios.py::"
                "test_dense_training_cost_fixture_resolves_user_facing_targets"
            ),
        ),
    )


def _bug_risks(evidence: _Evidence) -> tuple[NextWorkItem, ...]:
    cost_target = evidence.pythia_cost_target
    top_families = evidence.root_debt_families[:3]
    return (
        NextWorkItem(
            title="Pythia cost-per-token is not a sourced answer yet",
            evidence=(
                "live scenario audit: "
                f"cost_per_token status={getattr(cost_target, 'status', 'missing')} "
                f"and missing_count={getattr(cost_target, 'missing_count', 0)}"
            ),
            command=(
                "python -m gpu_stack.cli scenario-report "
                "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power "
                "--target cost_per_token=econ.cost.per_token "
                "--details --missing-families"
            ),
        ),
        NextWorkItem(
            title="Scenario missing families mix primitive roots and symbolic boundaries",
            evidence=(
                "live missing-family summary for Pythia cost_per_token: "
                f"{_missing_family_summary(cost_target, limit=5)}"
            ),
            path="gpu_stack/core/presets.py",
        ),
        NextWorkItem(
            title="Root-debt concentration can hide progress outside physical lithography",
            evidence=(
                "live top root-debt families: "
                f"{_format_families(top_families)}"
            ),
            command="python -m gpu_stack.cli root-debt --families --limit 3",
        ),
        NextWorkItem(
            title="Large Python files are beyond the audit threshold",
            evidence=(
                "live project scan at 700-line threshold: "
                f"large_project_files={len(evidence.large_project_files)}; "
                f"{_format_large_files(evidence.large_project_files)}"
            ),
            command="python -m gpu_stack.cli audit --details",
        ),
        NextWorkItem(
            title="Variable unit metadata still has holes",
            evidence=(
                "live Registry.coverage(): "
                f"{evidence.coverage['with_sp_units']} of "
                f"{evidence.coverage['non_constant_variables']} "
                f"non-constant variables have sp_units; "
                f"gap={evidence.missing_variable_units}"
            ),
            path="gpu_stack/scopes",
        ),
        NextWorkItem(
            title="Variable reference metadata is not complete",
            evidence=(
                "live Registry.coverage(): "
                f"{evidence.coverage['with_references']} of "
                f"{evidence.coverage['non_constant_variables']} "
                f"non-constant variables have references; "
                f"gap={evidence.missing_variable_references}"
            ),
            path="gpu_stack/scopes",
        ),
        NextWorkItem(
            title="Equation provenance still trails equation count",
            evidence=(
                "live Registry.coverage(): "
                f"{evidence.coverage['equations_with_references']} of "
                f"{evidence.coverage['equations']} equations have references; "
                f"gap={evidence.missing_equation_references}"
            ),
            path="gpu_stack/scopes",
        ),
        NextWorkItem(
            title="Unit-check coverage is not yet universal",
            evidence=(
                "live Registry.coverage(): "
                f"{evidence.coverage['equations_with_unit_check']} of "
                f"{evidence.coverage['equations']} equations have unit checks; "
                f"gap={evidence.missing_equation_unit_checks}"
            ),
            path="gpu_stack/scopes",
        ),
        NextWorkItem(
            title="Multi-definition variables depend on stable variant discipline",
            evidence=(
                "live registry introspection: "
                f"multi_definition_variables={evidence.multi_definition_count}; "
                "resolver calls need explicit variant selectors where applicable"
            ),
            command="python -m gpu_stack.cli audit --details",
        ),
        NextWorkItem(
            title="Sourced scenario inventory is still narrow",
            evidence=(
                "live scenarios.SOURCED_SCENARIO_PACKS: "
                f"pack_count={evidence.sourced_pack_count}; "
                "only advertised sourced packs are scenario-audited here"
            ),
            path="gpu_stack/presets/scenarios.py",
        ),
    )
