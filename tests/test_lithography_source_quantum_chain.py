"""Lithography source quantum-chain structure coverage."""

import sympy as sp

from gpu_stack import Registry
from gpu_stack.core import Inequality, RelationRole


def test_lithography_photon_energy_has_quantum_source_model():
    photon_energy = Registry.variables["physical.lithography.photon_energy"]
    up_quarks = Registry.variables[
        "physical.lithography.source_valence_up_quark_count"
    ]
    down_quarks = Registry.variables[
        "physical.lithography.source_valence_down_quark_count"
    ]
    atomic_number = Registry.variables["physical.lithography.source_atomic_number"]
    isotope_mass_number = Registry.variables["physical.lithography.source_isotope_mass_number"]
    proton_count = Registry.variables["physical.lithography.source_proton_count"]
    neutron_count = Registry.variables["physical.lithography.source_neutron_count"]
    binding_energy = Registry.variables["physical.lithography.source_nuclear_binding_energy"]
    mass_number = Registry.variables["physical.lithography.source_mass_number"]
    neutron_excess = Registry.variables["physical.lithography.source_neutron_excess"]
    saturation_density = Registry.variables[
        "physical.lithography.source_nuclear_saturation_number_density"
    ]
    radius_coeff = Registry.variables["physical.lithography.source_nuclear_radius_coefficient"]
    bulk_binding_density = Registry.variables[
        "physical.lithography.source_nuclear_bulk_binding_energy_density"
    ]
    volume_coeff = Registry.variables["physical.lithography.source_binding_volume_coefficient"]
    surface_tension = Registry.variables["physical.lithography.source_nuclear_surface_tension"]
    surface_coeff = Registry.variables["physical.lithography.source_binding_surface_coefficient"]
    symmetry_density = Registry.variables["physical.lithography.source_nuclear_symmetry_energy_density"]
    asymmetry_coeff = Registry.variables["physical.lithography.source_binding_asymmetry_coefficient"]
    pairing_gap_ref = Registry.variables[
        "physical.lithography.source_nuclear_pairing_gap_reference_energy"
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
    shared_pairing_gap_ref = Registry.variables[
        "physical.lithography.nuclear_pairing_gap_reference_energy"
    ]
    pairing_mass_ref = Registry.variables[
        "physical.lithography.source_pairing_reference_mass_number"
    ]
    pairing_coeff = Registry.variables["physical.lithography.source_binding_pairing_coefficient"]
    coulomb_coeff = Registry.variables["physical.lithography.source_binding_coulomb_coefficient"]
    volume_term = Registry.variables["physical.lithography.source_binding_volume_term"]
    surface_term = Registry.variables["physical.lithography.source_binding_surface_term"]
    coulomb_term = Registry.variables["physical.lithography.source_binding_coulomb_term"]
    asymmetry_term = Registry.variables["physical.lithography.source_binding_asymmetry_term"]
    pairing_sign = Registry.variables["physical.lithography.source_pairing_sign"]
    pairing_term = Registry.variables["physical.lithography.source_binding_pairing_term"]
    nuclear_mass = Registry.variables["physical.lithography.source_nuclear_mass"]
    reduced_mass = Registry.variables["physical.lithography.source_reduced_mass"]
    reduced_ratio = Registry.variables["physical.lithography.source_reduced_mass_ratio"]
    ion_charge_state = Registry.variables["physical.lithography.source_ion_charge_state"]
    plasma_mean_energy = Registry.variables[
        "physical.lithography.source_plasma_electron_mean_kinetic_energy"
    ]
    plasma_debye_length = Registry.variables[
        "physical.lithography.source_plasma_debye_length"
    ]
    plasma_pulse_period = Registry.variables[
        "physical.lithography.source_plasma_pulse_period"
    ]
    plasma_pulse_energy = Registry.variables[
        "physical.lithography.source_plasma_pulse_energy"
    ]
    plasma_pulse_repetition_rate = Registry.variables[
        "physical.lithography.source_plasma_pulse_repetition_rate"
    ]
    plasma_drive_pulse_duty_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_duty_factor"
    ]
    plasma_drive_pulse_fluence = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_fluence"
    ]
    plasma_drive_peak_intensity = Registry.variables[
        "physical.lithography.source_plasma_drive_peak_intensity"
    ]
    plasma_drive_pulse_duration = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_duration"
    ]
    plasma_drive_pulse_rise_fraction = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_rise_fraction"
    ]
    plasma_drive_pulse_fall_fraction = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_fall_fraction"
    ]
    plasma_drive_pulse_flat_fraction = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_flat_fraction"
    ]
    plasma_drive_pulse_temporal_shape_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor"
    ]
    plasma_drive_beam_wavelength = Registry.variables[
        "physical.lithography.source_plasma_drive_beam_wavelength"
    ]
    plasma_drive_edge_detuning_ratio = Registry.variables[
        "physical.lithography.source_plasma_drive_edge_detuning_ratio"
    ]
    plasma_drive_objective_pupil_radius = Registry.variables[
        "physical.lithography.source_plasma_drive_objective_pupil_radius"
    ]
    plasma_drive_objective_focal_length = Registry.variables[
        "physical.lithography.source_plasma_drive_objective_focal_length"
    ]
    plasma_drive_pupil_beam_fill_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_pupil_beam_fill_factor"
    ]
    plasma_drive_acceptance_half_angle = Registry.variables[
        "physical.lithography.source_plasma_drive_acceptance_half_angle"
    ]
    plasma_drive_numerical_aperture = Registry.variables[
        "physical.lithography.source_plasma_drive_numerical_aperture"
    ]
    plasma_drive_focus_f_number = Registry.variables[
        "physical.lithography.source_plasma_drive_focus_f_number"
    ]
    plasma_drive_beam_parameter_waist_radius = Registry.variables[
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius"
    ]
    plasma_drive_far_field_divergence_half_angle = Registry.variables[
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle"
    ]
    plasma_drive_beam_parameter_product = Registry.variables[
        "physical.lithography.source_plasma_drive_beam_parameter_product"
    ]
    plasma_drive_beam_quality_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_beam_quality_factor"
    ]
    plasma_drive_focus_waist_coefficient = Registry.variables[
        "physical.lithography.source_plasma_drive_focus_waist_coefficient"
    ]
    plasma_drive_spot_radius = Registry.variables[
        "physical.lithography.source_plasma_drive_spot_radius"
    ]
    plasma_drive_rayleigh_range = Registry.variables[
        "physical.lithography.source_plasma_drive_rayleigh_range"
    ]
    plasma_drive_confocal_length = Registry.variables[
        "physical.lithography.source_plasma_drive_confocal_length"
    ]
    plasma_drive_spot_axis_ratio = Registry.variables[
        "physical.lithography.source_plasma_drive_spot_axis_ratio"
    ]
    plasma_drive_spot_area_fill_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_spot_area_fill_factor"
    ]
    plasma_drive_spot_shape_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_spot_shape_factor"
    ]
    plasma_drive_spot_area = Registry.variables[
        "physical.lithography.source_plasma_drive_spot_area"
    ]
    plasma_drive_power = Registry.variables[
        "physical.lithography.source_plasma_drive_power"
    ]
    plasma_species_partial_pressure = Registry.variables[
        "physical.lithography.source_plasma_species_partial_pressure"
    ]
    plasma_species_gas_temperature = Registry.variables[
        "physical.lithography.source_plasma_species_gas_temperature"
    ]
    plasma_species_number_density = Registry.variables[
        "physical.lithography.source_plasma_species_number_density"
    ]
    plasma_column_expansion_speed_factor = Registry.variables[
        "physical.lithography.source_plasma_column_expansion_speed_factor"
    ]
    plasma_column_radial_expansion_speed = Registry.variables[
        "physical.lithography.source_plasma_column_radial_expansion_speed"
    ]
    plasma_column_radius_expansion_factor = Registry.variables[
        "physical.lithography.source_plasma_column_radius_expansion_factor"
    ]
    plasma_column_radius = Registry.variables[
        "physical.lithography.source_plasma_column_radius"
    ]
    plasma_column_aspect_ratio = Registry.variables[
        "physical.lithography.source_plasma_column_aspect_ratio"
    ]
    plasma_column_length = Registry.variables[
        "physical.lithography.source_plasma_column_length"
    ]
    plasma_active_fill_factor = Registry.variables[
        "physical.lithography.source_plasma_active_fill_factor"
    ]
    plasma_active_volume = Registry.variables[
        "physical.lithography.source_plasma_active_volume"
    ]
    plasma_absorption_path_direction_cosine = Registry.variables[
        "physical.lithography.source_plasma_absorption_path_direction_cosine"
    ]
    plasma_absorption_path_shape_factor = Registry.variables[
        "physical.lithography.source_plasma_absorption_path_shape_factor"
    ]
    plasma_absorption_path_length = Registry.variables[
        "physical.lithography.source_plasma_absorption_path_length"
    ]
    plasma_drive_beam_angular_frequency = Registry.variables[
        "physical.lithography.source_plasma_drive_beam_angular_frequency"
    ]
    plasma_absorption_resonance_to_drive_ratio = Registry.variables[
        "physical.lithography.source_plasma_absorption_resonance_to_drive_ratio"
    ]
    plasma_absorption_quality_factor = Registry.variables[
        "physical.lithography.source_plasma_absorption_quality_factor"
    ]
    plasma_absorption_collision_cross_section = Registry.variables[
        "physical.lithography.source_plasma_absorption_collision_cross_section"
    ]
    plasma_absorption_collision_orbital_radius = Registry.variables[
        "physical.lithography.source_plasma_absorption_collision_orbital_radius"
    ]
    plasma_absorption_participating_electron_fraction = Registry.variables[
        "physical.lithography.source_plasma_absorption_participating_electron_fraction"
    ]
    plasma_absorption_sum_rule_fraction = Registry.variables[
        "physical.lithography.source_plasma_absorption_sum_rule_fraction"
    ]
    plasma_absorption_resonance = Registry.variables[
        "physical.lithography.source_plasma_absorption_resonance_angular_frequency"
    ]
    plasma_absorption_damping_rate = Registry.variables[
        "physical.lithography.source_plasma_absorption_damping_rate"
    ]
    plasma_absorption_oscillator_strength = Registry.variables[
        "physical.lithography.source_plasma_absorption_oscillator_strength"
    ]
    plasma_absorption_cross_section = Registry.variables[
        "physical.lithography.source_plasma_absorption_cross_section"
    ]
    plasma_absorption_optical_depth = Registry.variables[
        "physical.lithography.source_plasma_absorption_optical_depth"
    ]
    plasma_drive_energy_absorption_fraction = Registry.variables[
        "physical.lithography.source_plasma_drive_energy_absorption_fraction"
    ]
    plasma_drive_centroid_offset_to_column_radius_ratio = Registry.variables[
        "physical.lithography.source_plasma_drive_centroid_offset_to_column_radius_ratio"
    ]
    plasma_drive_pointing_overlap_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_pointing_overlap_factor"
    ]
    plasma_drive_transverse_overlap_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_transverse_overlap_factor"
    ]
    plasma_drive_spatial_overlap_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_spatial_overlap_factor"
    ]
    plasma_active_lifetime_to_drive_pulse_ratio = Registry.variables[
        "physical.lithography.source_plasma_active_lifetime_to_drive_pulse_ratio"
    ]
    plasma_active_response_duration = Registry.variables[
        "physical.lithography.source_plasma_active_response_duration"
    ]
    plasma_drive_timing_offset_fraction = Registry.variables[
        "physical.lithography.source_plasma_drive_timing_offset_fraction"
    ]
    plasma_drive_timing_offset_duration = Registry.variables[
        "physical.lithography.source_plasma_drive_timing_offset_duration"
    ]
    plasma_drive_temporal_duration_match_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_temporal_duration_match_factor"
    ]
    plasma_drive_temporal_alignment_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_temporal_alignment_factor"
    ]
    plasma_drive_temporal_overlap_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_temporal_overlap_factor"
    ]
    plasma_drive_overlap_factor = Registry.variables[
        "physical.lithography.source_plasma_drive_overlap_factor"
    ]
    plasma_electron_heating_fraction = Registry.variables[
        "physical.lithography.source_plasma_electron_heating_fraction"
    ]
    plasma_absorption_efficiency = Registry.variables[
        "physical.lithography.source_plasma_absorption_efficiency"
    ]
    plasma_absorbed_power = Registry.variables[
        "physical.lithography.source_plasma_absorbed_power"
    ]
    plasma_energy_loss_path_direction_cosine = Registry.variables[
        "physical.lithography.source_plasma_energy_loss_path_direction_cosine"
    ]
    plasma_energy_loss_path_factor = Registry.variables[
        "physical.lithography.source_plasma_energy_loss_path_factor"
    ]
    plasma_energy_loss_path_length = Registry.variables[
        "physical.lithography.source_plasma_energy_loss_path_length"
    ]
    plasma_species_particle_mass = Registry.variables[
        "physical.lithography.source_plasma_species_particle_mass"
    ]
    plasma_energy_loss_transport_speed_factor = Registry.variables[
        "physical.lithography.source_plasma_energy_loss_transport_speed_factor"
    ]
    plasma_species_thermal_speed = Registry.variables[
        "physical.lithography.source_plasma_species_thermal_speed"
    ]
    plasma_energy_loss_speed = Registry.variables[
        "physical.lithography.source_plasma_energy_loss_speed"
    ]
    plasma_confinement_time = Registry.variables[
        "physical.lithography.source_plasma_energy_confinement_time"
    ]
    plasma_free_electron_inventory_charge_fraction = Registry.variables[
        "physical.lithography.source_plasma_free_electron_inventory_charge_fraction"
    ]
    plasma_free_electron_yield = Registry.variables[
        "physical.lithography.source_plasma_free_electron_yield_per_source_particle"
    ]
    plasma_free_electron_count = Registry.variables[
        "physical.lithography.source_plasma_free_electron_count"
    ]
    plasma_internal_energy = Registry.variables[
        "physical.lithography.source_plasma_electron_internal_energy"
    ]
    plasma_temperature = Registry.variables[
        "physical.lithography.source_plasma_electron_temperature"
    ]
    plasma_density = Registry.variables[
        "physical.lithography.source_plasma_electron_number_density"
    ]
    ionization_energy = Registry.variables["physical.lithography.source_ionization_energy"]
    ionization_principal = Registry.variables[
        "physical.lithography.source_ionization_principal_quantum_number"
    ]
    ionization_screening = Registry.variables[
        "physical.lithography.source_ionization_screening_constant"
    ]
    ionization_inner_screeners = Registry.variables[
        "physical.lithography.source_ionization_inner_shell_screening_electron_count"
    ]
    ionization_same_screeners = Registry.variables[
        "physical.lithography.source_ionization_same_shell_screening_electron_count"
    ]
    ionization_z_eff = Registry.variables[
        "physical.lithography.source_ionization_effective_nuclear_charge"
    ]
    partition_ratio = Registry.variables[
        "physical.lithography.source_ionization_partition_ratio"
    ]
    saha_thermal_density = Registry.variables[
        "physical.lithography.source_saha_thermal_number_density"
    ]
    saha_ratio = Registry.variables["physical.lithography.source_saha_ionization_ratio"]
    saha_fraction = Registry.variables["physical.lithography.source_saha_ionization_fraction"]
    bound_electrons = Registry.variables["physical.lithography.source_bound_electron_count"]
    lower_principal = Registry.variables[
        "physical.lithography.source_lower_principal_quantum_number"
    ]
    upper_principal = Registry.variables[
        "physical.lithography.source_upper_principal_quantum_number"
    ]
    transition_step = Registry.variables[
        "physical.lithography.source_transition_principal_quantum_step"
    ]
    shell_capacity = Registry.variables["physical.lithography.source_transition_shell_capacity"]
    inner_closed_capacity = Registry.variables[
        "physical.lithography.source_inner_closed_shell_capacity"
    ]
    inner_closed_shells = Registry.variables[
        "physical.lithography.source_inner_closed_shell_electron_count"
    ]
    outer_shells = Registry.variables[
        "physical.lithography.source_outer_shell_electron_count"
    ]
    transition_shell_occupancy = Registry.variables[
        "physical.lithography.source_transition_shell_occupancy"
    ]
    inner_screeners = Registry.variables["physical.lithography.source_inner_shell_screening_electron_count"]
    same_screeners = Registry.variables["physical.lithography.source_same_shell_screening_electron_count"]
    inner_shielding = Registry.variables["physical.lithography.source_inner_shell_shielding_factor"]
    same_shielding = Registry.variables["physical.lithography.source_same_shell_shielding_factor"]
    screening = Registry.variables["physical.lithography.source_screening_constant"]
    z_eff = Registry.variables["physical.lithography.source_effective_nuclear_charge"]
    transition = Registry.variables["physical.lithography.source_transition_energy"]
    assert not photon_energy.is_root_input
    assert up_quarks.is_root_input
    assert down_quarks.is_root_input
    assert not atomic_number.is_root_input
    assert not isotope_mass_number.is_root_input
    assert not proton_count.is_root_input
    assert not neutron_count.is_root_input
    assert len(proton_count.defining_equations) == 1
    assert len(neutron_count.defining_equations) == 1
    assert not proton_count.has_multiple_definitions()
    assert not neutron_count.has_multiple_definitions()
    assert not binding_energy.is_root_input
    assert not mass_number.is_root_input
    assert not neutron_excess.is_root_input
    assert not saturation_density.is_root_input
    assert not radius_coeff.is_root_input
    assert not bulk_binding_density.is_root_input
    assert shared_volume_coeff.is_root_input
    assert shared_surface_coeff.is_root_input
    assert shared_coulomb_coeff.is_root_input
    assert shared_asymmetry_coeff.is_root_input
    assert shared_pairing_gap_ref.is_root_input
    assert not volume_coeff.is_root_input
    assert not surface_tension.is_root_input
    assert not surface_coeff.is_root_input
    assert not symmetry_density.is_root_input
    assert not asymmetry_coeff.is_root_input
    assert not pairing_gap_ref.is_root_input
    assert not pairing_mass_ref.is_root_input
    assert not pairing_coeff.is_root_input
    assert not coulomb_coeff.is_root_input
    assert not volume_term.is_root_input
    assert not surface_term.is_root_input
    assert not coulomb_term.is_root_input
    assert not asymmetry_term.is_root_input
    assert not pairing_sign.is_root_input
    assert not pairing_term.is_root_input
    assert not nuclear_mass.is_root_input
    assert not reduced_mass.is_root_input
    assert not reduced_ratio.is_root_input
    assert not ion_charge_state.is_root_input
    assert not plasma_mean_energy.is_root_input
    assert not plasma_debye_length.is_root_input
    assert plasma_pulse_period.is_root_input
    assert not plasma_pulse_repetition_rate.is_root_input
    assert plasma_drive_pulse_duty_factor.is_root_input
    assert plasma_drive_pulse_fluence.is_root_input
    assert not plasma_drive_peak_intensity.is_root_input
    assert not plasma_drive_pulse_duration.is_root_input
    assert plasma_drive_pulse_rise_fraction.is_root_input
    assert not plasma_drive_pulse_fall_fraction.is_root_input
    assert not plasma_drive_pulse_flat_fraction.is_root_input
    assert not plasma_drive_pulse_temporal_shape_factor.is_root_input
    assert not plasma_drive_beam_wavelength.is_root_input
    assert plasma_drive_edge_detuning_ratio.is_root_input
    assert plasma_drive_objective_pupil_radius.is_root_input
    assert plasma_drive_objective_focal_length.is_root_input
    assert plasma_drive_pupil_beam_fill_factor.is_root_input
    assert not plasma_drive_acceptance_half_angle.is_root_input
    assert not plasma_drive_numerical_aperture.is_root_input
    assert not plasma_drive_focus_f_number.is_root_input
    assert not plasma_drive_beam_parameter_waist_radius.is_root_input
    assert plasma_drive_far_field_divergence_half_angle.is_root_input
    assert not plasma_drive_beam_parameter_product.is_root_input
    assert not plasma_drive_beam_quality_factor.is_root_input
    assert not plasma_drive_focus_waist_coefficient.is_root_input
    assert not plasma_drive_spot_radius.is_root_input
    assert not plasma_drive_rayleigh_range.is_root_input
    assert not plasma_drive_confocal_length.is_root_input
    assert not plasma_drive_spot_axis_ratio.is_root_input
    assert not plasma_drive_spot_area_fill_factor.is_root_input
    assert not plasma_drive_spot_shape_factor.is_root_input
    assert not plasma_drive_spot_area.is_root_input
    assert not plasma_pulse_energy.is_root_input
    assert not plasma_drive_power.is_root_input
    assert plasma_species_partial_pressure.is_root_input
    assert plasma_species_gas_temperature.is_root_input
    assert not plasma_species_number_density.is_root_input
    assert not plasma_column_expansion_speed_factor.is_root_input
    assert not plasma_column_radial_expansion_speed.is_root_input
    assert not plasma_column_radius_expansion_factor.is_root_input
    assert not plasma_column_radius.is_root_input
    assert not plasma_column_aspect_ratio.is_root_input
    assert not plasma_column_length.is_root_input
    assert not plasma_active_fill_factor.is_root_input
    assert not plasma_active_volume.is_root_input
    assert not plasma_absorption_path_direction_cosine.is_root_input
    assert not plasma_absorption_path_shape_factor.is_root_input
    assert not plasma_absorption_path_length.is_root_input
    assert not plasma_drive_beam_angular_frequency.is_root_input
    assert not plasma_absorption_resonance_to_drive_ratio.is_root_input
    assert not plasma_absorption_quality_factor.is_root_input
    assert not plasma_absorption_collision_cross_section.is_root_input
    assert not plasma_absorption_collision_orbital_radius.is_root_input
    assert not plasma_absorption_participating_electron_fraction.is_root_input
    assert not plasma_absorption_sum_rule_fraction.is_root_input
    assert not plasma_absorption_resonance.is_root_input
    assert not plasma_absorption_damping_rate.is_root_input
    assert not plasma_absorption_oscillator_strength.is_root_input
    assert not plasma_absorption_cross_section.is_root_input
    assert not plasma_absorption_optical_depth.is_root_input
    assert not plasma_drive_energy_absorption_fraction.is_root_input
    assert not plasma_drive_centroid_offset_to_column_radius_ratio.is_root_input
    assert not plasma_drive_pointing_overlap_factor.is_root_input
    assert not plasma_drive_transverse_overlap_factor.is_root_input
    assert not plasma_drive_spatial_overlap_factor.is_root_input
    assert not plasma_active_lifetime_to_drive_pulse_ratio.is_root_input
    assert not plasma_active_response_duration.is_root_input
    assert not plasma_drive_timing_offset_fraction.is_root_input
    assert not plasma_drive_timing_offset_duration.is_root_input
    assert not plasma_drive_temporal_duration_match_factor.is_root_input
    assert not plasma_drive_temporal_alignment_factor.is_root_input
    assert not plasma_drive_temporal_overlap_factor.is_root_input
    assert not plasma_drive_overlap_factor.is_root_input
    assert plasma_electron_heating_fraction.is_root_input
    assert not plasma_absorption_efficiency.is_root_input
    assert not plasma_absorbed_power.is_root_input
    assert not plasma_energy_loss_path_direction_cosine.is_root_input
    assert not plasma_energy_loss_path_factor.is_root_input
    assert not plasma_energy_loss_path_length.is_root_input
    assert not plasma_species_particle_mass.is_root_input
    assert not plasma_energy_loss_transport_speed_factor.is_root_input
    assert not plasma_species_thermal_speed.is_root_input
    assert not plasma_energy_loss_speed.is_root_input
    assert not plasma_confinement_time.is_root_input
    assert plasma_free_electron_inventory_charge_fraction.is_root_input
    assert not plasma_free_electron_yield.is_root_input
    assert not plasma_free_electron_count.is_root_input
    assert not plasma_internal_energy.is_root_input
    assert not plasma_temperature.is_root_input
    assert not plasma_density.is_root_input
    assert not ionization_energy.is_root_input
    assert not ionization_principal.is_root_input
    assert not ionization_screening.is_root_input
    assert not ionization_inner_screeners.is_root_input
    assert not ionization_same_screeners.is_root_input
    assert not ionization_z_eff.is_root_input
    assert not partition_ratio.is_root_input
    assert not saha_thermal_density.is_root_input
    assert not saha_ratio.is_root_input
    assert not saha_fraction.is_root_input
    assert not bound_electrons.is_root_input
    assert not lower_principal.is_root_input
    assert not upper_principal.is_root_input
    assert not transition_step.is_root_input
    assert not shell_capacity.is_root_input
    assert not inner_closed_capacity.is_root_input
    assert not inner_closed_shells.is_root_input
    assert not outer_shells.is_root_input
    assert not transition_shell_occupancy.is_root_input
    assert not inner_screeners.is_root_input
    assert not same_screeners.is_root_input
    assert not inner_shielding.is_root_input
    assert not same_shielding.is_root_input
    assert not screening.is_root_input
    assert not z_eff.is_root_input
    assert not transition.is_root_input
    assert {v.name for v in atomic_number.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in isotope_mass_number.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
    }
    assert {v.name for v in up_quarks.direct_dependencies()} == set()
    assert {v.name for v in down_quarks.direct_dependencies()} == set()
    assert {
        v.name for v in up_quarks.direct_dependencies(include_constraints=True)
    } == {
        "physical.lithography.source_valence_down_quark_count",
    }
    assert {
        v.name for v in down_quarks.direct_dependencies(include_constraints=True)
    } == {
        "physical.lithography.source_valence_up_quark_count",
    }
    assert {v.name for v in proton_count.direct_dependencies()} == {
        "physical.lithography.source_valence_down_quark_count",
        "physical.lithography.source_valence_up_quark_count",
    }
    assert {v.name for v in neutron_count.direct_dependencies()} == {
        "physical.lithography.source_valence_down_quark_count",
        "physical.lithography.source_valence_up_quark_count",
    }
    assert {v.name for v in mass_number.direct_dependencies()} == {
        "physical.lithography.source_isotope_mass_number",
    }
    assert {v.name for v in neutron_excess.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
    }
    assert {v.name for v in radius_coeff.direct_dependencies()} == {
        "physical.lithography.source_binding_coulomb_coefficient",
        "physics.elementary_charge",
        "physics.vacuum_permittivity",
    }
    assert {v.name for v in saturation_density.direct_dependencies()} == {
        "physical.lithography.source_nuclear_radius_coefficient",
    }
    assert {v.name for v in bulk_binding_density.direct_dependencies()} == {
        "physical.lithography.source_binding_volume_coefficient",
        "physical.lithography.source_nuclear_saturation_number_density",
    }
    assert {v.name for v in volume_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_volume_coefficient",
    }
    assert {v.name for v in surface_tension.direct_dependencies()} == {
        "physical.lithography.source_binding_surface_coefficient",
        "physical.lithography.source_nuclear_radius_coefficient",
    }
    assert {v.name for v in surface_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_surface_coefficient",
    }
    assert {v.name for v in symmetry_density.direct_dependencies()} == {
        "physical.lithography.source_binding_asymmetry_coefficient",
        "physical.lithography.source_nuclear_saturation_number_density",
    }
    assert {v.name for v in asymmetry_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_asymmetry_coefficient",
    }
    assert {v.name for v in pairing_mass_ref.direct_dependencies()} == {
        "physical.lithography.source_mass_number",
    }
    pairing_ref_eq = Registry.equations[
        "physical.eq.lithography_source_pairing_reference_mass_number"
    ]
    assert pairing_mass_ref.approximations() == [pairing_ref_eq]
    assert pairing_ref_eq.role is RelationRole.APPROXIMATION
    assert str(pairing_ref_eq.validity) == "A_litho_src > 0"
    assert pairing_ref_eq.references
    assert getattr(pairing_ref_eq, "_check_units_flag", False)
    assert {v.name for v in pairing_coeff.direct_dependencies()} == {
        "physical.lithography.source_nuclear_pairing_gap_reference_energy",
        "physical.lithography.source_pairing_reference_mass_number",
    }
    assert {v.name for v in pairing_gap_ref.direct_dependencies()} == {
        "physical.lithography.nuclear_pairing_gap_reference_energy",
    }
    assert {v.name for v in coulomb_coeff.direct_dependencies()} == {
        "physical.lithography.nuclear_binding_coulomb_coefficient",
    }
    assert {v.name for v in volume_term.direct_dependencies()} == {
        "physical.lithography.source_binding_volume_coefficient",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in surface_term.direct_dependencies()} == {
        "physical.lithography.source_binding_surface_coefficient",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in coulomb_term.direct_dependencies()} == {
        "physical.lithography.source_binding_coulomb_coefficient",
        "physical.lithography.source_proton_count",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in asymmetry_term.direct_dependencies()} == {
        "physical.lithography.source_binding_asymmetry_coefficient",
        "physical.lithography.source_neutron_excess",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in pairing_sign.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
    }
    assert {v.name for v in pairing_term.direct_dependencies()} == {
        "physical.lithography.source_binding_pairing_coefficient",
        "physical.lithography.source_pairing_sign",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in binding_energy.direct_dependencies()} == {
        "physical.lithography.source_binding_volume_term",
        "physical.lithography.source_binding_surface_term",
        "physical.lithography.source_binding_coulomb_term",
        "physical.lithography.source_binding_asymmetry_term",
        "physical.lithography.source_binding_pairing_term",
        "physical.lithography.source_mass_number",
    }
    assert {v.name for v in nuclear_mass.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_neutron_count",
        "physical.lithography.source_nuclear_binding_energy",
        "physics.proton_mass",
        "physics.neutron_mass",
        "physics.speed_of_light",
    }
    assert {v.name for v in reduced_mass.direct_dependencies()} == {
        "physical.lithography.source_nuclear_mass",
        "physics.electron_mass",
    }
    assert {v.name for v in reduced_ratio.direct_dependencies()} == {
        "physical.lithography.source_reduced_mass",
        "physics.electron_mass",
    }
    assert {v.name for v in ionization_principal.direct_dependencies()} == {
        "physical.lithography.source_lower_principal_quantum_number",
    }
    assert {v.name for v in ionization_inner_screeners.direct_dependencies()} == {
        "physical.lithography.source_inner_closed_shell_capacity",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in ionization_same_screeners.direct_dependencies()} == {
        "physical.lithography.source_ionization_inner_shell_screening_electron_count",
        "physical.lithography.source_proton_count",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in ionization_screening.direct_dependencies()} == {
        "physical.lithography.source_ionization_inner_shell_screening_electron_count",
        "physical.lithography.source_ionization_same_shell_screening_electron_count",
        "physical.lithography.source_inner_shell_shielding_factor",
        "physical.lithography.source_proton_count",
        "physical.lithography.source_same_shell_shielding_factor",
    }
    assert {v.name for v in ionization_z_eff.direct_dependencies()} == {
        "physical.lithography.source_ionization_screening_constant",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in ionization_energy.direct_dependencies()} == {
        "physical.lithography.source_ionization_effective_nuclear_charge",
        "physical.lithography.source_ionization_principal_quantum_number",
        "physics.rydberg_energy",
    }
    assert {v.name for v in partition_ratio.direct_dependencies()} == {
        "physical.lithography.source_ionization_same_shell_screening_electron_count",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in plasma_pulse_repetition_rate.direct_dependencies()} == {
        "physical.lithography.source_plasma_pulse_period",
    }
    assert plasma_drive_pulse_duty_factor.direct_dependencies() == set()
    assert plasma_drive_pulse_fluence.direct_dependencies() == set()
    assert {v.name for v in plasma_drive_pulse_duration.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_duty_factor",
        "physical.lithography.source_plasma_pulse_period",
    }
    assert plasma_drive_pulse_rise_fraction.direct_dependencies() == set()
    assert {v.name for v in plasma_drive_pulse_fall_fraction.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_rise_fraction",
    }
    assert {v.name for v in plasma_drive_pulse_flat_fraction.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_fall_fraction",
        "physical.lithography.source_plasma_drive_pulse_rise_fraction",
    }
    assert {
        v.name for v in plasma_drive_pulse_temporal_shape_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_drive_pulse_fall_fraction",
        "physical.lithography.source_plasma_drive_pulse_flat_fraction",
        "physical.lithography.source_plasma_drive_pulse_rise_fraction",
    }
    assert {v.name for v in plasma_drive_peak_intensity.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_pulse_fluence",
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
    }
    assert plasma_drive_focus_waist_coefficient.direct_dependencies() == set()
    assert {v.name for v in plasma_drive_beam_wavelength.direct_dependencies()} == {
        "physical.lithography.source_ionization_energy",
        "physical.lithography.source_plasma_drive_edge_detuning_ratio",
        "physics.hbar",
        "physics.speed_of_light",
    }
    assert {v.name for v in plasma_drive_acceptance_half_angle.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_objective_focal_length",
        "physical.lithography.source_plasma_drive_objective_pupil_radius",
    }
    assert {v.name for v in plasma_drive_numerical_aperture.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    }
    assert {v.name for v in plasma_drive_focus_f_number.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    }
    assert {
        v.name for v in plasma_drive_beam_parameter_waist_radius.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_drive_objective_pupil_radius",
        "physical.lithography.source_plasma_drive_pupil_beam_fill_factor",
    }
    assert {v.name for v in plasma_drive_beam_parameter_product.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius",
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle",
    }
    assert {
        v.name
        for v in plasma_drive_beam_parameter_product.direct_dependencies(
            include_constraints=True
        )
    } == {
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius",
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle",
        "physical.lithography.source_plasma_drive_beam_wavelength",
    }
    beam_parameter_product_floor = plasma_drive_beam_parameter_product.constraints()[0]
    assert isinstance(beam_parameter_product_floor, Inequality)
    assert beam_parameter_product_floor.name == (
        "physical.ineq.lithography_source_plasma_drive_beam_parameter_product_diffraction_floor"
    )
    assert beam_parameter_product_floor.role is RelationRole.CONSTRAINT
    assert beam_parameter_product_floor.op == ">="
    assert isinstance(beam_parameter_product_floor.as_sympy(), sp.Rel)
    assert beam_parameter_product_floor.references
    assert getattr(beam_parameter_product_floor, "_check_units_flag", False)
    assert {v.name for v in plasma_drive_beam_quality_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_parameter_product",
        "physical.lithography.source_plasma_drive_beam_wavelength",
    }
    assert {
        v.name
        for v in plasma_drive_beam_quality_factor.direct_dependencies(
            include_constraints=True
        )
    } == {
        "physical.lithography.source_plasma_drive_beam_parameter_product",
        "physical.lithography.source_plasma_drive_beam_wavelength",
    }
    beam_quality_factor_floor = plasma_drive_beam_quality_factor.constraints()[0]
    assert isinstance(beam_quality_factor_floor, Inequality)
    assert beam_quality_factor_floor.name == (
        "physical.ineq.lithography_source_plasma_drive_beam_quality_factor_diffraction_limit"
    )
    assert beam_quality_factor_floor.role is RelationRole.CONSTRAINT
    assert beam_quality_factor_floor.op == ">="
    assert isinstance(beam_quality_factor_floor.as_sympy(), sp.Rel)
    assert beam_quality_factor_floor.references
    assert getattr(beam_quality_factor_floor, "_check_units_flag", False)
    assert {v.name for v in plasma_drive_spot_radius.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_quality_factor",
        "physical.lithography.source_plasma_drive_beam_wavelength",
        "physical.lithography.source_plasma_drive_focus_f_number",
        "physical.lithography.source_plasma_drive_focus_waist_coefficient",
    }
    assert {v.name for v in plasma_drive_rayleigh_range.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_quality_factor",
        "physical.lithography.source_plasma_drive_beam_wavelength",
        "physical.lithography.source_plasma_drive_spot_radius",
    }
    assert {v.name for v in plasma_drive_confocal_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_rayleigh_range",
    }
    assert {v.name for v in plasma_drive_spot_shape_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_spot_area_fill_factor",
        "physical.lithography.source_plasma_drive_spot_axis_ratio",
    }
    assert not plasma_drive_spot_axis_ratio.direct_dependencies()
    assert not plasma_drive_spot_area_fill_factor.direct_dependencies()
    assert {v.name for v in plasma_drive_spot_area.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_spot_radius",
        "physical.lithography.source_plasma_drive_spot_shape_factor",
    }
    assert {v.name for v in plasma_pulse_energy.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_peak_intensity",
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
        "physical.lithography.source_plasma_drive_spot_area",
    }
    assert {v.name for v in plasma_drive_power.direct_dependencies()} == {
        "physical.lithography.source_plasma_pulse_energy",
        "physical.lithography.source_plasma_pulse_repetition_rate",
    }
    assert {v.name for v in plasma_species_number_density.direct_dependencies()} == {
        "physical.lithography.source_plasma_species_partial_pressure",
        "physical.lithography.source_plasma_species_gas_temperature",
        "physics.boltzmann",
    }
    assert not plasma_column_expansion_speed_factor.direct_dependencies()
    assert {v.name for v in plasma_column_radial_expansion_speed.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_expansion_speed_factor",
        "physical.lithography.source_plasma_species_thermal_speed",
    }
    assert {
        v.name for v in plasma_column_radius_expansion_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_column_radial_expansion_speed",
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_spot_radius",
    }
    assert {v.name for v in plasma_column_radius.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_radius_expansion_factor",
        "physical.lithography.source_plasma_drive_spot_radius",
    }
    assert {v.name for v in plasma_column_aspect_ratio.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_radius",
        "physical.lithography.source_plasma_drive_confocal_length",
    }
    assert {v.name for v in plasma_column_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_aspect_ratio",
        "physical.lithography.source_plasma_column_radius",
    }
    assert plasma_active_fill_factor.direct_dependencies() == set()
    assert {v.name for v in plasma_active_volume.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_radius",
        "physical.lithography.source_plasma_column_length",
        "physical.lithography.source_plasma_active_fill_factor",
    }
    assert {v.name for v in plasma_absorption_path_direction_cosine.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    }
    assert {v.name for v in plasma_absorption_path_shape_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_path_direction_cosine",
    }
    assert {v.name for v in plasma_absorption_path_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_path_shape_factor",
        "physical.lithography.source_plasma_column_length",
    }
    assert {v.name for v in plasma_drive_beam_angular_frequency.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_wavelength",
        "physics.speed_of_light",
    }
    assert {v.name for v in plasma_absorption_resonance_to_drive_ratio.direct_dependencies()} == {
        "physical.lithography.source_ionization_energy",
        "physical.lithography.source_plasma_drive_beam_angular_frequency",
        "physics.hbar",
    }
    assert {v.name for v in plasma_absorption_quality_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_damping_rate",
        "physical.lithography.source_plasma_absorption_resonance_angular_frequency",
    }
    assert {
        v.name for v in plasma_absorption_collision_orbital_radius.direct_dependencies()
    } == {
        "physical.lithography.source_ionization_effective_nuclear_charge",
        "physical.lithography.source_ionization_principal_quantum_number",
        "physics.bohr_radius",
    }
    assert {v.name for v in plasma_absorption_collision_cross_section.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_collision_orbital_radius",
    }
    assert {
        v.name for v in plasma_absorption_participating_electron_fraction.direct_dependencies()
    } == {
        "physical.lithography.source_ionization_same_shell_screening_electron_count",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in plasma_absorption_sum_rule_fraction.direct_dependencies()} == {
        "physical.lithography.source_ionization_same_shell_screening_electron_count",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in plasma_absorption_resonance.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_resonance_to_drive_ratio",
        "physical.lithography.source_plasma_drive_beam_angular_frequency",
    }
    assert {v.name for v in plasma_absorption_damping_rate.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_collision_cross_section",
        "physical.lithography.source_plasma_species_number_density",
        "physical.lithography.source_plasma_species_thermal_speed",
    }
    assert {
        v.name for v in plasma_absorption_oscillator_strength.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_absorption_participating_electron_fraction",
        "physical.lithography.source_plasma_absorption_sum_rule_fraction",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in plasma_absorption_cross_section.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_damping_rate",
        "physical.lithography.source_plasma_absorption_oscillator_strength",
        "physical.lithography.source_plasma_absorption_resonance_angular_frequency",
        "physical.lithography.source_plasma_drive_beam_angular_frequency",
        "physics.elementary_charge",
        "physics.electron_mass",
        "physics.speed_of_light",
        "physics.vacuum_permittivity",
    }
    assert {v.name for v in plasma_absorption_optical_depth.direct_dependencies()} == {
        "physical.lithography.source_plasma_species_number_density",
        "physical.lithography.source_plasma_absorption_cross_section",
        "physical.lithography.source_plasma_absorption_path_length",
    }
    assert {
        v.name for v in plasma_drive_energy_absorption_fraction.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_absorption_optical_depth",
    }
    assert {
        v.name for v in plasma_drive_pointing_overlap_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_drive_centroid_offset_to_column_radius_ratio",
    }
    assert (
        plasma_drive_centroid_offset_to_column_radius_ratio.direct_dependencies()
        == set()
    )
    assert {
        v.name for v in plasma_drive_transverse_overlap_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_column_radius",
        "physical.lithography.source_plasma_drive_spot_area",
    }
    assert {v.name for v in plasma_drive_spatial_overlap_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_active_fill_factor",
        "physical.lithography.source_plasma_drive_pointing_overlap_factor",
        "physical.lithography.source_plasma_drive_transverse_overlap_factor",
    }
    assert {
        v.name for v in plasma_active_lifetime_to_drive_pulse_ratio.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_energy_confinement_time",
    }
    assert {v.name for v in plasma_active_response_duration.direct_dependencies()} == {
        "physical.lithography.source_plasma_active_lifetime_to_drive_pulse_ratio",
        "physical.lithography.source_plasma_drive_pulse_duration",
    }
    assert plasma_drive_timing_offset_fraction.direct_dependencies() == set()
    assert {v.name for v in plasma_drive_timing_offset_duration.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_timing_offset_fraction",
    }
    assert {
        v.name for v in plasma_drive_temporal_duration_match_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_active_response_duration",
        "physical.lithography.source_plasma_drive_pulse_duration",
    }
    assert {
        v.name for v in plasma_drive_temporal_alignment_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_active_response_duration",
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_timing_offset_duration",
    }
    assert {v.name for v in plasma_drive_temporal_overlap_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_temporal_alignment_factor",
        "physical.lithography.source_plasma_drive_temporal_duration_match_factor",
    }
    assert {v.name for v in plasma_drive_overlap_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_spatial_overlap_factor",
        "physical.lithography.source_plasma_drive_temporal_overlap_factor",
    }
    assert {v.name for v in plasma_absorption_efficiency.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_overlap_factor",
        "physical.lithography.source_plasma_drive_energy_absorption_fraction",
        "physical.lithography.source_plasma_electron_heating_fraction",
    }
    assert {v.name for v in plasma_absorbed_power.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_efficiency",
        "physical.lithography.source_plasma_drive_power",
    }
    assert {v.name for v in plasma_energy_loss_path_direction_cosine.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    }
    assert {v.name for v in plasma_energy_loss_path_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_energy_loss_path_direction_cosine",
    }
    assert {v.name for v in plasma_energy_loss_path_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_energy_loss_path_factor",
        "physical.lithography.source_plasma_column_radius",
    }
    assert {v.name for v in plasma_species_particle_mass.direct_dependencies()} == {
        "physical.lithography.source_neutron_count",
        "physical.lithography.source_proton_count",
        "physics.neutron_mass",
        "physics.proton_mass",
    }
    assert {v.name for v in plasma_species_thermal_speed.direct_dependencies()} == {
        "physical.lithography.source_plasma_species_gas_temperature",
        "physical.lithography.source_plasma_species_particle_mass",
        "physics.boltzmann",
    }
    assert {
        v.name for v in plasma_energy_loss_transport_speed_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_species_particle_mass",
        "physics.electron_mass",
    }
    assert [e.name for e in plasma_drive_spot_axis_ratio.approximations()] == [
        "physical.eq.lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention",
    ]
    assert [e.name for e in plasma_drive_spot_area_fill_factor.approximations()] == [
        "physical.eq.lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention",
    ]
    assert [e.name for e in plasma_drive_rayleigh_range.approximations()] == [
        "physical.eq.lithography_source_plasma_drive_rayleigh_range_from_spot_geometry",
    ]
    assert [e.name for e in plasma_drive_confocal_length.approximations()] == [
        "physical.eq.lithography_source_plasma_drive_confocal_length_from_rayleigh_range",
    ]
    assert [e.name for e in plasma_column_expansion_speed_factor.approximations()] == [
        "physical.eq.lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed",
    ]
    assert [e.name for e in plasma_column_aspect_ratio.approximations()] == [
        "physical.eq.lithography_source_plasma_column_aspect_ratio_from_confocal_length",
    ]
    active_fill_eq = plasma_active_fill_factor.approximations()[0]
    assert active_fill_eq.name == (
        "physical.eq.lithography_source_plasma_active_fill_factor_from_ideal_column_convention"
    )
    assert active_fill_eq.rhs == sp.Integer(1)
    assert [e.name for e in plasma_absorption_collision_orbital_radius.approximations()] == [
        "physical.eq.lithography_source_plasma_absorption_collision_orbital_radius_from_hydrogenic_shell",
    ]
    assert [e.name for e in plasma_absorption_collision_cross_section.approximations()] == [
        "physical.eq.lithography_source_plasma_absorption_collision_cross_section_from_orbital_area",
    ]
    centroid_offset_eq = (
        plasma_drive_centroid_offset_to_column_radius_ratio.approximations()[0]
    )
    assert centroid_offset_eq.name == (
        "physical.eq.lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio_from_coaxial_convention"
    )
    assert centroid_offset_eq.rhs == sp.Integer(0)
    timing_offset_eq = plasma_drive_timing_offset_fraction.approximations()[0]
    assert timing_offset_eq.name == (
        "physical.eq.lithography_source_plasma_drive_timing_offset_fraction_from_synchronized_convention"
    )
    assert timing_offset_eq.rhs == sp.Integer(0)
    assert {v.name for v in plasma_energy_loss_speed.direct_dependencies()} == {
        "physical.lithography.source_plasma_energy_loss_transport_speed_factor",
        "physical.lithography.source_plasma_species_thermal_speed",
    }
    assert {v.name for v in plasma_confinement_time.direct_dependencies()} == {
        "physical.lithography.source_plasma_energy_loss_path_length",
        "physical.lithography.source_plasma_energy_loss_speed",
    }
    assert {v.name for v in plasma_free_electron_yield.direct_dependencies()} == {
        "physical.lithography.source_plasma_free_electron_inventory_charge_fraction",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in plasma_free_electron_count.direct_dependencies()} == {
        "physical.lithography.source_plasma_species_number_density",
        "physical.lithography.source_plasma_active_volume",
        "physical.lithography.source_plasma_free_electron_yield_per_source_particle",
    }
    assert {v.name for v in plasma_internal_energy.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorbed_power",
        "physical.lithography.source_plasma_energy_confinement_time",
    }
    assert {v.name for v in plasma_temperature.direct_dependencies()} == {
        "physical.lithography.source_plasma_electron_internal_energy",
        "physical.lithography.source_plasma_free_electron_count",
        "physics.boltzmann",
    }
    assert {v.name for v in plasma_density.direct_dependencies()} == {
        "physical.lithography.source_plasma_active_volume",
        "physical.lithography.source_plasma_free_electron_count",
    }
    assert {v.name for v in plasma_mean_energy.direct_dependencies()} == {
        "physical.lithography.source_plasma_electron_temperature",
        "physics.boltzmann",
    }
    assert {v.name for v in plasma_debye_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_electron_number_density",
        "physical.lithography.source_plasma_electron_temperature",
        "physics.boltzmann",
        "physics.elementary_charge",
        "physics.vacuum_permittivity",
    }
    assert {v.name for v in saha_thermal_density.direct_dependencies()} == {
        "physical.lithography.source_plasma_electron_temperature",
        "physics.boltzmann",
        "physics.electron_mass",
        "physics.planck",
    }
    assert {v.name for v in saha_ratio.direct_dependencies()} == {
        "physical.lithography.source_ionization_energy",
        "physical.lithography.source_ionization_partition_ratio",
        "physical.lithography.source_plasma_electron_number_density",
        "physical.lithography.source_plasma_electron_temperature",
        "physical.lithography.source_saha_thermal_number_density",
        "physics.boltzmann",
    }
    assert {v.name for v in saha_fraction.direct_dependencies()} == {
        "physical.lithography.source_saha_ionization_ratio",
    }
    assert {v.name for v in ion_charge_state.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_saha_ionization_fraction",
    }
    assert {v.name for v in bound_electrons.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_ion_charge_state",
    }
    assert {v.name for v in lower_principal.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in upper_principal.direct_dependencies()} == {
        "physical.lithography.source_lower_principal_quantum_number",
        "physical.lithography.source_transition_principal_quantum_step",
    }
    assert {v.name for v in transition_step.direct_dependencies()} == set()
    assert {v.name for v in shell_capacity.direct_dependencies()} == {
        "physical.lithography.source_lower_principal_quantum_number",
    }
    assert {v.name for v in inner_closed_capacity.direct_dependencies()} == {
        "physical.lithography.source_lower_principal_quantum_number",
    }
    assert {v.name for v in inner_closed_shells.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_inner_closed_shell_capacity",
        "physical.lithography.source_outer_shell_electron_count",
    }
    assert {v.name for v in outer_shells.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_inner_closed_shell_capacity",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in transition_shell_occupancy.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_inner_closed_shell_electron_count",
        "physical.lithography.source_outer_shell_electron_count",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in same_screeners.direct_dependencies()} == {
        "physical.lithography.source_transition_shell_occupancy",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in inner_screeners.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_transition_shell_occupancy",
        "physical.lithography.source_outer_shell_electron_count",
    }
    assert {v.name for v in inner_shielding.direct_dependencies()} == set()
    assert {v.name for v in same_shielding.direct_dependencies()} == set()
    assert {v.name for v in screening.direct_dependencies()} == {
        "physical.lithography.source_bound_electron_count",
        "physical.lithography.source_inner_shell_screening_electron_count",
        "physical.lithography.source_same_shell_screening_electron_count",
        "physical.lithography.source_inner_shell_shielding_factor",
        "physical.lithography.source_same_shell_shielding_factor",
    }
    assert {v.name for v in z_eff.direct_dependencies()} == {
        "physical.lithography.source_proton_count",
        "physical.lithography.source_screening_constant",
    }
    assert {v.name for v in transition.direct_dependencies()} == {
        "physical.lithography.source_reduced_mass_ratio",
        "physical.lithography.source_effective_nuclear_charge",
        "physical.lithography.source_lower_principal_quantum_number",
        "physical.lithography.source_upper_principal_quantum_number",
        "physics.rydberg_energy",
    }
