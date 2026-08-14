"""
scopes/physical_lithography_medium_formula_unit.py
==================================================

Formula-unit totals and rest mass for the imaging medium. Multiplying the
stoichiometric counts by per-component values gives the total proton,
neutron, and electron counts of one formula unit. The rest mass is not just
the sum of constituent masses: nuclear binding energy is subtracted through
the mass defect (E = mc^2 working in reverse), which is why the liquid-drop
layer below exists. This mass feeds the density closure above.
"""

import sympy as sp

from ..constants import ELECTRON_MASS, NEUTRON_MASS, PROTON_MASS, SPEED_OF_LIGHT
from ..core import Approximation, eq, var
from ..core.units import JOULE, KILOGRAM
from .physical_lithography_medium_binding import (
    lithography_medium_component_a_binding_energy,
    lithography_medium_component_b_binding_energy,
)
from .physical_lithography_medium_components import (
    LITHOGRAPHY_MEDIUM_COMPOSITION_REF,
    lithography_medium_component_a_neutron_count,
    lithography_medium_component_a_proton_count,
    lithography_medium_component_a_stoichiometric_count,
    lithography_medium_component_b_neutron_count,
    lithography_medium_component_b_proton_count,
    lithography_medium_component_b_stoichiometric_count,
)
from .physical_lithography_medium_intercomponent import (
    lithography_medium_formula_unit_intercomponent_binding_energy,
)


lithography_medium_formula_unit_proton_count = var(
    "physical.lithography.medium_formula_unit_proton_count", "Z_formula_litho_med", "count",
    "Total proton count in the representative formula unit of the lithography imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_formula_unit_neutron_count = var(
    "physical.lithography.medium_formula_unit_neutron_count", "N_formula_litho_med", "count",
    "Total neutron count in the representative formula unit of the lithography imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_formula_unit_electron_count = var(
    "physical.lithography.medium_formula_unit_electron_count", "e_formula_litho_med", "count",
    "Total bound electron count in the representative formula unit of the lithography imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_formula_unit_binding_energy = var(
    "physical.lithography.medium_formula_unit_binding_energy", "E_bind_formula_litho_med", "J",
    "Total nuclear, electronic, and chemical binding energy represented as a mass defect for one imaging-medium formula unit.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_formula_unit_rest_mass = var(
    "physical.lithography.medium_formula_unit_rest_mass", "m_formula_litho_med", "kg",
    "Rest mass of one representative formula unit of the lithography imaging medium.",
    scope="physical",
    positive=True,
    sp_units=KILOGRAM,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)


eq_lithography_medium_formula_unit_proton_count = eq(
    "physical.eq.lithography_medium_formula_unit_proton_count",
    lithography_medium_formula_unit_proton_count.symbol,
    (
        lithography_medium_component_a_stoichiometric_count.symbol
        * lithography_medium_component_a_proton_count.symbol
        + lithography_medium_component_b_stoichiometric_count.symbol
        * lithography_medium_component_b_proton_count.symbol
    ),
    "Formula-unit proton count from binary component stoichiometry.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_neutron_count = eq(
    "physical.eq.lithography_medium_formula_unit_neutron_count",
    lithography_medium_formula_unit_neutron_count.symbol,
    (
        lithography_medium_component_a_stoichiometric_count.symbol
        * lithography_medium_component_a_neutron_count.symbol
        + lithography_medium_component_b_stoichiometric_count.symbol
        * lithography_medium_component_b_neutron_count.symbol
    ),
    "Formula-unit neutron count from binary component stoichiometry.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_electron_count = eq(
    "physical.eq.lithography_medium_formula_unit_electron_count",
    lithography_medium_formula_unit_electron_count.symbol,
    lithography_medium_formula_unit_proton_count.symbol,
    "Neutral imaging-medium formula-unit electron count from total proton count.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_binding_energy = eq(
    "physical.eq.lithography_medium_formula_unit_binding_energy",
    lithography_medium_formula_unit_binding_energy.symbol,
    (
        lithography_medium_component_a_stoichiometric_count.symbol
        * lithography_medium_component_a_binding_energy.symbol
        + lithography_medium_component_b_stoichiometric_count.symbol
        * lithography_medium_component_b_binding_energy.symbol
        + lithography_medium_formula_unit_intercomponent_binding_energy.symbol
    ),
    "Formula-unit binding-energy mass defect from component and intercomponent terms.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_rest_mass = Approximation(
    "physical.eq.lithography_medium_formula_unit_rest_mass",
    lithography_medium_formula_unit_rest_mass.symbol,
    (
        lithography_medium_formula_unit_proton_count.symbol * PROTON_MASS.symbol
        + lithography_medium_formula_unit_neutron_count.symbol * NEUTRON_MASS.symbol
        + lithography_medium_formula_unit_electron_count.symbol * ELECTRON_MASS.symbol
        - lithography_medium_formula_unit_binding_energy.symbol / SPEED_OF_LIGHT.symbol**2
    ),
    (
        lithography_medium_formula_unit_binding_energy.symbol
        < (
            lithography_medium_formula_unit_proton_count.symbol * PROTON_MASS.symbol
            + lithography_medium_formula_unit_neutron_count.symbol * NEUTRON_MASS.symbol
            + lithography_medium_formula_unit_electron_count.symbol * ELECTRON_MASS.symbol
        )
        * SPEED_OF_LIGHT.symbol**2
    ),
    "Formula-unit rest mass from constituent proton, neutron, electron masses and binding-energy mass defect.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)


LITHOGRAPHY_MEDIUM_FORMULA_UNIT_VARIABLES = [
    lithography_medium_formula_unit_proton_count,
    lithography_medium_formula_unit_neutron_count,
    lithography_medium_formula_unit_electron_count,
    lithography_medium_formula_unit_binding_energy,
    lithography_medium_formula_unit_rest_mass,
]

LITHOGRAPHY_MEDIUM_FORMULA_UNIT_EQUATIONS = [
    eq_lithography_medium_formula_unit_proton_count,
    eq_lithography_medium_formula_unit_neutron_count,
    eq_lithography_medium_formula_unit_electron_count,
    eq_lithography_medium_formula_unit_binding_energy,
    eq_lithography_medium_formula_unit_rest_mass,
]


__all__ = [
    "lithography_medium_formula_unit_proton_count",
    "lithography_medium_formula_unit_neutron_count",
    "lithography_medium_formula_unit_electron_count",
    "lithography_medium_formula_unit_binding_energy",
    "lithography_medium_formula_unit_rest_mass",
    "eq_lithography_medium_formula_unit_proton_count",
    "eq_lithography_medium_formula_unit_neutron_count",
    "eq_lithography_medium_formula_unit_electron_count",
    "eq_lithography_medium_formula_unit_binding_energy",
    "eq_lithography_medium_formula_unit_rest_mass",
    "LITHOGRAPHY_MEDIUM_FORMULA_UNIT_VARIABLES",
    "LITHOGRAPHY_MEDIUM_FORMULA_UNIT_EQUATIONS",
]
