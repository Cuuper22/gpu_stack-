"""
scopes/physical_lithography_plasma_electron_state_confinement.py
================================================================

How long absorbed energy stays in the electrons before leaking out. The
loss path runs across the plasma column, stretched by a direction cosine
into an effective path length; the loss speed is the species thermal speed
scaled by an electron-to-species transport multiplier. Path length over
speed gives the energy confinement time, the tau_E that converts absorbed
power into stored electron energy in the inventory module.
"""

import sympy as sp

from ..constants import ELECTRON_MASS
from ..core import Approximation
from .physical_lithography_plasma_drive import (
    lithography_source_plasma_column_radius,
)
from .physical_lithography_plasma_focus import (
    lithography_source_plasma_drive_acceptance_half_angle,
)
from .physical_lithography_plasma_species import (
    LITHOGRAPHY_SOURCE_PLASMA_STATE_REF,
    lithography_source_plasma_species_particle_mass,
    lithography_source_plasma_species_thermal_speed,
)
from .physical_lithography_plasma_electron_state_variables import (
    lithography_source_plasma_energy_confinement_time,
    lithography_source_plasma_energy_loss_path_direction_cosine,
    lithography_source_plasma_energy_loss_path_factor,
    lithography_source_plasma_energy_loss_path_length,
    lithography_source_plasma_energy_loss_speed,
    lithography_source_plasma_energy_loss_transport_speed_factor,
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


LITHOGRAPHY_SOURCE_PLASMA_ELECTRON_CONFINEMENT_EQUATIONS = [
    eq_lithography_source_plasma_energy_loss_path_direction_cosine_from_acceptance_angle,
    eq_lithography_source_plasma_energy_loss_path_factor_from_direction_cosine,
    eq_lithography_source_plasma_energy_loss_path_length_from_radius,
    eq_lithography_source_plasma_energy_loss_transport_speed_factor_from_mass_ratio,
    eq_lithography_source_plasma_energy_loss_speed_from_species_thermal_speed,
    eq_lithography_source_plasma_energy_confinement_time_from_loss_path,
]


__all__ = [
    "eq_lithography_source_plasma_energy_loss_path_direction_cosine_from_acceptance_angle",
    "eq_lithography_source_plasma_energy_loss_path_factor_from_direction_cosine",
    "eq_lithography_source_plasma_energy_loss_path_length_from_radius",
    "eq_lithography_source_plasma_energy_loss_transport_speed_factor_from_mass_ratio",
    "eq_lithography_source_plasma_energy_loss_speed_from_species_thermal_speed",
    "eq_lithography_source_plasma_energy_confinement_time_from_loss_path",
    "LITHOGRAPHY_SOURCE_PLASMA_ELECTRON_CONFINEMENT_EQUATIONS",
]
