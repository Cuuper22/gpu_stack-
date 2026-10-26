"""Smoke run of the e003 Heatwave simulator on the default scenario (simulated data).

Runs the seven-day default scenario twice (no controller, and the reactive
site-cap baseline), checks determinism and hierarchy conservation, and writes
summary statistics only to ``results/sim-smoke-v1.json``.  Every number in the
output file is produced by this script.

    python experiments/e003-heatwave/run_sim_smoke.py

Needs numpy and scipy.  Provenance is written with ``heatwave.provenance``
(installed from the Heatwave repository) and then pointed at this repository's
git state.
"""

from __future__ import annotations

import copy
import hashlib
import json
import resource
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from gpu_stack.research.heatwave_sim import (  # noqa: E402
    ReactiveSiteCapController,
    load_scenario,
    run_scenario,
)
from gpu_stack.research.heatwave_thermal import fit  # noqa: E402

SCENARIO = HERE / "sim-scenario-v1.json"
OUT = HERE / "results" / "sim-smoke-v1.json"
E002_RAW = ROOT / "docs" / "data" / "e002-checkpoint-power-raw-v1.json"


def run_summary(res, wall_s: float) -> dict:
    run = res._run
    summary = res.summary()
    hourly = res.site_mean_power_w_1h
    return {
        "wall_seconds": wall_s,
        "summary": summary,
        "site_hourly_mean_power_w": {sid: [float(x) for x in hourly[:, i]] for i, sid in enumerate(run.site_ids)},
        "site_hourly_cost_usd": {sid: [float(x) for x in res.site_cost_usd_1h[:, i]] for i, sid in enumerate(run.site_ids)},
        "site_hourly_carbon_kg": {sid: [float(x) for x in res.site_carbon_kg_1h[:, i]] for i, sid in enumerate(run.site_ids)},
        "rack_max_air_temp_c": {rid: float(run.rack_air_b[:, i].max()) for i, rid in enumerate(run.rack_ids)},
        "rack_max_gpu_temp_c": {rid: float(run.rack_maxgpu_b[:, i].max()) for i, rid in enumerate(run.rack_ids)},
        "event_counts": count_kinds(res.events),
        "events": res.events,
        "actions_total": len(res.actions),
        "actions_applied": sum(1 for a in res.actions if a["status"] == "applied"),
        "actions_first_20": res.actions[:20],
        "jobs": res.jobs_table,
    }


def count_kinds(events: list) -> dict:
    out: dict = {}
    for e in events:
        key = e["kind"] if "phase" not in e else f"{e['kind']}:{e['phase']}"
        out[key] = out.get(key, 0) + 1
    return out


def conservation_check(scenario: dict) -> dict:
    sc = copy.deepcopy(scenario)
    sc["horizon_s"] = 3600
    sc["events"] = []
    sc["outputs"] = {"gpu_windows": [[0, 3600]]}
    res = run_scenario(sc, seed=0)
    run = res._run
    arr = res.to_arrays()
    gpu = arr["gpu_power_w_window_0"]
    rack_from_gpu = np.add.reduceat(gpu, run.rack_start, axis=0).T
    site_from_rack = np.stack([arr["rack_power_w"][:, run.rack_site == s].sum(axis=1) for s in range(run.S)], axis=1)
    rack_total = arr["rack_gpu_power_w"] + np.repeat(run.rack_host_b, run.K, axis=0) + arr["rack_cooling_power_w"]

    def rel(a, b):
        return float(np.max(np.abs(a - b) / np.maximum(np.abs(b), 1.0)))

    return {
        "data_kind": "simulated",
        "window_s": [0, 3600],
        "max_rel_error_gpu_to_rack": rel(rack_from_gpu, arr["rack_gpu_power_w"]),
        "max_rel_error_rack_components": rel(rack_total, arr["rack_power_w"]),
        "max_rel_error_rack_to_site": rel(site_from_rack, arr["site_power_w"]),
        "max_rel_error_energy_hourly": rel(arr["site_power_w"].sum(axis=0) / 3.6e6, arr["site_energy_kwh_1h"].sum(axis=0)),
    }


def determinism_check(scenario: dict) -> dict:
    sc = copy.deepcopy(scenario)
    sc["horizon_s"] = 6 * 3600
    sc["outputs"] = {"gpu_windows": []}
    sc["events"] = [e for e in sc["events"] if e["onset_s"] < 6 * 3600]

    def digest(seed: int) -> str:
        res = run_scenario(sc, seed=seed)
        return hashlib.sha256(res.site_power_w.tobytes() + res.rack_temp_c_1min.tobytes()).hexdigest()

    a, b, c = digest(0), digest(0), digest(1)
    return {"horizon_s": 6 * 3600, "same_seed_identical": a == b, "different_seed_differs": a != c}


def laptop_rc_fit() -> dict:
    """RC fit on measured laptop board telemetry (power in, die temperature out).

    The telemetry updates about every 0.49 s and each run lasts about 10 s, so
    this checks that the fit machinery runs on a measured trace; the fitted time
    constants are reported next to the update period, not used for racks.
    """
    data = json.loads(E002_RAW.read_text())
    rows = []
    for run in data["runs"]:
        trace = run["telemetry_trace"]
        if not trace.get("available"):
            continue
        ts = np.array([p["timestamp"] for p in trace["points"]], dtype=float)
        power = np.array([p["gpu_board_power_w"] for p in trace["points"]], dtype=float)
        temp = np.array([p["temperature_c"] for p in trace["points"]], dtype=float)
        dt = 0.25
        grid = np.arange(0.0, ts[-1], dt)
        idx = np.searchsorted(ts, grid, side="right") - 1
        _, report = fit(power[idx], np.zeros(grid.size), temp[idx], dt)
        rows.append(report)
    period = float(data["logger_calibration"]["effective_update_period_seconds"])
    tau = np.array([r["time_constant_s"] for r in rows])
    return {
        "data_kind": "measured",
        "source": "docs/data/e002-checkpoint-power-raw-v1.json",
        "runs_fitted": len(rows),
        "resample_dt_s": 0.25,
        "telemetry_update_period_s": period,
        "median_rmse_c": float(np.median([r["rmse_c"] for r in rows])),
        "median_r2": float(np.median([r["r2"] for r in rows])),
        "median_time_constant_s": float(np.median(tau)),
        "fraction_time_constant_below_update_period": float(np.mean(tau < period)),
        "all_converged": bool(all(r["success"] for r in rows)),
        "temperature_resolution_c": 1.0,
    }


def git_state() -> dict:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()

    dirty = bool(git("status", "--porcelain", "--", ".", ":(exclude)experiments/e003-heatwave/results"))
    return {"commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"), "dirty": str(dirty).lower()}


def main() -> None:
    scenario = load_scenario(SCENARIO)
    out: dict = {"data_kind": "simulated", "scenario_id": scenario["scenario_id"]}

    t0 = time.time()
    base = run_scenario(scenario, seed=0)
    base_wall = time.time() - t0
    out["no_controller"] = run_summary(base, base_wall)
    out["peak_rss_mb_after_first_run"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

    t0 = time.time()
    capped = run_scenario(scenario, controller=ReactiveSiteCapController(margin=0.97), seed=0)
    out["reactive_site_cap"] = run_summary(capped, time.time() - t0)
    out["peak_rss_mb_after_second_run"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

    run = base._run
    arrays = base.to_arrays()
    out["configuration"] = {
        "horizon_s": run.cfg.horizon_s,
        "base_dt_s": run.dt,
        "control_dt_s": run.cdt,
        "sites": run.site_ids,
        "racks": [{"rack_id": r, "site_id": s, "gpus": int(n)} for r, s, n in zip(run.rack_ids, run.rack_site_ids, run.rack_n)],
        "gpus_total": int(run.G),
        "rack_heat_capacity_j_per_k": [float(x) for x in run.C],
        "rack_resistance_k_per_w": [float(x) for x in run.Rres],
        "rack_cooling_capacity_nominal_w": [float(x) for x in run.cap_nominal],
        "jobs": len(run.jobs),
        "jobs_multisite": sum(1 for j in run.jobs if j.multisite),
        "gpu_windows_s": [[w["start_s"], w["end_s"]] for w in base.gpu_windows],
        "gpu_window_array_shapes": [list(w["gpu_power_w"].shape) for w in base.gpu_windows],
        "array_shapes": {k: list(v.shape) for k, v in arrays.items() if isinstance(v, np.ndarray)},
    }
    out["power_levels_w_per_gpu"] = base.meta["power_levels"]
    out["measured_e002"] = base.meta["measured_e002"]
    out["throttle_model"] = base.meta["throttle"]
    out["cooling_power_model"] = base.meta["cooling_power_model"]
    out["breaker_model"] = base.meta["breaker"]
    out["ground_truth_events"] = base.ground_truth_events
    out["plan_vs_realized"] = {
        "planned_jobs": len(base.plan),
        "jobs_started_at_planned_time": sum(
            1
            for pj in base.plan
            if any(e["kind"] == "job_start" and e["job_id"] == pj.job_id and abs(e["t_s"] - pj.start_s) < 1e-6 for e in base.events)
        ),
        "note": "events (faults, throttling) perturb the realized schedule; the plan assumes none",
    }
    out["conservation_check_event_free_1h"] = conservation_check(scenario)
    out["determinism_check"] = determinism_check(scenario)
    out["laptop_rc_fit"] = laptop_rc_fit()
    out["assumptions"] = base.meta["assumptions"]
    out["simplifications"] = base.meta["simplifications"]

    try:
        from heatwave.provenance import write_result
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("heatwave.provenance is needed to write the result file") from exc
    record = write_result(
        OUT, out, script=__file__, data_kind="simulated",
        inputs=[SCENARIO, E002_RAW],
        notes="Seven-day default scenario; all outputs simulated. laptop_rc_fit uses measured telemetry.",
    )
    # write_result records the Heatwave repository's git state; point it at this repository.
    record["provenance"]["git"] = git_state()
    record["provenance"]["script"] = str(Path(__file__).resolve().relative_to(ROOT))
    record["provenance"]["inputs"] = {str(Path(p).resolve().relative_to(ROOT)): h for p, h in zip([SCENARIO, E002_RAW], [
        hashlib.sha256(SCENARIO.read_bytes()).hexdigest(), hashlib.sha256(E002_RAW.read_bytes()).hexdigest()])}
    OUT.write_text(json.JSONEncoder(indent=1, allow_nan=False).encode(record) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB)")


if __name__ == "__main__":
    main()
