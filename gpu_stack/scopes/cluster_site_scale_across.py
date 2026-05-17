"""
Hyperscaler and scale-across WAN-link declarations.

This helper aggregates one site into uniform-site hyperscaler totals and
models inter-site bandwidth and latency for scale-across communication.
"""

from ..core.units import BPS, FLOPS, SECOND, WATT, byte
from .cluster_site_aggregation import (
    cluster_hbm_capacity,
    cluster_local_ssd_capacity,
    cluster_n_gpus,
    cluster_peak_flops,
    cluster_total_power_est,
)
from .cluster_site_common import DIMENSIONLESS, scale_across_eq, scale_across_var


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


CLUSTER_SITE_SCALE_ACROSS_VARIABLES = [
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

CLUSTER_SITE_SCALE_ACROSS_EQUATIONS = [
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
    "n_sites_hs", "hs_n_gpus", "hs_peak_flops", "hs_total_power",
    "hs_hbm_capacity", "hs_local_ssd_capacity",
    "wan_links_per_site", "bw_wan_link", "eta_scale_across",
    "bw_scale_across_site", "bw_scale_across", "lat_scale_across",
    "scale_across_msg_size", "scale_across_transfer_time",
    "eq_hs_n_gpus", "eq_hs_peak", "eq_hs_total_power",
    "eq_hs_hbm_capacity", "eq_hs_local_ssd_capacity",
    "eq_bw_scale_across_site", "eq_bw_scale_across",
    "eq_scale_across_transfer_time",
]
