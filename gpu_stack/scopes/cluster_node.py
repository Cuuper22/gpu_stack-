"""
scopes/cluster_node.py
======================

Node-level composition and aggregates.

A node is one server chassis carrying GPUs, host CPU, DRAM, NIC, and local
storage. This file defines those raw inputs and the per-node aggregates that
downstream rack and site files consume.
"""

from ..core import eq, var

from .gpu import (
    nic_bw_per_gpu_effective,
    p_gpu_total,
    peak_flops_gpu,
    peak_flops_gpu_power_limited,
)
from .memory_subsystem import hbm_bw_effective, hbm_effective_capacity


# ---------------------------------------------------------------------------
# Node composition
# ---------------------------------------------------------------------------

n_gpus_per_node = var(
    "cluster.node.n_gpus", "N_G_node", "GPUs",
    "GPUs per server node.",
    scope="cluster",
    integer=True,
)
n_cpus_per_node = var(
    "cluster.node.n_cpus", "N_C_node", "CPUs",
    "Host CPUs per server node.",
    scope="cluster",
    integer=True,
)
ram_per_node = var(
    "cluster.node.ram", "B_RAM_node", "byte",
    "CPU-side DRAM capacity per node.",
    scope="cluster",
)
node_dram_bw = var(
    "cluster.node.ram_bw", "BW_RAM_node", "byte/s",
    "Aggregate CPU-side DRAM bandwidth per node.",
    scope="cluster",
)
node_local_ssd_count = var(
    "cluster.node.local_ssd.count", "N_SSD_node", "drives",
    "Number of local SSDs or NVMe drives in one node.",
    scope="cluster",
    integer=True,
)
node_local_ssd_capacity_per_drive = var(
    "cluster.node.local_ssd.capacity_per_drive", "B_SSD_drv", "byte",
    "Usable capacity of one local SSD or NVMe drive.",
    scope="cluster",
)
node_local_ssd_bw_per_drive = var(
    "cluster.node.local_ssd.bw_per_drive", "BW_SSD_drv", "byte/s",
    "Sustained streaming bandwidth of one local SSD or NVMe drive.",
    scope="cluster",
)
cpu_power_node = var(
    "cluster.node.cpu_power", "P_cpu_node", "W",
    "CPU package power per node.",
    scope="cluster",
)
ram_power_node = var(
    "cluster.node.ram_power", "P_ram_node", "W",
    "CPU-side DRAM power per node.",
    scope="cluster",
)
nic_power_node = var(
    "cluster.node.nic_power", "P_nic_node", "W",
    "NIC and retimer power per node.",
    scope="cluster",
)
storage_power_node = var(
    "cluster.node.storage_power", "P_stor_node", "W",
    "Local storage power per node.",
    scope="cluster",
)
misc_power_node = var(
    "cluster.node.misc_power", "P_misc_node", "W",
    "Remaining node-level power, for fans, BMCs, and motherboard losses.",
    scope="cluster",
)


# ---------------------------------------------------------------------------
# Node-level aggregates
# ---------------------------------------------------------------------------

node_peak_flops = var(
    "cluster.node.peak_flops", "F_node", "FLOP/s",
    "Aggregate peak FLOPs of one node.",
    scope="cluster",
)
node_peak_flops_power_limited = var(
    "cluster.node.peak_flops_power_limited", "F_node_pl", "FLOP/s",
    "Power-limited peak FLOPs of one node.",
    scope="cluster",
)
node_hbm_capacity = var(
    "cluster.node.hbm_capacity", "B_HBM_node", "byte",
    "Aggregate usable HBM capacity in one node.",
    scope="cluster",
)
node_hbm_bw = var(
    "cluster.node.hbm_bw", "BW_HBM_node", "byte/s",
    "Aggregate effective HBM bandwidth in one node.",
    scope="cluster",
)
node_local_ssd_capacity = var(
    "cluster.node.local_ssd.capacity", "B_SSD_node", "byte",
    "Aggregate local SSD capacity in one node.",
    scope="cluster",
)
node_local_ssd_bw = var(
    "cluster.node.local_ssd.bw", "BW_SSD_node", "byte/s",
    "Aggregate local SSD bandwidth in one node.",
    scope="cluster",
)
node_nic_bw = var(
    "cluster.node.nic_bw", "BW_NIC_node", "byte/s",
    "Scale-out NIC bandwidth per node.",
    scope="cluster",
)
node_power = var(
    "cluster.node.power", "P_node", "W",
    "Total power draw of one node.",
    scope="cluster",
)


eq_node_peak_flops = eq(
    "cluster.eq.node_peak_flops",
    node_peak_flops.symbol,
    n_gpus_per_node.symbol * peak_flops_gpu.symbol,
    "Node peak FLOPs equal GPUs per node times per-GPU peak FLOPs.",
)

eq_node_peak_flops_power_limited = eq(
    "cluster.eq.node_peak_flops_power_limited",
    node_peak_flops_power_limited.symbol,
    n_gpus_per_node.symbol * peak_flops_gpu_power_limited.symbol,
    "Node power-limited peak FLOPs equal GPUs per node times per-GPU power-limited peak FLOPs.",
)

eq_node_hbm_capacity = eq(
    "cluster.eq.node_hbm_capacity",
    node_hbm_capacity.symbol,
    n_gpus_per_node.symbol * hbm_effective_capacity.symbol,
    "Node HBM capacity aggregates usable per-GPU HBM across the node.",
)

eq_node_hbm_bw = eq(
    "cluster.eq.node_hbm_bw",
    node_hbm_bw.symbol,
    n_gpus_per_node.symbol * hbm_bw_effective.symbol,
    "Node HBM bandwidth aggregates effective per-GPU HBM bandwidth across the node.",
)

eq_node_local_ssd_capacity = eq(
    "cluster.eq.node_local_ssd_capacity",
    node_local_ssd_capacity.symbol,
    node_local_ssd_count.symbol * node_local_ssd_capacity_per_drive.symbol,
    "Node local storage capacity equals drive count times per-drive capacity.",
)

eq_node_local_ssd_bw = eq(
    "cluster.eq.node_local_ssd_bw",
    node_local_ssd_bw.symbol,
    node_local_ssd_count.symbol * node_local_ssd_bw_per_drive.symbol,
    "Node local storage bandwidth equals drive count times per-drive streaming bandwidth.",
)

eq_node_nic_bw = eq(
    "cluster.eq.node_nic_bw",
    node_nic_bw.symbol,
    n_gpus_per_node.symbol * nic_bw_per_gpu_effective.symbol,
    "Node NIC bandwidth aggregates effective per-GPU scale-out bandwidth.",
)

eq_node_power = eq(
    "cluster.eq.node_power",
    node_power.symbol,
    n_gpus_per_node.symbol * p_gpu_total.symbol
    + cpu_power_node.symbol
    + ram_power_node.symbol
    + nic_power_node.symbol
    + storage_power_node.symbol
    + misc_power_node.symbol,
    "Node power equals GPU package power plus CPU, DRAM, NIC, storage, and chassis overhead.",
)


CLUSTER_NODE_VARIABLES = [
    n_gpus_per_node,
    n_cpus_per_node,
    ram_per_node,
    node_dram_bw,
    node_local_ssd_count,
    node_local_ssd_capacity_per_drive,
    node_local_ssd_bw_per_drive,
    cpu_power_node,
    ram_power_node,
    nic_power_node,
    storage_power_node,
    misc_power_node,
    node_peak_flops,
    node_peak_flops_power_limited,
    node_hbm_capacity,
    node_hbm_bw,
    node_local_ssd_capacity,
    node_local_ssd_bw,
    node_nic_bw,
    node_power,
]

CLUSTER_NODE_EQUATIONS = [
    eq_node_peak_flops,
    eq_node_peak_flops_power_limited,
    eq_node_hbm_capacity,
    eq_node_hbm_bw,
    eq_node_local_ssd_capacity,
    eq_node_local_ssd_bw,
    eq_node_nic_bw,
    eq_node_power,
]


__all__ = [
    "n_gpus_per_node", "n_cpus_per_node", "ram_per_node", "node_dram_bw",
    "node_local_ssd_count", "node_local_ssd_capacity_per_drive",
    "node_local_ssd_bw_per_drive",
    "cpu_power_node", "ram_power_node", "nic_power_node",
    "storage_power_node", "misc_power_node",
    "node_peak_flops", "node_peak_flops_power_limited",
    "node_hbm_capacity", "node_hbm_bw",
    "node_local_ssd_capacity", "node_local_ssd_bw",
    "node_nic_bw", "node_power",
    "eq_node_peak_flops", "eq_node_peak_flops_power_limited",
    "eq_node_hbm_capacity", "eq_node_hbm_bw",
    "eq_node_local_ssd_capacity", "eq_node_local_ssd_bw",
    "eq_node_nic_bw", "eq_node_power",
    "CLUSTER_NODE_VARIABLES", "CLUSTER_NODE_EQUATIONS",
]
