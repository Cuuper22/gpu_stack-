"""Lithography source quantum resolution-chain coverage."""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.core import Inequality, RelationRole
from tests.helpers.lithography import source_quark_assignments


def test_lithography_source_quantum_shell_and_valence_resolution_chain():
    inner_shielding = Registry.variables[
        "physical.lithography.source_inner_shell_shielding_factor"
    ]
    same_shielding = Registry.variables[
        "physical.lithography.source_same_shell_shielding_factor"
    ]
    ionization_principal_result = resolve(
        "physical.lithography.source_ionization_principal_quantum_number",
        assignments={
            "physical.lithography.source_lower_principal_quantum_number": 3,
        },
    )
    assert float(ionization_principal_result.value) == pytest.approx(3.0)

    proton_count_result = resolve(
        "physical.lithography.source_proton_count",
        assignments=source_quark_assignments(3, 4),
    )
    assert float(proton_count_result.value) == pytest.approx(3.0)
    assert [step.equation for step in proton_count_result.trace] == [
        "physical.eq.lithography_source_proton_count_from_valence_quarks",
    ]
    proton_feasibility_eq = Registry.equations[
        "physical.ineq.lithography_source_valence_quarks_imply_nonnegative_protons"
    ]
    positive_proton_feasibility_eq = Registry.equations[
        "physical.ineq.lithography_source_valence_quarks_imply_positive_protons"
    ]
    assert isinstance(proton_feasibility_eq, Inequality)
    assert isinstance(positive_proton_feasibility_eq, Inequality)
    assert proton_feasibility_eq.role is RelationRole.CONSTRAINT
    assert positive_proton_feasibility_eq.role is RelationRole.CONSTRAINT
    assert isinstance(proton_feasibility_eq.as_sympy(), sp.Rel)
    assert isinstance(positive_proton_feasibility_eq.as_sympy(), sp.Rel)
    assert not proton_feasibility_eq.is_trivially_true()
    assert not positive_proton_feasibility_eq.is_trivially_true()
    assert proton_feasibility_eq.references
    assert positive_proton_feasibility_eq.references
    assert getattr(proton_feasibility_eq, "_check_units_flag", False)
    assert getattr(positive_proton_feasibility_eq, "_check_units_flag", False)
    proton_feasibility = next(
        c for c in proton_count_result.constraints
        if c.equation == proton_feasibility_eq.name
    )
    assert proton_feasibility.satisfied is True
    positive_proton_feasibility = next(
        c for c in proton_count_result.constraints
        if c.equation == positive_proton_feasibility_eq.name
    )
    assert positive_proton_feasibility.satisfied is True
    triplet_integrality_eq = Registry.equations[
        "physical.eq.lithography_source_valence_quark_triplet_integrality"
    ]
    assert triplet_integrality_eq.role is RelationRole.CONSTRAINT
    assert isinstance(triplet_integrality_eq.as_sympy(), sp.Equality)
    assert triplet_integrality_eq.as_sympy() is not sp.S.true
    assert triplet_integrality_eq.references
    assert getattr(triplet_integrality_eq, "_check_units_flag", False)
    triplet_integrality = next(
        c for c in proton_count_result.constraints
        if c.equation == triplet_integrality_eq.name
    )
    assert triplet_integrality.satisfied is True
    neutron_count_result = resolve(
        "physical.lithography.source_neutron_count",
        assignments=source_quark_assignments(3, 4),
    )
    assert float(neutron_count_result.value) == pytest.approx(4.0)
    assert [step.equation for step in neutron_count_result.trace] == [
        "physical.eq.lithography_source_neutron_count_from_valence_quarks",
    ]
    neutron_feasibility_eq = Registry.equations[
        "physical.ineq.lithography_source_valence_quarks_imply_nonnegative_neutrons"
    ]
    assert isinstance(neutron_feasibility_eq, Inequality)
    assert neutron_feasibility_eq.role is RelationRole.CONSTRAINT
    assert isinstance(neutron_feasibility_eq.as_sympy(), sp.Rel)
    assert not neutron_feasibility_eq.is_trivially_true()
    assert neutron_feasibility_eq.references
    assert getattr(neutron_feasibility_eq, "_check_units_flag", False)
    neutron_feasibility = next(
        c for c in neutron_count_result.constraints
        if c.equation == neutron_feasibility_eq.name
    )
    assert neutron_feasibility.satisfied is True

    invalid_proton_result = resolve(
        "physical.lithography.source_proton_count",
        assignments={
            "physical.lithography.source_valence_up_quark_count": 1,
            "physical.lithography.source_valence_down_quark_count": 5,
        },
    )
    assert float(invalid_proton_result.value) == pytest.approx(-1.0)
    invalid_proton_feasibility = next(
        c for c in invalid_proton_result.constraints
        if c.equation == proton_feasibility_eq.name
    )
    assert invalid_proton_feasibility.satisfied is False

    zero_proton_result = resolve(
        "physical.lithography.source_proton_count",
        assignments=source_quark_assignments(0, 1),
    )
    assert float(zero_proton_result.value) == pytest.approx(0.0)
    zero_positive_proton_feasibility = next(
        c for c in zero_proton_result.constraints
        if c.equation == positive_proton_feasibility_eq.name
    )
    assert zero_positive_proton_feasibility.satisfied is False

    invalid_neutron_result = resolve(
        "physical.lithography.source_neutron_count",
        assignments={
            "physical.lithography.source_valence_up_quark_count": 5,
            "physical.lithography.source_valence_down_quark_count": 1,
        },
    )
    assert float(invalid_neutron_result.value) == pytest.approx(-1.0)
    invalid_neutron_feasibility = next(
        c for c in invalid_neutron_result.constraints
        if c.equation == neutron_feasibility_eq.name
    )
    assert invalid_neutron_feasibility.satisfied is False

    fractional_triplet_result = resolve(
        "physical.lithography.source_proton_count",
        assignments={
            "physical.lithography.source_valence_up_quark_count": 1,
            "physical.lithography.source_valence_down_quark_count": 1,
        },
    )
    assert float(fractional_triplet_result.value) == pytest.approx(1.0 / 3.0)
    fractional_triplet_constraint = next(
        c for c in fractional_triplet_result.constraints
        if c.equation == triplet_integrality_eq.name
    )
    assert fractional_triplet_constraint.satisfied is False
    fractional_down_root_result = resolve(
        "physical.lithography.source_valence_down_quark_count",
        assignments={
            "physical.lithography.source_valence_up_quark_count": 1,
            "physical.lithography.source_valence_down_quark_count": 1,
        },
    )
    assert float(fractional_down_root_result.value) == pytest.approx(1.0)
    fractional_down_triplet_constraint = next(
        c for c in fractional_down_root_result.constraints
        if c.equation == triplet_integrality_eq.name
    )
    assert fractional_down_triplet_constraint.satisfied is False
    assert [
        c.equation for c in fractional_down_root_result.constraints
    ].count(triplet_integrality_eq.name) == 1

    isotope_descriptor_result = resolve(
        "physical.lithography.source_isotope_mass_number",
        assignments=source_quark_assignments(3, 4),
    )
    assert float(isotope_descriptor_result.value) == pytest.approx(7.0)
    isotope_descriptor_trace = [
        step.equation for step in isotope_descriptor_result.trace
    ]
    assert set(isotope_descriptor_trace[:2]) == {
        "physical.eq.lithography_source_neutron_count_from_valence_quarks",
        "physical.eq.lithography_source_proton_count_from_valence_quarks",
    }
    assert isotope_descriptor_trace[2:] == [
        "physical.eq.lithography_source_isotope_mass_number",
    ]
    assert (
        Registry.equations[
            "physical.eq.lithography_source_isotope_mass_number"
        ].role
        is RelationRole.APPROXIMATION
    )
    atomic_descriptor_result = resolve(
        "physical.lithography.source_atomic_number",
        assignments=source_quark_assignments(3, 0),
    )
    assert float(atomic_descriptor_result.value) == pytest.approx(3.0)
    assert [step.equation for step in atomic_descriptor_result.trace] == [
        "physical.eq.lithography_source_proton_count_from_valence_quarks",
        "physical.eq.lithography_source_atomic_number",
    ]
    assert (
        Registry.equations["physical.eq.lithography_source_atomic_number"].role
        is RelationRole.IDENTITY
    )

    for atomic_number_value, expected_shell in (
        (1, 1),
        (2, 1),
        (3, 2),
        (10, 2),
        (11, 3),
        (28, 3),
        (29, 4),
        (60, 4),
        (61, 5),
        (110, 5),
        (111, 6),
        (182, 6),
        (183, 7),
        (280, 7),
    ):
        lower_shell_result = resolve(
            "physical.lithography.source_lower_principal_quantum_number",
            assignments=source_quark_assignments(atomic_number_value, 0),
        )
        assert float(lower_shell_result.value) == pytest.approx(expected_shell)
    lower_shell_eq = Registry.equations[
        "physical.eq.lithography_source_lower_principal_quantum_number"
    ]
    assert "Z_litho_src > 0" in str(lower_shell_eq.validity)
    assert "Z_litho_src <= 280" in str(lower_shell_eq.validity)

    inner_shielding_eq = Registry.equations[
        "physical.eq.lithography_source_inner_shell_shielding_factor"
    ]
    same_shielding_eq = Registry.equations[
        "physical.eq.lithography_source_same_shell_shielding_factor"
    ]
    assert inner_shielding.approximations() == [inner_shielding_eq]
    assert same_shielding.approximations() == [same_shielding_eq]
    assert inner_shielding_eq.role is RelationRole.APPROXIMATION
    assert same_shielding_eq.role is RelationRole.APPROXIMATION
    assert inner_shielding_eq.rhs == sp.Integer(1)
    assert same_shielding_eq.rhs == sp.Rational(1, 2)

    upper_shell_result = resolve(
        "physical.lithography.source_upper_principal_quantum_number",
        assignments=source_quark_assignments(8, 0),
    )
    assert float(upper_shell_result.value) == pytest.approx(3.0)

    ionization_screening_result = resolve(
        "physical.lithography.source_ionization_screening_constant",
        assignments=source_quark_assignments(4, 0),
    )
    assert float(ionization_screening_result.value) == pytest.approx(2.5)
    assert float(ionization_screening_result.values[
        "physical.lithography.source_ionization_inner_shell_screening_electron_count"
    ]) == pytest.approx(2.0)
    assert float(ionization_screening_result.values[
        "physical.lithography.source_ionization_same_shell_screening_electron_count"
    ]) == pytest.approx(1.0)
    ionization_screening_trace = {
        step.equation for step in ionization_screening_result.trace
    }
    assert "physical.eq.lithography_source_saha_ionization_ratio" not in ionization_screening_trace
    assert "physical.eq.lithography_source_ion_charge_state" not in ionization_screening_trace
