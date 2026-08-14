"""
scopes/physical_lithography_plasma_drive.py
===========================================

Compatibility surface for the source-plasma drive: the pulsed beam and gas
target that create the emitting plasma. Pulse timing and intensity, pulse
energy and average power, and the expanding active-column geometry live in
focused sibling modules (pulse, energy, column); this module re-exports
them and preserves the historical public import surface.
"""

from .physical_lithography_plasma_focus import *
from .physical_lithography_plasma_focus import (
    LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EXPORTS,
    LITHOGRAPHY_SOURCE_PLASMA_FOCUS_VARIABLES,
)
from .physical_lithography_plasma_drive_pulse import (
    LITHOGRAPHY_SOURCE_PLASMA_DRIVE_PULSE_EQUATIONS as _PULSE_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_DRIVE_PULSE_VARIABLES as _PULSE_VARIABLES,
    eq_lithography_source_plasma_drive_peak_intensity_from_fluence,
    eq_lithography_source_plasma_drive_pulse_duration_from_duty_cycle,
    eq_lithography_source_plasma_drive_pulse_fall_fraction_from_symmetric_ramp,
    eq_lithography_source_plasma_drive_pulse_flat_fraction_from_ramps,
    eq_lithography_source_plasma_drive_pulse_temporal_shape_factor_from_trapezoid,
    eq_lithography_source_plasma_pulse_repetition_rate_from_period,
    ineq_lithography_source_plasma_drive_peak_intensity_at_least_pulse_average_intensity,
    ineq_lithography_source_plasma_drive_pulse_duration_fractions_within_pulse,
    ineq_lithography_source_plasma_drive_pulse_duty_factor_within_unit_interval,
    ineq_lithography_source_plasma_drive_pulse_ramp_fractions_within_pulse,
    ineq_lithography_source_plasma_drive_pulse_temporal_shape_factor_within_unit_interval,
    lithography_source_plasma_drive_peak_intensity,
    lithography_source_plasma_drive_pulse_duration,
    lithography_source_plasma_drive_pulse_duty_factor,
    lithography_source_plasma_drive_pulse_fall_fraction,
    lithography_source_plasma_drive_pulse_flat_fraction,
    lithography_source_plasma_drive_pulse_fluence,
    lithography_source_plasma_drive_pulse_rise_fraction,
    lithography_source_plasma_drive_pulse_temporal_shape_factor,
    lithography_source_plasma_pulse_period,
    lithography_source_plasma_pulse_repetition_rate,
)
from .physical_lithography_plasma_drive_energy import (
    LITHOGRAPHY_SOURCE_PLASMA_DRIVE_ENERGY_EQUATIONS as _ENERGY_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_DRIVE_ENERGY_VARIABLES as _ENERGY_VARIABLES,
    eq_lithography_source_plasma_drive_power_from_pulses,
    eq_lithography_source_plasma_pulse_energy_from_intensity_area_duration,
    ineq_lithography_source_plasma_pulse_duration_within_period,
    lithography_source_plasma_drive_power,
    lithography_source_plasma_pulse_energy,
)
from .physical_lithography_plasma_drive_column import (
    LITHOGRAPHY_SOURCE_PLASMA_DRIVE_COLUMN_EQUATIONS as _COLUMN_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_DRIVE_COLUMN_VARIABLES as _COLUMN_VARIABLES,
    eq_lithography_source_plasma_active_fill_factor_from_ideal_column_convention,
    eq_lithography_source_plasma_active_volume_from_column_geometry,
    eq_lithography_source_plasma_column_aspect_ratio_from_confocal_length,
    eq_lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed,
    eq_lithography_source_plasma_column_length_from_aspect_ratio,
    eq_lithography_source_plasma_column_radial_expansion_speed_from_species_thermal_speed,
    eq_lithography_source_plasma_column_radius_expansion_factor_from_radial_speed,
    eq_lithography_source_plasma_column_radius_from_drive_spot,
    lithography_source_plasma_active_fill_factor,
    lithography_source_plasma_active_volume,
    lithography_source_plasma_column_aspect_ratio,
    lithography_source_plasma_column_expansion_speed_factor,
    lithography_source_plasma_column_length,
    lithography_source_plasma_column_radial_expansion_speed,
    lithography_source_plasma_column_radius,
    lithography_source_plasma_column_radius_expansion_factor,
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
)


LITHOGRAPHY_SOURCE_PLASMA_DRIVE_VARIABLES = [
    *_PULSE_VARIABLES,
    *LITHOGRAPHY_SOURCE_PLASMA_FOCUS_VARIABLES,
    *_ENERGY_VARIABLES,
    lithography_source_plasma_species_partial_pressure,
    lithography_source_plasma_species_gas_temperature,
    lithography_source_plasma_species_number_density,
    *_COLUMN_VARIABLES,
]

LITHOGRAPHY_SOURCE_PLASMA_DRIVE_EQUATIONS = [
    *_PULSE_EQUATIONS,
    *LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EQUATIONS,
    *_ENERGY_EQUATIONS,
    ineq_lithography_source_plasma_species_partial_pressure_positive,
    ineq_lithography_source_plasma_species_gas_temperature_positive,
    eq_lithography_source_plasma_species_number_density_from_ideal_gas,
    ineq_lithography_source_plasma_species_number_density_positive,
    *_COLUMN_EQUATIONS,
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
