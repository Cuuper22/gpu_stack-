"""
scopes/physical_lithography_source_variables.py
================================================

Variables and shared reference for the lithography exposure source closure.
"""

import sympy as sp

from ..core import Reference, var
from ..core.units import JOULE, KILOGRAM


LITHOGRAPHY_SOURCE_REF = Reference(
    citation=(
        "Lithography source abstraction: photon energy from nuclear mass defect, "
        "electron-nucleus reduced mass, screened effective charge, and a "
        "hydrogenic transition approximation"
    ),
    kind="memo",
)


lithography_photon_energy = var(
    "physical.lithography.photon_energy", "E_photon_litho", "J",
    "Photon energy of the lithography exposure source.",
    scope="physical",
    positive=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_nuclear_binding_energy = var(
    "physical.lithography.source_nuclear_binding_energy", "E_bind_litho_src", "J",
    "Nuclear binding energy of the emitting source isotope.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_mass_number = var(
    "physical.lithography.source_mass_number", "A_litho_src", "count",
    "Total nucleon count alias for the emitting source isotope mass-number descriptor.",
    scope="physical",
    integer=True,
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_neutron_excess = var(
    "physical.lithography.source_neutron_excess", "Delta_NZ_litho_src", "count",
    "Neutron-proton count difference for the emitting source isotope.",
    scope="physical",
    signed=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_pairing_sign = var(
    "physical.lithography.source_pairing_sign", "s_pair_litho_src", "dimensionless",
    "Pairing selector: +1 for even-even, 0 for odd-A, -1 for odd-odd source nuclei.",
    scope="physical",
    integer=True,
    signed=True,
    value_range=(-1.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_binding_volume_term = var(
    "physical.lithography.source_binding_volume_term", "E_vol_bind_litho_src", "J",
    "Volume contribution to source nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_binding_surface_term = var(
    "physical.lithography.source_binding_surface_term", "E_surf_bind_litho_src", "J",
    "Surface penalty contribution to source nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_binding_coulomb_term = var(
    "physical.lithography.source_binding_coulomb_term", "E_coul_bind_litho_src", "J",
    "Coulomb repulsion penalty contribution to source nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_binding_asymmetry_term = var(
    "physical.lithography.source_binding_asymmetry_term", "E_asym_bind_litho_src", "J",
    "Neutron-proton asymmetry penalty contribution to source nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_binding_pairing_term = var(
    "physical.lithography.source_binding_pairing_term", "E_pair_bind_litho_src", "J",
    "Pairing contribution to source nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_nuclear_mass = var(
    "physical.lithography.source_nuclear_mass", "m_nuc_litho_src", "kg",
    "Nuclear rest mass of the emitting source isotope.",
    scope="physical",
    sp_units=KILOGRAM,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_reduced_mass = var(
    "physical.lithography.source_reduced_mass", "mu_litho_src", "kg",
    "Electron-nucleus reduced mass for the emitting source transition.",
    scope="physical",
    sp_units=KILOGRAM,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_reduced_mass_ratio = var(
    "physical.lithography.source_reduced_mass_ratio", "eta_mu_litho_src", "dimensionless",
    "Reduced-mass correction relative to the electron mass.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_transition_energy = var(
    "physical.lithography.source_transition_energy", "E_transition_litho_src", "J",
    "Approximate bound-state transition energy emitted by the lithography source species.",
    scope="physical",
    positive=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)


_LITHOGRAPHY_SOURCE_PRE_ELECTRONIC_VARIABLES = [
    lithography_photon_energy,
    lithography_source_nuclear_binding_energy,
    lithography_source_mass_number,
    lithography_source_neutron_excess,
    lithography_source_pairing_sign,
    lithography_source_binding_volume_term,
    lithography_source_binding_surface_term,
    lithography_source_binding_coulomb_term,
    lithography_source_binding_asymmetry_term,
    lithography_source_binding_pairing_term,
    lithography_source_nuclear_mass,
    lithography_source_reduced_mass,
    lithography_source_reduced_mass_ratio,
]

_LITHOGRAPHY_SOURCE_TRANSITION_VARIABLES = [
    lithography_source_transition_energy,
]

_LITHOGRAPHY_SOURCE_VARIABLE_EXPORTS = [
    "LITHOGRAPHY_SOURCE_REF",
    "lithography_photon_energy",
    "lithography_source_nuclear_binding_energy",
    "lithography_source_mass_number",
    "lithography_source_neutron_excess",
    "lithography_source_pairing_sign",
    "lithography_source_binding_volume_term",
    "lithography_source_binding_surface_term",
    "lithography_source_binding_coulomb_term",
    "lithography_source_binding_asymmetry_term",
    "lithography_source_binding_pairing_term",
    "lithography_source_nuclear_mass",
    "lithography_source_reduced_mass",
    "lithography_source_reduced_mass_ratio",
    "lithography_source_transition_energy",
]


__all__ = _LITHOGRAPHY_SOURCE_VARIABLE_EXPORTS
