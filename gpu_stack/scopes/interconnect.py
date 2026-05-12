"""
scopes/interconnect.py
======================

GPU-to-GPU communication fabrics.

The old file stopped at one generic alpha-beta equation and a rack-level
bandwidth ratio. That throws away the actual structure that determines how
collectives behave in practice:

  * packet efficiency from payload bytes versus headers
  * propagation and switch-hop latency
  * congestion and oversubscription loss
  * the fact that NVLink and scale-out links are different fabrics with
    different alpha and beta terms

This scope now exposes those quantities directly so later collective and
training scopes can wire them in instead of treating communication as one
opaque tax.
"""

import sympy as sp

from ..core import Approximation, Reference, System, eq, var
from ..core.units import BPS, SECOND, byte
from .gpu import (
    nic_bw_per_gpu_effective,
    nic_rate_per_gpu,
    nvlink_bw_per_gpu,
    nvlink_bw_per_gpu_effective,
)
from .physical import t_flight


sys_link = System(
    name="interconnect",
    scope="interconnect",
    description="Packet efficiency, latency decomposition, NVLink, and scale-out fabrics.",
)


DIMENSIONLESS = sp.Integer(1)

LINK_PATH_REF = Reference(
    "Interconnect link model: packet payload efficiency, alpha-beta latency, "
    "queueing, and bandwidth-delay product are tracked as metadata-bearing "
    "symbolic relations.",
    kind="model",
)
NVLINK_FABRIC_REF = Reference(
    "NVLink tier model: effective per-GPU payload bandwidth from the GPU "
    "scope is paired with hop latency and rack-domain aggregation.",
    kind="model",
)
SCALEOUT_FABRIC_REF = Reference(
    "Scale-out fabric model: per-GPU NIC rails, oversubscription, hop latency, "
    "and bisection bandwidth are represented as first-order fabric relations.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Generic message path: payload efficiency, latency, and queueing
# ---------------------------------------------------------------------------

raw_line_rate = var(
    "link.raw_line_rate", "BW_line_raw", "byte/s",
    "Raw physical line rate before protocol overhead.",
    scope="interconnect",
    sp_units=BPS,
    references=[LINK_PATH_REF],
)
packet_payload_bytes = var(
    "link.packet.payload_bytes", "B_pkt_payload", "byte",
    "Useful payload bytes carried by one link-layer packet.",
    scope="interconnect",
    sp_units=byte,
    references=[LINK_PATH_REF],
)
packet_header_bytes = var(
    "link.packet.header_bytes", "B_pkt_hdr", "byte",
    "Per-packet framing, routing, and protocol overhead bytes.",
    scope="interconnect",
    sp_units=byte,
    references=[LINK_PATH_REF],
)
packet_efficiency = var(
    "link.packet.efficiency", "eta_pkt", "dimensionless",
    "Fraction of raw line bytes that become payload bytes after headers.",
    scope="interconnect",
    sp_units=DIMENSIONLESS,
    references=[LINK_PATH_REF],
)
bw_link = var(
    "link.bw", "BW_L", "byte/s",
    "Nominal payload bandwidth of the path before congestion loss.",
    scope="interconnect",
    sp_units=BPS,
    references=[LINK_PATH_REF],
)
eta_fabric = var(
    "link.efficiency", "eta_fab", "dimensionless",
    "Fabric efficiency after routing, arbitration, and implementation losses but before explicit oversubscription.",
    scope="interconnect",
    sp_units=DIMENSIONLESS,
    references=[LINK_PATH_REF],
)
oversubscription_ratio = var(
    "link.oversubscription", "rho_oversub", "dimensionless",
    "Oversubscription ratio of the studied path. One is non-oversubscribed; larger values reduce available bandwidth.",
    scope="interconnect",
    sp_units=DIMENSIONLESS,
    references=[LINK_PATH_REF],
)
bw_eff = var(
    "link.effective_bw", "BW_eff", "byte/s",
    "Effective payload bandwidth after protocol efficiency, congestion loss, and oversubscription.",
    scope="interconnect",
    sp_units=BPS,
    references=[LINK_PATH_REF],
)
n_switch_hops = var(
    "link.path.switch_hops", "H_sw", "hops",
    "Number of switch hops on the message path.",
    scope="interconnect",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[LINK_PATH_REF],
)
t_switch_hop = var(
    "link.switch.hop_latency", "t_sw_hop", "s",
    "Per-switch hop latency contribution.",
    scope="interconnect",
    sp_units=SECOND,
    references=[LINK_PATH_REF],
)
t_host_stack = var(
    "link.host_stack_latency", "t_host", "s",
    "Host and endpoint stack latency added before the first byte leaves the endpoint.",
    scope="interconnect",
    sp_units=SECOND,
    references=[LINK_PATH_REF],
)
lat_link = var(
    "link.latency", "t_L", "s",
    "Base one-message path latency before payload serialization.",
    scope="interconnect",
    sp_units=SECOND,
    references=[LINK_PATH_REF],
)
alpha_link = var(
    "link.alpha", "alpha_L", "s",
    "Startup latency term in the alpha-beta model for the studied path.",
    scope="interconnect",
    sp_units=SECOND,
    references=[LINK_PATH_REF],
)
beta_link = var(
    "link.beta", "beta_L", "s/byte",
    "Per-byte transfer time for the studied path.",
    scope="interconnect",
    sp_units=SECOND / byte,
    references=[LINK_PATH_REF],
)
link_utilization = var(
    "link.utilization", "rho_link", "dimensionless",
    "Average utilization of the studied path under the offered traffic pattern.",
    scope="interconnect",
    sp_units=DIMENSIONLESS,
    references=[LINK_PATH_REF],
)
msg_size = var(
    "link.msg_size", "B_msg", "byte",
    "Message size in payload bytes.",
    scope="interconnect",
    sp_units=byte,
    references=[LINK_PATH_REF],
)
n_packets_msg = var(
    "link.msg_packets", "N_pkt_msg", "packets",
    "Packet count required to carry the message payload.",
    scope="interconnect",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[LINK_PATH_REF],
)
t_queue_per_packet = var(
    "link.queue.per_packet", "t_q_pkt", "s",
    "Average queueing delay per packet on the studied path.",
    scope="interconnect",
    sp_units=SECOND,
    references=[LINK_PATH_REF],
)
t_queue_msg = var(
    "link.queue.msg", "t_q_msg", "s",
    "Queueing delay accumulated across all packets of the message.",
    scope="interconnect",
    sp_units=SECOND,
    references=[LINK_PATH_REF],
)
t_msg = var(
    "link.msg_time", "t_msg", "s",
    "Message time under an alpha-beta model with an explicit queueing term.",
    scope="interconnect",
    sp_units=SECOND,
    references=[LINK_PATH_REF],
)
bandwidth_delay_product = var(
    "link.bandwidth_delay_product", "BDP_L", "byte",
    "Bandwidth-delay product of the studied path.",
    scope="interconnect",
    sp_units=byte,
    references=[LINK_PATH_REF],
)

eq_packet_efficiency = eq(
    "link.eq.packet_efficiency",
    packet_efficiency.symbol,
    packet_payload_bytes.symbol / (packet_payload_bytes.symbol + packet_header_bytes.symbol),
    "Packet efficiency is payload bytes divided by total bytes on the wire.",
    references=[LINK_PATH_REF],
    check_units=True,
)
eq_bw_link = eq(
    "link.eq.bw",
    bw_link.symbol,
    raw_line_rate.symbol * packet_efficiency.symbol,
    "Nominal payload bandwidth equals raw line rate times packet efficiency.",
    references=[LINK_PATH_REF],
    check_units=True,
)
eq_bw_eff = eq(
    "link.eq.effective_bw",
    bw_eff.symbol,
    bw_link.symbol * eta_fabric.symbol / oversubscription_ratio.symbol,
    "Effective payload bandwidth equals nominal payload bandwidth times fabric efficiency and divided by oversubscription.",
    references=[LINK_PATH_REF],
    check_units=True,
)
eq_path_latency = eq(
    "link.eq.path_latency",
    lat_link.symbol,
    t_host_stack.symbol + n_switch_hops.symbol * t_switch_hop.symbol + t_flight.symbol,
    "Base path latency adds endpoint stack latency, switch-hop latency, and physical propagation time of flight.",
    references=[LINK_PATH_REF],
    check_units=True,
)
eq_alpha = eq(
    "link.eq.alpha",
    alpha_link.symbol,
    lat_link.symbol,
    "The alpha term is the startup latency of the message path.",
    references=[LINK_PATH_REF],
    check_units=True,
)
eq_beta = eq(
    "link.eq.beta",
    beta_link.symbol,
    1 / bw_eff.symbol,
    "The beta term is the reciprocal of effective payload bandwidth.",
    references=[LINK_PATH_REF],
    check_units=True,
)
eq_n_packets_msg = eq(
    "link.eq.msg_packets",
    n_packets_msg.symbol,
    sp.ceiling(msg_size.symbol / packet_payload_bytes.symbol),
    "Message packet count is the ceiling of message bytes over payload bytes per packet.",
    references=[LINK_PATH_REF],
)
approx_queue_per_packet = Approximation(
    "link.eq.queue_per_packet",
    t_queue_per_packet.symbol,
    (link_utilization.symbol / (1 - link_utilization.symbol)) * packet_payload_bytes.symbol / bw_eff.symbol,
    validity=sp.StrictLessThan(link_utilization.symbol, 1),
    description="Under an M/M/1-style approximation, queueing delay grows roughly as rho/(1-rho) times the packet serialization time, valid while utilization stays below one.",
    references=[LINK_PATH_REF],
    check_units=True,
)
eq_queue_msg = eq(
    "link.eq.queue_msg",
    t_queue_msg.symbol,
    n_packets_msg.symbol * t_queue_per_packet.symbol,
    "Message queueing delay is packet count times average per-packet queueing delay.",
    references=[LINK_PATH_REF],
    check_units=True,
)
eq_alpha_beta = eq(
    "link.eq.alpha_beta",
    t_msg.symbol,
    alpha_link.symbol + beta_link.symbol * msg_size.symbol + t_queue_msg.symbol,
    "Message time is startup latency plus serialized payload time plus accumulated queueing delay.",
    references=[LINK_PATH_REF, "Hockney, 1994."],
    check_units=True,
)
eq_bandwidth_delay_product = eq(
    "link.eq.bandwidth_delay_product",
    bandwidth_delay_product.symbol,
    bw_eff.symbol * lat_link.symbol,
    "Bandwidth-delay product equals effective payload bandwidth times path latency.",
    references=[LINK_PATH_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# NVLink tier
# ---------------------------------------------------------------------------

bw_nvlink_effective = var(
    "link.nvlink.bw_effective", "BW_NVL_eff", "byte/s",
    "Effective NVLink payload bandwidth per GPU on the studied topology tier.",
    scope="interconnect",
    sp_units=BPS,
    references=[NVLINK_FABRIC_REF],
)
nvlink_avg_hops = var(
    "link.nvlink.avg_hops", "H_NVL_avg", "hops",
    "Average NVLink hop count along the path under study.",
    scope="interconnect",
    sp_units=DIMENSIONLESS,
    references=[NVLINK_FABRIC_REF],
)
nvlink_hop_latency = var(
    "link.nvlink.hop_latency", "t_NVL_hop", "s",
    "Per-hop NVLink latency contribution.",
    scope="interconnect",
    sp_units=SECOND,
    references=[NVLINK_FABRIC_REF],
)
lat_nvlink = var(
    "link.nvlink.latency", "t_NVL", "s",
    "Base NVLink path latency for the studied path.",
    scope="interconnect",
    sp_units=SECOND,
    references=[NVLINK_FABRIC_REF],
)
alpha_nvlink = var(
    "link.nvlink.alpha", "alpha_NVL", "s",
    "Startup latency term for NVLink messages.",
    scope="interconnect",
    sp_units=SECOND,
    references=[NVLINK_FABRIC_REF],
)
beta_nvlink = var(
    "link.nvlink.beta", "beta_NVL", "s/byte",
    "Per-byte transfer time for effective NVLink payload traffic.",
    scope="interconnect",
    sp_units=SECOND / byte,
    references=[NVLINK_FABRIC_REF],
)
n_gpus_per_rack = var(
    "link.rack.n_gpus", "N_GPU_rack", "GPUs/rack",
    "GPUs in the rack-level NVLink domain or superpod unit under study.",
    scope="interconnect",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[NVLINK_FABRIC_REF],
)
rack_bisection_factor = var(
    "link.rack.bisection_factor", "phi_bisect_rack", "dimensionless",
    "Factor mapping aggregate per-GPU NVLink injection bandwidth to rack bisection bandwidth.",
    scope="interconnect",
    sp_units=DIMENSIONLESS,
    references=[NVLINK_FABRIC_REF],
)
bw_nvlink_rack = var(
    "link.rack.aggregate_bw", "BW_NVL_rack", "byte/s",
    "Rack-level NVLink bisection bandwidth.",
    scope="interconnect",
    sp_units=BPS,
    references=[NVLINK_FABRIC_REF],
)

eq_bw_nvlink_effective = eq(
    "link.eq.nvlink_bw_effective",
    bw_nvlink_effective.symbol,
    nvlink_bw_per_gpu_effective.symbol,
    "The interconnect-scope effective NVLink bandwidth aliases the GPU-scope effective NVLink bandwidth.",
    references=[NVLINK_FABRIC_REF],
    check_units=True,
)
eq_lat_nvlink = eq(
    "link.eq.nvlink_latency",
    lat_nvlink.symbol,
    nvlink_avg_hops.symbol * nvlink_hop_latency.symbol + t_flight.symbol,
    "NVLink path latency adds NVLink hop latency and physical propagation time of flight.",
    references=[NVLINK_FABRIC_REF],
    check_units=True,
)
eq_alpha_nvlink = eq(
    "link.eq.nvlink_alpha",
    alpha_nvlink.symbol,
    lat_nvlink.symbol,
    "The NVLink alpha term is its startup latency.",
    references=[NVLINK_FABRIC_REF],
    check_units=True,
)
eq_beta_nvlink = eq(
    "link.eq.nvlink_beta",
    beta_nvlink.symbol,
    1 / bw_nvlink_effective.symbol,
    "The NVLink beta term is the reciprocal of effective NVLink payload bandwidth.",
    references=[NVLINK_FABRIC_REF],
    check_units=True,
)
eq_rack_aggregate = eq(
    "link.eq.rack_aggregate_bw",
    bw_nvlink_rack.symbol,
    rack_bisection_factor.symbol * n_gpus_per_rack.symbol * nvlink_bw_per_gpu_effective.symbol,
    "Rack bisection bandwidth is modeled as a topology-specific factor times aggregate per-GPU effective NVLink injection bandwidth.",
    references=[NVLINK_FABRIC_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Scale-out tier
# ---------------------------------------------------------------------------

scaleout_rails_per_gpu = var(
    "link.scaleout.rails_per_gpu", "N_SO_rails", "rails",
    "Number of independent scale-out rails or NIC paths attached to one GPU communication group.",
    scope="interconnect",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[SCALEOUT_FABRIC_REF],
)
bw_scale_out_per_gpu = var(
    "link.scaleout.bw_per_gpu", "BW_SO_GPU", "byte/s",
    "Nominal aggregate effective scale-out payload bandwidth per GPU before fabric oversubscription.",
    scope="interconnect",
    sp_units=BPS,
    references=[SCALEOUT_FABRIC_REF],
)
scaleout_oversubscription = var(
    "link.scaleout.oversubscription", "rho_SO_oversub", "dimensionless",
    "Scale-out oversubscription ratio across the studied tier.",
    scope="interconnect",
    sp_units=DIMENSIONLESS,
    references=[SCALEOUT_FABRIC_REF],
)
bw_scale_out_effective = var(
    "link.scaleout.bw_effective", "BW_SO_eff", "byte/s",
    "Effective scale-out payload bandwidth per GPU after rail aggregation and oversubscription loss.",
    scope="interconnect",
    sp_units=BPS,
    references=[SCALEOUT_FABRIC_REF],
)
scaleout_avg_hops = var(
    "link.scaleout.avg_hops", "H_SO_avg", "hops",
    "Average switch-hop count on the scale-out path.",
    scope="interconnect",
    sp_units=DIMENSIONLESS,
    references=[SCALEOUT_FABRIC_REF],
)
scaleout_hop_latency = var(
    "link.scaleout.hop_latency", "t_SO_hop", "s",
    "Per-hop latency in the scale-out fabric.",
    scope="interconnect",
    sp_units=SECOND,
    references=[SCALEOUT_FABRIC_REF],
)
scaleout_host_overhead = var(
    "link.scaleout.host_latency", "t_SO_host", "s",
    "Endpoint stack latency for scale-out messages.",
    scope="interconnect",
    sp_units=SECOND,
    references=[SCALEOUT_FABRIC_REF],
)
lat_scale_out = var(
    "link.scaleout.latency", "t_SO", "s",
    "Base scale-out path latency.",
    scope="interconnect",
    sp_units=SECOND,
    references=[SCALEOUT_FABRIC_REF],
)
alpha_scale_out = var(
    "link.scaleout.alpha", "alpha_SO", "s",
    "Startup latency term for scale-out messages.",
    scope="interconnect",
    sp_units=SECOND,
    references=[SCALEOUT_FABRIC_REF],
)
beta_scale_out = var(
    "link.scaleout.beta", "beta_SO", "s/byte",
    "Per-byte transfer time for effective scale-out payload traffic.",
    scope="interconnect",
    sp_units=SECOND / byte,
    references=[SCALEOUT_FABRIC_REF],
)
switch_radix = var(
    "link.switch.radix", "R_sw", "ports",
    "Per-switch radix or port count.",
    scope="interconnect",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[SCALEOUT_FABRIC_REF],
)
switch_cap = var(
    "link.switch.capacity", "C_sw", "byte/s",
    "Aggregate payload switching capacity of one switch.",
    scope="interconnect",
    sp_units=BPS,
    references=[SCALEOUT_FABRIC_REF],
)
bw_scale_out_bisection = var(
    "link.scaleout.bisection_bw", "BW_SO_bisect", "byte/s",
    "Scale-out bisection bandwidth across the rack or pod under study.",
    scope="interconnect",
    sp_units=BPS,
    references=[SCALEOUT_FABRIC_REF],
)

eq_bw_scale_out_per_gpu = eq(
    "link.eq.scaleout_bw_per_gpu",
    bw_scale_out_per_gpu.symbol,
    scaleout_rails_per_gpu.symbol * nic_bw_per_gpu_effective.symbol,
    "Nominal scale-out payload bandwidth per GPU equals rail count times effective NIC payload bandwidth.",
    references=[SCALEOUT_FABRIC_REF],
    check_units=True,
)
eq_bw_scale_out_effective = eq(
    "link.eq.scaleout_bw_effective",
    bw_scale_out_effective.symbol,
    bw_scale_out_per_gpu.symbol / scaleout_oversubscription.symbol,
    "Effective scale-out payload bandwidth divides nominal aggregate rail bandwidth by oversubscription.",
    references=[SCALEOUT_FABRIC_REF],
    check_units=True,
)
eq_lat_scale_out = eq(
    "link.eq.scaleout_latency",
    lat_scale_out.symbol,
    scaleout_host_overhead.symbol + scaleout_avg_hops.symbol * scaleout_hop_latency.symbol + t_flight.symbol,
    "Scale-out path latency adds endpoint stack overhead, switch-hop latency, and physical propagation time of flight.",
    references=[SCALEOUT_FABRIC_REF],
    check_units=True,
)
eq_alpha_scale_out = eq(
    "link.eq.scaleout_alpha",
    alpha_scale_out.symbol,
    lat_scale_out.symbol,
    "The scale-out alpha term is its startup latency.",
    references=[SCALEOUT_FABRIC_REF],
    check_units=True,
)
eq_beta_scale_out = eq(
    "link.eq.scaleout_beta",
    beta_scale_out.symbol,
    1 / bw_scale_out_effective.symbol,
    "The scale-out beta term is the reciprocal of effective scale-out payload bandwidth.",
    references=[SCALEOUT_FABRIC_REF],
    check_units=True,
)
eq_scale_out_bisection = eq(
    "link.eq.scaleout_bisection_bw",
    bw_scale_out_bisection.symbol,
    n_gpus_per_rack.symbol * bw_scale_out_effective.symbol,
    "A first-order scale-out bisection estimate multiplies effective per-GPU scale-out bandwidth by GPU count in the domain.",
    references=[SCALEOUT_FABRIC_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Ratios across tiers
# ---------------------------------------------------------------------------

ratio_intra_to_scale_out = var(
    "link.ratio.intra_over_scale_out", "r_intra_SO", "dimensionless",
    "Effective NVLink payload bandwidth per GPU divided by effective scale-out payload bandwidth per GPU.",
    scope="interconnect",
    sp_units=DIMENSIONLESS,
    references=[SCALEOUT_FABRIC_REF],
)

eq_ratio_intra_scale_out = eq(
    "link.eq.intra_over_scale_out",
    ratio_intra_to_scale_out.symbol,
    bw_nvlink_effective.symbol / bw_scale_out_effective.symbol,
    "The intra-node to scale-out ratio compares effective NVLink payload bandwidth against effective scale-out payload bandwidth.",
    references=[SCALEOUT_FABRIC_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

for v in [
    raw_line_rate,
    packet_payload_bytes,
    packet_header_bytes,
    packet_efficiency,
    bw_link,
    eta_fabric,
    oversubscription_ratio,
    bw_eff,
    n_switch_hops,
    t_switch_hop,
    t_host_stack,
    lat_link,
    alpha_link,
    beta_link,
    link_utilization,
    msg_size,
    n_packets_msg,
    t_queue_per_packet,
    t_queue_msg,
    t_msg,
    bandwidth_delay_product,
    bw_nvlink_effective,
    nvlink_avg_hops,
    nvlink_hop_latency,
    lat_nvlink,
    alpha_nvlink,
    beta_nvlink,
    n_gpus_per_rack,
    rack_bisection_factor,
    bw_nvlink_rack,
    scaleout_rails_per_gpu,
    bw_scale_out_per_gpu,
    scaleout_oversubscription,
    bw_scale_out_effective,
    scaleout_avg_hops,
    scaleout_hop_latency,
    scaleout_host_overhead,
    lat_scale_out,
    alpha_scale_out,
    beta_scale_out,
    switch_radix,
    switch_cap,
    bw_scale_out_bisection,
    ratio_intra_to_scale_out,
]:
    sys_link.add(v)

for e in [
    eq_packet_efficiency,
    eq_bw_link,
    eq_bw_eff,
    eq_path_latency,
    eq_alpha,
    eq_beta,
    eq_n_packets_msg,
    approx_queue_per_packet,
    eq_queue_msg,
    eq_alpha_beta,
    eq_bandwidth_delay_product,
    eq_bw_nvlink_effective,
    eq_lat_nvlink,
    eq_alpha_nvlink,
    eq_beta_nvlink,
    eq_rack_aggregate,
    eq_bw_scale_out_per_gpu,
    eq_bw_scale_out_effective,
    eq_lat_scale_out,
    eq_alpha_scale_out,
    eq_beta_scale_out,
    eq_scale_out_bisection,
    eq_ratio_intra_scale_out,
]:
    sys_link.add(e)
