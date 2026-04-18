"""
scopes/kernel.py
=================

Single-kernel performance models.

The old file had a toy roofline and one naive GEMM arithmetic-intensity
formula. That is not enough. Real kernels are constrained by several
ceilings at once:

  * compute issue efficiency
  * HBM, L2, SMEM, and register bandwidth
  * occupancy-driven latency hiding
  * CTA resource limits from threads, registers, and shared memory
  * tiling, which changes effective bytes and therefore arithmetic intensity

This scope adds those missing pieces while keeping the original public
variables alive.
"""

import sympy as sp

from ..core import System, eq, var
from .gpu import (
    hbm_bw_gpu_effective,
    n_sms,
    peak_flops_gpu_power_limited,
    reg_bw_gpu,
    smem_bw_gpu,
)
from .memory_subsystem import (
    avg_global_load_latency,
    reg_file_bytes_per_sm,
    reg_width_bits,
    smem_bytes_per_sm,
    threads_per_sm_max,
    warp_size,
    l2_bw,
)


sys_kern = System(
    name="kernel",
    scope="kernel",
    description="Kernel rooflines, occupancy, CTA resource limits, and tiled matmul or attention arithmetic intensity.",
)


# ---------------------------------------------------------------------------
# Generic kernel ceilings
# ---------------------------------------------------------------------------

flops_kernel = var(
    "kernel.flops", "F_k", "FLOP",
    "Total model or algorithmic FLOPs attributed to the kernel.",
    scope="kernel",
)
bytes_kernel = var(
    "kernel.bytes", "B_k", "byte",
    "HBM bytes attributed to the kernel.",
    scope="kernel",
)
arith_intensity = var(
    "kernel.arith_intensity", "AI_k", "FLOP/byte",
    "HBM arithmetic intensity of the kernel.",
    scope="kernel",
)
bytes_l2 = var(
    "kernel.l2.bytes", "B_L2_k", "byte",
    "Bytes served from L2 during the kernel.",
    scope="kernel",
)
bytes_smem = var(
    "kernel.smem.bytes", "B_smem_k", "byte",
    "Bytes served from shared memory during the kernel.",
    scope="kernel",
)
bytes_reg = var(
    "kernel.reg.bytes", "B_reg_k", "byte",
    "Bytes served from the register file during the kernel.",
    scope="kernel",
)
ai_l2 = var(
    "kernel.l2.arith_intensity", "AI_L2_k", "FLOP/byte",
    "Arithmetic intensity with L2 bytes as the denominator.",
    scope="kernel",
)
ai_smem = var(
    "kernel.smem.arith_intensity", "AI_smem_k", "FLOP/byte",
    "Arithmetic intensity with SMEM bytes as the denominator.",
    scope="kernel",
)
ai_reg = var(
    "kernel.reg.arith_intensity", "AI_reg_k", "FLOP/byte",
    "Arithmetic intensity with register-file bytes as the denominator.",
    scope="kernel",
)
compute_efficiency = var(
    "kernel.compute_efficiency", "eta_comp_k", "dimensionless",
    "Fraction of the GPU's power-limited effective peak that the kernel can actually realize on the compute side.",
    scope="kernel",
)
compute_ceiling = var(
    "kernel.compute_ceiling", "P_comp_k", "FLOP/s",
    "Kernel compute-side throughput ceiling after issue and scheduling losses.",
    scope="kernel",
)
hbm_ceiling = var(
    "kernel.hbm_ceiling", "P_hbm_k", "FLOP/s",
    "HBM roofline ceiling for the kernel.",
    scope="kernel",
)
l2_ceiling = var(
    "kernel.l2_ceiling", "P_l2_k", "FLOP/s",
    "L2 roofline ceiling for the kernel.",
    scope="kernel",
)
smem_ceiling = var(
    "kernel.smem_ceiling", "P_smem_k", "FLOP/s",
    "Shared-memory roofline ceiling for the kernel.",
    scope="kernel",
)
reg_ceiling = var(
    "kernel.reg_ceiling", "P_reg_k", "FLOP/s",
    "Register-file roofline ceiling for the kernel.",
    scope="kernel",
)
roofline_flops = var(
    "kernel.roofline_flops", "P_roof_k", "FLOP/s",
    "Roofline throughput ceiling across compute and all modeled memory levels.",
    scope="kernel",
)
achieved_flops = var(
    "kernel.achieved_flops", "P_ach", "FLOP/s",
    "Achieved throughput of the kernel, including launch overhead.",
    scope="kernel",
)
t_compute_bound = var(
    "kernel.time_compute_bound", "T_comp_k", "s",
    "Compute-bound execution time lower bound.",
    scope="kernel",
)
t_hbm_bound = var(
    "kernel.time_hbm_bound", "T_hbm_k", "s",
    "HBM-bandwidth-bound execution time lower bound.",
    scope="kernel",
)
t_l2_bound = var(
    "kernel.time_l2_bound", "T_l2_k", "s",
    "L2-bandwidth-bound execution time lower bound.",
    scope="kernel",
)
t_smem_bound = var(
    "kernel.time_smem_bound", "T_smem_k", "s",
    "SMEM-bandwidth-bound execution time lower bound.",
    scope="kernel",
)
t_reg_bound = var(
    "kernel.time_reg_bound", "T_reg_k", "s",
    "Register-bandwidth-bound execution time lower bound.",
    scope="kernel",
)
global_load_count = var(
    "kernel.global_load_count", "N_gl_k", "loads",
    "Count of globally visible memory operations whose latency still matters after caching and coalescing.",
    scope="kernel",
)
occ_full_hide = var(
    "kernel.occupancy.full_hide", "occ_full_k", "dimensionless",
    "Occupancy level at which additional active warps no longer materially improve latency hiding.",
    scope="kernel",
)
latency_hiding_factor = var(
    "kernel.latency_hiding_factor", "eta_hide_k", "dimensionless",
    "Fraction of average global-load latency that remains exposed after occupancy hides some stalls.",
    scope="kernel",
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

eq_arith_intensity = eq(
    "kernel.eq.arith_intensity",
    arith_intensity.symbol,
    flops_kernel.symbol / bytes_kernel.symbol,
    "HBM arithmetic intensity equals kernel FLOPs divided by HBM bytes.",
)
eq_ai_l2 = eq(
    "kernel.eq.l2_arith_intensity",
    ai_l2.symbol,
    flops_kernel.symbol / bytes_l2.symbol,
    "L2 arithmetic intensity equals kernel FLOPs divided by L2 bytes.",
)
eq_ai_smem = eq(
    "kernel.eq.smem_arith_intensity",
    ai_smem.symbol,
    flops_kernel.symbol / bytes_smem.symbol,
    "SMEM arithmetic intensity equals kernel FLOPs divided by SMEM bytes.",
)
eq_ai_reg = eq(
    "kernel.eq.reg_arith_intensity",
    ai_reg.symbol,
    flops_kernel.symbol / bytes_reg.symbol,
    "Register arithmetic intensity equals kernel FLOPs divided by register bytes.",
)
eq_compute_ceiling = eq(
    "kernel.eq.compute_ceiling",
    compute_ceiling.symbol,
    compute_efficiency.symbol * peak_flops_gpu_power_limited.symbol,
    "Compute ceiling equals the GPU's power-limited effective peak scaled by kernel-specific compute efficiency.",
)
eq_hbm_ceiling = eq(
    "kernel.eq.hbm_ceiling",
    hbm_ceiling.symbol,
    hbm_bw_gpu_effective.symbol * arith_intensity.symbol,
    "HBM roofline ceiling equals effective HBM bandwidth times HBM arithmetic intensity.",
)
eq_l2_ceiling = eq(
    "kernel.eq.l2_ceiling",
    l2_ceiling.symbol,
    l2_bw.symbol * ai_l2.symbol,
    "L2 roofline ceiling equals L2 bandwidth times L2 arithmetic intensity.",
)
eq_smem_ceiling = eq(
    "kernel.eq.smem_ceiling",
    smem_ceiling.symbol,
    smem_bw_gpu.symbol * ai_smem.symbol,
    "SMEM roofline ceiling equals aggregate SMEM bandwidth times SMEM arithmetic intensity.",
)
eq_reg_ceiling = eq(
    "kernel.eq.reg_ceiling",
    reg_ceiling.symbol,
    reg_bw_gpu.symbol * ai_reg.symbol,
    "Register-file roofline ceiling equals aggregate register bandwidth times register arithmetic intensity.",
)
eq_roofline = eq(
    "kernel.eq.roofline",
    roofline_flops.symbol,
    sp.Min(compute_ceiling.symbol, hbm_ceiling.symbol, l2_ceiling.symbol, smem_ceiling.symbol, reg_ceiling.symbol),
    "The generalized roofline ceiling is the minimum of the compute and memory-level ceilings.",
    references=[
        "Williams, Waterman, and Patterson, Roofline, CACM 2009.",
    ],
)
eq_t_compute_bound = eq(
    "kernel.eq.time_compute_bound",
    t_compute_bound.symbol,
    flops_kernel.symbol / compute_ceiling.symbol,
    "Compute-bound time lower bound equals FLOPs divided by the compute ceiling.",
)
eq_t_hbm_bound = eq(
    "kernel.eq.time_hbm_bound",
    t_hbm_bound.symbol,
    bytes_kernel.symbol / hbm_bw_gpu_effective.symbol,
    "HBM-bound time lower bound equals HBM bytes divided by effective HBM bandwidth.",
)
eq_t_l2_bound = eq(
    "kernel.eq.time_l2_bound",
    t_l2_bound.symbol,
    bytes_l2.symbol / l2_bw.symbol,
    "L2-bound time lower bound equals L2 bytes divided by L2 bandwidth.",
)
eq_t_smem_bound = eq(
    "kernel.eq.time_smem_bound",
    t_smem_bound.symbol,
    bytes_smem.symbol / smem_bw_gpu.symbol,
    "SMEM-bound time lower bound equals SMEM bytes divided by aggregate SMEM bandwidth.",
)
eq_t_reg_bound = eq(
    "kernel.eq.time_reg_bound",
    t_reg_bound.symbol,
    bytes_reg.symbol / reg_bw_gpu.symbol,
    "Register-bound time lower bound equals register bytes divided by aggregate register bandwidth.",
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
)

eq_warps_per_block = eq(
    "kernel.eq.warps_per_block",
    warps_per_block.symbol,
    threads_per_block.symbol / warp_size.symbol,
    "Warps per CTA equal threads per CTA divided by warp size.",
)
eq_reg_bytes_per_block = eq(
    "kernel.eq.reg_bytes_per_block",
    reg_bytes_per_block.symbol,
    threads_per_block.symbol * regs_per_thread_kernel.symbol * reg_width_bits.symbol / 8,
    "Register bytes per CTA equal threads times registers per thread times register width in bytes.",
)
eq_blocks_limit_threads = eq(
    "kernel.eq.blocks_limit_threads",
    blocks_limit_threads.symbol,
    sp.floor(threads_per_sm_max.symbol / threads_per_block.symbol),
    "Thread-limited CTA residency is the floor of threads per SM over threads per CTA.",
)
eq_blocks_limit_regs = eq(
    "kernel.eq.blocks_limit_regs",
    blocks_limit_regs.symbol,
    sp.floor(reg_file_bytes_per_sm.symbol / reg_bytes_per_block.symbol),
    "Register-limited CTA residency is the floor of register bytes per SM over register bytes per CTA.",
)
eq_blocks_limit_smem = eq(
    "kernel.eq.blocks_limit_smem",
    blocks_limit_smem.symbol,
    sp.floor(smem_bytes_per_sm.symbol / smem_bytes_per_block.symbol),
    "Shared-memory-limited CTA residency is the floor of SMEM bytes per SM over SMEM bytes per CTA.",
)
eq_blocks_active_per_sm = eq(
    "kernel.eq.blocks_active_per_sm",
    blocks_active_per_sm.symbol,
    sp.Min(blocks_limit_threads.symbol, blocks_limit_regs.symbol, blocks_limit_smem.symbol),
    "Resident CTAs per SM are limited by the tightest of the thread, register, and shared-memory budgets.",
)
eq_warps_max = eq(
    "kernel.eq.warps_max",
    warps_max.symbol,
    threads_per_sm_max.symbol / warp_size.symbol,
    "Maximum resident warps equal the SM thread budget divided by warp size.",
)
eq_warps_active = eq(
    "kernel.eq.warps_active",
    warps_active.symbol,
    blocks_active_per_sm.symbol * warps_per_block.symbol,
    "Active warps equal resident CTAs per SM times warps per CTA.",
)
eq_occupancy = eq(
    "kernel.eq.occupancy",
    occupancy.symbol,
    warps_active.symbol / warps_max.symbol,
    "Occupancy equals active warps divided by maximum resident warps.",
)
eq_latency_hiding_factor = eq(
    "kernel.eq.latency_hiding_factor",
    latency_hiding_factor.symbol,
    1 / sp.Min(1, occupancy.symbol / occ_full_hide.symbol),
    "If occupancy is below the full-hide point, the latency penalty is amplified by the shortfall. Once occupancy reaches the full-hide point, additional warps do not reduce exposed latency further.",
)
eq_t_latency_bound = eq(
    "kernel.eq.time_latency_bound",
    t_latency_bound.symbol,
    global_load_count.symbol * avg_global_load_latency.symbol / latency_hiding_factor.symbol,
    "Latency-bound time multiplies average global-load latency by the effective count of exposed loads after occupancy-based hiding.",
)
eq_t_body = eq(
    "kernel.eq.time_body",
    t_body.symbol,
    sp.Max(t_compute_bound.symbol, t_hbm_bound.symbol, t_l2_bound.symbol, t_smem_bound.symbol, t_reg_bound.symbol, t_latency_bound.symbol),
    "The kernel body time is the maximum of the compute, bandwidth, and latency lower bounds.",
)
eq_kernel_time = eq(
    "kernel.eq.time",
    t_kernel.symbol,
    t_launch.symbol + t_body.symbol,
    "Full kernel time equals launch overhead plus steady-state kernel body time.",
)
eq_achieved_flops = eq(
    "kernel.eq.achieved_flops",
    achieved_flops.symbol,
    flops_kernel.symbol / t_kernel.symbol,
    "Achieved FLOPs equal kernel FLOPs divided by full kernel time, including launch overhead.",
)


# ---------------------------------------------------------------------------
# Tiled matmul model
# ---------------------------------------------------------------------------

M_mm = var("kernel.matmul.M", "M_mm", "dimensionless", "Matmul M dimension.", scope="kernel")
N_mm = var("kernel.matmul.N", "N_mm", "dimensionless", "Matmul N dimension.", scope="kernel")
K_mm = var("kernel.matmul.K", "K_mm", "dimensionless", "Matmul K dimension.", scope="kernel")
bpv = var(
    "kernel.matmul.bytes_per_val", "B_val_mm", "byte",
    "Bytes per matrix value at the selected precision.",
    scope="kernel",
)
tile_m = var(
    "kernel.matmul.tile_m", "T_M_mm", "dimensionless",
    "CTA tile size along M.",
    scope="kernel",
    integer=True,
)
tile_n = var(
    "kernel.matmul.tile_n", "T_N_mm", "dimensionless",
    "CTA tile size along N.",
    scope="kernel",
    integer=True,
)
tile_k = var(
    "kernel.matmul.tile_k", "T_K_mm", "dimensionless",
    "CTA tile size along K.",
    scope="kernel",
    integer=True,
)
n_tiles_m = var(
    "kernel.matmul.n_tiles_m", "N_tile_M_mm", "tiles",
    "Number of CTA tiles along M.",
    scope="kernel",
    integer=True,
)
n_tiles_n = var(
    "kernel.matmul.n_tiles_n", "N_tile_N_mm", "tiles",
    "Number of CTA tiles along N.",
    scope="kernel",
    integer=True,
)
n_tiles_k = var(
    "kernel.matmul.n_tiles_k", "N_tile_K_mm", "tiles",
    "Number of K-sweep tiles.",
    scope="kernel",
    integer=True,
)
flops_mm = var(
    "kernel.matmul.flops", "F_mm", "FLOP",
    "Matmul FLOPs.",
    scope="kernel",
)
bytes_mm = var(
    "kernel.matmul.bytes", "B_mm", "byte",
    "Naive HBM bytes for the matmul.",
    scope="kernel",
)
bytes_mm_tiled = var(
    "kernel.matmul.bytes_tiled", "B_mm_tiled", "byte",
    "Tiled HBM bytes for the matmul under CTA blocking.",
    scope="kernel",
)
ai_mm = var(
    "kernel.matmul.arith_intensity", "AI_mm", "FLOP/byte",
    "Arithmetic intensity of the naive matmul.",
    scope="kernel",
)
ai_mm_tiled = var(
    "kernel.matmul.arith_intensity_tiled", "AI_mm_tiled", "FLOP/byte",
    "Arithmetic intensity of the tiled matmul.",
    scope="kernel",
)

eq_matmul_flops = eq(
    "kernel.eq.matmul_flops",
    flops_mm.symbol,
    2 * M_mm.symbol * N_mm.symbol * K_mm.symbol,
    "Matmul FLOPs equal 2 times M times N times K.",
)
eq_matmul_bytes = eq(
    "kernel.eq.matmul_bytes",
    bytes_mm.symbol,
    (M_mm.symbol * K_mm.symbol + K_mm.symbol * N_mm.symbol + M_mm.symbol * N_mm.symbol) * bpv.symbol,
    "Naive HBM bytes read A and B once and write C once, with no tile-local reuse.",
)
eq_n_tiles_m = eq(
    "kernel.eq.matmul_n_tiles_m",
    n_tiles_m.symbol,
    sp.ceiling(M_mm.symbol / tile_m.symbol),
    "M tiling count is the ceiling of M over the M tile size.",
)
eq_n_tiles_n = eq(
    "kernel.eq.matmul_n_tiles_n",
    n_tiles_n.symbol,
    sp.ceiling(N_mm.symbol / tile_n.symbol),
    "N tiling count is the ceiling of N over the N tile size.",
)
eq_n_tiles_k = eq(
    "kernel.eq.matmul_n_tiles_k",
    n_tiles_k.symbol,
    sp.ceiling(K_mm.symbol / tile_k.symbol),
    "K tiling count is the ceiling of K over the K tile size.",
)
eq_matmul_bytes_tiled = eq(
    "kernel.eq.matmul_bytes_tiled",
    bytes_mm_tiled.symbol,
    n_tiles_m.symbol * n_tiles_n.symbol * (n_tiles_k.symbol * (tile_m.symbol * tile_k.symbol + tile_k.symbol * tile_n.symbol) + tile_m.symbol * tile_n.symbol) * bpv.symbol,
    "Tiled HBM bytes count one A and one B tile per K sweep for each output CTA tile, plus one write of the output tile.",
)
eq_matmul_intensity = eq(
    "kernel.eq.matmul_intensity",
    ai_mm.symbol,
    flops_mm.symbol / bytes_mm.symbol,
    "Naive matmul arithmetic intensity equals matmul FLOPs divided by naive HBM bytes.",
)
eq_matmul_intensity_tiled = eq(
    "kernel.eq.matmul_intensity_tiled",
    ai_mm_tiled.symbol,
    flops_mm.symbol / bytes_mm_tiled.symbol,
    "Tiled matmul arithmetic intensity equals matmul FLOPs divided by tiled HBM bytes.",
)


# ---------------------------------------------------------------------------
# Attention kernels
# ---------------------------------------------------------------------------

batch_heads = var(
    "kernel.attn.batch_heads", "BH_attn", "heads",
    "Product of batch size and head count for the attention kernel under study.",
    scope="kernel",
)
L_seq = var(
    "kernel.attn.seq_len", "L", "tokens",
    "Sequence length.",
    scope="kernel",
)
d_head = var(
    "kernel.attn.head_dim", "d_h", "dim",
    "Per-head dimension.",
    scope="kernel",
)
causal_factor = var(
    "kernel.attn.causal_factor", "phi_causal_attn", "dimensionless",
    "One for full attention and roughly one half for strictly causal triangular attention.",
    scope="kernel",
)
bpv_attn = var(
    "kernel.attn.bytes_per_val", "B_val_attn", "byte",
    "Bytes per attention activation value.",
    scope="kernel",
)
flops_attn = var(
    "kernel.attn.flops", "F_attn", "FLOP",
    "Attention FLOPs under the selected approximation.",
    scope="kernel",
)
bytes_attn_naive = var(
    "kernel.attn.bytes_naive", "B_attn_n", "byte",
    "Naive attention bytes, including score-matrix materialization.",
    scope="kernel",
)
bytes_attn_flash = var(
    "kernel.attn.bytes_flash", "B_attn_f", "byte",
    "FlashAttention-style bytes without materializing the full score matrix.",
    scope="kernel",
)
ai_attn_flash = var(
    "kernel.attn.arith_intensity_flash", "AI_attn_f", "FLOP/byte",
    "Arithmetic intensity of FlashAttention-style attention.",
    scope="kernel",
)
flash_io_reduction = var(
    "kernel.attn.flash_io_reduction", "rho_flash_io", "dimensionless",
    "Naive bytes divided by FlashAttention bytes, measuring the IO reduction from online softmax and tiling.",
    scope="kernel",
)

eq_attn_flops = eq(
    "kernel.eq.attn_flops",
    flops_attn.symbol,
    4 * batch_heads.symbol * causal_factor.symbol * L_seq.symbol**2 * d_head.symbol,
    "Attention FLOPs scale with batch-head count, a causal-structure factor, sequence length squared, and head dimension.",
)
eq_attn_bytes_naive = eq(
    "kernel.eq.attn_bytes_naive",
    bytes_attn_naive.symbol,
    batch_heads.symbol * (4 * L_seq.symbol * d_head.symbol + causal_factor.symbol * L_seq.symbol**2) * bpv_attn.symbol,
    "Naive attention bytes include Q, K, V, output, and the materialized score matrix.",
)
eq_attn_bytes_flash = eq(
    "kernel.eq.attn_bytes_flash",
    bytes_attn_flash.symbol,
    4 * batch_heads.symbol * L_seq.symbol * d_head.symbol * bpv_attn.symbol,
    "FlashAttention-style bytes scale linearly in sequence length and head dimension because the score matrix is never fully materialized.",
)
eq_attn_intensity_flash = eq(
    "kernel.eq.attn_intensity_flash",
    ai_attn_flash.symbol,
    flops_attn.symbol / bytes_attn_flash.symbol,
    "FlashAttention arithmetic intensity equals attention FLOPs divided by FlashAttention bytes.",
)
eq_flash_io_reduction = eq(
    "kernel.eq.flash_io_reduction",
    flash_io_reduction.symbol,
    bytes_attn_naive.symbol / bytes_attn_flash.symbol,
    "The FlashAttention IO reduction factor is naive bytes divided by FlashAttention bytes.",
)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

for v in [
    flops_kernel,
    bytes_kernel,
    arith_intensity,
    bytes_l2,
    bytes_smem,
    bytes_reg,
    ai_l2,
    ai_smem,
    ai_reg,
    compute_efficiency,
    compute_ceiling,
    hbm_ceiling,
    l2_ceiling,
    smem_ceiling,
    reg_ceiling,
    roofline_flops,
    achieved_flops,
    t_compute_bound,
    t_hbm_bound,
    t_l2_bound,
    t_smem_bound,
    t_reg_bound,
    global_load_count,
    occ_full_hide,
    latency_hiding_factor,
    t_latency_bound,
    t_body,
    t_kernel,
    t_launch,
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
    M_mm,
    N_mm,
    K_mm,
    bpv,
    tile_m,
    tile_n,
    tile_k,
    n_tiles_m,
    n_tiles_n,
    n_tiles_k,
    flops_mm,
    bytes_mm,
    bytes_mm_tiled,
    ai_mm,
    ai_mm_tiled,
    batch_heads,
    L_seq,
    d_head,
    causal_factor,
    bpv_attn,
    flops_attn,
    bytes_attn_naive,
    bytes_attn_flash,
    ai_attn_flash,
    flash_io_reduction,
]:
    sys_kern.add(v)

for e in [
    eq_arith_intensity,
    eq_ai_l2,
    eq_ai_smem,
    eq_ai_reg,
    eq_compute_ceiling,
    eq_hbm_ceiling,
    eq_l2_ceiling,
    eq_smem_ceiling,
    eq_reg_ceiling,
    eq_roofline,
    eq_t_compute_bound,
    eq_t_hbm_bound,
    eq_t_l2_bound,
    eq_t_smem_bound,
    eq_t_reg_bound,
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
    eq_matmul_flops,
    eq_matmul_bytes,
    eq_n_tiles_m,
    eq_n_tiles_n,
    eq_n_tiles_k,
    eq_matmul_bytes_tiled,
    eq_matmul_intensity,
    eq_matmul_intensity_tiled,
    eq_attn_flops,
    eq_attn_bytes_naive,
    eq_attn_bytes_flash,
    eq_attn_intensity_flash,
    eq_flash_io_reduction,
]:
    sys_kern.add(e)
