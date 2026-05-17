"""
scopes/physical_lithography_plasma_electron_state_variables.py
==============================================================

Electron-state variables for the lithography source plasma.
"""

import sympy as sp

from ..core.units import JOULE, KELVIN, METER, SECOND
from .physical_lithography_plasma_common import (
    DIMENSIONLESS,
    plasma_fraction,
    plasma_var,
)
from .physical_lithography_plasma_species import (
    lithography_source_plasma_species_particle_mass,
    lithography_source_plasma_species_thermal_speed,
)


lithography_source_plasma_energy_loss_path_direction_cosine = plasma_fraction(
    "source_plasma_energy_loss_path_direction_cosine",
    "mu_E_loss_path_litho_src",
    "Direction cosine of the electron-energy loss path relative to the source-plasma column radius.",
)
lithography_source_plasma_energy_loss_path_factor = plasma_var(
    "source_plasma_energy_loss_path_factor",
    "chi_E_path_litho_src",
    "dimensionless",
    "Geometry factor mapping plasma column radius to energy-loss path length.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_energy_loss_path_length = plasma_var(
    "source_plasma_energy_loss_path_length",
    "ell_E_loss_plasma_litho_src",
    "m",
    "Effective path length for source-plasma electron energy losses.",
    sp_units=METER,
)
lithography_source_plasma_energy_loss_transport_speed_factor = plasma_var(
    "source_plasma_energy_loss_transport_speed_factor",
    "chi_v_E_loss_litho_src",
    "dimensionless",
    "Transport multiplier mapping source-species thermal speed to electron-energy loss speed.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_energy_loss_speed = plasma_var(
    "source_plasma_energy_loss_speed",
    "v_E_loss_litho_src",
    "m/s",
    "Effective speed of free-electron plasma energy loss transport.",
    sp_units=METER / SECOND,
)
lithography_source_plasma_energy_confinement_time = plasma_var(
    "source_plasma_energy_confinement_time",
    "tau_E_plasma_litho_src",
    "s",
    "Effective energy confinement time for absorbed electron plasma energy.",
    sp_units=SECOND,
)
lithography_source_plasma_free_electron_inventory_charge_fraction = plasma_fraction(
    "source_plasma_free_electron_inventory_charge_fraction",
    "xi_e_free_inventory_litho_src",
    "Fraction of source nuclear charge represented as free-electron inventory per active source particle.",
)
lithography_source_plasma_free_electron_yield_per_source_particle = plasma_var(
    "source_plasma_free_electron_yield_per_source_particle",
    "nu_e_free_plasma_litho_src",
    "dimensionless",
    "Independent free-electron yield per source particle in the active plasma inventory.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_free_electron_count = plasma_var(
    "source_plasma_free_electron_count",
    "N_e_free_litho_src",
    "count",
    "Effective free-electron count in the active lithography source plasma volume.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_electron_internal_energy = plasma_var(
    "source_plasma_electron_internal_energy",
    "U_e_plasma_litho_src",
    "J",
    "Internal energy carried by free electrons over the confinement time.",
    sp_units=JOULE,
)
lithography_source_plasma_electron_mean_kinetic_energy = plasma_var(
    "source_plasma_electron_mean_kinetic_energy",
    "E_mean_e_litho_src",
    "J",
    "Mean kinetic energy per free electron derived from the lithography source plasma temperature.",
    sp_units=JOULE,
)
lithography_source_plasma_debye_length = plasma_var(
    "source_plasma_debye_length",
    "lambda_D_litho_src",
    "m",
    "Debye screening length derived from source plasma electron temperature and density.",
    sp_units=METER,
)
lithography_source_plasma_electron_temperature = plasma_var(
    "source_plasma_electron_temperature",
    "T_e_litho_src",
    "K",
    "Operating electron temperature of the lithography source plasma.",
    sp_units=KELVIN,
)
lithography_source_plasma_electron_number_density = plasma_var(
    "source_plasma_electron_number_density",
    "n_e_plasma_litho_src",
    "1/m^3",
    "Operating free electron number density in the lithography source plasma.",
    sp_units=sp.Integer(1) / METER**3,
)


__all__ = [
    "lithography_source_plasma_energy_loss_path_direction_cosine",
    "lithography_source_plasma_energy_loss_path_factor",
    "lithography_source_plasma_energy_loss_path_length",
    "lithography_source_plasma_species_particle_mass",
    "lithography_source_plasma_energy_loss_transport_speed_factor",
    "lithography_source_plasma_species_thermal_speed",
    "lithography_source_plasma_energy_loss_speed",
    "lithography_source_plasma_energy_confinement_time",
    "lithography_source_plasma_free_electron_inventory_charge_fraction",
    "lithography_source_plasma_free_electron_yield_per_source_particle",
    "lithography_source_plasma_free_electron_count",
    "lithography_source_plasma_electron_internal_energy",
    "lithography_source_plasma_electron_mean_kinetic_energy",
    "lithography_source_plasma_debye_length",
    "lithography_source_plasma_electron_temperature",
    "lithography_source_plasma_electron_number_density",
]
