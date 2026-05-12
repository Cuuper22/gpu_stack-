"""
scopes/kernel_roofline.py
=========================

Kernel bytes and arithmetic intensities at HBM, L2, shared memory, and
register levels. Generalized roofline as the minimum of compute and
per-level bandwidth ceilings. Lower bounds on time from compute, HBM,
L2, SMEM, and register bandwidth. Foundation helper for the kernel
scope.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import FLOP, FLOPS, SECOND, byte
from .gpu import (
    hbm_bw_gpu_effective,
    peak_flops_gpu_power_limited,
    reg_bw_gpu,
    smem_bw_gpu,
)
from .memory_subsystem import (
    l2_bw,
)


DIMENSIONLESS = sp.Integer(1)
ARITH_INTENSITY_UNIT = FLOP / byte

KERNEL_ROOFLINE_REF = Reference(
    "Williams, Waterman, and Patterson, Roofline: An Insightful Visual "
    "Performance Model for Multicore Architectures, CACM 2009.",
    kind="paper",
    year=2009,
)
KERNEL_MEMORY_ROOFLINE_REF = Reference(
    "GPU memory-hierarchy roofline model: separate HBM, L2, shared-memory, "
    "and register-file bandwidth ceilings bound kernel throughput.",
    kind="model",
)
KERNEL_TIME_BOUND_REF = Reference(
    "Kernel runtime lower-bound model: compute work, memory traffic, and "
    "launch latency produce independent time ceilings.",
    kind="model",
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

for _v in (flops_kernel,):
    _v.sp_units = FLOP
    _v.references.append(KERNEL_ROOFLINE_REF)

for _v in (bytes_kernel, bytes_l2, bytes_smem, bytes_reg):
    _v.sp_units = byte
    _v.references.append(KERNEL_MEMORY_ROOFLINE_REF)

for _v in (arith_intensity, ai_l2, ai_smem, ai_reg):
    _v.sp_units = ARITH_INTENSITY_UNIT
    _v.references.append(KERNEL_ROOFLINE_REF)

for _v in (compute_efficiency, global_load_count):
    _v.sp_units = DIMENSIONLESS
    _v.references.append(KERNEL_TIME_BOUND_REF)

for _v in (compute_ceiling, hbm_ceiling, l2_ceiling, smem_ceiling, reg_ceiling, roofline_flops):
    _v.sp_units = FLOPS
    _v.references.append(KERNEL_ROOFLINE_REF)

for _v in (t_compute_bound, t_hbm_bound, t_l2_bound, t_smem_bound, t_reg_bound):
    _v.sp_units = SECOND
    _v.references.append(KERNEL_TIME_BOUND_REF)

eq_arith_intensity = eq(
    "kernel.eq.arith_intensity",
    arith_intensity.symbol,
    flops_kernel.symbol / bytes_kernel.symbol,
    "HBM arithmetic intensity equals kernel FLOPs divided by HBM bytes.",
    references=[KERNEL_ROOFLINE_REF],
    check_units=True,
)
eq_ai_l2 = eq(
    "kernel.eq.l2_arith_intensity",
    ai_l2.symbol,
    flops_kernel.symbol / bytes_l2.symbol,
    "L2 arithmetic intensity equals kernel FLOPs divided by L2 bytes.",
    references=[KERNEL_MEMORY_ROOFLINE_REF],
    check_units=True,
)
eq_ai_smem = eq(
    "kernel.eq.smem_arith_intensity",
    ai_smem.symbol,
    flops_kernel.symbol / bytes_smem.symbol,
    "SMEM arithmetic intensity equals kernel FLOPs divided by SMEM bytes.",
    references=[KERNEL_MEMORY_ROOFLINE_REF],
    check_units=True,
)
eq_ai_reg = eq(
    "kernel.eq.reg_arith_intensity",
    ai_reg.symbol,
    flops_kernel.symbol / bytes_reg.symbol,
    "Register arithmetic intensity equals kernel FLOPs divided by register bytes.",
    references=[KERNEL_MEMORY_ROOFLINE_REF],
    check_units=True,
)
eq_compute_ceiling = eq(
    "kernel.eq.compute_ceiling",
    compute_ceiling.symbol,
    compute_efficiency.symbol * peak_flops_gpu_power_limited.symbol,
    "Compute ceiling equals the GPU's power-limited effective peak scaled by kernel-specific compute efficiency.",
    references=[KERNEL_ROOFLINE_REF],
    check_units=True,
)
eq_hbm_ceiling = eq(
    "kernel.eq.hbm_ceiling",
    hbm_ceiling.symbol,
    hbm_bw_gpu_effective.symbol * arith_intensity.symbol,
    "HBM roofline ceiling equals effective HBM bandwidth times HBM arithmetic intensity.",
    references=[KERNEL_ROOFLINE_REF],
    check_units=True,
)
eq_l2_ceiling = eq(
    "kernel.eq.l2_ceiling",
    l2_ceiling.symbol,
    l2_bw.symbol * ai_l2.symbol,
    "L2 roofline ceiling equals L2 bandwidth times L2 arithmetic intensity.",
    references=[KERNEL_MEMORY_ROOFLINE_REF],
    check_units=True,
)
eq_smem_ceiling = eq(
    "kernel.eq.smem_ceiling",
    smem_ceiling.symbol,
    smem_bw_gpu.symbol * ai_smem.symbol,
    "SMEM roofline ceiling equals aggregate SMEM bandwidth times SMEM arithmetic intensity.",
    references=[KERNEL_MEMORY_ROOFLINE_REF],
    check_units=True,
)
eq_reg_ceiling = eq(
    "kernel.eq.reg_ceiling",
    reg_ceiling.symbol,
    reg_bw_gpu.symbol * ai_reg.symbol,
    "Register-file roofline ceiling equals aggregate register bandwidth times register arithmetic intensity.",
    references=[KERNEL_MEMORY_ROOFLINE_REF],
    check_units=True,
)
eq_roofline = eq(
    "kernel.eq.roofline",
    roofline_flops.symbol,
    sp.Min(compute_ceiling.symbol, hbm_ceiling.symbol, l2_ceiling.symbol, smem_ceiling.symbol, reg_ceiling.symbol),
    "The generalized roofline ceiling is the minimum of the compute and memory-level ceilings.",
    references=[
        KERNEL_ROOFLINE_REF,
    ],
    check_units=True,
)
eq_t_compute_bound = eq(
    "kernel.eq.time_compute_bound",
    t_compute_bound.symbol,
    flops_kernel.symbol / compute_ceiling.symbol,
    "Compute-bound time lower bound equals FLOPs divided by the compute ceiling.",
    references=[KERNEL_TIME_BOUND_REF],
    check_units=True,
)
eq_t_hbm_bound = eq(
    "kernel.eq.time_hbm_bound",
    t_hbm_bound.symbol,
    bytes_kernel.symbol / hbm_bw_gpu_effective.symbol,
    "HBM-bound time lower bound equals HBM bytes divided by effective HBM bandwidth.",
    references=[KERNEL_TIME_BOUND_REF],
    check_units=True,
)
eq_t_l2_bound = eq(
    "kernel.eq.time_l2_bound",
    t_l2_bound.symbol,
    bytes_l2.symbol / l2_bw.symbol,
    "L2-bound time lower bound equals L2 bytes divided by L2 bandwidth.",
    references=[KERNEL_TIME_BOUND_REF],
    check_units=True,
)
eq_t_smem_bound = eq(
    "kernel.eq.time_smem_bound",
    t_smem_bound.symbol,
    bytes_smem.symbol / smem_bw_gpu.symbol,
    "SMEM-bound time lower bound equals SMEM bytes divided by aggregate SMEM bandwidth.",
    references=[KERNEL_TIME_BOUND_REF],
    check_units=True,
)
eq_t_reg_bound = eq(
    "kernel.eq.time_reg_bound",
    t_reg_bound.symbol,
    bytes_reg.symbol / reg_bw_gpu.symbol,
    "Register-bound time lower bound equals register bytes divided by aggregate register bandwidth.",
    references=[KERNEL_TIME_BOUND_REF],
    check_units=True,
)


KERNEL_ROOFLINE_VARIABLES = (
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
    t_compute_bound,
    t_hbm_bound,
    t_l2_bound,
    t_smem_bound,
    t_reg_bound,
    global_load_count,
)

KERNEL_ROOFLINE_EQUATIONS = (
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
)


__all__ = [
    "flops_kernel",
    "bytes_kernel",
    "arith_intensity",
    "bytes_l2",
    "bytes_smem",
    "bytes_reg",
    "ai_l2",
    "ai_smem",
    "ai_reg",
    "compute_efficiency",
    "compute_ceiling",
    "hbm_ceiling",
    "l2_ceiling",
    "smem_ceiling",
    "reg_ceiling",
    "roofline_flops",
    "t_compute_bound",
    "t_hbm_bound",
    "t_l2_bound",
    "t_smem_bound",
    "t_reg_bound",
    "global_load_count",
    "eq_arith_intensity",
    "eq_ai_l2",
    "eq_ai_smem",
    "eq_ai_reg",
    "eq_compute_ceiling",
    "eq_hbm_ceiling",
    "eq_l2_ceiling",
    "eq_smem_ceiling",
    "eq_reg_ceiling",
    "eq_roofline",
    "eq_t_compute_bound",
    "eq_t_hbm_bound",
    "eq_t_l2_bound",
    "eq_t_smem_bound",
    "eq_t_reg_bound",
    "KERNEL_ROOFLINE_VARIABLES",
    "KERNEL_ROOFLINE_EQUATIONS",
]
