"""
scopes/physical_lithography_plasma_drive_column.py
==================================================

Active-column expansion and geometry for the lithography source plasma.
"""

import sympy as sp

from ..core import Approximation
from ..core.units import METER, SECOND
from .physical_lithography_plasma_common import (
    DIMENSIONLESS,
    plasma_fraction,
    plasma_var,
)
from .physical_lithography_plasma_drive_pulse import (
    lithography_source_plasma_drive_pulse_duration,
)
from .physical_lithography_plasma_focus import (
    lithography_source_plasma_drive_confocal_length,
    lithography_source_plasma_drive_spot_radius,
)
from .physical_lithography_plasma_species import (
    LITHOGRAPHY_SOURCE_PLASMA_STATE_REF,
    lithography_source_plasma_species_thermal_speed,
)


lithography_source_plasma_column_expansion_speed_factor = plasma_var(
    "source_plasma_column_expansion_speed_factor",
    "chi_v_col_expansion_litho_src",
    "dimensionless",
    "Multiplier mapping source-species thermal speed to plasma-column radial expansion speed.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_column_radial_expansion_speed = plasma_var(
    "source_plasma_column_radial_expansion_speed",
    "v_col_radial_expansion_litho_src",
    "m/s",
    "Effective radial expansion speed of the source plasma column during the drive pulse.",
    sp_units=METER / SECOND,
)
lithography_source_plasma_column_radius_expansion_factor = plasma_var(
    "source_plasma_column_radius_expansion_factor",
    "g_col_radius_litho_src",
    "dimensionless",
    "Expansion factor mapping drive spot radius to effective source plasma column radius.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_column_radius = plasma_var(
    "source_plasma_column_radius",
    "r_col_plasma_litho_src",
    "m",
    "Effective radius of the source plasma column.",
    sp_units=METER,
)
lithography_source_plasma_column_aspect_ratio = plasma_var(
    "source_plasma_column_aspect_ratio",
    "AR_col_plasma_litho_src",
    "dimensionless",
    "Effective source plasma column length divided by column radius.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_column_length = plasma_var(
    "source_plasma_column_length",
    "L_col_plasma_litho_src",
    "m",
    "Effective length of the source plasma column.",
    sp_units=METER,
)
lithography_source_plasma_active_fill_factor = plasma_fraction(
    "source_plasma_active_fill_factor",
    "phi_active_plasma_litho_src",
    "Fraction of the source plasma column volume occupied by the active emitting plasma.",
)
lithography_source_plasma_active_volume = plasma_var(
    "source_plasma_active_volume",
    "V_plasma_litho_src",
    "m^3",
    "Active plasma volume containing the free-electron inventory.",
    sp_units=METER**3,
)


eq_lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed = Approximation(
    "physical.eq.lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed",
    lithography_source_plasma_column_expansion_speed_factor.symbol,
    sp.sqrt(sp.Rational(5, 3)),
    sp.S.true,
    "Monatomic ideal-gas acoustic expansion factor relative to the source-species thermal speed scale.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_column_radial_expansion_speed_from_species_thermal_speed = Approximation(
    "physical.eq.lithography_source_plasma_column_radial_expansion_speed_from_species_thermal_speed",
    lithography_source_plasma_column_radial_expansion_speed.symbol,
    (
        lithography_source_plasma_column_expansion_speed_factor.symbol
        * lithography_source_plasma_species_thermal_speed.symbol
    ),
    (
        (lithography_source_plasma_column_expansion_speed_factor.symbol > 0)
        & (lithography_source_plasma_species_thermal_speed.symbol > 0)
    ),
    "Source plasma column radial expansion speed from the source-species thermal speed scale and the monatomic heavy-species sound-speed factor.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_column_radius_expansion_factor_from_radial_speed = Approximation(
    "physical.eq.lithography_source_plasma_column_radius_expansion_factor_from_radial_speed",
    lithography_source_plasma_column_radius_expansion_factor.symbol,
    (
        sp.Integer(1)
        + (
            lithography_source_plasma_column_radial_expansion_speed.symbol
            * lithography_source_plasma_drive_pulse_duration.symbol
            / lithography_source_plasma_drive_spot_radius.symbol
        )
    ),
    (
        (lithography_source_plasma_column_radial_expansion_speed.symbol > 0)
        & (lithography_source_plasma_drive_pulse_duration.symbol > 0)
        & (lithography_source_plasma_drive_spot_radius.symbol > 0)
    ),
    "Source plasma column radial expansion factor from convention-based radial expansion over the drive pulse relative to focused spot radius.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_column_radius_from_drive_spot = Approximation(
    "physical.eq.lithography_source_plasma_column_radius_from_drive_spot",
    lithography_source_plasma_column_radius.symbol,
    (
        lithography_source_plasma_drive_spot_radius.symbol
        * lithography_source_plasma_column_radius_expansion_factor.symbol
    ),
    (
        (lithography_source_plasma_drive_spot_radius.symbol > 0)
        & (lithography_source_plasma_column_radius_expansion_factor.symbol > 0)
    ),
    "Effective source plasma column radius from drive spot radius and expansion factor.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_column_aspect_ratio_from_confocal_length = Approximation(
    "physical.eq.lithography_source_plasma_column_aspect_ratio_from_confocal_length",
    lithography_source_plasma_column_aspect_ratio.symbol,
    (
        lithography_source_plasma_drive_confocal_length.symbol
        / lithography_source_plasma_column_radius.symbol
    ),
    (
        (lithography_source_plasma_drive_confocal_length.symbol > 0)
        & (lithography_source_plasma_column_radius.symbol > 0)
    ),
    "Effective source plasma column aspect ratio from drive confocal length over expanded column radius.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_column_length_from_aspect_ratio = Approximation(
    "physical.eq.lithography_source_plasma_column_length_from_aspect_ratio",
    lithography_source_plasma_column_length.symbol,
    (
        lithography_source_plasma_column_radius.symbol
        * lithography_source_plasma_column_aspect_ratio.symbol
    ),
    (
        (lithography_source_plasma_column_radius.symbol > 0)
        & (lithography_source_plasma_column_aspect_ratio.symbol > 0)
    ),
    "Effective source plasma column length from radius and aspect ratio.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_active_fill_factor_from_ideal_column_convention = Approximation(
    "physical.eq.lithography_source_plasma_active_fill_factor_from_ideal_column_convention",
    lithography_source_plasma_active_fill_factor.symbol,
    sp.Integer(1),
    sp.S.true,
    "Ideal active-column convention where the modeled plasma column is fully occupied by active emitting plasma.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_active_volume_from_column_geometry = Approximation(
    "physical.eq.lithography_source_plasma_active_volume_from_column_geometry",
    lithography_source_plasma_active_volume.symbol,
    (
        sp.pi
        * lithography_source_plasma_column_radius.symbol**2
        * lithography_source_plasma_column_length.symbol
        * lithography_source_plasma_active_fill_factor.symbol
    ),
    (
        (lithography_source_plasma_column_radius.symbol > 0)
        & (lithography_source_plasma_column_length.symbol > 0)
        & (lithography_source_plasma_active_fill_factor.symbol > 0)
        & (lithography_source_plasma_active_fill_factor.symbol <= 1)
    ),
    "Active source plasma volume from cylindrical column geometry and active fill factor.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_PLASMA_DRIVE_COLUMN_VARIABLES = [
    lithography_source_plasma_column_expansion_speed_factor,
    lithography_source_plasma_column_radial_expansion_speed,
    lithography_source_plasma_column_radius_expansion_factor,
    lithography_source_plasma_column_radius,
    lithography_source_plasma_column_aspect_ratio,
    lithography_source_plasma_column_length,
    lithography_source_plasma_active_fill_factor,
    lithography_source_plasma_active_volume,
]

LITHOGRAPHY_SOURCE_PLASMA_DRIVE_COLUMN_EQUATIONS = [
    eq_lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed,
    eq_lithography_source_plasma_column_radial_expansion_speed_from_species_thermal_speed,
    eq_lithography_source_plasma_column_radius_expansion_factor_from_radial_speed,
    eq_lithography_source_plasma_column_radius_from_drive_spot,
    eq_lithography_source_plasma_column_aspect_ratio_from_confocal_length,
    eq_lithography_source_plasma_column_length_from_aspect_ratio,
    eq_lithography_source_plasma_active_fill_factor_from_ideal_column_convention,
    eq_lithography_source_plasma_active_volume_from_column_geometry,
]

LITHOGRAPHY_SOURCE_PLASMA_DRIVE_COLUMN_EXPORTS = [
    "lithography_source_plasma_column_expansion_speed_factor",
    "lithography_source_plasma_column_radial_expansion_speed",
    "lithography_source_plasma_column_radius_expansion_factor",
    "lithography_source_plasma_column_radius",
    "lithography_source_plasma_column_aspect_ratio",
    "lithography_source_plasma_column_length",
    "lithography_source_plasma_active_fill_factor",
    "lithography_source_plasma_active_volume",
    "eq_lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed",
    "eq_lithography_source_plasma_column_radial_expansion_speed_from_species_thermal_speed",
    "eq_lithography_source_plasma_column_radius_expansion_factor_from_radial_speed",
    "eq_lithography_source_plasma_column_radius_from_drive_spot",
    "eq_lithography_source_plasma_column_aspect_ratio_from_confocal_length",
    "eq_lithography_source_plasma_column_length_from_aspect_ratio",
    "eq_lithography_source_plasma_active_fill_factor_from_ideal_column_convention",
    "eq_lithography_source_plasma_active_volume_from_column_geometry",
    "LITHOGRAPHY_SOURCE_PLASMA_DRIVE_COLUMN_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_DRIVE_COLUMN_EQUATIONS",
    "LITHOGRAPHY_SOURCE_PLASMA_DRIVE_COLUMN_EXPORTS",
]

__all__ = LITHOGRAPHY_SOURCE_PLASMA_DRIVE_COLUMN_EXPORTS
