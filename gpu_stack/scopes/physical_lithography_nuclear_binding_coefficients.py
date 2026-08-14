"""
scopes/physical_lithography_nuclear_binding_coefficients.py
===========================================================

Shared semi-empirical liquid-drop calibration coefficients: volume,
surface, Coulomb, asymmetry, and pairing. These five numbers are the
nuclear-binding calibration boundary for every nucleus in the lithography
model -- the source isotope and both imaging-medium components. Each
consumer aliases these shared roots into its own coefficient variables
before applying its isotope-specific proton, neutron, mass-number, and
pairing structure. Calibrating once here keeps all nuclei on the same
footing.
"""

from ..core import Reference, VariableKind, var
from ..core.units import JOULE


LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF = Reference(
    citation=(
        "Shared semi-empirical mass-formula calibration: volume, surface, "
        "Coulomb, asymmetry, and pairing-gap coefficients are common nuclear "
        "liquid-drop calibration roots before source or medium isotope counts "
        "select the realized binding terms"
    ),
    kind="memo",
)


lithography_nuclear_binding_volume_coefficient = var(
    "physical.lithography.nuclear_binding_volume_coefficient",
    "a_vol_nuc_litho",
    "J",
    "Shared liquid-drop volume binding coefficient for lithography nuclear binding.",
    scope="physical",
    nonnegative=True,
    kind=VariableKind.ROOT_INPUT,
    sp_units=JOULE,
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
)
lithography_nuclear_binding_surface_coefficient = var(
    "physical.lithography.nuclear_binding_surface_coefficient",
    "a_surf_nuc_litho",
    "J",
    "Shared liquid-drop surface binding coefficient for lithography nuclear binding.",
    scope="physical",
    nonnegative=True,
    kind=VariableKind.ROOT_INPUT,
    sp_units=JOULE,
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
)
lithography_nuclear_binding_coulomb_coefficient = var(
    "physical.lithography.nuclear_binding_coulomb_coefficient",
    "a_coul_nuc_litho",
    "J",
    "Shared liquid-drop Coulomb binding coefficient for lithography nuclear binding.",
    scope="physical",
    positive=True,
    kind=VariableKind.ROOT_INPUT,
    sp_units=JOULE,
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
)
lithography_nuclear_binding_asymmetry_coefficient = var(
    "physical.lithography.nuclear_binding_asymmetry_coefficient",
    "a_asym_nuc_litho",
    "J",
    "Shared liquid-drop asymmetry binding coefficient for lithography nuclear binding.",
    scope="physical",
    nonnegative=True,
    kind=VariableKind.ROOT_INPUT,
    sp_units=JOULE,
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
)
lithography_nuclear_pairing_gap_reference_energy = var(
    "physical.lithography.nuclear_pairing_gap_reference_energy",
    "Delta_pair_ref_nuc_litho",
    "J",
    "Shared reference nuclear pairing gap energy for lithography liquid-drop calibration.",
    scope="physical",
    nonnegative=True,
    kind=VariableKind.ROOT_INPUT,
    sp_units=JOULE,
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
)


LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_VARIABLES = [
    lithography_nuclear_binding_volume_coefficient,
    lithography_nuclear_binding_surface_coefficient,
    lithography_nuclear_binding_coulomb_coefficient,
    lithography_nuclear_binding_asymmetry_coefficient,
    lithography_nuclear_pairing_gap_reference_energy,
]


LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_EXPORTS = [
    "LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF",
    "lithography_nuclear_binding_volume_coefficient",
    "lithography_nuclear_binding_surface_coefficient",
    "lithography_nuclear_binding_coulomb_coefficient",
    "lithography_nuclear_binding_asymmetry_coefficient",
    "lithography_nuclear_pairing_gap_reference_energy",
    "LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_VARIABLES",
    "LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_EXPORTS",
]


__all__ = LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_EXPORTS
