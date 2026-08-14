"""Guard rails on the source's nuclear mass, reduced mass, and their ratio.

The reduced mass is the effective mass of the electron-nucleus two-body
system, m_e*M / (m_e + M); the transition energies downstream scale with
its ratio to the bare electron mass. All three quantities — nuclear mass,
reduced mass, and the ratio — must be positive, and this module verifies
those positivity rules are explicit named Inequality constraints with
references (unit checks are deliberately off here, since both sides are
plain masses). It then constructs the pathological cases: a binding energy
of 2*m_p*c^2 drives the nuclear mass of a lone proton to exactly -m_p; a
nuclear mass of -m_e makes the reduced-mass denominator vanish, so the
value is SymPy's complex infinity (zoo) and both mass constraints fail; and
a negative reduced mass yields a ratio of -1 with both downstream
constraints flagged. In every case the violation is reported, never
swallowed.
"""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.core import Inequality, RelationRole
from tests.helpers.lithography import failed_constraint


def test_lithography_source_reduced_mass_constraints_are_explicit():
    expected = {
        "physical.ineq.lithography_source_nuclear_mass_positive": (
            "physical.lithography.source_nuclear_mass"
        ),
        "physical.ineq.lithography_source_reduced_mass_positive": (
            "physical.lithography.source_reduced_mass"
        ),
        "physical.ineq.lithography_source_reduced_mass_ratio_positive": (
            "physical.lithography.source_reduced_mass_ratio"
        ),
    }

    for equation_name, variable_name in expected.items():
        eq = Registry.equations[equation_name]
        assert isinstance(eq, Inequality)
        assert eq.role is RelationRole.CONSTRAINT
        assert eq in Registry.variables[variable_name].constraints()
        assert eq.references
        assert not getattr(eq, "_check_units_flag", False)
        relation = eq.as_sympy()
        assert relation is not sp.S.true
        assert isinstance(relation, sp.Rel)


def test_lithography_source_reduced_mass_constraints_report_invalid_masses():
    electron_mass = Registry.variables["physics.electron_mass"].value
    proton_mass = Registry.variables["physics.proton_mass"].value
    speed_of_light = Registry.variables["physics.speed_of_light"].value

    negative_nuclear_mass = resolve(
        "physical.lithography.source_nuclear_mass",
        assignments={
            "physical.lithography.source_proton_count": 1.0,
            "physical.lithography.source_neutron_count": 0.0,
            "physical.lithography.source_nuclear_binding_energy": (
                2.0 * proton_mass * speed_of_light**2
            ),
        },
    )
    assert float(negative_nuclear_mass.value) == pytest.approx(-proton_mass)
    failed_constraint(
        negative_nuclear_mass,
        "physical.ineq.lithography_source_nuclear_mass_positive",
    )

    singular_reduced_mass = resolve(
        "physical.lithography.source_reduced_mass",
        assignments={
            "physical.lithography.source_nuclear_mass": -electron_mass,
        },
    )
    assert singular_reduced_mass.value is sp.zoo
    failed_constraint(
        singular_reduced_mass,
        "physical.ineq.lithography_source_nuclear_mass_positive",
    )
    failed_constraint(
        singular_reduced_mass,
        "physical.ineq.lithography_source_reduced_mass_positive",
    )

    negative_reduced_mass_ratio = resolve(
        "physical.lithography.source_reduced_mass_ratio",
        assignments={
            "physical.lithography.source_reduced_mass": -electron_mass,
        },
    )
    assert float(negative_reduced_mass_ratio.value) == pytest.approx(-1.0)
    failed_constraint(
        negative_reduced_mass_ratio,
        "physical.ineq.lithography_source_reduced_mass_positive",
    )
    failed_constraint(
        negative_reduced_mass_ratio,
        "physical.ineq.lithography_source_reduced_mass_ratio_positive",
    )
