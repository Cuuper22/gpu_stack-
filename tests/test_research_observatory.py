"""Tests for the E001 screening observatory projection.

``build_e001_observatory_artifact`` turns an E001 comparison into the
published observatory view. These tests check the projection cannot
overstate the science: with no held-out learning data the artifact must say
so plainly ("cannot answer" in the plain-language summary, held-out
validation False, time-to-target marked "unmeasured", and no synthesized
progress-per-FLOP metric). Each run keeps its declared comparison role —
reference baseline, preregistered baseline, hypothesis policy — and the
artifact binds to its source result by schema and SHA-256 hash. Timelines
must be causally sorted, so every rendered event sequence reads in real
time order.
"""

from dataclasses import replace
from pathlib import Path

from gpu_stack.research.e001 import E001Scenario, run_e001
from gpu_stack.research.observatory import build_e001_observatory_artifact


SCENARIO_PATH = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "e001-beyond-one-datacenter"
    / "screening-scenario-v1.json"
)


def test_observatory_projection_preserves_inconclusive_learning_boundary():
    scenario = E001Scenario.from_json(SCENARIO_PATH.read_text(encoding="utf-8"))
    comparison = run_e001(
        replace(scenario, total_steps=4, checkpoint_bytes=0, outages=())
    )

    artifact = build_e001_observatory_artifact(comparison)

    assert artifact["status"]["held_out_learning_validation"] is False
    assert artifact["status"]["hypothesis_policy"] == "adaptive_cadence"
    adaptive_artifact = next(
        item for item in comparison.artifacts if item.policy == "adaptive_cadence"
    )
    assert artifact["status"]["conclusion"] == adaptive_artifact.conclusion
    assert artifact["source_result"]["schema"] == "gpu-stack.e001-comparison.v1"
    assert len(artifact["source_result"]["artifact_sha256"]) == 64
    assert len(artifact["artifact_sha256"]) == 64
    assert "cannot answer" in artifact["status"]["plain_answer"]
    assert [run["comparison_role"] for run in artifact["runs"]] == [
        "reference_baseline",
        "preregistered_baseline",
        "hypothesis_policy",
    ]
    evidence_by_node = {
        node["node_id"]: node["evidence_class"]
        for node in artifact["causal_graph"]["nodes"]
    }
    assert evidence_by_node["learning_progress"] == "prior"
    assert evidence_by_node["time_to_target"] == "unmeasured"
    assert "progress_per_flop_ratio" not in artifact["runs"][1][
        "experiment_artifact"
    ]["metrics"]
    assert artifact["timeline"]["synchronous"]
    assert len(artifact["missing_observation_ids"]) == 3


def test_observatory_timeline_is_causally_sorted():
    scenario = E001Scenario.from_json(SCENARIO_PATH.read_text(encoding="utf-8"))
    comparison = run_e001(
        replace(scenario, total_steps=3, checkpoint_bytes=0, outages=())
    )
    artifact = build_e001_observatory_artifact(comparison)

    for events in artifact["timeline"].values():
        ordering = [
            (event["start_ns"], event["end_ns"], event["event_id"])
            for event in events
        ]
        assert ordering == sorted(ordering)
