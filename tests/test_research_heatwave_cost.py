"""Tests for the Heatwave cost-timing module (dollars per token against carbon per token).

The scheduler tests use small synthetic price and carbon series (labelled synthetic here, used only
to check the code); the result-file test reads the committed result when it exists.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from scipy.optimize import linprog

from gpu_stack.research import heatwave_cost as hc

HERE = Path(__file__).resolve().parent
RESULT = HERE.parent / "experiments" / "e003-heatwave" / "results" / "cost-v1.json"
SCENARIO = HERE.parent / "experiments" / "e003-heatwave" / "cost-scenario-v1.json"


def synthetic_series(n_hours: int, seed: int = 0):
    """Synthetic daily cycle plus noise; price and carbon are correlated through a shared term."""
    rng = np.random.default_rng(seed)
    t = np.arange(n_hours)
    shared = np.sin(2 * np.pi * t / 24.0)
    price = 40.0 + 15.0 * shared + 6.0 * rng.normal(size=n_hours)
    carbon = 200.0 + 60.0 * shared + 25.0 * np.sin(2 * np.pi * t / 24.0 + 1.0) + 15.0 * rng.normal(size=n_hours)
    return price, carbon


NORM = {"price_mean": 40.0, "price_std": 15.0, "carbon_mean": 200.0, "carbon_std": 60.0}


# ---------------------------------------------------------------------------------------------
# Model and planning problem
# ---------------------------------------------------------------------------------------------


def test_quantile_grid_matches_heatwave():
    forecast = pytest.importorskip("heatwave.forecast")
    assert tuple(forecast.QUANTILE_LEVELS) == hc.QUANTILE_LEVELS


def test_flex_model_validation_and_rates():
    m = hc.FlexModel(0.7, 0.3, 24)
    assert m.flexible_rate == pytest.approx(0.21)
    assert m.inflexible_load == pytest.approx(0.49)
    assert m.flexible_cap == pytest.approx(0.51)
    with pytest.raises(ValueError):
        hc.FlexModel(1.2, 0.3, 24, power_cap=1.0)
    with pytest.raises(ValueError):
        hc.FlexModel(0.7, 1.5, 24)
    with pytest.raises(ValueError):
        hc.FlexModel(0.7, 0.3, 0)


def test_arrived_and_due_window_one_means_immediate():
    m = hc.FlexModel(0.7, 0.3, 1)
    t = np.arange(10)
    assert np.allclose(m.arrived(t), m.due(t))


def _transport_optimum(cost, model, t0, run_before, terminal):
    """Same problem as a transportation LP over (arrival hour, run hour) pairs, to check the cumulative form.

    Work that arrived before ``t0`` and has not run yet is split into arrival cohorts oldest first
    (first-in first-out is earliest-deadline first for one window length).
    """
    h = len(cost)
    a = model.flexible_rate
    arrivals = np.arange(0, t0 + h)
    # cohort remaining mass: cohorts before t0 are served oldest first up to run_before
    mass = np.full(arrivals.size, a)
    left = run_before
    for i in range(t0):
        take = min(mass[i], left)
        mass[i] -= take
        left -= take
    cohorts = [(i, mass[i]) for i in range(arrivals.size) if mass[i] > 1e-12 or i >= t0]
    n_c = len(cohorts)
    var = n_c * (h + 1)  # last column = carried past the horizon
    c = np.zeros(var)
    bounds = []
    for ci, (i, m) in enumerate(cohorts):
        for k in range(h + 1):
            idx = ci * (h + 1) + k
            if k < h:
                c[idx] = cost[k] - terminal
                ok = (t0 + k >= i) and (t0 + k <= i + model.window_hours - 1)
            else:
                ok = i + model.window_hours - 1 >= t0 + h  # deadline beyond the horizon
            bounds.append((0.0, None) if ok else (0.0, 0.0))
    a_eq = np.zeros((n_c, var))
    b_eq = np.zeros(n_c)
    for ci, (i, m) in enumerate(cohorts):
        a_eq[ci, ci * (h + 1):(ci + 1) * (h + 1)] = 1.0
        b_eq[ci] = m
    # arrivals after t0 are known inside the horizon, but a cohort arriving at hour i >= t0 is only available from hour i
    a_ub = np.zeros((h, var))
    for k in range(h):
        for ci in range(n_c):
            a_ub[k, ci * (h + 1) + k] = 1.0
    res = linprog(c, A_ub=a_ub, b_ub=np.full(h, model.flexible_cap), A_eq=a_eq, b_eq=b_eq, bounds=bounds, method="highs")
    assert res.status == 0
    return res.fun


@pytest.mark.parametrize("window", [3, 6])
def test_cumulative_form_matches_transportation_form(window):
    # Only cohorts whose deadline lies inside the horizon are forced; others may be carried (cost = terminal value).
    rng = np.random.default_rng(1)
    m = hc.FlexModel(0.6, 0.5, window)
    h, t0 = 12, 20
    for _ in range(5):
        cost = rng.normal(size=h)
        run_before = float(m.due(t0 - 1)) + rng.uniform(0.0, 0.2)
        y, fell_back = hc.plan_flexible(cost, m, t0, run_before)
        assert not fell_back
        terminal = float(cost.mean())
        obj = float(np.dot(cost - terminal, y))
        # the transportation form drops cohorts' carried mass cost (terminal - terminal = 0), so objectives are comparable
        assert obj == pytest.approx(_transport_optimum(cost, m, t0, run_before, terminal), abs=1e-7)


def test_plan_respects_bounds():
    m = hc.FlexModel(0.7, 0.3, 24)
    rng = np.random.default_rng(2)
    t0, run_before = 48, float(m.due(47)) + 0.3
    y, fb = hc.plan_flexible(rng.normal(size=48), m, t0, run_before)
    assert not fb
    t = np.arange(t0, t0 + 48)
    cum = run_before + np.cumsum(y)
    assert np.all(y >= -1e-9) and np.all(y <= m.flexible_cap + 1e-9)
    assert np.all(cum >= m.due(t) - 1e-7)
    assert np.all(cum <= m.arrived(t) + 1e-7)


def test_rolling_schedule_meets_deadlines_and_conserves_work():
    n_days = 12
    price, carbon = synthetic_series(n_days * 24 + 48, seed=3)
    for window in (24, 72):
        m = hc.FlexModel(0.7, 0.5, window)
        cost_by_day = np.stack([hc.mixed_cost(price[24 * d:24 * d + 48], carbon[24 * d:24 * d + 48], 0.5, NORM) for d in range(n_days)])
        y, diag = hc.schedule_forecast(cost_by_day, m, [(0, n_days)])
        assert diag["plan_fallbacks"] == 0
        t = np.arange(y.size)
        cum = np.cumsum(y)
        assert np.all(cum >= m.due(t) - 1e-6), "work finished after its deadline"
        assert np.all(cum <= m.arrived(t) + 1e-6), "work run before it arrived"
        backlog = m.arrived(t[-1]) - cum[-1]
        assert 0.0 <= backlog <= m.flexible_rate * window + 1e-6
        assert np.all(y <= m.flexible_cap + 1e-9)


def test_window_one_and_zero_flexible_fraction_equal_no_shift():
    n_days = 5
    price, carbon = synthetic_series(n_days * 24 + 48, seed=4)
    for m in (hc.FlexModel(0.7, 0.4, 1), hc.FlexModel(0.7, 0.0, 24)):
        cost_by_day = np.stack([hc.mixed_cost(price[24 * d:24 * d + 48], carbon[24 * d:24 * d + 48], 0.3, NORM) for d in range(n_days)])
        y, _ = hc.schedule_forecast(cost_by_day, m, [(0, n_days)])
        assert np.allclose(y, hc.schedule_none(m, n_days * 24), atol=1e-7)


def test_perfect_foresight_lowers_cost_and_carbon_at_the_ends_of_lambda():
    n_days = 20
    n = n_days * 24
    price, carbon = synthetic_series(n + 48, seed=5)
    m = hc.FlexModel(0.7, 0.5, 24)
    pf_p = hc.padded_future(price, [24 * d for d in range(n_days)], 48)
    pf_c = hc.padded_future(carbon, [24 * d for d in range(n_days)], 48)
    sums, flex, fb = hc.sweep_forecast_policy(pf_p, pf_c, [0.0, 1.0], m, NORM, [(0, n_days)], price[:n], carbon[:n])
    none_s, _ = hc.sweep_none(m, 2, price[:n], carbon[:n])
    p0, c0 = hc.effective_prices(none_s[0])
    p_cost, c_cost = hc.effective_prices(sums[1])  # lam = 1: price only
    p_carb, c_carb = hc.effective_prices(sums[0])  # lam = 0: carbon only
    assert fb == 0
    assert p_cost < p0 and c_carb < c0
    assert p_cost <= p_carb + 1e-9  # planning on price gives the lower price
    assert c_carb <= c_cost + 1e-9  # planning on carbon gives the lower carbon


def test_risk_quantile_changes_plan_when_spread_differs_by_hour():
    # Two hours with equal medians; the second has a wide upper tail.  A median planner is indifferent, a q=0.9 planner avoids it.
    m = hc.FlexModel(0.5, 1.0, 4)
    cost_mid = np.array([1.0, 1.0, 5.0, 5.0])
    cost_high = np.array([1.0, 3.0, 5.0, 5.0])
    y_mid, _ = hc.plan_flexible(cost_mid, m, 0, 0.0)
    y_high, _ = hc.plan_flexible(cost_high, m, 0, 0.0)
    assert y_high[0] >= y_mid[0] - 1e-9
    assert y_high[1] <= y_mid[1] + 1e-9


def test_reactive_obeys_deadline_and_cap_and_constant_cost_runs_on_arrival():
    n_days = 10
    price, carbon = synthetic_series(n_days * 24 + 200, seed=6)
    m = hc.FlexModel(0.7, 0.5, 24)
    cost = hc.mixed_cost(price, carbon, 0.5, NORM)
    y = hc.schedule_reactive(cost, m, [(200, n_days)], lookback=168)
    t = np.arange(y.size)
    cum = np.cumsum(y)
    assert np.all(cum >= m.due(t) - 1e-9) and np.all(cum <= m.arrived(t) + 1e-9)
    assert np.all(y <= m.flexible_cap + 1e-9)
    flat = np.zeros(n_days * 24 + 200)
    y_flat = hc.schedule_reactive(flat, m, [(200, n_days)], lookback=168)
    assert np.allclose(y_flat, hc.schedule_none(m, n_days * 24))


def test_trailing_median_matches_numpy():
    x = np.array([5.0, 1.0, 3.0, 2.0, 9.0, 4.0])
    out = hc.trailing_median(x, 3)
    assert np.isnan(out[:2]).all()
    assert out[2:] == pytest.approx([3.0, 2.0, 3.0, 4.0])


# ---------------------------------------------------------------------------------------------
# Accounting
# ---------------------------------------------------------------------------------------------


def test_no_shift_effective_values_are_plain_means():
    n = 10 * 24
    price, carbon = synthetic_series(n, seed=7)
    m = hc.FlexModel(0.7, 0.3, 24)
    s = hc.daily_sums(hc.schedule_none(m, n), m, price, carbon)
    p, c = hc.effective_prices(s)
    assert p == pytest.approx(price.mean()) and c == pytest.approx(carbon.mean())


def test_shift_identity_matches_the_power_forecast_scope():
    # price paid = (1 - phi) * unshifted price + phi * shifted price, with phi the flexible energy share
    n_days = 15
    n = n_days * 24
    price, carbon = synthetic_series(n + 48, seed=8)
    m = hc.FlexModel(0.7, 0.4, 24)
    pf_p = hc.padded_future(price, [24 * d for d in range(n_days)], 48)
    pf_c = hc.padded_future(carbon, [24 * d for d in range(n_days)], 48)
    sums, flex, _ = hc.sweep_forecast_policy(pf_p, pf_c, [0.5], m, NORM, [(0, n_days)], price[:n], carbon[:n])
    p, c = hc.effective_prices(sums[0])
    fl = flex[0].sum(axis=0)
    phi = fl[0] / sums[0][:, 0].sum()
    p_sh, c_sh = fl[1] / fl[0], fl[2] / fl[0]
    assert p == pytest.approx((1 - phi) * price[:n].mean() + phi * p_sh)
    assert c == pytest.approx((1 - phi) * carbon[:n].mean() + phi * c_sh)


def test_bootstrap_indices_shape_range_and_blocks():
    idx = hc.block_bootstrap_indices(50, 200, 7, seed=0)
    assert idx.shape == (200, 50) and idx.min() >= 0 and idx.max() < 50
    # inside a block the days are consecutive (circular)
    assert np.all((idx[:, 1:7] - idx[:, :6]) % 50 == 1)
    iid = hc.block_bootstrap_indices(50, 100, 1, seed=0)
    assert iid.shape == (100, 50)
    assert np.array_equal(idx, hc.block_bootstrap_indices(50, 200, 7, seed=0))


def test_effective_prices_under_bootstrap_has_boot_shape():
    sums = np.abs(np.random.default_rng(0).normal(size=(30, 3))) + 1.0
    idx = hc.block_bootstrap_indices(30, 40, 3, seed=1)
    p, c = hc.effective_prices(sums, idx)
    assert p.shape == (40,) and c.shape == (40,)
    lo, hi = hc.percentile_interval(p)
    assert lo <= np.median(p) <= hi


def test_fill_hourly_uses_same_hour_of_neighbouring_days():
    x = np.tile(np.arange(24, dtype=float), 6)
    y = x.copy()
    y[50] = np.nan
    filled, n = hc.fill_hourly(y)
    assert n == 1 and filled[50] == pytest.approx(x[50])


def test_padded_future_copies_previous_day_past_the_end():
    v = np.arange(48, dtype=float)
    out = hc.padded_future(v, [40], 16)
    assert out[0, 0] == 40 and out[0, 7] == 47
    assert out[0, 8] == 24 + 0  # hour 48 -> hour 24
    assert out[0, 15] == 31


def test_quantile_index_requires_grid_level():
    assert hc.quantile_index(0.5) == 10
    with pytest.raises(ValueError):
        hc.quantile_index(0.123)


# ---------------------------------------------------------------------------------------------
# Calculator terms and the feedback path
# ---------------------------------------------------------------------------------------------

REF = {"params": 7e9, "tokens": 2e12, "gpu": "H100-SXM", "n_gpus": 1024, "overrides": {}}


def test_reference_terms_agree_with_calculator():
    from gpu_stack.calculator import estimate

    terms = hc.reference_terms(REF)
    est = estimate(7e9, 2e12, gpu="H100-SXM", n_gpus=1024)
    assert terms["energy_mwh_per_mtoken"] * est.tokens / 1e6 == pytest.approx(est.energy_mwh)
    assert terms["facility_power_mw"] * est.training_days * 24 == pytest.approx(est.energy_mwh)
    assert terms["tokens_per_gpu_hour"] * est.gpu_hours == pytest.approx(est.tokens)
    default_elec = terms["energy_mwh_per_mtoken"] * 1000 * terms["calculator_default_electricity_price_usd_per_kwh"] * est.tokens / 1e6
    assert default_elec == pytest.approx(est.electricity_cost)
    assert terms["hardware_usd_per_mtoken"] * est.tokens / 1e6 == pytest.approx(est.hardware_cost)


def test_per_mtoken_units():
    terms = hc.reference_terms(REF)
    r = hc.per_mtoken(50.0, 200.0, terms)  # 50 USD/MWh, 200 g/kWh
    assert r["electricity_usd_per_mtoken"] == pytest.approx(terms["energy_mwh_per_mtoken"] * 50.0)
    assert r["co2_g_per_mtoken"] == pytest.approx(terms["energy_mwh_per_mtoken"] * 1000.0 * 200.0)
    assert r["total_usd_per_mtoken"] == pytest.approx(r["electricity_usd_per_mtoken"] + terms["hardware_usd_per_mtoken"])


def _toy_curve():
    return {
        "flexible_fraction": 0.3, "window_hours": 24, "utilization": 0.7, "lambda": [0.0, 1.0],
        "price_paid": [36.0, 30.0], "carbon_paid": [100.0, 110.0], "price_shifted": [20.0, 10.0],
        "carbon_shifted": [60.0, 90.0], "flexible_energy_share": [0.3, 0.3],
        "price_unshifted": 40.0, "carbon_unshifted": 120.0,
        "electricity_usd_per_mtoken": [0.0, 0.0], "total_usd_per_mtoken": [0.0, 0.0], "co2_g_per_mtoken": [0.0, 0.0],
    }


def test_timing_inputs_units_and_interpolation():
    ti = hc.timing_inputs(_toy_curve(), 0.5)
    assert ti["electricity_price"] == pytest.approx(33.0 / 1000.0)
    assert ti["carbon_intensity_paid"] == pytest.approx(105.0 / 1000.0)
    assert ti["price_shifted"] == pytest.approx(15.0 / 1000.0)
    ti_eur = hc.timing_inputs(_toy_curve(), 0.0, usd_per_price_unit=1.1)
    assert ti_eur["electricity_price"] == pytest.approx(36.0 / 1000.0 * 1.1)


def test_estimate_with_timing_changes_only_electricity():
    from gpu_stack.calculator import estimate

    base = estimate(7e9, 2e12, gpu="H100-SXM", n_gpus=1024, electricity_price=0.040)
    est, carbon_kg, ti = hc.estimate_with_timing(REF, _toy_curve(), 0.0)
    assert est.energy_mwh == pytest.approx(base.energy_mwh)
    assert est.hardware_cost == pytest.approx(base.hardware_cost)
    assert est.electricity_cost == pytest.approx(est.energy_mwh * 1000.0 * ti["electricity_price"])
    assert carbon_kg == pytest.approx(est.energy_mwh * 1000.0 * ti["carbon_intensity_paid"])


def test_lookup_curve_keys():
    doc = {"result": {"scenario": {"workload": {"utilization": 0.7}}, "pairs": {"x": {"curves": {
        hc.curve_key("timestral_28M", 0.3, 24, 0.7, 0.5): {"tag": "a"},
        hc.curve_key("no_shift", 0.3, 24, 0.7, None): {"tag": "b"}}}}}}
    assert hc.lookup_curve(doc, "x", "timestral_28M", 0.3, 24)["tag"] == "a"
    assert hc.lookup_curve(doc, "x", "no_shift", 0.3, 24)["tag"] == "b"


# ---------------------------------------------------------------------------------------------
# Forecast use is causal
# ---------------------------------------------------------------------------------------------


def test_rolling_forecast_only_reads_history():
    forecast = pytest.importorskip("heatwave.forecast")
    values = synthetic_series(24 * 40)[0]
    fc = forecast.SeasonalNaiveForecaster(24, max_context=168)
    t0 = [24 * 20, 24 * 21]
    a = hc.rolling_forecast(values, t0, fc, 168, 48, batch=2)
    changed = values.copy()
    changed[24 * 20:] += 1000.0  # change everything at and after the first decision time
    b = hc.rolling_forecast(changed, t0[:1], fc, 168, 48, batch=1)
    assert a.shape == (2, 48, 21)
    assert np.allclose(a[0], b[0])


# ---------------------------------------------------------------------------------------------
# The committed result
# ---------------------------------------------------------------------------------------------


@pytest.mark.skipif(not RESULT.exists(), reason="result file not written yet")
def test_committed_result_has_provenance_and_consistent_curves():
    doc = json.loads(RESULT.read_text())
    prov = doc["provenance"]
    assert prov["data_kind"] == "public"
    assert len(prov["script_sha256"]) == 64 and prov["git"]["commit"] != "unknown"
    assert any("public_caiso_np15_lmp_dam" in k for k in prov["inputs"])
    res = doc["result"]
    assert res["gpu_stack_git"]["commit"]
    scenario = json.loads(SCENARIO.read_text())
    assert res["scenario"]["scenario_id"] == scenario["scenario_id"]
    for pair, block in res["pairs"].items():
        assert block["same_region"] is True and block["plan_fallbacks_total"] == 0
        for key, curve in block["curves"].items():
            n = len(curve["lambda"])
            for field in ("price_paid", "carbon_paid", "electricity_usd_per_mtoken", "total_usd_per_mtoken", "co2_g_per_mtoken"):
                assert len(curve[field]) == n and len(curve[field + "_ci"]) == n
            # total cost = electricity + the calculator's hardware cost, the same for every policy
            hw = res["reference_run_terms"]["hardware_usd_per_mtoken"]
            tot = np.array(curve["total_usd_per_mtoken"]) - np.array(curve["electricity_usd_per_mtoken"])
            assert np.allclose(tot, hw)
        none = block["curves"][hc.curve_key("no_shift", 0.3, 24, 0.7, None)]
        assert np.allclose(none["saving_pct_electricity"], 0.0)
        assert np.allclose(none["price_paid"], block["mean_price_test"])


def test_offline_optimum_is_feasible_and_no_worse_than_rolling_perfect_foresight():
    n_days = 10
    n = n_days * 24
    price, carbon = synthetic_series(n + 48, seed=9)
    m = hc.FlexModel(0.7, 0.5, 24)
    cost = hc.mixed_cost(price[:n], carbon[:n], 0.5, NORM)
    y_off = hc.offline_optimum(cost, m)
    t = np.arange(n)
    cum = np.cumsum(y_off)
    assert np.all(cum >= m.due(t) - 1e-6) and np.all(cum <= m.arrived(t) + 1e-6)
    assert np.all(y_off <= m.flexible_cap + 1e-9) and np.all(y_off >= -1e-9)
    pf = hc.padded_future(price, [24 * d for d in range(n_days)], 48)
    pc = hc.padded_future(carbon, [24 * d for d in range(n_days)], 48)
    cost_rows = np.stack([hc.mixed_cost(pf[d], pc[d], 0.5, NORM) for d in range(n_days)])
    y_roll, _ = hc.schedule_forecast(cost_rows, m, [(0, n_days)])
    ref = cost.mean()
    obj_off = float(np.dot(cost - ref, y_off))
    obj_roll = float(np.dot(cost - ref, y_roll))
    assert obj_off <= obj_roll + 1e-7


def test_covariate_windows_pad_past_the_end_with_nan():
    known = np.arange(2 * 100, dtype=float).reshape(2, 100)
    w = hc.covariate_windows(known, [90], 20, 24)
    assert w.shape == (1, 2, 44)
    assert w[0, 0, 0] == known[0, 70] and w[0, 0, 29] == known[0, 99]
    assert np.isnan(w[0, :, 30:]).all()
