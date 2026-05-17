"""
scopes/optimizer_first_order_ema.py
===================================

EMA deployment-weight declarations.
"""

from ..core import eq, var

from .optimizer_first_order_common import DIMENSIONLESS, EMA_REF, theta_next


ema_decay = var(
    "opt.ema.decay", "beta_ema_opt", "dimensionless",
    "Exponential-moving-average decay for deployment weights.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[EMA_REF],
)
ema_prev = var(
    "opt.ema.prev", "theta_ema_prev_opt", "param",
    "Previous EMA weights.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[EMA_REF],
)
ema_theta = var(
    "opt.ema.theta", "theta_ema_opt", "param",
    "Current EMA weights.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[EMA_REF],
)


eq_ema_theta = eq(
    "opt.eq.ema_theta",
    ema_theta.symbol,
    ema_decay.symbol * ema_prev.symbol + (1 - ema_decay.symbol) * theta_next.symbol,
    "EMA weights blend the previous EMA with the latest parameter value.",
    references=[EMA_REF],
    check_units=True,
)


OPT_FIRST_ORDER_EMA_VARIABLES = [
    ema_decay, ema_prev, ema_theta,
]

OPT_FIRST_ORDER_EMA_EQUATIONS = [
    eq_ema_theta,
]


__all__ = [
    "ema_decay", "ema_prev", "ema_theta",
    "eq_ema_theta",
    "OPT_FIRST_ORDER_EMA_VARIABLES", "OPT_FIRST_ORDER_EMA_EQUATIONS",
]
