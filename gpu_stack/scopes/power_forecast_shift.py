"""
scopes/power_forecast_shift.py
==============================

Trading dollars per token against carbon per token by moving flexible work.

Some of a job's energy is flexible: it can run in a different hour without
changing what the job produces. Price and grid carbon intensity both vary by
hour, and a forecast of each says which hours are cheaper and cleaner. If a
fraction phi of the job's energy moves to hours with price p_sh and carbon
intensity I_sh while the rest stays at the economics scope's blended price
and carbon intensity, the energy-weighted average the job pays is the convex
combination (1 - phi) * unshifted + phi * shifted.

Dividing by throughput turns that into per-token numbers. Facility energy per
token is the job's allocated site power over tokens per second (the same
power the economics scope bills), so electricity cost per token is that energy
times the average price paid, and carbon per token is that energy times the
average intensity paid. Total cost per token starts from the economics
scope's cost per token and swaps in the shifted electricity and carbon cost.
Shifted work is assumed to use cluster hours that would otherwise sit idle,
so every non-energy cost per token is unchanged.

The shifted hours' price and carbon intensity come from the Heatwave
experiment's price and carbon forecasts and have no default here.
"""

import sympy as sp

from ..core import eq
from ..core.units import JOULE, KILOGRAM, KWH

from .economics_capex_refs import USD
from .economics_opex import (
    carbon_intensity_kg_per_kwh,
    carbon_price_per_tonne,
    job_dc_power,
    price_kwh,
)
from .economics_recovery import cost_per_token
from .training_scaling import tokens_per_sec
from .power_forecast_refs import (
    forecast_var,
    E003_INPUT_REF,
    RADOVANOVIC_2021_REF,
    TIME_SHIFT_MODEL_REF,
    WIESNER_2021_REF,
)


DIMENSIONLESS = sp.Integer(1)
ENERGY_PRICE_KWH = USD / KWH
CARBON_INTENSITY_KWH = KILOGRAM / KWH

SHIFT_REFS = [TIME_SHIFT_MODEL_REF, WIESNER_2021_REF, RADOVANOVIC_2021_REF]
SHIFT_INPUT_REFS = SHIFT_REFS + [E003_INPUT_REF]

JOULES_PER_KWH = sp.Integer(3_600_000)
KG_PER_TONNE = sp.Integer(1000)


# ---------------------------------------------------------------------------
# Root inputs: the flexible fraction and the shifted hours' price and carbon
# ---------------------------------------------------------------------------

flexible_fraction = forecast_var(
    "forecast.shift.flexible_fraction", "phi_flex_fc", "dimensionless",
    "Fraction of the job's energy that is moved to the shifted hours "
    "(0 keeps the job where it is, 1 moves all of it).",
    SHIFT_REFS,
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
)
price_shifted = forecast_var(
    "forecast.shift.price_shifted", "p_sh_fc", "USD/(kW*h)",
    "Energy-weighted average electricity price of the hours the flexible "
    "work moves to, read from the price forecast.",
    SHIFT_INPUT_REFS,
    nonnegative=True,
    sp_units=ENERGY_PRICE_KWH,
)
carbon_intensity_shifted = forecast_var(
    "forecast.shift.carbon_intensity_shifted", "I_sh_fc", "kg/(kW*h)",
    "Energy-weighted average grid carbon intensity of the hours the flexible "
    "work moves to, read from the carbon-intensity forecast.",
    SHIFT_INPUT_REFS,
    nonnegative=True,
    sp_units=CARBON_INTENSITY_KWH,
)


# ---------------------------------------------------------------------------
# Derived: energy-weighted averages paid, then per-token energy, cost, carbon
# ---------------------------------------------------------------------------

price_paid = forecast_var(
    "forecast.shift.price_paid", "p_paid_fc", "USD/(kW*h)",
    "Energy-weighted average electricity price paid after shifting: the "
    "economics scope's blended price for the unshifted share and the shifted "
    "hours' price for the shifted share.",
    SHIFT_REFS,
    nonnegative=True,
    sp_units=ENERGY_PRICE_KWH,
)
carbon_intensity_paid = forecast_var(
    "forecast.shift.carbon_intensity_paid", "I_paid_fc", "kg/(kW*h)",
    "Energy-weighted average carbon intensity paid after shifting: the "
    "economics scope's grid intensity for the unshifted share and the "
    "shifted hours' intensity for the shifted share.",
    SHIFT_REFS,
    nonnegative=True,
    sp_units=CARBON_INTENSITY_KWH,
)
facility_energy_per_token = forecast_var(
    "forecast.shift.facility_energy_per_token", "e_tok_fac_fc", "J/token",
    "Facility energy per training token: the job's allocated site power "
    "divided by tokens per second.",
    SHIFT_REFS,
    nonnegative=True,
    sp_units=JOULE,
)
energy_cost_per_token = forecast_var(
    "forecast.shift.energy_cost_per_token", "c_e_tok_fc", "USD/token",
    "Electricity cost per token after shifting: facility energy per token "
    "times the average price paid.",
    SHIFT_REFS,
    nonnegative=True,
    sp_units=USD,
)
carbon_per_token_unshifted = forecast_var(
    "forecast.shift.carbon_per_token_unshifted", "m_tok0_fc", "kg/token",
    "Carbon emitted per token with no shifting: facility energy per token "
    "times the economics scope's grid carbon intensity.",
    SHIFT_REFS,
    nonnegative=True,
    sp_units=KILOGRAM,
)
carbon_per_token = forecast_var(
    "forecast.shift.carbon_per_token", "m_tok_fc", "kg/token",
    "Carbon emitted per token after shifting: facility energy per token "
    "times the average carbon intensity paid.",
    SHIFT_REFS,
    nonnegative=True,
    sp_units=KILOGRAM,
)
cost_per_token_shifted = forecast_var(
    "forecast.shift.cost_per_token", "C_tok_sh_fc", "USD/token",
    "Fully allocated cost per token after shifting: the economics scope's "
    "cost per token, with its electricity cost replaced by the shifted "
    "electricity cost and its carbon cost replaced by the shifted carbon "
    "cost. Non-energy costs are unchanged.",
    SHIFT_REFS,
    signed=True,
    sp_units=USD,
)
cost_saving_per_token = forecast_var(
    "forecast.shift.cost_saving_per_token", "dC_tok_fc", "USD/token",
    "Dollars saved per token by shifting: economics cost per token minus "
    "shifted cost per token. Negative when shifting costs more.",
    SHIFT_REFS,
    signed=True,
    sp_units=USD,
)
carbon_saving_per_token = forecast_var(
    "forecast.shift.carbon_saving_per_token", "dm_tok_fc", "kg/token",
    "Carbon avoided per token by shifting: unshifted carbon per token minus "
    "shifted carbon per token. Negative when shifting emits more.",
    SHIFT_REFS,
    signed=True,
    sp_units=KILOGRAM,
)


# ---------------------------------------------------------------------------
# Equations
# ---------------------------------------------------------------------------

eq_price_paid = eq(
    "forecast.eq.shift.price_paid",
    price_paid.symbol,
    (1 - flexible_fraction.symbol) * price_kwh.symbol
    + flexible_fraction.symbol * price_shifted.symbol,
    "Average price paid is the energy-weighted mix of the unshifted blended price and the shifted hours' price.",
    references=SHIFT_REFS,
    check_units=True,
)
eq_carbon_intensity_paid = eq(
    "forecast.eq.shift.carbon_intensity_paid",
    carbon_intensity_paid.symbol,
    (1 - flexible_fraction.symbol) * carbon_intensity_kg_per_kwh.symbol
    + flexible_fraction.symbol * carbon_intensity_shifted.symbol,
    "Average carbon intensity paid is the energy-weighted mix of the unshifted grid intensity and the shifted hours' intensity.",
    references=SHIFT_REFS,
    check_units=True,
)
eq_facility_energy_per_token = eq(
    "forecast.eq.shift.facility_energy_per_token",
    facility_energy_per_token.symbol,
    job_dc_power.symbol / tokens_per_sec.symbol,
    "Facility energy per token equals the job's allocated site power divided by tokens per second.",
    references=SHIFT_REFS,
    check_units=True,
)
eq_energy_cost_per_token = eq(
    "forecast.eq.shift.energy_cost_per_token",
    energy_cost_per_token.symbol,
    facility_energy_per_token.symbol * price_paid.symbol / JOULES_PER_KWH,
    "Electricity cost per token equals energy per token times the average "
    "price paid, with joules converted to kilowatt-hours (3.6e6 J per kWh).",
    references=SHIFT_REFS,
    check_units=True,
)
eq_carbon_per_token_unshifted = eq(
    "forecast.eq.shift.carbon_per_token_unshifted",
    carbon_per_token_unshifted.symbol,
    facility_energy_per_token.symbol * carbon_intensity_kg_per_kwh.symbol
    / JOULES_PER_KWH,
    "Unshifted carbon per token equals energy per token times grid carbon "
    "intensity, with joules converted to kilowatt-hours.",
    references=SHIFT_REFS,
    check_units=True,
)
eq_carbon_per_token = eq(
    "forecast.eq.shift.carbon_per_token",
    carbon_per_token.symbol,
    facility_energy_per_token.symbol * carbon_intensity_paid.symbol
    / JOULES_PER_KWH,
    "Shifted carbon per token equals energy per token times the average "
    "carbon intensity paid, with joules converted to kilowatt-hours.",
    references=SHIFT_REFS,
    check_units=True,
)
eq_cost_per_token_shifted = eq(
    "forecast.eq.shift.cost_per_token",
    cost_per_token_shifted.symbol,
    cost_per_token.symbol
    + facility_energy_per_token.symbol
    * (price_paid.symbol - price_kwh.symbol) / JOULES_PER_KWH
    + carbon_price_per_tonne.symbol
    * (carbon_per_token.symbol - carbon_per_token_unshifted.symbol)
    / KG_PER_TONNE,
    "Shifted cost per token equals the economics cost per token plus the "
    "change in electricity cost and the change in carbon cost per token.",
    references=SHIFT_REFS,
    check_units=True,
)
eq_cost_saving_per_token = eq(
    "forecast.eq.shift.cost_saving_per_token",
    cost_saving_per_token.symbol,
    cost_per_token.symbol - cost_per_token_shifted.symbol,
    "Cost saving per token equals economics cost per token minus shifted cost per token.",
    references=SHIFT_REFS,
    check_units=True,
)
eq_carbon_saving_per_token = eq(
    "forecast.eq.shift.carbon_saving_per_token",
    carbon_saving_per_token.symbol,
    carbon_per_token_unshifted.symbol - carbon_per_token.symbol,
    "Carbon saving per token equals unshifted carbon per token minus shifted carbon per token.",
    references=SHIFT_REFS,
    check_units=True,
)


POWER_FORECAST_SHIFT_VARIABLES = [
    flexible_fraction,
    price_shifted,
    carbon_intensity_shifted,
    price_paid,
    carbon_intensity_paid,
    facility_energy_per_token,
    energy_cost_per_token,
    carbon_per_token_unshifted,
    carbon_per_token,
    cost_per_token_shifted,
    cost_saving_per_token,
    carbon_saving_per_token,
]

POWER_FORECAST_SHIFT_EQUATIONS = [
    eq_price_paid,
    eq_carbon_intensity_paid,
    eq_facility_energy_per_token,
    eq_energy_cost_per_token,
    eq_carbon_per_token_unshifted,
    eq_carbon_per_token,
    eq_cost_per_token_shifted,
    eq_cost_saving_per_token,
    eq_carbon_saving_per_token,
]


__all__ = [
    "flexible_fraction", "price_shifted", "carbon_intensity_shifted",
    "price_paid", "carbon_intensity_paid", "facility_energy_per_token",
    "energy_cost_per_token", "carbon_per_token_unshifted", "carbon_per_token",
    "cost_per_token_shifted", "cost_saving_per_token",
    "carbon_saving_per_token",
    "eq_price_paid", "eq_carbon_intensity_paid",
    "eq_facility_energy_per_token", "eq_energy_cost_per_token",
    "eq_carbon_per_token_unshifted", "eq_carbon_per_token",
    "eq_cost_per_token_shifted", "eq_cost_saving_per_token",
    "eq_carbon_saving_per_token",
    "POWER_FORECAST_SHIFT_VARIABLES", "POWER_FORECAST_SHIFT_EQUATIONS",
]
