"""Lithography source quantum numeric closure coverage."""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.core import RelationRole
from tests.helpers.lithography import source_quark_assignments


def test_lithography_source_quantum_numeric_chain_resolves_photon_energy():
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

    radius_coeff_result = resolve(
        "physical.lithography.source_nuclear_radius_coefficient",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
        },
    )
    assert float(radius_coeff_result.value) == pytest.approx(test_radius_coeff)

    saturation_density_result = resolve(
        "physical.lithography.source_nuclear_saturation_number_density",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
        },
    )
    assert float(saturation_density_result.value) == pytest.approx(test_saturation_density)

    bulk_binding_density_result = resolve(
        "physical.lithography.source_nuclear_bulk_binding_energy_density",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
            "physical.lithography.nuclear_binding_volume_coefficient": test_volume_coeff,
        },
    )
    assert float(bulk_binding_density_result.value) == pytest.approx(test_bulk_binding_density)

    surface_tension_result = resolve(
        "physical.lithography.source_nuclear_surface_tension",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
            "physical.lithography.nuclear_binding_surface_coefficient": test_surface_coeff,
        },
    )
    assert float(surface_tension_result.value) == pytest.approx(test_surface_tension)

    symmetry_density_result = resolve(
        "physical.lithography.source_nuclear_symmetry_energy_density",
        assignments={
            "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
            "physical.lithography.nuclear_binding_asymmetry_coefficient": test_asymmetry_coeff,
        },
    )
    assert float(symmetry_density_result.value) == pytest.approx(test_symmetry_density)

    pairing_ref_result = resolve(
        "physical.lithography.source_pairing_reference_mass_number",
        assignments=source_quark_assignments(8, 8),
    )
    assert float(pairing_ref_result.value) == pytest.approx(16.0)
    pairing_ref_trace = [step.equation for step in pairing_ref_result.trace]
    assert set(pairing_ref_trace[:2]) == {
        "physical.eq.lithography_source_neutron_count_from_valence_quarks",
        "physical.eq.lithography_source_proton_count_from_valence_quarks",
    }
    assert pairing_ref_trace[2:] == [
        "physical.eq.lithography_source_isotope_mass_number",
        "physical.eq.lithography_source_mass_number",
        "physical.eq.lithography_source_pairing_reference_mass_number",
    ]

    pairing_coeff_result = resolve(
        "physical.lithography.source_binding_pairing_coefficient",
        assignments={
            **source_quark_assignments(8, 8),
            "physical.lithography.nuclear_pairing_gap_reference_energy": test_pairing_gap_ref,
        },
    )
    assert float(pairing_coeff_result.value) == pytest.approx(4.0)
    assert "physical.eq.lithography_source_pairing_reference_mass_number" in {
        step.equation for step in pairing_coeff_result.trace
    }

    pairing_coeff_override_result = resolve(
        "physical.lithography.source_binding_pairing_coefficient",
        assignments={
            "physical.lithography.nuclear_pairing_gap_reference_energy": test_pairing_gap_ref,
            "physical.lithography.source_pairing_reference_mass_number": 9,
        },
    )
    assert float(pairing_coeff_override_result.value) == pytest.approx(3.0)
    assert "physical.eq.lithography_source_pairing_reference_mass_number" not in {
        step.equation for step in pairing_coeff_override_result.trace
    }

    plasma_assignments_with_source = {
        **source_quark_assignments(1, 0),
        **plasma_assignments_for_source(1),
    }
    absorbed_power_result = resolve(
        "physical.lithography.source_plasma_absorbed_power",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorbed_power_result.value) == pytest.approx(test_plasma_absorbed_power)
    drive_power_result = resolve(
        "physical.lithography.source_plasma_drive_power",
        assignments=plasma_assignments,
    )
    assert float(drive_power_result.value) == pytest.approx(test_plasma_drive_power)
    pulse_duration_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_duration",
        assignments=plasma_assignments,
    )
    assert float(pulse_duration_result.value) == pytest.approx(
        test_plasma_drive_pulse_duration
    )
    pulse_fall_fraction_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_fall_fraction",
        assignments=plasma_assignments,
    )
    assert float(pulse_fall_fraction_result.value) == pytest.approx(
        test_plasma_drive_pulse_fall_fraction
    )
    pulse_flat_fraction_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_flat_fraction",
        assignments=plasma_assignments,
    )
    assert float(pulse_flat_fraction_result.value) == pytest.approx(
        test_plasma_drive_pulse_flat_fraction
    )
    pulse_shape_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
        assignments=plasma_assignments,
    )
    assert float(pulse_shape_result.value) == pytest.approx(
        test_plasma_drive_pulse_temporal_shape_factor
    )
    peak_intensity_result = resolve(
        "physical.lithography.source_plasma_drive_peak_intensity",
        assignments=plasma_assignments,
    )
    assert float(peak_intensity_result.value) == pytest.approx(
        test_plasma_drive_peak_intensity
    )
    waist_coefficient_result = resolve(
        "physical.lithography.source_plasma_drive_focus_waist_coefficient",
        assignments=plasma_assignments,
    )
    assert float(waist_coefficient_result.value) == pytest.approx(
        test_plasma_drive_focus_waist_coefficient
    )
    acceptance_half_angle_result = resolve(
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
        assignments=plasma_assignments,
    )
    assert float(acceptance_half_angle_result.value) == pytest.approx(
        test_plasma_drive_acceptance_half_angle
    )
    numerical_aperture_result = resolve(
        "physical.lithography.source_plasma_drive_numerical_aperture",
        assignments=plasma_assignments,
    )
    assert float(numerical_aperture_result.value) == pytest.approx(
        test_plasma_drive_numerical_aperture
    )
    focus_f_number_result = resolve(
        "physical.lithography.source_plasma_drive_focus_f_number",
        assignments=plasma_assignments,
    )
    assert float(focus_f_number_result.value) == pytest.approx(
        test_plasma_drive_focus_f_number
    )
    beam_parameter_waist_result = resolve(
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius",
        assignments=plasma_assignments,
    )
    assert float(beam_parameter_waist_result.value) == pytest.approx(
        test_plasma_drive_beam_parameter_waist_radius
    )
    beam_parameter_product_result = resolve(
        "physical.lithography.source_plasma_drive_beam_parameter_product",
        assignments=plasma_assignments,
    )
    assert float(beam_parameter_product_result.value) == pytest.approx(
        test_plasma_drive_beam_parameter_product
    )
    beam_quality_result = resolve(
        "physical.lithography.source_plasma_drive_beam_quality_factor",
        assignments=plasma_assignments,
    )
    assert float(beam_quality_result.value) == pytest.approx(
        test_plasma_drive_beam_quality_factor
    )
    spot_axis_ratio_result = resolve(
        "physical.lithography.source_plasma_drive_spot_axis_ratio",
        assignments=plasma_assignments,
    )
    assert float(spot_axis_ratio_result.value) == pytest.approx(
        test_plasma_drive_spot_axis_ratio
    )
    spot_area_fill_factor_result = resolve(
        "physical.lithography.source_plasma_drive_spot_area_fill_factor",
        assignments=plasma_assignments,
    )
    assert float(spot_area_fill_factor_result.value) == pytest.approx(
        test_plasma_drive_spot_area_fill_factor
    )
    spot_radius_result = resolve(
        "physical.lithography.source_plasma_drive_spot_radius",
        assignments=plasma_assignments,
    )
    assert float(spot_radius_result.value) == pytest.approx(test_plasma_drive_spot_radius)
    rayleigh_range_result = resolve(
        "physical.lithography.source_plasma_drive_rayleigh_range",
        assignments=plasma_assignments,
    )
    assert float(rayleigh_range_result.value) == pytest.approx(
        test_plasma_drive_rayleigh_range
    )
    confocal_length_result = resolve(
        "physical.lithography.source_plasma_drive_confocal_length",
        assignments=plasma_assignments,
    )
    assert float(confocal_length_result.value) == pytest.approx(
        test_plasma_drive_confocal_length
    )
    spot_shape_result = resolve(
        "physical.lithography.source_plasma_drive_spot_shape_factor",
        assignments=plasma_assignments,
    )
    assert float(spot_shape_result.value) == pytest.approx(
        test_plasma_drive_spot_shape_factor
    )
    column_expansion_result = resolve(
        "physical.lithography.source_plasma_column_radius_expansion_factor",
        assignments=plasma_assignments_with_source,
    )
    assert float(column_expansion_result.value) == pytest.approx(
        test_plasma_column_radius_expansion_factor
    )
    column_aspect_result = resolve(
        "physical.lithography.source_plasma_column_aspect_ratio",
        assignments=plasma_assignments_with_source,
    )
    assert float(column_aspect_result.value) == pytest.approx(
        test_plasma_column_aspect_ratio
    )
    species_density_result = resolve(
        "physical.lithography.source_plasma_species_number_density",
        assignments=plasma_assignments,
    )
    assert float(species_density_result.value) == pytest.approx(
        test_plasma_species_number_density
    )
    absorption_path_direction_cosine_result = resolve(
        "physical.lithography.source_plasma_absorption_path_direction_cosine",
        assignments=plasma_assignments,
    )
    assert float(absorption_path_direction_cosine_result.value) == pytest.approx(
        test_plasma_absorption_path_direction_cosine
    )
    absorption_path_shape_result = resolve(
        "physical.lithography.source_plasma_absorption_path_shape_factor",
        assignments=plasma_assignments,
    )
    assert float(absorption_path_shape_result.value) == pytest.approx(
        test_plasma_absorption_path_shape_factor
    )
    absorption_path_result = resolve(
        "physical.lithography.source_plasma_absorption_path_length",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_path_result.value) == pytest.approx(
        test_plasma_absorption_path_length
    )
    drive_beam_angular_frequency_result = resolve(
        "physical.lithography.source_plasma_drive_beam_angular_frequency",
        assignments=plasma_assignments,
    )
    assert float(drive_beam_angular_frequency_result.value) == pytest.approx(
        test_plasma_drive_beam_angular_frequency
    )
    absorption_resonance_result = resolve(
        "physical.lithography.source_plasma_absorption_resonance_angular_frequency",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_resonance_result.value) == pytest.approx(
        test_plasma_absorption_resonance
    )
    collision_orbital_radius_result = resolve(
        "physical.lithography.source_plasma_absorption_collision_orbital_radius",
        assignments=plasma_assignments_with_source,
    )
    assert float(collision_orbital_radius_result.value) == pytest.approx(
        test_plasma_absorption_collision_orbital_radius
    )
    collision_cross_section_result = resolve(
        "physical.lithography.source_plasma_absorption_collision_cross_section",
        assignments=plasma_assignments_with_source,
    )
    assert float(collision_cross_section_result.value) == pytest.approx(
        test_plasma_absorption_collision_cross_section
    )
    absorption_damping_result = resolve(
        "physical.lithography.source_plasma_absorption_damping_rate",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_damping_result.value) == pytest.approx(
        test_plasma_absorption_damping_rate
    )
    absorption_quality_result = resolve(
        "physical.lithography.source_plasma_absorption_quality_factor",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_quality_result.value) == pytest.approx(
        test_plasma_absorption_quality_factor
    )
    absorption_oscillator_result = resolve(
        "physical.lithography.source_plasma_absorption_oscillator_strength",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_oscillator_result.value) == pytest.approx(
        test_plasma_absorption_oscillator_strength
    )
    absorption_cross_section_result = resolve(
        "physical.lithography.source_plasma_absorption_cross_section",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_cross_section_result.value) == pytest.approx(
        test_plasma_absorption_cross_section
    )
    absorption_depth_result = resolve(
        "physical.lithography.source_plasma_absorption_optical_depth",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_depth_result.value) == pytest.approx(
        test_plasma_absorption_optical_depth
    )
    absorption_fraction_result = resolve(
        "physical.lithography.source_plasma_drive_energy_absorption_fraction",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_fraction_result.value) == pytest.approx(
        test_plasma_drive_energy_absorption_fraction
    )
    overlap_result = resolve(
        "physical.lithography.source_plasma_drive_overlap_factor",
        assignments=plasma_assignments_with_source,
    )
    assert float(overlap_result.value) == pytest.approx(
        test_plasma_drive_overlap_factor
    )
    ideal_overlap_assignments = {
        key: value
        for key, value in plasma_assignments_with_source.items()
        if key not in {
            "physical.lithography.source_plasma_active_fill_factor",
            "physical.lithography.source_plasma_drive_centroid_offset_to_column_radius_ratio",
            "physical.lithography.source_plasma_drive_timing_offset_fraction",
        }
    }
    ideal_overlap_result = resolve(
        "physical.lithography.source_plasma_drive_overlap_factor",
        assignments=ideal_overlap_assignments,
    )
    assert float(ideal_overlap_result.value) == pytest.approx(
        test_plasma_drive_overlap_factor / test_plasma_active_fill_factor
    )
    ideal_overlap_trace = {step.equation for step in ideal_overlap_result.trace}
    assert {
        "physical.eq.lithography_source_plasma_active_fill_factor_from_ideal_column_convention",
        "physical.eq.lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio_from_coaxial_convention",
        "physical.eq.lithography_source_plasma_drive_timing_offset_fraction_from_synchronized_convention",
    } <= ideal_overlap_trace
    absorption_result = resolve(
        "physical.lithography.source_plasma_absorption_efficiency",
        assignments=plasma_assignments_with_source,
    )
    assert float(absorption_result.value) == pytest.approx(
        test_plasma_absorption_efficiency
    )
    active_volume_result = resolve(
        "physical.lithography.source_plasma_active_volume",
        assignments=plasma_assignments_with_source,
    )
    assert float(active_volume_result.value) == pytest.approx(test_plasma_active_volume)
    energy_loss_direction_result = resolve(
        "physical.lithography.source_plasma_energy_loss_path_direction_cosine",
        assignments=plasma_assignments_with_source,
    )
    assert float(energy_loss_direction_result.value) == pytest.approx(
        test_plasma_energy_loss_path_direction_cosine
    )
    energy_loss_path_factor_result = resolve(
        "physical.lithography.source_plasma_energy_loss_path_factor",
        assignments=plasma_assignments_with_source,
    )
    assert float(energy_loss_path_factor_result.value) == pytest.approx(
        test_plasma_energy_loss_path_factor
    )
    energy_loss_path_result = resolve(
        "physical.lithography.source_plasma_energy_loss_path_length",
        assignments=plasma_assignments_with_source,
    )
    assert float(energy_loss_path_result.value) == pytest.approx(
        test_plasma_energy_loss_path_length
    )
    particle_mass_result = resolve(
        "physical.lithography.source_plasma_species_particle_mass",
        assignments=plasma_assignments_with_source,
    )
    assert float(particle_mass_result.value) == pytest.approx(
        test_plasma_species_particle_mass
    )
    species_thermal_speed_result = resolve(
        "physical.lithography.source_plasma_species_thermal_speed",
        assignments=plasma_assignments_with_source,
    )
    assert float(species_thermal_speed_result.value) == pytest.approx(
        test_plasma_species_thermal_speed
    )
    transport_factor_result = resolve(
        "physical.lithography.source_plasma_energy_loss_transport_speed_factor",
        assignments=plasma_assignments_with_source,
    )
    assert float(transport_factor_result.value) == pytest.approx(
        test_plasma_energy_loss_transport_speed_factor
    )
    column_expansion_speed_factor_result = resolve(
        "physical.lithography.source_plasma_column_expansion_speed_factor",
        assignments=plasma_assignments_with_source,
    )
    assert float(column_expansion_speed_factor_result.value) == pytest.approx(
        test_plasma_column_expansion_speed_factor
    )
    radial_expansion_speed_result = resolve(
        "physical.lithography.source_plasma_column_radial_expansion_speed",
        assignments=plasma_assignments_with_source,
    )
    assert float(radial_expansion_speed_result.value) == pytest.approx(
        test_plasma_column_radial_expansion_speed
    )
    energy_loss_speed_result = resolve(
        "physical.lithography.source_plasma_energy_loss_speed",
        assignments=plasma_assignments_with_source,
    )
    assert float(energy_loss_speed_result.value) == pytest.approx(
        test_plasma_energy_loss_speed
    )
    confinement_time_result = resolve(
        "physical.lithography.source_plasma_energy_confinement_time",
        assignments=plasma_assignments_with_source,
    )
    assert float(confinement_time_result.value) == pytest.approx(
        test_plasma_energy_confinement_time
    )
    active_lifetime_ratio_result = resolve(
        "physical.lithography.source_plasma_active_lifetime_to_drive_pulse_ratio",
        assignments=plasma_assignments_with_source,
    )
    assert float(active_lifetime_ratio_result.value) == pytest.approx(
        test_plasma_active_lifetime_to_drive_pulse_ratio
    )
    free_electron_yield_result = resolve(
        "physical.lithography.source_plasma_free_electron_yield_per_source_particle",
        assignments=plasma_assignments_with_source,
    )
    assert float(free_electron_yield_result.value) == pytest.approx(
        test_plasma_free_electron_yield
    )
    free_electron_count_result = resolve(
        "physical.lithography.source_plasma_free_electron_count",
        assignments=plasma_assignments_with_source,
    )
    assert float(free_electron_count_result.value) == pytest.approx(
        test_plasma_free_electron_count
    )
    internal_energy_result = resolve(
        "physical.lithography.source_plasma_electron_internal_energy",
        assignments=plasma_assignments_with_source,
    )
    assert float(internal_energy_result.value) == pytest.approx(test_plasma_internal_energy)
    temperature_result = resolve(
        "physical.lithography.source_plasma_electron_temperature",
        assignments=plasma_assignments_with_source,
    )
    assert float(temperature_result.value) == pytest.approx(test_plasma_temperature)
    electron_density_result = resolve(
        "physical.lithography.source_plasma_electron_number_density",
        assignments=plasma_assignments_with_source,
    )
    assert float(electron_density_result.value) == pytest.approx(
        test_plasma_electron_number_density
    )

    mean_energy_result = resolve(
        "physical.lithography.source_plasma_electron_mean_kinetic_energy",
        assignments=plasma_assignments_with_source,
    )
    assert float(mean_energy_result.value) == pytest.approx(
        test_mean_electron_kinetic_energy
    )
    debye_length_result = resolve(
        "physical.lithography.source_plasma_debye_length",
        assignments=plasma_assignments_with_source,
    )
    assert float(debye_length_result.value) == pytest.approx(test_debye_length)

    violated_pulse_duration_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_duration",
        assignments={
            "physical.lithography.source_plasma_drive_pulse_duration": 2.0,
            "physical.lithography.source_plasma_pulse_period": 1.0,
        },
    )
    pulse_duration_check = next(
        c for c in violated_pulse_duration_result.constraints
        if c.equation
        == "physical.ineq.lithography_source_plasma_pulse_duration_within_period"
    )
    assert pulse_duration_check.satisfied is False
    assert pulse_duration_check.missing == set()

    partition_ratio_result = resolve(
        "physical.lithography.source_ionization_partition_ratio",
        assignments={
            "physical.lithography.source_transition_shell_capacity": 8.0,
            "physical.lithography.source_ionization_same_shell_screening_electron_count": 1.0,
        },
    )
    assert float(partition_ratio_result.value) == pytest.approx(2.0 / 7.0)
    assert [step.equation for step in partition_ratio_result.trace] == [
        "physical.eq.lithography_source_ionization_partition_ratio",
    ]
    hydrogen_partition_ratio_result = resolve(
        "physical.lithography.source_ionization_partition_ratio",
        assignments={
            "physical.lithography.source_transition_shell_capacity": 2.0,
            "physical.lithography.source_ionization_same_shell_screening_electron_count": 0.0,
        },
    )
    assert float(hydrogen_partition_ratio_result.value) == pytest.approx(0.5)
    assert (
        Registry.equations[
            "physical.eq.lithography_source_ionization_partition_ratio"
        ].role
        is RelationRole.APPROXIMATION
    )

    ion_charge_result = resolve(
        "physical.lithography.source_ion_charge_state",
        assignments={
            **source_quark_assignments(4, 0),
            "physical.lithography.source_plasma_electron_temperature": test_plasma_temperature,
            "physical.lithography.source_plasma_electron_number_density": test_plasma_electron_number_density,
            "physical.lithography.source_ionization_partition_ratio": 2.0 / 7.0,
            "physical.lithography.source_ionization_energy": 0.0,
        },
    )
    assert float(ion_charge_result.value) == pytest.approx(24.0 / 13.0)

    inner_closed_result = resolve(
        "physical.lithography.source_inner_closed_shell_electron_count",
        assignments={
            **source_quark_assignments(4, 0),
            **plasma_assignments_for_source(4),
            "physical.lithography.source_ionization_partition_ratio": 0.0,
        },
    )
    assert float(inner_closed_result.value) == pytest.approx(2.0)

    outer_shell_result = resolve(
        "physical.lithography.source_outer_shell_electron_count",
        assignments={
            **source_quark_assignments(12, 0),
            **plasma_assignments_for_source(12),
            "physical.lithography.source_ionization_partition_ratio": 0.0,
        },
    )
    assert float(outer_shell_result.value) == pytest.approx(0.0)

    binding_result = resolve(
        "physical.lithography.source_nuclear_binding_energy",
        assignments={
            **source_quark_assignments(2, 2),
            "physical.lithography.nuclear_binding_coulomb_coefficient": test_coulomb_coeff,
            "physical.lithography.nuclear_binding_volume_coefficient": test_volume_coeff,
            "physical.lithography.nuclear_binding_surface_coefficient": test_surface_coeff,
            "physical.lithography.nuclear_binding_asymmetry_coefficient": test_asymmetry_coeff,
            "physical.lithography.nuclear_pairing_gap_reference_energy": test_pairing_gap_ref,
        },
    )
    assert float(binding_result.value) == pytest.approx(
        10.0 * 4.0
        - 2.0 * 4.0 ** (2.0 / 3.0)
        - 0.5 * 2.0 * 1.0 / 4.0 ** (1.0 / 3.0)
        + 2.0 / 4.0 ** 0.5
    )

    assert float(resolve(
        "physical.lithography.source_pairing_sign",
        assignments=source_quark_assignments(2, 2),
    ).value) == pytest.approx(1.0)
    assert float(resolve(
        "physical.lithography.source_pairing_sign",
        assignments=source_quark_assignments(3, 3),
    ).value) == pytest.approx(-1.0)
    assert float(resolve(
        "physical.lithography.source_pairing_sign",
        assignments=source_quark_assignments(2, 3),
    ).value) == pytest.approx(0.0)

    screening_result = resolve(
        "physical.lithography.source_screening_constant",
        assignments={
            **source_quark_assignments(4, 0),
            **plasma_assignments_for_source(4),
            "physical.lithography.source_ionization_partition_ratio": 0.0,
        },
    )
    assert float(screening_result.value) == pytest.approx(2.5)

    energy_result = resolve(
        "physical.lithography.photon_energy",
        assignments=assignments,
    )
    assert float(energy_result.value) == pytest.approx(expected_energy)

    wavelength_result = resolve(
        "physical.lithography.wavelength",
        assignments=assignments,
    )
    assert float(wavelength_result.value) == pytest.approx(
        planck * c / expected_energy
    )
