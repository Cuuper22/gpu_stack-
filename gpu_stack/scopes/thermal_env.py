"""
scopes/thermal_env.py
=====================

Water usage and environmental envelope: evaporation, blowdown, drift,
water-usage rate, WUE, dew-point headroom, condensation margin, and the
ASHRAE-style inlet and humidity inequality constraints.
"""

import sympy as sp

from ..core import Inequality, eq, var
from .cluster import cluster_power_it
from .thermal_package import T_ambient, T_coolant_inlet
from .thermal_facility import heat_to_reject


# ---------------------------------------------------------------------------
# Water usage
# ---------------------------------------------------------------------------

water_latent_heat = var(
    "thermal.water.latent_heat", "h_fg", "J/kg",
    "Latent heat used to evaporate tower water.",
    scope="thermal",
)
water_density = var(
    "thermal.water.density", "rho_wL", "kg/L",
    "Water density expressed in kilograms per liter for WUE conversions.",
    scope="thermal",
)
water_cycles_of_concentration = var(
    "thermal.water.cycles_of_concentration", "N_coc", "dimensionless",
    "Cycles of concentration in the cooling tower.",
    scope="thermal",
)
tower_drift_fraction = var(
    "thermal.water.drift_fraction", "f_drift", "dimensionless",
    "Fractional tower drift loss relative to evaporated water mass.",
    scope="thermal",
)
water_evap_rate = var(
    "thermal.water.evap_rate", "m_evap", "kg/s",
    "Evaporation mass-flow rate needed to reject the site heat load through evaporative cooling.",
    scope="thermal",
)
water_blowdown_rate = var(
    "thermal.water.blowdown_rate", "m_blow", "kg/s",
    "Blowdown mass-flow rate required by cooling-tower chemistry control.",
    scope="thermal",
)
water_drift_rate = var(
    "thermal.water.drift_rate", "m_drift", "kg/s",
    "Drift mass-flow rate from cooling-tower droplets lost to the environment.",
    scope="thermal",
)
water_usage_rate = var(
    "thermal.water.usage_rate", "Wdot_use", "L/s",
    "Total site water usage rate.",
    scope="thermal",
)
wue = var(
    "thermal.water.wue", "WUE", "L/kWh",
    "Water Usage Effectiveness of the site.",
    scope="thermal",
)


# ---------------------------------------------------------------------------
# Environmental envelope: ASHRAE inlet, humidity, dew point
# ---------------------------------------------------------------------------

ashrae_a1_inlet_min = var(
    "thermal.env.ashrae_a1_inlet_min", "T_A1_min", "K",
    "Lower inlet-temperature bound for an ASHRAE A1-style operating window.",
    scope="thermal",
)
ashrae_a1_inlet_max = var(
    "thermal.env.ashrae_a1_inlet_max", "T_A1_max", "K",
    "Upper inlet-temperature bound for an ASHRAE A1-style operating window.",
    scope="thermal",
)
relative_humidity = var(
    "thermal.env.relative_humidity", "RH", "dimensionless",
    "Relative humidity in the IT room or inlet air stream.",
    scope="thermal",
)
relative_humidity_min = var(
    "thermal.env.relative_humidity_min", "RH_min", "dimensionless",
    "Lower relative-humidity limit for safe operation.",
    scope="thermal",
)
relative_humidity_max = var(
    "thermal.env.relative_humidity_max", "RH_max", "dimensionless",
    "Upper relative-humidity limit for safe operation.",
    scope="thermal",
)
dew_point = var(
    "thermal.env.dew_point", "T_dew", "K",
    "Dew-point temperature of the local air stream.",
    scope="thermal",
)
condensation_margin = var(
    "thermal.env.condensation_margin", "dT_cond", "K",
    "Minimum temperature margin between coolant supply and dew point required to avoid condensation.",
    scope="thermal",
)
dew_point_headroom = var(
    "thermal.env.dew_point_headroom", "dT_dew", "K",
    "Difference between coolant supply temperature and dew point.",
    scope="thermal",
)


eq_water_evap_rate = eq(
    "thermal.eq.water_evap_rate",
    water_evap_rate.symbol,
    heat_to_reject.symbol / water_latent_heat.symbol,
    "Evaporation mass-flow rate equals rejected heat divided by latent heat of vaporization.",
)

eq_water_blowdown_rate = eq(
    "thermal.eq.water_blowdown_rate",
    water_blowdown_rate.symbol,
    water_evap_rate.symbol / (water_cycles_of_concentration.symbol - 1),
    "Cooling-tower blowdown follows the usual cycles-of-concentration relation.",
)

eq_water_drift_rate = eq(
    "thermal.eq.water_drift_rate",
    water_drift_rate.symbol,
    tower_drift_fraction.symbol * water_evap_rate.symbol,
    "Tower drift is modeled as a fixed fraction of evaporated water mass.",
)

eq_water_usage_rate = eq(
    "thermal.eq.water_usage_rate",
    water_usage_rate.symbol,
    (water_evap_rate.symbol + water_blowdown_rate.symbol + water_drift_rate.symbol) / water_density.symbol,
    "Total site water usage in liters per second equals total water mass loss divided by water density expressed in kilograms per liter.",
)

eq_wue = eq(
    "thermal.eq.wue",
    wue.symbol,
    water_usage_rate.symbol * sp.Integer(3_600_000) / cluster_power_it.symbol,
    "WUE in liters per kWh equals liters per second divided by watts, with the standard kWh conversion factor applied.",
)

eq_dew_point_headroom = eq(
    "thermal.eq.dew_point_headroom",
    dew_point_headroom.symbol,
    T_coolant_inlet.symbol - dew_point.symbol,
    "Dew-point headroom is coolant supply temperature minus dew point.",
)

ineq_ashrae_a1_low = Inequality(
    "thermal.ineq.ashrae_a1_low",
    T_ambient.symbol,
    ashrae_a1_inlet_min.symbol,
    ">=",
    "Ambient inlet temperature must stay above the lower ASHRAE A1 bound.",
)
ineq_ashrae_a1_high = Inequality(
    "thermal.ineq.ashrae_a1_high",
    T_ambient.symbol,
    ashrae_a1_inlet_max.symbol,
    "<=",
    "Ambient inlet temperature must stay below the upper ASHRAE A1 bound.",
)
ineq_relative_humidity_low = Inequality(
    "thermal.ineq.relative_humidity_low",
    relative_humidity.symbol,
    relative_humidity_min.symbol,
    ">=",
    "Relative humidity must stay above the lower safe-operating bound.",
)
ineq_relative_humidity_high = Inequality(
    "thermal.ineq.relative_humidity_high",
    relative_humidity.symbol,
    relative_humidity_max.symbol,
    "<=",
    "Relative humidity must stay below the upper safe-operating bound.",
)
ineq_condensation_margin = Inequality(
    "thermal.ineq.condensation_margin",
    dew_point_headroom.symbol,
    condensation_margin.symbol,
    ">=",
    "Coolant supply temperature must exceed dew point by at least the configured condensation margin.",
)


THERMAL_ENV_VARIABLES = (
    water_latent_heat,
    water_density,
    water_cycles_of_concentration,
    tower_drift_fraction,
    water_evap_rate,
    water_blowdown_rate,
    water_drift_rate,
    water_usage_rate,
    wue,
    ashrae_a1_inlet_min,
    ashrae_a1_inlet_max,
    relative_humidity,
    relative_humidity_min,
    relative_humidity_max,
    dew_point,
    condensation_margin,
    dew_point_headroom,
)

THERMAL_ENV_EQUATIONS = (
    eq_water_evap_rate,
    eq_water_blowdown_rate,
    eq_water_drift_rate,
    eq_water_usage_rate,
    eq_wue,
    eq_dew_point_headroom,
    ineq_ashrae_a1_low,
    ineq_ashrae_a1_high,
    ineq_relative_humidity_low,
    ineq_relative_humidity_high,
    ineq_condensation_margin,
)


__all__ = [
    "water_latent_heat",
    "water_density",
    "water_cycles_of_concentration",
    "tower_drift_fraction",
    "water_evap_rate",
    "water_blowdown_rate",
    "water_drift_rate",
    "water_usage_rate",
    "wue",
    "ashrae_a1_inlet_min",
    "ashrae_a1_inlet_max",
    "relative_humidity",
    "relative_humidity_min",
    "relative_humidity_max",
    "dew_point",
    "condensation_margin",
    "dew_point_headroom",
    "eq_water_evap_rate",
    "eq_water_blowdown_rate",
    "eq_water_drift_rate",
    "eq_water_usage_rate",
    "eq_wue",
    "eq_dew_point_headroom",
    "ineq_ashrae_a1_low",
    "ineq_ashrae_a1_high",
    "ineq_relative_humidity_low",
    "ineq_relative_humidity_high",
    "ineq_condensation_margin",
    "THERMAL_ENV_VARIABLES",
    "THERMAL_ENV_EQUATIONS",
]
