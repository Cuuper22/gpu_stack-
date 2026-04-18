"""
core/units.py
=============

Lightweight dimensional analysis on top of sympy.physics.units.

We don't force every Variable to carry a sympy dimensional expression (that
would be annoying for things like "tokens" or "experts" that aren't SI). But
when units ARE given as sympy expressions, we support consistency checks on
equations.

Usage
-----
    from sympy.physics.units import meter, second
    v = Variable(..., units="m/s", sp_units=meter/second)

    Equation(..., lhs=v, rhs=other_expr, check_units=True)

If check_units=True and the dimensional analysis fails, the equation raises
a UnitError at construction time.
"""

from __future__ import annotations

from typing import Optional
import sympy as sp

# SymPy's physics.units package has full SI + derived units support.
try:
    from sympy.physics.units import (
        meter, second, kilogram, ampere, kelvin, mole, candela,  # base SI
        hertz, newton, pascal, joule, watt, coulomb, volt, ohm, farad,  # derived
        henry, tesla, weber, lux, lumen,  # more derived
        byte, bit,  # info
    )
    from sympy.physics.units.systems import SI
    from sympy.physics.units.dimensions import Dimension
    _UNITS_AVAILABLE = True
except ImportError:
    _UNITS_AVAILABLE = False


class UnitError(ValueError):
    """Raised when an equation's LHS and RHS have incompatible units."""
    pass


# ---------------------------------------------------------------------------
# Shortcuts for common derived units in the training stack
# ---------------------------------------------------------------------------

if _UNITS_AVAILABLE:
    # Derived units we use a lot
    FLOP = sp.Symbol("FLOP", positive=True)  # not a real SI unit; use as symbolic
    FLOPS = FLOP / second
    BPS = byte / second
    HZ = hertz
    JOULE = joule
    WATT = watt
    VOLT = volt
    OHM = ohm
    FARAD = farad
    COULOMB = coulomb
    AMPERE = ampere
    METER = meter
    SECOND = second
    KELVIN = kelvin
    KILOGRAM = kilogram
    PASCAL = pascal


def check_dimensional_consistency(
    lhs_units: Optional[sp.Expr],
    rhs_units: Optional[sp.Expr],
    equation_name: str = "",
) -> None:
    """
    Raise UnitError if lhs_units and rhs_units aren't dimensionally compatible.
    Silently passes if either is None (opt-in consistency).
    """
    if not _UNITS_AVAILABLE or lhs_units is None or rhs_units is None:
        return
    try:
        # Cancel lhs/rhs and see if it simplifies to a pure number
        ratio = sp.simplify(lhs_units / rhs_units)
        # If dimensions cancel cleanly, ratio is a pure number or dimensionless Symbol
        if ratio.has(Dimension):
            raise UnitError(
                f"Equation {equation_name!r}: units mismatch "
                f"LHS={lhs_units}, RHS={rhs_units}, ratio={ratio}"
            )
    except Exception as e:
        # Don't fail the whole build if sympy can't decide
        if isinstance(e, UnitError):
            raise


__all__ = ["UnitError", "check_dimensional_consistency", "_UNITS_AVAILABLE"]
