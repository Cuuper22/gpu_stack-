"""Symbolic lithography source quantum registry lookups."""

from __future__ import annotations

from types import SimpleNamespace

from gpu_stack import Registry

_NUCLEAR_VARIABLES = (
    ("photon_energy", "physical.lithography.photon_energy"),
    ("up_quarks", "physical.lithography.source_valence_up_quark_count"),
    ("down_quarks", "physical.lithography.source_valence_down_quark_count"),
    ("atomic_number", "physical.lithography.source_atomic_number"),
    ("isotope_mass_number", "physical.lithography.source_isotope_mass_number"),
    ("proton_count", "physical.lithography.source_proton_count"),
    ("neutron_count", "physical.lithography.source_neutron_count"),
    ("binding_energy", "physical.lithography.source_nuclear_binding_energy"),
    ("mass_number", "physical.lithography.source_mass_number"),
    ("neutron_excess", "physical.lithography.source_neutron_excess"),
    (
        "saturation_density",
        "physical.lithography.source_nuclear_saturation_number_density",
    ),
    ("radius_coeff", "physical.lithography.source_nuclear_radius_coefficient"),
    (
        "bulk_binding_density",
        "physical.lithography.source_nuclear_bulk_binding_energy_density",
    ),
    ("volume_coeff", "physical.lithography.source_binding_volume_coefficient"),
    ("surface_tension", "physical.lithography.source_nuclear_surface_tension"),
    ("surface_coeff", "physical.lithography.source_binding_surface_coefficient"),
    (
        "symmetry_density",
        "physical.lithography.source_nuclear_symmetry_energy_density",
    ),
    ("asymmetry_coeff", "physical.lithography.source_binding_asymmetry_coefficient"),
    (
        "pairing_gap_ref",
        "physical.lithography.source_nuclear_pairing_gap_reference_energy",
    ),
    (
        "shared_volume_coeff",
        "physical.lithography.nuclear_binding_volume_coefficient",
    ),
    (
        "shared_surface_coeff",
        "physical.lithography.nuclear_binding_surface_coefficient",
    ),
    (
        "shared_coulomb_coeff",
        "physical.lithography.nuclear_binding_coulomb_coefficient",
    ),
    (
        "shared_asymmetry_coeff",
        "physical.lithography.nuclear_binding_asymmetry_coefficient",
    ),
    (
        "shared_pairing_gap_ref",
        "physical.lithography.nuclear_pairing_gap_reference_energy",
    ),
    (
        "pairing_mass_ref",
        "physical.lithography.source_pairing_reference_mass_number",
    ),
    ("pairing_coeff", "physical.lithography.source_binding_pairing_coefficient"),
    ("coulomb_coeff", "physical.lithography.source_binding_coulomb_coefficient"),
    ("volume_term", "physical.lithography.source_binding_volume_term"),
    ("surface_term", "physical.lithography.source_binding_surface_term"),
    ("coulomb_term", "physical.lithography.source_binding_coulomb_term"),
    ("asymmetry_term", "physical.lithography.source_binding_asymmetry_term"),
    ("pairing_sign", "physical.lithography.source_pairing_sign"),
    ("pairing_term", "physical.lithography.source_binding_pairing_term"),
    ("nuclear_mass", "physical.lithography.source_nuclear_mass"),
    ("reduced_mass", "physical.lithography.source_reduced_mass"),
    ("reduced_ratio", "physical.lithography.source_reduced_mass_ratio"),
)

_PLASMA_DRIVE_VARIABLES = (
    ("plasma_pulse_period", "physical.lithography.source_plasma_pulse_period"),
    ("plasma_pulse_energy", "physical.lithography.source_plasma_pulse_energy"),
    (
        "plasma_pulse_repetition_rate",
        "physical.lithography.source_plasma_pulse_repetition_rate",
    ),
    (
        "plasma_drive_pulse_duty_factor",
        "physical.lithography.source_plasma_drive_pulse_duty_factor",
    ),
    (
        "plasma_drive_pulse_fluence",
        "physical.lithography.source_plasma_drive_pulse_fluence",
    ),
    (
        "plasma_drive_peak_intensity",
        "physical.lithography.source_plasma_drive_peak_intensity",
    ),
    (
        "plasma_drive_pulse_duration",
        "physical.lithography.source_plasma_drive_pulse_duration",
    ),
    (
        "plasma_drive_pulse_rise_fraction",
        "physical.lithography.source_plasma_drive_pulse_rise_fraction",
    ),
    (
        "plasma_drive_pulse_fall_fraction",
        "physical.lithography.source_plasma_drive_pulse_fall_fraction",
    ),
    (
        "plasma_drive_pulse_flat_fraction",
        "physical.lithography.source_plasma_drive_pulse_flat_fraction",
    ),
    (
        "plasma_drive_pulse_temporal_shape_factor",
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor",
    ),
    (
        "plasma_drive_beam_wavelength",
        "physical.lithography.source_plasma_drive_beam_wavelength",
    ),
    (
        "plasma_drive_edge_detuning_ratio",
        "physical.lithography.source_plasma_drive_edge_detuning_ratio",
    ),
    (
        "plasma_drive_objective_pupil_radius",
        "physical.lithography.source_plasma_drive_objective_pupil_radius",
    ),
    (
        "plasma_drive_objective_focal_length",
        "physical.lithography.source_plasma_drive_objective_focal_length",
    ),
    (
        "plasma_drive_pupil_beam_fill_factor",
        "physical.lithography.source_plasma_drive_pupil_beam_fill_factor",
    ),
    (
        "plasma_drive_acceptance_half_angle",
        "physical.lithography.source_plasma_drive_acceptance_half_angle",
    ),
    (
        "plasma_drive_numerical_aperture",
        "physical.lithography.source_plasma_drive_numerical_aperture",
    ),
    (
        "plasma_drive_focus_f_number",
        "physical.lithography.source_plasma_drive_focus_f_number",
    ),
    (
        "plasma_drive_beam_parameter_waist_radius",
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius",
    ),
    (
        "plasma_drive_far_field_divergence_half_angle",
        "physical.lithography.source_plasma_drive_far_field_divergence_half_angle",
    ),
    (
        "plasma_drive_beam_parameter_product",
        "physical.lithography.source_plasma_drive_beam_parameter_product",
    ),
    (
        "plasma_drive_beam_quality_factor",
        "physical.lithography.source_plasma_drive_beam_quality_factor",
    ),
    (
        "plasma_drive_focus_waist_coefficient",
        "physical.lithography.source_plasma_drive_focus_waist_coefficient",
    ),
    (
        "plasma_drive_spot_radius",
        "physical.lithography.source_plasma_drive_spot_radius",
    ),
    (
        "plasma_drive_rayleigh_range",
        "physical.lithography.source_plasma_drive_rayleigh_range",
    ),
    (
        "plasma_drive_confocal_length",
        "physical.lithography.source_plasma_drive_confocal_length",
    ),
    (
        "plasma_drive_spot_axis_ratio",
        "physical.lithography.source_plasma_drive_spot_axis_ratio",
    ),
    (
        "plasma_drive_spot_area_fill_factor",
        "physical.lithography.source_plasma_drive_spot_area_fill_factor",
    ),
    (
        "plasma_drive_spot_shape_factor",
        "physical.lithography.source_plasma_drive_spot_shape_factor",
    ),
    ("plasma_drive_spot_area", "physical.lithography.source_plasma_drive_spot_area"),
    ("plasma_drive_power", "physical.lithography.source_plasma_drive_power"),
)

_PLASMA_COLUMN_VARIABLES = (
    (
        "plasma_species_partial_pressure",
        "physical.lithography.source_plasma_species_partial_pressure",
    ),
    (
        "plasma_species_gas_temperature",
        "physical.lithography.source_plasma_species_gas_temperature",
    ),
    (
        "plasma_species_number_density",
        "physical.lithography.source_plasma_species_number_density",
    ),
    (
        "plasma_column_expansion_speed_factor",
        "physical.lithography.source_plasma_column_expansion_speed_factor",
    ),
    (
        "plasma_column_radial_expansion_speed",
        "physical.lithography.source_plasma_column_radial_expansion_speed",
    ),
    (
        "plasma_column_radius_expansion_factor",
        "physical.lithography.source_plasma_column_radius_expansion_factor",
    ),
    ("plasma_column_radius", "physical.lithography.source_plasma_column_radius"),
    (
        "plasma_column_aspect_ratio",
        "physical.lithography.source_plasma_column_aspect_ratio",
    ),
    ("plasma_column_length", "physical.lithography.source_plasma_column_length"),
    (
        "plasma_active_fill_factor",
        "physical.lithography.source_plasma_active_fill_factor",
    ),
    ("plasma_active_volume", "physical.lithography.source_plasma_active_volume"),
)

_PLASMA_ABSORPTION_VARIABLES = (
    (
        "plasma_absorption_path_direction_cosine",
        "physical.lithography.source_plasma_absorption_path_direction_cosine",
    ),
    (
        "plasma_absorption_path_shape_factor",
        "physical.lithography.source_plasma_absorption_path_shape_factor",
    ),
    (
        "plasma_absorption_path_length",
        "physical.lithography.source_plasma_absorption_path_length",
    ),
    (
        "plasma_drive_beam_angular_frequency",
        "physical.lithography.source_plasma_drive_beam_angular_frequency",
    ),
    (
        "plasma_absorption_resonance_to_drive_ratio",
        "physical.lithography.source_plasma_absorption_resonance_to_drive_ratio",
    ),
    (
        "plasma_absorption_quality_factor",
        "physical.lithography.source_plasma_absorption_quality_factor",
    ),
    (
        "plasma_absorption_collision_cross_section",
        "physical.lithography.source_plasma_absorption_collision_cross_section",
    ),
    (
        "plasma_absorption_collision_orbital_radius",
        "physical.lithography.source_plasma_absorption_collision_orbital_radius",
    ),
    (
        "plasma_absorption_participating_electron_fraction",
        "physical.lithography.source_plasma_absorption_participating_electron_fraction",
    ),
    (
        "plasma_absorption_sum_rule_fraction",
        "physical.lithography.source_plasma_absorption_sum_rule_fraction",
    ),
    (
        "plasma_absorption_resonance",
        "physical.lithography.source_plasma_absorption_resonance_angular_frequency",
    ),
    (
        "plasma_absorption_damping_rate",
        "physical.lithography.source_plasma_absorption_damping_rate",
    ),
    (
        "plasma_absorption_oscillator_strength",
        "physical.lithography.source_plasma_absorption_oscillator_strength",
    ),
    (
        "plasma_absorption_cross_section",
        "physical.lithography.source_plasma_absorption_cross_section",
    ),
    (
        "plasma_absorption_optical_depth",
        "physical.lithography.source_plasma_absorption_optical_depth",
    ),
    (
        "plasma_drive_energy_absorption_fraction",
        "physical.lithography.source_plasma_drive_energy_absorption_fraction",
    ),
    (
        "plasma_drive_centroid_offset_to_column_radius_ratio",
        "physical.lithography.source_plasma_drive_centroid_offset_to_column_radius_ratio",
    ),
    (
        "plasma_drive_pointing_overlap_factor",
        "physical.lithography.source_plasma_drive_pointing_overlap_factor",
    ),
    (
        "plasma_drive_transverse_overlap_factor",
        "physical.lithography.source_plasma_drive_transverse_overlap_factor",
    ),
    (
        "plasma_drive_spatial_overlap_factor",
        "physical.lithography.source_plasma_drive_spatial_overlap_factor",
    ),
    (
        "plasma_active_lifetime_to_drive_pulse_ratio",
        "physical.lithography.source_plasma_active_lifetime_to_drive_pulse_ratio",
    ),
    (
        "plasma_active_response_duration",
        "physical.lithography.source_plasma_active_response_duration",
    ),
    (
        "plasma_drive_timing_offset_fraction",
        "physical.lithography.source_plasma_drive_timing_offset_fraction",
    ),
    (
        "plasma_drive_timing_offset_duration",
        "physical.lithography.source_plasma_drive_timing_offset_duration",
    ),
    (
        "plasma_drive_temporal_duration_match_factor",
        "physical.lithography.source_plasma_drive_temporal_duration_match_factor",
    ),
    (
        "plasma_drive_temporal_alignment_factor",
        "physical.lithography.source_plasma_drive_temporal_alignment_factor",
    ),
    (
        "plasma_drive_temporal_overlap_factor",
        "physical.lithography.source_plasma_drive_temporal_overlap_factor",
    ),
    (
        "plasma_drive_overlap_factor",
        "physical.lithography.source_plasma_drive_overlap_factor",
    ),
)

_PLASMA_ENERGY_VARIABLES = (
    (
        "plasma_electron_heating_fraction",
        "physical.lithography.source_plasma_electron_heating_fraction",
    ),
    (
        "plasma_absorption_efficiency",
        "physical.lithography.source_plasma_absorption_efficiency",
    ),
    ("plasma_absorbed_power", "physical.lithography.source_plasma_absorbed_power"),
    (
        "plasma_energy_loss_path_direction_cosine",
        "physical.lithography.source_plasma_energy_loss_path_direction_cosine",
    ),
    (
        "plasma_energy_loss_path_factor",
        "physical.lithography.source_plasma_energy_loss_path_factor",
    ),
    (
        "plasma_energy_loss_path_length",
        "physical.lithography.source_plasma_energy_loss_path_length",
    ),
    (
        "plasma_species_particle_mass",
        "physical.lithography.source_plasma_species_particle_mass",
    ),
    (
        "plasma_energy_loss_transport_speed_factor",
        "physical.lithography.source_plasma_energy_loss_transport_speed_factor",
    ),
    (
        "plasma_species_thermal_speed",
        "physical.lithography.source_plasma_species_thermal_speed",
    ),
    ("plasma_energy_loss_speed", "physical.lithography.source_plasma_energy_loss_speed"),
    (
        "plasma_confinement_time",
        "physical.lithography.source_plasma_energy_confinement_time",
    ),
    (
        "plasma_free_electron_inventory_charge_fraction",
        "physical.lithography.source_plasma_free_electron_inventory_charge_fraction",
    ),
    (
        "plasma_free_electron_yield",
        "physical.lithography.source_plasma_free_electron_yield_per_source_particle",
    ),
    (
        "plasma_free_electron_count",
        "physical.lithography.source_plasma_free_electron_count",
    ),
    (
        "plasma_internal_energy",
        "physical.lithography.source_plasma_electron_internal_energy",
    ),
    (
        "plasma_temperature",
        "physical.lithography.source_plasma_electron_temperature",
    ),
    ("plasma_density", "physical.lithography.source_plasma_electron_number_density"),
    (
        "plasma_mean_energy",
        "physical.lithography.source_plasma_electron_mean_kinetic_energy",
    ),
    ("plasma_debye_length", "physical.lithography.source_plasma_debye_length"),
)

_ELECTRONIC_VARIABLES = (
    ("ionization_energy", "physical.lithography.source_ionization_energy"),
    (
        "ionization_principal",
        "physical.lithography.source_ionization_principal_quantum_number",
    ),
    (
        "ionization_screening",
        "physical.lithography.source_ionization_screening_constant",
    ),
    (
        "ionization_inner_screeners",
        "physical.lithography.source_ionization_inner_shell_screening_electron_count",
    ),
    (
        "ionization_same_screeners",
        "physical.lithography.source_ionization_same_shell_screening_electron_count",
    ),
    (
        "ionization_z_eff",
        "physical.lithography.source_ionization_effective_nuclear_charge",
    ),
    ("partition_ratio", "physical.lithography.source_ionization_partition_ratio"),
    (
        "saha_thermal_density",
        "physical.lithography.source_saha_thermal_number_density",
    ),
    ("saha_ratio", "physical.lithography.source_saha_ionization_ratio"),
    ("saha_fraction", "physical.lithography.source_saha_ionization_fraction"),
    ("ion_charge_state", "physical.lithography.source_ion_charge_state"),
    ("bound_electrons", "physical.lithography.source_bound_electron_count"),
    ("lower_principal", "physical.lithography.source_lower_principal_quantum_number"),
    ("upper_principal", "physical.lithography.source_upper_principal_quantum_number"),
    (
        "transition_step",
        "physical.lithography.source_transition_principal_quantum_step",
    ),
    ("shell_capacity", "physical.lithography.source_transition_shell_capacity"),
    (
        "inner_closed_capacity",
        "physical.lithography.source_inner_closed_shell_capacity",
    ),
    (
        "inner_closed_shells",
        "physical.lithography.source_inner_closed_shell_electron_count",
    ),
    ("outer_shells", "physical.lithography.source_outer_shell_electron_count"),
    (
        "transition_shell_occupancy",
        "physical.lithography.source_transition_shell_occupancy",
    ),
    (
        "inner_screeners",
        "physical.lithography.source_inner_shell_screening_electron_count",
    ),
    (
        "same_screeners",
        "physical.lithography.source_same_shell_screening_electron_count",
    ),
    ("inner_shielding", "physical.lithography.source_inner_shell_shielding_factor"),
    ("same_shielding", "physical.lithography.source_same_shell_shielding_factor"),
    ("screening", "physical.lithography.source_screening_constant"),
    ("z_eff", "physical.lithography.source_effective_nuclear_charge"),
    ("transition", "physical.lithography.source_transition_energy"),
)


def _registry_variable_namespace(*groups):
    variables = {}
    for group in groups:
        for name, variable_id in group:
            variables[name] = Registry.variables[variable_id]
    return variables


def source_quantum_model():
    variables = _registry_variable_namespace(
        _NUCLEAR_VARIABLES,
        _PLASMA_DRIVE_VARIABLES,
        _PLASMA_COLUMN_VARIABLES,
        _PLASMA_ABSORPTION_VARIABLES,
        _PLASMA_ENERGY_VARIABLES,
        _ELECTRONIC_VARIABLES,
    )
    return SimpleNamespace(**variables)
