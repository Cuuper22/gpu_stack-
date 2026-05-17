"""
Approximation and approximation-validity resolver coverage.
"""

import pytest

from gpu_stack import resolve
from gpu_stack.core import (
    Approximation,
    ApproximationValidityCheck,
    RelationRole,
)
from gpu_stack.core.variable import Variable
from tests.helpers.registry import registry_snapshot


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
        "physical.lithography.medium_formula_unit_intercomponent_binding_energy",
        assignments={
            "physical.lithography.medium_component_a_effective_intercomponent_charge_number": 1,
            "physical.lithography.medium_component_b_effective_intercomponent_charge_number": 1,
            "physical.lithography.medium_formula_unit_intercomponent_pair_count": 1,
            "physical.lithography.medium_intercomponent_effective_separation": 1e-9,
            "physical.lithography.medium_intercomponent_relative_permittivity": 1,
        },
    )
    check = next(
        c for c in result.approximation_validity
        if c.equation
        == "physical.eq.lithography_medium_formula_unit_intercomponent_binding_energy"
    )
    assert isinstance(check, ApproximationValidityCheck)
    assert check.satisfied is False


def test_recovered_approximation_validity_detects_violated_domain():
    result = resolve(
        "physical.lithography.source_nuclear_radius_coefficient",
        assignments={
            "physical.lithography.source_binding_coulomb_coefficient": -1.0,
        },
    )
    check = next(
        c for c in result.approximation_validity
        if c.equation == "physical.eq.lithography_source_nuclear_radius_coefficient"
    )
    assert check.satisfied is False
    assert check.missing == set()


def test_recovered_approximation_validity_stays_symbolic_when_domain_missing():
    result = resolve("physical.lithography.source_nuclear_radius_coefficient")
    check = next(
        c for c in result.approximation_validity
        if c.equation == "physical.eq.lithography_source_nuclear_radius_coefficient"
    )
    assert check.satisfied is None
    assert check.missing == {
        "physical.lithography.source_binding_coulomb_coefficient"
    }
