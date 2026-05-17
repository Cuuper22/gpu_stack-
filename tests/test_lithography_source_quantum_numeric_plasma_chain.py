"""Lithography source quantum numeric plasma closure coverage."""

import pytest

from gpu_stack import resolve
from tests.helpers.lithography_source_quantum import source_quantum_numeric_case


def test_lithography_source_quantum_numeric_plasma_resolves_drive_and_geometry_terms():
    case = source_quantum_numeric_case()

    absorbed_power_result = resolve(
        "physical.lithography.source_plasma_absorbed_power",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(absorbed_power_result.value) == pytest.approx(case.test_plasma_absorbed_power)
    drive_power_result = resolve(
        "physical.lithography.source_plasma_drive_power",
        assignments=case.plasma_assignments,
    )
    assert float(drive_power_result.value) == pytest.approx(case.test_plasma_drive_power)
    pulse_duration_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_duration",
        assignments=case.plasma_assignments,
    )
    assert float(pulse_duration_result.value) == pytest.approx(
        case.test_plasma_drive_pulse_duration
    )
    pulse_fall_fraction_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_fall_fraction",
        assignments=case.plasma_assignments,
    )
    assert float(pulse_fall_fraction_result.value) == pytest.approx(
        case.test_plasma_drive_pulse_fall_fraction
    )
    pulse_flat_fraction_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_flat_fraction",
        assignments=case.plasma_assignments,
    )
    assert float(pulse_flat_fraction_result.value) == pytest.approx(
        case.test_plasma_drive_pulse_flat_fraction
    )
    pulse_shape_result = resolve(
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
        assignments=case.plasma_assignments,
    )
    assert float(pulse_shape_result.value) == pytest.approx(
        case.test_plasma_drive_pulse_temporal_shape_factor
    )
    peak_intensity_result = resolve(
        "physical.lithography.source_plasma_drive_peak_intensity",
        assignments=case.plasma_assignments,
    )
    assert float(peak_intensity_result.value) == pytest.approx(
        case.test_plasma_drive_peak_intensity
    )
    waist_coefficient_result = resolve(
        "physical.lithography.source_plasma_drive_focus_waist_coefficient",
        assignments=case.plasma_assignments,
    )
    assert float(waist_coefficient_result.value) == pytest.approx(
        case.test_plasma_drive_focus_waist_coefficient
    )
    acceptance_half_angle_result = resolve(
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
        assignments=case.plasma_assignments,
    )
    assert float(acceptance_half_angle_result.value) == pytest.approx(
        case.test_plasma_drive_acceptance_half_angle
    )
    numerical_aperture_result = resolve(
        "physical.lithography.source_plasma_drive_numerical_aperture",
        assignments=case.plasma_assignments,
    )
    assert float(numerical_aperture_result.value) == pytest.approx(
        case.test_plasma_drive_numerical_aperture
    )
    focus_f_number_result = resolve(
        "physical.lithography.source_plasma_drive_focus_f_number",
        assignments=case.plasma_assignments,
    )
    assert float(focus_f_number_result.value) == pytest.approx(
        case.test_plasma_drive_focus_f_number
    )
    beam_parameter_waist_result = resolve(
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius",
        assignments=case.plasma_assignments,
    )
    assert float(beam_parameter_waist_result.value) == pytest.approx(
        case.test_plasma_drive_beam_parameter_waist_radius
    )
    beam_parameter_product_result = resolve(
        "physical.lithography.source_plasma_drive_beam_parameter_product",
        assignments=case.plasma_assignments,
    )
    assert float(beam_parameter_product_result.value) == pytest.approx(
        case.test_plasma_drive_beam_parameter_product
    )
    beam_quality_result = resolve(
        "physical.lithography.source_plasma_drive_beam_quality_factor",
        assignments=case.plasma_assignments,
    )
    assert float(beam_quality_result.value) == pytest.approx(
        case.test_plasma_drive_beam_quality_factor
    )
    spot_axis_ratio_result = resolve(
        "physical.lithography.source_plasma_drive_spot_axis_ratio",
        assignments=case.plasma_assignments,
    )
    assert float(spot_axis_ratio_result.value) == pytest.approx(
        case.test_plasma_drive_spot_axis_ratio
    )
    spot_area_fill_factor_result = resolve(
        "physical.lithography.source_plasma_drive_spot_area_fill_factor",
        assignments=case.plasma_assignments,
    )
    assert float(spot_area_fill_factor_result.value) == pytest.approx(
        case.test_plasma_drive_spot_area_fill_factor
    )
    spot_radius_result = resolve(
        "physical.lithography.source_plasma_drive_spot_radius",
        assignments=case.plasma_assignments,
    )
    assert float(spot_radius_result.value) == pytest.approx(case.test_plasma_drive_spot_radius)
    rayleigh_range_result = resolve(
        "physical.lithography.source_plasma_drive_rayleigh_range",
        assignments=case.plasma_assignments,
    )
    assert float(rayleigh_range_result.value) == pytest.approx(
        case.test_plasma_drive_rayleigh_range
    )
    confocal_length_result = resolve(
        "physical.lithography.source_plasma_drive_confocal_length",
        assignments=case.plasma_assignments,
    )
    assert float(confocal_length_result.value) == pytest.approx(
        case.test_plasma_drive_confocal_length
    )
    spot_shape_result = resolve(
        "physical.lithography.source_plasma_drive_spot_shape_factor",
        assignments=case.plasma_assignments,
    )
    assert float(spot_shape_result.value) == pytest.approx(
        case.test_plasma_drive_spot_shape_factor
    )
    column_expansion_result = resolve(
        "physical.lithography.source_plasma_column_radius_expansion_factor",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(column_expansion_result.value) == pytest.approx(
        case.test_plasma_column_radius_expansion_factor
    )
    column_aspect_result = resolve(
        "physical.lithography.source_plasma_column_aspect_ratio",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(column_aspect_result.value) == pytest.approx(
        case.test_plasma_column_aspect_ratio
    )
    species_density_result = resolve(
        "physical.lithography.source_plasma_species_number_density",
        assignments=case.plasma_assignments,
    )
    assert float(species_density_result.value) == pytest.approx(
        case.test_plasma_species_number_density
    )


def test_lithography_source_quantum_numeric_plasma_resolves_absorption_and_overlap_terms():
    case = source_quantum_numeric_case()

    absorption_path_direction_cosine_result = resolve(
        "physical.lithography.source_plasma_absorption_path_direction_cosine",
        assignments=case.plasma_assignments,
    )
    assert float(absorption_path_direction_cosine_result.value) == pytest.approx(
        case.test_plasma_absorption_path_direction_cosine
    )
    absorption_path_shape_result = resolve(
        "physical.lithography.source_plasma_absorption_path_shape_factor",
        assignments=case.plasma_assignments,
    )
    assert float(absorption_path_shape_result.value) == pytest.approx(
        case.test_plasma_absorption_path_shape_factor
    )
    absorption_path_result = resolve(
        "physical.lithography.source_plasma_absorption_path_length",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(absorption_path_result.value) == pytest.approx(
        case.test_plasma_absorption_path_length
    )
    drive_beam_angular_frequency_result = resolve(
        "physical.lithography.source_plasma_drive_beam_angular_frequency",
        assignments=case.plasma_assignments,
    )
    assert float(drive_beam_angular_frequency_result.value) == pytest.approx(
        case.test_plasma_drive_beam_angular_frequency
    )
    absorption_resonance_result = resolve(
        "physical.lithography.source_plasma_absorption_resonance_angular_frequency",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(absorption_resonance_result.value) == pytest.approx(
        case.test_plasma_absorption_resonance
    )
    collision_orbital_radius_result = resolve(
        "physical.lithography.source_plasma_absorption_collision_orbital_radius",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(collision_orbital_radius_result.value) == pytest.approx(
        case.test_plasma_absorption_collision_orbital_radius
    )
    collision_cross_section_result = resolve(
        "physical.lithography.source_plasma_absorption_collision_cross_section",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(collision_cross_section_result.value) == pytest.approx(
        case.test_plasma_absorption_collision_cross_section
    )
    absorption_damping_result = resolve(
        "physical.lithography.source_plasma_absorption_damping_rate",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(absorption_damping_result.value) == pytest.approx(
        case.test_plasma_absorption_damping_rate
    )
    absorption_quality_result = resolve(
        "physical.lithography.source_plasma_absorption_quality_factor",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(absorption_quality_result.value) == pytest.approx(
        case.test_plasma_absorption_quality_factor
    )
    absorption_oscillator_result = resolve(
        "physical.lithography.source_plasma_absorption_oscillator_strength",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(absorption_oscillator_result.value) == pytest.approx(
        case.test_plasma_absorption_oscillator_strength
    )
    absorption_cross_section_result = resolve(
        "physical.lithography.source_plasma_absorption_cross_section",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(absorption_cross_section_result.value) == pytest.approx(
        case.test_plasma_absorption_cross_section
    )
    absorption_depth_result = resolve(
        "physical.lithography.source_plasma_absorption_optical_depth",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(absorption_depth_result.value) == pytest.approx(
        case.test_plasma_absorption_optical_depth
    )
    absorption_fraction_result = resolve(
        "physical.lithography.source_plasma_drive_energy_absorption_fraction",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(absorption_fraction_result.value) == pytest.approx(
        case.test_plasma_drive_energy_absorption_fraction
    )
    overlap_result = resolve(
        "physical.lithography.source_plasma_drive_overlap_factor",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(overlap_result.value) == pytest.approx(
        case.test_plasma_drive_overlap_factor
    )
    ideal_overlap_assignments = {
        key: value
        for key, value in case.plasma_assignments_with_source.items()
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
        case.test_plasma_drive_overlap_factor / case.test_plasma_active_fill_factor
    )
    ideal_overlap_trace = {step.equation for step in ideal_overlap_result.trace}
    assert {
        "physical.eq.lithography_source_plasma_active_fill_factor_from_ideal_column_convention",
        "physical.eq.lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio_from_coaxial_convention",
        "physical.eq.lithography_source_plasma_drive_timing_offset_fraction_from_synchronized_convention",
    } <= ideal_overlap_trace
    absorption_result = resolve(
        "physical.lithography.source_plasma_absorption_efficiency",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(absorption_result.value) == pytest.approx(
        case.test_plasma_absorption_efficiency
    )


def test_lithography_source_quantum_numeric_plasma_resolves_transport_and_electron_terms():
    case = source_quantum_numeric_case()

    active_volume_result = resolve(
        "physical.lithography.source_plasma_active_volume",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(active_volume_result.value) == pytest.approx(case.test_plasma_active_volume)
    energy_loss_direction_result = resolve(
        "physical.lithography.source_plasma_energy_loss_path_direction_cosine",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(energy_loss_direction_result.value) == pytest.approx(
        case.test_plasma_energy_loss_path_direction_cosine
    )
    energy_loss_path_factor_result = resolve(
        "physical.lithography.source_plasma_energy_loss_path_factor",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(energy_loss_path_factor_result.value) == pytest.approx(
        case.test_plasma_energy_loss_path_factor
    )
    energy_loss_path_result = resolve(
        "physical.lithography.source_plasma_energy_loss_path_length",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(energy_loss_path_result.value) == pytest.approx(
        case.test_plasma_energy_loss_path_length
    )
    particle_mass_result = resolve(
        "physical.lithography.source_plasma_species_particle_mass",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(particle_mass_result.value) == pytest.approx(
        case.test_plasma_species_particle_mass
    )
    species_thermal_speed_result = resolve(
        "physical.lithography.source_plasma_species_thermal_speed",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(species_thermal_speed_result.value) == pytest.approx(
        case.test_plasma_species_thermal_speed
    )
    transport_factor_result = resolve(
        "physical.lithography.source_plasma_energy_loss_transport_speed_factor",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(transport_factor_result.value) == pytest.approx(
        case.test_plasma_energy_loss_transport_speed_factor
    )
    column_expansion_speed_factor_result = resolve(
        "physical.lithography.source_plasma_column_expansion_speed_factor",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(column_expansion_speed_factor_result.value) == pytest.approx(
        case.test_plasma_column_expansion_speed_factor
    )
    radial_expansion_speed_result = resolve(
        "physical.lithography.source_plasma_column_radial_expansion_speed",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(radial_expansion_speed_result.value) == pytest.approx(
        case.test_plasma_column_radial_expansion_speed
    )
    energy_loss_speed_result = resolve(
        "physical.lithography.source_plasma_energy_loss_speed",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(energy_loss_speed_result.value) == pytest.approx(
        case.test_plasma_energy_loss_speed
    )
    confinement_time_result = resolve(
        "physical.lithography.source_plasma_energy_confinement_time",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(confinement_time_result.value) == pytest.approx(
        case.test_plasma_energy_confinement_time
    )
    active_lifetime_ratio_result = resolve(
        "physical.lithography.source_plasma_active_lifetime_to_drive_pulse_ratio",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(active_lifetime_ratio_result.value) == pytest.approx(
        case.test_plasma_active_lifetime_to_drive_pulse_ratio
    )
    free_electron_yield_result = resolve(
        "physical.lithography.source_plasma_free_electron_yield_per_source_particle",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(free_electron_yield_result.value) == pytest.approx(
        case.test_plasma_free_electron_yield
    )
    free_electron_count_result = resolve(
        "physical.lithography.source_plasma_free_electron_count",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(free_electron_count_result.value) == pytest.approx(
        case.test_plasma_free_electron_count
    )
    internal_energy_result = resolve(
        "physical.lithography.source_plasma_electron_internal_energy",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(internal_energy_result.value) == pytest.approx(case.test_plasma_internal_energy)
    temperature_result = resolve(
        "physical.lithography.source_plasma_electron_temperature",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(temperature_result.value) == pytest.approx(case.test_plasma_temperature)
    electron_density_result = resolve(
        "physical.lithography.source_plasma_electron_number_density",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(electron_density_result.value) == pytest.approx(
        case.test_plasma_electron_number_density
    )

    mean_energy_result = resolve(
        "physical.lithography.source_plasma_electron_mean_kinetic_energy",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(mean_energy_result.value) == pytest.approx(
        case.test_mean_electron_kinetic_energy
    )
    debye_length_result = resolve(
        "physical.lithography.source_plasma_debye_length",
        assignments=case.plasma_assignments_with_source,
    )
    assert float(debye_length_result.value) == pytest.approx(case.test_debye_length)


def test_lithography_source_quantum_numeric_plasma_reports_pulse_duration_constraint():
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
