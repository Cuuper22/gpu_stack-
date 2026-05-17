"""CLI scenario report and audit command tests."""

import json

import pytest

from gpu_stack.cli import main
from tests.helpers.cli import (
    ORIGINAL_PYTHIA_SCENARIO,
    captured_stdout,
    pythia_energy_floor_report,
    report_by_preset,
    target_by_label,
)


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
