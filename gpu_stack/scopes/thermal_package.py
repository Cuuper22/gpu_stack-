"""
scopes/thermal_package.py
=========================

Package-level thermal path: die-attach, TIM, spreader, cold plate, and fluid
film resistances, case and junction temperatures, radiation, required heat
removal, heat-removal capacity, and thermal headroom for one package.
"""

import sympy as sp

from ..constants import STEFAN_BOLTZMANN
from ..core import Reference, eq, var
from ..core.units import KELVIN, METER, WATT
from .gpu import p_gpu_total


DIMENSIONLESS = sp.Integer(1)
THERMAL_RESISTANCE = KELVIN / WATT

THERMAL_PACKAGE_REF = Reference(
    "Package thermal path uses lumped series thermal resistances from "
    "junction to cold plate and a steady-state heat balance against package "
    "power and radiation.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Package thermal path, per GPU
# ---------------------------------------------------------------------------

theta_die_attach = var(
    "thermal.path.theta_die_attach", "theta_die", "K/W",
    "Die-attach and local silicon-to-lid thermal resistance.",
    scope="thermal",
    sp_units=THERMAL_RESISTANCE,
    references=[THERMAL_PACKAGE_REF],
)
theta_tim = var(
    "thermal.path.theta_tim", "theta_tim", "K/W",
    "Thermal interface material resistance.",
    scope="thermal",
    sp_units=THERMAL_RESISTANCE,
    references=[THERMAL_PACKAGE_REF],
)
theta_spreader = var(
    "thermal.path.theta_spreader", "theta_spr", "K/W",
    "Heat-spreader and lid thermal resistance.",
    scope="thermal",
    sp_units=THERMAL_RESISTANCE,
    references=[THERMAL_PACKAGE_REF],
)
theta_coldplate = var(
    "thermal.path.theta_coldplate", "theta_cp", "K/W",
    "Cold-plate conduction resistance.",
    scope="thermal",
    sp_units=THERMAL_RESISTANCE,
    references=[THERMAL_PACKAGE_REF],
)
theta_fluid_film = var(
    "thermal.path.theta_fluid_film", "theta_ff", "K/W",
    "Fluid-side film resistance from the cold plate into the coolant stream.",
    scope="thermal",
    sp_units=THERMAL_RESISTANCE,
    references=[THERMAL_PACKAGE_REF],
)
theta_jc = var(
    "thermal.theta_jc", "theta_jc", "K/W",
    "Junction-to-case thermal resistance of the package path above the cold plate.",
    scope="thermal",
    sp_units=THERMAL_RESISTANCE,
    references=[THERMAL_PACKAGE_REF],
)
theta_ca = var(
    "thermal.theta_ca", "theta_ca", "K/W",
    "Case-to-coolant thermal resistance through the cold plate and fluid film.",
    scope="thermal",
    sp_units=THERMAL_RESISTANCE,
    references=[THERMAL_PACKAGE_REF],
)
theta_ja = var(
    "thermal.theta_ja", "theta_ja", "K/W",
    "Overall junction-to-coolant thermal resistance.",
    scope="thermal",
    sp_units=THERMAL_RESISTANCE,
    references=[THERMAL_PACKAGE_REF],
)
T_case = var(
    "thermal.t_case", "T_case", "K",
    "Case or lid temperature of the package.",
    scope="thermal",
    sp_units=KELVIN,
    references=[THERMAL_PACKAGE_REF],
)
T_junction = var(
    "thermal.t_junction", "T_j", "K",
    "Die junction temperature.",
    scope="thermal",
    sp_units=KELVIN,
    references=[THERMAL_PACKAGE_REF],
)
T_coolant_inlet = var(
    "thermal.coolant.t_inlet", "T_c_in", "K",
    "Coolant supply temperature entering the cold plate.",
    scope="thermal",
    sp_units=KELVIN,
    references=[THERMAL_PACKAGE_REF],
)
T_ambient = var(
    "thermal.t_ambient", "T_amb", "K",
    "Server inlet or surrounding ambient dry-bulb temperature.",
    scope="thermal",
    sp_units=KELVIN,
    references=[THERMAL_PACKAGE_REF],
)
Q_removed = var(
    "thermal.q_removed", "Q_rem", "W",
    "Heat-removal capacity of the cold plate coolant path for one package.",
    scope="thermal",
    sp_units=WATT,
    references=[THERMAL_PACKAGE_REF],
)
Q_required = var(
    "thermal.q_required", "Q_req", "W",
    "Non-radiative heat that the coolant path must remove from one package.",
    scope="thermal",
    sp_units=WATT,
    references=[THERMAL_PACKAGE_REF],
)
thermal_headroom = var(
    "thermal.headroom", "Q_margin", "W",
    "Cold-plate heat-removal margin after subtracting required heat removal from available heat-removal capacity.",
    scope="thermal",
    sp_units=WATT,
    references=[THERMAL_PACKAGE_REF],
)
A_rad = var(
    "thermal.rad.area", "A_rad", "m^2",
    "Radiating surface area of the package or nearby heat spreader.",
    scope="thermal",
    sp_units=METER**2,
    references=[THERMAL_PACKAGE_REF],
)
eps_rad = var(
    "thermal.rad.emissivity", "eps_r", "dimensionless",
    "Effective emissivity of the radiating package surface.",
    scope="thermal",
    sp_units=DIMENSIONLESS,
    references=[THERMAL_PACKAGE_REF],
)
P_rad = var(
    "thermal.rad.power", "P_rad", "W",
    "Radiative heat-transfer power from the package to its surroundings.",
    scope="thermal",
    sp_units=WATT,
    references=[THERMAL_PACKAGE_REF],
)


eq_theta_jc = eq(
    "thermal.eq.theta_jc_components",
    theta_jc.symbol,
    theta_die_attach.symbol + theta_tim.symbol + theta_spreader.symbol,
    "Junction-to-case resistance is the sum of die-attach, TIM, and spreader resistances.",
    references=[THERMAL_PACKAGE_REF],
    check_units=True,
)

eq_theta_ca = eq(
    "thermal.eq.theta_ca_components",
    theta_ca.symbol,
    theta_coldplate.symbol + theta_fluid_film.symbol,
    "Case-to-coolant resistance is the sum of cold-plate and fluid-film resistances.",
    references=[THERMAL_PACKAGE_REF],
    check_units=True,
)

eq_theta_sum = eq(
    "thermal.eq.theta_sum",
    theta_ja.symbol,
    theta_jc.symbol + theta_ca.symbol,
    "Overall junction-to-coolant thermal resistance is the series sum of the package and cold-plate path.",
    references=[THERMAL_PACKAGE_REF],
    check_units=True,
)

eq_t_case = eq(
    "thermal.eq.case_temp",
    T_case.symbol,
    T_coolant_inlet.symbol + theta_ca.symbol * p_gpu_total.symbol,
    "Case temperature rises above coolant inlet temperature by package power times the case-to-coolant resistance.",
    references=[THERMAL_PACKAGE_REF],
    check_units=True,
)

eq_junction_temp = eq(
    "thermal.eq.junction_temp",
    T_junction.symbol,
    T_case.symbol + theta_jc.symbol * p_gpu_total.symbol,
    "Junction temperature rises above case temperature by package power times the junction-to-case resistance.",
    references=[THERMAL_PACKAGE_REF],
    check_units=True,
)

eq_stefan_boltzmann = eq(
    "thermal.eq.stefan_boltzmann",
    P_rad.symbol,
    eps_rad.symbol * STEFAN_BOLTZMANN.symbol * A_rad.symbol * (T_junction.symbol ** 4 - T_ambient.symbol ** 4),
    "Radiative heat transfer follows the Stefan-Boltzmann law.",
    references=[THERMAL_PACKAGE_REF],
    check_units=True,
)

eq_q_required = eq(
    "thermal.eq.q_required",
    Q_required.symbol,
    p_gpu_total.symbol - P_rad.symbol,
    "Coolant must remove package power minus the small portion rejected by radiation.",
    references=[THERMAL_PACKAGE_REF],
    check_units=True,
)

eq_thermal_headroom = eq(
    "thermal.eq.thermal_headroom",
    thermal_headroom.symbol,
    Q_removed.symbol - Q_required.symbol,
    "Thermal headroom is positive when the coolant path can remove more heat than the package requires.",
    references=[THERMAL_PACKAGE_REF],
    check_units=True,
)


THERMAL_PACKAGE_VARIABLES = (
    theta_die_attach,
    theta_tim,
    theta_spreader,
    theta_coldplate,
    theta_fluid_film,
    theta_jc,
    theta_ca,
    theta_ja,
    T_case,
    T_junction,
    T_coolant_inlet,
    T_ambient,
    Q_removed,
    Q_required,
    thermal_headroom,
    A_rad,
    eps_rad,
    P_rad,
)

THERMAL_PACKAGE_EQUATIONS = (
    eq_theta_jc,
    eq_theta_ca,
    eq_theta_sum,
    eq_t_case,
    eq_junction_temp,
    eq_stefan_boltzmann,
    eq_q_required,
    eq_thermal_headroom,
)


__all__ = [
    "theta_die_attach",
    "theta_tim",
    "theta_spreader",
    "theta_coldplate",
    "theta_fluid_film",
    "theta_jc",
    "theta_ca",
    "theta_ja",
    "T_case",
    "T_junction",
    "T_coolant_inlet",
    "T_ambient",
    "Q_removed",
    "Q_required",
    "thermal_headroom",
    "A_rad",
    "eps_rad",
    "P_rad",
    "eq_theta_jc",
    "eq_theta_ca",
    "eq_theta_sum",
    "eq_t_case",
    "eq_junction_temp",
    "eq_stefan_boltzmann",
    "eq_q_required",
    "eq_thermal_headroom",
    "THERMAL_PACKAGE_VARIABLES",
    "THERMAL_PACKAGE_EQUATIONS",
]
