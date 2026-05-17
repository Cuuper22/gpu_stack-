"""
scopes/physical_lithography_plasma_absorption_variables.py
===========================================================

Pre-overlap absorption variables for the lithography source plasma.
"""

import sympy as sp

from ..core.units import METER, SECOND
from .physical_lithography_plasma_common import (
    DIMENSIONLESS,
    plasma_fraction,
    plasma_var,
)


lithography_source_plasma_absorption_path_direction_cosine = plasma_fraction(
    "source_plasma_absorption_path_direction_cosine",
    "mu_abs_path_litho_src",
    "Direction cosine of the source-plasma absorption path relative to the plasma column axis.",
)
lithography_source_plasma_absorption_path_shape_factor = plasma_var(
    "source_plasma_absorption_path_shape_factor",
    "chi_abs_path_litho_src",
    "dimensionless",
    "Geometry factor mapping plasma column length to absorption path length.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_absorption_path_length = plasma_var(
    "source_plasma_absorption_path_length",
    "ell_abs_plasma_litho_src",
    "m",
    "Effective path length for source plasma drive absorption.",
    sp_units=METER,
)
lithography_source_plasma_drive_beam_angular_frequency = plasma_var(
    "source_plasma_drive_beam_angular_frequency",
    "omega_drive_plasma_litho_src",
    "1/s",
    "Angular frequency of the beam that drives source-plasma absorption.",
    sp_units=sp.Integer(1) / SECOND,
)
lithography_source_plasma_absorption_resonance_to_drive_ratio = plasma_var(
    "source_plasma_absorption_resonance_to_drive_ratio",
    "rho_omega_abs_drive_litho_src",
    "dimensionless",
    "Ratio of the dominant source-species absorption resonance to the drive-beam angular frequency.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_absorption_quality_factor = plasma_var(
    "source_plasma_absorption_quality_factor",
    "Q_abs_plasma_litho_src",
    "dimensionless",
    "Quality factor of the dominant source-species absorption resonance.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_absorption_collision_cross_section = plasma_var(
    "source_plasma_absorption_collision_cross_section",
    "sigma_abs_collision_litho_src",
    "m^2",
    "Effective source-species collision cross section controlling absorption-line damping.",
    sp_units=METER**2,
)
lithography_source_plasma_absorption_participating_electron_fraction = plasma_fraction(
    "source_plasma_absorption_participating_electron_fraction",
    "eta_e_abs_participating_litho_src",
    "Fraction of source nuclear charge contributing electrons to the dominant absorption oscillator.",
    positive=False,
)
lithography_source_plasma_absorption_sum_rule_fraction = plasma_fraction(
    "source_plasma_absorption_sum_rule_fraction",
    "eta_abs_sum_rule_litho_src",
    "Fraction of the available oscillator-strength sum rule carried by the dominant absorption resonance.",
    positive=False,
)
lithography_source_plasma_absorption_resonance_angular_frequency = plasma_var(
    "source_plasma_absorption_resonance_angular_frequency",
    "omega0_abs_plasma_litho_src",
    "1/s",
    "Dominant source-species resonance angular frequency for drive absorption.",
    sp_units=sp.Integer(1) / SECOND,
)
lithography_source_plasma_absorption_damping_rate = plasma_var(
    "source_plasma_absorption_damping_rate",
    "gamma_abs_plasma_litho_src",
    "1/s",
    "Effective damping rate of the source-species absorption resonance.",
    sp_units=sp.Integer(1) / SECOND,
)
lithography_source_plasma_absorption_oscillator_strength = plasma_var(
    "source_plasma_absorption_oscillator_strength",
    "f_abs_osc_plasma_litho_src",
    "dimensionless",
    "Dimensionless oscillator strength of the dominant source-plasma absorption resonance.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_absorption_cross_section = plasma_var(
    "source_plasma_absorption_cross_section",
    "sigma_abs_plasma_litho_src",
    "m^2",
    "Effective source-species cross section for drive-energy absorption.",
    sp_units=METER**2,
)
lithography_source_plasma_absorption_optical_depth = plasma_var(
    "source_plasma_absorption_optical_depth",
    "tau_abs_litho_src",
    "dimensionless",
    "Effective absorption optical depth across the source-plasma drive path.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_drive_energy_absorption_fraction = plasma_fraction(
    "source_plasma_drive_energy_absorption_fraction",
    "f_abs_drive_litho_src",
    "Single-pass fraction of drive energy absorbed by source species before channel factors.",
)


LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PRE_OVERLAP_VARIABLES = [
    lithography_source_plasma_absorption_path_direction_cosine,
    lithography_source_plasma_absorption_path_shape_factor,
    lithography_source_plasma_absorption_path_length,
    lithography_source_plasma_drive_beam_angular_frequency,
    lithography_source_plasma_absorption_resonance_to_drive_ratio,
    lithography_source_plasma_absorption_quality_factor,
    lithography_source_plasma_absorption_collision_cross_section,
    lithography_source_plasma_absorption_participating_electron_fraction,
    lithography_source_plasma_absorption_sum_rule_fraction,
    lithography_source_plasma_absorption_resonance_angular_frequency,
    lithography_source_plasma_absorption_damping_rate,
    lithography_source_plasma_absorption_oscillator_strength,
    lithography_source_plasma_absorption_cross_section,
    lithography_source_plasma_absorption_optical_depth,
    lithography_source_plasma_drive_energy_absorption_fraction,
]

LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_VARIABLE_EXPORTS = [
    "lithography_source_plasma_absorption_path_direction_cosine",
    "lithography_source_plasma_absorption_path_shape_factor",
    "lithography_source_plasma_absorption_path_length",
    "lithography_source_plasma_drive_beam_angular_frequency",
    "lithography_source_plasma_absorption_resonance_to_drive_ratio",
    "lithography_source_plasma_absorption_quality_factor",
    "lithography_source_plasma_absorption_collision_cross_section",
    "lithography_source_plasma_absorption_participating_electron_fraction",
    "lithography_source_plasma_absorption_sum_rule_fraction",
    "lithography_source_plasma_absorption_resonance_angular_frequency",
    "lithography_source_plasma_absorption_damping_rate",
    "lithography_source_plasma_absorption_oscillator_strength",
    "lithography_source_plasma_absorption_cross_section",
    "lithography_source_plasma_absorption_optical_depth",
    "lithography_source_plasma_drive_energy_absorption_fraction",
]

__all__ = [
    *LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_VARIABLE_EXPORTS,
    "LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PRE_OVERLAP_VARIABLES",
]
