"""
scopes/cluster_rack.py
======================

Rack-level aggregation.

A rack bundles several compute nodes behind shared power distribution and a
top-of-rack switch. This file lifts per-node aggregates up to rack scale,
wires the intra-rack fabric balance through NVLink, and records the
rack-level power-domain failure unit that reliability modeling consumes.
"""

from ..core import eq, var

from .interconnect import bw_nvlink_rack, n_gpus_per_rack
from .cluster_node import (
    n_gpus_per_node,
    node_hbm_bw,
    node_hbm_capacity,
    node_local_ssd_bw,
    node_local_ssd_capacity,
    node_nic_bw,
    node_peak_flops,
    node_peak_flops_power_limited,
    node_power,
)


# ---------------------------------------------------------------------------
# Rack composition and aggregates
# ---------------------------------------------------------------------------

n_nodes_per_rack = var(
    "cluster.rack.n_nodes", "N_node_rack", "nodes/rack",
    "Compute nodes per rack.",
    scope="cluster",
    integer=True,
)
rack_peak_flops = var(
    "cluster.rack.peak_flops", "F_rack", "FLOP/s",
    "Aggregate peak FLOPs in one rack.",
    scope="cluster",
)
rack_peak_flops_power_limited = var(
    "cluster.rack.peak_flops_power_limited", "F_rack_pl", "FLOP/s",
    "Aggregate power-limited peak FLOPs in one rack.",
    scope="cluster",
)
rack_hbm_capacity = var(
    "cluster.rack.hbm_capacity", "B_HBM_rack", "byte",
    "Aggregate usable HBM capacity in one rack.",
    scope="cluster",
)
rack_hbm_bw = var(
    "cluster.rack.hbm_bw", "BW_HBM_rack", "byte/s",
    "Aggregate effective HBM bandwidth in one rack.",
    scope="cluster",
)
rack_local_ssd_capacity = var(
    "cluster.rack.local_ssd.capacity", "B_SSD_rack", "byte",
    "Aggregate local SSD capacity in one rack.",
    scope="cluster",
)
rack_local_ssd_bw = var(
    "cluster.rack.local_ssd.bw", "BW_SSD_rack", "byte/s",
    "Aggregate local SSD bandwidth in one rack.",
    scope="cluster",
)
rack_nic_bw = var(
    "cluster.rack.nic_bw", "BW_NIC_rack", "byte/s",
    "Aggregate scale-out NIC bandwidth in one rack.",
    scope="cluster",
)
rack_power = var(
    "cluster.rack.power", "P_rack_W", "W",
    "Total IT power drawn by one rack.",
    scope="cluster",
)
rack_gpus_per_power_domain = var(
    "cluster.rack.gpus_per_power_domain", "N_GPU_pd", "GPUs",
    "GPUs that can disappear together when a shared power domain fails.",
    scope="cluster",
    integer=True,
)
nodes_per_power_domain = var(
    "cluster.rel.nodes_per_power_domain", "N_node_pd", "nodes",
    "Nodes attached to one shared rack-level or row-level power domain.",
    scope="cluster",
    integer=True,
)
rack_flops_per_intra_byte = var(
    "cluster.rack.flops_per_intra_byte", "AI_rack_intra", "FLOP/byte",
    "Rack-level compute to intra-rack fabric balance using NVLink-rack bandwidth.",
    scope="cluster",
)


eq_rack_gpu_count = eq(
    "cluster.eq.rack_gpu_count",
    n_gpus_per_rack.symbol,
    n_nodes_per_rack.symbol * n_gpus_per_node.symbol,
    "GPUs per rack equal nodes per rack times GPUs per node.",
)

eq_rack_peak_flops = eq(
    "cluster.eq.rack_peak_flops",
    rack_peak_flops.symbol,
    n_nodes_per_rack.symbol * node_peak_flops.symbol,
    "Rack peak FLOPs equal nodes per rack times node peak FLOPs.",
)

eq_rack_peak_flops_power_limited = eq(
    "cluster.eq.rack_peak_flops_power_limited",
    rack_peak_flops_power_limited.symbol,
    n_nodes_per_rack.symbol * node_peak_flops_power_limited.symbol,
    "Rack power-limited peak FLOPs equal nodes per rack times node power-limited peak FLOPs.",
)

eq_rack_hbm_capacity = eq(
    "cluster.eq.rack_hbm_capacity",
    rack_hbm_capacity.symbol,
    n_nodes_per_rack.symbol * node_hbm_capacity.symbol,
    "Rack HBM capacity equals nodes per rack times node HBM capacity.",
)

eq_rack_hbm_bw = eq(
    "cluster.eq.rack_hbm_bw",
    rack_hbm_bw.symbol,
    n_nodes_per_rack.symbol * node_hbm_bw.symbol,
    "Rack HBM bandwidth equals nodes per rack times node HBM bandwidth.",
)

eq_rack_local_ssd_capacity = eq(
    "cluster.eq.rack_local_ssd_capacity",
    rack_local_ssd_capacity.symbol,
    n_nodes_per_rack.symbol * node_local_ssd_capacity.symbol,
    "Rack local SSD capacity equals nodes per rack times node local storage capacity.",
)

eq_rack_local_ssd_bw = eq(
    "cluster.eq.rack_local_ssd_bw",
    rack_local_ssd_bw.symbol,
    n_nodes_per_rack.symbol * node_local_ssd_bw.symbol,
    "Rack local SSD bandwidth equals nodes per rack times node local storage bandwidth.",
)

eq_rack_nic_bw = eq(
    "cluster.eq.rack_nic_bw",
    rack_nic_bw.symbol,
    n_nodes_per_rack.symbol * node_nic_bw.symbol,
    "Rack NIC bandwidth equals nodes per rack times node NIC bandwidth.",
)

eq_rack_power = eq(
    "cluster.eq.rack_power",
    rack_power.symbol,
    n_nodes_per_rack.symbol * node_power.symbol,
    "Rack IT power equals nodes per rack times node power.",
)

eq_rack_gpus_per_power_domain = eq(
    "cluster.eq.rack_gpus_per_power_domain",
    rack_gpus_per_power_domain.symbol,
    n_gpus_per_node.symbol * nodes_per_power_domain.symbol,
    "GPUs lost in one shared rack power-domain failure equal GPUs per node times nodes served by that power domain.",
)

eq_rack_flops_per_intra_byte = eq(
    "cluster.eq.rack_flops_per_intra_byte",
    rack_flops_per_intra_byte.symbol,
    rack_peak_flops_power_limited.symbol / bw_nvlink_rack.symbol,
    "Rack compute to NVLink-rack balance equals rack power-limited FLOPs divided by aggregate intra-rack fabric bandwidth.",
)


CLUSTER_RACK_VARIABLES = [
    n_nodes_per_rack,
    rack_peak_flops,
    rack_peak_flops_power_limited,
    rack_hbm_capacity,
    rack_hbm_bw,
    rack_local_ssd_capacity,
    rack_local_ssd_bw,
    rack_nic_bw,
    rack_power,
    rack_gpus_per_power_domain,
    nodes_per_power_domain,
    rack_flops_per_intra_byte,
]

CLUSTER_RACK_EQUATIONS = [
    eq_rack_gpu_count,
    eq_rack_peak_flops,
    eq_rack_peak_flops_power_limited,
    eq_rack_hbm_capacity,
    eq_rack_hbm_bw,
    eq_rack_local_ssd_capacity,
    eq_rack_local_ssd_bw,
    eq_rack_nic_bw,
    eq_rack_power,
    eq_rack_gpus_per_power_domain,
    eq_rack_flops_per_intra_byte,
]


__all__ = [
    "n_nodes_per_rack", "rack_peak_flops", "rack_peak_flops_power_limited",
    "rack_hbm_capacity", "rack_hbm_bw",
    "rack_local_ssd_capacity", "rack_local_ssd_bw",
    "rack_nic_bw", "rack_power",
    "rack_gpus_per_power_domain", "nodes_per_power_domain",
    "rack_flops_per_intra_byte",
    "eq_rack_gpu_count", "eq_rack_peak_flops",
    "eq_rack_peak_flops_power_limited",
    "eq_rack_hbm_capacity", "eq_rack_hbm_bw",
    "eq_rack_local_ssd_capacity", "eq_rack_local_ssd_bw",
    "eq_rack_nic_bw", "eq_rack_power",
    "eq_rack_gpus_per_power_domain", "eq_rack_flops_per_intra_byte",
    "CLUSTER_RACK_VARIABLES", "CLUSTER_RACK_EQUATIONS",
]
