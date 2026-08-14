"""
tests/test_lithography_source_plasma_feasibility.py
===================================================

Shared fixtures for the source-plasma feasibility test family. This module
holds the two constraint tables the sibling test modules iterate over — the
operating-input constraints (duty factor, detuning ratio, divergence,
pupil fill, heating and charge fractions, each with a value that should
violate it) and the gas/thermal constraints (positive pressure, temperature,
density, and a thermal speed that must stay below the speed of light) —
plus the small helpers that fetch a named constraint or validity check from
a resolve result and assert whether it passed. Keeping the tables here means
every sibling module tests the exact same list, so a constraint added to
the registry only needs one new table row to be covered everywhere.
"""

import sympy as sp

from gpu_stack import Registry
from gpu_stack.constants import SPEED_OF_LIGHT


SOURCE_PLASMA_OPERATING_CONSTRAINTS = [
    (
        "physical.ineq.lithography_source_plasma_drive_pulse_duty_factor_within_unit_interval",
        "physical.lithography.source_plasma_drive_pulse_duty_factor",
        "<=",
        sp.Integer(1),
        1.25,
        {},
    ),
    (
        "physical.ineq.lithography_source_plasma_drive_edge_detuning_ratio_below_ionization_edge",
        "physical.lithography.source_plasma_drive_edge_detuning_ratio",
        ">",
        sp.Integer(1),
        1.0,
        {},
    ),
    (
        "physical.ineq.lithography_source_plasma_drive_far_field_divergence_half_angle_within_forward_half_space",
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle",
        "<=",
        sp.pi / 2,
        2.0,
        {},
    ),
    (
        "physical.ineq.lithography_source_plasma_drive_far_field_divergence_within_acceptance",
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle",
        "<=",
        Registry.variables[
            "physical.lithography.source_plasma_drive_acceptance_half_angle"
        ].symbol,
        0.5,
        {
            "physical.lithography.source_plasma_drive_acceptance_half_angle": (
                0.25
            ),
        },
    ),
    (
        "physical.ineq.lithography_source_plasma_drive_pupil_beam_fill_factor_within_unit_interval",
        "physical.lithography.source_plasma_drive_pupil_beam_fill_factor",
        "<=",
        sp.Integer(1),
        1.25,
        {},
    ),
    (
        "physical.ineq.lithography_source_plasma_electron_heating_fraction_within_unit_interval",
        "physical.lithography.source_plasma_electron_heating_fraction",
        "<=",
        sp.Integer(1),
        1.25,
        {},
    ),
    (
        "physical.ineq.lithography_source_plasma_free_electron_inventory_charge_fraction_within_unit_interval",
        "physical.lithography.source_plasma_free_electron_inventory_charge_fraction",
        "<=",
        sp.Integer(1),
        1.25,
        {},
    ),
]


def _failed_constraint(result, equation):
    check = next(c for c in result.constraints if c.equation == equation)
    assert check.satisfied is False
    assert check.missing == set()
    return check


def _failed_validity(result, equation):
    check = next(
        c for c in result.approximation_validity if c.equation == equation
    )
    assert check.satisfied is False
    assert check.missing == set()
    return check


def _satisfied_constraint(result, equation):
    check = next(c for c in result.constraints if c.equation == equation)
    assert check.satisfied is True
    assert check.missing == set()
    return check


SOURCE_PLASMA_GAS_THERMAL_CONSTRAINTS = [
    (
        "physical.ineq.lithography_source_plasma_species_partial_pressure_positive",
        "physical.lithography.source_plasma_species_partial_pressure",
        ">",
        sp.Integer(0),
        0.0,
    ),
    (
        "physical.ineq.lithography_source_plasma_species_gas_temperature_positive",
        "physical.lithography.source_plasma_species_gas_temperature",
        ">",
        sp.Integer(0),
        0.0,
    ),
    (
        "physical.ineq.lithography_source_plasma_species_number_density_positive",
        "physical.lithography.source_plasma_species_number_density",
        ">",
        sp.Integer(0),
        0.0,
    ),
    (
        "physical.ineq.lithography_source_plasma_species_thermal_speed_positive",
        "physical.lithography.source_plasma_species_thermal_speed",
        ">",
        sp.Integer(0),
        0.0,
    ),
    (
        "physical.ineq.lithography_source_plasma_species_thermal_speed_subluminal",
        "physical.lithography.source_plasma_species_thermal_speed",
        "<",
        SPEED_OF_LIGHT.symbol,
        SPEED_OF_LIGHT.value * 1.1,
    ),
]
