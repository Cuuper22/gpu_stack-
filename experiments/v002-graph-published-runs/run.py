"""Runner for study V002. Usage (venv python, repo on PYTHONPATH):

    PYTHONPATH=/path/to/repo python run.py [--dataset heldout-runs.json] [--out results/] [--smoke]

--smoke runs on synthetic-smoke.json (one made-up run) and skips the hash check.
The real run refuses to start unless heldout-runs.json matches FROZEN_DATASET_SHA256
and predict.py matches FROZEN_PREDICT_SHA256 (both filled in when the protocol is frozen).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import predict as P  # noqa: E402

# Filled in by the coordinator-visible freeze step (see protocol.md "Freeze record").
FROZEN_DATASET_SHA256 = "92f46f557fce538a5e012446a11cd746a4dcddbcae4f53ec9617ce58cfeeb6d1"
FROZEN_PREDICT_SHA256 = "bd0818d60c7eabc42abbecffb7d5bc0e73d37a41acd6bb029f5692d1b4e4a37f"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception as exc:  # pragma: no cover
        return f"unavailable: {exc}"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def ape(pred: np.ndarray, true: np.ndarray) -> np.ndarray:
    return np.abs(pred / true - 1.0)


def log_err(pred: np.ndarray, true: np.ndarray) -> np.ndarray:
    return np.log(pred / true)


def summarize(pred: Sequence[float], true: Sequence[float]) -> Dict[str, Any]:
    p, y = np.asarray(pred, float), np.asarray(true, float)
    if len(p) == 0:
        return {"n": 0}
    a, e = ape(p, y), log_err(p, y)
    out = {
        "n": int(len(p)),
        "mdape": float(np.median(a)),
        "mean_ape": float(np.mean(a)),
        "p90_ape": float(np.percentile(a, 90)),
        "median_log_error": float(np.median(e)),
        "median_abs_log_error": float(np.median(np.abs(e))),
        "ratio_pred_over_true_min": float(np.min(p / y)),
        "ratio_pred_over_true_max": float(np.max(p / y)),
    }
    if len(p) >= 3:
        rho = stats.spearmanr(p, y)
        out["spearman_rho"] = float(rho.statistic)
    out["pairwise_order_acc"] = pairwise_acc(p, y)
    return out


def pairwise_acc(p: np.ndarray, y: np.ndarray) -> Optional[float]:
    lo, hi = P.CRITERIA["pair_ratio_range"]
    ok = tot = 0
    for i in range(len(y)):
        for j in range(i + 1, len(y)):
            r = max(y[i], y[j]) / min(y[i], y[j])
            if lo <= r <= hi:
                tot += 1
                ok += int((p[i] > p[j]) == (y[i] > y[j]))
    return None if tot == 0 else ok / tot


def coverage(lo: Sequence[float], hi: Sequence[float], true: Sequence[float], n_total: int) -> Dict[str, Any]:
    lo, hi, y = map(lambda z: np.asarray(z, float), (lo, hi, true))
    inside = int(np.sum((y >= lo) & (y <= hi)))
    n = n_total
    k_min = int(stats.binom.ppf(P.CRITERIA["binom_alpha"], n, P.CRITERIA["interval_nominal"])) if n else 0
    sharp = float(np.median(hi / lo)) if len(lo) else None
    return {
        "covered": inside, "n": n, "coverage": inside / n if n else None,
        "k_min_for_pass": k_min, "median_p95_over_p5": sharp,
        "pass": bool(n and inside >= k_min and sharp is not None and sharp <= P.CRITERIA["sharpness_max_ratio"]),
    }


def cluster_bootstrap(clusters: Sequence[str], stat: Callable[[np.ndarray], float], reps: int, seed: int) -> Dict[str, Any]:
    cl = np.asarray(clusters)
    uniq = sorted(set(cl))
    idx = {u: np.where(cl == u)[0] for u in uniq}
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(reps):
        pick = rng.choice(len(uniq), size=len(uniq), replace=True)
        sel = np.concatenate([idx[uniq[k]] for k in pick])
        vals.append(stat(sel))
    vals = np.asarray(vals)
    return {"lo95": float(np.percentile(vals, 2.5)), "hi95": float(np.percentile(vals, 97.5)), "n_clusters": len(uniq)}


def leave_one_cluster_out(clusters: Sequence[str], pred: np.ndarray, true: np.ndarray) -> Dict[str, Any]:
    cl = np.asarray(clusters)
    vals = {}
    for u in sorted(set(cl)):
        m = cl != u
        if m.sum():
            vals[u] = float(np.median(ape(pred[m], true[m])))
    return {"range": [min(vals.values()), max(vals.values())] if vals else None, "by_cluster_removed": vals}


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
def select(ds: dict, tag: str) -> List[dict]:
    return [r for r in ds["records"] if tag in r["used_in"]]


def safe(fn: Callable[[], Any]) -> Dict[str, Any]:
    try:
        return {"ok": True, "val": fn()}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def run_T1(ds: dict, recs: List[dict], label: str) -> Dict[str, Any]:
    rows = []
    for r in recs:
        y = P.true_accel_seconds_per_token(r)
        row = {"id": r["id"], "family": r["family"], "tier": r["tier"], "true": y}
        row["A"] = P.baseline_a(ds, r)
        row["A_int"] = P.baseline_a_interval(ds, r)
        g0, g1 = safe(lambda: P.graph_time_G0(ds, r)), safe(lambda: P.graph_time_G1(ds, r))
        row["G0"] = g0["val"]["accel_s_per_token"] if g0["ok"] else None
        row["G0_err"] = None if g0["ok"] else g0["error"]
        if g0["ok"]:
            row["G0_violations"] = g0["val"]["violated_constraints"] + g0["val"]["violated_validity"]
        if g1["ok"]:
            row["G1"], row["G1_p5"], row["G1_p95"] = g1["val"]["accel_s_per_token"], g1["val"]["p5"], g1["val"]["p95"]
        else:
            row["G1"] = row["G1_p5"] = row["G1_p95"] = None
            row["G1_err"] = g1["error"]
        rows.append(row)
    out: Dict[str, Any] = {"label": label, "rows": rows, "arms": {}}
    cl = [r["family"] for r in rows]
    y_all = np.array([r["true"] for r in rows])
    for arm in ("A", "G0", "G1"):
        ok = [i for i, r in enumerate(rows) if r.get(arm) is not None]
        pred = np.array([rows[i][arm] for i in ok])
        y = y_all[ok]
        s = summarize(pred, y)
        s["n_failed"] = len(rows) - len(ok)
        if len(ok) >= 2:
            s["bootstrap_mdape"] = cluster_bootstrap(
                [cl[i] for i in ok], lambda sel: float(np.median(ape(pred[sel], y[sel]))),
                P.CRITERIA["bootstrap_reps"], P.CRITERIA["bootstrap_seed"])
            s["leave_one_cluster_out"] = leave_one_cluster_out([cl[i] for i in ok], pred, y)
        out["arms"][arm] = s
    # intervals: graph propagation and the closed-form interval of the same prior (baseline A)
    ok1 = [r for r in rows if r.get("G1") is not None]
    out["interval_G1"] = coverage([r["G1_p5"] for r in ok1], [r["G1_p95"] for r in ok1], [r["true"] for r in ok1], len(rows))
    out["interval_A_closed_form"] = coverage([r["A_int"]["p5"] for r in rows], [r["A_int"]["p95"] for r in rows], y_all, len(rows))
    # paired difference G1 - A in MdAPE
    if len(ok1) >= 2:
        ia = np.array([r["A"] for r in ok1])
        ig = np.array([r["G1"] for r in ok1])
        yy = np.array([r["true"] for r in ok1])
        d_point = float(np.median(ape(ig, yy)) - np.median(ape(ia, yy)))
        d_ci = cluster_bootstrap(
            [r["family"] for r in ok1],
            lambda sel: float(np.median(ape(ig[sel], yy[sel])) - np.median(ape(ia[sel], yy[sel]))),
            P.CRITERIA["bootstrap_reps"], P.CRITERIA["bootstrap_seed"])
        out["delta_mdape_G1_minus_A"] = {"point": d_point, **d_ci}
    # equal-weight-per-cluster median APE (secondary)
    byc: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        if r.get("G1") is not None:
            byc[r["family"]].append(abs(r["G1"] / r["true"] - 1))
    out["cluster_equal_weight_median_ape_G1"] = float(np.median([np.mean(v) for v in byc.values()])) if byc else None
    return out


def run_T2(ds: dict, recs: List[dict]) -> Dict[str, Any]:
    rows = []
    for r in recs:
        y = P.true_accel_seconds_per_token(r)
        g2 = safe(lambda: P.graph_time_G2(ds, r))
        rows.append({
            "id": r["id"], "true": y, "mfu_used": r["mfu_reported"]["value"],
            "G2": g2["val"]["accel_s_per_token"] if g2["ok"] else None,
            "A_fixed_40": P.baseline_a(ds, r),
            "A_with_reported_mfu": P.baseline_a(ds, r, r["mfu_reported"]["value"]),
            "G2_err": None if g2["ok"] else g2["error"],
        })
    ok = [r for r in rows if r["G2"] is not None]
    y = np.array([r["true"] for r in ok])
    return {
        "rows": rows,
        "G2": summarize([r["G2"] for r in ok], y),
        "A_fixed_40": summarize([r["A_fixed_40"] for r in ok], y),
        "A_with_reported_mfu": summarize([r["A_with_reported_mfu"] for r in ok], y),
        "note": "n is small; descriptive only.",
    }


def accel_hours_from_wall(r: dict) -> float:
    return r["accel_count"]["value"] * r["time"]["wall_days"]["value"] * 24.0


def run_E1(ds: dict, recs: List[dict], label: str) -> Dict[str, Any]:
    rows = []
    for r in recs:
        h = accel_hours_from_wall(r)
        en = r["energy"]
        y = en["energy_mwh"]["value"]
        base = P.energy_baselines(ds, r, h, en["pue"]["value"])
        g = safe(lambda: P.graph_energy(ds, r, en["scope"], h))
        rows.append({"id": r["id"], "family": r["family"], "tier": r["tier"], "true_mwh": y, "accel_hours": h,
                     **{f"base_{k}": v for k, v in base.items()},
                     "G_p50": g["val"]["mwh_p50"] if g["ok"] else None,
                     "G_p5": g["val"]["mwh_p5"] if g["ok"] else None,
                     "G_p95": g["val"]["mwh_p95"] if g["ok"] else None,
                     "G_err": None if g["ok"] else g["error"]})
    out: Dict[str, Any] = {"label": label, "rows": rows, "arms": {}}
    for arm, key in (("b_tdp", "base_b"), ("c_pue_fixed", "base_c"), ("c_pue_oracle", "base_c_oracle"), ("graph", "G_p50")):
        ok = [r for r in rows if r.get(key) is not None]
        out["arms"][arm] = summarize([r[key] for r in ok], [r["true_mwh"] for r in ok])
    ok = [r for r in rows if r.get("G_p50") is not None]
    out["interval_graph"] = coverage([r["G_p5"] for r in ok], [r["G_p95"] for r in ok], [r["true_mwh"] for r in ok], len(rows))
    out["n_clusters"] = len({r["family"] for r in rows})
    return out


def run_E2(ds: dict, recs: List[dict], label: str) -> Dict[str, Any]:
    rows = []
    for r in recs:
        en = r["energy"]
        raw = en["gpu_energy_raw_mwh"]["value"]
        pue = en["pue"]["value"]
        hours_a = P.baseline_a(ds, r) * r["tokens"]["value"] / 3600.0
        base = P.energy_baselines(ds, r, hours_a, pue)
        g = safe(lambda: P.graph_energy(ds, r, "gpu_only_raw", None))
        rows.append({"id": r["id"], "family": r["family"], "tier": r["tier"], "true_raw_mwh": raw, "true_raw_x_pue_mwh": raw * pue,
                     "pred_hours_A": hours_a,
                     "base_b": base["b"], "base_c": base["c"],
                     "G_p50": g["val"]["mwh_p50"] if g["ok"] else None,
                     "G_p5": g["val"]["mwh_p5"] if g["ok"] else None,
                     "G_p95": g["val"]["mwh_p95"] if g["ok"] else None,
                     "G_err": None if g["ok"] else g["error"]})
    out: Dict[str, Any] = {"label": label, "rows": rows, "arms": {}}
    out["arms"]["b_tdp_x_hoursA_vs_raw"] = summarize([r["base_b"] for r in rows], [r["true_raw_mwh"] for r in rows])
    out["arms"]["c_pue_fixed_vs_raw_x_pue"] = summarize([r["base_c"] for r in rows], [r["true_raw_x_pue_mwh"] for r in rows])
    ok = [r for r in rows if r.get("G_p50") is not None]
    out["arms"]["graph_gpu_only_vs_raw"] = summarize([r["G_p50"] for r in ok], [r["true_raw_mwh"] for r in ok])
    out["interval_graph"] = coverage([r["G_p5"] for r in ok], [r["G_p95"] for r in ok], [r["true_raw_mwh"] for r in ok], len(rows))
    out["n_clusters"] = len({r["family"] for r in rows})
    return out


def run_S2(ds: dict, recs: List[dict]) -> Dict[str, Any]:
    rows = []
    for r in recs:
        y = r["params"]["value"]
        g = safe(lambda: P.graph_params_from_arch(r))
        n = P.naive_params_from_arch(r)
        rows.append({"id": r["id"], "true": y, "graph": g["val"] if g["ok"] else None, "naive_12Ld2": n,
                     "graph_err": None if g["ok"] else g["error"]})
    ok = [r for r in rows if r["graph"] is not None]
    return {
        "rows": rows,
        "graph": summarize([r["graph"] for r in ok], [r["true"] for r in ok]),
        "naive": summarize([r["naive_12Ld2"] for r in rows], [r["true"] for r in rows]),
    }


# ---------------------------------------------------------------------------
# Verdicts: mechanical application of CRITERIA (protocol.md "Decision criteria")
# ---------------------------------------------------------------------------
def verdicts(res: Dict[str, Any]) -> Dict[str, Any]:
    C = P.CRITERIA
    v: Dict[str, Any] = {}
    t1 = res["T1_tierA"]
    v["Q1_graph_as_shipped_time"] = {
        "G0_mdape": t1["arms"]["G0"].get("mdape"),
        "pass": (t1["arms"]["G0"].get("mdape") is not None and t1["arms"]["G0"]["mdape"] <= C["mdape_pass"]),
        "rule": f"MdAPE(G0) <= {C['mdape_pass']}",
    }
    g1 = t1["arms"]["G1"]
    v["Q2a_graph_plus_prior_accuracy"] = {
        "G1_mdape": g1.get("mdape"), "pass": (g1.get("mdape") is not None and g1["mdape"] <= C["mdape_pass"]),
        "rule": f"MdAPE(G1) <= {C['mdape_pass']}"}
    v["Q2b_interval_calibration_and_sharpness"] = {**t1["interval_G1"], "rule": "covered >= binom 5th percentile of Bin(n,0.9) AND median p95/p5 <= 4"}
    d = t1.get("delta_mdape_G1_minus_A")
    if d:
        m = C["equivalence_margin"]
        if d["hi95"] < -m:
            word = "graph_better_than_baseline"
        elif d["lo95"] > m:
            word = "graph_worse_than_baseline"
        elif d["lo95"] >= -m and d["hi95"] <= m:
            word = "equivalent_to_baseline"
        else:
            word = "inconclusive"
        v["Q2c_value_over_baseline_A"] = {**d, "verdict": word, "rule": f"cluster-bootstrap 95% CI of MdAPE(G1)-MdAPE(A) vs +/-{m}"}
    t2 = res.get("T2")
    if t2 and t2["G2"].get("n"):
        v["Q3_oracle_mfu_accounting"] = {"G2_mdape": t2["G2"]["mdape"], "n": t2["G2"]["n"],
                                         "pass": t2["G2"]["mdape"] <= C["oracle_mdape_pass"],
                                         "rule": f"MdAPE(G2) <= {C['oracle_mdape_pass']} (n small, descriptive)"}
    for key in ("E1_tierA", "E2_tierA"):
        e = res.get(key)
        if e:
            v[f"Q4_{key}"] = {"n_clusters": e["n_clusters"],
                              "verdict": "not_tested_too_few_clusters" if e["n_clusters"] < C["energy_min_clusters"] else "evaluate_by_mdape",
                              "rule": f"fewer than {C['energy_min_clusters']} independent clusters => no verdict"}
    s2 = res.get("S2")
    if s2 and s2["graph"].get("n"):
        v["Q5_param_count_from_architecture"] = {"graph_mdape": s2["graph"]["mdape"], "naive_mdape": s2["naive"]["mdape"],
                                                  "pass": s2["graph"]["mdape"] <= C["s2_mdape_pass"],
                                                  "rule": f"MdAPE(graph params) <= {C['s2_mdape_pass']}"}
    return v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=os.path.join(HERE, "heldout-runs.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    if args.smoke:
        args.dataset = os.path.join(HERE, "synthetic-smoke.json")
        args.out = os.path.join(HERE, "results-smoke")
    ds_sha = sha256_file(args.dataset)
    pred_sha = sha256_file(os.path.join(HERE, "predict.py"))
    if not args.smoke:
        if FROZEN_DATASET_SHA256 == "TO_BE_SET_AT_FREEZE" or ds_sha != FROZEN_DATASET_SHA256:
            sys.exit(f"dataset hash {ds_sha} does not match frozen {FROZEN_DATASET_SHA256}; refusing to run")
        if FROZEN_PREDICT_SHA256 == "TO_BE_SET_AT_FREEZE" or pred_sha != FROZEN_PREDICT_SHA256:
            sys.exit(f"predict.py hash {pred_sha} does not match frozen {FROZEN_PREDICT_SHA256}; refusing to run")
    ds = json.load(open(args.dataset))
    os.makedirs(args.out, exist_ok=True)

    res: Dict[str, Any] = {}
    res["T1_tierA"] = run_T1(ds, select(ds, "T1"), "T1 tier A")
    tb = select(ds, "T1_tierB")
    if tb:
        res["T1_tierA_plus_B"] = run_T1(ds, select(ds, "T1") + tb, "T1 tier A + tier B (sensitivity)")
    if select(ds, "T2"):
        res["T2"] = run_T2(ds, select(ds, "T2"))
    if select(ds, "E1"):
        res["E1_tierA"] = run_E1(ds, select(ds, "E1"), "E1 tier A")
    if select(ds, "E1") or select(ds, "E1_tierB"):
        res["E1_tierA_plus_B"] = run_E1(ds, select(ds, "E1") + select(ds, "E1_tierB"), "E1 tier A + B")
    if select(ds, "E2"):
        res["E2_tierA"] = run_E2(ds, select(ds, "E2"), "E2 tier A")
    if select(ds, "E2") or select(ds, "E2_tierB"):
        res["E2_tierA_plus_B"] = run_E2(ds, select(ds, "E2") + select(ds, "E2_tierB"), "E2 tier A + B")
    if select(ds, "S2"):
        res["S2"] = run_S2(ds, select(ds, "S2"))
    res["verdicts"] = verdicts(res)
    res["provenance"] = {
        "git_head": git_head(), "dataset_sha256": ds_sha, "predict_py_sha256": pred_sha,
        "run_py_sha256": sha256_file(os.path.abspath(__file__)), "frozen_constants": P.FROZEN, "criteria": P.CRITERIA,
        "python": platform.python_version(), "numpy": np.__version__, "runtime_seconds": time.time() - t0,
        "smoke": args.smoke,
    }
    with open(os.path.join(args.out, "results.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("wrote", os.path.join(args.out, "results.json"), "in %.1fs" % (time.time() - t0))
    if args.smoke:
        print(json.dumps({k: res[k]["arms"] if "arms" in res[k] else None for k in res if k.startswith("T1")}, indent=1)[:1500])


if __name__ == "__main__":
    main()
