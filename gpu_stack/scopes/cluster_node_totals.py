"""
Node-level total declarations that depend on prior node sections.
"""

from .cluster_node_common import WATT, node_power_var


node_power = node_power_var(
    "cluster.node.power", "P_node", "W",
    "Total power draw of one node.",
    sp_units=WATT,
)


CLUSTER_NODE_TOTAL_VARIABLES = [
    node_power,
]


__all__ = [
    "node_power",
]
