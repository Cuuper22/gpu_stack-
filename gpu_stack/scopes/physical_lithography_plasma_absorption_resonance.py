"""
scopes/physical_lithography_plasma_absorption_resonance.py
==========================================================

Resonance, damping, oscillator, cross-section, and optical-depth equations
for source-plasma drive absorption.
"""

import sympy as sp

from ..constants import (
    ELEMENTARY_CHARGE,
    ELECTRON_MASS,
    EPSILON_0,
    SPEED_OF_LIGHT,
)
from ..core import Approximation, gt, valid_all
from .physical_lithography_plasma_absorption_variables import (
    lithography_source_plasma_absorption_collision_cross_section,
    lithography_source_plasma_absorption_cross_section,
    lithography_source_plasma_absorption_damping_rate,
    lithography_source_plasma_absorption_oscillator_strength,
    lithography_source_plasma_absorption_optical_depth,
    lithography_source_plasma_absorption_participating_electron_fraction,
    lithography_source_plasma_absorption_path_length,
    lithography_source_plasma_absorption_quality_factor,
    lithography_source_plasma_absorption_resonance_angular_frequency,
    lithography_source_plasma_absorption_resonance_to_drive_ratio,
    lithography_source_plasma_absorption_sum_rule_fraction,
    lithography_source_plasma_drive_beam_angular_frequency,
    lithography_source_plasma_drive_energy_absorption_fraction,
)
from .physical_lithography_plasma_species import (
    LITHOGRAPHY_SOURCE_PLASMA_STATE_REF,
    lithography_source_plasma_species_number_density,
    lithography_source_plasma_species_thermal_speed,
)
from .physical_lithography_species import lithography_source_proton_count


eq_lithography_source_plasma_absorption_resonance_from_drive_ratio = Approximation(
    "physical.eq.lithography_source_plasma_absorption_resonance_from_drive_ratio",
    lithography_source_plasma_absorption_resonance_angular_frequency.symbol,
    (
        lithography_source_plasma_absorption_resonance_to_drive_ratio.symbol
        * lithography_source_plasma_drive_beam_angular_frequency.symbol
    ),
    (
        (lithography_source_plasma_absorption_resonance_to_drive_ratio.symbol > 0)
        & (lithography_source_plasma_drive_beam_angular_frequency.symbol > 0)
    ),
    "Absorption resonance angular frequency from a normalized ratio to the drive angular frequency.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_damping_rate_from_species_collision = Approximation(
    "physical.eq.lithography_source_plasma_absorption_damping_rate_from_species_collision",
    lithography_source_plasma_absorption_damping_rate.symbol,
    (
        lithography_source_plasma_species_number_density.symbol
        * lithography_source_plasma_absorption_collision_cross_section.symbol
        * lithography_source_plasma_species_thermal_speed.symbol
    ),
    valid_all(
        gt(lithography_source_plasma_species_number_density.symbol, 0),
        gt(lithography_source_plasma_absorption_collision_cross_section.symbol, 0),
        gt(lithography_source_plasma_species_thermal_speed.symbol, 0),
    ),
    "Absorption damping rate from source-species collision frequency in the plasma.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_quality_factor_from_collision_damping = Approximation(
    "physical.eq.lithography_source_plasma_absorption_quality_factor_from_collision_damping",
    lithography_source_plasma_absorption_quality_factor.symbol,
    (
        lithography_source_plasma_absorption_resonance_angular_frequency.symbol
        / lithography_source_plasma_absorption_damping_rate.symbol
    ),
    valid_all(
        gt(lithography_source_plasma_absorption_resonance_angular_frequency.symbol, 0),
        gt(lithography_source_plasma_absorption_damping_rate.symbol, 0),
    ),
    "Absorption quality factor implied by resonance frequency and collisional damping rate.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_oscillator_strength_from_source_charge = Approximation(
    "physical.eq.lithography_source_plasma_absorption_oscillator_strength_from_source_charge",
    lithography_source_plasma_absorption_oscillator_strength.symbol,
    (
        lithography_source_proton_count.symbol
        * lithography_source_plasma_absorption_participating_electron_fraction.symbol
        * lithography_source_plasma_absorption_sum_rule_fraction.symbol
    ),
    (
        (lithography_source_proton_count.symbol > 0)
        & (
            lithography_source_plasma_absorption_participating_electron_fraction.symbol
            > 0
        )
        & (
            lithography_source_plasma_absorption_participating_electron_fraction.symbol
            <= 1
        )
        & (lithography_source_plasma_absorption_sum_rule_fraction.symbol > 0)
        & (lithography_source_plasma_absorption_sum_rule_fraction.symbol <= 1)
    ),
    "Oscillator strength from source charge count and participating absorption-electron fractions.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_cross_section_from_lorentz_oscillator = Approximation(
    "physical.eq.lithography_source_plasma_absorption_cross_section_from_lorentz_oscillator",
    lithography_source_plasma_absorption_cross_section.symbol,
    (
        lithography_source_plasma_absorption_oscillator_strength.symbol
        * ELEMENTARY_CHARGE.symbol**2
        * lithography_source_plasma_absorption_damping_rate.symbol
        * lithography_source_plasma_drive_beam_angular_frequency.symbol**2
        / (
            ELECTRON_MASS.symbol
            * EPSILON_0.symbol
            * SPEED_OF_LIGHT.symbol
            * (
                (
                    lithography_source_plasma_absorption_resonance_angular_frequency.symbol**2
                    - lithography_source_plasma_drive_beam_angular_frequency.symbol**2
                )**2
                + (
                    lithography_source_plasma_absorption_damping_rate.symbol**2
                    * lithography_source_plasma_drive_beam_angular_frequency.symbol**2
                )
            )
        )
    ),
    (
        (lithography_source_plasma_absorption_oscillator_strength.symbol > 0)
        & (lithography_source_plasma_absorption_damping_rate.symbol > 0)
        & (lithography_source_plasma_absorption_resonance_angular_frequency.symbol > 0)
        & (lithography_source_plasma_drive_beam_angular_frequency.symbol > 0)
    ),
    "Lorentz-oscillator absorption cross section for the source-plasma drive beam.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_optical_depth = Approximation(
    "physical.eq.lithography_source_plasma_absorption_optical_depth",
    lithography_source_plasma_absorption_optical_depth.symbol,
    (
        lithography_source_plasma_species_number_density.symbol
        * lithography_source_plasma_absorption_cross_section.symbol
        * lithography_source_plasma_absorption_path_length.symbol
    ),
    (
        (lithography_source_plasma_species_number_density.symbol > 0)
        & (lithography_source_plasma_absorption_cross_section.symbol > 0)
        & (lithography_source_plasma_absorption_path_length.symbol > 0)
    ),
    "Drive absorption optical depth from species density, absorption cross section, and path length.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_energy_absorption_fraction_from_optical_depth = Approximation(
    "physical.eq.lithography_source_plasma_drive_energy_absorption_fraction_from_optical_depth",
    lithography_source_plasma_drive_energy_absorption_fraction.symbol,
    sp.Integer(1) - sp.exp(-lithography_source_plasma_absorption_optical_depth.symbol),
    lithography_source_plasma_absorption_optical_depth.symbol > 0,
    "Single-pass absorbed drive-energy fraction from effective optical depth.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_RESONANCE_EQUATIONS = [
    eq_lithography_source_plasma_absorption_resonance_from_drive_ratio,
    eq_lithography_source_plasma_absorption_damping_rate_from_species_collision,
    eq_lithography_source_plasma_absorption_quality_factor_from_collision_damping,
    eq_lithography_source_plasma_absorption_oscillator_strength_from_source_charge,
    eq_lithography_source_plasma_absorption_cross_section_from_lorentz_oscillator,
    eq_lithography_source_plasma_absorption_optical_depth,
    eq_lithography_source_plasma_drive_energy_absorption_fraction_from_optical_depth,
]

LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_RESONANCE_EXPORTS = [
    "eq_lithography_source_plasma_absorption_resonance_from_drive_ratio",
    "eq_lithography_source_plasma_absorption_damping_rate_from_species_collision",
    "eq_lithography_source_plasma_absorption_quality_factor_from_collision_damping",
    "eq_lithography_source_plasma_absorption_oscillator_strength_from_source_charge",
    "eq_lithography_source_plasma_absorption_cross_section_from_lorentz_oscillator",
    "eq_lithography_source_plasma_absorption_optical_depth",
    "eq_lithography_source_plasma_drive_energy_absorption_fraction_from_optical_depth",
]

__all__ = LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_RESONANCE_EXPORTS
