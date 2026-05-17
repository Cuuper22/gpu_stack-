"""
scopes/interconnect_nvlink.py
=============================

NVLink-tier fabric relations and rack-domain aggregation.
"""

from ..core import eq, var
from ..core.units import BPS, SECOND, byte
from .gpu import nvlink_bw_per_gpu_effective
from .interconnect_refs import DIMENSIONLESS, NVLINK_FABRIC_REF
from .physical import t_flight


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


INTERCONNECT_NVLINK_VARIABLES = (
    bw_nvlink_effective,
    nvlink_avg_hops,
    nvlink_hop_latency,
    lat_nvlink,
    alpha_nvlink,
    beta_nvlink,
    n_gpus_per_rack,
    rack_bisection_factor,
    bw_nvlink_rack,
)

INTERCONNECT_NVLINK_EQUATIONS = (
    eq_bw_nvlink_effective,
    eq_lat_nvlink,
    eq_alpha_nvlink,
    eq_beta_nvlink,
    eq_rack_aggregate,
)


__all__ = [
    "DIMENSIONLESS",
    "NVLINK_FABRIC_REF",
    "bw_nvlink_effective",
    "nvlink_avg_hops",
    "nvlink_hop_latency",
    "lat_nvlink",
    "alpha_nvlink",
    "beta_nvlink",
    "n_gpus_per_rack",
    "rack_bisection_factor",
    "bw_nvlink_rack",
    "eq_bw_nvlink_effective",
    "eq_lat_nvlink",
    "eq_alpha_nvlink",
    "eq_beta_nvlink",
    "eq_rack_aggregate",
    "INTERCONNECT_NVLINK_VARIABLES",
    "INTERCONNECT_NVLINK_EQUATIONS",
]
