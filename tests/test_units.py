"""
tests/test_units.py
===================

Unit metadata and dimensional-check regressions.

The important behavior is not merely that some fields are populated. The
checker has to understand expressions structurally, especially sums where
direct substitution can erase the dimension by cancellation.
"""

import pytest
import sympy as sp

from gpu_stack import Registry
from gpu_stack.core import (
    Equation,
    Inequality,
    RelationRole,
    UnitError,
    infer_expr_units,
    var,
)
from gpu_stack.core.units import AMPERE, FARAD, METER, OHM, SECOND, VOLT, WATT


@pytest.fixture
def registry_snapshot():
    variables = dict(Registry.variables)
    equations = dict(Registry.equations)
    systems = dict(Registry.systems)
    symbol_cache = dict(Registry._symbol_cache)
    backrefs = {
        name: (list(v._defined_by), list(v._used_in))
        for name, v in variables.items()
    }

    yield

    for name, (defined_by, used_in) in backrefs.items():
        v = variables[name]
        v._defined_by[:] = defined_by
        v._used_in[:] = used_in
    Registry.variables = variables
    Registry.equations = equations
    Registry.systems = systems
    Registry._symbol_cache = symbol_cache


def test_structural_unit_inference_preserves_subtraction_units():
    x, y = sp.symbols("x y")
    inferred = infer_expr_units(x - y, {x: AMPERE, y: AMPERE}, "test.eq")
    assert inferred == AMPERE


def test_structural_unit_inference_rejects_bad_addition():
    x, y = sp.symbols("x y")
    with pytest.raises(UnitError):
        infer_expr_units(x + y, {x: AMPERE, y: VOLT}, "test.eq")


def test_structural_unit_inference_handles_cmos_power_product():
    c, v, f = sp.symbols("c v f")
    inferred = infer_expr_units(
        c * v**2 * f,
        {c: FARAD, v: VOLT, f: 1 / SECOND},
        "test.dynamic_power",
    )
    from gpu_stack.core.units import check_dimensional_consistency

    check_dimensional_consistency(WATT, inferred, "test.dynamic_power")


def test_structural_unit_inference_handles_inverse_trig_dimensionless_args():
    x, y = sp.symbols("x y")
    inferred = infer_expr_units(sp.atan(x / y), {x: METER, y: METER}, "test.atan")
    assert inferred == 1


def test_structural_unit_inference_handles_dimensionless_mod():
    x, y = sp.symbols("x y")
    inferred = infer_expr_units(sp.Mod(x + y, 3), {x: 1, y: 1}, "test.mod")
    assert inferred == 1


def test_structural_unit_inference_rejects_dimensionful_mod():
    x, y = sp.symbols("x y")
    with pytest.raises(UnitError):
        infer_expr_units(sp.Mod(x, 3), {x: METER}, "test.mod")
    with pytest.raises(UnitError):
        infer_expr_units(sp.Mod(x, y), {x: METER, y: METER}, "test.mod")


def test_expression_lhs_constraint_unit_check_accepts_matching_units(registry_snapshot):
    left = var(
        "test.units.expr_lhs.left",
        "test_units_expr_lhs_left",
        "m",
        "Temporary expression-LHS unit-check left term.",
        scope="test",
        sp_units=METER,
    )
    offset = var(
        "test.units.expr_lhs.offset",
        "test_units_expr_lhs_offset",
        "m",
        "Temporary expression-LHS unit-check offset term.",
        scope="test",
        sp_units=METER,
    )
    limit = var(
        "test.units.expr_lhs.limit",
        "test_units_expr_lhs_limit",
        "m",
        "Temporary expression-LHS unit-check limit.",
        scope="test",
        sp_units=METER,
    )

    Inequality(
        "test.units.ineq.expr_lhs_matching_units",
        left.symbol + offset.symbol,
        limit.symbol,
        "<=",
        "Temporary expression-LHS constraint with matching units.",
        check_units=True,
    )


def test_expression_lhs_equation_unit_check_accepts_matching_units(registry_snapshot):
    left = var(
        "test.units.expr_lhs_eq_ok.left",
        "test_units_expr_lhs_eq_ok_left",
        "m",
        "Temporary expression-LHS equation left term.",
        scope="test",
        sp_units=METER,
    )
    offset = var(
        "test.units.expr_lhs_eq_ok.offset",
        "test_units_expr_lhs_eq_ok_offset",
        "m",
        "Temporary expression-LHS equation offset term.",
        scope="test",
        sp_units=METER,
    )
    total = var(
        "test.units.expr_lhs_eq_ok.total",
        "test_units_expr_lhs_eq_ok_total",
        "m",
        "Temporary expression-LHS equation total.",
        scope="test",
        sp_units=METER,
    )

    Equation(
        "test.units.eq.expr_lhs_matching_units",
        left.symbol + offset.symbol,
        total.symbol,
        "Temporary expression-LHS equation with matching units.",
        role=RelationRole.CONSTRAINT,
        check_units=True,
    )


def test_expression_lhs_constraint_unit_check_rejects_bad_lhs_addition(
    registry_snapshot,
):
    length = var(
        "test.units.expr_lhs_bad.length",
        "test_units_expr_lhs_bad_length",
        "m",
        "Temporary expression-LHS unit-check length.",
        scope="test",
        sp_units=METER,
    )
    duration = var(
        "test.units.expr_lhs_bad.duration",
        "test_units_expr_lhs_bad_duration",
        "s",
        "Temporary expression-LHS unit-check duration.",
        scope="test",
        sp_units=SECOND,
    )
    limit = var(
        "test.units.expr_lhs_bad.limit",
        "test_units_expr_lhs_bad_limit",
        "m",
        "Temporary expression-LHS unit-check limit.",
        scope="test",
        sp_units=METER,
    )

    with pytest.raises(UnitError):
        Inequality(
            "test.units.ineq.expr_lhs_bad_addition",
            length.symbol + duration.symbol,
            limit.symbol,
            "<=",
            "Temporary expression-LHS constraint with bad additive units.",
            check_units=True,
        )


def test_expression_lhs_equation_unit_check_rejects_rhs_mismatch(registry_snapshot):
    left = var(
        "test.units.expr_lhs_eq.left",
        "test_units_expr_lhs_eq_left",
        "m",
        "Temporary expression-LHS equation left term.",
        scope="test",
        sp_units=METER,
    )
    offset = var(
        "test.units.expr_lhs_eq.offset",
        "test_units_expr_lhs_eq_offset",
        "m",
        "Temporary expression-LHS equation offset term.",
        scope="test",
        sp_units=METER,
    )
    duration = var(
        "test.units.expr_lhs_eq.duration",
        "test_units_expr_lhs_eq_duration",
        "s",
        "Temporary expression-LHS equation duration.",
        scope="test",
        sp_units=SECOND,
    )

    with pytest.raises(UnitError):
        Equation(
            "test.units.eq.expr_lhs_rhs_mismatch",
            left.symbol + offset.symbol,
            duration.symbol,
            "Temporary expression-LHS equation with mismatched RHS units.",
            role=RelationRole.CONSTRAINT,
            check_units=True,
        )


def test_unit_check_failure_does_not_register_invalid_equation(registry_snapshot):
    length = var(
        "test.units.atomic.length",
        "test_units_atomic_length",
        "m",
        "Temporary atomic unit-check length.",
        scope="test",
        sp_units=METER,
    )
    duration = var(
        "test.units.atomic.duration",
        "test_units_atomic_duration",
        "s",
        "Temporary atomic unit-check duration.",
        scope="test",
        sp_units=SECOND,
    )
    equation_name = "test.units.eq.atomic_bad_units"

    with pytest.raises(UnitError):
        Equation(
            equation_name,
            length.symbol,
            duration.symbol,
            "Temporary invalid equation that must not leak into the registry.",
            check_units=True,
        )

    assert equation_name not in Registry.equations
    assert all(eq.name != equation_name for eq in length.defining_equations)
    assert all(eq.name != equation_name for eq in duration.appearances)


def test_lithography_quark_count_from_zn_rhs_infers_dimensionless():
    eq = Registry.equations[
        "physical.eq.lithography_source_valence_up_quark_count_from_zn"
    ]
    lookup = {
        sym: Registry.lookup_by_symbol(sym).sp_units
        for sym in eq.rhs.free_symbols
    }
    assert infer_expr_units(eq.rhs, lookup, eq.name) == 1


def test_physical_scope_has_curated_unit_coverage():
    physical = Registry.by_scope("physical")
    with_units = [v for v in physical if v.sp_units is not None]
    assert len(with_units) >= 100
    assert Registry.variables["physical.current"].sp_units == AMPERE
    assert Registry.variables["physical.gate.c_load"].sp_units == FARAD
    assert Registry.variables["physical.interconnect.r_per_length"].sp_units == OHM / METER


def test_curated_equations_have_unit_checks_enabled():
    checked = [
        e.name for e in Registry.equations.values()
        if getattr(e, "_check_units_flag", False)
    ]
    assert len(checked) >= 49
    assert "physical.eq.current_from_carriers" in checked
    assert "physical.eq.dynamic_power" in checked
    assert "physical.eq.skin_depth" in checked
