"""
Constraint and variable-domain resolver coverage.
"""

import pytest
import sympy as sp

from gpu_stack import resolve
from gpu_stack.core import (
    ConstraintCheck,
    Equation,
    Inequality,
    RelationRole,
    var,
)
from gpu_stack.core.variable import Variable
from tests.helpers.registry import registry_snapshot


def test_constraint_helper_uses_selected_variant(registry_snapshot):
    target = Variable(
        "test.constraint_variant.target",
        "target_constraint_variant_test",
        "value",
        "Temporary target with a helper-dependent constraint.",
        scope="test",
    )
    helper = Variable(
        "test.constraint_variant.helper",
        "helper_constraint_variant_test",
        "value",
        "Temporary helper selected through a variant relation.",
        scope="test",
    )
    driver = Variable(
        "test.constraint_variant.driver",
        "driver_constraint_variant_test",
        "value",
        "Temporary assigned driver for the helper variant.",
        scope="test",
    )
    Equation(
        "test.eq.constraint_variant_target",
        target.symbol,
        sp.Integer(1),
        "Temporary target identity.",
    )
    Equation(
        "test.eq.constraint_variant_helper",
        helper.symbol,
        driver.symbol,
        "Temporary helper variant.",
        role=RelationRole.VARIANT,
        variant="selected",
    )
    Equation(
        "test.eq.constraint_variant_helper_too_small",
        helper.symbol,
        sp.Integer(0),
        "Temporary alternate helper variant that would violate the constraint.",
        role=RelationRole.VARIANT,
        variant="too_small",
    )
    Inequality(
        "test.ineq.constraint_variant_target_le_helper",
        target.symbol,
        helper.symbol,
        "<=",
        "Temporary constraint that needs a selected helper variant.",
    )

    result = resolve(
        target.name,
        assignments={driver.name: 2},
        variants={helper.name: "selected"},
    )

    check = next(
        c for c in result.constraints
        if c.equation == "test.ineq.constraint_variant_target_le_helper"
    )
    assert check.satisfied is True
    assert check.missing == set()


def test_resolve_reports_constraint_for_symbolic_boundary_variable(
    registry_snapshot,
):
    target = Variable(
        "test.boundary_constraint.target",
        "target_boundary_constraint_test",
        "value",
        "Temporary target with a symbolic boundary dependency.",
        scope="test",
    )
    boundary = Variable(
        "test.boundary_constraint.boundary",
        "boundary_constraint_test",
        "value",
        "Temporary symbolic boundary variable.",
        scope="test",
    )

    Equation(
        "test.eq.boundary_constraint_target",
        target.symbol,
        boundary.symbol + 1,
        "Temporary target that leaves a symbolic boundary.",
    )
    Inequality(
        "test.ineq.boundary_constraint_nonnegative",
        boundary.symbol,
        0,
        ">=",
        "Temporary constraint attached to a symbolic boundary.",
    )

    result = resolve(target.name)

    assert result.missing == {boundary.name}
    check = next(
        c for c in result.constraints
        if c.equation == "test.ineq.boundary_constraint_nonnegative"
    )
    assert check.satisfied is None
    assert check.missing == {boundary.name}


def test_constraint_helper_extends_values_recursively(registry_snapshot):
    target = Variable(
        "test.constraint_helper_chain.target",
        "target_constraint_helper_chain_test",
        "value",
        "Temporary target with a recursive helper constraint.",
        scope="test",
    )
    helper = Variable(
        "test.constraint_helper_chain.helper",
        "helper_constraint_helper_chain_test",
        "value",
        "Temporary recursive constraint helper.",
        scope="test",
    )
    mid = Variable(
        "test.constraint_helper_chain.mid",
        "mid_constraint_helper_chain_test",
        "value",
        "Temporary middle helper.",
        scope="test",
    )
    driver = Variable(
        "test.constraint_helper_chain.driver",
        "driver_constraint_helper_chain_test",
        "value",
        "Temporary helper-chain driver.",
        scope="test",
    )

    Equation(
        "test.eq.constraint_helper_chain_target",
        target.symbol,
        1,
        "Temporary constant target.",
    )
    Equation(
        "test.eq.constraint_helper_chain_mid",
        mid.symbol,
        driver.symbol + 1,
        "Temporary middle helper definition.",
    )
    Equation(
        "test.eq.constraint_helper_chain_helper",
        helper.symbol,
        mid.symbol + 1,
        "Temporary recursive helper definition.",
    )
    Inequality(
        "test.ineq.constraint_helper_chain_target_le_helper",
        target.symbol,
        helper.symbol,
        "<=",
        "Temporary constraint that needs a recursive helper.",
    )

    result = resolve(target.name, assignments={driver.name: 1})

    check = next(
        c for c in result.constraints
        if c.equation == "test.ineq.constraint_helper_chain_target_le_helper"
    )
    assert check.satisfied is True
    assert check.missing == set()


def test_constraint_helper_recursion_stops_at_unresolved_subtree(
    registry_snapshot,
):
    target = Variable(
        "test.constraint_helper_unresolved.target",
        "target_constraint_helper_unresolved_test",
        "value",
        "Temporary target with an unresolved helper constraint.",
        scope="test",
    )
    helper = Variable(
        "test.constraint_helper_unresolved.helper",
        "helper_constraint_helper_unresolved_test",
        "value",
        "Temporary unresolved constraint helper.",
        scope="test",
    )
    dangling = Variable(
        "test.constraint_helper_unresolved.dangling",
        "dangling_constraint_helper_unresolved_test",
        "value",
        "Temporary unresolved helper dependency.",
        scope="test",
    )

    Equation(
        "test.eq.constraint_helper_unresolved_target",
        target.symbol,
        1,
        "Temporary constant target.",
    )
    Equation(
        "test.eq.constraint_helper_unresolved_helper",
        helper.symbol,
        dangling.symbol + 1,
        "Temporary helper with an unresolved dependency.",
    )
    Inequality(
        "test.ineq.constraint_helper_unresolved_target_le_helper",
        target.symbol,
        helper.symbol,
        "<=",
        "Temporary constraint that should remain symbolic.",
    )

    result = resolve(target.name)

    check = next(
        c for c in result.constraints
        if c.equation == "test.ineq.constraint_helper_unresolved_target_le_helper"
    )
    assert check.satisfied is None
    assert check.missing == {helper.name}


def test_resolve_reports_satisfied_constraints():
    result = resolve(
        "physical.gate.elmore_delay",
        assignments={
            "physical.gate.r_on": 1.0,
            "physical.gate.fanout": 1,
            "physical.gate.c_input": 1.0,
            "physical.interconnect.c_total": 1.0,
            "physical.interconnect.r_per_length": 0.0,
            "physical.interconnect.c_per_length": 1.0,
            "physical.wire_length": 1.0,
            "physical.clock_frequency": 0.1,
        },
    )
    assert result.constraints
    check = next(
        c for c in result.constraints
        if c.equation == "physical.eq.clock_timing_constraint"
    )
    assert isinstance(check, ConstraintCheck)
    assert check.satisfied is True


def test_resolve_reports_violated_constraints():
    result = resolve(
        "physical.gate.elmore_delay",
        assignments={
            "physical.gate.r_on": 1.0,
            "physical.gate.fanout": 1,
            "physical.gate.c_input": 1.0,
            "physical.interconnect.c_total": 1.0,
            "physical.interconnect.r_per_length": 0.0,
            "physical.interconnect.c_per_length": 1.0,
            "physical.wire_length": 1.0,
            "physical.clock_frequency": 1.0,
        },
    )
    check = next(
        c for c in result.constraints
        if c.equation == "physical.eq.clock_timing_constraint"
    )
    assert check.satisfied is False


def test_expression_lhs_constraint_is_reported_for_lhs_variables(registry_snapshot):
    target = var(
        "test.expr_lhs.target",
        "test_expr_lhs_target",
        "value",
        "Temporary expression-LHS target.",
        scope="test",
    )
    driver = var(
        "test.expr_lhs.driver",
        "test_expr_lhs_driver",
        "value",
        "Temporary target driver.",
        scope="test",
    )
    offset = var(
        "test.expr_lhs.offset",
        "test_expr_lhs_offset",
        "value",
        "Temporary LHS offset.",
        scope="test",
    )
    limit = var(
        "test.expr_lhs.limit",
        "test_expr_lhs_limit",
        "value",
        "Temporary constraint limit.",
        scope="test",
    )

    Equation(
        "test.eq.expr_lhs_target",
        target.symbol,
        driver.symbol,
        "Temporary target identity.",
    )
    relation = Inequality(
        "test.ineq.expr_lhs_target_plus_offset_le_limit",
        target.symbol + offset.symbol,
        limit.symbol,
        "<=",
        "Temporary expression-LHS constraint.",
    )

    assert relation in target.constraints()
    assert relation in offset.constraints()
    assert target.direct_dependencies() == {driver}
    assert {
        v.name for v in target.direct_dependencies(include_constraints=True)
    } == {
        driver.name,
        offset.name,
        limit.name,
    }

    result = resolve(
        target.name,
        assignments={
            driver.name: 2,
            offset.name: 1,
            limit.name: 5,
        },
    )

    check = next(
        c for c in result.constraints
        if c.equation == "test.ineq.expr_lhs_target_plus_offset_le_limit"
    )
    assert check.satisfied is True
    assert check.missing == set()


def test_raw_symbols_on_expression_lhs_constraints_are_reported(registry_snapshot):
    owner = var(
        "test.expr_lhs_raw.owner",
        "test_expr_lhs_raw_owner",
        "value",
        "Temporary expression-LHS raw-symbol owner.",
        scope="test",
    )
    limit = var(
        "test.expr_lhs_raw.limit",
        "test_expr_lhs_raw_limit",
        "value",
        "Temporary expression-LHS raw-symbol limit.",
        scope="test",
    )
    raw = sp.Symbol("test_expr_lhs_raw_ghost")

    inequality = Inequality(
        "test.ineq.expr_lhs_raw",
        owner.symbol + raw,
        limit.symbol,
        "<=",
        "Temporary expression-LHS inequality with a raw symbol.",
    )
    generic_constraint = Equation(
        "test.eq.expr_lhs_raw_constraint",
        owner.symbol + raw,
        limit.symbol,
        "Temporary expression-LHS constraint with a raw symbol.",
        role=RelationRole.CONSTRAINT,
    )

    assert inequality.raw_dependency_symbols() == {raw}
    assert generic_constraint.raw_dependency_symbols() == {raw}


def test_resolve_reports_violated_variable_domain_for_assigned_boundary():
    result = resolve(
        "physical.lithography.source_plasma_drive_peak_intensity",
        assignments={
            "physical.lithography.source_plasma_drive_pulse_fluence": -1.0,
            "physical.lithography.source_plasma_drive_pulse_duration": 1.0,
            "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor": 1.0,
        },
    )

    assert float(result.value) == pytest.approx(-1.0)
    domain_check = next(
        c for c in result.constraints
        if c.equation
        == "domain.physical.lithography.source_plasma_drive_pulse_fluence.positive"
    )
    assert domain_check.satisfied is False
