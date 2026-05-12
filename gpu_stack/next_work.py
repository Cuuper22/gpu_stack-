"""
Live next-work planning from the current registry and preset evidence.

This module intentionally builds its output at call time. The registry, preset
inventory, scenario targets, and source files are moving quickly, so a static
snapshot would go stale almost immediately.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import gpu_stack
import sympy as sp
from . import Registry
from .core.resolver import _boundary_family
from .presets import scenarios


@dataclass(frozen=True)
class NextWorkItem:
    """One actionable next-work item backed by concrete current evidence."""

    title: str
    evidence: str
    command: str | None = None
    path: str | None = None

    def to_dict(self) -> dict[str, str]:
        data = {
            "title": self.title,
            "evidence": self.evidence,
        }
        if self.command is not None:
            data["command"] = self.command
        if self.path is not None:
            data["path"] = self.path
        return data


@dataclass(frozen=True)
class NextWorkPlan:
    """Exactly three top-level next-work lists."""

    highest_impact: tuple[NextWorkItem, ...]
    best_implementations: tuple[NextWorkItem, ...]
    bug_risks: tuple[NextWorkItem, ...]
    graph_evidence: Mapping[str, int]

    @property
    def implementation(self) -> tuple[NextWorkItem, ...]:
        """Compatibility alias for continuation-contract callers."""
        return self.best_implementations

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        return {
            "highest_impact": [item.to_dict() for item in self.highest_impact],
            "best_implementations": [
                item.to_dict() for item in self.best_implementations
            ],
            "bug_risks": [item.to_dict() for item in self.bug_risks],
        }


@dataclass(frozen=True)
class _RootDebtRow:
    dependents: int
    name: str
    units: str
    scope: str
    family: str


@dataclass(frozen=True)
class _RootDebtFamily:
    total_weight: int
    root_count: int
    family: str
    roots: tuple[_RootDebtRow, ...]


@dataclass(frozen=True)
class _Evidence:
    stats: Mapping[str, int]
    coverage: Mapping[str, int]
    topological_order_length: int
    cycle_count: int
    root_debt_families: tuple[_RootDebtFamily, ...]
    pythia_report: object | None
    pythia_cost_target: object | None
    euv_report: object | None
    dense_cost_result: object | None
    sourced_pack_count: int
    large_project_files: tuple[tuple[str, int], ...]
    multi_definition_count: int
    collapsed_equation_count: int
    raw_symbol_count: int
    orphan_value_equation_count: int

    @property
    def missing_variable_units(self) -> int:
        return self.coverage["non_constant_variables"] - self.coverage["with_sp_units"]

    @property
    def missing_variable_references(self) -> int:
        return (
            self.coverage["non_constant_variables"]
            - self.coverage["with_references"]
        )

    @property
    def missing_equation_references(self) -> int:
        return self.coverage["equations"] - self.coverage["equations_with_references"]

    @property
    def missing_equation_unit_checks(self) -> int:
        return self.coverage["equations"] - self.coverage["equations_with_unit_check"]

    @property
    def hard_failure_count(self) -> int:
        topo_failure = self.topological_order_length != self.stats["variables"]
        return (
            self.cycle_count
            + self.collapsed_equation_count
            + self.raw_symbol_count
            + self.orphan_value_equation_count
            + int(topo_failure)
        )


def build_next_work_plan(repo_root: Path | None = None) -> NextWorkPlan:
    """
    Build a live next-work plan from the currently imported registry.

    The returned plan has exactly three top-level lists:
    ``highest_impact`` with 3 items, ``best_implementations`` with 4 items,
    and ``bug_risks`` with 10 items.
    """

    evidence = _collect_evidence(repo_root)
    return NextWorkPlan(
        highest_impact=_highest_impact(evidence),
        best_implementations=_best_implementations(evidence),
        bug_risks=_bug_risks(evidence),
        graph_evidence={
            "variables": evidence.stats["variables"],
            "equations": evidence.stats["equations"],
            "root_inputs": evidence.stats["root_inputs"],
        },
    )


def _collect_evidence(repo_root: Path | None) -> _Evidence:
    stats = Registry.stats()
    coverage = Registry.coverage()
    try:
        topological_order_length = len(gpu_stack.topological_sort())
    except RuntimeError:
        topological_order_length = 0

    reports = {
        pack.name: pack.evaluate_targets(scenarios.scenario_targets_for(pack))
        for pack in scenarios.SOURCED_SCENARIO_PACKS
    }
    pythia_name = "pythia_70m_dgx_h100_us_2024_industrial_power"
    euv_name = "euv_tin120_lpp_source_context_assumption"
    pythia_report = reports.get(pythia_name)
    pythia_cost_target = _target_by_label(pythia_report, "cost_per_token")
    dense_cost_result = scenarios.dense_training_cost_fixture.resolve(
        scenarios.COST_PER_TOKEN_TARGET
    )

    return _Evidence(
        stats=stats,
        coverage=coverage,
        topological_order_length=topological_order_length,
        cycle_count=len(gpu_stack.find_cycles()),
        root_debt_families=_root_debt_families(),
        pythia_report=pythia_report,
        pythia_cost_target=pythia_cost_target,
        euv_report=reports.get(euv_name),
        dense_cost_result=dense_cost_result,
        sourced_pack_count=len(tuple(scenarios.SOURCED_SCENARIO_PACKS)),
        large_project_files=_large_project_files(repo_root=repo_root),
        multi_definition_count=sum(
            1 for variable in Registry.variables.values()
            if variable.has_multiple_definitions()
        ),
        collapsed_equation_count=sum(
            1 for equation in Registry.equations.values()
            if equation.as_sympy() in (sp.S.true, sp.S.false)
        ),
        raw_symbol_count=sum(
            1 for equation in Registry.equations.values()
            if equation.raw_dependency_symbols()
        ),
        orphan_value_equation_count=sum(
            1 for equation in Registry.equations.values()
            if equation.role is not gpu_stack.RelationRole.CONSTRAINT
            and equation.lhs_variable() is None
        ),
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


def _target_by_label(report: object | None, label: str) -> object | None:
    if report is None:
        return None
    for target in getattr(report, "targets", ()):
        if getattr(target, "label", None) == label:
            return target
    return None


def _root_debt_families() -> tuple[_RootDebtFamily, ...]:
    rows = tuple(
        sorted(
            (
                _RootDebtRow(
                    dependents=len(root.dependents()),
                    name=root.name,
                    units=root.units,
                    scope=root.scope,
                    family=_boundary_family(root),
                )
                for root in Registry.roots()
            ),
            key=lambda row: (-row.dependents, row.name),
        )
    )
    grouped: dict[str, list[_RootDebtRow]] = defaultdict(list)
    for row in rows:
        grouped[row.family].append(row)

    families = [
        _RootDebtFamily(
            total_weight=sum(row.dependents for row in family_rows),
            root_count=len(family_rows),
            family=family,
            roots=tuple(sorted(family_rows, key=lambda row: (-row.dependents, row.name))),
        )
        for family, family_rows in grouped.items()
    ]
    return tuple(
        sorted(
            families,
            key=lambda family: (
                -family.total_weight,
                -family.root_count,
                family.family,
            ),
        )
    )


def _large_project_files(
    repo_root: Path | None = None,
    threshold: int = 700,
) -> tuple[tuple[str, int], ...]:
    root = repo_root or Path(gpu_stack.__file__).resolve().parent.parent
    roots = (Path(gpu_stack.__file__).resolve().parent, root / "tests")
    out: list[tuple[str, int]] = []
    for scan_root in roots:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_count >= threshold:
                out.append((path.relative_to(root).as_posix(), line_count))
    return tuple(out)


def _missing_family_summary(target: object | None, limit: int = 4) -> str:
    if target is None:
        return "no target report found"
    summaries = tuple(getattr(target, "missing_family_summaries", ()))
    if not summaries:
        return "missing families: none"
    parts = [
        (
            f"{summary.family} {summary.boundary_category} "
            f"primitive={summary.primitive_boundary} count={summary.count}"
        )
        for summary in summaries[:limit]
    ]
    remaining = len(summaries) - len(parts)
    if remaining > 0:
        parts.append(f"{remaining} more families")
    return "missing families: " + "; ".join(parts)


def _format_roots(roots: Iterable[_RootDebtRow], limit: int = 4) -> str:
    selected = tuple(roots)[:limit]
    return ", ".join(f"{root.name}:{root.dependents}" for root in selected)


def _format_families(families: Iterable[_RootDebtFamily]) -> str:
    return "; ".join(
        f"{family.family} weight={family.total_weight} roots={family.root_count}"
        for family in families
    )


def _format_labels(labels: Iterable[str]) -> str:
    selected = tuple(labels)
    return ", ".join(selected) if selected else "none"


def _format_large_files(files: Iterable[tuple[str, int]], limit: int = 4) -> str:
    all_files = tuple(files)
    selected = all_files[:limit]
    if not selected:
        return "none"
    rendered = ", ".join(f"{path}:{lines}" for path, lines in selected)
    remaining = len(all_files) - len(selected)
    if remaining > 0:
        rendered = f"{rendered}, {remaining} more"
    return rendered


__all__ = [
    "NextWorkItem",
    "NextWorkPlan",
    "build_next_work_plan",
]
