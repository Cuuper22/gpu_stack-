"""
scopes/physical_lithography_medium_binding_coefficients.py
==========================================================

Shared liquid-drop nuclear binding coefficients for lithography media.
"""

import sympy as sp

from ..constants import ELEMENTARY_CHARGE, EPSILON_0
from ..core import Approximation, ge, gt, var
from ..core.units import JOULE, METER
from .physical_lithography_medium_components import LITHOGRAPHY_MEDIUM_COMPOSITION_REF
from .physical_lithography_nuclear_binding_coefficients import (
    LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF,
    lithography_nuclear_binding_asymmetry_coefficient,
    lithography_nuclear_binding_coulomb_coefficient,
    lithography_nuclear_binding_surface_coefficient,
    lithography_nuclear_binding_volume_coefficient,
    lithography_nuclear_pairing_gap_reference_energy,
)


lithography_medium_component_nuclear_saturation_number_density = var(
    "physical.lithography.medium_component_nuclear_saturation_number_density",
    "n0_litho_med_comp",
    "1/m^3",
    "Effective saturation nucleon number density for imaging-medium component nuclear liquid-drop terms.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1) / METER**3,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_nuclear_radius_coefficient = var(
    "physical.lithography.medium_component_nuclear_radius_coefficient",
    "r0_litho_med_comp",
    "m",
    "Nuclear radius coefficient for imaging-medium component liquid-drop terms.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_nuclear_bulk_binding_energy_density = var(
    "physical.lithography.medium_component_nuclear_bulk_binding_energy_density",
    "u_bulk_bind_litho_med_comp",
    "J/m^3",
    "Effective bulk nuclear binding energy density for imaging-medium component liquid-drop volume terms.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE / METER**3,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_binding_volume_coefficient = var(
    "physical.lithography.medium_component_binding_volume_coefficient",
    "a_vol_litho_med_comp",
    "J",
    "Liquid-drop volume binding coefficient shared by imaging-medium component nuclei.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_nuclear_surface_tension = var(
    "physical.lithography.medium_component_nuclear_surface_tension",
    "sigma_nuc_surf_litho_med_comp",
    "J/m^2",
    "Effective nuclear surface tension for imaging-medium component liquid-drop surface terms.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE / METER**2,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_binding_surface_coefficient = var(
    "physical.lithography.medium_component_binding_surface_coefficient",
    "a_surf_litho_med_comp",
    "J",
    "Liquid-drop surface binding coefficient shared by imaging-medium component nuclei.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_nuclear_symmetry_energy_density = var(
    "physical.lithography.medium_component_nuclear_symmetry_energy_density",
    "u_sym_litho_med_comp",
    "J/m^3",
    "Effective nuclear symmetry-energy density for imaging-medium component asymmetry terms.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE / METER**3,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_binding_asymmetry_coefficient = var(
    "physical.lithography.medium_component_binding_asymmetry_coefficient",
    "a_asym_litho_med_comp",
    "J",
    "Liquid-drop asymmetry coefficient shared by imaging-medium component nuclei.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_nuclear_pairing_gap_reference_energy = var(
    "physical.lithography.medium_component_nuclear_pairing_gap_reference_energy",
    "Delta_pair_ref_litho_med_comp",
    "J",
    "Reference nuclear pairing gap energy for imaging-medium component liquid-drop pairing terms.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_binding_coulomb_coefficient = var(
    "physical.lithography.medium_component_binding_coulomb_coefficient",
    "a_coul_litho_med_comp",
    "J",
    "Liquid-drop Coulomb coefficient shared by imaging-medium component nuclei.",
    scope="physical",
    positive=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)


eq_lithography_medium_component_binding_volume_coefficient_from_shared_nuclear_calibration = Approximation(
    "physical.eq.lithography_medium_component_binding_volume_coefficient_from_shared_nuclear_calibration",
    lithography_medium_component_binding_volume_coefficient.symbol,
    lithography_nuclear_binding_volume_coefficient.symbol,
    ge(lithography_nuclear_binding_volume_coefficient.symbol, 0),
    "Medium-component liquid-drop volume coefficient from shared nuclear binding calibration.",
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_medium_component_binding_surface_coefficient_from_shared_nuclear_calibration = Approximation(
    "physical.eq.lithography_medium_component_binding_surface_coefficient_from_shared_nuclear_calibration",
    lithography_medium_component_binding_surface_coefficient.symbol,
    lithography_nuclear_binding_surface_coefficient.symbol,
    ge(lithography_nuclear_binding_surface_coefficient.symbol, 0),
    "Medium-component liquid-drop surface coefficient from shared nuclear binding calibration.",
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_medium_component_binding_coulomb_coefficient_from_shared_nuclear_calibration = Approximation(
    "physical.eq.lithography_medium_component_binding_coulomb_coefficient_from_shared_nuclear_calibration",
    lithography_medium_component_binding_coulomb_coefficient.symbol,
    lithography_nuclear_binding_coulomb_coefficient.symbol,
    gt(lithography_nuclear_binding_coulomb_coefficient.symbol, 0),
    "Medium-component liquid-drop Coulomb coefficient from shared nuclear binding calibration.",
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_medium_component_binding_asymmetry_coefficient_from_shared_nuclear_calibration = Approximation(
    "physical.eq.lithography_medium_component_binding_asymmetry_coefficient_from_shared_nuclear_calibration",
    lithography_medium_component_binding_asymmetry_coefficient.symbol,
    lithography_nuclear_binding_asymmetry_coefficient.symbol,
    ge(lithography_nuclear_binding_asymmetry_coefficient.symbol, 0),
    "Medium-component liquid-drop asymmetry coefficient from shared nuclear binding calibration.",
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_medium_component_nuclear_pairing_gap_reference_energy_from_shared_nuclear_calibration = Approximation(
    "physical.eq.lithography_medium_component_nuclear_pairing_gap_reference_energy_from_shared_nuclear_calibration",
    lithography_medium_component_nuclear_pairing_gap_reference_energy.symbol,
    lithography_nuclear_pairing_gap_reference_energy.symbol,
    ge(lithography_nuclear_pairing_gap_reference_energy.symbol, 0),
    "Medium-component pairing-gap reference energy from shared nuclear binding calibration.",
    references=[LITHOGRAPHY_NUCLEAR_BINDING_COEFFICIENT_REF],
    check_units=True,
)

eq_lithography_medium_component_nuclear_radius_coefficient = Approximation(
    "physical.eq.lithography_medium_component_nuclear_radius_coefficient",
    lithography_medium_component_nuclear_radius_coefficient.symbol,
    (
        sp.Integer(3)
        * ELEMENTARY_CHARGE.symbol**2
        / (
            sp.Integer(20)
            * sp.pi
            * EPSILON_0.symbol
            * lithography_medium_component_binding_coulomb_coefficient.symbol
        )
    ),
    lithography_medium_component_binding_coulomb_coefficient.symbol > 0,
    "Medium-component nuclear radius coefficient from liquid-drop Coulomb coefficient.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)

eq_lithography_medium_component_nuclear_saturation_number_density = Approximation(
    "physical.eq.lithography_medium_component_nuclear_saturation_number_density",
    lithography_medium_component_nuclear_saturation_number_density.symbol,
    (
        sp.Integer(3)
        / (
            sp.Integer(4)
            * sp.pi
            * lithography_medium_component_nuclear_radius_coefficient.symbol**3
        )
    ),
    lithography_medium_component_nuclear_radius_coefficient.symbol > 0,
    "Medium-component saturation nucleon number density from nuclear radius coefficient.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)

eq_lithography_medium_component_nuclear_bulk_binding_energy_density = Approximation(
    "physical.eq.lithography_medium_component_nuclear_bulk_binding_energy_density",
    lithography_medium_component_nuclear_bulk_binding_energy_density.symbol,
    (
        lithography_medium_component_binding_volume_coefficient.symbol
        * lithography_medium_component_nuclear_saturation_number_density.symbol
    ),
    lithography_medium_component_nuclear_saturation_number_density.symbol > 0,
    "Medium-component bulk nuclear binding energy density from liquid-drop volume coefficient.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)

eq_lithography_medium_component_nuclear_surface_tension = Approximation(
    "physical.eq.lithography_medium_component_nuclear_surface_tension",
    lithography_medium_component_nuclear_surface_tension.symbol,
    (
        lithography_medium_component_binding_surface_coefficient.symbol
        / (
            sp.Integer(4)
            * sp.pi
            * lithography_medium_component_nuclear_radius_coefficient.symbol**2
        )
    ),
    lithography_medium_component_nuclear_radius_coefficient.symbol > 0,
    "Medium-component nuclear surface tension from liquid-drop surface coefficient.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)

eq_lithography_medium_component_nuclear_symmetry_energy_density = Approximation(
    "physical.eq.lithography_medium_component_nuclear_symmetry_energy_density",
    lithography_medium_component_nuclear_symmetry_energy_density.symbol,
    (
        lithography_medium_component_binding_asymmetry_coefficient.symbol
        * lithography_medium_component_nuclear_saturation_number_density.symbol
    ),
    lithography_medium_component_nuclear_saturation_number_density.symbol > 0,
    "Medium-component nuclear symmetry-energy density from liquid-drop asymmetry coefficient.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)


LITHOGRAPHY_MEDIUM_BINDING_COEFFICIENT_VARIABLES = [
    lithography_medium_component_nuclear_saturation_number_density,
    lithography_medium_component_nuclear_radius_coefficient,
    lithography_medium_component_nuclear_bulk_binding_energy_density,
    lithography_medium_component_binding_volume_coefficient,
    lithography_medium_component_nuclear_surface_tension,
    lithography_medium_component_binding_surface_coefficient,
    lithography_medium_component_nuclear_symmetry_energy_density,
    lithography_medium_component_binding_asymmetry_coefficient,
    lithography_medium_component_nuclear_pairing_gap_reference_energy,
    lithography_medium_component_binding_coulomb_coefficient,
]

LITHOGRAPHY_MEDIUM_BINDING_COEFFICIENT_EQUATIONS = [
    eq_lithography_medium_component_binding_volume_coefficient_from_shared_nuclear_calibration,
    eq_lithography_medium_component_binding_surface_coefficient_from_shared_nuclear_calibration,
    eq_lithography_medium_component_binding_coulomb_coefficient_from_shared_nuclear_calibration,
    eq_lithography_medium_component_binding_asymmetry_coefficient_from_shared_nuclear_calibration,
    eq_lithography_medium_component_nuclear_pairing_gap_reference_energy_from_shared_nuclear_calibration,
    eq_lithography_medium_component_nuclear_radius_coefficient,
    eq_lithography_medium_component_nuclear_saturation_number_density,
    eq_lithography_medium_component_nuclear_bulk_binding_energy_density,
    eq_lithography_medium_component_nuclear_surface_tension,
    eq_lithography_medium_component_nuclear_symmetry_energy_density,
]

LITHOGRAPHY_MEDIUM_BINDING_COEFFICIENT_EXPORTS = [
    "lithography_medium_component_nuclear_saturation_number_density",
    "lithography_medium_component_nuclear_radius_coefficient",
    "lithography_medium_component_nuclear_bulk_binding_energy_density",
    "lithography_medium_component_binding_volume_coefficient",
    "lithography_medium_component_nuclear_surface_tension",
    "lithography_medium_component_binding_surface_coefficient",
    "lithography_medium_component_nuclear_symmetry_energy_density",
    "lithography_medium_component_binding_asymmetry_coefficient",
    "lithography_medium_component_nuclear_pairing_gap_reference_energy",
    "lithography_medium_component_binding_coulomb_coefficient",
    "eq_lithography_medium_component_binding_volume_coefficient_from_shared_nuclear_calibration",
    "eq_lithography_medium_component_binding_surface_coefficient_from_shared_nuclear_calibration",
    "eq_lithography_medium_component_binding_coulomb_coefficient_from_shared_nuclear_calibration",
    "eq_lithography_medium_component_binding_asymmetry_coefficient_from_shared_nuclear_calibration",
    "eq_lithography_medium_component_nuclear_pairing_gap_reference_energy_from_shared_nuclear_calibration",
    "eq_lithography_medium_component_nuclear_radius_coefficient",
    "eq_lithography_medium_component_nuclear_saturation_number_density",
    "eq_lithography_medium_component_nuclear_bulk_binding_energy_density",
    "eq_lithography_medium_component_nuclear_surface_tension",
    "eq_lithography_medium_component_nuclear_symmetry_energy_density",
]

__all__ = [
    *LITHOGRAPHY_MEDIUM_BINDING_COEFFICIENT_EXPORTS,
    "LITHOGRAPHY_MEDIUM_BINDING_COEFFICIENT_VARIABLES",
    "LITHOGRAPHY_MEDIUM_BINDING_COEFFICIENT_EQUATIONS",
    "LITHOGRAPHY_MEDIUM_BINDING_COEFFICIENT_EXPORTS",
]
