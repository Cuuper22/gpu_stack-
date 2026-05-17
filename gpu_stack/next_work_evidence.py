"""Live evidence collection for next-work reports."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import gpu_stack
import sympy as sp

from . import Registry
from .core.resolver import _boundary_family
from .presets import scenarios


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
