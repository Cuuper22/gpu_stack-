"""Intercomponent and Lorentz-Lorenz medium formula-unit coverage."""

import pytest

from gpu_stack import resolve
from tests.helpers.lithography_medium_formula import (
    dependency_names,
    medium_formula_case,
    medium_formula_variables,
)


def test_lithography_medium_formula_unit_intercomponent_dependencies():
    variables = medium_formula_variables()
    component_a_intercomponent_charge = variables["component_a_intercomponent_charge"]
    component_b_intercomponent_charge = variables["component_b_intercomponent_charge"]
    intercomponent_charge_unit = variables["intercomponent_charge_unit"]
    intercomponent_charge_transfer_count = variables[
        "intercomponent_charge_transfer_count"
    ]
    intercomponent_pair_count = variables["intercomponent_pair_count"]
    intercomponent_separation = variables["intercomponent_separation"]
    component_a_intercomponent_radius_scale = variables[
        "component_a_intercomponent_radius_scale"
    ]
    component_b_intercomponent_radius_scale = variables[
        "component_b_intercomponent_radius_scale"
    ]
    component_a_intercomponent_radius = variables[
        "component_a_intercomponent_radius"
    ]
    component_b_intercomponent_radius = variables[
        "component_b_intercomponent_radius"
    ]
    intercomponent_gap_fraction = variables["intercomponent_gap_fraction"]
    intercomponent_gap = variables["intercomponent_gap"]
    intercomponent_polarizable_site_density_factor = variables[
        "intercomponent_polarizable_site_density_factor"
    ]
    intercomponent_lorentz_lorenz_factor = variables[
        "intercomponent_lorentz_lorenz_factor"
    ]
    intercomponent_relative_permittivity = variables[
        "intercomponent_relative_permittivity"
    ]
    intercomponent_binding = variables["intercomponent_binding"]

    assert dependency_names(component_a_intercomponent_charge) == {
        "physical.lithography.medium_component_b_stoichiometric_count",
        "physical.lithography.medium_intercomponent_charge_unit",
    }
    assert dependency_names(component_b_intercomponent_charge) == {
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_intercomponent_charge_unit",
    }
    assert dependency_names(intercomponent_charge_unit) == {
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_component_b_stoichiometric_count",
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count",
    }
    assert dependency_names(intercomponent_charge_transfer_count) == set()
    assert dependency_names(
        intercomponent_charge_transfer_count,
        include_constraints=True,
    ) == {
        "physical.lithography.medium_component_a_proton_count",
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_component_b_proton_count",
        "physical.lithography.medium_component_b_stoichiometric_count",
    }
    assert dependency_names(intercomponent_pair_count) == {
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_component_b_stoichiometric_count",
    }
    assert dependency_names(intercomponent_separation) == {
        "physical.lithography.medium_component_a_effective_intercomponent_radius",
        "physical.lithography.medium_component_b_effective_intercomponent_radius",
        "physical.lithography.medium_intercomponent_gap",
    }
    assert dependency_names(component_a_intercomponent_radius_scale) == set()
    assert dependency_names(component_b_intercomponent_radius_scale) == set()
    assert dependency_names(component_a_intercomponent_radius) == {
        "physical.lithography.medium_component_a_intercomponent_radius_scale_factor",
        "physical.lithography.medium_component_a_isotope_mass_number",
        "physical.lithography.medium_component_nuclear_radius_coefficient",
    }
    assert dependency_names(component_b_intercomponent_radius) == {
        "physical.lithography.medium_component_b_intercomponent_radius_scale_factor",
        "physical.lithography.medium_component_b_isotope_mass_number",
        "physical.lithography.medium_component_nuclear_radius_coefficient",
    }
    assert dependency_names(intercomponent_gap_fraction) == set()
    assert dependency_names(intercomponent_gap) == {
        "physical.lithography.medium_component_a_effective_intercomponent_radius",
        "physical.lithography.medium_component_b_effective_intercomponent_radius",
        "physical.lithography.medium_intercomponent_gap_fraction",
    }
    assert dependency_names(intercomponent_polarizable_site_density_factor) == set()
    assert dependency_names(intercomponent_lorentz_lorenz_factor) == {
        "physical.lithography.medium_electric_polarizability",
        "physical.lithography.medium_intercomponent_effective_separation",
        "physical.lithography.medium_intercomponent_polarizable_site_density_factor",
        "physics.vacuum_permittivity",
    }
    assert dependency_names(intercomponent_relative_permittivity) == {
        "physical.lithography.medium_intercomponent_lorentz_lorenz_factor",
    }
    assert dependency_names(intercomponent_binding) == {
        "physical.lithography.medium_component_a_effective_intercomponent_charge_number",
        "physical.lithography.medium_component_b_effective_intercomponent_charge_number",
        "physical.lithography.medium_formula_unit_intercomponent_pair_count",
        "physical.lithography.medium_intercomponent_effective_separation",
        "physical.lithography.medium_intercomponent_relative_permittivity",
        "physics.elementary_charge",
        "physics.vacuum_permittivity",
    }


def test_lithography_medium_formula_unit_intercomponent_semantics_resolve(
    medium_formula_case,
):
    intercomponent_charge_unit_result = resolve(
        "physical.lithography.medium_intercomponent_charge_unit",
        assignments=medium_formula_case.assignments,
    )
    assert float(intercomponent_charge_unit_result.value) == pytest.approx(
        medium_formula_case.expected_intercomponent_charge_unit
    )
    component_a_intercomponent_charge_result = resolve(
        "physical.lithography.medium_component_a_effective_intercomponent_charge_number",
        assignments=medium_formula_case.assignments,
    )
    assert float(component_a_intercomponent_charge_result.value) == pytest.approx(
        medium_formula_case.expected_component_a_intercomponent_charge
    )
    component_b_intercomponent_charge_result = resolve(
        "physical.lithography.medium_component_b_effective_intercomponent_charge_number",
        assignments=medium_formula_case.assignments,
    )
    assert float(component_b_intercomponent_charge_result.value) == pytest.approx(
        medium_formula_case.expected_component_b_intercomponent_charge
    )
    intercomponent_pair_count_result = resolve(
        "physical.lithography.medium_formula_unit_intercomponent_pair_count",
        assignments=medium_formula_case.assignments,
    )
    assert float(intercomponent_pair_count_result.value) == pytest.approx(
        medium_formula_case.expected_intercomponent_pair_count
    )
    component_a_intercomponent_radius_result = resolve(
        "physical.lithography.medium_component_a_effective_intercomponent_radius",
        assignments=medium_formula_case.assignments,
    )
    assert float(component_a_intercomponent_radius_result.value) == pytest.approx(
        medium_formula_case.component_a_intercomponent_test_radius
    )
    component_b_intercomponent_radius_result = resolve(
        "physical.lithography.medium_component_b_effective_intercomponent_radius",
        assignments=medium_formula_case.assignments,
    )
    assert float(component_b_intercomponent_radius_result.value) == pytest.approx(
        medium_formula_case.component_b_intercomponent_test_radius
    )
    intercomponent_gap_result = resolve(
        "physical.lithography.medium_intercomponent_gap",
        assignments=medium_formula_case.assignments,
    )
    assert float(intercomponent_gap_result.value) == pytest.approx(
        medium_formula_case.intercomponent_test_gap
    )
    intercomponent_separation_result = resolve(
        "physical.lithography.medium_intercomponent_effective_separation",
        assignments=medium_formula_case.assignments,
    )
    assert float(intercomponent_separation_result.value) == pytest.approx(
        medium_formula_case.intercomponent_test_separation
    )
    intercomponent_lorentz_lorenz_result = resolve(
        "physical.lithography.medium_intercomponent_lorentz_lorenz_factor",
        assignments=medium_formula_case.assignments,
    )
    assert float(intercomponent_lorentz_lorenz_result.value) == pytest.approx(0.0)
    intercomponent_relative_permittivity_result = resolve(
        "physical.lithography.medium_intercomponent_relative_permittivity",
        assignments=medium_formula_case.assignments,
    )
    assert float(intercomponent_relative_permittivity_result.value) == pytest.approx(
        1.0
    )
    intercomponent_binding_result = resolve(
        "physical.lithography.medium_formula_unit_intercomponent_binding_energy",
        assignments=medium_formula_case.assignments,
    )
    assert float(intercomponent_binding_result.value) == pytest.approx(
        medium_formula_case.expected_intercomponent_binding
    )
