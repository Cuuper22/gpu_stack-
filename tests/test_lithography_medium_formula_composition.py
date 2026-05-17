"""Formula-unit composition and electron-count coverage."""

import pytest

from gpu_stack import resolve
from tests.helpers.lithography_medium_formula import (
    dependency_names,
    medium_formula_case,
    medium_formula_variables,
)


def test_lithography_medium_formula_unit_composition_dependencies():
    variables = medium_formula_variables()
    component_a_protons = variables["component_a_protons"]
    component_b_protons = variables["component_b_protons"]
    component_a_neutrons = variables["component_a_neutrons"]
    component_b_neutrons = variables["component_b_neutrons"]
    component_a_atomic_number = variables["component_a_atomic_number"]
    component_b_atomic_number = variables["component_b_atomic_number"]
    component_a_mass_number = variables["component_a_mass_number"]
    component_b_mass_number = variables["component_b_mass_number"]
    proton_count = variables["proton_count"]
    neutron_count = variables["neutron_count"]
    electron_count = variables["electron_count"]

    assert dependency_names(component_a_protons) == {
        "physical.lithography.medium_component_a_valence_down_quark_count",
        "physical.lithography.medium_component_a_valence_up_quark_count",
    }
    assert dependency_names(component_a_neutrons) == {
        "physical.lithography.medium_component_a_valence_down_quark_count",
        "physical.lithography.medium_component_a_valence_up_quark_count",
    }
    assert dependency_names(component_b_protons) == {
        "physical.lithography.medium_component_b_valence_down_quark_count",
        "physical.lithography.medium_component_b_valence_up_quark_count",
    }
    assert dependency_names(component_b_neutrons) == {
        "physical.lithography.medium_component_b_valence_down_quark_count",
        "physical.lithography.medium_component_b_valence_up_quark_count",
    }
    assert dependency_names(component_a_atomic_number) == {
        "physical.lithography.medium_component_a_proton_count",
    }
    assert dependency_names(component_b_atomic_number) == {
        "physical.lithography.medium_component_b_proton_count",
    }
    assert dependency_names(component_a_mass_number) == {
        "physical.lithography.medium_component_a_neutron_count",
        "physical.lithography.medium_component_a_proton_count",
    }
    assert dependency_names(component_b_mass_number) == {
        "physical.lithography.medium_component_b_neutron_count",
        "physical.lithography.medium_component_b_proton_count",
    }
    assert dependency_names(proton_count) == {
        "physical.lithography.medium_component_a_proton_count",
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_component_b_proton_count",
        "physical.lithography.medium_component_b_stoichiometric_count",
    }
    assert dependency_names(neutron_count) == {
        "physical.lithography.medium_component_a_neutron_count",
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_component_b_neutron_count",
        "physical.lithography.medium_component_b_stoichiometric_count",
    }
    assert dependency_names(electron_count) == {
        "physical.lithography.medium_formula_unit_proton_count",
    }


def test_lithography_medium_formula_unit_composition_resolves_expected_counts(
    medium_formula_case,
):
    component_b_proton_result = resolve(
        "physical.lithography.medium_component_b_proton_count",
        assignments=medium_formula_case.assignments,
    )
    assert float(component_b_proton_result.value) == pytest.approx(8.0)
    component_b_neutron_result = resolve(
        "physical.lithography.medium_component_b_neutron_count",
        assignments=medium_formula_case.assignments,
    )
    assert float(component_b_neutron_result.value) == pytest.approx(9.0)

    proton_result = resolve(
        "physical.lithography.medium_formula_unit_proton_count",
        assignments=medium_formula_case.assignments,
    )
    assert float(proton_result.value) == pytest.approx(10.0)
    neutron_result = resolve(
        "physical.lithography.medium_formula_unit_neutron_count",
        assignments=medium_formula_case.assignments,
    )
    assert float(neutron_result.value) == pytest.approx(9.0)
    component_a_atomic_result = resolve(
        "physical.lithography.medium_component_a_atomic_number",
        assignments=medium_formula_case.assignments,
    )
    assert float(component_a_atomic_result.value) == pytest.approx(1.0)
    component_b_atomic_result = resolve(
        "physical.lithography.medium_component_b_atomic_number",
        assignments=medium_formula_case.assignments,
    )
    assert float(component_b_atomic_result.value) == pytest.approx(8.0)
    component_a_mass_number_result = resolve(
        "physical.lithography.medium_component_a_isotope_mass_number",
        assignments=medium_formula_case.assignments,
    )
    assert float(component_a_mass_number_result.value) == pytest.approx(1.0)
    component_b_mass_number_result = resolve(
        "physical.lithography.medium_component_b_isotope_mass_number",
        assignments=medium_formula_case.assignments,
    )
    assert float(component_b_mass_number_result.value) == pytest.approx(17.0)

    electron_result = resolve(
        "physical.lithography.medium_formula_unit_electron_count",
        assignments=medium_formula_case.assignments,
    )
    assert float(electron_result.value) == pytest.approx(10.0)
