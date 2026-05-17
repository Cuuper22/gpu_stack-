"""Lithography optics coverage for process geometry."""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.core import Inequality, RelationRole


def test_lithography_wavelength_and_numerical_aperture_have_physical_models():
    wavelength = Registry.variables["physical.lithography.wavelength"]
    photon_energy = Registry.variables["physical.lithography.photon_energy"]
    frequency = Registry.variables["physical.lithography.photon_frequency"]
    angular_frequency = Registry.variables["physical.lithography.source_angular_frequency"]
    numerical_aperture = Registry.variables["physical.lithography.numerical_aperture"]
    assert not wavelength.is_root_input
    assert not photon_energy.is_root_input
    assert not frequency.is_root_input
    assert not angular_frequency.is_root_input
    assert not numerical_aperture.is_root_input
    assert wavelength.symbol.is_positive is True
    assert photon_energy.symbol.is_positive is True
    assert frequency.symbol.is_positive is True
    assert angular_frequency.symbol.is_positive is True
    assert {v.name for v in wavelength.direct_dependencies()} == {
        "physics.speed_of_light",
        "physical.lithography.photon_frequency",
    }
    assert {v.name for v in photon_energy.direct_dependencies()} == {
        "physical.lithography.source_transition_energy",
    }
    assert {v.name for v in frequency.direct_dependencies()} == {
        "physical.lithography.photon_energy",
        "physics.planck",
    }
    assert {v.name for v in angular_frequency.direct_dependencies()} == {
        "physical.lithography.photon_frequency",
    }
    assert {v.name for v in numerical_aperture.direct_dependencies()} == {
        "physical.lithography.medium_refractive_index",
        "physical.lithography.acceptance_half_angle",
    }

    c = Registry.variables["physics.speed_of_light"].value
    h = Registry.variables["physics.planck"].value
    frequency_result = resolve(
        "physical.lithography.photon_frequency",
        assignments={
            "physical.lithography.photon_energy": h * c / 10.0,
        },
    )
    assert float(frequency_result.value) == pytest.approx(c / 10.0)

    angular_result = resolve(
        "physical.lithography.source_angular_frequency",
        assignments={
            "physical.lithography.photon_energy": h * c / 10.0,
        },
    )
    assert float(angular_result.value) == pytest.approx(2.0 * float(sp.pi) * c / 10.0)

    wavelength_result = resolve(
        "physical.lithography.wavelength",
        assignments={
            "physical.lithography.photon_energy": h * c / 10.0,
        },
    )
    assert float(wavelength_result.value) == pytest.approx(10.0)


def test_lithography_rejects_nonpositive_photon_domains():
    for bad_energy in (0.0, -1.0):
        result = resolve(
            "physical.lithography.wavelength",
            assignments={
                "physical.lithography.photon_energy": bad_energy,
            },
        )
        check = next(
            c for c in result.constraints
            if c.equation == "domain.physical.lithography.photon_energy.positive"
        )
        assert check.satisfied is False
        assert check.missing == set()

    for bad_frequency in (0.0, -1.0):
        result = resolve(
            "physical.lithography.wavelength",
            assignments={
                "physical.lithography.photon_frequency": bad_frequency,
            },
        )
        checks = {c.equation: c for c in result.constraints}
        assert (
            checks[
                "domain.physical.lithography.photon_frequency.positive"
            ].satisfied
            is False
        )
        assert (
            checks[
                "domain.physical.lithography.wavelength.positive"
            ].satisfied
            is False
        )

    for bad_transition_energy in (0.0, -1.0):
        result = resolve(
            "physical.lithography.photon_energy",
            assignments={
                "physical.lithography.source_transition_energy": (
                    bad_transition_energy
                ),
            },
        )
        checks = {c.equation: c for c in result.constraints}
        assert (
            checks[
                "domain.physical.lithography.source_transition_energy.positive"
            ].satisfied
            is False
        )
        assert (
            checks[
                "domain.physical.lithography.photon_energy.positive"
            ].satisfied
            is False
        )


def test_lithography_medium_relative_permittivity_rejects_bad_lorentz_lorenz_branch():
    result = resolve(
        "physical.lithography.medium_relative_permittivity",
        assignments={
            "physical.lithography.medium_lorentz_lorenz_factor": -0.75,
        },
    )
    assert float(result.value) == pytest.approx(-1.0 / 3.5)
    check = next(
        c for c in result.approximation_validity
        if c.equation == "physical.eq.lithography_medium_relative_permittivity"
    )
    assert check.satisfied is False
    assert check.missing == set()


def test_lithography_refractive_index_and_acceptance_angle_have_lower_models():
    refractive_index = Registry.variables["physical.lithography.medium_refractive_index"]
    acceptance = Registry.variables["physical.lithography.acceptance_half_angle"]
    numerical_aperture = Registry.variables["physical.lithography.numerical_aperture"]
    assert not refractive_index.is_root_input
    assert not acceptance.is_root_input
    assert not numerical_aperture.is_root_input
    assert {v.name for v in refractive_index.direct_dependencies()} == {
        "physical.lithography.medium_relative_permittivity",
        "physical.lithography.medium_relative_permeability",
    }
    assert {v.name for v in acceptance.direct_dependencies()} == {
        "physical.lithography.objective_pupil_radius",
        "physical.lithography.objective_focal_length",
    }
    assert {v.name for v in numerical_aperture.direct_dependencies()} == {
        "physical.lithography.medium_refractive_index",
        "physical.lithography.acceptance_half_angle",
    }

    forward_cone = Registry.equations[
        "physical.ineq.lithography_acceptance_half_angle_within_forward_half_space"
    ]
    na_medium_bound = Registry.equations[
        "physical.ineq.lithography_numerical_aperture_within_medium_index"
    ]
    assert isinstance(forward_cone, Inequality)
    assert isinstance(na_medium_bound, Inequality)
    assert forward_cone.role is RelationRole.CONSTRAINT
    assert na_medium_bound.role is RelationRole.CONSTRAINT
    assert forward_cone.op == "<="
    assert na_medium_bound.op == "<="
    assert forward_cone.rhs == sp.pi / 2
    assert na_medium_bound.rhs == refractive_index.symbol
    assert forward_cone.references
    assert na_medium_bound.references
    assert getattr(forward_cone, "_check_units_flag", False)
    assert getattr(na_medium_bound, "_check_units_flag", False)
    assert isinstance(forward_cone.as_sympy(), sp.Rel)
    assert isinstance(na_medium_bound.as_sympy(), sp.Rel)
    assert forward_cone.as_sympy() is not sp.S.true
    assert na_medium_bound.as_sympy() is not sp.S.true
    assert [eq.name for eq in acceptance.constraints()] == [forward_cone.name]
    assert [eq.name for eq in numerical_aperture.constraints()] == [
        na_medium_bound.name
    ]

    refractive_result = resolve(
        "physical.lithography.medium_refractive_index",
        assignments={
            "physical.lithography.medium_relative_permittivity": 4.0,
            "physical.lithography.medium_relative_permeability": 1.0,
        },
    )
    assert float(refractive_result.value) == pytest.approx(2.0)

    aperture_result = resolve(
        "physical.lithography.numerical_aperture",
        assignments={
            "physical.lithography.medium_relative_permittivity": 4.0,
            "physical.lithography.medium_relative_permeability": 1.0,
            "physical.lithography.objective_pupil_radius": 1.0,
            "physical.lithography.objective_focal_length": 1.0,
        },
    )
    assert float(aperture_result.value) == pytest.approx(2.0 ** 0.5)


def test_lithography_validity_stays_symbolic():
    eq = Registry.equations["physical.eq.gate_lithography_resolution"]
    assert eq.validity is not True
    assert "lambda_litho" in str(eq.validity)
    assert "NA_litho" in str(eq.validity)
