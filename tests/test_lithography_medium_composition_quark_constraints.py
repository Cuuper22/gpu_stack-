"""
tests/test_lithography_medium_composition_quark_constraints.py
==============================================================

The imaging medium should derive component nucleon counts from valence quarks.
"""

import pytest
import sympy as sp

from gpu_stack import Inequality, Registry, RelationRole, resolve
from tests.helpers.lithography import medium_component_quark_assignments


def test_lithography_medium_component_valence_quark_constraints():
    proton_eq = Registry.equations[
        "physical.eq.lithography_medium_component_a_proton_count_from_valence_quarks"
    ]
    neutron_eq = Registry.equations[
        "physical.eq.lithography_medium_component_a_neutron_count_from_valence_quarks"
    ]
    proton_feasibility_eq = Registry.equations[
        "physical.ineq.lithography_medium_component_a_valence_quarks_imply_nonnegative_protons"
    ]
    positive_proton_feasibility_eq = Registry.equations[
        "physical.ineq.lithography_medium_component_a_valence_quarks_imply_positive_protons"
    ]
    neutron_feasibility_eq = Registry.equations[
        "physical.ineq.lithography_medium_component_a_valence_quarks_imply_nonnegative_neutrons"
    ]
    triplet_integrality_eq = Registry.equations[
        "physical.eq.lithography_medium_component_a_valence_quark_triplet_integrality"
    ]

    assert proton_eq.role is RelationRole.IDENTITY
    assert neutron_eq.role is RelationRole.IDENTITY
    assert isinstance(proton_feasibility_eq, Inequality)
    assert isinstance(positive_proton_feasibility_eq, Inequality)
    assert isinstance(neutron_feasibility_eq, Inequality)
    assert proton_feasibility_eq.role is RelationRole.CONSTRAINT
    assert positive_proton_feasibility_eq.role is RelationRole.CONSTRAINT
    assert neutron_feasibility_eq.role is RelationRole.CONSTRAINT
    assert triplet_integrality_eq.role is RelationRole.CONSTRAINT
    assert positive_proton_feasibility_eq.references
    assert getattr(positive_proton_feasibility_eq, "_check_units_flag", False)
    assert isinstance(positive_proton_feasibility_eq.as_sympy(), sp.Rel)
    assert not positive_proton_feasibility_eq.is_trivially_true()
    assert isinstance(triplet_integrality_eq.as_sympy(), sp.Equality)
    assert triplet_integrality_eq.as_sympy() is not sp.S.true

    component_a_proton_result = resolve(
        "physical.lithography.medium_component_a_proton_count",
        assignments=medium_component_quark_assignments("a", 6, 7),
    )
    assert float(component_a_proton_result.value) == pytest.approx(6.0)
    assert (
        "physical.eq.lithography_medium_component_a_proton_count_from_valence_quarks"
        in [step.equation for step in component_a_proton_result.trace]
    )
    triplet_integrality = next(
        c for c in component_a_proton_result.constraints
        if c.equation == triplet_integrality_eq.name
    )
    assert triplet_integrality.satisfied is True

    invalid_proton_result = resolve(
        "physical.lithography.medium_component_a_proton_count",
        assignments={
            "physical.lithography.medium_component_a_valence_up_quark_count": 1,
            "physical.lithography.medium_component_a_valence_down_quark_count": 5,
        },
    )
    assert float(invalid_proton_result.value) == pytest.approx(-1.0)
    invalid_proton_feasibility = next(
        c for c in invalid_proton_result.constraints
        if c.equation == proton_feasibility_eq.name
    )
    assert invalid_proton_feasibility.satisfied is False

    zero_proton_result = resolve(
        "physical.lithography.medium_component_a_proton_count",
        assignments=medium_component_quark_assignments("a", 0, 1),
    )
    assert float(zero_proton_result.value) == pytest.approx(0.0)
    zero_positive_proton_feasibility = next(
        c for c in zero_proton_result.constraints
        if c.equation == positive_proton_feasibility_eq.name
    )
    assert zero_positive_proton_feasibility.satisfied is False

    invalid_neutron_result = resolve(
        "physical.lithography.medium_component_a_neutron_count",
        assignments={
            "physical.lithography.medium_component_a_valence_up_quark_count": 5,
            "physical.lithography.medium_component_a_valence_down_quark_count": 1,
        },
    )
    assert float(invalid_neutron_result.value) == pytest.approx(-1.0)
    invalid_neutron_feasibility = next(
        c for c in invalid_neutron_result.constraints
        if c.equation == neutron_feasibility_eq.name
    )
    assert invalid_neutron_feasibility.satisfied is False

    fractional_triplet_result = resolve(
        "physical.lithography.medium_component_a_valence_down_quark_count",
        assignments={
            "physical.lithography.medium_component_a_valence_up_quark_count": 1,
            "physical.lithography.medium_component_a_valence_down_quark_count": 1,
        },
    )
    fractional_triplet_constraint = next(
        c for c in fractional_triplet_result.constraints
        if c.equation == triplet_integrality_eq.name
    )
    assert fractional_triplet_constraint.satisfied is False
    assert [
        c.equation for c in fractional_triplet_result.constraints
    ].count(triplet_integrality_eq.name) == 1

    component_b_proton_eq = Registry.equations[
        "physical.eq.lithography_medium_component_b_proton_count_from_valence_quarks"
    ]
    component_b_neutron_eq = Registry.equations[
        "physical.eq.lithography_medium_component_b_neutron_count_from_valence_quarks"
    ]
    component_b_proton_feasibility_eq = Registry.equations[
        "physical.ineq.lithography_medium_component_b_valence_quarks_imply_nonnegative_protons"
    ]
    component_b_positive_proton_feasibility_eq = Registry.equations[
        "physical.ineq.lithography_medium_component_b_valence_quarks_imply_positive_protons"
    ]
    component_b_neutron_feasibility_eq = Registry.equations[
        "physical.ineq.lithography_medium_component_b_valence_quarks_imply_nonnegative_neutrons"
    ]
    component_b_triplet_eq = Registry.equations[
        "physical.eq.lithography_medium_component_b_valence_quark_triplet_integrality"
    ]

    assert component_b_proton_eq.role is RelationRole.IDENTITY
    assert component_b_neutron_eq.role is RelationRole.IDENTITY
    assert isinstance(component_b_proton_feasibility_eq, Inequality)
    assert isinstance(component_b_positive_proton_feasibility_eq, Inequality)
    assert isinstance(component_b_neutron_feasibility_eq, Inequality)
    assert component_b_proton_feasibility_eq.role is RelationRole.CONSTRAINT
    assert component_b_positive_proton_feasibility_eq.role is RelationRole.CONSTRAINT
    assert component_b_neutron_feasibility_eq.role is RelationRole.CONSTRAINT
    assert component_b_triplet_eq.role is RelationRole.CONSTRAINT
    assert component_b_positive_proton_feasibility_eq.references
    assert getattr(component_b_positive_proton_feasibility_eq, "_check_units_flag", False)
    assert isinstance(component_b_positive_proton_feasibility_eq.as_sympy(), sp.Rel)
    assert not component_b_positive_proton_feasibility_eq.is_trivially_true()
    assert isinstance(component_b_triplet_eq.as_sympy(), sp.Equality)
    assert component_b_triplet_eq.as_sympy() is not sp.S.true

    component_b_proton_result = resolve(
        "physical.lithography.medium_component_b_proton_count",
        assignments=medium_component_quark_assignments("b", 8, 9),
    )
    assert float(component_b_proton_result.value) == pytest.approx(8.0)
    assert (
        "physical.eq.lithography_medium_component_b_proton_count_from_valence_quarks"
        in [step.equation for step in component_b_proton_result.trace]
    )
    component_b_triplet_integrality = next(
        c for c in component_b_proton_result.constraints
        if c.equation == component_b_triplet_eq.name
    )
    assert component_b_triplet_integrality.satisfied is True

    component_b_neutron_result = resolve(
        "physical.lithography.medium_component_b_neutron_count",
        assignments=medium_component_quark_assignments("b", 8, 9),
    )
    assert float(component_b_neutron_result.value) == pytest.approx(9.0)
    assert [step.equation for step in component_b_neutron_result.trace] == [
        "physical.eq.lithography_medium_component_b_neutron_count_from_valence_quarks"
    ]

    invalid_component_b_proton_result = resolve(
        "physical.lithography.medium_component_b_proton_count",
        assignments={
            "physical.lithography.medium_component_b_valence_up_quark_count": 1,
            "physical.lithography.medium_component_b_valence_down_quark_count": 5,
        },
    )
    assert float(invalid_component_b_proton_result.value) == pytest.approx(-1.0)
    invalid_component_b_proton_feasibility = next(
        c for c in invalid_component_b_proton_result.constraints
        if c.equation == component_b_proton_feasibility_eq.name
    )
    assert invalid_component_b_proton_feasibility.satisfied is False

    zero_component_b_proton_result = resolve(
        "physical.lithography.medium_component_b_proton_count",
        assignments=medium_component_quark_assignments("b", 0, 1),
    )
    assert float(zero_component_b_proton_result.value) == pytest.approx(0.0)
    zero_component_b_positive_proton_feasibility = next(
        c for c in zero_component_b_proton_result.constraints
        if c.equation == component_b_positive_proton_feasibility_eq.name
    )
    assert zero_component_b_positive_proton_feasibility.satisfied is False

    invalid_component_b_neutron_result = resolve(
        "physical.lithography.medium_component_b_neutron_count",
        assignments={
            "physical.lithography.medium_component_b_valence_up_quark_count": 5,
            "physical.lithography.medium_component_b_valence_down_quark_count": 1,
        },
    )
    assert float(invalid_component_b_neutron_result.value) == pytest.approx(-1.0)
    invalid_component_b_neutron_feasibility = next(
        c for c in invalid_component_b_neutron_result.constraints
        if c.equation == component_b_neutron_feasibility_eq.name
    )
    assert invalid_component_b_neutron_feasibility.satisfied is False

    fractional_component_b_triplet_result = resolve(
        "physical.lithography.medium_component_b_valence_down_quark_count",
        assignments={
            "physical.lithography.medium_component_b_valence_up_quark_count": 1,
            "physical.lithography.medium_component_b_valence_down_quark_count": 1,
        },
    )
    fractional_component_b_triplet_constraint = next(
        c for c in fractional_component_b_triplet_result.constraints
        if c.equation == component_b_triplet_eq.name
    )
    assert fractional_component_b_triplet_constraint.satisfied is False
    assert [
        c.equation for c in fractional_component_b_triplet_result.constraints
    ].count(component_b_triplet_eq.name) == 1
