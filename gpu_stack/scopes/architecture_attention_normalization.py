"""
LayerNorm and RMSNorm architecture formulas.
"""

import sympy as sp

from ..core import eq, var

from .architecture_attention_refs import DIMENSIONLESS, NORMALIZATION_REF


norm_x = var(
    "arch.norm.x", "x_norm_arch", "value",
    "Input to a normalization layer.",
    scope="architecture",
)
norm_mean = var(
    "arch.norm.mean", "mu_norm_arch", "value",
    "Mean used by LayerNorm.",
    scope="architecture",
    positive=False,
)
norm_var = var(
    "arch.norm.var", "var_norm_arch", "value^2",
    "Variance used by LayerNorm.",
    scope="architecture",
)
norm_eps = var(
    "arch.norm.eps", "eps_norm_arch", "value",
    "Normalization epsilon.",
    scope="architecture",
)
layernorm_output = var(
    "arch.norm.layernorm_output", "y_ln_arch", "value",
    "LayerNorm output.",
    scope="architecture",
    positive=False,
)
rmsnorm_output = var(
    "arch.norm.rmsnorm_output", "y_rms_arch", "value",
    "RMSNorm output.",
    scope="architecture",
    positive=False,
)

for _v in (
    norm_x, norm_mean, norm_var, norm_eps, layernorm_output, rmsnorm_output,
):
    _v.sp_units = DIMENSIONLESS
    _v.references.append(NORMALIZATION_REF)


eq_layernorm_output = eq(
    "arch.eq.layernorm_output",
    layernorm_output.symbol,
    (norm_x.symbol - norm_mean.symbol) / sp.sqrt(norm_var.symbol + norm_eps.symbol),
    "LayerNorm subtracts the mean and divides by the standard deviation.",
    check_units=True,
)

eq_rmsnorm_output = eq(
    "arch.eq.rmsnorm_output",
    rmsnorm_output.symbol,
    norm_x.symbol / sp.sqrt(norm_var.symbol + norm_eps.symbol),
    "RMSNorm skips mean subtraction and divides by the root mean square scale.",
    check_units=True,
)


ARCH_ATTENTION_NORMALIZATION_VARIABLES = [
    norm_x, norm_mean, norm_var, norm_eps, layernorm_output, rmsnorm_output,
]

ARCH_ATTENTION_NORMALIZATION_EQUATIONS = [
    eq_layernorm_output,
    eq_rmsnorm_output,
]

for _e in (eq_layernorm_output, eq_rmsnorm_output):
    _e.references.append(NORMALIZATION_REF)


__all__ = [
    "norm_x", "norm_mean", "norm_var", "norm_eps",
    "layernorm_output", "rmsnorm_output",
    "eq_layernorm_output", "eq_rmsnorm_output",
    "ARCH_ATTENTION_NORMALIZATION_VARIABLES",
    "ARCH_ATTENTION_NORMALIZATION_EQUATIONS",
]
