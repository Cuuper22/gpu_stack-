"""
tests/test_lithography_source_plasma_feasibility.py
===================================================

Focused feasibility coverage for lithography source-plasma operating inputs.
"""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.constants import BOLTZMANN, SPEED_OF_LIGHT
from gpu_stack.core import Inequality, RelationRole, VariableKind


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


def test_source_plasma_gas_thermal_constraints_are_named_boundaries():
    for equation_name, variable_name, op, rhs, _bad_value in (
        SOURCE_PLASMA_GAS_THERMAL_CONSTRAINTS
    ):
        eq = Registry.equations[equation_name]
        variable = Registry.variables[variable_name]
        assert isinstance(eq, Inequality)
        assert eq.role is RelationRole.CONSTRAINT
        assert eq in variable.constraints()
        assert eq.op == op
        assert eq.rhs == rhs
        assert eq.references
        assert isinstance(eq.as_sympy(), sp.Rel)


def test_source_plasma_gas_thermal_variables_keep_boundary_semantics():
    root_inputs = {
        "physical.lithography.source_plasma_species_partial_pressure",
        "physical.lithography.source_plasma_species_gas_temperature",
    }
    derived_by_real_equations = {
        "physical.lithography.source_plasma_species_number_density": (
            "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas"
        ),
        "physical.lithography.source_plasma_species_thermal_speed": (
            "physical.eq.lithography_source_plasma_species_thermal_speed_from_gas_temperature"
        ),
    }

    for variable_name in root_inputs:
        variable = Registry.variables[variable_name]
        assert variable.kind is VariableKind.ROOT_INPUT
        assert variable.is_root_input
        assert variable.direct_dependencies() == set()
        assert variable.constraints()

    for variable_name, equation_name in derived_by_real_equations.items():
        variable = Registry.variables[variable_name]
        assert variable.kind is VariableKind.DERIVED
        assert not variable.is_root_input
        assert Registry.equations[equation_name] in variable.defining_equations
        assert variable.constraints()


def test_source_plasma_gas_thermal_constraints_report_invalid_assignments():
    for equation_name, variable_name, _op, _rhs, bad_value in (
        SOURCE_PLASMA_GAS_THERMAL_CONSTRAINTS
    ):
        result = resolve(variable_name, assignments={variable_name: bad_value})
        assert float(result.value) == pytest.approx(bad_value)
        _failed_constraint(result, equation_name)


def test_source_plasma_ideal_gas_validity_reports_invalid_pressure_boundary():
    result = resolve(
        "physical.lithography.source_plasma_species_number_density",
        assignments={
            "physical.lithography.source_plasma_species_partial_pressure": -1.0,
            "physical.lithography.source_plasma_species_gas_temperature": 300.0,
        },
    )

    assert float(result.value) < 0.0
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas",
    ]
    _failed_validity(
        result,
        "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas",
    )
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_species_partial_pressure_positive",
    )
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_species_number_density_positive",
    )


def test_source_plasma_ideal_gas_validity_reports_invalid_temperature_boundary():
    result = resolve(
        "physical.lithography.source_plasma_species_number_density",
        assignments={
            "physical.lithography.source_plasma_species_partial_pressure": 1.0,
            "physical.lithography.source_plasma_species_gas_temperature": -300.0,
        },
    )

    assert float(result.value) < 0.0
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas",
    ]
    _failed_validity(
        result,
        "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas",
    )
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_species_gas_temperature_positive",
    )
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_species_number_density_positive",
    )
    _failed_constraint(
        result,
        "domain.physical.lithography.source_plasma_species_gas_temperature.positive",
    )
    _failed_constraint(
        result,
        "domain.physical.lithography.source_plasma_species_number_density.positive",
    )


def test_source_plasma_ideal_gas_valid_assignments_resolve_cleanly():
    partial_pressure = 2.0
    gas_temperature = 400.0

    result = resolve(
        "physical.lithography.source_plasma_species_number_density",
        assignments={
            "physical.lithography.source_plasma_species_partial_pressure": (
                partial_pressure
            ),
            "physical.lithography.source_plasma_species_gas_temperature": (
                gas_temperature
            ),
        },
    )

    assert float(result.value) == pytest.approx(
        partial_pressure / (BOLTZMANN.value * gas_temperature)
    )
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas",
    ]
    assert all(
        check.satisfied is True for check in result.approximation_validity
    )
    for equation_name in [
        "physical.ineq.lithography_source_plasma_species_partial_pressure_positive",
        "physical.ineq.lithography_source_plasma_species_gas_temperature_positive",
        "physical.ineq.lithography_source_plasma_species_number_density_positive",
        "domain.physical.lithography.source_plasma_species_partial_pressure.positive",
        "domain.physical.lithography.source_plasma_species_gas_temperature.positive",
        "domain.physical.lithography.source_plasma_species_number_density.positive",
    ]:
        _satisfied_constraint(result, equation_name)


def test_source_plasma_operating_input_constraints_are_named_feasibility_relations():
    for (
        equation_name,
        variable_name,
        op,
        rhs,
        _bad_value,
        _extra_assignments,
    ) in SOURCE_PLASMA_OPERATING_CONSTRAINTS:
        eq = Registry.equations[equation_name]
        variable = Registry.variables[variable_name]
        assert isinstance(eq, Inequality)
        assert eq.role is RelationRole.CONSTRAINT
        assert eq in variable.constraints()
        assert variable.is_root_input
        assert eq.op == op
        assert eq.rhs == rhs
        assert eq.references
        assert getattr(eq, "_check_units_flag", False)
        assert isinstance(eq.as_sympy(), sp.Rel)
        assert not eq.is_trivially_true()


def test_source_plasma_far_field_divergence_constraint_depends_on_acceptance_angle():
    divergence = Registry.variables[
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle"
    ]
    assert [eq.name for eq in divergence.constraints()] == [
        "physical.ineq.lithography_source_plasma_drive_far_field_divergence_half_angle_within_forward_half_space",
        "physical.ineq.lithography_source_plasma_drive_far_field_divergence_within_acceptance",
    ]
    assert divergence.direct_dependencies() == set()
    assert {
        v.name for v in divergence.direct_dependencies(include_constraints=True)
    } == {
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    }


def test_source_plasma_acceptance_half_angle_has_forward_half_space_constraint():
    acceptance = Registry.variables[
        "physical.lithography.source_plasma_drive_acceptance_half_angle"
    ]
    constraint = Registry.equations[
        "physical.ineq.lithography_source_plasma_drive_acceptance_half_angle_within_forward_half_space"
    ]

    assert isinstance(constraint, Inequality)
    assert constraint.role is RelationRole.CONSTRAINT
    assert constraint in acceptance.constraints()
    assert constraint.op == "<"
    assert constraint.rhs == sp.pi / 2
    assert constraint.references
    assert getattr(constraint, "_check_units_flag", False)
    assert isinstance(constraint.as_sympy(), sp.Rel)
    assert not constraint.is_trivially_true()


def test_source_plasma_operating_input_constraints_report_invalid_assignments():
    for (
        equation_name,
        variable_name,
        _op,
        _rhs,
        bad_value,
        extra_assignments,
    ) in SOURCE_PLASMA_OPERATING_CONSTRAINTS:
        result = resolve(
            variable_name,
            assignments={
                variable_name: bad_value,
                **extra_assignments,
            },
        )
        assert float(result.value) == pytest.approx(bad_value)
        _failed_constraint(result, equation_name)


def test_source_plasma_pupil_fill_factor_lower_bound_uses_domain_checks():
    variable_name = (
        "physical.lithography.source_plasma_drive_pupil_beam_fill_factor"
    )

    zero_result = resolve(variable_name, assignments={variable_name: 0.0})
    assert float(zero_result.value) == pytest.approx(0.0)
    _failed_constraint(
        zero_result,
        "domain.physical.lithography.source_plasma_drive_pupil_beam_fill_factor.positive",
    )

    negative_result = resolve(variable_name, assignments={variable_name: -0.1})
    assert float(negative_result.value) == pytest.approx(-0.1)
    _failed_constraint(
        negative_result,
        "domain.physical.lithography.source_plasma_drive_pupil_beam_fill_factor.positive",
    )
    _failed_constraint(
        negative_result,
        "domain.physical.lithography.source_plasma_drive_pupil_beam_fill_factor.min",
    )


def test_source_plasma_detuning_domain_reports_invalid_root_and_wavelength_chain():
    variable_name = (
        "physical.lithography.source_plasma_drive_edge_detuning_ratio"
    )
    negative_result = resolve(variable_name, assignments={variable_name: -1.0})
    assert float(negative_result.value) == pytest.approx(-1.0)
    _failed_constraint(
        negative_result,
        "domain.physical.lithography.source_plasma_drive_edge_detuning_ratio.positive",
    )

    wavelength_result = resolve(
        "physical.lithography.source_plasma_drive_beam_wavelength",
        assignments={
            "physical.lithography.source_ionization_energy": 1.0e-16,
            variable_name: 0.0,
        },
    )

    assert float(wavelength_result.value) == pytest.approx(0.0)
    assert [step.equation for step in wavelength_result.trace] == [
        "physical.eq.lithography_source_plasma_drive_beam_wavelength_from_ionization_edge",
    ]
    _failed_validity(
        wavelength_result,
        "physical.eq.lithography_source_plasma_drive_beam_wavelength_from_ionization_edge",
    )
    _failed_constraint(
        wavelength_result,
        "domain.physical.lithography.source_plasma_drive_edge_detuning_ratio.positive",
    )
    _failed_constraint(
        wavelength_result,
        "domain.physical.lithography.source_plasma_drive_beam_wavelength.positive",
    )


@pytest.mark.parametrize(
    (
        "assignments",
        "expected_value",
        "failed_domain",
    ),
    [
        (
            {
                "physical.lithography.source_plasma_drive_objective_pupil_radius": 0.0,
                "physical.lithography.source_plasma_drive_objective_focal_length": 1.0,
            },
            0.0,
            "domain.physical.lithography.source_plasma_drive_objective_pupil_radius.positive",
        ),
        (
            {
                "physical.lithography.source_plasma_drive_objective_pupil_radius": 1.0,
                "physical.lithography.source_plasma_drive_objective_focal_length": -1.0,
            },
            -float(sp.pi) / 4.0,
            "domain.physical.lithography.source_plasma_drive_objective_focal_length.positive",
        ),
    ],
)
def test_source_plasma_acceptance_geometry_reports_invalid_pupil_or_focal_root(
    assignments,
    expected_value,
    failed_domain,
):
    result = resolve(
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
        assignments=assignments,
    )

    assert float(result.value) == pytest.approx(expected_value)
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_source_plasma_drive_acceptance_half_angle_from_pupil_geometry",
    ]
    _failed_validity(
        result,
        "physical.eq.lithography_source_plasma_drive_acceptance_half_angle_from_pupil_geometry",
    )
    _failed_constraint(result, failed_domain)
    _failed_constraint(
        result,
        "domain.physical.lithography.source_plasma_drive_acceptance_half_angle.positive",
    )


def test_source_plasma_numerical_aperture_reports_invalid_focal_geometry_chain():
    result = resolve(
        "physical.lithography.source_plasma_drive_numerical_aperture",
        assignments={
            "physical.lithography.source_plasma_drive_objective_pupil_radius": 1.0,
            "physical.lithography.source_plasma_drive_objective_focal_length": -1.0,
        },
    )

    assert float(result.value) == pytest.approx(-(2.0**-0.5))
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_source_plasma_drive_acceptance_half_angle_from_pupil_geometry",
        "physical.eq.lithography_source_plasma_drive_numerical_aperture_from_acceptance_angle",
    ]
    _failed_validity(
        result,
        "physical.eq.lithography_source_plasma_drive_acceptance_half_angle_from_pupil_geometry",
    )
    _failed_constraint(
        result,
        "domain.physical.lithography.source_plasma_drive_objective_focal_length.positive",
    )
    _failed_constraint(
        result,
        "domain.physical.lithography.source_plasma_drive_acceptance_half_angle.positive",
    )
    _failed_constraint(
        result,
        "domain.physical.lithography.source_plasma_drive_numerical_aperture.positive",
    )
    _failed_constraint(
        result,
        "domain.physical.lithography.source_plasma_drive_numerical_aperture.min",
    )


def test_source_plasma_acceptance_half_angle_rejects_backward_cone():
    variable_name = (
        "physical.lithography.source_plasma_drive_acceptance_half_angle"
    )

    result = resolve(variable_name, assignments={variable_name: 2.0})

    assert float(result.value) == pytest.approx(2.0)
    _failed_constraint(
        result,
        "physical.ineq.lithography_source_plasma_drive_acceptance_half_angle_within_forward_half_space",
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
