"""
scopes/physical_lithography_plasma_electron_state_inventory.py
==============================================================

The free-electron inventory and its temperature. Each active source
particle contributes electrons according to a charge fraction of its
nuclear charge, giving the electron count; absorbed power times the
confinement time gives the stored internal energy; energy per electron sets
the electron temperature. Count over active plasma volume gives the number
density, and temperature with density gives the Debye screening length.
Temperature and density are exactly what the Saha ionization balance in the
electronic-structure layer needs.
"""

import sympy as sp

from ..constants import (
    BOLTZMANN,
    ELEMENTARY_CHARGE,
    EPSILON_0,
)
from ..core import Approximation, Inequality
from .physical_lithography_plasma_absorption import (
    lithography_source_plasma_absorbed_power,
)
from .physical_lithography_plasma_drive import (
    lithography_source_plasma_active_volume,
)
from .physical_lithography_plasma_species import (
    LITHOGRAPHY_SOURCE_PLASMA_STATE_REF,
    lithography_source_plasma_species_number_density,
)
from .physical_lithography_species import lithography_source_proton_count
from .physical_lithography_plasma_electron_state_variables import (
    lithography_source_plasma_debye_length,
    lithography_source_plasma_electron_internal_energy,
    lithography_source_plasma_electron_mean_kinetic_energy,
    lithography_source_plasma_electron_number_density,
    lithography_source_plasma_electron_temperature,
    lithography_source_plasma_energy_confinement_time,
    lithography_source_plasma_free_electron_count,
    lithography_source_plasma_free_electron_inventory_charge_fraction,
    lithography_source_plasma_free_electron_yield_per_source_particle,
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


LITHOGRAPHY_SOURCE_PLASMA_ELECTRON_INVENTORY_EQUATIONS = [
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
    "ineq_lithography_source_plasma_free_electron_inventory_charge_fraction_within_unit_interval",
    "eq_lithography_source_plasma_free_electron_yield_per_source_particle_from_inventory_charge_fraction",
    "eq_lithography_source_plasma_free_electron_count_from_species_inventory",
    "eq_lithography_source_plasma_electron_internal_energy_from_confinement",
    "eq_lithography_source_plasma_electron_temperature_from_internal_energy",
    "eq_lithography_source_plasma_electron_number_density_from_count_volume",
    "eq_lithography_source_plasma_electron_mean_kinetic_energy_from_temperature",
    "eq_lithography_source_plasma_debye_length_from_temperature_density",
    "LITHOGRAPHY_SOURCE_PLASMA_ELECTRON_INVENTORY_EQUATIONS",
]
