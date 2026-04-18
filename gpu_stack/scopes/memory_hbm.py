"""
scopes/memory_hbm.py
====================

HBM organization, usable bandwidth, and capacity after refresh, ECC
overhead, and memory compression.
"""

from ..core import eq, var


# ---------------------------------------------------------------------------
# HBM and its usable bandwidth or capacity
# ---------------------------------------------------------------------------

hbm_stack_count = var(
    "mem.hbm.stacks", "N_HBM_stacks", "units",
    "Number of HBM stacks on the package.",
    scope="memory_subsystem",
)
hbm_stack_capacity = var(
    "mem.hbm.stack_capacity", "B_HBM_stack", "byte",
    "Capacity per HBM stack.",
    scope="memory_subsystem",
)
hbm_capacity = var(
    "mem.hbm.capacity", "B_HBM", "byte",
    "Total raw HBM capacity per GPU package.",
    scope="memory_subsystem",
)
hbm_pins_per_stack = var(
    "mem.hbm.pins_per_stack", "N_pins_HBM", "pins",
    "Data pins per HBM stack.",
    scope="memory_subsystem",
)
hbm_pin_rate = var(
    "mem.hbm.pin_rate", "r_pin_HBM", "bit/s/pin",
    "Per-pin signaling rate.",
    scope="memory_subsystem",
)
hbm_bw_per_stack = var(
    "mem.hbm.bw_per_stack", "BW_HBM_stack", "byte/s",
    "Per-stack HBM bandwidth.",
    scope="memory_subsystem",
)
hbm_bw = var(
    "mem.hbm.bw", "BW_HBM", "byte/s",
    "Total raw HBM bandwidth per GPU package.",
    scope="memory_subsystem",
)
hbm_latency = var(
    "mem.hbm.latency", "t_HBM", "s",
    "Average HBM read latency.",
    scope="memory_subsystem",
)
hbm_refresh_overhead = var(
    "mem.hbm.refresh_overhead", "phi_refresh_HBM", "dimensionless",
    "Fraction of raw HBM bandwidth lost to refresh activity.",
    scope="memory_subsystem",
)
hbm_bw_effective = var(
    "mem.hbm.bw_effective", "BW_HBM_eff", "byte/s",
    "Usable HBM bandwidth after refresh overhead.",
    scope="memory_subsystem",
)
hbm_ecc_overhead = var(
    "mem.hbm.ecc_overhead", "phi_ecc_HBM", "dimensionless",
    "Fraction of raw HBM capacity consumed by ECC or metadata overhead.",
    scope="memory_subsystem",
)
hbm_capacity_usable = var(
    "mem.hbm.capacity_usable", "B_HBM_use", "byte",
    "Usable HBM capacity after ECC or metadata overhead.",
    scope="memory_subsystem",
)
mem_compression_ratio = var(
    "mem.hbm.compression_ratio", "rho_comp_mem", "dimensionless",
    "Effective compression ratio seen by memory traffic or footprint.",
    scope="memory_subsystem",
)
hbm_effective_capacity = var(
    "mem.hbm.capacity_effective", "B_HBM_eff_cap", "byte",
    "Effective HBM capacity after usable-capacity adjustment and compression.",
    scope="memory_subsystem",
)
e_per_byte_hbm = var(
    "mem.energy.per_byte_hbm", "E_B_hbm", "J/byte",
    "Energy per byte read from HBM.",
    scope="memory_subsystem",
)

eq_hbm_capacity = eq(
    "mem.eq.hbm_capacity",
    hbm_capacity.symbol,
    hbm_stack_count.symbol * hbm_stack_capacity.symbol,
    "HBM capacity equals stack count times per-stack capacity.",
)

eq_hbm_bw_per_stack = eq(
    "mem.eq.hbm_bw_per_stack",
    hbm_bw_per_stack.symbol,
    hbm_pins_per_stack.symbol * hbm_pin_rate.symbol / 8,
    "Per-stack HBM bandwidth in bytes per second.",
)

eq_hbm_bw_total = eq(
    "mem.eq.hbm_bw_total",
    hbm_bw.symbol,
    hbm_stack_count.symbol * hbm_bw_per_stack.symbol,
    "Total HBM bandwidth across all stacks.",
)

eq_hbm_bw_effective = eq(
    "mem.eq.hbm_bw_effective",
    hbm_bw_effective.symbol,
    hbm_bw.symbol * (1 - hbm_refresh_overhead.symbol),
    "Effective HBM bandwidth after refresh steals a fraction of service cycles.",
)

eq_hbm_capacity_usable = eq(
    "mem.eq.hbm_capacity_usable",
    hbm_capacity_usable.symbol,
    hbm_capacity.symbol * (1 - hbm_ecc_overhead.symbol),
    "Usable HBM capacity after ECC or metadata overhead.",
)

eq_hbm_capacity_effective = eq(
    "mem.eq.hbm_capacity_effective",
    hbm_effective_capacity.symbol,
    hbm_capacity_usable.symbol * mem_compression_ratio.symbol,
    "Effective HBM capacity after compression.",
)


MEMSUB_HBM_VARIABLES = (
    hbm_stack_count,
    hbm_stack_capacity,
    hbm_capacity,
    hbm_pins_per_stack,
    hbm_pin_rate,
    hbm_bw_per_stack,
    hbm_bw,
    hbm_latency,
    hbm_refresh_overhead,
    hbm_bw_effective,
    hbm_ecc_overhead,
    hbm_capacity_usable,
    mem_compression_ratio,
    hbm_effective_capacity,
    e_per_byte_hbm,
)

MEMSUB_HBM_EQUATIONS = (
    eq_hbm_capacity,
    eq_hbm_bw_per_stack,
    eq_hbm_bw_total,
    eq_hbm_bw_effective,
    eq_hbm_capacity_usable,
    eq_hbm_capacity_effective,
)


__all__ = [
    "hbm_stack_count",
    "hbm_stack_capacity",
    "hbm_capacity",
    "hbm_pins_per_stack",
    "hbm_pin_rate",
    "hbm_bw_per_stack",
    "hbm_bw",
    "hbm_latency",
    "hbm_refresh_overhead",
    "hbm_bw_effective",
    "hbm_ecc_overhead",
    "hbm_capacity_usable",
    "mem_compression_ratio",
    "hbm_effective_capacity",
    "e_per_byte_hbm",
    "eq_hbm_capacity",
    "eq_hbm_bw_per_stack",
    "eq_hbm_bw_total",
    "eq_hbm_bw_effective",
    "eq_hbm_capacity_usable",
    "eq_hbm_capacity_effective",
    "MEMSUB_HBM_VARIABLES",
    "MEMSUB_HBM_EQUATIONS",
]
