"""
tests/test_lithography_medium_composition.py
============================================

The imaging medium should not treat molar mass as a terminal material knob.
"""

import pytest
import sympy as sp

from gpu_stack import Inequality, Registry, RelationRole, resolve


def medium_component_quark_assignments(component: str, protons: int, neutrons: int):
    return {
        f"physical.lithography.medium_component_{component}_valence_up_quark_count": (
            2 * protons + neutrons
        ),
        f"physical.lithography.medium_component_{component}_valence_down_quark_count": (
            protons + 2 * neutrons
        ),
    }


def medium_liquid_drop_root_assignments(
    volume_coeff=10.0e-13,
    surface_coeff=2.0e-13,
    coulomb_coeff=0.5e-13,
    asymmetry_coeff=3.0e-13,
    pairing_gap=2.0e-13,
):
    return {
        "physical.lithography.nuclear_binding_volume_coefficient": volume_coeff,
        "physical.lithography.nuclear_binding_surface_coefficient": surface_coeff,
        "physical.lithography.nuclear_binding_coulomb_coefficient": coulomb_coeff,
        "physical.lithography.nuclear_binding_asymmetry_coefficient": asymmetry_coeff,
        "physical.lithography.nuclear_pairing_gap_reference_energy": pairing_gap,
    }


def expected_medium_component_binding_energy(
    protons: int,
    neutrons: int,
    volume_coeff=10.0e-13,
    surface_coeff=2.0e-13,
    coulomb_coeff=0.5e-13,
    asymmetry_coeff=3.0e-13,
    pairing_gap=2.0e-13,
):
    mass_number = protons + neutrons
    neutron_excess = neutrons - protons
    if protons % 2 == 0 and neutrons % 2 == 0:
        pairing_sign = 1.0
    elif protons % 2 == 1 and neutrons % 2 == 1:
        pairing_sign = -1.0
    else:
        pairing_sign = 0.0
    return (
        volume_coeff * mass_number
        - surface_coeff * mass_number ** (2.0 / 3.0)
        - coulomb_coeff * protons * (protons - 1) / mass_number ** (1.0 / 3.0)
        - asymmetry_coeff * neutron_excess**2 / mass_number
        + pairing_sign * pairing_gap
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


def test_lithography_medium_component_liquid_drop_binding_terms():
    volume_coeff = 10.0e-13
    surface_coeff = 2.0e-13
    coulomb_coeff = 0.5e-13
    asymmetry_coeff = 3.0e-13
    assignments = {
        **medium_component_quark_assignments("a", 2, 2),
        **medium_liquid_drop_root_assignments(
            volume_coeff=volume_coeff,
            surface_coeff=surface_coeff,
            coulomb_coeff=coulomb_coeff,
            asymmetry_coeff=asymmetry_coeff,
        ),
    }
    elementary_charge = Registry.variables["physics.elementary_charge"].value
    vacuum_permittivity = Registry.variables["physics.vacuum_permittivity"].value
    expected_radius_coeff = (
        3.0
        * elementary_charge**2
        / (20.0 * float(sp.pi) * vacuum_permittivity * coulomb_coeff)
    )
    expected_saturation_density = 3.0 / (
        4.0 * float(sp.pi) * expected_radius_coeff**3
    )
    assert float(resolve(
        "physical.lithography.medium_component_nuclear_radius_coefficient",
        assignments=assignments,
    ).value) == pytest.approx(expected_radius_coeff)
    assert float(resolve(
        "physical.lithography.medium_component_nuclear_saturation_number_density",
        assignments=assignments,
    ).value) == pytest.approx(expected_saturation_density)
    assert float(resolve(
        "physical.lithography.medium_component_nuclear_bulk_binding_energy_density",
        assignments=assignments,
    ).value) == pytest.approx(volume_coeff * expected_saturation_density)
    assert float(resolve(
        "physical.lithography.medium_component_nuclear_surface_tension",
        assignments=assignments,
    ).value) == pytest.approx(
        surface_coeff / (4.0 * float(sp.pi) * expected_radius_coeff**2)
    )
    assert float(resolve(
        "physical.lithography.medium_component_nuclear_symmetry_energy_density",
        assignments=assignments,
    ).value) == pytest.approx(asymmetry_coeff * expected_saturation_density)
    assert float(resolve(
        "physical.lithography.medium_component_binding_coulomb_coefficient",
        assignments=assignments,
    ).value) == pytest.approx(coulomb_coeff)
    assert float(resolve(
        "physical.lithography.medium_component_binding_volume_coefficient",
        assignments=assignments,
    ).value) == pytest.approx(volume_coeff)
    assert float(resolve(
        "physical.lithography.medium_component_binding_surface_coefficient",
        assignments=assignments,
    ).value) == pytest.approx(surface_coeff)
    assert float(resolve(
        "physical.lithography.medium_component_binding_asymmetry_coefficient",
        assignments=assignments,
    ).value) == pytest.approx(asymmetry_coeff)
    assert float(resolve(
        "physical.lithography.medium_component_a_pairing_reference_mass_number",
        assignments=assignments,
    ).value) == pytest.approx(4.0)
    assert float(resolve(
        "physical.lithography.medium_component_a_binding_pairing_coefficient",
        assignments=assignments,
    ).value) == pytest.approx(4.0e-13)
    assert float(resolve(
        "physical.lithography.medium_component_a_pairing_sign",
        assignments=medium_component_quark_assignments("a", 2, 2),
    ).value) == pytest.approx(1.0)
    assert float(resolve(
        "physical.lithography.medium_component_a_pairing_sign",
        assignments=medium_component_quark_assignments("a", 3, 3),
    ).value) == pytest.approx(-1.0)
    assert float(resolve(
        "physical.lithography.medium_component_a_pairing_sign",
        assignments=medium_component_quark_assignments("a", 2, 3),
    ).value) == pytest.approx(0.0)

    component_a_binding = resolve(
        "physical.lithography.medium_component_a_binding_energy",
        assignments=assignments,
    )
    assert float(component_a_binding.value) == pytest.approx(
        expected_medium_component_binding_energy(2, 2)
    )

    component_b_binding = resolve(
        "physical.lithography.medium_component_b_binding_energy",
        assignments={
            **medium_component_quark_assignments("b", 3, 3),
            **medium_liquid_drop_root_assignments(),
        },
    )
    assert float(component_b_binding.value) == pytest.approx(
        expected_medium_component_binding_energy(3, 3)
    )


def test_lithography_medium_formula_unit_feasibility_constraints():
    packing_length_scale_factor_constraint = Registry.equations[
        "physical.ineq.lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity"
    ]
    packing_length_scale_factor = Registry.variables[
        "physical.lithography.medium_formula_unit_packing_length_scale_factor"
    ]

    assert isinstance(packing_length_scale_factor_constraint, Inequality)
    assert packing_length_scale_factor_constraint.role is RelationRole.CONSTRAINT
    assert packing_length_scale_factor_constraint in packing_length_scale_factor.constraints()
    assert packing_length_scale_factor_constraint.op == ">="
    assert packing_length_scale_factor_constraint.rhs == sp.Integer(1)
    assert packing_length_scale_factor_constraint.references
    assert getattr(packing_length_scale_factor_constraint, "_check_units_flag", False)
    assert isinstance(packing_length_scale_factor_constraint.as_sympy(), sp.Rel)
    assert not packing_length_scale_factor_constraint.is_trivially_true()

    constraint_cases = [
        (
            "physical.lithography.medium_component_a_stoichiometric_count",
            "physical.ineq.lithography_medium_component_a_stoichiometric_count_at_least_one",
            ">=",
            1,
            0,
        ),
        (
            "physical.lithography.medium_component_b_stoichiometric_count",
            "physical.ineq.lithography_medium_component_b_stoichiometric_count_at_least_one",
            ">=",
            1,
            0,
        ),
        (
            "physical.lithography.medium_formula_unit_packing_fill_factor",
            "physical.ineq.lithography_medium_formula_unit_packing_fill_factor_at_most_unity",
            "<=",
            1,
            1.25,
        ),
    ]

    for variable_name, equation_name, op, valid_value, invalid_value in constraint_cases:
        variable = Registry.variables[variable_name]
        relation = Registry.equations[equation_name]
        assert isinstance(relation, Inequality)
        assert relation.role is RelationRole.CONSTRAINT
        assert relation in variable.constraints()
        assert relation.op == op
        assert relation.rhs == sp.Integer(1)
        assert relation.references
        assert getattr(relation, "_check_units_flag", False)
        assert isinstance(relation.as_sympy(), sp.Rel)
        assert not relation.is_trivially_true()

        valid_result = resolve(variable_name, assignments={variable_name: valid_value})
        valid_check = next(
            c for c in valid_result.constraints if c.equation == equation_name
        )
        assert valid_check.satisfied is True

        invalid_result = resolve(
            variable_name,
            assignments={variable_name: invalid_value},
        )
        invalid_check = next(
            c for c in invalid_result.constraints if c.equation == equation_name
        )
        assert invalid_check.satisfied is False

    transfer_count = Registry.variables[
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count"
    ]
    component_a_stoich = Registry.variables[
        "physical.lithography.medium_component_a_stoichiometric_count"
    ]
    component_b_stoich = Registry.variables[
        "physical.lithography.medium_component_b_stoichiometric_count"
    ]
    component_a_protons = Registry.variables[
        "physical.lithography.medium_component_a_proton_count"
    ]
    component_b_protons = Registry.variables[
        "physical.lithography.medium_component_b_proton_count"
    ]
    transfer_constraints = [
        (
            "physical.ineq.lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_a_electron_inventory",
            component_a_stoich.symbol * component_a_protons.symbol,
        ),
        (
            "physical.ineq.lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_b_electron_inventory",
            component_b_stoich.symbol * component_b_protons.symbol,
        ),
    ]
    assert [eq.name for eq in transfer_count.constraints()] == [
        name for name, _rhs in transfer_constraints
    ]
    for equation_name, rhs in transfer_constraints:
        relation = Registry.equations[equation_name]
        assert isinstance(relation, Inequality)
        assert relation.role is RelationRole.CONSTRAINT
        assert relation in transfer_count.constraints()
        assert relation.op == "<="
        assert relation.rhs == rhs
        assert relation.references
        assert getattr(relation, "_check_units_flag", False)
        assert isinstance(relation.as_sympy(), sp.Rel)
        assert not relation.is_trivially_true()

    valid_transfer_assignments = {
        "physical.lithography.medium_component_a_stoichiometric_count": 2,
        **medium_component_quark_assignments("a", 1, 0),
        "physical.lithography.medium_component_b_stoichiometric_count": 1,
        **medium_component_quark_assignments("b", 8, 9),
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count": 2,
    }
    valid_transfer_result = resolve(
        transfer_count.name,
        assignments=valid_transfer_assignments,
    )
    for equation_name, _rhs in transfer_constraints:
        check = next(
            c for c in valid_transfer_result.constraints if c.equation == equation_name
        )
        assert check.satisfied is True

    invalid_transfer_assignments = dict(valid_transfer_assignments)
    invalid_transfer_assignments[transfer_count.name] = 3
    invalid_transfer_result = resolve(
        transfer_count.name,
        assignments=invalid_transfer_assignments,
    )
    component_a_inventory_check = next(
        c
        for c in invalid_transfer_result.constraints
        if c.equation == transfer_constraints[0][0]
    )
    component_b_inventory_check = next(
        c
        for c in invalid_transfer_result.constraints
        if c.equation == transfer_constraints[1][0]
    )
    assert component_a_inventory_check.satisfied is False
    assert component_b_inventory_check.satisfied is True

    invalid_component_a_formula_result = resolve(
        "physical.lithography.medium_formula_unit_proton_count",
        assignments={
            "physical.lithography.medium_component_a_stoichiometric_count": 0,
            **medium_component_quark_assignments("a", 1, 0),
            "physical.lithography.medium_component_b_stoichiometric_count": 1,
            **medium_component_quark_assignments("b", 8, 9),
        },
    )
    component_a_formula_check = next(
        c for c in invalid_component_a_formula_result.constraints
        if c.equation
        == "physical.ineq.lithography_medium_component_a_stoichiometric_count_at_least_one"
    )
    assert component_a_formula_check.satisfied is False

    invalid_component_b_formula_result = resolve(
        "physical.lithography.medium_formula_unit_proton_count",
        assignments={
            "physical.lithography.medium_component_a_stoichiometric_count": 1,
            **medium_component_quark_assignments("a", 1, 0),
            "physical.lithography.medium_component_b_stoichiometric_count": 0,
            **medium_component_quark_assignments("b", 8, 9),
        },
    )
    component_b_formula_check = next(
        c for c in invalid_component_b_formula_result.constraints
        if c.equation
        == "physical.ineq.lithography_medium_component_b_stoichiometric_count_at_least_one"
    )
    assert component_b_formula_check.satisfied is False


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


def test_lithography_medium_formula_unit_equations_have_unit_checks():
    checked_names = {
        "physical.ineq.lithography_medium_component_a_stoichiometric_count_at_least_one",
        "physical.ineq.lithography_medium_component_b_stoichiometric_count_at_least_one",
        "physical.eq.lithography_medium_component_a_proton_count_from_valence_quarks",
        "physical.eq.lithography_medium_component_a_neutron_count_from_valence_quarks",
        "physical.eq.lithography_medium_component_b_proton_count_from_valence_quarks",
        "physical.eq.lithography_medium_component_b_neutron_count_from_valence_quarks",
        "physical.ineq.lithography_medium_component_a_valence_quarks_imply_nonnegative_protons",
        "physical.ineq.lithography_medium_component_a_valence_quarks_imply_positive_protons",
        "physical.ineq.lithography_medium_component_a_valence_quarks_imply_nonnegative_neutrons",
        "physical.eq.lithography_medium_component_a_valence_quark_triplet_integrality",
        "physical.ineq.lithography_medium_component_b_valence_quarks_imply_nonnegative_protons",
        "physical.ineq.lithography_medium_component_b_valence_quarks_imply_positive_protons",
        "physical.ineq.lithography_medium_component_b_valence_quarks_imply_nonnegative_neutrons",
        "physical.eq.lithography_medium_component_b_valence_quark_triplet_integrality",
        "physical.eq.lithography_medium_component_a_atomic_number",
        "physical.eq.lithography_medium_component_b_atomic_number",
        "physical.eq.lithography_medium_component_a_isotope_mass_number",
        "physical.eq.lithography_medium_component_b_isotope_mass_number",
        "physical.eq.lithography_medium_component_binding_volume_coefficient_from_shared_nuclear_calibration",
        "physical.eq.lithography_medium_component_binding_surface_coefficient_from_shared_nuclear_calibration",
        "physical.eq.lithography_medium_component_binding_coulomb_coefficient_from_shared_nuclear_calibration",
        "physical.eq.lithography_medium_component_binding_asymmetry_coefficient_from_shared_nuclear_calibration",
        "physical.eq.lithography_medium_component_nuclear_pairing_gap_reference_energy_from_shared_nuclear_calibration",
        "physical.eq.lithography_medium_component_nuclear_radius_coefficient",
        "physical.eq.lithography_medium_component_nuclear_saturation_number_density",
        "physical.eq.lithography_medium_component_nuclear_bulk_binding_energy_density",
        "physical.eq.lithography_medium_component_nuclear_surface_tension",
        "physical.eq.lithography_medium_component_nuclear_symmetry_energy_density",
        "physical.eq.lithography_medium_component_a_neutron_excess",
        "physical.eq.lithography_medium_component_b_neutron_excess",
        "physical.eq.lithography_medium_component_a_pairing_sign",
        "physical.eq.lithography_medium_component_b_pairing_sign",
        "physical.eq.lithography_medium_component_a_pairing_reference_mass_number",
        "physical.eq.lithography_medium_component_b_pairing_reference_mass_number",
        "physical.eq.lithography_medium_component_a_binding_pairing_coefficient",
        "physical.eq.lithography_medium_component_b_binding_pairing_coefficient",
        "physical.eq.lithography_medium_component_a_binding_volume_term",
        "physical.eq.lithography_medium_component_b_binding_volume_term",
        "physical.eq.lithography_medium_component_a_binding_surface_term",
        "physical.eq.lithography_medium_component_b_binding_surface_term",
        "physical.eq.lithography_medium_component_a_binding_coulomb_term",
        "physical.eq.lithography_medium_component_b_binding_coulomb_term",
        "physical.eq.lithography_medium_component_a_binding_asymmetry_term",
        "physical.eq.lithography_medium_component_b_binding_asymmetry_term",
        "physical.eq.lithography_medium_component_a_binding_pairing_term",
        "physical.eq.lithography_medium_component_b_binding_pairing_term",
        "physical.eq.lithography_medium_component_a_binding_energy",
        "physical.eq.lithography_medium_component_b_binding_energy",
        "physical.ineq.lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_a_electron_inventory",
        "physical.ineq.lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_b_electron_inventory",
        "physical.eq.lithography_medium_intercomponent_charge_unit_from_formula_unit_charge_transfer",
        "physical.eq.lithography_medium_component_a_effective_intercomponent_charge_number",
        "physical.eq.lithography_medium_component_b_effective_intercomponent_charge_number",
        "physical.eq.lithography_medium_formula_unit_intercomponent_pair_count",
        "physical.eq.lithography_medium_component_a_effective_intercomponent_radius",
        "physical.eq.lithography_medium_component_b_effective_intercomponent_radius",
        "physical.eq.lithography_medium_intercomponent_gap_from_radius_fraction",
        "physical.eq.lithography_medium_intercomponent_effective_separation",
        "physical.eq.lithography_medium_formula_unit_intercomponent_binding_energy",
        "physical.eq.lithography_medium_formula_unit_proton_count",
        "physical.eq.lithography_medium_formula_unit_neutron_count",
        "physical.eq.lithography_medium_formula_unit_binding_energy",
        "physical.eq.lithography_medium_formula_unit_electron_count",
        "physical.eq.lithography_medium_formula_unit_rest_mass",
        "physical.eq.lithography_medium_molar_mass",
        "physical.eq.lithography_medium_particle_mass",
        "physical.ineq.lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity",
        "physical.eq.lithography_medium_formula_unit_packing_length_from_intercomponent_separation_scale",
        "physical.ineq.lithography_medium_formula_unit_packing_fill_factor_at_most_unity",
        "physical.eq.lithography_medium_formula_unit_packing_volume",
        "physical.eq.lithography_medium_mass_density_from_packing",
        "physical.eq.lithography_medium_number_density_from_mass",
        "physical.eq.lithography_medium_polarizable_electron_fraction_from_count",
        "physical.ineq.lithography_medium_polarizable_electron_count_within_formula_unit",
        "physical.eq.lithography_medium_oscillator_sum_rule_fraction_from_count",
        "physical.ineq.lithography_medium_dominant_oscillator_electron_count_within_polarizable_count",
        "physical.eq.lithography_medium_resonance_to_source_frequency_ratio_from_energy",
        "physical.ineq.lithography_medium_resonance_energy_above_source_photon_energy",
        "physical.eq.lithography_medium_resonance_angular_frequency_from_source_ratio",
        "physical.eq.lithography_medium_oscillator_strength_from_formula_electrons",
        "physical.eq.lithography_medium_electric_polarizability",
        "physical.eq.lithography_medium_intercomponent_lorentz_lorenz_factor",
        "physical.eq.lithography_medium_intercomponent_relative_permittivity_from_local_lorentz_lorenz",
    }
    for name in checked_names:
        assert getattr(Registry.equations[name], "_check_units_flag", False), name
