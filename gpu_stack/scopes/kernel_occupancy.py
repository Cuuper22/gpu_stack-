"""
scopes/kernel_occupancy.py
==========================

CTA resource accounting from threads, registers, and shared memory.
Active-block and occupancy formulas. Latency-hiding factor from active
warps per SM. Combines the bandwidth and latency lower bounds into the
full kernel body and wall-clock time.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import FLOPS, SECOND, byte
from .memory_subsystem import (
    avg_global_load_latency,
    reg_file_bytes_per_sm,
    reg_width_bits,
    smem_bytes_per_sm,
    threads_per_sm_max,
    warp_size,
)
from .kernel_roofline import (
    bytes_kernel,
    flops_kernel,
    global_load_count,
    t_compute_bound,
    t_hbm_bound,
    t_l2_bound,
    t_reg_bound,
    t_smem_bound,
)


DIMENSIONLESS = sp.Integer(1)

KERNEL_OCCUPANCY_REF = Reference(
    "CUDA occupancy model: resident CTAs and warps are constrained by thread, "
    "register-file, and shared-memory resources per SM.",
    kind="model",
)
KERNEL_LATENCY_HIDING_REF = Reference(
    "SIMT latency-hiding model: active resident warps cover exposed global-load "
    "latency until the scheduler reaches a full-hide occupancy point.",
    kind="model",
)
KERNEL_BODY_TIME_REF = Reference(
    "Kernel body time model: wall-clock kernel time is launch overhead plus the "
    "maximum of compute, bandwidth, and exposed-latency bounds.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Occupancy and CTA resource limits
# ---------------------------------------------------------------------------

threads_per_block = var(
    "kernel.cta.threads_per_block", "N_thr_blk_k", "threads",
    "Threads launched per CTA or block.",
    scope="kernel",
    integer=True,
)
warps_per_block = var(
    "kernel.cta.warps_per_block", "N_warp_blk_k", "warps",
    "Warps per CTA or block.",
    scope="kernel",
)
regs_per_thread_kernel = var(
    "kernel.cta.regs_per_thread", "N_reg_thr_k", "registers",
    "Registers consumed per thread by the kernel.",
    scope="kernel",
)
reg_bytes_per_block = var(
    "kernel.cta.reg_bytes_per_block", "B_reg_blk_k", "byte",
    "Register-file bytes reserved per CTA.",
    scope="kernel",
)
smem_bytes_per_block = var(
    "kernel.cta.smem_bytes_per_block", "B_smem_blk_k", "byte",
    "Shared-memory bytes reserved per CTA.",
    scope="kernel",
)
blocks_limit_threads = var(
    "kernel.occupancy.blocks_limit_threads", "N_blk_thr_lim_k", "blocks/SM",
    "CTA residency limit imposed by the thread budget per SM.",
    scope="kernel",
)
blocks_limit_regs = var(
    "kernel.occupancy.blocks_limit_regs", "N_blk_reg_lim_k", "blocks/SM",
    "CTA residency limit imposed by the register-file budget per SM.",
    scope="kernel",
)
blocks_limit_smem = var(
    "kernel.occupancy.blocks_limit_smem", "N_blk_smem_lim_k", "blocks/SM",
    "CTA residency limit imposed by the shared-memory budget per SM.",
    scope="kernel",
)
blocks_active_per_sm = var(
    "kernel.occupancy.blocks_active_per_sm", "N_blk_act_k", "blocks/SM",
    "Resident CTAs per SM after taking the minimum over resource limits.",
    scope="kernel",
)
warps_active = var(
    "kernel.occupancy.warps_active", "W_act", "warps/SM",
    "Active warps per SM during kernel execution.",
    scope="kernel",
)
warps_max = var(
    "kernel.occupancy.warps_max", "W_max", "warps/SM",
    "Maximum warps the SM can hold.",
    scope="kernel",
)
occupancy = var(
    "kernel.occupancy", "occ", "dimensionless",
    "Kernel occupancy, meaning active warps divided by maximum resident warps.",
    scope="kernel",
    positive=True,
    value_range=(0.0, 1.0),
)
occ_full_hide = var(
    "kernel.occupancy.full_hide", "occ_full_k", "dimensionless",
    "Occupancy level at which additional active warps no longer materially improve latency hiding.",
    scope="kernel",
    positive=True,
    value_range=(0.0, 1.0),
)
latency_hiding_factor = var(
    "kernel.latency_hiding_factor", "eta_hide_k", "dimensionless",
    "Fraction of full latency-hiding capacity achieved from active occupancy.",
    scope="kernel",
    positive=True,
    value_range=(0.0, 1.0),
)
t_latency_bound = var(
    "kernel.time_latency_bound", "T_lat_k", "s",
    "Latency-bound execution time contribution after occupancy-based hiding.",
    scope="kernel",
)
t_body = var(
    "kernel.time_body", "T_body_k", "s",
    "Steady-state kernel body time after taking the maximum of all relevant ceilings.",
    scope="kernel",
)
t_kernel = var(
    "kernel.time", "t_k", "s",
    "Full wall-clock time to execute the kernel, including launch overhead.",
    scope="kernel",
)
t_launch = var(
    "kernel.launch_overhead", "t_launch", "s",
    "Launch latency or graph-replay overhead before the kernel body begins.",
    scope="kernel",
)
achieved_flops = var(
    "kernel.achieved_flops", "P_ach", "FLOP/s",
    "Achieved throughput of the kernel, including launch overhead.",
    scope="kernel",
)

for _v in (
    threads_per_block,
    warps_per_block,
    regs_per_thread_kernel,
    blocks_limit_threads,
    blocks_limit_regs,
    blocks_limit_smem,
    blocks_active_per_sm,
    warps_active,
    warps_max,
    occupancy,
    occ_full_hide,
    latency_hiding_factor,
):
    _v.sp_units = DIMENSIONLESS
    _v.references.append(KERNEL_OCCUPANCY_REF)

for _v in (reg_bytes_per_block, smem_bytes_per_block):
    _v.sp_units = byte
    _v.references.append(KERNEL_OCCUPANCY_REF)

for _v in (t_latency_bound, t_body, t_kernel, t_launch):
    _v.sp_units = SECOND
    _v.references.append(KERNEL_BODY_TIME_REF)

achieved_flops.sp_units = FLOPS
achieved_flops.references.append(KERNEL_BODY_TIME_REF)

eq_warps_per_block = eq(
    "kernel.eq.warps_per_block",
    warps_per_block.symbol,
    threads_per_block.symbol / warp_size.symbol,
    "Warps per CTA equal threads per CTA divided by warp size.",
    references=[KERNEL_OCCUPANCY_REF],
    check_units=True,
)
eq_reg_bytes_per_block = eq(
    "kernel.eq.reg_bytes_per_block",
    reg_bytes_per_block.symbol,
    threads_per_block.symbol * regs_per_thread_kernel.symbol * reg_width_bits.symbol / 8,
    "Register bytes per CTA equal threads times registers per thread times register width in bytes.",
    references=[KERNEL_OCCUPANCY_REF],
    check_units=True,
)
eq_blocks_limit_threads = eq(
    "kernel.eq.blocks_limit_threads",
    blocks_limit_threads.symbol,
    sp.floor(threads_per_sm_max.symbol / threads_per_block.symbol),
    "Thread-limited CTA residency is the floor of threads per SM over threads per CTA.",
    references=[KERNEL_OCCUPANCY_REF],
)
eq_blocks_limit_regs = eq(
    "kernel.eq.blocks_limit_regs",
    blocks_limit_regs.symbol,
    sp.floor(reg_file_bytes_per_sm.symbol / reg_bytes_per_block.symbol),
    "Register-limited CTA residency is the floor of register bytes per SM over register bytes per CTA.",
    references=[KERNEL_OCCUPANCY_REF],
)
eq_blocks_limit_smem = eq(
    "kernel.eq.blocks_limit_smem",
    blocks_limit_smem.symbol,
    sp.floor(smem_bytes_per_sm.symbol / smem_bytes_per_block.symbol),
    "Shared-memory-limited CTA residency is the floor of SMEM bytes per SM over SMEM bytes per CTA.",
    references=[KERNEL_OCCUPANCY_REF],
)
eq_blocks_active_per_sm = eq(
    "kernel.eq.blocks_active_per_sm",
    blocks_active_per_sm.symbol,
    sp.Min(blocks_limit_threads.symbol, blocks_limit_regs.symbol, blocks_limit_smem.symbol),
    "Resident CTAs per SM are limited by the tightest of the thread, register, and shared-memory budgets.",
    references=[KERNEL_OCCUPANCY_REF],
    check_units=True,
)
eq_warps_max = eq(
    "kernel.eq.warps_max",
    warps_max.symbol,
    threads_per_sm_max.symbol / warp_size.symbol,
    "Maximum resident warps equal the SM thread budget divided by warp size.",
    references=[KERNEL_OCCUPANCY_REF],
    check_units=True,
)
eq_warps_active = eq(
    "kernel.eq.warps_active",
    warps_active.symbol,
    blocks_active_per_sm.symbol * warps_per_block.symbol,
    "Active warps equal resident CTAs per SM times warps per CTA.",
    references=[KERNEL_OCCUPANCY_REF],
    check_units=True,
)
eq_occupancy = eq(
    "kernel.eq.occupancy",
    occupancy.symbol,
    warps_active.symbol / warps_max.symbol,
    "Occupancy equals active warps divided by maximum resident warps.",
    references=[KERNEL_OCCUPANCY_REF],
    check_units=True,
)
eq_latency_hiding_factor = eq(
    "kernel.eq.latency_hiding_factor",
    latency_hiding_factor.symbol,
    sp.Min(1, occupancy.symbol / occ_full_hide.symbol),
    "If occupancy is below the full-hide point, the latency-hiding efficiency falls in proportion to the shortfall. Once occupancy reaches the full-hide point, additional warps do not reduce exposed latency further.",
    references=[KERNEL_LATENCY_HIDING_REF],
    check_units=True,
)
eq_t_latency_bound = eq(
    "kernel.eq.time_latency_bound",
    t_latency_bound.symbol,
    global_load_count.symbol * avg_global_load_latency.symbol / latency_hiding_factor.symbol,
    "Latency-bound time multiplies average global-load latency by the effective count of exposed loads after occupancy-based hiding.",
    references=[KERNEL_LATENCY_HIDING_REF],
    check_units=True,
)
eq_t_body = eq(
    "kernel.eq.time_body",
    t_body.symbol,
    sp.Max(t_compute_bound.symbol, t_hbm_bound.symbol, t_l2_bound.symbol, t_smem_bound.symbol, t_reg_bound.symbol, t_latency_bound.symbol),
    "The kernel body time is the maximum of the compute, bandwidth, and latency lower bounds.",
    references=[KERNEL_BODY_TIME_REF],
    check_units=True,
)
eq_kernel_time = eq(
    "kernel.eq.time",
    t_kernel.symbol,
    t_launch.symbol + t_body.symbol,
    "Full kernel time equals launch overhead plus steady-state kernel body time.",
    references=[KERNEL_BODY_TIME_REF],
    check_units=True,
)
eq_achieved_flops = eq(
    "kernel.eq.achieved_flops",
    achieved_flops.symbol,
    flops_kernel.symbol / t_kernel.symbol,
    "Achieved FLOPs equal kernel FLOPs divided by full kernel time, including launch overhead.",
    references=[KERNEL_BODY_TIME_REF],
    check_units=True,
)


KERNEL_OCCUPANCY_VARIABLES = (
    threads_per_block,
    warps_per_block,
    regs_per_thread_kernel,
    reg_bytes_per_block,
    smem_bytes_per_block,
    blocks_limit_threads,
    blocks_limit_regs,
    blocks_limit_smem,
    blocks_active_per_sm,
    warps_active,
    warps_max,
    occupancy,
    occ_full_hide,
    latency_hiding_factor,
    t_latency_bound,
    t_body,
    t_kernel,
    t_launch,
    achieved_flops,
)

KERNEL_OCCUPANCY_EQUATIONS = (
    eq_warps_per_block,
    eq_reg_bytes_per_block,
    eq_blocks_limit_threads,
    eq_blocks_limit_regs,
    eq_blocks_limit_smem,
    eq_blocks_active_per_sm,
    eq_warps_max,
    eq_warps_active,
    eq_occupancy,
    eq_latency_hiding_factor,
    eq_t_latency_bound,
    eq_t_body,
    eq_kernel_time,
    eq_achieved_flops,
)


__all__ = [
    "threads_per_block",
    "warps_per_block",
    "regs_per_thread_kernel",
    "reg_bytes_per_block",
    "smem_bytes_per_block",
    "blocks_limit_threads",
    "blocks_limit_regs",
    "blocks_limit_smem",
    "blocks_active_per_sm",
    "warps_active",
    "warps_max",
    "occupancy",
    "occ_full_hide",
    "latency_hiding_factor",
    "t_latency_bound",
    "t_body",
    "t_kernel",
    "t_launch",
    "achieved_flops",
    "eq_warps_per_block",
    "eq_reg_bytes_per_block",
    "eq_blocks_limit_threads",
    "eq_blocks_limit_regs",
    "eq_blocks_limit_smem",
    "eq_blocks_active_per_sm",
    "eq_warps_max",
    "eq_warps_active",
    "eq_occupancy",
    "eq_latency_hiding_factor",
    "eq_t_latency_bound",
    "eq_t_body",
    "eq_kernel_time",
    "eq_achieved_flops",
    "KERNEL_OCCUPANCY_VARIABLES",
    "KERNEL_OCCUPANCY_EQUATIONS",
]
