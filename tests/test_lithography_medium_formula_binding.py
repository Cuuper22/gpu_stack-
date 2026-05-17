"""Nuclear binding coverage for the lithography medium formula unit."""

import pytest

from gpu_stack import resolve
from tests.helpers.lithography_medium_formula import (
    dependency_names,
    medium_formula_case,
    medium_formula_variables,
)


def test_lithography_medium_formula_unit_binding_dependencies():
    variables = medium_formula_variables()
    medium_radius_coeff = variables["medium_radius_coeff"]
    medium_saturation_density = variables["medium_saturation_density"]
    medium_bulk_binding_density = variables["medium_bulk_binding_density"]
    medium_surface_tension = variables["medium_surface_tension"]
    medium_symmetry_density = variables["medium_symmetry_density"]
    medium_volume_coeff = variables["medium_volume_coeff"]
    medium_surface_coeff = variables["medium_surface_coeff"]
    medium_asymmetry_coeff = variables["medium_asymmetry_coeff"]
    medium_pairing_gap = variables["medium_pairing_gap"]
    medium_coulomb_coeff = variables["medium_coulomb_coeff"]
    component_a_binding = variables["component_a_binding"]
    component_b_binding = variables["component_b_binding"]
    binding_energy = variables["binding_energy"]

    assert dependency_names(medium_radius_coeff) == {
        "physical.lithography.medium_component_binding_coulomb_coefficient",
        "physics.elementary_charge",
        "physics.vacuum_permittivity",
    }
    assert dependency_names(medium_saturation_density) == {
        "physical.lithography.medium_component_nuclear_radius_coefficient",
    }
    assert dependency_names(medium_bulk_binding_density) == {
        "physical.lithography.medium_component_binding_volume_coefficient",
        "physical.lithography.medium_component_nuclear_saturation_number_density",
    }
    assert dependency_names(medium_surface_tension) == {
        "physical.lithography.medium_component_binding_surface_coefficient",
        "physical.lithography.medium_component_nuclear_radius_coefficient",
    }
    assert dependency_names(medium_symmetry_density) == {
        "physical.lithography.medium_component_binding_asymmetry_coefficient",
        "physical.lithography.medium_component_nuclear_saturation_number_density",
    }
    assert dependency_names(medium_volume_coeff) == {
        "physical.lithography.nuclear_binding_volume_coefficient",
    }
    assert dependency_names(medium_surface_coeff) == {
        "physical.lithography.nuclear_binding_surface_coefficient",
    }
    assert dependency_names(medium_asymmetry_coeff) == {
        "physical.lithography.nuclear_binding_asymmetry_coefficient",
    }
    assert dependency_names(medium_pairing_gap) == {
        "physical.lithography.nuclear_pairing_gap_reference_energy",
    }
    assert dependency_names(medium_coulomb_coeff) == {
        "physical.lithography.nuclear_binding_coulomb_coefficient",
    }
    assert dependency_names(component_a_binding) == {
        "physical.lithography.medium_component_a_binding_asymmetry_term",
        "physical.lithography.medium_component_a_binding_coulomb_term",
        "physical.lithography.medium_component_a_binding_pairing_term",
        "physical.lithography.medium_component_a_binding_surface_term",
        "physical.lithography.medium_component_a_binding_volume_term",
    }
    assert dependency_names(component_b_binding) == {
        "physical.lithography.medium_component_b_binding_asymmetry_term",
        "physical.lithography.medium_component_b_binding_coulomb_term",
        "physical.lithography.medium_component_b_binding_pairing_term",
        "physical.lithography.medium_component_b_binding_surface_term",
        "physical.lithography.medium_component_b_binding_volume_term",
    }
    assert dependency_names(binding_energy) == {
        "physical.lithography.medium_component_a_binding_energy",
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_component_b_binding_energy",
        "physical.lithography.medium_component_b_stoichiometric_count",
        "physical.lithography.medium_formula_unit_intercomponent_binding_energy",
    }


def test_lithography_medium_formula_unit_binding_energy_resolves(
    medium_formula_case,
):
    component_a_binding_result = resolve(
        "physical.lithography.medium_component_a_binding_energy",
        assignments=medium_formula_case.assignments,
    )
    assert float(component_a_binding_result.value) == pytest.approx(
        medium_formula_case.component_a_expected_binding
    )
    component_b_binding_result = resolve(
        "physical.lithography.medium_component_b_binding_energy",
        assignments=medium_formula_case.assignments,
    )
    assert float(component_b_binding_result.value) == pytest.approx(
        medium_formula_case.component_b_expected_binding
    )
    binding_result = resolve(
        "physical.lithography.medium_formula_unit_binding_energy",
        assignments=medium_formula_case.assignments,
    )
    assert float(binding_result.value) == pytest.approx(
        medium_formula_case.expected_binding_energy
    )
