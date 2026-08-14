"""
scopes/physical_lithography_plasma_focus_spot.py
================================================

The focused drive spot. Spot radius scales as waist coefficient times
f-number times wavelength times beam quality -- a slower (higher f-number)
or dirtier (higher M-squared) beam focuses to a bigger spot. The Rayleigh
range says how far from focus the beam stays tight, and twice that, the
confocal length, sets the useful interaction length for the plasma column.
Spot radius with an elliptical shape factor gives the illuminated area that
divides pulse energy into fluence.
"""

import sympy as sp

from ..core import Approximation
from .physical_lithography_plasma_focus_variables import (
    lithography_source_plasma_drive_beam_quality_factor,
    lithography_source_plasma_drive_beam_wavelength,
    lithography_source_plasma_drive_confocal_length,
    lithography_source_plasma_drive_focus_f_number,
    lithography_source_plasma_drive_focus_waist_coefficient,
    lithography_source_plasma_drive_rayleigh_range,
    lithography_source_plasma_drive_spot_area,
    lithography_source_plasma_drive_spot_area_fill_factor,
    lithography_source_plasma_drive_spot_axis_ratio,
    lithography_source_plasma_drive_spot_radius,
    lithography_source_plasma_drive_spot_shape_factor,
)
from .physical_lithography_plasma_species import LITHOGRAPHY_SOURCE_PLASMA_STATE_REF


eq_lithography_source_plasma_drive_spot_radius_from_focus = Approximation(
    "physical.eq.lithography_source_plasma_drive_spot_radius_from_focus",
    lithography_source_plasma_drive_spot_radius.symbol,
    (
        lithography_source_plasma_drive_focus_waist_coefficient.symbol
        * lithography_source_plasma_drive_beam_quality_factor.symbol
        * lithography_source_plasma_drive_focus_f_number.symbol
        * lithography_source_plasma_drive_beam_wavelength.symbol
    ),
    (
        (lithography_source_plasma_drive_focus_waist_coefficient.symbol > 0)
        & (lithography_source_plasma_drive_beam_quality_factor.symbol > 0)
        & (lithography_source_plasma_drive_focus_f_number.symbol > 0)
        & (lithography_source_plasma_drive_beam_wavelength.symbol > 0)
    ),
    "Effective source-plasma drive spot radius from focused beam wavelength, f-number, beam quality, and waist coefficient.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_rayleigh_range_from_spot_geometry = Approximation(
    "physical.eq.lithography_source_plasma_drive_rayleigh_range_from_spot_geometry",
    lithography_source_plasma_drive_rayleigh_range.symbol,
    (
        sp.pi
        * lithography_source_plasma_drive_spot_radius.symbol**2
        / (
            lithography_source_plasma_drive_beam_quality_factor.symbol
            * lithography_source_plasma_drive_beam_wavelength.symbol
        )
    ),
    (
        (lithography_source_plasma_drive_spot_radius.symbol > 0)
        & (lithography_source_plasma_drive_beam_quality_factor.symbol >= 1)
        & (lithography_source_plasma_drive_beam_wavelength.symbol > 0)
    ),
    "Focused-beam Rayleigh range from spot radius, beam quality, and drive wavelength.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_confocal_length_from_rayleigh_range = Approximation(
    "physical.eq.lithography_source_plasma_drive_confocal_length_from_rayleigh_range",
    lithography_source_plasma_drive_confocal_length.symbol,
    sp.Integer(2) * lithography_source_plasma_drive_rayleigh_range.symbol,
    lithography_source_plasma_drive_rayleigh_range.symbol > 0,
    "Focused-beam confocal length from twice the Rayleigh range.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention = Approximation(
    "physical.eq.lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention",
    lithography_source_plasma_drive_spot_axis_ratio.symbol,
    sp.Integer(1),
    sp.S.true,
    "Default circular source-plasma drive spot convention with equal minor and major axes.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention = Approximation(
    "physical.eq.lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention",
    lithography_source_plasma_drive_spot_area_fill_factor.symbol,
    sp.Integer(1),
    sp.S.true,
    "Default source-plasma drive spot convention using the full nominal illuminated ellipse.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_spot_shape_factor_from_ellipse = Approximation(
    "physical.eq.lithography_source_plasma_drive_spot_shape_factor_from_ellipse",
    lithography_source_plasma_drive_spot_shape_factor.symbol,
    (
        lithography_source_plasma_drive_spot_axis_ratio.symbol
        * lithography_source_plasma_drive_spot_area_fill_factor.symbol
    ),
    (
        (lithography_source_plasma_drive_spot_axis_ratio.symbol > 0)
        & (lithography_source_plasma_drive_spot_axis_ratio.symbol <= 1)
        & (lithography_source_plasma_drive_spot_area_fill_factor.symbol > 0)
        & (lithography_source_plasma_drive_spot_area_fill_factor.symbol <= 1)
    ),
    "Drive spot shape factor from elliptical axis ratio and illuminated area fill factor.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_spot_area_from_radius = Approximation(
    "physical.eq.lithography_source_plasma_drive_spot_area_from_radius",
    lithography_source_plasma_drive_spot_area.symbol,
    (
        sp.pi
        * lithography_source_plasma_drive_spot_radius.symbol**2
        * lithography_source_plasma_drive_spot_shape_factor.symbol
    ),
    (
        (lithography_source_plasma_drive_spot_radius.symbol > 0)
        & (lithography_source_plasma_drive_spot_shape_factor.symbol > 0)
    ),
    "Effective source-plasma drive spot area from spot radius and shape factor.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_PLASMA_FOCUS_SPOT_EQUATIONS = [
    eq_lithography_source_plasma_drive_spot_radius_from_focus,
    eq_lithography_source_plasma_drive_rayleigh_range_from_spot_geometry,
    eq_lithography_source_plasma_drive_confocal_length_from_rayleigh_range,
    eq_lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention,
    eq_lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention,
    eq_lithography_source_plasma_drive_spot_shape_factor_from_ellipse,
    eq_lithography_source_plasma_drive_spot_area_from_radius,
]

LITHOGRAPHY_SOURCE_PLASMA_FOCUS_SPOT_EXPORTS = [
    "eq_lithography_source_plasma_drive_spot_radius_from_focus",
    "eq_lithography_source_plasma_drive_rayleigh_range_from_spot_geometry",
    "eq_lithography_source_plasma_drive_confocal_length_from_rayleigh_range",
    "eq_lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention",
    "eq_lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention",
    "eq_lithography_source_plasma_drive_spot_shape_factor_from_ellipse",
    "eq_lithography_source_plasma_drive_spot_area_from_radius",
]

__all__ = [
    *LITHOGRAPHY_SOURCE_PLASMA_FOCUS_SPOT_EXPORTS,
    "LITHOGRAPHY_SOURCE_PLASMA_FOCUS_SPOT_EQUATIONS",
    "LITHOGRAPHY_SOURCE_PLASMA_FOCUS_SPOT_EXPORTS",
]
