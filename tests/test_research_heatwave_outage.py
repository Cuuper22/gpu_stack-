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


# ---------------------------------------------------------------------------
# per-GPU residual channel (outage scenario v2)
# ---------------------------------------------------------------------------

SCENARIO_V2 = ROOT / "experiments" / "e003-heatwave" / "outage-scenario-v2.json"


def gpu_settings(S: OutageSettings) -> OutageSettings:
    """Per-GPU channel on, 60 s decisions, short baseline so tiny windows can use it."""
    return replace(
        S, decision_interval_s=60.0, context_steps=12, horizon_steps=6, warmup_s=0.0, recheckpoint_s=300.0,
        anomaly_baseline_window_s=3600.0, anomaly_baseline_gap_s=600.0, per_gpu_channel=True,
    )


def v2_and_settings():
    outage = load_outage_scenario(SCENARIO_V2)
    return outage, OutageSettings.from_scenario(outage)


class Layout:
    """Dry run without events: which GPU slots of one rack hold which job, and each GPU's gain."""

    def __init__(self):
        self.job_slots = {}
        self.k_gpu = None
        self.rack_start = None

    def bind(self, run, cfg):
        self.run = run
        self.k_gpu = np.array(run.k_gpu)
        self.rack_start = np.array(run.rack_start)

    def decide(self, t_s, vs):
        if not self.job_slots and t_s > 0:
            run = self.run
            for sh in run.shards:
                if sh.gpus.size:
                    self.job_slots.setdefault(sh.job.job_id, []).extend(int(g) for g in sh.gpus)
        return ()


def layout_of(outage, jobs, horizon_s=3600):
    lay = Layout()
    sc = tiny_scenario(outage, horizon_s, jobs)
    cfg = build_config(sc, seed=0)
    from gpu_stack.research.heatwave_outage import OutageRun

    run = OutageRun(cfg, lay, 0)
    lay.bind(run, cfg)
    run.run()
    return lay, cfg


def test_scenario_v2_differs_from_v1_only_by_the_per_gpu_channel():
    v1, S1 = outage_and_settings()
    v2, S2 = v2_and_settings()
    assert not S1.per_gpu_channel and S2.per_gpu_channel
    assert v1["seeds"] == v2["seeds"] and v1["event_generation"] == v2["event_generation"] and v1["seed_streams"] == v2["seed_streams"]
    a = {k: v for k, v in v1["outage"].items()}
    b = {k: v for k, v in v2["outage"].items() if k != "per_gpu_channel"}
    assert a == b
    assert v2["data_kind"] == "simulated" and v2["sim"]["data_kind"] == "simulated"
    # the simulated inputs of a seed do not depend on the base scenario version (both seeds are set per run seed)
    assert seed_scenario(v1, 201)["events"] == seed_scenario(v2, 201)["events"]
    assert seed_scenario(v1, 201)["jobs"]["generate"] == seed_scenario(v2, 201)["jobs"]["generate"]


def test_series_layout_appends_one_series_per_gpu_after_the_v1_series():
    outage, S = v2_and_settings()
    cfg = build_config(seed_scenario(outage, 201, with_events=False), seed=201)
    from gpu_stack.research.heatwave_outage import SeriesIndex, gpu_unit_id

    base, full = SeriesIndex.from_config(cfg), SeriesIndex.from_config(cfg, True)
    n_gpus = sum(r.n_gpus for lay in cfg.layouts for r in lay.racks)
    assert len(full) == len(base) + n_gpus and full.keys[: len(base)] == base.keys
    assert len(set(full.gpu_units)) == n_gpus and full.gpu_units[0] == gpu_unit_id("a1", 0)
    assert all(full.gpu_parts(u) == (u.rsplit("/", 1)[0], int(u.rsplit("/", 1)[1])) for u in full.gpu_units)
    assert set(full.classes()[len(base):]) == {"hardware"}


def test_residual_cancels_job_power_changes_that_a_plain_difference_keeps():
    from gpu_stack.research.heatwave_outage import GpuResidualChannel

    outage, S = v2_and_settings()
    S = gpu_settings(S)
    rng = np.random.default_rng(0)
    gains = 0.0256 * (1.0 + 0.1 * rng.normal(size=12))
    key = np.zeros(12, dtype=np.int64)
    ch = GpuResidualChannel(12, S, floor_k=1.0)
    power = np.where(np.arange(40) % 8 < 4, 700.0, 300.0)  # the whole job changes power every 4 decisions
    out, plain = [], []
    for p in power:
        excess = gains * p
        out.append(ch.update(excess, key))
        plain.append(excess - np.median(excess))
    out, plain = np.array(out), np.array(plain)
    late = out[20:]
    assert np.isfinite(late).all()
    assert np.abs(late).max() < 1e-9
    assert np.abs(plain[20:]).max() > 0.5  # the plain difference to the peer median moves by several tenths of a kelvin or more


def test_residual_sees_a_creep_on_one_gpu_and_marks_group_changes_missing():
    from gpu_stack.research.heatwave_outage import GpuResidualChannel

    outage, S = v2_and_settings()
    S = gpu_settings(S)
    gains = np.full(10, 0.025)
    key = np.zeros(10, dtype=np.int64)
    ch = GpuResidualChannel(10, S, floor_k=1.0)
    res = []
    for i in range(60):
        excess = gains * 600.0
        if i >= 40:
            excess = excess.copy()
            excess[3] += 0.25 * (i - 40)  # 0.25 K per decision on GPU 3 only
        if i == 50:
            key = key.copy()
            key[7] = 5  # GPU 7 changes job group: its sample is missing at that decision
        res.append(ch.update(excess, key))
    res = np.array(res)
    assert res[59, 3] == pytest.approx(0.25 * 19, abs=1e-6)
    others = np.delete(res[59], 3)
    assert np.nanmax(np.abs(others)) < 1e-9
    assert np.isnan(res[50, 7]) and np.isfinite(res[49, 7])


def test_residual_channel_uses_no_future_samples():
    from gpu_stack.research.heatwave_outage import GpuResidualChannel

    outage, S = v2_and_settings()
    S = gpu_settings(S)
    rng = np.random.default_rng(3)
    n, g = 50, 16
    gains = 0.0256 * (1.0 + 0.1 * rng.normal(size=g))
    inputs = [(gains * rng.uniform(300, 700) + rng.normal(0, 0.1, size=g), np.zeros(g, dtype=np.int64)) for _ in range(n)]
    d = 30
    a = GpuResidualChannel(g, S, 1.0)
    out_a = [a.update(x, k) for x, k in inputs]
    changed = list(inputs[: d + 1]) + [(rng.uniform(0, 50, size=g), rng.integers(0, 3, size=g)) for _ in range(n - d - 1)]
    b = GpuResidualChannel(g, S, 1.0)
    out_b = [b.update(x, k) for x, k in changed]
    for i in range(d + 1):
        assert np.array_equal(out_a[i], out_b[i], equal_nan=True)
    assert not np.array_equal(out_a[-1], out_b[-1], equal_nan=True)


def test_channel_rows_before_a_precursor_start_do_not_depend_on_the_event():
    outage, S = v2_and_settings()
    S = gpu_settings(S)
    job = make_job(n=16, duration=7200.0)
    onset, lead = 4800.0, 1200.0
    pre = (Precursor("gpu_temp_c", lead, 6.0),)
    rows = []
    for ev in ([], [HardwareFault("h1", "site-a", "a1", 3, onset, 120.0, precursors=pre)]):
        rec = TraceRecorder(S)
        run_policy(tiny_scenario(outage, 7200, [job], ev), rec, 0)
        rows.append(rec.trace())
    t = rows[0]["times_s"]
    before = t < onset - lead - 1e-9
    assert before.sum() > 20
    assert np.array_equal(rows[0]["samples"][:, before], rows[1]["samples"][:, before], equal_nan=True)
    assert not np.array_equal(rows[0]["samples"][:, ~before], rows[1]["samples"][:, ~before], equal_nan=True)


def test_v1_series_are_unchanged_when_the_per_gpu_channel_is_on():
    outage, S = v2_and_settings()
    S_on = gpu_settings(S)
    S_off = replace(S_on, per_gpu_channel=False)
    job = make_job(n=16, duration=3600.0)
    traces = []
    for st in (S_off, S_on):
        rec = TraceRecorder(st)
        run_policy(tiny_scenario(outage, 3600, [job]), rec, 0)
        traces.append(rec.trace())
    n_v1 = traces[0]["samples"].shape[0]
    assert traces[1]["samples"].shape[0] > n_v1
    assert np.array_equal(traces[0]["samples"], traces[1]["samples"][:n_v1], equal_nan=True)
    assert "gpu_flex_move_gpu_h" not in traces[0] and traces[1]["gpu_nonflex_checkpoint_gpu_h"].shape[1] == traces[1]["samples"].shape[0] - n_v1


def creep_scenario(outage, jobs, events=()):
    """Six simulated hours with the scenario's own 600 s decision interval."""
    sc = tiny_scenario(outage, 21600, jobs, events)
    sc["controller_interval_s"] = 600.0
    return sc


@pytest.fixture(scope="module")
def creep():
    """Two 8-GPU jobs on rack a1; the lowest-gain GPU of job j1 creeps by 2.4 K over 3600 s, then faults.

    2.4 K is below the smallest gap between the rack's hottest GPU and this GPU in the same run without
    the event during the ramp, so the rack maximum never shows the creep; the test checks that.
    """
    outage, S = v2_and_settings()
    S = replace(S, warmup_s=0.0, context_steps=12)
    jobs = [make_job("j1", n=8, duration=21600.0), make_job("j2", n=8, duration=21600.0)]
    lay, cfg0 = layout_of(outage, jobs)
    first_rack_gpus = set(range(int(cfg0.layouts[0].racks[0].n_gpus)))
    j1 = [g for g in lay.job_slots["j1"] if g in first_rack_gpus]
    j2 = [g for g in lay.job_slots["j2"] if g in first_rack_gpus]
    assert len(j1) == 8 and len(j2) == 8
    slot = min(j1, key=lambda g: lay.k_gpu[g])
    strength, lead, onset = 2.4, 3600.0, 18000.0
    ev = HardwareFault("h1", "site-a", "a1", int(slot), onset, 300.0, precursors=(Precursor("gpu_temp_c", lead, strength),))
    return {"outage": outage, "S": S, "jobs": jobs, "slot": int(slot), "j2_gpus": j2, "strength": strength, "lead": lead,
            "onset": onset, "event": ev, "lay": lay}


class WatchRecorder(TraceRecorder):
    """Trace recorder that also keeps one GPU's visible temperature and its rack's visible maximum."""

    def __init__(self, S, g, rack_i):
        super().__init__(S)
        self.g, self.rack_i, self.seen = g, rack_i, []

    def decide(self, t_s, vs):
        self.seen.append((t_s, float(vs.now["gpu_temp_c"][self.g]), float(vs.now["max_gpu_temp_c"][self.rack_i])))
        return super().decide(t_s, vs)


def test_residual_sees_a_one_gpu_precursor_that_the_rack_maximum_hides(creep):
    from gpu_stack.research.heatwave_outage import CH_GPU_RESID, CH_GPU_TEMP, SeriesIndex, gpu_unit_id

    outage, S, onset, lead, strength = creep["outage"], creep["S"], creep["onset"], creep["lead"], creep["strength"]
    traces, seen = {}, {}
    for name, ev in (("with", [creep["event"]]), ("without", [])):
        rec = WatchRecorder(S, creep["slot"], 0)
        _, cfg = run_policy(creep_scenario(outage, creep["jobs"], ev), rec, 0)
        traces[name], seen[name] = rec.trace(), np.array(rec.seen)
    idx = SeriesIndex.from_config(cfg, True)
    t = traces["with"]["times_s"]
    k_res = idx.index(gpu_unit_id("a1", creep["slot"]), CH_GPU_RESID)
    k_max = idx.index("a1", CH_GPU_TEMP)
    pre = (t >= onset - lead) & (t < onset)
    late_ramp = (t >= onset - 2 * S.decision_interval_s) & (t < onset)
    # the creep is visible in the faulty GPU's own sensor ...
    own = seen["with"][late_ramp, 1] - seen["without"][late_ramp, 1]
    assert own.max() > 0.8 * strength
    # ... but the rack's visible maximum is another GPU's temperature the whole time, and is unchanged by the creep
    assert np.all(seen["with"][pre, 2] > seen["with"][pre, 1])
    assert np.allclose(traces["with"]["samples"][k_max][pre], traces["without"]["samples"][k_max][pre])
    # the residual follows the ramp (kelvin) and ends above the largest residual of any GPU in the run without the event
    gk = [k for k, (u, c) in enumerate(idx.keys) if c == CH_GPU_RESID]
    noise = np.nanmax(np.abs(traces["without"]["samples"][gk]))
    ramp = traces["with"]["samples"][k_res]
    assert np.nanmax(ramp[late_ramp]) > 0.5 * strength
    assert np.nanmax(ramp[late_ramp]) > noise
    # no other GPU of the cluster moves by more than the noise level of the run without the event (+ a small allowance)
    others = [k for k in gk if k != k_res]
    assert np.nanmax(np.abs(traces["with"]["samples"][others][:, t < onset])) < noise + 0.25


def test_gpu_warning_protects_only_the_job_that_holds_the_gpu(creep):
    from gpu_stack.research.heatwave_outage import Calibration, gpu_unit_id

    outage, S, onset = creep["outage"], creep["S"], creep["onset"]
    cal = Calibration({"supply_anom": 1.0e9, "gpu_anom": 1.0e9, "gpu_resid": 1.5}, 1.0, {}, "test")
    ctrl = ForecastWarningController(S, PersistenceForecaster(), 0.5, cal, "persistence")
    sc = creep_scenario(outage, creep["jobs"], [creep["event"]])
    res, cfg = run_policy(sc, ctrl, 0)
    unit = gpu_unit_id("a1", creep["slot"])
    ex = ctrl.export()
    gpu_eps = [e for e in ex["episodes"] if e["channel"] == "gpu_resid"]
    assert gpu_eps and {e["unit"] for e in gpu_eps} == {unit} and {e["class"] for e in gpu_eps} == {"hardware"}
    assert gpu_eps[0]["start_s"] < onset
    applied = [a for a in res.actions if a["status"] == "applied"]
    assert applied and {a["detail"]["job_id"] for a in applied} == {"j1"}
    assert all(m["unit"] == unit for m in ex["meta_actions"])
    table = build_event_table(cfg, res.events, S)
    score = score_run(res, cfg, table, ex, S, 0.0)
    row = [e for e in score["by_event"] if e["kind"] == "hardware_fault"][0]
    assert row["caught"] and row["first_channel"] == "gpu_resid" and row["lead_s"] > 0.0
    assert score["response"]["n_false_alarms"] == 0
    alarm = [a for a in score["alarms"] if a["unit"] == unit][0]
    assert alarm["true"] and alarm["channels"] == ["gpu_resid"] and alarm["cost_gpu_h"] > 0.0


def test_a_warning_on_another_gpu_of_the_rack_does_not_count_as_catching_the_fault(faulted):
    from gpu_stack.research.heatwave_outage import classify_alarms, match_events, merge_alarms

    S, table = faulted["S"], faulted["table"]
    ev = [e for e in table if e["kind"] == "hardware_fault"][0]
    assert "a1/2" in ev["units"] and "a1" in ev["units"]

    def episode(unit):
        return {"unit": unit, "class": "hardware", "channel": "gpu_resid", "start_s": ev["onset_s"] - 1200.0,
                "end_s": ev["onset_s"] - 120.0, "peak_p": 1.0, "n_decisions": 2, "k": 0}

    right, wrong = [episode("a1/2")], [episode("a1/5")]
    assert match_events(table, right, S)[ev["event_id"]]["caught"]
    assert not match_events(table, wrong, S)[ev["event_id"]]["caught"]
    cls = classify_alarms(merge_alarms(wrong, S.episode_merge_gap_s), table, S)
    assert cls and not cls[0]["true"]
    assert classify_alarms(merge_alarms(right, S.episode_merge_gap_s), table, S)[0]["true"]


def test_replay_objective_prices_a_gpu_alarm_by_the_job_that_holds_the_gpu(creep):
    from gpu_stack.research.heatwave_outage import SeriesIndex, gpu_unit_id, replay_objective

    outage, S = creep["outage"], creep["S"]
    rec = TraceRecorder(S)
    res, cfg = run_policy(creep_scenario(outage, creep["jobs"]), rec, 0)
    trace = rec.trace()
    idx = SeriesIndex.from_config(cfg, True)
    unit = gpu_unit_id("a1", creep["slot"])
    ep = {"unit": unit, "class": "hardware", "channel": "gpu_resid", "start_s": 7200.0, "end_s": 7200.0, "peak_p": 1.0, "n_decisions": 1, "k": 0}
    r = replay_objective([], [], [ep], trace, idx, S, 60.0)
    expected = job_costs(cfg.jobs[0], cfg.transfer)["checkpoint"]  # j1 is not flexible: one checkpoint of its 8 GPUs
    assert r["alarm_gpu_h"] == pytest.approx(expected)
    assert expected == pytest.approx(8 * cfg.jobs[0].checkpoint_duration_s / 3600.0)
