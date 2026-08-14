"""Tests for the E001 screening experiment engine.

E001 asks whether an adaptive checkpoint cadence beats a synchronous
baseline when training spans sites that suffer outages. ``run_e001``
replays a JSON scenario through three policies — synchronous, fixed-local,
and adaptive-cadence — and emits comparison artifacts with falsifier
verdicts.

These tests guard the engine's honesty. The scenario keeps absolute outage
times and an explicitly unfitted learning prior. Learning falsifiers stay
unresolved (None) in a virtual screen, so the conclusion can be at best
"inconclusive" — the engine may not synthesize progress or completion-time
ratios it never measured. The event timeline is causal: every collective
epoch starts exactly where a preceding compute epoch ended. Result identity
binds protocol, scenario hash, engine source hash, and trace schema, and
including traces changes the artifact hash. Finally, checkpoint cadence is
a property of the scenario, not the policy — all three policies checkpoint
at the same steps with the same bytes, so cadence can never be a hidden
advantage.
"""

from dataclasses import replace
from pathlib import Path

import pytest

from gpu_stack.research.e001 import (
    E001PolicyKind,
    E001Scenario,
    SiteOutage,
    run_e001,
)


SCENARIO_PATH = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "e001-beyond-one-datacenter"
    / "screening-scenario-v1.json"
)


def _screening_scenario() -> E001Scenario:
    return E001Scenario.from_json(SCENARIO_PATH.read_text(encoding="utf-8"))


def test_screening_scenario_keeps_absolute_recovery_and_unfitted_prior_explicit():
    scenario = _screening_scenario()

    assert scenario.outages[0].failure_start_ns == 100_000_000_000
    assert scenario.outages[0].recovery_ns == 130_000_000_000
    assert scenario.outages[0].duration_ns == 30_000_000_000
    assert scenario.learning_prior.to_dict()["evidence_status"] == (
        "screening_prior_not_fitted"
    )
    assert len(scenario.learning_prior.seed_observation_ids) == 3
    assert isinstance(scenario.learning_prior.seed_observation_ids, tuple)


def test_e001_uses_successive_epochs_and_leaves_learning_falsifiers_unresolved():
    scenario = replace(
        _screening_scenario(),
        total_steps=32,
        checkpoint_bytes=0,
        fixed_local_steps=8,
        outages=(
            SiteOutage(
                "test-curtailment",
                "central",
                10_000_000_000,
                12_000_000_000,
                "test event",
            ),
        ),
    )

    comparison = run_e001(scenario)
    fixed, adaptive = comparison.candidates

    assert comparison.baseline.policy_kind is E001PolicyKind.SYNCHRONOUS
    assert fixed.policy_kind is E001PolicyKind.FIXED_LOCAL
    assert adaptive.policy_kind is E001PolicyKind.ADAPTIVE_CADENCE
    assert adaptive.final_local_steps > adaptive.initial_local_steps
    assert len(adaptive.sync_cycles) < len(fixed.sync_cycles)

    adaptive_artifact = comparison.artifacts[1]
    falsifiers = {
        item.falsifier_id: item for item in adaptive_artifact.falsifiers
    }
    assert falsifiers["e001-wan"].survived is True
    assert falsifiers["e001-progress"].survived is None
    assert falsifiers["e001-time"].survived is None
    assert adaptive_artifact.conclusion == "inconclusive"
    assert adaptive_artifact.evidence_gaps
    assert "progress_per_flop_ratio" not in adaptive_artifact.metrics
    assert "completion_time_ratio" not in adaptive_artifact.metrics

    fixed_artifact = comparison.artifacts[0]
    assert fixed_artifact.metrics["collective_payload_byte_fraction"] == pytest.approx(
        0.125
    )
    assert fixed_artifact.conclusion == "failed_virtual_screen"


def test_every_collective_epoch_starts_after_its_preceding_compute_epoch():
    scenario = replace(
        _screening_scenario(),
        total_steps=4,
        checkpoint_bytes=0,
        fixed_local_steps=2,
        outages=(),
    )
    run = run_e001(scenario).candidates[0]

    for index, epoch in enumerate(run.epochs):
        event_kinds = {record.event.kind.value for record in epoch.trace.records}
        if "collective" not in event_kinds:
            continue
        assert index > 0
        previous = run.epochs[index - 1]
        assert previous.end_ns == epoch.start_ns
        assert any(
            record.event.kind.value == "compute"
            for record in previous.trace.records
        )


def test_result_identity_binds_protocol_scenario_engine_and_trace_schema():
    scenario = replace(
        _screening_scenario(),
        total_steps=2,
        checkpoint_bytes=0,
        outages=(),
    )
    comparison = run_e001(scenario)
    compact = comparison.to_dict(include_traces=False)
    traced = comparison.to_dict(include_traces=True)

    assert compact["schema"] == "gpu-stack.e001-comparison.v1"
    assert compact["scenario_hash"] == scenario.scenario_hash
    assert len(compact["engine"]["source_sha256"]) == 64
    assert len(compact["artifact_sha256"]) == 64
    assert compact["artifact_sha256"] != traced["artifact_sha256"]
    assert traced["traces_included"] is True
    for artifact in comparison.artifacts:
        assert scenario.scenario_hash[:12] in artifact.run_id
        assert comparison.engine_source_hash[:12] in artifact.run_id
        assert artifact.metadata["scenario_sha256"] == scenario.scenario_hash
        assert artifact.metadata["engine_source_sha256"] == (
            comparison.engine_source_hash
        )
        assert artifact.trace_uri.startswith("#/runs/")


def test_checkpoint_cadence_is_policy_independent():
    scenario = replace(
        _screening_scenario(),
        total_steps=9,
        checkpoint_bytes=900,
        checkpoint_interval_steps=4,
        fixed_local_steps=3,
        outages=(),
    )
    comparison = run_e001(scenario)
    runs = (comparison.baseline,) + comparison.candidates

    assert {
        run.metrics.checkpoint_bytes for run in runs
    } == {2700.0}
    for run in runs:
        checkpoint_steps = {
            int(dict(record.event.metadata)["step"])
            for epoch in run.epochs
            for record in epoch.trace.records
            if record.event.kind.value == "checkpoint"
        }
        assert checkpoint_steps == {4, 8, 9}
