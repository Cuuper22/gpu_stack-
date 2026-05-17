"""
scopes/physical_lithography_plasma_electron_state.py
====================================================

Confinement, free-electron inventory, and electron-state quantities for the
lithography source plasma.
"""

import sympy as sp

from ..constants import (
    BOLTZMANN,
    ELEMENTARY_CHARGE,
    ELECTRON_MASS,
    EPSILON_0,
)
from ..core import Approximation, Inequality
from ..core.units import JOULE, KELVIN, METER, SECOND
from .physical_lithography_plasma_absorption import lithography_source_plasma_absorbed_power
from .physical_lithography_plasma_common import (
    DIMENSIONLESS,
    plasma_fraction,
    plasma_var,
)
from .physical_lithography_plasma_drive import (
    lithography_source_plasma_active_volume,
    lithography_source_plasma_column_radius,
)
from .physical_lithography_plasma_focus import (
    lithography_source_plasma_drive_acceptance_half_angle,
)
from .physical_lithography_plasma_species import (
    LITHOGRAPHY_SOURCE_PLASMA_STATE_REF,
    eq_lithography_source_plasma_species_particle_mass_from_nuclear_counts,
    eq_lithography_source_plasma_species_thermal_speed_from_gas_temperature,
    lithography_source_plasma_species_gas_temperature,
    lithography_source_plasma_species_number_density,
    lithography_source_plasma_species_particle_mass,
    lithography_source_plasma_species_thermal_speed,
)
from .physical_lithography_species import lithography_source_proton_count


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


eq_lithography_source_plasma_energy_loss_path_direction_cosine_from_acceptance_angle = Approximation(
    "physical.eq.lithography_source_plasma_energy_loss_path_direction_cosine_from_acceptance_angle",
    lithography_source_plasma_energy_loss_path_direction_cosine.symbol,
    sp.sin(lithography_source_plasma_drive_acceptance_half_angle.symbol),
    (
        (lithography_source_plasma_drive_acceptance_half_angle.symbol > 0)
        & (lithography_source_plasma_drive_acceptance_half_angle.symbol <= sp.pi / 2)
    ),
    "Electron-energy loss path direction cosine from the source-plasma drive acceptance half-angle.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)


eq_lithography_source_plasma_energy_loss_path_factor_from_direction_cosine = Approximation(
    "physical.eq.lithography_source_plasma_energy_loss_path_factor_from_direction_cosine",
    lithography_source_plasma_energy_loss_path_factor.symbol,
    sp.Integer(1) / lithography_source_plasma_energy_loss_path_direction_cosine.symbol,
    (
        (lithography_source_plasma_energy_loss_path_direction_cosine.symbol > 0)
        & (lithography_source_plasma_energy_loss_path_direction_cosine.symbol <= 1)
    ),
    "Electron-energy loss path factor from the inverse direction cosine across the plasma column.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_energy_loss_path_length_from_radius = Approximation(
    "physical.eq.lithography_source_plasma_energy_loss_path_length_from_radius",
    lithography_source_plasma_energy_loss_path_length.symbol,
    (
        lithography_source_plasma_energy_loss_path_factor.symbol
        * lithography_source_plasma_column_radius.symbol
    ),
    (
        (lithography_source_plasma_energy_loss_path_factor.symbol > 0)
        & (lithography_source_plasma_column_radius.symbol > 0)
    ),
    "Electron-energy loss path length from plasma column radius and loss-path factor.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_energy_loss_transport_speed_factor_from_mass_ratio = Approximation(
    "physical.eq.lithography_source_plasma_energy_loss_transport_speed_factor_from_mass_ratio",
    lithography_source_plasma_energy_loss_transport_speed_factor.symbol,
    sp.sqrt(lithography_source_plasma_species_particle_mass.symbol / ELECTRON_MASS.symbol),
    (
        (lithography_source_plasma_species_particle_mass.symbol > 0)
        & (ELECTRON_MASS.symbol > 0)
    ),
    "Energy-loss transport multiplier from the electron-to-source-species thermal-speed mass ratio.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_energy_loss_speed_from_species_thermal_speed = Approximation(
    "physical.eq.lithography_source_plasma_energy_loss_speed_from_species_thermal_speed",
    lithography_source_plasma_energy_loss_speed.symbol,
    (
        lithography_source_plasma_energy_loss_transport_speed_factor.symbol
        * lithography_source_plasma_species_thermal_speed.symbol
    ),
    (
        (lithography_source_plasma_energy_loss_transport_speed_factor.symbol > 0)
        & (lithography_source_plasma_species_thermal_speed.symbol > 0)
    ),
    "Electron-energy loss speed from source-species thermal speed and a transport multiplier.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_energy_confinement_time_from_loss_path = Approximation(
    "physical.eq.lithography_source_plasma_energy_confinement_time_from_loss_path",
    lithography_source_plasma_energy_confinement_time.symbol,
    (
        lithography_source_plasma_energy_loss_path_length.symbol
        / lithography_source_plasma_energy_loss_speed.symbol
    ),
    (
        (lithography_source_plasma_energy_loss_path_length.symbol > 0)
        & (lithography_source_plasma_energy_loss_speed.symbol > 0)
    ),
    "Energy confinement time from effective loss path length over energy-loss speed.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_free_electron_yield_per_source_particle_from_inventory_charge_fraction = Approximation(
    "physical.eq.lithography_source_plasma_free_electron_yield_per_source_particle_from_inventory_charge_fraction",
    lithography_source_plasma_free_electron_yield_per_source_particle.symbol,
    (
        lithography_source_proton_count.symbol
        * lithography_source_plasma_free_electron_inventory_charge_fraction.symbol
    ),
    (
        (lithography_source_proton_count.symbol > 0)
        & (
            lithography_source_plasma_free_electron_inventory_charge_fraction.symbol
            > 0
        )
        & (
            lithography_source_plasma_free_electron_inventory_charge_fraction.symbol
            <= 1
        )
    ),
    "Free-electron yield per active source particle from nuclear charge and free-inventory charge fraction.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_free_electron_inventory_charge_fraction_within_unit_interval = Inequality(
    "physical.ineq.lithography_source_plasma_free_electron_inventory_charge_fraction_within_unit_interval",
    lithography_source_plasma_free_electron_inventory_charge_fraction.symbol,
    sp.Integer(1),
    "<=",
    "Source-plasma free-electron inventory charge fraction cannot exceed the source nuclear charge.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_free_electron_count_from_species_inventory = Approximation(
    "physical.eq.lithography_source_plasma_free_electron_count_from_species_inventory",
    lithography_source_plasma_free_electron_count.symbol,
    (
        lithography_source_plasma_species_number_density.symbol
        * lithography_source_plasma_active_volume.symbol
        * lithography_source_plasma_free_electron_yield_per_source_particle.symbol
    ),
    (
        (lithography_source_plasma_species_number_density.symbol > 0)
        & (lithography_source_plasma_active_volume.symbol > 0)
        & (lithography_source_plasma_free_electron_yield_per_source_particle.symbol > 0)
    ),
    "Independent free-electron inventory from source-species density, active volume, and free-electron yield per source particle.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_electron_internal_energy_from_confinement = Approximation(
    "physical.eq.lithography_source_plasma_electron_internal_energy_from_confinement",
    lithography_source_plasma_electron_internal_energy.symbol,
    (
        lithography_source_plasma_absorbed_power.symbol
        * lithography_source_plasma_energy_confinement_time.symbol
    ),
    (
        (lithography_source_plasma_absorbed_power.symbol > 0)
        & (lithography_source_plasma_energy_confinement_time.symbol > 0)
    ),
    "Free-electron plasma internal energy from absorbed power over the energy confinement time.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_electron_temperature_from_internal_energy = Approximation(
    "physical.eq.lithography_source_plasma_electron_temperature_from_internal_energy",
    lithography_source_plasma_electron_temperature.symbol,
    (
        sp.Integer(2)
        * lithography_source_plasma_electron_internal_energy.symbol
        / (
            sp.Integer(3)
            * BOLTZMANN.symbol
            * lithography_source_plasma_free_electron_count.symbol
        )
    ),
    (
        (lithography_source_plasma_electron_internal_energy.symbol > 0)
        & (lithography_source_plasma_free_electron_count.symbol > 0)
    ),
    "Electron temperature from free-electron internal energy and inventory.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_electron_number_density_from_count_volume = Approximation(
    "physical.eq.lithography_source_plasma_electron_number_density_from_count_volume",
    lithography_source_plasma_electron_number_density.symbol,
    (
        lithography_source_plasma_free_electron_count.symbol
        / lithography_source_plasma_active_volume.symbol
    ),
    (
        (lithography_source_plasma_free_electron_count.symbol > 0)
        & (lithography_source_plasma_active_volume.symbol > 0)
    ),
    "Free-electron number density from electron inventory and active plasma volume.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_electron_mean_kinetic_energy_from_temperature = Approximation(
    "physical.eq.lithography_source_plasma_electron_mean_kinetic_energy_from_temperature",
    lithography_source_plasma_electron_mean_kinetic_energy.symbol,
    (
        sp.Rational(3, 2)
        * BOLTZMANN.symbol
        * lithography_source_plasma_electron_temperature.symbol
    ),
    lithography_source_plasma_electron_temperature.symbol > 0,
    "Maxwellian mean kinetic energy per free electron from electron temperature.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_debye_length_from_temperature_density = Approximation(
    "physical.eq.lithography_source_plasma_debye_length_from_temperature_density",
    lithography_source_plasma_debye_length.symbol,
    (
        EPSILON_0.symbol
        * BOLTZMANN.symbol
        * lithography_source_plasma_electron_temperature.symbol
        / (
            lithography_source_plasma_electron_number_density.symbol
            * ELEMENTARY_CHARGE.symbol**2
        )
    ) ** sp.Rational(1, 2),
    (lithography_source_plasma_electron_temperature.symbol > 0)
    & (lithography_source_plasma_electron_number_density.symbol > 0),
    "Debye screening length from electron temperature and number density.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
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
