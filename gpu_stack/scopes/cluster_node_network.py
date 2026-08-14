"""
How fast one node can inject traffic into the scale-out network.

A node talks to other nodes through its NICs (network interface cards), and
its injection bandwidth is a hardware ceiling set before any software runs:
NIC count, ports per NIC, and per-port line rate multiply to a raw figure,
then protocol efficiency — the fraction of line rate left after link,
transport, and host overhead — cuts it to what payloads actually see. This
module declares those variables. The collective scope cares because
cross-node AllReduce and all-to-all time is bounded by this injection rate,
however fast the switches beyond it may be.
"""

from .cluster_node_common import BPS, DIMENSIONLESS, node_nic_topology_var


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


CLUSTER_NODE_NETWORK_VARIABLES = [
    node_nic_count,
    node_nic_ports_per_nic,
    node_nic_port_rate,
    node_nic_protocol_efficiency,
    node_nic_bw_raw,
    node_nic_bw,
]


__all__ = [
    "node_nic_count",
    "node_nic_ports_per_nic",
    "node_nic_port_rate",
    "node_nic_protocol_efficiency",
    "node_nic_bw_raw",
    "node_nic_bw",
]
