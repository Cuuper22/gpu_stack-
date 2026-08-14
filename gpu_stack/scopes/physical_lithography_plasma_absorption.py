"""
scopes/physical_lithography_plasma_absorption.py
================================================

Compatibility surface for source-plasma drive absorption: how much of the
drive-beam power the plasma actually swallows, and how much of that reaches
the free electrons that do the heating. The implementation is split into
path-geometry, resonance/optical-depth, and post-overlap electron-channel
helper modules; this module preserves the historical public imports.
"""

from .physical_lithography_plasma_absorption_variables import *
from .physical_lithography_plasma_absorption_variables import (
    LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PRE_OVERLAP_VARIABLES,
)
from .physical_lithography_plasma_absorption_path import *
from .physical_lithography_plasma_absorption_path import (
    LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PATH_EQUATIONS as _PATH_EQUATIONS,
)
from .physical_lithography_plasma_absorption_resonance import *
from .physical_lithography_plasma_absorption_resonance import (
    LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_RESONANCE_EQUATIONS as _RESONANCE_EQUATIONS,
)
from .physical_lithography_plasma_absorption_post_overlap import *
from .physical_lithography_plasma_absorption_post_overlap import (
    LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_VARIABLES,
)


LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_VARIABLES = [
    *LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PRE_OVERLAP_VARIABLES,
    *LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_VARIABLES,
]

LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PRE_OVERLAP_EQUATIONS = [
    *_PATH_EQUATIONS,
    *_RESONANCE_EQUATIONS,
]

LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_EQUATIONS = [
    *LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PRE_OVERLAP_EQUATIONS,
    *LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_EQUATIONS,
]


__all__ = [
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
    "lithography_source_plasma_electron_heating_fraction",
    "lithography_source_plasma_absorption_efficiency",
    "lithography_source_plasma_absorbed_power",
    "eq_lithography_source_plasma_drive_beam_angular_frequency",
    "eq_lithography_source_plasma_absorption_path_direction_cosine_from_acceptance_angle",
    "eq_lithography_source_plasma_absorption_path_shape_factor_from_direction_cosine",
    "eq_lithography_source_plasma_absorption_path_length_from_column",
    "eq_lithography_source_plasma_absorption_resonance_from_drive_ratio",
    "eq_lithography_source_plasma_absorption_damping_rate_from_species_collision",
    "eq_lithography_source_plasma_absorption_quality_factor_from_collision_damping",
    "eq_lithography_source_plasma_absorption_oscillator_strength_from_source_charge",
    "eq_lithography_source_plasma_absorption_cross_section_from_lorentz_oscillator",
    "eq_lithography_source_plasma_absorption_optical_depth",
    "eq_lithography_source_plasma_drive_energy_absorption_fraction_from_optical_depth",
    "ineq_lithography_source_plasma_electron_heating_fraction_within_unit_interval",
    "eq_lithography_source_plasma_absorption_efficiency_from_overlap_optical_depth_heating",
    "eq_lithography_source_plasma_absorbed_power_from_drive",
    "LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_EQUATIONS",
]
