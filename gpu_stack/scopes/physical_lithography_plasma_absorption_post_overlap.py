"""
scopes/physical_lithography_plasma_absorption_post_overlap.py
=============================================================

Post-overlap electron-channel absorption efficiency and absorbed power.
"""

import sympy as sp

from ..core import Approximation, Inequality
from ..core.units import WATT
from .physical_lithography_plasma_absorption_variables import (
    lithography_source_plasma_drive_energy_absorption_fraction,
)
from .physical_lithography_plasma_common import plasma_fraction, plasma_var
from .physical_lithography_plasma_drive import lithography_source_plasma_drive_power

# Import overlap here so the registry sees pre-overlap absorption terms before
# overlap terms, and electron-channel absorption terms after overlap terms.
from .physical_lithography_plasma_overlap import (  # noqa: E402
    lithography_source_plasma_drive_overlap_factor,
)
from .physical_lithography_plasma_species import LITHOGRAPHY_SOURCE_PLASMA_STATE_REF


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


LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_VARIABLES = [
    lithography_source_plasma_electron_heating_fraction,
    lithography_source_plasma_absorption_efficiency,
    lithography_source_plasma_absorbed_power,
]

LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_EQUATIONS = [
    ineq_lithography_source_plasma_electron_heating_fraction_within_unit_interval,
    eq_lithography_source_plasma_absorption_efficiency_from_overlap_optical_depth_heating,
    eq_lithography_source_plasma_absorbed_power_from_drive,
]

LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_EXPORTS = [
    "lithography_source_plasma_electron_heating_fraction",
    "lithography_source_plasma_absorption_efficiency",
    "lithography_source_plasma_absorbed_power",
    "ineq_lithography_source_plasma_electron_heating_fraction_within_unit_interval",
    "eq_lithography_source_plasma_absorption_efficiency_from_overlap_optical_depth_heating",
    "eq_lithography_source_plasma_absorbed_power_from_drive",
]

__all__ = [
    *LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_EXPORTS,
    "LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_EQUATIONS",
]
