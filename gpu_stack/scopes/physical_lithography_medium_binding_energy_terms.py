"""
scopes/physical_lithography_medium_binding_energy_terms.py
==========================================================

Component liquid-drop binding-energy terms for lithography imaging media.
"""

import sympy as sp

from ..core import Approximation, var
from ..core.units import JOULE
from .physical_lithography_medium_binding_coefficients import (
    lithography_medium_component_binding_asymmetry_coefficient,
    lithography_medium_component_binding_coulomb_coefficient,
    lithography_medium_component_binding_surface_coefficient,
    lithography_medium_component_binding_volume_coefficient,
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


lithography_medium_component_a_binding_volume_term = var(
    "physical.lithography.medium_component_a_binding_volume_term",
    "E_vol_bind_A_litho_med",
    "J",
    "Volume contribution to component A nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_binding_volume_term = var(
    "physical.lithography.medium_component_b_binding_volume_term",
    "E_vol_bind_B_litho_med",
    "J",
    "Volume contribution to component B nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_binding_surface_term = var(
    "physical.lithography.medium_component_a_binding_surface_term",
    "E_surf_bind_A_litho_med",
    "J",
    "Surface penalty contribution to component A nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_binding_surface_term = var(
    "physical.lithography.medium_component_b_binding_surface_term",
    "E_surf_bind_B_litho_med",
    "J",
    "Surface penalty contribution to component B nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_binding_coulomb_term = var(
    "physical.lithography.medium_component_a_binding_coulomb_term",
    "E_coul_bind_A_litho_med",
    "J",
    "Coulomb repulsion penalty contribution to component A nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_binding_coulomb_term = var(
    "physical.lithography.medium_component_b_binding_coulomb_term",
    "E_coul_bind_B_litho_med",
    "J",
    "Coulomb repulsion penalty contribution to component B nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_binding_asymmetry_term = var(
    "physical.lithography.medium_component_a_binding_asymmetry_term",
    "E_asym_bind_A_litho_med",
    "J",
    "Neutron-proton asymmetry penalty contribution to component A nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_binding_asymmetry_term = var(
    "physical.lithography.medium_component_b_binding_asymmetry_term",
    "E_asym_bind_B_litho_med",
    "J",
    "Neutron-proton asymmetry penalty contribution to component B nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_binding_pairing_term = var(
    "physical.lithography.medium_component_a_binding_pairing_term",
    "E_pair_bind_A_litho_med",
    "J",
    "Pairing contribution to component A nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_binding_pairing_term = var(
    "physical.lithography.medium_component_b_binding_pairing_term",
    "E_pair_bind_B_litho_med",
    "J",
    "Pairing contribution to component B nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_binding_energy = var(
    "physical.lithography.medium_component_a_binding_energy", "E_bind_A_litho_med", "J",
    "Binding-energy mass defect represented by one component A unit.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_binding_energy = var(
    "physical.lithography.medium_component_b_binding_energy", "E_bind_B_litho_med", "J",
    "Binding-energy mass defect represented by one component B unit.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
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


LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_VARIABLES = [
    lithography_medium_component_a_binding_volume_term,
    lithography_medium_component_b_binding_volume_term,
    lithography_medium_component_a_binding_surface_term,
    lithography_medium_component_b_binding_surface_term,
    lithography_medium_component_a_binding_coulomb_term,
    lithography_medium_component_b_binding_coulomb_term,
    lithography_medium_component_a_binding_asymmetry_term,
    lithography_medium_component_b_binding_asymmetry_term,
    lithography_medium_component_a_binding_pairing_term,
    lithography_medium_component_b_binding_pairing_term,
    lithography_medium_component_a_binding_energy,
    lithography_medium_component_b_binding_energy,
]

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

LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_EXPORTS = [
    "lithography_medium_component_a_binding_volume_term",
    "lithography_medium_component_b_binding_volume_term",
    "lithography_medium_component_a_binding_surface_term",
    "lithography_medium_component_b_binding_surface_term",
    "lithography_medium_component_a_binding_coulomb_term",
    "lithography_medium_component_b_binding_coulomb_term",
    "lithography_medium_component_a_binding_asymmetry_term",
    "lithography_medium_component_b_binding_asymmetry_term",
    "lithography_medium_component_a_binding_pairing_term",
    "lithography_medium_component_b_binding_pairing_term",
    "lithography_medium_component_a_binding_energy",
    "lithography_medium_component_b_binding_energy",
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

__all__ = [*LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_EXPORTS]
