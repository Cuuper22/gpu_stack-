"""
scopes/kernel_gemm.py
=====================

Tiled GEMM tile-count, traffic, and arithmetic-intensity formulas.
Covers naive and CTA-tiled HBM byte counts and the corresponding
arithmetic intensities.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import FLOP, byte


# ---------------------------------------------------------------------------
# Tiled matmul model
# ---------------------------------------------------------------------------

DIMENSIONLESS = sp.Integer(1)
ARITH_INTENSITY_UNIT = FLOP / byte

KERNEL_GEMM_REF = Reference(
    "GEMM work and traffic model: dense matrix multiplication performs "
    "2*M*N*K scalar FLOPs and reuses A/B tiles through CTA blocking.",
    kind="model",
)
KERNEL_GEMM_TILING_REF = Reference(
    "GPU tiled-GEMM model: CTA tile counts and K-sweep tiles determine HBM "
    "traffic for blocked matrix multiplication.",
    kind="model",
)

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

for _v in (M_mm, N_mm, K_mm, tile_m, tile_n, tile_k, n_tiles_m, n_tiles_n, n_tiles_k):
    _v.sp_units = DIMENSIONLESS
    _v.references.append(KERNEL_GEMM_TILING_REF)

bpv.sp_units = byte
bpv.references.append(KERNEL_GEMM_REF)

flops_mm.sp_units = FLOP
flops_mm.references.append(KERNEL_GEMM_REF)

for _v in (bytes_mm, bytes_mm_tiled):
    _v.sp_units = byte
    _v.references.append(KERNEL_GEMM_TILING_REF)

for _v in (ai_mm, ai_mm_tiled):
    _v.sp_units = ARITH_INTENSITY_UNIT
    _v.references.append(KERNEL_GEMM_REF)

eq_matmul_flops = eq(
    "kernel.eq.matmul_flops",
    flops_mm.symbol,
    2 * M_mm.symbol * N_mm.symbol * K_mm.symbol,
    "Matmul FLOPs equal 2 times M times N times K.",
    references=[KERNEL_GEMM_REF],
    check_units=True,
)
eq_matmul_bytes = eq(
    "kernel.eq.matmul_bytes",
    bytes_mm.symbol,
    (M_mm.symbol * K_mm.symbol + K_mm.symbol * N_mm.symbol + M_mm.symbol * N_mm.symbol) * bpv.symbol,
    "Naive HBM bytes read A and B once and write C once, with no tile-local reuse.",
    references=[KERNEL_GEMM_REF],
    check_units=True,
)
eq_n_tiles_m = eq(
    "kernel.eq.matmul_n_tiles_m",
    n_tiles_m.symbol,
    sp.ceiling(M_mm.symbol / tile_m.symbol),
    "M tiling count is the ceiling of M over the M tile size.",
    references=[KERNEL_GEMM_TILING_REF],
)
eq_n_tiles_n = eq(
    "kernel.eq.matmul_n_tiles_n",
    n_tiles_n.symbol,
    sp.ceiling(N_mm.symbol / tile_n.symbol),
    "N tiling count is the ceiling of N over the N tile size.",
    references=[KERNEL_GEMM_TILING_REF],
)
eq_n_tiles_k = eq(
    "kernel.eq.matmul_n_tiles_k",
    n_tiles_k.symbol,
    sp.ceiling(K_mm.symbol / tile_k.symbol),
    "K tiling count is the ceiling of K over the K tile size.",
    references=[KERNEL_GEMM_TILING_REF],
)
eq_matmul_bytes_tiled = eq(
    "kernel.eq.matmul_bytes_tiled",
    bytes_mm_tiled.symbol,
    n_tiles_m.symbol * n_tiles_n.symbol * (n_tiles_k.symbol * (tile_m.symbol * tile_k.symbol + tile_k.symbol * tile_n.symbol) + tile_m.symbol * tile_n.symbol) * bpv.symbol,
    "Tiled HBM bytes count one A and one B tile per K sweep for each output CTA tile, plus one write of the output tile.",
    references=[KERNEL_GEMM_TILING_REF],
    check_units=True,
)
eq_matmul_intensity = eq(
    "kernel.eq.matmul_intensity",
    ai_mm.symbol,
    flops_mm.symbol / bytes_mm.symbol,
    "Naive matmul arithmetic intensity equals matmul FLOPs divided by naive HBM bytes.",
    references=[KERNEL_GEMM_REF],
    check_units=True,
)
eq_matmul_intensity_tiled = eq(
    "kernel.eq.matmul_intensity_tiled",
    ai_mm_tiled.symbol,
    flops_mm.symbol / bytes_mm_tiled.symbol,
    "Tiled matmul arithmetic intensity equals matmul FLOPs divided by tiled HBM bytes.",
    references=[KERNEL_GEMM_TILING_REF],
    check_units=True,
)


KERNEL_GEMM_VARIABLES = (
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
)

KERNEL_GEMM_EQUATIONS = (
    eq_matmul_flops,
    eq_matmul_bytes,
    eq_n_tiles_m,
    eq_n_tiles_n,
    eq_n_tiles_k,
    eq_matmul_bytes_tiled,
    eq_matmul_intensity,
    eq_matmul_intensity_tiled,
)


__all__ = [
    "M_mm",
    "N_mm",
    "K_mm",
    "bpv",
    "tile_m",
    "tile_n",
    "tile_k",
    "n_tiles_m",
    "n_tiles_n",
    "n_tiles_k",
    "flops_mm",
    "bytes_mm",
    "bytes_mm_tiled",
    "ai_mm",
    "ai_mm_tiled",
    "eq_matmul_flops",
    "eq_matmul_bytes",
    "eq_n_tiles_m",
    "eq_n_tiles_n",
    "eq_n_tiles_k",
    "eq_matmul_bytes_tiled",
    "eq_matmul_intensity",
    "eq_matmul_intensity_tiled",
    "KERNEL_GEMM_VARIABLES",
    "KERNEL_GEMM_EQUATIONS",
]
