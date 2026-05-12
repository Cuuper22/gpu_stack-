"""
Tests for the live next-work planning API.
"""

from __future__ import annotations

import json

from gpu_stack import Registry
from gpu_stack.next_work import NextWorkItem, NextWorkPlan, build_next_work_plan
from gpu_stack.presets import scenarios


def _all_items(plan: NextWorkPlan) -> tuple[NextWorkItem, ...]:
    return (*plan.highest_impact, *plan.best_implementations, *plan.bug_risks)


def _all_evidence(plan: NextWorkPlan) -> str:
    return "\n".join(item.evidence for item in _all_items(plan))


def _pythia_cost_target_missing_count() -> int:
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power
    report = preset.evaluate_targets(scenarios.scenario_targets_for(preset))
    for target in report.targets:
        if target.label == "cost_per_token":
            return target.missing_count
    raise AssertionError("Pythia scenario report did not include cost_per_token")


def test_next_work_plan_has_exact_public_shape_and_lengths():
    plan = build_next_work_plan()
    payload = plan.to_dict()

    assert set(payload) == {"highest_impact", "best_implementations", "bug_risks"}
    assert len(plan.highest_impact) == 3
    assert len(plan.best_implementations) == 4
    assert len(plan.bug_risks) == 10

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
    stats = Registry.stats()
    coverage = Registry.coverage()
    pythia_missing = _pythia_cost_target_missing_count()

    assert "live Registry.stats()" in evidence
    assert f"{stats['variables']} variables" in evidence
    assert f"{stats['equations']} equations" in evidence
    assert f"Registry.roots()={stats['root_inputs']}" in evidence
    assert "live Registry.coverage()" in evidence
    assert str(coverage["non_constant_variables"]) in evidence
    assert "pythia_70m_dgx_h100_us_2024_industrial_power" in evidence
    assert f"cost_per_token has {pythia_missing} missing inputs" in evidence
    assert "missing families:" in evidence
    assert "physical.lithography" in evidence
    assert "large_project_files=" in evidence


def test_next_work_plan_output_has_no_stale_snapshot_numbers():
    rendered = json.dumps(build_next_work_plan().to_dict(), sort_keys=True)

    assert "954" not in rendered
    assert "548" not in rendered
