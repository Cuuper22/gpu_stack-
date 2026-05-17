"""Shared source quantum test setup."""

from __future__ import annotations

from types import SimpleNamespace

import sympy as sp

from gpu_stack import Registry
from tests.helpers.lithography import source_quark_assignments


def source_quantum_model():
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
    return SimpleNamespace(**locals())


def source_quantum_numeric_case():
    electron_mass = Registry.variables["physics.electron_mass"].value
    boltzmann = Registry.variables["physics.boltzmann"].value
    proton_mass = Registry.variables["physics.proton_mass"].value
    rydberg_energy = Registry.variables["physics.rydberg_energy"].value
    planck = Registry.variables["physics.planck"].value
    hbar = Registry.variables["physics.hbar"].value
    c = Registry.variables["physics.speed_of_light"].value
    elementary_charge = Registry.variables["physics.elementary_charge"].value
    vacuum_permittivity = Registry.variables["physics.vacuum_permittivity"].value
    bohr_radius = Registry.variables["physics.bohr_radius"].value
    test_coulomb_coeff = 0.5
    test_volume_coeff = 10.0
    test_surface_coeff = 2.0
    test_asymmetry_coeff = 3.0
    test_radius_coeff = (
        3.0
        * elementary_charge**2
        / (20.0 * float(sp.pi) * vacuum_permittivity * test_coulomb_coeff)
    )
    test_saturation_density = 3.0 / (
        4.0 * float(sp.pi) * test_radius_coeff**3
    )
    test_bulk_binding_density = 10.0 * test_saturation_density
    test_surface_tension = 2.0 / (
        4.0 * float(sp.pi) * test_radius_coeff**2
    )
    test_symmetry_density = 3.0 * test_saturation_density
    test_pairing_gap_ref = 1.0
    test_plasma_temperature = 10000.0
    test_plasma_absorption_efficiency = 0.05
    test_plasma_pulse_period = 1.0e-9
    test_plasma_pulse_repetition_rate = 1.0 / test_plasma_pulse_period
    test_plasma_drive_pulse_duration = 1.0e-12
    test_plasma_drive_pulse_duty_factor = (
        test_plasma_drive_pulse_duration / test_plasma_pulse_period
    )
    test_plasma_drive_pulse_rise_fraction = 0.0
    test_plasma_drive_pulse_fall_fraction = test_plasma_drive_pulse_rise_fraction
    test_plasma_drive_pulse_flat_fraction = (
        1.0
        - test_plasma_drive_pulse_rise_fraction
        - test_plasma_drive_pulse_fall_fraction
    )
    test_plasma_drive_pulse_temporal_shape_factor = (
        test_plasma_drive_pulse_flat_fraction
        + 0.5
        * (
            test_plasma_drive_pulse_rise_fraction
            + test_plasma_drive_pulse_fall_fraction
        )
    )
    test_plasma_drive_energy_absorption_fraction = 0.8
    test_plasma_absorption_optical_depth = -float(
        sp.log(1.0 - test_plasma_drive_energy_absorption_fraction)
    )
    test_plasma_species_gas_temperature = 1000.0
    test_plasma_species_particle_mass = proton_mass
    test_plasma_species_thermal_speed = (
        boltzmann
        * test_plasma_species_gas_temperature
        / test_plasma_species_particle_mass
    ) ** 0.5
    test_plasma_column_expansion_speed_factor = (5.0 / 3.0) ** 0.5
    test_plasma_column_radial_expansion_speed = (
        test_plasma_column_expansion_speed_factor
        * test_plasma_species_thermal_speed
    )
    test_plasma_free_electron_yield = 0.25
    test_plasma_free_electron_inventory_charge_fraction = test_plasma_free_electron_yield
    test_saha_thermal_density = (
        2.0
        * (
            2.0
            * float(sp.pi)
            * electron_mass
            * boltzmann
            * test_plasma_temperature
            / planck**2
        ) ** 1.5
    )
    test_saha_thermal_to_electron_density_ratio = 3.0
    test_plasma_electron_number_density = (
        test_saha_thermal_density
        / test_saha_thermal_to_electron_density_ratio
    )
    test_plasma_species_number_density = (
        test_plasma_electron_number_density
        / test_plasma_free_electron_yield
    )
    test_plasma_species_partial_pressure = (
        test_plasma_species_number_density
        * boltzmann
        * test_plasma_species_gas_temperature
    )
    plasma_source_root_assignments = {
        "physical.lithography.source_plasma_pulse_period": test_plasma_pulse_period,
        "physical.lithography.source_plasma_species_partial_pressure": test_plasma_species_partial_pressure,
        "physical.lithography.source_plasma_species_gas_temperature": test_plasma_species_gas_temperature,
        "physical.lithography.source_plasma_free_electron_inventory_charge_fraction": test_plasma_free_electron_inventory_charge_fraction,
    }
    test_mean_electron_kinetic_energy = 1.5 * boltzmann * test_plasma_temperature
    test_plasma_active_fill_factor = 0.5
    test_plasma_drive_focus_f_number = 1.0
    test_plasma_drive_objective_focal_length = 1.0
    test_plasma_drive_objective_pupil_radius = (
        test_plasma_drive_objective_focal_length
        / (2.0 * test_plasma_drive_focus_f_number)
    )
    test_plasma_drive_acceptance_half_angle = float(
        sp.atan(
            test_plasma_drive_objective_pupil_radius
            / test_plasma_drive_objective_focal_length
        )
    )
    test_plasma_drive_numerical_aperture = float(
        sp.sin(test_plasma_drive_acceptance_half_angle)
    )
    test_plasma_drive_pupil_beam_fill_factor = 0.25
    test_plasma_drive_beam_quality_factor = 1.0
    test_plasma_drive_focus_waist_coefficient = 2.0 / float(sp.pi)
    test_plasma_drive_spot_radius = 1.0e-6
    test_plasma_column_radius = (
        test_plasma_drive_spot_radius
        + test_plasma_column_radial_expansion_speed
        * test_plasma_drive_pulse_duration
    )
    test_plasma_column_radius_expansion_factor = (
        test_plasma_column_radius
        / test_plasma_drive_spot_radius
    )
    test_plasma_drive_beam_wavelength = (
        test_plasma_drive_spot_radius
        / (
            test_plasma_drive_focus_waist_coefficient
            * test_plasma_drive_beam_quality_factor
            * test_plasma_drive_focus_f_number
        )
    )
    test_plasma_drive_rayleigh_range = (
        float(sp.pi)
        * test_plasma_drive_spot_radius**2
        / (
            test_plasma_drive_beam_quality_factor
            * test_plasma_drive_beam_wavelength
        )
    )
    test_plasma_drive_confocal_length = 2.0 * test_plasma_drive_rayleigh_range
    test_plasma_column_length = test_plasma_drive_confocal_length
    test_plasma_column_aspect_ratio = (
        test_plasma_column_length
        / test_plasma_column_radius
    )
    test_plasma_active_volume = (
        float(sp.pi)
        * test_plasma_column_radius**2
        * test_plasma_column_length
        * test_plasma_active_fill_factor
    )
    test_plasma_free_electron_count = (
        test_plasma_species_number_density
        * test_plasma_free_electron_yield
        * test_plasma_active_volume
    )
    test_plasma_drive_edge_detuning_ratio = 1.0
    test_plasma_drive_beam_parameter_product = (
        test_plasma_drive_beam_quality_factor
        * test_plasma_drive_beam_wavelength
        / float(sp.pi)
    )
    test_plasma_drive_beam_parameter_waist_radius = (
        test_plasma_drive_pupil_beam_fill_factor
        * test_plasma_drive_objective_pupil_radius
    )
    test_plasma_drive_far_field_divergence_half_angle = (
        test_plasma_drive_beam_parameter_product
        / test_plasma_drive_beam_parameter_waist_radius
    )
    test_plasma_source_ionization_energy = (
        2.0
        * float(sp.pi)
        * hbar
        * c
        * test_plasma_drive_edge_detuning_ratio
        / test_plasma_drive_beam_wavelength
    )
    test_plasma_drive_spot_axis_ratio = 1.0
    test_plasma_drive_spot_area_fill_factor = 1.0
    test_plasma_drive_spot_shape_factor = (
        test_plasma_drive_spot_axis_ratio
        * test_plasma_drive_spot_area_fill_factor
    )
    test_plasma_drive_spot_area = (
        float(sp.pi)
        * test_plasma_drive_spot_radius**2
        * test_plasma_drive_spot_shape_factor
    )
    test_plasma_drive_centroid_offset_to_column_radius_ratio = 0.0
    test_plasma_drive_pointing_overlap_factor = float(
        sp.exp(-(test_plasma_drive_centroid_offset_to_column_radius_ratio**2))
    )
    test_plasma_drive_transverse_overlap_factor = (
        test_plasma_drive_spot_area
        / (float(sp.pi) * test_plasma_column_radius**2)
    )
    test_plasma_drive_spatial_overlap_factor = (
        test_plasma_drive_transverse_overlap_factor
        * test_plasma_drive_pointing_overlap_factor
        * test_plasma_active_fill_factor
    )
    test_plasma_energy_loss_path_direction_cosine = float(
        sp.sin(test_plasma_drive_acceptance_half_angle)
    )
    test_plasma_energy_loss_path_factor = (
        1.0 / test_plasma_energy_loss_path_direction_cosine
    )
    test_plasma_energy_loss_path_length = (
        test_plasma_energy_loss_path_factor
        * test_plasma_column_radius
    )
    test_plasma_energy_loss_transport_speed_factor = (
        test_plasma_species_particle_mass / electron_mass
    ) ** 0.5
    test_plasma_energy_loss_speed = (
        test_plasma_energy_loss_transport_speed_factor
        * test_plasma_species_thermal_speed
    )
    test_plasma_energy_confinement_time = (
        test_plasma_energy_loss_path_length
        / test_plasma_energy_loss_speed
    )
    test_plasma_internal_energy = (
        1.5
        * boltzmann
        * test_plasma_temperature
        * test_plasma_free_electron_count
    )
    test_plasma_absorbed_power = (
        test_plasma_internal_energy
        / test_plasma_energy_confinement_time
    )
    test_plasma_drive_power = (
        test_plasma_absorbed_power
        / test_plasma_absorption_efficiency
    )
    test_plasma_pulse_energy = (
        test_plasma_drive_power
        / test_plasma_pulse_repetition_rate
    )
    test_plasma_active_lifetime_to_drive_pulse_ratio = (
        test_plasma_energy_confinement_time
        / test_plasma_drive_pulse_duration
    )
    test_plasma_active_response_duration = (
        test_plasma_active_lifetime_to_drive_pulse_ratio
        * test_plasma_drive_pulse_duration
    )
    test_plasma_drive_timing_offset_fraction = 0.0
    test_plasma_drive_timing_offset_duration = (
        test_plasma_drive_timing_offset_fraction
        * test_plasma_drive_pulse_duration
    )
    test_plasma_drive_temporal_duration_match_factor = (
        4.0
        * test_plasma_drive_pulse_duration
        * test_plasma_active_response_duration
        / (
            test_plasma_drive_pulse_duration
            + test_plasma_active_response_duration
        ) ** 2
    )
    test_plasma_drive_temporal_alignment_factor = float(
        sp.exp(
            -(
                test_plasma_drive_timing_offset_duration
                / (
                    test_plasma_drive_pulse_duration
                    + test_plasma_active_response_duration
                )
            ) ** 2
        )
    )
    test_plasma_drive_temporal_overlap_factor = (
        test_plasma_drive_temporal_duration_match_factor
        * test_plasma_drive_temporal_alignment_factor
    )
    test_plasma_drive_overlap_factor = (
        test_plasma_drive_spatial_overlap_factor
        * test_plasma_drive_temporal_overlap_factor
    )
    test_plasma_electron_heating_fraction = (
        test_plasma_absorption_efficiency
        / (
            test_plasma_drive_overlap_factor
            * test_plasma_drive_energy_absorption_fraction
        )
    )
    test_plasma_drive_peak_intensity = (
        test_plasma_pulse_energy
        / (
            test_plasma_drive_spot_area
            * test_plasma_drive_pulse_duration
            * test_plasma_drive_pulse_temporal_shape_factor
        )
    )
    test_plasma_drive_pulse_fluence = (
        test_plasma_drive_peak_intensity
        * test_plasma_drive_pulse_duration
        * test_plasma_drive_pulse_temporal_shape_factor
    )
    test_plasma_absorption_path_direction_cosine = float(
        sp.cos(test_plasma_drive_acceptance_half_angle)
    )
    test_plasma_absorption_path_shape_factor = (
        1.0 / test_plasma_absorption_path_direction_cosine
    )
    test_plasma_absorption_path_length = (
        test_plasma_absorption_path_shape_factor
        * test_plasma_column_length
    )
    test_plasma_absorption_cross_section = (
        test_plasma_absorption_optical_depth
        / (
            test_plasma_species_number_density
            * test_plasma_absorption_path_length
        )
    )
    test_plasma_drive_beam_angular_frequency = (
        2.0 * float(sp.pi) * c / test_plasma_drive_beam_wavelength
    )
    test_plasma_absorption_resonance = test_plasma_drive_beam_angular_frequency
    test_source_ionization_principal_quantum_number = 1.0
    test_source_ionization_effective_nuclear_charge = 1.0
    test_plasma_absorption_collision_orbital_radius = (
        bohr_radius
        * test_source_ionization_principal_quantum_number**2
        / test_source_ionization_effective_nuclear_charge
    )
    test_plasma_absorption_collision_cross_section = (
        float(sp.pi) * test_plasma_absorption_collision_orbital_radius**2
    )
    test_plasma_absorption_damping_rate = (
        test_plasma_species_number_density
        * test_plasma_absorption_collision_cross_section
        * test_plasma_species_thermal_speed
    )
    test_plasma_absorption_resonance_to_drive_ratio = (
        test_plasma_absorption_resonance
        / test_plasma_drive_beam_angular_frequency
    )
    test_plasma_absorption_quality_factor = (
        test_plasma_absorption_resonance
        / test_plasma_absorption_damping_rate
    )
    test_plasma_absorption_oscillator_strength = (
        test_plasma_absorption_cross_section
        * electron_mass
        * vacuum_permittivity
        * c
        * (
            (
                test_plasma_absorption_resonance**2
                - test_plasma_drive_beam_angular_frequency**2
            ) ** 2
            + (
                test_plasma_absorption_damping_rate**2
                * test_plasma_drive_beam_angular_frequency**2
            )
        )
        / elementary_charge**2
        / test_plasma_absorption_damping_rate
        / test_plasma_drive_beam_angular_frequency**2
    )
    test_plasma_absorption_sum_rule_fraction = 1.0
    test_plasma_absorption_participating_electron_fraction = (
        test_plasma_absorption_oscillator_strength
        / test_plasma_absorption_sum_rule_fraction
    )
    test_debye_length = (
        vacuum_permittivity
        * boltzmann
        * test_plasma_temperature
        / (test_plasma_electron_number_density * elementary_charge**2)
    ) ** 0.5
    plasma_assignments = {
        **plasma_source_root_assignments,
        "physical.lithography.source_plasma_drive_pulse_fluence": test_plasma_drive_pulse_fluence,
        "physical.lithography.source_plasma_drive_pulse_duty_factor": test_plasma_drive_pulse_duty_factor,
        "physical.lithography.source_plasma_drive_pulse_rise_fraction": test_plasma_drive_pulse_rise_fraction,
        "physical.lithography.source_ionization_energy": test_plasma_source_ionization_energy,
        "physical.lithography.source_plasma_drive_edge_detuning_ratio": test_plasma_drive_edge_detuning_ratio,
        "physical.lithography.source_plasma_drive_objective_pupil_radius": test_plasma_drive_objective_pupil_radius,
        "physical.lithography.source_plasma_drive_objective_focal_length": test_plasma_drive_objective_focal_length,
        "physical.lithography.source_plasma_drive_pupil_beam_fill_factor": test_plasma_drive_pupil_beam_fill_factor,
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle": test_plasma_drive_far_field_divergence_half_angle,
        "physical.lithography.source_plasma_active_fill_factor": test_plasma_active_fill_factor,
        "physical.lithography.source_plasma_drive_centroid_offset_to_column_radius_ratio": test_plasma_drive_centroid_offset_to_column_radius_ratio,
            "physical.lithography.source_plasma_drive_timing_offset_fraction": test_plasma_drive_timing_offset_fraction,
            "physical.lithography.source_plasma_absorption_participating_electron_fraction": test_plasma_absorption_participating_electron_fraction,
        "physical.lithography.source_plasma_absorption_sum_rule_fraction": test_plasma_absorption_sum_rule_fraction,
        "physical.lithography.source_plasma_electron_heating_fraction": test_plasma_electron_heating_fraction,
    }
    def plasma_assignments_for_source(protons):
        return {
            **plasma_assignments,
            "physical.lithography.source_plasma_absorption_participating_electron_fraction": (
                test_plasma_absorption_oscillator_strength
                / (protons * test_plasma_absorption_sum_rule_fraction)
            ),
            "physical.lithography.source_plasma_free_electron_inventory_charge_fraction": (
                test_plasma_free_electron_yield / protons
            ),
        }

    assignments = {
        **source_quark_assignments(1, 0),
        "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
        "physical.lithography.nuclear_binding_volume_coefficient": 0.0,
        "physical.lithography.nuclear_binding_surface_coefficient": 0.0,
        "physical.lithography.nuclear_binding_asymmetry_coefficient": 0.0,
        "physical.lithography.nuclear_pairing_gap_reference_energy": 0.0,
        **plasma_assignments_for_source(1),
        "physical.lithography.source_ionization_partition_ratio": 0.0,
    }
    reduced_mass_ratio = proton_mass / (electron_mass + proton_mass)
    expected_energy = rydberg_energy * reduced_mass_ratio * (1.0 - 1.0 / 4.0)
    plasma_assignments_with_source = {
        **source_quark_assignments(1, 0),
        **plasma_assignments_for_source(1),
    }
    return SimpleNamespace(**locals())
