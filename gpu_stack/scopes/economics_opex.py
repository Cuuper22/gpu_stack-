"""
scopes/economics_opex.py
========================

Operating-expenditure primitives for the economics scope.

This helper covers the energy and tariff detail (peak and off-peak pricing,
blended price, demand charges, peak demand), water cost, maintenance, staff,
network transit, carbon intensity and cost rate, the allocated job power,
and the run-level power cost that the recovery rollups consume.
"""

import sympy as sp
from ..core import Reference, eq, var
from ..core.units import KILOGRAM, METER, SECOND, WATT, byte

from .thermal import dc_total_power, water_usage_rate
from .training import T_wallclock
from .economics_capex import USD, cluster_capex_total, job_share_of_cluster


DIMENSIONLESS = sp.Integer(1)
USD_RATE = USD / SECOND
ENERGY_PRICE = USD / (WATT * SECOND)
VOLUME = METER**3

POWER_TARIFF_REF = Reference(
    "Power opex decomposes blended energy price, watt-second conversion, "
    "allocated job power, and demand-charge rate.",
    kind="model",
)

WATER_OPEX_REF = Reference(
    "Water opex multiplies site water usage by price per liter and allocates "
    "the result by job share.",
    kind="model",
)

SITE_OPEX_REF = Reference(
    "Site opex covers maintenance, staff, network transit, carbon pricing, "
    "and run-level electricity charges.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Energy, tariff, and variable operating cost
# ---------------------------------------------------------------------------

job_dc_power = var(
    "econ.job.dc_power", "P_job_dc", "W",
    "Allocated share of total site electrical power attributed to the training job.",
    scope="economics",
    sp_units=WATT,
    references=[POWER_TARIFF_REF],
)
price_kwh_peak = var(
    "econ.power.price_kwh_peak", "p_kWh_peak", "USD/(kW*h)",
    "Peak-period electricity price.",
    scope="economics",
    sp_units=ENERGY_PRICE,
    references=[POWER_TARIFF_REF],
)
price_kwh_offpeak = var(
    "econ.power.price_kwh_offpeak", "p_kWh_off", "USD/(kW*h)",
    "Off-peak electricity price.",
    scope="economics",
    sp_units=ENERGY_PRICE,
    references=[POWER_TARIFF_REF],
)
peak_energy_fraction = var(
    "econ.power.peak_energy_fraction", "f_peak", "dimensionless",
    "Fraction of the training run's energy billed at the peak tariff.",
    scope="economics",
    sp_units=DIMENSIONLESS,
    references=[POWER_TARIFF_REF],
)
price_kwh = var(
    "econ.power.price_kwh", "p_kWh", "USD/(kW*h)",
    "Blended electricity price after peak and off-peak weighting.",
    scope="economics",
    sp_units=ENERGY_PRICE,
    references=[POWER_TARIFF_REF],
)
cost_per_watt_sec = var(
    "econ.power.price_ws", "p_Ws", "USD/(W*s)",
    "Electricity price in USD per watt-second.",
    scope="economics",
    sp_units=ENERGY_PRICE,
    references=[POWER_TARIFF_REF],
)
peak_demand_kw = var(
    "econ.power.peak_demand_kw", "P_job_peak_kW", "kW",
    "Allocated peak demand of the training job for capacity-charge accounting.",
    scope="economics",
    sp_units=WATT,
    references=[POWER_TARIFF_REF],
)
capacity_charge_kw_month = var(
    "econ.power.capacity_charge_kw_month", "p_cap", "USD/(kW*month)",
    "Capacity charge per kilowatt of peak demand per month.",
    scope="economics",
    sp_units=ENERGY_PRICE,
    references=[POWER_TARIFF_REF],
)
capacity_charge_rate = var(
    "econ.power.capacity_charge_rate", "Cdot_cap", "USD/s",
    "Demand-charge cost rate allocated to the training job.",
    scope="economics",
    sp_units=USD_RATE,
    references=[POWER_TARIFF_REF],
)
water_price_per_liter = var(
    "econ.water.price_per_liter", "p_L", "USD/L",
    "Water price per liter including treatment and discharge costs.",
    scope="economics",
    sp_units=USD / VOLUME,
    references=[WATER_OPEX_REF],
)
water_cost_rate = var(
    "econ.water.cost_rate", "Cdot_water", "USD/s",
    "Water cost rate attributed to the training job.",
    scope="economics",
    sp_units=USD_RATE,
    references=[WATER_OPEX_REF],
)
maintenance_fraction_per_year = var(
    "econ.maintenance.fraction_per_year", "f_maint_y", "1/year",
    "Annual maintenance cost as a fraction of total site capex.",
    scope="economics",
    sp_units=sp.Integer(1) / SECOND,
    references=[SITE_OPEX_REF],
)
maintenance_cost_rate = var(
    "econ.maintenance.cost_rate", "Cdot_maint", "USD/s",
    "Site maintenance cost rate before job-level allocation.",
    scope="economics",
    sp_units=USD_RATE,
    references=[SITE_OPEX_REF],
)
staff_cost_rate = var(
    "econ.staff.cost_rate", "Cdot_staff", "USD/s",
    "Cluster-operations staff cost rate before job-level allocation.",
    scope="economics",
    sp_units=USD_RATE,
    references=[SITE_OPEX_REF],
)
network_transit_price_per_gb = var(
    "econ.network.transit_price_per_gb", "p_GB_transit", "USD/GB",
    "Network transit price per gigabyte.",
    scope="economics",
    sp_units=USD / byte,
    references=[SITE_OPEX_REF],
)
network_egress_bytes_per_s = var(
    "econ.network.egress_bytes_per_s", "BW_egress", "byte/s",
    "Average job-specific WAN or cross-region egress bandwidth.",
    scope="economics",
    sp_units=byte / SECOND,
    references=[SITE_OPEX_REF],
)
network_transit_cost_rate = var(
    "econ.network.transit_cost_rate", "Cdot_net", "USD/s",
    "Network-transit cost rate attributed to the training job.",
    scope="economics",
    sp_units=USD_RATE,
    references=[SITE_OPEX_REF],
)
carbon_intensity_kg_per_kwh = var(
    "econ.carbon.intensity_kg_per_kwh", "I_CO2", "kg/(kW*h)",
    "Grid carbon intensity in kilograms of CO2e per kilowatt-hour.",
    scope="economics",
    sp_units=KILOGRAM / (WATT * SECOND),
    references=[SITE_OPEX_REF],
)
carbon_emission_rate = var(
    "econ.carbon.emission_rate", "mdot_CO2", "kg/s",
    "Carbon-emission rate attributed to the training job.",
    scope="economics",
    sp_units=KILOGRAM / SECOND,
    references=[SITE_OPEX_REF],
)
carbon_price_per_tonne = var(
    "econ.carbon.price_per_tonne", "p_CO2", "USD/t",
    "Actual or shadow carbon price per metric tonne of CO2e.",
    scope="economics",
    sp_units=USD / KILOGRAM,
    references=[SITE_OPEX_REF],
)
carbon_cost_rate = var(
    "econ.carbon.cost_rate", "Cdot_CO2", "USD/s",
    "Carbon cost rate attributed to the training job.",
    scope="economics",
    sp_units=USD_RATE,
    references=[SITE_OPEX_REF],
)
run_power_cost = var(
    "econ.run.power_cost", "C_pw_run", "USD",
    "Electricity cost of the training run.",
    scope="economics",
    sp_units=USD,
    references=[POWER_TARIFF_REF],
)


eq_job_dc_power = eq(
    "econ.eq.job_dc_power",
    job_dc_power.symbol,
    job_share_of_cluster.symbol * dc_total_power.symbol,
    "Allocated job DC power equals job share times total site electrical power.",
    references=[POWER_TARIFF_REF],
    check_units=True,
)

eq_price_kwh = eq(
    "econ.eq.price_kwh",
    price_kwh.symbol,
    peak_energy_fraction.symbol * price_kwh_peak.symbol + (1 - peak_energy_fraction.symbol) * price_kwh_offpeak.symbol,
    "Blended electricity price equals the weighted combination of peak and off-peak tariffs.",
    references=[POWER_TARIFF_REF],
    check_units=True,
)

eq_ws_from_kwh = eq(
    "econ.eq.ws_from_kwh",
    cost_per_watt_sec.symbol,
    price_kwh.symbol / sp.Integer(3_600_000),
    "One kilowatt-hour is 3.6e6 watt-seconds, so blended $/kWh converts directly to $/(W*s).",
    references=[POWER_TARIFF_REF],
    check_units=True,
)

eq_peak_demand_kw = eq(
    "econ.eq.peak_demand_kw",
    peak_demand_kw.symbol,
    job_dc_power.symbol / sp.Integer(1000),
    "Peak demand in kilowatts equals allocated job power in watts divided by one thousand.",
    references=[POWER_TARIFF_REF],
    check_units=True,
)

eq_capacity_charge_rate = eq(
    "econ.eq.capacity_charge_rate",
    capacity_charge_rate.symbol,
    capacity_charge_kw_month.symbol * peak_demand_kw.symbol / sp.Integer(2_592_000),
    "Demand-charge rate equals dollars per kilowatt-month times peak kilowatts, converted to a per-second rate using a 30-day month.",
    references=[POWER_TARIFF_REF],
    check_units=True,
)

eq_water_cost_rate = eq(
    "econ.eq.water_cost_rate",
    water_cost_rate.symbol,
    water_price_per_liter.symbol * water_usage_rate.symbol * job_share_of_cluster.symbol,
    "Job water cost rate equals liters per second times price per liter, scaled by job share of site activity.",
    references=[WATER_OPEX_REF],
    check_units=True,
)

eq_maintenance_cost_rate = eq(
    "econ.eq.maintenance_cost_rate",
    maintenance_cost_rate.symbol,
    maintenance_fraction_per_year.symbol * cluster_capex_total.symbol / sp.Integer(31_536_000),
    "Maintenance cost rate equals annual maintenance fraction times total site capex, converted to seconds using a 365-day year.",
    references=[SITE_OPEX_REF],
    check_units=True,
)

eq_network_transit_cost_rate = eq(
    "econ.eq.network_transit_cost_rate",
    network_transit_cost_rate.symbol,
    network_transit_price_per_gb.symbol * network_egress_bytes_per_s.symbol / sp.Integer(1_000_000_000),
    "Network-transit cost rate equals dollars per gigabyte times job-specific gigabytes per second.",
    references=[SITE_OPEX_REF],
    check_units=True,
)

eq_carbon_emission_rate = eq(
    "econ.eq.carbon_emission_rate",
    carbon_emission_rate.symbol,
    carbon_intensity_kg_per_kwh.symbol * job_dc_power.symbol / sp.Integer(3_600_000),
    "Carbon-emission rate equals grid carbon intensity times allocated job power, using the standard kWh conversion.",
    references=[SITE_OPEX_REF],
    check_units=True,
)

eq_carbon_cost_rate = eq(
    "econ.eq.carbon_cost_rate",
    carbon_cost_rate.symbol,
    carbon_price_per_tonne.symbol * carbon_emission_rate.symbol / sp.Integer(1000),
    "Carbon cost rate equals dollars per tonne times kilograms per second, with one thousand kilograms per tonne.",
    references=[SITE_OPEX_REF],
    check_units=True,
)

eq_run_power_cost = eq(
    "econ.eq.run_power_cost",
    run_power_cost.symbol,
    cost_per_watt_sec.symbol * job_dc_power.symbol * T_wallclock.symbol,
    "Run electricity cost equals $ per watt-second times allocated job power times wall-clock duration.",
    references=[POWER_TARIFF_REF],
    check_units=True,
)


ECON_OPEX_VARIABLES = [
    job_dc_power,
    price_kwh_peak,
    price_kwh_offpeak,
    peak_energy_fraction,
    price_kwh,
    cost_per_watt_sec,
    peak_demand_kw,
    capacity_charge_kw_month,
    capacity_charge_rate,
    water_price_per_liter,
    water_cost_rate,
    maintenance_fraction_per_year,
    maintenance_cost_rate,
    staff_cost_rate,
    network_transit_price_per_gb,
    network_egress_bytes_per_s,
    network_transit_cost_rate,
    carbon_intensity_kg_per_kwh,
    carbon_emission_rate,
    carbon_price_per_tonne,
    carbon_cost_rate,
    run_power_cost,
]

ECON_OPEX_EQUATIONS = [
    eq_job_dc_power,
    eq_price_kwh,
    eq_ws_from_kwh,
    eq_peak_demand_kw,
    eq_capacity_charge_rate,
    eq_water_cost_rate,
    eq_maintenance_cost_rate,
    eq_network_transit_cost_rate,
    eq_carbon_emission_rate,
    eq_carbon_cost_rate,
    eq_run_power_cost,
]


__all__ = [
    "job_dc_power", "price_kwh_peak", "price_kwh_offpeak",
    "peak_energy_fraction", "price_kwh", "cost_per_watt_sec",
    "peak_demand_kw", "capacity_charge_kw_month", "capacity_charge_rate",
    "water_price_per_liter", "water_cost_rate",
    "maintenance_fraction_per_year", "maintenance_cost_rate",
    "staff_cost_rate",
    "network_transit_price_per_gb", "network_egress_bytes_per_s",
    "network_transit_cost_rate",
    "carbon_intensity_kg_per_kwh", "carbon_emission_rate",
    "carbon_price_per_tonne", "carbon_cost_rate",
    "run_power_cost",
    "eq_job_dc_power", "eq_price_kwh", "eq_ws_from_kwh",
    "eq_peak_demand_kw", "eq_capacity_charge_rate",
    "eq_water_cost_rate", "eq_maintenance_cost_rate",
    "eq_network_transit_cost_rate",
    "eq_carbon_emission_rate", "eq_carbon_cost_rate",
    "eq_run_power_cost",
    "ECON_OPEX_VARIABLES", "ECON_OPEX_EQUATIONS",
]
