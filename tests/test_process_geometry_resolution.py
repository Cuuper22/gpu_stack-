"""Process-geometry resolver paths and unit-check flags."""

import pytest

from gpu_stack import Registry, resolve


def test_resolve_channel_length_from_process_geometry():
    result = resolve(
        "physical.channel_length",
        assignments={
            "physical.process.node_length": 4.0,
            "physical.process.gate_length_scale": 1.2,
            "physical.process.gate_length_bias": -0.5,
        },
    )
    assert float(result.value) == pytest.approx(4.3)
    assert any(step.equation == "physical.eq.channel_length_process" for step in result.trace)


def test_resolve_channel_length_through_process_pitch_layer():
    result = resolve(
        "physical.channel_length",
        assignments={
            "physical.process.drawn_gate_length": 1.0,
            "physical.process.source_drain_contact_width": 1.0,
            "physical.process.gate_contact_spacing": 1.0,
            "physical.process.minimum_metal_width": 4.0,
            "physical.process.minimum_metal_spacing": 5.0,
            "physical.process.node_geometry_factor": 2.0,
            "physical.process.gate_length_scale": 0.5,
            "physical.process.gate_length_bias": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(7.0)


def test_resolve_channel_length_through_lithography_layer():
    c = Registry.variables["physics.speed_of_light"].value
    h = Registry.variables["physics.planck"].value
    pupil_radius = 3.0 ** 0.5
    focal_length = 1.0
    numerical_aperture = 3.0 ** 0.5
    wavelength = 10.0
    gate_k1 = 0.8
    gate_cd = gate_k1 * wavelength / numerical_aperture
    contact_cd = gate_k1 * wavelength / numerical_aperture
    metal_width_cd = gate_k1 * wavelength / numerical_aperture
    metal_spacing_cd = gate_k1 * wavelength / numerical_aperture
    cpp = (gate_cd + 1.0) + (contact_cd + 1.0) + 2 * (0.5 + 1.0)
    mmp = metal_width_cd + metal_spacing_cd
    expected = 1.0 + 0.5 * 2.0 * (cpp * mmp) ** 0.5
    result = resolve(
        "physical.channel_length",
        assignments={
            "physical.lithography.photon_energy": h * c / wavelength,
            "physical.lithography.medium_relative_permittivity": 4.0,
            "physical.lithography.medium_relative_permeability": 1.0,
            "physical.lithography.objective_pupil_radius": pupil_radius,
            "physical.lithography.objective_focal_length": focal_length,
            "physical.lithography.gate_k1_aerial_image_contrast_factor": 0.5,
            "physical.lithography.gate_k1_resist_process_factor": 0.7,
            "physical.lithography.gate_k1_mask_error_factor": 0.8,
            "physical.lithography.gate_k1_resolution_enhancement_factor": 1.4,
            "physical.process.gate_length_lithography_bias": 1.0,
            "physical.process.source_drain_contact_bias": 1.0,
            "physical.process.gate_contact_overlay_budget": 0.5,
            "physical.process.gate_contact_enclosure_margin": 1.0,
            "physical.process.minimum_metal_width_bias": 0.0,
            "physical.process.minimum_metal_spacing_bias": 0.0,
            "physical.process.node_geometry_factor": 2.0,
            "physical.process.gate_length_scale": 0.5,
            "physical.process.gate_length_bias": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(expected)
    assert any(
        step.equation == "physical.eq.lithography_gate_k1_from_process_factors"
        for step in result.trace
    )
    assert {
        "physical.eq.contact_k1_from_gate_baseline",
        "physical.eq.metal_width_k1_from_gate_baseline",
        "physical.eq.metal_spacing_k1_from_gate_baseline",
    } <= {step.equation for step in result.trace}


def test_channel_length_process_equation_has_unit_check():
    eq = Registry.equations["physical.eq.channel_length_process"]
    assert getattr(eq, "_check_units_flag", False)
    assert Registry.variables["physical.process.gate_length_bias"].signed is True


def test_process_node_pitch_equation_has_unit_check():
    eq = Registry.equations["physical.eq.process_node_from_pitches"]
    assert getattr(eq, "_check_units_flag", False)


def test_process_pitch_component_equations_have_unit_checks():
    checked = {
        name
        for name, eq in Registry.equations.items()
        if getattr(eq, "_check_units_flag", False)
    }
    assert {
            "physical.eq.lithography_source_valence_up_quark_count_from_zn",
            "physical.eq.lithography_source_valence_down_quark_count_from_zn",
            "physical.ineq.lithography_source_proton_count_positive",
            "physical.eq.lithography_source_atomic_number",
            "physical.eq.lithography_source_isotope_mass_number",
            "physical.eq.lithography_source_mass_number",
            "physical.eq.lithography_source_binding_volume_coefficient_from_shared_nuclear_calibration",
            "physical.eq.lithography_source_binding_surface_coefficient_from_shared_nuclear_calibration",
            "physical.eq.lithography_source_binding_coulomb_coefficient_from_shared_nuclear_calibration",
            "physical.eq.lithography_source_binding_asymmetry_coefficient_from_shared_nuclear_calibration",
            "physical.eq.lithography_source_nuclear_pairing_gap_reference_energy_from_shared_nuclear_calibration",
            "physical.eq.lithography_source_pairing_reference_mass_number",
            "physical.eq.lithography_source_neutron_excess",
            "physical.eq.lithography_source_pairing_sign",
            "physical.eq.lithography_source_nuclear_radius_coefficient",
            "physical.eq.lithography_source_nuclear_saturation_number_density",
            "physical.eq.lithography_source_nuclear_bulk_binding_energy_density",
            "physical.eq.lithography_source_nuclear_surface_tension",
            "physical.eq.lithography_source_binding_pairing_coefficient",
            "physical.eq.lithography_source_nuclear_symmetry_energy_density",
            "physical.eq.lithography_source_binding_volume_term",
            "physical.eq.lithography_source_binding_surface_term",
            "physical.eq.lithography_source_binding_coulomb_term",
            "physical.eq.lithography_source_binding_asymmetry_term",
            "physical.eq.lithography_source_binding_pairing_term",
            "physical.eq.lithography_source_nuclear_binding_energy",
            "physical.eq.lithography_source_nuclear_mass",
            "physical.eq.lithography_source_reduced_mass",
            "physical.eq.lithography_source_reduced_mass_ratio",
            "physical.eq.lithography_source_inner_shell_shielding_factor",
            "physical.eq.lithography_source_same_shell_shielding_factor",
            "physical.eq.lithography_source_transition_principal_quantum_step_from_adjacent_shells",
            "physical.eq.lithography_source_lower_principal_quantum_number",
            "physical.eq.lithography_source_upper_principal_quantum_number",
            "physical.eq.lithography_source_ionization_principal_quantum_number",
            "physical.eq.lithography_source_ionization_inner_shell_screening_electron_count",
            "physical.eq.lithography_source_ionization_same_shell_screening_electron_count",
            "physical.eq.lithography_source_ionization_screening_constant",
            "physical.eq.lithography_source_ionization_effective_nuclear_charge",
            "physical.eq.lithography_source_ionization_energy",
            "physical.eq.lithography_source_ionization_partition_ratio",
            "physical.eq.lithography_source_plasma_drive_beam_wavelength_from_ionization_edge",
            "physical.eq.lithography_source_plasma_absorption_resonance_to_drive_ratio_from_ionization_edge",
            "physical.eq.lithography_source_plasma_absorption_participating_electron_fraction_from_ionization_shell",
            "physical.eq.lithography_source_plasma_absorption_sum_rule_fraction_from_ionization_shell_degeneracy",
            "physical.eq.lithography_source_plasma_absorption_collision_orbital_radius_from_hydrogenic_shell",
            "physical.eq.lithography_source_plasma_absorption_collision_cross_section_from_orbital_area",
            "physical.eq.lithography_source_plasma_pulse_repetition_rate_from_period",
            "physical.eq.lithography_source_plasma_drive_pulse_duration_from_duty_cycle",
            "physical.eq.lithography_source_plasma_drive_pulse_fall_fraction_from_symmetric_ramp",
            "physical.eq.lithography_source_plasma_drive_pulse_flat_fraction_from_ramps",
            "physical.eq.lithography_source_plasma_drive_pulse_temporal_shape_factor_from_trapezoid",
            "physical.ineq.lithography_source_plasma_drive_pulse_ramp_fractions_within_pulse",
            "physical.eq.lithography_source_plasma_drive_peak_intensity_from_fluence",
            "physical.eq.lithography_source_plasma_drive_focus_waist_coefficient_from_gaussian_f_number",
            "physical.eq.lithography_source_plasma_drive_acceptance_half_angle_from_pupil_geometry",
            "physical.eq.lithography_source_plasma_drive_numerical_aperture_from_acceptance_angle",
            "physical.eq.lithography_source_plasma_drive_focus_f_number_from_acceptance_angle",
            "physical.ineq.lithography_source_plasma_drive_pupil_beam_fill_factor_within_unit_interval",
            "physical.eq.lithography_source_plasma_drive_beam_parameter_waist_radius_from_pupil_fill",
            "physical.eq.lithography_source_plasma_drive_beam_parameter_product_from_waist_divergence",
            "physical.ineq.lithography_source_plasma_drive_beam_parameter_product_diffraction_floor",
            "physical.eq.lithography_source_plasma_drive_beam_quality_factor_from_beam_parameter_product",
            "physical.ineq.lithography_source_plasma_drive_beam_quality_factor_diffraction_limit",
            "physical.eq.lithography_source_plasma_drive_spot_radius_from_focus",
            "physical.eq.lithography_source_plasma_drive_rayleigh_range_from_spot_geometry",
            "physical.eq.lithography_source_plasma_drive_confocal_length_from_rayleigh_range",
            "physical.eq.lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention",
            "physical.eq.lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention",
            "physical.eq.lithography_source_plasma_drive_spot_shape_factor_from_ellipse",
            "physical.eq.lithography_source_plasma_drive_spot_area_from_radius",
            "physical.eq.lithography_source_plasma_pulse_energy_from_intensity_area_duration",
            "physical.ineq.lithography_source_plasma_pulse_duration_within_period",
            "physical.eq.lithography_source_plasma_drive_power_from_pulses",
            "physical.eq.lithography_source_plasma_species_number_density_from_ideal_gas",
            "physical.eq.lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed",
            "physical.eq.lithography_source_plasma_column_radial_expansion_speed_from_species_thermal_speed",
            "physical.eq.lithography_source_plasma_column_radius_expansion_factor_from_radial_speed",
            "physical.eq.lithography_source_plasma_column_radius_from_drive_spot",
            "physical.eq.lithography_source_plasma_column_aspect_ratio_from_confocal_length",
            "physical.eq.lithography_source_plasma_column_length_from_aspect_ratio",
            "physical.eq.lithography_source_plasma_active_fill_factor_from_ideal_column_convention",
            "physical.eq.lithography_source_plasma_active_volume_from_column_geometry",
            "physical.eq.lithography_source_plasma_drive_beam_angular_frequency",
            "physical.eq.lithography_source_plasma_absorption_path_direction_cosine_from_acceptance_angle",
            "physical.eq.lithography_source_plasma_absorption_path_shape_factor_from_direction_cosine",
            "physical.eq.lithography_source_plasma_absorption_path_length_from_column",
            "physical.eq.lithography_source_plasma_absorption_resonance_from_drive_ratio",
            "physical.eq.lithography_source_plasma_absorption_damping_rate_from_species_collision",
            "physical.eq.lithography_source_plasma_absorption_quality_factor_from_collision_damping",
            "physical.eq.lithography_source_plasma_absorption_oscillator_strength_from_source_charge",
            "physical.eq.lithography_source_plasma_absorption_cross_section_from_lorentz_oscillator",
            "physical.eq.lithography_source_plasma_absorption_optical_depth",
            "physical.eq.lithography_source_plasma_drive_energy_absorption_fraction_from_optical_depth",
            "physical.eq.lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio_from_coaxial_convention",
            "physical.eq.lithography_source_plasma_drive_pointing_overlap_factor_from_offset",
            "physical.eq.lithography_source_plasma_drive_transverse_overlap_factor_from_area_ratio",
            "physical.ineq.lithography_source_plasma_drive_spot_area_within_column_cross_section",
            "physical.eq.lithography_source_plasma_drive_spatial_overlap_factor_from_geometry",
            "physical.eq.lithography_source_plasma_active_response_duration_from_drive_ratio",
            "physical.eq.lithography_source_plasma_drive_timing_offset_fraction_from_synchronized_convention",
            "physical.eq.lithography_source_plasma_drive_timing_offset_duration_from_fraction",
            "physical.eq.lithography_source_plasma_drive_temporal_duration_match_factor",
            "physical.eq.lithography_source_plasma_drive_temporal_alignment_factor_from_timing_offset",
            "physical.eq.lithography_source_plasma_drive_temporal_overlap_factor_from_duration_and_alignment",
            "physical.eq.lithography_source_plasma_drive_overlap_factor_from_spatial_temporal",
            "physical.eq.lithography_source_plasma_absorption_efficiency_from_overlap_optical_depth_heating",
            "physical.eq.lithography_source_plasma_energy_loss_path_direction_cosine_from_acceptance_angle",
            "physical.eq.lithography_source_plasma_energy_loss_path_factor_from_direction_cosine",
            "physical.eq.lithography_source_plasma_energy_loss_path_length_from_radius",
            "physical.eq.lithography_source_plasma_species_particle_mass_from_nuclear_counts",
            "physical.eq.lithography_source_plasma_species_thermal_speed_from_gas_temperature",
            "physical.eq.lithography_source_plasma_energy_loss_transport_speed_factor_from_mass_ratio",
            "physical.eq.lithography_source_plasma_energy_loss_speed_from_species_thermal_speed",
            "physical.eq.lithography_source_plasma_energy_confinement_time_from_loss_path",
            "physical.eq.lithography_source_plasma_active_lifetime_to_drive_pulse_ratio_from_energy_confinement_time",
            "physical.eq.lithography_source_plasma_free_electron_yield_per_source_particle_from_inventory_charge_fraction",
            "physical.eq.lithography_source_plasma_free_electron_count_from_species_inventory",
            "physical.eq.lithography_source_plasma_absorbed_power_from_drive",
            "physical.eq.lithography_source_plasma_electron_internal_energy_from_confinement",
            "physical.eq.lithography_source_plasma_electron_temperature_from_internal_energy",
            "physical.eq.lithography_source_plasma_electron_number_density_from_count_volume",
            "physical.eq.lithography_source_plasma_electron_mean_kinetic_energy_from_temperature",
            "physical.eq.lithography_source_plasma_debye_length_from_temperature_density",
            "physical.eq.lithography_source_saha_thermal_number_density",
            "physical.eq.lithography_source_saha_ionization_ratio",
            "physical.eq.lithography_source_saha_ionization_fraction",
            "physical.eq.lithography_source_ion_charge_state",
            "physical.eq.lithography_source_bound_electron_count",
            "physical.eq.lithography_source_transition_shell_capacity",
            "physical.eq.lithography_source_inner_closed_shell_capacity",
            "physical.eq.lithography_source_outer_shell_electron_count",
            "physical.eq.lithography_source_inner_closed_shell_electron_count",
            "physical.eq.lithography_source_transition_shell_occupancy",
            "physical.eq.lithography_source_same_shell_screening_electron_count",
            "physical.eq.lithography_source_inner_shell_screening_electron_count",
            "physical.eq.lithography_source_screening_constant",
            "physical.eq.lithography_source_effective_nuclear_charge",
            "physical.eq.lithography_source_transition_energy",
            "physical.eq.lithography_photon_energy_from_source_transition",
            "physical.eq.lithography_photon_frequency",
            "physical.eq.lithography_wavelength_from_frequency",
            "physical.eq.lithography_source_angular_frequency",
            "physical.eq.lithography_medium_component_a_valence_up_quark_count_from_zn",
            "physical.eq.lithography_medium_component_a_valence_down_quark_count_from_zn",
            "physical.eq.lithography_medium_component_b_valence_up_quark_count_from_zn",
            "physical.eq.lithography_medium_component_b_valence_down_quark_count_from_zn",
            "physical.ineq.lithography_medium_component_a_proton_count_positive",
            "physical.ineq.lithography_medium_component_b_proton_count_positive",
            "physical.eq.lithography_medium_component_a_atomic_number",
            "physical.eq.lithography_medium_component_b_atomic_number",
            "physical.eq.lithography_medium_component_a_isotope_mass_number",
            "physical.eq.lithography_medium_component_b_isotope_mass_number",
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
            "physical.eq.lithography_medium_formula_unit_electron_count",
            "physical.eq.lithography_medium_formula_unit_binding_energy",
            "physical.eq.lithography_medium_formula_unit_rest_mass",
            "physical.eq.lithography_medium_molar_mass",
            "physical.eq.lithography_medium_particle_mass",
            "physical.ineq.lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity",
            "physical.eq.lithography_medium_formula_unit_packing_length_from_intercomponent_separation_scale",
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
            "physical.eq.lithography_medium_refractive_index",
            "physical.eq.lithography_acceptance_half_angle",
            "physical.ineq.lithography_acceptance_half_angle_within_forward_half_space",
            "physical.eq.lithography_numerical_aperture",
            "physical.ineq.lithography_numerical_aperture_within_medium_index",
            "physical.eq.lithography_gate_k1_from_process_factors",
        "physical.eq.gate_lithography_resolution",
        "physical.eq.contact_lithography_resolution",
        "physical.eq.metal_width_lithography_resolution",
        "physical.eq.metal_spacing_lithography_resolution",
        "physical.eq.drawn_gate_length",
        "physical.eq.source_drain_contact_width",
        "physical.eq.gate_contact_spacing",
        "physical.eq.minimum_metal_width",
        "physical.eq.minimum_metal_spacing",
        "physical.eq.contacted_gate_pitch",
        "physical.eq.minimum_metal_pitch",
    } <= checked
