"""
scopes/cluster_site.py
======================

Site-level aggregation, scheduler overhead, and hyperscaler scale-across.

A site is one data-center building, one set of utility feeds, and one set of
facility boundaries. This file lifts rack aggregates into site totals, carries
scheduler and provisioning overhead that operates at the site level, and
extends aggregation one step further into hyperscaler scale-across WAN
capacity and latency. The detailed facility cooling and power model lives in
`thermal.py`; the site totals here stop at IT power plus a coarse planning
overhead so `thermal.py` has something to attach to.
"""

from ..core import Reference
from ..core.units import BPS, FLOPS, SECOND, WATT, byte

from .interconnect import n_gpus_per_rack
from .cluster_rack import (
    n_nodes_per_rack,
    rack_hbm_bw,
    rack_hbm_capacity,
    rack_local_ssd_bw,
    rack_local_ssd_capacity,
    rack_scaleout_bisection_bw,
    rack_peak_flops,
    rack_peak_flops_power_limited,
    rack_power,
)
from .cluster_ops_declarations import (
    DIMENSIONLESS,
    referenced_eq,
    scoped_var,
)

SITE_AGGREGATION_REF = Reference(
    "Site aggregate compute, memory, local-storage, bandwidth, and IT-power "
    "quantities are rack-level rollups under a uniform-rack planning model.",
    kind="model",
)

SITE_POWER_PLANNING_REF = Reference(
    "Planning-stage site power applies a coarse facility overhead multiplier "
    "to IT power before the detailed thermal and facility model is attached.",
    kind="model",
)

SCHEDULER_OVERHEAD_REF = Reference(
    "Scheduler start delay is decomposed into queue wait, allocation, and "
    "provisioning terms before first useful training work begins.",
    kind="model",
)

SCALE_ACROSS_REF = Reference(
    "Scale-across WAN capacity is modeled from per-site long-haul link count, "
    "per-link payload bandwidth, transport efficiency, message size, and "
    "one-way latency.",
    kind="model",
)


site_aggregation_var = scoped_var("cluster", SITE_AGGREGATION_REF)
site_power_planning_var = scoped_var("cluster", SITE_POWER_PLANNING_REF)
scheduler_overhead_var = scoped_var("cluster", SCHEDULER_OVERHEAD_REF)
scale_across_var = scoped_var("cluster", SCALE_ACROSS_REF)

site_aggregation_eq = referenced_eq(SITE_AGGREGATION_REF)
site_power_planning_eq = referenced_eq(SITE_POWER_PLANNING_REF)
scheduler_overhead_eq = referenced_eq(SCHEDULER_OVERHEAD_REF)
scale_across_eq = referenced_eq(SCALE_ACROSS_REF)


# ---------------------------------------------------------------------------
# Site aggregation
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Scheduler and provisioning overhead
# ---------------------------------------------------------------------------

scheduler_queue_wait = scheduler_overhead_var(
    "cluster.sched.queue_wait", "T_queue", "s",
    "Time a job spends waiting in the scheduler queue.",
    sp_units=SECOND,
)
scheduler_allocation_time = scheduler_overhead_var(
    "cluster.sched.allocation_time", "T_alloc", "s",
    "Control-plane time to allocate nodes, wire up containers, and stage the job.",
    sp_units=SECOND,
)
provisioning_time = scheduler_overhead_var(
    "cluster.sched.provisioning_time", "T_prov", "s",
    "Time spent on image pull, filesystem mounts, and runtime startup.",
    sp_units=SECOND,
)
job_start_delay = scheduler_overhead_var(
    "cluster.sched.job_start_delay", "T_start_delay", "s",
    "End-to-end delay between job submission and first training step.",
    sp_units=SECOND,
)


eq_job_start_delay = scheduler_overhead_eq(
    "cluster.eq.job_start_delay",
    job_start_delay.symbol,
    scheduler_queue_wait.symbol + scheduler_allocation_time.symbol + provisioning_time.symbol,
    "Job start delay equals queue wait plus scheduler allocation plus provisioning time.",
    check_units=True,
)


# ---------------------------------------------------------------------------
# Hyperscaler and scale-across WAN links
# ---------------------------------------------------------------------------

n_sites_hs = scale_across_var(
    "cluster.hs.n_sites", "N_DC", "sites",
    "Number of sites operated by the hyperscaler.",
    integer=True,
    sp_units=DIMENSIONLESS,
)
hs_n_gpus = scale_across_var(
    "cluster.hs.n_gpus", "N_GPU_hs", "GPUs",
    "Total GPUs across all sites.",
    integer=True,
    sp_units=DIMENSIONLESS,
)
hs_peak_flops = scale_across_var(
    "cluster.hs.peak_flops", "F_hs", "FLOP/s",
    "Aggregate peak FLOPs across all sites.",
    sp_units=FLOPS,
)
hs_total_power = scale_across_var(
    "cluster.hs.power_total", "P_hs_tot", "W",
    "Estimated total electrical load across all sites.",
    sp_units=WATT,
)
hs_hbm_capacity = scale_across_var(
    "cluster.hs.hbm_capacity", "B_HBM_hs", "byte",
    "Aggregate usable HBM capacity across all sites.",
    sp_units=byte,
)
hs_local_ssd_capacity = scale_across_var(
    "cluster.hs.local_ssd.capacity", "B_SSD_hs", "byte",
    "Aggregate local SSD capacity across all sites.",
    sp_units=byte,
)
wan_links_per_site = scale_across_var(
    "cluster.hs.scale_across.links_per_site", "N_WAN_site", "links/site",
    "Number of long-haul or inter-DC links attached to one site for scale-across training or checkpoint replication.",
    integer=True,
    sp_units=DIMENSIONLESS,
)
bw_wan_link = scale_across_var(
    "cluster.hs.scale_across.bw_per_link", "BW_WAN_link", "byte/s",
    "Payload bandwidth of one inter-site link.",
    sp_units=BPS,
)
eta_scale_across = scale_across_var(
    "cluster.hs.scale_across.efficiency", "eta_SA", "dimensionless",
    "Protocol and utilization efficiency of the inter-site transport path.",
    sp_units=DIMENSIONLESS,
)
bw_scale_across_site = scale_across_var(
    "cluster.hs.scale_across.bw_per_site", "BW_SA_site", "byte/s",
    "Aggregate effective inter-site bandwidth available to one site.",
    sp_units=BPS,
)
bw_scale_across = scale_across_var(
    "cluster.hs.scale_across_bw", "BW_SA", "byte/s",
    "Effective inter-site bandwidth per GPU when a whole site participates in scale-across training.",
    sp_units=BPS,
)
lat_scale_across = scale_across_var(
    "cluster.hs.scale_across_latency", "L_SA", "s",
    "One-way inter-site latency for scale-across communication.",
    sp_units=SECOND,
)
scale_across_msg_size = scale_across_var(
    "cluster.hs.scale_across_msg_size", "B_SA_msg", "byte",
    "Representative message size moved across sites.",
    sp_units=byte,
)
scale_across_transfer_time = scale_across_var(
    "cluster.hs.scale_across_transfer_time", "T_SA_msg", "s",
    "Transfer time for one representative inter-site message.",
    sp_units=SECOND,
)


eq_hs_n_gpus = scale_across_eq(
    "cluster.eq.hs_n_gpus",
    hs_n_gpus.symbol,
    n_sites_hs.symbol * cluster_n_gpus.symbol,
    "Hyperscaler GPUs equal sites times GPUs per site under a uniform-site planning assumption.",
    check_units=True,
)

eq_hs_peak = scale_across_eq(
    "cluster.eq.hs_peak_flops",
    hs_peak_flops.symbol,
    n_sites_hs.symbol * cluster_peak_flops.symbol,
    "Hyperscaler peak FLOPs equal sites times site peak FLOPs under a uniform-site planning assumption.",
    check_units=True,
)

eq_hs_total_power = scale_across_eq(
    "cluster.eq.hs_total_power",
    hs_total_power.symbol,
    n_sites_hs.symbol * cluster_total_power_est.symbol,
    "Hyperscaler total electrical load is estimated as sites times estimated site power.",
    check_units=True,
)

eq_hs_hbm_capacity = scale_across_eq(
    "cluster.eq.hs_hbm_capacity",
    hs_hbm_capacity.symbol,
    n_sites_hs.symbol * cluster_hbm_capacity.symbol,
    "Hyperscaler HBM capacity equals sites times site HBM capacity.",
    check_units=True,
)

eq_hs_local_ssd_capacity = scale_across_eq(
    "cluster.eq.hs_local_ssd_capacity",
    hs_local_ssd_capacity.symbol,
    n_sites_hs.symbol * cluster_local_ssd_capacity.symbol,
    "Hyperscaler local SSD capacity equals sites times site local SSD capacity.",
    check_units=True,
)

eq_bw_scale_across_site = scale_across_eq(
    "cluster.eq.scale_across_bw_per_site",
    bw_scale_across_site.symbol,
    wan_links_per_site.symbol * bw_wan_link.symbol * eta_scale_across.symbol,
    "Per-site scale-across bandwidth equals link count times per-link bandwidth times transport efficiency.",
    check_units=True,
)

eq_bw_scale_across = scale_across_eq(
    "cluster.eq.scale_across_bw_per_gpu",
    bw_scale_across.symbol,
    bw_scale_across_site.symbol / cluster_n_gpus.symbol,
    "Per-GPU inter-site bandwidth equals per-site WAN bandwidth divided by GPUs sharing it.",
    check_units=True,
)

eq_scale_across_transfer_time = scale_across_eq(
    "cluster.eq.scale_across_transfer_time",
    scale_across_transfer_time.symbol,
    lat_scale_across.symbol + scale_across_msg_size.symbol / bw_scale_across_site.symbol,
    "A first-order inter-site transfer time equals path latency plus bytes divided by sustained per-site WAN bandwidth.",
    check_units=True,
)


CLUSTER_SITE_VARIABLES = [
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
    scheduler_queue_wait,
    scheduler_allocation_time,
    provisioning_time,
    job_start_delay,
    n_sites_hs,
    hs_n_gpus,
    hs_peak_flops,
    hs_total_power,
    hs_hbm_capacity,
    hs_local_ssd_capacity,
    wan_links_per_site,
    bw_wan_link,
    eta_scale_across,
    bw_scale_across_site,
    bw_scale_across,
    lat_scale_across,
    scale_across_msg_size,
    scale_across_transfer_time,
]

CLUSTER_SITE_EQUATIONS = [
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
    eq_job_start_delay,
    eq_hs_n_gpus,
    eq_hs_peak,
    eq_hs_total_power,
    eq_hs_hbm_capacity,
    eq_hs_local_ssd_capacity,
    eq_bw_scale_across_site,
    eq_bw_scale_across,
    eq_scale_across_transfer_time,
]


__all__ = [
    "n_racks_cluster", "cluster_n_nodes", "cluster_n_gpus",
    "cluster_peak_flops", "cluster_peak_flops_power_limited",
    "cluster_power_it", "cluster_hbm_capacity", "cluster_hbm_bw",
    "cluster_local_ssd_capacity", "cluster_local_ssd_bw", "cluster_nic_bw",
    "site_power_overhead_factor_est", "cluster_total_power_est",
    "site_flops_per_scaleout_byte",
    "scheduler_queue_wait", "scheduler_allocation_time", "provisioning_time",
    "job_start_delay",
    "n_sites_hs", "hs_n_gpus", "hs_peak_flops", "hs_total_power",
    "hs_hbm_capacity", "hs_local_ssd_capacity",
    "wan_links_per_site", "bw_wan_link", "eta_scale_across",
    "bw_scale_across_site", "bw_scale_across", "lat_scale_across",
    "scale_across_msg_size", "scale_across_transfer_time",
    "eq_cluster_n_nodes", "eq_cluster_n_gpus", "eq_cluster_peak",
    "eq_cluster_peak_power_limited", "eq_cluster_power_it",
    "eq_cluster_hbm_capacity", "eq_cluster_hbm_bw",
    "eq_cluster_local_ssd_capacity", "eq_cluster_local_ssd_bw",
    "eq_cluster_nic_bw", "eq_cluster_total_power_est",
    "eq_site_flops_per_scaleout_byte", "eq_job_start_delay",
    "eq_hs_n_gpus", "eq_hs_peak", "eq_hs_total_power",
    "eq_hs_hbm_capacity", "eq_hs_local_ssd_capacity",
    "eq_bw_scale_across_site", "eq_bw_scale_across",
    "eq_scale_across_transfer_time",
    "CLUSTER_SITE_VARIABLES", "CLUSTER_SITE_EQUATIONS",
]
