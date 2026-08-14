"""
scopes/physical_lithography_medium_intercomponent_binding.py
============================================================

Screened Coulomb binding energy of the A-B pair in the imaging medium.
The bond is modeled as two effective point charges separated by the
intercomponent distance, with the surrounding medium screening the
interaction through a relative permittivity. This ionic-style binding
energy is the chemical-scale counterpart of the nuclear binding terms and
enters the formula-unit energy accounting.
"""

import sympy as sp

from ..constants import ELEMENTARY_CHARGE, EPSILON_0
from ..core import Approximation
from .physical_lithography_medium_components import LITHOGRAPHY_MEDIUM_COMPOSITION_REF
from .physical_lithography_medium_intercomponent_variables import (
    lithography_medium_component_a_effective_intercomponent_charge_number,
    lithography_medium_component_b_effective_intercomponent_charge_number,
    lithography_medium_formula_unit_intercomponent_binding_energy,
    lithography_medium_formula_unit_intercomponent_pair_count,
    lithography_medium_intercomponent_effective_separation,
    lithography_medium_intercomponent_relative_permittivity,
)


eq_lithography_medium_formula_unit_intercomponent_binding_energy = Approximation(
    "physical.eq.lithography_medium_formula_unit_intercomponent_binding_energy",
    lithography_medium_formula_unit_intercomponent_binding_energy.symbol,
    (
        -lithography_medium_formula_unit_intercomponent_pair_count.symbol
        * lithography_medium_component_a_effective_intercomponent_charge_number.symbol
        * lithography_medium_component_b_effective_intercomponent_charge_number.symbol
        * ELEMENTARY_CHARGE.symbol**2
        / (
            sp.Integer(4)
            * sp.pi
            * EPSILON_0.symbol
            * lithography_medium_intercomponent_relative_permittivity.symbol
            * lithography_medium_intercomponent_effective_separation.symbol
        )
    ),
    sp.And(
        lithography_medium_component_a_effective_intercomponent_charge_number.symbol
        * lithography_medium_component_b_effective_intercomponent_charge_number.symbol
        < 0,
        lithography_medium_intercomponent_effective_separation.symbol > 0,
        lithography_medium_intercomponent_relative_permittivity.symbol > 0,
    ),
    "Intercomponent formula-unit binding from screened Coulomb attraction between effective ionic charge pairs.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)


LITHOGRAPHY_MEDIUM_INTERCOMPONENT_BINDING_EQUATIONS = [
    eq_lithography_medium_formula_unit_intercomponent_binding_energy,
]

LITHOGRAPHY_MEDIUM_INTERCOMPONENT_BINDING_EXPORTS = [
    "eq_lithography_medium_formula_unit_intercomponent_binding_energy",
]

__all__ = [
    *LITHOGRAPHY_MEDIUM_INTERCOMPONENT_BINDING_EXPORTS,
    "LITHOGRAPHY_MEDIUM_INTERCOMPONENT_BINDING_EQUATIONS",
    "LITHOGRAPHY_MEDIUM_INTERCOMPONENT_BINDING_EXPORTS",
]
