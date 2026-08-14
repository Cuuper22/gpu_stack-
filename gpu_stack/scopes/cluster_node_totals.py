"""
Node grand totals — declared last because they sum everything before them.

Today this holds one variable: total node power, the sum of GPU power and
every non-GPU subtotal from the power bill of materials. It lives in its own
module because it depends on all the other node sections, and keeping it
separate preserves a clean import order among the helpers. The rack scope
multiplies this figure by nodes per rack.
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
