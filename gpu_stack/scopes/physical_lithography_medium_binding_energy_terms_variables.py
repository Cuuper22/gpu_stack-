"""
scopes/physical_lithography_medium_binding_energy_terms_variables.py
====================================================================

Variables for component liquid-drop binding-energy terms.
"""

from ..core import var
from ..core.units import JOULE
from .physical_lithography_medium_components import LITHOGRAPHY_MEDIUM_COMPOSITION_REF


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

LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_VARIABLE_EXPORTS = [
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
]


__all__ = [*LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_VARIABLE_EXPORTS]
