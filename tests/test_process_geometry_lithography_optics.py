"""Tests for the lithography optics inputs behind process geometry.

Feature size on a chip comes down to optics. Wavelength, numerical aperture
(how wide a cone of light the lens gathers) and the refractive index of the
medium under the lens are plain inputs here. These tests pin that they are
root inputs with positive domains, that numerical aperture is bounded by the
medium index, and that the Rayleigh resolution equation keeps its validity
condition symbolic so it is judged per scenario.
"""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.core import Inequality, RelationRole


OPTICS_ROOTS = (
    "physical.lithography.wavelength",
    "physical.lithography.numerical_aperture",
    "physical.lithography.medium_refractive_index",
)


@pytest.mark.parametrize("name", OPTICS_ROOTS)
def test_lithography_optics_are_positive_root_inputs(name):
    variable = Registry.variables[name]
    assert variable.is_root_input
    assert variable.symbol.is_positive is True


@pytest.mark.parametrize("name", OPTICS_ROOTS)
def test_lithography_optics_reject_nonpositive_values(name):
    for bad_value in (0.0, -1.0):
        result = resolve(name, assignments={name: bad_value})
        check = next(
            c for c in result.constraints
            if c.equation == f"domain.{name}.positive"
        )
        assert check.satisfied is False
        assert check.missing == set()


def test_numerical_aperture_is_bounded_by_medium_index():
    refractive_index = Registry.variables["physical.lithography.medium_refractive_index"]
    numerical_aperture = Registry.variables["physical.lithography.numerical_aperture"]
    bound = Registry.equations[
        "physical.ineq.lithography_numerical_aperture_within_medium_index"
    ]
    assert isinstance(bound, Inequality)
    assert bound.role is RelationRole.CONSTRAINT
    assert bound.op == "<="
    assert bound.lhs == numerical_aperture.symbol
    assert bound.rhs == refractive_index.symbol
    assert bound.references
    assert isinstance(bound.as_sympy(), sp.Rel)
    assert [eq.name for eq in numerical_aperture.constraints()] == [bound.name]

    for na, index, satisfied in ((1.35, 1.44, True), (1.5, 1.0, False)):
        result = resolve(
            "physical.lithography.numerical_aperture",
            assignments={
                "physical.lithography.numerical_aperture": na,
                "physical.lithography.medium_refractive_index": index,
            },
        )
        check = next(c for c in result.constraints if c.equation == bound.name)
        assert check.satisfied is satisfied


def test_lithography_validity_stays_symbolic():
    eq = Registry.equations["physical.eq.gate_lithography_resolution"]
    assert eq.validity is not True
    assert "lambda_litho" in str(eq.validity)
    assert "NA_litho" in str(eq.validity)
