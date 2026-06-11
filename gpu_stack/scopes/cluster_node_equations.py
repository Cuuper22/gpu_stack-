"""
Node-level equations for composition, aggregation, NIC topology, and power.
"""

from .cluster_node_common import (
    hbm_bw_effective,
    hbm_effective_capacity,
    node_aggregation_eq,
    node_nic_topology_eq,
    node_power_eq,
    p_gpu_total,
    peak_flops_gpu,
    peak_flops_gpu_power_limited,
)
from .cluster_node_composition import (
    n_cpus_per_node,
    n_gpus_per_node,
    node_local_ssd_bw_per_drive,
    node_local_ssd_capacity_per_drive,
    node_local_ssd_count,
    ram_per_node,
)
from .cluster_node_power import (
    cpu_power_node,
    cpu_power_per_cpu,
    misc_power_node,
    nic_power_node,
    node_local_ssd_power_per_drive,
    node_misc_fixed_power,
    node_misc_power_per_gpu,
    node_nic_power_per_nic,
    node_nic_power_per_port,
    ram_power_node,
    ram_power_per_byte,
    storage_power_node,
)
from .cluster_node_aggregation import (
    node_hbm_bw,
    node_hbm_capacity,
    node_local_ssd_bw,
    node_local_ssd_capacity,
    node_peak_flops,
    node_peak_flops_power_limited,
)
from .cluster_node_network import (
    node_nic_bw,
    node_nic_bw_raw,
    node_nic_count,
    node_nic_port_rate,
    node_nic_ports_per_nic,
    node_nic_protocol_efficiency,
)
from .cluster_node_totals import node_power


eq_node_peak_flops = node_aggregation_eq(
    "cluster.eq.node_peak_flops",
    node_peak_flops.symbol,
    n_gpus_per_node.symbol * peak_flops_gpu.symbol,
    "Node peak FLOPs equal GPUs per node times per-GPU peak FLOPs.",
    check_units=True,
)

eq_node_peak_flops_power_limited = node_aggregation_eq(
    "cluster.eq.node_peak_flops_power_limited",
    node_peak_flops_power_limited.symbol,
    n_gpus_per_node.symbol * peak_flops_gpu_power_limited.symbol,
    "Node power-limited peak FLOPs equal GPUs per node times per-GPU power-limited peak FLOPs.",
    check_units=True,
)

eq_node_hbm_capacity = node_aggregation_eq(
    "cluster.eq.node_hbm_capacity",
    node_hbm_capacity.symbol,
    n_gpus_per_node.symbol * hbm_effective_capacity.symbol,
    "Node HBM capacity aggregates usable per-GPU HBM across the node.",
    check_units=True,
)

eq_node_hbm_bw = node_aggregation_eq(
    "cluster.eq.node_hbm_bw",
    node_hbm_bw.symbol,
    n_gpus_per_node.symbol * hbm_bw_effective.symbol,
    "Node HBM bandwidth aggregates effective per-GPU HBM bandwidth across the node.",
    check_units=True,
)

eq_node_local_ssd_capacity = node_aggregation_eq(
    "cluster.eq.node_local_ssd_capacity",
    node_local_ssd_capacity.symbol,
    node_local_ssd_count.symbol * node_local_ssd_capacity_per_drive.symbol,
    "Node local storage capacity equals drive count times per-drive capacity.",
    check_units=True,
)

eq_node_local_ssd_bw = node_aggregation_eq(
    "cluster.eq.node_local_ssd_bw",
    node_local_ssd_bw.symbol,
    node_local_ssd_count.symbol * node_local_ssd_bw_per_drive.symbol,
    "Node local storage bandwidth equals drive count times per-drive streaming bandwidth.",
    check_units=True,
)

eq_node_nic_bw_raw = node_nic_topology_eq(
    "cluster.eq.node_nic_bw_raw",
    node_nic_bw_raw.symbol,
    node_nic_count.symbol
    * node_nic_ports_per_nic.symbol
    * node_nic_port_rate.symbol,
    "Raw node scale-out bandwidth equals NIC count times ports per NIC times port rate.",
    check_units=True,
)

eq_node_nic_bw = node_nic_topology_eq(
    "cluster.eq.node_nic_bw",
    node_nic_bw.symbol,
    node_nic_bw_raw.symbol * node_nic_protocol_efficiency.symbol,
    "Effective node scale-out bandwidth applies node-level protocol efficiency to physical NIC injection.",
    check_units=True,
)

eq_cpu_power_node = node_power_eq(
    "cluster.eq.node_cpu_power",
    cpu_power_node.symbol,
    n_cpus_per_node.symbol * cpu_power_per_cpu.symbol,
    "Node CPU package power equals CPU count times the per-CPU package power.",
    check_units=True,
)

eq_ram_power_node = node_power_eq(
    "cluster.eq.node_ram_power",
    ram_power_node.symbol,
    ram_per_node.symbol * ram_power_per_byte.symbol,
    "Node host-DRAM power equals installed CPU-side DRAM capacity times the per-byte power coefficient.",
    check_units=True,
)

eq_nic_power_node = node_power_eq(
    "cluster.eq.node_nic_power",
    nic_power_node.symbol,
    node_nic_count.symbol
    * (
        node_nic_power_per_nic.symbol
        + node_nic_ports_per_nic.symbol * node_nic_power_per_port.symbol
    ),
    "Node NIC power equals installed NIC cards plus port-facing PHY, optics, or retimer overhead.",
    check_units=True,
)

eq_storage_power_node = node_power_eq(
    "cluster.eq.node_storage_power",
    storage_power_node.symbol,
    node_local_ssd_count.symbol * node_local_ssd_power_per_drive.symbol,
    "Node local-storage power equals SSD count times per-drive power.",
    check_units=True,
)

eq_misc_power_node = node_power_eq(
    "cluster.eq.node_misc_power",
    misc_power_node.symbol,
    node_misc_fixed_power.symbol
    + n_gpus_per_node.symbol * node_misc_power_per_gpu.symbol,
    "Node miscellaneous power combines fixed chassis overhead with per-GPU slot support overhead.",
    check_units=True,
)

eq_node_power = node_power_eq(
    "cluster.eq.node_power",
    node_power.symbol,
    n_gpus_per_node.symbol * p_gpu_total.symbol
    + cpu_power_node.symbol
    + ram_power_node.symbol
    + nic_power_node.symbol
    + storage_power_node.symbol
    + misc_power_node.symbol,
    "Node power equals GPU package power plus CPU, DRAM, NIC, storage, and chassis overhead.",
    check_units=True,
)


CLUSTER_NODE_EQUATION_LIST = [
    eq_node_peak_flops,
    eq_node_peak_flops_power_limited,
    eq_node_hbm_capacity,
    eq_node_hbm_bw,
    eq_node_local_ssd_capacity,
    eq_node_local_ssd_bw,
    eq_node_nic_bw_raw,
    eq_node_nic_bw,
    eq_cpu_power_node,
    eq_ram_power_node,
    eq_nic_power_node,
    eq_storage_power_node,
    eq_misc_power_node,
    eq_node_power,
]


__all__ = [
    "eq_node_peak_flops",
    "eq_node_peak_flops_power_limited",
    "eq_node_hbm_capacity",
    "eq_node_hbm_bw",
    "eq_node_local_ssd_capacity",
    "eq_node_local_ssd_bw",
    "eq_node_nic_bw_raw",
    "eq_node_nic_bw",
    "eq_cpu_power_node",
    "eq_ram_power_node",
    "eq_nic_power_node",
    "eq_storage_power_node",
    "eq_misc_power_node",
    "eq_node_power",
]
