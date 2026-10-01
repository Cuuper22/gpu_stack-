#!/usr/bin/env python
"""Post-hoc evidence re-analysis of every persisted GPUSTACK experiment run.

Reads ONLY persisted artifacts under experiments/*/ (result JSON plus the frozen
scenario JSON that holds the original bootstrap seeds). Writes
analysis/reanalysis/reanalysis-v1.json. No network, no GPU, no git writes.

Run:
    PYTHONPATH=<repo> <venv>/bin/python -B analysis/reanalysis/reanalyze.py

Everything here is labeled post-hoc: none of these analyses was frozen before
the original runs. Original verdict strings are copied verbatim, never edited.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from stats_helpers import (  # noqa: E402
    describe,
    power_to_pass_upper_bound,
    t_interval,
)

REPO = HERE.parents[1]
OUT = HERE / "reanalysis-v1.json"
PROJECT_SEED = 20261001
E1 = REPO / "experiments" / "e001-beyond-one-datacenter"
E2 = REPO / "experiments" / "e002-power-waveform-shaping"
EVAL_BLOCKS = [f"E{i}" for i in range(1, 7)]
FIXED = "fixed-local-checkpoint-restart"
ADAPT = "adaptive-survivor-continuation"

SOURCES: dict[str, dict[str, Any]] = {}
CHECKS: list[dict[str, Any]] = []


# ----------------------------------------------------------------- loading
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(key: str, path: Path) -> Any:
    SOURCES[key] = {
        "path": str(path.relative_to(REPO)),
        "file_sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }
    data = json.loads(path.read_bytes())
    if isinstance(data, dict) and "artifact_sha256" in data:
        SOURCES[key]["artifact_sha256_field"] = data["artifact_sha256"]
    return data


def git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


# --------------------------------------------------------------- utilities
def D(
    name: str,
    values: list[float],
    *,
    null: float = 0.0,
    ratio: bool = False,
    orig_seed: int | None = None,
    stored: dict[str, Any] | None = None,
    note: str | None = None,
    scope: str = "",
) -> dict[str, Any]:
    result = describe(
        values,
        name=f"{scope}:{name}",
        null=null,
        ratio=ratio,
        orig_seed=orig_seed,
        stored=stored,
        project_seed=PROJECT_SEED,
        note=note,
    )
    result["name"] = name
    orig = result.get("bootstrap_median_original_method")
    if orig and "reproduces_stored" in orig:
        CHECKS.append(
            {
                "metric": f"{scope}:{name}",
                "reproduces_stored": orig["reproduces_stored"],
                "max_abs_diff_vs_stored": orig["max_abs_diff_vs_stored"],
            }
        )
    return result


def by(runs: list[dict[str, Any]], *keys: str) -> dict[tuple, dict[str, Any]]:
    return {tuple(r[k] for k in keys): r for r in runs}


def arr(x: Any) -> np.ndarray:
    return np.asarray(x, dtype=np.float64)


def first(values: list[float]) -> float:
    return float(values[0])


# ================================================================== LC3
def analyze_lc3() -> dict[str, Any]:
    d = load("lc3_equal_work", E1 / "results" / "equal-work-v1.json")
    scenario = load("lc3_scenario", E1 / "equal-work-scenario-v1.json")
    seed = int(scenario["bootstrap"]["seed"])
    summ = d["summary"]
    runs = d["runs"]
    idx = by(runs, "stratum_id", "policy_id")
    scope = "LC3"

    def pairs(fn, blocks=EVAL_BLOCKS):
        return [fn(idx[(b, ADAPT)], idx[(b, FIXED)]) for b in blocks]

    nll = pairs(lambda a, f: a["final_held_out_nll"] - f["final_held_out_nll"])
    saving = pairs(
        lambda a, f: (f["attempted_compute_flops"] - a["attempted_compute_flops"])
        / f["attempted_compute_flops"]
    )
    ticks = pairs(lambda a, f: f["opportunity_ticks_elapsed"] - a["opportunity_ticks_elapsed"])
    e_idle = pairs(
        lambda a, f: a["energy"]["idle_subtracted_energy_j"] / f["energy"]["idle_subtracted_energy_j"]
    )
    e_raw = pairs(lambda a, f: a["energy"]["raw_energy_j"] / f["energy"]["raw_energy_j"])
    t_act = pairs(lambda a, f: a["local_active_seconds"] / f["local_active_seconds"])
    t_phys = pairs(lambda a, f: a["physical_seconds"] / f["physical_seconds"])
    ckpt_s = pairs(lambda a, f: a["checkpoint_copy_seconds"] - f["checkpoint_copy_seconds"])
    ckpt_n = pairs(lambda a, f: a["checkpoint_count"] - f["checkpoint_count"])
    samp = pairs(lambda a, f: a["energy"]["sample_count"] / f["energy"]["sample_count"])
    p_raw_a = [idx[(b, ADAPT)]["energy"]["raw_energy_j"] / idx[(b, ADAPT)]["local_active_seconds"] for b in EVAL_BLOCKS]
    p_raw_f = [idx[(b, FIXED)]["energy"]["raw_energy_j"] / idx[(b, FIXED)]["local_active_seconds"] for b in EVAL_BLOCKS]
    act_diff = pairs(lambda a, f: a["local_active_seconds"] - f["local_active_seconds"])

    metrics = {
        "nll_adaptive_minus_fixed": D("nll_adaptive_minus_fixed", nll, orig_seed=seed, stored=summ["paired_adaptive_minus_fixed_nll"], scope=scope),
        "attempted_flop_saving_fraction": D("attempted_flop_saving_fraction", saving, orig_seed=seed + 1, stored=summ["paired_attempted_flop_savings"], scope=scope),
        "opportunity_tick_saving": D("opportunity_tick_saving", ticks, orig_seed=seed + 2, stored=summ["paired_opportunity_tick_savings"], scope=scope),
        "energy_ratio_idle_subtracted_sampled": D("energy_ratio_idle_subtracted_sampled", e_idle, null=1.0, ratio=True, orig_seed=seed + 3, stored=summ["adaptive_to_fixed_device_energy_ratio"], scope=scope),
        "energy_ratio_raw_sampled_post_hoc": D("energy_ratio_raw_sampled_post_hoc", e_raw, null=1.0, ratio=True, scope=scope, note="raw sampled energy only covers sampled spans; post-hoc, not a frozen metric"),
        "metered_active_seconds_ratio": D("metered_active_seconds_ratio", t_act, null=1.0, ratio=True, scope=scope),
        "physical_run_seconds_ratio": D("physical_run_seconds_ratio", t_phys, null=1.0, ratio=True, scope=scope, note="whole run incl. evaluation and idle outage ticks"),
        "metered_active_seconds_difference_adaptive_minus_fixed": D("metered_active_seconds_difference", act_diff, scope=scope),
        "checkpoint_copy_seconds_difference": D("checkpoint_copy_seconds_difference", ckpt_s, scope=scope),
        "checkpoint_count_difference": D("checkpoint_count_difference", ckpt_n, scope=scope),
        "sample_count_ratio": D("sample_count_ratio", samp, null=1.0, ratio=True, scope=scope),
        "mean_raw_power_w_adaptive": D("mean_raw_power_w_adaptive", p_raw_a, scope=scope, note="raw sampled J / metered active s"),
        "mean_raw_power_w_fixed": D("mean_raw_power_w_fixed", p_raw_f, scope=scope, note="raw sampled J / metered active s"),
    }
    # does the original summary reproduce from runs?
    stored_pairs = {p["stratum_id"]: p for p in summ["evaluation_pairs"]}
    run_vs_pairs = max(
        abs(stored_pairs[b]["adaptive_to_fixed_device_energy_ratio"] - e_idle[i])
        for i, b in enumerate(EVAL_BLOCKS)
    )

    # calibration pairs: identical learning path, only checkpoint cadence differs
    cal_ratio = [
        idx[(b, ADAPT)]["energy"]["idle_subtracted_energy_j"] / idx[(b, FIXED)]["energy"]["idle_subtracted_energy_j"]
        for b in ("C1", "C2")
    ]
    cal_active_ratio = [
        idx[(b, ADAPT)]["local_active_seconds"] / idx[(b, FIXED)]["local_active_seconds"] for b in ("C1", "C2")
    ]
    cal_identical = [
        idx[(b, ADAPT)]["final_held_out_nll"] == idx[(b, FIXED)]["final_held_out_nll"] for b in ("C1", "C2")
    ]

    # per-arm run-to-run spread (same arm, same work, different seeds)
    def cv(values):
        v = arr(values)
        return {"n": len(v), "mean": float(v.mean()), "sd": float(v.std(ddof=1)), "cv": float(v.std(ddof=1) / v.mean())}

    spread = {
        "fixed_interrupted_idle_sub_j": cv([idx[(b, FIXED)]["energy"]["idle_subtracted_energy_j"] for b in EVAL_BLOCKS]),
        "adaptive_interrupted_idle_sub_j": cv([idx[(b, ADAPT)]["energy"]["idle_subtracted_energy_j"] for b in EVAL_BLOCKS]),
        "fixed_interrupted_active_s": cv([idx[(b, FIXED)]["local_active_seconds"] for b in EVAL_BLOCKS]),
        "adaptive_interrupted_active_s": cv([idx[(b, ADAPT)]["local_active_seconds"] for b in EVAL_BLOCKS]),
    }
    # sampling resolution
    opt = d["study"]["optimization"]
    segments = int(opt["canonical_target_ticks"]) // int(opt["evaluation_interval_ticks"])
    sample_counts = [r["energy"]["sample_count"] for r in runs if r["split"] == "evaluation"]
    active = [r["local_active_seconds"] for r in runs if r["split"] == "evaluation"]
    resolution = {
        "metered_segments_per_run_inferred": segments,
        "inference": "meter stops and restarts every evaluation_interval_ticks (read from e001_lc3_equal_work.py loop); no thermal pause occurred (all thermal_pause_seconds are 0)",
        "sampler_nominal_spacing_s": 0.1,
        "sampler_spacing_source": "e001_learning_calibration._PowerSampler.sample waits 0.1 s between instantaneous NVML reads (source read, not persisted in artifact)",
        "sample_count_per_run": {"min": int(min(sample_counts)), "max": int(max(sample_counts)), "mean": float(np.mean(sample_counts))},
        "metered_active_seconds_per_run": {"min": float(min(active)), "max": float(max(active)), "mean": float(np.mean(active))},
        "samples_per_segment_mean": float(np.mean(sample_counts)) / segments,
        "segment_seconds_mean": float(np.mean(active)) / segments,
        "persisted_raw_sample_timestamps": False,
        "idle_power_w_single_value_for_all_runs": d["runtime"]["idle_power_w"],
        "idle_estimate_inferred_window_s": "20 reads x 50 ms = about 1 s, i.e. about 2 meter updates at the 0.495 s update period",
        "clamp": "per-segment max(0, raw - idle*span): negative segments are set to 0 (read from source), which biases idle-subtracted energy upward when training power is near idle",
    }

    # gate power: how likely is a 6-pair test to pass 'upper <= 1.05' if the true ratio were exactly 1?
    log_sd = float(np.std(np.log(e_idle), ddof=1))
    power = {
        "log_ratio_sd_observed_lc3": log_sd,
        "pw2_raw_log_ratio_sd_for_comparison": None,  # filled later
        "bar": 1.05,
        "n_pairs": 6,
        "p_pass_if_true_ratio_1.00_lc3_sd": power_to_pass_upper_bound(log_sd, 1.00, 1.05, 6, seed=PROJECT_SEED + 11),
        "p_pass_if_true_ratio_1.02_lc3_sd": power_to_pass_upper_bound(log_sd, 1.02, 1.05, 6, seed=PROJECT_SEED + 12),
        "method": "Monte Carlo 20000 sims, per-pair log ratio ~ Normal(log true, observed sd), pass = t-interval upper bound <= bar; seeded",
    }

    # NLL non-inferiority robustness
    margin = float(d["study"]["calibration"]["noninferiority_margin_nll"])
    fixed_final = [idx[(b, FIXED)]["final_held_out_nll"] for b in ["C1", "C2"] + EVAL_BLOCKS]
    seed_sd = float(np.std(fixed_final, ddof=1))
    ti = t_interval(nll)
    boot = metrics["nll_adaptive_minus_fixed"]["bootstrap_median_original_method"]
    margins = {}
    for m in (0.005, 0.0075, 0.01, 0.015):
        margins[f"{m}"] = {
            "original_bootstrap_median_upper_pass": bool(boot["upper"] <= m),
            "t_upper_pass": bool(ti["upper"] <= m),
            "max_pair_pass": bool(max(nll) <= m),
            "n_pairs_above_margin": int(sum(v > m for v in nll)),
        }
    leave_one_out = {}
    for i, b in enumerate(EVAL_BLOCKS):
        rest = [v for j, v in enumerate(nll) if j != i]
        t = t_interval(rest)
        leave_one_out[f"drop_{b}"] = {"mean": float(np.mean(rest)), "t_upper": t["upper"], "median": float(np.median(rest))}
    nll_robust = {
        "frozen_margin_nll": margin,
        "margin_rule_text": d["study"]["calibration"]["margin_rule"],
        "two_seed_span_used": d["study"]["calibration"]["observed_lc2_fixed_final_nll_span"],
        "two_seed_span_times_2": 2 * d["study"]["calibration"]["observed_lc2_fixed_final_nll_span"],
        "seed_sd_fixed_final_nll_8_seeds": seed_sd,
        "seed_sd_n": len(fixed_final),
        "fixed_final_nll_values_8_seeds": fixed_final,
        "margin_over_seed_sd": margin / seed_sd,
        "t_interval_90_two_sided_of_mean": ti,
        "pairs_above_margin": [{"block": b, "diff": v} for b, v in zip(EVAL_BLOCKS, nll) if v > margin],
        "margin_sensitivity": margins,
        "leave_one_out": leave_one_out,
        "note": "adaptive-minus-fixed is positive in 6 of 6 pairs; the cost is small but systematic, so it is a real tiny penalty rather than noise",
    }
    return {
        "scope": "LC3 equal-canonical-work, 6 held-out fixed/adaptive pairs (n=6) on one RTX 3060 Laptop GPU",
        "original_verdict_verbatim": summ["conclusion"],
        "original_gate_results": summ["falsifier_results"],
        "run_vs_summary_max_abs_diff_energy_ratio": run_vs_pairs,
        "metrics": metrics,
        "calibration_identical_learning_pairs": {
            "final_nll_exactly_equal": cal_identical,
            "energy_ratio_idle_subtracted_adaptive_over_fixed": cal_ratio,
            "active_seconds_ratio": cal_active_ratio,
            "note": "same weights, same tokens; only checkpoint cadence differs. Ratios below 1 here show the sampled-energy noise exceeds the effect.",
        },
        "run_to_run_spread": spread,
        "energy_resolution": resolution,
        "energy_gate_power": power,
        "nll_noninferiority_robustness": nll_robust,
        "bridge_modeled": {
            "evidence_class": d["mechanics_bridge"]["evidence_class"],
            "plain_boundary": d["mechanics_bridge"]["plain_boundary"],
        },
    }


# ================================================================== LC1
def analyze_lc1() -> dict[str, Any]:
    d = load("lc1_learning", E1 / "results" / "learning-calibration-v1.json")
    scenario = load("lc1_scenario", E1 / "learning-scenario-v1.json")
    seed = int(scenario["bootstrap"]["seed"])
    runs = d["runs"]
    idx = by(runs, "stratum_id", "policy_id", "interrupted")
    summ = d["summary"]
    scope = "LC1"
    SYNC = "synchronous-reference"

    def p(b, pol, z):
        return idx[(b, pol, z)]["progress_per_flop"]

    tau = [(p(b, ADAPT, True) - p(b, ADAPT, False)) - (p(b, FIXED, True) - p(b, FIXED, False)) for b in EVAL_BLOCKS]
    direct = [p(b, ADAPT, True) - p(b, FIXED, True) for b in EVAL_BLOCKS]
    retained = [p(b, ADAPT, True) / p(b, ADAPT, False) for b in EVAL_BLOCKS]
    vs_sync = [p(b, ADAPT, True) / p(b, SYNC, False) for b in EVAL_BLOCKS]
    metrics = {
        "tau_progress_per_flop_diff_in_diff": D("tau", tau, orig_seed=seed, stored=summ["paired_tau"], scope=scope),
        "direct_interrupted_progress_per_flop_difference": D("direct", direct, orig_seed=seed + 1, stored=summ["direct_interrupted_contrast"], scope=scope),
        "adaptive_retained_progress_ratio": D("retained", retained, null=1.0, ratio=True, orig_seed=seed + 2, stored=summ["adaptive_retained_progress_per_flop"], scope=scope),
        "adaptive_vs_synchronous_progress_ratio": D("vs_sync", vs_sync, null=1.0, ratio=True, orig_seed=seed + 4, stored=summ["adaptive_vs_synchronous_progress_per_flop"], scope=scope),
    }
    # post-hoc: what the per-FLOP metric hid
    nll_diff = [idx[(b, ADAPT, True)]["final_held_out_nll"] - idx[(b, FIXED, True)]["final_held_out_nll"] for b in EVAL_BLOCKS]
    att_ratio = [idx[(b, FIXED, True)]["attempted_tokens"] / idx[(b, ADAPT, True)]["attempted_tokens"] for b in EVAL_BLOCKS]
    can_ratio = [idx[(b, FIXED, True)]["canonical_tokens"] / idx[(b, ADAPT, True)]["canonical_tokens"] for b in EVAL_BLOCKS]
    equal_compute = []
    for b in EVAL_BLOCKS:
        f = idx[(b, FIXED, True)]
        a = idx[(b, ADAPT, True)]
        tokens = [c["attempted_tokens"] for c in a["curve"]]
        nlls = [c["held_out_nll"] for c in a["curve"]]
        equal_compute.append(float(np.interp(f["attempted_tokens"], tokens, nlls)) - f["final_held_out_nll"])
    metrics["post_hoc_nll_adaptive_minus_fixed_interrupted_final"] = D("nll_final_diff", nll_diff, scope=scope, note="adaptive finishes all 256 canonical ticks, fixed does not (horizon is fixed in opportunity ticks)")
    metrics["post_hoc_fixed_over_adaptive_attempted_token_ratio"] = D("attempted_ratio", att_ratio, null=1.0, ratio=True, scope=scope)
    metrics["post_hoc_fixed_over_adaptive_canonical_token_ratio"] = D("canonical_ratio", can_ratio, null=1.0, ratio=True, scope=scope)
    metrics["post_hoc_nll_adaptive_at_equal_attempted_tokens_minus_fixed_final"] = D(
        "nll_equal_attempted_compute", equal_compute, scope=scope,
        note="adaptive curve linearly interpolated (8 points, every 32 ticks) at fixed's attempted tokens; coarse, post-hoc",
    )
    e_int = [idx[(b, ADAPT, True)]["energy"]["idle_subtracted_energy_j"] / idx[(b, FIXED, True)]["energy"]["idle_subtracted_energy_j"] for b in EVAL_BLOCKS]
    e_tok = [
        (idx[(b, ADAPT, True)]["energy"]["idle_subtracted_energy_j"] / idx[(b, ADAPT, True)]["attempted_tokens"])
        / (idx[(b, FIXED, True)]["energy"]["idle_subtracted_energy_j"] / idx[(b, FIXED, True)]["attempted_tokens"])
        for b in EVAL_BLOCKS
    ]
    metrics["post_hoc_energy_ratio_idle_subtracted_sampled_adaptive_over_fixed_interrupted"] = D(
        "energy_ratio_interrupted", e_int, null=1.0, ratio=True, scope=scope,
        note="from-scratch regime where adaptive does 12.5% more attempted work; sampled 100 ms NVML idle-subtracted; context only",
    )
    metrics["post_hoc_energy_per_attempted_token_ratio_adaptive_over_fixed_interrupted"] = D(
        "energy_per_token_ratio_interrupted", e_tok, null=1.0, ratio=True, scope=scope
    )
    # target / first-crossing resolution
    target = summ["target"]["held_out_nll"]
    crossing = []
    for r in runs:
        if r["split"] != "evaluation":
            continue
        c32 = next(c for c in r["curve"] if c["logical_tick"] == 32)
        l0 = r["curve"][0]["held_out_nll"]
        crossing.append(
            {
                "run_id": r["run_id"],
                "nll_at_first_observation_tick_32": c32["held_out_nll"],
                "target": target,
                "margin_below_target_at_first_observation": target - c32["held_out_nll"],
                "fraction_of_total_improvement_done_by_tick_32": (l0 - c32["held_out_nll"]) / (l0 - r["final_held_out_nll"]),
                "first_observation_is_tick": 32,
            }
        )
    frac = [c["fraction_of_total_improvement_done_by_tick_32"] for c in crossing]
    # no-failure fixed vs adaptive exact equivalence
    return {
        "scope": "LC1 survivor-continuation calibration, from-scratch 256-tick runs, 6 held-out strata (n=6)",
        "original_verdict_verbatim": summ["conclusion"],
        "original_gate_results": summ["falsifier_results"],
        "target": summ["target"],
        "metrics": metrics,
        "first_crossing_resolution": {
            "evaluation_interval_ticks": d["study"]["optimization"]["evaluation_interval_ticks"],
            "all_runs_first_cross_at_tick": sorted({r["logical_ticks_to_target"] for r in runs if r["split"] == "evaluation" and r["target_reached"]}),
            "target_is_fraction_of_improvement": 0.75,
            "fraction_of_total_improvement_done_by_tick_32": {"min": float(min(frac)), "max": float(max(frac))},
            "n_evaluation_runs": len(crossing),
            "per_run_first_observation_margin_min": float(min(c["margin_below_target_at_first_observation"] for c in crossing)),
        },
    }


# ================================================================== LC2
def analyze_lc2() -> dict[str, Any]:
    v1 = load("lc2_v1", E1 / "results" / "quality-target-v1.json")
    v2 = load("lc2_v2", E1 / "results" / "quality-target-v2.json")
    w1 = v1["warm_start"]["late_window"]
    w2 = v2["warm_start"]["late_window"]
    runs = v2["runs"]
    target = v2["summary"]["target"]["held_out_nll"]
    per_run = []
    for r in runs:
        ticks = [c["logical_tick"] for c in r["curve"]]
        nlls = np.array([c["held_out_nll"] for c in r["curve"]])
        sds = np.array([c["held_out_nll_standard_deviation"] for c in r["curve"]])
        first_cross = next(t for t, v in zip(ticks, nlls) if v <= target)
        later = [(t, v) for t, v in zip(ticks, nlls) if t > first_cross]
        above_later = [t for t, v in later if v > target]
        diffs = np.diff(nlls[2:])
        per_run.append(
            {
                "run_id": r["run_id"],
                "first_crossing_tick": first_cross,
                "evaluations_after_first_crossing": len(later),
                "evaluations_after_first_crossing_that_are_above_target": len(above_later),
                "last_tick_above_target": max([t for t, v in zip(ticks, nlls) if v > target] or [None]),
                "successive_eval_difference_sd": float(diffs.std(ddof=1)),
                "total_nll_drift_tick0_to_256": float(nlls[0] - nlls[-1]),
                "drift_over_successive_diff_sd": float((nlls[0] - nlls[-1]) / diffs.std(ddof=1)),
                "per_eval_standard_error_over_64_batches_mean": float(np.mean(sds) / math.sqrt(64)),
                "fraction_of_evals_at_or_below_target_in_ticks_192_to_288": float(
                    np.mean([v <= target for t, v in zip(ticks, nlls) if 192 <= t <= 288])
                ),
            }
        )
    return {
        "scope": "LC2 quality-to-target protocol stages; no held-out policy comparison exists (n=0 pairs)",
        "original_verdict_verbatim": {
            "v1": v1["summary"]["conclusion"],
            "v2": v2["summary"]["conclusion"],
        },
        "v1_warm_gate": {
            "nll_improvement_last_256_ticks": w1["nll_improvement"],
            "frozen_maximum": w1["maximum_nll_improvement"],
            "ratio_to_maximum": w1["nll_improvement"] / w1["maximum_nll_improvement"],
            "checkpoint_ticks": v1["warm_start"]["ticks"],
        },
        "v2_warm_gate": {
            "nll_improvement_last_256_ticks": w2["nll_improvement"],
            "frozen_maximum": w2["maximum_nll_improvement"],
            "passed": w2["late_stage_gate_passed"],
            "checkpoint_ticks": v2["warm_start"]["ticks"],
        },
        "v2_target": target,
        "v2_frozen_window_ticks": [192, 288],
        "v2_calibration_curve_analysis": per_run,
        "v2_calibration_first_crossings": v2["summary"]["calibration_first_crossings"],
        "reading": "At the late-stage plateau the 256-tick drift in held-out NLL is about as large as tick-to-tick evaluation wobble, so a first-crossing time is set by noise. The protocol check that caught this is a valid check.",
    }


# ================================================================== PW1 / PW2
def pw_blocks(runs, field_fn, arms="ABCD"):
    idx = by(runs, "block_id", "arm_code")
    return {a: arr([field_fn(idx[(b, a)]) for b in EVAL_BLOCKS]) for a in arms}


def meter_diagnostics_pw1(d: dict[str, Any]) -> dict[str, Any]:
    gaps: list[float] = []
    levels = []
    train_power = []
    drift = []
    for r in d["runs"]:
        pts = r["telemetry_trace"]["points"]
        t = arr([p["timestamp"] for p in pts])
        pw = arr([p["power_w"] for p in pts])
        change = np.nonzero(np.diff(pw) != 0.0)[0]
        gaps.extend(np.diff(t[change + 1]).tolist())
        a0 = r["telemetry_trace"]["active_start_seconds"]
        a1 = r["telemetry_trace"]["active_end_seconds"]
        win = (t >= a0) & (t <= a1)
        train_power.append(float(pw[win].mean()))
        levels.append(float(pw[win].std(ddof=1)))
        drift.append(r["idle_baseline"]["post_power_w"] - r["idle_baseline"]["pre_power_w"])
    g = arr(gaps)
    return {
        "n_runs": len(d["runs"]),
        "requested_poll_s": d["runs"][0]["telemetry_trace"]["poll_seconds"],
        "median_poll_spacing_s": float(np.median(np.diff(arr([p["timestamp"] for p in d["runs"][0]["telemetry_trace"]["points"]])))),
        "meter_value_change_gap_s": {"n": int(len(g)), "median": float(np.median(g)), "mean": float(g.mean()), "p10": float(np.percentile(g, 10)), "p90": float(np.percentile(g, 90))},
        "artifact_effective_update_period_s": d["logger_calibration"]["effective_update_period_seconds"],
        "mean_instantaneous_power_in_training_window_w": {"mean_over_runs": float(np.mean(train_power)), "within_run_sd_mean": float(np.mean(levels))},
        "idle_baseline_pre_to_post_drift_w": {"median_abs": float(np.median(np.abs(drift))), "max_abs": float(np.max(np.abs(drift)))},
        "idle_baseline_mean_w": float(np.mean([(r["idle_baseline"]["pre_power_w"] + r["idle_baseline"]["post_power_w"]) / 2 for r in d["runs"]])),
    }


def analyze_pw1() -> dict[str, Any]:
    d = load("pw1_checkpoint_power", E2 / "results" / "checkpoint-power-v1.json")
    seed = int(d["study"]["estimands"]["paired_interval"]["seed"])
    s = d["summary"]
    scope = "PW1"
    from_summary = {
        "primary_total_interaction": (0, s["primary_total_interaction"]),
        "checkpoint_related_interaction": (30, s["checkpoint_related_interaction"]),
        "scale_free_interaction_sensitivity": (31, s["scale_free_interaction_sensitivity"]),
        "sparse_continuation_nll_difference": (40, s["sparse_continuation_salvage"]["nll_difference"]),
        "sparse_continuation_attempted_flop_saving": (41, s["sparse_continuation_salvage"]["attempted_flop_saving_fraction"]),
        "sparse_continuation_tick_saving": (42, s["sparse_continuation_salvage"]["opportunity_tick_saving"]),
        "sparse_continuation_energy_ratio_C_over_A": (43, s["sparse_continuation_salvage"]["device_energy_ratio"]),
        "lc3_corner_energy_ratio_D_over_A": (44, s["lc3_corner_reproduction"]["dense_continue_to_sparse_restart_energy_ratio"]),
    }
    metrics = {}
    for name, (off, stored) in from_summary.items():
        is_ratio = "ratio" in name
        metrics[name] = D(name, stored["values"], null=1.0 if is_ratio else 0.0, ratio=is_ratio, orig_seed=seed + off, stored=stored, scope=scope)
    runs = d["runs"]
    energy = lambda r: r["idle_subtracted_gpu_board_energy_j"]  # noqa: E731
    raw = lambda r: r["total_gpu_board_energy_j"]  # noqa: E731
    active = lambda r: r["local_active_seconds"]  # noqa: E731
    e = pw_blocks(runs, energy)
    rr = pw_blocks(runs, raw)
    ac = pw_blocks(runs, active)
    metrics["post_hoc_raw_total_energy_ratio_D_over_A"] = D("raw_D_over_A", list(rr["D"] / rr["A"]), null=1.0, ratio=True, scope=scope)
    metrics["post_hoc_raw_total_energy_ratio_C_over_A"] = D("raw_C_over_A", list(rr["C"] / rr["A"]), null=1.0, ratio=True, scope=scope)
    metrics["post_hoc_active_seconds_ratio_D_over_A"] = D("active_D_over_A", list(ac["D"] / ac["A"]), null=1.0, ratio=True, scope=scope)
    diag = meter_diagnostics_pw1(d)
    mv = d["measurement_validity"]
    return {
        "scope": "PW1 checkpoint-power 2x2 factorial, 32 runs, 6 eval blocks (n=6), 20 ms polling of instantaneous NVML power",
        "original_verdict_verbatim": s["conclusion"],
        "invalidators_true": [k for k, v in mv["invalidators"].items() if v],
        "metrics": metrics,
        "meter_diagnostics": diag,
        "idle_subtracted_arm_means_j": {a: float(e[a].mean()) for a in "ABCD"},
        "raw_arm_means_j": {a: float(rr[a].mean()) for a in "ABCD"},
        "reading": "The artifact marks itself measurement_invalid. Its energy ratios (0.79 and 0.82) differ from LC3 (1.07) and PW2 (1.02) for the same contrast, which sizes the instantaneous-meter noise.",
    }


def analyze_pw2(pw1_scope_vals: dict[str, Any], lc3_vals: dict[str, Any]) -> dict[str, Any]:
    d = load("pw2_checkpoint_energy", E2 / "results" / "checkpoint-energy-v2.json")
    seed = int(d["study"]["estimands"]["paired_interval"]["seed"])
    s = d["summary"]
    runs = d["runs"]
    scope = "PW2"
    out_m: dict[str, Any] = {}
    sm = {
        "primary_total_interaction_j_per_token": (0, s["primary_total_interaction"], False),
        "checkpoint_related_group_interaction_j_per_token": (30, s["checkpoint_related_interaction"], False),
        "scale_free_interaction_sensitivity": (31, s["scale_free_interaction_sensitivity"], False),
        "penalty_removed_fraction": (32, s["penalty_removed_fraction"], False),
        "sparse_continuation_nll_difference": (40, s["sparse_continuation_salvage"]["nll_difference"], False),
        "sparse_continuation_attempted_flop_saving": (41, s["sparse_continuation_salvage"]["attempted_flop_saving_fraction"], False),
        "sparse_continuation_tick_saving": (42, s["sparse_continuation_salvage"]["opportunity_tick_saving"], False),
        "sparse_continuation_energy_ratio_C_over_A": (43, s["sparse_continuation_salvage"]["device_energy_ratio"], True),
        "lc3_corner_energy_ratio_D_over_A": (44, s["lc3_corner_reproduction"]["dense_continue_to_sparse_restart_energy_ratio"], True),
        "idle_subtracted_interaction_sensitivity_j_per_token": (70, s["idle_subtracted_interaction_sensitivity"], False),
    }
    for name, (off, stored, is_ratio) in sm.items():
        out_m[name] = D(name, stored["values"], null=1.0 if is_ratio else 0.0, ratio=is_ratio, orig_seed=seed + off, stored=stored, scope=scope)
    phases = [
        "canonical-healthy-compute", "replay-compute", "survivor-redistributed-compute",
        "model-optimizer-merge", "checkpoint-snapshot", "checkpoint-restore",
        "rejoin-state-transfer", "post-rejoin-sync", "runtime-control-remainder",
    ]
    for i, ph in enumerate(phases):
        stored = s["phase_interactions"][ph]
        out_m[f"phase_interaction__{ph}"] = D(f"phase_interaction__{ph}", stored["values"], orig_seed=seed + 10 + i, stored=stored, scope=scope)

    idx = by(runs, "block_id", "arm_code")
    tokens = 524288.0
    raw = pw_blocks(runs, lambda r: r["raw_run_energy_j"])
    sens = pw_blocks(runs, lambda r: r["idle_subtracted_energy_j_sensitivity"])
    act = pw_blocks(runs, lambda r: r["local_active_seconds"])
    mislabel = float(max(abs(r["idle_subtracted_gpu_board_energy_j"] - r["raw_run_energy_j"]) for r in runs))
    out_m["post_hoc_raw_energy_ratio_D_over_A"] = D("raw_D_over_A", list(raw["D"] / raw["A"]), null=1.0, ratio=True, scope=scope)
    out_m["post_hoc_raw_energy_ratio_C_over_A"] = D("raw_C_over_A", list(raw["C"] / raw["A"]), null=1.0, ratio=True, scope=scope)
    out_m["post_hoc_raw_energy_ratio_D_over_C"] = D("raw_D_over_C", list(raw["D"] / raw["C"]), null=1.0, ratio=True, scope=scope, note="cost of dense vs sparse checkpoints under continuation")
    out_m["post_hoc_raw_energy_ratio_B_over_A"] = D("raw_B_over_A", list(raw["B"] / raw["A"]), null=1.0, ratio=True, scope=scope, note="dense vs sparse under restart")
    out_m["post_hoc_idle_subtracted_ratio_D_over_A"] = D("idle_sub_D_over_A", list(sens["D"] / sens["A"]), null=1.0, ratio=True, scope=scope, note="uses idle_subtracted_energy_j_sensitivity; energy above idle is only 21-41 J per run")
    out_m["post_hoc_idle_subtracted_ratio_C_over_A"] = D("idle_sub_C_over_A", list(sens["C"] / sens["A"]), null=1.0, ratio=True, scope=scope)
    out_m["post_hoc_active_seconds_ratio_D_over_A"] = D("active_D_over_A", list(act["D"] / act["A"]), null=1.0, ratio=True, scope=scope)
    out_m["post_hoc_active_seconds_ratio_C_over_A"] = D("active_C_over_A", list(act["C"] / act["A"]), null=1.0, ratio=True, scope=scope)

    # recompute interactions from runs and compare to artifact
    inter_total, inter_phase = [], {ph: [] for ph in phases}
    removed_num, removed_den = [], []
    for b in EVAL_BLOCKS:
        arms = {a: idx[(b, a)] for a in "ABCD"}
        energy = {a: arms[a]["idle_subtracted_gpu_board_energy_j"] / tokens for a in "ABCD"}
        inter_total.append((energy["D"] - energy["C"]) - (energy["B"] - energy["A"]))
        for ph in phases:
            v = {a: arms[a]["phase_metrics"][ph]["idle_subtracted_energy_j_per_canonical_token"] for a in "ABCD"}
            inter_phase[ph].append((v["D"] - v["C"]) - (v["B"] - v["A"]))
        removed_num.append(arms["D"]["idle_subtracted_gpu_board_energy_j"] - arms["C"]["idle_subtracted_gpu_board_energy_j"])
        removed_den.append(arms["D"]["idle_subtracted_gpu_board_energy_j"] - arms["A"]["idle_subtracted_gpu_board_energy_j"])
    diff_total = max(abs(a - b) for a, b in zip(inter_total, s["primary_total_interaction"]["values"]))
    sum_phase = np.sum([inter_phase[ph] for ph in phases], axis=0)
    closure = float(np.max(np.abs(sum_phase - np.array(inter_total))))
    recomputed_ok = diff_total < 1e-12
    medians = {ph: float(np.median(inter_phase[ph])) for ph in phases}
    means = {ph: float(np.mean(inter_phase[ph])) for ph in phases}
    total_mean = float(np.mean(inter_total))
    total_median = float(np.median(inter_total))
    shares_mean = {ph: means[ph] / total_mean for ph in phases}
    group_phases = ["model-optimizer-merge", "checkpoint-snapshot", "checkpoint-restore", "rejoin-state-transfer", "post-rejoin-sync"]
    group_mean = float(np.sum([means[ph] for ph in group_phases]))
    # phase tables
    phase_means = {}
    for a in "ABCD":
        phase_means[a] = {
            ph: {
                "mean_energy_j": float(np.mean([idx[(b, a)]["phase_energy_j"][ph] for b in EVAL_BLOCKS])),
                "mean_duration_s": float(np.mean([idx[(b, a)]["phase_metrics"][ph]["duration_seconds"] for b in EVAL_BLOCKS])),
            }
            for ph in phases
        }
    mean_power = {a: float(np.mean(raw[a] / act[a])) for a in "ABCD"}
    dense_effect = {
        regime: {
            ph: {
                "energy_j": phase_means[dense][ph]["mean_energy_j"] - phase_means[sparse][ph]["mean_energy_j"],
                "duration_s": phase_means[dense][ph]["mean_duration_s"] - phase_means[sparse][ph]["mean_duration_s"],
            }
            for ph in phases
        }
        for regime, (dense, sparse) in {"continue_D_minus_C": ("D", "C"), "restart_B_minus_A": ("B", "A")}.items()
    }
    dense_effect_total = {
        "continue_D_minus_C_raw_energy_j": float(raw["D"].mean() - raw["C"].mean()),
        "restart_B_minus_A_raw_energy_j": float(raw["B"].mean() - raw["A"].mean()),
        "continue_D_minus_C_active_s": float(act["D"].mean() - act["C"].mean()),
        "restart_B_minus_A_active_s": float(act["B"].mean() - act["A"].mean()),
    }
    idle_w = float(np.mean([(r["idle_baseline"]["pre_power_w"] + r["idle_baseline"]["post_power_w"]) / 2 for r in runs]))
    attribution = {
        "recomputed_primary_total_matches_artifact": recomputed_ok,
        "max_abs_diff_total": float(diff_total),
        "sum_of_phase_interactions_equals_total_max_abs_diff": closure,
        "interaction_median_j_per_token_by_phase": medians,
        "interaction_mean_j_per_token_by_phase": means,
        "total_interaction_mean": total_mean,
        "total_interaction_median": total_median,
        "share_of_mean_total_by_phase": shares_mean,
        "checkpoint_related_group_definition": "merge + snapshot + restore + rejoin-state-transfer + post-rejoin-sync (replay compute is NOT in the group, from scenario estimands)",
        "checkpoint_related_group_mean": group_mean,
        "checkpoint_related_group_share_of_total_mean": group_mean / total_mean,
        "replay_compute_share_of_total_mean": shares_mean["replay-compute"],
        "snapshot_share_of_total_mean": shares_mean["checkpoint-snapshot"],
        "healthy_compute_share_of_total_mean": shares_mean["canonical-healthy-compute"],
        "replay_over_snapshot_ratio_of_medians": medians["replay-compute"] / medians["checkpoint-snapshot"],
        "replay_over_snapshot_ratio_of_means": means["replay-compute"] / means["checkpoint-snapshot"],
        "replay_minus_snapshot_per_block": [r - c for r, c in zip(inter_phase["replay-compute"], inter_phase["checkpoint-snapshot"])],
        "blocks_where_replay_exceeds_snapshot": int(sum(r > c for r, c in zip(inter_phase["replay-compute"], inter_phase["checkpoint-snapshot"]))),
        "interaction_definition": "(D - C) - (B - A) per canonical token; A sparse-restart, B dense-restart, C sparse-continue, D dense-continue",
        "plain": "Under restart, dense checkpoints save replay work; under continuation there is no replay, so dense checkpoints are pure cost. The interaction compares those two, so replay compute (a saving under restart) is the largest single term. Snapshot writing is the next largest.",
    }
    penalty = {
        "numerator_D_minus_C_j": removed_num,
        "denominator_D_minus_A_j": removed_den,
        "fraction_values_recomputed": [n / m if m > 0 else None for n, m in zip(removed_num, removed_den)],
        "stored_values": s["penalty_removed_fraction"]["values"],
        "n_blocks_with_positive_denominator": int(sum(m > 0 for m in removed_den)),
        "min_positive_denominator_j": float(min(m for m in removed_den if m > 0)),
        "stored_median": s["penalty_removed_fraction"]["median"],
        "stored_interval": [s["penalty_removed_fraction"]["lower_bound"], s["penalty_removed_fraction"]["upper_bound"]],
        "reading": "A 'fraction removed' above 1 is not a physical fraction. The denominator (D - A) is a few joules out of ~160 J, so the ratio is unstable. The gate (median >= 0.5) cannot discriminate.",
    }
    # per-run counter resolution
    resolution = {
        "meter": d["measurement_validity"]["meter"],
        "effective_update_period_s": d["logger_calibration"]["effective_update_period_seconds"],
        "updates_per_eval_arm": {"min": int(min(r["effective_power_update_count"] for r in runs if r["split"] == "evaluation")), "max": int(max(r["effective_power_update_count"] for r in runs if r["split"] == "evaluation"))},
        "mean_raw_run_energy_j": float(np.mean([r["raw_run_energy_j"] for r in runs])),
        "mean_idle_baseline_w": idle_w,
        "mean_power_w_by_arm": mean_power,
        "idle_share_of_raw_energy_estimate": float(np.mean([r["raw_run_energy_j"] - r["idle_subtracted_energy_j_sensitivity"] for r in runs]) / np.mean([r["raw_run_energy_j"] for r in runs])),
        "mean_energy_above_idle_j": float(np.mean([r["idle_subtracted_energy_j_sensitivity"] for r in runs])),
        "idle_subtracted_gpu_board_energy_j_field_equals_raw_max_abs_diff": mislabel,
        "label_warning": "In PW2 the field named idle_subtracted_gpu_board_energy_j holds RAW cumulative energy (max abs diff vs raw_run_energy_j above). The primary, salvage ratio and LC3-corner ratio are therefore on raw energy; the LC3 bar of 1.05 was set on idle-subtracted energy.",
    }
    # cross-meter comparison for the same contrast (dense continue vs sparse restart)
    cross = {
        "LC3_idle_subtracted_sampled_100ms_adaptive_over_fixed": lc3_vals["energy_ratio_idle_subtracted_sampled"],
        "PW1_idle_subtracted_sampled_20ms_D_over_A_invalid_meter": pw1_scope_vals["lc3_corner_energy_ratio_D_over_A"],
        "PW2_raw_cumulative_counter_D_over_A": out_m["lc3_corner_energy_ratio_D_over_A"],
        "PW2_idle_subtracted_sensitivity_D_over_A": out_m["post_hoc_idle_subtracted_ratio_D_over_A"],
        "PW2_active_seconds_D_over_A": out_m["post_hoc_active_seconds_ratio_D_over_A"],
        "LC3_active_seconds_adaptive_over_fixed": lc3_vals["metered_active_seconds_ratio"],
    }
    cross_summary = {
        k: {"median": v["median"], "mean": v["mean"], "min": v["min"], "max": v["max"]}
        for k, v in cross.items()
    }
    pw2_log_sd = float(np.std(np.log(raw["D"] / raw["A"]), ddof=1))
    power = {
        "pw2_raw_D_over_A_log_sd": pw2_log_sd,
        "p_pass_1.05_if_true_1.00_pw2_sd": power_to_pass_upper_bound(pw2_log_sd, 1.00, 1.05, 6, seed=PROJECT_SEED + 21),
        "p_pass_1.05_if_true_1.02_pw2_sd": power_to_pass_upper_bound(pw2_log_sd, 1.02, 1.05, 6, seed=PROJECT_SEED + 22),
        "p_pass_1.05_if_true_1.05_pw2_sd": power_to_pass_upper_bound(pw2_log_sd, 1.05, 1.05, 6, seed=PROJECT_SEED + 23),
    }
    return {
        "scope": "PW2 checkpoint-energy 2x2 factorial, same design as PW1, NVML cumulative energy counter, 6 eval blocks (n=6)",
        "original_verdict_verbatim": s["conclusion"],
        "metrics": out_m,
        "mechanism_attribution": attribution,
        "penalty_removed_fraction_diagnostics": penalty,
        "measurement": resolution,
        "arm_phase_means": phase_means,
        "dense_minus_sparse_by_phase_mean_over_6_blocks": dense_effect,
        "dense_minus_sparse_totals": dense_effect_total,
        "arm_raw_energy_mean_j": {a: float(raw[a].mean()) for a in "ABCD"},
        "arm_active_seconds_mean": {a: float(act[a].mean()) for a in "ABCD"},
        "cross_meter_same_contrast": cross_summary,
        "cross_meter_values": {k: v["values"] for k, v in cross.items()},
        "gate_power_pw2": power,
        "meter_idle_and_session_levels": {"pw2_idle_w": idle_w},
    }


# ================================================================== SC1
def analyze_sc1() -> dict[str, Any]:
    d = load("sc1_semantic_consistency", E1 / "results" / "semantic-consistency-v1.json")
    scenario = load("sc1_scenario", E1 / "semantic-consistency-scenario-v1.json")
    seed = int(scenario["uncertainty"]["paired_interval"]["seed"])
    runs = d["runs"]
    idx = by(runs, "family_or_stratum_id", "policy_id")
    fams = [f["family_id"] for f in d["evaluation"]["family_results"]]
    cal = d["calibration"]["stratum_ids"]
    summ = d["summary"]["paired_effect_intervals"]
    scope = "SC1"
    SYNC, FWD, DLY, PER, ADP = "synchronous_restart", "exact_forward_recovery", "delayed_one_step", "periodic_local", "observable_adaptive"

    def fin(f, p):
        return idx[(f, p)]["final_held_out_nll"]

    def pay(f, p):
        return idx[(f, p)]["modeled_infrastructure"]["inter_site_payload_bytes"]

    def tim(f, p):
        return idx[(f, p)]["modeled_infrastructure"]["completion_seconds"]

    nll = [fin(f, ADP) - fin(f, PER) for f in fams]
    payload = [pay(f, ADP) / pay(f, PER) for f in fams]
    comp = [tim(f, ADP) / tim(f, PER) for f in fams]
    oracle = {fr["family_id"]: fr["oracle"] for fr in d["evaluation"]["family_results"]}
    regret = [
        tim(f, ADP) / oracle[f]["stress_only_completion_seconds"] - 1.0
        for f in fams
        if oracle[f]["post_selection_learning_valid"]
    ]
    metrics = {
        "adaptive_minus_periodic_local_nll": D("nll", nll, orig_seed=seed, stored=summ["adaptive_minus_comparator_final_nll"], scope=scope),
        "adaptive_over_periodic_local_payload_ratio": D("payload", payload, null=1.0, ratio=True, orig_seed=seed + 1, stored=summ["adaptive_to_comparator_inter_site_payload_ratio"], scope=scope),
        "adaptive_over_periodic_local_completion_ratio": D("completion", comp, null=1.0, ratio=True, orig_seed=seed + 2, stored=summ["adaptive_to_comparator_modeled_completion_time_ratio"], scope=scope),
        "adaptive_normalized_oracle_regret": D("regret", regret, orig_seed=seed + 5, stored=summ["adaptive_normalized_oracle_regret"], scope=scope, note="n=4 families; the other two have no valid hindsight schedule"),
    }
    # extra comparisons
    nll_vs_sync = [fin(f, ADP) - fin(f, SYNC) for f in fams]
    comp_vs_sync = [tim(f, ADP) / tim(f, SYNC) for f in fams]
    pay_vs_sync = [pay(f, ADP) / pay(f, SYNC) for f in fams]
    metrics["post_hoc_adaptive_minus_sync_nll"] = D("nll_vs_sync", nll_vs_sync, scope=scope)
    metrics["post_hoc_adaptive_over_sync_completion_ratio"] = D("completion_vs_sync", comp_vs_sync, null=1.0, ratio=True, scope=scope)
    metrics["post_hoc_adaptive_over_sync_payload_ratio"] = D("payload_vs_sync", pay_vs_sync, null=1.0, ratio=True, scope=scope)
    per_vs_sync_eval = [fin(f, PER) - fin(f, SYNC) for f in fams]
    per_vs_sync_cal = [fin(f, PER) - fin(f, SYNC) for f in cal]
    metrics["post_hoc_periodic_local_minus_sync_nll_evaluation"] = D("per_vs_sync_eval", per_vs_sync_eval, scope=scope)
    metrics["post_hoc_periodic_local_minus_sync_nll_calibration"] = D("per_vs_sync_cal", per_vs_sync_cal, scope=scope)
    metrics["post_hoc_periodic_local_minus_sync_nll_all_10"] = D("per_vs_sync_all", per_vs_sync_cal + per_vs_sync_eval, scope=scope, note="10 families, one seed each")
    metrics["post_hoc_delayed_minus_sync_nll_all_10"] = D("delayed_vs_sync_all", [fin(f, DLY) - fin(f, SYNC) for f in cal + fams], scope=scope)
    metrics["post_hoc_periodic_over_sync_payload_ratio_all_10"] = D("per_payload_vs_sync", [pay(f, PER) / pay(f, SYNC) for f in cal + fams], null=1.0, ratio=True, scope=scope)
    metrics["post_hoc_periodic_over_sync_completion_ratio_all_10"] = D("per_time_vs_sync", [tim(f, PER) / tim(f, SYNC) for f in cal + fams], null=1.0, ratio=True, scope=scope)
    # gate 0.20 arithmetic
    per_action = defaultdict(list)
    for r in runs:
        for e in r.get("epoch_trace") or []:
            b = sum(w["payload_bytes"] for w in e["wan_events"])
            per_action[(e["action"], len(e["stress"]["active_sites"]))].append(b)
    table = {f"{a}|active_sites={n}": {"epochs": len(v), "mean_bytes_per_epoch": float(np.mean(v)), "min_bytes_per_epoch": float(min(v))} for (a, n), v in sorted(per_action.items())}
    periodic2 = float(np.mean(per_action[("periodic_local_updates", 2)]))
    other2 = min(float(np.mean(per_action[(a, 2)])) for a in ("exact_sync", "compute_and_queue_one_step_delayed_update"))
    gate = {
        "frozen_bound": d["falsifiers"]["definitions"]["adaptive_to_best_fixed_inter_site_payload_ratio_upper_bound_lte"],
        "observed_min_ratio_over_6_families": float(min(payload)),
        "observed_max_ratio_over_6_families": float(max(payload)),
        "families_with_ratio_below_1": int(sum(x < 1.0 for x in payload)),
        "bytes_per_epoch_by_action_and_membership": table,
        "periodic_local_mean_bytes_per_two_site_epoch": periodic2,
        "cheapest_non_periodic_action_mean_bytes_per_two_site_epoch": other2,
        "ratio_cheapest_other_over_periodic": other2 / periodic2,
        "single_site_epochs_all_zero_bytes": all(v["mean_bytes_per_epoch"] == 0.0 for k, v in table.items() if k.endswith("active_sites=1")),
        "periodic_over_sync_payload_median": float(np.median([pay(f, PER) / pay(f, SYNC) for f in cal + fams])),
        "reading": "Every action available to the controller costs at least as many bytes per two-site tick as periodic_local (the comparator). Adaptive can at best equal it (ratio 1.0). A 0.20 bound would need a 5x sparser action than exists (about one full-state average every 40 ticks instead of every 8). Arithmetically unreachable under the frozen action set. Even periodic_local itself is only 0.375 of synchronous bytes, so the original 10x-fewer-bytes hypothesis is also out of reach of every available action.",
    }
    # completion gate arithmetic: could ANY policy (even the hindsight oracle) be 10% faster than periodic_local?
    floor_all, floor_valid = [], []
    for f in fams:
        times = {p: tim(f, p) for p in (SYNC, FWD, DLY, PER, ADP)}
        valid = [p for p in times if fin(f, p) <= fin(f, SYNC) + 0.01]
        floor_all.append(min(times.values()) / times[PER])
        floor_valid.append(min(times[p] for p in valid) / times[PER])
    comp_gate = {
        "frozen_bound": d["falsifiers"]["definitions"]["adaptive_to_best_fixed_modeled_completion_time_ratio_upper_bound_lte"],
        "best_any_policy_over_periodic_per_family": floor_all,
        "best_learning_valid_policy_over_periodic_per_family": floor_valid,
        "learning_valid_rule": "final NLL <= synchronous_restart NLL + 0.01 (the oracle's own constraint in the scenario)",
        "median_best_learning_valid_over_periodic": float(np.median(floor_valid)),
        "families_where_a_learning_valid_policy_is_at_least_10pct_faster_than_periodic": int(sum(x <= 0.90 for x in floor_valid)),
        "reading": "Periodic_local was the calibration winner on time. On the six held-out families no learning-valid policy, including the hindsight envelope, is 10 percent faster than it in any family. No whole-policy schedule, including the hindsight envelope, meets a 0.90 bound while staying learning-valid, so the bound could not be met in these six families.",
    }
    # abstentions
    env = d["uncertainty"]["calibration_stress_envelope"]
    ab = []
    for f in fams:
        r = idx[(f, ADP)]
        eps = r["epoch_trace"]
        abst = [e for e in eps if e["abstention_state"]["abstained"]]
        single = [e for e in eps if len(e["stress"]["active_sites"]) == 1]
        ab.append(
            {
                "family": f,
                "abstention_ticks": len(abst),
                "ood_dimensions": sorted({x for e in abst for x in e["ood_state"]["dimensions"]}),
                "site_a_rate_during_abstention": sorted({e["stress"]["sites"]["site-a"]["compute_rate_factor"] for e in abst}),
                "actions_during_abstention": dict(Counter(e["action"] for e in abst)),
                "single_site_ticks": len(single),
                "actions_during_all_single_site_ticks": dict(Counter(e["action"] for e in single)),
                "abstention_ticks_equal_single_site_ticks_with_site_a_below_floor": len(abst),
            }
        )
    abst_total = sum(a["abstention_ticks"] for a in ab)
    abst_info = {
        "calibration_site_a_rate_floor": env["site_a_compute_rate_factor"]["minimum"],
        "per_family": ab,
        "total_abstention_ticks": abst_total,
        "all_abstentions_on_dimension": sorted({x for a in ab for x in a["ood_dimensions"]}),
        "action_taken_during_abstention_equals_single_site_action": all(set(a["actions_during_abstention"]) <= {"exact_forward_recovery"} for a in ab),
        "other_single_site_ticks_not_abstaining_took_same_action": all(set(a["actions_during_all_single_site_ticks"]) == {"exact_forward_recovery"} for a in ab if a["single_site_ticks"]),
        "scenario_site_a_rates_in_failure_segments": {
            fam["family_id"]: [seg["site_a_compute_rate"] for seg in fam["segments"] if len(seg["active_sites"]) == 1] for fam in scenario["evaluation_families"]
        },
        "reading": "Abstentions occurred only on site_a_compute_rate_factor (0.75, 0.65, 0.70 vs a calibration floor of 0.80), in the same ticks where one site was down. In those ticks the controller takes exact_forward_recovery whether it abstains or not, so abstention changed no action.",
    }
    per_family = []
    for f in fams:
        per_family.append(
            {
                "family": f,
                "nll_by_policy": {p: fin(f, p) for p in (SYNC, FWD, DLY, PER, ADP)},
                "payload_by_policy": {p: pay(f, p) for p in (SYNC, FWD, DLY, PER, ADP)},
                "completion_s_by_policy": {p: tim(f, p) for p in (SYNC, FWD, DLY, PER, ADP)},
                "adaptive_action_ticks": dict(Counter(e["action"] for e in idx[(f, ADP)]["epoch_trace"])),
                "oracle_selected_schedule": oracle[f]["selected_whole_policy_schedule"],
                "oracle_post_selection_learning_valid": oracle[f]["post_selection_learning_valid"],
            }
        )
    cal_rows = []
    for c in cal:
        cal_rows.append(
            {
                "stratum": c,
                "nll_by_policy": {p: fin(c, p) for p in (SYNC, FWD, DLY, PER, ADP)},
                "completion_s_by_policy": {p: tim(c, p) for p in (SYNC, FWD, DLY, PER, ADP)},
                "adaptive_action_ticks": dict(Counter(e["action"] for e in idx[(c, ADP)]["epoch_trace"])),
            }
        )
    nll_margin = 0.01
    adverse = {
        "families_where_adaptive_nll_exceeds_periodic_by_more_than_0.01": [f for f, v in zip(fams, nll) if v > nll_margin],
        "families_where_adaptive_nll_exceeds_periodic_by_more_than_0.005": [f for f, v in zip(fams, nll) if v > 0.005],
        "families_where_adaptive_nll_above_periodic": int(sum(v > 0 for v in nll)),
        "families_where_adaptive_slower_than_periodic": int(sum(v > 1 for v in comp)),
        "families_where_adaptive_more_bytes_than_periodic": int(sum(v > 1 for v in payload)),
        "adaptive_modes_in_failures_note": "In E3 (96 ticks) and E6 (216 ticks) the controller's medium-bandwidth/imbalance rule picks delayed_one_step, which calibration had already shown to be the worst-NLL policy (+0.044 to +0.051 vs synchronous in all 10 families, see post_hoc_delayed_minus_sync_nll_all_10).",
        "bootstrap_upper_bound_regret_vs_frozen_0.10": metrics["adaptive_normalized_oracle_regret"]["bootstrap_median_original_method"]["upper"],
    }
    # seed noise reference: scale of a family-to-family spread for the same policy is not a seed sd; use calibration range for sync
    return {
        "scope": "SC1 observable semantic-slack controller: 4 calibration + 6 held-out stress families, ONE seed per family and policy (n=6; regret n=4); learning is measured, bytes and time are modeled",
        "original_verdict_verbatim": d["summary"]["conclusion"],
        "original_gate_outcomes": d["falsifiers"]["outcomes"],
        "selected_comparator": d["summary"]["selected_comparator_policy_id"],
        "metrics": metrics,
        "payload_gate_arithmetic": gate,
        "completion_gate_arithmetic": comp_gate,
        "abstentions": abst_info,
        "adverse_summary": adverse,
        "per_family_evaluation": per_family,
        "calibration_rows": cal_rows,
        "periodic_local_vs_sync": {
            "mechanism_note": "Same tokens, same optimizer, same LR. Periodic local averages model AND AdamW state every 8 ticks; synchronous takes one AdamW step on the union of both quotas every tick. A consistent lower NLL (10 of 10) is what weight/iterate averaging at a constant-LR plateau would give, but it could also come from per-replica clipping or Adam-moment effects. No control arm in the artifact separates these.",
            "mechanism_tested_in_artifact": False,
        },
        "modeled_time_basis": {
            "compute_reference_source": d["runtime"]["warm_start"]["reference_local_site_quota_step_seconds"],
            "note": "Completion seconds use one frozen post-warm microbenchmark scaled by scenario rates plus bytes/bandwidth; they are modeled, not measured.",
        },
    }


# ================================================================== modeled runs
def analyze_recovery() -> dict[str, Any]:
    d = load("recovery_v2", E1 / "results" / "recovery-mechanics-v2.json")
    sc = load("recovery_v2_scenario", E1 / "recovery-scenario-v2.json")
    rows = []
    max_rel = 0.0
    for r in d["runs"]:
        m = r["metrics"]
        pred = sc["compute_energy_j_per_flop"] * m["attempted_compute_flops"] + sc["network_energy_j_per_link_byte"] * m["total_inter_site_link_bytes"]
        rel = abs(pred - m["modeled_energy_j"]) / m["modeled_energy_j"]
        max_rel = max(max_rel, rel)
        rows.append(
            {
                "policy": r["policy_id"],
                "completion_ms": m["mechanical_completion_time_ns"] / 1e6,
                "link_bytes": m["total_inter_site_link_bytes"],
                "attempted_pflop": m["attempted_compute_flops"] / 1e15,
                "lost_pflop": m["lost_compute_flops"] / 1e15,
                "modeled_energy_j": m["modeled_energy_j"],
                "energy_predicted_by_two_coefficients_j": pred,
                "relative_error_vs_two_coefficient_formula": rel,
                "learning_progress_value": m["learning_progress"]["value"],
                "learning_progress_evidence_class": m["learning_progress"]["evidence_class"],
            }
        )
    flop = arr([r["attempted_pflop"] for r in rows])
    energy = arr([r["modeled_energy_j"] for r in rows])
    corr = float(np.corrcoef(flop, energy)[0, 1])
    return {
        "scope": "E001 recovery mechanics v2: one deterministic virtual trace, 4 policies, n=1, no uncertainty exists",
        "original_verdict_verbatim": d["conclusion"]["status"],
        "original_mechanics_answer_verbatim": d["conclusion"]["mechanics_answer"],
        "rows": rows,
        "energy_equals_two_scenario_coefficients_max_relative_error": max_rel,
        "energy_coefficients": {"j_per_flop": sc["compute_energy_j_per_flop"], "j_per_link_byte": sc["network_energy_j_per_link_byte"]},
        "corr_attempted_flops_vs_energy": corr,
        "learning_progress_identical_across_policies": len({r["learning_progress_value"] for r in rows}) == 1,
        "checkpoint_interval_steps": {"baseline": sc["baseline_checkpoint_interval_steps"], "adaptive": sc["adaptive_checkpoint_interval_steps"]},
        "reading": "Energy is a linear function of attempted FLOPs (plus a negligible network term) because the scenario says so, so 'adaptive uses less energy' is the same fact as 'adaptive loses less work'. Lost work follows from checkpoint interval (1 step vs 2). Times follow from fixed durations in the scenario. Learning progress is one declared prior for every policy.",
    }


def analyze_screening() -> dict[str, Any]:
    d = load("screening_v1", E1 / "results" / "screening-mechanics-v1.json")
    sc = d["scenario"]
    base_w = sum(s["base_power_w"] for s in sc["sites"])
    gpu_w = sum(s["accelerator_count"] * s["accelerator_power_w"] for s in sc["sites"])
    n_links = len(sc["links"])
    rows = []
    max_rel_energy = 0.0
    max_rel_bytes = 0.0
    for r in d["runs"]:
        m = r["metrics"]
        elapsed_s = r["elapsed_ns"] / 1e9
        acc_s = m["accelerator_time_ns"] / 1e9
        pred_e = base_w * elapsed_s + (gpu_w / sum(s["accelerator_count"] for s in sc["sites"])) * acc_s
        # accelerator_time is summed over all devices; power per device = 700 W
        per_dev = sc["sites"][0]["accelerator_power_w"]
        pred_e = base_w * elapsed_s + per_dev * acc_s
        rel_e = abs(pred_e - m["modeled_base_and_compute_energy_j"]) / m["modeled_base_and_compute_energy_j"]
        pred_b = len(r["sync_cycles"]) * sc["gradient_bytes"] * n_links
        rel_b = abs(pred_b - m["inter_site_collective_bytes"]) / m["inter_site_collective_bytes"]
        max_rel_energy = max(max_rel_energy, rel_e)
        max_rel_bytes = max(max_rel_bytes, rel_b)
        rows.append(
            {
                "policy": r["policy"],
                "elapsed_s": elapsed_s,
                "sync_cycles": len(r["sync_cycles"]),
                "collective_bytes": m["inter_site_collective_bytes"],
                "modeled_energy_j": m["modeled_base_and_compute_energy_j"],
                "energy_predicted_by_base_x_time_plus_gpu_x_busy_j": pred_e,
                "relative_energy_error": rel_e,
                "relative_bytes_error_cycles_x_gradient_x_links": rel_b,
                "prior_screening_progress_ratio": r["learning_prior"]["prior_screening_progress_ratio"],
                "prior_evidence_status": r["learning_prior"]["evidence_status"],
                "final_local_steps": r["final_local_steps"],
            }
        )
    sens = sc["learning_prior"]["staleness_sensitivity"]
    fixed = next(x for x in rows if x["policy"] == "fixed_local")
    pred_prior = 1.0 / (1.0 + sens * (sc["fixed_local_steps"] - 1))
    verdicts = {a["policy"]: a["conclusion"] for a in d["artifacts"]}
    return {
        "scope": "E001 virtual screening v1: 3 policies, one scenario, n=1, all modeled",
        "original_verdicts_verbatim": verdicts,
        "rows": rows,
        "energy_identity_max_relative_error": max_rel_energy,
        "bytes_identity_max_relative_error": max_rel_bytes,
        "energy_formula": "base_power_total x elapsed + per_gpu_power x summed accelerator-seconds (inferred from scenario fields; identity holds to the error shown)",
        "bytes_formula": "sync_cycles x gradient_bytes x links (inferred; identity holds to the error shown)",
        "fixed_local_byte_fraction": next(x for x in rows if x["policy"] == "fixed_local")["collective_bytes"] / next(x for x in rows if x["policy"] == "synchronous")["collective_bytes"],
        "fixed_local_byte_fraction_equals_1_over_local_steps": abs(next(x for x in rows if x["policy"] == "fixed_local")["collective_bytes"] / next(x for x in rows if x["policy"] == "synchronous")["collective_bytes"] - 1.0 / sc["fixed_local_steps"]) < 1e-9,
        "learning_prior_formula_check_fixed_local": {"predicted": pred_prior, "stored": fixed["prior_screening_progress_ratio"], "inferred_formula": "1/(1+staleness_sensitivity*(local_steps-1))"},
        "learning_prior_declared_not_fitted": True,
        "reading": "Bytes follow from the number of sync cycles, energy from time and busy time, and the learning ratio from a declared sensitivity. All three are the scenario's inputs read back out. The only content is that the simulator is internally consistent.",
    }


def analyze_missing() -> dict[str, Any]:
    patterns = list((REPO / "experiments").glob("e002-*/results/*rack*")) + list((REPO / "experiments").glob("e002-*/results/*dephas*")) + list((REPO / "docs" / "data").glob("e002-rack*")) + list((REPO / "docs" / "data").glob("*dephas*"))
    result_files = sorted(p.name for p in (E2 / "results").glob("*.json"))
    return {
        "scope": "E002 rack-dephasing v3 (PW3)",
        "result_artifact_present": bool(patterns),
        "matched_paths": [str(p.relative_to(REPO)) for p in patterns],
        "e002_result_files_present": result_files,
        "example_telemetry_file_exists": (E2 / "checkpoint-rack-telemetry-v3.example.json").exists(),
        "status": "no result exists; nothing to re-adjudicate",
    }


# ================================================================== main
def main() -> None:
    head = git_head()
    lc3 = analyze_lc3()
    lc1 = analyze_lc1()
    lc2 = analyze_lc2()
    pw1 = analyze_pw1()
    pw2 = analyze_pw2(
        {k: v for k, v in pw1["metrics"].items()},
        {k: v for k, v in lc3["metrics"].items()},
    )
    lc3["energy_gate_power"]["pw2_raw_log_ratio_sd_for_comparison"] = pw2["gate_power_pw2"]["pw2_raw_D_over_A_log_sd"]
    sc1 = analyze_sc1()
    recovery = analyze_recovery()
    screening = analyze_screening()
    missing = analyze_missing()
    mism = [c for c in CHECKS if not c["reproduces_stored"]]
    out = {
        "schema": "gpu-stack.reanalysis.v1",
        "label": "POST-HOC re-analysis. Nothing here was frozen before the original runs. Original verdicts are quoted verbatim in original_verdict_verbatim fields and are never modified.",
        "git_commit": head,
        "project_seed": PROJECT_SEED,
        "confidence_level": 0.9,
        "bootstrap_draws": 10000,
        "reads_only": "experiments/*/results/*.json and the frozen scenario JSON next to them (for original bootstrap seeds). Writes only analysis/reanalysis/reanalysis-v1.json.",
        "sources": SOURCES,
        "reproduction_summary": {
            "n_original_intervals_recomputed": len(CHECKS),
            "n_reproduced_exactly": len(CHECKS) - len(mism),
            "mismatches": mism,
            "method": "same percentile bootstrap of the median, numpy default_rng(seed + offset), 10000 draws, 90% level; compared to stored lower/median/upper with relative tolerance 1e-9",
        },
        "runs": {
            "E001_screen_v1": screening,
            "E001_recovery_v2": recovery,
            "E001_LC1": lc1,
            "E001_LC2": lc2,
            "E001_LC3": lc3,
            "E002_PW1": pw1,
            "E002_PW2": pw2,
            "E001_SC1": sc1,
            "E002_rack_dephasing_v3": missing,
        },
    }
    OUT.write_text(json.dumps(out, indent=1, sort_keys=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")
    print(f"git {head}")
    print(f"original intervals recomputed: {len(CHECKS)}; exact reproductions: {len(CHECKS) - len(mism)}")
    for c in mism:
        print("MISMATCH", c)


if __name__ == "__main__":
    main()
