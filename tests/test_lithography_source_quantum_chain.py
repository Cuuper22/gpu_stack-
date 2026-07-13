"""Lithography source quantum-chain structure coverage."""

from gpu_stack import Registry
from gpu_stack.core import RelationRole
from tests.helpers.lithography_source_quantum import source_quantum_model


def test_lithography_photon_energy_has_quantum_source_model():
    model = source_quantum_model()

    assert not model.photon_energy.is_root_input
    assert model.proton_count.is_root_input
    assert model.neutron_count.is_root_input
    assert not model.atomic_number.is_root_input
    assert not model.isotope_mass_number.is_root_input
    assert not model.up_quarks.is_root_input
    assert not model.down_quarks.is_root_input
    assert len(model.up_quarks.defining_equations) == 1
    assert len(model.down_quarks.defining_equations) == 1
    assert not model.up_quarks.has_multiple_definitions()
    assert not model.down_quarks.has_multiple_definitions()
    assert not model.binding_energy.is_root_input
    assert not model.mass_number.is_root_input
    assert not model.neutron_excess.is_root_input
    assert not model.saturation_density.is_root_input
    assert not model.radius_coeff.is_root_input
    assert not model.bulk_binding_density.is_root_input
    assert model.shared_volume_coeff.is_root_input
    assert model.shared_surface_coeff.is_root_input
    assert model.shared_coulomb_coeff.is_root_input
    assert model.shared_asymmetry_coeff.is_root_input
    assert model.shared_pairing_gap_ref.is_root_input
    assert not model.volume_coeff.is_root_input
    assert not model.surface_tension.is_root_input
    assert not model.surface_coeff.is_root_input
    assert not model.symmetry_density.is_root_input
    assert not model.asymmetry_coeff.is_root_input
    assert not model.pairing_gap_ref.is_root_input
    assert not model.pairing_mass_ref.is_root_input
    assert not model.pairing_coeff.is_root_input
    assert not model.coulomb_coeff.is_root_input
    assert not model.volume_term.is_root_input
    assert not model.surface_term.is_root_input
    assert not model.coulomb_term.is_root_input
    assert not model.asymmetry_term.is_root_input
    assert not model.pairing_sign.is_root_input
    assert not model.pairing_term.is_root_input
    assert not model.nuclear_mass.is_root_input
    assert not model.reduced_mass.is_root_input
    assert not model.reduced_ratio.is_root_input
    assert not model.ion_charge_state.is_root_input
    assert not model.plasma_mean_energy.is_root_input
    assert not model.plasma_debye_length.is_root_input
    assert model.plasma_pulse_period.is_root_input
    assert not model.plasma_pulse_repetition_rate.is_root_input
    assert model.plasma_drive_pulse_duty_factor.is_root_input
    assert model.plasma_drive_pulse_fluence.is_root_input
    assert not model.plasma_drive_peak_intensity.is_root_input
    assert not model.plasma_drive_pulse_duration.is_root_input
    assert model.plasma_drive_pulse_rise_fraction.is_root_input
    assert not model.plasma_drive_pulse_fall_fraction.is_root_input
    assert not model.plasma_drive_pulse_flat_fraction.is_root_input
    assert not model.plasma_drive_pulse_temporal_shape_factor.is_root_input
    assert not model.plasma_drive_beam_wavelength.is_root_input
    assert model.plasma_drive_edge_detuning_ratio.is_root_input
    assert model.plasma_drive_objective_pupil_radius.is_root_input
    assert model.plasma_drive_objective_focal_length.is_root_input
    assert model.plasma_drive_pupil_beam_fill_factor.is_root_input
    assert not model.plasma_drive_acceptance_half_angle.is_root_input
    assert not model.plasma_drive_numerical_aperture.is_root_input
    assert not model.plasma_drive_focus_f_number.is_root_input
    assert not model.plasma_drive_beam_parameter_waist_radius.is_root_input
    assert model.plasma_drive_far_field_divergence_half_angle.is_root_input
    assert not model.plasma_drive_beam_parameter_product.is_root_input
    assert not model.plasma_drive_beam_quality_factor.is_root_input
    assert not model.plasma_drive_focus_waist_coefficient.is_root_input
    assert not model.plasma_drive_spot_radius.is_root_input
    assert not model.plasma_drive_rayleigh_range.is_root_input
    assert not model.plasma_drive_confocal_length.is_root_input
    assert not model.plasma_drive_spot_axis_ratio.is_root_input
    assert not model.plasma_drive_spot_area_fill_factor.is_root_input
    assert not model.plasma_drive_spot_shape_factor.is_root_input
    assert not model.plasma_drive_spot_area.is_root_input
    assert not model.plasma_pulse_energy.is_root_input
    assert not model.plasma_drive_power.is_root_input
    assert model.plasma_species_partial_pressure.is_root_input
    assert model.plasma_species_gas_temperature.is_root_input
    assert not model.plasma_species_number_density.is_root_input
    assert not model.plasma_column_expansion_speed_factor.is_root_input
    assert not model.plasma_column_radial_expansion_speed.is_root_input
    assert not model.plasma_column_radius_expansion_factor.is_root_input
    assert not model.plasma_column_radius.is_root_input
    assert not model.plasma_column_aspect_ratio.is_root_input
    assert not model.plasma_column_length.is_root_input
    assert not model.plasma_active_fill_factor.is_root_input
    assert not model.plasma_active_volume.is_root_input
    assert not model.plasma_absorption_path_direction_cosine.is_root_input
    assert not model.plasma_absorption_path_shape_factor.is_root_input
    assert not model.plasma_absorption_path_length.is_root_input
    assert not model.plasma_drive_beam_angular_frequency.is_root_input
    assert not model.plasma_absorption_resonance_to_drive_ratio.is_root_input
    assert not model.plasma_absorption_quality_factor.is_root_input
    assert not model.plasma_absorption_collision_cross_section.is_root_input
    assert not model.plasma_absorption_collision_orbital_radius.is_root_input
    assert not model.plasma_absorption_participating_electron_fraction.is_root_input
    assert not model.plasma_absorption_sum_rule_fraction.is_root_input
    assert not model.plasma_absorption_resonance.is_root_input
    assert not model.plasma_absorption_damping_rate.is_root_input
    assert not model.plasma_absorption_oscillator_strength.is_root_input
    assert not model.plasma_absorption_cross_section.is_root_input
    assert not model.plasma_absorption_optical_depth.is_root_input
    assert not model.plasma_drive_energy_absorption_fraction.is_root_input
    assert not model.plasma_drive_centroid_offset_to_column_radius_ratio.is_root_input
    assert not model.plasma_drive_pointing_overlap_factor.is_root_input
    assert not model.plasma_drive_transverse_overlap_factor.is_root_input
    assert not model.plasma_drive_spatial_overlap_factor.is_root_input
    assert not model.plasma_active_lifetime_to_drive_pulse_ratio.is_root_input
    assert not model.plasma_active_response_duration.is_root_input
    assert not model.plasma_drive_timing_offset_fraction.is_root_input
    assert not model.plasma_drive_timing_offset_duration.is_root_input
    assert not model.plasma_drive_temporal_duration_match_factor.is_root_input
    assert not model.plasma_drive_temporal_alignment_factor.is_root_input
    assert not model.plasma_drive_temporal_overlap_factor.is_root_input
    assert not model.plasma_drive_overlap_factor.is_root_input
    assert model.plasma_electron_heating_fraction.is_root_input
    assert not model.plasma_absorption_efficiency.is_root_input
    assert not model.plasma_absorbed_power.is_root_input
    assert not model.plasma_energy_loss_path_direction_cosine.is_root_input
    assert not model.plasma_energy_loss_path_factor.is_root_input
    assert not model.plasma_energy_loss_path_length.is_root_input
    assert not model.plasma_species_particle_mass.is_root_input
    assert not model.plasma_energy_loss_transport_speed_factor.is_root_input
    assert not model.plasma_species_thermal_speed.is_root_input
    assert not model.plasma_energy_loss_speed.is_root_input
    assert not model.plasma_confinement_time.is_root_input
    assert model.plasma_free_electron_inventory_charge_fraction.is_root_input
    assert not model.plasma_free_electron_yield.is_root_input
    assert not model.plasma_free_electron_count.is_root_input
    assert not model.plasma_internal_energy.is_root_input
    assert not model.plasma_temperature.is_root_input
    assert not model.plasma_density.is_root_input
    assert not model.ionization_energy.is_root_input
    assert not model.ionization_principal.is_root_input
    assert not model.ionization_screening.is_root_input
    assert not model.ionization_inner_screeners.is_root_input
    assert not model.ionization_same_screeners.is_root_input
    assert not model.ionization_z_eff.is_root_input
    assert not model.partition_ratio.is_root_input
    assert not model.saha_thermal_density.is_root_input
    assert not model.saha_ratio.is_root_input
    assert not model.saha_fraction.is_root_input
    assert not model.bound_electrons.is_root_input
    assert not model.lower_principal.is_root_input
    assert not model.upper_principal.is_root_input
    assert not model.transition_step.is_root_input
    assert not model.shell_capacity.is_root_input
    assert not model.inner_closed_capacity.is_root_input
    assert not model.inner_closed_shells.is_root_input
    assert not model.outer_shells.is_root_input
    assert not model.transition_shell_occupancy.is_root_input
    assert not model.inner_screeners.is_root_input
    assert not model.same_screeners.is_root_input
    assert not model.inner_shielding.is_root_input
    assert not model.same_shielding.is_root_input
    assert not model.screening.is_root_input
    assert not model.z_eff.is_root_input
    assert not model.transition.is_root_input


def test_lithography_source_quantum_particle_binding_and_reduced_mass_dependencies():
    model = source_quantum_model()

    assert {v.name for v in model.atomic_number.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in model.isotope_mass_number.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
    }
    assert {v.name for v in model.proton_count.direct_dependencies()} == set()
    assert {v.name for v in model.neutron_count.direct_dependencies()} == set()
    assert {
        v.name
        for v in model.proton_count.direct_dependencies(include_constraints=True)
    } == set()
    assert {
        v.name
        for v in model.neutron_count.direct_dependencies(include_constraints=True)
    } == set()
    assert {v.name for v in model.up_quarks.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
    }
    assert {v.name for v in model.down_quarks.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
    }
    assert {v.name for v in model.mass_number.direct_dependencies()} == {
        "physical.lithography.source_isotope_mass_number",
    }
    assert {v.name for v in model.neutron_excess.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
    }
    assert {v.name for v in model.radius_coeff.direct_dependencies()} == {
        "physical.lithography.source_binding_coulomb_coefficient",
        "physics.elementary_charge",
        "physics.vacuum_permittivity",
    }
    assert {v.name for v in model.saturation_density.direct_dependencies()} == {
        "physical.lithography.source_nuclear_radius_coefficient",
    }
    assert {v.name for v in model.bulk_binding_density.direct_dependencies()} == {
        "physical.lithography.source_binding_volume_coefficient",
        "physical.lithography.source_nuclear_saturation_number_density",
    }
    assert {v.name for v in model.volume_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_volume_coefficient",
    }
    assert {v.name for v in model.surface_tension.direct_dependencies()} == {
        "physical.lithography.source_binding_surface_coefficient",
        "physical.lithography.source_nuclear_radius_coefficient",
    }
    assert {v.name for v in model.surface_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_surface_coefficient",
    }
    assert {v.name for v in model.symmetry_density.direct_dependencies()} == {
        "physical.lithography.source_binding_asymmetry_coefficient",
        "physical.lithography.source_nuclear_saturation_number_density",
    }
    assert {v.name for v in model.asymmetry_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_asymmetry_coefficient",
    }
    assert {v.name for v in model.pairing_mass_ref.direct_dependencies()} == {
        "physical.lithography.source_mass_number",
    }
    pairing_ref_eq = Registry.equations[
        "physical.eq.lithography_source_pairing_reference_mass_number"
    ]
    assert model.pairing_mass_ref.approximations() == [pairing_ref_eq]
    assert pairing_ref_eq.role is RelationRole.APPROXIMATION
    assert str(pairing_ref_eq.validity) == "A_litho_src > 0"
    assert pairing_ref_eq.references
    assert getattr(pairing_ref_eq, "_check_units_flag", False)
    assert {v.name for v in model.pairing_coeff.direct_dependencies()} == {
        "physical.lithography.source_nuclear_pairing_gap_reference_energy",
        "physical.lithography.source_pairing_reference_mass_number",
    }
    assert {v.name for v in model.pairing_gap_ref.direct_dependencies()} == {
        "physical.lithography.nuclear_pairing_gap_reference_energy",
    }
    assert {v.name for v in model.coulomb_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_coulomb_coefficient",
    }
    assert {v.name for v in model.volume_term.direct_dependencies()} == {
        "physical.lithography.source_binding_volume_coefficient",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in model.surface_term.direct_dependencies()} == {
        "physical.lithography.source_binding_surface_coefficient",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in model.coulomb_term.direct_dependencies()} == {
        "physical.lithography.source_binding_coulomb_coefficient",
        "physical.lithography.source_proton_count",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in model.asymmetry_term.direct_dependencies()} == {
        "physical.lithography.source_binding_asymmetry_coefficient",
        "physical.lithography.source_neutron_excess",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in model.pairing_sign.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
    }
    assert {v.name for v in model.pairing_term.direct_dependencies()} == {
        "physical.lithography.source_binding_pairing_coefficient",
        "physical.lithography.source_pairing_sign",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in model.binding_energy.direct_dependencies()} == {
        "physical.lithography.source_binding_volume_term",
        "physical.lithography.source_binding_surface_term",
        "physical.lithography.source_binding_coulomb_term",
        "physical.lithography.source_binding_asymmetry_term",
        "physical.lithography.source_binding_pairing_term",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in model.nuclear_mass.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
        "physical.lithography.source_nuclear_binding_energy",
        "physics.proton_mass",
        "physics.neutron_mass",
        "physics.speed_of_light",
    }
    assert {v.name for v in model.reduced_mass.direct_dependencies()} == {
        "physical.lithography.source_nuclear_mass",
        "physics.electron_mass",
    }
    assert {v.name for v in model.reduced_ratio.direct_dependencies()} == {
        "physical.lithography.source_reduced_mass",
        "physics.electron_mass",
    }

def test_lithography_source_quantum_electronic_transition_dependencies():
    model = source_quantum_model()

    assert {v.name for v in model.ionization_principal.direct_dependencies()} == {
        "physical.lithography.source_lower_principal_quantum_number",
    }
    assert {v.name for v in model.ionization_inner_screeners.direct_dependencies()} == {
        "physical.lithography.source_inner_closed_shell_capacity",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in model.ionization_same_screeners.direct_dependencies()} == {
        "physical.lithography.source_ionization_inner_shell_screening_electron_count",
        "physical.lithography.source_proton_count",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in model.ionization_screening.direct_dependencies()} == {
        "physical.lithography.source_ionization_inner_shell_screening_electron_count",
        "physical.lithography.source_ionization_same_shell_screening_electron_count",
        "physical.lithography.source_inner_shell_shielding_factor",
        "physical.lithography.source_proton_count",
        "physical.lithography.source_same_shell_shielding_factor",
    }
    assert {v.name for v in model.ionization_z_eff.direct_dependencies()} == {
        "physical.lithography.source_ionization_screening_constant",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in model.ionization_energy.direct_dependencies()} == {
        "physical.lithography.source_ionization_effective_nuclear_charge",
        "physical.lithography.source_ionization_principal_quantum_number",
        "physics.rydberg_energy",
    }
    assert {v.name for v in model.partition_ratio.direct_dependencies()} == {
        "physical.lithography.source_ionization_same_shell_screening_electron_count",
        "physical.lithography.source_transition_shell_capacity",
    }

    assert {v.name for v in model.saha_thermal_density.direct_dependencies()} == {
        "physical.lithography.source_plasma_electron_temperature",
        "physics.boltzmann",
        "physics.electron_mass",
        "physics.planck",
    }
    assert {v.name for v in model.saha_ratio.direct_dependencies()} == {
        "physical.lithography.source_ionization_energy",
        "physical.lithography.source_ionization_partition_ratio",
        "physical.lithography.source_plasma_electron_number_density",
        "physical.lithography.source_plasma_electron_temperature",
        "physical.lithography.source_saha_thermal_number_density",
        "physics.boltzmann",
    }
    assert {v.name for v in model.saha_fraction.direct_dependencies()} == {
        "physical.lithography.source_saha_ionization_ratio",
    }
    assert {v.name for v in model.ion_charge_state.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_saha_ionization_fraction",
    }
    assert {v.name for v in model.bound_electrons.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_ion_charge_state",
    }
    assert {v.name for v in model.lower_principal.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in model.upper_principal.direct_dependencies()} == {
        "physical.lithography.source_lower_principal_quantum_number",
        "physical.lithography.source_transition_principal_quantum_step",
    }
    assert {v.name for v in model.transition_step.direct_dependencies()} == set()
    assert {v.name for v in model.shell_capacity.direct_dependencies()} == {
        "physical.lithography.source_lower_principal_quantum_number",
    }
    assert {v.name for v in model.inner_closed_capacity.direct_dependencies()} == {
        "physical.lithography.source_lower_principal_quantum_number",
    }
    assert {v.name for v in model.inner_closed_shells.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_inner_closed_shell_capacity",
        "physical.lithography.source_outer_shell_electron_count",
    }
    assert {v.name for v in model.outer_shells.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_inner_closed_shell_capacity",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in model.transition_shell_occupancy.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_inner_closed_shell_electron_count",
        "physical.lithography.source_outer_shell_electron_count",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in model.same_screeners.direct_dependencies()} == {
        "physical.lithography.source_transition_shell_occupancy",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in model.inner_screeners.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_transition_shell_occupancy",
        "physical.lithography.source_outer_shell_electron_count",
    }
    assert {v.name for v in model.inner_shielding.direct_dependencies()} == set()
    assert {v.name for v in model.same_shielding.direct_dependencies()} == set()
    assert {v.name for v in model.screening.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_inner_shell_screening_electron_count",
        "physical.lithography.source_same_shell_screening_electron_count",
        "physical.lithography.source_inner_shell_shielding_factor",
        "physical.lithography.source_same_shell_shielding_factor",
    }
    assert {v.name for v in model.z_eff.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_screening_constant",
    }
    assert {v.name for v in model.transition.direct_dependencies()} == {
        "physical.lithography.source_reduced_mass_ratio",
        "physical.lithography.source_effective_nuclear_charge",
        "physical.lithography.source_lower_principal_quantum_number",
        "physical.lithography.source_upper_principal_quantum_number",
        "physics.rydberg_energy",
    }
