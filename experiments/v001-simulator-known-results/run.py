"""Runner for study V001.  Usage (from the repo root, venv python):

    PYTHONPATH=. python -B experiments/v001-simulator-known-results/run.py --mode smoke|full [--only ckpt_stat,...]

Writes results/<check>.json (or results/smoke/ for smoke mode) and results/verdict.json.
Every file records git HEAD, SHA-256 of every input source file, seeds and runtime.
Nothing here edits gpu_stack/.  Thresholds live in CRITERIA below and in protocol.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing as mp
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
from scipy import stats as sps  # noqa: E402

import analytic as A  # noqa: E402
import check_ckpt as K  # noqa: E402
import check_queue as Q  # noqa: E402

BASE_SEED = 20261001

# ---------------------------------------------------------------------------------------
# Frozen settings
# ---------------------------------------------------------------------------------------
XS_STD = [0.25, 0.5, 0.7, 0.85, 1.0, 1.2, 1.5, 2.0, 3.0]
XS_HIGH = [0.5, 0.7, 1.0, 1.5]
XS_TOP = [0.7, 1.0]
REGIMES = [
    dict(name="C/M=0.001,R=C", c_over_m=0.001, r_over_m=0.001, xs=XS_STD),
    dict(name="C/M=0.01,R=C", c_over_m=0.01, r_over_m=0.01, xs=XS_STD),
    dict(name="C/M=0.1,R=C", c_over_m=0.1, r_over_m=0.1, xs=XS_STD),
    dict(name="C/M=0.5,R=C", c_over_m=0.5, r_over_m=0.5, xs=XS_STD),
    dict(name="C/M=1,R=C", c_over_m=1.0, r_over_m=1.0, xs=XS_HIGH),
    dict(name="C/M=2,R=C (outside Daly range)", c_over_m=2.0, r_over_m=2.0, xs=XS_TOP),
    dict(name="C/M=0.01,R~0", c_over_m=0.01, r_over_m=1e-9, xs=XS_STD),
    dict(name="C/M=0.01,R=10C", c_over_m=0.01, r_over_m=0.1, xs=XS_STD),
    dict(name="C/M=0.01,R=C,D=2C", c_over_m=0.01, r_over_m=0.01, d_over_m=0.02, xs=XS_STD),
]

SETTINGS = {
    "full": dict(
        stat_budget=dict(fail_target=10000, max_seg=40000, min_seg=20), smoke_regimes=False,
        diff_traces=300, diff_k=[1, 2, 3, 5, 8], diff_mtbf_mult=[0.5, 2.0, 10.0],
        acc_random=200, acc_boundary=120,
        q_reps=2000, q_n=800, q_warm_n=1000, little_cases=20, little_n=300,
        pub_budget=dict(fail_target=10000, max_seg=40000, min_seg=20),
    ),
    "smoke": dict(
        stat_budget=dict(fail_target=100, max_seg=100, min_seg=20), smoke_regimes=True,
        diff_traces=6, diff_k=[1, 3], diff_mtbf_mult=[2.0],
        acc_random=5, acc_boundary=4,
        q_reps=12, q_n=150, q_warm_n=200, little_cases=2, little_n=80,
        pub_budget=dict(fail_target=100, max_seg=60, min_seg=20),
    ),
}

# Thresholds.  Each is justified in protocol.md ("Decision criteria").
CRITERIA = dict(
    z_crit=3.5,                  # Bonferroni: ~100 tests at family alpha ~0.05 -> per-test p ~ 5e-4 -> |z| 3.5
    chi2_p_min=1e-3,
    pooled_bias_ci_half_width=0.01,
    pooled_se_max=0.005,
    queue_rel_se_max=0.03,
    identity_rel_tol=1e-9,
)


# ---------------------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------------------
def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def provenance(mode: str, seeds: dict) -> dict:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "gpu_stack", "experiments/v001-simulator-known-results"],
                           cwd=REPO, capture_output=True, text=True).stdout.strip().splitlines()
    inputs = {}
    for rel in ("gpu_stack/research/recovery.py", "gpu_stack/research/recovery_runtime.py",
                "gpu_stack/research/temporal.py", "gpu_stack/research/multisite.py"):
        inputs[rel] = sha256_file(REPO / rel)
    for p in sorted(HERE.glob("*.py")):
        inputs[f"experiments/v001-simulator-known-results/{p.name}"] = sha256_file(p)
    proto = HERE / "protocol.md"
    if proto.exists():
        inputs["experiments/v001-simulator-known-results/protocol.md"] = sha256_file(proto)
    return {"git_head": head, "uncommitted_in_scope": dirty, "mode": mode, "input_sha256": inputs, "seeds": seeds,
            "python": platform.python_version(), "numpy": np.__version__,
            "settings": SETTINGS[mode], "criteria": CRITERIA}


def write(out: Path, name: str, payload: dict, prov: dict, seconds: float) -> None:
    out.mkdir(parents=True, exist_ok=True)
    payload = {"provenance": prov, "runtime_seconds": seconds, **payload}
    (out / f"{name}.json").write_text(json.dumps(payload, indent=1, sort_keys=True, default=str))


# ---------------------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------------------
def run_ckpt_stat(cfg, pool) -> dict:
    cells = []
    idx0 = 0
    regs = [dict(REGIMES[1], xs=[0.7, 1.0, 1.5])] if cfg["smoke_regimes"] else REGIMES
    for reg in regs:
        cs = K.regime_cells([reg], reg["xs"])
        for c in cs:
            c["idx"] = idx0
            idx0 += 1
        cells += cs
    jobs = [(c, BASE_SEED, cfg["stat_budget"]) for c in cells]
    res = pool.map(K.stat_cell, jobs, chunksize=1)
    return {"summary": K.summarize_stat(res, CRITERIA["z_crit"]), "n_cells": len(cells)}


def run_ckpt_diff(cfg, pool) -> dict:
    jobs = []
    j = 0
    for k in cfg["diff_k"]:
        for mult in cfg["diff_mtbf_mult"]:
            step, ckpt = 40, 9
            seg = k * step + ckpt
            c = dict(step_s=step, k=k, n_segments=6, ckpt_s=ckpt, rfix_s=3, rxfer_s=4, mtbf_s=mult * seg)
            jobs.append((c, BASE_SEED + 1000 + j, cfg["diff_traces"]))
            j += 1
    res = pool.map(K.diff_cell, jobs, chunksize=1)
    tot: Counter = Counter()
    errs: Counter = Counter()
    for r in res:
        tot.update(r["cats"])
        errs.update(r["errors"])
    return {"cells": res, "totals": dict(tot), "engine_error_signatures": dict(errs),
            "minimal_repro": K.minimal_repro()}


def _acc_job(a):
    seed, n_random, n_boundary, k = a
    return K.accounting_suite(seed, n_random, n_boundary, ks=(k,))


def run_accounting(cfg, pool) -> dict:
    jobs = [(BASE_SEED + 2000 + k, cfg["acc_random"], cfg["acc_boundary"], k) for k in (1, 2, 3, 5)]
    res = pool.map(_acc_job, jobs, chunksize=1)
    out = {"tally": Counter(), "violations": Counter(), "engine_errors": Counter(), "metamorphic": Counter(),
           "examples": []}
    for r in res:
        for key in ("tally", "violations", "engine_errors", "metamorphic"):
            out[key].update(r[key])
        out["examples"] += r["examples"]
    return {k: (dict(v) if isinstance(v, Counter) else v[:10]) for k, v in out.items()}


QUEUE_SCENARIOS = [
    dict(name="M/M/1 rho=0.5", c=1, rho=0.5, service="exp"),
    dict(name="M/M/1 rho=0.8", c=1, rho=0.8, service="exp"),
    dict(name="M/M/1 rho=0.9", c=1, rho=0.9, service="exp"),
    dict(name="M/M/2 rho=0.7", c=2, rho=0.7, service="exp"),
    dict(name="M/M/2 rho=0.9", c=2, rho=0.9, service="exp"),
    dict(name="M/M/5 rho=0.8", c=5, rho=0.8, service="exp"),
    dict(name="M/M/20 rho=0.9", c=20, rho=0.9, service="exp"),
    dict(name="M/D/1 rho=0.5", c=1, rho=0.5, service="det"),
    dict(name="M/D/1 rho=0.7", c=1, rho=0.7, service="det"),
    dict(name="M/H2/1 rho=0.5", c=1, rho=0.5, service="h2"),
]


def _h2_moments():
    p, m1, m2 = 0.1127, 0.2, 4.0
    mean = p * m2 + (1 - p) * m1
    f = 1.0 / mean
    return 1.0, 2 * f * f * (p * m2 * m2 + (1 - p) * m1 * m1)


def queue_scenario(a) -> dict:
    sc, reps, n, n_warm, seed = a
    c, rho, service = sc["c"], sc["rho"], sc["service"]
    stationary = service == "exp"
    warm = 0 if stationary else n_warm
    rng = np.random.default_rng(np.random.SeedSequence([seed]))
    means, frac_wait, mism = [], [], 0
    nn = n if stationary else n + warm
    for _ in range(reps):
        w, m, lam, *_ = Q.run_rep(rng, c, rho, nn, service, stationary, warm=warm)
        mism += m
        means.append(w.mean())
        frac_wait.append(float((w > 0).mean()))
    lam_per_s = rho * c
    if service == "exp":
        theory = Q.mmc_wq(c, lam_per_s, 1.0)
        pw = Q.erlang_c(c, rho * c)
    elif service == "det":
        theory = Q.mg1_wq(lam_per_s, 1.0, 1.0)
        pw = None
    else:
        es, es2 = _h2_moments()
        theory = Q.mg1_wq(lam_per_s, es, es2)
        pw = None
    m = np.asarray(means)
    se = float(m.std(ddof=1) / math.sqrt(len(m)))
    out = {"scenario": sc, "reps": reps, "n_customers_per_rep": n, "warmup_deleted": warm,
           "oracle_mismatches": mism, "mean_wq": float(m.mean()), "se": se, "theory_wq": theory,
           "rel_dev": float(m.mean()) / theory - 1.0, "rel_se": se / theory, "z": (float(m.mean()) - theory) / se}
    if pw is not None:
        f = np.asarray(frac_wait)
        fse = float(f.std(ddof=1) / math.sqrt(len(f)))
        out["p_wait"] = {"est": float(f.mean()), "se": fse, "theory_erlang_c": pw, "z": (float(f.mean()) - pw) / fse}
    return out


def _little_job(a):
    seed, c, n = a
    rng = np.random.default_rng(np.random.SeedSequence([seed]))
    w, mism, lam, A_, S_, st = Q.run_rep(rng, c, 0.8, n, "exp", True)
    full_starts, res = Q.substrate_starts(A_, S_, c, full=True)
    dc_starts, _ = Q.datacenter_starts(A_, S_, c)
    lit = Q.little_checks(A_, S_, st, c)
    snap = Q.snapshot_consistency(A_, S_, full_starts, c, res)
    return {"c": c, "n": len(A_), "oracle_mismatch": mism, "full_vs_nosnap_mismatch": int(full_starts != st),
            "datacenter_vs_timeline_mismatch": int(dc_starts != st),
            "little_L_rel": abs(lit["L_system_time_avg"] - lit["lam_hat_times_W"]) / lit["L_system_time_avg"],
            "little_Lq_rel": abs(lit["Lq_time_avg"] - lit["lam_hat_times_Wq"]) / max(lit["Lq_time_avg"], 1e-30),
            "snapshots": snap,
            "avg_in_service_rel": abs(snap["avg_in_service"] - snap["expected_avg_in_service"]) / snap["expected_avg_in_service"]}


def run_queue(cfg, pool) -> dict:
    jobs = [(sc, cfg["q_reps"], cfg["q_n"], cfg["q_warm_n"], BASE_SEED + 3000 + i) for i, sc in enumerate(QUEUE_SCENARIOS)]
    stat = pool.map(queue_scenario, jobs, chunksize=1)
    lj = [(BASE_SEED + 4000 + i, [1, 2, 4][i % 3], cfg["little_n"]) for i in range(cfg["little_cases"])]
    little = pool.map(_little_job, lj, chunksize=1)
    return {"scenarios": stat, "little_and_consistency": little, "priority_probe": Q.priority_probe()}


# Check 4: published failure statistics (descriptive).  All numbers below were read from the
# papers' text; see protocol.md section "Published numbers used".
LLAMA3 = dict(days=54, unexpected=419, planned=47, total=466, gpus=16384,
              source="Dubey et al. 2024, The Llama 3 Herd of Models, arXiv:2407.21783v3, Sec. 3.3.4 and Table 5",
              reported_effective_training_time="higher than 90% (Sec. 3.3.4)")


def run_published(cfg, pool) -> dict:
    M_unexp = LLAMA3["days"] * 86400 / LLAMA3["unexpected"]
    M_all = LLAMA3["days"] * 86400 / LLAMA3["total"]
    out = {"llama3": LLAMA3, "mtbf_s_unexpected_only": M_unexp, "mtbf_s_all_interruptions": M_all, "rows": []}
    # largest C (= R) at which the closed form still allows 90% effective time at the best interval
    from scipy.optimize import brentq

    def eff(Cs, M):
        te = A.tau_exact(Cs, M, Cs)
        return 1 - A.waste_fraction(te, Cs, M, Cs)
    for label, M in (("unexpected_only", M_unexp), ("all_interruptions", M_all)):
        cmax = brentq(lambda c: eff(c, M) - 0.90, 1.0, 0.2 * M)
        out[f"closed_form_max_C_eq_R_for_90pct_s__{label}"] = cmax
    # engine at a few stated (assumed) costs, Daly higher-order interval
    cells, idx = [], 0
    for Cs in (30.0, 60.0, 120.0, 300.0):
        for label, M in (("unexpected_only", M_unexp),):
            tau = A.tau_daly2(Cs, M)
            cells.append({"idx": 9000 + idx, "regime": f"llama3 C=R={Cs:.0f}s", "label": label, "x": None, "tau_s": tau,
                          "L_s": tau + Cs, "M_s": M, "C_s": Cs, "R_s": Cs, "D_s": 0.0, "tau_exact_s": tau})
            idx += 1
    # the boundary cell: C = R = closed-form maximum for 90 percent
    cm = out["closed_form_max_C_eq_R_for_90pct_s__unexpected_only"]
    tau = A.tau_exact(cm, M_unexp, cm)
    cells.append({"idx": 9100, "regime": "llama3 boundary 90pct", "label": "boundary", "x": None, "tau_s": tau,
                  "L_s": tau + cm, "M_s": M_unexp, "C_s": cm, "R_s": cm, "D_s": 0.0, "tau_exact_s": tau})
    res = pool.map(K.stat_cell, [(c, BASE_SEED + 5000, cfg["pub_budget"]) for c in cells], chunksize=1)
    for r in res:
        out["rows"].append({"regime": r["cell"]["regime"], "C_s": r["cell"]["C_s"], "tau_s": r["cell"]["tau_s"],
                            "effective_time_closed_form": 1 - r["waste_exact"],
                            "effective_time_engine": 1 - r["engine"]["waste"], "se": r["engine"]["waste_se"],
                            "z_engine_vs_closed_form": r["engine"]["z"], "engine_errors": r["engine_errors"]})
    return out


# ---------------------------------------------------------------------------------------
# Verdicts against the frozen criteria
# ---------------------------------------------------------------------------------------
def evaluate(res: dict) -> list[dict]:
    zc = CRITERIA["z_crit"]
    v: list[dict] = []

    def add(cid, text, passed, observed):
        v.append({"id": cid, "criterion": text, "pass": None if passed is None else bool(passed), "observed": observed})

    if "ckpt_stat" in res:
        s = res["ckpt_stat"]["summary"]
        hw = CRITERIA["pooled_bias_ci_half_width"]
        for who, key in (("engine", "engine"), ("reference", "ref")):
            ci = s[f"{key}_pooled_rel_bias"]["ci95"]
            ok = s[f"{key}_z"]["max_abs"] <= zc and s[f"{key}_z"]["chi2_p"] >= CRITERIA["chi2_p_min"] \
                and -hw <= ci[0] and ci[1] <= hw
            if s[f"{key}_pooled_rel_bias"]["se"] > CRITERIA["pooled_se_max"]:
                ok = None  # inconclusive: not enough precision to exclude a 1% bias
            add(f"C1a-{who}-vs-closed-form",
                f"all cells |z|<={zc}; chi2 p>={CRITERIA['chi2_p_min']}; pooled relative bias 95% CI within +-{hw:.0%}",
                ok, {"max_abs_z": s[f"{key}_z"]["max_abs"], "chi2_p": s[f"{key}_z"]["chi2_p"], "pooled_bias_ci95": ci,
                     "cells": s[f"{key}_z"]["n"]})
        add("C1a-engine-ne-reference-on-same-traces", "engine wall time equals reference wall time on every trace (0 differences)",
            s["engine_ne_ref_total"] == 0 and s["engine_total_errors"] == 0,
            {"differences": s["engine_ne_ref_total"], "engine_errors": s["engine_total_errors"]})
        ok = all(e["exact_in_plateau_hull_one_step_slack"] for e in s["by_regime"].values())
        add("C1c-exact-optimum-not-rejected",
            "in every regime the exact optimum lies inside the plateau hull of simulated waste (within 2 SE of the simulated minimum), one grid step of slack",
            ok, {r: e["exact_in_plateau_hull_one_step_slack"] for r, e in s["by_regime"].items()})
        zs = {f"{r}|{lab}": f["z_measured_vs_analytic"] for r, e in s["by_regime"].items() for lab, f in e["formulas"].items()}
        add("C1d-formula-excess-waste", f"measured excess waste of Young/Daly intervals vs the exact optimum agrees with the analytic excess, |z|<={zc} in every regime",
            all(abs(z) <= zc for z in zs.values()), {"max_abs_z": max(abs(z) for z in zs.values()), "n": len(zs)})
    if "ckpt_diff" in res:
        t = res["ckpt_diff"]["totals"]
        completed = t.get("match", 0) + t.get("mismatch", 0)
        add("C1b-differential", "engine wall time equals independent reference to the nanosecond on every trace that completes",
            t.get("mismatch", 0) == 0, {"completed": completed, "mismatch": t.get("mismatch", 0)})
        errs = t.get("engine_error_predicted", 0) + t.get("engine_error_unpredicted", 0)
        add("C1b-completion", "engine completes every failure trace (0 exceptions)", errs == 0,
            {"traces": sum(t.values()), "engine_errors": errs, "signatures": res["ckpt_diff"]["engine_error_signatures"]})
        add("C1b-root-cause", "every engine exception is predicted by the replay-then-failure rule, and every prediction raises",
            t.get("engine_error_unpredicted", 0) == 0 and t.get("no_error_but_predicted", 0) == 0,
            {"unpredicted_errors": t.get("engine_error_unpredicted", 0), "predicted_but_no_error": t.get("no_error_but_predicted", 0)})
    if "accounting" in res:
        a = res["accounting"]
        mm = a["metamorphic"]
        meta_bad = sum(val for key, val in mm.items() if key.endswith("_changed") or key.endswith("_error"))
        bad = sum(a["violations"].values()) + a["tally"].get("wall_ne_reference", 0) + \
            a["tally"].get("completed_but_predicted_crash", 0) + meta_bad
        add("C2-accounting", "0 violations of identities A1-A10, 0 wall-clock differences from the reference, 0 metamorphic changes, on all completed runs",
            bad == 0, {"tally": a["tally"], "violations": a["violations"], "metamorphic": mm})
    if "queue" in res:
        q = res["queue"]
        mis = sum(s["oracle_mismatches"] for s in q["scenarios"]) + sum(
            x["oracle_mismatch"] + x["full_vs_nosnap_mismatch"] + x["datacenter_vs_timeline_mismatch"] for x in q["little_and_consistency"])
        add("C3a-exact-FCFS", "substrate (and VirtualDatacenter WAN link) start times equal an exact FCFS c-server recursion for every customer", mis == 0,
            {"mismatching_customers_or_runs": mis})
        rows = []
        ok = True
        for s in q["scenarios"]:
            conclusive = s["rel_se"] <= CRITERIA["queue_rel_se_max"]
            this = abs(s["z"]) <= zc and conclusive
            if "p_wait" in s:
                this = this and abs(s["p_wait"]["z"]) <= zc
            ok &= this
            rows.append({"scenario": s["scenario"]["name"], "rel_dev": s["rel_dev"], "z": s["z"], "rel_se": s["rel_se"],
                         "conclusive": conclusive})
        add("C3b-theory", f"mean wait vs Erlang C / Pollaczek-Khinchine and P(wait>0) vs Erlang C: |z|<={zc}, and relative SE<={CRITERIA['queue_rel_se_max']:.0%} so the test is not vacuous", ok, rows)
        tol = CRITERIA["identity_rel_tol"]
        lit = q["little_and_consistency"]
        ok = all(x["little_L_rel"] <= tol and x["little_Lq_rel"] <= tol and x["avg_in_service_rel"] <= tol
                 and x["snapshots"]["capacity_violations"] == 0 and x["snapshots"]["active_mismatches"] == 0 for x in lit)
        add("C3c-little-and-snapshots", f"Little's law identities to {tol:g}; snapshots never exceed capacity and agree with the event records", ok,
            {"cases": len(lit), "max_L_rel": max(x["little_L_rel"] for x in lit), "max_in_service_rel": max(x["avg_in_service_rel"] for x in lit)})
        add("C3d-priority-expressible", "DESCRIPTIVE (no pass/fail): a later high-priority customer is served before an earlier waiting low-priority one",
            None, {"high_priority_served_before_waiting_low": q["priority_probe"]["high_priority_served_before_waiting_low"],
                   "starts_ns": q["priority_probe"]["starts_ns"]})
    if "published" in res:
        p = res["published"]
        add("C4-llama3-replay-engine-vs-closed-form", f"engine effective-time at assumed C=R and at the closed-form 90 percent boundary equals the closed form, |z|<={zc}",
            all(abs(r["z_engine_vs_closed_form"]) <= zc and r["engine_errors"] == 0 for r in p["rows"]),
            {"mtbf_s_unexpected_only": p["mtbf_s_unexpected_only"],
             "max_C_eq_R_for_90pct_s": p["closed_form_max_C_eq_R_for_90pct_s__unexpected_only"],
             "rows": p["rows"]})
    return v


# ---------------------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["smoke", "full"], required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--procs", type=int, default=4)
    args = ap.parse_args()
    cfg = SETTINGS[args.mode]
    out = Path(args.out) if args.out else HERE / "results" / ("smoke" if args.mode == "smoke" else "")
    wanted = [x for x in args.only.split(",") if x] or ["ckpt_stat", "ckpt_diff", "accounting", "queue", "published"]
    prov = provenance(args.mode, {"base_seed": BASE_SEED})
    funcs = {"ckpt_stat": run_ckpt_stat, "ckpt_diff": run_ckpt_diff, "accounting": run_accounting,
             "queue": run_queue, "published": run_published}
    results: dict = {}
    with mp.get_context("fork").Pool(args.procs) as pool:
        for name in wanted:
            t0 = time.time()
            print(f"[{name}] start", flush=True)
            results[name] = funcs[name](cfg, pool)
            write(out, name, results[name], prov, time.time() - t0)
            print(f"[{name}] done in {time.time() - t0:.1f}s", flush=True)
    verdict = evaluate(results)
    write(out, "verdict", {"criteria_results": verdict}, prov, 0.0)
    for item in verdict:
        print({True: "PASS ", False: "FAIL ", None: "INFO "}[item["pass"]] + item["id"])


if __name__ == "__main__":
    main()
