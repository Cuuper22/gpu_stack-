"""Tests for how the resolver handles approximations and their validity.

An Approximation is an equation that is only trustworthy inside a stated
regime — its validity predicate. The resolver must still use the formula but
report the check honestly: satisfied when the regime holds, violated when it
does not, and unresolved (None) when the predicate's inputs are missing.
These tests also confirm that validity-only inputs never leak into the value
trace, so a regime check cannot change the computed number.
"""

import pytest

from gpu_stack import resolve
from gpu_stack.core import (
    Approximation,
    ApproximationValidityCheck,
    RelationRole,
)
from gpu_stack.core.variable import Variable
from tests.helpers.registry import registry_snapshot  # noqa: F401  (pytest fixture)


def test_resolver_value_trace_ignores_validity_only_dependencies():
    result = resolve(
        "physical.clock_frequency",
        assignments={
            "physical.clock.max_timing_frequency": 0.5,
            "physical.clock.derate": 0.8,
            "physical.gate.r_on": 1.0,
            "physical.gate.fanout": 1,
            "physical.gate.c_input": 1.0,
            "physical.interconnect.c_total": 1.0,
            "physical.interconnect.r_per_length": 0.0,
            "physical.interconnect.c_per_length": 1.0,
            "physical.wire_length": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(0.4)
    assert "physical.eq.elmore_delay" not in [
        step.equation for step in result.trace
    ]
    check = next(
        c for c in result.approximation_validity
        if c.equation == "physical.eq.clock_frequency_timing_model"
    )
    assert check.satisfied is True


def test_variant_approximation_reports_unresolved_validity(registry_snapshot):
    x = Variable(
        "test.approx.x",
        "x_approx_variant_test",
        "value",
        "Temporary approximation output.",
        scope="test",
    )
    y = Variable(
        "test.approx.y",
        "y_approx_variant_test",
        "value",
        "Temporary approximation input.",
        scope="test",
    )
    z = Variable(
        "test.approx.z",
        "z_approx_variant_test",
        "value",
        "Temporary approximation validity input.",
        scope="test",
    )
    Approximation(
        "test.eq.approx_variant",
        x.symbol,
        y.symbol + 1,
        z.symbol > 0,
        "Temporary approximate variant with independent validity predicate.",
        role=RelationRole.VARIANT,
        variant="alt",
    )

    result = resolve(
        "test.approx.x",
        assignments={"test.approx.y": 2},
        variants={"test.approx.x": "alt"},
    )

    assert result.value == 3
    assert result.missing == set()
    assert len(result.approximation_validity) == 1
    check = result.approximation_validity[0]
    assert check.equation == "test.eq.approx_variant"
    assert check.satisfied is None
    assert check.missing == {"test.approx.z"}


def test_resolve_reports_violated_approximation_validity():
    result = resolve(
        "physical.lithography.gate_resolution",
        assignments={
            "physical.lithography.gate_k1": 0.4,
            "physical.lithography.wavelength": -13.5e-9,
            "physical.lithography.numerical_aperture": 0.33,
        },
    )
    check = next(
        c for c in result.approximation_validity
        if c.equation == "physical.eq.gate_lithography_resolution"
    )
    assert isinstance(check, ApproximationValidityCheck)
    assert check.satisfied is False


def _recovered_domain_approximation():
    """A temporary approximation whose validity is recovered from RHS domains."""
    x = Variable(
        "test.recovered.x",
        "x_recovered_test",
        "value",
        "Temporary approximation output.",
        scope="test",
    )
    y = Variable(
        "test.recovered.y",
        "y_recovered_test",
        "value",
        "Temporary approximation input with a positive domain.",
        scope="test",
        positive=True,
    )
    Approximation(
        "test.eq.recovered_domain",
        x.symbol,
        2 * y.symbol,
        True,
        "Temporary approximation that recovers its validity from y being positive.",
    )
    return x, y


def test_recovered_approximation_validity_detects_violated_domain(registry_snapshot):
    x, y = _recovered_domain_approximation()
    result = resolve(x.name, assignments={y.name: -1.0})
    check = next(
        c for c in result.approximation_validity
        if c.equation == "test.eq.recovered_domain"
    )
    assert check.satisfied is False
    assert check.missing == set()


def test_recovered_approximation_validity_stays_symbolic_when_domain_missing(
    registry_snapshot,
):
    x, y = _recovered_domain_approximation()
    result = resolve(x.name)
    check = next(
        c for c in result.approximation_validity
        if c.equation == "test.eq.recovered_domain"
    )
    assert check.satisfied is None
    assert check.missing == {y.name}
