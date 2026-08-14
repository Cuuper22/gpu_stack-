"""Boundary tests for process geometry dimensions.

Process dimensions — gate length, metal pitch, contact spacing, and so on —
are normally derived by the graph. But a scenario may pin any one of them
directly, treating it as a known boundary value. When the pinned value is
physically impossible (a zero-length gate, a negative spacing), the resolver
must not crash and must not invent new equations. It should report the one
existing feasibility constraint for that dimension, exactly once.

These tests cover both sides: each dimension's constraint is registered a
single time in the graph, and each invalid assignment produces exactly one
violation diagnostic naming the right constraint with the offending value.
"""

import pytest

from gpu_stack import Registry, resolve
from gpu_stack.scopes import physical_process


PROCESS_BOUNDARY_CASES = [
    pytest.param(
        "physical.process.node_length",
        0.0,
        "physical.ineq.process_node_length_positive",
        id="process-node-length",
    ),
    pytest.param(
        "physical.process.drawn_gate_length",
        0.0,
        "physical.ineq.drawn_gate_length_positive",
        id="drawn-gate-length",
    ),
    pytest.param(
        "physical.process.source_drain_contact_width",
        0.0,
        "physical.ineq.source_drain_contact_width_positive",
        id="source-drain-contact-width",
    ),
    pytest.param(
        "physical.process.gate_contact_spacing",
        -1.0,
        "physical.ineq.gate_contact_spacing_nonnegative",
        id="gate-contact-spacing",
    ),
    pytest.param(
        "physical.process.contacted_gate_pitch",
        0.0,
        "physical.ineq.contacted_gate_pitch_positive",
        id="contacted-gate-pitch",
    ),
    pytest.param(
        "physical.process.minimum_metal_width",
        0.0,
        "physical.ineq.minimum_metal_width_positive",
        id="minimum-metal-width",
    ),
    pytest.param(
        "physical.process.minimum_metal_spacing",
        0.0,
        "physical.ineq.minimum_metal_spacing_positive",
        id="minimum-metal-spacing",
    ),
    pytest.param(
        "physical.process.minimum_metal_pitch",
        0.0,
        "physical.ineq.minimum_metal_pitch_positive",
        id="minimum-metal-pitch",
    ),
]


def _violated_constraint(result, equation_name):
    for violation in result.violated_constraints:
        if violation.equation == equation_name:
            return violation
    observed = [violation.equation for violation in result.violated_constraints]
    pytest.fail(f"missing violated constraint {equation_name!r}; saw {observed!r}")


def test_process_boundary_constraints_are_registered_once():
    process_equation_names = [eq.name for eq in physical_process.PROCESS_EQUATIONS]
    assert len(process_equation_names) == len(set(process_equation_names))

    for variable_name, _invalid_value, constraint_name in [
        item.values for item in PROCESS_BOUNDARY_CASES
    ]:
        variable = Registry.variables[variable_name]
        constraint_names = [eq.name for eq in variable.constraints()]
        constraint_shapes = [
            (eq.lhs, getattr(eq, "op", None), eq.rhs)
            for eq in variable.constraints()
        ]

        assert constraint_names.count(constraint_name) == 1
        assert len(constraint_shapes) == len(set(constraint_shapes))
        assert process_equation_names.count(constraint_name) == 1
        assert Registry.equations[constraint_name] in variable.constraints()


@pytest.mark.parametrize(
    ("variable_name", "invalid_value", "constraint_name"),
    PROCESS_BOUNDARY_CASES,
)
def test_invalid_process_boundary_assignments_report_single_diagnostic(
    variable_name,
    invalid_value,
    constraint_name,
):
    result = resolve(variable_name, assignments={variable_name: invalid_value})

    assert float(result.value) == pytest.approx(invalid_value)
    assert result.trace == []
    assert result.missing == set()

    constraint_names = [check.equation for check in result.constraints]
    assert len(constraint_names) == len(set(constraint_names))
    assert constraint_names.count(constraint_name) == 1

    violation_names = [
        violation.equation for violation in result.violated_constraints
    ]
    assert violation_names.count(constraint_name) == 1

    violation = _violated_constraint(result, constraint_name)
    assert violation.variable == variable_name
    assert violation.missing == set()
    assert variable_name in violation.inputs
    assert float(violation.inputs[variable_name]) == pytest.approx(invalid_value)
    assert violation.description
