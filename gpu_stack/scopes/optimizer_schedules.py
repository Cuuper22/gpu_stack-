"""
scopes/optimizer_schedules.py
=============================

Learning-rate schedules: how the step size changes over a run.

A fixed learning rate serves a long run badly — too hot for freshly
initialized weights, too coarse for a converged model — so the rate is a
function of the step index. All schedules here start with linear warmup, a
ramp from zero that protects the early steps. After warmup the paths
diverge: cosine decay glides smoothly down to zero over the declared
horizon; inverse-square-root decays without needing the total step count
in advance; and warmup-stable-decay (WSD) holds the rate flat through a
long stable phase and only decays at the end, which lets one run branch
into checkpoints of different lengths. Inequalities pin the horizon
bookkeeping — total steps must exceed warmup, and warmup plus stable, and
reach the current step.
"""

import sympy as sp
from ..core import Inequality, PiecewiseEquation, Reference, eq, var

from .optimizer_first_order import t_step


DIMENSIONLESS = sp.Integer(1)

OPT_SCHEDULE_REF = Reference(
    "Optimizer learning-rate schedules are dimensionless multipliers over "
    "a dimensionless optimizer step index and explicit finite horizons.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Learning-rate schedules
# ---------------------------------------------------------------------------

lr_base = var(
    "opt.schedule.lr_base", "eta_base_opt", "dimensionless",
    "Base learning rate before schedule multipliers.",
    scope="optimizer",
    nonnegative=True,
    sp_units=DIMENSIONLESS,
    references=[OPT_SCHEDULE_REF],
)
warmup_steps = var(
    "opt.schedule.warmup_steps", "N_warm_opt", "steps",
    "Warmup steps.",
    scope="optimizer",
    integer=True,
    positive=True,
    sp_units=DIMENSIONLESS,
    references=[OPT_SCHEDULE_REF],
)
schedule_total_steps = var(
    "opt.schedule.total_steps", "N_sched_total_opt", "steps",
    "Total scheduled steps.",
    scope="optimizer",
    integer=True,
    positive=True,
    sp_units=DIMENSIONLESS,
    references=[OPT_SCHEDULE_REF],
)
wsd_stable_steps = var(
    "opt.schedule.wsd_stable_steps", "N_wsd_stable_opt", "steps",
    "Stable plateau steps in a warmup-stable-decay schedule.",
    scope="optimizer",
    integer=True,
    nonnegative=True,
    sp_units=DIMENSIONLESS,
    references=[OPT_SCHEDULE_REF],
)
lr_warmup = var(
    "opt.schedule.lr_warmup", "eta_warm_opt", "dimensionless",
    "Learning rate under linear warmup.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[OPT_SCHEDULE_REF],
)
lr_cosine = var(
    "opt.schedule.lr_cosine", "eta_cos_opt", "dimensionless",
    "Learning rate under warmup followed by cosine decay.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[OPT_SCHEDULE_REF],
)
lr_inv_sqrt = var(
    "opt.schedule.lr_inv_sqrt", "eta_isqrt_opt", "dimensionless",
    "Learning rate under inverse-square-root decay.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[OPT_SCHEDULE_REF],
)
lr_wsd = var(
    "opt.schedule.lr_wsd", "eta_wsd_opt", "dimensionless",
    "Learning rate under warmup-stable-decay.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[OPT_SCHEDULE_REF],
)


eq_lr_warmup = eq(
    "opt.eq.lr_warmup",
    lr_warmup.symbol,
    lr_base.symbol * sp.Min(1, t_step.symbol / warmup_steps.symbol),
    "Linear warmup ramps linearly to the base learning rate and then stays there.",
    references=[OPT_SCHEDULE_REF],
    check_units=True,
)

eq_lr_cosine = PiecewiseEquation(
    "opt.eq.lr_cosine",
    lr_cosine.symbol,
    pieces=[
        (lr_base.symbol * t_step.symbol / warmup_steps.symbol, t_step.symbol <= warmup_steps.symbol),
        (lr_base.symbol * (1 + sp.cos(sp.pi * (t_step.symbol - warmup_steps.symbol) / (schedule_total_steps.symbol - warmup_steps.symbol))) / 2, True),
    ],
    description="Cosine decay uses linear warmup followed by a half-cosine decay to zero.",
    references=[OPT_SCHEDULE_REF],
)

eq_lr_inv_sqrt = eq(
    "opt.eq.lr_inv_sqrt",
    lr_inv_sqrt.symbol,
    lr_base.symbol * sp.Min(1, t_step.symbol / warmup_steps.symbol) / sp.sqrt(sp.Max(1, t_step.symbol / warmup_steps.symbol)),
    "Inverse-square-root decay warms up linearly and then falls as 1/sqrt(t).",
    references=[OPT_SCHEDULE_REF],
    check_units=True,
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
    references=[OPT_SCHEDULE_REF],
)


ineq_schedule_total_steps_exceeds_warmup_steps = Inequality(
    "opt.ineq.schedule_total_steps_exceeds_warmup_steps",
    schedule_total_steps.symbol,
    warmup_steps.symbol,
    ">",
    "A scheduled decay interval needs total steps strictly greater than warmup steps.",
    references=[OPT_SCHEDULE_REF],
)

ineq_schedule_total_steps_exceeds_warmup_and_stable_steps = Inequality(
    "opt.ineq.schedule_total_steps_exceeds_warmup_and_stable_steps",
    schedule_total_steps.symbol,
    warmup_steps.symbol + wsd_stable_steps.symbol,
    ">",
    "A WSD tail needs total steps strictly greater than warmup plus stable steps.",
    references=[OPT_SCHEDULE_REF],
)

ineq_schedule_total_steps_reaches_current_step = Inequality(
    "opt.ineq.schedule_total_steps_reaches_current_step",
    schedule_total_steps.symbol,
    t_step.symbol,
    ">=",
    "A schedule is only valid while the current optimizer step is within its total horizon.",
    references=[OPT_SCHEDULE_REF],
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
    ineq_schedule_total_steps_exceeds_warmup_steps,
    ineq_schedule_total_steps_exceeds_warmup_and_stable_steps,
    ineq_schedule_total_steps_reaches_current_step,
]


__all__ = [
    "lr_base", "warmup_steps", "schedule_total_steps", "wsd_stable_steps",
    "lr_warmup", "lr_cosine", "lr_inv_sqrt", "lr_wsd",
    "eq_lr_warmup", "eq_lr_cosine", "eq_lr_inv_sqrt", "eq_lr_wsd",
    "ineq_schedule_total_steps_exceeds_warmup_steps",
    "ineq_schedule_total_steps_exceeds_warmup_and_stable_steps",
    "ineq_schedule_total_steps_reaches_current_step",
    "OPT_SCHEDULES_VARIABLES", "OPT_SCHEDULES_EQUATIONS",
]
