"""
scopes/thermal_liquid.py
========================

The liquid-cooling loop between the cold plates and the facility plant.
Sensible heat sets the physics: removed heat equals mass flow times
specific heat times the coolant temperature rise, so the inlet temperature,
outlet temperature, and flow rate are one constraint, not three free
choices. Volumetric flow follows from mass flow and density; pushing that
flow through the loop pressure drop at finite pump efficiency costs pump
power per GPU and per site, and the coolant distribution units (CDUs) add
their own draw. The average coolant temperature anchors the package-scope
temperature stack; the removed heat is what the facility must reject.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import JOULE, KELVIN, KILOGRAM, METER, PASCAL, SECOND, WATT
from .cluster import cluster_n_gpus
from .thermal_package import Q_removed, T_coolant_inlet


DIMENSIONLESS = sp.Integer(1)
MASS_FLOW = KILOGRAM / SECOND
SPECIFIC_HEAT = JOULE / (KILOGRAM * KELVIN)
DENSITY = KILOGRAM / METER**3
VOLUMETRIC_FLOW = METER**3 / SECOND

LIQUID_COOLING_REF = Reference(
    "Liquid-cooling loop uses the sensible-heat relation m-dot c_p delta-T, "
    "volumetric flow from density, pump hydraulic power, and CDU auxiliary "
    "power as a fraction of liquid heat removed.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Coolant flow and outlet conditions, per GPU
# ---------------------------------------------------------------------------

T_coolant_outlet = var(
    "thermal.coolant.t_outlet", "T_c_out", "K",
    "Coolant return temperature leaving the cold plate.",
    scope="thermal",
    sp_units=KELVIN,
    references=[LIQUID_COOLING_REF],
)
T_coolant_avg = var(
    "thermal.coolant.t_avg", "T_c_avg", "K",
    "Average coolant temperature through the cold plate.",
    scope="thermal",
    sp_units=KELVIN,
    references=[LIQUID_COOLING_REF],
)
delta_T_coolant = var(
    "thermal.coolant.delta_T", "dT_c", "K",
    "Coolant temperature rise across one package cold plate.",
    scope="thermal",
    sp_units=KELVIN,
    references=[LIQUID_COOLING_REF],
)
m_dot_coolant = var(
    "thermal.coolant.m_dot", "m_dot", "kg/s",
    "Coolant mass-flow rate through one package cold plate.",
    scope="thermal",
    sp_units=MASS_FLOW,
    references=[LIQUID_COOLING_REF],
)
c_p_coolant = var(
    "thermal.coolant.c_p", "c_p", "J/(kg*K)",
    "Coolant specific heat capacity.",
    scope="thermal",
    sp_units=SPECIFIC_HEAT,
    references=[LIQUID_COOLING_REF],
)
coolant_density = var(
    "thermal.coolant.density", "rho_c", "kg/m^3",
    "Coolant density for flow and pump-power calculations.",
    scope="thermal",
    sp_units=DENSITY,
    references=[LIQUID_COOLING_REF],
)
volumetric_flow_coolant = var(
    "thermal.coolant.vol_flow", "Qdot_c", "m^3/s",
    "Coolant volumetric flow through one package cold plate.",
    scope="thermal",
    sp_units=VOLUMETRIC_FLOW,
    references=[LIQUID_COOLING_REF],
)


eq_t_coolant_outlet = eq(
    "thermal.eq.coolant_outlet_temp",
    T_coolant_outlet.symbol,
    T_coolant_inlet.symbol + delta_T_coolant.symbol,
    "Coolant outlet temperature equals inlet temperature plus coolant temperature rise.",
    references=[LIQUID_COOLING_REF],
    check_units=True,
)

eq_t_coolant_avg = eq(
    "thermal.eq.coolant_avg_temp",
    T_coolant_avg.symbol,
    T_coolant_inlet.symbol + delta_T_coolant.symbol / 2,
    "Average coolant temperature through the cold plate is the midpoint between inlet and outlet under a linear-rise approximation.",
    references=[LIQUID_COOLING_REF],
    check_units=True,
)

eq_volumetric_flow_coolant = eq(
    "thermal.eq.coolant_vol_flow",
    volumetric_flow_coolant.symbol,
    m_dot_coolant.symbol / coolant_density.symbol,
    "Coolant volumetric flow equals mass-flow rate divided by coolant density.",
    references=[LIQUID_COOLING_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Heat-removal capacity sensible-heat relation
# ---------------------------------------------------------------------------

eq_heat_removed = eq(
    "thermal.eq.q_removed",
    Q_removed.symbol,
    m_dot_coolant.symbol * c_p_coolant.symbol * delta_T_coolant.symbol,
    "Cold-plate heat-removal capacity follows the sensible-heat relation m-dot times c_p times delta-T.",
    references=[LIQUID_COOLING_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Pump power and CDU power
# ---------------------------------------------------------------------------

delta_p_coolant_loop = var(
    "thermal.facility.loop_delta_p", "dP_loop", "Pa",
    "Pressure drop across the package liquid-cooling loop served by the pump.",
    scope="thermal",
    sp_units=PASCAL,
    references=[LIQUID_COOLING_REF],
)
pump_efficiency = var(
    "thermal.facility.pump_efficiency", "eta_pump", "dimensionless",
    "Hydraulic-to-electrical efficiency of the coolant pump.",
    scope="thermal",
    sp_units=DIMENSIONLESS,
    references=[LIQUID_COOLING_REF],
)
pump_power_per_gpu = var(
    "thermal.facility.pump_power_per_gpu", "P_pump_g", "W",
    "Pump power attributable to one package cold-plate loop.",
    scope="thermal",
    sp_units=WATT,
    references=[LIQUID_COOLING_REF],
)
pump_power_site = var(
    "thermal.facility.pump_power_site", "P_pump_site", "W",
    "Aggregate site pump power allocated to GPU liquid-cooling loops.",
    scope="thermal",
    sp_units=WATT,
    references=[LIQUID_COOLING_REF],
)
liquid_heat_removed_site = var(
    "thermal.facility.liquid_heat_removed_site", "Q_liq_site", "W",
    "Aggregate liquid-side heat-removal capacity across all GPU cold plates.",
    scope="thermal",
    sp_units=WATT,
    references=[LIQUID_COOLING_REF],
)
cdu_aux_fraction = var(
    "thermal.facility.cdu_aux_fraction", "f_cdu_aux", "dimensionless",
    "CDU auxiliary electric-power fraction relative to liquid heat removed at the site.",
    scope="thermal",
    sp_units=DIMENSIONLESS,
    references=[LIQUID_COOLING_REF],
)
cdu_power = var(
    "thermal.facility.cdu_power", "P_cdu", "W",
    "Coolant distribution unit power.",
    scope="thermal",
    sp_units=WATT,
    references=[LIQUID_COOLING_REF],
)


eq_pump_power_per_gpu = eq(
    "thermal.eq.pump_power_per_gpu",
    pump_power_per_gpu.symbol,
    volumetric_flow_coolant.symbol * delta_p_coolant_loop.symbol / pump_efficiency.symbol,
    "Per-package pump power equals volumetric flow times pressure drop divided by pump efficiency.",
    references=[LIQUID_COOLING_REF],
    check_units=True,
)

eq_pump_power_site = eq(
    "thermal.eq.pump_power_site",
    pump_power_site.symbol,
    cluster_n_gpus.symbol * pump_power_per_gpu.symbol,
    "Site pump power allocated to the GPU loops equals GPU count times per-package pump power.",
    references=[LIQUID_COOLING_REF],
    check_units=True,
)

eq_liquid_heat_removed_site = eq(
    "thermal.eq.liquid_heat_removed_site",
    liquid_heat_removed_site.symbol,
    cluster_n_gpus.symbol * Q_removed.symbol,
    "Site liquid heat-removal capacity equals GPU count times per-package cold-plate heat-removal capacity.",
    references=[LIQUID_COOLING_REF],
    check_units=True,
)

eq_cdu_power = eq(
    "thermal.eq.cdu_power",
    cdu_power.symbol,
    cdu_aux_fraction.symbol * liquid_heat_removed_site.symbol,
    "CDU power is modeled as an auxiliary electric-power fraction of site liquid heat removed.",
    references=[LIQUID_COOLING_REF],
    check_units=True,
)


THERMAL_LIQUID_VARIABLES = (
    T_coolant_outlet,
    T_coolant_avg,
    m_dot_coolant,
    c_p_coolant,
    delta_T_coolant,
    coolant_density,
    volumetric_flow_coolant,
    delta_p_coolant_loop,
    pump_efficiency,
    pump_power_per_gpu,
    pump_power_site,
    liquid_heat_removed_site,
    cdu_aux_fraction,
    cdu_power,
)

THERMAL_LIQUID_EQUATIONS = (
    eq_t_coolant_outlet,
    eq_t_coolant_avg,
    eq_volumetric_flow_coolant,
    eq_heat_removed,
    eq_pump_power_per_gpu,
    eq_pump_power_site,
    eq_liquid_heat_removed_site,
    eq_cdu_power,
)


__all__ = [
    "T_coolant_outlet",
    "T_coolant_avg",
    "delta_T_coolant",
    "m_dot_coolant",
    "c_p_coolant",
    "coolant_density",
    "volumetric_flow_coolant",
    "delta_p_coolant_loop",
    "pump_efficiency",
    "pump_power_per_gpu",
    "pump_power_site",
    "liquid_heat_removed_site",
    "cdu_aux_fraction",
    "cdu_power",
    "eq_t_coolant_outlet",
    "eq_t_coolant_avg",
    "eq_volumetric_flow_coolant",
    "eq_heat_removed",
    "eq_pump_power_per_gpu",
    "eq_pump_power_site",
    "eq_liquid_heat_removed_site",
    "eq_cdu_power",
    "THERMAL_LIQUID_VARIABLES",
    "THERMAL_LIQUID_EQUATIONS",
]
