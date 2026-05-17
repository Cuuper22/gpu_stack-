"""
scopes/physical_lithography_plasma_drive.py
===========================================

Pulse drive, gas inventory, and active-column geometry for the lithography
source plasma.
"""

import sympy as sp

from ..core import Approximation, Inequality
from ..core.units import JOULE, METER, SECOND, WATT
from .physical_lithography_plasma_common import (
    DIMENSIONLESS,
    plasma_fraction,
    plasma_var,
)
from .physical_lithography_plasma_focus import *
from .physical_lithography_plasma_focus import (
    LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EXPORTS,
    LITHOGRAPHY_SOURCE_PLASMA_FOCUS_VARIABLES,
)
from .physical_lithography_plasma_species import (
    LITHOGRAPHY_SOURCE_PLASMA_STATE_REF,
    eq_lithography_source_plasma_species_number_density_from_ideal_gas,
    ineq_lithography_source_plasma_species_gas_temperature_positive,
    ineq_lithography_source_plasma_species_number_density_positive,
    ineq_lithography_source_plasma_species_partial_pressure_positive,
    lithography_source_plasma_species_gas_temperature,
    lithography_source_plasma_species_number_density,
    lithography_source_plasma_species_partial_pressure,
    lithography_source_plasma_species_thermal_speed,
)


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
lithography_source_plasma_drive_pulse_fall_fraction = _pulse_fraction("fall", "phi_fall_pulse_drive_litho_src", "Fraction of the effective drive pulse duration spent ramping down from peak intensity to zero.")
lithography_source_plasma_drive_pulse_flat_fraction = _pulse_fraction("flat", "phi_flat_pulse_drive_litho_src", "Fraction of the effective drive pulse duration spent near peak intensity between ramp segments.")
lithography_source_plasma_drive_pulse_temporal_shape_factor = plasma_var(
    "source_plasma_drive_pulse_temporal_shape_factor",
    "chi_time_drive_litho_src",
    "dimensionless",
    "Temporal shape factor mapping peak intensity and pulse duration to effective pulse energy.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_pulse_energy = plasma_var(
    "source_plasma_pulse_energy",
    "E_pulse_plasma_litho_src",
    "J",
    "Energy delivered per source-plasma drive pulse.",
    sp_units=JOULE,
)
lithography_source_plasma_drive_power = plasma_var(
    "source_plasma_drive_power",
    "P_drive_litho_src",
    "W",
    "Input drive power delivered to the lithography source plasma system.",
    sp_units=WATT,
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
eq_lithography_source_plasma_pulse_energy_from_intensity_area_duration = Approximation(
    "physical.eq.lithography_source_plasma_pulse_energy_from_intensity_area_duration",
    lithography_source_plasma_pulse_energy.symbol,
    (
        lithography_source_plasma_drive_peak_intensity.symbol
        * lithography_source_plasma_drive_spot_area.symbol
        * lithography_source_plasma_drive_pulse_duration.symbol
        * lithography_source_plasma_drive_pulse_temporal_shape_factor.symbol
    ),
    (
        (lithography_source_plasma_drive_peak_intensity.symbol > 0)
        & (lithography_source_plasma_drive_spot_area.symbol > 0)
        & (lithography_source_plasma_drive_pulse_duration.symbol > 0)
        & (lithography_source_plasma_drive_pulse_temporal_shape_factor.symbol > 0)
    ),
    "Source plasma pulse energy from peak drive intensity, illuminated area, pulse duration, and temporal shape factor.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_pulse_duration_within_period = Inequality(
    "physical.ineq.lithography_source_plasma_pulse_duration_within_period",
    lithography_source_plasma_drive_pulse_duration.symbol,
    lithography_source_plasma_pulse_period.symbol,
    "<=",
    "Source plasma drive pulse duration must not exceed the pulse period.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_power_from_pulses = Approximation(
    "physical.eq.lithography_source_plasma_drive_power_from_pulses",
    lithography_source_plasma_drive_power.symbol,
    (
        lithography_source_plasma_pulse_energy.symbol
        * lithography_source_plasma_pulse_repetition_rate.symbol
    ),
    (
        (lithography_source_plasma_pulse_energy.symbol > 0)
        & (lithography_source_plasma_pulse_repetition_rate.symbol > 0)
    ),
    "Average source plasma drive power from pulse energy times pulse repetition rate.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
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


LITHOGRAPHY_SOURCE_PLASMA_DRIVE_VARIABLES = [
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
    *LITHOGRAPHY_SOURCE_PLASMA_FOCUS_VARIABLES,
    lithography_source_plasma_pulse_energy,
    lithography_source_plasma_drive_power,
    lithography_source_plasma_species_partial_pressure,
    lithography_source_plasma_species_gas_temperature,
    lithography_source_plasma_species_number_density,
    lithography_source_plasma_column_expansion_speed_factor,
    lithography_source_plasma_column_radial_expansion_speed,
    lithography_source_plasma_column_radius_expansion_factor,
    lithography_source_plasma_column_radius,
    lithography_source_plasma_column_aspect_ratio,
    lithography_source_plasma_column_length,
    lithography_source_plasma_active_fill_factor,
    lithography_source_plasma_active_volume,
]

LITHOGRAPHY_SOURCE_PLASMA_DRIVE_EQUATIONS = [
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
    *LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EQUATIONS,
    eq_lithography_source_plasma_pulse_energy_from_intensity_area_duration,
    ineq_lithography_source_plasma_pulse_duration_within_period,
    eq_lithography_source_plasma_drive_power_from_pulses,
    ineq_lithography_source_plasma_species_partial_pressure_positive,
    ineq_lithography_source_plasma_species_gas_temperature_positive,
    eq_lithography_source_plasma_species_number_density_from_ideal_gas,
    ineq_lithography_source_plasma_species_number_density_positive,
    eq_lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed,
    eq_lithography_source_plasma_column_radial_expansion_speed_from_species_thermal_speed,
    eq_lithography_source_plasma_column_radius_expansion_factor_from_radial_speed,
    eq_lithography_source_plasma_column_radius_from_drive_spot,
    eq_lithography_source_plasma_column_aspect_ratio_from_confocal_length,
    eq_lithography_source_plasma_column_length_from_aspect_ratio,
    eq_lithography_source_plasma_active_fill_factor_from_ideal_column_convention,
    eq_lithography_source_plasma_active_volume_from_column_geometry,
]


__all__ = [
    "LITHOGRAPHY_SOURCE_PLASMA_STATE_REF",
    *LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EXPORTS,
    "lithography_source_plasma_pulse_period", "lithography_source_plasma_pulse_repetition_rate",
    "lithography_source_plasma_drive_pulse_duty_factor", "lithography_source_plasma_drive_pulse_fluence",
    "lithography_source_plasma_drive_peak_intensity", "lithography_source_plasma_drive_pulse_duration",
    "lithography_source_plasma_drive_pulse_rise_fraction", "lithography_source_plasma_drive_pulse_fall_fraction",
    "lithography_source_plasma_drive_pulse_flat_fraction", "lithography_source_plasma_drive_pulse_temporal_shape_factor",
    "lithography_source_plasma_pulse_energy",
    "lithography_source_plasma_drive_power", "lithography_source_plasma_species_partial_pressure",
    "lithography_source_plasma_species_gas_temperature", "lithography_source_plasma_species_number_density",
    "lithography_source_plasma_column_expansion_speed_factor",
    "lithography_source_plasma_column_radial_expansion_speed", "lithography_source_plasma_column_radius_expansion_factor",
    "lithography_source_plasma_column_radius", "lithography_source_plasma_column_aspect_ratio",
    "lithography_source_plasma_column_length", "lithography_source_plasma_active_fill_factor",
    "lithography_source_plasma_active_volume",
    "eq_lithography_source_plasma_pulse_repetition_rate_from_period", "eq_lithography_source_plasma_drive_pulse_duration_from_duty_cycle",
    "ineq_lithography_source_plasma_drive_pulse_duty_factor_within_unit_interval",
    "eq_lithography_source_plasma_drive_pulse_fall_fraction_from_symmetric_ramp",
    "eq_lithography_source_plasma_drive_pulse_flat_fraction_from_ramps", "eq_lithography_source_plasma_drive_pulse_temporal_shape_factor_from_trapezoid",
    "ineq_lithography_source_plasma_drive_pulse_ramp_fractions_within_pulse",
    "ineq_lithography_source_plasma_drive_pulse_duration_fractions_within_pulse",
    "ineq_lithography_source_plasma_drive_pulse_temporal_shape_factor_within_unit_interval",
    "eq_lithography_source_plasma_drive_peak_intensity_from_fluence",
    "ineq_lithography_source_plasma_drive_peak_intensity_at_least_pulse_average_intensity",
    "eq_lithography_source_plasma_pulse_energy_from_intensity_area_duration",
    "ineq_lithography_source_plasma_pulse_duration_within_period", "eq_lithography_source_plasma_drive_power_from_pulses",
    "ineq_lithography_source_plasma_species_partial_pressure_positive",
    "ineq_lithography_source_plasma_species_gas_temperature_positive",
    "eq_lithography_source_plasma_species_number_density_from_ideal_gas",
    "ineq_lithography_source_plasma_species_number_density_positive",
    "eq_lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed",
    "eq_lithography_source_plasma_column_radial_expansion_speed_from_species_thermal_speed",
    "eq_lithography_source_plasma_column_radius_expansion_factor_from_radial_speed",
    "eq_lithography_source_plasma_column_radius_from_drive_spot",
    "eq_lithography_source_plasma_column_aspect_ratio_from_confocal_length",
    "eq_lithography_source_plasma_column_length_from_aspect_ratio",
    "eq_lithography_source_plasma_active_fill_factor_from_ideal_column_convention",
    "eq_lithography_source_plasma_active_volume_from_column_geometry",
    "LITHOGRAPHY_SOURCE_PLASMA_DRIVE_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_DRIVE_EQUATIONS",
]
