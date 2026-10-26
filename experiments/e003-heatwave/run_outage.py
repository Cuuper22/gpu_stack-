"""Outage-response experiment on the e003 Heatwave simulator (all data simulated).

Compares warning-and-response policies on the simulated two-site cluster of
``sim-scenario-v2.json`` with the settings in ``outage-scenario-v1.json``:

* reactive (no forecast; the simulator rolls work back to the last checkpoint),
* the e001 averaging rule alone (every splittable job runs as two shards),
* observed crossing (persistence forecast, warn when the current value is past its limit),
* seasonal naive, ETS and ARIMA forecasts driving the warning rule,
* Timestral zero-shot 5M and 28M driving the warning rule,
* a fine-tuned Timestral through ``--finetuned-weights`` (not run without weights),
* perfect foresight (upper bound: reads the event times of the reactive run).

Stages, each cached in ``--work-dir`` so an interrupted run resumes:

``prepare``  event-free and reactive runs per seed (traces, event tables, reactive scores)
``openloop`` warning probabilities of every forecaster on the recorded reactive traces
``tune``     warning threshold per forecaster on training seeds only (replay objective)
``closed``   closed-loop runs on held-out seeds (the response actually runs in the simulator)
``report``   aggregation with seed-bootstrap intervals, written with provenance

    python experiments/e003-heatwave/run_outage.py --work-dir DIR --stage all

``--policies`` and ``--forecasters`` restrict a stage so several processes can
share the work.  Needs numpy, scipy, statsforecast and (for Timestral) torch
plus the ``timestral`` package.  Provenance is written with
``heatwave.provenance`` and then pointed at this repository's git state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from gpu_stack.research.heatwave_outage import (  # noqa: E402
    EVENT_TYPES,
    ForecastWarningController,
    OracleAlarm,
    OracleController,
    OutageSettings,
    PersistenceForecaster,
    SeriesIndex,
    TraceRecorder,
    aggregate_runs,
    build_event_table,
    calibrate,
    detection_stats,
    episodes_from_pmax,
    file_sha256,
    load_outage_scenario,
    openloop_pmax,
    oracle_alarms_from_reference,
    oracle_scenario,
    oracle_settings,
    paired_difference,
    periodic_local_jobs,
    pooled_quantile_ci,
    ratio_ci,
    bootstrap_ci,
    replay_objective,
    run_policy,
    score_run,
    seed_scenario,
    throttle_episodes,
)
from gpu_stack.research.heatwave_sim import build_config  # noqa: E402

SCENARIO = HERE / "outage-scenario-v1.json"
BASE_SCENARIO = HERE / "sim-scenario-v2.json"
OUT = HERE / "results" / "outage-v1.json"

FORECASTERS = ("naive", "ets", "arima", "ts5m", "ts28m", "finetuned")
CLASSICAL = ("naive", "ets", "arima")
POLICIES = ("reactive", "e001", "observed", "naive", "ets", "arima", "ts5m", "ts28m", "finetuned", "perfect_foresight")
NO_WARNING_POLICIES = ("reactive", "e001")
POLICY_LABELS = {
    "reactive": "reactive (no forecast)",
    "e001": "e001 averaging rule alone",
    "observed": "observed crossing (persistence)",
    "naive": "seasonal naive",
    "ets": "ETS",
    "arima": "ARIMA",
    "ts5m": "Timestral 5M zero-shot",
    "ts28m": "Timestral 28M zero-shot",
    "finetuned": "Timestral fine-tuned",
    "perfect_foresight": "perfect foresight (upper bound, reads event times)",
}


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def load_pickle(path: Path):
    with open(path, "rb") as f:
        return pickle.load(f)


def save_pickle(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        pickle.dump(obj, f)
    tmp.replace(path)


def make_forecaster(name: str, outage: dict, args: argparse.Namespace):
    from heatwave.forecast import ARIMAForecaster, ETSForecaster, SeasonalNaiveForecaster

    cl = outage["outage"]["classical"]
    if name == "naive":
        return SeasonalNaiveForecaster(int(cl["seasonal_naive_season_length"]))
    if name == "ets":
        return ETSForecaster(int(cl["ets_season_length"]))
    if name == "arima":
        return ARIMAForecaster(tuple(cl["arima_order"]))
    from heatwave.forecast.timestral_fc import TimestralForecaster

    if name == "ts5m":
        return TimestralForecaster("5M", threads=args.threads)
    if name == "ts28m":
        return TimestralForecaster("28M", threads=args.threads)
    if name == "finetuned":
        return TimestralForecaster(args.finetuned_size, weights_dir=args.finetuned_weights, threads=args.threads)
    raise ValueError(name)


def finetuned_available(args: argparse.Namespace) -> bool:
    return bool(args.finetuned_weights) and Path(args.finetuned_weights).exists()


def seeds_for(outage: dict, which: str, args: argparse.Namespace) -> list[int]:
    train = [int(s) for s in outage["seeds"]["train"]]
    test = [int(s) for s in outage["seeds"]["test"]]
    if args.n_test:
        test = test[: args.n_test]
    return {"train": train, "test": test, "all": train + test}[which]


# ---------------------------------------------------------------------------
# stage prepare
# ---------------------------------------------------------------------------


def prepare_seed(outage: dict, S: OutageSettings, seed: int, train: bool, work: Path) -> dict:
    path = work / f"prep_{seed}.pkl"
    if path.exists():
        return load_pickle(path)
    t0 = time.time()
    free = seed_scenario(outage, seed, with_events=False)
    out: dict = {"seed": seed}
    if train:
        rec_free = TraceRecorder(S)
        res_free, _ = run_policy(free, rec_free, seed)
        tr = rec_free.trace()
        out["ef_samples"], out["ef_times"] = tr["samples"], tr["times_s"]
    else:
        res_free, _ = run_policy(free, None, seed)
    ref_useful = float(res_free.summary()["useful_gpu_hours"])
    sc = seed_scenario(outage, seed)
    rec = TraceRecorder(S)
    res, cfg = run_policy(sc, rec, seed)
    trace = rec.trace()
    table = build_event_table(cfg, res.events, S)
    export = rec.export()
    export["episodes"] = []
    score = score_run(res, cfg, table, export, S, ref_useful)
    thr = throttle_episodes(res.events, cfg.horizon_s, S.episode_merge_gap_s)
    alarms = oracle_alarms_from_reference(cfg, res.events, thr, oracle_settings(S, cfg.control_dt_s))
    out.update(
        ref_useful=ref_useful, table=table, score=score, trace=trace, oracle_alarms=[a.__dict__ for a in alarms],
        n_events=len(table), wall_s=time.time() - t0,
    )
    save_pickle(path, out)
    log(f"prepare seed {seed}: {len(table)} events, reactive lost {score['summary']['lost_gpu_hours']:.1f} GPU-h ({time.time() - t0:.0f} s)")
    return out


def stage_prepare(outage, S, args, work) -> None:
    for seed in seeds_for(outage, "all", args):
        prepare_seed(outage, S, seed, seed in outage["seeds"]["train"], work)


def load_calibration(outage, S, args, work):
    train = seeds_for(outage, "train", args)
    preps = [prepare_seed(outage, S, s, True, work) for s in train]
    cfg = build_config(seed_scenario(outage, train[0], with_events=False), seed=train[0])
    index = SeriesIndex.from_config(cfg)
    return calibrate([p["ef_samples"] for p in preps], index, S, [p["ef_times"] for p in preps], "event-free runs on training seeds"), index


# ---------------------------------------------------------------------------
# stage openloop
# ---------------------------------------------------------------------------


def stage_openloop(outage, S, args, work) -> None:
    cal, _ = load_calibration(outage, S, args, work)
    if args.forecasters:
        names = list(args.forecasters)
    else:
        names = [n for n in FORECASTERS if n != "finetuned" or finetuned_available(args)] + ["perfect"]
    for name in names:
        fc = None
        order = seeds_for(outage, "all", args)
        for seed in (order[::-1] if args.reverse else order):
            path = work / f"pmax_{name}_{seed}.npy"
            if path.exists():
                continue
            prep = prepare_seed(outage, S, seed, seed in outage["seeds"]["train"], work)
            cfg = build_config(seed_scenario(outage, seed), seed=seed)
            if name != "perfect" and fc is None:
                fc = make_forecaster(name, outage, args)
            t0 = time.time()
            pm = openloop_pmax(fc, prep["trace"], cfg, S, cal, batch_size=args.batch_size, perfect=(name == "perfect"))
            np.save(path, pm)
            log(f"openloop {name} seed {seed}: {time.time() - t0:.0f} s")


# ---------------------------------------------------------------------------
# stage tune
# ---------------------------------------------------------------------------


def threshold_table(outage, S, args, work, name: str, seeds: list[int], index: SeriesIndex) -> dict:
    """Replay objective per threshold, summed over ``seeds``."""
    rows = {}
    for thr in S.threshold_grid:
        miss = alarm = 0.0
        for seed in seeds:
            prep = load_pickle(work / f"prep_{seed}.pkl")
            pm = np.load(work / f"pmax_{name}_{seed}.npy")
            eps = episodes_from_pmax(prep["trace"]["times_s"], pm, thr, S.clear_decisions, index)
            eps = [e for e in eps if e["start_s"] >= 0.0]
            r = replay_objective(prep["table"], prep["score"]["by_event"], eps, prep["trace"], index, S, prep["score"]["min_lead_s"])
            miss += r["miss_gpu_h"]
            alarm += r["alarm_gpu_h"]
        rows[f"{thr:g}"] = {"threshold": thr, "miss_gpu_h": miss, "alarm_gpu_h": alarm, "total_gpu_h": miss + alarm}
    return rows


def choose_threshold(rows: dict) -> float:
    best = min(rows.values(), key=lambda r: (round(r["total_gpu_h"], 9), -r["threshold"]))
    return float(best["threshold"])


def stage_tune(outage, S, args, work) -> dict:
    _, index = load_calibration(outage, S, args, work)
    train = seeds_for(outage, "train", args)
    out = {}
    names = [n for n in FORECASTERS if (work / f"pmax_{n}_{train[0]}.npy").exists()] + ["perfect"]
    for name in names:
        if not all((work / f"pmax_{name}_{s}.npy").exists() for s in train):
            continue
        rows = threshold_table(outage, S, args, work, name, train, index)
        out[name] = {"train_seeds": train, "objective_by_threshold": rows, "chosen_threshold": choose_threshold(rows)}
        log(f"tune {name}: chosen {out[name]['chosen_threshold']}")
    (work / "tuning.json").write_text(json.JSONEncoder(indent=1, allow_nan=False).encode(out) + "\n")
    return out


# ---------------------------------------------------------------------------
# stage closed
# ---------------------------------------------------------------------------


def closed_policy_seed(outage, S, cal, name: str, seed: int, work: Path, tuning: dict, args) -> dict:
    path = work / f"closed_{name}_{seed}.pkl"
    if path.exists():
        return load_pickle(path)
    prep = prepare_seed(outage, S, seed, seed in outage["seeds"]["train"], work)
    table, ref_useful = prep["table"], prep["ref_useful"]
    sc = seed_scenario(outage, seed)
    t0 = time.time()
    if name == "reactive":
        score = prep["score"]
        threshold = None
    elif name == "e001":
        res, cfg = run_policy(sc, None, seed, job_transform=periodic_local_jobs)
        score = score_run(res, cfg, table, {"policy": "e001", "episodes": [], "meta_actions": []}, S, ref_useful)
        threshold = None
    elif name == "perfect_foresight":
        So = oracle_settings(S, float(sc["control_dt_s"]))
        alarms = [OracleAlarm(**a) for a in prep["oracle_alarms"]]
        ctrl = OracleController(So, alarms)
        res, cfg = run_policy(oracle_scenario(sc), ctrl, seed)
        score = score_run(res, cfg, table, ctrl.export(), So, ref_useful)
        threshold = None
    else:
        if name == "observed":
            fc, threshold = PersistenceForecaster(), S.observed_threshold
        else:
            fc, threshold = make_forecaster(name, outage, args), tuning[name]["chosen_threshold"]
        ctrl = ForecastWarningController(S, fc, threshold, cal, name, batch_size=args.batch_size)
        res, cfg = run_policy(sc, ctrl, seed)
        score = score_run(res, cfg, table, ctrl.export(), S, ref_useful)
    out = {"seed": seed, "policy": name, "threshold": threshold, "score": score, "wall_s": time.time() - t0}
    save_pickle(path, out)
    s = score["summary"]
    log(f"closed {name} seed {seed}: lost {s['lost_gpu_hours']:.1f} GPU-h, alarms {score['response']['n_alarms']}, {out['wall_s']:.0f} s")
    return out


def stage_closed(outage, S, args, work) -> None:
    cal, _ = load_calibration(outage, S, args, work)
    tuning = json.loads((work / "tuning.json").read_text()) if (work / "tuning.json").exists() else {}
    pols = args.policies or [p for p in POLICIES if p != "finetuned" or finetuned_available(args)]
    for name in pols:
        if name in tuning or name in ("reactive", "e001", "observed", "perfect_foresight"):
            for seed in seeds_for(outage, "test", args):
                closed_policy_seed(outage, S, cal, name, seed, work, tuning, args)
        else:
            log(f"skip {name}: no tuned threshold (run openloop and tune first)")


# ---------------------------------------------------------------------------
# stage report
# ---------------------------------------------------------------------------


def sweep_rows(outage, S, args, work, name: str, seeds: list[int], index: SeriesIndex) -> dict:
    B = S.bootstrap_resamples
    rows = {}
    for thr in S.threshold_grid:
        stats = []
        costs = []
        for seed in seeds:
            prep = load_pickle(work / f"prep_{seed}.pkl")
            pm = np.load(work / f"pmax_{name}_{seed}.npy")
            eps = episodes_from_pmax(prep["trace"]["times_s"], pm, thr, S.clear_decisions, index)
            eps = [e for e in eps if e["start_s"] >= 0.0]
            stats.append(detection_stats(prep["table"], eps, S, float(prep["score"]["response"]["evaluated_days"]), prep["score"]["min_lead_s"]))
            costs.append(replay_objective(prep["table"], prep["score"]["by_event"], eps, prep["trace"], index, S, prep["score"]["min_lead_s"]))
        n_ev = [sum(b["n"] for b in s["by_kind"].values()) for s in stats]
        caught = [sum(b["caught"] for b in s["by_kind"].values()) for s in stats]
        in_time = [sum(b["caught_in_time"] for b in s["by_kind"].values()) for s in stats]
        leads = [[x / 60.0 for b in s["by_kind"].values() for x in b["leads_s"]] for s in stats]
        by_kind = {}
        for kind in EVENT_TYPES:
            nk = [s["by_kind"].get(kind, {"n": 0})["n"] for s in stats]
            if sum(nk) == 0:
                continue
            by_kind[kind] = {
                "n_events": int(sum(nk)),
                "recall": ratio_ci([s["by_kind"].get(kind, {"caught": 0})["caught"] for s in stats], nk, B, 41),
                "recall_in_time": ratio_ci([s["by_kind"].get(kind, {"caught_in_time": 0})["caught_in_time"] for s in stats], nk, B, 42),
            }
        rows[f"{thr:g}"] = {
            "threshold": thr,
            "recall": ratio_ci(caught, n_ev, B, 43),
            "recall_in_time": ratio_ci(in_time, n_ev, B, 44),
            "false_alarms_per_day": bootstrap_ci([s["false_alarms_per_day"] for s in stats], B, 45),
            "n_alarms": bootstrap_ci([s["n_alarms"] for s in stats], B, 46),
            "lead_minutes_median": pooled_quantile_ci(leads, 0.5, B, 47),
            "replay_total_gpu_h": bootstrap_ci([c["total_gpu_h"] for c in costs], B, 48),
            "replay_miss_gpu_h": bootstrap_ci([c["miss_gpu_h"] for c in costs], B, 49),
            "replay_alarm_gpu_h": bootstrap_ci([c["alarm_gpu_h"] for c in costs], B, 50),
            "by_event_type": by_kind,
        }
    return rows


def git_state() -> dict:
    def git(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()

    dirty = bool(git("status", "--porcelain", "--", ".", ":(exclude)experiments/e003-heatwave/results"))
    return {"commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"), "dirty": str(dirty).lower()}


def stage_report(outage, S, args, work) -> None:
    B = S.bootstrap_resamples
    cal, index = load_calibration(outage, S, args, work)
    tuning = json.loads((work / "tuning.json").read_text())
    test = seeds_for(outage, "test", args)
    train = seeds_for(outage, "train", args)
    preps = {s: load_pickle(work / f"prep_{s}.pkl") for s in train + test}
    policies: dict = {}
    runs_by_policy: dict = {}
    not_run: dict = {}
    for name in POLICIES:
        files = [work / f"closed_{name}_{s}.pkl" for s in test]
        if name == "finetuned" and not finetuned_available(args):
            not_run[name] = "no fine-tuned weights were found (pass --finetuned-weights); the hook is wired but was not run"
            continue
        if not all(f.exists() for f in files):
            not_run[name] = "closed-loop runs missing for some held-out seeds"
            continue
        recs = [load_pickle(f) for f in files]
        runs = [r["score"] for r in recs]
        runs_by_policy[name] = runs
        agg = aggregate_runs(runs, S, has_warnings=name not in NO_WARNING_POLICIES)
        agg["label"] = POLICY_LABELS[name]
        agg["threshold"] = recs[0]["threshold"]
        agg["wall_s_total"] = float(sum(r["wall_s"] for r in recs))
        agg["response_gpu_h_by_action"] = {
            k: bootstrap_ci([r["response"]["gpu_h_by_action"].get(k, 0.0) for r in runs], B, 60)
            for k in sorted({k for r in runs for k in r["response"]["gpu_h_by_action"]})
        }
        agg["per_seed"] = {
            str(r["seed"]): {
                "lost_gpu_h": r["score"]["summary"]["lost_gpu_hours"], "lost_steps": r["score"]["summary"]["lost_steps"],
                "deficit_gpu_h": r["score"]["deficit_gpu_h"], "response_gpu_h": r["score"]["response"]["total_gpu_h"],
                "n_alarms": r["score"]["response"]["n_alarms"], "n_false_alarms": r["score"]["response"]["n_false_alarms"],
            }
            for r in recs
        }
        policies[name] = agg
    paired = {}
    if "reactive" in runs_by_policy:
        base = runs_by_policy["reactive"]
        for name, runs in runs_by_policy.items():
            if name == "reactive":
                continue
            paired[name] = {
                "lost_gpu_h_minus_reactive": paired_difference([r["summary"]["lost_gpu_hours"] for r in runs], [r["summary"]["lost_gpu_hours"] for r in base], B, 70),
                "lost_steps_minus_reactive": paired_difference([r["summary"]["lost_steps"] for r in runs], [r["summary"]["lost_steps"] for r in base], B, 71),
                "deficit_gpu_h_minus_reactive": paired_difference([r["deficit_gpu_h"] for r in runs], [r["deficit_gpu_h"] for r in base], B, 72),
                "import_energy_above_kwh_minus_reactive": paired_difference(
                    [r["summary"]["import_energy_above_kwh"] for r in runs], [r["summary"]["import_energy_above_kwh"] for r in base], B, 73),
            }
    sweep = {}
    for name in tuning:
        if all((work / f"pmax_{name}_{s}.npy").exists() for s in test):
            sweep[name] = sweep_rows(outage, S, args, work, name, test, index)
    event_counts = {}
    for s in test:
        for ev in preps[s]["table"]:
            c = event_counts.setdefault(ev["kind"], {"n": 0, "with_precursor": 0, "scheduled": 0})
            c["n"] += 1
            c["with_precursor"] += int(bool(ev["has_precursor"]))
            c["scheduled"] += int(ev["source"] == "scheduled")
    first = preps[test[0]]
    cfg0 = build_config(seed_scenario(outage, test[0]), seed=test[0])
    result = {
        "data_kind": "simulated",
        "scenario_id": outage["scenario_id"],
        "seeds": {"train": train, "test": test},
        "settings": {k: (list(v) if isinstance(v, tuple) else v) for k, v in S.__dict__.items()},
        "calibration": cal.to_dict(),
        "series": {"n_series": len(index), "keys": [list(k) for k in index.keys]},
        "horizon_s": cfg0.horizon_s,
        "event_counts_test_seeds": event_counts,
        "tuning": tuning,
        "threshold_sweep_open_loop_test_seeds": sweep,
        "policies": policies,
        "paired_vs_reactive": paired,
        "not_run": not_run,
        "finetuned_weights": args.finetuned_weights if finetuned_available(args) else None,
        "notes": [
            "All data are simulated; no measured cluster data are used.",
            "Thresholds were chosen on training seeds with a replay objective, then used unchanged on held-out seeds.",
            "The sweep is open loop on the recorded reactive traces; closed-loop numbers are in policies.",
            "The perfect-foresight policy reads event times of the reactive run and is an upper bound, not a deployable policy.",
            "deficit_gpu_h is the useful GPU-hours of the event-free run minus the policy run on the same seed.",
            "Forecast compute: every forecaster's open-loop probabilities are computed once per seed on all decision points (no subsampling) and cached; tuning and the threshold sweep reuse that cache.",
            "Each forecast-driven policy then runs closed loop once per held-out seed at its tuned threshold; those runs forecast at every decision point because the response changes the trajectory the forecaster sees.",
        ],
        "assumptions": outage["assumptions"],
    }
    from heatwave.provenance import write_result

    inputs = [SCENARIO, BASE_SCENARIO]
    record = write_result(OUT, result, script=__file__, data_kind="simulated", inputs=inputs,
                          notes="Held-out seeds; thresholds tuned on training seeds; all outputs simulated.")
    record["provenance"]["git"] = git_state()
    record["provenance"]["script"] = str(Path(__file__).resolve().relative_to(ROOT))
    record["provenance"]["script_sha256"] = file_sha256(__file__)
    record["provenance"]["module_sha256"] = file_sha256(ROOT / "gpu_stack" / "research" / "heatwave_outage.py")
    record["provenance"]["inputs"] = {str(Path(p).resolve().relative_to(ROOT)): file_sha256(p) for p in inputs}
    record["provenance"]["seeds"] = {"train": train, "test": test}
    OUT.write_text(json.JSONEncoder(indent=1, allow_nan=False).encode(record) + "\n")
    log(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB)")


def main() -> None:
    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work-dir", required=True, type=Path)
    ap.add_argument("--stage", default="all", choices=("prepare", "openloop", "tune", "closed", "report", "all"))
    ap.add_argument("--policies", nargs="*", default=None, choices=POLICIES)
    ap.add_argument("--forecasters", nargs="*", default=None, choices=FORECASTERS + ("perfect",))
    ap.add_argument("--n-test", type=int, default=0, help="use only the first N held-out seeds (0 = all)")
    ap.add_argument("--reverse", action="store_true", help="open-loop pass visits seeds last to first (a second process can share the work)")
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--batch-size", type=int, default=512)
    ap.add_argument("--finetuned-weights", default=None)
    ap.add_argument("--finetuned-size", default="28M")
    args = ap.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    outage = load_outage_scenario(SCENARIO)
    S = OutageSettings.from_scenario(outage)
    work = args.work_dir
    stages = ("prepare", "openloop", "tune", "closed", "report") if args.stage == "all" else (args.stage,)
    for st in stages:
        t0 = time.time()
        {"prepare": stage_prepare, "openloop": stage_openloop, "tune": stage_tune, "closed": stage_closed, "report": stage_report}[st](
            outage, S, args, work
        )
        log(f"stage {st} done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
