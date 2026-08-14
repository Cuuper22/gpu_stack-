"""From particle counts to a bulk density for the imaging medium.

The rest mass of one formula unit is the sum of its proton, neutron, and
electron masses minus the mass equivalent of its binding energy (E/c^2 —
bound systems weigh less than their parts). Multiply by Avogadro's number to
get molar mass; divide back to get the per-particle mass. Bulk density then
comes from packing: each formula unit claims a cube whose edge is the
intercomponent separation times a scale factor, and only a fill fraction of
that cube is actually occupied. This module checks the dependency wiring of
that whole chain, verifies the numbers on a reference case (for example a
0.25 separation with scale factor 2 gives a 0.125 packing volume), and
confirms the two packing constraints fire: a scale factor below 1 and a fill
factor above 1 are both reported as violated.
"""

import pytest

from gpu_stack import resolve
from tests.helpers.lithography_medium_formula import (
    dependency_names,
    medium_formula_case,
    medium_formula_variables,
)


def test_lithography_medium_molar_mass_has_formula_unit_model(
    medium_formula_case,
):
    variables = medium_formula_variables()
    formula_mass = variables["formula_mass"]
    molar_mass = variables["molar_mass"]
    particle_mass = variables["particle_mass"]

    assert dependency_names(formula_mass) == {
        "physical.lithography.medium_formula_unit_proton_count",
        "physical.lithography.medium_formula_unit_neutron_count",
        "physical.lithography.medium_formula_unit_electron_count",
        "physical.lithography.medium_formula_unit_binding_energy",
        "physics.proton_mass",
        "physics.neutron_mass",
        "physics.electron_mass",
        "physics.speed_of_light",
    }
    assert dependency_names(molar_mass) == {
        "physical.lithography.medium_formula_unit_rest_mass",
        "physics.avogadro",
    }
    assert dependency_names(particle_mass) == {
        "physical.lithography.medium_molar_mass",
        "physics.avogadro",
    }

    formula_result = resolve(
        "physical.lithography.medium_formula_unit_rest_mass",
        assignments=medium_formula_case.assignments,
    )
    assert float(formula_result.value) == pytest.approx(
        medium_formula_case.expected_formula_mass
    )

    molar_result = resolve(
        "physical.lithography.medium_molar_mass",
        assignments=medium_formula_case.assignments,
    )
    assert float(molar_result.value) == pytest.approx(
        medium_formula_case.avogadro * medium_formula_case.expected_formula_mass
    )

    particle_result = resolve(
        "physical.lithography.medium_particle_mass",
        assignments=medium_formula_case.assignments,
    )
    assert float(particle_result.value) == pytest.approx(
        medium_formula_case.expected_formula_mass
    )


def test_lithography_medium_formula_unit_density_constraints_resolve(
    medium_formula_case,
):
    variables = medium_formula_variables()
    packing_length_scale_factor = variables["packing_length_scale_factor"]
    packing_length = variables["packing_length"]
    packing_fill_factor = variables["packing_fill_factor"]
    packing_volume = variables["packing_volume"]
    mass_density = variables["mass_density"]
    number_density = variables["number_density"]

    assert dependency_names(packing_length_scale_factor) == set()
    assert dependency_names(packing_length) == {
        "physical.lithography.medium_intercomponent_effective_separation",
        "physical.lithography.medium_formula_unit_packing_length_scale_factor",
    }
    assert dependency_names(packing_fill_factor) == set()
    assert dependency_names(packing_volume) == {
        "physical.lithography.medium_formula_unit_packing_length",
    }
    assert dependency_names(mass_density) == {
        "physical.lithography.medium_formula_unit_packing_fill_factor",
        "physical.lithography.medium_formula_unit_packing_volume",
        "physical.lithography.medium_particle_mass",
    }
    assert dependency_names(number_density) == {
        "physical.lithography.medium_mass_density",
        "physical.lithography.medium_particle_mass",
    }

    packing_volume_result = resolve(
        "physical.lithography.medium_formula_unit_packing_volume",
        assignments={
            "physical.lithography.medium_formula_unit_packing_length_scale_factor": 2.0,
            "physical.lithography.medium_intercomponent_effective_separation": 0.25,
        },
    )
    assert float(packing_volume_result.value) == pytest.approx(0.125)

    mass_density_result = resolve(
        "physical.lithography.medium_mass_density",
        assignments={
            **medium_formula_case.assignments,
            "physical.lithography.medium_formula_unit_packing_length_scale_factor": (
                medium_formula_case.packing_length_scale_factor_test
            ),
            "physical.lithography.medium_formula_unit_packing_fill_factor": 0.625,
        },
    )
    assert float(mass_density_result.value) == pytest.approx(
        5.0 * medium_formula_case.expected_formula_mass
    )
    valid_packing_length_constraint = next(
        c for c in mass_density_result.constraints
        if c.equation
        == "physical.ineq.lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity"
    )
    assert valid_packing_length_constraint.satisfied is True

    undersized_packing_mass_density_result = resolve(
        "physical.lithography.medium_mass_density",
        assignments={
            **medium_formula_case.assignments,
            "physical.lithography.medium_formula_unit_packing_length_scale_factor": 0.5,
            "physical.lithography.medium_formula_unit_packing_fill_factor": 0.625,
        },
    )
    undersized_packing_constraint = next(
        c for c in undersized_packing_mass_density_result.constraints
        if c.equation
        == "physical.ineq.lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity"
    )
    assert undersized_packing_constraint.satisfied is False

    overpacked_mass_density_result = resolve(
        "physical.lithography.medium_mass_density",
        assignments={
            **medium_formula_case.assignments,
            "physical.lithography.medium_formula_unit_packing_length_scale_factor": (
                medium_formula_case.packing_length_scale_factor_test
            ),
            "physical.lithography.medium_formula_unit_packing_fill_factor": 1.25,
        },
    )
    overpacked_constraint = next(
        c for c in overpacked_mass_density_result.constraints
        if c.equation
        == "physical.ineq.lithography_medium_formula_unit_packing_fill_factor_at_most_unity"
    )
    assert overpacked_constraint.satisfied is False

    density_result = resolve(
        "physical.lithography.medium_number_density",
        assignments={
            **medium_formula_case.assignments,
            "physical.lithography.medium_formula_unit_packing_length_scale_factor": (
                medium_formula_case.packing_length_scale_factor_test
            ),
            "physical.lithography.medium_formula_unit_packing_fill_factor": 0.625,
        },
    )
    assert float(density_result.value) == pytest.approx(5.0)
