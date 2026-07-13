"""
tests/test_lithography_medium_composition_quark_constraints.py
==============================================================

The imaging medium should derive component valence quark counts from the
proton/neutron roots via U = 2Z + N and D = Z + 2N.
"""

import pytest
import sympy as sp

from gpu_stack import Inequality, Registry, RelationRole, resolve
from tests.helpers.lithography import medium_component_quark_assignments


def test_lithography_medium_component_valence_quark_constraints():
    up_quark_eq = Registry.equations[
        "physical.eq.lithography_medium_component_a_valence_up_quark_count_from_zn"
    ]
    down_quark_eq = Registry.equations[
        "physical.eq.lithography_medium_component_a_valence_down_quark_count_from_zn"
    ]
    positive_proton_eq = Registry.equations[
        "physical.ineq.lithography_medium_component_a_proton_count_positive"
    ]

    assert up_quark_eq.role is RelationRole.IDENTITY
    assert down_quark_eq.role is RelationRole.IDENTITY
    assert isinstance(positive_proton_eq, Inequality)
    assert positive_proton_eq.role is RelationRole.CONSTRAINT
    assert positive_proton_eq.references
    assert getattr(positive_proton_eq, "_check_units_flag", False)
    assert isinstance(positive_proton_eq.as_sympy(), sp.Rel)
    assert not positive_proton_eq.is_trivially_true()
    assert up_quark_eq.references
    assert down_quark_eq.references

    component_a_up_result = resolve(
        "physical.lithography.medium_component_a_valence_up_quark_count",
        assignments=medium_component_quark_assignments("a", 6, 7),
    )
    assert float(component_a_up_result.value) == pytest.approx(19.0)
    assert (
        "physical.eq.lithography_medium_component_a_valence_up_quark_count_from_zn"
        in [step.equation for step in component_a_up_result.trace]
    )
    positive_proton = next(
        c for c in component_a_up_result.constraints
        if c.equation == positive_proton_eq.name
    )
    assert positive_proton.satisfied is True

    component_a_down_result = resolve(
        "physical.lithography.medium_component_a_valence_down_quark_count",
        assignments=medium_component_quark_assignments("a", 6, 7),
    )
    assert float(component_a_down_result.value) == pytest.approx(20.0)
    assert [step.equation for step in component_a_down_result.trace] == [
        "physical.eq.lithography_medium_component_a_valence_down_quark_count_from_zn"
    ]

    zero_proton_result = resolve(
        "physical.lithography.medium_component_a_valence_up_quark_count",
        assignments=medium_component_quark_assignments("a", 0, 1),
    )
    assert float(zero_proton_result.value) == pytest.approx(1.0)
    zero_positive_proton = next(
        c for c in zero_proton_result.constraints
        if c.equation == positive_proton_eq.name
    )
    assert zero_positive_proton.satisfied is False
    assert [
        c.equation for c in zero_proton_result.constraints
    ].count(positive_proton_eq.name) == 1

    fractional_proton_result = resolve(
        "physical.lithography.medium_component_a_valence_up_quark_count",
        assignments={
            "physical.lithography.medium_component_a_proton_count": 2.5,
            "physical.lithography.medium_component_a_neutron_count": 2,
        },
    )
    assert float(fractional_proton_result.value) == pytest.approx(7.0)
    fractional_integer_violations = [
        v for v in fractional_proton_result.violated_constraints
        if v.equation
        == "domain.physical.lithography.medium_component_a_proton_count.integer"
    ]
    assert len(fractional_integer_violations) == 1

    component_b_up_quark_eq = Registry.equations[
        "physical.eq.lithography_medium_component_b_valence_up_quark_count_from_zn"
    ]
    component_b_down_quark_eq = Registry.equations[
        "physical.eq.lithography_medium_component_b_valence_down_quark_count_from_zn"
    ]
    component_b_positive_proton_eq = Registry.equations[
        "physical.ineq.lithography_medium_component_b_proton_count_positive"
    ]

    assert component_b_up_quark_eq.role is RelationRole.IDENTITY
    assert component_b_down_quark_eq.role is RelationRole.IDENTITY
    assert isinstance(component_b_positive_proton_eq, Inequality)
    assert component_b_positive_proton_eq.role is RelationRole.CONSTRAINT
    assert component_b_positive_proton_eq.references
    assert getattr(component_b_positive_proton_eq, "_check_units_flag", False)
    assert isinstance(component_b_positive_proton_eq.as_sympy(), sp.Rel)
    assert not component_b_positive_proton_eq.is_trivially_true()

    component_b_up_result = resolve(
        "physical.lithography.medium_component_b_valence_up_quark_count",
        assignments=medium_component_quark_assignments("b", 8, 9),
    )
    assert float(component_b_up_result.value) == pytest.approx(25.0)
    assert (
        "physical.eq.lithography_medium_component_b_valence_up_quark_count_from_zn"
        in [step.equation for step in component_b_up_result.trace]
    )
    component_b_positive_proton = next(
        c for c in component_b_up_result.constraints
        if c.equation == component_b_positive_proton_eq.name
    )
    assert component_b_positive_proton.satisfied is True

    component_b_down_result = resolve(
        "physical.lithography.medium_component_b_valence_down_quark_count",
        assignments=medium_component_quark_assignments("b", 8, 9),
    )
    assert float(component_b_down_result.value) == pytest.approx(26.0)
    assert [step.equation for step in component_b_down_result.trace] == [
        "physical.eq.lithography_medium_component_b_valence_down_quark_count_from_zn"
    ]

    zero_component_b_proton_result = resolve(
        "physical.lithography.medium_component_b_valence_up_quark_count",
        assignments=medium_component_quark_assignments("b", 0, 1),
    )
    assert float(zero_component_b_proton_result.value) == pytest.approx(1.0)
    zero_component_b_positive_proton = next(
        c for c in zero_component_b_proton_result.constraints
        if c.equation == component_b_positive_proton_eq.name
    )
    assert zero_component_b_positive_proton.satisfied is False
    assert [
        c.equation for c in zero_component_b_proton_result.constraints
    ].count(component_b_positive_proton_eq.name) == 1
