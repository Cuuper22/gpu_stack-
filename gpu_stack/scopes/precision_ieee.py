"""
scopes/precision_ieee.py
========================

IEEE-754 structural foundation.

Sign, exponent, mantissa bit counts, total width and bytes per value,
exponent bias and unbiased exponent limits, smallest normal and subnormal
values, largest normal, dynamic range, machine epsilon, ULP at one, the
subnormal-enabled flag, NaN and infinity code counts, and the piecewise
minimum-nonzero model that distinguishes subnormal support from flush-to-zero.
"""

import sympy as sp

from ..core import PiecewiseEquation, eq, var


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


PRECISION_IEEE_VARIABLES = (
    n_sign,
    n_exp,
    n_man,
    n_bits,
    bytes_per_val,
    exp_bias,
    exp_min_normal,
    exp_max_normal,
    min_normal,
    min_subnormal,
    min_nonzero,
    max_normal,
    dyn_range,
    epsilon_machine,
    ulp_at_one,
    subnormal_enabled,
    inf_code_count,
    nan_code_count,
)

PRECISION_IEEE_EQUATIONS = (
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
)


__all__ = [
    "n_sign",
    "n_exp",
    "n_man",
    "n_bits",
    "bytes_per_val",
    "exp_bias",
    "exp_min_normal",
    "exp_max_normal",
    "min_normal",
    "min_subnormal",
    "min_nonzero",
    "max_normal",
    "dyn_range",
    "epsilon_machine",
    "ulp_at_one",
    "subnormal_enabled",
    "inf_code_count",
    "nan_code_count",
    "eq_total_bits",
    "eq_bytes_per_value",
    "eq_exp_bias",
    "eq_exp_min_normal",
    "eq_exp_max_normal",
    "eq_machine_eps",
    "eq_ulp_at_one",
    "eq_min_normal",
    "eq_min_subnormal",
    "eq_min_nonzero",
    "eq_max_normal",
    "eq_dynamic_range",
    "eq_inf_code_count",
    "eq_nan_code_count",
    "PRECISION_IEEE_VARIABLES",
    "PRECISION_IEEE_EQUATIONS",
]
