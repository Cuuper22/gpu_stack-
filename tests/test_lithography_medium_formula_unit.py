"""Lithography medium formula-unit model coverage."""

import pytest
import sympy as sp

from gpu_stack import Registry, RelationRole, resolve
from tests.helpers.lithography import (
    expected_medium_component_binding_energy,
    medium_component_quark_assignments,
    medium_liquid_drop_root_assignments,
)


def test_lithography_medium_molar_mass_has_formula_unit_model():
    component_a_stoich = Registry.variables[
        "physical.lithography.medium_component_a_stoichiometric_count"
    ]
    component_b_stoich = Registry.variables[
        "physical.lithography.medium_component_b_stoichiometric_count"
    ]
    component_a_up_quarks = Registry.variables[
        "physical.lithography.medium_component_a_valence_up_quark_count"
    ]
    component_a_down_quarks = Registry.variables[
        "physical.lithography.medium_component_a_valence_down_quark_count"
    ]
    component_b_up_quarks = Registry.variables[
        "physical.lithography.medium_component_b_valence_up_quark_count"
    ]
    component_b_down_quarks = Registry.variables[
        "physical.lithography.medium_component_b_valence_down_quark_count"
    ]
    component_a_protons = Registry.variables[
        "physical.lithography.medium_component_a_proton_count"
    ]
    component_b_protons = Registry.variables[
        "physical.lithography.medium_component_b_proton_count"
    ]
    component_a_neutrons = Registry.variables[
        "physical.lithography.medium_component_a_neutron_count"
    ]
    component_b_neutrons = Registry.variables[
        "physical.lithography.medium_component_b_neutron_count"
    ]
    component_a_atomic_number = Registry.variables[
        "physical.lithography.medium_component_a_atomic_number"
    ]
    component_b_atomic_number = Registry.variables[
        "physical.lithography.medium_component_b_atomic_number"
    ]
    component_a_mass_number = Registry.variables[
        "physical.lithography.medium_component_a_isotope_mass_number"
    ]
    component_b_mass_number = Registry.variables[
        "physical.lithography.medium_component_b_isotope_mass_number"
    ]
    component_a_binding = Registry.variables[
        "physical.lithography.medium_component_a_binding_energy"
    ]
    component_b_binding = Registry.variables[
        "physical.lithography.medium_component_b_binding_energy"
    ]
    medium_saturation_density = Registry.variables[
        "physical.lithography.medium_component_nuclear_saturation_number_density"
    ]
    medium_radius_coeff = Registry.variables[
        "physical.lithography.medium_component_nuclear_radius_coefficient"
    ]
    medium_bulk_binding_density = Registry.variables[
        "physical.lithography.medium_component_nuclear_bulk_binding_energy_density"
    ]
    medium_volume_coeff = Registry.variables[
        "physical.lithography.medium_component_binding_volume_coefficient"
    ]
    medium_surface_tension = Registry.variables[
        "physical.lithography.medium_component_nuclear_surface_tension"
    ]
    medium_surface_coeff = Registry.variables[
        "physical.lithography.medium_component_binding_surface_coefficient"
    ]
    medium_symmetry_density = Registry.variables[
        "physical.lithography.medium_component_nuclear_symmetry_energy_density"
    ]
    medium_asymmetry_coeff = Registry.variables[
        "physical.lithography.medium_component_binding_asymmetry_coefficient"
    ]
    medium_pairing_gap = Registry.variables[
        "physical.lithography.medium_component_nuclear_pairing_gap_reference_energy"
    ]
    medium_coulomb_coeff = Registry.variables[
        "physical.lithography.medium_component_binding_coulomb_coefficient"
    ]
    shared_volume_coeff = Registry.variables[
        "physical.lithography.nuclear_binding_volume_coefficient"
    ]
    shared_surface_coeff = Registry.variables[
        "physical.lithography.nuclear_binding_surface_coefficient"
    ]
    shared_coulomb_coeff = Registry.variables[
        "physical.lithography.nuclear_binding_coulomb_coefficient"
    ]
    shared_asymmetry_coeff = Registry.variables[
        "physical.lithography.nuclear_binding_asymmetry_coefficient"
    ]
    shared_pairing_gap = Registry.variables[
        "physical.lithography.nuclear_pairing_gap_reference_energy"
    ]
    component_a_intercomponent_charge = Registry.variables[
        "physical.lithography.medium_component_a_effective_intercomponent_charge_number"
    ]
    component_b_intercomponent_charge = Registry.variables[
        "physical.lithography.medium_component_b_effective_intercomponent_charge_number"
    ]
    intercomponent_charge_unit = Registry.variables[
        "physical.lithography.medium_intercomponent_charge_unit"
    ]
    intercomponent_charge_transfer_count = Registry.variables[
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count"
    ]
    intercomponent_pair_count = Registry.variables[
        "physical.lithography.medium_formula_unit_intercomponent_pair_count"
    ]
    intercomponent_separation = Registry.variables[
        "physical.lithography.medium_intercomponent_effective_separation"
    ]
    component_a_intercomponent_radius_scale = Registry.variables[
        "physical.lithography.medium_component_a_intercomponent_radius_scale_factor"
    ]
    component_b_intercomponent_radius_scale = Registry.variables[
        "physical.lithography.medium_component_b_intercomponent_radius_scale_factor"
    ]
    component_a_intercomponent_radius = Registry.variables[
        "physical.lithography.medium_component_a_effective_intercomponent_radius"
    ]
    component_b_intercomponent_radius = Registry.variables[
        "physical.lithography.medium_component_b_effective_intercomponent_radius"
    ]
    intercomponent_gap_fraction = Registry.variables[
        "physical.lithography.medium_intercomponent_gap_fraction"
    ]
    intercomponent_gap = Registry.variables[
        "physical.lithography.medium_intercomponent_gap"
    ]
    intercomponent_relative_permittivity = Registry.variables[
        "physical.lithography.medium_intercomponent_relative_permittivity"
    ]
    intercomponent_polarizable_site_density_factor = Registry.variables[
        "physical.lithography.medium_intercomponent_polarizable_site_density_factor"
    ]
    intercomponent_lorentz_lorenz_factor = Registry.variables[
        "physical.lithography.medium_intercomponent_lorentz_lorenz_factor"
    ]
    intercomponent_binding = Registry.variables[
        "physical.lithography.medium_formula_unit_intercomponent_binding_energy"
    ]
    proton_count = Registry.variables[
        "physical.lithography.medium_formula_unit_proton_count"
    ]
    neutron_count = Registry.variables[
        "physical.lithography.medium_formula_unit_neutron_count"
    ]
    electron_count = Registry.variables[
        "physical.lithography.medium_formula_unit_electron_count"
    ]
    binding_energy = Registry.variables[
        "physical.lithography.medium_formula_unit_binding_energy"
    ]
    formula_mass = Registry.variables[
        "physical.lithography.medium_formula_unit_rest_mass"
    ]
    molar_mass = Registry.variables["physical.lithography.medium_molar_mass"]
    particle_mass = Registry.variables["physical.lithography.medium_particle_mass"]
    packing_length = Registry.variables[
        "physical.lithography.medium_formula_unit_packing_length"
    ]
    packing_length_scale_factor = Registry.variables[
        "physical.lithography.medium_formula_unit_packing_length_scale_factor"
    ]
    packing_fill_factor = Registry.variables[
        "physical.lithography.medium_formula_unit_packing_fill_factor"
    ]
    packing_volume = Registry.variables[
        "physical.lithography.medium_formula_unit_packing_volume"
    ]
    mass_density = Registry.variables["physical.lithography.medium_mass_density"]
    number_density = Registry.variables["physical.lithography.medium_number_density"]

    assert component_a_stoich.is_root_input
    assert component_b_stoich.is_root_input
    assert component_a_up_quarks.is_root_input
    assert component_a_down_quarks.is_root_input
    assert component_b_up_quarks.is_root_input
    assert component_b_down_quarks.is_root_input
    assert not component_a_protons.is_root_input
    assert not component_b_protons.is_root_input
    assert not component_a_neutrons.is_root_input
    assert not component_b_neutrons.is_root_input
    assert not component_a_atomic_number.is_root_input
    assert not component_b_atomic_number.is_root_input
    assert not component_a_mass_number.is_root_input
    assert not component_b_mass_number.is_root_input
    assert not medium_saturation_density.is_root_input
    assert not medium_radius_coeff.is_root_input
    assert not medium_bulk_binding_density.is_root_input
    assert shared_volume_coeff.is_root_input
    assert shared_surface_coeff.is_root_input
    assert shared_coulomb_coeff.is_root_input
    assert shared_asymmetry_coeff.is_root_input
    assert shared_pairing_gap.is_root_input
    assert not medium_volume_coeff.is_root_input
    assert not medium_surface_tension.is_root_input
    assert not medium_surface_coeff.is_root_input
    assert not medium_symmetry_density.is_root_input
    assert not medium_asymmetry_coeff.is_root_input
    assert not medium_pairing_gap.is_root_input
    assert not medium_coulomb_coeff.is_root_input
    assert not component_a_binding.is_root_input
    assert not component_b_binding.is_root_input
    assert not component_a_intercomponent_charge.is_root_input
    assert not component_b_intercomponent_charge.is_root_input
    assert intercomponent_charge_transfer_count.is_root_input
    assert not intercomponent_charge_unit.is_root_input
    assert not intercomponent_pair_count.is_root_input
    assert not intercomponent_separation.is_root_input
    assert component_a_intercomponent_radius_scale.is_root_input
    assert component_b_intercomponent_radius_scale.is_root_input
    assert not component_a_intercomponent_radius.is_root_input
    assert not component_b_intercomponent_radius.is_root_input
    assert intercomponent_gap_fraction.is_root_input
    assert not intercomponent_gap.is_root_input
    assert intercomponent_polarizable_site_density_factor.is_root_input
    assert not intercomponent_lorentz_lorenz_factor.is_root_input
    assert not intercomponent_relative_permittivity.is_root_input
    assert not intercomponent_binding.is_root_input
    assert not proton_count.is_root_input
    assert not neutron_count.is_root_input
    assert not electron_count.is_root_input
    assert not binding_energy.is_root_input
    assert not formula_mass.is_root_input
    assert not molar_mass.is_root_input
    assert not particle_mass.is_root_input
    assert packing_length_scale_factor.is_root_input
    assert not packing_length.is_root_input
    assert packing_fill_factor.is_root_input
    assert not packing_volume.is_root_input
    assert not mass_density.is_root_input
    assert not number_density.is_root_input
    assert [eq.name for eq in component_a_stoich.constraints()] == [
        "physical.ineq.lithography_medium_component_a_stoichiometric_count_at_least_one"
    ]
    assert [eq.name for eq in component_b_stoich.constraints()] == [
        "physical.ineq.lithography_medium_component_b_stoichiometric_count_at_least_one"
    ]
    assert [eq.name for eq in packing_length_scale_factor.constraints()] == [
        "physical.ineq.lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity"
    ]
    assert [eq.name for eq in packing_fill_factor.constraints()] == [
        "physical.ineq.lithography_medium_formula_unit_packing_fill_factor_at_most_unity"
    ]

    assert {v.name for v in component_a_protons.direct_dependencies()} == {
        "physical.lithography.medium_component_a_valence_down_quark_count",
        "physical.lithography.medium_component_a_valence_up_quark_count",
    }
    assert {v.name for v in component_a_neutrons.direct_dependencies()} == {
        "physical.lithography.medium_component_a_valence_down_quark_count",
        "physical.lithography.medium_component_a_valence_up_quark_count",
    }
    assert {v.name for v in component_b_protons.direct_dependencies()} == {
        "physical.lithography.medium_component_b_valence_down_quark_count",
        "physical.lithography.medium_component_b_valence_up_quark_count",
    }
    assert {v.name for v in component_b_neutrons.direct_dependencies()} == {
        "physical.lithography.medium_component_b_valence_down_quark_count",
        "physical.lithography.medium_component_b_valence_up_quark_count",
    }
    assert {v.name for v in component_a_atomic_number.direct_dependencies()} == {
        "physical.lithography.medium_component_a_proton_count",
    }
    assert {v.name for v in component_b_atomic_number.direct_dependencies()} == {
        "physical.lithography.medium_component_b_proton_count",
    }
    assert {v.name for v in component_a_mass_number.direct_dependencies()} == {
        "physical.lithography.medium_component_a_neutron_count",
        "physical.lithography.medium_component_a_proton_count",
    }
    assert {v.name for v in component_b_mass_number.direct_dependencies()} == {
        "physical.lithography.medium_component_b_neutron_count",
        "physical.lithography.medium_component_b_proton_count",
    }
    assert {v.name for v in medium_radius_coeff.direct_dependencies()} == {
        "physical.lithography.medium_component_binding_coulomb_coefficient",
        "physics.elementary_charge",
        "physics.vacuum_permittivity",
    }
    assert {v.name for v in medium_saturation_density.direct_dependencies()} == {
        "physical.lithography.medium_component_nuclear_radius_coefficient",
    }
    assert {v.name for v in medium_bulk_binding_density.direct_dependencies()} == {
        "physical.lithography.medium_component_binding_volume_coefficient",
        "physical.lithography.medium_component_nuclear_saturation_number_density",
    }
    assert {v.name for v in medium_surface_tension.direct_dependencies()} == {
        "physical.lithography.medium_component_binding_surface_coefficient",
        "physical.lithography.medium_component_nuclear_radius_coefficient",
    }
    assert {v.name for v in medium_symmetry_density.direct_dependencies()} == {
        "physical.lithography.medium_component_binding_asymmetry_coefficient",
        "physical.lithography.medium_component_nuclear_saturation_number_density",
    }
    assert {v.name for v in medium_volume_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_volume_coefficient",
    }
    assert {v.name for v in medium_surface_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_surface_coefficient",
    }
    assert {v.name for v in medium_asymmetry_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_asymmetry_coefficient",
    }
    assert {v.name for v in medium_pairing_gap.direct_dependencies()} == {
        "physical.lithography.nuclear_pairing_gap_reference_energy",
    }
    assert {v.name for v in medium_coulomb_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_coulomb_coefficient",
    }
    assert {v.name for v in component_a_intercomponent_charge.direct_dependencies()} == {
        "physical.lithography.medium_component_b_stoichiometric_count",
        "physical.lithography.medium_intercomponent_charge_unit",
    }
    assert {v.name for v in component_b_intercomponent_charge.direct_dependencies()} == {
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_intercomponent_charge_unit",
    }
    assert {v.name for v in intercomponent_charge_unit.direct_dependencies()} == {
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_component_b_stoichiometric_count",
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count",
    }
    assert intercomponent_charge_transfer_count.direct_dependencies() == set()
    assert {
        v.name
        for v in intercomponent_charge_transfer_count.direct_dependencies(
            include_constraints=True
        )
    } == {
        "physical.lithography.medium_component_a_proton_count",
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_component_b_proton_count",
        "physical.lithography.medium_component_b_stoichiometric_count",
    }
    assert {v.name for v in intercomponent_pair_count.direct_dependencies()} == {
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_component_b_stoichiometric_count",
    }
    assert {v.name for v in intercomponent_separation.direct_dependencies()} == {
        "physical.lithography.medium_component_a_effective_intercomponent_radius",
        "physical.lithography.medium_component_b_effective_intercomponent_radius",
        "physical.lithography.medium_intercomponent_gap",
    }
    assert component_a_intercomponent_radius_scale.direct_dependencies() == set()
    assert component_b_intercomponent_radius_scale.direct_dependencies() == set()
    assert {v.name for v in component_a_intercomponent_radius.direct_dependencies()} == {
        "physical.lithography.medium_component_a_intercomponent_radius_scale_factor",
        "physical.lithography.medium_component_a_isotope_mass_number",
        "physical.lithography.medium_component_nuclear_radius_coefficient",
    }
    assert {v.name for v in component_b_intercomponent_radius.direct_dependencies()} == {
        "physical.lithography.medium_component_b_intercomponent_radius_scale_factor",
        "physical.lithography.medium_component_b_isotope_mass_number",
        "physical.lithography.medium_component_nuclear_radius_coefficient",
    }
    assert intercomponent_gap_fraction.direct_dependencies() == set()
    assert {v.name for v in intercomponent_gap.direct_dependencies()} == {
        "physical.lithography.medium_component_a_effective_intercomponent_radius",
        "physical.lithography.medium_component_b_effective_intercomponent_radius",
        "physical.lithography.medium_intercomponent_gap_fraction",
    }
    assert intercomponent_polarizable_site_density_factor.direct_dependencies() == set()
    assert {v.name for v in intercomponent_lorentz_lorenz_factor.direct_dependencies()} == {
        "physical.lithography.medium_electric_polarizability",
        "physical.lithography.medium_intercomponent_effective_separation",
        "physical.lithography.medium_intercomponent_polarizable_site_density_factor",
        "physics.vacuum_permittivity",
    }
    assert {v.name for v in intercomponent_relative_permittivity.direct_dependencies()} == {
        "physical.lithography.medium_intercomponent_lorentz_lorenz_factor",
    }
    assert {v.name for v in intercomponent_binding.direct_dependencies()} == {
        "physical.lithography.medium_component_a_effective_intercomponent_charge_number",
        "physical.lithography.medium_component_b_effective_intercomponent_charge_number",
        "physical.lithography.medium_formula_unit_intercomponent_pair_count",
        "physical.lithography.medium_intercomponent_effective_separation",
        "physical.lithography.medium_intercomponent_relative_permittivity",
        "physics.elementary_charge",
        "physics.vacuum_permittivity",
    }
    assert {v.name for v in component_a_binding.direct_dependencies()} == {
        "physical.lithography.medium_component_a_binding_asymmetry_term",
        "physical.lithography.medium_component_a_binding_coulomb_term",
        "physical.lithography.medium_component_a_binding_pairing_term",
        "physical.lithography.medium_component_a_binding_surface_term",
        "physical.lithography.medium_component_a_binding_volume_term",
    }
    assert {v.name for v in component_b_binding.direct_dependencies()} == {
        "physical.lithography.medium_component_b_binding_asymmetry_term",
        "physical.lithography.medium_component_b_binding_coulomb_term",
        "physical.lithography.medium_component_b_binding_pairing_term",
        "physical.lithography.medium_component_b_binding_surface_term",
        "physical.lithography.medium_component_b_binding_volume_term",
    }
    assert {v.name for v in proton_count.direct_dependencies()} == {
        "physical.lithography.medium_component_a_proton_count",
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_component_b_proton_count",
        "physical.lithography.medium_component_b_stoichiometric_count",
    }
    assert {v.name for v in neutron_count.direct_dependencies()} == {
        "physical.lithography.medium_component_a_neutron_count",
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_component_b_neutron_count",
        "physical.lithography.medium_component_b_stoichiometric_count",
    }
    assert {v.name for v in binding_energy.direct_dependencies()} == {
        "physical.lithography.medium_component_a_binding_energy",
        "physical.lithography.medium_component_a_stoichiometric_count",
        "physical.lithography.medium_component_b_binding_energy",
        "physical.lithography.medium_component_b_stoichiometric_count",
        "physical.lithography.medium_formula_unit_intercomponent_binding_energy",
    }
    assert {v.name for v in formula_mass.direct_dependencies()} == {
        "physical.lithography.medium_formula_unit_proton_count",
        "physical.lithography.medium_formula_unit_neutron_count",
        "physical.lithography.medium_formula_unit_electron_count",
        "physical.lithography.medium_formula_unit_binding_energy",
        "physics.proton_mass",
        "physics.neutron_mass",
        "physics.electron_mass",
        "physics.speed_of_light",
    }
    assert {v.name for v in electron_count.direct_dependencies()} == {
        "physical.lithography.medium_formula_unit_proton_count",
    }
    assert {v.name for v in molar_mass.direct_dependencies()} == {
        "physical.lithography.medium_formula_unit_rest_mass",
        "physics.avogadro",
    }
    assert {v.name for v in particle_mass.direct_dependencies()} == {
        "physical.lithography.medium_molar_mass",
        "physics.avogadro",
    }
    assert packing_length_scale_factor.direct_dependencies() == set()
    assert {v.name for v in packing_length.direct_dependencies()} == {
        "physical.lithography.medium_intercomponent_effective_separation",
        "physical.lithography.medium_formula_unit_packing_length_scale_factor",
    }
    assert packing_fill_factor.direct_dependencies() == set()
    assert {v.name for v in packing_volume.direct_dependencies()} == {
        "physical.lithography.medium_formula_unit_packing_length",
    }
    assert {v.name for v in mass_density.direct_dependencies()} == {
        "physical.lithography.medium_formula_unit_packing_fill_factor",
        "physical.lithography.medium_formula_unit_packing_volume",
        "physical.lithography.medium_particle_mass",
    }
    assert {v.name for v in number_density.direct_dependencies()} == {
        "physical.lithography.medium_mass_density",
        "physical.lithography.medium_particle_mass",
    }

    proton_mass = Registry.variables["physics.proton_mass"].value
    neutron_mass = Registry.variables["physics.neutron_mass"].value
    electron_mass = Registry.variables["physics.electron_mass"].value
    speed_of_light = Registry.variables["physics.speed_of_light"].value
    elementary_charge = Registry.variables["physics.elementary_charge"].value
    vacuum_permittivity = Registry.variables["physics.vacuum_permittivity"].value
    avogadro = Registry.variables["physics.avogadro"].value
    component_a_expected_binding = expected_medium_component_binding_energy(1, 0)
    component_b_expected_binding = expected_medium_component_binding_energy(8, 9)
    expected_intercomponent_binding = 5.0e-12
    intercomponent_charge_transfer_count_test = 2.0
    expected_intercomponent_charge_unit = 1.0
    expected_component_a_intercomponent_charge = 1.0
    expected_component_b_intercomponent_charge = -2.0
    expected_intercomponent_pair_count = 2
    intercomponent_test_separation = (
        -expected_intercomponent_pair_count
        * expected_component_a_intercomponent_charge
        * expected_component_b_intercomponent_charge
        * elementary_charge**2
        / (4.0 * float(sp.pi) * vacuum_permittivity * expected_intercomponent_binding)
    )
    packing_length_scale_factor_test = 0.5 / intercomponent_test_separation
    component_a_intercomponent_test_radius = intercomponent_test_separation / 4.0
    component_b_intercomponent_test_radius = intercomponent_test_separation / 4.0
    intercomponent_test_gap = intercomponent_test_separation / 2.0
    medium_radius_coeff_test = (
        3.0
        * elementary_charge**2
        / (20.0 * float(sp.pi) * vacuum_permittivity * 0.5e-13)
    )
    component_a_intercomponent_radius_scale_test = (
        component_a_intercomponent_test_radius
        / (medium_radius_coeff_test * 1.0 ** (1.0 / 3.0))
    )
    component_b_intercomponent_radius_scale_test = (
        component_b_intercomponent_test_radius
        / (medium_radius_coeff_test * 17.0 ** (1.0 / 3.0))
    )
    intercomponent_gap_fraction_test = (
        intercomponent_test_gap
        / (
            component_a_intercomponent_test_radius
            + component_b_intercomponent_test_radius
        )
    )
    expected_binding_energy = (
        2 * component_a_expected_binding
        + component_b_expected_binding
        + expected_intercomponent_binding
    )
    expected_formula_mass = (
        10 * proton_mass
        + 9 * neutron_mass
        + 10 * electron_mass
        - expected_binding_energy / speed_of_light**2
    )

    assignments = {
        "physical.lithography.medium_component_a_stoichiometric_count": 2,
        **medium_component_quark_assignments("a", 1, 0),
        "physical.lithography.medium_component_b_stoichiometric_count": 1,
        **medium_component_quark_assignments("b", 8, 9),
        **medium_liquid_drop_root_assignments(),
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count": (
            intercomponent_charge_transfer_count_test
        ),
        "physical.lithography.medium_component_a_intercomponent_radius_scale_factor": (
            component_a_intercomponent_radius_scale_test
        ),
        "physical.lithography.medium_component_b_intercomponent_radius_scale_factor": (
            component_b_intercomponent_radius_scale_test
        ),
        "physical.lithography.medium_intercomponent_gap_fraction": (
            intercomponent_gap_fraction_test
        ),
        "physical.lithography.medium_intercomponent_polarizable_site_density_factor": (
            1.0
        ),
        "physical.lithography.medium_electric_polarizability": 0.0,
    }

    component_b_proton_result = resolve(
        "physical.lithography.medium_component_b_proton_count",
        assignments=assignments,
    )
    assert float(component_b_proton_result.value) == pytest.approx(8.0)
    component_b_neutron_result = resolve(
        "physical.lithography.medium_component_b_neutron_count",
        assignments=assignments,
    )
    assert float(component_b_neutron_result.value) == pytest.approx(9.0)

    proton_result = resolve(
        "physical.lithography.medium_formula_unit_proton_count",
        assignments=assignments,
    )
    assert float(proton_result.value) == pytest.approx(10.0)
    neutron_result = resolve(
        "physical.lithography.medium_formula_unit_neutron_count",
        assignments=assignments,
    )
    assert float(neutron_result.value) == pytest.approx(9.0)
    component_a_atomic_result = resolve(
        "physical.lithography.medium_component_a_atomic_number",
        assignments=assignments,
    )
    assert float(component_a_atomic_result.value) == pytest.approx(1.0)
    component_b_atomic_result = resolve(
        "physical.lithography.medium_component_b_atomic_number",
        assignments=assignments,
    )
    assert float(component_b_atomic_result.value) == pytest.approx(8.0)
    component_a_mass_number_result = resolve(
        "physical.lithography.medium_component_a_isotope_mass_number",
        assignments=assignments,
    )
    assert float(component_a_mass_number_result.value) == pytest.approx(1.0)
    component_b_mass_number_result = resolve(
        "physical.lithography.medium_component_b_isotope_mass_number",
        assignments=assignments,
    )
    assert float(component_b_mass_number_result.value) == pytest.approx(17.0)
    component_a_binding_result = resolve(
        "physical.lithography.medium_component_a_binding_energy",
        assignments=assignments,
    )
    assert float(component_a_binding_result.value) == pytest.approx(
        component_a_expected_binding
    )
    component_b_binding_result = resolve(
        "physical.lithography.medium_component_b_binding_energy",
        assignments=assignments,
    )
    assert float(component_b_binding_result.value) == pytest.approx(
        component_b_expected_binding
    )
    intercomponent_charge_unit_result = resolve(
        "physical.lithography.medium_intercomponent_charge_unit",
        assignments=assignments,
    )
    assert float(intercomponent_charge_unit_result.value) == pytest.approx(
        expected_intercomponent_charge_unit
    )
    component_a_intercomponent_charge_result = resolve(
        "physical.lithography.medium_component_a_effective_intercomponent_charge_number",
        assignments=assignments,
    )
    assert float(component_a_intercomponent_charge_result.value) == pytest.approx(
        expected_component_a_intercomponent_charge
    )
    component_b_intercomponent_charge_result = resolve(
        "physical.lithography.medium_component_b_effective_intercomponent_charge_number",
        assignments=assignments,
    )
    assert float(component_b_intercomponent_charge_result.value) == pytest.approx(
        expected_component_b_intercomponent_charge
    )
    intercomponent_pair_count_result = resolve(
        "physical.lithography.medium_formula_unit_intercomponent_pair_count",
        assignments=assignments,
    )
    assert float(intercomponent_pair_count_result.value) == pytest.approx(
        expected_intercomponent_pair_count
    )
    component_a_intercomponent_radius_result = resolve(
        "physical.lithography.medium_component_a_effective_intercomponent_radius",
        assignments=assignments,
    )
    assert float(component_a_intercomponent_radius_result.value) == pytest.approx(
        component_a_intercomponent_test_radius
    )
    component_b_intercomponent_radius_result = resolve(
        "physical.lithography.medium_component_b_effective_intercomponent_radius",
        assignments=assignments,
    )
    assert float(component_b_intercomponent_radius_result.value) == pytest.approx(
        component_b_intercomponent_test_radius
    )
    intercomponent_gap_result = resolve(
        "physical.lithography.medium_intercomponent_gap",
        assignments=assignments,
    )
    assert float(intercomponent_gap_result.value) == pytest.approx(
        intercomponent_test_gap
    )
    intercomponent_separation_result = resolve(
        "physical.lithography.medium_intercomponent_effective_separation",
        assignments=assignments,
    )
    assert float(intercomponent_separation_result.value) == pytest.approx(
        intercomponent_test_separation
    )
    intercomponent_lorentz_lorenz_result = resolve(
        "physical.lithography.medium_intercomponent_lorentz_lorenz_factor",
        assignments=assignments,
    )
    assert float(intercomponent_lorentz_lorenz_result.value) == pytest.approx(0.0)
    intercomponent_relative_permittivity_result = resolve(
        "physical.lithography.medium_intercomponent_relative_permittivity",
        assignments=assignments,
    )
    assert float(intercomponent_relative_permittivity_result.value) == pytest.approx(
        1.0
    )
    intercomponent_binding_result = resolve(
        "physical.lithography.medium_formula_unit_intercomponent_binding_energy",
        assignments=assignments,
    )
    assert float(intercomponent_binding_result.value) == pytest.approx(
        expected_intercomponent_binding
    )
    binding_result = resolve(
        "physical.lithography.medium_formula_unit_binding_energy",
        assignments=assignments,
    )
    assert float(binding_result.value) == pytest.approx(expected_binding_energy)

    electron_result = resolve(
        "physical.lithography.medium_formula_unit_electron_count",
        assignments=assignments,
    )
    assert float(electron_result.value) == pytest.approx(10.0)

    formula_result = resolve(
        "physical.lithography.medium_formula_unit_rest_mass",
        assignments=assignments,
    )
    assert float(formula_result.value) == pytest.approx(expected_formula_mass)

    molar_result = resolve(
        "physical.lithography.medium_molar_mass",
        assignments=assignments,
    )
    assert float(molar_result.value) == pytest.approx(
        avogadro * expected_formula_mass
    )

    particle_result = resolve(
        "physical.lithography.medium_particle_mass",
        assignments=assignments,
    )
    assert float(particle_result.value) == pytest.approx(expected_formula_mass)

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
            **assignments,
            "physical.lithography.medium_formula_unit_packing_length_scale_factor": (
                packing_length_scale_factor_test
            ),
            "physical.lithography.medium_formula_unit_packing_fill_factor": 0.625,
        },
    )
    assert float(mass_density_result.value) == pytest.approx(
        5.0 * expected_formula_mass
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
            **assignments,
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
            **assignments,
            "physical.lithography.medium_formula_unit_packing_length_scale_factor": (
                packing_length_scale_factor_test
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
            **assignments,
            "physical.lithography.medium_formula_unit_packing_length_scale_factor": (
                packing_length_scale_factor_test
            ),
            "physical.lithography.medium_formula_unit_packing_fill_factor": 0.625,
        },
    )
    assert float(density_result.value) == pytest.approx(5.0)
