"""Tests for the forecast-aware power, thermal, and cost scope.

The scope puts the equations behind forecast-driven operation into the map:
planning site power at a forecast quantile, stranded power, a lumped RC
thermal model, the value of an early checkpoint, and time-shifted cost and
carbon per token. These tests cover each group three ways. Metadata: every
variable has a unit and a reference, every equation has a reference, and the
unit-checked set is pinned. Numbers: each equation is evaluated through the
resolver at inputs chosen so the answer can be derived by hand, and the
expected value is computed in the test from those same inputs. Behavior: the
limiting cases (never reaches the throttle threshold, no recall, no shifting)
come out where the algebra says they must. A unit check that has been
deliberately broken must raise, so the checks are known to bite.

Inputs in these tests are arbitrary numbers picked for arithmetic, not
measurements of any system. The one sampling test uses simulated (synthetic)
draws from a normal distribution to check the exceedance rule 1 - q.
"""

import math

import numpy as np
import pytest
import sympy as sp

import gpu_stack
from gpu_stack import Registry, resolve
from gpu_stack.core.units import (
    HOUR, JOULE, KELVIN, KILOGRAM, KWH, SECOND, WATT, UnitError,
    check_equation_units, infer_expr_units_with_coefficient,
)
from gpu_stack.scopes import (
    SCOPE_DESCRIPTIONS, SCOPE_MODULES, power_forecast as pf,
)
from gpu_stack.scopes.economics_capex_refs import USD


# Equations that carry a unit check. Pinned on purpose: the one piecewise
# relation is not unit-checked (the checker cannot infer a Piecewise), and
# its closed-form branch is checked on its own; inequalities state bounds.
UNCHECKED_POWER_FORECAST_RELATIONS = {
    "forecast.eq.rc.time_to_throttle",
    "forecast.ineq.plan.quantile_level_below_one",
    "forecast.ineq.rc.threshold_above_supply",
    "forecast.ineq.ckpt.lead_time_covers_checkpoint",
}


def value(variable_name, **assignments):
    """Resolve a variable with assignments keyed by registered variable name."""
    result = resolve(variable_name, assignments=assignments)
    assert result.value is not None, result
    return result.value


def constraint(variable_name, equation, **assignments):
    result = resolve(variable_name, assignments=assignments)
    return next(c for c in result.constraints if c.equation == equation)


# ---------------------------------------------------------------------------
# Registration and metadata
# ---------------------------------------------------------------------------

def test_scope_is_registered_after_economics():
    assert "power_forecast" in SCOPE_MODULES
    assert SCOPE_MODULES.index("power_forecast") > SCOPE_MODULES.index("economics")
    assert SCOPE_DESCRIPTIONS["power_forecast"]
    assert "power_forecast" in Registry.systems


def test_every_variable_and_equation_has_units_and_references():
    assert pf.POWER_FORECAST_VARIABLES
    assert [v.name for v in pf.POWER_FORECAST_VARIABLES if v.sp_units is None] == []
    assert [v.name for v in pf.POWER_FORECAST_VARIABLES if not v.references] == []
    assert [e.name for e in pf.POWER_FORECAST_EQUATIONS if not e.references] == []
    assert all(v.scope == "power_forecast" for v in pf.POWER_FORECAST_VARIABLES)


def test_unit_checked_equations_are_explicitly_curated():
    unchecked = {
        e.name
        for e in pf.POWER_FORECAST_EQUATIONS
        if not getattr(e, "_check_units_flag", False)
    }
    assert unchecked == UNCHECKED_POWER_FORECAST_RELATIONS


def test_names_follow_the_forecast_prefix_and_are_unique():
    names = [v.name for v in pf.POWER_FORECAST_VARIABLES]
    assert len(names) == len(set(names))
    assert all(n.startswith("forecast.") for n in names)
    eq_names = [e.name for e in pf.POWER_FORECAST_EQUATIONS]
    assert len(eq_names) == len(set(eq_names))
    assert all(n.startswith("forecast.eq.") or n.startswith("forecast.ineq.") for n in eq_names)


def test_sources_are_cited_with_links():
    sources = {
        r
        for v in pf.POWER_FORECAST_VARIABLES
        for r in v.references
        if r.kind in {"paper", "textbook"}
    }
    # Gneiting & Raftery, Koenker, Koenker & Bassett, Fan et al., Incropera,
    # Young, Daly, Wiesner et al., Radovanovic et al.
    assert len(sources) == 9
    for ref in sources:
        if ref.kind == "paper":
            assert ref.url and ref.year


def test_forecaster_inputs_point_at_the_experiment_and_carry_no_default():
    for name in (
        "forecast.plan.site_power_planned",
        "forecast.plan.site_power_expected",
        "forecast.plan.overshoot_power_mean",
        "forecast.rc.heat_power",
        "forecast.ckpt.lead_time",
        "forecast.ckpt.recall",
        "forecast.shift.price_shifted",
        "forecast.shift.carbon_intensity_shifted",
    ):
        v = Registry.variables[name]
        assert v.is_root_input, name
        assert any("e003-heatwave" in r.citation for r in v.references), name


def test_the_scope_adds_no_cycles_and_no_duplicate_of_existing_variables():
    assert gpu_stack.find_cycles() == []
    reused = {
        "thermal.dc.pue",
        "thermal.coolant.t_inlet",
        "cluster.rel.checkpoint_time",
        "cluster.rel.optimal_checkpoint_interval",
        "econ.power.price_kwh",
        "econ.carbon.intensity_kg_per_kwh",
        "econ.carbon.price_per_tonne",
        "econ.job.dc_power",
        "econ.cost.per_token",
        "training.tokens_per_sec",
    }
    used = {
        v.name
        for e in pf.POWER_FORECAST_EQUATIONS
        for v in e.variables_in_relation()
    }
    assert reused <= used


def test_representative_units():
    assert pf.site_power_cap.sp_units == WATT
    assert pf.overcap_energy.sp_units == KWH
    assert pf.overcap_penalty_cost.sp_units == USD
    assert pf.rc_resistance.sp_units == KELVIN / WATT
    assert pf.rc_capacitance.sp_units == JOULE / KELVIN
    assert pf.rc_time_constant.sp_units == SECOND
    assert pf.rc_steady_temperature.sp_units == KELVIN
    assert pf.lost_work_unwarned.sp_units == HOUR
    assert pf.facility_energy_per_token.sp_units == JOULE
    assert pf.carbon_per_token.sp_units == KILOGRAM
    assert pf.price_paid.sp_units == USD / KWH


def _units_agree(equation, rhs):
    symbol_units = {
        v.symbol: v.sp_units for v in Registry.variables.values() if v.sp_units is not None
    }
    lhs_u = infer_expr_units_with_coefficient(equation.lhs, symbol_units, equation.name)
    rhs_u = infer_expr_units_with_coefficient(rhs, symbol_units, equation.name)
    check_equation_units(lhs_u, rhs_u, equation.name)


def test_unit_checks_pass_as_written_and_raise_when_broken():
    for equation in pf.POWER_FORECAST_EQUATIONS:
        if getattr(equation, "_check_units_flag", False):
            _units_agree(equation, equation.rhs)

    # Dropping or doubling a conversion factor must be caught.
    broken = {
        pf.eq_overcap_energy: pf.eq_overcap_energy.rhs * sp.Integer(3_600_000),
        pf.eq_lost_work_unwarned: pf.eq_lost_work_unwarned.rhs * sp.Integer(3600),
        pf.eq_energy_cost_per_token: pf.eq_energy_cost_per_token.rhs * sp.Integer(3_600_000),
    }
    # A time constant swapped for a resistance changes the exponent's dimension.
    broken[pf.eq_rc_temperature_at_time] = pf.eq_rc_temperature_at_time.rhs.subs(
        pf.rc_time_constant.symbol, pf.rc_resistance.symbol
    )
    for equation, bad_rhs in broken.items():
        with pytest.raises(UnitError):
            _units_agree(equation, bad_rhs)


# ---------------------------------------------------------------------------
# Group 1: planning at a quantile, packing, exceedance, over-cap energy
# ---------------------------------------------------------------------------

def test_headroom_and_packable_gpus():
    cap, planned = 10.0e6, 8.0e6
    gpu_it_power, pue = 700.0, 1.25
    headroom = cap - planned
    assert value(
        "forecast.plan.headroom",
        **{"forecast.plan.site_power_cap": cap, "forecast.plan.site_power_planned": planned},
    ) == pytest.approx(headroom)
    per_gpu_site = gpu_it_power * pue
    assert value(
        "forecast.plan.gpu_site_power_planned",
        **{"forecast.plan.gpu_power_planned": gpu_it_power, "thermal.dc.pue": pue},
    ) == pytest.approx(per_gpu_site)
    assert value(
        "forecast.plan.n_gpus_packable",
        **{
            "forecast.plan.site_power_cap": cap,
            "forecast.plan.site_power_planned": planned,
            "forecast.plan.gpu_power_planned": gpu_it_power,
            "thermal.dc.pue": pue,
        },
    ) == pytest.approx(headroom / per_gpu_site)


def test_plan_over_the_cap_gives_negative_headroom_and_gpus_to_remove():
    inputs = {
        "forecast.plan.site_power_cap": 5.0e6,
        "forecast.plan.site_power_planned": 6.0e6,
        "forecast.plan.gpu_power_planned": 800.0,
        "thermal.dc.pue": 1.0,
    }
    assert value("forecast.plan.headroom", **inputs) == pytest.approx(-1.0e6)
    assert value("forecast.plan.n_gpus_packable", **inputs) == pytest.approx(-1.0e6 / 800.0)


@pytest.mark.parametrize("q", [0.5, 0.9, 0.95, 0.99])
def test_exceedance_probability_is_one_minus_q(q):
    assert value(
        "forecast.plan.exceedance_probability", **{"forecast.plan.quantile_level": q}
    ) == pytest.approx(1.0 - q)


def test_calibrated_quantile_exceedance_matches_one_minus_q_on_synthetic_draws():
    # Simulated (synthetic) site power draws, not a measurement.
    rng = np.random.default_rng(0)
    draws = rng.normal(loc=8.0e6, scale=0.5e6, size=200_000)
    for q in (0.5, 0.9, 0.99):
        planned = float(np.quantile(draws, q))
        empirical = float(np.mean(draws > planned))
        predicted = value(
            "forecast.plan.exceedance_probability", **{"forecast.plan.quantile_level": q}
        )
        assert empirical == pytest.approx(predicted, abs=0.004)


def test_overcap_energy_and_penalty():
    q, overshoot, horizon, price = 0.9, 5.0e5, 3600.0, 0.2
    p_exceed = 1.0 - q
    energy_kwh = p_exceed * overshoot * horizon / 3.6e6
    inputs = {
        "forecast.plan.quantile_level": q,
        "forecast.plan.overshoot_power_mean": overshoot,
        "forecast.plan.horizon": horizon,
        "forecast.plan.overcap_price": price,
    }
    assert value("forecast.plan.overcap_energy", **inputs) == pytest.approx(energy_kwh)
    assert value("forecast.plan.overcap_penalty_cost", **inputs) == pytest.approx(
        energy_kwh * price
    )


def test_raising_the_quantile_lowers_expected_overcap_penalty():
    base = {
        "forecast.plan.overshoot_power_mean": 5.0e5,
        "forecast.plan.horizon": 7200.0,
        "forecast.plan.overcap_price": 0.1,
    }
    costs = [
        value("forecast.plan.overcap_penalty_cost", **base, **{"forecast.plan.quantile_level": q})
        for q in (0.5, 0.9, 0.99)
    ]
    assert costs[0] > costs[1] > costs[2] > 0


def test_quantile_level_must_lie_strictly_between_zero_and_one():
    for q, ok in ((0.5, True), (0.0, False), (1.0, False)):
        above = constraint(
            "forecast.plan.exceedance_probability",
            "domain.forecast.plan.quantile_level.positive",
            **{"forecast.plan.quantile_level": q},
        )
        below = constraint(
            "forecast.plan.exceedance_probability",
            "forecast.ineq.plan.quantile_level_below_one",
            **{"forecast.plan.quantile_level": q},
        )
        assert (above.satisfied and below.satisfied) is ok


# ---------------------------------------------------------------------------
# Group 2: stranded power
# ---------------------------------------------------------------------------

def test_stranded_power_utilization_and_reserve():
    cap, expected, planned = 10.0e6, 6.0e6, 8.0e6
    inputs = {
        "forecast.plan.site_power_cap": cap,
        "forecast.plan.site_power_expected": expected,
        "forecast.plan.site_power_planned": planned,
    }
    assert value("forecast.plan.stranded_power", **inputs) == pytest.approx(cap - expected)
    assert value("forecast.plan.cap_utilization", **inputs) == pytest.approx(expected / cap)
    assert value("forecast.plan.uncertainty_reserve", **inputs) == pytest.approx(planned - expected)


def test_stranded_power_plus_utilization_account_for_the_whole_cap():
    inputs = {
        "forecast.plan.site_power_cap": 12.0e6,
        "forecast.plan.site_power_expected": 9.0e6,
    }
    stranded = value("forecast.plan.stranded_power", **inputs)
    utilization = value("forecast.plan.cap_utilization", **inputs)
    assert stranded / inputs["forecast.plan.site_power_cap"] == pytest.approx(1.0 - utilization)


# ---------------------------------------------------------------------------
# Group 3: lumped RC thermal model
# ---------------------------------------------------------------------------

RC = {
    "forecast.rc.resistance": 0.05,         # K/W
    "forecast.rc.capacitance": 2000.0,      # J/K
    "forecast.rc.heat_power": 700.0,        # W
    "thermal.coolant.t_inlet": 300.0,       # K
    "forecast.rc.initial_temperature": 310.0,
    "forecast.rc.throttle_temperature": 330.0,
    "forecast.rc.elapsed_time": 60.0,
}


def rc(**overrides):
    return {**RC, **overrides}


def test_rc_time_constant_and_steady_state():
    tau = RC["forecast.rc.resistance"] * RC["forecast.rc.capacitance"]
    steady = RC["thermal.coolant.t_inlet"] + RC["forecast.rc.heat_power"] * RC["forecast.rc.resistance"]
    assert value("forecast.rc.time_constant", **RC) == pytest.approx(tau)
    assert value("forecast.rc.steady_temperature", **RC) == pytest.approx(steady)


def test_rc_temperature_after_time_matches_the_closed_form():
    tau = RC["forecast.rc.resistance"] * RC["forecast.rc.capacitance"]
    steady = RC["thermal.coolant.t_inlet"] + RC["forecast.rc.heat_power"] * RC["forecast.rc.resistance"]
    t0 = RC["forecast.rc.initial_temperature"]
    for t in (0.0, 30.0, tau, 5 * tau, 50 * tau):
        expected = steady + (t0 - steady) * math.exp(-t / tau)
        assert value(
            "forecast.rc.temperature_at_time", **rc(**{"forecast.rc.elapsed_time": t})
        ) == pytest.approx(expected)


def test_rc_temperature_limits_and_one_time_constant():
    tau = RC["forecast.rc.resistance"] * RC["forecast.rc.capacitance"]
    steady = RC["thermal.coolant.t_inlet"] + RC["forecast.rc.heat_power"] * RC["forecast.rc.resistance"]
    t0 = RC["forecast.rc.initial_temperature"]

    def at(t):
        return value("forecast.rc.temperature_at_time", **rc(**{"forecast.rc.elapsed_time": t}))

    assert at(0.0) == pytest.approx(t0)
    assert at(100 * tau) == pytest.approx(steady)
    # After one time constant the gap to steady state has shrunk to 1/e.
    assert at(tau) - steady == pytest.approx((t0 - steady) / math.e)


def test_rc_time_to_throttle_is_the_time_the_closed_form_reaches_the_threshold():
    tau = RC["forecast.rc.resistance"] * RC["forecast.rc.capacitance"]
    steady = RC["thermal.coolant.t_inlet"] + RC["forecast.rc.heat_power"] * RC["forecast.rc.resistance"]
    t0, thr = RC["forecast.rc.initial_temperature"], RC["forecast.rc.throttle_temperature"]
    expected = tau * math.log((steady - t0) / (steady - thr))
    t_hit = value("forecast.rc.time_to_throttle", **RC)
    assert t_hit == pytest.approx(expected)
    # Round trip: evaluated at that time, the temperature equals the threshold.
    assert value(
        "forecast.rc.temperature_at_time", **rc(**{"forecast.rc.elapsed_time": t_hit})
    ) == pytest.approx(thr)


def test_rc_time_to_throttle_is_infinite_when_the_threshold_is_never_reached():
    # Steady state 325 K sits below the 330 K threshold.
    low_power = rc(**{"forecast.rc.heat_power": 500.0})
    assert value("forecast.rc.time_to_throttle", **low_power) == sp.oo
    # Steady state exactly at the threshold is approached but not reached.
    at_threshold = rc(**{"forecast.rc.heat_power": 600.0})
    assert value("forecast.rc.time_to_throttle", **at_threshold) == sp.oo


def test_rc_time_to_throttle_is_zero_when_already_at_or_above_the_threshold():
    for t0 in (330.0, 335.0):
        assert value(
            "forecast.rc.time_to_throttle", **rc(**{"forecast.rc.initial_temperature": t0})
        ) == 0


def test_rc_cooling_margin_sign_matches_whether_the_threshold_is_reached():
    sustainable = (RC["forecast.rc.throttle_temperature"] - RC["thermal.coolant.t_inlet"]) / RC["forecast.rc.resistance"]
    assert value("forecast.rc.sustainable_power", **RC) == pytest.approx(sustainable)
    for power in (500.0, 599.0, 601.0, 700.0):
        margin = value("forecast.rc.cooling_margin", **rc(**{"forecast.rc.heat_power": power}))
        assert margin == pytest.approx(sustainable - power)
        t_hit = value("forecast.rc.time_to_throttle", **rc(**{"forecast.rc.heat_power": power}))
        assert (margin > 0) == (t_hit == sp.oo)


def test_rc_matches_the_package_junction_temperature_in_the_thermal_scope():
    # One package: R = theta_ja and Q = package power, so the RC steady state
    # equals the thermal scope's junction temperature.
    theta_jc, theta_ca, power, supply = 0.015, 0.025, 1000.0, 305.0
    theta_ja = theta_jc + theta_ca
    junction = value(
        "thermal.t_junction",
        **{
            "thermal.coolant.t_inlet": supply,
            "thermal.theta_ca": theta_ca,
            "thermal.theta_jc": theta_jc,
            "gpu.power.total": power,
        },
    )
    steady = value(
        "forecast.rc.steady_temperature",
        **{
            "forecast.rc.resistance": theta_ja,
            "forecast.rc.heat_power": power,
            "thermal.coolant.t_inlet": supply,
        },
    )
    assert steady == pytest.approx(junction)


def test_rc_threshold_must_lie_above_supply_temperature():
    ok = constraint(
        "forecast.rc.sustainable_power", "forecast.ineq.rc.threshold_above_supply", **RC
    )
    bad = constraint(
        "forecast.rc.sustainable_power",
        "forecast.ineq.rc.threshold_above_supply",
        **rc(**{"forecast.rc.throttle_temperature": 295.0}),
    )
    assert ok.satisfied is True
    assert bad.satisfied is False


# ---------------------------------------------------------------------------
# Group 4: early checkpoint value
# ---------------------------------------------------------------------------

CKPT = {
    "cluster.rel.optimal_checkpoint_interval": 3600.0,  # s
    "cluster.rel.checkpoint_time": 120.0,                # s
    "forecast.ckpt.gpus_affected": 1024,
    "forecast.ckpt.recall": 0.8,
    "forecast.ckpt.lead_time": 300.0,
}


def test_lost_work_without_and_with_warning():
    unwarned = 0.5 * CKPT["cluster.rel.optimal_checkpoint_interval"] * CKPT["forecast.ckpt.gpus_affected"] / 3600.0
    warned = CKPT["cluster.rel.checkpoint_time"] * CKPT["forecast.ckpt.gpus_affected"] / 3600.0
    assert value("forecast.ckpt.lost_work_unwarned", **CKPT) == pytest.approx(unwarned)
    assert value("forecast.ckpt.lost_work_warned", **CKPT) == pytest.approx(warned)
    # 0.5 h on 1024 GPUs is 512 GPU-hours; one 120 s write is 1024/30 GPU-hours.
    assert unwarned == pytest.approx(512.0)
    assert warned == pytest.approx(1024.0 / 30.0)


def test_expected_loss_and_gpu_hours_saved_weight_the_cases_by_recall():
    unwarned = 0.5 * 3600.0 * 1024 / 3600.0
    warned = 120.0 * 1024 / 3600.0
    r = CKPT["forecast.ckpt.recall"]
    expected = r * warned + (1 - r) * unwarned
    assert value("forecast.ckpt.lost_work_expected", **CKPT) == pytest.approx(expected)
    assert value("forecast.ckpt.gpu_hours_saved", **CKPT) == pytest.approx(unwarned - expected)
    assert value("forecast.ckpt.gpu_hours_saved", **CKPT) == pytest.approx(r * (unwarned - warned))


def test_recall_zero_saves_nothing_and_recall_one_saves_the_full_difference():
    unwarned = 0.5 * 3600.0 * 1024 / 3600.0
    warned = 120.0 * 1024 / 3600.0
    none = {**CKPT, "forecast.ckpt.recall": 0.0}
    full = {**CKPT, "forecast.ckpt.recall": 1.0}
    assert value("forecast.ckpt.gpu_hours_saved", **none) == pytest.approx(0.0)
    assert value("forecast.ckpt.gpu_hours_saved", **full) == pytest.approx(unwarned - warned)


def test_gpu_hours_saved_scale_with_job_size_and_interval():
    base = value("forecast.ckpt.gpu_hours_saved", **CKPT)
    double_gpus = value("forecast.ckpt.gpu_hours_saved", **{**CKPT, "forecast.ckpt.gpus_affected": 2048})
    assert double_gpus == pytest.approx(2 * base)
    longer = value(
        "forecast.ckpt.gpu_hours_saved",
        **{**CKPT, "cluster.rel.optimal_checkpoint_interval": 7200.0},
    )
    assert longer > base


def test_lead_time_must_cover_the_checkpoint_write():
    ok = constraint(
        "forecast.ckpt.gpu_hours_saved", "forecast.ineq.ckpt.lead_time_covers_checkpoint", **CKPT
    )
    short = constraint(
        "forecast.ckpt.gpu_hours_saved",
        "forecast.ineq.ckpt.lead_time_covers_checkpoint",
        **{**CKPT, "forecast.ckpt.lead_time": 60.0},
    )
    exact = constraint(
        "forecast.ckpt.gpu_hours_saved",
        "forecast.ineq.ckpt.lead_time_covers_checkpoint",
        **{**CKPT, "forecast.ckpt.lead_time": 120.0},
    )
    assert ok.satisfied is True
    assert short.satisfied is False
    assert exact.satisfied is True


# ---------------------------------------------------------------------------
# Group 5: time-shifting flexible work
# ---------------------------------------------------------------------------

SHIFT = {
    "forecast.shift.flexible_fraction": 0.25,
    "econ.power.price_kwh": 0.10,                 # USD/kWh, unshifted blended
    "forecast.shift.price_shifted": 0.04,         # USD/kWh
    "econ.carbon.intensity_kg_per_kwh": 0.40,     # kg/kWh, unshifted
    "forecast.shift.carbon_intensity_shifted": 0.10,
    "econ.job.dc_power": 1.0e6,                   # W
    "training.tokens_per_sec": 2.0e5,             # tokens/s
    "econ.cost.per_token": 1.0e-6,                # USD/token
    "econ.carbon.price_per_tonne": 50.0,          # USD/t
}


def test_energy_weighted_price_and_carbon_paid():
    phi = SHIFT["forecast.shift.flexible_fraction"]
    price = (1 - phi) * SHIFT["econ.power.price_kwh"] + phi * SHIFT["forecast.shift.price_shifted"]
    carbon = (
        (1 - phi) * SHIFT["econ.carbon.intensity_kg_per_kwh"]
        + phi * SHIFT["forecast.shift.carbon_intensity_shifted"]
    )
    assert value("forecast.shift.price_paid", **SHIFT) == pytest.approx(price)
    assert value("forecast.shift.carbon_intensity_paid", **SHIFT) == pytest.approx(carbon)


def test_facility_energy_cost_and_carbon_per_token():
    energy = SHIFT["econ.job.dc_power"] / SHIFT["training.tokens_per_sec"]   # J/token
    phi = SHIFT["forecast.shift.flexible_fraction"]
    price = (1 - phi) * 0.10 + phi * 0.04
    carbon = (1 - phi) * 0.40 + phi * 0.10
    assert energy == pytest.approx(5.0)
    assert value("forecast.shift.facility_energy_per_token", **SHIFT) == pytest.approx(energy)
    assert value("forecast.shift.energy_cost_per_token", **SHIFT) == pytest.approx(
        energy * price / 3.6e6
    )
    assert value("forecast.shift.carbon_per_token", **SHIFT) == pytest.approx(
        energy * carbon / 3.6e6
    )
    assert value("forecast.shift.carbon_per_token_unshifted", **SHIFT) == pytest.approx(
        energy * 0.40 / 3.6e6
    )


def test_shifted_cost_per_token_swaps_in_shifted_electricity_and_carbon_cost():
    phi = 0.25
    energy = 5.0
    price_paid = (1 - phi) * 0.10 + phi * 0.04
    m0 = energy * 0.40 / 3.6e6
    m1 = energy * ((1 - phi) * 0.40 + phi * 0.10) / 3.6e6
    expected = (
        SHIFT["econ.cost.per_token"]
        + energy * (price_paid - 0.10) / 3.6e6
        + 50.0 * (m1 - m0) / 1000.0
    )
    assert value("forecast.shift.cost_per_token", **SHIFT) == pytest.approx(expected)
    assert value("forecast.shift.cost_saving_per_token", **SHIFT) == pytest.approx(
        SHIFT["econ.cost.per_token"] - expected
    )
    assert value("forecast.shift.carbon_saving_per_token", **SHIFT) == pytest.approx(m0 - m1)


def test_no_shifting_leaves_cost_and_carbon_per_token_unchanged():
    none = {**SHIFT, "forecast.shift.flexible_fraction": 0.0}
    assert value("forecast.shift.price_paid", **none) == pytest.approx(0.10)
    assert value("forecast.shift.cost_per_token", **none) == pytest.approx(SHIFT["econ.cost.per_token"])
    assert value("forecast.shift.cost_saving_per_token", **none) == pytest.approx(0.0, abs=1e-18)
    assert value("forecast.shift.carbon_saving_per_token", **none) == pytest.approx(0.0, abs=1e-18)


def test_shifting_everything_pays_the_shifted_hours_price_and_intensity():
    all_in = {**SHIFT, "forecast.shift.flexible_fraction": 1.0}
    assert value("forecast.shift.price_paid", **all_in) == pytest.approx(0.04)
    assert value("forecast.shift.carbon_intensity_paid", **all_in) == pytest.approx(0.10)


def test_savings_grow_with_the_flexible_fraction_when_shifted_hours_are_cheaper_and_cleaner():
    savings = [
        value(
            "forecast.shift.cost_saving_per_token",
            **{**SHIFT, "forecast.shift.flexible_fraction": phi},
        )
        for phi in (0.0, 0.25, 0.5, 1.0)
    ]
    carbon = [
        value(
            "forecast.shift.carbon_saving_per_token",
            **{**SHIFT, "forecast.shift.flexible_fraction": phi},
        )
        for phi in (0.0, 0.25, 0.5, 1.0)
    ]
    assert savings == sorted(savings) and savings[-1] > savings[0]
    assert carbon == sorted(carbon) and carbon[-1] > carbon[0]


def test_shifting_to_dearer_hours_gives_negative_cost_saving():
    dearer = {**SHIFT, "forecast.shift.price_shifted": 0.20, "econ.carbon.price_per_tonne": 0.0}
    assert value("forecast.shift.cost_saving_per_token", **dearer) < 0


def test_economics_run_power_cost_agrees_with_facility_energy_per_token():
    # Run electricity cost per token in the economics scope is
    # price_ws * job power * wall-clock / tokens, and wall-clock = tokens / TPS,
    # so it equals the facility energy per token times the blended price.
    tokens = 1.0e12
    tps = SHIFT["training.tokens_per_sec"]
    wallclock = tokens / tps
    run_cost = value(
        "econ.run.power_cost",
        **{
            "econ.power.price_kwh": SHIFT["econ.power.price_kwh"],
            "econ.job.dc_power": SHIFT["econ.job.dc_power"],
            "training.wallclock": wallclock,
        },
    )
    energy = value("forecast.shift.facility_energy_per_token", **SHIFT)
    assert run_cost / tokens == pytest.approx(energy * SHIFT["econ.power.price_kwh"] / 3.6e6)
