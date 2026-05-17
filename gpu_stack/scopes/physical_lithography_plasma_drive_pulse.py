"""
scopes/physical_lithography_plasma_drive_pulse.py
=================================================

Pulse timing, pulse fractions, and incident intensity for the lithography
source-plasma drive.
"""

import sympy as sp

from ..core import Approximation, Inequality
from ..core.units import JOULE, METER, SECOND, WATT
from .physical_lithography_plasma_common import (
    DIMENSIONLESS,
    plasma_fraction,
    plasma_var,
)
from .physical_lithography_plasma_species import LITHOGRAPHY_SOURCE_PLASMA_STATE_REF


lithography_source_plasma_pulse_period = plasma_var(
    "source_plasma_pulse_period",
    "T_pulse_period_litho_src",
    "s",
    "Time between source-plasma drive pulses.",
    sp_units=SECOND,
)
lithography_source_plasma_pulse_repetition_rate = plasma_var(
    "source_plasma_pulse_repetition_rate",
    "f_pulse_litho_src",
    "1/s",
    "Pulse repetition rate of the lithography source plasma drive.",
    sp_units=sp.Integer(1) / SECOND,
)
lithography_source_plasma_drive_pulse_duty_factor = plasma_fraction(
    "source_plasma_drive_pulse_duty_factor",
    "D_pulse_drive_litho_src",
    "Fraction of each pulse period occupied by the effective source-plasma drive pulse.",
)
lithography_source_plasma_drive_pulse_fluence = plasma_var(
    "source_plasma_drive_pulse_fluence",
    "Phi_pulse_drive_plasma_litho_src",
    "J/m^2",
    "Drive-pulse energy per illuminated area delivered to the source-plasma spot.",
    sp_units=JOULE / METER**2,
)


def _pulse_fraction(kind, symbol, description, value_range=(0.0, 1.0)):
    return plasma_fraction(
        f"source_plasma_drive_pulse_{kind}_fraction",
        symbol,
        description,
        positive=False,
        value_range=value_range,
    )


lithography_source_plasma_drive_peak_intensity = plasma_var(
    "source_plasma_drive_peak_intensity",
    "I_peak_drive_plasma_litho_src",
    "W/m^2",
    "Peak drive intensity incident on the source-plasma spot during a pulse.",
    sp_units=WATT / METER**2,
)
lithography_source_plasma_drive_pulse_duration = plasma_var(
    "source_plasma_drive_pulse_duration",
    "tau_pulse_drive_litho_src",
    "s",
    "Effective source-plasma drive pulse duration.",
    sp_units=SECOND,
)
lithography_source_plasma_drive_pulse_rise_fraction = _pulse_fraction(
    "rise",
    "phi_rise_pulse_drive_litho_src",
    "Fraction of the effective drive pulse duration spent ramping up from zero to peak intensity under the symmetric fall-ramp convention.",
    value_range=(0.0, 0.5),
)
lithography_source_plasma_drive_pulse_fall_fraction = _pulse_fraction(
    "fall",
    "phi_fall_pulse_drive_litho_src",
    "Fraction of the effective drive pulse duration spent ramping down from peak intensity to zero.",
)
lithography_source_plasma_drive_pulse_flat_fraction = _pulse_fraction(
    "flat",
    "phi_flat_pulse_drive_litho_src",
    "Fraction of the effective drive pulse duration spent near peak intensity between ramp segments.",
)
lithography_source_plasma_drive_pulse_temporal_shape_factor = plasma_var(
    "source_plasma_drive_pulse_temporal_shape_factor",
    "chi_time_drive_litho_src",
    "dimensionless",
    "Temporal shape factor mapping peak intensity and pulse duration to effective pulse energy.",
    sp_units=DIMENSIONLESS,
)


eq_lithography_source_plasma_pulse_repetition_rate_from_period = Approximation(
    "physical.eq.lithography_source_plasma_pulse_repetition_rate_from_period",
    lithography_source_plasma_pulse_repetition_rate.symbol,
    sp.Integer(1) / lithography_source_plasma_pulse_period.symbol,
    lithography_source_plasma_pulse_period.symbol > 0,
    "Source plasma pulse repetition rate from pulse period.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_pulse_duration_from_duty_cycle = Approximation(
    "physical.eq.lithography_source_plasma_drive_pulse_duration_from_duty_cycle",
    lithography_source_plasma_drive_pulse_duration.symbol,
    (
        lithography_source_plasma_drive_pulse_duty_factor.symbol
        * lithography_source_plasma_pulse_period.symbol
    ),
    (
        (lithography_source_plasma_drive_pulse_duty_factor.symbol > 0)
        & (lithography_source_plasma_drive_pulse_duty_factor.symbol <= 1)
        & (lithography_source_plasma_pulse_period.symbol > 0)
    ),
    "Source plasma drive pulse duration from pulse period and duty factor.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_drive_pulse_duty_factor_within_unit_interval = Inequality(
    "physical.ineq.lithography_source_plasma_drive_pulse_duty_factor_within_unit_interval",
    lithography_source_plasma_drive_pulse_duty_factor.symbol,
    sp.Integer(1),
    "<=",
    "Source plasma drive pulse duty factor cannot exceed one pulse period.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
_pulse_fluence = lithography_source_plasma_drive_pulse_fluence.symbol
_pulse_duration = lithography_source_plasma_drive_pulse_duration.symbol
_pulse_fall_fraction = lithography_source_plasma_drive_pulse_fall_fraction.symbol
_pulse_flat_fraction = lithography_source_plasma_drive_pulse_flat_fraction.symbol
_pulse_rise_fraction = lithography_source_plasma_drive_pulse_rise_fraction.symbol
_pulse_shape_factor = lithography_source_plasma_drive_pulse_temporal_shape_factor.symbol

eq_lithography_source_plasma_drive_pulse_fall_fraction_from_symmetric_ramp = Approximation(
    "physical.eq.lithography_source_plasma_drive_pulse_fall_fraction_from_symmetric_ramp",
    _pulse_fall_fraction,
    _pulse_rise_fraction,
    (_pulse_rise_fraction >= 0) & (_pulse_rise_fraction <= sp.Rational(1, 2)),
    "Drive pulse fall fraction from a symmetric rise/fall ramp convention.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_pulse_flat_fraction_from_ramps = Approximation(
    "physical.eq.lithography_source_plasma_drive_pulse_flat_fraction_from_ramps",
    _pulse_flat_fraction,
    sp.Integer(1) - _pulse_rise_fraction - _pulse_fall_fraction,
    (
        (_pulse_rise_fraction >= 0)
        & (_pulse_fall_fraction >= 0)
        & (_pulse_rise_fraction + _pulse_fall_fraction <= 1)
    ),
    "Flat-top pulse fraction from the remaining duration after rise and fall ramps.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_pulse_temporal_shape_factor_from_trapezoid = Approximation(
    "physical.eq.lithography_source_plasma_drive_pulse_temporal_shape_factor_from_trapezoid",
    lithography_source_plasma_drive_pulse_temporal_shape_factor.symbol,
    _pulse_flat_fraction
    + (_pulse_rise_fraction + _pulse_fall_fraction) / sp.Integer(2),
    (
        (_pulse_flat_fraction >= 0)
        & (_pulse_rise_fraction >= 0)
        & (_pulse_fall_fraction >= 0)
        & (_pulse_flat_fraction + _pulse_rise_fraction + _pulse_fall_fraction <= 1)
    ),
    "Temporal shape factor from a normalized trapezoidal drive-pulse waveform.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_drive_pulse_ramp_fractions_within_pulse = Inequality(
    "physical.ineq.lithography_source_plasma_drive_pulse_ramp_fractions_within_pulse",
    _pulse_rise_fraction + _pulse_fall_fraction,
    sp.Integer(1),
    "<=",
    "Source plasma pulse rise and fall fractions must leave a nonnegative flat-top interval.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_drive_pulse_duration_fractions_within_pulse = Inequality(
    "physical.ineq.lithography_source_plasma_drive_pulse_duration_fractions_within_pulse",
    _pulse_rise_fraction + _pulse_flat_fraction + _pulse_fall_fraction,
    sp.Integer(1),
    "<=",
    "Source plasma pulse rise, flat-top, and fall fractions cannot exceed the normalized pulse duration.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_drive_pulse_temporal_shape_factor_within_unit_interval = Inequality(
    "physical.ineq.lithography_source_plasma_drive_pulse_temporal_shape_factor_within_unit_interval",
    _pulse_shape_factor,
    sp.Integer(1),
    "<=",
    "Source plasma drive temporal shape factor cannot exceed unity when normalized to peak intensity.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_peak_intensity_from_fluence = Approximation(
    "physical.eq.lithography_source_plasma_drive_peak_intensity_from_fluence",
    lithography_source_plasma_drive_peak_intensity.symbol,
    _pulse_fluence / (_pulse_duration * _pulse_shape_factor),
    (
        (_pulse_fluence > 0)
        & (_pulse_duration > 0)
        & (_pulse_shape_factor > 0)
    ),
    "Peak drive intensity from pulse fluence, effective duration, and temporal shape factor.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_drive_peak_intensity_at_least_pulse_average_intensity = Inequality(
    "physical.ineq.lithography_source_plasma_drive_peak_intensity_at_least_pulse_average_intensity",
    lithography_source_plasma_drive_peak_intensity.symbol,
    _pulse_fluence / _pulse_duration,
    ">=",
    "Source plasma drive peak intensity must be at least the pulse-average intensity implied by fluence and duration.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_PLASMA_DRIVE_PULSE_VARIABLES = [
    lithography_source_plasma_pulse_period,
    lithography_source_plasma_pulse_repetition_rate,
    lithography_source_plasma_drive_pulse_duty_factor,
    lithography_source_plasma_drive_pulse_fluence,
    lithography_source_plasma_drive_peak_intensity,
    lithography_source_plasma_drive_pulse_duration,
    lithography_source_plasma_drive_pulse_rise_fraction,
    lithography_source_plasma_drive_pulse_fall_fraction,
    lithography_source_plasma_drive_pulse_flat_fraction,
    lithography_source_plasma_drive_pulse_temporal_shape_factor,
]

LITHOGRAPHY_SOURCE_PLASMA_DRIVE_PULSE_EQUATIONS = [
    eq_lithography_source_plasma_pulse_repetition_rate_from_period,
    eq_lithography_source_plasma_drive_pulse_duration_from_duty_cycle,
    ineq_lithography_source_plasma_drive_pulse_duty_factor_within_unit_interval,
    eq_lithography_source_plasma_drive_pulse_fall_fraction_from_symmetric_ramp,
    eq_lithography_source_plasma_drive_pulse_flat_fraction_from_ramps,
    eq_lithography_source_plasma_drive_pulse_temporal_shape_factor_from_trapezoid,
    ineq_lithography_source_plasma_drive_pulse_ramp_fractions_within_pulse,
    ineq_lithography_source_plasma_drive_pulse_duration_fractions_within_pulse,
    ineq_lithography_source_plasma_drive_pulse_temporal_shape_factor_within_unit_interval,
    eq_lithography_source_plasma_drive_peak_intensity_from_fluence,
    ineq_lithography_source_plasma_drive_peak_intensity_at_least_pulse_average_intensity,
]

LITHOGRAPHY_SOURCE_PLASMA_DRIVE_PULSE_EXPORTS = [
    "lithography_source_plasma_pulse_period",
    "lithography_source_plasma_pulse_repetition_rate",
    "lithography_source_plasma_drive_pulse_duty_factor",
    "lithography_source_plasma_drive_pulse_fluence",
    "lithography_source_plasma_drive_peak_intensity",
    "lithography_source_plasma_drive_pulse_duration",
    "lithography_source_plasma_drive_pulse_rise_fraction",
    "lithography_source_plasma_drive_pulse_fall_fraction",
    "lithography_source_plasma_drive_pulse_flat_fraction",
    "lithography_source_plasma_drive_pulse_temporal_shape_factor",
    "eq_lithography_source_plasma_pulse_repetition_rate_from_period",
    "eq_lithography_source_plasma_drive_pulse_duration_from_duty_cycle",
    "ineq_lithography_source_plasma_drive_pulse_duty_factor_within_unit_interval",
    "eq_lithography_source_plasma_drive_pulse_fall_fraction_from_symmetric_ramp",
    "eq_lithography_source_plasma_drive_pulse_flat_fraction_from_ramps",
    "eq_lithography_source_plasma_drive_pulse_temporal_shape_factor_from_trapezoid",
    "ineq_lithography_source_plasma_drive_pulse_ramp_fractions_within_pulse",
    "ineq_lithography_source_plasma_drive_pulse_duration_fractions_within_pulse",
    "ineq_lithography_source_plasma_drive_pulse_temporal_shape_factor_within_unit_interval",
    "eq_lithography_source_plasma_drive_peak_intensity_from_fluence",
    "ineq_lithography_source_plasma_drive_peak_intensity_at_least_pulse_average_intensity",
    "LITHOGRAPHY_SOURCE_PLASMA_DRIVE_PULSE_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_DRIVE_PULSE_EQUATIONS",
    "LITHOGRAPHY_SOURCE_PLASMA_DRIVE_PULSE_EXPORTS",
]

__all__ = LITHOGRAPHY_SOURCE_PLASMA_DRIVE_PULSE_EXPORTS
