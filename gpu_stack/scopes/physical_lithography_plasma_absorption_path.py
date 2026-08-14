"""
scopes/physical_lithography_plasma_absorption_path.py
=====================================================

Path geometry for drive absorption. The drive-beam angular frequency
follows from its wavelength and the vacuum light speed. The absorption path
runs through the plasma column at an angle set by the focusing optics, so a
direction cosine and shape factor stretch the column length into the
effective path length the optical-depth relation uses.
"""

import sympy as sp

from ..constants import SPEED_OF_LIGHT
from ..core import Approximation
from .physical_lithography_plasma_absorption_variables import (
    lithography_source_plasma_absorption_path_direction_cosine,
    lithography_source_plasma_absorption_path_length,
    lithography_source_plasma_absorption_path_shape_factor,
    lithography_source_plasma_drive_beam_angular_frequency,
)
from .physical_lithography_plasma_drive import lithography_source_plasma_column_length
from .physical_lithography_plasma_focus import (
    lithography_source_plasma_drive_acceptance_half_angle,
    lithography_source_plasma_drive_beam_wavelength,
)
from .physical_lithography_plasma_species import LITHOGRAPHY_SOURCE_PLASMA_STATE_REF


eq_lithography_source_plasma_drive_beam_angular_frequency = Approximation(
    "physical.eq.lithography_source_plasma_drive_beam_angular_frequency",
    lithography_source_plasma_drive_beam_angular_frequency.symbol,
    (
        sp.Integer(2)
        * sp.pi
        * SPEED_OF_LIGHT.symbol
        / lithography_source_plasma_drive_beam_wavelength.symbol
    ),
    lithography_source_plasma_drive_beam_wavelength.symbol > 0,
    "Drive-beam angular frequency from drive wavelength and vacuum light speed.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_path_direction_cosine_from_acceptance_angle = Approximation(
    "physical.eq.lithography_source_plasma_absorption_path_direction_cosine_from_acceptance_angle",
    lithography_source_plasma_absorption_path_direction_cosine.symbol,
    sp.cos(lithography_source_plasma_drive_acceptance_half_angle.symbol),
    (
        (lithography_source_plasma_drive_acceptance_half_angle.symbol >= 0)
        & (lithography_source_plasma_drive_acceptance_half_angle.symbol < sp.pi / 2)
    ),
    "Absorption path direction cosine from the source-plasma drive acceptance half-angle.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_path_shape_factor_from_direction_cosine = Approximation(
    "physical.eq.lithography_source_plasma_absorption_path_shape_factor_from_direction_cosine",
    lithography_source_plasma_absorption_path_shape_factor.symbol,
    sp.Integer(1) / lithography_source_plasma_absorption_path_direction_cosine.symbol,
    (
        (lithography_source_plasma_absorption_path_direction_cosine.symbol > 0)
        & (lithography_source_plasma_absorption_path_direction_cosine.symbol <= 1)
    ),
    "Absorption path shape factor from the inverse direction cosine through the plasma column.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_path_length_from_column = Approximation(
    "physical.eq.lithography_source_plasma_absorption_path_length_from_column",
    lithography_source_plasma_absorption_path_length.symbol,
    (
        lithography_source_plasma_absorption_path_shape_factor.symbol
        * lithography_source_plasma_column_length.symbol
    ),
    (
        (lithography_source_plasma_absorption_path_shape_factor.symbol > 0)
        & (lithography_source_plasma_column_length.symbol > 0)
    ),
    "Absorption path length from plasma column length and path-shape factor.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PATH_EQUATIONS = [
    eq_lithography_source_plasma_drive_beam_angular_frequency,
    eq_lithography_source_plasma_absorption_path_direction_cosine_from_acceptance_angle,
    eq_lithography_source_plasma_absorption_path_shape_factor_from_direction_cosine,
    eq_lithography_source_plasma_absorption_path_length_from_column,
]

LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PATH_EXPORTS = [
    "eq_lithography_source_plasma_drive_beam_angular_frequency",
    "eq_lithography_source_plasma_absorption_path_direction_cosine_from_acceptance_angle",
    "eq_lithography_source_plasma_absorption_path_shape_factor_from_direction_cosine",
    "eq_lithography_source_plasma_absorption_path_length_from_column",
]

__all__ = LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PATH_EXPORTS
