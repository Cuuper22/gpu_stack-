"""Numeric lithography source quantum fixture setup."""

from __future__ import annotations

from types import SimpleNamespace

import sympy as sp

from gpu_stack import Registry
from tests.helpers.lithography import source_quark_assignments


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
