"""
scopes/physical_lithography_plasma_drive_energy.py
==================================================

Energy bookkeeping for the plasma drive. Pulse energy is peak intensity
times illuminated spot area times pulse duration times a temporal shape
factor that accounts for the ramp-up, plateau, and ramp-down of a real
pulse. Average drive power is pulse energy times repetition rate, and a
constraint keeps the pulse duration inside the pulse period. The absorption
chain multiplies this power by its efficiency factors to get plasma
heating power.
"""

from ..core import Approximation, Inequality
from ..core.units import JOULE, WATT
from .physical_lithography_plasma_common import plasma_var
from .physical_lithography_plasma_drive_pulse import (
    lithography_source_plasma_drive_peak_intensity,
    lithography_source_plasma_drive_pulse_duration,
    lithography_source_plasma_drive_pulse_temporal_shape_factor,
    lithography_source_plasma_pulse_period,
    lithography_source_plasma_pulse_repetition_rate,
)
from .physical_lithography_plasma_focus import (
    lithography_source_plasma_drive_spot_area,
)
from .physical_lithography_plasma_species import LITHOGRAPHY_SOURCE_PLASMA_STATE_REF


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


LITHOGRAPHY_SOURCE_PLASMA_DRIVE_ENERGY_VARIABLES = [
    lithography_source_plasma_pulse_energy,
    lithography_source_plasma_drive_power,
]

LITHOGRAPHY_SOURCE_PLASMA_DRIVE_ENERGY_EQUATIONS = [
    eq_lithography_source_plasma_pulse_energy_from_intensity_area_duration,
    ineq_lithography_source_plasma_pulse_duration_within_period,
    eq_lithography_source_plasma_drive_power_from_pulses,
]

LITHOGRAPHY_SOURCE_PLASMA_DRIVE_ENERGY_EXPORTS = [
    "lithography_source_plasma_pulse_energy",
    "lithography_source_plasma_drive_power",
    "eq_lithography_source_plasma_pulse_energy_from_intensity_area_duration",
    "ineq_lithography_source_plasma_pulse_duration_within_period",
    "eq_lithography_source_plasma_drive_power_from_pulses",
    "LITHOGRAPHY_SOURCE_PLASMA_DRIVE_ENERGY_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_DRIVE_ENERGY_EQUATIONS",
    "LITHOGRAPHY_SOURCE_PLASMA_DRIVE_ENERGY_EXPORTS",
]

__all__ = LITHOGRAPHY_SOURCE_PLASMA_DRIVE_ENERGY_EXPORTS
