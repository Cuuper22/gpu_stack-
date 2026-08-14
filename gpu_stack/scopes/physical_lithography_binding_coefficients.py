"""
scopes/physical_lithography_binding_coefficients.py
===================================================

Liquid-drop coefficients for the source nucleus. The semi-empirical mass
formula treats a nucleus like a charged liquid drop: binding energy is a
volume term minus surface, Coulomb, asymmetry, and pairing corrections,
each scaled by an empirical coefficient. Those coefficients are the
calibration boundary here; everything else is reconstructed from them. The
Coulomb coefficient sets the nuclear radius scale, the radius sets the
saturation number density, and the volume, surface, and asymmetry
coefficients set the bulk binding-energy density, surface tension, and
symmetry-energy density of nuclear matter.
"""

import sympy as sp

from ..constants import ELEMENTARY_CHARGE, EPSILON_0
from ..core import Approximation, Reference, ge, gt, var
from ..core.units import JOULE, METER
from .physical_lithography_nuclear_binding_coefficients import *
from .physical_lithography_nuclear_binding_coefficients import (
    LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_EXPORTS,
    LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF,
    LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_VARIABLES,
)


LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF = Reference(
    citation=(
        "Liquid-drop nuclear binding coefficients calibrated as empirical "
        "source terms: Coulomb coefficient fixes the uniformly charged sphere "
        "radius scale R = r0 A^(1/3); volume, surface, and asymmetry "
        "coefficients reconstruct bulk binding density, nuclear surface "
        "tension, and symmetry-energy density; pairing coefficient follows "
        "from a reference pairing gap calibration scale"
    ),
    kind="memo",
)


lithography_source_nuclear_saturation_number_density = var(
    "physical.lithography.source_nuclear_saturation_number_density", "n0_litho_src", "1/m^3",
    "Effective saturation nucleon number density for the lithography source nuclear liquid-drop radius law.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1) / METER**3,
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
)
lithography_source_nuclear_radius_coefficient = var(
    "physical.lithography.source_nuclear_radius_coefficient", "r0_litho_src", "m",
    "Nuclear radius coefficient for the lithography source isotope radius law R = r0 A^(1/3).",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
)
lithography_source_nuclear_bulk_binding_energy_density = var(
    "physical.lithography.source_nuclear_bulk_binding_energy_density", "u_bulk_bind_litho_src", "J/m^3",
    "Effective bulk nuclear binding energy density for the lithography source liquid-drop volume term.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE / METER**3,
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
)
lithography_source_binding_volume_coefficient = var(
    "physical.lithography.source_binding_volume_coefficient", "a_vol_litho_src", "J",
    "Empirical liquid-drop volume binding coefficient for source nuclear binding.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
)
lithography_source_nuclear_surface_tension = var(
    "physical.lithography.source_nuclear_surface_tension", "sigma_nuc_surf_litho_src", "J/m^2",
    "Effective nuclear surface tension for the lithography source liquid-drop surface penalty.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE / METER**2,
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
)
lithography_source_binding_surface_coefficient = var(
    "physical.lithography.source_binding_surface_coefficient", "a_surf_litho_src", "J",
    "Empirical liquid-drop surface binding coefficient for source nuclear binding.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
)
lithography_source_nuclear_symmetry_energy_density = var(
    "physical.lithography.source_nuclear_symmetry_energy_density", "u_sym_litho_src", "J/m^3",
    "Effective nuclear symmetry energy density for the lithography source liquid-drop asymmetry term.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE / METER**3,
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
)
lithography_source_binding_asymmetry_coefficient = var(
    "physical.lithography.source_binding_asymmetry_coefficient", "a_asym_litho_src", "J",
    "Empirical liquid-drop asymmetry coefficient for source nuclear binding.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
)
lithography_source_nuclear_pairing_gap_reference_energy = var(
    "physical.lithography.source_nuclear_pairing_gap_reference_energy", "Delta_pair_ref_litho_src", "J",
    "Reference nuclear pairing gap energy for calibrating the lithography source liquid-drop pairing coefficient.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
)
lithography_source_pairing_reference_mass_number = var(
    "physical.lithography.source_pairing_reference_mass_number", "A_pair_ref_litho_src", "count",
    "Reference mass number at which the nuclear pairing gap calibrates the liquid-drop pairing coefficient.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
)
lithography_source_binding_pairing_coefficient = var(
    "physical.lithography.source_binding_pairing_coefficient", "a_pair_litho_src", "J",
    "Liquid-drop pairing coefficient derived from a reference pairing gap and reference mass number.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
)
lithography_source_binding_coulomb_coefficient = var(
    "physical.lithography.source_binding_coulomb_coefficient", "a_coul_litho_src", "J",
    "Empirical liquid-drop Coulomb binding coefficient for source nuclear binding.",
    scope="physical",
    positive=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
)


eq_lithography_source_binding_volume_coefficient_from_shared_nuclear_calibration = Approximation(
    "physical.eq.lithography_source_binding_volume_coefficient_from_shared_nuclear_calibration",
    lithography_source_binding_volume_coefficient.symbol,
    lithography_nuclear_binding_volume_coefficient.symbol,
    ge(lithography_nuclear_binding_volume_coefficient.symbol, 0),
    "Source liquid-drop volume coefficient from shared nuclear binding calibration.",
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_source_binding_surface_coefficient_from_shared_nuclear_calibration = Approximation(
    "physical.eq.lithography_source_binding_surface_coefficient_from_shared_nuclear_calibration",
    lithography_source_binding_surface_coefficient.symbol,
    lithography_nuclear_binding_surface_coefficient.symbol,
    ge(lithography_nuclear_binding_surface_coefficient.symbol, 0),
    "Source liquid-drop surface coefficient from shared nuclear binding calibration.",
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_source_binding_coulomb_coefficient_from_shared_nuclear_calibration = Approximation(
    "physical.eq.lithography_source_binding_coulomb_coefficient_from_shared_nuclear_calibration",
    lithography_source_binding_coulomb_coefficient.symbol,
    lithography_nuclear_binding_coulomb_coefficient.symbol,
    gt(lithography_nuclear_binding_coulomb_coefficient.symbol, 0),
    "Source liquid-drop Coulomb coefficient from shared nuclear binding calibration.",
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_source_binding_asymmetry_coefficient_from_shared_nuclear_calibration = Approximation(
    "physical.eq.lithography_source_binding_asymmetry_coefficient_from_shared_nuclear_calibration",
    lithography_source_binding_asymmetry_coefficient.symbol,
    lithography_nuclear_binding_asymmetry_coefficient.symbol,
    ge(lithography_nuclear_binding_asymmetry_coefficient.symbol, 0),
    "Source liquid-drop asymmetry coefficient from shared nuclear binding calibration.",
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_source_nuclear_pairing_gap_reference_energy_from_shared_nuclear_calibration = Approximation(
    "physical.eq.lithography_source_nuclear_pairing_gap_reference_energy_from_shared_nuclear_calibration",
    lithography_source_nuclear_pairing_gap_reference_energy.symbol,
    lithography_nuclear_pairing_gap_reference_energy.symbol,
    ge(lithography_nuclear_pairing_gap_reference_energy.symbol, 0),
    "Source pairing-gap reference energy from shared nuclear binding calibration.",
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_source_nuclear_radius_coefficient = Approximation(
    "physical.eq.lithography_source_nuclear_radius_coefficient",
    lithography_source_nuclear_radius_coefficient.symbol,
    (
        sp.Integer(3)
        * ELEMENTARY_CHARGE.symbol**2
        / (
            sp.Integer(20)
            * sp.pi
            * EPSILON_0.symbol
            * lithography_source_binding_coulomb_coefficient.symbol
        )
    ),
    lithography_source_binding_coulomb_coefficient.symbol > 0,
    "Nuclear radius coefficient inferred from the source Coulomb self-energy coefficient.",
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_source_nuclear_saturation_number_density = Approximation(
    "physical.eq.lithography_source_nuclear_saturation_number_density",
    lithography_source_nuclear_saturation_number_density.symbol,
    (
        sp.Integer(3)
        / (
            sp.Integer(4)
            * sp.pi
            * lithography_source_nuclear_radius_coefficient.symbol**3
        )
    ),
    lithography_source_nuclear_radius_coefficient.symbol > 0,
    "Saturation nucleon number density from the source nuclear radius coefficient.",
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_source_nuclear_bulk_binding_energy_density = Approximation(
    "physical.eq.lithography_source_nuclear_bulk_binding_energy_density",
    lithography_source_nuclear_bulk_binding_energy_density.symbol,
    (
        lithography_source_binding_volume_coefficient.symbol
        * lithography_source_nuclear_saturation_number_density.symbol
    ),
    lithography_source_nuclear_saturation_number_density.symbol > 0,
    "Bulk binding energy density reconstructed from volume coefficient and saturation density.",
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_source_nuclear_surface_tension = Approximation(
    "physical.eq.lithography_source_nuclear_surface_tension",
    lithography_source_nuclear_surface_tension.symbol,
    (
        lithography_source_binding_surface_coefficient.symbol
        / (
            sp.Integer(4)
            * sp.pi
            * lithography_source_nuclear_radius_coefficient.symbol**2
        )
    ),
    lithography_source_nuclear_radius_coefficient.symbol > 0,
    "Nuclear surface tension reconstructed from source surface coefficient and radius scale.",
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_source_binding_pairing_coefficient = Approximation(
    "physical.eq.lithography_source_binding_pairing_coefficient",
    lithography_source_binding_pairing_coefficient.symbol,
    (
        lithography_source_nuclear_pairing_gap_reference_energy.symbol
        * sp.sqrt(lithography_source_pairing_reference_mass_number.symbol)
    ),
    lithography_source_pairing_reference_mass_number.symbol > 0,
    "Liquid-drop pairing coefficient calibrated from a reference pairing gap.",
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_source_nuclear_symmetry_energy_density = Approximation(
    "physical.eq.lithography_source_nuclear_symmetry_energy_density",
    lithography_source_nuclear_symmetry_energy_density.symbol,
    (
        lithography_source_binding_asymmetry_coefficient.symbol
        * lithography_source_nuclear_saturation_number_density.symbol
    ),
    lithography_source_nuclear_saturation_number_density.symbol > 0,
    "Symmetry-energy density reconstructed from asymmetry coefficient and saturation density.",
    references=[LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_VARIABLES = [
    *LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_VARIABLES,
    lithography_source_nuclear_saturation_number_density,
    lithography_source_nuclear_radius_coefficient,
    lithography_source_nuclear_bulk_binding_energy_density,
    lithography_source_binding_volume_coefficient,
    lithography_source_nuclear_surface_tension,
    lithography_source_binding_surface_coefficient,
    lithography_source_nuclear_symmetry_energy_density,
    lithography_source_binding_asymmetry_coefficient,
    lithography_source_nuclear_pairing_gap_reference_energy,
    lithography_source_pairing_reference_mass_number,
    lithography_source_binding_pairing_coefficient,
    lithography_source_binding_coulomb_coefficient,
]

LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_EQUATIONS = [
    eq_lithography_source_binding_volume_coefficient_from_shared_nuclear_calibration,
    eq_lithography_source_binding_surface_coefficient_from_shared_nuclear_calibration,
    eq_lithography_source_binding_coulomb_coefficient_from_shared_nuclear_calibration,
    eq_lithography_source_binding_asymmetry_coefficient_from_shared_nuclear_calibration,
    eq_lithography_source_nuclear_pairing_gap_reference_energy_from_shared_nuclear_calibration,
    eq_lithography_source_nuclear_radius_coefficient,
    eq_lithography_source_nuclear_saturation_number_density,
    eq_lithography_source_nuclear_bulk_binding_energy_density,
    eq_lithography_source_nuclear_surface_tension,
    eq_lithography_source_binding_pairing_coefficient,
    eq_lithography_source_nuclear_symmetry_energy_density,
]


__all__ = [
    *LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_EXPORTS,
    "LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_REF",
    "lithography_source_nuclear_saturation_number_density",
    "lithography_source_nuclear_radius_coefficient",
    "lithography_source_nuclear_bulk_binding_energy_density",
    "lithography_source_binding_volume_coefficient",
    "lithography_source_nuclear_surface_tension",
    "lithography_source_binding_surface_coefficient",
    "lithography_source_nuclear_symmetry_energy_density",
    "lithography_source_binding_asymmetry_coefficient",
    "lithography_source_nuclear_pairing_gap_reference_energy",
    "lithography_source_pairing_reference_mass_number",
    "lithography_source_binding_pairing_coefficient",
    "lithography_source_binding_coulomb_coefficient",
    "eq_lithography_source_binding_volume_coefficient_from_shared_nuclear_calibration",
    "eq_lithography_source_binding_surface_coefficient_from_shared_nuclear_calibration",
    "eq_lithography_source_binding_coulomb_coefficient_from_shared_nuclear_calibration",
    "eq_lithography_source_binding_asymmetry_coefficient_from_shared_nuclear_calibration",
    "eq_lithography_source_nuclear_pairing_gap_reference_energy_from_shared_nuclear_calibration",
    "eq_lithography_source_nuclear_radius_coefficient",
    "eq_lithography_source_nuclear_saturation_number_density",
    "eq_lithography_source_nuclear_bulk_binding_energy_density",
    "eq_lithography_source_nuclear_surface_tension",
    "eq_lithography_source_binding_pairing_coefficient",
    "eq_lithography_source_nuclear_symmetry_energy_density",
    "LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_VARIABLES",
    "LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_EQUATIONS",
]
