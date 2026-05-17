"""Lithography source-plasma operating chain coverage."""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.scopes import physical_lithography_absorption_edge as absorption_edge


def test_source_plasma_absorption_edge_uses_ionization_shell_chain():
    assert "LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF" in absorption_edge.__all__
    assert absorption_edge.LITHOGRAPHY_SOURCE_ABSORPTION_EDGE_REF

    hbar = Registry.variables["physics.hbar"].value
    c = Registry.variables["physics.speed_of_light"].value

    wavelength_result = resolve(
        "physical.lithography.source_plasma_drive_beam_wavelength",
        assignments={
            "physical.lithography.source_ionization_energy": 6.0 * hbar * c,
            "physical.lithography.source_plasma_drive_edge_detuning_ratio": 1.5,
        },
    )
    assert float(wavelength_result.value) == pytest.approx(
        1.5 * 2.0 * float(sp.pi) * hbar * c / (6.0 * hbar * c)
    )
    assert [step.equation for step in wavelength_result.trace] == [
        "physical.eq.lithography_source_plasma_drive_beam_wavelength_from_ionization_edge",
    ]

    resonance_result = resolve(
        "physical.lithography.source_plasma_absorption_resonance_to_drive_ratio",
        assignments={
            "physical.lithography.source_ionization_energy": 6.0 * hbar,
            "physical.lithography.source_plasma_drive_beam_angular_frequency": 3.0,
        },
    )
    assert float(resonance_result.value) == pytest.approx(2.0)
    assert [step.equation for step in resonance_result.trace] == [
        "physical.eq.lithography_source_plasma_absorption_resonance_to_drive_ratio_from_ionization_edge",
    ]

    participating_result = resolve(
        "physical.lithography.source_plasma_absorption_participating_electron_fraction",
        assignments={
            "physical.lithography.source_proton_count": 4.0,
            "physical.lithography.source_ionization_same_shell_screening_electron_count": 1.0,
        },
    )
    assert float(participating_result.value) == pytest.approx(0.5)
    assert [step.equation for step in participating_result.trace] == [
        "physical.eq.lithography_source_plasma_absorption_participating_electron_fraction_from_ionization_shell",
    ]

    sum_rule_result = resolve(
        "physical.lithography.source_plasma_absorption_sum_rule_fraction",
        assignments={
            "physical.lithography.source_transition_shell_capacity": 8.0,
            "physical.lithography.source_ionization_same_shell_screening_electron_count": 1.0,
        },
    )
    assert float(sum_rule_result.value) == pytest.approx(0.875)
    assert [step.equation for step in sum_rule_result.trace] == [
        "physical.eq.lithography_source_plasma_absorption_sum_rule_fraction_from_ionization_shell_degeneracy",
    ]


def test_source_plasma_operating_root_frontier_is_explicit():
    def deps(name):
        return {v.name for v in Registry.variables[name].direct_dependencies()}

    def assert_root(name):
        variable = Registry.variables[name]
        assert variable.is_root_input
        assert variable.direct_dependencies() == set()

    for root in {
        "physical.lithography.source_plasma_pulse_period",
        "physical.lithography.source_plasma_drive_pulse_duty_factor",
        "physical.lithography.source_plasma_drive_pulse_fluence",
        "physical.lithography.source_plasma_drive_edge_detuning_ratio",
        "physical.lithography.source_plasma_drive_objective_pupil_radius",
        "physical.lithography.source_plasma_drive_objective_focal_length",
        "physical.lithography.source_plasma_species_partial_pressure",
        "physical.lithography.source_plasma_species_gas_temperature",
    }:
        assert_root(root)

    assert deps("physical.lithography.source_plasma_pulse_repetition_rate") == {
        "physical.lithography.source_plasma_pulse_period",
    }
    assert deps("physical.lithography.source_plasma_drive_pulse_duration") == {
        "physical.lithography.source_plasma_drive_pulse_duty_factor",
        "physical.lithography.source_plasma_pulse_period",
    }
    assert deps("physical.lithography.source_plasma_drive_peak_intensity") == {
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_pulse_fluence",
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
    }
    assert deps("physical.lithography.source_plasma_drive_beam_wavelength") == {
        "physical.lithography.source_ionization_energy",
        "physical.lithography.source_plasma_drive_edge_detuning_ratio",
        "physics.hbar",
        "physics.speed_of_light",
    }
    assert deps("physical.lithography.source_plasma_drive_acceptance_half_angle") == {
        "physical.lithography.source_plasma_drive_objective_focal_length",
        "physical.lithography.source_plasma_drive_objective_pupil_radius",
    }
    assert deps("physical.lithography.source_plasma_species_number_density") == {
        "physical.lithography.source_plasma_species_gas_temperature",
        "physical.lithography.source_plasma_species_partial_pressure",
        "physics.boltzmann",
    }
