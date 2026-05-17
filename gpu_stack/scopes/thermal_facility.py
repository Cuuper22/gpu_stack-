"""
scopes/thermal_facility.py
==========================

Facility cooling plant and site power: fan power, chiller load and power,
cooling-tower auxiliary power, heat reuse, wet-bulb-driven free-cooling
piecewise logic, humidity-control power, total cooling power, PUE
definition, and the component sum that gives DC total power.
"""

from ..core import Reference
from ..core.units import KELVIN, METER, PASCAL, SECOND, WATT
from .cluster import cluster_power_it, n_racks_cluster
from .thermal_liquid import cdu_power, pump_power_site
from .cluster_ops_declarations import (
    DIMENSIONLESS,
    referenced_eq,
    referenced_piecewise,
    scoped_var,
)


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


facility_thermal_var = scoped_var("thermal", FACILITY_THERMAL_REF)
facility_sizing_var = scoped_var("thermal", FACILITY_SIZING_REF)

facility_thermal_eq = referenced_eq(FACILITY_THERMAL_REF)
facility_thermal_piecewise = referenced_piecewise(FACILITY_THERMAL_REF)


# ---------------------------------------------------------------------------
# Fans
# ---------------------------------------------------------------------------

air_flow_rate = facility_thermal_var(
    "thermal.facility.air_flow_rate", "Vdot_air", "m^3/s",
    "Airflow rate through fans used for room air management or dry coolers.",
    sp_units=VOLUMETRIC_FLOW,
)
fan_pressure_rise = facility_thermal_var(
    "thermal.facility.fan_pressure_rise", "dP_fan", "Pa",
    "Pressure rise developed by the fan system.",
    sp_units=PASCAL,
)
fan_efficiency = facility_thermal_var(
    "thermal.facility.fan_efficiency", "eta_fan", "dimensionless",
    "Electrical-to-airflow efficiency of the fan system.",
    sp_units=DIMENSIONLESS,
)
fan_power = facility_thermal_var(
    "thermal.facility.fan_power", "P_fan", "W",
    "Aggregate fan power.",
    sp_units=WATT,
)


# ---------------------------------------------------------------------------
# Site heat load, reuse, and heat to reject
# ---------------------------------------------------------------------------

cluster_heat_load = facility_thermal_var(
    "thermal.facility.heat_load", "Q_site", "W",
    "Site heat load from IT equipment. In steady state this is the same as IT electrical power.",
    sp_units=WATT,
)
heat_reuse_fraction = facility_thermal_var(
    "thermal.facility.heat_reuse_fraction", "f_reuse", "dimensionless",
    "Fraction of site heat load diverted to useful heat reuse instead of the cooling tower or dry cooler.",
    sp_units=DIMENSIONLESS,
)
recovered_heat_power = facility_thermal_var(
    "thermal.facility.recovered_heat_power", "Q_reuse", "W",
    "Heat power recovered for district heating or other reuse paths.",
    sp_units=WATT,
)
heat_to_reject = facility_thermal_var(
    "thermal.facility.heat_to_reject", "Q_reject", "W",
    "Heat that still must be rejected to the environment after any reuse.",
    sp_units=WATT,
)


# ---------------------------------------------------------------------------
# Free cooling, chiller, and tower
# ---------------------------------------------------------------------------

ambient_wet_bulb = facility_thermal_var(
    "thermal.facility.wet_bulb", "T_wb", "K",
    "Ambient wet-bulb temperature relevant for evaporative cooling and tower operation.",
    sp_units=KELVIN,
)
free_cooling_threshold = facility_thermal_var(
    "thermal.facility.free_cooling_threshold", "T_fc", "K",
    "Wet-bulb threshold below which the site can satisfy the cooling load without active chilling.",
    sp_units=KELVIN,
)
free_cooling_fraction = facility_thermal_var(
    "thermal.facility.free_cooling_fraction", "f_fc", "dimensionless",
    "Fraction of the facility heat-rejection load that can be handled by free cooling rather than an active chiller.",
    sp_units=DIMENSIONLESS,
)
chiller_cop = facility_thermal_var(
    "thermal.facility.chiller_cop", "COP_ch", "dimensionless",
    "Coefficient of performance of the active chiller plant.",
    sp_units=DIMENSIONLESS,
)
chiller_heat_load = facility_thermal_var(
    "thermal.facility.chiller_heat_load", "Q_ch", "W",
    "Heat load that must still be lifted by the active chiller plant.",
    sp_units=WATT,
)
chiller_power = facility_thermal_var(
    "thermal.facility.chiller_power", "P_ch", "W",
    "Electrical power of the active chiller plant.",
    sp_units=WATT,
)
cooling_tower_aux_fraction = facility_thermal_var(
    "thermal.facility.tower_aux_fraction", "f_twr_aux", "dimensionless",
    "Auxiliary electric-power fraction for the cooling tower or dry-cooler path, excluding chiller power.",
    sp_units=DIMENSIONLESS,
)
cooling_tower_power = facility_thermal_var(
    "thermal.facility.tower_power", "P_twr", "W",
    "Cooling-tower or dry-cooler auxiliary power.",
    sp_units=WATT,
)
humidity_control_power = facility_thermal_var(
    "thermal.facility.humidity_control_power", "P_hum", "W",
    "Power used for humidity control and condensation management.",
    sp_units=WATT,
)
p_cooling_total = facility_thermal_var(
    "thermal.facility.cooling_power", "P_cool", "W",
    "Total facility cooling power.",
    sp_units=WATT,
)


# ---------------------------------------------------------------------------
# Non-cooling facility overheads and DC total power / PUE
# ---------------------------------------------------------------------------

ups_loss_fraction = facility_thermal_var(
    "thermal.facility.ups_loss_fraction", "f_ups_loss", "dimensionless",
    "UPS conversion and battery-system loss fraction relative to IT power.",
    sp_units=DIMENSIONLESS,
)
transformer_loss_fraction = facility_thermal_var(
    "thermal.facility.transformer_loss_fraction", "f_xfrm_loss", "dimensionless",
    "Transformer and power-distribution loss fraction relative to IT power.",
    sp_units=DIMENSIONLESS,
)
lighting_power_per_rack = facility_thermal_var(
    "thermal.facility.lighting_power_per_rack", "P_light_rack", "W/rack",
    "Lighting and small non-IT facility electrical load allocated per rack.",
    sp_units=WATT,
)
facility_misc_fraction = facility_thermal_var(
    "thermal.facility.misc_fraction", "f_misc_fac", "dimensionless",
    "Miscellaneous facility electrical-load fraction relative to IT power.",
    sp_units=DIMENSIONLESS,
)
p_ups_loss = facility_thermal_var(
    "thermal.facility.ups_loss", "P_ups", "W",
    "UPS conversion and battery-system losses.",
    sp_units=WATT,
)
p_transformer_loss = facility_thermal_var(
    "thermal.facility.transformer_loss", "P_xfrm", "W",
    "Transformer and power-distribution losses.",
    sp_units=WATT,
)
p_lighting = facility_thermal_var(
    "thermal.facility.lighting", "P_light", "W",
    "Lighting and small non-IT facility electrical load.",
    sp_units=WATT,
)
p_facility_misc = facility_thermal_var(
    "thermal.facility.misc", "P_misc_fac", "W",
    "Other facility electrical load not captured elsewhere.",
    sp_units=WATT,
)
dc_total_power = facility_thermal_var(
    "thermal.dc.total_power", "P_dc", "W",
    "Total site electrical load including IT, cooling, and other facility overheads.",
    sp_units=WATT,
)
pue = facility_thermal_var(
    "thermal.dc.pue", "PUE", "dimensionless",
    "Power Usage Effectiveness, defined as total site power divided by IT load.",
    sp_units=DIMENSIONLESS,
)


# ---------------------------------------------------------------------------
# Facility sizing quantities used by capex
# ---------------------------------------------------------------------------

facility_floor_area = facility_sizing_var(
    "thermal.facility.floor_area", "A_fac", "m^2",
    "Gross facility floor area allocated to the site.",
    sp_units=METER**2,
)
facility_power_design_capacity = facility_sizing_var(
    "thermal.facility.power_design_capacity", "P_fac_design", "W",
    "Nameplate electrical design capacity for the facility power infrastructure.",
    sp_units=WATT,
)
facility_cooling_design_capacity = facility_sizing_var(
    "thermal.facility.cooling_design_capacity", "Q_cool_design", "W",
    "Nameplate thermal design capacity for the facility cooling infrastructure.",
    sp_units=WATT,
)


eq_fan_power = facility_thermal_eq(
    "thermal.eq.fan_power",
    fan_power.symbol,
    air_flow_rate.symbol * fan_pressure_rise.symbol / fan_efficiency.symbol,
    "Fan power equals volumetric airflow times pressure rise divided by fan efficiency.",
    check_units=True,
)

eq_cluster_heat_load = facility_thermal_eq(
    "thermal.eq.cluster_heat_load",
    cluster_heat_load.symbol,
    cluster_power_it.symbol,
    "In steady state, essentially all IT electrical power appears as heat that must be managed by the facility.",
)

eq_recovered_heat_power = facility_thermal_eq(
    "thermal.eq.recovered_heat_power",
    recovered_heat_power.symbol,
    heat_reuse_fraction.symbol * cluster_heat_load.symbol,
    "Recovered heat equals the reusable fraction of the site heat load.",
    check_units=True,
)

eq_heat_to_reject = facility_thermal_eq(
    "thermal.eq.heat_to_reject",
    heat_to_reject.symbol,
    cluster_heat_load.symbol - recovered_heat_power.symbol,
    "Heat to reject equals total site heat load minus recovered heat.",
    check_units=True,
)

eq_free_cooling_fraction = facility_thermal_piecewise(
    "thermal.eq.free_cooling_fraction",
    free_cooling_fraction.symbol,
    [
        (1, ambient_wet_bulb.symbol <= free_cooling_threshold.symbol),
        (0, True),
    ],
    "Free cooling is available when ambient wet-bulb temperature is at or below the configured threshold.",
)

eq_chiller_heat_load = facility_thermal_eq(
    "thermal.eq.chiller_heat_load",
    chiller_heat_load.symbol,
    (1 - free_cooling_fraction.symbol) * heat_to_reject.symbol,
    "Active chiller heat load is the residual heat load not covered by free cooling.",
    check_units=True,
)

eq_chiller_power = facility_thermal_eq(
    "thermal.eq.chiller_power",
    chiller_power.symbol,
    chiller_heat_load.symbol / chiller_cop.symbol,
    "Chiller electrical power equals chiller heat load divided by chiller COP.",
    check_units=True,
)

eq_cooling_tower_power = facility_thermal_eq(
    "thermal.eq.cooling_tower_power",
    cooling_tower_power.symbol,
    cooling_tower_aux_fraction.symbol * heat_to_reject.symbol,
    "Cooling-tower or dry-cooler auxiliary power is modeled as a fraction of the heat rejected to the environment.",
    check_units=True,
)

eq_p_cooling_total = facility_thermal_eq(
    "thermal.eq.cooling_power_total",
    p_cooling_total.symbol,
    pump_power_site.symbol + fan_power.symbol + chiller_power.symbol + cdu_power.symbol + cooling_tower_power.symbol + humidity_control_power.symbol,
    "Total cooling power sums pumps, fans, chillers, CDU power, tower auxiliaries, and humidity control.",
    check_units=True,
)

eq_ups_loss = facility_thermal_eq(
    "thermal.eq.ups_loss",
    p_ups_loss.symbol,
    ups_loss_fraction.symbol * cluster_power_it.symbol,
    "UPS losses are modeled as a fraction of site IT power.",
)

eq_transformer_loss = facility_thermal_eq(
    "thermal.eq.transformer_loss",
    p_transformer_loss.symbol,
    transformer_loss_fraction.symbol * cluster_power_it.symbol,
    "Transformer and power-distribution losses are modeled as a fraction of site IT power.",
)

eq_lighting = facility_thermal_eq(
    "thermal.eq.lighting",
    p_lighting.symbol,
    lighting_power_per_rack.symbol * n_racks_cluster.symbol,
    "Facility lighting and small non-IT electrical load scale with site rack count.",
    check_units=True,
)

eq_facility_misc = facility_thermal_eq(
    "thermal.eq.facility_misc",
    p_facility_misc.symbol,
    facility_misc_fraction.symbol * cluster_power_it.symbol,
    "Miscellaneous facility electrical load is modeled as a fraction of site IT power.",
)

eq_dc_total_power = facility_thermal_eq(
    "thermal.eq.dc_total_power",
    dc_total_power.symbol,
    cluster_power_it.symbol + p_cooling_total.symbol + p_ups_loss.symbol + p_transformer_loss.symbol + p_lighting.symbol + p_facility_misc.symbol,
    "Total site power equals IT load plus cooling and other facility overheads.",
)

eq_pue_definition = facility_thermal_eq(
    "thermal.eq.pue_definition",
    pue.symbol,
    dc_total_power.symbol / cluster_power_it.symbol,
    "PUE is defined as total site power divided by IT load.",
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
