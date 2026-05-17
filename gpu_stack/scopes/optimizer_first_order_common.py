"""
scopes/optimizer_first_order_common.py
======================================

Shared first-order optimizer state.

These declarations provide the gradient, parameter, learning-rate, decay, step
index, and optimizer-state byte handles used by every first-order optimizer
family.
"""

import sympy as sp
from ..core import Reference, var
from ..core.units import byte


DIMENSIONLESS = sp.Integer(1)

OPT_FIRST_ORDER_REF = Reference(
    "First-order optimizer bookkeeping treats parameters, gradients, "
    "moments, learning-rate coefficients, and signed update directions as "
    "dimensionless tensor values; storage state is tracked separately in "
    "bytes.",
    kind="model",
)
ADAM_REF = Reference(
    "Kingma and Ba, Adam: A Method for Stochastic Optimization, ICLR 2015.",
    kind="paper",
    year=2015,
)
ADAMW_REF = Reference(
    "Loshchilov and Hutter, Decoupled Weight Decay Regularization, ICLR 2019.",
    kind="paper",
    year=2019,
)
SGD_MOMENTUM_REF = Reference(
    "SGD momentum and Nesterov updates are represented as first-moment "
    "velocity-buffer recurrences over optimizer steps.",
    kind="model",
)
RMSPROP_REF = Reference(
    "Tieleman and Hinton, RMSProp, Neural Networks for Machine Learning "
    "lecture notes, 2012.",
    kind="memo",
    year=2012,
)
LAMB_REF = Reference(
    "You et al., Large Batch Optimization for Deep Learning: Training BERT "
    "in 76 minutes, ICLR 2020.",
    kind="paper",
    year=2020,
)
LION_REF = Reference(
    "Chen et al., Symbolic Discovery of Optimization Algorithms, 2023.",
    kind="paper",
    year=2023,
)
EMA_REF = Reference(
    "Optimizer EMA deployment weights are modeled as a standard exponential "
    "moving average over post-update parameters.",
    kind="model",
)


g = var(
    "opt.grad", "g_opt", "grad",
    "Gradient at step t.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[OPT_FIRST_ORDER_REF],
)
lr = var(
    "opt.lr", "eta_opt", "dimensionless",
    "Selected learning rate used by the optimizer update.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[OPT_FIRST_ORDER_REF],
)
wd = var(
    "opt.weight_decay", "lambda_wd_opt", "dimensionless",
    "Weight-decay coefficient.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[ADAMW_REF],
)
theta = var(
    "opt.param", "theta_opt", "param",
    "Parameter value at step t.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[OPT_FIRST_ORDER_REF],
)
theta_next = var(
    "opt.param_next", "theta_next_opt", "param",
    "Parameter value at step t + 1 under the selected optimizer.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[OPT_FIRST_ORDER_REF],
)
t_step = var(
    "opt.step_index", "t_opt", "step",
    "Optimizer step index, starting at one.",
    scope="optimizer",
    integer=True,
    positive=True,
    sp_units=DIMENSIONLESS,
    references=[OPT_FIRST_ORDER_REF],
)
bytes_per_opt_param = var(
    "opt.bytes_per_param", "B_opt_state_opt", "byte/param",
    "Bytes per optimizer-state value.",
    scope="optimizer",
    sp_units=byte,
    references=[OPT_FIRST_ORDER_REF],
)


OPT_FIRST_ORDER_SHARED_VARIABLES = [
    g, lr, wd, theta, theta_next, t_step,
    bytes_per_opt_param,
]


__all__ = [
    "DIMENSIONLESS",
    "OPT_FIRST_ORDER_REF", "ADAM_REF", "ADAMW_REF",
    "SGD_MOMENTUM_REF", "RMSPROP_REF", "LAMB_REF", "LION_REF", "EMA_REF",
    "g", "lr", "wd", "theta", "theta_next", "t_step",
    "bytes_per_opt_param",
    "OPT_FIRST_ORDER_SHARED_VARIABLES",
]
