"""
scopes/optimizer_loss_scaling.py
================================

Dynamic loss scaling for low-precision training.

This helper tracks the scaled loss, its observed gradient, the unscaled
gradient used by the optimizer, overflow counting, the stable-step counter,
and the piecewise rule that chooses the next loss scale.
"""

import sympy as sp

from ..core import PiecewiseEquation, Reference, eq, var


DIMENSIONLESS = sp.Integer(1)

LOSS_SCALING_REF = Reference(
    "Dynamic loss scaling is modeled as dimensionless loss and gradient "
    "rescaling with integer overflow/stability counters controlling the next "
    "scale value.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Dynamic loss scaling for low-precision training
# ---------------------------------------------------------------------------

loss_scale_growth_interval = var(
    "opt.loss_scale.growth_interval", "N_ls_growth_opt", "steps",
    "Stable steps required before increasing the loss scale.",
    scope="optimizer",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[LOSS_SCALING_REF],
)
loss_unscaled = var(
    "opt.loss_scale.loss_unscaled", "L_unscaled_opt", "value",
    "Original loss before scaling.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[LOSS_SCALING_REF],
)
loss_scaled = var(
    "opt.loss_scale.loss_scaled", "L_scaled_opt", "value",
    "Scaled loss.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[LOSS_SCALING_REF],
)
loss_scale = var(
    "opt.loss_scale.scale", "S_loss_opt", "dimensionless",
    "Current loss scale.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[LOSS_SCALING_REF],
)
grad_scaled = var(
    "opt.loss_scale.grad_scaled", "g_scaled_opt", "grad",
    "Gradient observed in the scaled-loss backward pass.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[LOSS_SCALING_REF],
)
grad_unscaled = var(
    "opt.loss_scale.grad_unscaled", "g_unscaled_opt", "grad",
    "Gradient after dividing by the loss scale.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[LOSS_SCALING_REF],
)
overflow_count = var(
    "opt.loss_scale.overflow_count", "N_overflow_opt", "events",
    "Gradient overflow events seen at the current step.",
    scope="optimizer",
    positive=False,
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[LOSS_SCALING_REF],
)
stable_steps_since_overflow = var(
    "opt.loss_scale.stable_steps_since_overflow", "N_stable_ls_opt", "steps",
    "Consecutive stable steps since the last overflow.",
    scope="optimizer",
    positive=False,
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[LOSS_SCALING_REF],
)
loss_scale_growth_factor = var(
    "opt.loss_scale.growth_factor", "r_ls_growth_opt", "dimensionless",
    "Multiplicative growth factor for dynamic loss scaling.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[LOSS_SCALING_REF],
)
loss_scale_next = var(
    "opt.loss_scale.scale_next", "S_loss_next_opt", "dimensionless",
    "Loss scale chosen for the next step.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[LOSS_SCALING_REF],
)


eq_loss_scaled = eq(
    "opt.eq.loss_scaled",
    loss_scaled.symbol,
    loss_unscaled.symbol * loss_scale.symbol,
    "Scaling the loss scales every gradient in the backward pass by the same factor.",
    references=[LOSS_SCALING_REF],
    check_units=True,
)

eq_grad_unscaled = eq(
    "opt.eq.grad_unscaled",
    grad_unscaled.symbol,
    grad_scaled.symbol / loss_scale.symbol,
    "Unscaling divides the gradient by the loss scale before the optimizer update.",
    references=[LOSS_SCALING_REF],
    check_units=True,
)

eq_loss_scale_next = PiecewiseEquation(
    "opt.eq.loss_scale_next",
    loss_scale_next.symbol,
    pieces=[
        (loss_scale.symbol / loss_scale_growth_factor.symbol, overflow_count.symbol > 0),
        (loss_scale.symbol * loss_scale_growth_factor.symbol, stable_steps_since_overflow.symbol >= loss_scale_growth_interval.symbol),
        (loss_scale.symbol, True),
    ],
    description="Dynamic loss scaling shrinks on overflow, grows after a sufficiently long stable streak, and otherwise holds steady.",
    references=[LOSS_SCALING_REF],
)


OPT_LOSS_SCALING_VARIABLES = [
    loss_scale_growth_interval,
    loss_unscaled, loss_scaled, loss_scale, grad_scaled, grad_unscaled,
    overflow_count, stable_steps_since_overflow, loss_scale_growth_factor,
    loss_scale_next,
]

OPT_LOSS_SCALING_EQUATIONS = [
    eq_loss_scaled,
    eq_grad_unscaled,
    eq_loss_scale_next,
]


__all__ = [
    "loss_scale_growth_interval",
    "loss_unscaled", "loss_scaled", "loss_scale",
    "grad_scaled", "grad_unscaled",
    "overflow_count", "stable_steps_since_overflow",
    "loss_scale_growth_factor", "loss_scale_next",
    "eq_loss_scaled", "eq_grad_unscaled", "eq_loss_scale_next",
    "OPT_LOSS_SCALING_VARIABLES", "OPT_LOSS_SCALING_EQUATIONS",
]
