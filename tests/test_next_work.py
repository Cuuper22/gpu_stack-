"""
Tests for the live next-work planning API.
"""

from __future__ import annotations

import json

from gpu_stack import Registry
from gpu_stack.next_work import NextWorkItem, NextWorkPlan, build_next_work_plan
from gpu_stack.next_work_evidence import _experiment_artifacts


def _all_items(plan: NextWorkPlan) -> tuple[NextWorkItem, ...]:
    return (
        *plan.highest_impact,
        *plan.best_implementations,
        *plan.bug_risks,
        *plan.legacy_diagnostics,
    )


def _all_evidence(plan: NextWorkPlan) -> str:
    return "\n".join(item.evidence for item in _all_items(plan))


def test_next_work_plan_has_exact_public_shape_and_lengths():
    plan = build_next_work_plan()
    payload = plan.to_dict()

    assert set(payload) == {"highest_impact", "best_implementations", "bug_risks"}
    assert len(plan.highest_impact) == 3
    assert len(plan.best_implementations) == 4
    assert len(plan.bug_risks) == 10
    assert len(plan.legacy_diagnostics) == 2
    assert plan.research_priorities == plan.highest_impact

    for section in payload.values():
        assert isinstance(section, list)
        for item in section:
            assert {"title", "evidence"} <= set(item)
            assert set(item) <= {"title", "evidence", "command", "path"}
            assert item["title"].strip()
            assert item["evidence"].strip()


def test_next_work_plan_evidence_is_live_and_high_signal():
    plan = build_next_work_plan()
    evidence = _all_evidence(plan)

    assert "No physical PW3 result artifact exists" in evidence
    assert "named rack with at least eight GPUs" in evidence
    assert "Summed GPU power, inferred storage power, or static PUE" in evidence
    assert "two calibration and six evaluation blocks" in evidence
    assert "one stable NVML UUID per torchrun rank" in evidence
    assert "No physical artifact means no PW3 visual claim" in "\n".join(
        item.title for item in plan.bug_risks
    )


def test_highest_impact_is_research_first_and_legacy_diagnostics_stay_secondary():
    plan = build_next_work_plan()

    assert [item.title for item in plan.highest_impact] == [
        "Bind E002-PW3 to a named instrumented rack and execute it",
        "Keep the first rack result at the direct measurement boundary",
        "Let the paired physical result choose PW4 or kill the mechanism",
    ]
    highest_titles = "\n".join(item.title.lower() for item in plan.highest_impact)
    assert "pythia" not in highest_titles
    assert "root-debt" not in highest_titles

    legacy_titles = [item.title for item in plan.legacy_diagnostics]
    assert legacy_titles == [
        "Close the sourced Pythia cost frontier",
        "Pay down the heaviest root-debt family",
    ]
    assert all(
        "classification=legacy" in item.evidence
        for item in plan.legacy_diagnostics
    )


def test_research_priorities_are_backed_by_live_executable_artifact_evidence():
    plan = build_next_work_plan()
    rendered = "\n".join(item.evidence for item in plan.highest_impact)

    assert "dependency-safe scheduler" in rendered
    assert "torchrun runtime" in rendered
    assert "UUID-bound GPU telemetry" in rendered
    assert "No physical PW3 result artifact exists" in rendered
    assert "direct rack-PDU power" in rendered
    assert "independent storage power and cooling" in rendered
    assert "measurement_invalid" in rendered
    assert "synchronized, random-jitter, storage-only" in rendered
    assert "two calibration and six evaluation blocks" in rendered
    assert "otherwise publish the failed or simpler mechanism" in rendered


def test_experiment_result_scan_does_not_count_scenario_inputs(tmp_path):
    experiment = tmp_path / "experiments" / "e001"
    experiment.mkdir(parents=True)
    (experiment / "experiment.md").write_text("# E001\n", encoding="utf-8")
    (experiment / "screening-scenario.json").write_text(
        json.dumps({"scenario_id": "screening", "sites": []}),
        encoding="utf-8",
    )
    result = experiment / "screening-result.json"
    result.write_text(
        json.dumps(
            {
                "scenario_id": "screening",
                "protocol_hash": "sha256:example",
                "runs": [],
            }
        ),
        encoding="utf-8",
    )

    specs, results = _experiment_artifacts(tmp_path)

    assert specs == (experiment / "experiment.md",)
    assert results == (result,)


def test_zero_gap_metadata_categories_are_not_active_bug_titles():
    plan = build_next_work_plan()
    coverage = Registry.coverage()
    titles = {item.title for item in plan.bug_risks}

    checks = (
        (
            coverage["non_constant_variables"] - coverage["with_sp_units"],
            "Variable unit metadata has an active gap",
        ),
        (
            coverage["non_constant_variables"] - coverage["with_references"],
            "Variable provenance metadata has an active gap",
        ),
        (
            coverage["equations"] - coverage["equations_with_references"],
            "Equation provenance metadata has an active gap",
        ),
        (
            coverage["equations"] - coverage["equations_with_unit_check"],
            "Equation unit checking has an active gap",
        ),
    )
    for gap, title in checks:
        if gap == 0:
            assert title not in titles


def test_legacy_diagnostics_do_not_change_json_wire_shape():
    plan = build_next_work_plan()
    payload = plan.to_dict()

    assert set(payload) == {"highest_impact", "best_implementations", "bug_risks"}
    rendered = json.dumps(payload, sort_keys=True)
    assert "classification=legacy" not in rendered


def test_next_work_plan_output_has_no_stale_snapshot_numbers():
    rendered = json.dumps(build_next_work_plan().to_dict(), sort_keys=True)

    assert "954 variables" not in rendered
    assert "548 equations" not in rendered
