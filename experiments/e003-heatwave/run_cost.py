"""Cost timing runner (e003): dollars per token against carbon per token, real public series.

Stages (each run is short; forecasts are cached week by week so a stage can be repeated):

    python experiments/e003-heatwave/run_cost.py forecast --worker 0 --of 2   # fill the forecast cache
    python experiments/e003-heatwave/run_cost.py schedule --worker 0 --of 2   # plan and account every configuration (cached)
    python experiments/e003-heatwave/run_cost.py evaluate                      # bootstrap, write results/cost-v1.json

The price and carbon series are public data (``heatwave.data.public``); the workload is a scenario
assumption (``cost-scenario-v1.json``).  Needs numpy, scipy, pandas, statsforecast, torch,
timestral and the ``heatwave`` package (``PYTHONPATH`` may point at its repository).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from gpu_stack.research import heatwave_cost as hc  # noqa: E402

SCENARIO = HERE / "cost-scenario-v1.json"
CACHE = HERE / "cache"
SCHED = HERE / "cache" / "schedule"
OUT = HERE / "results" / "cost-v1.json"
INPUTS = HERE / "inputs"


def gpu_stack_git() -> dict:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()

    dirty = bool(git("status", "--porcelain", "--", ".", ":(exclude)experiments/e003-heatwave/results"))
    return {"repo": "gpu_stack", "commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"), "dirty": str(dirty).lower()}


def cache_digest(directory: Path, pattern: str) -> dict:
    """sha256 over the sorted (file name, file sha256) list of a cache directory, and the file count."""
    import hashlib
    from heatwave.provenance import sha256_file

    rows = sorted((p.name, sha256_file(p)) for p in directory.glob(pattern))
    return {"n_files": len(rows), "sha256": hashlib.sha256(repr(rows).encode()).hexdigest()}


def series_for(pair: str, scenario: dict) -> dict:
    """Hourly series of a pair plus the index positions of the test period and of the normalization window."""
    import pandas as pd

    d = hc.load_hourly_pair(pair)
    t = scenario["test"]
    start = pd.Timestamp(t["first_day_utc"], tz="UTC")
    i0 = int(d["index"].get_loc(start))
    n_hours = t["weeks"] * 7 * hc.HOURS_PER_DAY
    if i0 + n_hours > len(d["index"]):
        raise ValueError("the test period runs past the end of the series")
    d["test_start"] = i0
    d["n_test_hours"] = n_hours
    d["norm_slice"] = (i0 - t["normalization_days"] * hc.HOURS_PER_DAY, i0)
    return d


def forecast_tasks(scenario: dict) -> list:
    order = ["seasonal_naive_24", "timestral_5M", "timestral_28M", "timestral_28M_cov", "ets_24", "arima_seasonal", "timestral_209M"]
    tasks = []
    for fk in order:
        spec = scenario["forecasters"][fk]
        weeks = scenario["subsample_weeks"] if spec.get("subsample_only") else range(scenario["test"]["weeks"])
        for pair in scenario["pairs"]:
            for what in ("price", "carbon"):
                for w in weeks:
                    tasks.append((f"{pair}_{what}", fk, int(w)))
    return tasks


def forecast_stage(scenario: dict, worker: int, of: int, only: list) -> None:
    CACHE.mkdir(exist_ok=True)
    (CACHE / ".gitignore").write_text("*\n")
    data: dict = {}
    fc_cache: dict = {}
    todo = [t for t in forecast_tasks(scenario) if not only or t[1] in only][worker::of]
    ctx_cfg = scenario["context_hours"]
    horizon = scenario["decision"]["horizon_hours"]
    for series_key, fk, week in todo:
        path = hc.week_cache_path(CACHE, series_key, fk, week)
        if path.exists():
            continue
        pair, what = series_key.split("_")
        if pair not in data:
            data[pair] = series_for(pair, scenario)
        spec = scenario["forecasters"][fk]
        if fk not in fc_cache:
            fc_cache = {fk: hc.make_forecaster(spec)}
        ctx = ctx_cfg["timestral"] if spec["kind"] == "timestral" else ctx_cfg["classical"]
        t0 = time.time()
        known = None
        if spec.get("known_covariates"):
            if "known" not in data[pair]:
                data[pair]["known"] = hc.known_covariate_matrix(pair, data[pair]["index"])
            known = data[pair]["known"]["matrix"]
        vals = hc.compute_week(data[pair][what], data[pair]["test_start"], week, fc_cache[fk], ctx, horizon, known=known)
        tmp = path.with_suffix(f".{os.getpid()}.tmp.npz")
        np.savez_compressed(tmp, values=vals, levels=np.array(hc.QUANTILE_LEVELS))
        tmp.rename(path)
        print(f"{series_key} {fk} week {week}: {time.time() - t0:.1f}s", flush=True)


# ---------------------------------------------------------------------------------------------
# Schedule stage: one cached task = one policy configuration swept over all lambdas
# ---------------------------------------------------------------------------------------------

def planned_policies(scenario: dict) -> list:
    """Policies that solve the planning problem; the perfect-foresight upper bound is last."""
    return list(scenario["policies"]["planned"]) + [scenario["policies"]["upper_bound"]]


def day_blocks_for(scenario: dict, which: str) -> list:
    if which == "full":
        return [(0, scenario["test"]["weeks"] * 7)]
    return [(7 * w, 7) for w in scenario["subsample_weeks"]]


def schedule_task_list(scenario: dict) -> list:
    wl = scenario["workload"]
    q_default = scenario["planning_quantiles"]["default"]
    rho0 = wl["utilization"]
    f_risk = scenario["planning_quantiles"]["risk_sweep_flexible_fraction"]
    tasks = []
    for pair in scenario["pairs"]:
        for which in ("full", "sub"):
            pols = planned_policies(scenario) + (list(scenario["policies"]["subsample_extra"]) if which == "sub" else [])
            for pol in pols:
                for f in wl["flexible_fractions"]:
                    for w in wl["windows_hours"]:
                        tasks.append(dict(pair=pair, which=which, policy=pol, f=f, W=w, rho=rho0, q=q_default))
        for f in wl["flexible_fractions"]:
            for w in wl["windows_hours"]:
                tasks.append(dict(pair=pair, which="full", policy="offline_optimum", f=f, W=w, rho=rho0, q=q_default))
        for q in scenario["planning_quantiles"]["risk_sweep"]:
            if q == q_default:
                continue
            for pol in scenario["policies"]["planned"]:
                for w in wl["windows_hours"]:
                    tasks.append(dict(pair=pair, which="full", policy=pol, f=f_risk, W=w, rho=rho0, q=q))
        for rho in wl["utilization_sensitivity"]:
            for pol in wl["utilization_sensitivity_policies"]:
                hf = wl["headline"]
                tasks.append(dict(pair=pair, which="full", policy=pol, f=hf["flexible_fraction"], W=hf["window_hours"], rho=rho, q=q_default))
    return tasks


def task_key(t: dict) -> str:
    return f"{t['pair']}__{t['which']}__{t['policy']}__f{t['f']:g}_W{t['W']}_rho{t['rho']:g}_q{t['q']:g}"


class PairContext:
    """Series, normalization constants and forecast tables of one pair."""

    def __init__(self, pair: str, scenario: dict):
        self.pair = pair
        self.scenario = scenario
        self.d = series_for(pair, scenario)
        lo, hi = self.d["norm_slice"]
        self.norm = hc.zscore_constants(self.d["price"][lo:hi], self.d["carbon"][lo:hi])
        self.i0 = self.d["test_start"]
        self._tables: dict = {}

    def realised(self, blocks: list) -> tuple:
        idx = hc.block_hour_indices(blocks, self.i0)
        return self.d["price"][idx], self.d["carbon"][idx]

    def table(self, what: str, fk: str, weeks: list) -> np.ndarray:
        key = (what, fk, tuple(weeks))
        if key not in self._tables:
            parts = []
            for w in weeks:
                path = hc.week_cache_path(CACHE, f"{self.pair}_{what}", fk, w)
                parts.append(np.load(path)["values"].astype(np.float64))
            self._tables[key] = np.concatenate(parts, axis=0)
        return self._tables[key]

    def perfect(self, what: str, days: list) -> np.ndarray:
        t0 = [self.i0 + d * hc.HOURS_PER_DAY for d in days]
        H = self.scenario["decision"]["horizon_hours"]
        return hc.padded_future(self.d[what], t0, H)


def run_schedule_task(ctx: PairContext, scenario: dict, t: dict) -> dict:
    which = t["which"]
    real_blocks = day_blocks_for(scenario, which)
    weeks = list(range(scenario["test"]["weeks"])) if which == "full" else list(scenario["subsample_weeks"])
    days = [7 * w + k for w in weeks for k in range(7)]
    table_blocks = [(0, len(days))] if which == "full" else [(7 * j, 7) for j in range(len(weeks))]
    price_real, carbon_real = ctx.realised(real_blocks)
    model = hc.FlexModel(t["rho"], t["f"], t["W"], scenario["workload"]["power_cap"])
    lambdas = scenario["lambdas"]
    if t["policy"] == "offline_optimum":
        sums, flex = hc.sweep_offline(price_real, carbon_real, lambdas, model, ctx.norm)
        return {"sums": sums, "flex": flex, "fallbacks": 0}
    if t["policy"] == "perfect":
        pq, cq = ctx.perfect("price", days), ctx.perfect("carbon", days)
    else:
        j = hc.quantile_index(t["q"])
        pq = ctx.table("price", t["policy"], weeks)[:, :, j]
        cq = ctx.table("carbon", t["policy"], weeks)[:, :, j]
    sums, flex, fb = hc.sweep_forecast_policy(pq, cq, lambdas, model, ctx.norm, table_blocks, price_real, carbon_real)
    return {"sums": sums, "flex": flex, "fallbacks": fb}


def schedule_stage(scenario: dict, worker: int, of: int) -> None:
    SCHED.mkdir(exist_ok=True)
    (SCHED / ".gitignore").write_text("*\n")
    ctxs: dict = {}
    for t in schedule_task_list(scenario)[worker::of]:
        path = SCHED / f"{task_key(t)}.npz"
        if path.exists():
            continue
        if t["pair"] not in ctxs:
            ctxs[t["pair"]] = PairContext(t["pair"], scenario)
        t0 = time.time()
        try:
            res = run_schedule_task(ctxs[t["pair"]], scenario, t)
        except FileNotFoundError:
            print(f"{task_key(t)}: forecasts not cached yet, skipped", flush=True)
            continue
        tmp = path.with_suffix(f".{os.getpid()}.tmp.npz")
        np.savez_compressed(tmp, **res)
        tmp.rename(path)
        print(f"{task_key(t)}: {time.time() - t0:.1f}s fallbacks={res['fallbacks']}", flush=True)


# ---------------------------------------------------------------------------------------------
# Evaluate stage: bootstrap, per-token numbers, result JSON
# ---------------------------------------------------------------------------------------------

POLICY_ORDER = ["no_shift", "reactive", "seasonal_naive_24", "ets_24", "arima_seasonal", "timestral_5M", "timestral_28M", "timestral_28M_cov", "timestral_209M", "perfect", "offline_optimum"]


def load_fx() -> tuple:
    import csv
    path = INPUTS / "ecb_usd_per_eur_2026-04-27_2026-10-25.csv"
    rows = list(csv.DictReader(path.open()))
    rates = np.array([float(r["usd_per_eur"]) for r in rows])
    return float(rates.mean()), len(rates), path


def ratio_safe(num, den, tiny=1e-12):
    return np.where(np.abs(den) > tiny, num / np.where(np.abs(den) > tiny, den, 1.0), np.nan)


def curve_from_sums(sums, flex, none_sums, pf_sums, idx, terms, fx, level, f, W, rho) -> dict:
    """Per-lambda numbers (with bootstrap intervals) for one policy configuration."""
    L = sums.shape[0]
    fields: dict = {k: [] for k in [
        "price_paid", "carbon_paid", "electricity_usd_per_mtoken", "total_usd_per_mtoken", "co2_g_per_mtoken",
        "saving_pct_electricity", "saving_pct_total", "saving_pct_co2", "pf_share_cost", "pf_share_co2"]}
    cis: dict = {k: [] for k in fields}
    shifted_p, shifted_c, phi = [], [], []
    for l in range(L):
        p, c = hc.effective_prices(sums[l])
        p0, c0 = hc.effective_prices(none_sums[l])
        pp, cp = hc.effective_prices(pf_sums[l])
        bp, bc = hc.effective_prices(sums[l], idx)
        bp0, bc0 = hc.effective_prices(none_sums[l], idx)
        bpp, bcp = hc.effective_prices(pf_sums[l], idx)
        hw = terms["hardware_usd_per_mtoken"]
        e = terms["energy_mwh_per_mtoken"]

        def usd(price):
            return e * price * fx

        def point_and_boot(name, point, boot):
            fields[name].append(float(point))
            lo, hi = hc.percentile_interval(boot, level)
            cis[name].append([lo, hi])

        point_and_boot("price_paid", p, bp)
        point_and_boot("carbon_paid", c, bc)
        point_and_boot("electricity_usd_per_mtoken", usd(p), usd(bp))
        point_and_boot("total_usd_per_mtoken", usd(p) + hw, usd(bp) + hw)
        point_and_boot("co2_g_per_mtoken", e * c * 1000.0, e * bc * 1000.0)
        point_and_boot("saving_pct_electricity", 100 * (p0 - p) / p0, 100 * (bp0 - bp) / bp0)
        point_and_boot("saving_pct_total", 100 * (usd(p0) - usd(p)) / (usd(p0) + hw), 100 * (usd(bp0) - usd(bp)) / (usd(bp0) + hw))
        point_and_boot("saving_pct_co2", 100 * (c0 - c) / c0, 100 * (bc0 - bc) / bc0)
        point_and_boot("pf_share_cost", ratio_safe(p0 - p, p0 - pp), ratio_safe(bp0 - bp, bp0 - bpp))
        point_and_boot("pf_share_co2", ratio_safe(c0 - c, c0 - cp), ratio_safe(bc0 - bc, bc0 - bcp))
        fl = flex[l].sum(axis=0)
        shifted_p.append(fl[1] / fl[0] if fl[0] > 0 else float("nan"))
        shifted_c.append(fl[2] / fl[0] if fl[0] > 0 else float("nan"))
        phi.append(fl[0] / sums[l][:, 0].sum())
    p0, c0 = hc.effective_prices(none_sums[0])
    out = {"flexible_fraction": f, "window_hours": W, "utilization": rho, "lambda": None,
           "price_unshifted": float(p0), "carbon_unshifted": float(c0),
           "price_shifted": shifted_p, "carbon_shifted": shifted_c, "flexible_energy_share": phi}
    out.update(fields)
    out.update({k + "_ci": v for k, v in cis.items()})
    return out


def forecast_scores(ctx: PairContext, scenario: dict) -> dict:
    """Pinball-based scores of every forecaster on the test period (full weeks, and the sub-sampled weeks)."""
    from heatwave.forecast import QuantileForecast
    from heatwave.forecast import metrics as M

    H = scenario["decision"]["horizon_hours"]
    out: dict = {}
    for what in ("price", "carbon"):
        for fk, spec in scenario["forecasters"].items():
            sets = {"subsample": scenario["subsample_weeks"]}
            if not spec.get("subsample_only"):
                sets["full"] = list(range(scenario["test"]["weeks"]))
            for name, weeks in sets.items():
                days = [7 * w + k for w in weeks for k in range(7)]
                t0 = [ctx.i0 + d * hc.HOURS_PER_DAY for d in days]
                _, fut = hc.forecast_windows(ctx.d[what], t0, 1, H)
                vals = ctx.table(what, fk, weeks)
                rec = {}
                for tag, sl in (("h1_24", slice(0, 24)), ("h25_48", slice(24, 48))):
                    fc = QuantileForecast(values=vals[:, None, sl, :])
                    y = fut[:, None, sl]
                    rec[tag] = {"wql": M.wql(fc, y), "mae_median": M.mae_median(fc, y), "coverage_80": M.coverage(fc, y, 0.8)}
                out.setdefault(what, {}).setdefault(fk, {})[name] = rec
    return out


def evaluate_stage(scenario: dict) -> None:
    from heatwave.provenance import write_result

    tasks = schedule_task_list(scenario)
    missing = [task_key(t) for t in tasks if not (SCHED / f"{task_key(t)}.npz").exists()]
    if missing:
        raise SystemExit(f"{len(missing)} schedule tasks are not cached yet, e.g. {missing[:3]}; run the schedule stage first")
    terms = hc.reference_terms(scenario["reference_run"])
    fx_eur, fx_n, fx_path = load_fx()
    wl = scenario["workload"]
    bs = scenario["bootstrap"]
    lambdas = scenario["lambdas"]
    n_full = scenario["test"]["weeks"] * 7
    n_sub = 7 * len(scenario["subsample_weeks"])
    idx = {"full": hc.block_bootstrap_indices(n_full, bs["n"], bs["block_days"], bs["seed"]),
           "sub": hc.block_bootstrap_indices(n_sub, bs["n"], bs["block_days"], bs["seed"])}
    idx_iid = {"full": hc.block_bootstrap_indices(n_full, bs["n"], 1, bs["seed"] + 1)}
    out_pairs: dict = {}
    from heatwave.data.schema import PROCESSED
    from heatwave.provenance import sha256_file

    data_files = ["public_caiso_np15_lmp_dam", "public_caiso_carbon", "public_de_price_dam_1h", "public_de_generation"]
    inputs: list = [SCENARIO, fx_path] + [PROCESSED / f"{n}{ext}" for n in data_files for ext in (".parquet", ".meta.json")]
    for pair in scenario["pairs"]:
        ctx = PairContext(pair, scenario)
        fx = 1.0 if ctx.d["meta"]["currency"] == "USD" else fx_eur
        curves = {"full": {}, "sub": {}}
        fallbacks = 0
        pair_tasks = [t for t in tasks if t["pair"] == pair]
        loaded = {}
        for t in pair_tasks:
            z = np.load(SCHED / f"{task_key(t)}.npz")
            loaded[task_key(t)] = (z["sums"], z["flex"])
            fallbacks += int(z["fallbacks"])
        configs = sorted({(t["which"], t["f"], t["W"], t["rho"]) for t in pair_tasks})
        for which, f, W, rho in configs:
            blocks = day_blocks_for(scenario, which)
            price_real, carbon_real = ctx.realised(blocks)
            model = hc.FlexModel(rho, f, W, wl["power_cap"])
            none_s = hc.sweep_none(model, len(lambdas), price_real, carbon_real)
            react = hc.sweep_reactive(ctx.d["price"], ctx.d["carbon"], lambdas, model, ctx.norm, blocks, ctx.i0, price_real, carbon_real,
                                      scenario["reactive"]["lookback_hours"])
            pf_key = task_key(dict(pair=pair, which=which, policy="perfect", f=f, W=W, rho=rho, q=scenario["planning_quantiles"]["default"]))
            pf_s = loaded[pf_key][0]
            ix = idx[which]
            block = curves[which]
            block[hc.curve_key("no_shift", f, W, rho, None)] = curve_from_sums(none_s[0], none_s[1], none_s[0], pf_s, ix, terms, fx, bs["level"], f, W, rho)
            block[hc.curve_key("reactive", f, W, rho, None)] = curve_from_sums(react[0], react[1], none_s[0], pf_s, ix, terms, fx, bs["level"], f, W, rho)
            for t in pair_tasks:
                if (t["which"], t["f"], t["W"], t["rho"]) != (which, f, W, rho):
                    continue
                sums, flex = loaded[task_key(t)]
                block[hc.curve_key(t["policy"], f, W, rho, t["q"])] = curve_from_sums(sums, flex, none_s[0], pf_s, ix, terms, fx, bs["level"], f, W, rho)
        for which in curves:
            for c in curves[which].values():
                c["lambda"] = list(lambdas)
        out_pairs[pair] = {
            "series": ctx.d["meta"], "same_region": True, "usd_per_price_unit": fx,
            "normalization_constants": ctx.norm,
            "plan_fallbacks_total": fallbacks,
            "forecast_scores": forecast_scores(ctx, scenario),
            "curves": curves["full"], "curves_subsample": curves["sub"],
            "mean_price_test": float(ctx.realised(day_blocks_for(scenario, "full"))[0].mean()),
            "mean_carbon_test": float(ctx.realised(day_blocks_for(scenario, "full"))[1].mean()),
        }
    # round trip through the calculator for the headline curves
    hf = wl["headline"]
    roundtrip = {}
    doc = {"scenario": scenario, "pairs": out_pairs}
    for pair in scenario["pairs"]:
        curve = hc.lookup_curve(doc, pair, "timestral_28M", hf["flexible_fraction"], hf["window_hours"])
        fxp = out_pairs[pair]["usd_per_price_unit"]
        recs = []
        for lam in (0.0, 0.5, 1.0):
            est, carbon_kg, ti = hc.estimate_with_timing(scenario["reference_run"], curve, lam, fxp)
            i = scenario["lambdas"].index(lam)
            recs.append({
                "lambda": lam, "calculator_electricity_cost_usd": est.electricity_cost,
                "calculator_electricity_usd_per_mtoken": est.electricity_cost / (est.tokens / 1e6),
                "curve_electricity_usd_per_mtoken": curve["electricity_usd_per_mtoken"][i],
                "calculator_total_usd_per_mtoken": est.cost_per_million_tokens,
                "curve_total_usd_per_mtoken": curve["total_usd_per_mtoken"][i],
                "carbon_kg_reference_run": carbon_kg,
                "curve_co2_g_per_mtoken_times_run_mtokens_kg": curve["co2_g_per_mtoken"][i] * est.tokens / 1e6 / 1000.0,
                "timing_inputs": ti,
            })
        roundtrip[pair] = {"policy": "timestral_28M", "flexible_fraction": hf["flexible_fraction"], "window_hours": hf["window_hours"], "points": recs}
    result = {
        "scenario": scenario, "reference_run_terms": terms,
        "fx": {"usd_per_eur_mean_over_ecb_business_days": fx_eur, "n_days": fx_n,
               "source": "ECB euro foreign exchange reference rates, USD per EUR, 2026-04-27 to 2026-10-25 (https://data-api.ecb.europa.eu)"},
        "pairs": out_pairs, "calculator_roundtrip": roundtrip,
        "gpu_stack_git": gpu_stack_git(),
        "cache_digests": {"forecast": cache_digest(CACHE, "*.npz"), "schedule": cache_digest(SCHED, "*.npz")},
        "notes": [
            "Electricity price is the wholesale day-ahead price (CAISO NP15 LMP, DE-LU day-ahead); no retail adders, network fees or taxes.",
            "Hardware cost per token is the calculator's and does not depend on timing; total = electricity + hardware. DE electricity is converted at the mean ECB rate.",
            "CAISO carbon is the in-state intensity computed from CAISO's published CO2 and fuel mix (imports excluded). DE carbon is a production-based lifecycle proxy from IPCC AR5 medians, not an official figure.",
            "Workload (utilization, flexible share, windows, no idle power, constant energy per token) is a scenario assumption; nothing is measured on a real cluster.",
            "Forecasts are made at 00:00 UTC from history only; no day-ahead publications are used as inputs.",
        ],
    }
    write_result(OUT, result, script=__file__, data_kind="public", inputs=inputs,
                 notes="Public price and carbon series; modeled workload. The git field is the heatwave repository; the gpu_stack repository state is in result.gpu_stack_git.")


def main() -> None:
    global OUT, SCHED, SCENARIO
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["forecast", "schedule", "evaluate"])
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    ap.add_argument("--only", default="", help="comma-separated forecaster keys (forecast stage)")
    ap.add_argument("--scenario", default=str(SCENARIO))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--sched-dir", default=str(SCHED))
    a = ap.parse_args()
    OUT, SCHED, SCENARIO = Path(a.out), Path(a.sched_dir), Path(a.scenario)
    scenario = hc.load_scenario(SCENARIO)
    if a.stage == "forecast":
        forecast_stage(scenario, a.worker, a.of, [x for x in a.only.split(',') if x])
    elif a.stage == "schedule":
        schedule_stage(scenario, a.worker, a.of)
    else:
        evaluate_stage(scenario)


if __name__ == "__main__":
    main()
