"""
scopes/power_forecast_planning.py
=================================

Packing jobs under a site power cap by planning at a forecast quantile.

A site has a power cap: a contract limit, a transformer rating, or a feeder
rating. A reactive operator keeps power under the cap by leaving room for the
worst case it has seen. A forecast-aware operator reads a probabilistic
forecast of site power and plans at a chosen quantile q: the planned power is
the forecast q-quantile, and for a calibrated forecast the chance that real
power lands above the plan is 1 - q. Headroom is the cap minus the plan, and
dividing headroom by the planned facility power of one more GPU gives how many
more GPUs fit. Power that does land above the cap costs energy at an over-cap
price. Stranded power is the other side of the same ledger: the cap minus the
expected power, which is the capacity a reactive operator leaves unused.

The forecast outputs (planned power, expected power, mean overshoot) are root
inputs: the scope sets no default for them, because they come from the
Heatwave experiment's forecasts. The facility overhead that turns a GPU's IT
power into site power is the PUE already in the thermal scope.
"""

import sympy as sp

from ..core import Inequality, eq
from ..core.units import KWH, SECOND, WATT

from .thermal_facility import pue
from .power_forecast_refs import (
    forecast_var,
    E003_INPUT_REF,
    FAN_WEBER_BARROSO_2007_REF,
    GNEITING_RAFTERY_2007_REF,
    KOENKER_2005_REF,
    KOENKER_BASSETT_1978_REF,
    OVERCAP_COST_MODEL_REF,
    QUANTILE_PLANNING_MODEL_REF,
    STRANDED_POWER_MODEL_REF,
)
from .economics_capex_refs import USD


DIMENSIONLESS = sp.Integer(1)
ENERGY_PRICE_KWH = USD / KWH

PLANNING_REFS = [
    QUANTILE_PLANNING_MODEL_REF,
    GNEITING_RAFTERY_2007_REF,
    KOENKER_2005_REF,
]
FORECAST_INPUT_REFS = [
    QUANTILE_PLANNING_MODEL_REF,
    E003_INPUT_REF,
    KOENKER_BASSETT_1978_REF,
]
OVERCAP_REFS = [OVERCAP_COST_MODEL_REF, KOENKER_2005_REF]
STRANDED_REFS = [STRANDED_POWER_MODEL_REF, FAN_WEBER_BARROSO_2007_REF]


# ---------------------------------------------------------------------------
# Root inputs: the cap, the quantile, and what the forecaster supplies
# ---------------------------------------------------------------------------

plan_quantile_level = forecast_var(
    "forecast.plan.quantile_level", "q_plan_fc", "dimensionless",
    "Quantile level q in (0, 1) at which the operator plans site power. A "
    "higher q plans closer to the worst case and lowers the chance of "
    "exceeding the cap.",
    [QUANTILE_PLANNING_MODEL_REF, KOENKER_2005_REF],
    value_range=(0.0, 1.0),
    positive=True,
    sp_units=DIMENSIONLESS,
)
site_power_cap = forecast_var(
    "forecast.plan.site_power_cap", "P_cap_fc", "W",
    "Site power cap that planned power must stay under (contract limit, "
    "transformer or feeder rating). It can equal the facility electrical "
    "design capacity in the thermal scope, or sit below it.",
    [QUANTILE_PLANNING_MODEL_REF],
    positive=True,
    sp_units=WATT,
)
site_power_planned = forecast_var(
    "forecast.plan.site_power_planned", "P_plan_fc", "W",
    "Planned site power: the forecast q-quantile of site power over the "
    "planning horizon, read from the forecaster at the quantile level "
    "forecast.plan.quantile_level.",
    FORECAST_INPUT_REFS,
    nonnegative=True,
    sp_units=WATT,
)
site_power_expected = forecast_var(
    "forecast.plan.site_power_expected", "P_exp_fc", "W",
    "Expected site power over the planning horizon: the forecast mean or the "
    "forecast median (state which when supplying it).",
    FORECAST_INPUT_REFS,
    nonnegative=True,
    sp_units=WATT,
)
gpu_power_planned = forecast_var(
    "forecast.plan.gpu_power_planned", "p_gpu_plan_fc", "W",
    "Planned IT power of one added GPU (a forecast quantile of its draw, "
    "including its share of the node), before facility overhead.",
    FORECAST_INPUT_REFS,
    positive=True,
    sp_units=WATT,
)
overshoot_power_mean = forecast_var(
    "forecast.plan.overshoot_power_mean", "P_over_fc", "W",
    "Mean amount by which site power exceeds the cap, averaged over the time "
    "it is above the cap. Read from the forecast's upper tail.",
    FORECAST_INPUT_REFS,
    nonnegative=True,
    sp_units=WATT,
)
planning_horizon = forecast_var(
    "forecast.plan.horizon", "T_hor_fc", "s",
    "Length of the planning horizon over which the plan applies.",
    [QUANTILE_PLANNING_MODEL_REF],
    positive=True,
    sp_units=SECOND,
)
overcap_price = forecast_var(
    "forecast.plan.overcap_price", "p_over_kWh_fc", "USD/(kW*h)",
    "Price paid per kilowatt-hour drawn above the cap (contract overage "
    "charge, curtailment cost, or shadow price). Supply from the site's "
    "tariff or contract; the scope sets no default.",
    [OVERCAP_COST_MODEL_REF],
    nonnegative=True,
    sp_units=ENERGY_PRICE_KWH,
)


# ---------------------------------------------------------------------------
# Derived: headroom, packing, exceedance, over-cap energy and penalty
# ---------------------------------------------------------------------------

planning_headroom = forecast_var(
    "forecast.plan.headroom", "P_head_fc", "W",
    "Provisioning headroom: site power cap minus planned site power. "
    "Negative when the plan already exceeds the cap.",
    PLANNING_REFS,
    signed=True,
    sp_units=WATT,
)
gpu_site_power_planned = forecast_var(
    "forecast.plan.gpu_site_power_planned", "p_gpu_site_fc", "W",
    "Planned site power of one added GPU: its planned IT power times PUE.",
    PLANNING_REFS,
    positive=True,
    sp_units=WATT,
)
n_gpus_packable = forecast_var(
    "forecast.plan.n_gpus_packable", "N_pack_fc", "GPUs",
    "Number of additional GPUs that fit in the headroom at their planned "
    "site power, before rounding down to a whole GPU. Negative when headroom "
    "is negative (GPUs to remove).",
    PLANNING_REFS,
    signed=True,
    sp_units=DIMENSIONLESS,
)
exceedance_probability = forecast_var(
    "forecast.plan.exceedance_probability", "p_exceed_fc", "dimensionless",
    "Expected probability that site power exceeds the plan, for a calibrated "
    "forecast: 1 - q. A miscalibrated forecast has a different realized rate; "
    "measure it from replays.",
    PLANNING_REFS,
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
)
overcap_energy = forecast_var(
    "forecast.plan.overcap_energy", "E_over_fc", "kW*h",
    "Expected energy drawn above the cap over the planning horizon: "
    "exceedance probability times mean overshoot power times horizon length.",
    OVERCAP_REFS,
    nonnegative=True,
    sp_units=KWH,
)
overcap_penalty_cost = forecast_var(
    "forecast.plan.overcap_penalty_cost", "C_over_fc", "USD",
    "Expected over-cap penalty over the planning horizon: over-cap energy "
    "times the over-cap price.",
    OVERCAP_REFS,
    nonnegative=True,
    sp_units=USD,
)


# ---------------------------------------------------------------------------
# Derived: stranded power and the reserve held for forecast uncertainty
# ---------------------------------------------------------------------------

stranded_power = forecast_var(
    "forecast.plan.stranded_power", "P_strand_fc", "W",
    "Stranded power: site power cap minus expected site power. It is the "
    "provisioned capacity that a reactive operator, who plans for the worst "
    "case, leaves unused on average.",
    STRANDED_REFS,
    signed=True,
    sp_units=WATT,
)
cap_utilization = forecast_var(
    "forecast.plan.cap_utilization", "u_cap_fc", "dimensionless",
    "Utilization of the cap: expected site power divided by the cap.",
    STRANDED_REFS,
    nonnegative=True,
    sp_units=DIMENSIONLESS,
)
uncertainty_reserve = forecast_var(
    "forecast.plan.uncertainty_reserve", "P_res_fc", "W",
    "Power held back for forecast uncertainty: planned power minus expected "
    "power. It is the part of the cap a quantile plan reserves beyond the "
    "expected draw.",
    PLANNING_REFS,
    signed=True,
    sp_units=WATT,
)


# ---------------------------------------------------------------------------
# Equations
# ---------------------------------------------------------------------------

eq_planning_headroom = eq(
    "forecast.eq.plan.headroom",
    planning_headroom.symbol,
    site_power_cap.symbol - site_power_planned.symbol,
    "Headroom equals the site power cap minus planned site power.",
    references=PLANNING_REFS,
    check_units=True,
)
eq_gpu_site_power_planned = eq(
    "forecast.eq.plan.gpu_site_power_planned",
    gpu_site_power_planned.symbol,
    gpu_power_planned.symbol * pue.symbol,
    "Planned site power of one added GPU equals its planned IT power times PUE.",
    references=PLANNING_REFS,
    check_units=True,
)
eq_n_gpus_packable = eq(
    "forecast.eq.plan.n_gpus_packable",
    n_gpus_packable.symbol,
    planning_headroom.symbol / gpu_site_power_planned.symbol,
    "GPUs that fit under the cap equal headroom divided by the planned site power of one GPU.",
    references=PLANNING_REFS,
    check_units=True,
)
eq_exceedance_probability = eq(
    "forecast.eq.plan.exceedance_probability",
    exceedance_probability.symbol,
    1 - plan_quantile_level.symbol,
    "For a calibrated quantile forecast, site power exceeds the planned "
    "q-quantile with probability 1 - q.",
    references=PLANNING_REFS,
    check_units=True,
)
eq_overcap_energy = eq(
    "forecast.eq.plan.overcap_energy",
    overcap_energy.symbol,
    exceedance_probability.symbol * overshoot_power_mean.symbol
    * planning_horizon.symbol / sp.Integer(3_600_000),
    "Expected over-cap energy equals exceedance probability times mean "
    "overshoot power times horizon, converted from joules to kilowatt-hours "
    "(3.6e6 J per kWh).",
    references=OVERCAP_REFS,
    check_units=True,
)
eq_overcap_penalty_cost = eq(
    "forecast.eq.plan.overcap_penalty_cost",
    overcap_penalty_cost.symbol,
    overcap_energy.symbol * overcap_price.symbol,
    "Over-cap penalty equals over-cap energy times the over-cap price.",
    references=OVERCAP_REFS,
    check_units=True,
)
eq_stranded_power = eq(
    "forecast.eq.plan.stranded_power",
    stranded_power.symbol,
    site_power_cap.symbol - site_power_expected.symbol,
    "Stranded power equals the site power cap minus expected site power.",
    references=STRANDED_REFS,
    check_units=True,
)
eq_cap_utilization = eq(
    "forecast.eq.plan.cap_utilization",
    cap_utilization.symbol,
    site_power_expected.symbol / site_power_cap.symbol,
    "Cap utilization equals expected site power divided by the cap.",
    references=STRANDED_REFS,
    check_units=True,
)
eq_uncertainty_reserve = eq(
    "forecast.eq.plan.uncertainty_reserve",
    uncertainty_reserve.symbol,
    site_power_planned.symbol - site_power_expected.symbol,
    "The uncertainty reserve equals planned site power minus expected site power.",
    references=PLANNING_REFS,
    check_units=True,
)

ineq_quantile_level_below_one = Inequality(
    "forecast.ineq.plan.quantile_level_below_one",
    plan_quantile_level.symbol,
    1,
    "<",
    "The planning quantile level must be strictly below 1 (the domain rule on the variable already requires it to be positive).",
    references=[QUANTILE_PLANNING_MODEL_REF],
)


POWER_FORECAST_PLANNING_VARIABLES = [
    plan_quantile_level,
    site_power_cap,
    site_power_planned,
    site_power_expected,
    gpu_power_planned,
    overshoot_power_mean,
    planning_horizon,
    overcap_price,
    planning_headroom,
    gpu_site_power_planned,
    n_gpus_packable,
    exceedance_probability,
    overcap_energy,
    overcap_penalty_cost,
    stranded_power,
    cap_utilization,
    uncertainty_reserve,
]

POWER_FORECAST_PLANNING_EQUATIONS = [
    eq_planning_headroom,
    eq_gpu_site_power_planned,
    eq_n_gpus_packable,
    eq_exceedance_probability,
    eq_overcap_energy,
    eq_overcap_penalty_cost,
    eq_stranded_power,
    eq_cap_utilization,
    eq_uncertainty_reserve,
    ineq_quantile_level_below_one,
]


__all__ = [
    "plan_quantile_level", "site_power_cap", "site_power_planned",
    "site_power_expected", "gpu_power_planned", "overshoot_power_mean",
    "planning_horizon", "overcap_price", "planning_headroom",
    "gpu_site_power_planned", "n_gpus_packable", "exceedance_probability",
    "overcap_energy", "overcap_penalty_cost", "stranded_power",
    "cap_utilization", "uncertainty_reserve",
    "eq_planning_headroom", "eq_gpu_site_power_planned", "eq_n_gpus_packable",
    "eq_exceedance_probability", "eq_overcap_energy",
    "eq_overcap_penalty_cost", "eq_stranded_power", "eq_cap_utilization",
    "eq_uncertainty_reserve",
    "ineq_quantile_level_below_one",
    "POWER_FORECAST_PLANNING_VARIABLES", "POWER_FORECAST_PLANNING_EQUATIONS",
]
