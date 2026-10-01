"""Runner for study S001 (global sensitivity of the gpu_stack graph).

    PYTHONPATH=<repo> <venv python> -B experiments/s001-graph-sensitivity/run.py --smoke --out <scratch dir>
    PYTHONPATH=<repo> <venv python> -B experiments/s001-graph-sensitivity/run.py            # stage 2 only

--smoke runs tiny samples to check the code path and an analytic test function
(Ishigami). It prints no graph-derived sensitivity numbers.
The full run writes results/*.json and must only be started after the protocol
is frozen.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import scipy
import sympy

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import sens_lib as L  # noqa: E402
from gpu_stack import Registry  # noqa: E402
from gpu_stack.core.resolver import _boundary_family, resolve  # noqa: E402

# ---- frozen run configuration (see protocol.md, "Compute budget") ----
SEED = 20261001
N_POW_MAIN = 15          # Sobol base N = 2^15 for the primary rule R1
N_POW_ALT = 14           # width / zero-extension variants
N_BOOT_MAIN = 1000
N_BOOT_ALT = 500
N_BOOT_TAU = 1000
MORRIS_R = 100
REPLICATE_SEEDS = (SEED + 1, SEED + 2)
PRIMARY = ("P1_pythia70m_full_tco", "cost_per_token", "R1")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


def provenance(presets: dict, runtime: float | None = None) -> dict:
    gp = REPO / "gpu_stack"
    return {
        "git_head": git("rev-parse", "HEAD"),
        "git_status_gpu_stack": git("status", "--porcelain", "--", "gpu_stack"),
        "gpu_stack_py_tree_sha256": L.tree_sha256(gp),
        "script_sha256": {
            p.name: L.sha256_bytes(p.read_bytes()) for p in (HERE / "run.py", HERE / "sens_lib.py", HERE / "protocol.md")
            if p.exists()
        },
        "preset_sha256": {
            k: L.sha256_bytes(json.dumps(
                {"assignments": dict(p.assignments), "variants": dict(p.variants)},
                sort_keys=True).encode())
            for k, p in presets.items()
        },
        "seeds": {"main": SEED, "replicates": list(REPLICATE_SEEDS)},
        "versions": {
            "python": platform.python_version(), "numpy": np.__version__,
            "scipy": scipy.__version__, "sympy": sympy.__version__,
        },
        "runtime_seconds": runtime,
    }


# ---------------------------------------------------------------------------

def build_groups(ev: L.Evaluator) -> dict:
    s = ev.spec
    names = s.factor_names
    root_names = {r.name for r in Registry.roots()}
    groups: dict = {}

    def add(key, pred):
        cols = [i for i, n in enumerate(names) if pred(n)]
        if cols:
            groups[key] = cols

    for dom in sorted({n.split(".")[0] for n in names}):
        add(f"domain:{dom}", lambda n, d=dom: n.split(".")[0] == d)
    add("ALL_ROOTS", lambda n: n in root_names)
    add("ALL_PINS", lambda n: n not in root_names)
    add("LITHOGRAPHY", L.is_lith)
    add("NUCLEAR_QUARK", L.is_nuc)
    fams = sorted({_boundary_family(Registry.variables[n]) for n in names if n in root_names})
    for fam in fams:
        add(f"family:{fam}", lambda n, f=fam: n in root_names and _boundary_family(Registry.variables[n]) == f)
    return groups


def valid_rows(design: dict) -> np.ndarray:
    ok = np.isfinite(design["yA"]) & (design["yA"] > 0) & np.isfinite(design["yB"]) & (design["yB"] > 0)
    ok &= np.all(np.isfinite(design["yAB"]) & (design["yAB"] > 0), axis=0)
    if design["yG"].size:
        ok &= np.all(np.isfinite(design["yG"]) & (design["yG"] > 0), axis=0)
    return ok


def analyze(preset, model, rule, n_pow, seed, n_boot, debt, ext_debt, morris_r=0,
            with_tau=True) -> dict:
    t0 = time.time()
    t_step = float(resolve("training.t_step", assignments=dict(preset.assignments), variants=dict(preset.variants)).value)
    spec = L.make_spec(preset, model, rule, t_step)
    ev = L.Evaluator(preset, model, spec)
    k = ev.k
    groups = build_groups(ev)
    design = L.sobol_design_eval(ev, n_pow, seed, groups)
    ok = valid_rows(design)
    n_total = len(ok)
    design = {
        "yA": design["yA"][ok], "yB": design["yB"][ok], "yAB": design["yAB"][:, ok],
        "yG": design["yG"][:, ok] if design["yG"].size else design["yG"],
    }
    n_ok = int(ok.sum())
    out: dict = {
        "preset": preset.name, "target": model.target_name, "rule": rule, "seed": seed,
        "n_pow": n_pow, "n_rows": n_total, "n_valid_rows": n_ok, "k_factors": k,
        "held_inputs": spec.held, "tied": {a: list(b) for a, b in spec.tied.items()},
        "n_boot": n_boot, "expr_ops": model.n_ops,
    }
    if n_ok < 0.99 * n_total or n_ok < 16:
        out["status"] = "FAILED_INVALID_ROWS"
        return out
    # largest power of two <= n_ok, for prefix convergence
    n_use = 1 << int(math.floor(math.log2(n_ok)))
    gnames = list(groups)
    pts = {}
    ladder = [1 << m for m in range(10, int(math.log2(n_use)) + 1)] or [n_use]
    for n in ladder:
        pts[n] = {
            "log": L.sobol_point(design, n, L.log_transform),
            "raw": L.sobol_point(design, n, L.identity_transform),
        }
    final_log, final_raw = pts[n_use]["log"], pts[n_use]["raw"]
    boot = L.sobol_bootstrap(design, n_use, L.log_transform, n_boot, seed + 101) if n_boot else None
    boot_raw = L.sobol_bootstrap(design, n_use, L.identity_transform, n_boot, seed + 102) if n_boot else None
    if boot is not None:
        s1_lo, s1_hi = L.ci(boot[0])
        st_lo, st_hi = L.ci(boot[1])
        g_lo, g_hi = L.ci(boot[2]) if boot[2].size else (np.zeros(0), np.zeros(0))
        raw_st_lo, raw_st_hi = L.ci(boot_raw[1])
    else:
        z = np.full(k, np.nan)
        s1_lo = s1_hi = st_lo = st_hi = raw_st_lo = raw_st_hi = z
        g_lo = g_hi = np.full(len(gnames), np.nan)

    mor = L.morris(ev, morris_r, seed + 7) if morris_r else None
    root_names = {r.name for r in Registry.roots()}
    elast = L.local_elasticities(model, spec.factor_names)

    factors = []
    for i, n in enumerate(spec.factor_names):
        var = Registry.variables[n]
        is_root = n in root_names
        rec = {
            "name": n, "is_root": is_root, "units": var.units,
            "family": _boundary_family(var) if is_root else None,
            "root_debt": debt.get(n) if is_root else None,
            "dependents": ext_debt[n],
            "nominal": ev.nominal_full[n], "lo": float(spec.lo[i]), "hi": float(spec.hi[i]),
            "log_uniform": bool(spec.is_log[i]), "integer": bool(spec.is_int[i]),
            "note": spec.notes.get(n, ""),
            "in_resolved_formula": n in model.names,
            "S1": float(final_log["S1"][i]), "ST": float(final_log["ST"][i]),
            "S1_ci": [float(s1_lo[i]), float(s1_hi[i])],
            "ST_ci": [float(st_lo[i]), float(st_hi[i])],
            "ST_raw_Y": float(final_raw["ST"][i]), "ST_raw_Y_ci": [float(raw_st_lo[i]), float(raw_st_hi[i])],
            "class": L.classify(float(st_lo[i]), float(st_hi[i])) if boot is not None else None,
            "elasticity_nominal": elast.get(n),
        }
        if mor is not None:
            rec.update({"morris_mu_star": float(mor["mu_star"][i]), "morris_sigma": float(mor["sigma"][i])})
        factors.append(rec)

    group_rows = {}
    for gi, g in enumerate(gnames):
        group_rows[g] = {
            "members": [spec.factor_names[c] for c in groups[g]],
            "ST_group": float(final_log["STg"][gi]),
            "ST_group_ci": [float(g_lo[gi]), float(g_hi[gi])],
            "ST_group_raw_Y": float(final_raw["STg"][gi]),
            "sum_individual_ST": float(sum(final_log["ST"][c] for c in groups[g])),
        }
    # Groups with no factors have exactly zero influence by construction.
    for g in ("LITHOGRAPHY", "NUCLEAR_QUARK"):
        if g not in group_rows:
            group_rows[g] = {"members": [], "ST_group": 0.0, "ST_group_ci": [0.0, 0.0],
                             "note": "no member is a factor of this target: exactly zero by construction"}

    out.update({
        "status": "ok", "n_used_for_indices": n_use,
        "variance_log_target": float(final_log["V"]),
        "sum_S1": float(np.sum(final_log["S1"])), "sum_ST": float(np.sum(final_log["ST"])),
        "factors": factors, "groups": group_rows,
        "convergence": {
            str(n): {"ST": [float(x) for x in p["log"]["ST"]], "S1": [float(x) for x in p["log"]["S1"]]}
            for n, p in pts.items()
        },
        "nominal_target_value": model.nominal_value,
    })
    if with_tau and boot is not None:
        out["tau"] = tau_block(spec, ev, factors, group_rows, debt, ext_debt, boot, final_log["ST"], mor, seed)
    out["seconds"] = time.time() - t0
    return out


def tau_block(spec, ev, factors, group_rows, debt, ext_debt, boot, st_point, mor, seed) -> dict:
    root_names = [r.name for r in Registry.roots()]
    fnames = [f["name"] for f in factors]
    st = {f["name"]: f["ST"] for f in factors}
    res: dict = {}

    def one(label, names_, pts_x, boot_cols, y):
        y = np.asarray(y, float)
        x = np.asarray(pts_x, float)
        tau = L.kendall_tau(x, y)
        entry = {"n": len(names_), "tau_b": tau}
        if boot_cols is not None:
            tb = L.tau_bootstrap(boot_cols, y, seed + 303)
            tb = tb[np.isfinite(tb)]
            if len(tb):
                lo95, hi95 = float(np.percentile(tb, 5)), float(np.percentile(tb, 95))
                entry.update({
                    "ci90_two_sided": [float(np.percentile(tb, 5)), float(np.percentile(tb, 95))],
                    "ci95_two_sided": [float(np.percentile(tb, 2.5)), float(np.percentile(tb, 97.5))],
                    "verdict_vs_0.30": L.tau_verdict(lo95, hi95),
                })
        res[label] = entry

    # (a) PRIMARY: roots that are factors of this target (present roots, incl. tied drivers).
    cols = [i for i, n in enumerate(fnames) if n in debt]
    names_a = [fnames[i] for i in cols]
    one("a_present_roots", names_a, [st[n] for n in names_a], boot[1][:, cols], [debt[n] for n in names_a])
    # (b) all 619 roots; roots that are not factors have ST = 0.
    allst = np.zeros((boot[1].shape[0], len(root_names)))
    allpt = np.zeros(len(root_names))
    pos = {n: j for j, n in enumerate(root_names)}
    for i, n in enumerate(fnames):
        if n in pos:
            allst[:, pos[n]] = boot[1][:, i]
            allpt[pos[n]] = st[n]
    one("b_all_619_roots", root_names, allpt, allst, [debt[n] for n in root_names])
    # (c) all factors incl. pinned derived inputs, using the dependents count.
    one("c_all_factors_dependents", fnames, [st[n] for n in fnames], boot[1], [ext_debt[n] for n in fnames])
    # (d) family level: sum of root debt per family vs joint family ST, families with a factor.
    fam_keys = [g for g in group_rows if g.startswith("family:") and group_rows[g]["members"]]
    if len(fam_keys) >= 3:
        fam_w = []
        for g in fam_keys:
            fam = g.split(":", 1)[1]
            fam_w.append(sum(debt[r.name] for r in Registry.roots() if _boundary_family(r) == fam))
        res["d_family_level"] = {
            "n": len(fam_keys),
            "tau_b": L.kendall_tau([group_rows[g]["ST_group"] for g in fam_keys], fam_w),
            "families": fam_keys,
        }
    # (e) Morris cross-check against Sobol.
    if mor is not None:
        res["e_morris_mu_star_vs_ST"] = {
            "n": len(fnames),
            "tau_b": L.kendall_tau(mor["mu_star"], [st[n] for n in fnames]),
        }
    # (f) top-20 root-debt roots: how many matter?
    top20 = sorted(root_names, key=lambda n: (-debt[n], n))[:20]
    cls = {f["name"]: f["class"] for f in factors}
    res["f_top20_root_debt"] = {
        "names": top20,
        "is_factor": [n in cls for n in top20],
        "not_negligible": [bool(cls.get(n) in ("minor", "major")) for n in top20],
    }
    # (g) Top 10 by ST: where do they sit in the root-debt ranking (roots only, dense rank over 619)?
    rank = {n: 1 + sum(1 for m in root_names if debt[m] > debt[n]) for n in root_names}
    top_st = sorted([f for f in factors if f["is_root"]], key=lambda f: -f["ST"])[:10]
    res["g_top10_ST_roots_debt_rank"] = [{"name": f["name"], "ST": f["ST"], "debt_rank_of_619": rank[f["name"]]} for f in top_st]
    return res


# ---------------------------------------------------------------------------

def seed_agreement(a: dict, b_list: list) -> dict:
    """Rank agreement of ST between the main run and replicates on the same factors."""
    base = [f["ST"] for f in a["factors"]]
    out = []
    for b in b_list:
        other = [f["ST"] for f in b["factors"]]
        top = lambda arr: set(np.argsort(arr)[::-1][:10])  # noqa: E731
        out.append({
            "seed": b["seed"], "tau_b": L.kendall_tau(base, other),
            "max_abs_diff": float(np.max(np.abs(np.array(base) - np.array(other)))),
            "top10_overlap": len(top(base) & top(other)),
        })
    return {"replicates": out}


def convergence_checks(r: dict) -> dict:
    ns = sorted(int(n) for n in r["convergence"])
    last, prev = r["convergence"][str(ns[-1])]["ST"], r["convergence"][str(ns[-2])]["ST"] if len(ns) > 1 else None
    chk: dict = {"ladder": ns}
    if prev is not None:
        sig = [i for i, v in enumerate(last) if v >= L.NEGLIGIBLE_ST]
        d = max((abs(last[i] - prev[i]) for i in sig), default=0.0)
        chk["C1_max_abs_change_last_doubling_nonnegligible"] = d
        chk["C1_pass"] = d <= 0.02
    hw = [(f["ST_ci"][1] - f["ST_ci"][0]) / 2 for f in r["factors"]]
    chk["C2_max_ci_halfwidth"] = float(max(hw)) if hw else None
    chk["C2_pass"] = bool(hw) and max(hw) <= 0.02
    return chk


def run_full(out_dir: Path) -> None:
    t_start = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)
    presets = L.get_presets()
    debt = L.root_debt()
    all_vars = Registry.variables
    ext_debt = {n: len(v.dependents(include_constraints=False)) for n, v in all_vars.items()}
    summary: dict = {"primary": PRIMARY, "pairs": {}}
    structure: dict = {}
    for pkey, preset in presets.items():
        for tlabel in L.TARGETS:
            t0 = time.time()
            model = L.build_model(preset, tlabel)
            structure[f"{pkey}/{tlabel}"] = L.structure_report(preset, model, debt) | {
                "nominal_target_value": model.nominal_value, "build_seconds": model.build_seconds}
            plans = [("R1", N_POW_MAIN, N_BOOT_MAIN, MORRIS_R, SEED, True)]
            plans += [(r, N_POW_ALT, N_BOOT_ALT, 0, SEED, True) for r in ("R1_f1.25", "R1_f4", "R4")]
            for rule, n_pow, n_boot, mr, seed, wt in plans:
                res = analyze(preset, model, rule, n_pow, seed, n_boot, debt, ext_debt, mr, wt)
                if rule == "R1":
                    res["convergence_checks"] = convergence_checks(res) if res.get("status") == "ok" else None
                if (pkey, tlabel, rule) == PRIMARY and res.get("status") == "ok":
                    reps = [analyze(preset, model, rule, N_POW_ALT, s, 0, debt, ext_debt, 0, False)
                            for s in REPLICATE_SEEDS]
                    res["seed_replicates"] = seed_agreement(res, reps)
                (out_dir / f"sobol__{pkey}__{tlabel}__{rule}.json").write_text(json.dumps(res, indent=1, default=float))
                summary["pairs"][f"{pkey}/{tlabel}/{rule}"] = {
                    "status": res.get("status"), "k": res.get("k_factors"),
                    "tau_a_present_roots": (res.get("tau") or {}).get("a_present_roots"),
                    "tau_b_all_619": (res.get("tau") or {}).get("b_all_619_roots"),
                    "LITH_ST_group": (res.get("groups") or {}).get("LITHOGRAPHY", {}).get("ST_group"),
                    "NUC_ST_group": (res.get("groups") or {}).get("NUCLEAR_QUARK", {}).get("ST_group"),
                    "convergence_checks": res.get("convergence_checks"),
                }
            print(f"done {pkey}/{tlabel} in {time.time()-t0:.0f}s", flush=True)
    (out_dir / "structure.json").write_text(json.dumps(structure, indent=1, default=float))
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=float))
    (out_dir / "provenance.json").write_text(json.dumps(provenance(presets, time.time() - t_start), indent=1))


# ---------------------------------------------------------------------------
# Smoke test: code path and analytic check only
# ---------------------------------------------------------------------------

def ishigami_check(n_pow: int = 13) -> dict:
    """Validate the estimators on Ishigami (a=7, b=0.1). Analytic: S1=(0.3139,0.4424,0), ST=(0.5576,0.4424,0.2437)."""
    from scipy.stats import qmc

    def f(U):
        x = -np.pi + 2 * np.pi * U
        return np.sin(x[:, 0]) + 7 * np.sin(x[:, 1]) ** 2 + 0.1 * x[:, 2] ** 4 * np.sin(x[:, 0])

    k = 3
    M = qmc.Sobol(d=2 * k, scramble=True, seed=1).random_base2(n_pow)
    A, B = M[:, :k], M[:, k:]
    yA, yB = f(A), f(B)
    yAB = np.empty((k, len(A)))
    for i in range(k):
        T = A.copy()
        T[:, i] = B[:, i]
        yAB[i] = f(T)
    design = {"yA": yA, "yB": yB, "yAB": yAB, "yG": np.zeros((0, len(A)))}
    p = L.sobol_point(design, len(A), L.identity_transform)
    S1, ST, _ = L.sobol_bootstrap(design, len(A), L.identity_transform, 200, 5)
    exp_s1, exp_st = np.array([0.3139, 0.4424, 0.0]), np.array([0.5576, 0.4424, 0.2437])
    lo, hi = L.ci(ST)
    return {
        "S1": p["S1"].round(3).tolist(), "ST": p["ST"].round(3).tolist(),
        "max_abs_err_S1": float(np.max(np.abs(p["S1"] - exp_s1))),
        "max_abs_err_ST": float(np.max(np.abs(p["ST"] - exp_st))),
        "ST_ci_contains_truth": bool(np.all((lo <= exp_st) & (exp_st <= hi))),
    }


def smoke(out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    problems = []
    ish = ishigami_check()
    print("ishigami (analytic function, not graph):", ish)
    if ish["max_abs_err_S1"] > 0.03 or ish["max_abs_err_ST"] > 0.03:
        problems.append("estimators off on Ishigami")
    # root-debt helper agrees with the CLI
    cli = json.loads(subprocess.run(
        [sys.executable, "-B", "-m", "gpu_stack.cli", "root-debt", "--json", "--limit", "700"],
        cwd=REPO, capture_output=True, text=True, env={**__import__("os").environ, "PYTHONPATH": str(REPO)},
    ).stdout)
    debt = L.root_debt()
    mism = [r["variable"] for r in cli["rows"] if debt[r["variable"]] != r["dependents"]]
    print(f"root-debt helper vs CLI: {len(cli['rows'])} rows, {len(mism)} mismatches, total_roots={cli['total_roots']}")
    if mism or cli["total_roots"] != len(debt):
        problems.append("root debt mismatch")
    ext_debt = {n: len(v.dependents(include_constraints=False)) for n, v in Registry.variables.items()}
    presets = L.get_presets()
    for pkey, preset in presets.items():
        for tlabel in L.TARGETS:
            model = L.build_model(preset, tlabel)
            st = L.structure_report(preset, model, debt)
            for rule in ("R1", "R4"):
                res = analyze(preset, model, rule, 5, 1, 4, debt, ext_debt, morris_r=2, with_tau=True)
                (out_dir / f"smoke__{pkey}__{tlabel}__{rule}.json").write_text(json.dumps(res, default=float))
                bad = res.get("status") != "ok" or "tau" not in res
                print(f"smoke {pkey}/{tlabel}/{rule}: status={res.get('status')} k={res.get('k_factors')} "
                      f"valid_rows={res.get('n_valid_rows')}/{res.get('n_rows')} tau_blocks={sorted((res.get('tau') or {}))}")
                if bad:
                    problems.append(f"{pkey}/{tlabel}/{rule} did not complete")
            del st
    prov = provenance(presets, 0.0)
    (out_dir / "smoke_provenance.json").write_text(json.dumps(prov, indent=1))
    print("provenance keys:", sorted(prov))
    print("SMOKE", "FAILED: " + "; ".join(problems) if problems else "OK")
    return 1 if problems else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", type=Path, default=HERE / "results")
    a = ap.parse_args()
    sys.exit(smoke(a.out) if a.smoke else (run_full(a.out) or 0))
