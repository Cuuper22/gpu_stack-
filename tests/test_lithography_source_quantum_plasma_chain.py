"""Lithography source quantum plasma-chain structure coverage."""

import sympy as sp

from gpu_stack.core import Inequality, RelationRole
from tests.helpers.lithography_source_quantum import source_quantum_model


def test_lithography_source_quantum_plasma_drive_and_focus_dependencies():
    model = source_quantum_model()

    assert {v.name for v in model.plasma_pulse_repetition_rate.direct_dependencies()} == {
        "physical.lithography.source_plasma_pulse_period",
    }
    assert model.plasma_drive_pulse_duty_factor.direct_dependencies() == set()
    assert model.plasma_drive_pulse_fluence.direct_dependencies() == set()
    assert {v.name for v in model.plasma_drive_pulse_duration.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_duty_factor",
        "physical.lithography.source_plasma_pulse_period",
    }
    assert model.plasma_drive_pulse_rise_fraction.direct_dependencies() == set()
    assert {v.name for v in model.plasma_drive_pulse_fall_fraction.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_rise_fraction",
    }
    assert {v.name for v in model.plasma_drive_pulse_flat_fraction.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_fall_fraction",
        "physical.lithography.source_plasma_drive_pulse_rise_fraction",
    }
    assert {
        v.name for v in model.plasma_drive_pulse_temporal_shape_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_drive_pulse_fall_fraction",
        "physical.lithography.source_plasma_drive_pulse_flat_fraction",
        "physical.lithography.source_plasma_drive_pulse_rise_fraction",
    }
    assert {v.name for v in model.plasma_drive_peak_intensity.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_pulse_fluence",
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
    }
    assert model.plasma_drive_focus_waist_coefficient.direct_dependencies() == set()
    assert {v.name for v in model.plasma_drive_beam_wavelength.direct_dependencies()} == {
        "physical.lithography.source_ionization_energy",
        "physical.lithography.source_plasma_drive_edge_detuning_ratio",
        "physics.hbar",
        "physics.speed_of_light",
    }
    assert {v.name for v in model.plasma_drive_acceptance_half_angle.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_objective_focal_length",
        "physical.lithography.source_plasma_drive_objective_pupil_radius",
    }
    assert {v.name for v in model.plasma_drive_numerical_aperture.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    }
    assert {v.name for v in model.plasma_drive_focus_f_number.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    }
    assert {
        v.name for v in model.plasma_drive_beam_parameter_waist_radius.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_drive_objective_pupil_radius",
        "physical.lithography.source_plasma_drive_pupil_beam_fill_factor",
    }
    assert {v.name for v in model.plasma_drive_beam_parameter_product.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius",
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle",
    }
    assert {
        v.name
        for v in model.plasma_drive_beam_parameter_product.direct_dependencies(
            include_constraints=True
        )
    } == {
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius",
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle",
        "physical.lithography.source_plasma_drive_beam_wavelength",
    }
    beam_parameter_product_floor = model.plasma_drive_beam_parameter_product.constraints()[0]
    assert isinstance(beam_parameter_product_floor, Inequality)
    assert beam_parameter_product_floor.name == (
        "physical.ineq.lithography_source_plasma_drive_beam_parameter_product_diffraction_floor"
    )
    assert beam_parameter_product_floor.role is RelationRole.CONSTRAINT
    assert beam_parameter_product_floor.op == ">="
    assert isinstance(beam_parameter_product_floor.as_sympy(), sp.Rel)
    assert beam_parameter_product_floor.references
    assert getattr(beam_parameter_product_floor, "_check_units_flag", False)
    assert {v.name for v in model.plasma_drive_beam_quality_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_parameter_product",
        "physical.lithography.source_plasma_drive_beam_wavelength",
    }
    assert {
        v.name
        for v in model.plasma_drive_beam_quality_factor.direct_dependencies(
            include_constraints=True
        )
    } == {
        "physical.lithography.source_plasma_drive_beam_parameter_product",
        "physical.lithography.source_plasma_drive_beam_wavelength",
    }
    beam_quality_factor_floor = model.plasma_drive_beam_quality_factor.constraints()[0]
    assert isinstance(beam_quality_factor_floor, Inequality)
    assert beam_quality_factor_floor.name == (
        "physical.ineq.lithography_source_plasma_drive_beam_quality_factor_diffraction_limit"
    )
    assert beam_quality_factor_floor.role is RelationRole.CONSTRAINT
    assert beam_quality_factor_floor.op == ">="
    assert isinstance(beam_quality_factor_floor.as_sympy(), sp.Rel)
    assert beam_quality_factor_floor.references
    assert getattr(beam_quality_factor_floor, "_check_units_flag", False)
    assert {v.name for v in model.plasma_drive_spot_radius.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_quality_factor",
        "physical.lithography.source_plasma_drive_beam_wavelength",
        "physical.lithography.source_plasma_drive_focus_f_number",
        "physical.lithography.source_plasma_drive_focus_waist_coefficient",
    }
    assert {v.name for v in model.plasma_drive_rayleigh_range.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_quality_factor",
        "physical.lithography.source_plasma_drive_beam_wavelength",
        "physical.lithography.source_plasma_drive_spot_radius",
    }
    assert {v.name for v in model.plasma_drive_confocal_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_rayleigh_range",
    }
    assert {v.name for v in model.plasma_drive_spot_shape_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_spot_area_fill_factor",
        "physical.lithography.source_plasma_drive_spot_axis_ratio",
    }
    assert not model.plasma_drive_spot_axis_ratio.direct_dependencies()
    assert not model.plasma_drive_spot_area_fill_factor.direct_dependencies()
    assert {v.name for v in model.plasma_drive_spot_area.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_spot_radius",
        "physical.lithography.source_plasma_drive_spot_shape_factor",
    }
    assert {v.name for v in model.plasma_pulse_energy.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_peak_intensity",
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
        "physical.lithography.source_plasma_drive_spot_area",
    }
    assert {v.name for v in model.plasma_drive_power.direct_dependencies()} == {
        "physical.lithography.source_plasma_pulse_energy",
        "physical.lithography.source_plasma_pulse_repetition_rate",
    }


def test_lithography_source_quantum_plasma_column_absorption_and_overlap_dependencies():
    model = source_quantum_model()

    assert {v.name for v in model.plasma_species_number_density.direct_dependencies()} == {
        "physical.lithography.source_plasma_species_partial_pressure",
        "physical.lithography.source_plasma_species_gas_temperature",
        "physics.boltzmann",
    }
    assert not model.plasma_column_expansion_speed_factor.direct_dependencies()
    assert {v.name for v in model.plasma_column_radial_expansion_speed.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_expansion_speed_factor",
        "physical.lithography.source_plasma_species_thermal_speed",
    }
    assert {
        v.name for v in model.plasma_column_radius_expansion_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_column_radial_expansion_speed",
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_spot_radius",
    }
    assert {v.name for v in model.plasma_column_radius.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_radius_expansion_factor",
        "physical.lithography.source_plasma_drive_spot_radius",
    }
    assert {v.name for v in model.plasma_column_aspect_ratio.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_radius",
        "physical.lithography.source_plasma_drive_confocal_length",
    }
    assert {v.name for v in model.plasma_column_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_aspect_ratio",
        "physical.lithography.source_plasma_column_radius",
    }
    assert model.plasma_active_fill_factor.direct_dependencies() == set()
    assert {v.name for v in model.plasma_active_volume.direct_dependencies()} == {
        "physical.lithography.source_plasma_column_radius",
        "physical.lithography.source_plasma_column_length",
        "physical.lithography.source_plasma_active_fill_factor",
    }
    assert {v.name for v in model.plasma_absorption_path_direction_cosine.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    }
    assert {v.name for v in model.plasma_absorption_path_shape_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_path_direction_cosine",
    }
    assert {v.name for v in model.plasma_absorption_path_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_path_shape_factor",
        "physical.lithography.source_plasma_column_length",
    }
    assert {v.name for v in model.plasma_drive_beam_angular_frequency.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_beam_wavelength",
        "physics.speed_of_light",
    }
    assert {v.name for v in model.plasma_absorption_resonance_to_drive_ratio.direct_dependencies()} == {
        "physical.lithography.source_ionization_energy",
        "physical.lithography.source_plasma_drive_beam_angular_frequency",
        "physics.hbar",
    }
    assert {v.name for v in model.plasma_absorption_quality_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_damping_rate",
        "physical.lithography.source_plasma_absorption_resonance_angular_frequency",
    }
    assert {
        v.name for v in model.plasma_absorption_collision_orbital_radius.direct_dependencies()
    } == {
        "physical.lithography.source_ionization_effective_nuclear_charge",
        "physical.lithography.source_ionization_principal_quantum_number",
        "physics.bohr_radius",
    }
    assert {v.name for v in model.plasma_absorption_collision_cross_section.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_collision_orbital_radius",
    }
    assert {
        v.name for v in model.plasma_absorption_participating_electron_fraction.direct_dependencies()
    } == {
        "physical.lithography.source_ionization_same_shell_screening_electron_count",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in model.plasma_absorption_sum_rule_fraction.direct_dependencies()} == {
        "physical.lithography.source_ionization_same_shell_screening_electron_count",
        "physical.lithography.source_transition_shell_capacity",
    }
    assert {v.name for v in model.plasma_absorption_resonance.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_resonance_to_drive_ratio",
        "physical.lithography.source_plasma_drive_beam_angular_frequency",
    }
    assert {v.name for v in model.plasma_absorption_damping_rate.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_collision_cross_section",
        "physical.lithography.source_plasma_species_number_density",
        "physical.lithography.source_plasma_species_thermal_speed",
    }
    assert {
        v.name for v in model.plasma_absorption_oscillator_strength.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_absorption_participating_electron_fraction",
        "physical.lithography.source_plasma_absorption_sum_rule_fraction",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in model.plasma_absorption_cross_section.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_damping_rate",
        "physical.lithography.source_plasma_absorption_oscillator_strength",
        "physical.lithography.source_plasma_absorption_resonance_angular_frequency",
        "physical.lithography.source_plasma_drive_beam_angular_frequency",
        "physics.elementary_charge",
        "physics.electron_mass",
        "physics.speed_of_light",
        "physics.vacuum_permittivity",
    }
    assert {v.name for v in model.plasma_absorption_optical_depth.direct_dependencies()} == {
        "physical.lithography.source_plasma_species_number_density",
        "physical.lithography.source_plasma_absorption_cross_section",
        "physical.lithography.source_plasma_absorption_path_length",
    }
    assert {
        v.name for v in model.plasma_drive_energy_absorption_fraction.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_absorption_optical_depth",
    }
    assert {
        v.name for v in model.plasma_drive_pointing_overlap_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_drive_centroid_offset_to_column_radius_ratio",
    }
    assert (
        model.plasma_drive_centroid_offset_to_column_radius_ratio.direct_dependencies()
        == set()
    )
    assert {
        v.name for v in model.plasma_drive_transverse_overlap_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_column_radius",
        "physical.lithography.source_plasma_drive_spot_area",
    }
    assert {v.name for v in model.plasma_drive_spatial_overlap_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_active_fill_factor",
        "physical.lithography.source_plasma_drive_pointing_overlap_factor",
        "physical.lithography.source_plasma_drive_transverse_overlap_factor",
    }
    assert {
        v.name for v in model.plasma_active_lifetime_to_drive_pulse_ratio.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_energy_confinement_time",
    }
    assert {v.name for v in model.plasma_active_response_duration.direct_dependencies()} == {
        "physical.lithography.source_plasma_active_lifetime_to_drive_pulse_ratio",
        "physical.lithography.source_plasma_drive_pulse_duration",
    }
    assert model.plasma_drive_timing_offset_fraction.direct_dependencies() == set()
    assert {v.name for v in model.plasma_drive_timing_offset_duration.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_timing_offset_fraction",
    }
    assert {
        v.name for v in model.plasma_drive_temporal_duration_match_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_active_response_duration",
        "physical.lithography.source_plasma_drive_pulse_duration",
    }
    assert {
        v.name for v in model.plasma_drive_temporal_alignment_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_active_response_duration",
        "physical.lithography.source_plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_timing_offset_duration",
    }
    assert {v.name for v in model.plasma_drive_temporal_overlap_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_temporal_alignment_factor",
        "physical.lithography.source_plasma_drive_temporal_duration_match_factor",
    }
    assert {v.name for v in model.plasma_drive_overlap_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_spatial_overlap_factor",
        "physical.lithography.source_plasma_drive_temporal_overlap_factor",
    }
    assert {v.name for v in model.plasma_absorption_efficiency.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_overlap_factor",
        "physical.lithography.source_plasma_drive_energy_absorption_fraction",
        "physical.lithography.source_plasma_electron_heating_fraction",
    }
    assert {v.name for v in model.plasma_absorbed_power.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorption_efficiency",
        "physical.lithography.source_plasma_drive_power",
    }
    assert {v.name for v in model.plasma_energy_loss_path_direction_cosine.direct_dependencies()} == {
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    }
    assert {v.name for v in model.plasma_energy_loss_path_factor.direct_dependencies()} == {
        "physical.lithography.source_plasma_energy_loss_path_direction_cosine",
    }
    assert {v.name for v in model.plasma_energy_loss_path_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_energy_loss_path_factor",
        "physical.lithography.source_plasma_column_radius",
    }
    assert {v.name for v in model.plasma_species_particle_mass.direct_dependencies()} == {
        "physical.lithography.source_neutron_count",
        "physical.lithography.source_proton_count",
        "physics.neutron_mass",
        "physics.proton_mass",
    }
    assert {v.name for v in model.plasma_species_thermal_speed.direct_dependencies()} == {
        "physical.lithography.source_plasma_species_gas_temperature",
        "physical.lithography.source_plasma_species_particle_mass",
        "physics.boltzmann",
    }
    assert {
        v.name for v in model.plasma_energy_loss_transport_speed_factor.direct_dependencies()
    } == {
        "physical.lithography.source_plasma_species_particle_mass",
        "physics.electron_mass",
    }


def test_lithography_source_quantum_plasma_approximations_and_electron_energy_dependencies():
    model = source_quantum_model()

    assert [e.name for e in model.plasma_drive_spot_axis_ratio.approximations()] == [
        "physical.eq.lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention",
    ]
    assert [e.name for e in model.plasma_drive_spot_area_fill_factor.approximations()] == [
        "physical.eq.lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention",
    ]
    assert [e.name for e in model.plasma_drive_rayleigh_range.approximations()] == [
        "physical.eq.lithography_source_plasma_drive_rayleigh_range_from_spot_geometry",
    ]
    assert [e.name for e in model.plasma_drive_confocal_length.approximations()] == [
        "physical.eq.lithography_source_plasma_drive_confocal_length_from_rayleigh_range",
    ]
    assert [e.name for e in model.plasma_column_expansion_speed_factor.approximations()] == [
        "physical.eq.lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed",
    ]
    assert [e.name for e in model.plasma_column_aspect_ratio.approximations()] == [
        "physical.eq.lithography_source_plasma_column_aspect_ratio_from_confocal_length",
    ]
    active_fill_eq = model.plasma_active_fill_factor.approximations()[0]
    assert active_fill_eq.name == (
        "physical.eq.lithography_source_plasma_active_fill_factor_from_ideal_column_convention"
    )
    assert active_fill_eq.rhs == sp.Integer(1)
    assert [e.name for e in model.plasma_absorption_collision_orbital_radius.approximations()] == [
        "physical.eq.lithography_source_plasma_absorption_collision_orbital_radius_from_hydrogenic_shell",
    ]
    assert [e.name for e in model.plasma_absorption_collision_cross_section.approximations()] == [
        "physical.eq.lithography_source_plasma_absorption_collision_cross_section_from_orbital_area",
    ]
    centroid_offset_eq = (
        model.plasma_drive_centroid_offset_to_column_radius_ratio.approximations()[0]
    )
    assert centroid_offset_eq.name == (
        "physical.eq.lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio_from_coaxial_convention"
    )
    assert centroid_offset_eq.rhs == sp.Integer(0)
    timing_offset_eq = model.plasma_drive_timing_offset_fraction.approximations()[0]
    assert timing_offset_eq.name == (
        "physical.eq.lithography_source_plasma_drive_timing_offset_fraction_from_synchronized_convention"
    )
    assert timing_offset_eq.rhs == sp.Integer(0)
    assert {v.name for v in model.plasma_energy_loss_speed.direct_dependencies()} == {
        "physical.lithography.source_plasma_energy_loss_transport_speed_factor",
        "physical.lithography.source_plasma_species_thermal_speed",
    }
    assert {v.name for v in model.plasma_confinement_time.direct_dependencies()} == {
        "physical.lithography.source_plasma_energy_loss_path_length",
        "physical.lithography.source_plasma_energy_loss_speed",
    }
    assert {v.name for v in model.plasma_free_electron_yield.direct_dependencies()} == {
        "physical.lithography.source_plasma_free_electron_inventory_charge_fraction",
        "physical.lithography.source_proton_count",
    }
    assert {v.name for v in model.plasma_free_electron_count.direct_dependencies()} == {
        "physical.lithography.source_plasma_species_number_density",
        "physical.lithography.source_plasma_active_volume",
        "physical.lithography.source_plasma_free_electron_yield_per_source_particle",
    }
    assert {v.name for v in model.plasma_internal_energy.direct_dependencies()} == {
        "physical.lithography.source_plasma_absorbed_power",
        "physical.lithography.source_plasma_energy_confinement_time",
    }
    assert {v.name for v in model.plasma_temperature.direct_dependencies()} == {
        "physical.lithography.source_plasma_electron_internal_energy",
        "physical.lithography.source_plasma_free_electron_count",
        "physics.boltzmann",
    }
    assert {v.name for v in model.plasma_density.direct_dependencies()} == {
        "physical.lithography.source_plasma_active_volume",
        "physical.lithography.source_plasma_free_electron_count",
    }
    assert {v.name for v in model.plasma_mean_energy.direct_dependencies()} == {
        "physical.lithography.source_plasma_electron_temperature",
        "physics.boltzmann",
    }
    assert {v.name for v in model.plasma_debye_length.direct_dependencies()} == {
        "physical.lithography.source_plasma_electron_number_density",
        "physical.lithography.source_plasma_electron_temperature",
        "physics.boltzmann",
        "physics.elementary_charge",
        "physics.vacuum_permittivity",
    }
