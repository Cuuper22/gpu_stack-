"""Write scenario.json: every seed, schedule, and frozen setting for R001.

Failure schedules: the original E1-E6 schedules were written by hand; no generator
exists in the repo. This file defines one inferred from them (see protocol.md):
  count K in {2, 3} with P(3) = 1/6 (5 of the 6 originals have 2 failures, E5 has 3);
  each failure is [start_tick, duration] with start a multiple of 8 in [32, 216]
  and duration in {8, 16, 24};
  failures are ordered and the gap from one failure's end to the next start is >= 48
  (the smallest gap in E1-E6);
  the last failure ends by tick 240 (E1-E6 end by 240).
Schedules identical to E1-E6 are rejected. No evaluation data exists at this stage.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EXP = REPO / "experiments" / "e001-beyond-one-datacenter"

ORIGINAL = [
    [[40, 8], [136, 16]], [[64, 16], [200, 8]], [[72, 8], [128, 24]],
    [[104, 16], [184, 16]], [[32, 8], [104, 8], [216, 16]], [[88, 24], [168, 8]],
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample_schedule(rng) -> list[list[int]]:
    while True:
        k = 3 if rng.random() < 1 / 6 else 2
        failures: list[list[int]] = []
        cursor = 32
        ok = True
        for _ in range(k):
            starts = [s for s in range(cursor, 217, 8)]
            if not starts:
                ok = False
                break
            start = int(rng.choice(starts))
            duration = int(rng.choice([8, 16, 24]))
            if start + duration > 240:
                ok = False
                break
            failures.append([start, duration])
            cursor = start + duration + 48
            cursor += (-cursor) % 8
        if ok and failures not in ORIGINAL:
            return failures


def main() -> None:
    lc3 = json.loads((EXP / "equal-work-scenario-v1.json").read_text())
    rng = np.random.default_rng(20261001)
    cal_warm = [9101, 9102, 9103]
    eval_warm = [8101, 8102, 8103, 8104, 8105, 8106]

    lc3_cal = []
    for j, w in enumerate(cal_warm):
        lc3_cal.append({"warm_seed": w, "stream_seeds": [9211 + 100 * j, 9229 + 100 * j, 9247 + 100 * j]})
    lc3_eval = []
    n = 0
    for w in eval_warm:
        for _ in range(3):
            n += 1
            lc3_eval.append(
                {
                    "pair_id": f"P{n:02d}",
                    "warm_seed": w,
                    "stream_seed": 8200 + n,
                    "failures": sample_schedule(rng),
                }
            )

    nofail = ["E1-bursty-wan", "E3-power-throttle-with-fast-wan", "E5-short-alternating-stress"]
    fail = ["E2-low-wan-then-failure", "E4-failure-inside-wan-collapse", "E6-repeated-membership-loss"]
    sc1_eval = []
    c = 0
    for i, w in enumerate(eval_warm):
        for fam in (nofail[i % 3], fail[(i + i // 3) % 3]):
            c += 1
            sc1_eval.append({"cell_id": f"Q{c:02d}", "warm_seed": w, "family_id": fam, "stream_seed": 8300 + c})
    sc1_cal = []
    c = 0
    for j, w in enumerate(cal_warm):
        for fam in ("C1-healthy-high-bandwidth", "C4-single-failure"):
            c += 1
            sc1_cal.append({"cell_id": f"K{c:02d}", "warm_seed": w, "family_id": fam, "stream_seed": 9300 + c})

    levels = {
        "L0": {"calibration_warm_seeds": cal_warm, "evaluation_warm_seeds": eval_warm, "optional_arms": True},
        "L1": {"calibration_warm_seeds": cal_warm, "evaluation_warm_seeds": eval_warm[:5], "optional_arms": False},
        "L2": {"calibration_warm_seeds": cal_warm[:2], "evaluation_warm_seeds": eval_warm[:5], "optional_arms": False},
        "rule": ("chosen once, before any task runs, from a measured warm-start throughput probe "
                 "(`run.py probe`): the richest level whose projected wall-clock is <= 3.0 h (L0, then L1, then L2); "
                 "if even L2 projects above 3.0 h, wait for a quieter machine or do not run. Never chosen from outcomes."),
    }
    scenario = {
        "schema": "r001.scenario.v1",
        "levels": levels,
        "study_id": "R001-cpu-replication",
        "sources": {
            "lc3_scenario": {"path": "experiments/e001-beyond-one-datacenter/equal-work-scenario-v1.json",
                             "sha256": sha(EXP / "equal-work-scenario-v1.json")},
            "sc1_scenario": {"path": "experiments/e001-beyond-one-datacenter/semantic-consistency-scenario-v1.json",
                             "sha256": sha(EXP / "semantic-consistency-scenario-v1.json")},
        },
        "dataset": lc3["dataset"],
        "model": lc3["model"],
        "optimization": {
            **{k: v for k, v in lc3["optimization"].items()},
            "autocast": "bfloat16 (CPU autocast via cpu_runtime.install)",
            "evaluation_interval_ticks": 64,
            "validation_batches": 64,
            "validation_seed": 20260712,
            "num_threads_per_worker": 1,
            "workers": 4,
        },
        "warm_start": {"ticks": 8192, "late_window_ticks": 256, "max_late_window_nll_improvement": 0.03,
                       "invalid_seed_rule": "a warm seed failing the late-stage gate is dropped from every analysis and reported; it is not replaced"},
        "calibration_warm_seeds": cal_warm,
        "evaluation_warm_seeds": eval_warm,
        "lc3": {
            "calibration": lc3_cal,
            "calibration_arms": "fixed no-failure for all three streams; adaptive no-failure for the first stream only (exact-equivalence check)",
            "evaluation_pairs": lc3_eval,
            "schedule_generator_seed": 20261001,
            "margin": {"original_nll": 0.01, "multiplier_on_sd": 2.0, "round_up_to": 0.001,
                       "floor_nll": 0.003, "cap_nll": 0.01},
            "ci_level": 0.90,
            "pairs_per_warm_seed": 3,
            "unit_of_analysis": "warm seed (mean of its three paired differences)",
        },
        "sc1": {
            "calibration_cells": sc1_cal,
            "evaluation_cells": sc1_eval,
            "calibration_arms": ["exact_forward_recovery", "periodic_local"],
            "evaluation_arms": ["exact_forward_recovery", "periodic_local",
                                "exact_forward_recovery+cosine", "periodic_local+cosine"],
            "optional_arms": ["periodic_local+cosine"],
            "ema_decays": [0.9, 0.95, 0.98, 0.99],
            "ema_rule": "EMA of the surviving replica's weights, updated once per canonical tick; evaluated only at tick 256; the decay used for the primary test is the one with the lowest mean EMA NLL on calibration cells",
            "cosine": "lr_t = 3e-4 * 0.5 * (1 + cos(pi * t / 256)) at canonical tick t = 0..255",
            "advantage_floor_nll": 0.005,
            "explained_fraction_thresholds": {"mostly_explained_lower_bound_gte": 0.75, "not_explained_upper_bound_lte": 0.25},
            "ci_level": 0.90,
            "overrides": {"evaluation_interval_ticks": 64, "validation_batches": 64},
        },
    }
    out = HERE / "scenario.json"
    out.write_text(json.dumps(scenario, indent=1) + "\n")
    print("wrote", out, "sha256", sha(out))
    for p in lc3_eval:
        print(p["pair_id"], p["warm_seed"], p["stream_seed"], p["failures"])


if __name__ == "__main__":
    main()
