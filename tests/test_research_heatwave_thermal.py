"""Tests for the Heatwave RC thermal, throttle, and cooling power models."""

from __future__ import annotations

import math

import numpy as np
import pytest

from gpu_stack.research.heatwave_thermal import (
    CoolingPowerModel,
    GPUThrottleModel,
    RCThermalParams,
    fit,
    rc_step,
    simulate,
    simulate_full,
    supply_setpoint,
)


def make_params(**over: float) -> RCThermalParams:
    values = dict(
        heat_capacity_j_per_k=2.0e5,
        resistance_k_per_w=1.5e-3,
        cooling_lag_s=120.0,
        cooling_capacity_w=math.inf,
        supply_setpoint_c=22.0,
        outdoor_coupling_k_per_k=0.3,
        outdoor_reference_c=25.0,
    )
    values.update(over)
    return RCThermalParams(**values)


def test_params_validation():
    with pytest.raises(ValueError):
        make_params(heat_capacity_j_per_k=0.0)
    with pytest.raises(ValueError):
        make_params(resistance_k_per_w=-1.0)
    with pytest.raises(ValueError):
        make_params(cooling_lag_s=-1.0)
    with pytest.raises(ValueError):
        make_params(cooling_capacity_w=-5.0)
    p = make_params()
    assert p.time_constant_s == pytest.approx(300.0)
    assert p.to_dict()["cooling_capacity_w"] is None


def test_steady_state_matches_formula():
    p = make_params(outdoor_coupling_k_per_k=0.0, cooling_lag_s=0.0)
    n = 4000
    temps = simulate(p, np.full(n, 10_000.0), np.full(n, 20.0), 10.0, T0=22.0)
    assert temps[-1] == pytest.approx(22.0 + 1.5e-3 * 10_000.0, abs=1e-6)


def test_exact_in_dt_for_piecewise_constant_inputs():
    p = make_params()
    rng = np.random.default_rng(3)
    coarse_p = rng.uniform(5_000, 15_000, size=40)
    coarse_a = rng.uniform(15, 40, size=40)
    dt = 60.0
    coarse = simulate(p, coarse_p, coarse_a, dt, T0=30.0)
    sub = 120
    fine = simulate(p, np.repeat(coarse_p, sub), np.repeat(coarse_a, sub), dt / sub, T0=30.0)
    # Same state at the coarse sample times, up to rounding.
    assert np.allclose(coarse, fine[::sub], atol=1e-6)


def test_lag_equals_time_constant_branch_is_continuous():
    p_eq = make_params(cooling_lag_s=300.0)
    p_near = make_params(cooling_lag_s=300.0 * (1 + 1e-6))
    pw = np.full(200, 9_000.0)
    am = np.linspace(20, 40, 200)
    a = simulate(p_eq, pw, am, 30.0, 28.0)
    b = simulate(p_near, pw, am, 30.0, 28.0)
    assert np.allclose(a, b, atol=1e-3)


def test_scalar_and_vector_steps_agree():
    p = make_params(cooling_capacity_w=8_000.0)
    pw = np.concatenate([np.full(50, 6_000.0), np.full(100, 14_000.0), np.full(100, 3_000.0)])
    am = np.full(pw.size, 30.0)
    scalar = simulate_full(p, pw, am, 20.0, T0=30.0)
    T = np.array(30.0)
    Ts = np.array(float(supply_setpoint(p, 30.0)))
    out = []
    for i in range(pw.size):
        out.append(float(T))
        T, Ts, _ = rc_step(
            p.heat_capacity_j_per_k, p.resistance_k_per_w, p.cooling_lag_s,
            p.cooling_capacity_w, supply_setpoint(p, am[i]), T, Ts, pw[i], 20.0,
        )
    assert np.allclose(out, scalar["temp_c"], atol=1e-9)


def test_capacity_limit_and_energy_balance():
    cap = 8_000.0
    p = make_params(cooling_capacity_w=cap, outdoor_coupling_k_per_k=0.0)
    pw = np.full(600, 14_000.0)
    am = np.full(600, 25.0)
    out = simulate_full(p, pw, am, 10.0, T0=30.0)
    assert np.all(out["heat_removed_w"] <= cap + 1e-6)
    # Heat above capacity warms the node at (P - cap) / C once saturated.
    late = out["temp_c"][-200:]
    slope = (late[-1] - late[0]) / (199 * 10.0)
    assert slope == pytest.approx((14_000.0 - cap) / p.heat_capacity_j_per_k, rel=1e-6)
    # Energy balance: sum of heat removed + stored equals energy in.
    stored = p.heat_capacity_j_per_k * (out["temp_c"][-1] - out["temp_c"][0])
    total_in = float(np.sum(pw)) * 10.0
    # temps has the state at the start of each step, so add the last step.
    last_step_removed = out["heat_removed_w"][-1] * 10.0
    last_step_dt = 10.0 * (pw[-1] - out["heat_removed_w"][-1]) / p.heat_capacity_j_per_k
    stored_total = stored + p.heat_capacity_j_per_k * last_step_dt
    removed_total = float(np.sum(out["heat_removed_w"])) * 10.0
    assert removed_total + stored_total == pytest.approx(total_in, rel=1e-9)
    assert last_step_removed > 0


def test_capacity_series_override_cooling_failure_raises_temperature():
    p = make_params(outdoor_coupling_k_per_k=0.0)
    n = 720
    pw = np.full(n, 10_000.0)
    am = np.full(n, 25.0)
    cap = np.full(n, 20_000.0)
    cap[300:] = 2_000.0
    base = simulate(p, pw, am, 10.0, T0=22.0 + 15.0)
    failed = simulate(p, pw, am, 10.0, T0=22.0 + 15.0, capacity_w=cap)
    assert failed[-1] > base[-1] + 10.0
    assert np.allclose(failed[:300], base[:300])


def test_saturation_crossing_is_close_to_fine_integration():
    p = make_params(cooling_capacity_w=9_000.0, outdoor_coupling_k_per_k=0.0)
    n = 90
    pw = np.concatenate([np.full(30, 6_000.0), np.full(60, 12_000.0)])
    am = np.full(n, 25.0)
    coarse = simulate(p, pw, am, 60.0, T0=22.0 + 9.0)
    sub = 60
    fine = simulate(p, np.repeat(pw, sub), np.repeat(am, sub), 1.0, T0=22.0 + 9.0)
    assert np.max(np.abs(coarse - fine[::sub])) < 0.05


def test_fit_recovers_known_parameters():
    truth = make_params(cooling_lag_s=90.0)
    rng = np.random.default_rng(11)
    n = 3000
    dt = 20.0
    # Piecewise-constant power with random levels and a diurnal-like outdoor swing.
    pw = np.repeat(rng.uniform(4_000, 16_000, size=n // 30), 30)
    am = 28.0 + 8.0 * np.sin(2 * np.pi * np.arange(n) * dt / 86_400.0 * 6) + 4.0 * np.sin(
        2 * np.pi * np.arange(n) * dt / 5_000.0
    )
    temps = simulate(truth, pw, am, dt, T0=35.0)
    temps_noisy = temps + rng.normal(0.0, 0.02, size=n)
    fitted, report = fit(
        pw, am, temps_noisy, dt,
        free=("heat_capacity_j_per_k", "resistance_k_per_w", "cooling_lag_s", "supply_setpoint_c", "outdoor_coupling_k_per_k"),
        fixed={"outdoor_reference_c": truth.outdoor_reference_c},
    )
    assert fitted.heat_capacity_j_per_k == pytest.approx(truth.heat_capacity_j_per_k, rel=0.05)
    assert fitted.resistance_k_per_w == pytest.approx(truth.resistance_k_per_w, rel=0.05)
    assert fitted.time_constant_s == pytest.approx(truth.time_constant_s, rel=0.05)
    assert fitted.cooling_lag_s == pytest.approx(truth.cooling_lag_s, rel=0.05)
    assert fitted.supply_setpoint_c == pytest.approx(truth.supply_setpoint_c, abs=0.5)
    assert report["rmse_c"] < 0.1
    assert report["r2"] > 0.99
    assert report["time_constant_s"] == pytest.approx(fitted.time_constant_s)


def test_fit_recovers_rc_without_lag():
    truth = make_params(cooling_lag_s=0.0, outdoor_coupling_k_per_k=0.0)
    rng = np.random.default_rng(5)
    n = 1500
    pw = np.repeat(rng.uniform(3_000, 18_000, size=n // 25), 25)
    am = np.full(n, 20.0)
    temps = simulate(truth, pw, am, 15.0, T0=25.0)
    fitted, report = fit(pw, am, temps, 15.0)
    assert fitted.heat_capacity_j_per_k == pytest.approx(truth.heat_capacity_j_per_k, rel=0.05)
    assert fitted.resistance_k_per_w == pytest.approx(truth.resistance_k_per_w, rel=0.05)
    assert report["success"]


def test_fit_rejects_bad_inputs():
    with pytest.raises(ValueError):
        fit(np.ones(4), np.ones(4), np.ones(4), 1.0)
    with pytest.raises(ValueError):
        fit(np.ones(20), np.ones(20), np.ones(20), 1.0, free=("supply_setpoint_c",))


def throttle() -> GPUThrottleModel:
    return GPUThrottleModel(
        throttle_threshold_c=80.0, throttle_span_c=10.0, min_clock_fraction=0.5, power_exponent=2.0
    )


def test_throttle_model_has_no_defaults():
    with pytest.raises(TypeError):
        GPUThrottleModel()  # type: ignore[call-arg]


def test_throttle_reduces_clock_and_power_monotonically():
    m = throttle()
    temps = np.array([60.0, 80.0, 85.0, 90.0, 120.0])
    clk = m.clock_fraction(temps)
    assert clk[0] == 1.0 and clk[1] == 1.0
    assert np.all(np.diff(clk) <= 0)
    assert clk[-1] == pytest.approx(0.5)
    pw = m.power_w(560.0, 100.0, clk)
    assert np.all(np.diff(pw) <= 1e-12)
    assert pw[-1] < pw[0]
    # Idle power does not scale.
    assert m.power_w(100.0, 100.0, 0.5) == pytest.approx(100.0)


def test_clock_for_power_inverts_power_w():
    m = throttle()
    clk = m.clock_for_power(300.0, 560.0, 100.0)
    assert float(m.power_w(560.0, 100.0, clk)) == pytest.approx(300.0)
    assert float(m.clock_for_power(1_000.0, 560.0, 100.0)) == 1.0
    assert float(m.clock_for_power(50.0, 560.0, 100.0)) == pytest.approx(0.5)


def test_cooling_power_pue_mode():
    m = CoolingPowerModel(kind="pue", pue=1.2)
    assert float(m.power_w(10_000.0, 30.0, 24.0)) == pytest.approx(2_000.0)


def test_carnot_calibration_reproduces_pue_and_rises_with_outdoor_temperature():
    m = CoolingPowerModel.carnot_from_pue(
        pue=1.2, reference_outdoor_c=20.0, reference_supply_c=24.0,
        evaporator_approach_k=10.0, condenser_approach_k=10.0, cop_min=1.5, cop_max=40.0,
    )
    assert float(m.power_w(10_000.0, 20.0, 24.0)) == pytest.approx(2_000.0)
    cool = float(m.power_w(10_000.0, 10.0, 24.0))
    hot = float(m.power_w(10_000.0, 40.0, 24.0))
    assert cool < 2_000.0 < hot
    assert m.to_dict()["kind"] == "carnot"
    with pytest.raises(ValueError):
        CoolingPowerModel.carnot_from_pue(
            pue=1.2, reference_outdoor_c=20.0, reference_supply_c=24.0,
            evaporator_approach_k=10.0, condenser_approach_k=10.0, cop_min=6.0, cop_max=40.0,
        )
