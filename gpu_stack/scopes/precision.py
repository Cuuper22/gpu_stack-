"""
scopes/precision.py
===================

Number formats and quantization behavior.

This scope started as sign, exponent, mantissa, then stopped. That was not
remotely enough. Real training depends on underflow thresholds, subnormals,
NaN/Inf encodings, quantization noise, microscaling overhead, loss scaling,
and the format transforms used to keep FP4 from detonating on outliers.
"""

import sympy as sp
from ..core import (
    Approximation,
    PiecewiseEquation,
    StochasticRelation,
    System,
    eq,
    var,
)


sys_prec = System(
    name="precision",
    scope="precision",
    description="Floating-point, integer, microscaled, and quantized numeric formats.",
)


# ---------------------------------------------------------------------------
# Generic floating-point format
# ---------------------------------------------------------------------------

n_sign = var(
    "precision.sign_bits", "b_s", "bit",
    "Sign bits, usually 1 for IEEE-like formats.",
    scope="precision",
)
n_exp = var(
    "precision.exp_bits", "b_e", "bit",
    "Exponent bits.",
    scope="precision",
)
n_man = var(
    "precision.man_bits", "b_m", "bit",
    "Mantissa bits, excluding the implicit leading 1 for normal values.",
    scope="precision",
)
n_bits = var(
    "precision.total_bits", "b_tot", "bit",
    "Total bits per value: sign + exponent + mantissa.",
    scope="precision",
)
bytes_per_val = var(
    "precision.bytes_per_value", "B_val", "byte",
    "Bytes per value.",
    scope="precision",
)
exp_bias = var(
    "precision.exp_bias", "bias_e", "dimensionless",
    "Exponent bias for an IEEE-like encoding.",
    scope="precision",
)
exp_min_normal = var(
    "precision.exp_unbiased_min_normal", "e_fmt_min", "dimensionless",
    "Smallest unbiased exponent used by a normal number.",
    scope="precision",
)
exp_max_normal = var(
    "precision.exp_unbiased_max_normal", "e_fmt_max", "dimensionless",
    "Largest unbiased exponent used by a normal number.",
    scope="precision",
)
min_normal = var(
    "precision.min_normal", "x_fmt_min_norm", "value",
    "Smallest positive normal value.",
    scope="precision",
)
min_subnormal = var(
    "precision.min_subnormal", "x_fmt_min_sub", "value",
    "Smallest positive subnormal value.",
    scope="precision",
)
min_nonzero = var(
    "precision.min_nonzero", "x_fmt_min_nz", "value",
    "Smallest positive nonzero representable value.",
    scope="precision",
)
max_normal = var(
    "precision.max_normal", "x_fmt_max_norm", "value",
    "Largest finite normal value.",
    scope="precision",
)
dyn_range = var(
    "precision.dynamic_range", "R_dyn", "dimensionless",
    "Ratio of largest to smallest positive nonzero representable magnitudes.",
    scope="precision",
)
epsilon_machine = var(
    "precision.machine_eps", "eps_m", "dimensionless",
    "Machine epsilon near 1.0.",
    scope="precision",
)
ulp_at_one = var(
    "precision.ulp_at_one", "ulp_1_fmt", "value",
    "Spacing between adjacent representable values around 1.0.",
    scope="precision",
)
subnormal_enabled = var(
    "precision.subnormals.enabled", "I_sub_fmt", "flag",
    "1 if the format preserves subnormals, 0 if it flushes them to zero.",
    scope="precision",
    positive=False,
    integer=True,
)
inf_code_count = var(
    "precision.inf_code_count", "N_inf_fmt", "codes",
    "Number of infinity bit patterns.",
    scope="precision",
)
nan_code_count = var(
    "precision.nan_code_count", "N_nan_fmt", "codes",
    "Number of NaN bit patterns.",
    scope="precision",
)


eq_total_bits = eq(
    "precision.eq.total_bits",
    n_bits.symbol,
    n_sign.symbol + n_exp.symbol + n_man.symbol,
    "Format width is the sum of sign, exponent, and mantissa bits.",
)

eq_bytes_per_value = eq(
    "precision.eq.bytes_per_value",
    bytes_per_val.symbol,
    n_bits.symbol / 8,
    "Bytes per value equals bits per value divided by eight.",
)

eq_exp_bias = eq(
    "precision.eq.exp_bias",
    exp_bias.symbol,
    2 ** (n_exp.symbol - 1) - 1,
    "IEEE-like exponent bias.",
)

eq_exp_min_normal = eq(
    "precision.eq.exp_min_normal",
    exp_min_normal.symbol,
    1 - exp_bias.symbol,
    "Minimum unbiased normal exponent equals 1 minus the exponent bias.",
)

eq_exp_max_normal = eq(
    "precision.eq.exp_max_normal",
    exp_max_normal.symbol,
    exp_bias.symbol,
    "Maximum unbiased normal exponent equals the exponent bias when all-ones exponents are reserved.",
)

eq_machine_eps = eq(
    "precision.eq.machine_eps",
    epsilon_machine.symbol,
    2 ** (-n_man.symbol),
    "Machine epsilon near one is 2^(-mantissa_bits).",
)

eq_ulp_at_one = eq(
    "precision.eq.ulp_at_one",
    ulp_at_one.symbol,
    2 ** (-n_man.symbol),
    "ULP spacing around one matches machine epsilon for an IEEE-like normal encoding.",
)

eq_min_normal = eq(
    "precision.eq.min_normal",
    min_normal.symbol,
    2 ** exp_min_normal.symbol,
    "Smallest positive normal value is 2^(minimum normal exponent).",
)

eq_min_subnormal = eq(
    "precision.eq.min_subnormal",
    min_subnormal.symbol,
    2 ** (exp_min_normal.symbol - n_man.symbol),
    "Smallest positive subnormal extends the exponent ladder downward by mantissa_bits.",
)

eq_min_nonzero = PiecewiseEquation(
    "precision.eq.min_nonzero",
    min_nonzero.symbol,
    pieces=[
        (min_subnormal.symbol, sp.Eq(subnormal_enabled.symbol, 1)),
        (min_normal.symbol, True),
    ],
    description="Minimum positive nonzero value depends on whether subnormals are preserved or flushed.",
)

eq_max_normal = eq(
    "precision.eq.max_normal",
    max_normal.symbol,
    (2 - 2 ** (-n_man.symbol)) * 2 ** exp_max_normal.symbol,
    "Largest finite normal value uses the largest non-reserved exponent and an all-ones mantissa.",
)

eq_dynamic_range = eq(
    "precision.eq.dynamic_range",
    dyn_range.symbol,
    max_normal.symbol / min_nonzero.symbol,
    "Dynamic range is max finite magnitude divided by min positive nonzero magnitude.",
)

eq_inf_code_count = eq(
    "precision.eq.inf_code_count",
    inf_code_count.symbol,
    2,
    "IEEE-like formats have two infinity encodings, positive and negative.",
)

eq_nan_code_count = eq(
    "precision.eq.nan_code_count",
    nan_code_count.symbol,
    2 * (2 ** n_man.symbol - 1),
    "NaN codes use all-ones exponents and any nonzero mantissa, with both sign choices.",
)


# ---------------------------------------------------------------------------
# Quantization and rounding
# ---------------------------------------------------------------------------

x_in = var(
    "precision.quant.x_in", "x_q_in", "value",
    "Exact input value before quantization.",
    scope="precision",
)
x_lo = var(
    "precision.quant.x_lo", "x_q_lo", "value",
    "Nearest representable value below the input.",
    scope="precision",
)
x_hi = var(
    "precision.quant.x_hi", "x_q_hi", "value",
    "Nearest representable value above the input.",
    scope="precision",
)
q_step = var(
    "precision.quant.step", "q_step_fmt", "value",
    "Quantization step for a local uniform grid.",
    scope="precision",
)
q_error_var = var(
    "precision.quant.error_variance", "sigma_q2_fmt", "value^2",
    "Quantization-error variance for a uniform mid-tread quantizer on a uniform residual.",
    scope="precision",
)
q_error_rms = var(
    "precision.quant.error_rms", "sigma_q_fmt", "value",
    "RMS quantization error.",
    scope="precision",
)
rn_mean_error = var(
    "precision.rounding.rn_mean_error", "mu_rn_fmt", "value",
    "Mean error under round-to-nearest-even for a symmetric residual distribution.",
    scope="precision",
    positive=False,
)
rn_error_var = var(
    "precision.rounding.rn_error_variance", "sigma_rn2_fmt", "value^2",
    "Error variance under round-to-nearest for a uniform residual.",
    scope="precision",
)
rz_abs_bias = var(
    "precision.rounding.rz_abs_bias", "b_rz_abs_fmt", "value",
    "Worst-case absolute bias scale for round-toward-zero on one quantization cell.",
    scope="precision",
)
rp_bias = var(
    "precision.rounding.rp_bias", "b_rp_fmt", "value",
    "Upper-directed rounding bias on one quantization cell.",
    scope="precision",
)
rm_bias = var(
    "precision.rounding.rm_bias", "b_rm_fmt", "value",
    "Lower-directed rounding bias on one quantization cell.",
    scope="precision",
    positive=False,
)
p_sr = var(
    "precision.sr.p_up", "p_SR_fmt", "probability",
    "Probability of rounding up under stochastic rounding.",
    scope="precision",
)
sr_error_var = var(
    "precision.sr.error_variance", "sigma_sr2_fmt", "value^2",
    "Error variance under stochastic rounding between the local bracketing points.",
    scope="precision",
)
x_quantized = var(
    "precision.sr.x_quantized", "x_SR_fmt", "value",
    "Random quantized value produced by stochastic rounding.",
    scope="precision",
)


eq_q_step = eq(
    "precision.eq.quant_step",
    q_step.symbol,
    x_hi.symbol - x_lo.symbol,
    "The local quantization step is the gap between adjacent representable values.",
)

eq_q_error_var = eq(
    "precision.eq.quant_error_variance",
    q_error_var.symbol,
    q_step.symbol ** 2 / 12,
    "Uniform-quantizer error variance on a uniform residual is q^2 / 12.",
)

eq_q_error_rms = eq(
    "precision.eq.quant_error_rms",
    q_error_rms.symbol,
    sp.sqrt(q_error_var.symbol),
    "RMS quantization error is the square root of the variance.",
)

eq_rn_mean_error = eq(
    "precision.eq.rn_mean_error",
    rn_mean_error.symbol,
    0,
    "Round-to-nearest-even is unbiased on a symmetric local residual distribution.",
)

eq_rn_error_var = eq(
    "precision.eq.rn_error_variance",
    rn_error_var.symbol,
    q_step.symbol ** 2 / 12,
    "Round-to-nearest has the same local variance as uniform quantization noise under a uniform residual model.",
)

eq_rz_abs_bias = eq(
    "precision.eq.rz_abs_bias",
    rz_abs_bias.symbol,
    q_step.symbol / 2,
    "Round-toward-zero can shift values by up to half a cell in one direction.",
)

eq_rp_bias = eq(
    "precision.eq.rp_bias",
    rp_bias.symbol,
    q_step.symbol / 2,
    "Round-toward-plus-infinity biases upward by half a cell under a uniform local residual model.",
)

eq_rm_bias = eq(
    "precision.eq.rm_bias",
    rm_bias.symbol,
    -q_step.symbol / 2,
    "Round-toward-minus-infinity biases downward by half a cell under a uniform local residual model.",
)

eq_sr_probability = eq(
    "precision.eq.sr_probability",
    p_sr.symbol,
    (x_in.symbol - x_lo.symbol) / (x_hi.symbol - x_lo.symbol),
    "Stochastic rounding chooses the upper grid point with probability proportional to the distance from the lower grid point.",
)

eq_sr_error_var = eq(
    "precision.eq.sr_error_variance",
    sr_error_var.symbol,
    (x_in.symbol - x_lo.symbol) * (x_hi.symbol - x_in.symbol),
    "Two-point stochastic rounding has variance (x - x_lo) * (x_hi - x).",
)
sr_distribution = StochasticRelation(
    "precision.eq.sr_distribution",
    x_quantized.symbol,
    distribution="TwoPoint",
    parameters={
        "x_lo": x_lo.symbol,
        "x_hi": x_hi.symbol,
        "p_up": p_sr.symbol,
    },
    mean=x_in.symbol,
    variance=sr_error_var.symbol,
    description="Stochastic rounding emits x_lo or x_hi with probabilities chosen so the expected value equals the exact input.",
)


# ---------------------------------------------------------------------------
# Microscaling, block floating point, and dynamic fixed point
# ---------------------------------------------------------------------------

block_size = var(
    "precision.microscale.block_size", "B_blk_ms", "elements",
    "Number of values sharing one microscale factor.",
    scope="precision",
)
scale_bits = var(
    "precision.microscale.scale_bits", "b_scale_ms", "bit",
    "Bits used for the first-level per-block scale.",
    scope="precision",
)
second_scale_bits = var(
    "precision.microscale.second_scale_bits", "b_scale2_ms", "bit",
    "Bits used for the optional second-level tensor scale.",
    scope="precision",
)
second_scale_fanout = var(
    "precision.microscale.second_scale_fanout", "N_scale2_ms", "elements",
    "Number of values amortizing one second-level scale.",
    scope="precision",
)
eff_bits_per_val = var(
    "precision.microscale.effective_bits", "b_eff_ms", "bit",
    "Effective bits per value after amortizing scale metadata.",
    scope="precision",
)
bfp_block_size = var(
    "precision.bfp.block_size", "B_blk_bfp", "elements",
    "Block size for block-floating-point.",
    scope="precision",
)
bfp_shared_exp_bits = var(
    "precision.bfp.shared_exp_bits", "b_exp_bfp", "bit",
    "Shared exponent bits per BFP block.",
    scope="precision",
)
bfp_eff_bits = var(
    "precision.bfp.effective_bits", "b_eff_bfp", "bit",
    "Effective bits per BFP value including amortized shared exponent overhead.",
    scope="precision",
)
fixed_frac_bits = var(
    "precision.fixed.frac_bits", "b_frac_fix", "bit",
    "Fractional bits in a dynamic fixed-point format.",
    scope="precision",
)
fixed_scale = var(
    "precision.fixed.scale", "s_fix", "value",
    "Dynamic fixed-point scale factor for one least-significant step.",
    scope="precision",
)


eq_effective_bits = eq(
    "precision.eq.effective_bits",
    eff_bits_per_val.symbol,
    n_bits.symbol + scale_bits.symbol / block_size.symbol + second_scale_bits.symbol / second_scale_fanout.symbol,
    "Effective bits per value equal payload bits plus amortized first-level and second-level scale overheads.",
)

eq_bfp_eff_bits = eq(
    "precision.eq.bfp_effective_bits",
    bfp_eff_bits.symbol,
    n_bits.symbol + bfp_shared_exp_bits.symbol / bfp_block_size.symbol,
    "BFP effective bits equal payload bits plus amortized shared exponent metadata.",
)

eq_fixed_scale = eq(
    "precision.eq.fixed_scale",
    fixed_scale.symbol,
    2 ** (-fixed_frac_bits.symbol),
    "A dynamic fixed-point step is 2^(-fractional_bits) in the chosen local scale frame.",
)


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


eq_bytes_fp32 = eq("precision.eq.bytes_fp32", bytes_fp32.symbol, 4, "FP32 stores four bytes per value.")
eq_bytes_bf16 = eq("precision.eq.bytes_bf16", bytes_bf16.symbol, 2, "BF16 stores two bytes per value.")
eq_bytes_fp16 = eq("precision.eq.bytes_fp16", bytes_fp16.symbol, 2, "FP16 stores two bytes per value.")
eq_bytes_tf32 = eq("precision.eq.bytes_tf32", bytes_tf32.symbol, 4, "TF32 is typically carried in FP32 storage.")
eq_bytes_fp8 = eq("precision.eq.bytes_fp8", bytes_fp8.symbol, 1, "FP8 stores one byte per value.")
eq_bytes_fp6 = eq("precision.eq.bytes_fp6", bytes_fp6.symbol, sp.Rational(3, 4), "Packed FP6 stores three quarters of a byte per value.")
eq_bytes_fp4 = eq("precision.eq.bytes_fp4", bytes_fp4.symbol, sp.Rational(1, 2), "Packed FP4 stores half a byte per value.")
eq_bytes_int8 = eq("precision.eq.bytes_int8", bytes_int8.symbol, 1, "INT8 stores one byte per value.")
eq_bytes_int4 = eq("precision.eq.bytes_int4", bytes_int4.symbol, sp.Rational(1, 2), "Packed INT4 stores half a byte per value.")
eq_tf32_man_bits = eq(
    "precision.eq.tf32_man_bits",
    tf32_man_bits.symbol,
    10,
    "TF32 preserves 10 explicit mantissa bits in its Tensor Core arithmetic path.",
)

eq_posit_useed = eq(
    "precision.eq.posit_useed",
    posit_useed.symbol,
    2 ** (2 ** posit_es.symbol),
    "Posit useed equals 2 raised to 2^es.",
)

eq_lns_rel_error = eq(
    "precision.eq.lns_relative_error",
    lns_rel_error.symbol,
    sp.exp(lns_step.symbol / 2) - 1,
    "A half-step on a logarithmic lattice produces multiplicative relative error exp(Delta/2) - 1.",
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


eq_scaled_grad_min = eq(
    "precision.eq.scaled_grad_min",
    scaled_grad_min.symbol,
    loss_scale.symbol * grad_min_magnitude.symbol,
    "Scaling the loss scales the backward gradient by the same factor.",
)

eq_min_loss_scale_safe = eq(
    "precision.eq.min_loss_scale_safe",
    min_loss_scale_safe.symbol,
    min_normal.symbol / grad_min_magnitude.symbol,
    "Minimum safe loss scale is the normal underflow threshold divided by the smallest gradient magnitude worth retaining.",
)

eq_grad_unscaled = eq(
    "precision.eq.grad_unscaled",
    grad_unscaled.symbol,
    grad_scaled.symbol / loss_scale.symbol,
    "Unscaling divides the accumulated low-precision gradient by the loss scale before the optimizer update.",
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


eq_rht_scale = eq(
    "precision.eq.rht_scale",
    rht_scale.symbol,
    1 / sp.sqrt(rht_dim.symbol),
    "The normalized Hadamard transform uses 1/sqrt(m).",
)

eq_rht_output = eq(
    "precision.eq.rht_output",
    rht_output.symbol,
    rht_hadamard.symbol * rht_sign_diag.symbol * rht_input.symbol * rht_scale.symbol,
    "The random Hadamard transform is H_m D x / sqrt(m), represented here with abstract matrix-valued factors.",
)

eq_rht_norm = eq(
    "precision.eq.rht_norm_preservation",
    rht_output_norm.symbol,
    rht_input_norm.symbol,
    "The normalized Hadamard transform preserves vector norm.",
)

eq_rht_outlier = Approximation(
    "precision.eq.rht_outlier_spread",
    rht_outlier_out.symbol,
    rht_outlier_in.symbol / sp.sqrt(rht_dim.symbol),
    sp.Abs(rht_outlier_in.symbol) > 0,
    "When an outlier is concentrated in one coordinate, a random Hadamard rotation spreads it across the block by about sqrt(m).",
)


PRECISION_VARIABLES = [
    n_sign, n_exp, n_man, n_bits, bytes_per_val, exp_bias,
    exp_min_normal, exp_max_normal, min_normal, min_subnormal, min_nonzero,
    max_normal, dyn_range, epsilon_machine, ulp_at_one, subnormal_enabled,
    inf_code_count, nan_code_count,
    x_in, x_lo, x_hi, q_step, q_error_var, q_error_rms, rn_mean_error,
    rn_error_var, rz_abs_bias, rp_bias, rm_bias, p_sr, sr_error_var,
    x_quantized,
    block_size, scale_bits, second_scale_bits, second_scale_fanout,
    eff_bits_per_val, bfp_block_size, bfp_shared_exp_bits, bfp_eff_bits,
    fixed_frac_bits, fixed_scale,
    bytes_fp32, bytes_bf16, bytes_fp16, bytes_tf32, bytes_fp8, bytes_fp6,
    bytes_fp4, bytes_int8, bytes_int4, tf32_man_bits, posit_es, posit_useed,
    lns_step, lns_rel_error, ratio_vs_bf16,
    grad_min_magnitude, loss_scale, scaled_grad_min, min_loss_scale_safe,
    grad_scaled, grad_unscaled,
    rht_dim, rht_hadamard, rht_sign_diag, rht_input, rht_output, rht_scale,
    rht_input_norm, rht_output_norm, rht_outlier_in, rht_outlier_out,
]

PRECISION_EQUATIONS = [
    eq_total_bits,
    eq_bytes_per_value,
    eq_exp_bias,
    eq_exp_min_normal,
    eq_exp_max_normal,
    eq_machine_eps,
    eq_ulp_at_one,
    eq_min_normal,
    eq_min_subnormal,
    eq_min_nonzero,
    eq_max_normal,
    eq_dynamic_range,
    eq_inf_code_count,
    eq_nan_code_count,
    eq_q_step,
    eq_q_error_var,
    eq_q_error_rms,
    eq_rn_mean_error,
    eq_rn_error_var,
    eq_rz_abs_bias,
    eq_rp_bias,
    eq_rm_bias,
    eq_sr_probability,
    eq_sr_error_var,
    sr_distribution,
    eq_effective_bits,
    eq_bfp_eff_bits,
    eq_fixed_scale,
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
]

for v in PRECISION_VARIABLES:
    sys_prec.add(v)

for e in PRECISION_EQUATIONS:
    sys_prec.add(e)
