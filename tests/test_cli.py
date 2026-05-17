"""
tests/test_cli.py
=================

CLI smoke tests. The CLI is a thin wrapper over the registry, the
resolver, and the preset library; these tests verify the wiring, not
the underlying math.
"""

import io
import json
import contextlib
from types import SimpleNamespace

import pytest
import sympy as sp

import gpu_stack.cli as cli_mod
from gpu_stack import Registry
from gpu_stack.cli import build_parser, main
from gpu_stack.core import Inequality, var
from tests.helpers.cli import (
    ORIGINAL_PYTHIA_SCENARIO,
    captured_stderr,
    captured_stdout,
    pythia_energy_floor_report,
    registry_snapshot,
    report_by_preset,
    target_by_label,
    unresolved_input_line,
)
from tests.test_import import PUBLISHED_SNAPSHOT





def test_parser_builds_without_args():
    parser = build_parser()
    assert parser.prog == "gpu-stack"


def test_stats_prints_registry_counts():
    with captured_stdout() as buf:
        rc = main(["stats"])
    out = buf.getvalue()
    assert rc == 0
    assert "variables" in out
    assert str(PUBLISHED_SNAPSHOT["variables"]) in out
    assert "Coverage" in out


def test_audit_reports_integrity_counts():
    with captured_stdout() as buf:
        rc = main(["audit", "--fail-on-issues"])
    out = buf.getvalue()
    assert rc == 0
    assert "Audit:" in out
    assert "collapsed_equations             0" in out
    assert "collapsed_approximation_validity 0" in out
    assert "unresolved_raw_symbols          0" in out
    assert "orphan_value_equations          0" in out
    assert "large_scope_files               0" in out
    assert "large_project_files" in out
    assert "hard_failures                   0" in out


def test_audit_large_project_files_scan_core_and_tests_after_cli_split():
    large_files = {
        name for name, _lines in cli_mod._large_project_files(threshold=700)
    }

    assert not any(name.startswith("gpu_stack/cli") for name in large_files)
    assert "gpu_stack/core/equation.py" not in large_files
    assert "tests/test_cli.py" in large_files
    assert not any(
        name.startswith("tests/test_process_geometry") for name in large_files
    )


def test_audit_details_lists_multi_definition_variables():
    with captured_stdout() as buf:
        rc = main(["audit", "--details"])
    out = buf.getvalue()
    assert rc == 0
    assert "multi_definition_variables" in out
    assert "training.flops_per_step" in out


def test_audit_fails_on_raw_symbol_in_expression_lhs_constraint():
    with registry_snapshot():
        owner = var(
            "test.cli.raw_lhs.owner",
            "test_cli_raw_lhs_owner",
            "value",
            "Temporary CLI raw-LHS owner.",
            scope="test",
        )
        raw = sp.Symbol("test_cli_raw_lhs_ghost")
        Inequality(
            "test.cli.ineq.raw_lhs",
            owner.symbol + raw,
            0,
            "<=",
            "Temporary CLI raw-LHS constraint.",
        )

        with captured_stdout() as buf:
            rc = main(["audit", "--details", "--fail-on-issues"])

    out = buf.getvalue()
    assert rc == 1
    assert "unresolved_raw_symbols          1" in out
    assert "test.cli.ineq.raw_lhs: test_cli_raw_lhs_ghost" in out


def test_audit_fails_on_collapsed_approximation_validity():
    with registry_snapshot():
        equation = Registry.equations[
            "physical.eq.lithography_source_nuclear_radius_coefficient"
        ]
        original_validity = equation.validity
        try:
            equation.validity = sp.S.true

            with captured_stdout() as buf:
                rc = main(["audit", "--details", "--fail-on-issues"])
        finally:
            equation.validity = original_validity

    out = buf.getvalue()
    assert rc == 1
    assert "collapsed_approximation_validity 1" in out
    assert "physical.eq.lithography_source_nuclear_radius_coefficient" in out


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
    assert "physical.lithography.source_valence_up_quark_count" in ranked_variables
    assert "physical.lithography.source_valence_down_quark_count" in ranked_variables
    assert "physical.lithography.medium_component_a_valence_up_quark_count" in ranked_variables
    assert "physical.lithography.medium_component_b_valence_up_quark_count" in ranked_variables
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
    assert "physical.lithography.source_proton_count" not in ranked_variables
    assert "physical.lithography.source_neutron_count" not in ranked_variables
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


def test_verify_fast_prints_compact_gate_summary(monkeypatch):
    calls = []

    def fake_run(gate, cwd, timeout_seconds):
        calls.append((gate.name, cwd, gate.command, timeout_seconds))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli_mod, "_run_verify_gate", fake_run)
    with captured_stdout() as buf:
        rc = main(["verify", "--profile", "fast"])
    out = buf.getvalue()
    assert rc == 0
    assert "Verify profile: fast" in out
    assert "OK   audit" in out
    assert "OK   core-tests" in out
    assert "Summary: 2/2 gates passed" in out
    assert [name for name, _, _, _ in calls] == ["audit", "core-tests"]
    assert [timeout for *_, timeout in calls] == [120.0, 120.0]
    core_command = calls[1][2]
    assert "tests/test_relation_roles.py" in core_command
    assert "tests/test_symbolic_integrity.py" in core_command
    assert "tests/test_resolver.py" in core_command
    assert (
        "tests/test_process_geometry.py::"
        "test_source_plasma_radial_expansion_uses_species_mass_chain"
    ) in core_command
    assert "Read-only mode: off" in out


def test_verify_read_only_uses_no_bytecode_and_no_pytest_cache(monkeypatch):
    calls = []

    def fake_run(gate, cwd, timeout_seconds):
        calls.append((gate.name, gate.command, gate.env))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli_mod, "_run_verify_gate", fake_run)
    with captured_stdout() as buf:
        rc = main(["verify", "--profile", "full", "--read-only"])
    out = buf.getvalue()

    assert rc == 0
    assert "Read-only mode: on" in out
    assert [name for name, _, _ in calls] == ["pytest", "syntax", "audit", "demo"]
    for _, command, env in calls:
        assert command[1] == "-B"
        assert env == {"PYTHONDONTWRITEBYTECODE": "1"}
    pytest_command = calls[0][1]
    assert "-p" in pytest_command
    assert "no:cacheprovider" in pytest_command
    assert "compileall" not in calls[1][1]
    assert "tokenize.open" in calls[1][1][-1]


def test_run_verify_gate_merges_gate_env(monkeypatch, tmp_path):
    captured = {}

    def fake_run(*args, **kwargs):
        captured["env"] = kwargs["env"]
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)
    result = cli_mod._run_verify_gate(
        cli_mod.VerifyGate(
            "readonly",
            ("python", "-B", "-c", "pass"),
            env={"PYTHONDONTWRITEBYTECODE": "1"},
        ),
        tmp_path,
        1.0,
    )
    assert result.returncode == 0
    assert captured["env"]["PYTHONDONTWRITEBYTECODE"] == "1"


def test_verify_failure_prints_limited_tail(monkeypatch):
    def fake_run(gate, cwd, timeout_seconds):
        return SimpleNamespace(
            returncode=7,
            stdout="old\nnew\n",
            stderr="problem\n",
        )

    monkeypatch.setattr(cli_mod, "_run_verify_gate", fake_run)
    with captured_stdout() as buf:
        rc = main(["verify", "--profile", "fast", "--tail-lines", "1"])
    out = buf.getvalue()
    assert rc == 7
    assert "FAIL audit" in out
    assert "stdout tail:" in out
    assert "new" in out
    assert "old" not in out
    assert "stderr tail:" in out


def test_verify_timeout_prints_timeout_status(monkeypatch):
    def fake_run(gate, cwd, timeout_seconds):
        return SimpleNamespace(
            returncode=cli_mod.VERIFY_TIMEOUT_RETURN_CODE,
            stdout="partial stdout\n",
            stderr=f"gate timed out after {timeout_seconds:g}s\n",
            timed_out=True,
        )

    monkeypatch.setattr(cli_mod, "_run_verify_gate", fake_run)
    with captured_stdout() as buf:
        rc = main(["verify", "--profile", "fast", "--gate-timeout", "3"])
    out = buf.getvalue()
    assert rc == cli_mod.VERIFY_TIMEOUT_RETURN_CODE
    assert "Gate timeout: 3s" in out
    assert "TIMEOUT audit" in out
    assert "gate timed out after 3s" in out
    assert "Summary: 0/2 gates passed" in out


def test_verify_gate_timeout_override_applies_to_all_gates(monkeypatch):
    seen = []

    def fake_run(gate, cwd, timeout_seconds):
        seen.append(timeout_seconds)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli_mod, "_run_verify_gate", fake_run)
    with captured_stdout():
        rc = main(["verify", "--profile", "fast", "--gate-timeout", "12"])
    assert rc == 0
    assert seen == [12.0, 12.0]


def test_verify_gate_timeout_zero_disables_timeout(monkeypatch):
    seen = []

    def fake_run(gate, cwd, timeout_seconds):
        seen.append(timeout_seconds)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli_mod, "_run_verify_gate", fake_run)
    with captured_stdout() as buf:
        rc = main(["verify", "--profile", "fast", "--gate-timeout", "0"])
    assert rc == 0
    assert seen == [None, None]
    assert "Gate timeout: unbounded" in buf.getvalue()


def test_run_verify_gate_converts_subprocess_timeout(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        assert kwargs["timeout"] == 0.5
        raise cli_mod.subprocess.TimeoutExpired(
            cmd=args[0],
            timeout=0.5,
            output=b"partial out\n",
            stderr=b"partial err\n",
        )

    monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)
    result = cli_mod._run_verify_gate(
        cli_mod.VerifyGate("slow", ("python", "-c", "pass")),
        tmp_path,
        0.5,
    )
    assert result.returncode == cli_mod.VERIFY_TIMEOUT_RETURN_CODE
    assert result.timed_out is True
    assert "partial out" in result.stdout
    assert "partial err" in result.stderr
    assert "gate timed out after 0.5s" in result.stderr


def test_list_presets_shows_representative_dynamic_inventory():
    with captured_stdout() as buf:
        rc = main(["list-presets"])
    out = buf.getvalue()
    assert rc == 0
    for preset_name in (
        "hardware.demo_rack",
        "hardware.dgx_h100_8gpu_node",
        "materials.medium_h2o_h1_o16_composition",
        "materials.source_tin_120",
        "lithography.euv_tin120_lpp_source_boundary_assumption",
        "workload.dense_variant_selector",
        "workload.pythia_70m_dense_training",
        "economics.us_2024_industrial_flat_power_tariff",
        "scenarios.dense_training_cost_fixture",
        "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
    ):
        assert preset_name in out


def test_scenario_report_sourced_pack_prints_compact_target_statuses():
    with captured_stdout() as buf:
        rc = main([
            "scenario-report",
            "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "Scenario report: pythia_70m_dgx_h100_us_2024_industrial_power" in out
    assert "tokens_per_second: ok target=training.tokens_per_sec" in out
    assert "value=1268976.30961386" in out
    assert "job_dc_power: ok target=econ.job.dc_power value=10200.0000000000" in out
    assert "run_power_cost: ok target=econ.run.power_cost" in out
    assert "missing=0" in out
    assert "violated_constraints=0" in out


def test_next_work_text_prints_live_compass_sections():
    with captured_stdout() as buf:
        rc = main(["next-work"])

    out = buf.getvalue()
    assert rc == 0
    assert "Next work:" in out
    assert "graph evidence: variables=1517 equations=959 root_inputs=619" in out
    assert "Top 3 highest impact:" in out
    assert "4 best implementations:" in out
    assert "10 bugs/risks:" in out
    assert "Close the sourced Pythia cost frontier" in out
    assert "cost_per_token has" in out
    assert "Pay down the heaviest root-debt family" in out


def test_next_work_json_shape_matches_public_compass_contract():
    with captured_stdout() as buf:
        rc = main(["next-work", "--json"])

    payload = json.loads(buf.getvalue())
    assert rc == 0
    assert set(payload) == {"highest_impact", "best_implementations", "bug_risks"}
    assert len(payload["highest_impact"]) == 3
    assert len(payload["best_implementations"]) == 4
    assert len(payload["bug_risks"]) == 10
    assert payload["highest_impact"][0]["title"] == (
        "Close the sourced Pythia cost frontier"
    )


def test_scenario_report_missing_families_groups_cost_per_token_roots():
    with captured_stdout() as buf:
        rc = main([
            "scenario-report",
            "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
            "--missing-families",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "tokens_per_second: ok target=training.tokens_per_sec" in out
    assert "cost_per_token: issues target=econ.cost.per_token" in out
    assert "missing=33" in out

    clean_slice = out[
        out.index("tokens_per_second: ok"):
        out.index("cost_per_token: issues")
    ]
    assert "missing families:" not in clean_slice
    assert "    missing families:" in out
    assert (
        "family=cluster.node boundary_category=primitive-root "
        "primitive_boundary=True count=6"
    ) in out
    assert (
        "family=cluster.node boundary_category=symbolic-boundary "
        "primitive_boundary=False count=1 names=cluster.node.storage_power"
    ) in out
    assert (
        "family=econ.asset boundary_category=primitive-root "
        "primitive_boundary=True count=2"
    ) in out
    assert (
        "family=econ.cluster boundary_category=primitive-root "
        "primitive_boundary=True count=3"
    ) in out
    assert (
        "family=econ.cluster boundary_category=symbolic-boundary "
        "primitive_boundary=False count=1 names=econ.cluster.facility_capex"
    ) in out
    assert (
        "family=econ.node boundary_category=primitive-root "
        "primitive_boundary=True count=5"
    ) in out
    assert (
        "family=econ.power boundary_category=primitive-root "
        "primitive_boundary=True count=1 names=econ.power.capacity_charge_kw_month"
    ) in out
    assert (
        "family=thermal.water boundary_category=primitive-root "
        "primitive_boundary=True count=4"
    ) in out


def test_scenario_report_json_default_targets_exposes_status_contract():
    with captured_stdout() as buf:
        rc = main([
            "scenario-report",
            "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
            "--json",
        ])

    report = json.loads(buf.getvalue())
    assert rc == 0
    assert report["preset"] == "pythia_70m_dgx_h100_us_2024_industrial_power"
    assert report["assignment_count"] > 0
    assert report["variant_count"] >= 0
    assert report["sourced"] is True
    assert report["issue_count"] >= 1

    targets = {target["label"]: target for target in report["targets"]}
    for label, target in targets.items():
        assert {
            "status",
            "value",
            "missing_count",
            "violated_constraint_count",
            "violated_approximation_validity_count",
            "trace_steps",
        } <= set(target), label

    tokens_per_second = targets["tokens_per_second"]
    assert tokens_per_second["status"] == "ok"
    assert tokens_per_second["target"] == "training.tokens_per_sec"
    assert tokens_per_second["missing_count"] == 0
    assert tokens_per_second["violated_constraint_count"] == 0
    assert tokens_per_second["violated_approximation_validity_count"] == 0
    assert tokens_per_second["trace_steps"] > 0

    cost_per_token = targets["cost_per_token"]
    assert cost_per_token["status"] == "issues"
    assert cost_per_token["target"] == "econ.cost.per_token"
    assert cost_per_token["missing_count"] > 0


def test_scenario_report_json_custom_material_target_keeps_exact_label():
    with captured_stdout() as buf:
        rc = main([
            "scenario-report",
            "materials.source_hydrogen_1",
            "--target",
            "source_z=physical.lithography.source_proton_count",
            "--json",
        ])

    report = json.loads(buf.getvalue())
    assert rc == 0
    assert report["preset"] == "source_hydrogen_1"
    assert report["assignment_count"] > 0
    assert report["variant_count"] >= 0
    assert report["sourced"] is True
    assert report["issue_count"] == 0
    assert [target["label"] for target in report["targets"]] == ["source_z"]

    target = report["targets"][0]
    assert target["status"] == "ok"
    assert target["target"] == "physical.lithography.source_proton_count"
    assert target["value"] == 1
    assert target["missing_count"] == 0
    assert target["violated_constraint_count"] == 0
    assert target["violated_approximation_validity_count"] == 0
    assert target["trace_steps"] > 0


def test_scenario_audit_text_lists_sourced_pack_targets():
    with captured_stdout() as buf:
        rc = main(["scenario-audit"])

    out = buf.getvalue()
    assert rc == 0
    assert "Scenario audit:" in out
    assert "packs  " in out
    assert "pythia_70m_dgx_h100_us_2024_industrial_power: issues" in out
    assert "tokens_per_second: ok target=training.tokens_per_sec" in out
    assert "cost_per_token: issues target=econ.cost.per_token" in out
    assert "euv_tin120_lpp_source_context_assumption: ok" in out
    assert (
        "pulse_repetition_rate: ok "
        "target=physical.lithography.source_plasma_pulse_repetition_rate"
    ) in out


def test_scenario_audit_json_reports_sourced_pack_issue_contract():
    with captured_stdout() as buf:
        rc = main(["scenario-audit", "--json"])

    audit = json.loads(buf.getvalue())
    assert rc == 0
    assert audit["pack_count"] >= 2
    assert audit["issue_count"] >= 1

    reports = {report["preset"]: report for report in audit["reports"]}
    assert {
        "pythia_70m_dgx_h100_us_2024_industrial_power",
        "euv_tin120_lpp_source_context_assumption",
    } <= set(reports)
    assert reports["pythia_70m_dgx_h100_us_2024_industrial_power"]["status"] == (
        "issues"
    )
    assert reports["euv_tin120_lpp_source_context_assumption"]["status"] == "ok"

    euv_targets = {
        target["label"]: target
        for target in reports["euv_tin120_lpp_source_context_assumption"]["targets"]
    }
    assert euv_targets["source_proton_count"]["value"] == 50
    assert euv_targets["source_neutron_count"]["value"] == 70


def test_scenario_audit_json_compares_pythia_full_cost_and_energy_floor():
    with captured_stdout() as buf:
        rc = main(["scenario-audit", "--json"])

    audit = json.loads(buf.getvalue())
    assert rc == 0

    original_report = report_by_preset(audit["reports"], ORIGINAL_PYTHIA_SCENARIO)
    original_cost = target_by_label(original_report, "cost_per_token")
    assert original_report["status"] == "issues"
    assert original_cost["status"] == "issues"
    assert original_cost["target"] == "econ.cost.per_token"
    assert original_cost["missing_count"] > 0

    energy_floor_report = pythia_energy_floor_report(audit["reports"])
    energy_floor_cost = target_by_label(energy_floor_report, "cost_per_token")
    assert energy_floor_cost["status"] == "ok"
    assert energy_floor_cost["target"] == "econ.cost.per_token"
    assert energy_floor_cost["missing_count"] == 0
    assert energy_floor_cost["violated_constraint_count"] == 0
    assert energy_floor_cost["violated_approximation_validity_count"] == 0
    assert energy_floor_cost["value"] is not None


def test_scenario_audit_preset_selector_audits_only_selected_pack():
    with captured_stdout() as buf:
        rc = main([
            "scenario-audit",
            "--preset",
            "scenarios.euv_tin120_lpp_source_context_assumption",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "Scenario audit:" in out
    assert "packs  1" in out
    assert "euv_tin120_lpp_source_context_assumption: ok" in out
    assert "source_proton_count: ok target=physical.lithography.source_proton_count" in out
    assert "pythia_70m_dgx_h100_us_2024_industrial_power" not in out


def test_scenario_audit_missing_families_groups_selected_cost_per_token():
    with captured_stdout() as buf:
        rc = main([
            "scenario-audit",
            "--preset",
            "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
            "--target",
            "cost_per_token=econ.cost.per_token",
            "--missing-families",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "packs  1" in out
    assert "pythia_70m_dgx_h100_us_2024_industrial_power: issues" in out
    assert (
        "cost_per_token: issues target=econ.cost.per_token "
        "missing=33 violated_constraints=0"
    ) in out
    assert "unresolved inputs:" not in out
    assert "      missing families:" in out
    assert (
        "family=cluster.node boundary_category=primitive-root "
        "primitive_boundary=True count=6"
    ) in out
    assert (
        "family=cluster.node boundary_category=symbolic-boundary "
        "primitive_boundary=False count=1 names=cluster.node.storage_power"
    ) in out
    assert (
        "family=econ.cluster boundary_category=symbolic-boundary "
        "primitive_boundary=False count=1 names=econ.cluster.facility_capex"
    ) in out
    assert (
        "family=thermal.water boundary_category=primitive-root "
        "primitive_boundary=True count=4"
    ) in out


def test_scenario_audit_missing_families_omits_clean_selected_euv_pack():
    with captured_stdout() as buf:
        rc = main([
            "scenario-audit",
            "--preset",
            "scenarios.euv_tin120_lpp_source_context_assumption",
            "--missing-families",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "packs  1" in out
    assert "euv_tin120_lpp_source_context_assumption: ok" in out
    assert "source_proton_count: ok target=physical.lithography.source_proton_count" in out
    assert "missing families:" not in out


def test_scenario_audit_json_preset_and_target_selectors_return_one_target():
    with captured_stdout() as buf:
        rc = main([
            "scenario-audit",
            "--preset",
            "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
            "--target",
            "power=econ.run.power_cost",
            "--json",
        ])

    audit = json.loads(buf.getvalue())
    assert rc == 0
    assert audit["pack_count"] == 1
    assert len(audit["reports"]) == 1

    report = audit["reports"][0]
    assert report["preset"] == "pythia_70m_dgx_h100_us_2024_industrial_power"
    assert report["target_count"] == 1
    assert [target["label"] for target in report["targets"]] == ["power"]

    target = report["targets"][0]
    assert target["status"] == "ok"
    assert target["target"] == "econ.run.power_cost"


def test_scenario_audit_unknown_target_variable_raises_parser_helper_exit():
    with pytest.raises(SystemExit, match="unknown report target variable"):
        main([
            "scenario-audit",
            "--target",
            "bad=econ.run.power_costz",
        ])


def test_scenario_audit_fail_on_issues_respects_selected_pack_and_target():
    with captured_stdout() as buf:
        euv_rc = main([
            "scenario-audit",
            "--preset",
            "scenarios.euv_tin120_lpp_source_context_assumption",
            "--fail-on-issues",
        ])
    euv_out = buf.getvalue()
    assert euv_rc == 0
    assert "packs  1" in euv_out
    assert "issues 0" in euv_out
    assert "euv_tin120_lpp_source_context_assumption: ok" in euv_out

    with captured_stdout() as buf:
        pythia_rc = main([
            "scenario-audit",
            "--preset",
            "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
            "--target",
            "cost_per_token=econ.cost.per_token",
            "--fail-on-issues",
        ])
    pythia_out = buf.getvalue()
    assert pythia_rc == 1
    assert "packs  1" in pythia_out
    assert "pythia_70m_dgx_h100_us_2024_industrial_power: issues" in pythia_out
    assert "cost_per_token: issues target=econ.cost.per_token" in pythia_out


def test_scenario_audit_fail_on_issues_returns_nonzero():
    with captured_stdout() as buf:
        rc = main(["scenario-audit", "--fail-on-issues"])

    assert rc == 1
    assert "issues" in buf.getvalue()


def test_scenario_report_custom_target_and_fail_on_issues():
    with captured_stdout() as buf:
        rc = main([
            "scenario-report",
            "materials.source_hydrogen_1",
            "--target",
            "source_z=physical.lithography.source_proton_count",
            "--fail-on-issues",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "source_z: ok target=physical.lithography.source_proton_count" in out
    assert "value=1" in out

    with captured_stdout() as buf:
        rc = main([
            "scenario-report",
            "materials.source_hydrogen_1",
            "--target",
            "source_z=physical.lithography.source_proton_count",
            "--assign",
            "physical.lithography.source_valence_up_quark_count=0",
            "--fail-on-issues",
        ])
    out = buf.getvalue()
    assert rc == 1
    assert "source_z: issues target=physical.lithography.source_proton_count" in out
    assert "violated_constraints=" in out


def test_resolve_missing_exposes_source_valence_root_diagnostics():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.source_proton_count",
            "--missing",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert (
        "missing: ['physical.lithography.source_valence_down_quark_count', "
        "'physical.lithography.source_valence_up_quark_count']"
    ) in out
    assert "unresolved inputs:" in out
    assert out.count("kind=ROOT_INPUT reason=root input assignment required") == 2
    assert "kind=DERIVED reason=symbolic boundary" not in out

    down = unresolved_input_line(
        out,
        "physical.lithography.source_valence_down_quark_count",
    )
    up = unresolved_input_line(
        out,
        "physical.lithography.source_valence_up_quark_count",
    )
    assert "[count] scope=physical kind=ROOT_INPUT" in down
    assert "[count] scope=physical kind=ROOT_INPUT" in up
    assert (
        "hint: --assign "
        "physical.lithography.source_valence_down_quark_count=VALUE"
    ) in out
    assert (
        "direct physical.lithography.source_neutron_count, "
        "physical.lithography.source_proton_count"
    ) in out


def test_resolve_missing_families_groups_source_valence_roots():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.source_proton_count",
            "--missing-families",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "physical.lithography.source_proton_count =" in out
    assert "unresolved inputs:" not in out
    assert "missing families:" in out
    assert (
        "family=physical.lithography.source_valence "
        "boundary_category=primitive-root primitive_boundary=True count=2 "
        "names=physical.lithography.source_valence_down_quark_count, "
        "physical.lithography.source_valence_up_quark_count"
    ) in out


def test_resolve_missing_exposes_mixed_cost_frontier_diagnostics():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "econ.cost.per_token",
            "--preset",
            "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
            "--missing",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "econ.cost.per_token =" in out
    assert "missing:" in out
    assert "unresolved inputs:" in out
    assert out.count("kind=DERIVED reason=symbolic boundary") == 3
    assert "missing families:" not in out

    for variable, expected in {
        "cluster.node.cpu.power_per_cpu": (
            "[W/CPU] scope=cluster kind=ROOT_INPUT "
            "reason=root input assignment required"
        ),
        "cluster.node.storage_power": (
            "[W] scope=cluster kind=DERIVED "
            "reason=symbolic boundary; assign directly or resolve its inputs"
        ),
        "econ.cluster.facility_capex": (
            "[USD] scope=economics kind=DERIVED "
            "reason=symbolic boundary; assign directly or resolve its inputs"
        ),
        "econ.node.cpu_capex": (
            "[USD] scope=economics kind=ROOT_INPUT "
            "reason=root input assignment required"
        ),
        "econ.power.capacity_charge_kw_month": (
            "[USD/(kW*month)] scope=economics kind=ROOT_INPUT "
            "reason=root input assignment required"
        ),
        "thermal.water.latent_heat": (
            "[J/kg] scope=thermal kind=ROOT_INPUT "
            "reason=root input assignment required"
        ),
    }.items():
        assert expected in unresolved_input_line(out, variable)

    assert "definitions: cluster.eq.node_storage_power" in out
    assert "definitions: econ.eq.cluster_facility_capex" in out
    assert "definitions: econ.eq.network_transit_cost_rate" in out


def test_resolve_missing_families_groups_mixed_cost_frontier():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "econ.cost.per_token",
            "--preset",
            "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
            "--missing-families",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "econ.cost.per_token =" in out
    assert "unresolved inputs:" not in out
    assert "missing families:" in out
    assert (
        "family=cluster.node boundary_category=primitive-root "
        "primitive_boundary=True count=6"
    ) in out
    assert (
        "family=cluster.node boundary_category=symbolic-boundary "
        "primitive_boundary=False count=1 names=cluster.node.storage_power"
    ) in out
    assert (
        "family=econ.cluster boundary_category=primitive-root "
        "primitive_boundary=True count=3"
    ) in out
    assert (
        "family=econ.cluster boundary_category=symbolic-boundary "
        "primitive_boundary=False count=1 names=econ.cluster.facility_capex"
    ) in out
    assert (
        "family=econ.network boundary_category=symbolic-boundary "
        "primitive_boundary=False count=1 names=econ.network.transit_cost_rate"
    ) in out
    assert (
        "family=thermal.water boundary_category=primitive-root "
        "primitive_boundary=True count=4"
    ) in out


def test_resolve_missing_and_missing_families_prints_both_sections():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.source_proton_count",
            "--missing",
            "--missing-families",
        ])

    out = buf.getvalue()
    assert rc == 0
    assert "missing:" in out
    assert "unresolved inputs:" in out
    assert "missing families:" in out
    assert (
        "physical.lithography.source_valence_down_quark_count [count] "
        "scope=physical kind=ROOT_INPUT"
    ) in unresolved_input_line(
        out,
        "physical.lithography.source_valence_down_quark_count",
    )
    assert (
        "family=physical.lithography.source_valence "
        "boundary_category=primitive-root primitive_boundary=True count=2"
    ) in out


def test_resolve_with_material_preset_hits_formula_count():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main([
            "resolve",
            "physical.lithography.medium_formula_unit_electron_count",
            "--preset",
            "materials.medium_h2o_h1_o16_composition",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "physical.lithography.medium_formula_unit_electron_count = 10" in out


def test_resolve_with_preset_hits_demo_number():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "cluster.rack.peak_flops",
            "--preset", "hardware.demo_rack",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "cluster.rack.peak_flops" in out
    # 1.08e18 shown in SymPy Float format.
    assert "1.08" in out


def test_resolve_with_unused_workload_selector_preset_hits_demo_number():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "cluster.rack.peak_flops",
            "--preset", "hardware.demo_rack",
            "--preset", "workload.dense_variant_selector",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "cluster.rack.peak_flops" in out
    assert "1.08" in out


def test_resolve_with_scenario_preset_hits_cost_per_token():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "econ.cost.per_token",
            "--preset", "scenarios.dense_training_cost_fixture",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "econ.cost.per_token" in out
    assert "0.000003000078" in out


def test_resolve_with_sourced_scenario_preset_hits_power_cost():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "econ.run.power_cost",
            "--preset",
            "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
            "--trace",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "econ.run.power_cost = 54.4378103942861" in out
    assert "econ.eq.run_power_cost" in out
    assert "econ.eq.price_kwh" in out
    assert "0.0813000000000000" in out


def test_resolve_cli_variant_overrides_preset_selector():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "training.flops_per_step",
            "--preset", "workload.dense_variant_selector",
            "--assign", "arch.flops.step_dense=1e21",
            "--assign", "arch.flops.step_moe=3e20",
            "--variant", "training.flops_per_step=moe",
            "--trace",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "training.eq.flops_step_moe" in out
    assert "3.00000000000000E+20" in out


def test_resolve_with_inline_assignment():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "cluster.node.peak_flops",
            "--assign", "cluster.node.n_gpus=4",
            "--assign", "gpu.peak_flops=2e15",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "8.00" in out.replace("E+", "e+").replace("E-", "e-")


def test_resolve_trace_prints_equation_names():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "cluster.rack.peak_flops",
            "--preset", "hardware.demo_rack",
            "--trace",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "cluster.eq.rack_peak_flops" in out


def test_resolve_constraints_prints_constraint_status():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.gate.elmore_delay",
            "--assign", "physical.gate.r_on=1",
            "--assign", "physical.gate.fanout=1",
            "--assign", "physical.gate.c_input=1",
            "--assign", "physical.interconnect.c_total=1",
            "--assign", "physical.interconnect.r_per_length=0",
            "--assign", "physical.interconnect.c_per_length=1",
            "--assign", "physical.wire_length=1",
            "--assign", "physical.clock_frequency=0.1",
            "--constraints",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "constraints:" in out
    assert "physical.eq.clock_timing_constraint [satisfied]" in out


def test_resolve_approximation_validity_prints_status():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.medium_formula_unit_intercomponent_binding_energy",
            "--assign",
            "physical.lithography.medium_component_a_effective_intercomponent_charge_number=1",
            "--assign",
            "physical.lithography.medium_component_b_effective_intercomponent_charge_number=1",
            "--assign",
            "physical.lithography.medium_formula_unit_intercomponent_pair_count=1",
            "--assign",
            "physical.lithography.medium_component_a_effective_intercomponent_radius=4e-10",
            "--assign",
            "physical.lithography.medium_component_b_effective_intercomponent_radius=4e-10",
            "--assign",
            "physical.lithography.medium_intercomponent_gap=2e-10",
            "--assign",
            "physical.lithography.medium_intercomponent_relative_permittivity=1",
            "--approximation-validity",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "approximation validity:" in out
    assert (
        "physical.eq.lithography_medium_formula_unit_intercomponent_binding_energy"
        " [violated]"
    ) in out


def test_resolve_fail_on_violated_constraints_returns_nonzero():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.gate.elmore_delay",
            "--assign", "physical.gate.r_on=1",
            "--assign", "physical.gate.fanout=1",
            "--assign", "physical.gate.c_input=1",
            "--assign", "physical.interconnect.c_total=1",
            "--assign", "physical.interconnect.r_per_length=0",
            "--assign", "physical.interconnect.c_per_length=1",
            "--assign", "physical.wire_length=1",
            "--assign", "physical.clock_frequency=1",
            "--constraints",
            "--fail-on-violated-constraints",
        ])
    out = buf.getvalue()
    assert rc == 1
    assert "physical.eq.clock_timing_constraint [violated]" in out


def test_resolve_fail_on_violated_domain_constraint_returns_nonzero():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.source_plasma_drive_peak_intensity",
            "--assign",
            "physical.lithography.source_plasma_drive_pulse_fluence=-1",
            "--assign",
            "physical.lithography.source_plasma_drive_pulse_duration=1",
            "--assign",
            "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor=1",
            "--constraints",
            "--fail-on-violated-constraints",
        ])
    out = buf.getvalue()
    assert rc == 1
    assert (
        "domain.physical.lithography.source_plasma_drive_pulse_fluence.positive"
        " [violated]"
    ) in out


def test_resolve_fail_on_violated_approximation_validity_returns_nonzero():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.medium_formula_unit_intercomponent_binding_energy",
            "--assign",
            "physical.lithography.medium_component_a_effective_intercomponent_charge_number=1",
            "--assign",
            "physical.lithography.medium_component_b_effective_intercomponent_charge_number=1",
            "--assign",
            "physical.lithography.medium_formula_unit_intercomponent_pair_count=1",
            "--assign",
            "physical.lithography.medium_component_a_effective_intercomponent_radius=4e-10",
            "--assign",
            "physical.lithography.medium_component_b_effective_intercomponent_radius=4e-10",
            "--assign",
            "physical.lithography.medium_intercomponent_gap=2e-10",
            "--assign",
            "physical.lithography.medium_intercomponent_relative_permittivity=1",
            "--approximation-validity",
            "--fail-on-violated-approximation-validity",
        ])
    out = buf.getvalue()
    assert rc == 1
    assert (
        "physical.eq.lithography_medium_formula_unit_intercomponent_binding_energy"
        " [violated]"
    ) in out


def test_resolve_fail_on_recovered_violated_approximation_validity_returns_nonzero():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.lithography.source_nuclear_radius_coefficient",
            "--assign",
            "physical.lithography.source_binding_coulomb_coefficient=-1",
            "--approximation-validity",
            "--fail-on-violated-approximation-validity",
        ])
    out = buf.getvalue()
    assert rc == 1
    assert (
        "physical.eq.lithography_source_nuclear_radius_coefficient"
        " [violated]"
    ) in out


def test_resolve_bad_variant_selector_returns_clean_error():
    with captured_stderr() as err:
        rc = main([
            "resolve",
            "cluster.rack.peak_flops",
            "--variant",
            "cluster.rack.n_nodes=dense",
        ])
    assert rc == 1
    assert "resolve error:" in err.getvalue()
    assert "no VARIANT relations" in err.getvalue()


def test_resolve_bad_assignment_returns_clean_error():
    with captured_stderr() as err:
        rc = main([
            "resolve",
            "cluster.rack.peak_flops",
            "--assign",
            "cluster.rack.n_NODES=9",
        ])
    assert rc == 1
    assert "resolve error:" in err.getvalue()
    assert "unknown variable name in assignments" in err.getvalue()


def test_resolve_unknown_target_returns_clean_error():
    with captured_stderr() as err:
        rc = main(["resolve", "cluster.rack.peak_flopz"])
    assert rc == 1
    assert "resolve error:" in err.getvalue()
    assert "unknown variable name" in err.getvalue()


def test_resolve_unknown_preset_raises_clean_error():
    with pytest.raises(SystemExit):
        main([
            "resolve",
            "cluster.rack.peak_flops",
            "--preset", "hardware.does_not_exist",
        ])
