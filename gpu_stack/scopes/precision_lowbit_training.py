"""
scopes/precision_lowbit_training.py
===================================

Loss scaling and underflow avoidance declarations.
"""

from ..core import eq, var
from .precision_ieee import min_normal
from .precision_lowbit_common import (
    DIMENSIONLESS,
    LOSS_SCALING_REF,
    _annotate_variables,
)


grad_min_magnitude = var(
    "precision.loss_scaling.grad_min_magnitude", "g_min_ls", "value",
    "Smallest gradient magnitude worth preserving during low-precision training.",
    scope="precision",
)
loss_scale = var(
    "precision.loss_scaling.scale", "S_loss_ls", "dimensionless",
    "Loss-scaling multiplier.",
    scope="precision",
)
scaled_grad_min = var(
    "precision.loss_scaling.scaled_grad_min", "g_min_scaled_ls", "value",
    "Minimum preserved gradient magnitude after scaling.",
    scope="precision",
)
min_loss_scale_safe = var(
    "precision.loss_scaling.min_safe_scale", "S_loss_safe_ls", "dimensionless",
    "Minimum loss scale that lifts the target gradient above the normal underflow floor.",
    scope="precision",
)
grad_scaled = var(
    "precision.loss_scaling.grad_scaled", "g_scaled_ls", "value",
    "Gradient after multiplying the loss by the current scale.",
    scope="precision",
)
grad_unscaled = var(
    "precision.loss_scaling.grad_unscaled", "g_unscaled_ls", "value",
    "Gradient after dividing by the loss scale before the optimizer step.",
    scope="precision",
)

_annotate_variables(
    (
        grad_min_magnitude,
        loss_scale,
        scaled_grad_min,
        min_loss_scale_safe,
        grad_scaled,
        grad_unscaled,
    ),
    DIMENSIONLESS,
    [LOSS_SCALING_REF],
)


eq_scaled_grad_min = eq(
    "precision.eq.scaled_grad_min",
    scaled_grad_min.symbol,
    loss_scale.symbol * grad_min_magnitude.symbol,
    "Scaling the loss scales the backward gradient by the same factor.",
    references=[LOSS_SCALING_REF],
    check_units=True,
)

eq_min_loss_scale_safe = eq(
    "precision.eq.min_loss_scale_safe",
    min_loss_scale_safe.symbol,
    min_normal.symbol / grad_min_magnitude.symbol,
    "Minimum safe loss scale is the normal underflow threshold divided by the smallest gradient magnitude worth retaining.",
    references=[LOSS_SCALING_REF],
    check_units=True,
)

eq_grad_unscaled = eq(
    "precision.eq.grad_unscaled",
    grad_unscaled.symbol,
    grad_scaled.symbol / loss_scale.symbol,
    "Unscaling divides the accumulated low-precision gradient by the loss scale before the optimizer update.",
    references=[LOSS_SCALING_REF],
    check_units=True,
)


PRECISION_LOWBIT_TRAINING_VARIABLES = (
    grad_min_magnitude,
    loss_scale,
    scaled_grad_min,
    min_loss_scale_safe,
    grad_scaled,
    grad_unscaled,
)

PRECISION_LOWBIT_TRAINING_EQUATIONS = (
    eq_scaled_grad_min,
    eq_min_loss_scale_safe,
    eq_grad_unscaled,
)


__all__ = [
    "grad_min_magnitude",
    "loss_scale",
    "scaled_grad_min",
    "min_loss_scale_safe",
    "grad_scaled",
    "grad_unscaled",
    "eq_scaled_grad_min",
    "eq_min_loss_scale_safe",
    "eq_grad_unscaled",
]
