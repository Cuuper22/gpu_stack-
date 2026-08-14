"""
scopes/interconnect_scaleout.py
===============================

The scale-out tier: the switched network that joins racks together.

Beyond the rack, GPUs communicate through NICs into a multi-stage switch
fabric — the scale-out network. Per-GPU bandwidth starts as rails (parallel
NIC paths) times effective NIC bandwidth from the gpu scope, then divides
by the fabric's oversubscription ratio, since upper switch tiers are
usually thinner than the edge. Latency stacks more parts than NVLink:
flight time, several switch hops, and the host network stack, so alpha
here is markedly larger.

Two structural figures complete the tier: bisection bandwidth (switch
radix and capacity determine how much traffic can cross the fabric's
midline) and the intra-over-scale-out ratio — NVLink bandwidth divided by
scale-out bandwidth per GPU — which quantifies why hierarchical
collectives keep as much traffic as possible inside the rack.
"""

from ..core import eq, var
from ..core.units import BPS, SECOND, byte
from .gpu import nic_bw_per_gpu_effective
from .interconnect_nvlink import bw_nvlink_effective, n_gpus_per_rack
from .interconnect_refs import DIMENSIONLESS, SCALEOUT_FABRIC_REF
from .physical import t_flight


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
ratio_intra_to_scale_out = var(
    "link.ratio.intra_over_scale_out", "r_intra_SO", "dimensionless",
    "Effective NVLink payload bandwidth per GPU divided by effective scale-out payload bandwidth per GPU.",
    scope="interconnect",
    sp_units=DIMENSIONLESS,
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
eq_ratio_intra_scale_out = eq(
    "link.eq.intra_over_scale_out",
    ratio_intra_to_scale_out.symbol,
    bw_nvlink_effective.symbol / bw_scale_out_effective.symbol,
    "The intra-node to scale-out ratio compares effective NVLink payload bandwidth against effective scale-out payload bandwidth.",
    references=[SCALEOUT_FABRIC_REF],
    check_units=True,
)


INTERCONNECT_SCALEOUT_VARIABLES = (
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
)

INTERCONNECT_SCALEOUT_EQUATIONS = (
    eq_bw_scale_out_per_gpu,
    eq_bw_scale_out_effective,
    eq_lat_scale_out,
    eq_alpha_scale_out,
    eq_beta_scale_out,
    eq_scale_out_bisection,
    eq_ratio_intra_scale_out,
)


__all__ = [
    "DIMENSIONLESS",
    "SCALEOUT_FABRIC_REF",
    "scaleout_rails_per_gpu",
    "bw_scale_out_per_gpu",
    "scaleout_oversubscription",
    "bw_scale_out_effective",
    "scaleout_avg_hops",
    "scaleout_hop_latency",
    "scaleout_host_overhead",
    "lat_scale_out",
    "alpha_scale_out",
    "beta_scale_out",
    "switch_radix",
    "switch_cap",
    "bw_scale_out_bisection",
    "ratio_intra_to_scale_out",
    "eq_bw_scale_out_per_gpu",
    "eq_bw_scale_out_effective",
    "eq_lat_scale_out",
    "eq_alpha_scale_out",
    "eq_beta_scale_out",
    "eq_scale_out_bisection",
    "eq_ratio_intra_scale_out",
    "INTERCONNECT_SCALEOUT_VARIABLES",
    "INTERCONNECT_SCALEOUT_EQUATIONS",
]
