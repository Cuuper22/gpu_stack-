"""Resolving the source's shell and valence chain, value by value.

This module exercises the electronic-structure side of the quantum source
model with concrete inputs. Quark counts follow the U = 2Z + N, D = Z + 2N
identities (Z=3, N=4 gives 10 up and 11 down), the isotope mass number is
Z + N, and a zero proton count trips the positivity constraint exactly
once. The lower principal quantum number — which shell the transition's
lower level lives in — is checked against a table of atomic numbers at
every shell boundary (Z=2 is still shell 1, Z=3 opens shell 2, and so on up
to Z=280 in shell 7), and its declared validity window 0 < Z <= 280 is
confirmed. The two shielding-factor conventions are pinned to their
constant values (inner shells screen fully, rhs = 1; same-shell electrons
screen half, rhs = 1/2), and the ionization screening constant for Z=4
resolves to 2.5 = 2*1 + 1*(1/2) without ever pulling the Saha ionization
equations into the trace.
"""

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

    up_quark_result = resolve(
        "physical.lithography.source_valence_up_quark_count",
        assignments=source_quark_assignments(3, 4),
    )
    assert float(up_quark_result.value) == pytest.approx(10.0)
    assert [step.equation for step in up_quark_result.trace] == [
        "physical.eq.lithography_source_valence_up_quark_count_from_zn",
    ]
    positive_proton_eq = Registry.equations[
        "physical.ineq.lithography_source_proton_count_positive"
    ]
    assert isinstance(positive_proton_eq, Inequality)
    assert positive_proton_eq.role is RelationRole.CONSTRAINT
    assert isinstance(positive_proton_eq.as_sympy(), sp.Rel)
    assert not positive_proton_eq.is_trivially_true()
    assert positive_proton_eq.references
    assert getattr(positive_proton_eq, "_check_units_flag", False)
    positive_proton = next(
        c for c in up_quark_result.constraints
        if c.equation == positive_proton_eq.name
    )
    assert positive_proton.satisfied is True
    down_quark_result = resolve(
        "physical.lithography.source_valence_down_quark_count",
        assignments=source_quark_assignments(3, 4),
    )
    assert float(down_quark_result.value) == pytest.approx(11.0)
    assert [step.equation for step in down_quark_result.trace] == [
        "physical.eq.lithography_source_valence_down_quark_count_from_zn",
    ]

    zero_proton_result = resolve(
        "physical.lithography.source_valence_up_quark_count",
        assignments=source_quark_assignments(0, 1),
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

    isotope_descriptor_result = resolve(
        "physical.lithography.source_isotope_mass_number",
        assignments=source_quark_assignments(3, 4),
    )
    assert float(isotope_descriptor_result.value) == pytest.approx(7.0)
    assert [step.equation for step in isotope_descriptor_result.trace] == [
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
