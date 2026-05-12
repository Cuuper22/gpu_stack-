"""
tests/test_lithography_k1_closure.py
====================================

Lithography feature-family k1 factors can share the gate k1 baseline when a
process deck has not provided separate contact or metal values.
"""

import pytest

from gpu_stack import Registry, resolve
from gpu_stack.core import RelationRole


K1_CLOSURES = {
    "physical.lithography.contact_k1": "physical.eq.contact_k1_from_gate_baseline",
    "physical.lithography.metal_width_k1": "physical.eq.metal_width_k1_from_gate_baseline",
    "physical.lithography.metal_spacing_k1": "physical.eq.metal_spacing_k1_from_gate_baseline",
}

GATE_K1_PROCESS_FACTOR_ASSIGNMENTS = {
    "physical.lithography.gate_k1_aerial_image_contrast_factor": 0.5,
    "physical.lithography.gate_k1_resist_process_factor": 0.7,
    "physical.lithography.gate_k1_mask_error_factor": 1.2,
    "physical.lithography.gate_k1_resolution_enhancement_factor": 1.4,
}

STRICTLY_POSITIVE_K1_VARIABLES = [
    "physical.lithography.gate_k1",
    "physical.lithography.contact_k1",
    "physical.lithography.metal_width_k1",
    "physical.lithography.metal_spacing_k1",
    "physical.lithography.gate_k1_aerial_image_contrast_factor",
    "physical.lithography.gate_k1_resist_process_factor",
    "physical.lithography.gate_k1_mask_error_factor",
    "physical.lithography.gate_k1_resolution_enhancement_factor",
]

FEATURE_RESOLUTION_CASES = [
    (
        "physical.lithography.contact_resolution",
        "physical.eq.contact_k1_from_gate_baseline",
        "physical.eq.contact_lithography_resolution",
    ),
    (
        "physical.lithography.metal_width_resolution",
        "physical.eq.metal_width_k1_from_gate_baseline",
        "physical.eq.metal_width_lithography_resolution",
    ),
    (
        "physical.lithography.metal_spacing_resolution",
        "physical.eq.metal_spacing_k1_from_gate_baseline",
        "physical.eq.metal_spacing_lithography_resolution",
    ),
]

NEGATIVE_K1_RESOLUTION_CASES = [
    (
        "physical.lithography.gate_resolution",
        "physical.lithography.gate_k1",
        "physical.eq.gate_lithography_resolution",
    ),
    (
        "physical.lithography.contact_resolution",
        "physical.lithography.contact_k1",
        "physical.eq.contact_lithography_resolution",
    ),
    (
        "physical.lithography.metal_width_resolution",
        "physical.lithography.metal_width_k1",
        "physical.eq.metal_width_lithography_resolution",
    ),
    (
        "physical.lithography.metal_spacing_resolution",
        "physical.lithography.metal_spacing_k1",
        "physical.eq.metal_spacing_lithography_resolution",
    ),
]


def test_k1_variables_have_strictly_positive_domains():
    for variable_name in STRICTLY_POSITIVE_K1_VARIABLES:
        variable = Registry.variables[variable_name]
        assert variable.assumptions.get("positive") is True


def test_gate_k1_has_process_factor_model():
    variable = Registry.variables["physical.lithography.gate_k1"]
    equation = Registry.equations["physical.eq.lithography_gate_k1_from_process_factors"]

    assert not variable.is_root_input
    assert variable.approximations() == [equation]
    assert equation.role == RelationRole.APPROXIMATION
    assert getattr(equation, "_check_units_flag", False)
    assert equation.references
    assert {v.name for v in variable.direct_dependencies()} == {
        "physical.lithography.gate_k1_aerial_image_contrast_factor",
        "physical.lithography.gate_k1_resist_process_factor",
        "physical.lithography.gate_k1_mask_error_factor",
        "physical.lithography.gate_k1_resolution_enhancement_factor",
    }
    assert {symbol.name for symbol in equation.validity.free_symbols} == {
        "chi_img_gate_litho",
        "chi_resist_gate_litho",
        "chi_mask_gate_litho",
        "eta_RET_gate_litho",
    }


def test_gate_k1_resolves_from_process_factors():
    result = resolve(
        "physical.lithography.gate_k1",
        assignments=GATE_K1_PROCESS_FACTOR_ASSIGNMENTS,
    )

    assert float(result.value) == pytest.approx(1.2)
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_gate_k1_from_process_factors",
    ]


def test_gate_resolution_resolves_gate_k1_from_process_factors():
    result = resolve(
        "physical.lithography.gate_resolution",
        assignments={
            **GATE_K1_PROCESS_FACTOR_ASSIGNMENTS,
            "physical.lithography.wavelength": 10.0,
            "physical.lithography.numerical_aperture": 2.0,
        },
    )

    assert float(result.value) == pytest.approx(6.0)
    assert {
        "physical.eq.lithography_gate_k1_from_process_factors",
        "physical.eq.gate_lithography_resolution",
    } <= {step.equation for step in result.trace}


def test_lithography_feature_k1_factors_share_gate_baseline():
    for variable_name, equation_name in K1_CLOSURES.items():
        variable = Registry.variables[variable_name]
        equation = Registry.equations[equation_name]

        assert not variable.is_root_input
        assert variable.approximations() == [equation]
        assert equation.role == RelationRole.APPROXIMATION
        assert getattr(equation, "_check_units_flag", False)
        assert equation.references
        assert {v.name for v in variable.direct_dependencies()} == {
            "physical.lithography.gate_k1",
        }
        assert str(equation.validity) == "k1_gate_litho > 0"


def test_lithography_feature_k1_factors_resolve_from_gate_k1():
    for variable_name, equation_name in K1_CLOSURES.items():
        result = resolve(
            variable_name,
            assignments={"physical.lithography.gate_k1": 0.72},
        )

        assert float(result.value) == pytest.approx(0.72)
        assert [step.equation for step in result.trace] == [equation_name]


def test_lithography_resolution_uses_gate_k1_when_feature_k1_is_unassigned():
    for target, k1_equation, resolution_equation in FEATURE_RESOLUTION_CASES:
        result = resolve(
            target,
            assignments={
                "physical.lithography.gate_k1": 0.72,
                "physical.lithography.wavelength": 10.0,
                "physical.lithography.numerical_aperture": 2.0,
            },
        )

        assert float(result.value) == pytest.approx(3.6)
        assert [step.equation for step in result.trace] == [
            k1_equation,
            resolution_equation,
        ]


@pytest.mark.parametrize(
    ("target", "k1_equation", "resolution_equation"),
    FEATURE_RESOLUTION_CASES,
)
def test_lithography_resolution_can_resolve_gate_k1_from_process_factors(
    target,
    k1_equation,
    resolution_equation,
):
    result = resolve(
        target,
        assignments={
            **GATE_K1_PROCESS_FACTOR_ASSIGNMENTS,
            "physical.lithography.wavelength": 10.0,
            "physical.lithography.numerical_aperture": 2.0,
        },
    )

    assert float(result.value) == pytest.approx(6.0)
    assert [step.equation for step in result.trace] == [
        "physical.eq.lithography_gate_k1_from_process_factors",
        k1_equation,
        resolution_equation,
    ]


@pytest.mark.parametrize(
    ("target", "k1_variable", "resolution_equation"),
    NEGATIVE_K1_RESOLUTION_CASES,
)
def test_negative_explicit_k1_is_reported_as_invalid(
    target,
    k1_variable,
    resolution_equation,
):
    result = resolve(
        target,
        assignments={
            k1_variable: -0.5,
            "physical.lithography.wavelength": 10.0,
            "physical.lithography.numerical_aperture": 2.0,
        },
    )

    domain_check = next(
        check
        for check in result.constraints
        if check.equation == f"domain.{k1_variable}.positive"
    )
    validity_check = next(
        check
        for check in result.approximation_validity
        if check.equation == resolution_equation
    )

    assert float(result.value) == pytest.approx(-2.5)
    assert domain_check.satisfied is False
    assert validity_check.satisfied is False


def test_explicit_feature_k1_assignment_overrides_gate_baseline():
    cases = [
        ("physical.lithography.contact_k1", "physical.lithography.contact_resolution"),
        ("physical.lithography.metal_width_k1", "physical.lithography.metal_width_resolution"),
        ("physical.lithography.metal_spacing_k1", "physical.lithography.metal_spacing_resolution"),
    ]

    for feature_k1, target in cases:
        result = resolve(
            target,
            assignments={
                "physical.lithography.gate_k1": 0.72,
                feature_k1: 0.50,
                "physical.lithography.wavelength": 10.0,
                "physical.lithography.numerical_aperture": 2.0,
            },
        )

        assert float(result.value) == pytest.approx(2.5)
        assert all("k1_from_gate_baseline" not in step.equation for step in result.trace)
