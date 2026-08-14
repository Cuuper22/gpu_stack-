"""
scopes/optimizer_first_order_ema.py
===================================

EMA weights: a smoothed shadow copy of the model for deployment.

Training weights jitter step to step, and the checkpoint you happen to
stop at may sit in a noisy spot. An exponential moving average fixes that
cheaply: keep a shadow copy updated as decay times the old shadow plus
(1 - decay) times the fresh weights, with decay near 1 so the shadow
trails the training trajectory smoothly. The averaged weights often
evaluate better than the raw ones and are what gets shipped. The cost is
one extra full copy of the parameters — a memory line item the sharding
helper's state multiplier can include.
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
