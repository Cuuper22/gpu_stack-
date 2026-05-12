"""
scopes/physical_lithography_medium_density.py
=============================================

Imaging-medium molar, particle, mass-density, and number-density closure.
"""

import sympy as sp

from ..constants import AVOGADRO
from ..core import Approximation, Inequality, Reference, eq, gt, valid_all, var
from ..core.units import KILOGRAM, METER, MOLE
from .physical_lithography_medium_composition import (
    LITHOGRAPHY_MEDIUM_COMPOSITION_REF,
    lithography_medium_formula_unit_rest_mass,
    lithography_medium_intercomponent_effective_separation,
)


LITHOGRAPHY_MEDIUM_DENSITY_REF = Reference(
    citation="Imaging-medium density abstraction: formula-unit mass, packing length, and packing fill factor",
    kind="memo",
)


lithography_medium_formula_unit_packing_length_scale_factor = var(
    "physical.lithography.medium_formula_unit_packing_length_scale_factor",
    "k_pack_linear_litho_med",
    "dimensionless",
    "Dimensionless linear cell-span factor multiplying the representative intercomponent separation.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
)
lithography_medium_formula_unit_packing_length = var(
    "physical.lithography.medium_formula_unit_packing_length",
    "ell_pack_litho_med",
    "m",
    "Effective linear packing scale for one representative imaging-medium formula unit.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
)
lithography_medium_formula_unit_packing_fill_factor = var(
    "physical.lithography.medium_formula_unit_packing_fill_factor",
    "phi_pack_litho_med",
    "dimensionless",
    "Dimensionless occupancy factor converting formula-unit packing volume into bulk mass density.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
)
ineq_lithography_medium_formula_unit_packing_fill_factor_at_most_unity = Inequality(
    "physical.ineq.lithography_medium_formula_unit_packing_fill_factor_at_most_unity",
    lithography_medium_formula_unit_packing_fill_factor.symbol,
    sp.Integer(1),
    "<=",
    "Formula-unit packing fill factor cannot exceed full occupancy.",
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
    check_units=True,
)
ineq_lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity = Inequality(
    "physical.ineq.lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity",
    lithography_medium_formula_unit_packing_length_scale_factor.symbol,
    sp.Integer(1),
    ">=",
    "Formula-unit linear packing span must not be smaller than the represented intercomponent separation.",
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
    check_units=True,
)
lithography_medium_formula_unit_packing_volume = var(
    "physical.lithography.medium_formula_unit_packing_volume",
    "V_pack_litho_med",
    "m^3",
    "Effective packing-cell volume for one representative imaging-medium formula unit.",
    scope="physical",
    sp_units=METER**3,
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
)
lithography_medium_mass_density = var(
    "physical.lithography.medium_mass_density", "rho_litho_med", "kg/m^3",
    "Mass density of the lithography imaging medium.",
    scope="physical",
    sp_units=KILOGRAM / METER**3,
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
)
lithography_medium_molar_mass = var(
    "physical.lithography.medium_molar_mass", "M_litho_med", "kg/mol",
    "Molar mass of the representative polarizable species in the lithography imaging medium.",
    scope="physical",
    sp_units=KILOGRAM / MOLE,
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
)
lithography_medium_particle_mass = var(
    "physical.lithography.medium_particle_mass", "m_litho_med", "kg",
    "Particle or molecular mass of the representative polarizable species in the lithography imaging medium.",
    scope="physical",
    sp_units=KILOGRAM,
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
)
lithography_medium_number_density = var(
    "physical.lithography.medium_number_density", "N_litho_med", "1/m^3",
    "Number density of polarizable molecules or atoms in the lithography imaging medium.",
    scope="physical",
    sp_units=METER ** -3,
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
)


eq_lithography_medium_molar_mass = eq(
    "physical.eq.lithography_medium_molar_mass",
    lithography_medium_molar_mass.symbol,
    AVOGADRO.symbol * lithography_medium_formula_unit_rest_mass.symbol,
    "Imaging-medium molar mass from formula-unit rest mass and Avogadro's constant.",
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
    check_units=True,
)
eq_lithography_medium_particle_mass = eq(
    "physical.eq.lithography_medium_particle_mass",
    lithography_medium_particle_mass.symbol,
    lithography_medium_molar_mass.symbol / AVOGADRO.symbol,
    "Representative particle mass from molar mass and Avogadro's constant.",
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_packing_length_from_intercomponent_separation_scale = eq(
    "physical.eq.lithography_medium_formula_unit_packing_length_from_intercomponent_separation_scale",
    lithography_medium_formula_unit_packing_length.symbol,
    (
        lithography_medium_formula_unit_packing_length_scale_factor.symbol
        * lithography_medium_intercomponent_effective_separation.symbol
    ),
    "Formula-unit packing length from intercomponent separation and linear cell-span scale.",
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF, LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_packing_volume = Approximation(
    "physical.eq.lithography_medium_formula_unit_packing_volume",
    lithography_medium_formula_unit_packing_volume.symbol,
    lithography_medium_formula_unit_packing_length.symbol**3,
    gt(lithography_medium_formula_unit_packing_length.symbol, 0),
    "Packing-cell volume from an effective formula-unit packing length.",
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
    check_units=True,
)
eq_lithography_medium_mass_density_from_packing = Approximation(
    "physical.eq.lithography_medium_mass_density_from_packing",
    lithography_medium_mass_density.symbol,
    (
        lithography_medium_formula_unit_packing_fill_factor.symbol
        * lithography_medium_particle_mass.symbol
        / lithography_medium_formula_unit_packing_volume.symbol
    ),
    valid_all(
        gt(lithography_medium_formula_unit_packing_fill_factor.symbol, 0),
        gt(lithography_medium_particle_mass.symbol, 0),
        gt(lithography_medium_formula_unit_packing_volume.symbol, 0),
    ),
    "Bulk imaging-medium mass density from particle mass and effective formula-unit packing.",
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
    check_units=True,
)
eq_lithography_medium_number_density_from_mass = Approximation(
    "physical.eq.lithography_medium_number_density_from_mass",
    lithography_medium_number_density.symbol,
    lithography_medium_mass_density.symbol / lithography_medium_particle_mass.symbol,
    valid_all(
        gt(lithography_medium_mass_density.symbol, 0),
        gt(lithography_medium_particle_mass.symbol, 0),
    ),
    "Medium number density from mass density and representative particle mass.",
    references=[LITHOGRAPHY_MEDIUM_DENSITY_REF],
    check_units=True,
)


LITHOGRAPHY_MEDIUM_DENSITY_VARIABLES = [
    lithography_medium_formula_unit_packing_length_scale_factor,
    lithography_medium_formula_unit_packing_length,
    lithography_medium_formula_unit_packing_fill_factor,
    lithography_medium_formula_unit_packing_volume,
    lithography_medium_mass_density,
    lithography_medium_molar_mass,
    lithography_medium_particle_mass,
    lithography_medium_number_density,
]

LITHOGRAPHY_MEDIUM_DENSITY_EQUATIONS = [
    ineq_lithography_medium_formula_unit_packing_fill_factor_at_most_unity,
    ineq_lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity,
    eq_lithography_medium_molar_mass,
    eq_lithography_medium_particle_mass,
    eq_lithography_medium_formula_unit_packing_length_from_intercomponent_separation_scale,
    eq_lithography_medium_formula_unit_packing_volume,
    eq_lithography_medium_mass_density_from_packing,
    eq_lithography_medium_number_density_from_mass,
]


__all__ = [
    "LITHOGRAPHY_MEDIUM_DENSITY_REF",
    "lithography_medium_formula_unit_packing_length_scale_factor",
    "lithography_medium_formula_unit_packing_length",
    "lithography_medium_formula_unit_packing_fill_factor",
    "lithography_medium_formula_unit_packing_volume",
    "lithography_medium_mass_density",
    "lithography_medium_molar_mass",
    "lithography_medium_particle_mass",
    "lithography_medium_number_density",
    "ineq_lithography_medium_formula_unit_packing_fill_factor_at_most_unity",
    "ineq_lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity",
    "eq_lithography_medium_molar_mass",
    "eq_lithography_medium_particle_mass",
    "eq_lithography_medium_formula_unit_packing_length_from_intercomponent_separation_scale",
    "eq_lithography_medium_formula_unit_packing_volume",
    "eq_lithography_medium_mass_density_from_packing",
    "eq_lithography_medium_number_density_from_mass",
    "LITHOGRAPHY_MEDIUM_DENSITY_VARIABLES",
    "LITHOGRAPHY_MEDIUM_DENSITY_EQUATIONS",
]
