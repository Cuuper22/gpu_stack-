"""
scopes/physical_lithography_plasma_state.py
===========================================

Compatibility shim for the complete source-plasma operating state. The
implementation is split into drive (pulse, energy, column), focus, overlap,
absorption, and electron-state helper modules; this module re-exports the
whole closure in registry order and preserves the historical public surface
that the electronic-structure source layer imports. Read the sibling
modules for the physics; read this one to see the assembly order.
"""

from ..core import Approximation
from .physical_lithography_plasma_drive import *
from .physical_lithography_plasma_drive import (
    LITHOGRAPHY_SOURCE_PLASMA_DRIVE_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_DRIVE_VARIABLES,
)
from .physical_lithography_plasma_species import (
    LITHOGRAPHY_SOURCE_PLASMA_SPECIES_TRANSPORT_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_STATE_REF,
    ineq_lithography_source_plasma_species_thermal_speed_positive,
    ineq_lithography_source_plasma_species_thermal_speed_subluminal,
)
from .physical_lithography_plasma_absorption import *
from .physical_lithography_plasma_absorption import (
    LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_VARIABLES,
    LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PRE_OVERLAP_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PRE_OVERLAP_VARIABLES,
)
from .physical_lithography_plasma_overlap import *
from .physical_lithography_plasma_overlap import (
    LITHOGRAPHY_SOURCE_PLASMA_OVERLAP_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_OVERLAP_VARIABLES,
)
from .physical_lithography_plasma_electron_state import *
from .physical_lithography_plasma_electron_state import (
    LITHOGRAPHY_SOURCE_PLASMA_ELECTRON_STATE_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_ELECTRON_STATE_VARIABLES,
)


eq_lithography_source_plasma_active_lifetime_to_drive_pulse_ratio_from_energy_confinement_time = Approximation(
    "physical.eq.lithography_source_plasma_active_lifetime_to_drive_pulse_ratio_from_energy_confinement_time",
    lithography_source_plasma_active_lifetime_to_drive_pulse_ratio.symbol,
    (
        lithography_source_plasma_energy_confinement_time.symbol
        / lithography_source_plasma_drive_pulse_duration.symbol
    ),
    (
        (lithography_source_plasma_energy_confinement_time.symbol > 0)
        & (lithography_source_plasma_drive_pulse_duration.symbol > 0)
    ),
    "Active plasma lifetime-to-drive-pulse ratio from energy confinement time normalized by drive pulse duration.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)


def _equation_index_after(equations, equation_name):
    for index, equation in enumerate(equations):
        if equation.name == equation_name:
            return index + 1
    raise RuntimeError(f"Missing source-plasma equation splice anchor: {equation_name}")


_SPECIES_TRANSPORT_INSERT_INDEX = _equation_index_after(
    LITHOGRAPHY_SOURCE_PLASMA_DRIVE_EQUATIONS,
    "physical.ineq.lithography_source_plasma_species_number_density_positive",
)
_OVERLAP_ELECTRON_INSERT_INDEX = _equation_index_after(
    LITHOGRAPHY_SOURCE_PLASMA_OVERLAP_EQUATIONS,
    "physical.eq.lithography_source_plasma_drive_spatial_overlap_factor_from_geometry",
)


LITHOGRAPHY_SOURCE_PLASMA_STATE_VARIABLES = [
    *LITHOGRAPHY_SOURCE_PLASMA_DRIVE_VARIABLES,
    *LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PRE_OVERLAP_VARIABLES,
    *LITHOGRAPHY_SOURCE_PLASMA_OVERLAP_VARIABLES,
    *LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_POST_OVERLAP_VARIABLES,
    *LITHOGRAPHY_SOURCE_PLASMA_ELECTRON_STATE_VARIABLES,
]

LITHOGRAPHY_SOURCE_PLASMA_STATE_EQUATIONS = [
    *LITHOGRAPHY_SOURCE_PLASMA_DRIVE_EQUATIONS[:_SPECIES_TRANSPORT_INSERT_INDEX],
    *LITHOGRAPHY_SOURCE_PLASMA_SPECIES_TRANSPORT_EQUATIONS,
    *LITHOGRAPHY_SOURCE_PLASMA_DRIVE_EQUATIONS[_SPECIES_TRANSPORT_INSERT_INDEX:],
    *LITHOGRAPHY_SOURCE_PLASMA_ABSORPTION_PRE_OVERLAP_EQUATIONS,
    *LITHOGRAPHY_SOURCE_PLASMA_OVERLAP_EQUATIONS[:_OVERLAP_ELECTRON_INSERT_INDEX],
    eq_lithography_source_plasma_energy_loss_path_direction_cosine_from_acceptance_angle,
    eq_lithography_source_plasma_energy_loss_path_factor_from_direction_cosine,
    eq_lithography_source_plasma_energy_loss_path_length_from_radius,
    eq_lithography_source_plasma_energy_loss_transport_speed_factor_from_mass_ratio,
    eq_lithography_source_plasma_energy_loss_speed_from_species_thermal_speed,
    eq_lithography_source_plasma_energy_confinement_time_from_loss_path,
    eq_lithography_source_plasma_active_lifetime_to_drive_pulse_ratio_from_energy_confinement_time,
    *LITHOGRAPHY_SOURCE_PLASMA_OVERLAP_EQUATIONS[_OVERLAP_ELECTRON_INSERT_INDEX:],
    ineq_lithography_source_plasma_electron_heating_fraction_within_unit_interval,
    eq_lithography_source_plasma_absorption_efficiency_from_overlap_optical_depth_heating,
    ineq_lithography_source_plasma_free_electron_inventory_charge_fraction_within_unit_interval,
    eq_lithography_source_plasma_free_electron_yield_per_source_particle_from_inventory_charge_fraction,
    eq_lithography_source_plasma_free_electron_count_from_species_inventory,
    eq_lithography_source_plasma_absorbed_power_from_drive,
    eq_lithography_source_plasma_electron_internal_energy_from_confinement,
    eq_lithography_source_plasma_electron_temperature_from_internal_energy,
    eq_lithography_source_plasma_electron_number_density_from_count_volume,
    eq_lithography_source_plasma_electron_mean_kinetic_energy_from_temperature,
    eq_lithography_source_plasma_debye_length_from_temperature_density,
]


__all__ = [
    "LITHOGRAPHY_SOURCE_PLASMA_STATE_REF",
    "lithography_source_plasma_pulse_period",
    "lithography_source_plasma_pulse_repetition_rate",
    "lithography_source_plasma_drive_pulse_duty_factor",
    "lithography_source_plasma_drive_pulse_fluence",
    "lithography_source_plasma_drive_peak_intensity",
    "lithography_source_plasma_drive_pulse_duration",
    "lithography_source_plasma_drive_pulse_rise_fraction",
    "lithography_source_plasma_drive_pulse_fall_fraction",
    "lithography_source_plasma_drive_pulse_flat_fraction",
    "lithography_source_plasma_drive_pulse_temporal_shape_factor",
    "lithography_source_plasma_drive_beam_wavelength",
    "lithography_source_plasma_drive_edge_detuning_ratio",
    "lithography_source_plasma_drive_objective_pupil_radius",
    "lithography_source_plasma_drive_objective_focal_length",
    "lithography_source_plasma_drive_pupil_beam_fill_factor",
    "lithography_source_plasma_drive_acceptance_half_angle",
    "lithography_source_plasma_drive_numerical_aperture",
    "lithography_source_plasma_drive_focus_f_number",
    "lithography_source_plasma_drive_beam_parameter_waist_radius",
    "lithography_source_plasma_drive_far_field_divergence_half_angle",
    "lithography_source_plasma_drive_beam_parameter_product",
    "lithography_source_plasma_drive_beam_quality_factor",
    "lithography_source_plasma_drive_focus_waist_coefficient",
    "lithography_source_plasma_drive_spot_radius",
    "lithography_source_plasma_drive_rayleigh_range",
    "lithography_source_plasma_drive_confocal_length",
    "lithography_source_plasma_drive_spot_axis_ratio",
    "lithography_source_plasma_drive_spot_area_fill_factor",
    "lithography_source_plasma_drive_spot_shape_factor",
    "lithography_source_plasma_drive_spot_area",
    "lithography_source_plasma_pulse_energy",
    "lithography_source_plasma_drive_power",
    "lithography_source_plasma_species_partial_pressure",
    "lithography_source_plasma_species_gas_temperature",
    "lithography_source_plasma_species_number_density",
    "lithography_source_plasma_column_expansion_speed_factor",
    "lithography_source_plasma_column_radial_expansion_speed",
    "lithography_source_plasma_column_radius_expansion_factor",
    "lithography_source_plasma_column_radius",
    "lithography_source_plasma_column_aspect_ratio",
    "lithography_source_plasma_column_length",
    "lithography_source_plasma_active_fill_factor",
    "lithography_source_plasma_active_volume",
    "lithography_source_plasma_absorption_path_direction_cosine",
    "lithography_source_plasma_absorption_path_shape_factor",
    "lithography_source_plasma_absorption_path_length",
    "lithography_source_plasma_drive_beam_angular_frequency",
    "lithography_source_plasma_absorption_resonance_to_drive_ratio",
    "lithography_source_plasma_absorption_quality_factor",
    "lithography_source_plasma_absorption_collision_cross_section",
    "lithography_source_plasma_absorption_participating_electron_fraction",
    "lithography_source_plasma_absorption_sum_rule_fraction",
    "lithography_source_plasma_absorption_resonance_angular_frequency",
    "lithography_source_plasma_absorption_damping_rate",
    "lithography_source_plasma_absorption_oscillator_strength",
    "lithography_source_plasma_absorption_cross_section",
    "lithography_source_plasma_absorption_optical_depth",
    "lithography_source_plasma_drive_energy_absorption_fraction",
    "lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio",
    "lithography_source_plasma_drive_pointing_overlap_factor",
    "lithography_source_plasma_drive_transverse_overlap_factor",
    "lithography_source_plasma_drive_spatial_overlap_factor",
    "lithography_source_plasma_active_lifetime_to_drive_pulse_ratio",
    "lithography_source_plasma_active_response_duration",
    "lithography_source_plasma_drive_timing_offset_fraction",
    "lithography_source_plasma_drive_timing_offset_duration",
    "lithography_source_plasma_drive_temporal_duration_match_factor",
    "lithography_source_plasma_drive_temporal_alignment_factor",
    "lithography_source_plasma_drive_temporal_overlap_factor",
    "lithography_source_plasma_drive_overlap_factor",
    "lithography_source_plasma_electron_heating_fraction",
    "lithography_source_plasma_absorption_efficiency",
    "lithography_source_plasma_absorbed_power",
    "lithography_source_plasma_energy_loss_path_direction_cosine",
    "lithography_source_plasma_energy_loss_path_factor",
    "lithography_source_plasma_energy_loss_path_length",
    "lithography_source_plasma_species_particle_mass",
    "lithography_source_plasma_energy_loss_transport_speed_factor",
    "lithography_source_plasma_species_thermal_speed",
    "lithography_source_plasma_energy_loss_speed",
    "lithography_source_plasma_energy_confinement_time",
    "lithography_source_plasma_free_electron_inventory_charge_fraction",
    "lithography_source_plasma_free_electron_yield_per_source_particle",
    "lithography_source_plasma_free_electron_count",
    "lithography_source_plasma_electron_internal_energy",
    "lithography_source_plasma_electron_mean_kinetic_energy",
    "lithography_source_plasma_debye_length",
    "lithography_source_plasma_electron_temperature",
    "lithography_source_plasma_electron_number_density",
    "eq_lithography_source_plasma_pulse_repetition_rate_from_period",
    "eq_lithography_source_plasma_drive_pulse_duration_from_duty_cycle",
    "ineq_lithography_source_plasma_drive_pulse_duty_factor_within_unit_interval",
    "eq_lithography_source_plasma_drive_pulse_fall_fraction_from_symmetric_ramp",
    "eq_lithography_source_plasma_drive_pulse_flat_fraction_from_ramps",
    "eq_lithography_source_plasma_drive_pulse_temporal_shape_factor_from_trapezoid",
    "ineq_lithography_source_plasma_drive_pulse_ramp_fractions_within_pulse",
    "ineq_lithography_source_plasma_drive_pulse_duration_fractions_within_pulse",
    "ineq_lithography_source_plasma_drive_pulse_temporal_shape_factor_within_unit_interval",
    "eq_lithography_source_plasma_drive_peak_intensity_from_fluence",
    "ineq_lithography_source_plasma_drive_peak_intensity_at_least_pulse_average_intensity",
    "eq_lithography_source_plasma_drive_focus_waist_coefficient_from_gaussian_f_number",
    "eq_lithography_source_plasma_drive_acceptance_half_angle_from_pupil_geometry",
    "eq_lithography_source_plasma_drive_numerical_aperture_from_acceptance_angle",
    "eq_lithography_source_plasma_drive_focus_f_number_from_acceptance_angle",
    "ineq_lithography_source_plasma_drive_acceptance_half_angle_within_forward_half_space",
    "ineq_lithography_source_plasma_drive_edge_detuning_ratio_below_ionization_edge",
    "ineq_lithography_source_plasma_drive_far_field_divergence_half_angle_within_forward_half_space",
    "ineq_lithography_source_plasma_drive_far_field_divergence_within_acceptance",
    "ineq_lithography_source_plasma_drive_pupil_beam_fill_factor_within_unit_interval",
    "eq_lithography_source_plasma_drive_beam_parameter_waist_radius_from_pupil_fill",
    "eq_lithography_source_plasma_drive_beam_parameter_product_from_waist_divergence",
    "ineq_lithography_source_plasma_drive_beam_parameter_product_diffraction_floor",
    "eq_lithography_source_plasma_drive_beam_quality_factor_from_beam_parameter_product",
    "ineq_lithography_source_plasma_drive_beam_quality_factor_diffraction_limit",
    "eq_lithography_source_plasma_drive_spot_radius_from_focus",
    "eq_lithography_source_plasma_drive_rayleigh_range_from_spot_geometry",
    "eq_lithography_source_plasma_drive_confocal_length_from_rayleigh_range",
    "eq_lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention",
    "eq_lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention",
    "eq_lithography_source_plasma_drive_spot_shape_factor_from_ellipse",
    "eq_lithography_source_plasma_drive_spot_area_from_radius",
    "eq_lithography_source_plasma_pulse_energy_from_intensity_area_duration",
    "ineq_lithography_source_plasma_pulse_duration_within_period",
    "eq_lithography_source_plasma_drive_power_from_pulses",
    "ineq_lithography_source_plasma_species_partial_pressure_positive",
    "ineq_lithography_source_plasma_species_gas_temperature_positive",
    "eq_lithography_source_plasma_species_number_density_from_ideal_gas",
    "ineq_lithography_source_plasma_species_number_density_positive",
    "eq_lithography_source_plasma_column_expansion_speed_factor_from_monatomic_sound_speed",
    "eq_lithography_source_plasma_column_radial_expansion_speed_from_species_thermal_speed",
    "eq_lithography_source_plasma_column_radius_expansion_factor_from_radial_speed",
    "eq_lithography_source_plasma_column_radius_from_drive_spot",
    "eq_lithography_source_plasma_column_aspect_ratio_from_confocal_length",
    "eq_lithography_source_plasma_column_length_from_aspect_ratio",
    "eq_lithography_source_plasma_active_fill_factor_from_ideal_column_convention",
    "eq_lithography_source_plasma_active_volume_from_column_geometry",
    "eq_lithography_source_plasma_drive_beam_angular_frequency",
    "eq_lithography_source_plasma_absorption_path_direction_cosine_from_acceptance_angle",
    "eq_lithography_source_plasma_absorption_path_shape_factor_from_direction_cosine",
    "eq_lithography_source_plasma_absorption_path_length_from_column",
    "eq_lithography_source_plasma_absorption_resonance_from_drive_ratio",
    "eq_lithography_source_plasma_absorption_damping_rate_from_species_collision",
    "eq_lithography_source_plasma_absorption_quality_factor_from_collision_damping",
    "eq_lithography_source_plasma_absorption_oscillator_strength_from_source_charge",
    "eq_lithography_source_plasma_absorption_cross_section_from_lorentz_oscillator",
    "eq_lithography_source_plasma_absorption_optical_depth",
    "eq_lithography_source_plasma_drive_energy_absorption_fraction_from_optical_depth",
    "eq_lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio_from_coaxial_convention",
    "eq_lithography_source_plasma_drive_pointing_overlap_factor_from_offset",
    "eq_lithography_source_plasma_drive_transverse_overlap_factor_from_area_ratio",
    "ineq_lithography_source_plasma_drive_spot_area_within_column_cross_section",
    "eq_lithography_source_plasma_drive_spatial_overlap_factor_from_geometry",
    "eq_lithography_source_plasma_active_response_duration_from_drive_ratio",
    "eq_lithography_source_plasma_drive_timing_offset_fraction_from_synchronized_convention",
    "eq_lithography_source_plasma_drive_timing_offset_duration_from_fraction",
    "eq_lithography_source_plasma_drive_temporal_duration_match_factor",
    "eq_lithography_source_plasma_drive_temporal_alignment_factor_from_timing_offset",
    "eq_lithography_source_plasma_drive_temporal_overlap_factor_from_duration_and_alignment",
    "eq_lithography_source_plasma_drive_overlap_factor_from_spatial_temporal",
    "ineq_lithography_source_plasma_electron_heating_fraction_within_unit_interval",
    "eq_lithography_source_plasma_absorption_efficiency_from_overlap_optical_depth_heating",
    "eq_lithography_source_plasma_energy_loss_path_direction_cosine_from_acceptance_angle",
    "eq_lithography_source_plasma_energy_loss_path_factor_from_direction_cosine",
    "eq_lithography_source_plasma_energy_loss_path_length_from_radius",
    "eq_lithography_source_plasma_species_particle_mass_from_nuclear_counts",
    "eq_lithography_source_plasma_species_thermal_speed_from_gas_temperature",
    "ineq_lithography_source_plasma_species_thermal_speed_positive",
    "ineq_lithography_source_plasma_species_thermal_speed_subluminal",
    "eq_lithography_source_plasma_energy_loss_transport_speed_factor_from_mass_ratio",
    "eq_lithography_source_plasma_energy_loss_speed_from_species_thermal_speed",
    "eq_lithography_source_plasma_energy_confinement_time_from_loss_path",
    "eq_lithography_source_plasma_active_lifetime_to_drive_pulse_ratio_from_energy_confinement_time",
    "ineq_lithography_source_plasma_free_electron_inventory_charge_fraction_within_unit_interval",
    "eq_lithography_source_plasma_free_electron_yield_per_source_particle_from_inventory_charge_fraction",
    "eq_lithography_source_plasma_free_electron_count_from_species_inventory",
    "eq_lithography_source_plasma_absorbed_power_from_drive",
    "eq_lithography_source_plasma_electron_internal_energy_from_confinement",
    "eq_lithography_source_plasma_electron_temperature_from_internal_energy",
    "eq_lithography_source_plasma_electron_number_density_from_count_volume",
    "eq_lithography_source_plasma_electron_mean_kinetic_energy_from_temperature",
    "eq_lithography_source_plasma_debye_length_from_temperature_density",
    "LITHOGRAPHY_SOURCE_PLASMA_STATE_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_STATE_EQUATIONS",
]
