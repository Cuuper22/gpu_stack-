"""
scopes/memory_smem.py
=====================

Shared memory (SMEM) and Tensor Memory (TMEM). Covers banked bandwidth,
L1 / SMEM carveout math, and TMEM service throughput.
"""

from ..core import eq, var
from .memory_regfile import mem_array_clock


# ---------------------------------------------------------------------------
# Shared memory and L1
# ---------------------------------------------------------------------------

l1_smem_pool_bytes_per_sm = var(
    "mem.l1_smem.pool_bytes_per_sm", "B_L1SMEM_pool", "byte",
    "Unified on-SM SRAM pool partitioned between shared memory and L1.",
    scope="memory_subsystem",
)
smem_bytes_per_sm = var(
    "mem.smem.bytes_per_sm", "B_SMEM", "byte",
    "Shared-memory allocation carved out per SM.",
    scope="memory_subsystem",
)
smem_bw_per_sm = var(
    "mem.smem.bw_per_sm", "BW_SMEM_sm", "byte/s",
    "Effective shared-memory bandwidth per SM.",
    scope="memory_subsystem",
)
smem_latency = var(
    "mem.smem.latency", "t_SMEM", "s",
    "Shared-memory load latency.",
    scope="memory_subsystem",
)
l1_bytes_per_sm = var(
    "mem.l1.bytes_per_sm", "B_L1", "byte",
    "Effective L1 capacity after the SMEM carveout.",
    scope="memory_subsystem",
)
smem_bank_count = var(
    "mem.smem.bank_count", "N_bank_SMEM", "banks",
    "Shared-memory bank count.",
    scope="memory_subsystem",
)
smem_bank_width_bytes = var(
    "mem.smem.bank_width", "B_bank_SMEM", "byte",
    "Bytes served per bank access.",
    scope="memory_subsystem",
)
smem_ports_per_bank = var(
    "mem.smem.ports_per_bank", "N_port_SMEM", "ports",
    "Effective service ports per SMEM bank.",
    scope="memory_subsystem",
)
smem_bw_peak = var(
    "mem.smem.bw_peak", "BW_SMEM_peak", "byte/s",
    "Peak shared-memory bandwidth before conflicts.",
    scope="memory_subsystem",
)
smem_conflict_factor = var(
    "mem.smem.conflict_factor", "k_SMEM_conf", "dimensionless",
    "Bandwidth loss factor from shared-memory bank conflicts.",
    scope="memory_subsystem",
)
e_per_byte_smem = var(
    "mem.energy.per_byte_smem", "E_B_smem", "J/byte",
    "Energy per byte read from SMEM.",
    scope="memory_subsystem",
)


# ---------------------------------------------------------------------------
# Tensor Memory (TMEM)
# ---------------------------------------------------------------------------

tmem_bytes_per_sm = var(
    "mem.tmem.bytes_per_sm", "B_TMEM", "byte",
    "Tensor Memory per SM.",
    scope="memory_subsystem",
)
tmem_bw_per_sm = var(
    "mem.tmem.bw_per_sm", "BW_TMEM_sm", "byte/s",
    "Tensor Memory bandwidth per SM.",
    scope="memory_subsystem",
)
tmem_mma_write_latency = var(
    "mem.tmem.mma_write_latency", "t_TMEM_w", "s",
    "Latency from MMA issue to TMEM accumulator update.",
    scope="memory_subsystem",
)
tmem_bank_count = var(
    "mem.tmem.bank_count", "N_bank_TMEM", "banks",
    "Tensor Memory bank count.",
    scope="memory_subsystem",
)
tmem_bank_width_bytes = var(
    "mem.tmem.bank_width", "B_bank_TMEM", "byte",
    "Bytes served per TMEM bank access.",
    scope="memory_subsystem",
)
tmem_ports_per_bank = var(
    "mem.tmem.ports_per_bank", "N_port_TMEM", "ports",
    "Effective service ports per TMEM bank.",
    scope="memory_subsystem",
)
tmem_bw_peak = var(
    "mem.tmem.bw_peak", "BW_TMEM_peak", "byte/s",
    "Peak TMEM bandwidth per SM.",
    scope="memory_subsystem",
)


eq_l1_capacity = eq(
    "mem.eq.l1_capacity",
    l1_bytes_per_sm.symbol,
    l1_smem_pool_bytes_per_sm.symbol - smem_bytes_per_sm.symbol,
    "L1 capacity is whatever remains after carving out shared memory from the unified SRAM pool.",
)

eq_smem_bw_peak = eq(
    "mem.eq.smem_bw_peak",
    smem_bw_peak.symbol,
    smem_bank_count.symbol * smem_bank_width_bytes.symbol * smem_ports_per_bank.symbol * mem_array_clock.symbol,
    "Peak SMEM bandwidth from bank count, width, ports, and cycle rate.",
)

eq_smem_bw_effective = eq(
    "mem.eq.smem_bw_effective",
    smem_bw_per_sm.symbol,
    smem_bw_peak.symbol / smem_conflict_factor.symbol,
    "Effective SMEM bandwidth after bank conflicts.",
)

eq_tmem_bw_peak = eq(
    "mem.eq.tmem_bw_peak",
    tmem_bw_peak.symbol,
    tmem_bank_count.symbol * tmem_bank_width_bytes.symbol * tmem_ports_per_bank.symbol * mem_array_clock.symbol,
    "Peak TMEM bandwidth from banks, width, ports, and cycle rate.",
)

eq_tmem_bw = eq(
    "mem.eq.tmem_bw",
    tmem_bw_per_sm.symbol,
    tmem_bw_peak.symbol,
    "TMEM bandwidth currently treated as peak service bandwidth because the access pattern is warp-synchronous and heavily structured.",
)


MEMSUB_SMEM_VARIABLES = (
    l1_smem_pool_bytes_per_sm,
    smem_bytes_per_sm,
    smem_bw_per_sm,
    smem_latency,
    l1_bytes_per_sm,
    smem_bank_count,
    smem_bank_width_bytes,
    smem_ports_per_bank,
    smem_bw_peak,
    smem_conflict_factor,
    tmem_bytes_per_sm,
    tmem_bw_per_sm,
    tmem_mma_write_latency,
    tmem_bank_count,
    tmem_bank_width_bytes,
    tmem_ports_per_bank,
    tmem_bw_peak,
    e_per_byte_smem,
)

MEMSUB_SMEM_EQUATIONS = (
    eq_l1_capacity,
    eq_smem_bw_peak,
    eq_smem_bw_effective,
    eq_tmem_bw_peak,
    eq_tmem_bw,
)


__all__ = [
    "l1_smem_pool_bytes_per_sm",
    "smem_bytes_per_sm",
    "smem_bw_per_sm",
    "smem_latency",
    "l1_bytes_per_sm",
    "smem_bank_count",
    "smem_bank_width_bytes",
    "smem_ports_per_bank",
    "smem_bw_peak",
    "smem_conflict_factor",
    "tmem_bytes_per_sm",
    "tmem_bw_per_sm",
    "tmem_mma_write_latency",
    "tmem_bank_count",
    "tmem_bank_width_bytes",
    "tmem_ports_per_bank",
    "tmem_bw_peak",
    "e_per_byte_smem",
    "eq_l1_capacity",
    "eq_smem_bw_peak",
    "eq_smem_bw_effective",
    "eq_tmem_bw_peak",
    "eq_tmem_bw",
    "MEMSUB_SMEM_VARIABLES",
    "MEMSUB_SMEM_EQUATIONS",
]
