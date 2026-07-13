"""Compact three-depth observatory projection for E001-LC3."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence


SCHEMA = "gpu-stack.causal-observatory.e001-equal-work.v1"
RESULT_SCHEMA = "gpu-stack.e001-equal-work-evidence.v1"


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _content_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _validate(result: Mapping[str, Any]) -> None:
    if result.get("schema") != RESULT_SCHEMA:
        raise ValueError("unsupported E001-LC3 result schema")
    expected = result.get("artifact_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("LC3 artifact hash is missing")
    unhashed = dict(result)
    unhashed.pop("artifact_sha256", None)
    actual = _content_hash(unhashed)
    if actual != expected:
        raise ValueError(
            f"LC3 content hash mismatch: expected {expected}, got {actual}"
        )


def _median(values: Sequence[float | int | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    return statistics.median(present) if present else None


def _evaluation_runs(result: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        run for run in result["runs"] if run.get("split") == "evaluation"
    )


def _policy_summary(
    runs: Sequence[Mapping[str, Any]],
    policy_id: str,
    label: str,
) -> dict[str, Any]:
    selected = tuple(run for run in runs if run["policy_id"] == policy_id)
    if not selected:
        raise ValueError(f"LC3 projection has no runs for {policy_id}")
    return {
        "policy_id": policy_id,
        "label": label,
        "run_count": len(selected),
        "final_held_out_nll": _median(
            [run["final_held_out_nll"] for run in selected]
        ),
        "opportunity_ticks": _median(
            [run["opportunity_ticks_to_target"] for run in selected]
        ),
        "attempted_tokens": _median(
            [run["attempted_tokens"] for run in selected]
        ),
        "canonical_tokens": _median(
            [run["canonical_tokens"] for run in selected]
        ),
        "replayed_tokens": _median(
            [run["replayed_tokens"] for run in selected]
        ),
        "discarded_tokens": _median(
            [run["discarded_tokens"] for run in selected]
        ),
        "survivor_redistributed_tokens": _median(
            [run["survivor_redistributed_tokens"] for run in selected]
        ),
        "training_device_energy_j": _median(
            [run["energy"]["idle_subtracted_energy_j"] for run in selected]
        ),
        "local_active_seconds": _median(
            [run["local_active_seconds"] for run in selected]
        ),
        "checkpoint_bytes": _median(
            [run["checkpoint_bytes"] for run in selected]
        ),
        "checkpoint_count": _median(
            [run["checkpoint_count"] for run in selected]
        ),
        "divergence_count": sum(bool(run["diverged"]) for run in selected),
    }


def _curves(runs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    policies = (
        ("fixed-local-checkpoint-restart", "Fixed-local restart"),
        ("adaptive-survivor-continuation", "Adaptive survivor continuation"),
    )
    for policy_id, label in policies:
        selected = tuple(run for run in runs if run["policy_id"] == policy_id)
        by_tick: dict[int, list[float]] = {}
        for run in selected:
            for point in run["curve"]:
                by_tick.setdefault(int(point["wall_tick"]), []).append(
                    float(point["held_out_nll"])
                )
        projected.append(
            {
                "policy_id": policy_id,
                "label": label,
                "points": [
                    {
                        "wall_tick": tick,
                        "median_nll": statistics.median(by_tick[tick]),
                        "minimum_nll": min(by_tick[tick]),
                        "maximum_nll": max(by_tick[tick]),
                        "contributing_runs": len(by_tick[tick]),
                    }
                    for tick in sorted(by_tick)
                ],
            }
        )
    return projected


def _run_details(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "run_id": run["run_id"],
            "split": run["split"],
            "stratum_id": run["stratum_id"],
            "seed": run["seed"],
            "policy_id": run["policy_id"],
            "interrupted": run["interrupted"],
            "failure_schedule": run["failure_schedule"],
            "target_reached": run["target_reached"],
            "final_held_out_nll": run["final_held_out_nll"],
            "opportunity_ticks": run["opportunity_ticks_elapsed"],
            "logical_ticks": run["logical_ticks_completed"],
            "attempted_tokens": run["attempted_tokens"],
            "canonical_tokens": run["canonical_tokens"],
            "replayed_tokens": run["replayed_tokens"],
            "discarded_tokens": run["discarded_tokens"],
            "survivor_redistributed_tokens": run[
                "survivor_redistributed_tokens"
            ],
            "training_device_energy_j": run["energy"][
                "idle_subtracted_energy_j"
            ],
            "local_active_seconds": run["local_active_seconds"],
            "checkpoint_bytes": run["checkpoint_bytes"],
            "checkpoint_count": run["checkpoint_count"],
            "diverged": run["diverged"],
        }
        for run in result["runs"]
    ]


def build_e001_equal_work_observatory_artifact(
    result: Mapping[str, Any],
    *,
    source_uri: str | None = None,
) -> dict[str, Any]:
    _validate(result)
    runs = _evaluation_runs(result)
    summary = result["summary"]
    fixed = _policy_summary(
        runs,
        "fixed-local-checkpoint-restart",
        "Fixed-local restart",
    )
    adaptive = _policy_summary(
        runs,
        "adaptive-survivor-continuation",
        "Adaptive survivor continuation",
    )
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "experiment_id": result["experiment_id"],
        "scenario_id": result["scenario_id"],
        "source_result": {
            "schema": result["schema"],
            "artifact_sha256": result["artifact_sha256"],
            "scenario_sha256": result["scenario_sha256"],
            "engine_source_sha256": result["engine"]["source_sha256"],
            "engine_bundle_sha256": result["engine"]["bundle_sha256"],
            "uri": source_uri,
        },
        "source_lc2_protocol_results": result["source_lc2_protocol_results"],
        "source_learning_result": result["source_learning_result"],
        "source_recovery_result": result["source_recovery_result"],
        "conclusion": {
            "status": summary["conclusion"],
            "candidate_survives_lc3": summary["candidate_survives_lc3"],
            "plain_answer": (
                "Adaptive continuation preserved late-stage learning and reached "
                "the same useful-work frontier with less attempted work and 40 "
                "fewer opportunity ticks at the median. It still failed LC3: "
                "measured training-device energy was too high under the frozen "
                "energy bound."
            ),
            "why_it_failed": (
                "The adaptive/fixed device-energy ratio had median 1.068 and a "
                "90% upper bound of 1.134, above the preregistered 1.05 limit."
            ),
            "next_question": (
                "Which checkpoint and recovery phases create the adaptive energy "
                "penalty, and can dependency-safe power scheduling remove it "
                "without losing the learning, work, or time gains?"
            ),
        },
        "canonical_target": summary["canonical_target"],
        "noninferiority_margin_nll": summary[
            "noninferiority_margin_nll"
        ],
        "policy_comparison": {
            "fixed_interrupted": fixed,
            "adaptive_interrupted": adaptive,
            "derived": {
                "adaptive_minus_fixed_median_final_nll": (
                    float(adaptive["final_held_out_nll"])
                    - float(fixed["final_held_out_nll"])
                ),
                "adaptive_to_fixed_median_energy_ratio": (
                    float(adaptive["training_device_energy_j"])
                    / float(fixed["training_device_energy_j"])
                ),
                "adaptive_to_fixed_checkpoint_byte_ratio": (
                    float(adaptive["checkpoint_bytes"])
                    / float(fixed["checkpoint_bytes"])
                ),
            },
        },
        "learning_curves": _curves(runs),
        "evaluation_pairs": summary["evaluation_pairs"],
        "paired_effects": {
            "adaptive_minus_fixed_nll": summary[
                "paired_adaptive_minus_fixed_nll"
            ],
            "attempted_flop_savings": summary[
                "paired_attempted_flop_savings"
            ],
            "opportunity_tick_savings": summary[
                "paired_opportunity_tick_savings"
            ],
            "adaptive_to_fixed_device_energy_ratio": summary[
                "adaptive_to_fixed_device_energy_ratio"
            ],
        },
        "falsifier_results": summary["falsifier_results"],
        "falsifier_labels": {
            "all_equal_work_pairs_complete": "All six pairs reached identical canonical work",
            "learning_noninferior": "Adaptive final NLL stayed inside the 0.01 noninferiority margin",
            "attempted_flop_saving_positive": "Attempted-FLOP saving interval stayed above zero",
            "attempted_flop_saving_material": "Median attempted-FLOP saving reached 3%",
            "opportunity_tick_saving_material": "Adaptive saved at least 24 ticks and won all six schedules",
            "device_energy_ratio_bounded": "Adaptive device energy stayed within 5% of fixed",
            "calibration_no_failure_exact_equivalence": "No-failure policy controls were exactly equivalent",
            "adaptive_does_not_diverge": "Adaptive had zero held-out divergences",
        },
        "calibration_equivalence": summary["calibration_equivalence"],
        "warm_start": result["warm_start"],
        "mechanics_bridge": result["mechanics_bridge"],
        "run_details": _run_details(result),
        "split": result["split"],
        "dataset": result["dataset"],
        "runtime": result["runtime"],
        "evidence_boundary": result["result_scope"],
        "interpretation": {
            "learning": (
                "Adaptive was slightly worse on final NLL in every stratum, but "
                "the paired 90% upper bound 0.00850 stayed below the frozen 0.01 margin."
            ),
            "work_and_time": (
                "Adaptive removed replay/discard overhead: median attempted-work "
                "saving was 3.03% and opportunity-tick saving was 40."
            ),
            "energy": (
                "Adaptive wrote about 2.76 times as many checkpoint bytes and "
                "used more local active time, making phase-level power attribution "
                "the next causal experiment rather than a scale-up."
            ),
        },
    }
    payload["artifact_sha256"] = _content_hash(payload)
    return payload


def project_e001_equal_work_result_file(
    result_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    result_file = Path(result_path)
    result = json.loads(result_file.read_text(encoding="utf-8"))
    payload = build_e001_equal_work_observatory_artifact(
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
    "SCHEMA",
    "build_e001_equal_work_observatory_artifact",
    "project_e001_equal_work_result_file",
]
