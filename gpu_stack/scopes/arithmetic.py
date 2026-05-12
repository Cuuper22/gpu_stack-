"""
scopes/arithmetic.py
====================

Arithmetic units inside the SM.

The original file stopped at one generic MMA shape and one scalar FMA count.
That was not enough to reason about structured sparsity, integer dot-product
paths, or SFU-limited kernels. This version keeps the generic Tensor Core path
and adds the missing alternative datapaths.
"""

import sympy as sp
from ..core import Reference, System, eq, var
from ..core.units import FLOP, FLOPS, SECOND
from .physical import f_clock


DIMENSIONLESS = sp.Integer(1)
OPS = DIMENSIONLESS / SECOND

ARITHMETIC_THROUGHPUT_REF = Reference(
    "Arithmetic throughput accounting: per-instruction work counts and "
    "per-cycle issue rates scale by functional-unit count and clock frequency.",
    kind="model",
)
TENSOR_CORE_MMA_REF = Reference(
    "NVIDIA PTX ISA matrix multiply-accumulate semantics: one MMA tile "
    "performs multiply-add accumulation over M, N, and K dimensions.",
    kind="manual",
)
STRUCTURED_SPARSITY_REF = Reference(
    "Structured sparsity dense-equivalent throughput model: hardware skips "
    "masked weights and reports speedup relative to dense work.",
    kind="model",
)
INTEGER_DOT_REF = Reference(
    "Integer dot-product instruction accounting: DP4A performs four "
    "multiply-accumulates and DP2A performs two multiply-accumulates.",
    kind="manual",
)
SFU_THROUGHPUT_REF = Reference(
    "Special Function Unit throughput accounting for transcendental "
    "operations such as exp, log, reciprocal, and reciprocal square root.",
    kind="model",
)


sys_arith = System(
    name="arithmetic",
    scope="arithmetic",
    description="ALU, FMA, Tensor Core, integer dot-product, and SFU throughput inside one SM.",
)


# ---------------------------------------------------------------------------
# Scalar and vector arithmetic
# ---------------------------------------------------------------------------

flops_per_fma = var(
    "arith.fma.flops_per_op", "N_flop_fma_arith", "FLOP",
    "FLOPs counted per fused multiply-add, normally two.",
    scope="arithmetic",
    sp_units=FLOP,
    references=[ARITHMETIC_THROUGHPUT_REF],
)
ops_per_alu_cycle = var(
    "arith.alu.ops_per_cycle", "N_alu_cyc_arith", "op/cycle",
    "Scalar ALU operations issued per thread or lane per clock.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[ARITHMETIC_THROUGHPUT_REF],
)
n_fma_per_sm = var(
    "arith.fma.count_per_sm", "N_fma_sm_arith", "units",
    "Non-Tensor-Core FMA lanes per SM.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[ARITHMETIC_THROUGHPUT_REF],
)
peak_fma_sm = var(
    "arith.sm.peak_fma_flops", "P_fma_sm_arith", "FLOP/s",
    "Peak non-Tensor-Core FMA FLOPs per SM.",
    scope="arithmetic",
    sp_units=FLOPS,
    references=[ARITHMETIC_THROUGHPUT_REF],
)


eq_peak_fma_sm = eq(
    "arith.eq.peak_fma_sm",
    peak_fma_sm.symbol,
    n_fma_per_sm.symbol * flops_per_fma.symbol * f_clock.symbol,
    "Scalar FMA peak equals FMA lanes times FLOPs per FMA times clock frequency.",
    references=[ARITHMETIC_THROUGHPUT_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Tensor Core MMA
# ---------------------------------------------------------------------------

mma_M = var(
    "arith.mma.M", "M_mma_arith", "dimensionless",
    "M dimension of the MMA tile.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[TENSOR_CORE_MMA_REF],
)
mma_N = var(
    "arith.mma.N", "N_mma_arith", "dimensionless",
    "N dimension of the MMA tile.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[TENSOR_CORE_MMA_REF],
)
mma_K = var(
    "arith.mma.K", "K_mma_arith", "dimensionless",
    "Reduction dimension of the MMA tile.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[TENSOR_CORE_MMA_REF],
)
flops_per_mma = var(
    "arith.mma.flops_per_inst", "F_mma_inst_arith", "FLOP",
    "FLOPs performed by one MMA instruction.",
    scope="arithmetic",
    sp_units=FLOP,
    references=[TENSOR_CORE_MMA_REF],
)
mma_per_tc_cycle = var(
    "arith.mma.per_tc_cycle", "r_mma_tc_cyc_arith", "MMA/cycle",
    "MMA instructions a single Tensor Core can issue per cycle.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[TENSOR_CORE_MMA_REF],
)
n_tc_per_sm = var(
    "arith.tc.per_sm", "N_tc_sm_arith", "units",
    "Tensor Cores per SM.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[TENSOR_CORE_MMA_REF],
)
flops_per_tc_cycle = var(
    "arith.tc.flops_per_cycle", "F_tc_cyc_arith", "FLOP/cycle",
    "FLOPs delivered by one Tensor Core in one cycle.",
    scope="arithmetic",
    sp_units=FLOP,
    references=[TENSOR_CORE_MMA_REF],
)
peak_flops_sm = var(
    "arith.sm.peak_flops", "P_sm_tc_arith", "FLOP/s",
    "Peak Tensor-Core FLOPs per SM at the chosen MMA shape and issue rate.",
    scope="arithmetic",
    sp_units=FLOPS,
    references=[TENSOR_CORE_MMA_REF],
)
tc_issue_efficiency = var(
    "arith.tc.issue_efficiency", "rho_tc_issue_arith", "dimensionless",
    "Fraction of theoretical Tensor Core issue slots actually filled by a kernel.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[TENSOR_CORE_MMA_REF],
)
peak_flops_sm_effective = var(
    "arith.sm.peak_flops_effective", "P_sm_tc_eff_arith", "FLOP/s",
    "Effective Tensor-Core FLOPs per SM after applying issue efficiency.",
    scope="arithmetic",
    sp_units=FLOPS,
    references=[TENSOR_CORE_MMA_REF],
)


eq_flops_per_mma = eq(
    "arith.eq.flops_per_mma",
    flops_per_mma.symbol,
    2 * mma_M.symbol * mma_N.symbol * mma_K.symbol,
    "An MMA computes one multiply and one add for each accumulation term, so FLOPs per instruction are 2 * M * N * K.",
    references=[TENSOR_CORE_MMA_REF],
    check_units=True,
)

eq_flops_per_tc_cycle = eq(
    "arith.eq.flops_per_tc_cycle",
    flops_per_tc_cycle.symbol,
    flops_per_mma.symbol * mma_per_tc_cycle.symbol,
    "Tensor-Core FLOPs per cycle equal FLOPs per MMA times MMAs issued per cycle.",
    references=[TENSOR_CORE_MMA_REF],
    check_units=True,
)

eq_peak_flops_sm = eq(
    "arith.eq.peak_flops_sm",
    peak_flops_sm.symbol,
    n_tc_per_sm.symbol * flops_per_tc_cycle.symbol * f_clock.symbol,
    "Peak Tensor-Core FLOPs per SM equal Tensor Cores per SM times FLOPs per Tensor Core cycle times clock frequency.",
    references=[TENSOR_CORE_MMA_REF],
    check_units=True,
)

eq_peak_flops_sm_effective = eq(
    "arith.eq.peak_flops_sm_effective",
    peak_flops_sm_effective.symbol,
    peak_flops_sm.symbol * tc_issue_efficiency.symbol,
    "Effective Tensor-Core throughput equals theoretical peak times the achieved issue efficiency.",
    references=[TENSOR_CORE_MMA_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Structured sparsity
# ---------------------------------------------------------------------------

sparsity_group_size = var(
    "arith.sparsity.group_size", "N_sparse_grp_arith", "weights",
    "Weights per structured-sparsity group, four in a 2:4 pattern.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[STRUCTURED_SPARSITY_REF],
)
sparsity_nonzero_per_group = var(
    "arith.sparsity.nonzero_per_group", "N_sparse_nz_arith", "weights",
    "Nonzero weights retained per structured-sparsity group, two in a 2:4 pattern.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[STRUCTURED_SPARSITY_REF],
)
sparsity_speedup = var(
    "arith.sparsity.speedup", "r_sparse_arith", "dimensionless",
    "Dense-equivalent throughput multiplier from hardware-accelerated structured sparsity.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[STRUCTURED_SPARSITY_REF],
)
peak_flops_sm_sparse = var(
    "arith.sm.peak_flops_sparse", "P_sm_sparse_arith", "FLOP/s",
    "Dense-equivalent sparse Tensor-Core peak per SM.",
    scope="arithmetic",
    sp_units=FLOPS,
    references=[STRUCTURED_SPARSITY_REF],
)


eq_sparsity_speedup = eq(
    "arith.eq.sparsity_speedup",
    sparsity_speedup.symbol,
    sparsity_group_size.symbol / sparsity_nonzero_per_group.symbol,
    "If hardware only multiplies the surviving nonzeros, dense-equivalent throughput scales as group_size divided by nonzeros_per_group.",
    references=[STRUCTURED_SPARSITY_REF],
    check_units=True,
)

eq_peak_flops_sm_sparse = eq(
    "arith.eq.peak_flops_sm_sparse",
    peak_flops_sm_sparse.symbol,
    peak_flops_sm.symbol * sparsity_speedup.symbol,
    "Sparse dense-equivalent peak equals dense peak times the structured-sparsity speedup.",
    references=[STRUCTURED_SPARSITY_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Integer dot-product paths
# ---------------------------------------------------------------------------

n_dp4a_per_sm = var(
    "arith.int.dp4a_per_sm", "N_dp4a_sm_arith", "units",
    "DP4A-capable integer dot-product units per SM.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[INTEGER_DOT_REF],
)
int_ops_per_dp4a = var(
    "arith.int.dp4a_ops_per_inst", "N_dp4a_ops_arith", "ops",
    "Integer operations counted per DP4A instruction.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[INTEGER_DOT_REF],
)
peak_dp4a_sm = var(
    "arith.sm.peak_dp4a_ops", "P_dp4a_sm_arith", "op/s",
    "Peak DP4A integer operations per second per SM.",
    scope="arithmetic",
    sp_units=OPS,
    references=[INTEGER_DOT_REF],
)
n_dp2a_per_sm = var(
    "arith.int.dp2a_per_sm", "N_dp2a_sm_arith", "units",
    "DP2A-capable integer dot-product units per SM.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[INTEGER_DOT_REF],
)
int_ops_per_dp2a = var(
    "arith.int.dp2a_ops_per_inst", "N_dp2a_ops_arith", "ops",
    "Integer operations counted per DP2A instruction.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[INTEGER_DOT_REF],
)
peak_dp2a_sm = var(
    "arith.sm.peak_dp2a_ops", "P_dp2a_sm_arith", "op/s",
    "Peak DP2A integer operations per second per SM.",
    scope="arithmetic",
    sp_units=OPS,
    references=[INTEGER_DOT_REF],
)


eq_int_ops_per_dp4a = eq(
    "arith.eq.int_ops_per_dp4a",
    int_ops_per_dp4a.symbol,
    8,
    "A DP4A instruction performs four integer multiply-accumulates, eight scalar integer ops if each multiply and add is counted separately.",
    references=[INTEGER_DOT_REF],
    check_units=True,
)

eq_peak_dp4a_sm = eq(
    "arith.eq.peak_dp4a_sm",
    peak_dp4a_sm.symbol,
    n_dp4a_per_sm.symbol * int_ops_per_dp4a.symbol * f_clock.symbol,
    "Peak DP4A throughput equals units per SM times integer ops per instruction times clock frequency.",
    references=[INTEGER_DOT_REF],
    check_units=True,
)

eq_int_ops_per_dp2a = eq(
    "arith.eq.int_ops_per_dp2a",
    int_ops_per_dp2a.symbol,
    4,
    "A DP2A instruction performs two integer multiply-accumulates, four scalar integer ops if multiplies and adds are counted separately.",
    references=[INTEGER_DOT_REF],
    check_units=True,
)

eq_peak_dp2a_sm = eq(
    "arith.eq.peak_dp2a_sm",
    peak_dp2a_sm.symbol,
    n_dp2a_per_sm.symbol * int_ops_per_dp2a.symbol * f_clock.symbol,
    "Peak DP2A throughput equals units per SM times integer ops per instruction times clock frequency.",
    references=[INTEGER_DOT_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Special Function Units
# ---------------------------------------------------------------------------

sfu_ops_per_cycle_sm = var(
    "arith.sfu.ops_per_cycle_sm", "N_sfu_cyc_arith", "op/cycle",
    "SFU operations the SM can retire per cycle.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[SFU_THROUGHPUT_REF],
)
peak_sfu_ops_sm = var(
    "arith.sm.peak_sfu_ops", "P_sfu_sm_arith", "op/s",
    "Peak SFU operations per second per SM.",
    scope="arithmetic",
    sp_units=OPS,
    references=[SFU_THROUGHPUT_REF],
)
transcendental_ops_per_token = var(
    "arith.sfu.transcendental_ops_per_token", "N_sfu_tok_arith", "op/token",
    "Transcendental operations per token for a kernel, such as exp, log, rcp, or rsqrt inside softmax or normalization.",
    scope="arithmetic",
    sp_units=DIMENSIONLESS,
    references=[SFU_THROUGHPUT_REF],
)
sfu_time_per_token = var(
    "arith.sfu.time_per_token", "T_sfu_tok_arith", "s/token",
    "Lower-bound time per token if the kernel is purely SFU-limited on one SM.",
    scope="arithmetic",
    sp_units=SECOND,
    references=[SFU_THROUGHPUT_REF],
)


eq_peak_sfu_ops_sm = eq(
    "arith.eq.peak_sfu_ops_sm",
    peak_sfu_ops_sm.symbol,
    sfu_ops_per_cycle_sm.symbol * f_clock.symbol,
    "Peak SFU throughput equals SFU operations per cycle times clock frequency.",
    references=[SFU_THROUGHPUT_REF],
    check_units=True,
)

eq_sfu_time_per_token = eq(
    "arith.eq.sfu_time_per_token",
    sfu_time_per_token.symbol,
    transcendental_ops_per_token.symbol / peak_sfu_ops_sm.symbol,
    "An SFU-only lower bound is transcendental ops per token divided by peak SFU throughput.",
    references=[SFU_THROUGHPUT_REF],
    check_units=True,
)


ARITHMETIC_VARIABLES = [
    flops_per_fma, ops_per_alu_cycle, n_fma_per_sm, peak_fma_sm,
    mma_M, mma_N, mma_K, flops_per_mma, mma_per_tc_cycle, n_tc_per_sm,
    flops_per_tc_cycle, peak_flops_sm, tc_issue_efficiency,
    peak_flops_sm_effective,
    sparsity_group_size, sparsity_nonzero_per_group, sparsity_speedup,
    peak_flops_sm_sparse,
    n_dp4a_per_sm, int_ops_per_dp4a, peak_dp4a_sm,
    n_dp2a_per_sm, int_ops_per_dp2a, peak_dp2a_sm,
    sfu_ops_per_cycle_sm, peak_sfu_ops_sm, transcendental_ops_per_token,
    sfu_time_per_token,
]

ARITHMETIC_EQUATIONS = [
    eq_peak_fma_sm,
    eq_flops_per_mma,
    eq_flops_per_tc_cycle,
    eq_peak_flops_sm,
    eq_peak_flops_sm_effective,
    eq_sparsity_speedup,
    eq_peak_flops_sm_sparse,
    eq_int_ops_per_dp4a,
    eq_peak_dp4a_sm,
    eq_int_ops_per_dp2a,
    eq_peak_dp2a_sm,
    eq_peak_sfu_ops_sm,
    eq_sfu_time_per_token,
]

for v in ARITHMETIC_VARIABLES:
    sys_arith.add(v)

for e in ARITHMETIC_EQUATIONS:
    sys_arith.add(e)
