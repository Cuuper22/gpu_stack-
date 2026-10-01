"""Cross-layer tests for physical boundary-hardening constraints.

A boundary-hardening constraint is an inequality that fences a primitive root
into its physically meaningful range (for example, numerical aperture cannot
exceed the medium index). The same constraint must be visible from three angles at once: as
a CONSTRAINT-role inequality in the registry graph, as extra dependent weight
in the root-debt ranking when ``--include-constraints`` is passed, and as a
relation that passes the audit's equation invariants. These tests check all
three views agree, and that derived variables with constraints never
masquerade as root debt.
"""

from __future__ import annotations

import contextlib
import io
import json
from dataclasses import dataclass

import sympy as sp

from gpu_stack import Registry
from gpu_stack.cli import main
from gpu_stack.core import Inequality, RelationRole


@dataclass(frozen=True)
class PhysicalBoundaryFixture:
    equation: str
    variable: str
    family: str
    constraint_dependencies: frozenset[str] = frozenset()
    primitive_root: bool = True


PHYSICAL_BOUNDARY_FIXTURES = (
    PhysicalBoundaryFixture(
        equation=(
            "physical.ineq."
            "lithography_numerical_aperture_within_medium_index"
        ),
        variable="physical.lithography.numerical_aperture",
        family="physical.lithography",
        constraint_dependencies=frozenset(
            {
                "physical.lithography.medium_refractive_index",
            }
        ),
    ),
)


DERIVED_PHYSICAL_BOUNDARIES = (
    (
        "physical.process.drawn_gate_length",
        "physical.ineq.drawn_gate_length_positive",
    ),
)


def _run_cli_json(*args: str) -> dict[str, object]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main([*args, "--json"])
    assert rc == 0
    return json.loads(buf.getvalue())


def _root_debt_rows(*args: str) -> dict[str, dict[str, object]]:
    payload = _run_cli_json("root-debt", "--scope", "physical", "--limit", "1000", *args)
    return {str(row["variable"]): row for row in payload["rows"]}


def test_physical_boundary_hardening_constraints_are_graph_constraints():
    for fixture in PHYSICAL_BOUNDARY_FIXTURES:
        variable = Registry.variables[fixture.variable]
        equation = Registry.equations[fixture.equation]

        assert isinstance(equation, Inequality)
        assert equation.role is RelationRole.CONSTRAINT
        assert equation in variable.constraints()
        assert isinstance(equation.as_sympy(), sp.Rel)
        assert equation.as_sympy() not in (sp.S.true, sp.S.false)
        assert not equation.is_trivially_false()
        assert equation.references

        if fixture.primitive_root:
            assert variable.is_root_input
            assert variable.direct_dependencies() == set()

        constraint_dependencies = {
            dependency.name
            for dependency in variable.direct_dependencies(include_constraints=True)
        }
        assert fixture.constraint_dependencies <= constraint_dependencies
        if fixture.constraint_dependencies:
            assert getattr(equation, "_check_units_flag", False)
            assert not equation.is_trivially_true()


def test_physical_boundary_hardening_is_visible_in_root_debt_rows():
    default_rows = _root_debt_rows()
    constraint_rows = _root_debt_rows("--include-constraints")

    for fixture in PHYSICAL_BOUNDARY_FIXTURES:
        variable = Registry.variables[fixture.variable]

        assert fixture.variable in default_rows
        assert fixture.variable in constraint_rows

        row = constraint_rows[fixture.variable]
        assert row["scope"] == "physical"
        assert row["family"] == fixture.family
        assert row["boundary_category"] == "primitive-root"
        assert row["primitive_boundary"] is True
        assert row["dependents"] == len(variable.dependents(include_constraints=True))
        assert row["dependents"] >= default_rows[fixture.variable]["dependents"]


def test_derived_physical_boundaries_do_not_reappear_as_root_debt():
    root_rows = _root_debt_rows("--include-constraints")

    for variable_name, constraint_name in DERIVED_PHYSICAL_BOUNDARIES:
        variable = Registry.variables[variable_name]
        constraint = Registry.equations[constraint_name]

        assert not variable.is_root_input
        assert constraint in variable.constraints()
        assert variable.defining_equations
        assert variable_name not in root_rows


def test_physical_boundary_hardening_passes_audit_style_invariants():
    for fixture in PHYSICAL_BOUNDARY_FIXTURES:
        equation = Registry.equations[fixture.equation]

        assert equation.as_sympy() not in (sp.S.true, sp.S.false)
        assert equation.raw_dependency_symbols() == set()
        assert equation.lhs_variable() is Registry.variables[fixture.variable]

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(["audit", "--fail-on-issues"])

    assert rc == 0
    assert "hard_failures                   0" in buf.getvalue()
