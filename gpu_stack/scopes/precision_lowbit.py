"""
scopes/precision_lowbit.py
==========================

Low-bit formats and format-transform support.

Byte widths for FP32, BF16, FP16, TF32, FP8, FP6, FP4, INT8, and INT4.
TF32 mantissa bits, posit useed, logarithmic-number-system relative
error, FP16 loss scaling, and the symbolic Random Hadamard Transform
block used by microscaled low-bit formats.
"""

import sympy as sp

from ..core import Approximation, Reference, eq, var
from ..core.units import bit, byte
from .precision_ieee import min_normal


DIMENSIONLESS = sp.Integer(1)

LOWBIT_STORAGE_REF = Reference(
    "Low-bit precision storage widths for FP32, BF16, FP16, TF32, FP8, "
    "FP6, FP4, INT8, and INT4.",
    kind="model",
)

TF32_REF = Reference(
    "NVIDIA TensorFloat-32 uses an FP32-range format with a 10-bit "
    "explicit mantissa in Tensor Core arithmetic.",
    kind="datasheet",
)

POSIT_LNS_REF = Reference(
    "Gustafson and Yonemoto, Beating Floating Point at its Own Game: "
    "Posit Arithmetic, 2017, and logarithmic number-system quantization models.",
    kind="paper",
    year=2017,
)

LOSS_SCALING_REF = Reference(
    "Micikevicius et al., Mixed Precision Training, 2017.",
    kind="paper",
    year=2017,
)

RHT_REF = Reference(
    "Randomized Hadamard transforms spread coordinate outliers while preserving "
    "vector norm.",
    kind="model",
)


def _annotate_variables(variables, sp_units, references):
    for variable in variables:
        variable.sp_units = sp_units
        variable.references.extend(references)


# ---------------------------------------------------------------------------
# Integer, TF32, posit, and logarithmic number systems
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Loss scaling and underflow avoidance
# ---------------------------------------------------------------------------

grad_min_magnitude = var(
    "precision.loss_scaling.grad_min_magnitude", "g_min_ls", "value",
    "Smallest gradient magnitude worth preserving during low-precision training.",
    scope="precision",
)
loss_scale = var(
    "precision.loss_scaling.scale", "S_loss_ls", "dimensionless",
    "Loss-scaling multiplier.",
    scope="precision",
)
scaled_grad_min = var(
    "precision.loss_scaling.scaled_grad_min", "g_min_scaled_ls", "value",
    "Minimum preserved gradient magnitude after scaling.",
    scope="precision",
)
min_loss_scale_safe = var(
    "precision.loss_scaling.min_safe_scale", "S_loss_safe_ls", "dimensionless",
    "Minimum loss scale that lifts the target gradient above the normal underflow floor.",
    scope="precision",
)
grad_scaled = var(
    "precision.loss_scaling.grad_scaled", "g_scaled_ls", "value",
    "Gradient after multiplying the loss by the current scale.",
    scope="precision",
)
grad_unscaled = var(
    "precision.loss_scaling.grad_unscaled", "g_unscaled_ls", "value",
    "Gradient after dividing by the loss scale before the optimizer step.",
    scope="precision",
)

_annotate_variables(
    (
        grad_min_magnitude,
        loss_scale,
        scaled_grad_min,
        min_loss_scale_safe,
        grad_scaled,
        grad_unscaled,
    ),
    DIMENSIONLESS,
    [LOSS_SCALING_REF],
)


eq_scaled_grad_min = eq(
    "precision.eq.scaled_grad_min",
    scaled_grad_min.symbol,
    loss_scale.symbol * grad_min_magnitude.symbol,
    "Scaling the loss scales the backward gradient by the same factor.",
    references=[LOSS_SCALING_REF],
    check_units=True,
)

eq_min_loss_scale_safe = eq(
    "precision.eq.min_loss_scale_safe",
    min_loss_scale_safe.symbol,
    min_normal.symbol / grad_min_magnitude.symbol,
    "Minimum safe loss scale is the normal underflow threshold divided by the smallest gradient magnitude worth retaining.",
    references=[LOSS_SCALING_REF],
    check_units=True,
)

eq_grad_unscaled = eq(
    "precision.eq.grad_unscaled",
    grad_unscaled.symbol,
    grad_scaled.symbol / loss_scale.symbol,
    "Unscaling divides the accumulated low-precision gradient by the loss scale before the optimizer update.",
    references=[LOSS_SCALING_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Random Hadamard Transform, for microscaled low-bit formats
# ---------------------------------------------------------------------------

rht_dim = var(
    "precision.rht.dim", "m_rht", "dimensionless",
    "Dimension of the Hadamard block.",
    scope="precision",
)
rht_hadamard = var(
    "precision.rht.hadamard_matrix", "H_rht", "matrix",
    "Hadamard matrix block used in the random rotation.",
    scope="precision",
)
rht_sign_diag = var(
    "precision.rht.sign_diag", "D_rht", "matrix",
    "Diagonal matrix of random plus-or-minus one signs.",
    scope="precision",
)
rht_input = var(
    "precision.rht.input", "x_rht_in", "vector",
    "Input vector before the random Hadamard rotation.",
    scope="precision",
)
rht_output = var(
    "precision.rht.output", "x_rht_out", "vector",
    "Output vector after the random Hadamard rotation.",
    scope="precision",
)
rht_scale = var(
    "precision.rht.scale", "s_rht", "dimensionless",
    "Normalization factor applied to the Hadamard transform.",
    scope="precision",
)
rht_input_norm = var(
    "precision.rht.input_norm", "n_rht_in", "value",
    "Input norm before rotation.",
    scope="precision",
)
rht_output_norm = var(
    "precision.rht.output_norm", "n_rht_out", "value",
    "Output norm after rotation.",
    scope="precision",
)
rht_outlier_in = var(
    "precision.rht.outlier_in", "o_rht_in", "value",
    "Representative coordinate outlier magnitude before rotation.",
    scope="precision",
)
rht_outlier_out = var(
    "precision.rht.outlier_out", "o_rht_out", "value",
    "Representative coordinate outlier magnitude after rotation.",
    scope="precision",
)

_annotate_variables(
    (
        rht_dim,
        rht_hadamard,
        rht_sign_diag,
        rht_input,
        rht_output,
        rht_scale,
        rht_input_norm,
        rht_output_norm,
        rht_outlier_in,
        rht_outlier_out,
    ),
    DIMENSIONLESS,
    [RHT_REF],
)


eq_rht_scale = eq(
    "precision.eq.rht_scale",
    rht_scale.symbol,
    1 / sp.sqrt(rht_dim.symbol),
    "The normalized Hadamard transform uses 1/sqrt(m).",
    references=[RHT_REF],
    check_units=True,
)

eq_rht_output = eq(
    "precision.eq.rht_output",
    rht_output.symbol,
    rht_hadamard.symbol * rht_sign_diag.symbol * rht_input.symbol * rht_scale.symbol,
    "The random Hadamard transform is H_m D x / sqrt(m), represented here with abstract matrix-valued factors.",
    references=[RHT_REF],
    check_units=True,
)

eq_rht_norm = eq(
    "precision.eq.rht_norm_preservation",
    rht_output_norm.symbol,
    rht_input_norm.symbol,
    "The normalized Hadamard transform preserves vector norm.",
    references=[RHT_REF],
    check_units=True,
)

eq_rht_outlier = Approximation(
    "precision.eq.rht_outlier_spread",
    rht_outlier_out.symbol,
    rht_outlier_in.symbol / sp.sqrt(rht_dim.symbol),
    sp.Abs(rht_outlier_in.symbol) > 0,
    "When an outlier is concentrated in one coordinate, a random Hadamard rotation spreads it across the block by about sqrt(m).",
    references=[RHT_REF],
    check_units=True,
)


PRECISION_LOWBIT_VARIABLES = (
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
    grad_min_magnitude,
    loss_scale,
    scaled_grad_min,
    min_loss_scale_safe,
    grad_scaled,
    grad_unscaled,
    rht_dim,
    rht_hadamard,
    rht_sign_diag,
    rht_input,
    rht_output,
    rht_scale,
    rht_input_norm,
    rht_output_norm,
    rht_outlier_in,
    rht_outlier_out,
)

PRECISION_LOWBIT_EQUATIONS = (
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
    eq_scaled_grad_min,
    eq_min_loss_scale_safe,
    eq_grad_unscaled,
    eq_rht_scale,
    eq_rht_output,
    eq_rht_norm,
    eq_rht_outlier,
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
    "grad_min_magnitude",
    "loss_scale",
    "scaled_grad_min",
    "min_loss_scale_safe",
    "grad_scaled",
    "grad_unscaled",
    "rht_dim",
    "rht_hadamard",
    "rht_sign_diag",
    "rht_input",
    "rht_output",
    "rht_scale",
    "rht_input_norm",
    "rht_output_norm",
    "rht_outlier_in",
    "rht_outlier_out",
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
    "eq_scaled_grad_min",
    "eq_min_loss_scale_safe",
    "eq_grad_unscaled",
    "eq_rht_scale",
    "eq_rht_output",
    "eq_rht_norm",
    "eq_rht_outlier",
    "PRECISION_LOWBIT_VARIABLES",
    "PRECISION_LOWBIT_EQUATIONS",
]
