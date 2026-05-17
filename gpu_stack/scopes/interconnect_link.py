"""
scopes/interconnect_link.py
===========================

Generic message path relations: packet efficiency, latency decomposition,
alpha-beta transfer time, queueing, and bandwidth-delay product.
"""

import sympy as sp

from ..core import Approximation, eq, var
from ..core.units import BPS, SECOND, byte
from .interconnect_refs import DIMENSIONLESS, LINK_PATH_REF
from .physical import t_flight


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


INTERCONNECT_LINK_VARIABLES = (
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
)

INTERCONNECT_LINK_EQUATIONS = (
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
)


__all__ = [
    "DIMENSIONLESS",
    "LINK_PATH_REF",
    "raw_line_rate",
    "packet_payload_bytes",
    "packet_header_bytes",
    "packet_efficiency",
    "bw_link",
    "eta_fabric",
    "oversubscription_ratio",
    "bw_eff",
    "n_switch_hops",
    "t_switch_hop",
    "t_host_stack",
    "lat_link",
    "alpha_link",
    "beta_link",
    "link_utilization",
    "msg_size",
    "n_packets_msg",
    "t_queue_per_packet",
    "t_queue_msg",
    "t_msg",
    "bandwidth_delay_product",
    "eq_packet_efficiency",
    "eq_bw_link",
    "eq_bw_eff",
    "eq_path_latency",
    "eq_alpha",
    "eq_beta",
    "eq_n_packets_msg",
    "approx_queue_per_packet",
    "eq_queue_msg",
    "eq_alpha_beta",
    "eq_bandwidth_delay_product",
    "INTERCONNECT_LINK_VARIABLES",
    "INTERCONNECT_LINK_EQUATIONS",
]
