"""
scopes/economics.py
===================

The dollar layer. Physics, architecture, and systems constraints set what the
machine can do. Economics turns those constraints into capital charges,
operating expense, and cost-recovery targets.

The original file only priced GPUs and electricity. That was too thin to say
anything serious about real deployments. This version adds:

* node, rack, cluster, and facility capex breakdowns,
* residual value, utilization, and amortization allocation,
* energy tariffs with peak and off-peak blending plus demand charges,
* water, maintenance, staff, transit, and carbon costs,
* run-level NPV and inference-token recovery targets.
"""

import sympy as sp
from ..core import System, eq, var

from .cluster import cluster_n_gpus, n_gpus_per_node, n_nodes_per_rack, n_racks_cluster
from .parallelism import n_gpus_total
from .thermal import dc_total_power, water_usage_rate
from .training import N_train_tokens, T_wallclock, achieved_flops_run, n_steps


sys_econ = System(
    name="economics",
    scope="economics",
    description="Capex, opex, training-run cost, and cost-recovery targets.",
)


# ---------------------------------------------------------------------------
# GPU-level amortization
# ---------------------------------------------------------------------------

gpu_capex = var(
    "econ.gpu.capex", "C_cap_GPU", "USD",
    "Purchase price of one GPU.",
    scope="economics",
)
useful_life = var(
    "econ.asset.useful_life", "T_life", "s",
    "Depreciation horizon in seconds.",
    scope="economics",
)
residual_value_fraction = var(
    "econ.asset.residual_fraction", "f_resid", "dimensionless",
    "Residual-value fraction remaining at the end of the depreciation horizon.",
    scope="economics",
)
gpu_residual_value = var(
    "econ.gpu.residual_value", "C_resid_GPU", "USD",
    "Residual value of one GPU at end of life.",
    scope="economics",
)
gpu_hourly_amortized = var(
    "econ.gpu.hourly_amortized", "C_amort", "USD/s",
    "Straight-line amortized GPU cost per second after residual value is removed.",
    scope="economics",
)
gpu_hourly_rent = var(
    "econ.gpu.hourly_rent", "C_rent", "USD/s",
    "Market rental price of one GPU per second.",
    scope="economics",
)
gpu_rental_markup = var(
    "econ.gpu.rental_markup", "k_rent", "dimensionless",
    "Rental markup relative to straight-line amortized GPU cost.",
    scope="economics",
)


eq_gpu_residual_value = eq(
    "econ.eq.gpu_residual_value",
    gpu_residual_value.symbol,
    residual_value_fraction.symbol * gpu_capex.symbol,
    "GPU residual value equals residual fraction times GPU purchase cost.",
)

eq_amortized = eq(
    "econ.eq.amortized",
    gpu_hourly_amortized.symbol,
    (gpu_capex.symbol - gpu_residual_value.symbol) / useful_life.symbol,
    "GPU straight-line amortization equals depreciable GPU capex divided by useful life.",
)

eq_gpu_rental_markup = eq(
    "econ.eq.gpu_rental_markup",
    gpu_rental_markup.symbol,
    gpu_hourly_rent.symbol / gpu_hourly_amortized.symbol,
    "Rental markup is market rental price divided by straight-line amortized GPU cost.",
)


# ---------------------------------------------------------------------------
# Cluster capex breakdown
# ---------------------------------------------------------------------------

node_cpu_capex = var(
    "econ.node.cpu_capex", "C_cpu_node", "USD",
    "CPU capex per node.",
    scope="economics",
)
node_dram_capex = var(
    "econ.node.dram_capex", "C_dram_node", "USD",
    "CPU-side DRAM capex per node.",
    scope="economics",
)
node_nic_capex = var(
    "econ.node.nic_capex", "C_nic_node", "USD",
    "NIC, retimer, and cable capex per node.",
    scope="economics",
)
node_storage_capex = var(
    "econ.node.storage_capex", "C_stor_node", "USD",
    "Local SSD or NVMe storage capex per node.",
    scope="economics",
)
node_chassis_capex = var(
    "econ.node.chassis_capex", "C_chassis_node", "USD",
    "Chassis, motherboard, PSU, and assembly capex per node.",
    scope="economics",
)
rack_switch_capex = var(
    "econ.rack.switch_capex", "C_sw_rack", "USD",
    "Top-of-rack and rack-local fabric capex per rack.",
    scope="economics",
)
rack_power_distribution_capex = var(
    "econ.rack.power_distribution_capex", "C_pdu_rack", "USD",
    "Rack-level power-distribution, busbar, and rack integration capex.",
    scope="economics",
)
cluster_spine_network_capex = var(
    "econ.cluster.spine_network_capex", "C_spine", "USD",
    "Cluster-scale spine and aggregation network capex.",
    scope="economics",
)
cluster_storage_capex = var(
    "econ.cluster.storage_capex", "C_stor_site", "USD",
    "Parallel filesystem and shared-storage capex for the site.",
    scope="economics",
)
building_shell_capex = var(
    "econ.facility.building_shell_capex", "C_bldg", "USD",
    "Building shell and civil works capex allocated to the site.",
    scope="economics",
)
power_infra_capex = var(
    "econ.facility.power_infra_capex", "C_power_fac", "USD",
    "Utility service, switchgear, UPS, transformers, and generator capex.",
    scope="economics",
)
cooling_infra_capex = var(
    "econ.facility.cooling_infra_capex", "C_cool_fac", "USD",
    "Cooling-plant capex, including chillers, CDU plant, tower, and distribution piping.",
    scope="economics",
)
node_capex = var(
    "econ.node.capex", "C_node", "USD",
    "All-in capex of one compute node.",
    scope="economics",
)
rack_capex = var(
    "econ.rack.capex", "C_rack", "USD",
    "All-in capex of one compute rack.",
    scope="economics",
)
cluster_it_capex = var(
    "econ.cluster.it_capex", "C_IT_site", "USD",
    "IT-side capex of the site, including compute, network, and shared storage.",
    scope="economics",
)
cluster_facility_capex = var(
    "econ.cluster.facility_capex", "C_fac_site", "USD",
    "Facility-side capex of the site, excluding the IT equipment itself.",
    scope="economics",
)
cluster_capex_total = var(
    "econ.cluster.capex_total", "C_site", "USD",
    "Total site capex.",
    scope="economics",
)
cluster_residual_value = var(
    "econ.cluster.residual_value", "C_resid_site", "USD",
    "Residual site value at the end of the depreciation horizon.",
    scope="economics",
)
cluster_depreciable_base = var(
    "econ.cluster.depreciable_base", "C_dep_site", "USD",
    "Depreciable site capex after residual value is removed.",
    scope="economics",
)
cluster_capex_rate = var(
    "econ.cluster.capex_rate", "Cdot_site", "USD/s",
    "Straight-line site capex charge per second before utilization allocation.",
    scope="economics",
)
cluster_utilization = var(
    "econ.cluster.utilization", "u_site", "dimensionless",
    "Fraction of time the site is productively used by billable jobs.",
    scope="economics",
)
job_share_of_cluster = var(
    "econ.job.share_of_cluster", "f_job", "dimensionless",
    "Fraction of the site's GPU fleet allocated to the training job.",
    scope="economics",
)
allocated_fixed_cost_factor = var(
    "econ.job.allocated_fixed_cost_factor", "k_alloc", "dimensionless",
    "Fixed-cost allocation factor after accounting for both job share and cluster utilization.",
    scope="economics",
)
job_capex_rate = var(
    "econ.job.capex_rate", "Cdot_job_cap", "USD/s",
    "Allocated site capex charge rate attributed to the training job.",
    scope="economics",
)


eq_node_capex = eq(
    "econ.eq.node_capex",
    node_capex.symbol,
    n_gpus_per_node.symbol * gpu_capex.symbol
    + node_cpu_capex.symbol
    + node_dram_capex.symbol
    + node_nic_capex.symbol
    + node_storage_capex.symbol
    + node_chassis_capex.symbol,
    "Node capex equals GPU capex plus CPU, DRAM, NIC, storage, and chassis capex.",
)

eq_rack_capex = eq(
    "econ.eq.rack_capex",
    rack_capex.symbol,
    n_nodes_per_rack.symbol * node_capex.symbol + rack_switch_capex.symbol + rack_power_distribution_capex.symbol,
    "Rack capex equals nodes per rack times node capex plus rack switch and power-distribution capex.",
)

eq_cluster_it_capex = eq(
    "econ.eq.cluster_it_capex",
    cluster_it_capex.symbol,
    n_racks_cluster.symbol * rack_capex.symbol + cluster_spine_network_capex.symbol + cluster_storage_capex.symbol,
    "Site IT capex equals rack capex plus cluster-scale spine-network and shared-storage capex.",
)

eq_cluster_facility_capex = eq(
    "econ.eq.cluster_facility_capex",
    cluster_facility_capex.symbol,
    building_shell_capex.symbol + power_infra_capex.symbol + cooling_infra_capex.symbol,
    "Site facility capex equals building, power infrastructure, and cooling infrastructure capex.",
)

eq_cluster_capex_total = eq(
    "econ.eq.cluster_capex_total",
    cluster_capex_total.symbol,
    cluster_it_capex.symbol + cluster_facility_capex.symbol,
    "Total site capex equals IT capex plus facility capex.",
)

eq_cluster_residual_value = eq(
    "econ.eq.cluster_residual_value",
    cluster_residual_value.symbol,
    residual_value_fraction.symbol * cluster_capex_total.symbol,
    "Site residual value equals residual fraction times total site capex.",
)

eq_cluster_depreciable_base = eq(
    "econ.eq.cluster_depreciable_base",
    cluster_depreciable_base.symbol,
    cluster_capex_total.symbol - cluster_residual_value.symbol,
    "Site depreciable base equals total capex minus residual value.",
)

eq_cluster_capex_rate = eq(
    "econ.eq.cluster_capex_rate",
    cluster_capex_rate.symbol,
    cluster_depreciable_base.symbol / useful_life.symbol,
    "Site capex charge rate equals depreciable site capex divided by useful life.",
)

eq_job_share_of_cluster = eq(
    "econ.eq.job_share_of_cluster",
    job_share_of_cluster.symbol,
    n_gpus_total.symbol / cluster_n_gpus.symbol,
    "Job share of cluster equals training-job GPUs divided by total site GPUs.",
)

eq_allocated_fixed_cost_factor = eq(
    "econ.eq.allocated_fixed_cost_factor",
    allocated_fixed_cost_factor.symbol,
    job_share_of_cluster.symbol / cluster_utilization.symbol,
    "Fixed-cost allocation factor equals job share divided by site utilization.",
)

eq_job_capex_rate = eq(
    "econ.eq.job_capex_rate",
    job_capex_rate.symbol,
    cluster_capex_rate.symbol * allocated_fixed_cost_factor.symbol,
    "Allocated job capex rate equals site capex rate scaled by fixed-cost allocation factor.",
)


# ---------------------------------------------------------------------------
# Energy, tariff, and variable operating cost
# ---------------------------------------------------------------------------

job_dc_power = var(
    "econ.job.dc_power", "P_job_dc", "W",
    "Allocated share of total site electrical power attributed to the training job.",
    scope="economics",
)
price_kwh_peak = var(
    "econ.power.price_kwh_peak", "p_kWh_peak", "USD/(kW*h)",
    "Peak-period electricity price.",
    scope="economics",
)
price_kwh_offpeak = var(
    "econ.power.price_kwh_offpeak", "p_kWh_off", "USD/(kW*h)",
    "Off-peak electricity price.",
    scope="economics",
)
peak_energy_fraction = var(
    "econ.power.peak_energy_fraction", "f_peak", "dimensionless",
    "Fraction of the training run's energy billed at the peak tariff.",
    scope="economics",
)
price_kwh = var(
    "econ.power.price_kwh", "p_kWh", "USD/(kW*h)",
    "Blended electricity price after peak and off-peak weighting.",
    scope="economics",
)
cost_per_watt_sec = var(
    "econ.power.price_ws", "p_Ws", "USD/(W*s)",
    "Electricity price in USD per watt-second.",
    scope="economics",
)
peak_demand_kw = var(
    "econ.power.peak_demand_kw", "P_job_peak_kW", "kW",
    "Allocated peak demand of the training job for capacity-charge accounting.",
    scope="economics",
)
capacity_charge_kw_month = var(
    "econ.power.capacity_charge_kw_month", "p_cap", "USD/(kW*month)",
    "Capacity charge per kilowatt of peak demand per month.",
    scope="economics",
)
capacity_charge_rate = var(
    "econ.power.capacity_charge_rate", "Cdot_cap", "USD/s",
    "Demand-charge cost rate allocated to the training job.",
    scope="economics",
)
water_price_per_liter = var(
    "econ.water.price_per_liter", "p_L", "USD/L",
    "Water price per liter including treatment and discharge costs.",
    scope="economics",
)
water_cost_rate = var(
    "econ.water.cost_rate", "Cdot_water", "USD/s",
    "Water cost rate attributed to the training job.",
    scope="economics",
)
maintenance_fraction_per_year = var(
    "econ.maintenance.fraction_per_year", "f_maint_y", "1/year",
    "Annual maintenance cost as a fraction of total site capex.",
    scope="economics",
)
maintenance_cost_rate = var(
    "econ.maintenance.cost_rate", "Cdot_maint", "USD/s",
    "Site maintenance cost rate before job-level allocation.",
    scope="economics",
)
staff_cost_rate = var(
    "econ.staff.cost_rate", "Cdot_staff", "USD/s",
    "Cluster-operations staff cost rate before job-level allocation.",
    scope="economics",
)
network_transit_price_per_gb = var(
    "econ.network.transit_price_per_gb", "p_GB_transit", "USD/GB",
    "Network transit price per gigabyte.",
    scope="economics",
)
network_egress_bytes_per_s = var(
    "econ.network.egress_bytes_per_s", "BW_egress", "byte/s",
    "Average job-specific WAN or cross-region egress bandwidth.",
    scope="economics",
)
network_transit_cost_rate = var(
    "econ.network.transit_cost_rate", "Cdot_net", "USD/s",
    "Network-transit cost rate attributed to the training job.",
    scope="economics",
)
carbon_intensity_kg_per_kwh = var(
    "econ.carbon.intensity_kg_per_kwh", "I_CO2", "kg/(kW*h)",
    "Grid carbon intensity in kilograms of CO2e per kilowatt-hour.",
    scope="economics",
)
carbon_emission_rate = var(
    "econ.carbon.emission_rate", "mdot_CO2", "kg/s",
    "Carbon-emission rate attributed to the training job.",
    scope="economics",
)
carbon_price_per_tonne = var(
    "econ.carbon.price_per_tonne", "p_CO2", "USD/t",
    "Actual or shadow carbon price per metric tonne of CO2e.",
    scope="economics",
)
carbon_cost_rate = var(
    "econ.carbon.cost_rate", "Cdot_CO2", "USD/s",
    "Carbon cost rate attributed to the training job.",
    scope="economics",
)


eq_job_dc_power = eq(
    "econ.eq.job_dc_power",
    job_dc_power.symbol,
    job_share_of_cluster.symbol * dc_total_power.symbol,
    "Allocated job DC power equals job share times total site electrical power.",
)

eq_price_kwh = eq(
    "econ.eq.price_kwh",
    price_kwh.symbol,
    peak_energy_fraction.symbol * price_kwh_peak.symbol + (1 - peak_energy_fraction.symbol) * price_kwh_offpeak.symbol,
    "Blended electricity price equals the weighted combination of peak and off-peak tariffs.",
)

eq_ws_from_kwh = eq(
    "econ.eq.ws_from_kwh",
    cost_per_watt_sec.symbol,
    price_kwh.symbol / sp.Integer(3_600_000),
    "One kilowatt-hour is 3.6e6 watt-seconds, so blended $/kWh converts directly to $/(W*s).",
)

eq_peak_demand_kw = eq(
    "econ.eq.peak_demand_kw",
    peak_demand_kw.symbol,
    job_dc_power.symbol / sp.Integer(1000),
    "Peak demand in kilowatts equals allocated job power in watts divided by one thousand.",
)

eq_capacity_charge_rate = eq(
    "econ.eq.capacity_charge_rate",
    capacity_charge_rate.symbol,
    capacity_charge_kw_month.symbol * peak_demand_kw.symbol / sp.Integer(2_592_000),
    "Demand-charge rate equals dollars per kilowatt-month times peak kilowatts, converted to a per-second rate using a 30-day month.",
)

eq_water_cost_rate = eq(
    "econ.eq.water_cost_rate",
    water_cost_rate.symbol,
    water_price_per_liter.symbol * water_usage_rate.symbol * job_share_of_cluster.symbol,
    "Job water cost rate equals liters per second times price per liter, scaled by job share of site activity.",
)

eq_maintenance_cost_rate = eq(
    "econ.eq.maintenance_cost_rate",
    maintenance_cost_rate.symbol,
    maintenance_fraction_per_year.symbol * cluster_capex_total.symbol / sp.Integer(31_536_000),
    "Maintenance cost rate equals annual maintenance fraction times total site capex, converted to seconds using a 365-day year.",
)

eq_network_transit_cost_rate = eq(
    "econ.eq.network_transit_cost_rate",
    network_transit_cost_rate.symbol,
    network_transit_price_per_gb.symbol * network_egress_bytes_per_s.symbol / sp.Integer(1_000_000_000),
    "Network-transit cost rate equals dollars per gigabyte times job-specific gigabytes per second.",
)

eq_carbon_emission_rate = eq(
    "econ.eq.carbon_emission_rate",
    carbon_emission_rate.symbol,
    carbon_intensity_kg_per_kwh.symbol * job_dc_power.symbol / sp.Integer(3_600_000),
    "Carbon-emission rate equals grid carbon intensity times allocated job power, using the standard kWh conversion.",
)

eq_carbon_cost_rate = eq(
    "econ.eq.carbon_cost_rate",
    carbon_cost_rate.symbol,
    carbon_price_per_tonne.symbol * carbon_emission_rate.symbol / sp.Integer(1000),
    "Carbon cost rate equals dollars per tonne times kilograms per second, with one thousand kilograms per tonne.",
)


# ---------------------------------------------------------------------------
# Run cost, step cost, and delivered-work cost
# ---------------------------------------------------------------------------

cost_per_step = var(
    "econ.cost.per_step", "C_step", "USD",
    "Average fully allocated cost per optimizer step over the whole run.",
    scope="economics",
)
cost_per_token = var(
    "econ.cost.per_token", "C_tok", "USD/token",
    "Average fully allocated cost per training token.",
    scope="economics",
)
cost_per_flop = var(
    "econ.cost.per_flop", "C_FLOP", "USD/FLOP",
    "Average fully allocated cost per delivered FLOP.",
    scope="economics",
)
run_hw_cost = var(
    "econ.run.hw_cost", "C_hw_run", "USD",
    "Allocated capex charge of the training run.",
    scope="economics",
)
run_power_cost = var(
    "econ.run.power_cost", "C_pw_run", "USD",
    "Electricity cost of the training run.",
    scope="economics",
)
run_water_cost = var(
    "econ.run.water_cost", "C_water_run", "USD",
    "Water cost of the training run.",
    scope="economics",
)
run_maintenance_cost = var(
    "econ.run.maintenance_cost", "C_maint_run", "USD",
    "Allocated maintenance cost of the training run.",
    scope="economics",
)
run_staff_cost = var(
    "econ.run.staff_cost", "C_staff_run", "USD",
    "Allocated operations-staff cost of the training run.",
    scope="economics",
)
run_network_cost = var(
    "econ.run.network_cost", "C_net_run", "USD",
    "Network-transit cost of the training run.",
    scope="economics",
)
run_capacity_charge_cost = var(
    "econ.run.capacity_charge_cost", "C_capchg_run", "USD",
    "Demand-charge cost of the training run.",
    scope="economics",
)
run_carbon_cost = var(
    "econ.run.carbon_cost", "C_CO2_run", "USD",
    "Carbon cost of the training run.",
    scope="economics",
)
run_opex_misc_cost = var(
    "econ.run.opex_misc_cost", "C_opex_run", "USD",
    "Non-energy opex of the training run.",
    scope="economics",
)
run_cost = var(
    "econ.run.total_cost", "C_run", "USD",
    "Total fully allocated training-run cost.",
    scope="economics",
)


eq_run_hw_cost = eq(
    "econ.eq.run_hw_cost",
    run_hw_cost.symbol,
    job_capex_rate.symbol * T_wallclock.symbol,
    "Run capex charge equals allocated job capex rate times wall-clock duration.",
)

eq_run_power_cost = eq(
    "econ.eq.run_power_cost",
    run_power_cost.symbol,
    cost_per_watt_sec.symbol * job_dc_power.symbol * T_wallclock.symbol,
    "Run electricity cost equals $ per watt-second times allocated job power times wall-clock duration.",
)

eq_run_water_cost = eq(
    "econ.eq.run_water_cost",
    run_water_cost.symbol,
    water_cost_rate.symbol * T_wallclock.symbol,
    "Run water cost equals water cost rate times wall-clock duration.",
)

eq_run_maintenance_cost = eq(
    "econ.eq.run_maintenance_cost",
    run_maintenance_cost.symbol,
    maintenance_cost_rate.symbol * allocated_fixed_cost_factor.symbol * T_wallclock.symbol,
    "Run maintenance cost equals site maintenance rate times fixed-cost allocation factor times wall-clock duration.",
)

eq_run_staff_cost = eq(
    "econ.eq.run_staff_cost",
    run_staff_cost.symbol,
    staff_cost_rate.symbol * allocated_fixed_cost_factor.symbol * T_wallclock.symbol,
    "Run staff cost equals site operations-staff rate times fixed-cost allocation factor times wall-clock duration.",
)

eq_run_network_cost = eq(
    "econ.eq.run_network_cost",
    run_network_cost.symbol,
    network_transit_cost_rate.symbol * T_wallclock.symbol,
    "Run network-transit cost equals network-transit cost rate times wall-clock duration.",
)

eq_run_capacity_charge_cost = eq(
    "econ.eq.run_capacity_charge_cost",
    run_capacity_charge_cost.symbol,
    capacity_charge_rate.symbol * T_wallclock.symbol,
    "Run demand-charge cost equals capacity-charge rate times wall-clock duration.",
)

eq_run_carbon_cost = eq(
    "econ.eq.run_carbon_cost",
    run_carbon_cost.symbol,
    carbon_cost_rate.symbol * T_wallclock.symbol,
    "Run carbon cost equals carbon cost rate times wall-clock duration.",
)

eq_run_opex_misc_cost = eq(
    "econ.eq.run_opex_misc_cost",
    run_opex_misc_cost.symbol,
    run_water_cost.symbol + run_maintenance_cost.symbol + run_staff_cost.symbol + run_network_cost.symbol + run_capacity_charge_cost.symbol + run_carbon_cost.symbol,
    "Miscellaneous run opex sums water, maintenance, staff, network transit, demand charges, and carbon costs.",
)

eq_run_total = eq(
    "econ.eq.run_total",
    run_cost.symbol,
    run_hw_cost.symbol + run_power_cost.symbol + run_opex_misc_cost.symbol,
    "Total run cost equals capex allocation plus power cost plus all other operating costs.",
)

eq_cost_per_step = eq(
    "econ.eq.cost_per_step",
    cost_per_step.symbol,
    run_cost.symbol / n_steps.symbol,
    "Average cost per optimizer step equals total run cost divided by the total number of training steps.",
)

eq_cost_per_token = eq(
    "econ.eq.cost_per_token",
    cost_per_token.symbol,
    run_cost.symbol / N_train_tokens.symbol,
    "Average cost per token equals total run cost divided by total training tokens.",
)

eq_cost_per_flop = eq(
    "econ.eq.cost_per_flop",
    cost_per_flop.symbol,
    run_cost.symbol / (T_wallclock.symbol * achieved_flops_run.symbol),
    "Average cost per delivered FLOP equals total run cost divided by delivered FLOPs over wall-clock time.",
)


# ---------------------------------------------------------------------------
# Cost of capital and recovery targets
# ---------------------------------------------------------------------------

wacc_annual = var(
    "econ.finance.wacc_annual", "r_wacc", "1/year",
    "Annual weighted average cost of capital or internal hurdle rate.",
    scope="economics",
)
discount_factor_run = var(
    "econ.finance.discount_factor_run", "D_run", "dimensionless",
    "Present-value discount factor applied across the run duration.",
    scope="economics",
)
npv_run_cost = var(
    "econ.finance.npv_run_cost", "NPV_run", "USD",
    "Present-value cost of the training run.",
    scope="economics",
)
inference_revenue_per_token = var(
    "econ.recovery.inference_revenue_per_token", "R_tok_inf", "USD/token",
    "Gross revenue captured per served inference token.",
    scope="economics",
)
inference_serving_cost_per_token = var(
    "econ.recovery.inference_serving_cost_per_token", "C_tok_inf", "USD/token",
    "Serving cost per inference token, excluding the amortized training bill being recovered.",
    scope="economics",
)
net_inference_margin_per_token = var(
    "econ.recovery.net_inference_margin_per_token", "M_tok_inf", "USD/token",
    "Net contribution margin per inference token available to recover training cost.",
    scope="economics",
)
inference_tokens_to_recover_run = var(
    "econ.recovery.inference_tokens_to_recover_run", "N_tok_rec", "tokens",
    "Inference tokens required to recover the full training-run cost.",
    scope="economics",
)


eq_discount_factor_run = eq(
    "econ.eq.discount_factor_run",
    discount_factor_run.symbol,
    (1 + wacc_annual.symbol) ** (-T_wallclock.symbol / sp.Integer(31_536_000)),
    "Run discount factor applies annual WACC across wall-clock duration using a 365-day year.",
)

eq_npv_run_cost = eq(
    "econ.eq.npv_run_cost",
    npv_run_cost.symbol,
    run_cost.symbol * discount_factor_run.symbol,
    "Present-value run cost equals nominal run cost times the run discount factor.",
)

eq_net_inference_margin_per_token = eq(
    "econ.eq.net_inference_margin_per_token",
    net_inference_margin_per_token.symbol,
    inference_revenue_per_token.symbol - inference_serving_cost_per_token.symbol,
    "Net inference margin per token equals gross revenue minus serving cost.",
)

eq_inference_tokens_to_recover_run = eq(
    "econ.eq.inference_tokens_to_recover_run",
    inference_tokens_to_recover_run.symbol,
    run_cost.symbol / net_inference_margin_per_token.symbol,
    "Training-cost recovery target equals run cost divided by net inference margin per token.",
)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

sys_econ.add_all([
    gpu_capex,
    useful_life,
    residual_value_fraction,
    gpu_residual_value,
    gpu_hourly_amortized,
    gpu_hourly_rent,
    gpu_rental_markup,
    node_cpu_capex,
    node_dram_capex,
    node_nic_capex,
    node_storage_capex,
    node_chassis_capex,
    rack_switch_capex,
    rack_power_distribution_capex,
    cluster_spine_network_capex,
    cluster_storage_capex,
    building_shell_capex,
    power_infra_capex,
    cooling_infra_capex,
    node_capex,
    rack_capex,
    cluster_it_capex,
    cluster_facility_capex,
    cluster_capex_total,
    cluster_residual_value,
    cluster_depreciable_base,
    cluster_capex_rate,
    cluster_utilization,
    job_share_of_cluster,
    allocated_fixed_cost_factor,
    job_capex_rate,
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
    cost_per_step,
    cost_per_token,
    cost_per_flop,
    run_hw_cost,
    run_power_cost,
    run_water_cost,
    run_maintenance_cost,
    run_staff_cost,
    run_network_cost,
    run_capacity_charge_cost,
    run_carbon_cost,
    run_opex_misc_cost,
    run_cost,
    wacc_annual,
    discount_factor_run,
    npv_run_cost,
    inference_revenue_per_token,
    inference_serving_cost_per_token,
    net_inference_margin_per_token,
    inference_tokens_to_recover_run,
])

sys_econ.add_all([
    eq_gpu_residual_value,
    eq_amortized,
    eq_gpu_rental_markup,
    eq_node_capex,
    eq_rack_capex,
    eq_cluster_it_capex,
    eq_cluster_facility_capex,
    eq_cluster_capex_total,
    eq_cluster_residual_value,
    eq_cluster_depreciable_base,
    eq_cluster_capex_rate,
    eq_job_share_of_cluster,
    eq_allocated_fixed_cost_factor,
    eq_job_capex_rate,
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
    eq_run_hw_cost,
    eq_run_power_cost,
    eq_run_water_cost,
    eq_run_maintenance_cost,
    eq_run_staff_cost,
    eq_run_network_cost,
    eq_run_capacity_charge_cost,
    eq_run_carbon_cost,
    eq_run_opex_misc_cost,
    eq_run_total,
    eq_cost_per_step,
    eq_cost_per_token,
    eq_cost_per_flop,
    eq_discount_factor_run,
    eq_npv_run_cost,
    eq_net_inference_margin_per_token,
    eq_inference_tokens_to_recover_run,
])
