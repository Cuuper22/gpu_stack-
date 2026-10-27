"""Replay one packing test episode per policy and keep downsampled traces for the site's Heatwave Lab window.

SIMULATED data. For test seed 500 of the packing experiment it re-runs, with the
same code and settings as ``run_packing.py eval``: Timestral-5M planning at each
of the 21 quantile levels, the reactive baseline, and the learned quantile policy
at every penalty of the sweep. For each run it keeps, inside the scored window,
5-minute means of site power and busy GPUs, 5-minute maxima of each rack's
hottest GPU and means of rack air temperature, plus the episode metrics, and
checks that the metrics equal the committed eval part for the same policy and
seed (the replay must reproduce the experiment, or the script stops).

Usage: python experiments/e003-heatwave/run_lab_traces.py [--workers 8] [--seed 500]
Writes experiments/e003-heatwave/results/lab-traces-v1.json.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "lab-traces-v1.json"
BIN_S = 300.0


def _runner():
    spec = importlib.util.spec_from_file_location("run_packing", HERE / "run_packing.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_packing"] = mod
    spec.loader.exec_module(mod)
    return mod


def policies(rp, packing):
    out = [("reactive", "reactive", None, None)]
    for q in rp.hp.QUANTILE_LEVELS:
        out.append((rp.policy_id("timestral-5M", f"q{q:g}"), "fixed", "timestral-5M", float(q)))
    for lam in packing["penalty"]["sweep_usd_per_kwh"]:
        out.append((rp.policy_id("timestral-5M", f"learned@{lam:g}"), "learned", "timestral-5M", float(lam)))
    return out


def _bin(t_s, values, a, b, how="mean"):
    edges = np.arange(a, b + 1e-9, BIN_S)
    idx = np.digitize(t_s, edges) - 1
    out = np.full((len(edges) - 1,) + values.shape[1:], np.nan)
    for k in range(len(edges) - 1):
        m = idx == k
        if m.any():
            out[k] = values[m].mean(axis=0) if how == "mean" else values[m].max(axis=0)
    return out


def one(job):
    pid, kind, fcn, arg, seed = job
    rp = _runner()
    hp = rp.hp
    packing, sim, settings = rp.setup()
    models = rp.load_models()
    use_cov = fcn in packing["policies"]["use_covariates"] if fcn else False
    pen = float(packing["penalty"]["default_usd_per_kwh"])
    fc = rp.make_forecaster(fcn, packing, 1) if fcn else None
    learned = None
    if kind == "learned":
        learned = hp.LearnedQ(hp.CostSensitiveModel.from_dict(json.loads(rp.MODEL_PATH.read_text())["result"]["model"]))

    def factory(ep, site_ids):
        if kind == "reactive":
            return hp.PackingController(ep.jobs, models, site_ids, settings, ep.hour0_local, mode="reactive")
        policy = hp.FixedQ(arg) if kind == "fixed" else learned
        penalty = float(arg) if kind == "learned" else pen
        return hp.PackingController(
            ep.jobs, models, site_ids, settings, ep.hour0_local, mode="forecast", forecaster=fc, policy=policy,
            penalty_usd_per_kwh=penalty, use_covariates=use_cov,
            forecast_refresh_bins=int(packing["policies"]["forecast_refresh_bins"].get(fcn, 1)),
        )

    ep, ctrl, res, wall = rp.run_one(packing, sim, settings, models, seed, factory)
    metrics = hp.episode_metrics(res, ctrl, ep, settings)
    part = rp.PARTS / "eval" / f"{pid.replace('/', '__').replace('@', '_at_')}__seed{seed}.json"
    ref = json.loads(part.read_text())["result"]["metrics"] if part.exists() else None
    if ref is not None:
        for key in ("gpu_hours", "energy_above_cap_kwh", "violation_rate"):
            if not math.isclose(ref[key], metrics[key], rel_tol=1e-6, abs_tol=1e-9):
                raise RuntimeError(f"{pid} seed {seed}: replay {key} {metrics[key]} != committed {ref[key]}")
    arr = res.to_arrays()
    a, b = metrics["window_s"]
    dt = float(ep.scenario["base_dt_s"])
    sp = np.asarray(arr["site_power_w"])
    t_sp = (np.arange(sp.shape[0]) + 0.5) * dt
    keep = (t_sp >= a) & (t_sp < b)
    site_power = _bin(t_sp[keep], sp[keep], a, b)
    rt = np.asarray(arr["rack_temp_c_1min"])
    t_rt = (np.arange(rt.shape[0]) + 0.5) * 60.0
    k2 = (t_rt >= a) & (t_rt < b)
    rack_air = _bin(t_rt[k2], rt[k2], a, b)
    rmax = _bin(t_rt[k2], np.asarray(arr["rack_max_gpu_temp_c_1min"])[k2], a, b, how="max")
    P, B = ctrl.minute_records()
    t_c = (np.arange(len(B)) + 1.0) * settings.call_s - 0.5 * settings.call_s
    k3 = (t_c >= a) & (t_c < b)
    busy = _bin(t_c[k3], np.asarray(B)[k3], a, b) if k3.any() else None
    return {
        "policy": pid, "kind": kind, "seed": seed, "metrics": metrics, "matches_committed_part": ref is not None,
        "bin_s": BIN_S, "window_s": [a, b],
        "site_power_w": site_power.round(1).tolist(),
        "busy_gpus": None if busy is None else busy.round(2).tolist(),
        "rack_air_c": rack_air.round(2).tolist(),
        "rack_max_gpu_c": rmax.round(2).tolist(),
        "wall_s": wall,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=500)
    a = ap.parse_args()
    rp = _runner()
    packing, sim, settings = rp.setup()
    models = rp.load_models()
    jobs = [(*p, a.seed) for p in policies(rp, packing)]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        runs = list(ex.map(one, jobs))
    site_ids = list(models)
    rack_ids = [r["rack_id"] for item in sim["sites"] for r in item["racks"]]
    result = {
        "data_kind": "simulated", "seed": a.seed, "site_ids": site_ids, "rack_ids": rack_ids,
        "site_caps_w": [models[s].cap_w for s in site_ids],
        "quantile_levels": list(rp.hp.QUANTILE_LEVELS),
        "runs": runs,
        "note": ("Replays of packing-v1 test seed 500 with the same code and settings; every replay's metrics were checked "
                 "against the committed eval part where one exists (matches_committed_part)."),
    }
    record = {"provenance": rp.part_provenance(seed=a.seed, role="lab-traces"), "result": rp._clean(result)}
    rp.write_json(OUT, record)
    print(f"wrote {OUT} ({len(runs)} runs)")


if __name__ == "__main__":
    main()
