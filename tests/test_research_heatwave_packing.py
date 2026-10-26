"""Tests for the e003 power-cap packing module (all simulated, short horizons)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from gpu_stack.research import heatwave_packing as hp
from gpu_stack.research.heatwave_sim import load_scenario

ROOT = Path(__file__).resolve().parents[1]
E003 = ROOT / "experiments" / "e003-heatwave"


class StubForecaster:
    """Persistence of the last ratio with a symmetric spread that grows with the level distance from the median."""

    name = "stub"

    def __init__(self, spread: float = 0.1) -> None:
        self.spread = spread

    def forecast(self, context, horizon, known_covariates=None, past_covariates=None):
        last = np.asarray(context)[:, 0, -1]
        levels = np.asarray(hp.QUANTILE_LEVELS)
        vals = last[:, None, None, None] * (1.0 + self.spread * (levels - 0.5))[None, None, None, :]
        return SimpleNamespace(values=np.broadcast_to(vals, (last.shape[0], 1, horizon, levels.size)).copy())


@pytest.fixture(scope="module")
def tiny():
    packing = hp.load_packing_scenario(E003 / "packing-scenario-v1.json")
    packing = copy.deepcopy(packing)
    packing["episode"].update({"horizon_s": 10800, "warmup_s": 3600, "min_context_bins": 6, "warm_ratio_bins": 6})
    packing["cap"]["calibration"] = {"idle_hours": 1, "full_hours": 1}
    packing["jobs"]["generate"].update({"duration_range_s": [1800, 7200], "utilization_goal": 1.5})
    sim = load_scenario(E003 / "sim-scenario-v2.json")
    cal = hp.calibrate_sites(sim, packing)
    return packing, sim, cal


def make_controller(tiny, ep, mode="forecast", q=0.5, **kw):
    packing, sim, cal = tiny
    settings = hp.PackingSettings.from_scenario(packing)
    site_ids = list(cal["models"])
    if mode == "forecast":
        kw.setdefault("forecaster", StubForecaster())
        kw.setdefault("policy", hp.FixedQ(q))
    return hp.PackingController(ep.jobs, cal["models"], site_ids, settings, ep.hour0_local, mode=mode, **kw), settings


def test_levels_and_feature_names():
    assert len(hp.QUANTILE_LEVELS) == hp.N_LEVELS == 21
    assert hp.QUANTILE_LEVELS[hp.MEDIAN_INDEX] == 0.5
    assert hp.level_index(0.9) == 18
    with pytest.raises(ValueError):
        hp.level_index(0.42)
    assert len(hp.FEATURE_NAMES) == hp.N_FEATURES
    assert "log_penalty" in hp.FEATURE_NAMES and "value_per_gpu_hour" in hp.FEATURE_NAMES


def test_scenario_file_loads_and_rejects_bad_schema(tmp_path):
    sc = hp.load_packing_scenario(E003 / "packing-scenario-v1.json")
    assert sc["data_kind"] == "simulated"
    bad = dict(sc, schema="nope")
    p = tmp_path / "bad.json"
    p.write_text(json.JSONEncoder().encode(bad))
    with pytest.raises(ValueError):
        hp.load_packing_scenario(p)


def test_calibration_is_affine_and_caps_sit_between_idle_and_full(tiny):
    _, _, cal = tiny
    for sid, m in cal["models"].items():
        assert m.full_w > m.idle_w > 0
        assert m.idle_w < m.cap_w < m.full_w
        assert m.beta_w_per_gpu == pytest.approx((m.full_w - m.idle_w) / m.n_gpus)
    for row in cal["half_load_check"]:
        assert abs(row["relative_error"]) < 0.01


def test_build_episode_is_seeded_and_runs(tiny):
    packing, sim, cal = tiny
    a = hp.build_episode(packing, sim, cal["models"], 3)
    b = hp.build_episode(packing, sim, cal["models"], 3)
    c = hp.build_episode(packing, sim, cal["models"], 4)
    assert [j.to_dict() for j in a.jobs] == [j.to_dict() for j in b.jobs]
    assert [j.to_dict() for j in a.jobs] != [j.to_dict() for j in c.jobs]
    assert all(j.flexible and j.site_id is None and j.start_s == j.submit_s for j in a.jobs)
    for item in a.scenario["sites"]:
        assert item["site"]["power_cap_w"] == pytest.approx(cal["models"][item["site"]["site_id"]].cap_w)
    assert a.scenario["data_kind"] == "simulated"


def test_slack_decreases_with_level_and_with_extra_jobs(tiny):
    packing, sim, cal = tiny
    ep = hp.build_episode(packing, sim, cal["models"], 1)
    ctrl, st = make_controller(tiny, ep)
    H = st.horizon_bins
    levels = np.asarray(hp.QUANTILE_LEVELS)
    paths = np.broadcast_to((1.0 + 0.1 * (levels - 0.5))[None, None, :], (2, H, 21)).copy()
    bplan = np.zeros((2, H))
    active = np.ones(H)
    s_small = ctrl._slack((0,), (8.0,), active, bplan, paths)
    s_big = ctrl._slack((0,), (64.0,), active, bplan, paths)
    assert np.all(np.diff(s_small) <= 1e-12)
    assert np.all(s_big <= s_small + 1e-12)
    # a job that ends after the first bin only counts in that bin
    short = np.zeros(H)
    short[0] = 1.0
    assert np.all(ctrl._slack((0,), (64.0,), short, bplan, paths) >= s_big - 1e-12)
    # two sites: slack is the minimum over the sites
    both = ctrl._slack((0, 1), (32.0, 32.0), active, bplan, paths)
    one = [ctrl._slack((j,), (32.0,), active, bplan, paths) for j in (0, 1)]
    assert np.allclose(both, np.minimum(one[0], one[1]))


def test_jobs_wait_for_admission_and_higher_q_admits_no_more(tiny):
    packing, sim, cal = tiny
    ep = hp.build_episode(packing, sim, cal["models"], 5)
    out = {}
    for q in (0.5, 0.99):
        ctrl, st = make_controller(tiny, ep, q=q)
        res = hp.run_episode(ep, ctrl)
        starts = {e["job_id"]: e["t_s"] for e in res.events if e["kind"] == "job_start"}
        admitted_at = {a["job_id"]: a["t_s"] for a in ctrl.admissions}
        # no job starts unless the controller admitted it, and never before the admission time
        assert set(starts) <= set(admitted_at)
        assert all(starts[j] >= admitted_at[j] - 1e-9 for j in starts)
        out[q] = (len(ctrl.admissions), hp.episode_metrics(res, ctrl, ep, st))
    # before the warm-up ends both runs use the same rule
    assert out[0.5][1]["data_kind"] == "simulated"
    assert out[0.5][0] >= out[0.99][0]
    assert out[0.5][1]["gpu_hours"] >= out[0.99][1]["gpu_hours"] - 1e-6


def test_warmup_decisions_do_not_depend_on_the_policy(tiny):
    packing, sim, cal = tiny
    ep = hp.build_episode(packing, sim, cal["models"], 6)
    logs = []
    for q in (0.1, 0.9):
        ctrl, st = make_controller(tiny, ep, q=q)
        hp.run_episode(ep, ctrl)
        logs.append([(a["t_s"], a["job_id"]) for a in ctrl.admissions if a["t_s"] < st.warmup_s])
    assert logs[0] == logs[1] and len(logs[0]) > 0


def test_metrics_window_and_ranges(tiny):
    packing, sim, cal = tiny
    ep = hp.build_episode(packing, sim, cal["models"], 7)
    ctrl, st = make_controller(tiny, ep, q=0.9)
    res = hp.run_episode(ep, ctrl)
    m = hp.episode_metrics(res, ctrl, ep, st)
    assert 0.0 <= m["violation_rate"] <= 1.0
    assert m["energy_above_cap_kwh"] >= 0.0 and m["seconds_above_cap"] >= 0.0
    assert m["stranded_kwh"] >= 0.0
    assert m["window_s"] == [st.warmup_s, st.horizon_s]
    assert hp.net_value(m, 0.0) == pytest.approx(m["value_usd"])
    assert hp.net_value(m, 5.0) == pytest.approx(m["value_usd"] - 5.0 * m["energy_above_cap_kwh"])


def test_reactive_controller_throttles_when_over_cap(tiny):
    packing, sim, cal = tiny
    low = copy.deepcopy(packing)
    low["cap"]["load_fraction"] = 0.05
    models = {
        sid: hp.SiteModel(m.site_id, m.n_gpus, m.idle_w, m.full_w, m.idle_w + 0.05 * (m.full_w - m.idle_w), m.utc_offset_h)
        for sid, m in cal["models"].items()
    }
    ep = hp.build_episode(low, sim, models, 8)
    ctrl, st = make_controller(tiny, ep, mode="reactive")
    ctrl.cap = np.array([m.cap_w for m in models.values()])
    res = hp.run_episode(ep, ctrl)
    names = [a["action"] for a in res.actions]
    assert "SetRackPowerCap" in names
    assert "AdmitJob" in names


def test_oracle_follows_the_reference_ratio(tiny):
    packing, sim, cal = tiny
    ep = hp.build_episode(packing, sim, cal["models"], 9)
    ref, st = make_controller(tiny, ep, q=0.9)
    hp.run_episode(ep, ref)
    trace = ref.ratio_bins()
    assert trace.shape[0] == 2 and trace.shape[1] > 0
    ctrl, _ = make_controller(tiny, ep, mode="oracle", oracle_ratio=trace)
    res = hp.run_episode(ep, ctrl)
    m = hp.episode_metrics(res, ctrl, ep, st)
    assert m["forecast_calls"] == 0
    assert len(ctrl.admissions) > 0


def test_ratio_bins_match_the_definition(tiny):
    packing, sim, cal = tiny
    ep = hp.build_episode(packing, sim, cal["models"], 10)
    ctrl, st = make_controller(tiny, ep, q=0.9)
    res = hp.run_episode(ep, ctrl)
    p, b = ctrl.minute_records()
    bins = ctrl.ratio_bins()
    k = int(st.bin_s / st.call_s)
    i = 3
    expect = p[i * k:(i + 1) * k, 0].sum() / (ctrl.idle[0] + ctrl.beta[0] * b[i * k:(i + 1) * k, 0]).sum()
    assert bins[0, i] == pytest.approx(expect)
    # the recorded call-interval means equal the simulator's control-step samples averaged over the interval
    m0 = res.site_power_w[: int(st.call_s / res.dt), 0].mean()
    assert p[0, 0] == pytest.approx(m0)


def test_hindsight_costs_hand_example():
    models = [hp.SiteModel("s", 10, 1000.0, 2000.0, 1500.0, 0.0)]  # beta = 100 W per GPU
    M = 70
    p_min = np.full((M, 1), 1450.0)
    b_min = np.full((M, 1), 5.0)  # idle + beta*b = 1500, s_real = 1450/1500
    t = np.array([0.0])
    # a candidate of 10 GPUs that was NOT admitted: admitting adds 10 * 100 * (1450/1500) = 966.67 W
    sit = {
        "t": t, "sites": np.array([[0]]), "shares": np.array([[10.0]]), "x": np.zeros((1, hp.N_FEATURES)),
        "slack": np.array([np.linspace(0.1, -0.1, hp.N_LEVELS)]), "k": np.array([0]), "admit": np.array([False]),
        "value": np.array([2.0]), "n_gpus": np.array([10.0]), "life_s": np.array([7200.0]),
    }
    costs, value = hp.hindsight_costs(sit, p_min, b_min, models, [0.0, 10.0], 60.0, 3600.0)
    assert value[0] == pytest.approx(10 * 2.0 * 1.0)
    fits = sit["slack"][0] >= 0
    # no penalty: admitting is best, so refusing levels cost the value
    assert np.allclose(costs[0][0][fits], 0.0)
    assert np.allclose(costs[0][0][~fits], 20.0)
    # excess energy if admitted: (1450 + 966.67 - 1500) W for one hour = 0.91667 kWh; penalty 10 => 9.1667 USD
    excess_kwh = (1450.0 + 100 * 10 * 1450.0 / 1500.0 - 1500.0) / 1000.0
    assert costs[1][0][fits][0] == pytest.approx(0.0 + 0.0)  # admit reward 20 - 9.17 > refuse reward 0
    assert costs[1][0][~fits][0] == pytest.approx(20.0 - 10.0 * excess_kwh)
    # a very large penalty flips the best action to refusing
    c3, _ = hp.hindsight_costs(sit, p_min, b_min, models, [100.0], 60.0, 3600.0)
    assert np.allclose(c3[0][0][~fits], 0.0)
    assert np.allclose(c3[0][0][fits], 100.0 * excess_kwh - 20.0)


def test_cost_sensitive_model_learns_a_threshold_rule():
    rng = np.random.default_rng(0)
    n = 3000
    X = rng.normal(size=(n, hp.N_FEATURES))
    best = (X[:, 0] > 0).astype(int) * 10 + 5  # level 15 when the first feature is positive, else level 5
    costs = np.abs(np.arange(hp.N_LEVELS)[None, :] - best[:, None]).astype(float)
    value = np.ones(n)
    model = hp.CostSensitiveModel(n_rff=128, bandwidth=1.0, ridge=1.0).fit(X[:2000], costs[:2000], value[:2000])
    pick = np.argmin(model.predict_costs(X[2000:]), axis=1)
    assert np.mean(np.abs(pick - best[2000:]) <= 2) > 0.9
    again = hp.CostSensitiveModel.from_dict(model.to_dict())
    assert np.allclose(again.predict_costs(X[2000:2010]), model.predict_costs(X[2000:2010]))
    assert model.regret(X[2000:], costs[2000:], value[2000:]) < 1.0


def test_bootstrap_ci():
    v = [1.0, 2.0, 3.0, 4.0]
    a = hp.bootstrap_ci(v, n_boot=500, seed=1)
    b = hp.bootstrap_ci(v, n_boot=500, seed=1)
    assert a == b
    assert a["mean"] == pytest.approx(2.5) and a["lo"] <= 2.5 <= a["hi"] and a["n"] == 4
    one = hp.bootstrap_ci([3.0], n_boot=50)
    assert one["lo"] == one["hi"] == 3.0
    with pytest.raises(ValueError):
        hp.bootstrap_ci([])
