"""
scopes/optimizer_schedules.py
=============================

Learning-rate schedules.

This helper covers linear warmup, cosine decay after warmup, inverse
square-root decay, and warmup-stable-decay (WSD).
"""

import sympy as sp
from ..core import PiecewiseEquation, eq, var

from .optimizer_first_order import t_step


# ---------------------------------------------------------------------------
# Learning-rate schedules
# ---------------------------------------------------------------------------

lr_base = var(
    "opt.schedule.lr_base", "eta_base_opt", "dimensionless",
    "Base learning rate before schedule multipliers.",
    scope="optimizer",
)
warmup_steps = var(
    "opt.schedule.warmup_steps", "N_warm_opt", "steps",
    "Warmup steps.",
    scope="optimizer",
    integer=True,
)
schedule_total_steps = var(
    "opt.schedule.total_steps", "N_sched_total_opt", "steps",
    "Total scheduled steps.",
    scope="optimizer",
    integer=True,
)
wsd_stable_steps = var(
    "opt.schedule.wsd_stable_steps", "N_wsd_stable_opt", "steps",
    "Stable plateau steps in a warmup-stable-decay schedule.",
    scope="optimizer",
    integer=True,
)
lr_warmup = var(
    "opt.schedule.lr_warmup", "eta_warm_opt", "dimensionless",
    "Learning rate under linear warmup.",
    scope="optimizer",
)
lr_cosine = var(
    "opt.schedule.lr_cosine", "eta_cos_opt", "dimensionless",
    "Learning rate under warmup followed by cosine decay.",
    scope="optimizer",
)
lr_inv_sqrt = var(
    "opt.schedule.lr_inv_sqrt", "eta_isqrt_opt", "dimensionless",
    "Learning rate under inverse-square-root decay.",
    scope="optimizer",
)
lr_wsd = var(
    "opt.schedule.lr_wsd", "eta_wsd_opt", "dimensionless",
    "Learning rate under warmup-stable-decay.",
    scope="optimizer",
)


eq_lr_warmup = eq(
    "opt.eq.lr_warmup",
    lr_warmup.symbol,
    lr_base.symbol * sp.Min(1, t_step.symbol / warmup_steps.symbol),
    "Linear warmup ramps linearly to the base learning rate and then stays there.",
)

eq_lr_cosine = PiecewiseEquation(
    "opt.eq.lr_cosine",
    lr_cosine.symbol,
    pieces=[
        (lr_base.symbol * t_step.symbol / warmup_steps.symbol, t_step.symbol <= warmup_steps.symbol),
        (lr_base.symbol * (1 + sp.cos(sp.pi * (t_step.symbol - warmup_steps.symbol) / (schedule_total_steps.symbol - warmup_steps.symbol))) / 2, True),
    ],
    description="Cosine decay uses linear warmup followed by a half-cosine decay to zero.",
)

eq_lr_inv_sqrt = eq(
    "opt.eq.lr_inv_sqrt",
    lr_inv_sqrt.symbol,
    lr_base.symbol * sp.Min(1, t_step.symbol / warmup_steps.symbol) / sp.sqrt(sp.Max(1, t_step.symbol / warmup_steps.symbol)),
    "Inverse-square-root decay warms up linearly and then falls as 1/sqrt(t).",
)

eq_lr_wsd = PiecewiseEquation(
    "opt.eq.lr_wsd",
    lr_wsd.symbol,
    pieces=[
        (lr_base.symbol * t_step.symbol / warmup_steps.symbol, t_step.symbol <= warmup_steps.symbol),
        (lr_base.symbol, t_step.symbol <= warmup_steps.symbol + wsd_stable_steps.symbol),
        (lr_base.symbol * (schedule_total_steps.symbol - t_step.symbol) / (schedule_total_steps.symbol - warmup_steps.symbol - wsd_stable_steps.symbol), True),
    ],
    description="Warmup-stable-decay uses linear warmup, a flat plateau, and then a linear tail to zero.",
)


OPT_SCHEDULES_VARIABLES = [
    lr_base, warmup_steps, schedule_total_steps, wsd_stable_steps,
    lr_warmup, lr_cosine, lr_inv_sqrt, lr_wsd,
]

OPT_SCHEDULES_EQUATIONS = [
    eq_lr_warmup,
    eq_lr_cosine,
    eq_lr_inv_sqrt,
    eq_lr_wsd,
]


__all__ = [
    "lr_base", "warmup_steps", "schedule_total_steps", "wsd_stable_steps",
    "lr_warmup", "lr_cosine", "lr_inv_sqrt", "lr_wsd",
    "eq_lr_warmup", "eq_lr_cosine", "eq_lr_inv_sqrt", "eq_lr_wsd",
    "OPT_SCHEDULES_VARIABLES", "OPT_SCHEDULES_EQUATIONS",
]
