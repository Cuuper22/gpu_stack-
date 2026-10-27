"""Tests for the Heatwave outage-response module.

Every run here is simulated.  Horizons are short and job lists tiny; the full
experiment lives in ``experiments/e003-heatwave/run_outage.py``.  Expected
values are computed from the configuration the simulator builds, never typed
in as power or checkpoint numbers.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from gpu_stack.research.heatwave_events import GridCurtailment, HardwareFault, Precursor
from gpu_stack.research.heatwave_outage import (
    EpisodeTracker,
    ForecastWarningController,
    OracleAlarm,
    OracleController,
    OutageSettings,
    PersistenceForecaster,
    TraceRecorder,
    aggregate_runs,
    bootstrap_ci,
    build_event_table,
    episodes_from_pmax,
    exceedance_probability,
    job_costs,
    load_outage_scenario,
    oracle_alarms_from_reference,
    oracle_scenario,
    oracle_settings,
    periodic_local_jobs,
    ratio_ci,
    run_policy,
    score_run,
    seed_scenario,
)
from gpu_stack.research.heatwave_sim import Job, build_config

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "experiments" / "e003-heatwave" / "outage-scenario-v1.json"

LEVELS = np.linspace(0.05, 0.95, 21)


def outage_and_settings():
    outage = load_outage_scenario(SCENARIO)
    return outage, OutageSettings.from_scenario(outage)


def make_job(job_id="j1", n=8, start=0.0, duration=7200.0, step=4.0, ckpt_every=3600.0, ckpt_dur=30.0, **kw) -> Job:
    values = dict(
        job_id=job_id, n_gpus=n, submit_s=0.0, start_s=start, duration_s=duration, step_time_s=step,
        checkpoint_every_s=ckpt_every, checkpoint_duration_s=ckpt_dur, value_per_gpu_hour=2.0, flexible=False, site_id="site-a",
    )
    values.update(kw)
    return Job(**values)


def tiny_scenario(outage, horizon_s, jobs, events=()):
    sc = copy.deepcopy(outage["sim"])
    sc["horizon_s"] = horizon_s
    sc["events"] = [e.to_dict() for e in events]
    sc["jobs"] = {"list": [j.to_dict() for j in jobs]}
    sc["controller_interval_s"] = 60.0
    return sc


def fast_settings(S: OutageSettings) -> OutageSettings:
    return replace(S, decision_interval_s=60.0, context_steps=12, horizon_steps=6, warmup_s=0.0, recheckpoint_s=300.0)


# ---------------------------------------------------------------------------
# scenario and seeds
# ---------------------------------------------------------------------------


def test_scenario_is_labeled_simulated_and_loads():
    outage, S = outage_and_settings()
    assert outage["data_kind"] == "simulated"
    assert outage["sim"]["data_kind"] == "simulated"
    assert set(outage["seeds"]["train"]).isdisjoint(outage["seeds"]["test"])
    assert S.horizon_s == S.horizon_steps * S.decision_interval_s
    assert outage["sim"]["controller_interval_s"] == S.decision_interval_s


def test_seed_scenario_is_deterministic_and_event_free_variant_is_empty():
    outage, S = outage_and_settings()
    a, b = seed_scenario(outage, 201), seed_scenario(outage, 201)
    assert a == b
    assert seed_scenario(outage, 202)["events"] != a["events"]
    assert a["events"], "the generator draws events"
    assert all(e["onset_s"] >= S.warmup_s for e in a["events"])
    assert seed_scenario(outage, 201, with_events=False)["events"] == []
    assert a["jobs"]["generate"]["seed"] != seed_scenario(outage, 202)["jobs"]["generate"]["seed"]


def test_periodic_local_jobs_splits_even_single_site_jobs_only():
    even, odd = make_job("e", n=8), make_job("o", n=7)
    already = make_job("m", n=8, multisite=True, site_id=None, average_every_steps=4)
    out = periodic_local_jobs([even, odd, already])
    assert out[0].multisite and out[0].average_every_steps == 8 and out[0].site_id is None
    assert out[1] == odd
    assert out[2] == already


# ---------------------------------------------------------------------------
# probabilities and warning episodes
# ---------------------------------------------------------------------------


def test_exceedance_probability_from_quantiles():
    values = np.broadcast_to(np.linspace(10.0, 20.0, 21), (3, 4, 21)).copy()
    hi = exceedance_probability(values, LEVELS, np.full((3, 4), 25.0))
    lo = exceedance_probability(values, LEVELS, np.full((3, 4), 5.0))
    assert np.allclose(hi, 1.0 - LEVELS[-1])
    assert np.allclose(lo, 1.0 - LEVELS[0])
    mid = np.stack([exceedance_probability(values, LEVELS, np.full((3, 4), x))[0, 0] for x in (11.0, 14.0, 17.0, 19.0)])
    assert np.all(np.diff(mid) < 0)
    assert np.isclose(exceedance_probability(values, LEVELS, np.full((3, 4), 15.0))[0, 0], 0.5)


def test_exceedance_probability_zero_spread_and_missing_limit():
    flat = np.full((2, 3, 21), 7.0)
    assert np.all(exceedance_probability(flat, LEVELS, np.full((2, 3), 6.0)) == 1.0)
    assert np.all(exceedance_probability(flat, LEVELS, np.full((2, 3), 8.0)) == 0.0)
    assert np.all(exceedance_probability(flat, LEVELS, np.full((2, 3), np.nan)) == 0.0)
    with pytest.raises(ValueError):
        exceedance_probability(flat, LEVELS[:-1], np.full((2, 3), 1.0))


def test_episode_tracker_hysteresis_and_end_time():
    tr = EpisodeTracker(2, threshold=0.5, clear_decisions=2)
    series = [(0, 0.1), (1, 0.6), (2, 0.2), (3, 0.7), (4, 0.2), (5, 0.2), (6, 0.9)]
    for t, p in series:
        tr.update(float(t), np.array([p, 0.0]))
    eps = tr.finish()
    assert [(e["k"], e["start_s"], e["end_s"]) for e in eps] == [(0, 1.0, 3.0), (0, 6.0, 6.0)]
    assert eps[0]["peak_p"] == pytest.approx(0.7)
    assert eps[0]["n_decisions"] == 2


def test_episodes_from_pmax_matches_tracker_and_labels_with_index():
    pm = np.zeros((6, 2))
    pm[2:4, 1] = 0.8
    eps = episodes_from_pmax(np.arange(6) * 60.0, pm, 0.5, 1)
    assert len(eps) == 1 and eps[0]["k"] == 1 and eps[0]["start_s"] == 120.0 and eps[0]["end_s"] == 180.0


# ---------------------------------------------------------------------------
# simulator interface
# ---------------------------------------------------------------------------


def test_hardware_precursor_is_visible_in_the_faulty_gpu_temperature():
    outage, _ = outage_and_settings()
    strength, lead, onset, slot = 6.0, 1200.0, 2400.0, 2

    def event(with_precursor: bool):
        pre = (Precursor("gpu_temp_c", lead, strength),) if with_precursor else ()
        return HardwareFault("h1", "site-a", "a1", slot, onset, 120.0, precursors=pre)

    class Watch:
        def __init__(self):
            self.rows = []

        def decide(self, t_s, vs):
            self.rows.append((t_s, np.array(vs.now["gpu_temp_c"], dtype=float)))
            return ()

    peaks = []
    for flag in (True, False):
        sc = tiny_scenario(outage, 3600, [make_job(duration=3600.0)], [event(flag)])
        w = Watch()
        _, cfg = run_policy(sc, w, 0)
        racks = [r for lay in cfg.layouts for r in lay.racks]
        first = sum(r.n_gpus for r in racks[: [r.rack_id for r in racks].index("a1")])
        peaks.append(max(row[first + slot] for t, row in w.rows if t < onset))
    assert peaks[0] - peaks[1] > 0.5 * strength


def test_job_costs_follow_the_simulator_configuration():
    outage, _ = outage_and_settings()
    cfg = build_config(tiny_scenario(outage, 3600, [make_job(n=8, ckpt_dur=30.0)]), seed=0)
    job = cfg.jobs[0]
    c = job_costs(job, cfg.transfer)
    assert c["checkpoint"] == pytest.approx(job.n_gpus * job.checkpoint_duration_s / 3600.0)
    assert c["move"] > c["checkpoint"]
    twice = job_costs(replace(job, checkpoint_duration_s=2 * job.checkpoint_duration_s), cfg.transfer)
    assert twice["checkpoint"] == pytest.approx(2 * c["checkpoint"])


# ---------------------------------------------------------------------------
# scoring and policies on a tiny simulated window
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def faulted():
    """One non-flexible job, a hardware fault without precursor, and a long checkpoint interval."""
    outage, S = outage_and_settings()
    S = fast_settings(S)
    sc = tiny_scenario(outage, 7200, [make_job(duration=7200.0, ckpt_every=3000.0)],
                       [HardwareFault("h1", "site-a", "a1", 2, 2900.0, 600.0)])
    rec = TraceRecorder(S)
    res, cfg = run_policy(sc, rec, 0)
    table = build_event_table(cfg, res.events, S)
    ex = rec.export()
    ex["episodes"] = []
    ref = float(run_policy(tiny_scenario(outage, 7200, [make_job(duration=7200.0, ckpt_every=3000.0)]), None, 0)[0].summary()["useful_gpu_hours"])
    score = score_run(res, cfg, table, ex, S, ref)
    return {"outage": outage, "S": S, "sc": sc, "res": res, "cfg": cfg, "table": table, "score": score, "ref": ref}


def test_reactive_loses_work_and_attribution_conserves_it(faulted):
    res, score = faulted["res"], faulted["score"]
    lost = res.summary()["lost_gpu_hours"]
    assert lost > 0.0
    attributed = sum(e["lost_gpu_h"] for e in score["by_event"]) + score["unattributed"]["lost_gpu_h"]
    assert attributed == pytest.approx(lost, rel=1e-6)
    fault_rows = [e for e in score["by_event"] if e["kind"] == "hardware_fault"]
    assert len(fault_rows) == 1 and fault_rows[0]["lost_gpu_h"] > 0.0 and not fault_rows[0]["caught"]
    assert score["response"]["n_alarms"] == 0 and score["response"]["total_gpu_h"] == 0.0
    assert score["data_kind"] == "simulated"


def test_perfect_foresight_loses_less_than_reactive_and_catches_the_event(faulted):
    S, sc, cfg, res, table = faulted["S"], faulted["sc"], faulted["cfg"], faulted["res"], faulted["table"]
    So = oracle_settings(S, cfg.control_dt_s)
    alarms = oracle_alarms_from_reference(cfg, res.events, [], So)
    assert alarms and all(isinstance(a, OracleAlarm) for a in alarms)
    ctrl = OracleController(So, alarms)
    res_o, cfg_o = run_policy(oracle_scenario(sc), ctrl, 0)
    score_o = score_run(res_o, cfg_o, table, ctrl.export(), So, faulted["ref"])
    assert res_o.summary()["lost_gpu_hours"] < 0.5 * res.summary()["lost_gpu_hours"]
    assert all(e["caught_in_time"] for e in score_o["by_event"] if e["kind"] == "hardware_fault")
    assert score_o["response"]["total_gpu_h"] > 0.0


def test_persistence_warning_on_announced_curtailment_checkpoints_then_resumes():
    outage, S = outage_and_settings()
    S = fast_settings(S)
    flex = make_job("f", n=16, duration=7200.0, flexible=True, ckpt_every=3000.0)
    sc = tiny_scenario(outage, 7200, [flex], [GridCurtailment("g1", "site-a", 1800.0, 900.0, 0.2, announce_lead_s=1500.0)])
    ctrl = ForecastWarningController(S, PersistenceForecaster(), 0.5, None, "persistence")
    res, cfg = run_policy(sc, ctrl, 0)
    ex = ctrl.export()
    site_eps = [e for e in ex["episodes"] if e["class"] == "curtail"]
    assert site_eps and site_eps[0]["start_s"] < 1800.0
    applied = [a for a in res.actions if a["status"] == "applied"]
    assert applied, "the response ran at least one action"
    table = build_event_table(cfg, res.events, S)
    score = score_run(res, cfg, table, ex, S, 0.0)
    row = [e for e in score["by_event"] if e["kind"] == "grid_curtailment"][0]
    assert row["caught"] and row["lead_s"] is not None and row["lead_s"] > 0.0


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------


def test_bootstrap_helpers_are_deterministic_and_pooled():
    vals = [1.0, 2.0, 3.0, 4.0]
    a, b = bootstrap_ci(vals, 200, 3), bootstrap_ci(vals, 200, 3)
    assert a == b and a["mean"] == pytest.approx(2.5) and a["lo"] <= a["mean"] <= a["hi"]
    r = ratio_ci([1, 2, 3], [2, 4, 6], 200, 1)
    assert r["value"] == pytest.approx(0.5) and r["lo"] == pytest.approx(0.5) and r["hi"] == pytest.approx(0.5)
    assert bootstrap_ci([], 50)["n"] == 0


def test_aggregate_hides_detection_fields_without_a_warning_rule(faulted):
    S = faulted["S"]
    runs = [faulted["score"]] * 3
    with_w = aggregate_runs(runs, S, has_warnings=True)
    without = aggregate_runs(runs, S, has_warnings=False)
    assert with_w["overall"]["recall"]["value"] == 0.0
    assert without["overall"]["recall"] is None and without["has_warnings"] is False
    assert without["no_precursor"]["n_events"] == 3
    assert without["no_precursor"]["lost_gpu_h"]["mean"] == pytest.approx(with_w["no_precursor"]["lost_gpu_h"]["mean"])
    assert with_w["data_kind"] == "simulated"
