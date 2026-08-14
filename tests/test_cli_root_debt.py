"""Tests for the ``root-debt`` CLI command.

"Root debt" is the count of unassigned root inputs, ranked by how many
derived variables depend on each one — assigning the top-ranked roots pays
down the most uncertainty per value. The big test here pins, name by name,
which lithography variables are roots (they appear in the ranking) and
which are derived (they must not). That split is the model's real structure:
if a refactor turns a derived quantity back into a root, or vice versa,
this test names the exact variable that moved. The others cover the scope
filter and the ``--include-constraints`` toggle.
"""

from gpu_stack.cli import main
from tests.helpers.cli import captured_stdout


def test_root_debt_ranks_central_roots():
    with captured_stdout() as buf:
        rc = main(["root-debt", "--limit", "1000"])
    out = buf.getvalue()
    assert rc == 0
    assert "Root-debt ranking:" in out
    assert "include_constraints False" in out
    assert "dependents" in out
    ranked_variables = {
        parts[2]
        for line in out.splitlines()
        if (parts := line.split()) and parts[0].isdigit() and len(parts) >= 3
    }
    assert "physical.lithography.source_proton_count" in ranked_variables
    assert "physical.lithography.source_neutron_count" in ranked_variables
    assert "physical.lithography.medium_component_a_proton_count" in ranked_variables
    assert "physical.lithography.medium_component_b_proton_count" in ranked_variables
    assert "physical.lithography.nuclear_binding_coulomb_coefficient" in ranked_variables
    assert "physical.lithography.nuclear_binding_volume_coefficient" in ranked_variables
    assert "physical.lithography.nuclear_binding_surface_coefficient" in ranked_variables
    assert "physical.lithography.nuclear_binding_asymmetry_coefficient" in ranked_variables
    assert "physical.lithography.nuclear_pairing_gap_reference_energy" in ranked_variables
    assert "physical.lithography.gate_k1_aerial_image_contrast_factor" in ranked_variables
    assert "physical.lithography.gate_k1_resist_process_factor" in ranked_variables
    assert "physical.lithography.gate_k1_mask_error_factor" in ranked_variables
    assert "physical.lithography.gate_k1_resolution_enhancement_factor" in ranked_variables
    assert "physical.lithography.gate_k1" not in ranked_variables
    assert "physical.lithography.source_valence_up_quark_count" not in ranked_variables
    assert "physical.lithography.source_valence_down_quark_count" not in ranked_variables
    assert "physical.lithography.medium_component_binding_coulomb_coefficient" not in ranked_variables
    assert "physical.lithography.medium_component_binding_volume_coefficient" not in ranked_variables
    assert "physical.lithography.medium_component_binding_surface_coefficient" not in ranked_variables
    assert "physical.lithography.medium_component_binding_asymmetry_coefficient" not in ranked_variables
    assert "physical.lithography.source_binding_coulomb_coefficient" not in ranked_variables
    assert "physical.lithography.source_binding_volume_coefficient" not in ranked_variables
    assert "physical.lithography.source_binding_surface_coefficient" not in ranked_variables
    assert "physical.lithography.source_binding_asymmetry_coefficient" not in ranked_variables
    assert "physical.lithography.source_nuclear_saturation_number_density" not in ranked_variables
    assert "physical.lithography.source_transition_principal_quantum_step" not in ranked_variables
    assert "physical.lithography.source_plasma_pulse_period" in ranked_variables
    assert "physical.lithography.source_plasma_drive_pulse_duty_factor" in ranked_variables
    assert "physical.lithography.source_plasma_drive_pulse_fluence" in ranked_variables
    assert "physical.lithography.source_plasma_drive_pulse_rise_fraction" in ranked_variables
    assert "physical.lithography.source_plasma_drive_pulse_fall_fraction" not in ranked_variables
    assert (
        "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor"
        not in ranked_variables
    )
    assert "physical.lithography.source_plasma_drive_beam_wavelength" not in ranked_variables
    assert "physical.lithography.source_plasma_drive_edge_detuning_ratio" in ranked_variables
    assert "physical.lithography.source_plasma_drive_objective_pupil_radius" in ranked_variables
    assert "physical.lithography.source_plasma_drive_objective_focal_length" in ranked_variables
    assert "physical.lithography.source_plasma_drive_pupil_beam_fill_factor" in ranked_variables
    assert "physical.lithography.source_plasma_drive_acceptance_half_angle" not in ranked_variables
    assert "physical.lithography.source_plasma_drive_numerical_aperture" not in ranked_variables
    assert "physical.lithography.source_plasma_drive_focus_f_number" not in ranked_variables
    assert (
        "physical.lithography.source_plasma_drive_beam_parameter_waist_radius"
        not in ranked_variables
    )
    assert "physical.lithography.source_plasma_drive_far_field_divergence_half_angle" in ranked_variables
    assert "physical.lithography.source_plasma_drive_beam_parameter_product" not in ranked_variables
    assert "physical.lithography.source_plasma_drive_beam_quality_factor" not in ranked_variables
    assert (
        "physical.lithography.source_plasma_drive_focus_waist_coefficient"
        not in ranked_variables
    )
    assert "physical.lithography.source_plasma_drive_spot_axis_ratio" not in ranked_variables
    assert (
        "physical.lithography.source_plasma_drive_spot_area_fill_factor"
        not in ranked_variables
    )
    assert "physical.lithography.source_plasma_species_partial_pressure" in ranked_variables
    assert "physical.lithography.source_plasma_species_gas_temperature" in ranked_variables
    assert "physical.lithography.source_plasma_column_expansion_speed_factor" not in ranked_variables
    assert "physical.lithography.source_plasma_column_aspect_ratio" not in ranked_variables
    assert "physical.lithography.source_plasma_active_fill_factor" not in ranked_variables
    assert "physical.lithography.source_plasma_absorption_path_direction_cosine" not in ranked_variables
    assert "physical.lithography.source_plasma_absorption_resonance_to_drive_ratio" not in ranked_variables
    assert "physical.lithography.source_plasma_absorption_quality_factor" not in ranked_variables
    assert (
        "physical.lithography.source_plasma_absorption_collision_cross_section"
        not in ranked_variables
    )
    assert "physical.lithography.source_plasma_absorption_participating_electron_fraction" not in ranked_variables
    assert "physical.lithography.source_plasma_absorption_sum_rule_fraction" not in ranked_variables
    assert (
        "physical.lithography.source_plasma_drive_centroid_offset_to_column_radius_ratio"
        not in ranked_variables
    )
    assert "physical.lithography.source_plasma_active_lifetime_to_drive_pulse_ratio" not in ranked_variables
    assert "physical.lithography.source_plasma_drive_timing_offset_fraction" not in ranked_variables
    assert "physical.lithography.source_plasma_electron_heating_fraction" in ranked_variables
    assert "physical.lithography.source_plasma_energy_loss_path_direction_cosine" not in ranked_variables
    assert "physical.lithography.source_plasma_energy_loss_transport_speed_factor" not in ranked_variables
    assert "physical.lithography.source_plasma_free_electron_inventory_charge_fraction" in ranked_variables
    assert "physical.lithography.source_plasma_drive_spot_radius" not in ranked_variables
    assert "physical.lithography.source_plasma_drive_spot_shape_factor" not in ranked_variables
    assert "physical.lithography.source_plasma_drive_spot_area" not in ranked_variables
    assert "physical.lithography.source_plasma_pulse_energy" not in ranked_variables
    assert "physical.lithography.source_plasma_pulse_repetition_rate" not in ranked_variables
    assert "physical.lithography.source_plasma_drive_pulse_duration" not in ranked_variables
    assert "physical.lithography.source_plasma_drive_pulse_flat_fraction" not in ranked_variables
    assert "physical.lithography.source_plasma_drive_peak_intensity" not in ranked_variables
    assert "physical.lithography.source_plasma_absorption_path_shape_factor" not in ranked_variables
    assert "physical.lithography.source_plasma_drive_overlap_factor" not in ranked_variables
    assert (
        "physical.lithography.source_plasma_column_radius_expansion_factor"
        not in ranked_variables
    )
    assert (
        "physical.lithography.source_plasma_column_radial_expansion_speed"
        not in ranked_variables
    )
    assert "physical.lithography.source_plasma_column_radius" not in ranked_variables
    assert "physical.lithography.source_plasma_column_length" not in ranked_variables
    assert "physical.lithography.source_plasma_drive_beam_angular_frequency" not in ranked_variables
    assert "physical.lithography.source_plasma_absorption_resonance_angular_frequency" not in ranked_variables
    assert "physical.lithography.source_plasma_absorption_damping_rate" not in ranked_variables
    assert "physical.lithography.source_plasma_absorption_oscillator_strength" not in ranked_variables
    assert "physical.lithography.source_plasma_absorption_cross_section" not in ranked_variables
    assert "physical.lithography.source_plasma_drive_power" not in ranked_variables
    assert "physical.lithography.source_plasma_absorption_efficiency" not in ranked_variables
    assert "physical.lithography.source_plasma_energy_loss_path_factor" not in ranked_variables
    assert "physical.lithography.source_plasma_energy_loss_speed" not in ranked_variables
    assert "physical.lithography.source_plasma_energy_confinement_time" not in ranked_variables
    assert "physical.lithography.source_plasma_free_electron_yield_per_source_particle" not in ranked_variables
    assert "physical.lithography.source_plasma_free_electron_count" not in ranked_variables
    assert "physical.lithography.source_plasma_active_volume" not in ranked_variables
    assert "physical.lithography.source_plasma_absorbed_power" not in ranked_variables
    assert "physical.lithography.source_plasma_electron_internal_energy" not in ranked_variables
    assert "physical.lithography.source_plasma_electron_temperature" not in ranked_variables
    assert "physical.lithography.source_plasma_electron_number_density" not in ranked_variables
    assert "physical.lithography.medium_intercomponent_effective_separation" not in ranked_variables
    assert (
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count"
        in ranked_variables
    )
    assert "physical.lithography.medium_intercomponent_charge_unit" not in ranked_variables
    assert (
        "physical.lithography.medium_component_a_intercomponent_radius_scale_factor"
        in ranked_variables
    )
    assert (
        "physical.lithography.medium_component_b_intercomponent_radius_scale_factor"
        in ranked_variables
    )
    assert "physical.lithography.medium_intercomponent_gap_fraction" in ranked_variables
    assert (
        "physical.lithography.medium_component_a_effective_intercomponent_radius"
        not in ranked_variables
    )
    assert (
        "physical.lithography.medium_component_b_effective_intercomponent_radius"
        not in ranked_variables
    )
    assert "physical.lithography.medium_intercomponent_gap" not in ranked_variables
    assert "physical.lithography.medium_polarizable_electron_count" in ranked_variables
    assert "physical.lithography.medium_dominant_oscillator_electron_count" in ranked_variables
    assert "physical.lithography.medium_resonance_energy" in ranked_variables
    assert "physical.lithography.medium_polarizable_electron_fraction" not in ranked_variables
    assert "physical.lithography.medium_oscillator_sum_rule_fraction" not in ranked_variables
    assert "physical.lithography.medium_resonance_to_source_frequency_ratio" not in ranked_variables
    assert (
        "physical.lithography.medium_intercomponent_polarizable_site_density_factor"
        in ranked_variables
    )
    assert (
        "physical.lithography.medium_formula_unit_packing_length_scale_factor"
        in ranked_variables
    )
    assert (
        "physical.lithography.medium_formula_unit_packing_length"
        not in ranked_variables
    )
    assert (
        "physical.lithography.medium_formula_unit_packing_fill_factor"
        in ranked_variables
    )
    assert "physical.lithography.medium_mass_density" not in ranked_variables
    assert (
        "physical.lithography.medium_intercomponent_lorentz_lorenz_factor"
        not in ranked_variables
    )
    assert "physical.lithography.medium_intercomponent_relative_permittivity" not in ranked_variables


def test_root_debt_scope_filter():
    with captured_stdout() as buf:
        rc = main(["root-debt", "--scope", "gpu", "--limit", "3"])
    out = buf.getvalue()
    assert rc == 0
    assert "filtered_scope     gpu" in out
    assert "gpu.sm.tensor_core_area_per_unit" in out


def test_root_debt_can_include_constraint_edges():
    with captured_stdout() as buf:
        rc = main(["root-debt", "--scope", "thermal", "--limit", "5", "--include-constraints"])
    out = buf.getvalue()
    assert rc == 0
    assert "include_constraints True" in out
