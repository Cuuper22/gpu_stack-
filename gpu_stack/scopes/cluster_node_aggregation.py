"""
Node compute, HBM, and local-storage aggregate declarations.
"""

from .cluster_node_common import BPS, FLOPS, byte, node_aggregation_var


node_peak_flops = node_aggregation_var(
    "cluster.node.peak_flops", "F_node", "FLOP/s",
    "Aggregate peak FLOPs of one node.",
    sp_units=FLOPS,
)
node_peak_flops_power_limited = node_aggregation_var(
    "cluster.node.peak_flops_power_limited", "F_node_pl", "FLOP/s",
    "Power-limited peak FLOPs of one node.",
    sp_units=FLOPS,
)
node_hbm_capacity = node_aggregation_var(
    "cluster.node.hbm_capacity", "B_HBM_node", "byte",
    "Aggregate usable HBM capacity in one node.",
    sp_units=byte,
)
node_hbm_bw = node_aggregation_var(
    "cluster.node.hbm_bw", "BW_HBM_node", "byte/s",
    "Aggregate effective HBM bandwidth in one node.",
    sp_units=BPS,
)
node_local_ssd_capacity = node_aggregation_var(
    "cluster.node.local_ssd.capacity", "B_SSD_node", "byte",
    "Aggregate local SSD capacity in one node.",
    sp_units=byte,
)
node_local_ssd_bw = node_aggregation_var(
    "cluster.node.local_ssd.bw", "BW_SSD_node", "byte/s",
    "Aggregate local SSD bandwidth in one node.",
    sp_units=BPS,
)


CLUSTER_NODE_AGGREGATION_VARIABLES = [
    node_peak_flops,
    node_peak_flops_power_limited,
    node_hbm_capacity,
    node_hbm_bw,
    node_local_ssd_capacity,
    node_local_ssd_bw,
]


__all__ = [
    "node_peak_flops",
    "node_peak_flops_power_limited",
    "node_hbm_capacity",
    "node_hbm_bw",
    "node_local_ssd_capacity",
    "node_local_ssd_bw",
]
