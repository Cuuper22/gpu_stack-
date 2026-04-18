"""
scopes/training_overheads.py
============================

Training overheads.

Pipeline-bubble, straggler, restart, and evaluation overhead fractions,
nominal step time as the sum of compute, exposed communication, and
memory-bound auxiliary time, and the availability-adjusted step time.
"""

from ..core import eq, var
from .parallelism import bubble_1f1b
from .training_compute import T_compute, T_exposed_comm, T_mem_bound, T_step


# ---------------------------------------------------------------------------
# Bubbles and overhead fractions
# ---------------------------------------------------------------------------

T_step_nominal = var(
    "training.t_step_nominal", "T_step_nom", "s",
    "Nominal step time before bubble and availability penalties are applied.",
    scope="training",
)
T_bubbles = var(
    "training.t_bubbles", "T_bub", "s",
    "Time lost to pipeline bubbles, stragglers, retries, and evaluation overhead.",
    scope="training",
)
pipeline_bubble_fraction = var(
    "training.pipeline_bubble_fraction", "phi_pipe_train", "dimensionless",
    "Fractional pipeline bubble penalty applied to the nominal step time.",
    scope="training",
)
straggler_fraction = var(
    "training.straggler_fraction", "phi_strag_train", "dimensionless",
    "Fractional step-time penalty from stragglers, imbalance, or transient slow nodes.",
    scope="training",
)
restart_fraction = var(
    "training.restart_fraction", "phi_restart_train", "dimensionless",
    "Fractional step-time penalty from retries, restarts, or checkpoint restore overhead.",
    scope="training",
)
eval_fraction = var(
    "training.eval_fraction", "phi_eval_train", "dimensionless",
    "Fractional step-time penalty from evaluation or validation interleaves.",
    scope="training",
)
overhead_fraction = var(
    "training.overhead_fraction", "phi_over_train", "dimensionless",
    "Total non-nominal fractional overhead added on top of the compute, communication, and memory-bound baseline.",
    scope="training",
)

eq_pipeline_bubble_fraction = eq(
    "training.eq.pipeline_bubble_fraction",
    pipeline_bubble_fraction.symbol,
    bubble_1f1b.symbol,
    "By default the training scope uses the lower-scope 1F1B bubble fraction as its pipeline bubble term.",
)
eq_overhead_fraction = eq(
    "training.eq.overhead_fraction",
    overhead_fraction.symbol,
    pipeline_bubble_fraction.symbol + straggler_fraction.symbol + restart_fraction.symbol + eval_fraction.symbol,
    "Total overhead fraction adds pipeline bubbles, stragglers, restarts, and evaluation overhead.",
)
eq_t_step_nominal = eq(
    "training.eq.t_step_nominal",
    T_step_nominal.symbol,
    T_compute.symbol + T_exposed_comm.symbol + T_mem_bound.symbol,
    "Nominal step time adds executed compute, exposed communication, and auxiliary memory-bound time.",
)
eq_t_bubbles = eq(
    "training.eq.t_bubbles",
    T_bubbles.symbol,
    T_step_nominal.symbol * overhead_fraction.symbol,
    "Bubble and overhead time is modeled as a fractional expansion of the nominal step time.",
)
eq_t_step = eq(
    "training.eq.t_step",
    T_step.symbol,
    T_step_nominal.symbol + T_bubbles.symbol,
    "Full step time equals nominal step time plus bubble and overhead penalties.",
)


TRAINING_OVERHEADS_VARIABLES = (
    T_step_nominal,
    T_bubbles,
    pipeline_bubble_fraction,
    straggler_fraction,
    restart_fraction,
    eval_fraction,
    overhead_fraction,
)

TRAINING_OVERHEADS_EQUATIONS = (
    eq_pipeline_bubble_fraction,
    eq_overhead_fraction,
    eq_t_step_nominal,
    eq_t_bubbles,
    eq_t_step,
)


__all__ = [
    "T_step_nominal",
    "T_bubbles",
    "pipeline_bubble_fraction",
    "straggler_fraction",
    "restart_fraction",
    "eval_fraction",
    "overhead_fraction",
    "eq_pipeline_bubble_fraction",
    "eq_overhead_fraction",
    "eq_t_step_nominal",
    "eq_t_bubbles",
    "eq_t_step",
    "TRAINING_OVERHEADS_VARIABLES",
    "TRAINING_OVERHEADS_EQUATIONS",
]
