"""Registry coverage for lithography medium formula-unit model roots."""

from tests.helpers.lithography_medium_formula import medium_formula_variables


def test_lithography_medium_formula_unit_inputs_and_constraints():
    variables = medium_formula_variables()
    component_a_stoich = variables["component_a_stoich"]
    component_b_stoich = variables["component_b_stoich"]
    component_a_up_quarks = variables["component_a_up_quarks"]
    component_a_down_quarks = variables["component_a_down_quarks"]
    component_b_up_quarks = variables["component_b_up_quarks"]
    component_b_down_quarks = variables["component_b_down_quarks"]
    component_a_protons = variables["component_a_protons"]
    component_b_protons = variables["component_b_protons"]
    component_a_neutrons = variables["component_a_neutrons"]
    component_b_neutrons = variables["component_b_neutrons"]
    component_a_atomic_number = variables["component_a_atomic_number"]
    component_b_atomic_number = variables["component_b_atomic_number"]
    component_a_mass_number = variables["component_a_mass_number"]
    component_b_mass_number = variables["component_b_mass_number"]
    component_a_binding = variables["component_a_binding"]
    component_b_binding = variables["component_b_binding"]
    medium_saturation_density = variables["medium_saturation_density"]
    medium_radius_coeff = variables["medium_radius_coeff"]
    medium_bulk_binding_density = variables["medium_bulk_binding_density"]
    medium_volume_coeff = variables["medium_volume_coeff"]
    medium_surface_tension = variables["medium_surface_tension"]
    medium_surface_coeff = variables["medium_surface_coeff"]
    medium_symmetry_density = variables["medium_symmetry_density"]
    medium_asymmetry_coeff = variables["medium_asymmetry_coeff"]
    medium_pairing_gap = variables["medium_pairing_gap"]
    medium_coulomb_coeff = variables["medium_coulomb_coeff"]
    shared_volume_coeff = variables["shared_volume_coeff"]
    shared_surface_coeff = variables["shared_surface_coeff"]
    shared_coulomb_coeff = variables["shared_coulomb_coeff"]
    shared_asymmetry_coeff = variables["shared_asymmetry_coeff"]
    shared_pairing_gap = variables["shared_pairing_gap"]
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
    intercomponent_relative_permittivity = variables[
        "intercomponent_relative_permittivity"
    ]
    intercomponent_polarizable_site_density_factor = variables[
        "intercomponent_polarizable_site_density_factor"
    ]
    intercomponent_lorentz_lorenz_factor = variables[
        "intercomponent_lorentz_lorenz_factor"
    ]
    intercomponent_binding = variables["intercomponent_binding"]
    proton_count = variables["proton_count"]
    neutron_count = variables["neutron_count"]
    electron_count = variables["electron_count"]
    binding_energy = variables["binding_energy"]
    formula_mass = variables["formula_mass"]
    molar_mass = variables["molar_mass"]
    particle_mass = variables["particle_mass"]
    packing_length = variables["packing_length"]
    packing_length_scale_factor = variables["packing_length_scale_factor"]
    packing_fill_factor = variables["packing_fill_factor"]
    packing_volume = variables["packing_volume"]
    mass_density = variables["mass_density"]
    number_density = variables["number_density"]

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
