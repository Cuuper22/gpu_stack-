"""
Site rollups from rack-level quantities.

This helper owns the uniform-rack aggregation model for compute, memory,
local storage, site fabric bandwidth, IT power, and planning-stage total
site power.
"""

from ..core.units import BPS, FLOPS, WATT, byte
from .cluster_rack import (
    n_nodes_per_rack,
    rack_hbm_bw,
    rack_hbm_capacity,
    rack_local_ssd_bw,
    rack_local_ssd_capacity,
    rack_peak_flops,
    rack_peak_flops_power_limited,
    rack_power,
    rack_scaleout_bisection_bw,
)
from .interconnect import n_gpus_per_rack
from .cluster_site_common import (
    DIMENSIONLESS,
    site_aggregation_eq,
    site_aggregation_var,
    site_power_planning_eq,
    site_power_planning_var,
)


n_racks_cluster = site_aggregation_var(
    "cluster.site.n_racks", "N_rack", "racks",
    "Number of racks in one site.",
    integer=True,
    sp_units=DIMENSIONLESS,
)
cluster_n_nodes = site_aggregation_var(
    "cluster.site.n_nodes", "N_node_site", "nodes",
    "Total nodes in one site.",
    integer=True,
    sp_units=DIMENSIONLESS,
)
cluster_n_gpus = site_aggregation_var(
    "cluster.site.n_gpus", "N_GPU_clust", "GPUs",
    "Total GPUs in one site.",
    integer=True,
    sp_units=DIMENSIONLESS,
)
cluster_peak_flops = site_aggregation_var(
    "cluster.site.peak_flops", "F_clust", "FLOP/s",
    "Aggregate peak FLOPs of one site.",
    sp_units=FLOPS,
)
cluster_peak_flops_power_limited = site_aggregation_var(
    "cluster.site.peak_flops_power_limited", "F_clust_pl", "FLOP/s",
    "Aggregate power-limited peak FLOPs of one site.",
    sp_units=FLOPS,
)
cluster_power_it = site_aggregation_var(
    "cluster.site.power_it", "P_IT", "W",
    "Total IT power of one site, before facility overhead.",
    sp_units=WATT,
)
cluster_hbm_capacity = site_aggregation_var(
    "cluster.site.hbm_capacity", "B_HBM_site", "byte",
    "Aggregate usable HBM capacity of one site.",
    sp_units=byte,
)
cluster_hbm_bw = site_aggregation_var(
    "cluster.site.hbm_bw", "BW_HBM_site", "byte/s",
    "Aggregate effective HBM bandwidth of one site.",
    sp_units=BPS,
)
cluster_local_ssd_capacity = site_aggregation_var(
    "cluster.site.local_ssd.capacity", "B_SSD_site", "byte",
    "Aggregate local SSD capacity of one site.",
    sp_units=byte,
)
cluster_local_ssd_bw = site_aggregation_var(
    "cluster.site.local_ssd.bw", "BW_SSD_site", "byte/s",
    "Aggregate local SSD bandwidth of one site.",
    sp_units=BPS,
)
cluster_nic_bw = site_aggregation_var(
    "cluster.site.nic_bw", "BW_NIC_site", "byte/s",
    "Aggregate scale-out NIC bandwidth of one site.",
    sp_units=BPS,
)
site_power_overhead_factor_est = site_power_planning_var(
    "cluster.site.power_overhead_factor_est", "k_site_pow", "dimensionless",
    "Planning-stage multiplier from IT power to total site power before the detailed facility model is attached.",
    sp_units=DIMENSIONLESS,
)
cluster_total_power_est = site_power_planning_var(
    "cluster.site.power_total_est", "P_site_est", "W",
    "Estimated total site electrical power from a simple planning multiplier.",
    sp_units=WATT,
)
site_flops_per_scaleout_byte = site_aggregation_var(
    "cluster.site.flops_per_scaleout_byte", "AI_site_fabric", "FLOP/byte",
    "Site-level compute to scale-out fabric balance.",
    sp_units=FLOPS / BPS,
)


eq_cluster_n_nodes = site_aggregation_eq(
    "cluster.eq.site_n_nodes",
    cluster_n_nodes.symbol,
    n_racks_cluster.symbol * n_nodes_per_rack.symbol,
    "Site nodes equal racks times nodes per rack.",
    check_units=True,
)

eq_cluster_n_gpus = site_aggregation_eq(
    "cluster.eq.site_n_gpus",
    cluster_n_gpus.symbol,
    n_racks_cluster.symbol * n_gpus_per_rack.symbol,
    "Site GPUs equal racks times GPUs per rack.",
    check_units=True,
)

eq_cluster_peak = site_aggregation_eq(
    "cluster.eq.site_peak_flops",
    cluster_peak_flops.symbol,
    n_racks_cluster.symbol * rack_peak_flops.symbol,
    "Site peak FLOPs equal racks times rack peak FLOPs.",
    check_units=True,
)

eq_cluster_peak_power_limited = site_aggregation_eq(
    "cluster.eq.site_peak_flops_power_limited",
    cluster_peak_flops_power_limited.symbol,
    n_racks_cluster.symbol * rack_peak_flops_power_limited.symbol,
    "Site power-limited peak FLOPs equal racks times rack power-limited peak FLOPs.",
    check_units=True,
)

eq_cluster_power_it = site_aggregation_eq(
    "cluster.eq.site_power_it",
    cluster_power_it.symbol,
    n_racks_cluster.symbol * rack_power.symbol,
    "Site IT power equals racks times rack IT power.",
    check_units=True,
)

eq_cluster_hbm_capacity = site_aggregation_eq(
    "cluster.eq.site_hbm_capacity",
    cluster_hbm_capacity.symbol,
    n_racks_cluster.symbol * rack_hbm_capacity.symbol,
    "Site HBM capacity equals racks times rack HBM capacity.",
    check_units=True,
)

eq_cluster_hbm_bw = site_aggregation_eq(
    "cluster.eq.site_hbm_bw",
    cluster_hbm_bw.symbol,
    n_racks_cluster.symbol * rack_hbm_bw.symbol,
    "Site HBM bandwidth equals racks times rack HBM bandwidth.",
    check_units=True,
)

eq_cluster_local_ssd_capacity = site_aggregation_eq(
    "cluster.eq.site_local_ssd_capacity",
    cluster_local_ssd_capacity.symbol,
    n_racks_cluster.symbol * rack_local_ssd_capacity.symbol,
    "Site local SSD capacity equals racks times rack local SSD capacity.",
    check_units=True,
)

eq_cluster_local_ssd_bw = site_aggregation_eq(
    "cluster.eq.site_local_ssd_bw",
    cluster_local_ssd_bw.symbol,
    n_racks_cluster.symbol * rack_local_ssd_bw.symbol,
    "Site local SSD bandwidth equals racks times rack local SSD bandwidth.",
    check_units=True,
)

eq_cluster_nic_bw = site_aggregation_eq(
    "cluster.eq.site_nic_bw",
    cluster_nic_bw.symbol,
    n_racks_cluster.symbol * rack_scaleout_bisection_bw.symbol,
    "Site scale-out bandwidth equals racks times rack off-rack bisection bandwidth.",
    check_units=True,
)

eq_cluster_total_power_est = site_power_planning_eq(
    "cluster.eq.site_total_power_est",
    cluster_total_power_est.symbol,
    site_power_overhead_factor_est.symbol * cluster_power_it.symbol,
    "Planning-stage total site power equals IT power times a coarse overhead multiplier.",
    check_units=True,
)

eq_site_flops_per_scaleout_byte = site_aggregation_eq(
    "cluster.eq.site_flops_per_scaleout_byte",
    site_flops_per_scaleout_byte.symbol,
    cluster_peak_flops_power_limited.symbol / cluster_nic_bw.symbol,
    "Site compute to scale-out balance equals site power-limited FLOPs divided by aggregate bisection-aware scale-out bandwidth.",
    check_units=True,
)


CLUSTER_SITE_AGGREGATION_VARIABLES = [
    n_racks_cluster,
    cluster_n_nodes,
    cluster_n_gpus,
    cluster_peak_flops,
    cluster_peak_flops_power_limited,
    cluster_power_it,
    cluster_hbm_capacity,
    cluster_hbm_bw,
    cluster_local_ssd_capacity,
    cluster_local_ssd_bw,
    cluster_nic_bw,
    site_power_overhead_factor_est,
    cluster_total_power_est,
    site_flops_per_scaleout_byte,
]

CLUSTER_SITE_AGGREGATION_EQUATIONS = [
    eq_cluster_n_nodes,
    eq_cluster_n_gpus,
    eq_cluster_peak,
    eq_cluster_peak_power_limited,
    eq_cluster_power_it,
    eq_cluster_hbm_capacity,
    eq_cluster_hbm_bw,
    eq_cluster_local_ssd_capacity,
    eq_cluster_local_ssd_bw,
    eq_cluster_nic_bw,
    eq_cluster_total_power_est,
    eq_site_flops_per_scaleout_byte,
]


__all__ = [
    "n_racks_cluster", "cluster_n_nodes", "cluster_n_gpus",
    "cluster_peak_flops", "cluster_peak_flops_power_limited",
    "cluster_power_it", "cluster_hbm_capacity", "cluster_hbm_bw",
    "cluster_local_ssd_capacity", "cluster_local_ssd_bw", "cluster_nic_bw",
    "site_power_overhead_factor_est", "cluster_total_power_est",
    "site_flops_per_scaleout_byte",
    "eq_cluster_n_nodes", "eq_cluster_n_gpus", "eq_cluster_peak",
    "eq_cluster_peak_power_limited", "eq_cluster_power_it",
    "eq_cluster_hbm_capacity", "eq_cluster_hbm_bw",
    "eq_cluster_local_ssd_capacity", "eq_cluster_local_ssd_bw",
    "eq_cluster_nic_bw", "eq_cluster_total_power_est",
    "eq_site_flops_per_scaleout_byte",
]
