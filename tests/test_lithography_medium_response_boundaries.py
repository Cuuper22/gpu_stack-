"""
tests/test_lithography_medium_response_boundaries.py
====================================================

The imaging medium's optical response is modeled with electron counts and
fractions, and simple accounting rules must hold: you cannot polarize more
electrons than the formula unit contains, a fraction can never exceed 1, and
the medium's resonance energy must sit strictly above the source photon
energy (a resonance at or below the drive energy would make the transparency
model invalid). This module verifies those rules three ways. It checks the
inequalities exist with the exact operator and right-hand side. It assigns
values that break each rule and confirms the matching constraint is reported
as violated — while exact boundary values like fraction = 1.0 pass cleanly.
And it checks propagation: violating an upstream count also flags the
downstream fraction and marks the fraction equation's validity as failed,
so a bad input cannot hide behind a derived value.
"""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.core import Inequality, RelationRole


FORMULA_ELECTRON_COUNT = Registry.variables[
    "physical.lithography.medium_formula_unit_electron_count"
].symbol
POLARIZABLE_ELECTRON_COUNT = Registry.variables[
    "physical.lithography.medium_polarizable_electron_count"
].symbol
SOURCE_PHOTON_ENERGY = Registry.variables[
    "physical.lithography.photon_energy"
].symbol


MEDIUM_RESPONSE_BOUNDARY_CONSTRAINTS = [
    (
        "physical.ineq.lithography_medium_polarizable_electron_count_within_formula_unit",
        "physical.lithography.medium_polarizable_electron_count",
        "<=",
        FORMULA_ELECTRON_COUNT,
    ),
    (
        "physical.ineq.lithography_medium_polarizable_electron_fraction_within_unit_interval",
        "physical.lithography.medium_polarizable_electron_fraction",
        "<=",
        sp.Integer(1),
    ),
    (
        "physical.ineq.lithography_medium_dominant_oscillator_electron_count_within_polarizable_count",
        "physical.lithography.medium_dominant_oscillator_electron_count",
        "<=",
        POLARIZABLE_ELECTRON_COUNT,
    ),
    (
        "physical.ineq.lithography_medium_dominant_oscillator_electron_count_within_formula_unit",
        "physical.lithography.medium_dominant_oscillator_electron_count",
        "<=",
        FORMULA_ELECTRON_COUNT,
    ),
    (
        "physical.ineq.lithography_medium_oscillator_sum_rule_fraction_within_unit_interval",
        "physical.lithography.medium_oscillator_sum_rule_fraction",
        "<=",
        sp.Integer(1),
    ),
    (
        "physical.ineq.lithography_medium_resonance_energy_above_source_photon_energy",
        "physical.lithography.medium_resonance_energy",
        ">",
        SOURCE_PHOTON_ENERGY,
    ),
    (
        "physical.ineq.lithography_medium_resonance_to_source_frequency_ratio_above_unity",
        "physical.lithography.medium_resonance_to_source_frequency_ratio",
        ">",
        sp.Integer(1),
    ),
]


def _failed_constraint(result, equation):
    check = next(c for c in result.constraints if c.equation == equation)
    assert check.satisfied is False
    assert check.missing == set()
    return check


def _failed_medium_response_constraints(result):
    return {
        c.equation
        for c in result.constraints
        if c.satisfied is False
        and c.equation.startswith("physical.ineq.lithography_medium_")
    }


def _failed_medium_response_domain_constraints(result):
    return {
        c.equation
        for c in result.constraints
        if c.satisfied is False
        and c.equation.startswith("domain.physical.lithography.medium_")
    }


def _failed_medium_response_validity(result):
    return {
        c.equation
        for c in result.approximation_validity
        if c.satisfied is False
        and c.equation.startswith("physical.eq.lithography_medium_")
    }


def test_medium_response_boundaries_are_named_constraints():
    for equation_name, variable_name, op, rhs in MEDIUM_RESPONSE_BOUNDARY_CONSTRAINTS:
        eq = Registry.equations[equation_name]
        variable = Registry.variables[variable_name]

        assert isinstance(eq, Inequality)
        assert eq.role is RelationRole.CONSTRAINT
        assert eq in variable.constraints()
        assert eq.op == op
        assert eq.rhs == rhs
        assert eq.references
        assert getattr(eq, "_check_units_flag", False)
        assert isinstance(eq.as_sympy(), sp.Rel)
        assert not eq.is_trivially_true()


def test_medium_response_count_boundaries_report_invalid_assignments():
    polarizable_result = resolve(
        "physical.lithography.medium_polarizable_electron_count",
        assignments={
            "physical.lithography.medium_polarizable_electron_count": 6.0,
            "physical.lithography.medium_formula_unit_electron_count": 4.0,
        },
    )
    assert float(polarizable_result.value) == pytest.approx(6.0)
    _failed_constraint(
        polarizable_result,
        "physical.ineq.lithography_medium_polarizable_electron_count_within_formula_unit",
    )
    assert _failed_medium_response_constraints(polarizable_result) == {
        "physical.ineq.lithography_medium_polarizable_electron_count_within_formula_unit",
    }

    oscillator_result = resolve(
        "physical.lithography.medium_dominant_oscillator_electron_count",
        assignments={
            "physical.lithography.medium_dominant_oscillator_electron_count": 5.0,
            "physical.lithography.medium_polarizable_electron_count": 3.0,
            "physical.lithography.medium_formula_unit_electron_count": 4.0,
        },
    )
    assert float(oscillator_result.value) == pytest.approx(5.0)
    _failed_constraint(
        oscillator_result,
        "physical.ineq.lithography_medium_dominant_oscillator_electron_count_within_polarizable_count",
    )
    _failed_constraint(
        oscillator_result,
        "physical.ineq.lithography_medium_dominant_oscillator_electron_count_within_formula_unit",
    )
    assert _failed_medium_response_constraints(oscillator_result) == {
        "physical.ineq.lithography_medium_dominant_oscillator_electron_count_within_polarizable_count",
        "physical.ineq.lithography_medium_dominant_oscillator_electron_count_within_formula_unit",
    }


def test_medium_response_fraction_boundaries_report_invalid_assignments():
    polarizable_fraction_result = resolve(
        "physical.lithography.medium_polarizable_electron_fraction",
        assignments={
            "physical.lithography.medium_polarizable_electron_fraction": 1.25,
        },
    )
    assert float(polarizable_fraction_result.value) == pytest.approx(1.25)
    _failed_constraint(
        polarizable_fraction_result,
        "physical.ineq.lithography_medium_polarizable_electron_fraction_within_unit_interval",
    )
    assert _failed_medium_response_constraints(polarizable_fraction_result) == {
        "physical.ineq.lithography_medium_polarizable_electron_fraction_within_unit_interval",
    }

    sum_rule_result = resolve(
        "physical.lithography.medium_oscillator_sum_rule_fraction",
        assignments={
            "physical.lithography.medium_oscillator_sum_rule_fraction": 1.25,
        },
    )
    assert float(sum_rule_result.value) == pytest.approx(1.25)
    _failed_constraint(
        sum_rule_result,
        "physical.ineq.lithography_medium_oscillator_sum_rule_fraction_within_unit_interval",
    )
    assert _failed_medium_response_constraints(sum_rule_result) == {
        "physical.ineq.lithography_medium_oscillator_sum_rule_fraction_within_unit_interval",
    }


def test_medium_response_resonance_boundaries_report_invalid_assignments():
    resonance_result = resolve(
        "physical.lithography.medium_resonance_energy",
        assignments={
            "physical.lithography.medium_resonance_energy": 1.0,
            "physical.lithography.photon_energy": 2.0,
        },
    )
    assert float(resonance_result.value) == pytest.approx(1.0)
    _failed_constraint(
        resonance_result,
        "physical.ineq.lithography_medium_resonance_energy_above_source_photon_energy",
    )
    assert _failed_medium_response_constraints(resonance_result) == {
        "physical.ineq.lithography_medium_resonance_energy_above_source_photon_energy",
    }

    equal_resonance_result = resolve(
        "physical.lithography.medium_resonance_energy",
        assignments={
            "physical.lithography.medium_resonance_energy": 2.0,
            "physical.lithography.photon_energy": 2.0,
        },
    )
    assert float(equal_resonance_result.value) == pytest.approx(2.0)
    _failed_constraint(
        equal_resonance_result,
        "physical.ineq.lithography_medium_resonance_energy_above_source_photon_energy",
    )
    assert _failed_medium_response_constraints(equal_resonance_result) == {
        "physical.ineq.lithography_medium_resonance_energy_above_source_photon_energy",
    }

    ratio_result = resolve(
        "physical.lithography.medium_resonance_to_source_frequency_ratio",
        assignments={
            "physical.lithography.medium_resonance_to_source_frequency_ratio": 1.0,
        },
    )
    assert float(ratio_result.value) == pytest.approx(1.0)
    _failed_constraint(
        ratio_result,
        "physical.ineq.lithography_medium_resonance_to_source_frequency_ratio_above_unity",
    )
    assert _failed_medium_response_constraints(ratio_result) == {
        "physical.ineq.lithography_medium_resonance_to_source_frequency_ratio_above_unity",
    }


def test_medium_response_closed_boundaries_accept_exact_assignments():
    polarizable_result = resolve(
        "physical.lithography.medium_polarizable_electron_fraction",
        assignments={
            "physical.lithography.medium_polarizable_electron_count": 4.0,
            "physical.lithography.medium_formula_unit_electron_count": 4.0,
        },
    )
    assert float(polarizable_result.value) == pytest.approx(1.0)
    assert _failed_medium_response_constraints(polarizable_result) == set()
    assert _failed_medium_response_domain_constraints(polarizable_result) == set()
    assert _failed_medium_response_validity(polarizable_result) == set()

    oscillator_result = resolve(
        "physical.lithography.medium_oscillator_sum_rule_fraction",
        assignments={
            "physical.lithography.medium_dominant_oscillator_electron_count": 3.0,
            "physical.lithography.medium_polarizable_electron_count": 3.0,
            "physical.lithography.medium_formula_unit_electron_count": 3.0,
        },
    )
    assert float(oscillator_result.value) == pytest.approx(1.0)
    assert _failed_medium_response_constraints(oscillator_result) == set()
    assert _failed_medium_response_domain_constraints(oscillator_result) == set()
    assert _failed_medium_response_validity(oscillator_result) == set()


@pytest.mark.parametrize(
    ("target", "value", "expected_domains"),
    [
        (
            "physical.lithography.medium_polarizable_electron_count",
            -1.0,
            {
                "domain.physical.lithography.medium_polarizable_electron_count.nonnegative",
            },
        ),
        (
            "physical.lithography.medium_polarizable_electron_fraction",
            -0.1,
            {
                "domain.physical.lithography.medium_polarizable_electron_fraction.nonnegative",
                "domain.physical.lithography.medium_polarizable_electron_fraction.min",
            },
        ),
        (
            "physical.lithography.medium_dominant_oscillator_electron_count",
            -1.0,
            {
                "domain.physical.lithography.medium_dominant_oscillator_electron_count.nonnegative",
            },
        ),
        (
            "physical.lithography.medium_oscillator_sum_rule_fraction",
            -0.1,
            {
                "domain.physical.lithography.medium_oscillator_sum_rule_fraction.nonnegative",
                "domain.physical.lithography.medium_oscillator_sum_rule_fraction.min",
            },
        ),
        (
            "physical.lithography.medium_resonance_energy",
            0.0,
            {
                "domain.physical.lithography.medium_resonance_energy.positive",
            },
        ),
        (
            "physical.lithography.medium_resonance_to_source_frequency_ratio",
            0.0,
            {
                "domain.physical.lithography.medium_resonance_to_source_frequency_ratio.positive",
            },
        ),
    ],
)
def test_medium_response_lower_domains_report_invalid_assignments(
    target, value, expected_domains
):
    result = resolve(target, assignments={target: value})

    assert float(result.value) == pytest.approx(value)
    assert expected_domains <= _failed_medium_response_domain_constraints(result)


def test_medium_response_polarizable_count_violation_propagates_to_fraction():
    result = resolve(
        "physical.lithography.medium_polarizable_electron_fraction",
        assignments={
            "physical.lithography.medium_polarizable_electron_count": 6.0,
            "physical.lithography.medium_formula_unit_electron_count": 4.0,
        },
    )

    assert float(result.value) == pytest.approx(1.5)
    assert _failed_medium_response_constraints(result) == {
        "physical.ineq.lithography_medium_polarizable_electron_count_within_formula_unit",
        "physical.ineq.lithography_medium_polarizable_electron_fraction_within_unit_interval",
    }
    assert _failed_medium_response_validity(result) == {
        "physical.eq.lithography_medium_polarizable_electron_fraction_from_count",
    }


def test_medium_response_negative_polarizable_count_domain_propagates_to_fraction():
    result = resolve(
        "physical.lithography.medium_polarizable_electron_fraction",
        assignments={
            "physical.lithography.medium_polarizable_electron_count": -1.0,
            "physical.lithography.medium_formula_unit_electron_count": 4.0,
        },
    )

    assert float(result.value) == pytest.approx(-0.25)
    assert {
        "domain.physical.lithography.medium_polarizable_electron_count.nonnegative",
        "domain.physical.lithography.medium_polarizable_electron_fraction.nonnegative",
        "domain.physical.lithography.medium_polarizable_electron_fraction.min",
    } <= _failed_medium_response_domain_constraints(result)
    assert _failed_medium_response_validity(result) == {
        "physical.eq.lithography_medium_polarizable_electron_fraction_from_count",
    }


def test_medium_response_dominant_oscillator_violation_propagates_to_sum_rule_fraction():
    result = resolve(
        "physical.lithography.medium_oscillator_sum_rule_fraction",
        assignments={
            "physical.lithography.medium_dominant_oscillator_electron_count": 5.0,
            "physical.lithography.medium_polarizable_electron_count": 3.0,
            "physical.lithography.medium_formula_unit_electron_count": 4.0,
        },
    )

    assert float(result.value) == pytest.approx(5.0 / 3.0)
    assert _failed_medium_response_constraints(result) == {
        "physical.ineq.lithography_medium_dominant_oscillator_electron_count_within_polarizable_count",
        "physical.ineq.lithography_medium_dominant_oscillator_electron_count_within_formula_unit",
        "physical.ineq.lithography_medium_oscillator_sum_rule_fraction_within_unit_interval",
    }
    assert _failed_medium_response_validity(result) == {
        "physical.eq.lithography_medium_oscillator_sum_rule_fraction_from_count",
    }


def test_medium_response_negative_oscillator_count_domain_propagates_to_sum_rule_fraction():
    result = resolve(
        "physical.lithography.medium_oscillator_sum_rule_fraction",
        assignments={
            "physical.lithography.medium_dominant_oscillator_electron_count": -1.0,
            "physical.lithography.medium_polarizable_electron_count": 3.0,
        },
    )

    assert float(result.value) == pytest.approx(-1.0 / 3.0)
    assert {
        "domain.physical.lithography.medium_dominant_oscillator_electron_count.nonnegative",
        "domain.physical.lithography.medium_oscillator_sum_rule_fraction.nonnegative",
        "domain.physical.lithography.medium_oscillator_sum_rule_fraction.min",
    } <= _failed_medium_response_domain_constraints(result)
    assert _failed_medium_response_validity(result) == {
        "physical.eq.lithography_medium_oscillator_sum_rule_fraction_from_count",
    }


def test_medium_response_resonance_energy_violation_propagates_to_ratio():
    result = resolve(
        "physical.lithography.medium_resonance_to_source_frequency_ratio",
        assignments={
            "physical.lithography.medium_resonance_energy": 1.0,
            "physical.lithography.photon_energy": 2.0,
        },
    )

    assert float(result.value) == pytest.approx(0.5)
    assert _failed_medium_response_constraints(result) == {
        "physical.ineq.lithography_medium_resonance_energy_above_source_photon_energy",
        "physical.ineq.lithography_medium_resonance_to_source_frequency_ratio_above_unity",
    }


def test_medium_response_zero_resonance_energy_domain_propagates_to_ratio():
    result = resolve(
        "physical.lithography.medium_resonance_to_source_frequency_ratio",
        assignments={
            "physical.lithography.medium_resonance_energy": 0.0,
            "physical.lithography.photon_energy": 2.0,
        },
    )

    assert float(result.value) == pytest.approx(0.0)
    assert {
        "domain.physical.lithography.medium_resonance_energy.positive",
        "domain.physical.lithography.medium_resonance_to_source_frequency_ratio.positive",
    } <= _failed_medium_response_domain_constraints(result)
