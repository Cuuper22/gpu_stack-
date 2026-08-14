"""
The drive laser's operating inputs — pupil fill factor, edge detuning
ratio, objective pupil radius and focal length — feed the acceptance
geometry: the half angle of the cone of light the focusing objective can
deliver, and from it the numerical aperture. This module verifies the
feasibility net around those inputs. Every operating constraint must be a
named Inequality on a root input with the right operator, right-hand side,
references, and unit check. The acceptance half angle must stay strictly
below pi/2 (a wider cone would point backward), and the far-field
divergence constraint must reference the acceptance angle as a
constraint-only dependency. Bad roots must be visible everywhere they
matter: a zero or negative fill factor trips the domain checks, a negative
focal length flags the acceptance-geometry equation's validity and every
derived positive-domain check down the chain to numerical aperture, and a
zero detuning ratio invalidates the derived beam wavelength.
"""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.core import Inequality, RelationRole
from tests.test_lithography_source_plasma_feasibility import (
    SOURCE_PLASMA_OPERATING_CONSTRAINTS,
    _failed_constraint,
    _failed_validity,
)


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
