"""
scopes/physical_lithography_medium_intercomponent_charge.py
===========================================================

Charge bookkeeping for the A-B bond. A fixed number of electrons is
transferred per formula unit; times the elementary charge this sets the
charge unit, and spread over the stoichiometry it gives the effective
charge numbers on components A and B (equal and opposite). The pair count
says how many A-B contacts one formula unit contributes to the binding
sum.
"""

from ..core import Inequality, eq
from .physical_lithography_medium_components import (
    LITHOGRAPHY_MEDIUM_COMPOSITION_REF,
    lithography_medium_component_a_proton_count,
    lithography_medium_component_a_stoichiometric_count,
    lithography_medium_component_b_proton_count,
    lithography_medium_component_b_stoichiometric_count,
)
from .physical_lithography_medium_intercomponent_variables import (
    lithography_medium_component_a_effective_intercomponent_charge_number,
    lithography_medium_component_b_effective_intercomponent_charge_number,
    lithography_medium_formula_unit_intercomponent_charge_transfer_electron_count,
    lithography_medium_formula_unit_intercomponent_pair_count,
    lithography_medium_intercomponent_charge_unit,
)


ineq_lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_a_electron_inventory = Inequality(
    "physical.ineq.lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_a_electron_inventory",
    lithography_medium_formula_unit_intercomponent_charge_transfer_electron_count.symbol,
    (
        lithography_medium_component_a_stoichiometric_count.symbol
        * lithography_medium_component_a_proton_count.symbol
    ),
    "<=",
    "Formula-unit intercomponent charge transfer cannot exceed the neutral component-A electron inventory.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
ineq_lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_b_electron_inventory = Inequality(
    "physical.ineq.lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_b_electron_inventory",
    lithography_medium_formula_unit_intercomponent_charge_transfer_electron_count.symbol,
    (
        lithography_medium_component_b_stoichiometric_count.symbol
        * lithography_medium_component_b_proton_count.symbol
    ),
    "<=",
    "Formula-unit intercomponent charge transfer cannot exceed the neutral component-B electron inventory.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_intercomponent_charge_unit_from_formula_unit_charge_transfer = eq(
    "physical.eq.lithography_medium_intercomponent_charge_unit_from_formula_unit_charge_transfer",
    lithography_medium_intercomponent_charge_unit.symbol,
    (
        lithography_medium_formula_unit_intercomponent_charge_transfer_electron_count.symbol
        / (
            lithography_medium_component_a_stoichiometric_count.symbol
            * lithography_medium_component_b_stoichiometric_count.symbol
        )
    ),
    "Intercomponent charge-unit magnitude from formula-unit charge transfer normalized by binary stoichiometric pair count.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_a_effective_intercomponent_charge_number = eq(
    "physical.eq.lithography_medium_component_a_effective_intercomponent_charge_number",
    lithography_medium_component_a_effective_intercomponent_charge_number.symbol,
    (
        lithography_medium_component_b_stoichiometric_count.symbol
        * lithography_medium_intercomponent_charge_unit.symbol
    ),
    "Component-A effective intercomponent charge from binary stoichiometry and a shared charge-unit magnitude.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_effective_intercomponent_charge_number = eq(
    "physical.eq.lithography_medium_component_b_effective_intercomponent_charge_number",
    lithography_medium_component_b_effective_intercomponent_charge_number.symbol,
    (
        -lithography_medium_component_a_stoichiometric_count.symbol
        * lithography_medium_intercomponent_charge_unit.symbol
    ),
    "Component-B effective intercomponent charge from binary stoichiometry and a shared charge-unit magnitude.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_intercomponent_pair_count = eq(
    "physical.eq.lithography_medium_formula_unit_intercomponent_pair_count",
    lithography_medium_formula_unit_intercomponent_pair_count.symbol,
    (
        lithography_medium_component_a_stoichiometric_count.symbol
        * lithography_medium_component_b_stoichiometric_count.symbol
    ),
    "Formula-unit intercomponent pair count from binary component stoichiometry.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)


LITHOGRAPHY_MEDIUM_INTERCOMPONENT_CHARGE_EQUATIONS = [
    ineq_lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_a_electron_inventory,
    ineq_lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_b_electron_inventory,
    eq_lithography_medium_intercomponent_charge_unit_from_formula_unit_charge_transfer,
    eq_lithography_medium_component_a_effective_intercomponent_charge_number,
    eq_lithography_medium_component_b_effective_intercomponent_charge_number,
    eq_lithography_medium_formula_unit_intercomponent_pair_count,
]

LITHOGRAPHY_MEDIUM_INTERCOMPONENT_CHARGE_EXPORTS = [
    "ineq_lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_a_electron_inventory",
    "ineq_lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_b_electron_inventory",
    "eq_lithography_medium_intercomponent_charge_unit_from_formula_unit_charge_transfer",
    "eq_lithography_medium_component_a_effective_intercomponent_charge_number",
    "eq_lithography_medium_component_b_effective_intercomponent_charge_number",
    "eq_lithography_medium_formula_unit_intercomponent_pair_count",
]

__all__ = [
    *LITHOGRAPHY_MEDIUM_INTERCOMPONENT_CHARGE_EXPORTS,
    "LITHOGRAPHY_MEDIUM_INTERCOMPONENT_CHARGE_EQUATIONS",
    "LITHOGRAPHY_MEDIUM_INTERCOMPONENT_CHARGE_EXPORTS",
]
