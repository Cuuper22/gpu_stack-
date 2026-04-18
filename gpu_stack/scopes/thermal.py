"""
scopes/thermal.py
=================

Heat transfer, cooling, and facility overhead from the package scale up to the
whole data center.

The old file had the right nouns but one bad graph edge: it defined PUE from
DC total power and then defined DC total power from PUE, which is the same
relation written twice and therefore a cycle. This version keeps the PUE
ratio as the definition and computes total facility power from explicit
cooling and non-IT overhead terms.

The scope now covers:

* detailed package-to-coolant thermal resistances,
* coolant flow, pump power, and fan power,
* free-cooling versus chiller operation,
* heat reuse, water use, and WUE,
* ASHRAE-style inlet and humidity constraints,
* facility total power and PUE without circularity.
"""

import sympy as sp
from ..constants import STEFAN_BOLTZMANN
from ..core import Inequality, PiecewiseEquation, System, eq, var

from .cluster import cluster_n_gpus, cluster_power_it
from .gpu import p_gpu_total


sys_thermal = System(
    name="thermal",
    scope="thermal",
    description="Package-to-facility thermal path, cooling overhead, and PUE.",
)


# ---------------------------------------------------------------------------
# Package thermal path, per GPU
# ---------------------------------------------------------------------------

theta_die_attach = var(
    "thermal.path.theta_die_attach", "theta_die", "K/W",
    "Die-attach and local silicon-to-lid thermal resistance.",
    scope="thermal",
)
theta_tim = var(
    "thermal.path.theta_tim", "theta_tim", "K/W",
    "Thermal interface material resistance.",
    scope="thermal",
)
theta_spreader = var(
    "thermal.path.theta_spreader", "theta_spr", "K/W",
    "Heat-spreader and lid thermal resistance.",
    scope="thermal",
)
theta_coldplate = var(
    "thermal.path.theta_coldplate", "theta_cp", "K/W",
    "Cold-plate conduction resistance.",
    scope="thermal",
)
theta_fluid_film = var(
    "thermal.path.theta_fluid_film", "theta_ff", "K/W",
    "Fluid-side film resistance from the cold plate into the coolant stream.",
    scope="thermal",
)
theta_jc = var(
    "thermal.theta_jc", "theta_jc", "K/W",
    "Junction-to-case thermal resistance of the package path above the cold plate.",
    scope="thermal",
)
theta_ca = var(
    "thermal.theta_ca", "theta_ca", "K/W",
    "Case-to-coolant thermal resistance through the cold plate and fluid film.",
    scope="thermal",
)
theta_ja = var(
    "thermal.theta_ja", "theta_ja", "K/W",
    "Overall junction-to-coolant thermal resistance.",
    scope="thermal",
)
T_case = var(
    "thermal.t_case", "T_case", "K",
    "Case or lid temperature of the package.",
    scope="thermal",
)
T_junction = var(
    "thermal.t_junction", "T_j", "K",
    "Die junction temperature.",
    scope="thermal",
)
T_coolant_inlet = var(
    "thermal.coolant.t_inlet", "T_c_in", "K",
    "Coolant supply temperature entering the cold plate.",
    scope="thermal",
)
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
T_ambient = var(
    "thermal.t_ambient", "T_amb", "K",
    "Server inlet or surrounding ambient dry-bulb temperature.",
    scope="thermal",
)
delta_T_coolant = var(
    "thermal.coolant.delta_T", "dT_c", "K",
    "Coolant temperature rise across one package cold plate.",
    scope="thermal",
)


eq_theta_jc = eq(
    "thermal.eq.theta_jc_components",
    theta_jc.symbol,
    theta_die_attach.symbol + theta_tim.symbol + theta_spreader.symbol,
    "Junction-to-case resistance is the sum of die-attach, TIM, and spreader resistances.",
)

eq_theta_ca = eq(
    "thermal.eq.theta_ca_components",
    theta_ca.symbol,
    theta_coldplate.symbol + theta_fluid_film.symbol,
    "Case-to-coolant resistance is the sum of cold-plate and fluid-film resistances.",
)

eq_theta_sum = eq(
    "thermal.eq.theta_sum",
    theta_ja.symbol,
    theta_jc.symbol + theta_ca.symbol,
    "Overall junction-to-coolant thermal resistance is the series sum of the package and cold-plate path.",
)

eq_t_case = eq(
    "thermal.eq.case_temp",
    T_case.symbol,
    T_coolant_inlet.symbol + theta_ca.symbol * p_gpu_total.symbol,
    "Case temperature rises above coolant inlet temperature by package power times the case-to-coolant resistance.",
)

eq_junction_temp = eq(
    "thermal.eq.junction_temp",
    T_junction.symbol,
    T_case.symbol + theta_jc.symbol * p_gpu_total.symbol,
    "Junction temperature rises above case temperature by package power times the junction-to-case resistance.",
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


# ---------------------------------------------------------------------------
# Coolant flow, heat removal, and radiation, per GPU
# ---------------------------------------------------------------------------

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
Q_removed = var(
    "thermal.q_removed", "Q_rem", "W",
    "Heat-removal capacity of the cold plate coolant path for one package.",
    scope="thermal",
)
Q_required = var(
    "thermal.q_required", "Q_req", "W",
    "Non-radiative heat that the coolant path must remove from one package.",
    scope="thermal",
)
thermal_headroom = var(
    "thermal.headroom", "Q_margin", "W",
    "Cold-plate heat-removal margin after subtracting required heat removal from available heat-removal capacity.",
    scope="thermal",
)
A_rad = var(
    "thermal.rad.area", "A_rad", "m^2",
    "Radiating surface area of the package or nearby heat spreader.",
    scope="thermal",
)
eps_rad = var(
    "thermal.rad.emissivity", "eps_r", "dimensionless",
    "Effective emissivity of the radiating package surface.",
    scope="thermal",
)
P_rad = var(
    "thermal.rad.power", "P_rad", "W",
    "Radiative heat-transfer power from the package to its surroundings.",
    scope="thermal",
)


eq_volumetric_flow_coolant = eq(
    "thermal.eq.coolant_vol_flow",
    volumetric_flow_coolant.symbol,
    m_dot_coolant.symbol / coolant_density.symbol,
    "Coolant volumetric flow equals mass-flow rate divided by coolant density.",
)

eq_heat_removed = eq(
    "thermal.eq.q_removed",
    Q_removed.symbol,
    m_dot_coolant.symbol * c_p_coolant.symbol * delta_T_coolant.symbol,
    "Cold-plate heat-removal capacity follows the sensible-heat relation m-dot times c_p times delta-T.",
)

eq_stefan_boltzmann = eq(
    "thermal.eq.stefan_boltzmann",
    P_rad.symbol,
    eps_rad.symbol * STEFAN_BOLTZMANN.symbol * A_rad.symbol * (T_junction.symbol ** 4 - T_ambient.symbol ** 4),
    "Radiative heat transfer follows the Stefan-Boltzmann law.",
)

eq_q_required = eq(
    "thermal.eq.q_required",
    Q_required.symbol,
    p_gpu_total.symbol - P_rad.symbol,
    "Coolant must remove package power minus the small portion rejected by radiation.",
)

eq_thermal_headroom = eq(
    "thermal.eq.thermal_headroom",
    thermal_headroom.symbol,
    Q_removed.symbol - Q_required.symbol,
    "Thermal headroom is positive when the coolant path can remove more heat than the package requires.",
)


# ---------------------------------------------------------------------------
# Facility cooling plant
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
air_flow_rate = var(
    "thermal.facility.air_flow_rate", "Vdot_air", "m^3/s",
    "Airflow rate through fans used for room air management or dry coolers.",
    scope="thermal",
)
fan_pressure_rise = var(
    "thermal.facility.fan_pressure_rise", "dP_fan", "Pa",
    "Pressure rise developed by the fan system.",
    scope="thermal",
)
fan_efficiency = var(
    "thermal.facility.fan_efficiency", "eta_fan", "dimensionless",
    "Electrical-to-airflow efficiency of the fan system.",
    scope="thermal",
)
fan_power = var(
    "thermal.facility.fan_power", "P_fan", "W",
    "Aggregate fan power.",
    scope="thermal",
)
cluster_heat_load = var(
    "thermal.facility.heat_load", "Q_site", "W",
    "Site heat load from IT equipment. In steady state this is the same as IT electrical power.",
    scope="thermal",
)
heat_reuse_fraction = var(
    "thermal.facility.heat_reuse_fraction", "f_reuse", "dimensionless",
    "Fraction of site heat load diverted to useful heat reuse instead of the cooling tower or dry cooler.",
    scope="thermal",
)
recovered_heat_power = var(
    "thermal.facility.recovered_heat_power", "Q_reuse", "W",
    "Heat power recovered for district heating or other reuse paths.",
    scope="thermal",
)
heat_to_reject = var(
    "thermal.facility.heat_to_reject", "Q_reject", "W",
    "Heat that still must be rejected to the environment after any reuse.",
    scope="thermal",
)
ambient_wet_bulb = var(
    "thermal.facility.wet_bulb", "T_wb", "K",
    "Ambient wet-bulb temperature relevant for evaporative cooling and tower operation.",
    scope="thermal",
)
free_cooling_threshold = var(
    "thermal.facility.free_cooling_threshold", "T_fc", "K",
    "Wet-bulb threshold below which the site can satisfy the cooling load without active chilling.",
    scope="thermal",
)
free_cooling_fraction = var(
    "thermal.facility.free_cooling_fraction", "f_fc", "dimensionless",
    "Fraction of the facility heat-rejection load that can be handled by free cooling rather than an active chiller.",
    scope="thermal",
)
chiller_cop = var(
    "thermal.facility.chiller_cop", "COP_ch", "dimensionless",
    "Coefficient of performance of the active chiller plant.",
    scope="thermal",
)
chiller_heat_load = var(
    "thermal.facility.chiller_heat_load", "Q_ch", "W",
    "Heat load that must still be lifted by the active chiller plant.",
    scope="thermal",
)
chiller_power = var(
    "thermal.facility.chiller_power", "P_ch", "W",
    "Electrical power of the active chiller plant.",
    scope="thermal",
)
cdu_power = var(
    "thermal.facility.cdu_power", "P_cdu", "W",
    "Coolant distribution unit power.",
    scope="thermal",
)
cooling_tower_aux_fraction = var(
    "thermal.facility.tower_aux_fraction", "f_twr_aux", "dimensionless",
    "Auxiliary electric-power fraction for the cooling tower or dry-cooler path, excluding chiller power.",
    scope="thermal",
)
cooling_tower_power = var(
    "thermal.facility.tower_power", "P_twr", "W",
    "Cooling-tower or dry-cooler auxiliary power.",
    scope="thermal",
)
humidity_control_power = var(
    "thermal.facility.humidity_control_power", "P_hum", "W",
    "Power used for humidity control and condensation management.",
    scope="thermal",
)
p_cooling_total = var(
    "thermal.facility.cooling_power", "P_cool", "W",
    "Total facility cooling power.",
    scope="thermal",
)
p_ups_loss = var(
    "thermal.facility.ups_loss", "P_ups", "W",
    "UPS conversion and battery-system losses.",
    scope="thermal",
)
p_transformer_loss = var(
    "thermal.facility.transformer_loss", "P_xfrm", "W",
    "Transformer and power-distribution losses.",
    scope="thermal",
)
p_lighting = var(
    "thermal.facility.lighting", "P_light", "W",
    "Lighting and small non-IT facility electrical load.",
    scope="thermal",
)
p_facility_misc = var(
    "thermal.facility.misc", "P_misc_fac", "W",
    "Other facility electrical load not captured elsewhere.",
    scope="thermal",
)
dc_total_power = var(
    "thermal.dc.total_power", "P_dc", "W",
    "Total site electrical load including IT, cooling, and other facility overheads.",
    scope="thermal",
)
pue = var(
    "thermal.dc.pue", "PUE", "dimensionless",
    "Power Usage Effectiveness, defined as total site power divided by IT load.",
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

eq_fan_power = eq(
    "thermal.eq.fan_power",
    fan_power.symbol,
    air_flow_rate.symbol * fan_pressure_rise.symbol / fan_efficiency.symbol,
    "Fan power equals volumetric airflow times pressure rise divided by fan efficiency.",
)

eq_cluster_heat_load = eq(
    "thermal.eq.cluster_heat_load",
    cluster_heat_load.symbol,
    cluster_power_it.symbol,
    "In steady state, essentially all IT electrical power appears as heat that must be managed by the facility.",
)

eq_recovered_heat_power = eq(
    "thermal.eq.recovered_heat_power",
    recovered_heat_power.symbol,
    heat_reuse_fraction.symbol * cluster_heat_load.symbol,
    "Recovered heat equals the reusable fraction of the site heat load.",
)

eq_heat_to_reject = eq(
    "thermal.eq.heat_to_reject",
    heat_to_reject.symbol,
    cluster_heat_load.symbol - recovered_heat_power.symbol,
    "Heat to reject equals total site heat load minus recovered heat.",
)

eq_free_cooling_fraction = PiecewiseEquation(
    "thermal.eq.free_cooling_fraction",
    free_cooling_fraction.symbol,
    [
        (1, ambient_wet_bulb.symbol <= free_cooling_threshold.symbol),
        (0, True),
    ],
    "Free cooling is available when ambient wet-bulb temperature is at or below the configured threshold.",
)

eq_chiller_heat_load = eq(
    "thermal.eq.chiller_heat_load",
    chiller_heat_load.symbol,
    (1 - free_cooling_fraction.symbol) * heat_to_reject.symbol,
    "Active chiller heat load is the residual heat load not covered by free cooling.",
)

eq_chiller_power = eq(
    "thermal.eq.chiller_power",
    chiller_power.symbol,
    chiller_heat_load.symbol / chiller_cop.symbol,
    "Chiller electrical power equals chiller heat load divided by chiller COP.",
)

eq_cooling_tower_power = eq(
    "thermal.eq.cooling_tower_power",
    cooling_tower_power.symbol,
    cooling_tower_aux_fraction.symbol * heat_to_reject.symbol,
    "Cooling-tower or dry-cooler auxiliary power is modeled as a fraction of the heat rejected to the environment.",
)

eq_p_cooling_total = eq(
    "thermal.eq.cooling_power_total",
    p_cooling_total.symbol,
    pump_power_site.symbol + fan_power.symbol + chiller_power.symbol + cdu_power.symbol + cooling_tower_power.symbol + humidity_control_power.symbol,
    "Total cooling power sums pumps, fans, chillers, CDU power, tower auxiliaries, and humidity control.",
)

eq_dc_total_power = eq(
    "thermal.eq.dc_total_power",
    dc_total_power.symbol,
    cluster_power_it.symbol + p_cooling_total.symbol + p_ups_loss.symbol + p_transformer_loss.symbol + p_lighting.symbol + p_facility_misc.symbol,
    "Total site power equals IT load plus cooling and other facility overheads.",
)

eq_pue_definition = eq(
    "thermal.eq.pue_definition",
    pue.symbol,
    dc_total_power.symbol / cluster_power_it.symbol,
    "PUE is defined as total site power divided by IT load.",
)


# ---------------------------------------------------------------------------
# Water usage and environmental envelope
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


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

sys_thermal.add_all([
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
    T_coolant_outlet,
    T_coolant_avg,
    T_ambient,
    m_dot_coolant,
    c_p_coolant,
    delta_T_coolant,
    coolant_density,
    volumetric_flow_coolant,
    Q_removed,
    Q_required,
    thermal_headroom,
    A_rad,
    eps_rad,
    P_rad,
    delta_p_coolant_loop,
    pump_efficiency,
    pump_power_per_gpu,
    pump_power_site,
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
    cdu_power,
    cooling_tower_aux_fraction,
    cooling_tower_power,
    humidity_control_power,
    p_cooling_total,
    p_ups_loss,
    p_transformer_loss,
    p_lighting,
    p_facility_misc,
    dc_total_power,
    pue,
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
])

sys_thermal.add_all([
    eq_theta_jc,
    eq_theta_ca,
    eq_theta_sum,
    eq_t_case,
    eq_junction_temp,
    eq_t_coolant_outlet,
    eq_t_coolant_avg,
    eq_volumetric_flow_coolant,
    eq_heat_removed,
    eq_stefan_boltzmann,
    eq_q_required,
    eq_thermal_headroom,
    eq_pump_power_per_gpu,
    eq_pump_power_site,
    eq_fan_power,
    eq_cluster_heat_load,
    eq_recovered_heat_power,
    eq_heat_to_reject,
    eq_free_cooling_fraction,
    eq_chiller_heat_load,
    eq_chiller_power,
    eq_cooling_tower_power,
    eq_p_cooling_total,
    eq_dc_total_power,
    eq_pue_definition,
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
])
