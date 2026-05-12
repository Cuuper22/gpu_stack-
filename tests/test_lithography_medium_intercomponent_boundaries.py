"""
tests/test_lithography_medium_intercomponent_boundaries.py
==========================================================

Focused boundary coverage for lithography imaging-medium intercomponent roots.
"""

import pytest

from gpu_stack import Registry, resolve


INTERCOMPONENT_DOMAIN_CASES = [
    (
        "physical.lithography.medium_intercomponent_gap_fraction",
        -0.25,
        "nonnegative",
    ),
    (
        "physical.lithography.medium_intercomponent_polarizable_site_density_factor",
        -1.0,
        "nonnegative",
    ),
    (
        "physical.lithography.medium_intercomponent_effective_separation",
        0.0,
        "positive",
    ),
    (
        "physical.lithography.medium_intercomponent_relative_permittivity",
        0.0,
        "positive",
    ),
    (
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count",
        0.0,
        "positive",
    ),
]


def _failed_medium_domain_constraints(result):
    return {
        c.equation
        for c in result.constraints
        if c.satisfied is False
        and c.equation.startswith("domain.physical.lithography.medium_")
    }


@pytest.mark.parametrize(
    ("variable_name", "invalid_value", "domain_suffix"),
    INTERCOMPONENT_DOMAIN_CASES,
)
def test_medium_intercomponent_domains_report_invalid_assignments(
    variable_name, invalid_value, domain_suffix
):
    result = resolve(variable_name, assignments={variable_name: invalid_value})

    assert float(result.value) == pytest.approx(invalid_value)
    assert (
        f"domain.{variable_name}.{domain_suffix}"
        in _failed_medium_domain_constraints(result)
    )


@pytest.mark.parametrize(
    ("variable_name", "_invalid_value", "domain_suffix"),
    INTERCOMPONENT_DOMAIN_CASES,
)
def test_medium_intercomponent_boundary_domains_are_declared(
    variable_name, _invalid_value, domain_suffix
):
    variable = Registry.variables[variable_name]

    assert variable.assumptions[domain_suffix] is True
    assert variable.references
