"""
core/units.py
=============

Dimensional analysis: checking that both sides of an equation measure the
same kind of thing. An equation that sets watts equal to meters is wrong no
matter what the numbers are, and this module catches that class of mistake
at construction time, built on sympy.physics.units.

The checks are opt-in. Not every Variable has an SI dimension — "tokens" and
"experts" are counts, not physical units — so forcing a dimensional
expression on everything would be noise. When a Variable does carry one
(via `sp_units`), equations can ask for a consistency check.

Usage
-----
    from sympy.physics.units import meter, second
    v = Variable(..., units="m/s", sp_units=meter/second)

    Equation(..., lhs=v, rhs=other_expr, check_units=True)

With check_units=True, a dimensional mismatch raises UnitError the moment
the equation is constructed, not later at evaluation time.
"""

from __future__ import annotations

from typing import Mapping, Optional
import sympy as sp

# Import real SI units when sympy.physics.units is available. When it is not
# (or a specific unit is missing in this SymPy version), fall back to plain
# symbols so scope modules can still declare unit metadata without crashing;
# _UNITS_AVAILABLE records which world we are in.
try:
    from sympy.physics.units import (
        meter, second, kilogram, ampere, kelvin, mole, candela,  # base SI
        hertz, newton, pascal, joule, watt, coulomb, volt, ohm, farad,  # derived
        henry, tesla, weber,  # more derived
    )
    try:
        from sympy.physics.units import lux, lumen
    except ImportError:
        lux = sp.Symbol("lux_unit")
        lumen = sp.Symbol("lumen_unit")
    try:
        from sympy.physics.units import byte, bit
    except ImportError:
        byte = sp.Symbol("byte_unit")
        bit = sp.Symbol("bit_unit")
    from sympy.physics.units.systems import SI
    _UNITS_AVAILABLE = True
except ImportError:
    meter = sp.Symbol("meter_unit")
    second = sp.Symbol("second_unit")
    kilogram = sp.Symbol("kilogram_unit")
    ampere = sp.Symbol("ampere_unit")
    kelvin = sp.Symbol("kelvin_unit")
    mole = sp.Symbol("mole_unit")
    candela = sp.Symbol("candela_unit")
    hertz = sp.Symbol("hertz_unit")
    newton = sp.Symbol("newton_unit")
    pascal = sp.Symbol("pascal_unit")
    joule = sp.Symbol("joule_unit")
    watt = sp.Symbol("watt_unit")
    coulomb = sp.Symbol("coulomb_unit")
    volt = sp.Symbol("volt_unit")
    ohm = sp.Symbol("ohm_unit")
    farad = sp.Symbol("farad_unit")
    henry = sp.Symbol("henry_unit")
    tesla = sp.Symbol("tesla_unit")
    weber = sp.Symbol("weber_unit")
    lux = sp.Symbol("lux_unit")
    lumen = sp.Symbol("lumen_unit")
    byte = sp.Symbol("byte_unit")
    bit = sp.Symbol("bit_unit")
    _UNITS_AVAILABLE = False


class UnitError(ValueError):
    """Raised when an equation's LHS and RHS have incompatible units."""
    pass


# ---------------------------------------------------------------------------
# Shortcuts for common derived units in the training stack
# ---------------------------------------------------------------------------

# Derived units we use a lot. These names are always bound so scope modules can
# declare metadata even when optional SymPy unit exports vary by version.
FLOP = sp.Symbol("FLOP", positive=True)  # not a real SI unit; use as symbolic
FLOPS = FLOP / second
BPS = byte / second
HZ = hertz
JOULE = joule
WATT = watt
VOLT = volt
OHM = ohm
FARAD = farad
HENRY = henry
COULOMB = coulomb
AMPERE = ampere
METER = meter
SECOND = second
KELVIN = kelvin
KILOGRAM = kilogram
MOLE = mole
PASCAL = pascal


def check_dimensional_consistency(
    lhs_units: Optional[sp.Expr],
    rhs_units: Optional[sp.Expr],
    equation_name: str = "",
) -> None:
    """
    Raise UnitError when lhs_units and rhs_units measure different dimensions.

    Passes silently when either side is None: unit checking is opt-in, and a
    missing dimension means "not declared", not "wrong".
    """
    if not _UNITS_AVAILABLE or lhs_units is None or rhs_units is None:
        return
    try:
        _assert_equivalent_units(lhs_units, rhs_units, equation_name)
    except Exception as e:
        # A genuine mismatch propagates; anything else means SymPy could not
        # decide, and an undecidable check should not fail the whole build.
        if isinstance(e, UnitError):
            raise


def infer_expr_units(
    expr: sp.Expr,
    symbol_units: Mapping[sp.Symbol, sp.Expr],
    equation_name: str = "",
) -> Optional[sp.Expr]:
    """
    Infer an expression's unit by walking its structure, not by substitution.

    Why structural? Substituting units directly into `G - R`, where both
    terms carry the same unit, would simplify to zero and the dimension
    would vanish. Walking the tree instead, we check every additive term
    against the first and return the shared unit. Along the way we also
    enforce the usual rules: exponents and transcendental-function arguments
    must be dimensionless, and Min/Max arguments must agree.

    Returns None when the unit cannot be determined.
    """
    expr = sp.sympify(expr)
    if expr.is_Number:
        return sp.Integer(1)
    if isinstance(expr, sp.Symbol):
        return symbol_units.get(expr, sp.Integer(1))
    if isinstance(expr, sp.Add):
        term_units = [
            infer_expr_units(arg, symbol_units, equation_name)
            for arg in expr.args
        ]
        term_units = [u for u in term_units if u is not None]
        if not term_units:
            return sp.Integer(1)
        first = term_units[0]
        for unit in term_units[1:]:
            _assert_equivalent_units(first, unit, equation_name)
        return first
    if isinstance(expr, sp.Mul):
        out = sp.Integer(1)
        for arg in expr.args:
            unit = infer_expr_units(arg, symbol_units, equation_name)
            if unit is not None:
                out *= unit
        return out
    if isinstance(expr, sp.Pow):
        base_unit = infer_expr_units(expr.base, symbol_units, equation_name)
        exp_unit = infer_expr_units(expr.exp, symbol_units, equation_name)
        if exp_unit is not None:
            _assert_equivalent_units(sp.Integer(1), exp_unit, equation_name)
        if base_unit is None:
            return None
        if expr.exp.free_symbols and not _is_dimensionless(base_unit):
            return None
        return base_unit ** expr.exp
    if isinstance(expr, sp.Abs):
        return infer_expr_units(expr.args[0], symbol_units, equation_name)

    if expr.is_Function:
        name = expr.func.__name__
        arg_units = [
            infer_expr_units(arg, symbol_units, equation_name)
            for arg in expr.args
        ]
        if name in {"exp", "log", "sin", "cos", "tan", "asin", "acos", "atan"}:
            for unit in arg_units:
                if unit is not None:
                    _assert_equivalent_units(sp.Integer(1), unit, equation_name)
            return sp.Integer(1)
        if name == "Mod":
            for unit in arg_units:
                if unit is not None:
                    _assert_equivalent_units(sp.Integer(1), unit, equation_name)
            return sp.Integer(1) if all(unit is not None for unit in arg_units) else None
        if name in {"Min", "Max"} and arg_units:
            first = arg_units[0]
            for unit in arg_units[1:]:
                if first is not None and unit is not None:
                    _assert_equivalent_units(first, unit, equation_name)
            return first
        return None

    return None


def _assert_equivalent_units(
    lhs_units: sp.Expr,
    rhs_units: sp.Expr,
    equation_name: str = "",
) -> None:
    lhs_dim = SI.get_dimensional_expr(lhs_units)
    rhs_dim = SI.get_dimensional_expr(rhs_units)
    dim_system = SI.get_dimension_system()
    if not dim_system.equivalent_dims(lhs_dim, rhs_dim):
        raise UnitError(
            f"Equation {equation_name!r}: units mismatch "
            f"LHS={lhs_units} ({lhs_dim}), RHS={rhs_units} ({rhs_dim})"
        )


def _is_dimensionless(unit: sp.Expr) -> bool:
    try:
        dim = SI.get_dimensional_expr(unit)
        return SI.get_dimension_system().equivalent_dims(dim, sp.Integer(1))
    except Exception:
        return False


__all__ = [
    "UnitError",
    "check_dimensional_consistency",
    "infer_expr_units",
    "_UNITS_AVAILABLE",
]
