"""
scopes/physical_lithography_medium_components_isotope_state.py
==============================================================

Isotope composition variables for lithography imaging-medium components.
"""

import sympy as sp

from ..core import var
from .physical_lithography_medium_components_reference import (
    LITHOGRAPHY_MEDIUM_COMPOSITION_REF,
)


lithography_medium_component_a_valence_up_quark_count = var(
    "physical.lithography.medium_component_a_valence_up_quark_count",
    "N_u_val_A_litho_med",
    "count",
    "Total valence up-quark count in one component A isotope of the imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_valence_down_quark_count = var(
    "physical.lithography.medium_component_a_valence_down_quark_count",
    "N_d_val_A_litho_med",
    "count",
    "Total valence down-quark count in one component A isotope of the imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_valence_up_quark_count = var(
    "physical.lithography.medium_component_b_valence_up_quark_count",
    "N_u_val_B_litho_med",
    "count",
    "Total valence up-quark count in one component B isotope of the imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_valence_down_quark_count = var(
    "physical.lithography.medium_component_b_valence_down_quark_count",
    "N_d_val_B_litho_med",
    "count",
    "Total valence down-quark count in one component B isotope of the imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_proton_count = var(
    "physical.lithography.medium_component_a_proton_count", "Z_A_litho_med", "count",
    "Proton count of component A in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_proton_count = var(
    "physical.lithography.medium_component_b_proton_count", "Z_B_litho_med", "count",
    "Proton count of component B in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_neutron_count = var(
    "physical.lithography.medium_component_a_neutron_count", "N_A_litho_med", "count",
    "Neutron count of component A in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_neutron_count = var(
    "physical.lithography.medium_component_b_neutron_count", "N_B_litho_med", "count",
    "Neutron count of component B in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_atomic_number = var(
    "physical.lithography.medium_component_a_atomic_number", "Z_atom_A_litho_med", "count",
    "Atomic number of component A in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_atomic_number = var(
    "physical.lithography.medium_component_b_atomic_number", "Z_atom_B_litho_med", "count",
    "Atomic number of component B in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_isotope_mass_number = var(
    "physical.lithography.medium_component_a_isotope_mass_number", "A_iso_A_litho_med", "count",
    "Mass number of component A in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_isotope_mass_number = var(
    "physical.lithography.medium_component_b_isotope_mass_number", "A_iso_B_litho_med", "count",
    "Mass number of component B in the representative imaging-medium formula unit.",
    scope="physical",
    integer=True,
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)


LITHOGRAPHY_MEDIUM_COMPONENT_ISOTOPE_STATE_VARIABLES = [
    lithography_medium_component_a_valence_up_quark_count,
    lithography_medium_component_a_valence_down_quark_count,
    lithography_medium_component_b_valence_up_quark_count,
    lithography_medium_component_b_valence_down_quark_count,
    lithography_medium_component_a_proton_count,
    lithography_medium_component_b_proton_count,
    lithography_medium_component_a_neutron_count,
    lithography_medium_component_b_neutron_count,
    lithography_medium_component_a_atomic_number,
    lithography_medium_component_b_atomic_number,
    lithography_medium_component_a_isotope_mass_number,
    lithography_medium_component_b_isotope_mass_number,
]


LITHOGRAPHY_MEDIUM_COMPONENT_ISOTOPE_STATE_EXPORTS = [
    "lithography_medium_component_a_valence_up_quark_count",
    "lithography_medium_component_a_valence_down_quark_count",
    "lithography_medium_component_b_valence_up_quark_count",
    "lithography_medium_component_b_valence_down_quark_count",
    "lithography_medium_component_a_proton_count",
    "lithography_medium_component_b_proton_count",
    "lithography_medium_component_a_neutron_count",
    "lithography_medium_component_b_neutron_count",
    "lithography_medium_component_a_atomic_number",
    "lithography_medium_component_b_atomic_number",
    "lithography_medium_component_a_isotope_mass_number",
    "lithography_medium_component_b_isotope_mass_number",
]


__all__ = [*LITHOGRAPHY_MEDIUM_COMPONENT_ISOTOPE_STATE_EXPORTS]
