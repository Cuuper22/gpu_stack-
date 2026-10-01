"""R001 analysis. Stage 2 only (on real data). `selftest` uses synthetic numbers.

  analyze.py calibrate   -> results/calibration.json  (margin, SD, EMA decay; calibration data only)
  analyze.py evaluate    -> results/analysis.json     (refuses to run without calibration.json)
  analyze.py selftest    -> synthetic data in a temp dir; checks the code path only

Decision rules are those in protocol.md and scenario.json; nothing is tuned here.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
SC = json.loads((HERE / "scenario.json").read_text())
FIXED = "fixed-local-checkpoint-restart"
ADAPT = "adaptive-survivor-continuation"


def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def load(raw: Path, task_id: str):
    p = raw / f"{task_id}.json"
    return json.loads(p.read_text()) if p.exists() else None


def short(policy: str) -> str:
    return "fixed" if policy.startswith("fixed") else "adaptive"


def arm_short(arm: str) -> str:
    return arm.replace("exact_forward_recovery", "sync").replace("periodic_local", "local").replace("+cosine", "-cos")


def t_interval(values, level=0.90):
    """Mean and two-sided level CI by t. Returns dict; n<2 gives None bounds."""
    x = np.asarray(values, dtype=float)
    n = len(x)
    mean = float(x.mean()) if n else None
    if n < 2:
        return {"n": n, "mean": mean, "lower": None, "upper": None, "sd": None}
    sd = float(x.std(ddof=1))
    half = float(stats.t.ppf(0.5 + level / 2, n - 1)) * sd / math.sqrt(n)
    return {"n": n, "mean": mean, "lower": mean - half, "upper": mean + half, "sd": sd}


def valid_warm_seeds(raw: Path, seeds):
    ok, bad = [], []
    for s in seeds:
        w = load(raw, f"warm-{s}")
        if w and (w["summary"]["late_window"]["late_stage_gate_passed"] or os.environ.get("R001_TINY")):
            ok.append(s)
        else:
            bad.append({"seed": s, "reason": "missing" if not w else "late-stage gate failed"})
    return ok, bad


# ------------------------------------------------------------------ calibration

def calibrate(raw: Path, out: Path, level: str = "L0") -> dict:
    lc = SC["lc3"]
    cal_seeds = SC["levels"][level]["calibration_warm_seeds"]
    ok, bad = valid_warm_seeds(raw, cal_seeds)
    if any(b["reason"] == "missing" for b in bad):
        raise SystemExit(f"calibration warm checkpoints missing: {bad}")
    fixed_nll, by_seed, equivalence = [], {}, []
    for item in lc["calibration"]:
        w = item["warm_seed"]
        if w not in ok:
            continue
        for k, stream in enumerate(item["stream_seeds"]):
            f = load(raw, f"lc3cal-{w}-{stream}-fixed")
            if f is None:
                raise SystemExit(f"missing calibration task lc3cal-{w}-{stream}-fixed")
            v = f["run"]["final_held_out_nll"]
            fixed_nll.append(v)
            by_seed.setdefault(w, []).append(v)
            if k == 0:
                a = load(raw, f"lc3cal-{w}-{stream}-adaptive")
                if a is not None:
                    equivalence.append({
                        "warm_seed": w,
                        "final_nll_identical": a["run"]["final_held_out_nll"] == v,
                        "attempted_tokens_identical": a["run"]["attempted_tokens"] == f["run"]["attempted_tokens"],
                        "curve_identical": [p["held_out_nll"] for p in a["run"]["curve"]]
                        == [p["held_out_nll"] for p in f["run"]["curve"]]})
    sd = float(np.std(fixed_nll, ddof=1)) if len(fixed_nll) > 1 else None
    m = lc["margin"]
    if sd is None:
        margin = None
    else:
        raw_margin = m["multiplier_on_sd"] * sd
        rounded = math.ceil(raw_margin / m["round_up_to"] - 1e-9) * m["round_up_to"]
        margin = round(min(m["cap_nll"], max(m["floor_nll"], rounded)), 6)
    # one-way variance components (descriptive)
    seeds = sorted(by_seed)
    comp = None
    if len(seeds) >= 2 and len({len(by_seed[s]) for s in seeds}) == 1:
        m_ = len(by_seed[seeds[0]])
        within = float(np.mean([np.var(by_seed[s], ddof=1) for s in seeds]))
        means = [np.mean(by_seed[s]) for s in seeds]
        between = max(0.0, float(np.var(means, ddof=1)) - within / m_)
        comp = {"within_warm_seed_sd": math.sqrt(within), "between_warm_seed_sd": math.sqrt(between)}
    # SC1 EMA decay choice on calibration cells (exact-sync arm EMA only)
    decays = {f"{d:g}": [] for d in SC["sc1"]["ema_decays"]}
    advantage = []
    for cell in SC["sc1"]["calibration_cells"]:
        if cell["warm_seed"] not in ok or cell["warm_seed"] not in cal_seeds:
            continue
        s = load(raw, f"sc1-{cell['cell_id']}-sync")
        l = load(raw, f"sc1-{cell['cell_id']}-local")
        if s is None or l is None:
            raise SystemExit(f"missing calibration task for SC1 cell {cell['cell_id']}")
        for d, v in s["run"]["ema_final_held_out_nll"].items():
            decays[d].append(v)
        if l is not None:
            advantage.append(s["run"]["final_held_out_nll"] - l["run"]["final_held_out_nll"])
    decay_means = {d: float(np.mean(v)) for d, v in decays.items() if v}
    chosen = min(decay_means, key=decay_means.get) if decay_means else None
    result = {
        "calibration_warm_seeds_valid": ok, "calibration_warm_seeds_dropped": bad,
        "fixed_no_failure_final_nll": fixed_nll, "fixed_nll_sd": sd, "variance_components": comp,
        "margin_rule": m, "noninferiority_margin_nll": margin,
        "no_failure_equivalence": equivalence,
        "sc1_calibration_mean_ema_nll_by_decay": decay_means, "ema_decay_selected": chosen,
        "sc1_calibration_sync_minus_local_mean": float(np.mean(advantage)) if advantage else None,
    }
    result["sha256"] = sha(result)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1))
    return result


# ------------------------------------------------------------------ evaluation

def evaluate(raw: Path, calibration_path: Path, out: Path, level: str = "L0") -> dict:
    if not calibration_path.exists():
        raise SystemExit("calibration.json missing: run `analyze.py calibrate` first")
    eval_seeds = SC["levels"][level]["evaluation_warm_seeds"]
    missing: list[str] = []
    cal = json.loads(calibration_path.read_text())
    delta = cal["noninferiority_margin_nll"]
    ok, bad = valid_warm_seeds(raw, eval_seeds)
    if any(b["reason"] == "missing" for b in bad):
        raise SystemExit(f"warm checkpoints missing for {bad}; refusing to analyze a partial set")
    # ---- Q1
    pairs, by_seed = [], {}
    for p in SC["lc3"]["evaluation_pairs"]:
        if p["warm_seed"] not in ok:
            continue
        f = load(raw, f"lc3-{p['pair_id']}-fixed")
        a = load(raw, f"lc3-{p['pair_id']}-adaptive")
        if f is None or a is None:
            missing.append(f"lc3-{p['pair_id']}")
            continue
        f, a = f["run"], a["run"]
        complete = bool(f["target_reached"] and a["target_reached"])
        row = {"pair_id": p["pair_id"], "warm_seed": p["warm_seed"], "n_failures": len(p["failures"]),
               "complete": complete, "fixed_nll": f["final_held_out_nll"], "adaptive_nll": a["final_held_out_nll"],
               "diff": a["final_held_out_nll"] - f["final_held_out_nll"],
               "attempted_saving": (f["attempted_tokens"] - a["attempted_tokens"]) / f["attempted_tokens"],
               "tick_saving": (f["opportunity_ticks_to_target"] or 0) - (a["opportunity_ticks_to_target"] or 0),
               "fixed_replayed": f["replayed_tokens"], "fixed_discarded": f["discarded_tokens"],
               "adaptive_redistributed": a["survivor_redistributed_tokens"],
               "adaptive_diverged": a["diverged"]}
        pairs.append(row)
        if complete:
            by_seed.setdefault(p["warm_seed"], []).append(row)
    units = {s: float(np.mean([r["diff"] for r in rows])) for s, rows in by_seed.items()}
    ci = t_interval(list(units.values()), SC["lc3"]["ci_level"])
    def verdict(d):
        if ci["upper"] is None:
            return "not_computable"
        if ci["upper"] <= d:
            return "non_inferior"
        if ci["lower"] > d:
            return "inferior"
        return "not_shown_non_inferior"
    diffs = [r["diff"] for r in pairs if r["complete"]]
    q1 = {
        "margin_primary": delta, "margin_original": SC["lc3"]["margin"]["original_nll"],
        "n_units": ci["n"], "n_pairs_complete": len(diffs), "n_pairs_total": len(pairs),
        "unit_means": units, "mean_diff_ci90": ci,
        "verdict_primary": verdict(delta), "verdict_at_original_margin": verdict(SC["lc3"]["margin"]["original_nll"]),
        "pair_level_descriptive": {"median": float(np.median(diffs)) if diffs else None,
                                   "min": min(diffs) if diffs else None, "max": max(diffs) if diffs else None,
                                   "pairs_above_primary_margin": sum(d > delta for d in diffs),
                                   "pairs_negative": sum(d < 0 for d in diffs)},
        "attempted_token_saving_unit_ci90": t_interval(
            [float(np.mean([r["attempted_saving"] for r in rows])) for rows in by_seed.values()]),
        "opportunity_tick_saving_unit_ci90": t_interval(
            [float(np.mean([r["tick_saving"] for r in rows])) for rows in by_seed.values()]),
        "by_failure_count": {str(k): {"n": sum(r["n_failures"] == k for r in pairs if r["complete"]),
                                      "mean_diff": float(np.mean([r["diff"] for r in pairs if r["complete"] and r["n_failures"] == k]))}
                             for k in sorted({r["n_failures"] for r in pairs})},
        "any_adaptive_divergence": any(r["adaptive_diverged"] for r in pairs),
        "pairs": pairs,
    }
    # ---- Q2
    cells = []
    for c in SC["sc1"]["evaluation_cells"]:
        if c["warm_seed"] not in ok or c["warm_seed"] not in eval_seeds:
            continue
        g = lambda arm: load(raw, f"sc1-{c['cell_id']}-{arm_short(arm)}")
        s, l, sc_, lc_ = g("exact_forward_recovery"), g("periodic_local"), g("exact_forward_recovery+cosine"), g("periodic_local+cosine")
        if s is None or l is None or sc_ is None:
            missing.append(f"sc1-{c['cell_id']}")
            continue
        d = cal["ema_decay_selected"]
        cells.append({
            "cell_id": c["cell_id"], "warm_seed": c["warm_seed"], "family_id": c["family_id"],
            "sync": s["run"]["final_held_out_nll"], "local": l["run"]["final_held_out_nll"],
            "sync_ema": s["run"]["ema_final_held_out_nll"].get(d),
            "sync_ema_all": s["run"]["ema_final_held_out_nll"],
            "sync_cos": sc_["run"]["final_held_out_nll"] if sc_ else None,
            "local_cos": lc_["run"]["final_held_out_nll"] if lc_ else None})
    seeds = sorted({c["warm_seed"] for c in cells})
    def per_seed(key_fn):
        out_ = {}
        for sd_ in seeds:
            vals = [key_fn(c) for c in cells if c["warm_seed"] == sd_]
            if all(v is not None for v in vals) and vals:
                out_[sd_] = float(np.mean(vals))
        return out_
    adv = per_seed(lambda c: c["sync"] - c["local"])
    adv_ci = t_interval(list(adv.values()), SC["sc1"]["ci_level"])
    floor = SC["sc1"]["advantage_floor_nll"]
    def fraction(num_fn):
        num = per_seed(num_fn)
        f = {s_: num[s_] / adv[s_] for s_ in num if s_ in adv and adv[s_] > 0}
        return f, t_interval(list(f.values()), SC["sc1"]["ci_level"])
    th = SC["sc1"]["explained_fraction_thresholds"]
    def label(ci_):
        if ci_["lower"] is None:
            return "not_computable"
        if ci_["lower"] >= th["mostly_explained_lower_bound_gte"]:
            return "mostly_explained"
        if ci_["upper"] <= th["not_explained_upper_bound_lte"]:
            return "not_explained"
        return "partial_or_inconclusive"
    f_ema, f_ema_ci = fraction(lambda c: c["sync"] - c["sync_ema"] if c["sync_ema"] is not None else None)
    f_cos, f_cos_ci = fraction(lambda c: c["sync"] - c["sync_cos"] if c["sync_cos"] is not None else None)
    f_by_decay = {}
    for dkey in sorted({k for c in cells for k in c["sync_ema_all"]}):
        _, ci_ = fraction(lambda c, k=dkey: c["sync"] - c["sync_ema_all"][k])
        f_by_decay[dkey] = ci_
    cos_adv = per_seed(lambda c: None if c["sync_cos"] is None or c["local_cos"] is None else c["sync_cos"] - c["local_cos"])
    cos_adv_ci = t_interval(list(cos_adv.values()), SC["sc1"]["ci_level"])
    q2 = {
        "ema_decay_selected_on_calibration": cal["ema_decay_selected"],
        "n_seeds": len(seeds), "n_cells": len(cells),
        "advantage_sync_minus_local_unit_ci90": adv_ci,
        "advantage_replicated": bool(adv_ci["lower"] is not None and adv_ci["lower"] > floor),
        "explained_by_ema": {"unit_fractions": f_ema, "ci90": f_ema_ci, "label": label(f_ema_ci)},
        "explained_by_cosine": {"unit_fractions": f_cos, "ci90": f_cos_ci, "label": label(f_cos_ci)},
        "ema_fraction_by_decay_descriptive": f_by_decay,
        "advantage_under_cosine_sync_cos_minus_local_cos": {"unit_ci90": cos_adv_ci,
            "vanishes": bool(cos_adv_ci["upper"] is not None and cos_adv_ci["upper"] <= floor),
            "note": "optional arm; empty if periodic_local+cosine was not run"},
        "cells": cells,
    }
    if missing:
        raise SystemExit(f"required tasks missing, refusing to analyze a partial set: {missing}")
    result = {"level": level, "calibration_sha256": cal["sha256"], "evaluation_warm_seeds_valid": ok,
              "evaluation_warm_seeds_dropped": bad, "q1": q1, "q2": q2}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1))
    return result


# ------------------------------------------------------------------ synthetic self-test

def selftest() -> None:
    rng = np.random.default_rng(0)
    (HERE / "work").mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="selftest-", dir=HERE / "work"))
    raw = tmp / "raw"
    raw.mkdir()
    def w(name, obj):
        (raw / f"{name}.json").write_text(json.dumps(obj))
    for s in SC["calibration_warm_seeds"] + SC["evaluation_warm_seeds"]:
        w(f"warm-{s}", {"summary": {"late_window": {"late_stage_gate_passed": True}}})
    for item in SC["lc3"]["calibration"]:
        for k, stream in enumerate(item["stream_seeds"]):
            base = 1.0 + rng.normal(0, 0.003)
            run = lambda: {"run": {"final_held_out_nll": base, "attempted_tokens": 524288,
                                   "curve": [{"held_out_nll": base}]}}
            w(f"lc3cal-{item['warm_seed']}-{stream}-fixed", run())
            if k == 0:
                w(f"lc3cal-{item['warm_seed']}-{stream}-adaptive", run())
    def sc1run(nll, ema=None):
        return {"run": {"final_held_out_nll": nll, "ema_final_held_out_nll": ema or {}}}
    for cell in SC["sc1"]["calibration_cells"]:
        b = 1.0 + rng.normal(0, 0.002)
        w(f"sc1-{cell['cell_id']}-sync", sc1run(b, {"0.9": b - 0.004, "0.95": b - 0.012, "0.98": b - 0.017, "0.99": b - 0.015}))
        w(f"sc1-{cell['cell_id']}-local", sc1run(b - 0.019))
    cal = calibrate(raw, tmp / "calibration.json")  # level L0
    assert cal["ema_decay_selected"] == "0.98" and cal["noninferiority_margin_nll"] is not None, cal
    for p in SC["lc3"]["evaluation_pairs"]:
        base = 1.0 + rng.normal(0, 0.003)
        def r(nll, att, ticks):
            return {"run": {"final_held_out_nll": nll, "attempted_tokens": att, "target_reached": True,
                            "opportunity_ticks_to_target": ticks, "replayed_tokens": 0, "discarded_tokens": 0,
                            "survivor_redistributed_tokens": 0, "diverged": False}}
        w(f"lc3-{p['pair_id']}-fixed", r(base, 540672, 296))
        w(f"lc3-{p['pair_id']}-adaptive", r(base + rng.normal(0.004, 0.003), 524288, 256))
    for c in SC["sc1"]["evaluation_cells"]:
        b = 1.0 + rng.normal(0, 0.002)
        w(f"sc1-{c['cell_id']}-sync", sc1run(b, {"0.9": b - 0.004, "0.95": b - 0.012, "0.98": b - 0.016, "0.99": b - 0.015}))
        w(f"sc1-{c['cell_id']}-local", sc1run(b - 0.019 + rng.normal(0, 0.0015)))
        w(f"sc1-{c['cell_id']}-sync-cos", sc1run(b - 0.02 + rng.normal(0, 0.0015)))
        w(f"sc1-{c['cell_id']}-local-cos", sc1run(b - 0.021 + rng.normal(0, 0.0015)))
    res = evaluate(raw, tmp / "calibration.json", tmp / "analysis.json")
    q1, q2 = res["q1"], res["q2"]
    assert q1["n_units"] == 6 and q1["n_pairs_complete"] == 18
    assert q1["verdict_primary"] in {"non_inferior", "not_shown_non_inferior", "inferior"}
    assert q2["advantage_replicated"] and q2["explained_by_ema"]["label"] == "mostly_explained", q2["explained_by_ema"]
    print("synthetic selftest passed; q1 verdict:", q1["verdict_primary"], "q2 ema:", q2["explained_by_ema"]["label"])
    print("(synthetic numbers; written to", tmp, ")")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    results = HERE / "work" / "tiny" if os.environ.get("R001_TINY") else HERE / "results"
    raw = results / "raw"
    if cmd == "calibrate":
        level = json.loads((results / "manifest.json").read_text()).get("level", "L0")
        print(json.dumps(calibrate(raw, results / "calibration.json", level), indent=1))
    elif cmd == "evaluate":
        level = json.loads((results / "manifest.json").read_text()).get("level", "L0")
        print(json.dumps(evaluate(raw, results / "calibration.json", results / "analysis.json", level), indent=1)[:3000])
    elif cmd == "selftest":
        selftest()
    else:
        raise SystemExit(__doc__)
