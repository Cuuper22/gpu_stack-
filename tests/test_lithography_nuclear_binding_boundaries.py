"""
tests/test_lithography_nuclear_binding_boundaries.py
====================================================

Focused boundary coverage for shared SEMF calibration coefficients.
"""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.core import VariableKind
from gpu_stack.core.units import JOULE


SEMF_CALIBRATION_BOUNDARIES = [
    (
        "physical.lithography.nuclear_binding_volume_coefficient",
        "nonnegative",
        0.0,
        -1.0,
    ),
    (
        "physical.lithography.nuclear_binding_surface_coefficient",
        "nonnegative",
        0.0,
        -1.0,
    ),
    (
        "physical.lithography.nuclear_binding_coulomb_coefficient",
        "positive",
        1.0,
        0.0,
    ),
    (
        "physical.lithography.nuclear_binding_asymmetry_coefficient",
        "nonnegative",
        0.0,
        -1.0,
    ),
    (
        "physical.lithography.nuclear_pairing_gap_reference_energy",
        "nonnegative",
        0.0,
        -1.0,
    ),
]


def _domain_constraint_name(variable_name, domain):
    return f"domain.{variable_name}.{domain}"


def _constraint(result, equation_name):
    return next(c for c in result.constraints if c.equation == equation_name)


@pytest.mark.parametrize(
    ("variable_name", "domain", "_valid_value", "_invalid_value"),
    SEMF_CALIBRATION_BOUNDARIES,
)
def test_shared_semf_coefficients_are_primitive_calibration_boundaries(
    variable_name,
    domain,
    _valid_value,
    _invalid_value,
):
    variable = Registry.variables[variable_name]

    assert variable.is_root_input
    assert variable.kind is VariableKind.ROOT_INPUT
    assert variable.defining_equations == []
    assert variable.sp_units == JOULE
    assert variable.value_range is None
    assert variable.references
    assert variable.assumptions[domain] is True


@pytest.mark.parametrize(
    ("variable_name", "domain", "valid_value", "_invalid_value"),
    SEMF_CALIBRATION_BOUNDARIES,
)
def test_shared_semf_coefficients_accept_physical_boundary_values(
    variable_name,
    domain,
    valid_value,
    _invalid_value,
):
    result = resolve(variable_name, assignments={variable_name: valid_value})

    check = _constraint(result, _domain_constraint_name(variable_name, domain))
    assert check.satisfied is True
    assert check.missing == set()
    assert isinstance(check.relation, sp.Rel)
    assert not result.violated_constraints


@pytest.mark.parametrize(
    ("variable_name", "domain", "_valid_value", "invalid_value"),
    SEMF_CALIBRATION_BOUNDARIES,
)
def test_shared_semf_coefficients_reject_invalid_calibration_boundaries(
    variable_name,
    domain,
    _valid_value,
    invalid_value,
):
    result = resolve(variable_name, assignments={variable_name: invalid_value})
    equation_name = _domain_constraint_name(variable_name, domain)

    check = _constraint(result, equation_name)
    assert check.satisfied is False
    assert check.missing == set()
    assert isinstance(check.relation, sp.Rel)
    assert any(v.equation == equation_name for v in result.violated_constraints)


def test_coulomb_coefficient_strict_positive_boundary_rejects_negative_energy():
    variable_name = "physical.lithography.nuclear_binding_coulomb_coefficient"
    equation_name = _domain_constraint_name(variable_name, "positive")

    result = resolve(variable_name, assignments={variable_name: -1.0})

    check = _constraint(result, equation_name)
    assert check.satisfied is False
    assert check.missing == set()
    assert isinstance(check.relation, sp.Rel)
    assert any(v.equation == equation_name for v in result.violated_constraints)
