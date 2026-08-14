"""
scopes/optimizer_first_order.py
===============================

Public facade for first-order optimizers — the ones that use only gradients.

A first-order optimizer sees nothing but the gradient and its own running
statistics; everything from plain SGD to AdamW and Lion fits that mold.
The declarations live in focused helpers: shared state (parameters,
gradient, learning rate, weight decay, step index), AdamW's moment
estimates, the variant family (SGD momentum, RMSProp, LAMB, Lion), and
the EMA weights kept for deployment. This facade re-exports them in a
deliberate order — the registry preserves insertion order, so the import
sequence here is part of the public contract — and assembles the combined
variable and equation lists the optimizer aggregator registers.
"""

import sympy as sp
from ..core import Reference, RelationRole, eq, var
from ..core.units import byte

from .optimizer_first_order_common import (
    ADAM_REF,
    ADAMW_REF,
    DIMENSIONLESS,
    EMA_REF,
    LAMB_REF,
    LION_REF,
    OPT_FIRST_ORDER_REF,
    OPT_FIRST_ORDER_SHARED_VARIABLES,
    RMSPROP_REF,
    SGD_MOMENTUM_REF,
    bytes_per_opt_param,
    g,
    lr,
    theta,
    theta_next,
    t_step,
    wd,
)
from .optimizer_first_order_adamw import *
from .optimizer_first_order_adamw import (
    OPT_FIRST_ORDER_ADAMW_EQUATIONS,
    OPT_FIRST_ORDER_ADAMW_VARIABLES,
)
from .optimizer_first_order_variants import *
from .optimizer_first_order_variants import (
    OPT_FIRST_ORDER_VARIANT_EQUATIONS,
    OPT_FIRST_ORDER_VARIANT_VARIABLES,
)
from .optimizer_first_order_ema import *
from .optimizer_first_order_ema import (
    OPT_FIRST_ORDER_EMA_EQUATIONS,
    OPT_FIRST_ORDER_EMA_VARIABLES,
)


OPT_FIRST_ORDER_VARIABLES = (
    OPT_FIRST_ORDER_SHARED_VARIABLES
    + OPT_FIRST_ORDER_ADAMW_VARIABLES
    + OPT_FIRST_ORDER_VARIANT_VARIABLES
    + OPT_FIRST_ORDER_EMA_VARIABLES
)

OPT_FIRST_ORDER_EQUATIONS = (
    OPT_FIRST_ORDER_ADAMW_EQUATIONS
    + OPT_FIRST_ORDER_VARIANT_EQUATIONS
    + OPT_FIRST_ORDER_EMA_EQUATIONS
)


__all__ = [
    "g", "lr", "wd", "theta", "theta_next", "t_step",
    "bytes_per_opt_param",
    "m", "v_adam", "m_prev", "v_prev", "beta1", "beta2", "eps_adam",
    "m_hat", "v_hat",
    "sgd_velocity_prev", "sgd_velocity", "sgd_momentum_coeff",
    "theta_next_sgd", "theta_next_nesterov",
    "rmsprop_avg_prev", "rmsprop_avg", "beta_rms", "eps_rms",
    "theta_next_rms",
    "weight_norm", "update_norm", "trust_ratio", "theta_next_lamb",
    "lion_m_prev", "lion_m", "lion_beta1", "lion_beta2",
    "lion_direction", "theta_next_lion",
    "ema_decay", "ema_prev", "ema_theta",
    "eq_adam_m", "eq_adam_v", "eq_adam_m_hat", "eq_adam_v_hat",
    "eq_adam_step",
    "eq_sgd_velocity", "eq_sgd_step", "eq_nesterov_step",
    "eq_rmsprop_avg", "eq_rmsprop_step",
    "eq_trust_ratio", "eq_lamb_step",
    "eq_lion_direction", "eq_lion_m", "eq_lion_step",
    "eq_ema_theta",
    "OPT_FIRST_ORDER_VARIABLES", "OPT_FIRST_ORDER_EQUATIONS",
]
