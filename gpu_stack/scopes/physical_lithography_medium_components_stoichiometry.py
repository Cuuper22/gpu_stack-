"""
scopes/physical_lithography_medium_components_stoichiometry.py
==============================================================

Stoichiometric counts for the imaging medium: how many atoms of component
A and component B make up one formula unit of the compound. These two
integers are the recipe of the medium. The formula-unit layer multiplies
them by per-component nucleon and electron counts to get totals, and the
density layer multiplies by particle mass to reach bulk properties.
"""

import sympy as sp

from ..core import Inequality, var
from .physical_lithography_medium_components_reference import (
    LITHOGRAPHY_MEDIUM_COMPOSITION_REF,
)


lithography_medium_component_a_stoichiometric_count = var(
    "physical.lithography.medium_component_a_stoichiometric_count", "nu_A_litho_med", "count",
    "Stoichiometric count of component A in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_stoichiometric_count = var(
    "physical.lithography.medium_component_b_stoichiometric_count", "nu_B_litho_med", "count",
    "Stoichiometric count of component B in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)


ineq_lithography_medium_component_a_stoichiometric_count_at_least_one = Inequality(
    "physical.ineq.lithography_medium_component_a_stoichiometric_count_at_least_one",
    lithography_medium_component_a_stoichiometric_count.symbol,
    sp.Integer(1),
    ">=",
    "Component A stoichiometric count must be at least one in the representative binary imaging-medium formula unit.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
ineq_lithography_medium_component_b_stoichiometric_count_at_least_one = Inequality(
    "physical.ineq.lithography_medium_component_b_stoichiometric_count_at_least_one",
    lithography_medium_component_b_stoichiometric_count.symbol,
    sp.Integer(1),
    ">=",
    "Component B stoichiometric count must be at least one in the representative binary imaging-medium formula unit.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)


LITHOGRAPHY_MEDIUM_COMPONENT_STOICHIOMETRY_VARIABLES = [
    lithography_medium_component_a_stoichiometric_count,
    lithography_medium_component_b_stoichiometric_count,
]

LITHOGRAPHY_MEDIUM_COMPONENT_STOICHIOMETRY_EQUATIONS = [
    ineq_lithography_medium_component_a_stoichiometric_count_at_least_one,
    ineq_lithography_medium_component_b_stoichiometric_count_at_least_one,
]


LITHOGRAPHY_MEDIUM_COMPONENT_STOICHIOMETRY_EXPORTS = [
    "lithography_medium_component_a_stoichiometric_count",
    "lithography_medium_component_b_stoichiometric_count",
    "ineq_lithography_medium_component_a_stoichiometric_count_at_least_one",
    "ineq_lithography_medium_component_b_stoichiometric_count_at_least_one",
]


__all__ = [*LITHOGRAPHY_MEDIUM_COMPONENT_STOICHIOMETRY_EXPORTS]
