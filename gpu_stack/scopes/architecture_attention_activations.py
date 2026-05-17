"""
Pointwise activation functions used by architecture blocks.
"""

import sympy as sp

from ..core import eq, var

from .architecture_attention_refs import ACTIVATION_REF, DIMENSIONLESS


act_x = var(
    "arch.act.x", "x_act_arch", "value",
    "Activation input.",
    scope="architecture",
)
sigmoid_x = var(
    "arch.act.sigmoid_x", "sigma_act_arch", "value",
    "Sigmoid applied to the activation input.",
    scope="architecture",
)
gelu_output = var(
    "arch.act.gelu", "gelu_act_arch", "value",
    "GeLU output.",
    scope="architecture",
)
silu_output = var(
    "arch.act.silu", "silu_act_arch", "value",
    "SiLU output.",
    scope="architecture",
)
swiglu_gate = var(
    "arch.act.swiglu_gate", "gate_swiglu_arch", "value",
    "Gate input to SwiGLU.",
    scope="architecture",
)
swiglu_value = var(
    "arch.act.swiglu_value", "value_swiglu_arch", "value",
    "Value branch input to SwiGLU.",
    scope="architecture",
)
swiglu_output = var(
    "arch.act.swiglu", "swiglu_act_arch", "value",
    "SwiGLU output.",
    scope="architecture",
)

for _v in (
    act_x, sigmoid_x, gelu_output, silu_output, swiglu_gate, swiglu_value,
    swiglu_output,
):
    _v.sp_units = DIMENSIONLESS
    _v.references.append(ACTIVATION_REF)


eq_sigmoid_x = eq(
    "arch.eq.sigmoid_x",
    sigmoid_x.symbol,
    1 / (1 + sp.exp(-act_x.symbol)),
    "Sigmoid is 1 / (1 + exp(-x)).",
    check_units=True,
)

eq_gelu_output = eq(
    "arch.eq.gelu",
    gelu_output.symbol,
    act_x.symbol * (1 + sp.erf(act_x.symbol / sp.sqrt(2))) / 2,
    "GeLU equals x times the Gaussian CDF of x.",
    check_units=True,
)

eq_silu_output = eq(
    "arch.eq.silu",
    silu_output.symbol,
    act_x.symbol / (1 + sp.exp(-act_x.symbol)),
    "SiLU equals x times sigmoid(x).",
    check_units=True,
)

eq_swiglu_output = eq(
    "arch.eq.swiglu",
    swiglu_output.symbol,
    swiglu_value.symbol / (1 + sp.exp(-swiglu_gate.symbol)),
    "SwiGLU multiplies the value branch by SiLU applied to the gate branch.",
    check_units=True,
)


ARCH_ATTENTION_ACTIVATION_VARIABLES = [
    act_x, sigmoid_x, gelu_output, silu_output, swiglu_gate, swiglu_value,
    swiglu_output,
]

ARCH_ATTENTION_ACTIVATION_EQUATIONS = [
    eq_sigmoid_x,
    eq_gelu_output,
    eq_silu_output,
    eq_swiglu_output,
]

for _e in (eq_sigmoid_x, eq_gelu_output, eq_silu_output, eq_swiglu_output):
    _e.references.append(ACTIVATION_REF)


__all__ = [
    "act_x", "sigmoid_x", "gelu_output", "silu_output",
    "swiglu_gate", "swiglu_value", "swiglu_output",
    "eq_sigmoid_x", "eq_gelu_output", "eq_silu_output", "eq_swiglu_output",
    "ARCH_ATTENTION_ACTIVATION_VARIABLES",
    "ARCH_ATTENTION_ACTIVATION_EQUATIONS",
]
