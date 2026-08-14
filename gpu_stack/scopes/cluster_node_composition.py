"""
What is inside one node: the bill-of-materials input variables.

These are pure inputs, not derived quantities — you read them off the server
spec sheet: GPUs per node, host CPUs, CPU-side DRAM capacity and bandwidth,
and the local SSD count with per-drive capacity and bandwidth. Everything
else the node scope computes (aggregates, power, NIC injection) is built
from these counts, so this file is where a new server configuration enters
the model.
"""

from .cluster_node_common import BPS, DIMENSIONLESS, byte, node_composition_var


n_gpus_per_node = node_composition_var(
    "cluster.node.n_gpus", "N_G_node", "GPUs",
    "GPUs per server node.",
    integer=True,
    sp_units=DIMENSIONLESS,
)
n_cpus_per_node = node_composition_var(
    "cluster.node.n_cpus", "N_C_node", "CPUs",
    "Host CPUs per server node.",
    integer=True,
    sp_units=DIMENSIONLESS,
)
ram_per_node = node_composition_var(
    "cluster.node.ram", "B_RAM_node", "byte",
    "CPU-side DRAM capacity per node.",
    sp_units=byte,
)
node_dram_bw = node_composition_var(
    "cluster.node.ram_bw", "BW_RAM_node", "byte/s",
    "Aggregate CPU-side DRAM bandwidth per node.",
    sp_units=BPS,
)
node_local_ssd_count = node_composition_var(
    "cluster.node.local_ssd.count", "N_SSD_node", "drives",
    "Number of local SSDs or NVMe drives in one node.",
    integer=True,
    sp_units=DIMENSIONLESS,
)
node_local_ssd_capacity_per_drive = node_composition_var(
    "cluster.node.local_ssd.capacity_per_drive", "B_SSD_drv", "byte",
    "Usable capacity of one local SSD or NVMe drive.",
    sp_units=byte,
)
node_local_ssd_bw_per_drive = node_composition_var(
    "cluster.node.local_ssd.bw_per_drive", "BW_SSD_drv", "byte/s",
    "Sustained streaming bandwidth of one local SSD or NVMe drive.",
    sp_units=BPS,
)


CLUSTER_NODE_COMPOSITION_VARIABLES = [
    n_gpus_per_node,
    n_cpus_per_node,
    ram_per_node,
    node_dram_bw,
    node_local_ssd_count,
    node_local_ssd_capacity_per_drive,
    node_local_ssd_bw_per_drive,
]


__all__ = [
    "n_gpus_per_node",
    "n_cpus_per_node",
    "ram_per_node",
    "node_dram_bw",
    "node_local_ssd_count",
    "node_local_ssd_capacity_per_drive",
    "node_local_ssd_bw_per_drive",
]
