"""
scopes/cluster_rack.py
======================

Rack-level aggregation.

A rack bundles several compute nodes behind shared power distribution and a
top-of-rack switch. This file lifts per-node aggregates up to rack scale,
wires the intra-rack fabric balance through NVLink, and records the
rack-level power-domain failure unit that reliability modeling consumes.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import BPS, FLOPS, WATT, byte

from .interconnect import bw_nvlink_rack, n_gpus_per_rack
from .cluster_node import (
    n_gpus_per_node,
    node_hbm_bw,
    node_hbm_capacity,
    node_local_ssd_bw,
    node_local_ssd_capacity,
    node_nic_bw,
    node_peak_flops,
    node_peak_flops_power_limited,
    node_power,
)

DIMENSIONLESS = sp.Integer(1)

RACK_SCALEOUT_TOPOLOGY_REF = Reference(
    "Rack scale-out bandwidth is bounded separately by node NIC injection, "
    "top-of-rack downlink capacity, and top-of-rack uplink capacity; the "
    "usable off-rack bisection is the minimum of those physical limits.",
    kind="model",
)

RACK_AGGREGATION_REF = Reference(
    "Rack aggregate compute, memory, local-storage, and power quantities are "
    "linear rollups of homogeneous node-level capacities for one rack.",
    kind="model",
)

RACK_POWER_DOMAIN_REF = Reference(
    "Rack reliability planning treats shared rack or row power equipment as a "
    "failure domain that can remove multiple nodes at once.",
    kind="model",
)

RACK_FABRIC_BALANCE_REF = Reference(
    "Rack compute-to-fabric balance compares power-limited rack FLOPs against "
    "the aggregate intra-rack fabric bisection bandwidth.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Rack composition and aggregates
# ---------------------------------------------------------------------------

n_nodes_per_rack = var(
    "cluster.rack.n_nodes", "N_node_rack", "nodes/rack",
    "Compute nodes per rack.",
    scope="cluster",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[RACK_AGGREGATION_REF],
)
rack_peak_flops = var(
    "cluster.rack.peak_flops", "F_rack", "FLOP/s",
    "Aggregate peak FLOPs in one rack.",
    scope="cluster",
    sp_units=FLOPS,
    references=[RACK_AGGREGATION_REF],
)
rack_peak_flops_power_limited = var(
    "cluster.rack.peak_flops_power_limited", "F_rack_pl", "FLOP/s",
    "Aggregate power-limited peak FLOPs in one rack.",
    scope="cluster",
    sp_units=FLOPS,
    references=[RACK_AGGREGATION_REF],
)
rack_hbm_capacity = var(
    "cluster.rack.hbm_capacity", "B_HBM_rack", "byte",
    "Aggregate usable HBM capacity in one rack.",
    scope="cluster",
    sp_units=byte,
    references=[RACK_AGGREGATION_REF],
)
rack_hbm_bw = var(
    "cluster.rack.hbm_bw", "BW_HBM_rack", "byte/s",
    "Aggregate effective HBM bandwidth in one rack.",
    scope="cluster",
    sp_units=BPS,
    references=[RACK_AGGREGATION_REF],
)
rack_local_ssd_capacity = var(
    "cluster.rack.local_ssd.capacity", "B_SSD_rack", "byte",
    "Aggregate local SSD capacity in one rack.",
    scope="cluster",
    sp_units=byte,
    references=[RACK_AGGREGATION_REF],
)
rack_local_ssd_bw = var(
    "cluster.rack.local_ssd.bw", "BW_SSD_rack", "byte/s",
    "Aggregate local SSD bandwidth in one rack.",
    scope="cluster",
    sp_units=BPS,
    references=[RACK_AGGREGATION_REF],
)
rack_nic_bw = var(
    "cluster.rack.nic_bw", "BW_NIC_rack", "byte/s",
    "Aggregate node NIC injection bandwidth in one rack before top-of-rack fabric limits.",
    scope="cluster",
    sp_units=BPS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_tor_switch_count = var(
    "cluster.rack.tor.count", "N_ToR_rack", "switches",
    "Top-of-rack or rack-local scale-out switches serving one rack.",
    scope="cluster",
    positive=True,
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_tor_downlink_ports_per_switch = var(
    "cluster.rack.tor.downlink_ports_per_switch", "N_ToR_down_port_sw", "ports/switch",
    "Node-facing scale-out ports on one rack switch.",
    scope="cluster",
    positive=True,
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_tor_downlink_port_rate = var(
    "cluster.rack.tor.downlink_port_rate", "BW_ToR_down_port", "byte/s",
    "Payload line rate of one node-facing rack switch port before rack-switch efficiency.",
    scope="cluster",
    positive=True,
    sp_units=BPS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_tor_downlink_protocol_efficiency = var(
    "cluster.rack.tor.downlink_protocol_efficiency", "eta_ToR_down", "dimensionless",
    "Payload efficiency of the rack-switch node-facing downlink side.",
    scope="cluster",
    nonnegative=True,
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_tor_downlink_bw_per_switch = var(
    "cluster.rack.tor.downlink_bw_per_switch", "BW_ToR_down_sw", "byte/s",
    "Aggregate node-facing downlink payload bandwidth of one rack scale-out switch.",
    scope="cluster",
    positive=True,
    sp_units=BPS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_tor_uplink_ports_per_switch = var(
    "cluster.rack.tor.uplink_ports_per_switch", "N_ToR_up_port_sw", "ports/switch",
    "Fabric-facing scale-out ports on one rack switch.",
    scope="cluster",
    positive=True,
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_tor_uplink_port_rate = var(
    "cluster.rack.tor.uplink_port_rate", "BW_ToR_up_port", "byte/s",
    "Payload line rate of one fabric-facing rack switch port before rack-switch efficiency.",
    scope="cluster",
    positive=True,
    sp_units=BPS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_tor_uplink_protocol_efficiency = var(
    "cluster.rack.tor.uplink_protocol_efficiency", "eta_ToR_up", "dimensionless",
    "Payload efficiency of the rack-switch fabric-facing uplink side.",
    scope="cluster",
    nonnegative=True,
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_tor_uplink_bw_per_switch = var(
    "cluster.rack.tor.uplink_bw_per_switch", "BW_ToR_up_sw", "byte/s",
    "Aggregate fabric-facing uplink payload bandwidth of one rack scale-out switch.",
    scope="cluster",
    positive=True,
    sp_units=BPS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_scaleout_downlink_bw = var(
    "cluster.rack.scaleout_downlink_bw", "BW_rack_down", "byte/s",
    "Aggregate node-facing scale-out downlink bandwidth available in one rack.",
    scope="cluster",
    positive=True,
    sp_units=BPS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_scaleout_uplink_bw = var(
    "cluster.rack.scaleout_uplink_bw", "BW_rack_up", "byte/s",
    "Aggregate fabric-facing scale-out uplink bandwidth available from one rack.",
    scope="cluster",
    positive=True,
    sp_units=BPS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_scaleout_oversubscription = var(
    "cluster.rack.scaleout_oversubscription", "rho_rack_so", "dimensionless",
    "Rack scale-out oversubscription ratio: node-facing downlink capacity divided by fabric-facing uplink capacity.",
    scope="cluster",
    positive=True,
    sp_units=DIMENSIONLESS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_scaleout_bisection_bw = var(
    "cluster.rack.scaleout_bisection_bw", "BW_rack_so_bisect", "byte/s",
    "Usable off-rack scale-out bandwidth after node injection, rack downlink, and rack uplink limits.",
    scope="cluster",
    positive=True,
    sp_units=BPS,
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
)
rack_power = var(
    "cluster.rack.power", "P_rack_W", "W",
    "Total IT power drawn by one rack.",
    scope="cluster",
    sp_units=WATT,
    references=[RACK_AGGREGATION_REF],
)
rack_gpus_per_power_domain = var(
    "cluster.rack.gpus_per_power_domain", "N_GPU_pd", "GPUs",
    "GPUs that can disappear together when a shared power domain fails.",
    scope="cluster",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[RACK_POWER_DOMAIN_REF],
)
nodes_per_power_domain = var(
    "cluster.rel.nodes_per_power_domain", "N_node_pd", "nodes",
    "Nodes attached to one shared rack-level or row-level power domain.",
    scope="cluster",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[RACK_POWER_DOMAIN_REF],
)
rack_flops_per_intra_byte = var(
    "cluster.rack.flops_per_intra_byte", "AI_rack_intra", "FLOP/byte",
    "Rack-level compute to intra-rack fabric balance using NVLink-rack bandwidth.",
    scope="cluster",
    sp_units=FLOPS / BPS,
    references=[RACK_FABRIC_BALANCE_REF],
)


eq_rack_gpu_count = eq(
    "cluster.eq.rack_gpu_count",
    n_gpus_per_rack.symbol,
    n_nodes_per_rack.symbol * n_gpus_per_node.symbol,
    "GPUs per rack equal nodes per rack times GPUs per node.",
    references=[RACK_AGGREGATION_REF],
)

eq_rack_peak_flops = eq(
    "cluster.eq.rack_peak_flops",
    rack_peak_flops.symbol,
    n_nodes_per_rack.symbol * node_peak_flops.symbol,
    "Rack peak FLOPs equal nodes per rack times node peak FLOPs.",
    references=[RACK_AGGREGATION_REF],
    check_units=True,
)

eq_rack_peak_flops_power_limited = eq(
    "cluster.eq.rack_peak_flops_power_limited",
    rack_peak_flops_power_limited.symbol,
    n_nodes_per_rack.symbol * node_peak_flops_power_limited.symbol,
    "Rack power-limited peak FLOPs equal nodes per rack times node power-limited peak FLOPs.",
    references=[RACK_AGGREGATION_REF],
    check_units=True,
)

eq_rack_hbm_capacity = eq(
    "cluster.eq.rack_hbm_capacity",
    rack_hbm_capacity.symbol,
    n_nodes_per_rack.symbol * node_hbm_capacity.symbol,
    "Rack HBM capacity equals nodes per rack times node HBM capacity.",
    references=[RACK_AGGREGATION_REF],
    check_units=True,
)

eq_rack_hbm_bw = eq(
    "cluster.eq.rack_hbm_bw",
    rack_hbm_bw.symbol,
    n_nodes_per_rack.symbol * node_hbm_bw.symbol,
    "Rack HBM bandwidth equals nodes per rack times node HBM bandwidth.",
    references=[RACK_AGGREGATION_REF],
    check_units=True,
)

eq_rack_local_ssd_capacity = eq(
    "cluster.eq.rack_local_ssd_capacity",
    rack_local_ssd_capacity.symbol,
    n_nodes_per_rack.symbol * node_local_ssd_capacity.symbol,
    "Rack local SSD capacity equals nodes per rack times node local storage capacity.",
    references=[RACK_AGGREGATION_REF],
    check_units=True,
)

eq_rack_local_ssd_bw = eq(
    "cluster.eq.rack_local_ssd_bw",
    rack_local_ssd_bw.symbol,
    n_nodes_per_rack.symbol * node_local_ssd_bw.symbol,
    "Rack local SSD bandwidth equals nodes per rack times node local storage bandwidth.",
    references=[RACK_AGGREGATION_REF],
    check_units=True,
)

eq_rack_nic_bw = eq(
    "cluster.eq.rack_nic_bw",
    rack_nic_bw.symbol,
    n_nodes_per_rack.symbol * node_nic_bw.symbol,
    "Rack node-injection bandwidth equals nodes per rack times node NIC bandwidth.",
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
    check_units=True,
)

eq_rack_tor_downlink_bw_per_switch = eq(
    "cluster.eq.rack_tor_downlink_bw_per_switch",
    rack_tor_downlink_bw_per_switch.symbol,
    rack_tor_downlink_ports_per_switch.symbol
    * rack_tor_downlink_port_rate.symbol
    * rack_tor_downlink_protocol_efficiency.symbol,
    "Rack switch downlink bandwidth equals downlink port count times port rate and payload efficiency.",
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
    check_units=True,
)

eq_rack_tor_uplink_bw_per_switch = eq(
    "cluster.eq.rack_tor_uplink_bw_per_switch",
    rack_tor_uplink_bw_per_switch.symbol,
    rack_tor_uplink_ports_per_switch.symbol
    * rack_tor_uplink_port_rate.symbol
    * rack_tor_uplink_protocol_efficiency.symbol,
    "Rack switch uplink bandwidth equals uplink port count times port rate and payload efficiency.",
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
    check_units=True,
)

eq_rack_scaleout_downlink_bw = eq(
    "cluster.eq.rack_scaleout_downlink_bw",
    rack_scaleout_downlink_bw.symbol,
    rack_tor_switch_count.symbol * rack_tor_downlink_bw_per_switch.symbol,
    "Rack scale-out downlink bandwidth equals switch count times node-facing bandwidth per switch.",
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
    check_units=True,
)

eq_rack_scaleout_uplink_bw = eq(
    "cluster.eq.rack_scaleout_uplink_bw",
    rack_scaleout_uplink_bw.symbol,
    rack_tor_switch_count.symbol * rack_tor_uplink_bw_per_switch.symbol,
    "Rack scale-out uplink bandwidth equals switch count times fabric-facing bandwidth per switch.",
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
    check_units=True,
)

eq_rack_scaleout_oversubscription = eq(
    "cluster.eq.rack_scaleout_oversubscription",
    rack_scaleout_oversubscription.symbol,
    rack_scaleout_downlink_bw.symbol / rack_scaleout_uplink_bw.symbol,
    "Rack scale-out oversubscription is downlink capacity divided by uplink capacity.",
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
    check_units=True,
)

eq_rack_scaleout_bisection_bw = eq(
    "cluster.eq.rack_scaleout_bisection_bw",
    rack_scaleout_bisection_bw.symbol,
    sp.Min(
        rack_nic_bw.symbol,
        rack_scaleout_downlink_bw.symbol,
        rack_scaleout_uplink_bw.symbol,
    ),
    "Rack off-rack scale-out bisection is the minimum of node injection, ToR downlink, and ToR uplink capacity.",
    references=[RACK_SCALEOUT_TOPOLOGY_REF],
    check_units=True,
)

eq_rack_power = eq(
    "cluster.eq.rack_power",
    rack_power.symbol,
    n_nodes_per_rack.symbol * node_power.symbol,
    "Rack IT power equals nodes per rack times node power.",
    references=[RACK_AGGREGATION_REF],
    check_units=True,
)

eq_rack_gpus_per_power_domain = eq(
    "cluster.eq.rack_gpus_per_power_domain",
    rack_gpus_per_power_domain.symbol,
    n_gpus_per_node.symbol * nodes_per_power_domain.symbol,
    "GPUs lost in one shared rack power-domain failure equal GPUs per node times nodes served by that power domain.",
    references=[RACK_POWER_DOMAIN_REF],
    check_units=True,
)

eq_rack_flops_per_intra_byte = eq(
    "cluster.eq.rack_flops_per_intra_byte",
    rack_flops_per_intra_byte.symbol,
    rack_peak_flops_power_limited.symbol / bw_nvlink_rack.symbol,
    "Rack compute to NVLink-rack balance equals rack power-limited FLOPs divided by aggregate intra-rack fabric bandwidth.",
    references=[RACK_FABRIC_BALANCE_REF],
)


CLUSTER_RACK_VARIABLES = [
    n_nodes_per_rack,
    rack_peak_flops,
    rack_peak_flops_power_limited,
    rack_hbm_capacity,
    rack_hbm_bw,
    rack_local_ssd_capacity,
    rack_local_ssd_bw,
    rack_nic_bw,
    rack_tor_switch_count,
    rack_tor_downlink_ports_per_switch,
    rack_tor_downlink_port_rate,
    rack_tor_downlink_protocol_efficiency,
    rack_tor_downlink_bw_per_switch,
    rack_tor_uplink_ports_per_switch,
    rack_tor_uplink_port_rate,
    rack_tor_uplink_protocol_efficiency,
    rack_tor_uplink_bw_per_switch,
    rack_scaleout_downlink_bw,
    rack_scaleout_uplink_bw,
    rack_scaleout_oversubscription,
    rack_scaleout_bisection_bw,
    rack_power,
    rack_gpus_per_power_domain,
    nodes_per_power_domain,
    rack_flops_per_intra_byte,
]

CLUSTER_RACK_EQUATIONS = [
    eq_rack_gpu_count,
    eq_rack_peak_flops,
    eq_rack_peak_flops_power_limited,
    eq_rack_hbm_capacity,
    eq_rack_hbm_bw,
    eq_rack_local_ssd_capacity,
    eq_rack_local_ssd_bw,
    eq_rack_nic_bw,
    eq_rack_tor_downlink_bw_per_switch,
    eq_rack_tor_uplink_bw_per_switch,
    eq_rack_scaleout_downlink_bw,
    eq_rack_scaleout_uplink_bw,
    eq_rack_scaleout_oversubscription,
    eq_rack_scaleout_bisection_bw,
    eq_rack_power,
    eq_rack_gpus_per_power_domain,
    eq_rack_flops_per_intra_byte,
]


__all__ = [
    "n_nodes_per_rack", "rack_peak_flops", "rack_peak_flops_power_limited",
    "rack_hbm_capacity", "rack_hbm_bw",
    "rack_local_ssd_capacity", "rack_local_ssd_bw",
    "rack_nic_bw", "rack_tor_switch_count",
    "rack_tor_downlink_ports_per_switch", "rack_tor_downlink_port_rate",
    "rack_tor_downlink_protocol_efficiency",
    "rack_tor_downlink_bw_per_switch", "rack_tor_uplink_bw_per_switch",
    "rack_tor_uplink_ports_per_switch", "rack_tor_uplink_port_rate",
    "rack_tor_uplink_protocol_efficiency",
    "rack_scaleout_downlink_bw", "rack_scaleout_uplink_bw",
    "rack_scaleout_oversubscription", "rack_scaleout_bisection_bw",
    "rack_power",
    "rack_gpus_per_power_domain", "nodes_per_power_domain",
    "rack_flops_per_intra_byte",
    "eq_rack_gpu_count", "eq_rack_peak_flops",
    "eq_rack_peak_flops_power_limited",
    "eq_rack_hbm_capacity", "eq_rack_hbm_bw",
    "eq_rack_local_ssd_capacity", "eq_rack_local_ssd_bw",
    "eq_rack_nic_bw", "eq_rack_tor_downlink_bw_per_switch",
    "eq_rack_tor_uplink_bw_per_switch", "eq_rack_scaleout_downlink_bw",
    "eq_rack_scaleout_uplink_bw", "eq_rack_scaleout_oversubscription",
    "eq_rack_scaleout_bisection_bw", "eq_rack_power",
    "eq_rack_gpus_per_power_domain", "eq_rack_flops_per_intra_byte",
    "CLUSTER_RACK_VARIABLES", "CLUSTER_RACK_EQUATIONS",
]
