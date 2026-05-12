"""
scopes/physical_lithography_shielding.py
========================================

Coarse source shielding factors for lithography electronic structure.

The factors here are deliberately limiting approximations rather than fitted
Slater coefficients: inner shells fully screen by enclosed charge, while a
same-shell electron is radially inside the transitioning electron half the
time under an exchange-symmetric ordering assumption.
"""

import sympy as sp

from ..core import Approximation, Reference, var


LITHOGRAPHY_SOURCE_SHIELDING_REF = Reference(
    citation=(
        "Lithography source shielding: Gauss-law enclosed-charge limit for "
        "inner-shell electrons and exchange-symmetric radial ordering for "
        "same-shell electrons"
    ),
    kind="memo",
)
lithography_source_inner_shell_shielding_factor = var(
    "physical.lithography.source_inner_shell_shielding_factor",
    "s_inner_screen_litho_src",
    "dimensionless",
    "Effective shielding factor per inner-shell screening electron.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_SHIELDING_REF],
)
lithography_source_same_shell_shielding_factor = var(
    "physical.lithography.source_same_shell_shielding_factor",
    "s_same_screen_litho_src",
    "dimensionless",
    "Effective shielding factor per same-shell screening electron.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_SHIELDING_REF],
)


eq_lithography_source_inner_shell_shielding_factor = Approximation(
    "physical.eq.lithography_source_inner_shell_shielding_factor",
    lithography_source_inner_shell_shielding_factor.symbol,
    sp.Integer(1),
    sp.S.true,
    "Gauss-law enclosed-charge limit: inner-shell electrons fully screen the active-shell electron.",
    references=[LITHOGRAPHY_SOURCE_SHIELDING_REF],
    check_units=True,
)
eq_lithography_source_same_shell_shielding_factor = Approximation(
    "physical.eq.lithography_source_same_shell_shielding_factor",
    lithography_source_same_shell_shielding_factor.symbol,
    sp.Rational(1, 2),
    sp.S.true,
    "Exchange-symmetric radial-ordering approximation: a same-shell electron is inside the transitioning electron half the time.",
    references=[LITHOGRAPHY_SOURCE_SHIELDING_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_SHIELDING_VARIABLES = [
    lithography_source_inner_shell_shielding_factor,
    lithography_source_same_shell_shielding_factor,
]

LITHOGRAPHY_SOURCE_SHIELDING_EQUATIONS = [
    eq_lithography_source_inner_shell_shielding_factor,
    eq_lithography_source_same_shell_shielding_factor,
]

__all__ = [
    "LITHOGRAPHY_SOURCE_SHIELDING_REF",
    "lithography_source_inner_shell_shielding_factor",
    "lithography_source_same_shell_shielding_factor",
    "eq_lithography_source_inner_shell_shielding_factor",
    "eq_lithography_source_same_shell_shielding_factor",
    "LITHOGRAPHY_SOURCE_SHIELDING_VARIABLES",
    "LITHOGRAPHY_SOURCE_SHIELDING_EQUATIONS",
]
