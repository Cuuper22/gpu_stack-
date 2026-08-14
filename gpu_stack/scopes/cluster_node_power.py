"""
The power the node burns besides its GPUs.

GPUs dominate a training server's power, but they are not alone: host CPU
sockets, installed DRAM, NIC cards and their active ports, local SSDs, and
the chassis itself (fans, board losses) all draw watts around the clock.
This module declares that bill of materials — a per-unit coefficient for
each component (watts per socket, watts per byte of DRAM, watts per drive)
plus the node-level subtotal each one rolls into. Getting this overhead
right matters downstream: the thermal scope must remove it as heat and the
economics scope pays for it in every kWh.
"""

from .cluster_node_common import DIMENSIONLESS, WATT, byte, node_power_var


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


CLUSTER_NODE_POWER_VARIABLES = [
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
]


__all__ = [
    "cpu_power_per_cpu",
    "cpu_power_node",
    "ram_power_per_byte",
    "ram_power_node",
    "node_nic_power_per_nic",
    "node_nic_power_per_port",
    "nic_power_node",
    "node_local_ssd_power_per_drive",
    "storage_power_node",
    "node_misc_fixed_power",
    "node_misc_power_per_gpu",
    "misc_power_node",
]
