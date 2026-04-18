"""
scopes/gpu_memory.py
====================

Aggregate on-chip and HBM memory capacity and bandwidth at GPU-die scope.
Register files, shared memory, TMEM, and L2 are summed across all SMs,
and HBM capacity and bandwidth are exposed as package-level views.
"""

from ..core import eq, var
from .memory_subsystem import (
    hbm_bw_effective,
    hbm_effective_capacity,
    hbm_pins_per_stack,
    hbm_stack_count,
    l2_bw,
    l2_bytes,
    reg_bw_effective,
    reg_file_bytes_per_sm,
    smem_bw_per_sm,
    smem_bytes_per_sm,
    tmem_bw_per_sm,
    tmem_bytes_per_sm,
)
from .gpu_compute import n_sms


# ---------------------------------------------------------------------------
# On-chip memory and bandwidth aggregation
# ---------------------------------------------------------------------------

reg_bytes_gpu = var(
    "gpu.reg.bytes", "B_reg_GPU", "byte",
    "Total register-file capacity aggregated across all SMs.",
    scope="gpu",
)
smem_bytes_gpu = var(
    "gpu.smem.bytes", "B_smem_GPU", "byte",
    "Total software-managed shared-memory capacity aggregated across all SMs.",
    scope="gpu",
)
tmem_bytes_gpu = var(
    "gpu.tmem.bytes", "B_tmem_GPU", "byte",
    "Total TMEM capacity aggregated across all SMs.",
    scope="gpu",
)
l2_bytes_gpu = var(
    "gpu.l2.bytes", "B_L2_GPU", "byte",
    "L2 capacity exposed as a GPU-level variable for higher scopes.",
    scope="gpu",
)
onchip_sram_bytes_gpu = var(
    "gpu.onchip_sram.bytes", "B_onchip_GPU", "byte",
    "Aggregate on-chip memory capacity from register files, SMEM, TMEM, and L2.",
    scope="gpu",
)
reg_bw_gpu = var(
    "gpu.reg.bw", "BW_reg_GPU", "byte/s",
    "Aggregate effective register-file bandwidth across all SMs.",
    scope="gpu",
)
smem_bw_gpu = var(
    "gpu.smem.bw", "BW_smem_GPU", "byte/s",
    "Aggregate shared-memory bandwidth across all SMs.",
    scope="gpu",
)
tmem_bw_gpu = var(
    "gpu.tmem.bw", "BW_tmem_GPU", "byte/s",
    "Aggregate TMEM bandwidth across all SMs.",
    scope="gpu",
)
l2_bw_gpu = var(
    "gpu.l2.bw", "BW_L2_GPU", "byte/s",
    "L2 bandwidth exposed as a GPU-level variable for higher scopes.",
    scope="gpu",
)

eq_reg_bytes_gpu = eq(
    "gpu.eq.reg_bytes",
    reg_bytes_gpu.symbol,
    n_sms.symbol * reg_file_bytes_per_sm.symbol,
    "Total register-file capacity equals per-SM register bytes times SM count.",
)
eq_smem_bytes_gpu = eq(
    "gpu.eq.smem_bytes",
    smem_bytes_gpu.symbol,
    n_sms.symbol * smem_bytes_per_sm.symbol,
    "Total SMEM capacity equals per-SM SMEM bytes times SM count.",
)
eq_tmem_bytes_gpu = eq(
    "gpu.eq.tmem_bytes",
    tmem_bytes_gpu.symbol,
    n_sms.symbol * tmem_bytes_per_sm.symbol,
    "Total TMEM capacity equals per-SM TMEM bytes times SM count.",
)
eq_l2_bytes_gpu = eq(
    "gpu.eq.l2_bytes",
    l2_bytes_gpu.symbol,
    l2_bytes.symbol,
    "GPU-level L2 capacity is the underlying package L2 capacity.",
)
eq_onchip_sram_bytes_gpu = eq(
    "gpu.eq.onchip_sram_bytes",
    onchip_sram_bytes_gpu.symbol,
    reg_bytes_gpu.symbol + smem_bytes_gpu.symbol + tmem_bytes_gpu.symbol + l2_bytes_gpu.symbol,
    "On-chip memory adds register files, SMEM, TMEM, and L2.",
)
eq_reg_bw_gpu = eq(
    "gpu.eq.reg_bw",
    reg_bw_gpu.symbol,
    n_sms.symbol * reg_bw_effective.symbol,
    "Aggregate register bandwidth equals effective per-SM register bandwidth times SM count.",
)
eq_smem_bw_gpu = eq(
    "gpu.eq.smem_bw",
    smem_bw_gpu.symbol,
    n_sms.symbol * smem_bw_per_sm.symbol,
    "Aggregate SMEM bandwidth equals per-SM SMEM bandwidth times SM count.",
)
eq_tmem_bw_gpu = eq(
    "gpu.eq.tmem_bw",
    tmem_bw_gpu.symbol,
    n_sms.symbol * tmem_bw_per_sm.symbol,
    "Aggregate TMEM bandwidth equals per-SM TMEM bandwidth times SM count.",
)
eq_l2_bw_gpu = eq(
    "gpu.eq.l2_bw",
    l2_bw_gpu.symbol,
    l2_bw.symbol,
    "GPU-level L2 bandwidth is the underlying package L2 bandwidth.",
)


# ---------------------------------------------------------------------------
# HBM package view
# ---------------------------------------------------------------------------

hbm_bw_gpu_effective = var(
    "gpu.hbm.bw_effective", "BW_HBM_GPU_eff", "byte/s",
    "Effective HBM bandwidth for the GPU package after refresh overhead.",
    scope="gpu",
)
hbm_capacity_gpu_effective = var(
    "gpu.hbm.capacity_effective", "B_HBM_GPU_eff", "byte",
    "Effective HBM capacity after ECC and compression effects.",
    scope="gpu",
)
hbm_pins_total = var(
    "gpu.hbm.pins_total", "N_pins_HBM_GPU", "pins",
    "Total HBM data pins across all attached HBM stacks.",
    scope="gpu",
    integer=True,
)
hbm_bw_per_pin = var(
    "gpu.hbm.bw_per_pin", "BW_pin_HBM_GPU", "byte/s/pin",
    "Average effective HBM bandwidth per data pin at the package edge.",
    scope="gpu",
)
hbm_bw_per_stack_avg = var(
    "gpu.hbm.bw_per_stack_avg", "BW_stack_HBM_GPU", "byte/s",
    "Average effective bandwidth carried by one HBM stack.",
    scope="gpu",
)
hbm_capacity_per_stack_avg = var(
    "gpu.hbm.capacity_per_stack_avg", "B_stack_HBM_GPU", "byte",
    "Average effective capacity provided by one HBM stack.",
    scope="gpu",
)

eq_hbm_bw_gpu_effective = eq(
    "gpu.eq.hbm_bw_effective",
    hbm_bw_gpu_effective.symbol,
    hbm_bw_effective.symbol,
    "GPU-level effective HBM bandwidth aliases the lower-scope HBM effective bandwidth.",
)
eq_hbm_capacity_gpu_effective = eq(
    "gpu.eq.hbm_capacity_effective",
    hbm_capacity_gpu_effective.symbol,
    hbm_effective_capacity.symbol,
    "GPU-level effective HBM capacity aliases the lower-scope effective HBM capacity.",
)
eq_hbm_pins_total = eq(
    "gpu.eq.hbm_pins_total",
    hbm_pins_total.symbol,
    hbm_stack_count.symbol * hbm_pins_per_stack.symbol,
    "Total HBM pins equal stack count times pins per stack.",
)
eq_hbm_bw_per_pin = eq(
    "gpu.eq.hbm_bw_per_pin",
    hbm_bw_per_pin.symbol,
    hbm_bw_gpu_effective.symbol / hbm_pins_total.symbol,
    "Average effective HBM bandwidth per pin equals effective package bandwidth divided by total HBM pins.",
)
eq_hbm_bw_per_stack_avg = eq(
    "gpu.eq.hbm_bw_per_stack_avg",
    hbm_bw_per_stack_avg.symbol,
    hbm_bw_gpu_effective.symbol / hbm_stack_count.symbol,
    "Average effective HBM bandwidth per stack equals package bandwidth divided by stack count.",
)
eq_hbm_capacity_per_stack_avg = eq(
    "gpu.eq.hbm_capacity_per_stack_avg",
    hbm_capacity_per_stack_avg.symbol,
    hbm_capacity_gpu_effective.symbol / hbm_stack_count.symbol,
    "Average effective HBM capacity per stack equals package effective capacity divided by stack count.",
)


GPU_MEMORY_VARIABLES = (
    reg_bytes_gpu,
    smem_bytes_gpu,
    tmem_bytes_gpu,
    l2_bytes_gpu,
    onchip_sram_bytes_gpu,
    reg_bw_gpu,
    smem_bw_gpu,
    tmem_bw_gpu,
    l2_bw_gpu,
    hbm_bw_gpu_effective,
    hbm_capacity_gpu_effective,
    hbm_pins_total,
    hbm_bw_per_pin,
    hbm_bw_per_stack_avg,
    hbm_capacity_per_stack_avg,
)

GPU_MEMORY_EQUATIONS = (
    eq_reg_bytes_gpu,
    eq_smem_bytes_gpu,
    eq_tmem_bytes_gpu,
    eq_l2_bytes_gpu,
    eq_onchip_sram_bytes_gpu,
    eq_reg_bw_gpu,
    eq_smem_bw_gpu,
    eq_tmem_bw_gpu,
    eq_l2_bw_gpu,
    eq_hbm_bw_gpu_effective,
    eq_hbm_capacity_gpu_effective,
    eq_hbm_pins_total,
    eq_hbm_bw_per_pin,
    eq_hbm_bw_per_stack_avg,
    eq_hbm_capacity_per_stack_avg,
)


__all__ = [
    "reg_bytes_gpu",
    "smem_bytes_gpu",
    "tmem_bytes_gpu",
    "l2_bytes_gpu",
    "onchip_sram_bytes_gpu",
    "reg_bw_gpu",
    "smem_bw_gpu",
    "tmem_bw_gpu",
    "l2_bw_gpu",
    "hbm_bw_gpu_effective",
    "hbm_capacity_gpu_effective",
    "hbm_pins_total",
    "hbm_bw_per_pin",
    "hbm_bw_per_stack_avg",
    "hbm_capacity_per_stack_avg",
    "eq_reg_bytes_gpu",
    "eq_smem_bytes_gpu",
    "eq_tmem_bytes_gpu",
    "eq_l2_bytes_gpu",
    "eq_onchip_sram_bytes_gpu",
    "eq_reg_bw_gpu",
    "eq_smem_bw_gpu",
    "eq_tmem_bw_gpu",
    "eq_l2_bw_gpu",
    "eq_hbm_bw_gpu_effective",
    "eq_hbm_capacity_gpu_effective",
    "eq_hbm_pins_total",
    "eq_hbm_bw_per_pin",
    "eq_hbm_bw_per_stack_avg",
    "eq_hbm_capacity_per_stack_avg",
    "GPU_MEMORY_VARIABLES",
    "GPU_MEMORY_EQUATIONS",
]
