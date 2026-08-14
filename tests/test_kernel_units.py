"""Checks unit and reference metadata for the kernel scope.

The kernel scope carries the roofline model (FLOPs, bytes, and arithmetic
intensity in FLOP per byte), occupancy, tiled GEMM, and flash attention.
These tests require all 66-plus kernel variables to declare units and
references, pin the exact set of six equations exempt from dimensional
checking (block-limit and tile-count relations, which are pure counts),
and spot-check representative variables across all four sub-areas.
"""

import sympy as sp

from gpu_stack.core.units import FLOP, FLOPS, SECOND, byte
from gpu_stack.scopes import kernel


DIMENSIONLESS = sp.Integer(1)

UNCHECKED_KERNEL_EQUATIONS = {
    "kernel.eq.blocks_limit_threads",
    "kernel.eq.blocks_limit_regs",
    "kernel.eq.blocks_limit_smem",
    "kernel.eq.matmul_n_tiles_m",
    "kernel.eq.matmul_n_tiles_n",
    "kernel.eq.matmul_n_tiles_k",
}


def test_kernel_variables_have_units_and_references():
    assert len(kernel.KERNEL_VARIABLES) >= 66
    assert [v.name for v in kernel.KERNEL_VARIABLES if v.sp_units is None] == []
    assert [v.name for v in kernel.KERNEL_VARIABLES if not v.references] == []


def test_kernel_equations_have_references_and_curated_unit_checks():
    checked = {
        eq.name
        for eq in kernel.KERNEL_EQUATIONS
        if getattr(eq, "_check_units_flag", False)
    }
    unchecked = {eq.name for eq in kernel.KERNEL_EQUATIONS} - checked

    assert len(kernel.KERNEL_EQUATIONS) >= 42
    assert [eq.name for eq in kernel.KERNEL_EQUATIONS if not eq.references] == []
    assert len(checked) >= 34
    assert unchecked == UNCHECKED_KERNEL_EQUATIONS


def test_kernel_representative_units_cover_roofline_occupancy_gemm_and_attention():
    assert kernel.flops_kernel.sp_units == FLOP
    assert kernel.bytes_kernel.sp_units == byte
    assert kernel.arith_intensity.sp_units == FLOP / byte
    assert kernel.compute_ceiling.sp_units == FLOPS
    assert kernel.roofline_flops.sp_units == FLOPS
    assert kernel.t_kernel.sp_units == SECOND
    assert kernel.global_load_count.sp_units == DIMENSIONLESS

    assert kernel.threads_per_block.sp_units == DIMENSIONLESS
    assert kernel.reg_bytes_per_block.sp_units == byte
    assert kernel.occupancy.sp_units == DIMENSIONLESS
    assert kernel.latency_hiding_factor.sp_units == DIMENSIONLESS
    assert kernel.achieved_flops.sp_units == FLOPS

    assert kernel.M_mm.sp_units == DIMENSIONLESS
    assert kernel.bpv.sp_units == byte
    assert kernel.flops_mm.sp_units == FLOP
    assert kernel.bytes_mm_tiled.sp_units == byte
    assert kernel.ai_mm_tiled.sp_units == FLOP / byte

    assert kernel.batch_heads.sp_units == DIMENSIONLESS
    assert kernel.bpv_attn.sp_units == byte
    assert kernel.flops_attn.sp_units == FLOP
    assert kernel.bytes_attn_flash.sp_units == byte
    assert kernel.ai_attn_flash.sp_units == FLOP / byte
