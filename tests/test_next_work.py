"""Tests for the live next-work planning API.

``build_next_work_plan()`` reads the current dependency graph and experiment
artifacts, then returns a prioritized work plan: what to research next, how to
implement it, and which bugs threaten the results. These tests verify three
properties that keep the plan trustworthy. First, the shape is exact — fixed
section sizes and a stable JSON wire format, so downstream tooling never
breaks. Second, the evidence is live — every item cites current graph numbers
and real experiment results, never stale snapshots. Third, the ordering is
honest — research priorities come first, and legacy diagnostics stay out of
the public payload.
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

    assert "adaptive switching failed all four claim gates" in evidence
    assert "104 decisions fell outside calibrated support" in evidence
    assert "software-selectable model and optimizer families" in evidence
    assert "cannot inspect future loss" in evidence
    assert "zero sample-hash, optimizer-lineage, and work violations" in evidence
    assert "Physical PW3 is optional calibration, not an execution gate" in "\n".join(
        item.title for item in plan.bug_risks
    )


def test_highest_impact_is_research_first_and_legacy_diagnostics_stay_secondary():
    plan = build_next_work_plan()

    assert [item.title for item in plan.highest_impact] == [
        "Preserve E001-SC1's rejected controller as the baseline result",
        "Run E001-SC2 on a held-out model or optimizer family",
        "Use physical collaboration only as optional calibration",
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
    priorities = "\n".join(item.evidence for item in plan.highest_impact)
    implementations = "\n".join(item.evidence for item in plan.best_implementations)

    assert "conclusion=abstain_without_policy_claim" in priorities
    assert "failed learning, communication, modeled-time" in priorities
    assert "Do not retune on its six evaluation families" in priorities
    assert "wholly withheld model or optimizer family" in priorities
    assert "optional calibration" in "\n".join(
        item.title.lower() + " " + item.evidence.lower()
        for item in plan.highest_impact
    )
    assert "predictor target, family split, comparator, and falsifiers" in implementations
    assert "pre-action learning-penalty, WAN, and virtual-time prediction" in implementations
    assert "realized held-out learning and infrastructure consequences" in implementations


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
