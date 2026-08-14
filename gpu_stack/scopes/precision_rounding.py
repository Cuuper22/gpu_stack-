"""
scopes/precision_rounding.py
============================

What quantization costs, statistically. A format can only represent a
grid of values, and the gap between neighbors is the quantization step;
any input lands between a lower and upper grid point. Round-to-nearest is
unbiased with error variance step^2 / 12; round-toward-zero and the
directional modes trade that for a systematic bias of order the step.
Stochastic rounding rounds up with probability equal to the fractional
position, which makes the expected value exactly the input -- the
two-point StochasticRelation encodes that unbiasedness, at the price of a
larger variance. These error terms are what low-bit training analyses
build on.
"""

import sympy as sp

from ..core import Reference, StochasticRelation, eq, var


DIMENSIONLESS = sp.Integer(1)

ROUNDING_MODEL_REF = Reference(
    "Higham, Accuracy and Stability of Numerical Algorithms, 2nd ed., "
    "for floating-point rounding and local quantization-error models.",
    kind="textbook",
    year=2002,
)

STOCHASTIC_ROUNDING_REF = Reference(
    "Higham and Mary, A New Approach to Probabilistic Rounding Error Analysis, 2019.",
    kind="paper",
    year=2019,
)


def _annotate_variables(variables, sp_units, references):
    for variable in variables:
        variable.sp_units = sp_units
        variable.references.extend(references)


# ---------------------------------------------------------------------------
# The quantization grid first, then the error statistics of each rounding rule on it
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

_annotate_variables(
    (
        x_in,
        x_lo,
        x_hi,
        q_step,
        q_error_var,
        q_error_rms,
        rn_mean_error,
        rn_error_var,
        rz_abs_bias,
        rp_bias,
        rm_bias,
    ),
    DIMENSIONLESS,
    [ROUNDING_MODEL_REF],
)
_annotate_variables(
    (
        p_sr,
        sr_error_var,
        x_quantized,
    ),
    DIMENSIONLESS,
    [STOCHASTIC_ROUNDING_REF],
)


eq_q_step = eq(
    "precision.eq.quant_step",
    q_step.symbol,
    x_hi.symbol - x_lo.symbol,
    "The local quantization step is the gap between adjacent representable values.",
    references=[ROUNDING_MODEL_REF],
    check_units=True,
)

eq_q_error_var = eq(
    "precision.eq.quant_error_variance",
    q_error_var.symbol,
    q_step.symbol ** 2 / 12,
    "Uniform-quantizer error variance on a uniform residual is q^2 / 12.",
    references=[ROUNDING_MODEL_REF],
    check_units=True,
)

eq_q_error_rms = eq(
    "precision.eq.quant_error_rms",
    q_error_rms.symbol,
    sp.sqrt(q_error_var.symbol),
    "RMS quantization error is the square root of the variance.",
    references=[ROUNDING_MODEL_REF],
    check_units=True,
)

eq_rn_mean_error = eq(
    "precision.eq.rn_mean_error",
    rn_mean_error.symbol,
    0,
    "Round-to-nearest-even is unbiased on a symmetric local residual distribution.",
    references=[ROUNDING_MODEL_REF],
    check_units=True,
)

eq_rn_error_var = eq(
    "precision.eq.rn_error_variance",
    rn_error_var.symbol,
    q_step.symbol ** 2 / 12,
    "Round-to-nearest has the same local variance as uniform quantization noise under a uniform residual model.",
    references=[ROUNDING_MODEL_REF],
    check_units=True,
)

eq_rz_abs_bias = eq(
    "precision.eq.rz_abs_bias",
    rz_abs_bias.symbol,
    q_step.symbol / 2,
    "Round-toward-zero can shift values by up to half a cell in one direction.",
    references=[ROUNDING_MODEL_REF],
    check_units=True,
)

eq_rp_bias = eq(
    "precision.eq.rp_bias",
    rp_bias.symbol,
    q_step.symbol / 2,
    "Round-toward-plus-infinity biases upward by half a cell under a uniform local residual model.",
    references=[ROUNDING_MODEL_REF],
    check_units=True,
)

eq_rm_bias = eq(
    "precision.eq.rm_bias",
    rm_bias.symbol,
    -q_step.symbol / 2,
    "Round-toward-minus-infinity biases downward by half a cell under a uniform local residual model.",
    references=[ROUNDING_MODEL_REF],
    check_units=True,
)

eq_sr_probability = eq(
    "precision.eq.sr_probability",
    p_sr.symbol,
    (x_in.symbol - x_lo.symbol) / (x_hi.symbol - x_lo.symbol),
    "Stochastic rounding chooses the upper grid point with probability proportional to the distance from the lower grid point.",
    references=[STOCHASTIC_ROUNDING_REF],
    check_units=True,
)

eq_sr_error_var = eq(
    "precision.eq.sr_error_variance",
    sr_error_var.symbol,
    (x_in.symbol - x_lo.symbol) * (x_hi.symbol - x_in.symbol),
    "Two-point stochastic rounding has variance (x - x_lo) * (x_hi - x).",
    references=[STOCHASTIC_ROUNDING_REF],
    check_units=True,
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
    references=[STOCHASTIC_ROUNDING_REF],
)


PRECISION_ROUNDING_VARIABLES = (
    x_in,
    x_lo,
    x_hi,
    q_step,
    q_error_var,
    q_error_rms,
    rn_mean_error,
    rn_error_var,
    rz_abs_bias,
    rp_bias,
    rm_bias,
    p_sr,
    sr_error_var,
    x_quantized,
)

PRECISION_ROUNDING_EQUATIONS = (
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
)


__all__ = [
    "x_in",
    "x_lo",
    "x_hi",
    "q_step",
    "q_error_var",
    "q_error_rms",
    "rn_mean_error",
    "rn_error_var",
    "rz_abs_bias",
    "rp_bias",
    "rm_bias",
    "p_sr",
    "sr_error_var",
    "x_quantized",
    "eq_q_step",
    "eq_q_error_var",
    "eq_q_error_rms",
    "eq_rn_mean_error",
    "eq_rn_error_var",
    "eq_rz_abs_bias",
    "eq_rp_bias",
    "eq_rm_bias",
    "eq_sr_probability",
    "eq_sr_error_var",
    "sr_distribution",
    "PRECISION_ROUNDING_VARIABLES",
    "PRECISION_ROUNDING_EQUATIONS",
]
