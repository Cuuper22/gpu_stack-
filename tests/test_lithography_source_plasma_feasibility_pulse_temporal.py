"""
Pulse-shape and temporal feasibility coverage for source plasma drives.
"""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from tests.test_lithography_source_plasma_feasibility import (
    _failed_constraint,
)


def test_source_plasma_symmetric_rise_fraction_half_pulse_domain():
    variable_name = (
        "physical.lithography.source_plasma_drive_pulse_rise_fraction"
    )
    variable = Registry.variables[variable_name]
    assert variable.value_range == (0.0, 0.5)

    result = resolve(variable_name, assignments={variable_name: 0.6})
    assert float(result.value) == pytest.approx(0.6)
    _failed_constraint(
        result,
        "domain.physical.lithography.source_plasma_drive_pulse_rise_fraction.max",
    )


def test_source_plasma_symmetric_fall_approximation_declares_half_pulse_boundary():
    result = resolve(
        "physical.lithography.source_plasma_drive_pulse_fall_fraction",
        assignments={
            "physical.lithography.source_plasma_drive_pulse_rise_fraction": 0.6,
        },
    )

    assert float(result.value) == pytest.approx(0.6)
    validity = next(
        check
        for check in result.approximation_validity
        if check.equation
        == "physical.eq.lithography_source_plasma_drive_pulse_fall_fraction_from_symmetric_ramp"
    )
    assert validity.satisfied is False
    _failed_constraint(
        result,
        "domain.physical.lithography.source_plasma_drive_pulse_rise_fraction.max",
    )


def test_source_plasma_bpp_diffraction_constraints_report_invalid_fill_chain():
    result = resolve(
        "physical.lithography.source_plasma_drive_beam_quality_factor",
        assignments={
            "physical.lithography.source_plasma_drive_beam_wavelength": 1.0e-6,
            "physical.lithography.source_plasma_drive_objective_pupil_radius": 1.0e-6,
            "physical.lithography.source_plasma_drive_pupil_beam_fill_factor": 0.1,
            "physical.lithography.source_plasma_drive_far_field_divergence_half_angle": 1.0e-3,
        },
    )

    assert float(result.value) == pytest.approx(float(sp.pi) * 1.0e-4)
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_source_plasma_drive_beam_parameter_waist_radius_from_pupil_fill",
        "physical.eq.lithography_source_plasma_drive_beam_parameter_product_from_waist_divergence",
        "physical.eq.lithography_source_plasma_drive_beam_quality_factor_from_beam_parameter_product",
    ]
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_drive_beam_parameter_product_diffraction_floor",
    )
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_drive_beam_quality_factor_diffraction_limit",
    )


def test_source_plasma_symmetric_ramp_reports_overfull_pulse():
    result = resolve(
        "physical.lithography.source_plasma_drive_pulse_flat_fraction",
        assignments={
            "physical.lithography.source_plasma_drive_pulse_rise_fraction": 0.6,
        },
    )

    assert float(result.value) == pytest.approx(-0.2)
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_source_plasma_drive_pulse_fall_fraction_from_symmetric_ramp",
        "physical.eq.lithography_source_plasma_drive_pulse_flat_fraction_from_ramps",
    ]
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_drive_pulse_ramp_fractions_within_pulse",
    )
    _failed_constraint(
        result,
        "domain.physical.lithography.source_plasma_drive_pulse_flat_fraction.nonnegative",
    )


def test_source_plasma_explicit_pulse_fractions_cannot_exceed_duration():
    result = resolve(
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
        assignments={
            "physical.lithography.source_plasma_drive_pulse_rise_fraction": 0.4,
            "physical.lithography.source_plasma_drive_pulse_flat_fraction": 0.4,
            "physical.lithography.source_plasma_drive_pulse_fall_fraction": 0.4,
        },
    )

    assert float(result.value) == pytest.approx(0.8)
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_drive_pulse_duration_fractions_within_pulse",
    )


def test_source_plasma_temporal_shape_factor_cannot_exceed_peak_normalization():
    result = resolve(
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
        assignments={
            "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor": 1.25,
        },
    )

    assert float(result.value) == pytest.approx(1.25)
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_drive_pulse_temporal_shape_factor_within_unit_interval",
    )


def test_source_plasma_peak_intensity_cannot_undershoot_pulse_average():
    result = resolve(
        "physical.lithography.source_plasma_drive_peak_intensity",
        assignments={
            "physical.lithography.source_plasma_drive_peak_intensity": 5.0,
            "physical.lithography.source_plasma_drive_pulse_fluence": 10.0,
            "physical.lithography.source_plasma_drive_pulse_duration": 1.0,
        },
    )

    assert float(result.value) == pytest.approx(5.0)
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_drive_peak_intensity_at_least_pulse_average_intensity",
    )
