"""
tests/test_lithography_source_plasma_drive_boundaries.py
========================================================

The drive laser that ignites the source plasma is described by a handful of
root inputs: pulse period, duty factor, fluence, pulse-shape fractions, the
objective's pupil radius and focal length, the edge detuning ratio, and the
beam's far-field divergence. Each has hard physical bounds — durations and
lengths must be positive, factors like the duty cycle must sit inside the
unit interval, the divergence must stay in the forward half space and inside
the acceptance angle. This module assigns values that break each bound and
verifies the resolver's contract: the raw value is still returned (nothing
is silently clamped), the matching domain or named inequality is reported as
violated, and the damage propagates downstream — a bad duty factor also
flags the derived pulse duration, a bad fluence flags peak intensity, and
the equations that used the bad input have their validity marked failed.
It ends by confirming these roots stay pure assignment-only inputs with no
defining equations beyond their own constraints.
"""

import pytest

from gpu_stack import Registry, resolve


PULSE_PERIOD = "physical.lithography.source_plasma_pulse_period"
PULSE_REPETITION_RATE = "physical.lithography.source_plasma_pulse_repetition_rate"
PULSE_DUTY_FACTOR = "physical.lithography.source_plasma_drive_pulse_duty_factor"
PULSE_FLUENCE = "physical.lithography.source_plasma_drive_pulse_fluence"
PULSE_DURATION = "physical.lithography.source_plasma_drive_pulse_duration"
PULSE_RISE_FRACTION = "physical.lithography.source_plasma_drive_pulse_rise_fraction"
PULSE_FALL_FRACTION = "physical.lithography.source_plasma_drive_pulse_fall_fraction"
PULSE_FLAT_FRACTION = "physical.lithography.source_plasma_drive_pulse_flat_fraction"
PULSE_SHAPE_FACTOR = (
    "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor"
)
PEAK_INTENSITY = "physical.lithography.source_plasma_drive_peak_intensity"
EDGE_DETUNING_RATIO = (
    "physical.lithography.source_plasma_drive_edge_detuning_ratio"
)
OBJECTIVE_PUPIL_RADIUS = (
    "physical.lithography.source_plasma_drive_objective_pupil_radius"
)
OBJECTIVE_FOCAL_LENGTH = (
    "physical.lithography.source_plasma_drive_objective_focal_length"
)
PUPIL_BEAM_FILL_FACTOR = (
    "physical.lithography.source_plasma_drive_pupil_beam_fill_factor"
)
ACCEPTANCE_HALF_ANGLE = (
    "physical.lithography.source_plasma_drive_acceptance_half_angle"
)
FAR_FIELD_DIVERGENCE = (
    "physical.lithography.source_plasma_drive_far_field_divergence_half_angle"
)
INEQ_DUTY_FACTOR_WITHIN_UNIT = (
    "physical.ineq."
    "lithography_source_plasma_drive_pulse_duty_factor_within_unit_interval"
)
INEQ_EDGE_DETUNING_BELOW_EDGE = (
    "physical.ineq."
    "lithography_source_plasma_drive_edge_detuning_ratio_below_ionization_edge"
)
INEQ_FAR_FIELD_FORWARD = (
    "physical.ineq."
    "lithography_source_plasma_drive_far_field_divergence_half_angle_"
    "within_forward_half_space"
)
INEQ_FAR_FIELD_WITHIN_ACCEPTANCE = (
    "physical.ineq."
    "lithography_source_plasma_drive_far_field_divergence_within_acceptance"
)
INEQ_PUPIL_FILL_WITHIN_UNIT = (
    "physical.ineq."
    "lithography_source_plasma_drive_pupil_beam_fill_factor_within_unit_interval"
)
INEQ_PULSE_DURATION_WITHIN_PERIOD = (
    "physical.ineq.lithography_source_plasma_pulse_duration_within_period"
)
INEQ_RAMP_FRACTIONS_WITHIN_PULSE = (
    "physical.ineq.lithography_source_plasma_drive_pulse_ramp_fractions_within_pulse"
)
EQ_ACCEPTANCE_FROM_PUPIL = (
    "physical.eq."
    "lithography_source_plasma_drive_acceptance_half_angle_from_pupil_geometry"
)
EQ_FALL_FROM_SYMMETRIC_RAMP = (
    "physical.eq."
    "lithography_source_plasma_drive_pulse_fall_fraction_from_symmetric_ramp"
)
EQ_FLAT_FROM_RAMPS = (
    "physical.eq.lithography_source_plasma_drive_pulse_flat_fraction_from_ramps"
)
EQ_DURATION_FROM_DUTY = (
    "physical.eq.lithography_source_plasma_drive_pulse_duration_from_duty_cycle"
)
EQ_REPETITION_RATE_FROM_PERIOD = (
    "physical.eq.lithography_source_plasma_pulse_repetition_rate_from_period"
)
EQ_PEAK_INTENSITY_FROM_FLUENCE = (
    "physical.eq.lithography_source_plasma_drive_peak_intensity_from_fluence"
)


def _failed_equations(result):
    return {
        check.equation
        for check in result.constraints
        if check.satisfied is False
    }


def _failed_validity_equations(result):
    return {
        check.equation
        for check in result.approximation_validity
        if check.satisfied is False
    }


@pytest.mark.parametrize(
    ("variable_name", "invalid_value", "expected_failed_domains"),
    [
        (
            PULSE_PERIOD,
            0.0,
            {f"domain.{PULSE_PERIOD}.positive"},
        ),
        (
            PULSE_FLUENCE,
            0.0,
            {f"domain.{PULSE_FLUENCE}.positive"},
        ),
        (
            OBJECTIVE_PUPIL_RADIUS,
            0.0,
            {f"domain.{OBJECTIVE_PUPIL_RADIUS}.positive"},
        ),
        (
            OBJECTIVE_FOCAL_LENGTH,
            0.0,
            {f"domain.{OBJECTIVE_FOCAL_LENGTH}.positive"},
        ),
        (
            EDGE_DETUNING_RATIO,
            0.0,
            {f"domain.{EDGE_DETUNING_RATIO}.positive"},
        ),
        (
            FAR_FIELD_DIVERGENCE,
            0.0,
            {f"domain.{FAR_FIELD_DIVERGENCE}.positive"},
        ),
        (
            PULSE_DUTY_FACTOR,
            0.0,
            {f"domain.{PULSE_DUTY_FACTOR}.positive"},
        ),
        (
            PULSE_RISE_FRACTION,
            -0.1,
            {
                f"domain.{PULSE_RISE_FRACTION}.nonnegative",
                f"domain.{PULSE_RISE_FRACTION}.min",
            },
        ),
        (
            PULSE_FALL_FRACTION,
            -0.1,
            {
                f"domain.{PULSE_FALL_FRACTION}.nonnegative",
                f"domain.{PULSE_FALL_FRACTION}.min",
            },
        ),
        (
            PULSE_FLAT_FRACTION,
            -0.1,
            {
                f"domain.{PULSE_FLAT_FRACTION}.nonnegative",
                f"domain.{PULSE_FLAT_FRACTION}.min",
            },
        ),
    ],
)
def test_source_plasma_drive_root_domains_report_invalid_assignments(
    variable_name,
    invalid_value,
    expected_failed_domains,
):
    result = resolve(variable_name, assignments={variable_name: invalid_value})

    assert float(result.value) == pytest.approx(invalid_value)
    assert expected_failed_domains <= _failed_equations(result)


@pytest.mark.parametrize(
    ("variable_name", "invalid_value", "expected_failed_constraints"),
    [
        (
            EDGE_DETUNING_RATIO,
            1.0,
            {INEQ_EDGE_DETUNING_BELOW_EDGE},
        ),
        (
            PUPIL_BEAM_FILL_FACTOR,
            1.25,
            {
                INEQ_PUPIL_FILL_WITHIN_UNIT,
                f"domain.{PUPIL_BEAM_FILL_FACTOR}.max",
            },
        ),
        (
            FAR_FIELD_DIVERGENCE,
            2.0,
            {INEQ_FAR_FIELD_FORWARD},
        ),
        (
            PULSE_DUTY_FACTOR,
            1.25,
            {
                INEQ_DUTY_FACTOR_WITHIN_UNIT,
                f"domain.{PULSE_DUTY_FACTOR}.max",
            },
        ),
        (
            PULSE_RISE_FRACTION,
            0.6,
            {f"domain.{PULSE_RISE_FRACTION}.max"},
        ),
    ],
)
def test_source_plasma_drive_named_bounds_report_invalid_root_assignments(
    variable_name,
    invalid_value,
    expected_failed_constraints,
):
    result = resolve(variable_name, assignments={variable_name: invalid_value})

    assert float(result.value) == pytest.approx(invalid_value)
    assert expected_failed_constraints <= _failed_equations(result)


def test_source_plasma_drive_far_field_divergence_rejects_acceptance_overfill():
    result = resolve(
        FAR_FIELD_DIVERGENCE,
        assignments={
            FAR_FIELD_DIVERGENCE: 0.5,
            ACCEPTANCE_HALF_ANGLE: 0.25,
        },
    )

    assert float(result.value) == pytest.approx(0.5)
    assert INEQ_FAR_FIELD_WITHIN_ACCEPTANCE in _failed_equations(result)


def test_source_plasma_drive_acceptance_geometry_reports_invalid_objective_root():
    result = resolve(
        ACCEPTANCE_HALF_ANGLE,
        assignments={
            OBJECTIVE_PUPIL_RADIUS: 1.0,
            OBJECTIVE_FOCAL_LENGTH: -1.0,
        },
    )

    assert EQ_ACCEPTANCE_FROM_PUPIL in _failed_validity_equations(result)
    assert f"domain.{OBJECTIVE_FOCAL_LENGTH}.positive" in _failed_equations(result)
    assert f"domain.{ACCEPTANCE_HALF_ANGLE}.positive" in _failed_equations(result)


def test_source_plasma_drive_duty_cycle_overfill_propagates_to_pulse_duration():
    result = resolve(
        PULSE_DURATION,
        assignments={
            PULSE_DUTY_FACTOR: 1.25,
            PULSE_PERIOD: 1.0,
        },
    )

    assert float(result.value) == pytest.approx(1.25)
    assert {
        INEQ_DUTY_FACTOR_WITHIN_UNIT,
        INEQ_PULSE_DURATION_WITHIN_PERIOD,
        f"domain.{PULSE_DUTY_FACTOR}.max",
    } <= _failed_equations(result)
    assert {EQ_DURATION_FROM_DUTY} <= _failed_validity_equations(result)


def test_source_plasma_drive_invalid_period_propagates_to_repetition_rate():
    result = resolve(
        PULSE_REPETITION_RATE,
        assignments={PULSE_PERIOD: -1.0},
    )

    assert float(result.value) == pytest.approx(-1.0)
    assert f"domain.{PULSE_PERIOD}.positive" in _failed_equations(result)
    assert f"domain.{PULSE_REPETITION_RATE}.positive" in _failed_equations(result)
    assert {EQ_REPETITION_RATE_FROM_PERIOD} <= _failed_validity_equations(result)


def test_source_plasma_drive_invalid_fluence_propagates_to_peak_intensity():
    result = resolve(
        PEAK_INTENSITY,
        assignments={
            PULSE_FLUENCE: -1.0,
            PULSE_DURATION: 1.0,
            PULSE_SHAPE_FACTOR: 1.0,
        },
    )

    assert float(result.value) == pytest.approx(-1.0)
    assert f"domain.{PULSE_FLUENCE}.positive" in _failed_equations(result)
    assert f"domain.{PEAK_INTENSITY}.positive" in _failed_equations(result)
    assert {EQ_PEAK_INTENSITY_FROM_FLUENCE} <= _failed_validity_equations(result)


def test_source_plasma_drive_symmetric_ramp_overfill_propagates_to_shape_roots():
    result = resolve(
        PULSE_SHAPE_FACTOR,
        assignments={
            PULSE_RISE_FRACTION: 0.6,
        },
    )

    assert float(result.value) == pytest.approx(0.4)
    assert {
        f"domain.{PULSE_RISE_FRACTION}.max",
        f"domain.{PULSE_FLAT_FRACTION}.nonnegative",
        INEQ_RAMP_FRACTIONS_WITHIN_PULSE,
    } <= _failed_equations(result)
    assert {
        EQ_FALL_FROM_SYMMETRIC_RAMP,
        EQ_FLAT_FROM_RAMPS,
    } <= _failed_validity_equations(result)


def test_source_plasma_drive_boundary_roots_remain_assignment_only_inputs():
    for variable_name in [
        PULSE_PERIOD,
        PULSE_DUTY_FACTOR,
        PULSE_FLUENCE,
        PULSE_RISE_FRACTION,
        EDGE_DETUNING_RATIO,
        OBJECTIVE_PUPIL_RADIUS,
        OBJECTIVE_FOCAL_LENGTH,
        PUPIL_BEAM_FILL_FACTOR,
        FAR_FIELD_DIVERGENCE,
    ]:
        variable = Registry.variables[variable_name]
        assert variable.is_root_input
        assert variable.defining_equations == variable.constraints()
        assert not hasattr(variable, "value")
