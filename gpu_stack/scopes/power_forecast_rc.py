"""
scopes/power_forecast_rc.py
===========================

A lumped RC thermal model for forecasting temperature and time to throttle.

Heat from a GPU, a node, or a rack loop flows through a thermal resistance R
(kelvin per watt) to the coolant supply, and the hardware stores heat in a
heat capacity C (joules per kelvin). With constant heat power Q the
temperature relaxes exponentially from its start value T0 toward a steady
state of supply temperature plus Q*R, with time constant tau = R*C. That is
the lumped-capacitance solution from any heat-transfer text, and it is
enough to turn a power forecast into a temperature forecast and a
time-until-throttle.

The time until a throttle threshold is reached has a closed form,
t = tau * ln((T_ss - T0) / (T_ss - T_thr)), which only exists when the
steady state sits above the threshold. The piecewise definition returns 0
when the node already sits at or above the threshold and infinity when the
threshold is never reached. The cooling margin is the power the node can
sustain below the threshold, (T_thr - T_supply) / R, minus the power it is
dissipating.

The coolant supply temperature is the thermal scope's coolant inlet
temperature. For one package, R equals the thermal scope's junction-to-
coolant resistance and the steady state equals its junction temperature;
this scope keeps R as its own input so it can describe a node or a rack loop
whose resistance and capacity are fitted from telemetry.
"""

import sympy as sp

from ..core import Inequality, PiecewiseEquation, eq
from ..core.units import JOULE, KELVIN, SECOND, WATT

from .thermal_package import T_coolant_inlet
from .power_forecast_refs import (
    forecast_var,
    E003_INPUT_REF,
    INCROPERA_LUMPED_REF,
    LUMPED_RC_MODEL_REF,
)


DIMENSIONLESS = sp.Integer(1)
THERMAL_RESISTANCE = KELVIN / WATT
HEAT_CAPACITY = JOULE / KELVIN

RC_REFS = [LUMPED_RC_MODEL_REF, INCROPERA_LUMPED_REF]
RC_INPUT_REFS = [LUMPED_RC_MODEL_REF, INCROPERA_LUMPED_REF, E003_INPUT_REF]


# ---------------------------------------------------------------------------
# Root inputs: R, C, heat power, start temperature, throttle threshold, time
# ---------------------------------------------------------------------------

rc_resistance = forecast_var(
    "forecast.rc.resistance", "R_rc_fc", "K/W",
    "Thermal resistance from the lumped node to its coolant supply. For one "
    "package it is the thermal scope's junction-to-coolant resistance; for a "
    "node or rack loop, fit it from telemetry.",
    RC_REFS,
    positive=True,
    sp_units=THERMAL_RESISTANCE,
)
rc_capacitance = forecast_var(
    "forecast.rc.capacitance", "C_rc_fc", "J/K",
    "Heat capacity of the lumped node: the energy needed to raise its "
    "temperature by one kelvin (mass times specific heat of the hardware and "
    "coolant it holds).",
    RC_REFS,
    positive=True,
    sp_units=HEAT_CAPACITY,
)
rc_heat_power = forecast_var(
    "forecast.rc.heat_power", "Q_rc_fc", "W",
    "Constant heat power dissipated into the lumped node over the interval. "
    "Take it from a power forecast quantile.",
    RC_INPUT_REFS,
    nonnegative=True,
    sp_units=WATT,
)
rc_initial_temperature = forecast_var(
    "forecast.rc.initial_temperature", "T0_rc_fc", "K",
    "Node temperature at the start of the interval.",
    RC_INPUT_REFS,
    positive=True,
    sp_units=KELVIN,
)
rc_elapsed_time = forecast_var(
    "forecast.rc.elapsed_time", "t_rc_fc", "s",
    "Time elapsed since the start of the interval.",
    RC_REFS,
    nonnegative=True,
    sp_units=SECOND,
)
rc_throttle_temperature = forecast_var(
    "forecast.rc.throttle_temperature", "T_thr_rc_fc", "K",
    "Temperature at which the hardware begins to throttle. Take it from the "
    "device datasheet; the scope sets no default.",
    RC_REFS,
    positive=True,
    sp_units=KELVIN,
)


# ---------------------------------------------------------------------------
# Derived: tau, steady state, temperature at time t, time to throttle, margin
# ---------------------------------------------------------------------------

rc_time_constant = forecast_var(
    "forecast.rc.time_constant", "tau_rc_fc", "s",
    "Thermal time constant: resistance times heat capacity.",
    RC_REFS,
    positive=True,
    sp_units=SECOND,
)
rc_steady_temperature = forecast_var(
    "forecast.rc.steady_temperature", "T_ss_rc_fc", "K",
    "Steady-state temperature under constant heat power: coolant supply "
    "temperature plus heat power times resistance.",
    RC_REFS,
    positive=True,
    sp_units=KELVIN,
)
rc_temperature_at_time = forecast_var(
    "forecast.rc.temperature_at_time", "T_t_rc_fc", "K",
    "Node temperature after the elapsed time, starting from the initial "
    "temperature under constant heat power.",
    RC_REFS,
    positive=True,
    sp_units=KELVIN,
)
rc_time_to_throttle_reachable = forecast_var(
    "forecast.rc.time_to_throttle_reachable", "t_thr_reach_rc_fc", "s",
    "Closed-form time to reach the throttle temperature, valid only when "
    "the initial temperature is below the threshold and the steady state is "
    "above it. Outside that case this expression has no real value; use "
    "forecast.rc.time_to_throttle, which handles those cases.",
    RC_REFS,
    sp_units=SECOND,
)
rc_time_to_throttle = forecast_var(
    "forecast.rc.time_to_throttle", "t_thr_rc_fc", "s",
    "Time until the node reaches the throttle temperature under constant "
    "heat power: 0 if it already sits at or above the threshold, infinity "
    "if the steady state never reaches it.",
    RC_REFS,
    nonnegative=True,
    sp_units=SECOND,
)
rc_sustainable_power = forecast_var(
    "forecast.rc.sustainable_power", "Q_sus_rc_fc", "W",
    "Largest constant heat power the node can dissipate without ever "
    "reaching the throttle temperature: (threshold - supply) / resistance.",
    RC_REFS,
    sp_units=WATT,
)
rc_cooling_margin = forecast_var(
    "forecast.rc.cooling_margin", "Q_mar_rc_fc", "W",
    "Cooling capacity margin: sustainable power minus the heat power being "
    "dissipated. Positive means the threshold is never reached; zero or "
    "negative means it is reached in finite time.",
    RC_REFS,
    signed=True,
    sp_units=WATT,
)


# ---------------------------------------------------------------------------
# Equations
# ---------------------------------------------------------------------------

eq_rc_time_constant = eq(
    "forecast.eq.rc.time_constant",
    rc_time_constant.symbol,
    rc_resistance.symbol * rc_capacitance.symbol,
    "The time constant is thermal resistance times heat capacity.",
    references=RC_REFS,
    check_units=True,
)
eq_rc_steady_temperature = eq(
    "forecast.eq.rc.steady_temperature",
    rc_steady_temperature.symbol,
    T_coolant_inlet.symbol + rc_heat_power.symbol * rc_resistance.symbol,
    "Steady-state temperature equals the coolant supply temperature plus heat power times resistance.",
    references=RC_REFS,
    check_units=True,
)
eq_rc_temperature_at_time = eq(
    "forecast.eq.rc.temperature_at_time",
    rc_temperature_at_time.symbol,
    rc_steady_temperature.symbol
    + (rc_initial_temperature.symbol - rc_steady_temperature.symbol)
    * sp.exp(-rc_elapsed_time.symbol / rc_time_constant.symbol),
    "Temperature relaxes exponentially from its initial value toward the "
    "steady state with the thermal time constant.",
    references=RC_REFS,
    check_units=True,
)
eq_rc_time_to_throttle_reachable = eq(
    "forecast.eq.rc.time_to_throttle_reachable",
    rc_time_to_throttle_reachable.symbol,
    rc_time_constant.symbol
    * sp.log(
        (rc_steady_temperature.symbol - rc_initial_temperature.symbol)
        / (rc_steady_temperature.symbol - rc_throttle_temperature.symbol)
    ),
    "Solving the exponential approach for the threshold gives time constant "
    "times the log of (steady - initial) over (steady - threshold).",
    references=RC_REFS,
    check_units=True,
)
eq_rc_time_to_throttle = PiecewiseEquation(
    "forecast.eq.rc.time_to_throttle",
    rc_time_to_throttle.symbol,
    [
        (0, rc_initial_temperature.symbol >= rc_throttle_temperature.symbol),
        (
            rc_time_to_throttle_reachable.symbol,
            rc_steady_temperature.symbol > rc_throttle_temperature.symbol,
        ),
        (sp.oo, True),
    ],
    "Time to throttle is 0 when the node already sits at or above the "
    "threshold, the closed-form time when the steady state lies above the "
    "threshold, and infinity when the threshold is never reached.",
    references=RC_REFS,
)
eq_rc_sustainable_power = eq(
    "forecast.eq.rc.sustainable_power",
    rc_sustainable_power.symbol,
    (rc_throttle_temperature.symbol - T_coolant_inlet.symbol)
    / rc_resistance.symbol,
    "Sustainable power equals the temperature room between supply and threshold divided by resistance.",
    references=RC_REFS,
    check_units=True,
)
eq_rc_cooling_margin = eq(
    "forecast.eq.rc.cooling_margin",
    rc_cooling_margin.symbol,
    rc_sustainable_power.symbol - rc_heat_power.symbol,
    "Cooling margin equals sustainable power minus the heat power dissipated.",
    references=RC_REFS,
    check_units=True,
)

ineq_rc_threshold_above_supply = Inequality(
    "forecast.ineq.rc.threshold_above_supply",
    rc_throttle_temperature.symbol,
    T_coolant_inlet.symbol,
    ">",
    "The throttle threshold must lie above the coolant supply temperature, "
    "otherwise no heat power is sustainable.",
    references=RC_REFS,
)


POWER_FORECAST_RC_VARIABLES = [
    rc_resistance,
    rc_capacitance,
    rc_heat_power,
    rc_initial_temperature,
    rc_elapsed_time,
    rc_throttle_temperature,
    rc_time_constant,
    rc_steady_temperature,
    rc_temperature_at_time,
    rc_time_to_throttle_reachable,
    rc_time_to_throttle,
    rc_sustainable_power,
    rc_cooling_margin,
]

POWER_FORECAST_RC_EQUATIONS = [
    eq_rc_time_constant,
    eq_rc_steady_temperature,
    eq_rc_temperature_at_time,
    eq_rc_time_to_throttle_reachable,
    eq_rc_time_to_throttle,
    eq_rc_sustainable_power,
    eq_rc_cooling_margin,
    ineq_rc_threshold_above_supply,
]


__all__ = [
    "rc_resistance", "rc_capacitance", "rc_heat_power",
    "rc_initial_temperature", "rc_elapsed_time", "rc_throttle_temperature",
    "rc_time_constant", "rc_steady_temperature", "rc_temperature_at_time",
    "rc_time_to_throttle_reachable", "rc_time_to_throttle",
    "rc_sustainable_power", "rc_cooling_margin",
    "eq_rc_time_constant", "eq_rc_steady_temperature",
    "eq_rc_temperature_at_time", "eq_rc_time_to_throttle_reachable",
    "eq_rc_time_to_throttle", "eq_rc_sustainable_power",
    "eq_rc_cooling_margin", "ineq_rc_threshold_above_supply",
    "POWER_FORECAST_RC_VARIABLES", "POWER_FORECAST_RC_EQUATIONS",
]
