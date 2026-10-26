"""Power-cap packing experiment for the e003 Heatwave simulator (simulated data, task T06a).

Stages (each stays well under 20 minutes on 2 cores; run them in this order)::

    python experiments/e003-heatwave/run_packing.py calibrate
    python experiments/e003-heatwave/run_packing.py collect [--shard 0/2]
    python experiments/e003-heatwave/run_packing.py train
    python experiments/e003-heatwave/run_packing.py eval --group GROUP [--shard 0/2]
    python experiments/e003-heatwave/run_packing.py merge

``GROUP`` is one of ``t5m-fixed``, ``t28m-fixed``, ``seasonal-naive``, ``ets``,
``arima``, ``reactive``, ``learned``, ``oracle`` (``oracle`` needs the
``t5m-fixed`` runs at q=0.9 for its reference ratio path).  Part files go to
``results/packing-v1-parts/`` (each with script hash, git commit and seeds);
``merge`` writes ``results/packing-v1.json`` through ``heatwave.provenance``.
Existing part files are kept, so a stage can be resumed.  Run heavy stages
under ``nice -n 10``.  ETS and ARIMA refit once per hour of decisions (see
``policies.forecast_refresh_bins`` in the scenario); the setting is recorded in
every run's metrics.

Every quantity is simulated.  The scenario is ``packing-scenario-v1.json``;
power levels, cooling and thermal parameters are read from the simulator
scenario and the measured e002 ratios it points to, never typed here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from gpu_stack.research import heatwave_packing as hp  # noqa: E402
from gpu_stack.research.heatwave_sim import load_scenario  # noqa: E402

SCENARIO = HERE / "packing-scenario-v1.json"
SIM_SCENARIO = HERE / json.loads(SCENARIO.read_text())["base_scenario"]
E002_RAW = ROOT / "docs" / "data" / "e002-checkpoint-power-raw-v1.json"
PARTS = HERE / "results" / "packing-v1-parts"
OUT = HERE / "results" / "packing-v1.json"
CAL_PATH = PARTS / "calibration.json"
MODEL_PATH = PARTS / "model.json"


# ---------------------------------------------------------------------------
# provenance and files
# ---------------------------------------------------------------------------


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()

    dirty = bool(git("status", "--porcelain", "--", ".", ":(exclude)experiments/e003-heatwave/results"))
    return {"commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"), "dirty": str(dirty).lower()}


def part_provenance(**extra) -> dict:
    return {
        "script": str(Path(__file__).resolve().relative_to(ROOT)),
        "script_sha256": sha_file(Path(__file__)),
        "module_sha256": sha_file(ROOT / "gpu_stack" / "research" / "heatwave_packing.py"),
        "scenario_sha256": sha_file(SCENARIO),
        "git": git_state(),
        "data_kind": "simulated",
        **extra,
    }


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.JSONEncoder(indent=1, allow_nan=False).encode(_clean(obj)) + "\n")


def _clean(v):
    if isinstance(v, np.ndarray):
        return _clean(v.tolist())
    if isinstance(v, np.generic):
        return _clean(v.item())
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, float) and not np.isfinite(v):
        return None
    return v


def load_models() -> dict:
    cal = json.loads(CAL_PATH.read_text())["result"]
    return {
        sid: hp.SiteModel(d["site_id"], d["n_gpus"], d["idle_w"], d["full_w"], d["cap_w"], d["utc_offset_h"])
        for sid, d in cal["sites"].items()
    }


def setup():
    packing = hp.load_packing_scenario(SCENARIO)
    sim = load_scenario(SIM_SCENARIO)
    return packing, sim, hp.PackingSettings.from_scenario(packing)


def shard_filter(items: list, shard: str) -> list:
    i, n = (int(x) for x in shard.split("/"))
    return [x for k, x in enumerate(items) if k % n == i]


# ---------------------------------------------------------------------------
# forecasters
# ---------------------------------------------------------------------------


def make_forecaster(name: str, packing: dict, threads: int):
    ep = packing["episode"]
    season = int(round(86400.0 / ep["forecast_bin_s"]))
    if name.startswith("timestral-"):
        from heatwave.forecast.timestral_fc import TimestralForecaster

        return TimestralForecaster(size=name.split("-")[1], threads=threads)
    from heatwave.forecast import ARIMAForecaster, ETSForecaster, SeasonalNaiveForecaster

    if name == "seasonal-naive":
        return SeasonalNaiveForecaster(season_length=season, max_context=int(ep["context_bins"]))
    if name == "ets":
        return ETSForecaster(season_length=1, max_context=season)
    if name == "arima":
        return ARIMAForecaster(order=(2, 1, 1), max_context=season)
    raise ValueError(f"unknown forecaster {name!r}")


GROUPS = {
    "t5m-fixed": "timestral-5M",
    "t28m-fixed": "timestral-28M",
    "seasonal-naive": "seasonal-naive",
    "ets": "ets",
    "arima": "arima",
}


def policy_id(forecaster: str, label: str) -> str:
    return f"{forecaster}/{label}"


def fixed_levels(packing: dict, forecaster: str, opts: argparse.Namespace) -> list:
    if forecaster in packing["policies"]["full_grid_forecasters"]:
        return list(hp.QUANTILE_LEVELS)[:: max(1, opts.grid_stride)]
    if opts.subset_q:
        return [float(x) for x in opts.subset_q.split(",")]
    return list(packing["policies"]["subset_q"])


def used_seeds(packing: dict, key: str, opts: argparse.Namespace) -> list:
    n = {"train": opts.n_train, "test": opts.n_test}[key]
    seeds = list(packing["seeds"][key])
    return seeds[:n] if n > 0 else seeds


def option_record(opts: argparse.Namespace) -> dict:
    return {"n_train": opts.n_train, "n_test": opts.n_test, "grid_stride": opts.grid_stride, "subset_q": opts.subset_q}


# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------


def stage_calibrate() -> None:
    packing, sim, _ = setup()
    from heatwave.forecast import QUANTILE_LEVELS

    assert tuple(QUANTILE_LEVELS) == hp.QUANTILE_LEVELS, "quantile grid differs from heatwave.forecast"
    cal = hp.calibrate_sites(sim, packing)
    cal.pop("models")
    write_json(CAL_PATH, {"provenance": part_provenance(seed=packing["seeds"]["calibration"],
                                                         sim_scenario_sha256=sha_file(SIM_SCENARIO),
                                                         e002_raw_sha256=sha_file(E002_RAW)),
                          "result": cal})
    print(f"wrote {CAL_PATH}")


def run_one(packing, sim, settings, models, seed: int, controller_factory):
    ep = hp.build_episode(packing, sim, models, seed)
    site_ids = list(models)
    ctrl = controller_factory(ep, site_ids)
    t0 = time.time()
    res = hp.run_episode(ep, ctrl)
    wall = time.time() - t0
    return ep, ctrl, res, wall


def stage_collect(args) -> None:
    packing, sim, settings = setup()
    models = load_models()
    seeds = shard_filter(used_seeds(packing, "train", args), args.shard)
    fc = make_forecaster("timestral-5M", packing, args.threads)
    for seed in seeds:
        out = PARTS / f"collect-seed{seed}.json"
        if out.exists():
            continue

        def factory(ep, site_ids):
            return hp.PackingController(
                ep.jobs, models, site_ids, settings, ep.hour0_local, mode="forecast", forecaster=fc,
                policy=hp.RandomQ(seed), use_covariates="timestral-5M" in packing["policies"]["use_covariates"],
                log_situations=True,
            )

        ep, ctrl, res, wall = run_one(packing, sim, settings, models, seed, factory)
        metrics = hp.episode_metrics(res, ctrl, ep, settings)
        sit = ctrl.situations()
        p_min, b_min = ctrl.minute_records()
        np.savez_compressed(PARTS / f"collect-seed{seed}.npz", p_min=p_min, b_min=b_min, **sit)
        write_json(out, {"provenance": part_provenance(seed=seed, role="train-exploration", forecaster="timestral-5M",
                                                         policy="random-q", options=option_record(args)),
                         "result": {"metrics": metrics, "wall_s": wall, "n_situations": int(sit["t"].shape[0]),
                                    "draws": ep.draws}})
        print(f"collect seed {seed}: {sit['t'].shape[0]} situations, wall {wall:.0f}s", flush=True)


def stage_train(args) -> None:
    packing, sim, settings = setup()
    models_d = load_models()
    models = list(models_d.values())
    penalties = list(packing["penalty"]["sweep_usd_per_kwh"])
    train_seeds = used_seeds(packing, "train", args)
    val_seeds = set(train_seeds[-2:])
    parts = {"train": [], "val": []}
    for seed in train_seeds:
        z = np.load(PARTS / f"collect-seed{seed}.npz")
        sit = {k: z[k] for k in z.files if k not in ("p_min", "b_min")}
        costs, value = hp.hindsight_costs(sit, z["p_min"], z["b_min"], models, penalties, settings.call_s, settings.reward_window_s)
        usable = sit["t"] + settings.reward_window_s <= settings.horizon_s
        X_all, C_all, V_all = [], [], []
        for pi, lam in enumerate(penalties):
            X = sit["x"].copy()
            X[:, hp.FEATURE_NAMES.index("log_penalty")] = np.log(lam)
            X_all.append(X[usable])
            C_all.append(costs[pi][usable])
            V_all.append(value[usable])
        parts["val" if seed in val_seeds else "train"].append((np.concatenate(X_all), np.concatenate(C_all), np.concatenate(V_all)))

    def stack(items):
        return tuple(np.concatenate([it[i] for it in items]) for i in range(3))

    Xtr, Ctr, Vtr = stack(parts["train"])
    Xva, Cva, Vva = stack(parts["val"])
    lc = packing["learning"]
    grid = []
    best = None
    for bw in lc["bandwidths"]:
        for rg in lc["ridges"]:
            m = hp.CostSensitiveModel(n_rff=lc["n_rff"], bandwidth=bw, ridge=rg, seed=lc["model_seed"]).fit(Xtr, Ctr, Vtr)
            row = {"bandwidth": bw, "ridge": rg, "val_regret_per_value": m.regret(Xva, Cva, Vva),
                   "train_regret_per_value": m.regret(Xtr, Ctr, Vtr)}
            grid.append(row)
            if best is None or row["val_regret_per_value"] < best[0]["val_regret_per_value"]:
                best = (row, m)
    row = best[0]
    Xall, Call, Vall = np.concatenate([Xtr, Xva]), np.concatenate([Ctr, Cva]), np.concatenate([Vtr, Vva])
    final = hp.CostSensitiveModel(n_rff=lc["n_rff"], bandwidth=row["bandwidth"], ridge=row["ridge"], seed=lc["model_seed"]).fit(Xall, Call, Vall)
    # reference regrets on all rows: always the median level, and the best single level in hindsight
    ref = {
        "median_level_regret_per_value": float(Call[:, hp.MEDIAN_INDEX].sum() / Vall.sum()),
        "best_single_level_regret_per_value": float(Call.sum(axis=0).min() / Vall.sum()),
        "best_single_level": float(hp.QUANTILE_LEVELS[int(Call.sum(axis=0).argmin())]),
        "refit_regret_per_value_on_all": final.regret(Xall, Call, Vall),
    }
    write_json(MODEL_PATH, {"provenance": part_provenance(train_seeds=train_seeds, validation_seeds=sorted(val_seeds),
                                                            penalties=penalties, options=option_record(args)),
                            "result": {"selected": row, "grid": grid, "reference_regrets": ref,
                                       "n_rows_train": int(Xtr.shape[0]), "n_rows_validation": int(Xva.shape[0]),
                                       "feature_names": hp.FEATURE_NAMES, "model": final.to_dict()}})
    print(f"wrote {MODEL_PATH}: selected {row}")


def eval_jobs(packing: dict, group: str, opts: argparse.Namespace) -> list:
    """List of (policy_id, kind, forecaster, level_or_penalty)."""
    jobs = []
    if group in GROUPS:
        fcn = GROUPS[group]
        for q in fixed_levels(packing, fcn, opts):
            jobs.append((policy_id(fcn, f"q{q:g}"), "fixed", fcn, q))
    elif group == "reactive":
        jobs.append(("reactive", "reactive", None, None))
    elif group == "oracle":
        jobs.append(("oracle", "oracle", None, None))
    elif group == "learned":
        for lam in packing["penalty"]["sweep_usd_per_kwh"]:
            jobs.append((policy_id("timestral-5M", f"learned@{lam:g}"), "learned", "timestral-5M", lam))
    else:
        raise ValueError(f"unknown group {group!r}")
    return jobs


def stage_eval(args) -> None:
    packing, sim, settings = setup()
    models = load_models()
    seeds = used_seeds(packing, "test", args)
    jobs = [(j, s) for j in eval_jobs(packing, args.group, args) for s in seeds]
    jobs = shard_filter(jobs, args.shard)
    cache = {}
    learned = None
    if args.group == "learned":
        learned = hp.LearnedQ(hp.CostSensitiveModel.from_dict(json.loads(MODEL_PATH.read_text())["result"]["model"]))
    for (pid, kind, fcn, arg), seed in jobs:
        out = PARTS / "eval" / f"{pid.replace('/', '__').replace('@', '_at_')}__seed{seed}.json"
        if out.exists():
            continue
        use_cov = fcn in packing["policies"]["use_covariates"] if fcn else False
        if fcn and fcn not in cache:
            cache[fcn] = make_forecaster(fcn, packing, args.threads)
        pen = float(packing["penalty"]["default_usd_per_kwh"])

        def factory(ep, site_ids):
            if kind == "reactive":
                return hp.PackingController(ep.jobs, models, site_ids, settings, ep.hour0_local, mode="reactive")
            if kind == "oracle":
                tr = np.load(PARTS / f"trace-seed{seed}.npz")["ratio_bins"]
                return hp.PackingController(ep.jobs, models, site_ids, settings, ep.hour0_local, mode="oracle", oracle_ratio=tr)
            policy = hp.FixedQ(arg) if kind == "fixed" else learned
            penalty = float(arg) if kind == "learned" else pen
            return hp.PackingController(
                ep.jobs, models, site_ids, settings, ep.hour0_local, mode="forecast", forecaster=cache[fcn], policy=policy,
                penalty_usd_per_kwh=penalty, use_covariates=use_cov,
                forecast_refresh_bins=int(packing["policies"]["forecast_refresh_bins"].get(fcn, 1)),
            )

        ep, ctrl, res, wall = run_one(packing, sim, settings, models, seed, factory)
        metrics = hp.episode_metrics(res, ctrl, ep, settings)
        if pid == "timestral-5M/q0.9":
            np.savez_compressed(PARTS / f"trace-seed{seed}.npz", ratio_bins=ctrl.ratio_bins())
        write_json(out, {"provenance": part_provenance(seed=seed, policy=pid, forecaster=fcn, use_covariates=use_cov,
                                                         options=option_record(args)),
                         "result": {"policy": pid, "kind": kind, "seed": seed, "metrics": metrics, "wall_s": wall,
                                    "draws": ep.draws}})
        print(f"{pid} seed {seed}: gpu_h {metrics['gpu_hours']:.0f} viol {metrics['violation_rate']:.3f} "
              f"over {metrics['energy_above_cap_kwh']:.2f} kWh wall {wall:.0f}s", flush=True)


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

METRIC_KEYS = ("gpu_hours", "value_usd", "jobs_admitted", "jobs_completed", "violation_rate", "energy_above_cap_kwh",
               "seconds_above_cap", "stranded_kwh", "mean_power_over_cap", "gpu_hours_multisite_jobs", "max_excess_w")


def stage_merge(args) -> None:
    packing, sim, settings = setup()
    bs = packing["bootstrap"]
    penalties = list(packing["penalty"]["sweep_usd_per_kwh"])
    runs: dict = {}
    files = sorted((PARTS / "eval").glob("*.json"))
    for f in files:
        rec = json.loads(f.read_text())["result"]
        runs.setdefault(rec["policy"], {})[rec["seed"]] = rec["metrics"]
    seeds = sorted({s for by in runs.values() for s in by})
    cal = json.loads(CAL_PATH.read_text())["result"]
    summary = {}
    for pid, by_seed in sorted(runs.items()):
        ordered = [by_seed[s] for s in seeds if s in by_seed]
        ent = {"n_seeds": len(ordered), "seeds": [s for s in seeds if s in by_seed]}
        for key in METRIC_KEYS:
            ent[key] = hp.bootstrap_ci([m[key] for m in ordered], bs["n_boot"], bs["seed"], bs["level"])
        ent["net_value_usd"] = {
            f"{lam:g}": hp.bootstrap_ci([hp.net_value(m, lam) for m in ordered], bs["n_boot"], bs["seed"], bs["level"])
            for lam in penalties
        }
        summary[pid] = ent

    # Pareto data per forecaster family: violation rate against GPU-hours (means and intervals).
    families: dict = {}
    for pid, ent in summary.items():
        fam, _, label = pid.partition("/")
        if not label:
            fam, label = "reference", pid
        families.setdefault(fam, []).append({
            "policy": pid, "label": label,
            "violation_rate": ent["violation_rate"], "gpu_hours": ent["gpu_hours"], "value_usd": ent["value_usd"],
            "energy_above_cap_kwh": ent["energy_above_cap_kwh"],
        })
    points = [(p["policy"], p["violation_rate"]["mean"], p["gpu_hours"]["mean"]) for fam in families.values() for p in fam]
    frontier = []
    for name, v, g in points:
        dominated = any((v2 <= v and g2 >= g) and (v2 < v or g2 > g) for _, v2, g2 in points)
        if not dominated:
            frontier.append(name)

    # Paired differences of the learned policy against every other policy, per penalty.
    paired = {}
    for lam in penalties:
        lid = policy_id("timestral-5M", f"learned@{lam:g}")
        if lid not in runs:
            continue
        rows = {}
        for pid, by_seed in runs.items():
            if pid == lid or pid.startswith("timestral-5M/learned@"):
                continue
            common = [s for s in seeds if s in by_seed and s in runs[lid]]
            if not common:
                continue
            d = [hp.net_value(runs[lid][s], lam) - hp.net_value(by_seed[s], lam) for s in common]
            rows[pid] = hp.bootstrap_ci(d, bs["n_boot"], bs["seed"], bs["level"])
        paired[f"{lam:g}"] = {"learned_policy": lid, "net_value_difference_usd_vs": rows}

    selection_by_penalty = {}
    for lam in penalties:
        key = f"{lam:g}"
        fixed = {pid: e["net_value_usd"][key]["mean"] for pid, e in summary.items() if "/q" in pid}
        if fixed:
            best = max(fixed, key=fixed.get)
            selection_by_penalty[key] = {"best_fixed_policy_by_mean_net_value_on_test_seeds": best, "mean_net_value_usd": fixed[best]}

    model_rec = json.loads(MODEL_PATH.read_text())["result"] if MODEL_PATH.exists() else None
    collect = [json.loads(p.read_text())["result"] for p in sorted(PARTS.glob("collect-seed*.json"))]
    result = {
        "data_kind": "simulated",
        "scenario_id": packing["scenario_id"],
        "scenario": {k: packing[k] for k in ("episode", "cap", "jobs", "heatwave_draw", "events", "penalty", "reward_window_s",
                                              "queue_order", "reactive", "policies", "learning", "bootstrap", "seeds")},
        "assumptions": packing["assumptions"],
        "run_options": sorted({json.JSONEncoder(sort_keys=True).encode(json.loads(f.read_text())["provenance"].get("options")) for f in files}),
        "test_seeds_run": seeds,
        "calibration": cal,
        "metric_definitions": {
            "window": "evaluation window = last (horizon_s - warmup_s) seconds of each episode; warm-up excluded",
            "gpu_hours": "useful GPU-hours delivered in the window (net of work lost to faults), summed over jobs",
            "value_usd": "sum over jobs of window GPU-hours times value per GPU-hour",
            "violation_rate": "fraction of decision intervals (300 s) in the window in which any site's power exceeded its cap, at the simulator's 10 s control-step samples",
            "energy_above_cap_kwh": "sum over sites and samples of the excess over the cap, in kWh",
            "seconds_above_cap": "number of site-samples above the cap times the sample length, summed over sites",
            "stranded_kwh": "headroom below the cap (kWh, both sites) in intervals where a queued job that fit in free GPUs was refused",
            "net_value_usd": "value_usd minus penalty (USD per kWh above cap) times energy_above_cap_kwh",
            "ci": "percentile bootstrap interval of the mean over held-out episodes",
        },
        "policies": summary,
        "pareto": {"families": families, "non_dominated_by_mean": frontier,
                   "axes": {"x": "violation_rate (mean over held-out episodes)", "y": "gpu_hours (mean)"}},
        "paired_net_value_difference": paired,
        "best_fixed_by_penalty": selection_by_penalty,
        "learned_model": None if model_rec is None else {k: v for k, v in model_rec.items() if k != "model"},
        "training_episodes": [{"sim_seed": c["draws"]["sim_seed"], "n_situations": c["n_situations"]} for c in collect],
        "per_seed_metrics": {pid: {str(s): m for s, m in by.items()} for pid, by in sorted(runs.items())},
    }
    from heatwave.provenance import write_result

    inputs = [SCENARIO, SIM_SCENARIO, E002_RAW, CAL_PATH, MODEL_PATH] + files
    record = write_result(OUT, result, script=__file__, data_kind="simulated", inputs=inputs,
                          notes="All outputs simulated. Held-out episodes only; training episodes are listed separately.")
    record["provenance"]["git"] = git_state()
    record["provenance"]["script"] = str(Path(__file__).resolve().relative_to(ROOT))
    record["provenance"]["inputs"] = {str(Path(p).resolve().relative_to(ROOT)): sha_file(Path(p)) for p in inputs if Path(p).exists()}
    OUT.write_text(json.JSONEncoder(indent=1, allow_nan=False).encode(record) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["calibrate", "collect", "train", "eval", "merge"])
    ap.add_argument("--group", default="")
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--n-train", type=int, default=0, help="use only the first N training seeds (0 = all)")
    ap.add_argument("--n-test", type=int, default=0, help="use only the first N test seeds (0 = all)")
    ap.add_argument("--grid-stride", type=int, default=1, help="use every S-th of the 21 levels for full-grid forecasters")
    ap.add_argument("--subset-q", default="", help="comma list replacing policies.subset_q")
    args = ap.parse_args()
    if args.stage == "calibrate":
        stage_calibrate()
    elif args.stage == "collect":
        stage_collect(args)
    elif args.stage == "train":
        stage_train(args)
    elif args.stage == "eval":
        stage_eval(args)
    else:
        stage_merge(args)


if __name__ == "__main__":
    main()
