"""
scopes/physical_lithography_plasma_common.py
============================================

Shared builders for source-plasma declarations. Every plasma variable
carries the same scope, reference, and metadata boilerplate, so these
helpers construct them in one place: one builder for general plasma
variables and one for dimensionless fractions with the usual zero-to-one
bounds. Using the builders keeps the many plasma fragment modules short and
guarantees their metadata cannot drift apart.
"""

import sympy as sp

from ..core import var
from .physical_lithography_plasma_species import LITHOGRAPHY_SOURCE_PLASMA_STATE_REF


_SOURCE_PLASMA_NAME_PREFIX = "physical.lithography."
DIMENSIONLESS = sp.Integer(1)


def plasma_var(
    name_suffix,
    symbol,
    units,
    description,
    *,
    sp_units,
    positive=True,
    nonnegative=False,
    value_range=None,
):
    """Create a source-plasma variable with the shared physical scope metadata."""
    if positive and nonnegative:
        raise ValueError("plasma_var accepts only one sign constraint")

    kwargs = {
        "scope": "physical",
        "sp_units": sp_units,
        "references": [LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    }
    if positive:
        kwargs["positive"] = True
    elif nonnegative:
        kwargs["nonnegative"] = True
    if value_range is not None:
        kwargs["value_range"] = value_range

    return var(
        f"{_SOURCE_PLASMA_NAME_PREFIX}{name_suffix}",
        symbol,
        units,
        description,
        **kwargs,
    )


def plasma_fraction(
    name_suffix,
    symbol,
    description,
    *,
    positive=True,
    value_range=(0.0, 1.0),
):
    """Create a dimensionless source-plasma fraction with the usual bounds."""
    return plasma_var(
        name_suffix,
        symbol,
        "dimensionless",
        description,
        sp_units=DIMENSIONLESS,
        positive=positive,
        nonnegative=not positive,
        value_range=value_range,
    )


__all__ = [
    "DIMENSIONLESS",
    "plasma_fraction",
    "plasma_var",
]
