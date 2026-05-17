"""
scopes/cluster_node.py
======================

Node-level composition and aggregates.

A node is one server chassis carrying GPUs, host CPU, DRAM, NIC, and local
storage. This file defines those raw inputs and the per-node aggregates that
downstream rack and site files consume.
"""

from ..core import Reference
from ..core.units import BPS, FLOPS, WATT, byte

from .gpu import (
    p_gpu_total,
    peak_flops_gpu,
    peak_flops_gpu_power_limited,
)
from .memory_subsystem import hbm_bw_effective, hbm_effective_capacity
from .cluster_ops_declarations import (
    DIMENSIONLESS,
    referenced_eq,
    scoped_var,
)

NODE_NIC_TOPOLOGY_REF = Reference(
    "Node scale-out bandwidth is a bill-of-materials and cable-plan quantity: "
    "NIC count, port count, port rate, and protocol efficiency bound injection "
    "before any per-GPU traffic allocation.",
    kind="model",
)

NODE_POWER_BOM_REF = Reference(
    "Node non-GPU power is modeled as a compact bill of materials: CPU "
    "sockets, installed host DRAM capacity, NIC cards and active ports, "
    "local SSDs, and fixed/per-GPU chassis overhead.",
    kind="model",
)

NODE_COMPOSITION_REF = Reference(
    "Node composition treats GPUs, host CPUs, CPU DRAM, local SSDs, and NICs "
    "as the planning bill of materials for one accelerator server.",
    kind="model",
)

NODE_AGGREGATION_REF = Reference(
    "Node aggregate compute, HBM, local storage, and network quantities are "
    "linear rollups of per-device capacities inside one server chassis.",
    kind="model",
)


node_composition_var = scoped_var("cluster", NODE_COMPOSITION_REF)
node_power_var = scoped_var("cluster", NODE_POWER_BOM_REF)
node_aggregation_var = scoped_var("cluster", NODE_AGGREGATION_REF)
node_nic_topology_var = scoped_var("cluster", NODE_NIC_TOPOLOGY_REF)

node_power_eq = referenced_eq(NODE_POWER_BOM_REF)
node_aggregation_eq = referenced_eq(NODE_AGGREGATION_REF)
node_nic_topology_eq = referenced_eq(NODE_NIC_TOPOLOGY_REF)


# ---------------------------------------------------------------------------
# Node composition
# ---------------------------------------------------------------------------

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
cpu_power_per_cpu = node_power_var(
    "cluster.node.cpu.power_per_cpu", "P_cpu_socket", "W/CPU",
    "Power draw of one host CPU package or socket.",
    nonnegative=True,
    sp_units=WATT,
)
cpu_power_node = node_power_var(
    "cluster.node.cpu_power", "P_cpu_node", "W",
    "CPU package power per node.",
    sp_units=WATT,
)
ram_power_per_byte = node_power_var(
    "cluster.node.ram.power_per_byte", "P_RAM_byte", "W/byte",
    "Host DRAM power coefficient per installed byte of CPU-side memory.",
    nonnegative=True,
    sp_units=WATT / byte,
)
ram_power_node = node_power_var(
    "cluster.node.ram_power", "P_ram_node", "W",
    "CPU-side DRAM power per node.",
    sp_units=WATT,
)
node_nic_power_per_nic = node_power_var(
    "cluster.node.nic.power_per_nic", "P_NIC_card", "W/NIC",
    "Power draw of one installed scale-out NIC card before port-facing overhead.",
    nonnegative=True,
    sp_units=WATT,
)
node_nic_power_per_port = node_power_var(
    "cluster.node.nic.power_per_port", "P_NIC_port", "W/port",
    "Power draw for each active NIC port, including PHY, optics, or retimer budget.",
    nonnegative=True,
    sp_units=WATT,
)
nic_power_node = node_power_var(
    "cluster.node.nic_power", "P_nic_node", "W",
    "NIC and retimer power per node.",
    sp_units=WATT,
)
node_local_ssd_power_per_drive = node_power_var(
    "cluster.node.local_ssd.power_per_drive", "P_SSD_drv", "W/drive",
    "Power draw of one local SSD or NVMe drive.",
    nonnegative=True,
    sp_units=WATT,
)
storage_power_node = node_power_var(
    "cluster.node.storage_power", "P_stor_node", "W",
    "Local storage power per node.",
    sp_units=WATT,
)
node_misc_fixed_power = node_power_var(
    "cluster.node.misc.fixed_power", "P_misc_fixed", "W",
    "Fixed node chassis, BMC, motherboard, and fan overhead independent of installed accelerators.",
    nonnegative=True,
    sp_units=WATT,
)
node_misc_power_per_gpu = node_power_var(
    "cluster.node.misc.power_per_gpu", "P_misc_gpu", "W/GPU",
    "Per-GPU slot, riser, cabling, and chassis support overhead.",
    nonnegative=True,
    sp_units=WATT,
)
misc_power_node = node_power_var(
    "cluster.node.misc_power", "P_misc_node", "W",
    "Remaining node-level power, for fans, BMCs, and motherboard losses.",
    sp_units=WATT,
)


# ---------------------------------------------------------------------------
# Node-level aggregates
# ---------------------------------------------------------------------------

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
node_nic_count = node_nic_topology_var(
    "cluster.node.nic.count", "N_NIC_node", "NICs",
    "Number of scale-out NICs installed in one node.",
    positive=True,
    integer=True,
    sp_units=DIMENSIONLESS,
)
node_nic_ports_per_nic = node_nic_topology_var(
    "cluster.node.nic.ports_per_nic", "N_port_NIC", "ports/NIC",
    "Scale-out network ports exposed by one node NIC.",
    positive=True,
    integer=True,
    sp_units=DIMENSIONLESS,
)
node_nic_port_rate = node_nic_topology_var(
    "cluster.node.nic.port_rate", "BW_NIC_port", "byte/s",
    "Line-rate payload bandwidth of one scale-out NIC port before node-level protocol efficiency.",
    positive=True,
    sp_units=BPS,
)
node_nic_protocol_efficiency = node_nic_topology_var(
    "cluster.node.nic.protocol_efficiency", "eta_NIC_node_proto", "dimensionless",
    "Payload efficiency of the node scale-out NIC path after link, transport, and host overhead.",
    nonnegative=True,
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
)
node_nic_bw_raw = node_nic_topology_var(
    "cluster.node.nic_bw_raw", "BW_NIC_node_raw", "byte/s",
    "Raw node scale-out injection bandwidth before protocol efficiency.",
    positive=True,
    sp_units=BPS,
)
node_nic_bw = node_nic_topology_var(
    "cluster.node.nic_bw", "BW_NIC_node", "byte/s",
    "Scale-out NIC bandwidth per node.",
    positive=True,
    sp_units=BPS,
)
node_power = node_power_var(
    "cluster.node.power", "P_node", "W",
    "Total power draw of one node.",
    sp_units=WATT,
)


eq_node_peak_flops = node_aggregation_eq(
    "cluster.eq.node_peak_flops",
    node_peak_flops.symbol,
    n_gpus_per_node.symbol * peak_flops_gpu.symbol,
    "Node peak FLOPs equal GPUs per node times per-GPU peak FLOPs.",
)

eq_node_peak_flops_power_limited = node_aggregation_eq(
    "cluster.eq.node_peak_flops_power_limited",
    node_peak_flops_power_limited.symbol,
    n_gpus_per_node.symbol * peak_flops_gpu_power_limited.symbol,
    "Node power-limited peak FLOPs equal GPUs per node times per-GPU power-limited peak FLOPs.",
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


CLUSTER_NODE_VARIABLES = [
    n_gpus_per_node,
    n_cpus_per_node,
    ram_per_node,
    node_dram_bw,
    node_local_ssd_count,
    node_local_ssd_capacity_per_drive,
    node_local_ssd_bw_per_drive,
    cpu_power_per_cpu,
    cpu_power_node,
    ram_power_per_byte,
    ram_power_node,
    node_nic_power_per_nic,
    node_nic_power_per_port,
    nic_power_node,
    node_local_ssd_power_per_drive,
    storage_power_node,
    node_misc_fixed_power,
    node_misc_power_per_gpu,
    misc_power_node,
    node_peak_flops,
    node_peak_flops_power_limited,
    node_hbm_capacity,
    node_hbm_bw,
    node_local_ssd_capacity,
    node_local_ssd_bw,
    node_nic_count,
    node_nic_ports_per_nic,
    node_nic_port_rate,
    node_nic_protocol_efficiency,
    node_nic_bw_raw,
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
    "n_gpus_per_node", "n_cpus_per_node", "ram_per_node", "node_dram_bw",
    "node_local_ssd_count", "node_local_ssd_capacity_per_drive",
    "node_local_ssd_bw_per_drive",
    "cpu_power_per_cpu",
    "cpu_power_node", "ram_power_node", "nic_power_node",
    "ram_power_per_byte",
    "node_nic_power_per_nic", "node_nic_power_per_port",
    "storage_power_node", "node_local_ssd_power_per_drive",
    "node_misc_fixed_power", "node_misc_power_per_gpu",
    "misc_power_node",
    "node_peak_flops", "node_peak_flops_power_limited",
    "node_hbm_capacity", "node_hbm_bw",
    "node_local_ssd_capacity", "node_local_ssd_bw",
    "node_nic_count", "node_nic_ports_per_nic",
    "node_nic_port_rate", "node_nic_protocol_efficiency",
    "node_nic_bw_raw", "node_nic_bw", "node_power",
    "eq_node_peak_flops", "eq_node_peak_flops_power_limited",
    "eq_node_hbm_capacity", "eq_node_hbm_bw",
    "eq_node_local_ssd_capacity", "eq_node_local_ssd_bw",
    "eq_node_nic_bw_raw", "eq_node_nic_bw",
    "eq_cpu_power_node", "eq_ram_power_node", "eq_nic_power_node",
    "eq_storage_power_node", "eq_misc_power_node", "eq_node_power",
    "CLUSTER_NODE_VARIABLES", "CLUSTER_NODE_EQUATIONS",
]
