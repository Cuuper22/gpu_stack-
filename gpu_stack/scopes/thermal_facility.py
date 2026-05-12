"""
scopes/thermal_facility.py
==========================

Facility cooling plant and site power: fan power, chiller load and power,
cooling-tower auxiliary power, heat reuse, wet-bulb-driven free-cooling
piecewise logic, humidity-control power, total cooling power, PUE
definition, and the component sum that gives DC total power.
"""

import sympy as sp

from ..core import PiecewiseEquation, Reference, eq, var
from ..core.units import KELVIN, METER, PASCAL, SECOND, WATT
from .cluster import cluster_power_it, n_racks_cluster
from .thermal_liquid import cdu_power, pump_power_site


DIMENSIONLESS = sp.Integer(1)
VOLUMETRIC_FLOW = METER**3 / SECOND

FACILITY_THERMAL_REF = Reference(
    "Facility thermal plant uses steady-state heat rejection, fan hydraulic "
    "power, chiller COP, tower auxiliary fraction, and a component sum for "
    "cooling and site power overhead.",
    kind="model",
)

FACILITY_SIZING_REF = Reference(
    "Facility sizing quantities expose floor area, electrical design capacity, "
    "and cooling design capacity as capex-facing root inputs.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Fans
# ---------------------------------------------------------------------------

air_flow_rate = var(
    "thermal.facility.air_flow_rate", "Vdot_air", "m^3/s",
    "Airflow rate through fans used for room air management or dry coolers.",
    scope="thermal",
    sp_units=VOLUMETRIC_FLOW,
    references=[FACILITY_THERMAL_REF],
)
fan_pressure_rise = var(
    "thermal.facility.fan_pressure_rise", "dP_fan", "Pa",
    "Pressure rise developed by the fan system.",
    scope="thermal",
    sp_units=PASCAL,
    references=[FACILITY_THERMAL_REF],
)
fan_efficiency = var(
    "thermal.facility.fan_efficiency", "eta_fan", "dimensionless",
    "Electrical-to-airflow efficiency of the fan system.",
    scope="thermal",
    sp_units=DIMENSIONLESS,
    references=[FACILITY_THERMAL_REF],
)
fan_power = var(
    "thermal.facility.fan_power", "P_fan", "W",
    "Aggregate fan power.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)


# ---------------------------------------------------------------------------
# Site heat load, reuse, and heat to reject
# ---------------------------------------------------------------------------

cluster_heat_load = var(
    "thermal.facility.heat_load", "Q_site", "W",
    "Site heat load from IT equipment. In steady state this is the same as IT electrical power.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)
heat_reuse_fraction = var(
    "thermal.facility.heat_reuse_fraction", "f_reuse", "dimensionless",
    "Fraction of site heat load diverted to useful heat reuse instead of the cooling tower or dry cooler.",
    scope="thermal",
    sp_units=DIMENSIONLESS,
    references=[FACILITY_THERMAL_REF],
)
recovered_heat_power = var(
    "thermal.facility.recovered_heat_power", "Q_reuse", "W",
    "Heat power recovered for district heating or other reuse paths.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)
heat_to_reject = var(
    "thermal.facility.heat_to_reject", "Q_reject", "W",
    "Heat that still must be rejected to the environment after any reuse.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)


# ---------------------------------------------------------------------------
# Free cooling, chiller, and tower
# ---------------------------------------------------------------------------

ambient_wet_bulb = var(
    "thermal.facility.wet_bulb", "T_wb", "K",
    "Ambient wet-bulb temperature relevant for evaporative cooling and tower operation.",
    scope="thermal",
    sp_units=KELVIN,
    references=[FACILITY_THERMAL_REF],
)
free_cooling_threshold = var(
    "thermal.facility.free_cooling_threshold", "T_fc", "K",
    "Wet-bulb threshold below which the site can satisfy the cooling load without active chilling.",
    scope="thermal",
    sp_units=KELVIN,
    references=[FACILITY_THERMAL_REF],
)
free_cooling_fraction = var(
    "thermal.facility.free_cooling_fraction", "f_fc", "dimensionless",
    "Fraction of the facility heat-rejection load that can be handled by free cooling rather than an active chiller.",
    scope="thermal",
    sp_units=DIMENSIONLESS,
    references=[FACILITY_THERMAL_REF],
)
chiller_cop = var(
    "thermal.facility.chiller_cop", "COP_ch", "dimensionless",
    "Coefficient of performance of the active chiller plant.",
    scope="thermal",
    sp_units=DIMENSIONLESS,
    references=[FACILITY_THERMAL_REF],
)
chiller_heat_load = var(
    "thermal.facility.chiller_heat_load", "Q_ch", "W",
    "Heat load that must still be lifted by the active chiller plant.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)
chiller_power = var(
    "thermal.facility.chiller_power", "P_ch", "W",
    "Electrical power of the active chiller plant.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)
cooling_tower_aux_fraction = var(
    "thermal.facility.tower_aux_fraction", "f_twr_aux", "dimensionless",
    "Auxiliary electric-power fraction for the cooling tower or dry-cooler path, excluding chiller power.",
    scope="thermal",
    sp_units=DIMENSIONLESS,
    references=[FACILITY_THERMAL_REF],
)
cooling_tower_power = var(
    "thermal.facility.tower_power", "P_twr", "W",
    "Cooling-tower or dry-cooler auxiliary power.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)
humidity_control_power = var(
    "thermal.facility.humidity_control_power", "P_hum", "W",
    "Power used for humidity control and condensation management.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)
p_cooling_total = var(
    "thermal.facility.cooling_power", "P_cool", "W",
    "Total facility cooling power.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)


# ---------------------------------------------------------------------------
# Non-cooling facility overheads and DC total power / PUE
# ---------------------------------------------------------------------------

ups_loss_fraction = var(
    "thermal.facility.ups_loss_fraction", "f_ups_loss", "dimensionless",
    "UPS conversion and battery-system loss fraction relative to IT power.",
    scope="thermal",
    sp_units=DIMENSIONLESS,
    references=[FACILITY_THERMAL_REF],
)
transformer_loss_fraction = var(
    "thermal.facility.transformer_loss_fraction", "f_xfrm_loss", "dimensionless",
    "Transformer and power-distribution loss fraction relative to IT power.",
    scope="thermal",
    sp_units=DIMENSIONLESS,
    references=[FACILITY_THERMAL_REF],
)
lighting_power_per_rack = var(
    "thermal.facility.lighting_power_per_rack", "P_light_rack", "W/rack",
    "Lighting and small non-IT facility electrical load allocated per rack.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)
facility_misc_fraction = var(
    "thermal.facility.misc_fraction", "f_misc_fac", "dimensionless",
    "Miscellaneous facility electrical-load fraction relative to IT power.",
    scope="thermal",
    sp_units=DIMENSIONLESS,
    references=[FACILITY_THERMAL_REF],
)
p_ups_loss = var(
    "thermal.facility.ups_loss", "P_ups", "W",
    "UPS conversion and battery-system losses.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)
p_transformer_loss = var(
    "thermal.facility.transformer_loss", "P_xfrm", "W",
    "Transformer and power-distribution losses.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)
p_lighting = var(
    "thermal.facility.lighting", "P_light", "W",
    "Lighting and small non-IT facility electrical load.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)
p_facility_misc = var(
    "thermal.facility.misc", "P_misc_fac", "W",
    "Other facility electrical load not captured elsewhere.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)
dc_total_power = var(
    "thermal.dc.total_power", "P_dc", "W",
    "Total site electrical load including IT, cooling, and other facility overheads.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_THERMAL_REF],
)
pue = var(
    "thermal.dc.pue", "PUE", "dimensionless",
    "Power Usage Effectiveness, defined as total site power divided by IT load.",
    scope="thermal",
    sp_units=DIMENSIONLESS,
    references=[FACILITY_THERMAL_REF],
)


# ---------------------------------------------------------------------------
# Facility sizing quantities used by capex
# ---------------------------------------------------------------------------

facility_floor_area = var(
    "thermal.facility.floor_area", "A_fac", "m^2",
    "Gross facility floor area allocated to the site.",
    scope="thermal",
    sp_units=METER**2,
    references=[FACILITY_SIZING_REF],
)
facility_power_design_capacity = var(
    "thermal.facility.power_design_capacity", "P_fac_design", "W",
    "Nameplate electrical design capacity for the facility power infrastructure.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_SIZING_REF],
)
facility_cooling_design_capacity = var(
    "thermal.facility.cooling_design_capacity", "Q_cool_design", "W",
    "Nameplate thermal design capacity for the facility cooling infrastructure.",
    scope="thermal",
    sp_units=WATT,
    references=[FACILITY_SIZING_REF],
)


eq_fan_power = eq(
    "thermal.eq.fan_power",
    fan_power.symbol,
    air_flow_rate.symbol * fan_pressure_rise.symbol / fan_efficiency.symbol,
    "Fan power equals volumetric airflow times pressure rise divided by fan efficiency.",
    references=[FACILITY_THERMAL_REF],
    check_units=True,
)

eq_cluster_heat_load = eq(
    "thermal.eq.cluster_heat_load",
    cluster_heat_load.symbol,
    cluster_power_it.symbol,
    "In steady state, essentially all IT electrical power appears as heat that must be managed by the facility.",
    references=[FACILITY_THERMAL_REF],
)

eq_recovered_heat_power = eq(
    "thermal.eq.recovered_heat_power",
    recovered_heat_power.symbol,
    heat_reuse_fraction.symbol * cluster_heat_load.symbol,
    "Recovered heat equals the reusable fraction of the site heat load.",
    references=[FACILITY_THERMAL_REF],
    check_units=True,
)

eq_heat_to_reject = eq(
    "thermal.eq.heat_to_reject",
    heat_to_reject.symbol,
    cluster_heat_load.symbol - recovered_heat_power.symbol,
    "Heat to reject equals total site heat load minus recovered heat.",
    references=[FACILITY_THERMAL_REF],
    check_units=True,
)

eq_free_cooling_fraction = PiecewiseEquation(
    "thermal.eq.free_cooling_fraction",
    free_cooling_fraction.symbol,
    [
        (1, ambient_wet_bulb.symbol <= free_cooling_threshold.symbol),
        (0, True),
    ],
    "Free cooling is available when ambient wet-bulb temperature is at or below the configured threshold.",
    references=[FACILITY_THERMAL_REF],
)

eq_chiller_heat_load = eq(
    "thermal.eq.chiller_heat_load",
    chiller_heat_load.symbol,
    (1 - free_cooling_fraction.symbol) * heat_to_reject.symbol,
    "Active chiller heat load is the residual heat load not covered by free cooling.",
    references=[FACILITY_THERMAL_REF],
    check_units=True,
)

eq_chiller_power = eq(
    "thermal.eq.chiller_power",
    chiller_power.symbol,
    chiller_heat_load.symbol / chiller_cop.symbol,
    "Chiller electrical power equals chiller heat load divided by chiller COP.",
    references=[FACILITY_THERMAL_REF],
    check_units=True,
)

eq_cooling_tower_power = eq(
    "thermal.eq.cooling_tower_power",
    cooling_tower_power.symbol,
    cooling_tower_aux_fraction.symbol * heat_to_reject.symbol,
    "Cooling-tower or dry-cooler auxiliary power is modeled as a fraction of the heat rejected to the environment.",
    references=[FACILITY_THERMAL_REF],
    check_units=True,
)

eq_p_cooling_total = eq(
    "thermal.eq.cooling_power_total",
    p_cooling_total.symbol,
    pump_power_site.symbol + fan_power.symbol + chiller_power.symbol + cdu_power.symbol + cooling_tower_power.symbol + humidity_control_power.symbol,
    "Total cooling power sums pumps, fans, chillers, CDU power, tower auxiliaries, and humidity control.",
    references=[FACILITY_THERMAL_REF],
    check_units=True,
)

eq_ups_loss = eq(
    "thermal.eq.ups_loss",
    p_ups_loss.symbol,
    ups_loss_fraction.symbol * cluster_power_it.symbol,
    "UPS losses are modeled as a fraction of site IT power.",
    references=[FACILITY_THERMAL_REF],
)

eq_transformer_loss = eq(
    "thermal.eq.transformer_loss",
    p_transformer_loss.symbol,
    transformer_loss_fraction.symbol * cluster_power_it.symbol,
    "Transformer and power-distribution losses are modeled as a fraction of site IT power.",
    references=[FACILITY_THERMAL_REF],
)

eq_lighting = eq(
    "thermal.eq.lighting",
    p_lighting.symbol,
    lighting_power_per_rack.symbol * n_racks_cluster.symbol,
    "Facility lighting and small non-IT electrical load scale with site rack count.",
    references=[FACILITY_THERMAL_REF],
    check_units=True,
)

eq_facility_misc = eq(
    "thermal.eq.facility_misc",
    p_facility_misc.symbol,
    facility_misc_fraction.symbol * cluster_power_it.symbol,
    "Miscellaneous facility electrical load is modeled as a fraction of site IT power.",
    references=[FACILITY_THERMAL_REF],
)

eq_dc_total_power = eq(
    "thermal.eq.dc_total_power",
    dc_total_power.symbol,
    cluster_power_it.symbol + p_cooling_total.symbol + p_ups_loss.symbol + p_transformer_loss.symbol + p_lighting.symbol + p_facility_misc.symbol,
    "Total site power equals IT load plus cooling and other facility overheads.",
    references=[FACILITY_THERMAL_REF],
)

eq_pue_definition = eq(
    "thermal.eq.pue_definition",
    pue.symbol,
    dc_total_power.symbol / cluster_power_it.symbol,
    "PUE is defined as total site power divided by IT load.",
    references=[FACILITY_THERMAL_REF],
)


THERMAL_FACILITY_VARIABLES = (
    air_flow_rate,
    fan_pressure_rise,
    fan_efficiency,
    fan_power,
    cluster_heat_load,
    heat_reuse_fraction,
    recovered_heat_power,
    heat_to_reject,
    ambient_wet_bulb,
    free_cooling_threshold,
    free_cooling_fraction,
    chiller_cop,
    chiller_heat_load,
    chiller_power,
    cooling_tower_aux_fraction,
    cooling_tower_power,
    humidity_control_power,
    p_cooling_total,
    ups_loss_fraction,
    transformer_loss_fraction,
    lighting_power_per_rack,
    facility_misc_fraction,
    p_ups_loss,
    p_transformer_loss,
    p_lighting,
    p_facility_misc,
    dc_total_power,
    pue,
    facility_floor_area,
    facility_power_design_capacity,
    facility_cooling_design_capacity,
)

THERMAL_FACILITY_EQUATIONS = (
    eq_fan_power,
    eq_cluster_heat_load,
    eq_recovered_heat_power,
    eq_heat_to_reject,
    eq_free_cooling_fraction,
    eq_chiller_heat_load,
    eq_chiller_power,
    eq_cooling_tower_power,
    eq_p_cooling_total,
    eq_ups_loss,
    eq_transformer_loss,
    eq_lighting,
    eq_facility_misc,
    eq_dc_total_power,
    eq_pue_definition,
)


__all__ = [
    "air_flow_rate",
    "fan_pressure_rise",
    "fan_efficiency",
    "fan_power",
    "cluster_heat_load",
    "heat_reuse_fraction",
    "recovered_heat_power",
    "heat_to_reject",
    "ambient_wet_bulb",
    "free_cooling_threshold",
    "free_cooling_fraction",
    "chiller_cop",
    "chiller_heat_load",
    "chiller_power",
    "cooling_tower_aux_fraction",
    "cooling_tower_power",
    "humidity_control_power",
    "p_cooling_total",
    "ups_loss_fraction",
    "transformer_loss_fraction",
    "lighting_power_per_rack",
    "facility_misc_fraction",
    "p_ups_loss",
    "p_transformer_loss",
    "p_lighting",
    "p_facility_misc",
    "dc_total_power",
    "pue",
    "facility_floor_area",
    "facility_power_design_capacity",
    "facility_cooling_design_capacity",
    "eq_fan_power",
    "eq_cluster_heat_load",
    "eq_recovered_heat_power",
    "eq_heat_to_reject",
    "eq_free_cooling_fraction",
    "eq_chiller_heat_load",
    "eq_chiller_power",
    "eq_cooling_tower_power",
    "eq_p_cooling_total",
    "eq_ups_loss",
    "eq_transformer_loss",
    "eq_lighting",
    "eq_facility_misc",
    "eq_dc_total_power",
    "eq_pue_definition",
    "THERMAL_FACILITY_VARIABLES",
    "THERMAL_FACILITY_EQUATIONS",
]
