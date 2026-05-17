"""
scopes/optimizer_first_order_adamw.py
=====================================

AdamW moment declarations and update equations.
"""

import sympy as sp
from ..core import RelationRole, eq, var

from .optimizer_first_order_common import (
    ADAM_REF,
    ADAMW_REF,
    DIMENSIONLESS,
    g,
    lr,
    theta,
    theta_next,
    t_step,
    wd,
)


m = var(
    "opt.adam.m", "m_adam_opt", "moment",
    "AdamW first-moment estimate.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[ADAM_REF],
)
v_adam = var(
    "opt.adam.v", "v_adam_opt", "moment",
    "AdamW second-moment estimate.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[ADAM_REF],
)
m_prev = var(
    "opt.adam.m_prev", "m_prev_adam_opt", "moment",
    "Previous AdamW first moment.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[ADAM_REF],
)
v_prev = var(
    "opt.adam.v_prev", "v_prev_adam_opt", "moment",
    "Previous AdamW second moment.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[ADAM_REF],
)
beta1 = var(
    "opt.adam.beta1", "beta1_adam_opt", "dimensionless",
    "EMA coefficient for AdamW first moment.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[ADAM_REF],
)
beta2 = var(
    "opt.adam.beta2", "beta2_adam_opt", "dimensionless",
    "EMA coefficient for AdamW second moment.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[ADAM_REF],
)
eps_adam = var(
    "opt.adam.eps", "eps_adam_opt", "dimensionless",
    "Numerical stability epsilon in AdamW.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[ADAM_REF],
)
m_hat = var(
    "opt.adam.m_hat", "mhat_adam_opt", "moment",
    "Bias-corrected AdamW first moment.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[ADAM_REF],
)
v_hat = var(
    "opt.adam.v_hat", "vhat_adam_opt", "moment",
    "Bias-corrected AdamW second moment.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[ADAM_REF],
)


eq_adam_m = eq(
    "opt.eq.adam_m",
    m.symbol,
    beta1.symbol * m_prev.symbol + (1 - beta1.symbol) * g.symbol,
    "AdamW first-moment update.",
    references=[ADAM_REF],
    check_units=True,
)

eq_adam_v = eq(
    "opt.eq.adam_v",
    v_adam.symbol,
    beta2.symbol * v_prev.symbol + (1 - beta2.symbol) * g.symbol ** 2,
    "AdamW second-moment update.",
    references=[ADAM_REF],
    check_units=True,
)

eq_adam_m_hat = eq(
    "opt.eq.adam_m_hat",
    m_hat.symbol,
    m.symbol / (1 - beta1.symbol ** t_step.symbol),
    "Bias correction for the first moment.",
    references=[ADAM_REF],
    check_units=True,
)

eq_adam_v_hat = eq(
    "opt.eq.adam_v_hat",
    v_hat.symbol,
    v_adam.symbol / (1 - beta2.symbol ** t_step.symbol),
    "Bias correction for the second moment.",
    references=[ADAM_REF],
    check_units=True,
)

eq_adam_step = eq(
    "opt.eq.adam_step",
    theta_next.symbol,
    theta.symbol - lr.symbol * (m_hat.symbol / (sp.sqrt(v_hat.symbol) + eps_adam.symbol) + wd.symbol * theta.symbol),
    "AdamW subtracts the adaptive update and decoupled weight decay.",
    references=[ADAM_REF, ADAMW_REF],
    check_units=True,
    role=RelationRole.VARIANT,
    variant="adamw",
)


OPT_FIRST_ORDER_ADAMW_VARIABLES = [
    m, v_adam, m_prev, v_prev, beta1, beta2, eps_adam, m_hat, v_hat,
]

OPT_FIRST_ORDER_ADAMW_EQUATIONS = [
    eq_adam_m,
    eq_adam_v,
    eq_adam_m_hat,
    eq_adam_v_hat,
    eq_adam_step,
]


__all__ = [
    "m", "v_adam", "m_prev", "v_prev", "beta1", "beta2", "eps_adam",
    "m_hat", "v_hat",
    "eq_adam_m", "eq_adam_v", "eq_adam_m_hat", "eq_adam_v_hat",
    "eq_adam_step",
    "OPT_FIRST_ORDER_ADAMW_VARIABLES", "OPT_FIRST_ORDER_ADAMW_EQUATIONS",
]
