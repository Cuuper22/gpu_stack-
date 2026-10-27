"""Outage-response experiment on the e003 Heatwave simulator (all data simulated).

Compares warning-and-response policies on the simulated two-site cluster of
``sim-scenario-v3.json`` with the settings in ``outage-scenario-v3.json`` (v3 keeps the
v2 warning channels and redesigns the response; ``--scenario outage-scenario-v2.json
--out results/outage-v2.json`` runs the v2 response and ``outage-scenario-v1.json``
the v1 channel set):

* reactive (no forecast; the simulator rolls work back to the last checkpoint),
* the e001 averaging rule alone (every splittable job runs as two shards),
* observed crossing (persistence forecast, warn when the current value is past its limit),
* seasonal naive, ETS and ARIMA forecasts driving the warning rule,
* Timestral zero-shot 5M and 28M driving the warning rule,
* a fine-tuned Timestral through ``--finetuned-weights`` (not run without weights),
* perfect foresight (upper bound: reads the event times of the reactive run).

Stages, each cached in ``--work-dir`` so an interrupted run resumes:

``prepare``  event-free and reactive runs per seed (traces, ledgers, event tables, reactive scores)
``design``   response search on training seeds only: perfect foresight with each candidate
            response (coordinate descent over the steps in the scenario), the deficit
            decomposition of the reference and chosen designs, perfect-foresight timing
            sensitivity (v3 scenario only)
``openloop`` warning probabilities of every forecaster on the recorded reactive traces
``tune``     warning threshold per forecaster on training seeds only (replay objective of
            the response in the scenario)
``closed``   closed-loop runs on held-out seeds (the response actually runs in the simulator)
``report``   aggregation with seed-bootstrap intervals, deficit decomposition, written with
            provenance (and, for v3, the side-by-side comparison with the v1 and v2 results)

    python experiments/e003-heatwave/run_outage.py --work-dir DIR --stage all

``--policies`` and ``--forecasters`` restrict a stage so several processes can
share the work; ``--procs N`` runs the independent tasks of a stage in N processes.  Needs numpy, scipy, statsforecast and (for Timestral) torch
plus the ``timestral`` package.  Provenance is written with
``heatwave.provenance`` and then pointed at this repository's git state.  In a
``git archive`` copy (no .git, as on Colab) set ``GPU_STACK_GIT_COMMIT`` to the
archived commit, or run the ``report`` stage on a machine with the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import warnings
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from gpu_stack.research.heatwave_outage import (  # noqa: E402
    EVENT_TYPES,
    ForecastWarningController,
    OracleController,
    OutageSettings,
    PersistenceForecaster,
    ResponseDesign,
    SeriesIndex,
    TraceRecorder,
    aggregate_runs,
    build_event_table,
    calibrate,
    decompose_deficit,
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

SCENARIO = HERE / "outage-scenario-v3.json"
OUT = HERE / "results" / "outage-v3.json"
V1_RESULT = HERE / "results" / "outage-v1.json"
V2_RESULT = HERE / "results" / "outage-v2.json"

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
    """Read a cached stage object (stored as a one-element object array by ``save_pickle``)."""
    return np.load(path, allow_pickle=True)[0]


def save_pickle(path: Path, obj) -> None:
    """Cache a stage object atomically (a one-element object array in an .npy file)."""
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    holder = np.empty(1, dtype=object)
    holder[0] = obj
    with open(tmp, "wb") as f:
        np.save(f, holder, allow_pickle=True)
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
    """Seed lists: ``train`` (calibration seeds), ``design`` (training seeds incl. the extra ones), ``test``, ``all``."""
    train = [int(s) for s in outage["seeds"]["train"]]
    extra = [int(s) for s in outage["seeds"].get("design_extra", [])]
    test = [int(s) for s in outage["seeds"]["test"]]
    if getattr(args, "n_design", 0):
        extra = extra[: args.n_design]
    if args.n_test:
        test = test[: args.n_test]
    if getattr(args, "only_seeds", None) and which not in ("train", "design"):
        test = [x for x in test if x in set(args.only_seeds)]
    return {"train": train, "design": train + extra, "test": test, "all": train + extra + test}[which]


def tuning_seeds(outage: dict, args: argparse.Namespace) -> list[int]:
    """Seeds on which warning thresholds are tuned.

    ``outage.tuning_seeds`` is ``"train"`` (the calibration seeds, default), ``"design"`` (all training seeds), or an
    integer N (the calibration seeds and the first N-4 extra training seeds, so N seeds in all).
    """
    spec = outage["outage"].get("tuning_seeds", "train")
    if spec == "train":
        return seeds_for(outage, "train", args)
    design = seeds_for(outage, "design", args)
    if spec == "design":
        return design
    return design[: max(int(spec), len(seeds_for(outage, "train", args)))]


def openloop_seeds(outage: dict, args: argparse.Namespace) -> list[int]:
    tune = tuning_seeds(outage, args)
    return tune + [s for s in seeds_for(outage, "test", args) if s not in tune]


# ---------------------------------------------------------------------------
# parallel tasks
# ---------------------------------------------------------------------------

_CTX: dict = {}


def _init_worker(ctx: dict) -> None:
    _CTX.clear()
    _CTX.update(ctx)
    _CTX["forecasters"] = {}
    if ctx.get("nice"):
        os.nice(int(ctx["nice"]))


def run_tasks(fn, tasks: list, ctx: dict, procs: int) -> list:
    """Run ``fn`` over ``tasks`` in this process or a pool of ``procs`` processes (ctx is shared read-only)."""
    if not tasks:
        return []
    if procs <= 1 or len(tasks) == 1:
        _init_worker(ctx)
        return [fn(t) for t in tasks]
    import multiprocessing as mp

    with mp.get_context("fork").Pool(min(procs, len(tasks)), initializer=_init_worker, initargs=(ctx,)) as pool:
        return pool.map(fn, tasks, chunksize=1)


def make_ctx(outage, S, args, work) -> dict:
    return {"outage": outage, "S": S, "args": args, "work": work, "nice": getattr(args, "nice", 0)}


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
    out.update(
        ref_useful=ref_useful, ref_ledger=res_free._run.ledger.to_gpu_hours(), table=table, score=score, trace=trace,
        ref_events=list(res.events), n_events=len(table), wall_s=time.time() - t0,
    )
    save_pickle(path, out)
    log(f"prepare seed {seed}: {len(table)} events, reactive lost {score['summary']['lost_gpu_hours']:.1f} GPU-h ({time.time() - t0:.0f} s)")
    return out


def _task_prepare(seed: int) -> int:
    ctx = _CTX
    prepare_seed(ctx["outage"], ctx["S"], seed, seed in ctx["outage"]["seeds"]["train"], ctx["work"])
    return seed


def perfect_alarms(outage, S: OutageSettings, prep: dict, seed: int):
    """Oracle alarms rebuilt from the reactive run's event log (the perfect-foresight policy reads event times)."""
    sc = seed_scenario(outage, seed)
    cfg = build_config(sc, seed=seed)
    thr = throttle_episodes(prep["ref_events"], cfg.horizon_s, S.episode_merge_gap_s)
    return oracle_alarms_from_reference(cfg, prep["ref_events"], thr, oracle_settings(S, cfg.control_dt_s))


def run_perfect_foresight(outage, S: OutageSettings, prep: dict, seed: int) -> dict:
    """Closed-loop perfect-foresight run on one seed with the response in ``S``; returns the score."""
    sc = seed_scenario(outage, seed)
    So = oracle_settings(S, float(sc["control_dt_s"]))
    ctrl = OracleController(So, perfect_alarms(outage, S, prep, seed))
    res, cfg = run_policy(oracle_scenario(sc), ctrl, seed)
    return score_run(res, cfg, prep["table"], ctrl.export(), So, prep["ref_useful"])


def stage_prepare(outage, S, args, work) -> None:
    run_tasks(_task_prepare, seeds_for(outage, "all", args), make_ctx(outage, S, args, work), args.procs)


def load_calibration(outage, S, args, work):
    train = seeds_for(outage, "train", args)
    preps = [prepare_seed(outage, S, s, True, work) for s in train]
    cfg = build_config(seed_scenario(outage, train[0], with_events=False), seed=train[0])
    index = SeriesIndex.from_config(cfg, S.per_gpu_channel)
    return calibrate([p["ef_samples"] for p in preps], index, S, [p["ef_times"] for p in preps], "event-free runs on training seeds"), index


# ---------------------------------------------------------------------------
# stage design: response search on training seeds with perfect foresight
# ---------------------------------------------------------------------------


def design_key(design: dict | None, extra_lead: int | None, mode: tuple | None = None) -> str:
    blob = json.dumps({"design": design, "extra_lead": extra_lead, "mode": mode}, sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:10]


def settings_with(S: OutageSettings, design: dict | None, extra_lead: int | None) -> OutageSettings:
    """Settings with the response replaced (``None`` = the v1/v2 planner) and, optionally, the oracle lead."""
    S2 = replace(S, response=None if design is None else ResponseDesign.from_dict(design))
    if design is None:
        S2 = replace(S2, response_tick_s=None)
    if extra_lead is not None:
        S2 = replace(S2, oracle_extra_lead_steps=int(extra_lead))
    return S2


def run_warned(outage, S: OutageSettings, prep: dict, seed: int, forecaster, name: str, threshold: float, cal, batch_size: int) -> dict:
    """Closed-loop run of a forecast-driven warning policy on one seed with the response in ``S``; returns the score."""
    sc = seed_scenario(outage, seed)
    if S.response is None:
        sc["controller_interval_s"] = S.decision_interval_s  # the v1/v2 planner runs on the decision grid only
    ctrl = ForecastWarningController(S, forecaster, threshold, cal, name, batch_size=batch_size)
    res, cfg = run_policy(sc, ctrl, seed)
    return score_run(res, cfg, prep["table"], ctrl.export(), S, prep["ref_useful"])


def _task_design(task) -> tuple:
    key, design, extra_lead, seed, mode = task
    ctx = _CTX
    path = ctx["work"] / "design" / f"{key}_{seed}.pkl"
    if path.exists():
        return key, seed
    path.parent.mkdir(parents=True, exist_ok=True)
    outage, args, work = ctx["outage"], ctx["args"], ctx["work"]
    prep = load_pickle(work / f"prep_{seed}.pkl")
    S2 = settings_with(ctx["S"], design, extra_lead)
    if mode is None:
        score = run_perfect_foresight(outage, S2, prep, seed)
    else:
        fname, thr = mode
        cal, _ = load_calibration(outage, ctx["S"], args, work)
        fc = ctx["forecasters"].get(fname)
        if fc is None:
            fc = ctx["forecasters"][fname] = make_forecaster(fname, outage, args)
        score = run_warned(outage, S2, prep, seed, fc, fname, float(thr), cal, args.batch_size)
    save_pickle(path, score)
    return key, seed


def design_scores(outage, S, args, work, design: dict | None, extra_lead: int | None, seeds: list[int], mode: tuple | None = None) -> dict:
    key = design_key(design, extra_lead, mode)
    pending = [(key, design, extra_lead, s, mode) for s in seeds if not (work / "design" / f"{key}_{s}.pkl").exists()]
    run_tasks(_task_design, pending, make_ctx(outage, S, args, work), args.procs)
    return {s: load_pickle(work / "design" / f"{key}_{s}.pkl") for s in seeds}


def floor0(x: float) -> float:
    """Deficit with work above the event-free reference not credited (a paused or moved job can free GPUs for other jobs)."""
    return max(float(x), 0.0)


def design_summary(scores: dict, preps: dict, seeds: list[int]) -> dict:
    """Seed means of a candidate and its paired difference to the reactive run.

    The design objective is the deficit with per-seed values floored at zero: useful GPU-hours above the event-free
    reference come from other jobs using GPUs a paused or moved job released, not from protection against the outage.
    """
    def mean(f):
        return float(np.mean([f(scores[s], preps[s]) for s in seeds]))

    diff = np.array([floor0(scores[s]["deficit_gpu_h"]) - floor0(preps[s]["score"]["deficit_gpu_h"]) for s in seeds])
    raw = np.array([scores[s]["deficit_gpu_h"] - preps[s]["score"]["deficit_gpu_h"] for s in seeds])
    se = lambda x: float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else float("nan")  # noqa: E731
    return {
        "n_seeds": len(seeds),
        "deficit_gpu_h": mean(lambda sc, p: floor0(sc["deficit_gpu_h"])),
        "reactive_deficit_gpu_h": mean(lambda sc, p: floor0(p["score"]["deficit_gpu_h"])),
        "deficit_minus_reactive_gpu_h": float(diff.mean()),
        "deficit_minus_reactive_se_gpu_h": se(diff),
        "deficit_unfloored_gpu_h": mean(lambda sc, p: sc["deficit_gpu_h"]),
        "deficit_unfloored_minus_reactive_gpu_h": float(raw.mean()),
        "deficit_unfloored_minus_reactive_se_gpu_h": se(raw),
        "seeds_with_negative_deficit": int(sum(scores[s]["deficit_gpu_h"] < -1e-6 for s in seeds)),
        "lost_gpu_h": mean(lambda sc, p: sc["summary"]["lost_gpu_hours"]),
        "response_gpu_h": mean(lambda sc, p: sc["response"]["total_gpu_h"]),
        "false_alarms_per_day": mean(lambda sc, p: sc["response"]["false_alarms_per_day"]),
        "import_energy_above_kwh": mean(lambda sc, p: sc["summary"]["import_energy_above_kwh"]),
        "reactive_import_energy_above_kwh": mean(lambda sc, p: p["score"]["summary"]["import_energy_above_kwh"]),
        "throttle_slowdown_gpu_h": mean(lambda sc, p: sum(e["throttle_slowdown_gpu_h"] for e in sc["by_event"])),
        "deficit_by_seed_gpu_h": {str(s): floor0(scores[s]["deficit_gpu_h"]) for s in seeds},
    }


def combine_summaries(parts: dict) -> dict:
    """Average of several summaries (one per forecaster) on the same seeds: per-seed deficits are averaged."""
    keys = [k for k in next(iter(parts.values())) if k not in ("n_seeds", "deficit_by_seed_gpu_h")]
    out = {k: float(np.mean([p[k] for p in parts.values()])) for k in keys}
    first = next(iter(parts.values()))
    out["n_seeds"] = first["n_seeds"]
    out["deficit_by_seed_gpu_h"] = {s: float(np.mean([p["deficit_by_seed_gpu_h"][s] for p in parts.values()])) for s in first["deficit_by_seed_gpu_h"]}
    out["per_forecaster"] = {f: {k: v for k, v in p.items() if k != "deficit_by_seed_gpu_h"} for f, p in parts.items()}
    return out


def apply_step(design: dict, param: str, value) -> dict:
    """Design with one search parameter changed; ``rule_a+b`` sets the rule of classes a and b together."""
    d = ResponseDesign.from_dict(design)
    if param.startswith("rule_"):
        for cls in param[len("rule_"):].split("+"):
            d = d.with_changes(**{f"rule_{cls}": tuple(value)})
    else:
        d = d.with_changes(**{param: value})
    return d.to_dict()


def stage_design(outage, S, args, work) -> dict:
    spec = outage["outage"].get("design")
    if not spec:
        log("no design block in this scenario: nothing to search")
        return {}
    seeds = seeds_for(outage, "design", args)
    stage_prepare_design(outage, S, args, work, seeds)
    preps = {s: load_pickle(work / f"prep_{s}.pkl") for s in seeds}
    B = S.bootstrap_resamples
    margin = float(spec.get("margin_se", 1.0))
    warned_ref = spec.get("warned_reference", {}).get("forecasters", {})
    cache: dict = {}

    def evaluate(design: dict | None, label: str, extra_lead: int | None = None, objective: str = "pf") -> dict:
        key = design_key(design, extra_lead, None if objective == "pf" else ("warned", tuple(sorted(warned_ref.items()))))
        if key not in cache:
            if objective == "pf":
                sc_all = {"perfect_foresight": design_scores(outage, S, args, work, design, extra_lead, seeds)}
            else:
                sc_all = {f: design_scores(outage, S, args, work, design, extra_lead, seeds, (f, thr)) for f, thr in warned_ref.items()}
            parts = {f: design_summary(sc, preps, seeds) for f, sc in sc_all.items()}
            summary = next(iter(parts.values())) if objective == "pf" else combine_summaries(parts)
            cache[key] = {"label": label, "key": key, "objective": objective, "design": design, "oracle_extra_lead_steps": extra_lead,
                          "summary": summary, "_scores": sc_all}
            s = summary
            log(f"design [{objective}] {label}: deficit {s['deficit_gpu_h']:.2f} (reactive {s['reactive_deficit_gpu_h']:.2f}), diff {s['deficit_minus_reactive_gpu_h']:+.2f} +- {s['deficit_minus_reactive_se_gpu_h']:.2f}, response {s['response_gpu_h']:.2f}")
        return cache[key]

    reference = {"v2_response": evaluate(None, "perfect foresight, v2 response (planner of outage v2)")}
    current = ResponseDesign.from_dict(spec["start"]).to_dict()
    cur = evaluate(current, "start: " + spec["start"]["name"])
    reference["start"] = cur
    if warned_ref:
        reference["v2_response_warned"] = evaluate(None, "warned reference forecasters, v2 response", objective="warned")
        reference["start_warned"] = evaluate(current, "warned reference forecasters, start design", objective="warned")
    steps_out = []
    for step in spec["steps"]:
        objective = step.get("objective", "pf")
        cur = evaluate(current, f"current before {step['param']}", objective=objective)
        evals = []
        for value in step["values"]:
            cand = apply_step(current, step["param"], value)
            evals.append({"value": value, "ev": evaluate(cand, f"{step['param']}={value}", objective=objective), "design": cand})
        cur_def = cur["summary"]["deficit_by_seed_gpu_h"]
        before = current
        best = None
        for e in evals:
            d = np.array([e["ev"]["summary"]["deficit_by_seed_gpu_h"][str(s)] - cur_def[str(s)] for s in seeds])
            e["paired_vs_current_gpu_h"] = {"mean": float(d.mean()), "se": float(d.std(ddof=1) / np.sqrt(len(seeds)))}
            if e["design"] != before and (best is None or d.mean() < best["paired_vs_current_gpu_h"]["mean"]):
                best = e
        adopted = None
        if best is not None and best["paired_vs_current_gpu_h"]["mean"] < -margin * best["paired_vs_current_gpu_h"]["se"]:
            adopted = best
            current = best["design"]
        steps_out.append({
            "param": step["param"], "objective": objective, "reason": step.get("reason"),
            "evaluations": [{"value": e["value"], "is_current_design": e["design"] == before,
                             "paired_vs_current_gpu_h": e["paired_vs_current_gpu_h"],
                             "summary": {k: v for k, v in e["ev"]["summary"].items() if k != "deficit_by_seed_gpu_h"}}
                            for e in evals],
            "adopted_value": None if adopted is None else adopted["value"],
            "design_after": current,
        })
        log(f"design step {step['param']} [{objective}]: adopted {None if adopted is None else adopted['value']}")
    chosen = evaluate(current, "chosen design")
    chosen_warned = evaluate(current, "chosen design, warned reference forecasters", objective="warned") if warned_ref else None
    sens = []
    for lead in spec.get("timing_sensitivity", []):
        ev = evaluate(chosen["design"], f"chosen design, perfect-foresight lead = checkpoint + {lead} control steps", int(lead))
        sens.append({"oracle_extra_lead_steps": int(lead), "summary": {k: v for k, v in ev["summary"].items() if k != "deficit_by_seed_gpu_h"}})
    ref_ledgers = [preps[s]["ref_ledger"] for s in seeds]
    first = lambda ev: ev["_scores"][next(iter(ev["_scores"]))]  # noqa: E731
    decomposition = {
        "reactive": decompose_deficit([preps[s]["score"] for s in seeds], ref_ledgers, B),
        "perfect_foresight_v2_response": decompose_deficit([first(reference["v2_response"])[s] for s in seeds], ref_ledgers, B),
        "perfect_foresight_start_design": decompose_deficit([first(reference["start"])[s] for s in seeds], ref_ledgers, B),
        "perfect_foresight_chosen_design": decompose_deficit([first(chosen)[s] for s in seeds], ref_ledgers, B),
    }
    for f in warned_ref:
        decomposition[f"{f}_warned_v2_response"] = decompose_deficit([reference["v2_response_warned"]["_scores"][f][s] for s in seeds], ref_ledgers, B)
        decomposition[f"{f}_warned_chosen_design"] = decompose_deficit([chosen_warned["_scores"][f][s] for s in seeds], ref_ledgers, B)
    strip = lambda ev: {k: v for k, v in ev.items() if k != "_scores"}  # noqa: E731
    out = {
        "data_kind": "simulated",
        "seeds": {"train": seeds_for(outage, "train", args), "design_extra": [s for s in seeds if s not in seeds_for(outage, "train", args)]},
        "objective": spec.get("objective"),
        "deficit_definition": "per-seed deficit floored at zero (useful GPU-hours above the event-free reference are not credited); unfloored values are reported next to it",
        "warned_reference": spec.get("warned_reference"),
        "adopt_rule": f"a candidate replaces the current design when its mean paired deficit difference to the current design is below -{margin:g} standard errors",
        "reference": {k: strip(v) for k, v in reference.items()},
        "steps": steps_out,
        "chosen": strip(chosen),
        "chosen_warned": None if chosen_warned is None else strip(chosen_warned),
        "chosen_equals_scenario_response": _same_design(chosen["design"], outage["outage"].get("response")),
        "timing_sensitivity": sens,
        "decomposition": decomposition,
    }
    (work / "design.json").write_text(json.JSONEncoder(indent=1, allow_nan=False).encode(_jsonable(out)) + "\n")
    return out


def stage_prepare_design(outage, S, args, work, seeds) -> None:
    run_tasks(_task_prepare, [s for s in seeds if not (work / f"prep_{s}.pkl").exists()], make_ctx(outage, S, args, work), args.procs)


def _same_design(a: dict | None, b: dict | None) -> bool:
    if a is None or b is None:
        return False
    ra, rb = ResponseDesign.from_dict(a).to_dict(), ResponseDesign.from_dict(b).to_dict()
    ra.pop("name"), rb.pop("name")
    return ra == rb


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    return x


# ---------------------------------------------------------------------------
# stage openloop
# ---------------------------------------------------------------------------


def _task_openloop(task) -> tuple:
    name, seed = task
    ctx = _CTX
    outage, S, args, work = ctx["outage"], ctx["S"], ctx["args"], ctx["work"]
    path = work / f"pmax_{name}_{seed}.npy"
    if path.exists():
        return name, seed
    cal, _ = load_calibration(outage, S, args, work)
    prep = load_pickle(work / f"prep_{seed}.pkl")
    cfg = build_config(seed_scenario(outage, seed), seed=seed)
    fc = None
    if name != "perfect":
        fc = ctx["forecasters"].get(name)
        if fc is None:
            fc = ctx["forecasters"][name] = make_forecaster(name, outage, args)
    t0 = time.time()
    pm = openloop_pmax(fc, prep["trace"], cfg, S, cal, batch_size=args.batch_size, perfect=(name == "perfect"))
    np.save(path, pm)
    log(f"openloop {name} seed {seed}: {time.time() - t0:.0f} s")
    return name, seed


def stage_openloop(outage, S, args, work) -> None:
    load_calibration(outage, S, args, work)
    if args.forecasters:
        names = list(args.forecasters)
    else:
        names = [n for n in FORECASTERS if n != "finetuned" or finetuned_available(args)] + ["perfect"]
    order = openloop_seeds(outage, args)
    if args.reverse:
        order = order[::-1]
    tasks = [(n, s) for n in names for s in order if not (work / f"pmax_{n}_{s}.npy").exists()]
    run_tasks(_task_openloop, tasks, make_ctx(outage, S, args, work), args.procs)


# ---------------------------------------------------------------------------
# stage tune
# ---------------------------------------------------------------------------


def threshold_table(outage, S, args, work, name: str, seeds: list[int], index: SeriesIndex) -> dict:
    """Replay objective per threshold, summed over ``seeds``."""
    rows = {}
    loaded = {s: (load_pickle(work / f"prep_{s}.pkl"), np.load(work / f"pmax_{name}_{s}.npy")) for s in seeds}
    for thr in S.threshold_grid:
        miss = alarm = 0.0
        for seed in seeds:
            prep, pm = loaded[seed]
            eps = episodes_from_pmax(prep["trace"]["times_s"], pm, thr, S.clear_decisions_effective, index)
            eps = [e for e in eps if e["start_s"] >= 0.0]
            r = replay_objective(prep["table"], prep["score"]["by_event"], eps, prep["trace"], index, S, prep["score"]["min_lead_s"], S.response)
            miss += r["miss_gpu_h"]
            alarm += r["alarm_gpu_h"]
        rows[f"{thr:g}"] = {"threshold": thr, "miss_gpu_h": miss, "alarm_gpu_h": alarm, "total_gpu_h": miss + alarm}
    return rows


def choose_threshold(rows: dict) -> float:
    best = min(rows.values(), key=lambda r: (round(r["total_gpu_h"], 9), -r["threshold"]))
    return float(best["threshold"])


def stage_tune(outage, S, args, work) -> dict:
    _, index = load_calibration(outage, S, args, work)
    tune = tuning_seeds(outage, args)
    out = {}
    names = [n for n in FORECASTERS if (work / f"pmax_{n}_{tune[0]}.npy").exists()] + ["perfect"]
    for name in names:
        if not all((work / f"pmax_{name}_{s}.npy").exists() for s in tune):
            continue
        rows = threshold_table(outage, S, args, work, name, tune, index)
        out[name] = {"tuning_seeds": tune, "objective_by_threshold": rows, "chosen_threshold": choose_threshold(rows)}
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
        score = run_perfect_foresight(outage, S, prep, seed)
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


def _task_closed(task) -> tuple:
    name, seed = task
    ctx = _CTX
    outage, S, args, work = ctx["outage"], ctx["S"], ctx["args"], ctx["work"]
    cal, _ = load_calibration(outage, S, args, work)
    tuning = json.loads((work / "tuning.json").read_text()) if (work / "tuning.json").exists() else {}
    closed_policy_seed(outage, S, cal, name, seed, work, tuning, args)
    return name, seed


def stage_closed(outage, S, args, work) -> None:
    tuning = json.loads((work / "tuning.json").read_text()) if (work / "tuning.json").exists() else {}
    pols = args.policies or [p for p in POLICIES if p != "finetuned" or finetuned_available(args)]
    tasks = []
    for name in pols:
        if name in tuning or name in ("reactive", "e001", "observed", "perfect_foresight"):
            tasks += [(name, s) for s in seeds_for(outage, "test", args) if not (work / f"closed_{name}_{s}.pkl").exists()]
        else:
            log(f"skip {name}: no tuned threshold (run openloop and tune first)")
    run_tasks(_task_closed, tasks, make_ctx(outage, S, args, work), args.procs)


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
            eps = episodes_from_pmax(prep["trace"]["times_s"], pm, thr, S.clear_decisions_effective, index)
            eps = [e for e in eps if e["start_s"] >= 0.0]
            stats.append(detection_stats(prep["table"], eps, S, float(prep["score"]["response"]["evaluated_days"]), prep["score"]["min_lead_s"]))
            costs.append(replay_objective(prep["table"], prep["score"]["by_event"], eps, prep["trace"], index, S, prep["score"]["min_lead_s"], S.response))
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

    try:
        dirty = bool(git("status", "--porcelain", "--", ".", ":(exclude)experiments/e003-heatwave/results"))
        return {"commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"), "dirty": str(dirty).lower()}
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        commit = os.environ.get("GPU_STACK_GIT_COMMIT")
        if not commit:
            raise RuntimeError("not a git checkout: set GPU_STACK_GIT_COMMIT to the archived commit, or run the report stage on the VM")
        return {"commit": commit, "branch": "archive", "dirty": "false", "source": "archive"}


def paired_by_seed(new: dict, old: dict, key: str, seeds: list, B: int, seed: int) -> dict:
    """Mean over seeds of (new - old) for a per-seed field, with a bootstrap interval."""
    a = [new[str(s)][key] for s in seeds]
    b = [old[str(s)][key] for s in seeds]
    return paired_difference(a, b, B, seed)


def compare_versions(policies: dict, old: dict, test: list, B: int) -> dict:
    """Side-by-side of the same policies in the older result files (``old``: label -> result) and this one (v3)."""
    out: dict = {
        "versions": {lab: {"scenario_id": r["scenario_id"], "seeds": r["seeds"], "same_test_seeds": r["seeds"]["test"] == test} for lab, r in old.items()},
        "policies": {},
    }
    for name, p3 in policies.items():
        o3 = p3["overall"]
        by_ver = {"v3": p3}
        for lab, res in old.items():
            if name in res["policies"]:
                by_ver[lab] = res["policies"][name]

        def hw(p):
            e = p["by_event_type"].get("hardware_fault")
            if e is None:
                return None
            return {"n_events": e["n_events"], "n_with_precursor": e["n_with_precursor"], "recall": e["recall"],
                    "recall_in_time": e["recall_in_time"], "lead_minutes_median": e["lead_minutes_median"], "lost_gpu_h": e["lost_gpu_h"]}

        def metric(f):
            return {lab: f(p) for lab, p in by_ver.items()}

        row = {
            "threshold": metric(lambda p: p.get("threshold")),
            "useful_gpu_h": metric(lambda p: p["overall"]["useful_gpu_h"]),
            "deficit_gpu_h": metric(lambda p: p["overall"]["deficit_gpu_h"]),
            "lost_gpu_h": metric(lambda p: p["overall"]["lost_gpu_h"]),
            "response_gpu_h": metric(lambda p: p["overall"]["response_gpu_h"]),
            "import_energy_above_kwh": metric(lambda p: p["overall"]["import_energy_above_kwh"]),
            "recall": metric(lambda p: p["overall"].get("recall")),
            "recall_in_time": metric(lambda p: p["overall"].get("recall_in_time")),
            "lead_minutes_median": metric(lambda p: None if p["overall"].get("lead_minutes") is None else p["overall"]["lead_minutes"]["median"]),
            "false_alarms_per_day": metric(lambda p: p["overall"].get("false_alarms_per_day")),
            "hardware_fault": metric(hw),
        }
        for lab in old:
            if lab in by_ver and all(str(sd) in by_ver[lab]["per_seed"] and str(sd) in p3["per_seed"] for sd in test):
                row[f"paired_v3_minus_{lab}"] = {
                    "deficit_gpu_h": paired_by_seed(p3["per_seed"], by_ver[lab]["per_seed"], "deficit_gpu_h", test, B, 81),
                    "lost_gpu_h": paired_by_seed(p3["per_seed"], by_ver[lab]["per_seed"], "lost_gpu_h", test, B, 82),
                    "response_gpu_h": paired_by_seed(p3["per_seed"], by_ver[lab]["per_seed"], "response_gpu_h", test, B, 83),
                }
        out["policies"][name] = row
    return out


def stage_report(outage, S, args, work) -> None:
    B = S.bootstrap_resamples
    cal, index = load_calibration(outage, S, args, work)
    tuning = json.loads((work / "tuning.json").read_text())
    test = seeds_for(outage, "test", args)
    train = seeds_for(outage, "train", args)
    tune = tuning_seeds(outage, args)
    preps = {s: load_pickle(work / f"prep_{s}.pkl") for s in sorted(set(train + tune + test))}
    policies: dict = {}
    runs_by_policy: dict = {}
    not_run: dict = {}
    decomposition: dict = {}
    ref_ledgers = [preps[s]["ref_ledger"] for s in test]
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
                "useful_gpu_h": r["score"]["summary"]["useful_gpu_hours"],
                "deficit_gpu_h": r["score"]["deficit_gpu_h"], "response_gpu_h": r["score"]["response"]["total_gpu_h"],
                "n_alarms": r["score"]["response"]["n_alarms"], "n_false_alarms": r["score"]["response"]["n_false_alarms"],
                "import_energy_above_kwh": r["score"]["summary"]["import_energy_above_kwh"],
            }
            for r in recs
        }
        policies[name] = agg
        decomposition[name] = decompose_deficit(runs, ref_ledgers, B)
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
                "useful_gpu_h_minus_reactive": paired_difference(
                    [r["summary"]["useful_gpu_hours"] for r in runs], [r["summary"]["useful_gpu_hours"] for r in base], B, 74),
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
    cfg0 = build_config(seed_scenario(outage, test[0]), seed=test[0])
    ref_useful = {str(s): float(preps[s]["ref_useful"]) for s in test}
    reference = {
        "useful_gpu_h_event_free_per_seed": ref_useful,
        "useful_gpu_h_event_free": bootstrap_ci(list(ref_useful.values()), B, 61),
        "ledger_gpu_h_event_free_mean": {k: float(np.mean([preps[s]["ref_ledger"][k] for s in test])) for k in preps[test[0]]["ref_ledger"]},
        "note": "useful GPU-hours of the event-free run of the same seed; deficit_gpu_h = this minus the policy's useful GPU-hours",
    }
    headline = {}
    for name, agg in policies.items():
        o = agg["overall"]
        headline[name] = {
            "label": agg["label"], "threshold": agg["threshold"],
            "useful_gpu_h": o["useful_gpu_h"], "deficit_gpu_h": o["deficit_gpu_h"], "lost_gpu_h": o["lost_gpu_h"],
            "response_gpu_h": o["response_gpu_h"], "import_energy_above_kwh": o["import_energy_above_kwh"],
            "deficit_vs_reactive_paired": paired.get(name, {}).get("deficit_gpu_h_minus_reactive"),
            "useful_vs_reactive_paired": paired.get(name, {}).get("useful_gpu_h_minus_reactive"),
        }
    old: dict = {}
    if args.compare_previous:
        for lab, path in (("v1", V1_RESULT), ("v2", V2_RESULT)):
            if path.exists():
                old[lab] = json.loads(path.read_text())["result"]
    versions = compare_versions(policies, old, test, B) if old else None
    reactive_matches = None
    if old and "reactive" in policies:
        reactive_matches = {lab: abs(r["policies"]["reactive"]["overall"]["useful_gpu_h"]["mean"] - policies["reactive"]["overall"]["useful_gpu_h"]["mean"]) < 1e-9 for lab, r in old.items()}
    design_record = json.loads((work / "design.json").read_text()) if (work / "design.json").exists() else None
    result = {
        "data_kind": "simulated",
        "scenario_id": outage["scenario_id"],
        "seeds": {"train": train, "design_extra": [s for s in seeds_for(outage, "design", args) if s not in train], "tuning": tune, "test": test},
        "settings": {k: (list(v) if isinstance(v, tuple) else (v.to_dict() if isinstance(v, ResponseDesign) else v)) for k, v in S.__dict__.items()},
        "response_design": None if S.response is None else S.response.to_dict(),
        "calibration": cal.to_dict(),
        "series": {"n_series": len(index), "keys": [list(k) for k in index.keys]},
        "horizon_s": cfg0.horizon_s,
        "event_counts_test_seeds": event_counts,
        "design": design_record,
        "tuning": tuning,
        "threshold_sweep_open_loop_test_seeds": sweep,
        "event_free_reference": reference,
        "headline_useful_and_deficit": headline,
        "policies": policies,
        "paired_vs_reactive": paired,
        "deficit_decomposition_test_seeds": decomposition,
        "comparison_with_previous_versions": versions,
        "reactive_equals_previous_versions": reactive_matches,
        "not_run": not_run,
        "finetuned_weights": args.finetuned_weights if finetuned_available(args) else None,
        "notes": [
            "All data are simulated; no measured cluster data are used.",
            "The response design was chosen on training seeds only (perfect foresight, the design block); thresholds were tuned on training seeds with a replay objective of that response; both were then used unchanged on held-out seeds.",
            "The sweep is open loop on the recorded reactive traces; closed-loop numbers are in policies.",
            "The perfect-foresight policy reads event times of the reactive run and is an upper bound, not a deployable policy.",
            "deficit_gpu_h is the useful GPU-hours of the event-free run minus the policy run on the same seed; useful GPU-hours are counted at the end of the 15-hour window, so stalls that the schedule absorbs cost nothing in them (see the deficit decomposition).",
            "Forecast compute: every forecaster's open-loop probabilities are computed once per seed on all decision points (no subsampling) and cached; tuning and the threshold sweep reuse that cache.",
            "Each forecast-driven policy then runs closed loop once per held-out seed at its tuned threshold; those runs forecast at every decision point because the response changes the trajectory the forecaster sees.",
            "The simulator calls the controller every control step (60 s); forecasts and warnings run every 600 s, and the response chain (checkpoint, then pause) runs on the 60 s tick.",
        ],
        "assumptions": outage["assumptions"],
    }
    from heatwave.provenance import write_result

    base_scenario = SCENARIO.parent / outage["base_scenario"]
    inputs = [SCENARIO, base_scenario] + [p for lab, p in (("v1", V1_RESULT), ("v2", V2_RESULT)) if lab in old]
    record = write_result(OUT, result, script=__file__, data_kind="simulated", inputs=inputs,
                          notes="Held-out seeds; response designed and thresholds tuned on training seeds; all outputs simulated."
                                + (f" Design search, open-loop, tuning and closed-loop stages ran on: {args.ran_on}." if args.ran_on else ""))
    record["provenance"]["git"] = git_state()
    record["provenance"]["script"] = str(Path(__file__).resolve().relative_to(ROOT))
    record["provenance"]["script_sha256"] = file_sha256(__file__)
    record["provenance"]["module_sha256"] = file_sha256(ROOT / "gpu_stack" / "research" / "heatwave_outage.py")
    record["provenance"]["inputs"] = {str(Path(p).resolve().relative_to(ROOT)): file_sha256(p) for p in inputs}
    record["provenance"]["seeds"] = {"train": train, "test": test}
    OUT.write_text(json.JSONEncoder(indent=1, allow_nan=False).encode(_jsonable(record)) + "\n")
    log(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB)")


def set_paths(scenario: Path, out: Path) -> None:
    global SCENARIO, OUT
    SCENARIO, OUT = Path(scenario).resolve(), Path(out).resolve()


def main() -> None:
    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work-dir", required=True, type=Path)
    ap.add_argument("--stage", default="all", choices=("prepare", "design", "openloop", "tune", "closed", "report", "all"))
    ap.add_argument("--policies", nargs="*", default=None, choices=POLICIES)
    ap.add_argument("--forecasters", nargs="*", default=None, choices=FORECASTERS + ("perfect",))
    ap.add_argument("--n-test", type=int, default=0, help="use only the first N held-out seeds (0 = all)")
    ap.add_argument("--n-design", type=int, default=0, help="use only the first N extra training seeds (0 = all)")
    ap.add_argument("--only-seeds", type=int, nargs="*", default=None,
                    help="restrict the openloop/closed stages to these held-out seeds (several processes can share the work; report needs all)")
    ap.add_argument("--reverse", action="store_true", help="open-loop pass visits seeds last to first (a second process can share the work)")
    ap.add_argument("--procs", type=int, default=1, help="processes for the independent tasks of a stage")
    ap.add_argument("--nice", type=int, default=0, help="nice increment for worker processes")
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--batch-size", type=int, default=512)
    ap.add_argument("--scenario", type=Path, default=SCENARIO, help="outage scenario file (default outage-scenario-v3.json)")
    ap.add_argument("--out", type=Path, default=OUT, help="result file written by the report stage")
    ap.add_argument("--no-compare-previous", dest="compare_previous", action="store_false", help="skip the side-by-side with results/outage-v1.json and outage-v2.json")
    ap.add_argument("--ran-on", default=None, help="hardware description recorded in the result notes (stages other than report)")
    ap.add_argument("--finetuned-weights", default=None)
    ap.add_argument("--finetuned-size", default="28M")
    args = ap.parse_args()
    if args.procs > 1 and args.threads is None:
        args.threads = 1
    args.work_dir.mkdir(parents=True, exist_ok=True)
    set_paths(args.scenario, args.out)
    outage = load_outage_scenario(SCENARIO)
    S = OutageSettings.from_scenario(outage)
    work = args.work_dir
    stages = ("prepare", "design", "openloop", "tune", "closed", "report") if args.stage == "all" else (args.stage,)
    funcs = {"prepare": stage_prepare, "design": stage_design, "openloop": stage_openloop, "tune": stage_tune, "closed": stage_closed, "report": stage_report}
    for st in stages:
        t0 = time.time()
        funcs[st](outage, S, args, work)
        log(f"stage {st} done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
