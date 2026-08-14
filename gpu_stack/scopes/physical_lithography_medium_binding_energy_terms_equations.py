"""
scopes/physical_lithography_medium_binding_energy_terms_equations.py
====================================================================

Equations for the liquid-drop binding-energy terms of each imaging-medium
component nucleus. Each term follows the semi-empirical mass formula: the
volume term grows with mass number A, the surface term with A^(2/3), the
Coulomb term with Z(Z-1)/A^(1/3), the asymmetry term with (N-Z)^2/A, and
the pairing term alternates sign with nucleon parity. Summing them gives
each component binding energy, which the formula-unit layer converts into a
rest mass through the mass defect.
"""

import sympy as sp

from ..core import Approximation
from .physical_lithography_medium_binding_coefficients import (
    lithography_medium_component_binding_asymmetry_coefficient,
    lithography_medium_component_binding_coulomb_coefficient,
    lithography_medium_component_binding_surface_coefficient,
    lithography_medium_component_binding_volume_coefficient,
)
from .physical_lithography_medium_binding_energy_terms_variables import (
    lithography_medium_component_a_binding_asymmetry_term,
    lithography_medium_component_a_binding_coulomb_term,
    lithography_medium_component_a_binding_energy,
    lithography_medium_component_a_binding_pairing_term,
    lithography_medium_component_a_binding_surface_term,
    lithography_medium_component_a_binding_volume_term,
    lithography_medium_component_b_binding_asymmetry_term,
    lithography_medium_component_b_binding_coulomb_term,
    lithography_medium_component_b_binding_energy,
    lithography_medium_component_b_binding_pairing_term,
    lithography_medium_component_b_binding_surface_term,
    lithography_medium_component_b_binding_volume_term,
)
from .physical_lithography_medium_binding_nuclear_state import (
    lithography_medium_component_a_binding_pairing_coefficient,
    lithography_medium_component_a_neutron_excess,
    lithography_medium_component_a_pairing_sign,
    lithography_medium_component_b_binding_pairing_coefficient,
    lithography_medium_component_b_neutron_excess,
    lithography_medium_component_b_pairing_sign,
)
from .physical_lithography_medium_components import (
    LITHOGRAPHY_MEDIUM_COMPOSITION_REF,
    lithography_medium_component_a_isotope_mass_number,
    lithography_medium_component_a_proton_count,
    lithography_medium_component_b_isotope_mass_number,
    lithography_medium_component_b_proton_count,
)


eq_lithography_medium_component_a_binding_volume_term = Approximation(
    "physical.eq.lithography_medium_component_a_binding_volume_term",
    lithography_medium_component_a_binding_volume_term.symbol,
    lithography_medium_component_binding_volume_coefficient.symbol
    * lithography_medium_component_a_isotope_mass_number.symbol,
    lithography_medium_component_a_isotope_mass_number.symbol > 0,
    "Component A liquid-drop volume binding term.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_binding_volume_term = Approximation(
    "physical.eq.lithography_medium_component_b_binding_volume_term",
    lithography_medium_component_b_binding_volume_term.symbol,
    lithography_medium_component_binding_volume_coefficient.symbol
    * lithography_medium_component_b_isotope_mass_number.symbol,
    lithography_medium_component_b_isotope_mass_number.symbol > 0,
    "Component B liquid-drop volume binding term.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_a_binding_surface_term = Approximation(
    "physical.eq.lithography_medium_component_a_binding_surface_term",
    lithography_medium_component_a_binding_surface_term.symbol,
    lithography_medium_component_binding_surface_coefficient.symbol
    * lithography_medium_component_a_isotope_mass_number.symbol**sp.Rational(2, 3),
    lithography_medium_component_a_isotope_mass_number.symbol > 0,
    "Component A liquid-drop surface binding penalty term.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_binding_surface_term = Approximation(
    "physical.eq.lithography_medium_component_b_binding_surface_term",
    lithography_medium_component_b_binding_surface_term.symbol,
    lithography_medium_component_binding_surface_coefficient.symbol
    * lithography_medium_component_b_isotope_mass_number.symbol**sp.Rational(2, 3),
    lithography_medium_component_b_isotope_mass_number.symbol > 0,
    "Component B liquid-drop surface binding penalty term.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_a_binding_coulomb_term = Approximation(
    "physical.eq.lithography_medium_component_a_binding_coulomb_term",
    lithography_medium_component_a_binding_coulomb_term.symbol,
    lithography_medium_component_binding_coulomb_coefficient.symbol
    * lithography_medium_component_a_proton_count.symbol
    * (lithography_medium_component_a_proton_count.symbol - 1)
    / lithography_medium_component_a_isotope_mass_number.symbol**sp.Rational(1, 3),
    lithography_medium_component_a_isotope_mass_number.symbol > 0,
    "Component A liquid-drop Coulomb repulsion binding penalty term.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_binding_coulomb_term = Approximation(
    "physical.eq.lithography_medium_component_b_binding_coulomb_term",
    lithography_medium_component_b_binding_coulomb_term.symbol,
    lithography_medium_component_binding_coulomb_coefficient.symbol
    * lithography_medium_component_b_proton_count.symbol
    * (lithography_medium_component_b_proton_count.symbol - 1)
    / lithography_medium_component_b_isotope_mass_number.symbol**sp.Rational(1, 3),
    lithography_medium_component_b_isotope_mass_number.symbol > 0,
    "Component B liquid-drop Coulomb repulsion binding penalty term.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_a_binding_asymmetry_term = Approximation(
    "physical.eq.lithography_medium_component_a_binding_asymmetry_term",
    lithography_medium_component_a_binding_asymmetry_term.symbol,
    lithography_medium_component_binding_asymmetry_coefficient.symbol
    * lithography_medium_component_a_neutron_excess.symbol**2
    / lithography_medium_component_a_isotope_mass_number.symbol,
    lithography_medium_component_a_isotope_mass_number.symbol > 0,
    "Component A liquid-drop neutron-proton asymmetry binding penalty term.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_binding_asymmetry_term = Approximation(
    "physical.eq.lithography_medium_component_b_binding_asymmetry_term",
    lithography_medium_component_b_binding_asymmetry_term.symbol,
    lithography_medium_component_binding_asymmetry_coefficient.symbol
    * lithography_medium_component_b_neutron_excess.symbol**2
    / lithography_medium_component_b_isotope_mass_number.symbol,
    lithography_medium_component_b_isotope_mass_number.symbol > 0,
    "Component B liquid-drop neutron-proton asymmetry binding penalty term.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_a_binding_pairing_term = Approximation(
    "physical.eq.lithography_medium_component_a_binding_pairing_term",
    lithography_medium_component_a_binding_pairing_term.symbol,
    lithography_medium_component_a_pairing_sign.symbol
    * lithography_medium_component_a_binding_pairing_coefficient.symbol
    / sp.sqrt(lithography_medium_component_a_isotope_mass_number.symbol),
    lithography_medium_component_a_isotope_mass_number.symbol > 0,
    "Component A liquid-drop pairing contribution.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_binding_pairing_term = Approximation(
    "physical.eq.lithography_medium_component_b_binding_pairing_term",
    lithography_medium_component_b_binding_pairing_term.symbol,
    lithography_medium_component_b_pairing_sign.symbol
    * lithography_medium_component_b_binding_pairing_coefficient.symbol
    / sp.sqrt(lithography_medium_component_b_isotope_mass_number.symbol),
    lithography_medium_component_b_isotope_mass_number.symbol > 0,
    "Component B liquid-drop pairing contribution.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_a_binding_energy = Approximation(
    "physical.eq.lithography_medium_component_a_binding_energy",
    lithography_medium_component_a_binding_energy.symbol,
    lithography_medium_component_a_binding_volume_term.symbol
    - lithography_medium_component_a_binding_surface_term.symbol
    - lithography_medium_component_a_binding_coulomb_term.symbol
    - lithography_medium_component_a_binding_asymmetry_term.symbol
    + lithography_medium_component_a_binding_pairing_term.symbol,
    lithography_medium_component_a_isotope_mass_number.symbol > 0,
    "Semi-empirical liquid-drop nuclear binding energy for medium component A.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_binding_energy = Approximation(
    "physical.eq.lithography_medium_component_b_binding_energy",
    lithography_medium_component_b_binding_energy.symbol,
    lithography_medium_component_b_binding_volume_term.symbol
    - lithography_medium_component_b_binding_surface_term.symbol
    - lithography_medium_component_b_binding_coulomb_term.symbol
    - lithography_medium_component_b_binding_asymmetry_term.symbol
    + lithography_medium_component_b_binding_pairing_term.symbol,
    lithography_medium_component_b_isotope_mass_number.symbol > 0,
    "Semi-empirical liquid-drop nuclear binding energy for medium component B.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)


LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_EQUATIONS = [
    eq_lithography_medium_component_a_binding_volume_term,
    eq_lithography_medium_component_b_binding_volume_term,
    eq_lithography_medium_component_a_binding_surface_term,
    eq_lithography_medium_component_b_binding_surface_term,
    eq_lithography_medium_component_a_binding_coulomb_term,
    eq_lithography_medium_component_b_binding_coulomb_term,
    eq_lithography_medium_component_a_binding_asymmetry_term,
    eq_lithography_medium_component_b_binding_asymmetry_term,
    eq_lithography_medium_component_a_binding_pairing_term,
    eq_lithography_medium_component_b_binding_pairing_term,
    eq_lithography_medium_component_a_binding_energy,
    eq_lithography_medium_component_b_binding_energy,
]

LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_EQUATION_EXPORTS = [
    "eq_lithography_medium_component_a_binding_volume_term",
    "eq_lithography_medium_component_b_binding_volume_term",
    "eq_lithography_medium_component_a_binding_surface_term",
    "eq_lithography_medium_component_b_binding_surface_term",
    "eq_lithography_medium_component_a_binding_coulomb_term",
    "eq_lithography_medium_component_b_binding_coulomb_term",
    "eq_lithography_medium_component_a_binding_asymmetry_term",
    "eq_lithography_medium_component_b_binding_asymmetry_term",
    "eq_lithography_medium_component_a_binding_pairing_term",
    "eq_lithography_medium_component_b_binding_pairing_term",
    "eq_lithography_medium_component_a_binding_energy",
    "eq_lithography_medium_component_b_binding_energy",
]


__all__ = [*LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_EQUATION_EXPORTS]
