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

Scale
-----
A Variable's numeric value is in its display unit (a price in USD/kWh, a
duration in ms). Its `sp_units` must carry that unit's scale, for example
`USD / KWH`, not the SI-coherent `USD / (WATT * SECOND)`. The checker compares
scale as well as dimension: seconds and milliseconds cannot be added or equated
unless a numeric literal in the equation converts between them (`t_s = t_ms / 1000`).
A literal counts as a conversion only when it differs between the two sides and
leaves a residual factor within a small bound; `t_s = t_ms * 1000` fails.
Literals on equal-scale units are physical coefficients and are never checked.
"""

from __future__ import annotations

from typing import Dict, Mapping, Optional, Tuple
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
    from sympy.physics.units import Quantity, day, hour, kilo, giga, liter, tonne
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
    Quantity = None
    day = hour = kilo = giga = liter = tonne = sp.Symbol("unit_unavailable")
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

# Units whose scale differs from the SI coherent unit. A Variable's numeric
# value is expressed in its display unit, so the Variable's sp_units must carry
# the same scale (kWh is 3.6e6 J, not 1 J).
KILOWATT = kilo * watt
KWH = kilo * watt * hour
HOUR = hour
MONTH = 30 * day          # the model's billing month is 30 days (2,592,000 s)
YEAR = 365 * day          # the model's year is 365 days
LITER = liter
TONNE = tonne
GIGABYTE = giga * byte    # decimal GB, 1e9 bytes


# ---------------------------------------------------------------------------
# Undecided checks
# ---------------------------------------------------------------------------

# Equation name -> reason. A check lands here when SymPy could not decide it
# (an unexpected exception, or a unit expression that could not be inferred).
# That is not a failure and not a pass: the audit reports the count.
UNDECIDED_UNIT_CHECKS: Dict[str, str] = {}


def record_undecided_unit_check(equation_name: str, reason: str) -> None:
    UNDECIDED_UNIT_CHECKS[equation_name or "<unnamed>"] = reason


def undecided_unit_checks() -> Dict[str, str]:
    return dict(UNDECIDED_UNIT_CHECKS)


# ---------------------------------------------------------------------------
# Scale handling
# ---------------------------------------------------------------------------

# A numeric literal that bridges two unit scales is a conversion factor. One
# that is a plain physical coefficient (0.5, 2, 4*pi) is a different thing,
# and the checker cannot tell them apart from the literal alone. It accepts a
# literal as a valid conversion when, after applying it, the two sides agree
# up to a factor no larger than this. Real unit slips are 1e3, 3600, 8, 1e9.
_COEFFICIENT_BOUND = 20.0


def unit_scale(unit: sp.Expr) -> sp.Expr:
    """
    Scale of `unit` relative to SI coherent units (SymPy's internal base).

    Quantities are replaced by their SI scale factors. Placeholder symbols
    such as USD and FLOP carry no scale and count as 1.
    """
    expr = sp.sympify(unit)
    if Quantity is not None:
        expr = expr.subs(
            {q: SI.get_quantity_scale_factor(q) for q in expr.atoms(Quantity)}
        )
    return expr.subs({sym: 1 for sym in expr.free_symbols})


def _close(a: sp.Expr, b: sp.Expr) -> bool:
    fa, fb = float(a), float(b)
    return abs(fa - fb) <= 1e-9 * max(abs(fa), abs(fb), 1e-300)


def _scales_compatible(
    unit_a: sp.Expr, k_a: float, unit_b: sp.Expr, k_b: float
) -> bool:
    """
    True when two quantities of equal dimension agree in scale.

    k_a and k_b are the products of the numeric literals multiplied into each
    side. Equal scales pass whatever the literals are. Unequal scales pass
    only when the literals differ and, once applied as conversions, leave a
    residual factor within _COEFFICIENT_BOUND.
    """
    sa, sb = unit_scale(unit_a), unit_scale(unit_b)
    if _close(sa, sb):
        return True
    if abs(k_a - k_b) <= 1e-12 * max(abs(k_a), abs(k_b), 1.0):
        return False
    rho = (float(sa) / k_a) / (float(sb) / k_b)
    return 1.0 / _COEFFICIENT_BOUND <= rho <= _COEFFICIENT_BOUND


def check_dimensional_consistency(
    lhs_units: Optional[sp.Expr],
    rhs_units: Optional[sp.Expr],
    equation_name: str = "",
) -> None:
    """
    Raise UnitError when lhs_units and rhs_units differ in dimension or scale.

    Passes silently when either side is None: unit checking is opt-in, and a
    missing dimension means "not declared", not "wrong". If SymPy cannot
    decide, the check is recorded as undecided (see undecided_unit_checks)
    instead of failing the build.
    """
    if not _UNITS_AVAILABLE or lhs_units is None or rhs_units is None:
        return
    try:
        _assert_equivalent_units(lhs_units, rhs_units, equation_name)
    except UnitError:
        raise
    except Exception as exc:
        record_undecided_unit_check(
            equation_name, f"{type(exc).__name__}: {exc}"
        )


def check_equation_units(
    lhs_units: Optional[Tuple[sp.Expr, float]],
    rhs_units: Optional[Tuple[sp.Expr, float]],
    equation_name: str = "",
) -> None:
    """
    Check one equation given (unit, literal-coefficient) pairs for each side,
    as returned by infer_expr_units_with_coefficient. A side whose unit could
    not be inferred makes the check undecided, which is recorded, not raised.
    """
    if not _UNITS_AVAILABLE:
        return
    if lhs_units is None or rhs_units is None:
        record_undecided_unit_check(equation_name, "unit could not be inferred")
        return
    try:
        _assert_equivalent_units(
            lhs_units[0], rhs_units[0], equation_name,
            lhs_units[1], rhs_units[1],
        )
    except UnitError:
        raise
    except Exception as exc:
        record_undecided_unit_check(
            equation_name, f"{type(exc).__name__}: {exc}"
        )


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

    Scale is checked as well as dimension. Variable values are numbers in
    their display unit, so a symbol declared in milliseconds and one declared
    in seconds cannot be added unless a numeric literal converts between them.

    Returns None when the unit cannot be determined.
    """
    result = infer_expr_units_with_coefficient(expr, symbol_units, equation_name)
    return None if result is None else result[0]


def infer_expr_units_with_coefficient(
    expr: sp.Expr,
    symbol_units: Mapping[sp.Symbol, sp.Expr],
    equation_name: str = "",
) -> Optional[Tuple[sp.Expr, float]]:
    """
    Like infer_expr_units, but also return the product of the numeric
    literals multiplied into the expression. Scale checking needs it: a
    literal such as 1/3600 is how an equation converts seconds to hours.
    """
    expr = sp.sympify(expr)
    one = sp.Integer(1)
    if expr.is_Number:
        return one, _literal_magnitude(expr)
    if isinstance(expr, sp.Symbol):
        return symbol_units.get(expr, one), 1.0
    if isinstance(expr, sp.Add):
        inferred_terms = [
            infer_expr_units_with_coefficient(arg, symbol_units, equation_name)
            for arg in expr.args
        ]
        terms = [t for t in inferred_terms if t is not None]
        if not terms:
            return one, 1.0
        first = terms[0]
        for term in terms[1:]:
            _assert_equivalent_units(
                first[0], term[0], equation_name, first[1], term[1]
            )
        return first
    if isinstance(expr, sp.Mul):
        out = one
        k = 1.0
        for arg in expr.args:
            inferred = infer_expr_units_with_coefficient(
                arg, symbol_units, equation_name
            )
            if inferred is not None:
                out *= inferred[0]
                k *= inferred[1]
        return out, k
    if isinstance(expr, sp.Pow):
        base = infer_expr_units_with_coefficient(expr.base, symbol_units, equation_name)
        exp = infer_expr_units_with_coefficient(expr.exp, symbol_units, equation_name)
        if exp is not None:
            _assert_equivalent_units(one, exp[0], equation_name, 1.0, exp[1])
        if base is None:
            return None
        if expr.exp.free_symbols and not _is_dimensionless(base[0]):
            return None
        k = base[1] ** float(expr.exp) if expr.exp.is_number else 1.0
        return base[0] ** expr.exp, k
    if isinstance(expr, sp.Abs):
        return infer_expr_units_with_coefficient(expr.args[0], symbol_units, equation_name)

    if expr.is_number:
        # pi, E, and similar numeric constants.
        return one, _literal_magnitude(expr)

    if expr.is_Function:
        name = expr.func.__name__
        arg_units = [
            infer_expr_units_with_coefficient(arg, symbol_units, equation_name)
            for arg in expr.args
        ]
        if name in {"exp", "log", "sin", "cos", "tan", "asin", "acos", "atan"}:
            for unit in arg_units:
                if unit is not None:
                    _assert_equivalent_units(one, unit[0], equation_name, 1.0, unit[1])
            return one, 1.0
        if name == "Mod":
            for unit in arg_units:
                if unit is not None:
                    _assert_equivalent_units(one, unit[0], equation_name, 1.0, unit[1])
            return (one, 1.0) if all(unit is not None for unit in arg_units) else None
        if name in {"Min", "Max"} and arg_units:
            lead = arg_units[0]
            for unit in arg_units[1:]:
                if lead is not None and unit is not None:
                    _assert_equivalent_units(
                        lead[0], unit[0], equation_name, lead[1], unit[1]
                    )
            return lead
        return None

    return None


def _literal_magnitude(expr: sp.Expr) -> float:
    try:
        value = abs(float(expr))
    except (TypeError, ValueError):
        return 1.0
    return value if value > 0 else 1.0


def _assert_equivalent_units(
    lhs_units: sp.Expr,
    rhs_units: sp.Expr,
    equation_name: str = "",
    lhs_coeff: float = 1.0,
    rhs_coeff: float = 1.0,
) -> None:
    lhs_dim = SI.get_dimensional_expr(lhs_units)
    rhs_dim = SI.get_dimensional_expr(rhs_units)
    dim_system = SI.get_dimension_system()
    if not dim_system.equivalent_dims(lhs_dim, rhs_dim):
        raise UnitError(
            f"Equation {equation_name!r}: units mismatch "
            f"LHS={lhs_units} ({lhs_dim}), RHS={rhs_units} ({rhs_dim})"
        )
    if not _scales_compatible(lhs_units, lhs_coeff, rhs_units, rhs_coeff):
        raise UnitError(
            f"Equation {equation_name!r}: unit scale mismatch, a conversion "
            f"factor is missing or wrong. "
            f"LHS={lhs_units} (scale {unit_scale(lhs_units)}, literal {lhs_coeff:g}), "
            f"RHS={rhs_units} (scale {unit_scale(rhs_units)}, literal {rhs_coeff:g})"
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
    "check_equation_units",
    "infer_expr_units",
    "infer_expr_units_with_coefficient",
    "undecided_unit_checks",
    "unit_scale",
    "_UNITS_AVAILABLE",
]
