"""
scopes/kernel_attention.py
==========================

Attention-specific IO and arithmetic-intensity formulas. Contrasts
naive attention, which materializes the score matrix, with
FlashAttention-style tiled online softmax, which does not.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import FLOP, byte


# ---------------------------------------------------------------------------
# Attention kernels
# ---------------------------------------------------------------------------

DIMENSIONLESS = sp.Integer(1)
ARITH_INTENSITY_UNIT = FLOP / byte

KERNEL_ATTENTION_REF = Reference(
    "Vaswani et al., Attention Is All You Need, 2017.",
    kind="paper",
    year=2017,
)
KERNEL_FLASH_ATTENTION_REF = Reference(
    "Dao et al., FlashAttention: Fast and Memory-Efficient Exact Attention "
    "with IO-Awareness, 2022.",
    kind="paper",
    year=2022,
)

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

for _v in (batch_heads, L_seq, d_head, causal_factor, flash_io_reduction):
    _v.sp_units = DIMENSIONLESS
    _v.references.append(KERNEL_ATTENTION_REF)

bpv_attn.sp_units = byte
bpv_attn.references.append(KERNEL_ATTENTION_REF)

flops_attn.sp_units = FLOP
flops_attn.references.append(KERNEL_ATTENTION_REF)

for _v in (bytes_attn_naive, bytes_attn_flash):
    _v.sp_units = byte
    _v.references.append(KERNEL_FLASH_ATTENTION_REF)

ai_attn_flash.sp_units = ARITH_INTENSITY_UNIT
ai_attn_flash.references.append(KERNEL_FLASH_ATTENTION_REF)

eq_attn_flops = eq(
    "kernel.eq.attn_flops",
    flops_attn.symbol,
    4 * batch_heads.symbol * causal_factor.symbol * L_seq.symbol**2 * d_head.symbol,
    "Attention FLOPs scale with batch-head count, a causal-structure factor, sequence length squared, and head dimension.",
    references=[KERNEL_ATTENTION_REF],
)
eq_attn_bytes_naive = eq(
    "kernel.eq.attn_bytes_naive",
    bytes_attn_naive.symbol,
    batch_heads.symbol * (4 * L_seq.symbol * d_head.symbol + causal_factor.symbol * L_seq.symbol**2) * bpv_attn.symbol,
    "Naive attention bytes include Q, K, V, output, and the materialized score matrix.",
    references=[KERNEL_ATTENTION_REF],
    check_units=True,
)
eq_attn_bytes_flash = eq(
    "kernel.eq.attn_bytes_flash",
    bytes_attn_flash.symbol,
    4 * batch_heads.symbol * L_seq.symbol * d_head.symbol * bpv_attn.symbol,
    "FlashAttention-style bytes scale linearly in sequence length and head dimension because the score matrix is never fully materialized.",
    references=[KERNEL_FLASH_ATTENTION_REF],
    check_units=True,
)
eq_attn_intensity_flash = eq(
    "kernel.eq.attn_intensity_flash",
    ai_attn_flash.symbol,
    flops_attn.symbol / bytes_attn_flash.symbol,
    "FlashAttention arithmetic intensity equals attention FLOPs divided by FlashAttention bytes.",
    references=[KERNEL_FLASH_ATTENTION_REF],
    check_units=True,
)
eq_flash_io_reduction = eq(
    "kernel.eq.flash_io_reduction",
    flash_io_reduction.symbol,
    bytes_attn_naive.symbol / bytes_attn_flash.symbol,
    "The FlashAttention IO reduction factor is naive bytes divided by FlashAttention bytes.",
    references=[KERNEL_FLASH_ATTENTION_REF],
    check_units=True,
)


KERNEL_ATTENTION_VARIABLES = (
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
)

KERNEL_ATTENTION_EQUATIONS = (
    eq_attn_flops,
    eq_attn_bytes_naive,
    eq_attn_bytes_flash,
    eq_attn_intensity_flash,
    eq_flash_io_reduction,
)


__all__ = [
    "batch_heads",
    "L_seq",
    "d_head",
    "causal_factor",
    "bpv_attn",
    "flops_attn",
    "bytes_attn_naive",
    "bytes_attn_flash",
    "ai_attn_flash",
    "flash_io_reduction",
    "eq_attn_flops",
    "eq_attn_bytes_naive",
    "eq_attn_bytes_flash",
    "eq_attn_intensity_flash",
    "eq_flash_io_reduction",
    "KERNEL_ATTENTION_VARIABLES",
    "KERNEL_ATTENTION_EQUATIONS",
]
