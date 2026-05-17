"""
scopes/cluster_node.py
======================

Public facade for node-level composition and aggregates.

A node is one server chassis carrying GPUs, host CPU, DRAM, NIC, and local
storage. Focused helper modules hold composition, power bill-of-materials,
aggregate capacity, and NIC topology definitions; this wrapper keeps the
historical import path, public exports, and registry ordering stable.
"""

from .cluster_node_common import *
from .cluster_node_composition import *
from .cluster_node_composition import (
    CLUSTER_NODE_COMPOSITION_VARIABLES as _CLUSTER_NODE_COMPOSITION_VARIABLES,
)
from .cluster_node_power import *
from .cluster_node_power import (
    CLUSTER_NODE_POWER_VARIABLES as _CLUSTER_NODE_POWER_VARIABLES,
)
from .cluster_node_aggregation import *
from .cluster_node_aggregation import (
    CLUSTER_NODE_AGGREGATION_VARIABLES as _CLUSTER_NODE_AGGREGATION_VARIABLES,
)
from .cluster_node_network import *
from .cluster_node_network import (
    CLUSTER_NODE_NETWORK_VARIABLES as _CLUSTER_NODE_NETWORK_VARIABLES,
)
from .cluster_node_totals import *
from .cluster_node_totals import (
    CLUSTER_NODE_TOTAL_VARIABLES as _CLUSTER_NODE_TOTAL_VARIABLES,
)
from .cluster_node_equations import *
from .cluster_node_equations import (
    CLUSTER_NODE_EQUATION_LIST as _CLUSTER_NODE_EQUATION_LIST,
)


CLUSTER_NODE_VARIABLES = (
    _CLUSTER_NODE_COMPOSITION_VARIABLES
    + _CLUSTER_NODE_POWER_VARIABLES
    + _CLUSTER_NODE_AGGREGATION_VARIABLES
    + _CLUSTER_NODE_NETWORK_VARIABLES
    + _CLUSTER_NODE_TOTAL_VARIABLES
)

CLUSTER_NODE_EQUATIONS = _CLUSTER_NODE_EQUATION_LIST


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
