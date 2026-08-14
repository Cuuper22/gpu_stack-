"""
scopes/precision_lowbit_formats.py
==================================

Storage cost and structure of the low-bit numeric formats. Bytes per
value for FP32, BF16, FP16, TF32, FP8, FP6, FP4, INT8, and INT4 are what
the training memory model multiplies by parameter and activation counts.
TF32 keeps FP32 range but only 10 mantissa bits. Two alternative systems
are also declared: posits, whose useed = 2^(2^es) sets a tapered-accuracy
regime scale, and the logarithmic number system, which stores log2 of the
value and pays a fixed relative error per step instead of a fixed absolute
one.
"""

import sympy as sp

from ..core import eq, var
from ..core.units import bit, byte
from .precision_lowbit_common import (
    DIMENSIONLESS,
    LOWBIT_STORAGE_REF,
    POSIT_LNS_REF,
    TF32_REF,
    _annotate_variables,
)


bytes_fp32 = var(
    "precision.fp32.bytes", "B_FP32_fmt", "byte",
    "Bytes per FP32 value.",
    scope="precision",
)
bytes_bf16 = var(
    "precision.bf16.bytes", "B_BF16_fmt", "byte",
    "Bytes per BF16 value.",
    scope="precision",
)
bytes_fp16 = var(
    "precision.fp16.bytes", "B_FP16_fmt", "byte",
    "Bytes per FP16 value.",
    scope="precision",
)
bytes_tf32 = var(
    "precision.tf32.bytes", "B_TF32_fmt", "byte",
    "Bytes per TF32 value, typically carried in FP32 storage.",
    scope="precision",
)
bytes_fp8 = var(
    "precision.fp8.bytes", "B_FP8_fmt", "byte",
    "Bytes per FP8 value.",
    scope="precision",
)
bytes_fp6 = var(
    "precision.fp6.bytes", "B_FP6_fmt", "byte",
    "Bytes per packed FP6 value.",
    scope="precision",
)
bytes_fp4 = var(
    "precision.fp4.bytes", "B_FP4_fmt", "byte",
    "Bytes per packed FP4 value.",
    scope="precision",
)
bytes_int8 = var(
    "precision.int8.bytes", "B_INT8_fmt", "byte",
    "Bytes per INT8 value.",
    scope="precision",
)
bytes_int4 = var(
    "precision.int4.bytes", "B_INT4_fmt", "byte",
    "Bytes per packed INT4 value.",
    scope="precision",
)
tf32_man_bits = var(
    "precision.tf32.man_bits", "b_m_tf32", "bit",
    "Mantissa bits preserved by TF32 arithmetic.",
    scope="precision",
)
posit_es = var(
    "precision.posit.es", "es_posit", "bit",
    "Exponent-size parameter of a posit format.",
    scope="precision",
)
posit_useed = var(
    "precision.posit.useed", "useed_posit", "dimensionless",
    "Posit useed = 2^(2^es).",
    scope="precision",
)
lns_step = var(
    "precision.lns.log_step", "Delta_log_lns", "dimensionless",
    "Step size on the logarithmic lattice.",
    scope="precision",
)
lns_rel_error = var(
    "precision.lns.relative_error", "eps_lns", "dimensionless",
    "Relative error induced by half a log-step in a logarithmic number system.",
    scope="precision",
)
ratio_vs_bf16 = var(
    "precision.throughput_ratio_vs_bf16", "r_prec_BF16", "dimensionless",
    "Hardware throughput multiplier of the selected precision relative to BF16.",
    scope="precision",
)

_annotate_variables(
    (
        bytes_fp32,
        bytes_bf16,
        bytes_fp16,
        bytes_tf32,
        bytes_fp8,
        bytes_fp6,
        bytes_fp4,
        bytes_int8,
        bytes_int4,
    ),
    byte,
    [LOWBIT_STORAGE_REF],
)
_annotate_variables((tf32_man_bits,), bit, [TF32_REF])
_annotate_variables((posit_es,), bit, [POSIT_LNS_REF])
_annotate_variables(
    (posit_useed, lns_step, lns_rel_error),
    DIMENSIONLESS,
    [POSIT_LNS_REF],
)
_annotate_variables((ratio_vs_bf16,), DIMENSIONLESS, [LOWBIT_STORAGE_REF])


eq_bytes_fp32 = eq(
    "precision.eq.bytes_fp32",
    bytes_fp32.symbol,
    4,
    "FP32 stores four bytes per value.",
    references=[LOWBIT_STORAGE_REF],
)
eq_bytes_bf16 = eq(
    "precision.eq.bytes_bf16",
    bytes_bf16.symbol,
    2,
    "BF16 stores two bytes per value.",
    references=[LOWBIT_STORAGE_REF],
)
eq_bytes_fp16 = eq(
    "precision.eq.bytes_fp16",
    bytes_fp16.symbol,
    2,
    "FP16 stores two bytes per value.",
    references=[LOWBIT_STORAGE_REF],
)
eq_bytes_tf32 = eq(
    "precision.eq.bytes_tf32",
    bytes_tf32.symbol,
    4,
    "TF32 is typically carried in FP32 storage.",
    references=[TF32_REF],
)
eq_bytes_fp8 = eq(
    "precision.eq.bytes_fp8",
    bytes_fp8.symbol,
    1,
    "FP8 stores one byte per value.",
    references=[LOWBIT_STORAGE_REF],
)
eq_bytes_fp6 = eq(
    "precision.eq.bytes_fp6",
    bytes_fp6.symbol,
    sp.Rational(3, 4),
    "Packed FP6 stores three quarters of a byte per value.",
    references=[LOWBIT_STORAGE_REF],
)
eq_bytes_fp4 = eq(
    "precision.eq.bytes_fp4",
    bytes_fp4.symbol,
    sp.Rational(1, 2),
    "Packed FP4 stores half a byte per value.",
    references=[LOWBIT_STORAGE_REF],
)
eq_bytes_int8 = eq(
    "precision.eq.bytes_int8",
    bytes_int8.symbol,
    1,
    "INT8 stores one byte per value.",
    references=[LOWBIT_STORAGE_REF],
)
eq_bytes_int4 = eq(
    "precision.eq.bytes_int4",
    bytes_int4.symbol,
    sp.Rational(1, 2),
    "Packed INT4 stores half a byte per value.",
    references=[LOWBIT_STORAGE_REF],
)
eq_tf32_man_bits = eq(
    "precision.eq.tf32_man_bits",
    tf32_man_bits.symbol,
    10,
    "TF32 preserves 10 explicit mantissa bits in its Tensor Core arithmetic path.",
    references=[TF32_REF],
)

eq_posit_useed = eq(
    "precision.eq.posit_useed",
    posit_useed.symbol,
    2 ** (2 ** posit_es.symbol),
    "Posit useed equals 2 raised to 2^es.",
    references=[POSIT_LNS_REF],
)

eq_lns_rel_error = eq(
    "precision.eq.lns_relative_error",
    lns_rel_error.symbol,
    sp.exp(lns_step.symbol / 2) - 1,
    "A half-step on a logarithmic lattice produces multiplicative relative error exp(Delta/2) - 1.",
    references=[POSIT_LNS_REF],
    check_units=True,
)


PRECISION_LOWBIT_FORMAT_VARIABLES = (
    bytes_fp32,
    bytes_bf16,
    bytes_fp16,
    bytes_tf32,
    bytes_fp8,
    bytes_fp6,
    bytes_fp4,
    bytes_int8,
    bytes_int4,
    tf32_man_bits,
    posit_es,
    posit_useed,
    lns_step,
    lns_rel_error,
    ratio_vs_bf16,
)

PRECISION_LOWBIT_FORMAT_EQUATIONS = (
    eq_bytes_fp32,
    eq_bytes_bf16,
    eq_bytes_fp16,
    eq_bytes_tf32,
    eq_bytes_fp8,
    eq_bytes_fp6,
    eq_bytes_fp4,
    eq_bytes_int8,
    eq_bytes_int4,
    eq_tf32_man_bits,
    eq_posit_useed,
    eq_lns_rel_error,
)


__all__ = [
    "bytes_fp32",
    "bytes_bf16",
    "bytes_fp16",
    "bytes_tf32",
    "bytes_fp8",
    "bytes_fp6",
    "bytes_fp4",
    "bytes_int8",
    "bytes_int4",
    "tf32_man_bits",
    "posit_es",
    "posit_useed",
    "lns_step",
    "lns_rel_error",
    "ratio_vs_bf16",
    "eq_bytes_fp32",
    "eq_bytes_bf16",
    "eq_bytes_fp16",
    "eq_bytes_tf32",
    "eq_bytes_fp8",
    "eq_bytes_fp6",
    "eq_bytes_fp4",
    "eq_bytes_int8",
    "eq_bytes_int4",
    "eq_tf32_man_bits",
    "eq_posit_useed",
    "eq_lns_rel_error",
]
