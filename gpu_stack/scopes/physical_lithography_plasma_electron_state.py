"""
scopes/physical_lithography_plasma_electron_state.py
====================================================

Compatibility shim for confinement, free-electron inventory, and electron-state
quantities in the lithography source plasma.
"""

from .physical_lithography_plasma_electron_state_variables import (
    lithography_source_plasma_debye_length,
    lithography_source_plasma_electron_internal_energy,
    lithography_source_plasma_electron_mean_kinetic_energy,
    lithography_source_plasma_electron_number_density,
    lithography_source_plasma_electron_temperature,
    lithography_source_plasma_energy_confinement_time,
    lithography_source_plasma_energy_loss_path_direction_cosine,
    lithography_source_plasma_energy_loss_path_factor,
    lithography_source_plasma_energy_loss_path_length,
    lithography_source_plasma_energy_loss_speed,
    lithography_source_plasma_energy_loss_transport_speed_factor,
    lithography_source_plasma_free_electron_count,
    lithography_source_plasma_free_electron_inventory_charge_fraction,
    lithography_source_plasma_free_electron_yield_per_source_particle,
    lithography_source_plasma_species_particle_mass,
    lithography_source_plasma_species_thermal_speed,
)
from .physical_lithography_plasma_species import (
    eq_lithography_source_plasma_species_particle_mass_from_nuclear_counts,
    eq_lithography_source_plasma_species_thermal_speed_from_gas_temperature,
)
from .physical_lithography_plasma_electron_state_confinement import (
    eq_lithography_source_plasma_energy_confinement_time_from_loss_path,
    eq_lithography_source_plasma_energy_loss_path_direction_cosine_from_acceptance_angle,
    eq_lithography_source_plasma_energy_loss_path_factor_from_direction_cosine,
    eq_lithography_source_plasma_energy_loss_path_length_from_radius,
    eq_lithography_source_plasma_energy_loss_speed_from_species_thermal_speed,
    eq_lithography_source_plasma_energy_loss_transport_speed_factor_from_mass_ratio,
)
from .physical_lithography_plasma_electron_state_inventory import (
    eq_lithography_source_plasma_debye_length_from_temperature_density,
    eq_lithography_source_plasma_electron_internal_energy_from_confinement,
    eq_lithography_source_plasma_electron_mean_kinetic_energy_from_temperature,
    eq_lithography_source_plasma_electron_number_density_from_count_volume,
    eq_lithography_source_plasma_electron_temperature_from_internal_energy,
    eq_lithography_source_plasma_free_electron_count_from_species_inventory,
    eq_lithography_source_plasma_free_electron_yield_per_source_particle_from_inventory_charge_fraction,
    ineq_lithography_source_plasma_free_electron_inventory_charge_fraction_within_unit_interval,
)


LITHOGRAPHY_SOURCE_PLASMA_ELECTRON_STATE_VARIABLES = [
    lithography_source_plasma_energy_loss_path_direction_cosine,
    lithography_source_plasma_energy_loss_path_factor,
    lithography_source_plasma_energy_loss_path_length,
    lithography_source_plasma_species_particle_mass,
    lithography_source_plasma_energy_loss_transport_speed_factor,
    lithography_source_plasma_species_thermal_speed,
    lithography_source_plasma_energy_loss_speed,
    lithography_source_plasma_energy_confinement_time,
    lithography_source_plasma_free_electron_inventory_charge_fraction,
    lithography_source_plasma_free_electron_yield_per_source_particle,
    lithography_source_plasma_free_electron_count,
    lithography_source_plasma_electron_internal_energy,
    lithography_source_plasma_electron_mean_kinetic_energy,
    lithography_source_plasma_debye_length,
    lithography_source_plasma_electron_temperature,
    lithography_source_plasma_electron_number_density,
]

LITHOGRAPHY_SOURCE_PLASMA_ELECTRON_STATE_EQUATIONS = [
    eq_lithography_source_plasma_energy_loss_path_direction_cosine_from_acceptance_angle,
    eq_lithography_source_plasma_energy_loss_path_factor_from_direction_cosine,
    eq_lithography_source_plasma_energy_loss_path_length_from_radius,
    eq_lithography_source_plasma_species_particle_mass_from_nuclear_counts,
    eq_lithography_source_plasma_species_thermal_speed_from_gas_temperature,
    eq_lithography_source_plasma_energy_loss_transport_speed_factor_from_mass_ratio,
    eq_lithography_source_plasma_energy_loss_speed_from_species_thermal_speed,
    eq_lithography_source_plasma_energy_confinement_time_from_loss_path,
    ineq_lithography_source_plasma_free_electron_inventory_charge_fraction_within_unit_interval,
    eq_lithography_source_plasma_free_electron_yield_per_source_particle_from_inventory_charge_fraction,
    eq_lithography_source_plasma_free_electron_count_from_species_inventory,
    eq_lithography_source_plasma_electron_internal_energy_from_confinement,
    eq_lithography_source_plasma_electron_temperature_from_internal_energy,
    eq_lithography_source_plasma_electron_number_density_from_count_volume,
    eq_lithography_source_plasma_electron_mean_kinetic_energy_from_temperature,
    eq_lithography_source_plasma_debye_length_from_temperature_density,
]


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
    "eq_lithography_source_plasma_energy_loss_path_direction_cosine_from_acceptance_angle",
    "eq_lithography_source_plasma_energy_loss_path_factor_from_direction_cosine",
    "eq_lithography_source_plasma_energy_loss_path_length_from_radius",
    "eq_lithography_source_plasma_species_particle_mass_from_nuclear_counts",
    "eq_lithography_source_plasma_species_thermal_speed_from_gas_temperature",
    "eq_lithography_source_plasma_energy_loss_transport_speed_factor_from_mass_ratio",
    "eq_lithography_source_plasma_energy_loss_speed_from_species_thermal_speed",
    "eq_lithography_source_plasma_energy_confinement_time_from_loss_path",
    "ineq_lithography_source_plasma_free_electron_inventory_charge_fraction_within_unit_interval",
    "eq_lithography_source_plasma_free_electron_yield_per_source_particle_from_inventory_charge_fraction",
    "eq_lithography_source_plasma_free_electron_count_from_species_inventory",
    "eq_lithography_source_plasma_electron_internal_energy_from_confinement",
    "eq_lithography_source_plasma_electron_temperature_from_internal_energy",
    "eq_lithography_source_plasma_electron_number_density_from_count_volume",
    "eq_lithography_source_plasma_electron_mean_kinetic_energy_from_temperature",
    "eq_lithography_source_plasma_debye_length_from_temperature_density",
    "LITHOGRAPHY_SOURCE_PLASMA_ELECTRON_STATE_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_ELECTRON_STATE_EQUATIONS",
]
