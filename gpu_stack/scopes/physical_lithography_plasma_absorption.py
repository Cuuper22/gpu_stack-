"""
scopes/physical_lithography_plasma_absorption.py
================================================

Optical-depth absorption and electron-channel power coupling for the
lithography source plasma.
"""

import sympy as sp

from ..constants import (
    ELEMENTARY_CHARGE,
    ELECTRON_MASS,
    EPSILON_0,
    SPEED_OF_LIGHT,
)
from ..core import Approximation, Inequality, gt, valid_all
from ..core.units import METER, SECOND, WATT
from .physical_lithography_plasma_common import (
    DIMENSIONLESS,
    plasma_fraction,
    plasma_var,
)
from .physical_lithography_plasma_drive import (
    lithography_source_plasma_column_length,
    lithography_source_plasma_drive_power,
)
from .physical_lithography_plasma_focus import (
    lithography_source_plasma_drive_acceptance_half_angle,
    lithography_source_plasma_drive_beam_wavelength,
)
from .physical_lithography_plasma_species import (
    LITHOGRAPHY_SOURCE_PLASMA_STATE_REF,
    lithography_source_plasma_species_number_density,
    lithography_source_plasma_species_thermal_speed,
)
from .physical_lithography_species import lithography_source_proton_count


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

# Keep overlap registration after pre-overlap absorption terms so raw registry
# order matches the public plasma-state assembly.
from .physical_lithography_plasma_overlap import (  # noqa: E402
    lithography_source_plasma_drive_overlap_factor,
)


lithography_source_plasma_electron_heating_fraction = plasma_fraction(
    "source_plasma_electron_heating_fraction",
    "eta_e_heat_plasma_litho_src",
    "Fraction of absorbed drive energy coupled into the free-electron energy channel.",
)
lithography_source_plasma_absorption_efficiency = plasma_fraction(
    "source_plasma_absorption_efficiency",
    "eta_abs_litho_src",
    "Fraction of source drive power absorbed into the free-electron plasma energy channel.",
)
lithography_source_plasma_absorbed_power = plasma_var(
    "source_plasma_absorbed_power",
    "P_abs_litho_src",
    "W",
    "Drive power absorbed into the source-plasma free-electron energy channel.",
    sp_units=WATT,
)

ineq_lithography_source_plasma_electron_heating_fraction_within_unit_interval = Inequality(
    "physical.ineq.lithography_source_plasma_electron_heating_fraction_within_unit_interval",
    lithography_source_plasma_electron_heating_fraction.symbol,
    sp.Integer(1),
    "<=",
    "Source-plasma electron heating fraction cannot exceed the absorbed drive-energy channel.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorption_efficiency_from_overlap_optical_depth_heating = Approximation(
    "physical.eq.lithography_source_plasma_absorption_efficiency_from_overlap_optical_depth_heating",
    lithography_source_plasma_absorption_efficiency.symbol,
    (
        lithography_source_plasma_drive_overlap_factor.symbol
        * lithography_source_plasma_drive_energy_absorption_fraction.symbol
        * lithography_source_plasma_electron_heating_fraction.symbol
    ),
    (
        (lithography_source_plasma_drive_overlap_factor.symbol > 0)
        & (lithography_source_plasma_drive_overlap_factor.symbol <= 1)
        & (lithography_source_plasma_drive_energy_absorption_fraction.symbol > 0)
        & (lithography_source_plasma_drive_energy_absorption_fraction.symbol <= 1)
        & (lithography_source_plasma_electron_heating_fraction.symbol > 0)
        & (lithography_source_plasma_electron_heating_fraction.symbol <= 1)
    ),
    "Electron-channel absorption efficiency from drive overlap, optical-depth absorption, and heating fraction.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_absorbed_power_from_drive = Approximation(
    "physical.eq.lithography_source_plasma_absorbed_power_from_drive",
    lithography_source_plasma_absorbed_power.symbol,
    (
        lithography_source_plasma_absorption_efficiency.symbol
        * lithography_source_plasma_drive_power.symbol
    ),
    (
        (lithography_source_plasma_absorption_efficiency.symbol > 0)
        & (lithography_source_plasma_absorption_efficiency.symbol <= 1)
        & (lithography_source_plasma_drive_power.symbol > 0)
    ),
    "Absorbed electron-channel plasma power from source drive power and absorption efficiency.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
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

LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_VARIABLES = [
    lithography_source_plasma_electron_heating_fraction,
    lithography_source_plasma_absorption_efficiency,
    lithography_source_plasma_absorbed_power,
]

LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_VARIABLES = [
    *LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PRE_OVERLAP_VARIABLES,
    *LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_VARIABLES,
]

LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PRE_OVERLAP_EQUATIONS = [
    eq_lithography_source_plasma_drive_beam_angular_frequency,
    eq_lithography_source_plasma_absorption_path_direction_cosine_from_acceptance_angle,
    eq_lithography_source_plasma_absorption_path_shape_factor_from_direction_cosine,
    eq_lithography_source_plasma_absorption_path_length_from_column,
    eq_lithography_source_plasma_absorption_resonance_from_drive_ratio,
    eq_lithography_source_plasma_absorption_damping_rate_from_species_collision,
    eq_lithography_source_plasma_absorption_quality_factor_from_collision_damping,
    eq_lithography_source_plasma_absorption_oscillator_strength_from_source_charge,
    eq_lithography_source_plasma_absorption_cross_section_from_lorentz_oscillator,
    eq_lithography_source_plasma_absorption_optical_depth,
    eq_lithography_source_plasma_drive_energy_absorption_fraction_from_optical_depth,
]

LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_EQUATIONS = [
    ineq_lithography_source_plasma_electron_heating_fraction_within_unit_interval,
    eq_lithography_source_plasma_absorption_efficiency_from_overlap_optical_depth_heating,
    eq_lithography_source_plasma_absorbed_power_from_drive,
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
