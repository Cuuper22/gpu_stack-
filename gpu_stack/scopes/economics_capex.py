"""
scopes/economics_capex.py
=========================

Capital-expenditure primitives for the economics scope.

This helper collects the node, rack, cluster, and facility capex inputs,
the site-level rollups, residual value, depreciable base, and the straight-line
site capex rate. It also holds job_share_of_cluster, which is the allocation
primitive that every other economics helper consumes.
"""

from ..core import eq, var

from .cluster import cluster_n_gpus, n_gpus_per_node, n_nodes_per_rack, n_racks_cluster
from .parallelism import n_gpus_total


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
job_share_of_cluster = var(
    "econ.job.share_of_cluster", "f_job", "dimensionless",
    "Fraction of the site's GPU fleet allocated to the training job.",
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


ECON_CAPEX_VARIABLES = [
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
    job_share_of_cluster,
]

ECON_CAPEX_EQUATIONS = [
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
]


__all__ = [
    "gpu_capex", "useful_life", "residual_value_fraction",
    "gpu_residual_value", "gpu_hourly_amortized", "gpu_hourly_rent",
    "gpu_rental_markup",
    "node_cpu_capex", "node_dram_capex", "node_nic_capex",
    "node_storage_capex", "node_chassis_capex",
    "rack_switch_capex", "rack_power_distribution_capex",
    "cluster_spine_network_capex", "cluster_storage_capex",
    "building_shell_capex", "power_infra_capex", "cooling_infra_capex",
    "node_capex", "rack_capex", "cluster_it_capex",
    "cluster_facility_capex", "cluster_capex_total",
    "cluster_residual_value", "cluster_depreciable_base",
    "cluster_capex_rate", "job_share_of_cluster",
    "eq_gpu_residual_value", "eq_amortized", "eq_gpu_rental_markup",
    "eq_node_capex", "eq_rack_capex", "eq_cluster_it_capex",
    "eq_cluster_facility_capex", "eq_cluster_capex_total",
    "eq_cluster_residual_value", "eq_cluster_depreciable_base",
    "eq_cluster_capex_rate", "eq_job_share_of_cluster",
    "ECON_CAPEX_VARIABLES", "ECON_CAPEX_EQUATIONS",
]
