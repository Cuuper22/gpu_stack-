"""
scopes/thermal_liquid.py
========================

Liquid-cooling loop: coolant inlet and outlet temperatures, average coolant
temperature, volumetric flow, required non-radiative heat removal, pump
power per GPU and per site, and CDU power.
"""

from ..core import eq, var
from .cluster import cluster_n_gpus
from .thermal_package import Q_removed, T_coolant_inlet


# ---------------------------------------------------------------------------
# Coolant flow and outlet conditions, per GPU
# ---------------------------------------------------------------------------

T_coolant_outlet = var(
    "thermal.coolant.t_outlet", "T_c_out", "K",
    "Coolant return temperature leaving the cold plate.",
    scope="thermal",
)
T_coolant_avg = var(
    "thermal.coolant.t_avg", "T_c_avg", "K",
    "Average coolant temperature through the cold plate.",
    scope="thermal",
)
delta_T_coolant = var(
    "thermal.coolant.delta_T", "dT_c", "K",
    "Coolant temperature rise across one package cold plate.",
    scope="thermal",
)
m_dot_coolant = var(
    "thermal.coolant.m_dot", "m_dot", "kg/s",
    "Coolant mass-flow rate through one package cold plate.",
    scope="thermal",
)
c_p_coolant = var(
    "thermal.coolant.c_p", "c_p", "J/(kg*K)",
    "Coolant specific heat capacity.",
    scope="thermal",
)
coolant_density = var(
    "thermal.coolant.density", "rho_c", "kg/m^3",
    "Coolant density for flow and pump-power calculations.",
    scope="thermal",
)
volumetric_flow_coolant = var(
    "thermal.coolant.vol_flow", "Qdot_c", "m^3/s",
    "Coolant volumetric flow through one package cold plate.",
    scope="thermal",
)


eq_t_coolant_outlet = eq(
    "thermal.eq.coolant_outlet_temp",
    T_coolant_outlet.symbol,
    T_coolant_inlet.symbol + delta_T_coolant.symbol,
    "Coolant outlet temperature equals inlet temperature plus coolant temperature rise.",
)

eq_t_coolant_avg = eq(
    "thermal.eq.coolant_avg_temp",
    T_coolant_avg.symbol,
    T_coolant_inlet.symbol + delta_T_coolant.symbol / 2,
    "Average coolant temperature through the cold plate is the midpoint between inlet and outlet under a linear-rise approximation.",
)

eq_volumetric_flow_coolant = eq(
    "thermal.eq.coolant_vol_flow",
    volumetric_flow_coolant.symbol,
    m_dot_coolant.symbol / coolant_density.symbol,
    "Coolant volumetric flow equals mass-flow rate divided by coolant density.",
)


# ---------------------------------------------------------------------------
# Heat-removal capacity sensible-heat relation
# ---------------------------------------------------------------------------

eq_heat_removed = eq(
    "thermal.eq.q_removed",
    Q_removed.symbol,
    m_dot_coolant.symbol * c_p_coolant.symbol * delta_T_coolant.symbol,
    "Cold-plate heat-removal capacity follows the sensible-heat relation m-dot times c_p times delta-T.",
)


# ---------------------------------------------------------------------------
# Pump power and CDU power
# ---------------------------------------------------------------------------

delta_p_coolant_loop = var(
    "thermal.facility.loop_delta_p", "dP_loop", "Pa",
    "Pressure drop across the package liquid-cooling loop served by the pump.",
    scope="thermal",
)
pump_efficiency = var(
    "thermal.facility.pump_efficiency", "eta_pump", "dimensionless",
    "Hydraulic-to-electrical efficiency of the coolant pump.",
    scope="thermal",
)
pump_power_per_gpu = var(
    "thermal.facility.pump_power_per_gpu", "P_pump_g", "W",
    "Pump power attributable to one package cold-plate loop.",
    scope="thermal",
)
pump_power_site = var(
    "thermal.facility.pump_power_site", "P_pump_site", "W",
    "Aggregate site pump power allocated to GPU liquid-cooling loops.",
    scope="thermal",
)
cdu_power = var(
    "thermal.facility.cdu_power", "P_cdu", "W",
    "Coolant distribution unit power.",
    scope="thermal",
)


eq_pump_power_per_gpu = eq(
    "thermal.eq.pump_power_per_gpu",
    pump_power_per_gpu.symbol,
    volumetric_flow_coolant.symbol * delta_p_coolant_loop.symbol / pump_efficiency.symbol,
    "Per-package pump power equals volumetric flow times pressure drop divided by pump efficiency.",
)

eq_pump_power_site = eq(
    "thermal.eq.pump_power_site",
    pump_power_site.symbol,
    cluster_n_gpus.symbol * pump_power_per_gpu.symbol,
    "Site pump power allocated to the GPU loops equals GPU count times per-package pump power.",
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
    cdu_power,
)

THERMAL_LIQUID_EQUATIONS = (
    eq_t_coolant_outlet,
    eq_t_coolant_avg,
    eq_volumetric_flow_coolant,
    eq_heat_removed,
    eq_pump_power_per_gpu,
    eq_pump_power_site,
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
    "cdu_power",
    "eq_t_coolant_outlet",
    "eq_t_coolant_avg",
    "eq_volumetric_flow_coolant",
    "eq_heat_removed",
    "eq_pump_power_per_gpu",
    "eq_pump_power_site",
    "THERMAL_LIQUID_VARIABLES",
    "THERMAL_LIQUID_EQUATIONS",
]
