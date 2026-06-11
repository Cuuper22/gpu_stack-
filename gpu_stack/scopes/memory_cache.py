"""
scopes/memory_cache.py
======================

L1 and L2 cache organization. Covers bytes, line size, associativity,
sets, partitions, miss penalty, and the average global-load latency
assembly from cache hit rates.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import BPS, JOULE, SECOND
from .memory_smem import l1_bytes_per_sm
from .memory_hbm import hbm_latency
from .memory_virtual import avg_translation_latency


# ---------------------------------------------------------------------------
# L1 cache organization
# ---------------------------------------------------------------------------

DIMENSIONLESS = sp.Integer(1)
BYTE = BPS * SECOND

CACHE_ORGANIZATION_REF = Reference(
    "Computer architecture texts and GPU architecture documentation describe "
    "cache line size, associativity, set/partition organization, hit rates, "
    "and miss penalties.",
    kind="textbook",
)

l1_line_bytes = var(
    "mem.l1.line_bytes", "B_line_L1", "byte",
    "L1 cache line size.",
    scope="memory_subsystem",
    sp_units=BYTE,
    references=[CACHE_ORGANIZATION_REF],
)
l1_assoc = var(
    "mem.l1.assoc", "A_L1", "ways",
    "L1 associativity.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[CACHE_ORGANIZATION_REF],
)
l1_sets = var(
    "mem.l1.sets", "N_set_L1", "sets",
    "Number of L1 sets.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[CACHE_ORGANIZATION_REF],
)
l1_hit_rate = var(
    "mem.l1.hit_rate", "p_hit_L1", "dimensionless",
    "L1 hit probability for the workload of interest.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[CACHE_ORGANIZATION_REF],
)
l1_latency = var(
    "mem.l1.latency", "t_L1", "s",
    "L1-hit latency.",
    scope="memory_subsystem",
    sp_units=SECOND,
    references=[CACHE_ORGANIZATION_REF],
)


# ---------------------------------------------------------------------------
# L2 organization and miss penalties
# ---------------------------------------------------------------------------

l2_bytes = var(
    "mem.l2.bytes", "B_L2", "byte",
    "L2 cache capacity, chip-wide.",
    scope="memory_subsystem",
    sp_units=BYTE,
    references=[CACHE_ORGANIZATION_REF],
)
l2_bw = var(
    "mem.l2.bw", "BW_L2", "byte/s",
    "Aggregate L2 bandwidth.",
    scope="memory_subsystem",
    sp_units=BPS,
    references=[CACHE_ORGANIZATION_REF],
)
l2_line_bytes = var(
    "mem.l2.line_bytes", "B_line_L2", "byte",
    "L2 cache line size.",
    scope="memory_subsystem",
    sp_units=BYTE,
    references=[CACHE_ORGANIZATION_REF],
)
l2_assoc = var(
    "mem.l2.assoc", "A_L2", "ways",
    "L2 associativity.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[CACHE_ORGANIZATION_REF],
)
l2_partitions = var(
    "mem.l2.partitions", "N_part_L2", "partitions",
    "Independent L2 partitions or slices.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[CACHE_ORGANIZATION_REF],
)
l2_sets_per_partition = var(
    "mem.l2.sets_per_partition", "N_set_L2", "sets",
    "Sets per L2 partition.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[CACHE_ORGANIZATION_REF],
)
l2_hit_rate = var(
    "mem.l2.hit_rate", "p_hit_L2", "dimensionless",
    "Conditional L2 hit probability given an L1 miss.",
    scope="memory_subsystem",
    sp_units=DIMENSIONLESS,
    references=[CACHE_ORGANIZATION_REF],
)
l2_latency = var(
    "mem.l2.latency", "t_L2", "s",
    "L2-hit latency.",
    scope="memory_subsystem",
    sp_units=SECOND,
    references=[CACHE_ORGANIZATION_REF],
)
l2_miss_penalty = var(
    "mem.l2.miss_penalty", "t_miss_L2", "s",
    "Additional latency of an L2 miss that falls through to HBM.",
    scope="memory_subsystem",
    sp_units=SECOND,
    references=[CACHE_ORGANIZATION_REF],
)
avg_global_load_latency = var(
    "mem.global_load.latency_avg", "t_glob_avg", "s",
    "Average latency of a global-memory access after cache and translation effects.",
    scope="memory_subsystem",
    sp_units=SECOND,
    references=[CACHE_ORGANIZATION_REF],
)
e_per_byte_l2 = var(
    "mem.energy.per_byte_l2", "E_B_l2", "J/byte",
    "Energy per byte read from L2.",
    scope="memory_subsystem",
    sp_units=JOULE / BYTE,
    references=[CACHE_ORGANIZATION_REF],
)


eq_l1_sets = eq(
    "mem.eq.l1_sets",
    l1_sets.symbol,
    l1_bytes_per_sm.symbol / (l1_line_bytes.symbol * l1_assoc.symbol),
    "Set count from total bytes divided by line size times associativity.",
    references=[CACHE_ORGANIZATION_REF],
    check_units=True,
)

eq_l2_sets = eq(
    "mem.eq.l2_sets_per_partition",
    l2_sets_per_partition.symbol,
    l2_bytes.symbol / (l2_partitions.symbol * l2_line_bytes.symbol * l2_assoc.symbol),
    "L2 sets per partition from total capacity, partition count, line size, and associativity.",
    references=[CACHE_ORGANIZATION_REF],
    check_units=True,
)

eq_l2_miss_penalty = eq(
    "mem.eq.l2_miss_penalty",
    l2_miss_penalty.symbol,
    hbm_latency.symbol - l2_latency.symbol,
    "Additional latency of falling through from L2 to HBM.",
    references=[CACHE_ORGANIZATION_REF],
    check_units=True,
)

eq_avg_global_load_latency = eq(
    "mem.eq.avg_global_load_latency",
    avg_global_load_latency.symbol,
    l1_hit_rate.symbol * l1_latency.symbol
    + (1 - l1_hit_rate.symbol)
      * (l2_hit_rate.symbol * l2_latency.symbol + (1 - l2_hit_rate.symbol) * hbm_latency.symbol)
    + avg_translation_latency.symbol,
    "Average global-memory latency from cache hit rates plus translation overhead.",
    references=[CACHE_ORGANIZATION_REF],
    check_units=True,
)


MEMSUB_CACHE_VARIABLES = (
    l1_line_bytes,
    l1_assoc,
    l1_sets,
    l1_hit_rate,
    l1_latency,
    l2_bytes,
    l2_bw,
    l2_line_bytes,
    l2_assoc,
    l2_partitions,
    l2_sets_per_partition,
    l2_hit_rate,
    l2_latency,
    l2_miss_penalty,
    avg_global_load_latency,
    e_per_byte_l2,
)

MEMSUB_CACHE_EQUATIONS = (
    eq_l1_sets,
    eq_l2_sets,
    eq_l2_miss_penalty,
    eq_avg_global_load_latency,
)


__all__ = [
    "l1_line_bytes",
    "l1_assoc",
    "l1_sets",
    "l1_hit_rate",
    "l1_latency",
    "l2_bytes",
    "l2_bw",
    "l2_line_bytes",
    "l2_assoc",
    "l2_partitions",
    "l2_sets_per_partition",
    "l2_hit_rate",
    "l2_latency",
    "l2_miss_penalty",
    "avg_global_load_latency",
    "e_per_byte_l2",
    "eq_l1_sets",
    "eq_l2_sets",
    "eq_l2_miss_penalty",
    "eq_avg_global_load_latency",
    "MEMSUB_CACHE_VARIABLES",
    "MEMSUB_CACHE_EQUATIONS",
]
