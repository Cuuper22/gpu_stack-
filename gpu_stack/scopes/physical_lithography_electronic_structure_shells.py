"""
scopes/physical_lithography_electronic_structure_shells.py
==========================================================

Shell capacity and occupancy for the source ion. A principal shell n holds
at most 2n^2 electrons; summing the closed shells below the transition
gives the inner-electron count that screens the nucleus. These equations
turn the bound-electron total into per-shell occupancy and the screening
constant seen by the transitioning electron, which the hydrogenic
transition-energy relation then consumes.
"""

import sympy as sp

from ..core import Approximation, eq
from .physical_lithography_electronic_structure_variables import (
    LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF,
    lithography_source_bound_electron_count,
    lithography_source_effective_nuclear_charge,
    lithography_source_inner_closed_shell_capacity,
    lithography_source_inner_closed_shell_electron_count,
    lithography_source_inner_shell_screening_electron_count,
    lithography_source_lower_principal_quantum_number,
    lithography_source_outer_shell_electron_count,
    lithography_source_same_shell_screening_electron_count,
    lithography_source_screening_constant,
    lithography_source_transition_shell_capacity,
    lithography_source_transition_shell_occupancy,
)
from .physical_lithography_shielding import (
    lithography_source_inner_shell_shielding_factor,
    lithography_source_same_shell_shielding_factor,
)
from .physical_lithography_species import lithography_source_proton_count


eq_lithography_source_transition_shell_capacity = eq(
    "physical.eq.lithography_source_transition_shell_capacity",
    lithography_source_transition_shell_capacity.symbol,
    sp.Integer(2) * lithography_source_lower_principal_quantum_number.symbol**2,
    "Principal-shell electron capacity 2 n^2 for the active source transition shell.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_inner_closed_shell_capacity = eq(
    "physical.eq.lithography_source_inner_closed_shell_capacity",
    lithography_source_inner_closed_shell_capacity.symbol,
    (
        lithography_source_lower_principal_quantum_number.symbol
        * (lithography_source_lower_principal_quantum_number.symbol - 1)
        * (2 * lithography_source_lower_principal_quantum_number.symbol - 1)
    )
    / sp.Integer(3),
    "Closed-form sum of 2 n^2 electron states below the active principal shell.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_outer_shell_electron_count = Approximation(
    "physical.eq.lithography_source_outer_shell_electron_count",
    lithography_source_outer_shell_electron_count.symbol,
    sp.Max(
        sp.Integer(0),
        lithography_source_bound_electron_count.symbol
        - lithography_source_inner_closed_shell_capacity.symbol
        - lithography_source_transition_shell_capacity.symbol,
    ),
    lithography_source_lower_principal_quantum_number.symbol >= 1,
    "Filled-shell approximation for bound electrons outside the active transition shell.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_inner_closed_shell_electron_count = Approximation(
    "physical.eq.lithography_source_inner_closed_shell_electron_count",
    lithography_source_inner_closed_shell_electron_count.symbol,
    sp.Min(
        lithography_source_bound_electron_count.symbol
        - lithography_source_outer_shell_electron_count.symbol,
        lithography_source_inner_closed_shell_capacity.symbol,
    ),
    (
        lithography_source_lower_principal_quantum_number.symbol >= 1
    )
    & (
        lithography_source_bound_electron_count.symbol
        >= lithography_source_outer_shell_electron_count.symbol
    ),
    "Filled-lower-shell approximation for closed inner electrons below the active transition shell.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_transition_shell_occupancy = Approximation(
    "physical.eq.lithography_source_transition_shell_occupancy",
    lithography_source_transition_shell_occupancy.symbol,
    lithography_source_bound_electron_count.symbol
    - lithography_source_inner_closed_shell_electron_count.symbol
    - lithography_source_outer_shell_electron_count.symbol,
    (
        lithography_source_bound_electron_count.symbol
        >= (
            lithography_source_inner_closed_shell_electron_count.symbol
            + lithography_source_outer_shell_electron_count.symbol
        )
    )
    & (
        (
            lithography_source_bound_electron_count.symbol
            - lithography_source_inner_closed_shell_electron_count.symbol
            - lithography_source_outer_shell_electron_count.symbol
        )
        <= lithography_source_transition_shell_capacity.symbol
    ),
    "Active-shell occupancy from bound electrons after accounting for closed inner shells and outer electrons.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_same_shell_screening_electron_count = Approximation(
    "physical.eq.lithography_source_same_shell_screening_electron_count",
    lithography_source_same_shell_screening_electron_count.symbol,
    lithography_source_transition_shell_occupancy.symbol - 1,
    (lithography_source_transition_shell_occupancy.symbol > 0)
    & (
        lithography_source_transition_shell_occupancy.symbol
        <= lithography_source_transition_shell_capacity.symbol
    ),
    "Same-shell screening electrons as active-shell occupancy excluding the transitioning electron.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_inner_shell_screening_electron_count = Approximation(
    "physical.eq.lithography_source_inner_shell_screening_electron_count",
    lithography_source_inner_shell_screening_electron_count.symbol,
    lithography_source_bound_electron_count.symbol
    - lithography_source_transition_shell_occupancy.symbol
    - lithography_source_outer_shell_electron_count.symbol,
    lithography_source_bound_electron_count.symbol
    >= (
        lithography_source_transition_shell_occupancy.symbol
        + lithography_source_outer_shell_electron_count.symbol
    ),
    "Inner-shell screening electron count from bound electrons, active-shell occupancy, and outer electrons.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)
eq_lithography_source_screening_constant = Approximation(
    "physical.eq.lithography_source_screening_constant",
    lithography_source_screening_constant.symbol,
    lithography_source_inner_shell_screening_electron_count.symbol
    * lithography_source_inner_shell_shielding_factor.symbol
    + lithography_source_same_shell_screening_electron_count.symbol
    * lithography_source_same_shell_shielding_factor.symbol,
    (
        lithography_source_inner_shell_screening_electron_count.symbol
        + lithography_source_same_shell_screening_electron_count.symbol
        <= lithography_source_bound_electron_count.symbol
    ),
    "Shell-count screening approximation from bound electrons and per-shell shielding factors.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)

eq_lithography_source_effective_nuclear_charge = Approximation(
    "physical.eq.lithography_source_effective_nuclear_charge",
    lithography_source_effective_nuclear_charge.symbol,
    lithography_source_proton_count.symbol
    - lithography_source_screening_constant.symbol,
    lithography_source_proton_count.symbol
    > lithography_source_screening_constant.symbol,
    "Screened effective nuclear charge from nuclear proton count and electronic screening.",
    references=[LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_SHELL_EQUATIONS = [
    eq_lithography_source_transition_shell_capacity,
    eq_lithography_source_inner_closed_shell_capacity,
    eq_lithography_source_outer_shell_electron_count,
    eq_lithography_source_inner_closed_shell_electron_count,
    eq_lithography_source_transition_shell_occupancy,
    eq_lithography_source_same_shell_screening_electron_count,
    eq_lithography_source_inner_shell_screening_electron_count,
    eq_lithography_source_screening_constant,
    eq_lithography_source_effective_nuclear_charge,
]


__all__ = [
    "eq_lithography_source_transition_shell_capacity",
    "eq_lithography_source_inner_closed_shell_capacity",
    "eq_lithography_source_outer_shell_electron_count",
    "eq_lithography_source_inner_closed_shell_electron_count",
    "eq_lithography_source_transition_shell_occupancy",
    "eq_lithography_source_same_shell_screening_electron_count",
    "eq_lithography_source_inner_shell_screening_electron_count",
    "eq_lithography_source_screening_constant",
    "eq_lithography_source_effective_nuclear_charge",
]
