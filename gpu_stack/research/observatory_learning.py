"""Observatory projection for E001-LC1, the measured learning-calibration sidecar.

Verifies the LC1 result artifact's content hash, then condenses it into a
compact UI payload: per-arm medians, learning curves, paired effects, and
falsifier results. The source conclusion and evidence boundary pass through
unchanged, and the output carries its own SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence


E001_LEARNING_OBSERVATORY_SCHEMA = (
    "gpu-stack.causal-observatory.e001-learning-calibration.v1"
)


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _content_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _median(values: Sequence[float | int | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    return statistics.median(present) if present else None


def _validate_source(result: Mapping[str, Any]) -> None:
    if result.get("schema") != "gpu-stack.e001-recovery-learning-evidence.v1":
        raise ValueError("unsupported E001 learning-evidence schema")
    expected = result.get("artifact_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("learning result artifact_sha256 is missing")
    unhashed = dict(result)
    unhashed.pop("artifact_sha256", None)
    actual = _content_hash(unhashed)
    if actual != expected:
        raise ValueError(
            f"learning result content hash mismatch: expected {expected}, got {actual}"
        )


def _evaluation_runs(result: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    runs = result.get("runs")
    if not isinstance(runs, list):
        raise TypeError("learning result runs must be a list")
    return tuple(run for run in runs if run.get("split") == "evaluation")


def _arm_runs(
    runs: Sequence[Mapping[str, Any]],
    policy_id: str,
    interrupted: bool,
) -> tuple[Mapping[str, Any], ...]:
    selected = tuple(
        run
        for run in runs
        if run.get("policy_id") == policy_id
        and bool(run.get("interrupted")) is interrupted
    )
    if not selected:
        raise ValueError(f"no evaluation runs for {policy_id}, interrupted={interrupted}")
    return selected


def _policy_summary(
    runs: Sequence[Mapping[str, Any]],
    *,
    policy_id: str,
    interrupted: bool,
    label: str,
) -> dict[str, Any]:
    selected = _arm_runs(runs, policy_id, interrupted)
    return {
        "policy_id": policy_id,
        "interrupted": interrupted,
        "label": label,
        "run_count": len(selected),
        "final_held_out_nll": _median(
            [run.get("final_held_out_nll") for run in selected]
        ),
        "held_out_loss_progress": _median(
            [run.get("held_out_loss_progress") for run in selected]
        ),
        "attempted_tokens": _median([run.get("attempted_tokens") for run in selected]),
        "canonical_tokens": _median([run.get("canonical_tokens") for run in selected]),
        "replayed_tokens": _median([run.get("replayed_tokens") for run in selected]),
        "discarded_tokens": _median([run.get("discarded_tokens") for run in selected]),
        "survivor_redistributed_tokens": _median(
            [run.get("survivor_redistributed_tokens") for run in selected]
        ),
        "progress_per_flop": _median(
            [run.get("progress_per_flop") for run in selected]
        ),
        "energy_j": _median(
            [run.get("energy", {}).get("idle_subtracted_energy_j") for run in selected]
        ),
        "active_seconds": _median(
            [run.get("local_wall_clock_seconds") for run in selected]
        ),
        "ticks_to_target": _median(
            [run.get("logical_ticks_to_target") for run in selected]
        ),
        "checkpoint_bytes": _median(
            [run.get("checkpoint_bytes") for run in selected]
        ),
        "divergence_count": sum(bool(run.get("diverged")) for run in selected),
    }


def _learning_curves(runs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    arms = (
        ("synchronous-reference", False, "Synchronous reference"),
        ("fixed-local-checkpoint-restart", False, "Fixed local · no failure"),
        ("fixed-local-checkpoint-restart", True, "Fixed local · interrupted"),
        ("adaptive-survivor-continuation", False, "Adaptive · no failure"),
        ("adaptive-survivor-continuation", True, "Adaptive · interrupted"),
    )
    projected: list[dict[str, Any]] = []
    for policy_id, interrupted, label in arms:
        selected = _arm_runs(runs, policy_id, interrupted)
        by_tick: dict[int, list[float]] = {}
        for run in selected:
            for point in run["curve"]:
                by_tick.setdefault(int(point["wall_tick"]), []).append(
                    float(point["held_out_nll"])
                )
        projected.append(
            {
                "arm_id": (
                    f"{policy_id}:{'interrupted' if interrupted else 'no-failure'}"
                ),
                "policy_id": policy_id,
                "interrupted": interrupted,
                "label": label,
                "points": [
                    {
                        "wall_tick": tick,
                        "median_nll": statistics.median(by_tick[tick]),
                        "minimum_nll": min(by_tick[tick]),
                        "maximum_nll": max(by_tick[tick]),
                    }
                    for tick in sorted(by_tick)
                ],
            }
        )
    return projected


def _run_details(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for run in result["runs"]:
        details.append(
            {
                "run_id": run["run_id"],
                "split": run["split"],
                "stratum_id": run["stratum_id"],
                "seed": run["seed"],
                "policy_id": run["policy_id"],
                "interrupted": run["interrupted"],
                "failure_schedule": run["failure_schedule"],
                "initial_held_out_nll": run["initial_held_out_nll"],
                "final_held_out_nll": run["final_held_out_nll"],
                "held_out_loss_progress": run["held_out_loss_progress"],
                "attempted_tokens": run["attempted_tokens"],
                "canonical_tokens": run["canonical_tokens"],
                "replayed_tokens": run["replayed_tokens"],
                "discarded_tokens": run["discarded_tokens"],
                "survivor_redistributed_tokens": run[
                    "survivor_redistributed_tokens"
                ],
                "progress_per_flop": run["progress_per_flop"],
                "energy_j": run["energy"]["idle_subtracted_energy_j"],
                "active_seconds": run["local_wall_clock_seconds"],
                "physical_seconds": run["physical_wall_clock_seconds"],
                "thermal_pause_seconds": run["thermal_pause_seconds"],
                "start_temperature_c": run["start_temperature_c"],
                "end_temperature_c": run["end_temperature_c"],
                "ticks_to_target": run["logical_ticks_to_target"],
                "diverged": run["diverged"],
                "checkpoint_bytes": run["checkpoint_bytes"],
            }
        )
    return details


def build_e001_learning_observatory_artifact(
    result: Mapping[str, Any],
    *,
    source_uri: str | None = None,
) -> dict[str, Any]:
    """Condense a verified LC1 result into the observatory payload."""

    _validate_source(result)
    runs = _evaluation_runs(result)
    summary = result["summary"]
    fixed = _policy_summary(
        runs,
        policy_id="fixed-local-checkpoint-restart",
        interrupted=True,
        label="Fixed-local restart",
    )
    adaptive = _policy_summary(
        runs,
        policy_id="adaptive-survivor-continuation",
        interrupted=True,
        label="Adaptive survivor continuation",
    )
    synchronous = _policy_summary(
        runs,
        policy_id="synchronous-reference",
        interrupted=False,
        label="Synchronous no-failure reference",
    )
    final_nll_delta = float(adaptive["final_held_out_nll"]) - float(
        fixed["final_held_out_nll"]
    )
    attempted_token_ratio = float(adaptive["attempted_tokens"]) / float(
        fixed["attempted_tokens"]
    )
    progress_per_flop_ratio = float(adaptive["progress_per_flop"]) / float(
        fixed["progress_per_flop"]
    )
    payload: dict[str, Any] = {
        "schema": E001_LEARNING_OBSERVATORY_SCHEMA,
        "experiment_id": result["experiment_id"],
        "scenario_id": result["scenario_id"],
        "source_learning_result": {
            "schema": result["schema"],
            "artifact_sha256": result["artifact_sha256"],
            "scenario_sha256": result["scenario_sha256"],
            "engine_source_sha256": result["engine"]["source_sha256"],
            "uri": source_uri,
        },
        "source_recovery_result": result["source_recovery_result"],
        "conclusion": {
            "status": summary["conclusion"],
            "candidate_survives_lc1": summary["candidate_survives_lc1"],
            "plain_answer": (
                "Adaptive survivor continuation ended with better held-out loss, "
                "but the frozen LC1 rule rejected it: fixed restart performed less "
                "work and therefore looked better per attempted FLOP, while every "
                "policy crossed the calibration target at the first observation."
            ),
            "next_question": (
                "In late-stage training near a fixed loss target, does survivor "
                "continuation reduce time and device energy to target without "
                "sacrificing learning progress per FLOP?"
            ),
        },
        "target": summary["target"],
        "policy_comparison": {
            "fixed_interrupted": fixed,
            "adaptive_interrupted": adaptive,
            "synchronous_reference": synchronous,
            "derived": {
                "adaptive_minus_fixed_final_nll": final_nll_delta,
                "adaptive_to_fixed_attempted_token_ratio": attempted_token_ratio,
                "adaptive_to_fixed_progress_per_flop_ratio": progress_per_flop_ratio,
            },
        },
        "learning_curves": _learning_curves(runs),
        "paired_effect": summary["paired_tau"],
        "direct_interrupted_contrast": summary["direct_interrupted_contrast"],
        "falsifier_results": summary["falsifier_results"],
        "falsifier_labels": {
            "paired_tau_positive": "Adaptive interruption effect improves progress/FLOP",
            "adaptive_retains_progress_per_flop": "Adaptive retains at least 95% of clean progress/FLOP",
            "no_failure_learning_equivalence": "No-failure policy implementations agree within 1%",
            "adaptive_vs_synchronous_progress_per_flop": "Adaptive reaches 95% of synchronous progress/FLOP",
            "adaptive_reaches_target_sooner": "Adaptive reaches the frozen target sooner",
            "adaptive_does_not_diverge": "Adaptive has zero held-out divergences",
        },
        "evaluation_pairs": summary["evaluation_pairs"],
        "run_details": _run_details(result),
        "split": result["split"],
        "dataset": result["dataset"],
        "runtime": result["runtime"],
        "study": result["study"],
        "evidence_boundary": result["result_scope"],
        "interpretation": {
            "denominator_trap": (
                "Fixed restart ends worse but receives a larger progress/FLOP ratio "
                "because it attempts fewer tokens inside the finite horizon."
            ),
            "target_resolution": (
                "The calibration-derived target was crossed by every evaluation arm "
                "at the first 32-tick observation, so ticks-to-target cannot rank them."
            ),
            "valid_control": (
                "Fixed and adaptive no-failure arms are learning-equivalent, so the "
                "interrupted contrast is not an implementation mismatch."
            ),
        },
    }
    if not all(
        math.isfinite(value)
        for value in (
            final_nll_delta,
            attempted_token_ratio,
            progress_per_flop_ratio,
        )
    ):
        raise ValueError("LC1 comparison contains non-finite derived values")
    payload["artifact_sha256"] = _content_hash(payload)
    return payload


def project_e001_learning_result_file(
    result_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    result_file = Path(result_path)
    result = json.loads(result_file.read_text(encoding="utf-8"))
    payload = build_e001_learning_observatory_artifact(
        result,
        source_uri=result_file.as_posix(),
    )
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return payload


__all__ = [
    "E001_LEARNING_OBSERVATORY_SCHEMA",
    "build_e001_learning_observatory_artifact",
    "project_e001_learning_result_file",
]
