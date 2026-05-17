"""
Shared declarations for node-level cluster helper modules.

The node scope is split by model responsibility, but references, declaration
factories, and historically visible imported dependencies stay here so every
helper uses the same source annotations and cluster scope wiring.
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


__all__ = [
    "Reference",
    "BPS",
    "FLOPS",
    "WATT",
    "byte",
    "p_gpu_total",
    "peak_flops_gpu",
    "peak_flops_gpu_power_limited",
    "hbm_bw_effective",
    "hbm_effective_capacity",
    "DIMENSIONLESS",
    "referenced_eq",
    "scoped_var",
    "NODE_NIC_TOPOLOGY_REF",
    "NODE_POWER_BOM_REF",
    "NODE_COMPOSITION_REF",
    "NODE_AGGREGATION_REF",
    "node_composition_var",
    "node_power_var",
    "node_aggregation_var",
    "node_nic_topology_var",
    "node_power_eq",
    "node_aggregation_eq",
    "node_nic_topology_eq",
]
