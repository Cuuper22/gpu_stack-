"""
scopes/training_overheads.py
============================

The taxes on a training step. The nominal step time is the sum of
compute, exposed communication, and memory-bound time -- but real steps
pay more: pipeline bubbles (idle ramp-in and ramp-out stages of pipeline
parallelism), stragglers, restarts after failures, and evaluation pauses.
Each is a fraction; together they form the overhead fraction that inflates
the nominal step time into the availability-adjusted step time the wall
clock is built on.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import SECOND
from .parallelism import bubble_1f1b
from .training_compute import T_compute, T_exposed_comm, T_mem_bound, T_step


DIMENSIONLESS = sp.Integer(1)

TRAINING_OVERHEADS_REF = Reference(
    "Training overhead accounting expands nominal compute, communication, "
    "and memory-bound step time by pipeline bubbles, stragglers, restarts, "
    "and evaluation interleaves.",
    kind="model",
)

NARAYANAN_2021_REF = Reference(
    "Narayanan et al., Efficient Large-Scale Language Model Training on GPU "
    "Clusters Using Megatron-LM, SC21, Sec. 2.2: the 1F1B pipeline bubble "
    "adds (p-1)(t_f+t_b) to an ideal m(t_f+t_b), so the step-time "
    "multiplier is 1 + (p-1)/m.",
    kind="paper",
    url="https://arxiv.org/abs/2104.04473",
    year=2021,
    doi="10.1145/3458817.3476209",
)


# ---------------------------------------------------------------------------
# Overhead fractions: bubbles, stragglers, restarts, and eval inflate the nominal step time
# ---------------------------------------------------------------------------

T_step_nominal = var(
    "training.t_step_nominal", "T_step_nom", "s",
    "Nominal step time before bubble and availability penalties are applied.",
    scope="training",
    sp_units=SECOND,
    references=[TRAINING_OVERHEADS_REF],
)
T_bubbles = var(
    "training.t_bubbles", "T_bub", "s",
    "Time lost to pipeline bubbles, stragglers, retries, and evaluation overhead.",
    scope="training",
    sp_units=SECOND,
    references=[TRAINING_OVERHEADS_REF],
)
pipeline_bubble_fraction = var(
    "training.pipeline_bubble_fraction", "phi_pipe_train", "dimensionless",
    "Pipeline bubble time divided by nominal (bubble-free) step time, i.e. an overhead "
    "over nominal, equal to (p-1)/m for 1F1B. Not the bubble share of the total step.",
    scope="training",
    sp_units=DIMENSIONLESS,
    references=[TRAINING_OVERHEADS_REF, NARAYANAN_2021_REF],
)
straggler_fraction = var(
    "training.straggler_fraction", "phi_strag_train", "dimensionless",
    "Fractional step-time penalty from stragglers, imbalance, or transient slow nodes.",
    scope="training",
    sp_units=DIMENSIONLESS,
    references=[TRAINING_OVERHEADS_REF],
)
restart_fraction = var(
    "training.restart_fraction", "phi_restart_train", "dimensionless",
    "Fractional step-time penalty from retries, restarts, or checkpoint restore overhead.",
    scope="training",
    sp_units=DIMENSIONLESS,
    references=[TRAINING_OVERHEADS_REF],
)
eval_fraction = var(
    "training.eval_fraction", "phi_eval_train", "dimensionless",
    "Fractional step-time penalty from evaluation or validation interleaves.",
    scope="training",
    sp_units=DIMENSIONLESS,
    references=[TRAINING_OVERHEADS_REF],
)
overhead_fraction = var(
    "training.overhead_fraction", "phi_over_train", "dimensionless",
    "Total non-nominal overhead: extra time divided by nominal step time. Every term "
    "summed into it (pipeline, straggler, restart, eval) is an overhead over nominal, "
    "so step time is nominal * (1 + overhead_fraction).",
    scope="training",
    sp_units=DIMENSIONLESS,
    references=[TRAINING_OVERHEADS_REF],
)

eq_pipeline_bubble_fraction = eq(
    "training.eq.pipeline_bubble_fraction",
    pipeline_bubble_fraction.symbol,
    bubble_1f1b.symbol / (1 - bubble_1f1b.symbol),
    "The lower-scope 1F1B bubble is a share of the total step, phi = (p-1)/(p+m-1). "
    "Converting it to an overhead over nominal time gives phi/(1-phi) = (p-1)/m.",
    references=[TRAINING_OVERHEADS_REF, NARAYANAN_2021_REF],
    check_units=True,
)
eq_overhead_fraction = eq(
    "training.eq.overhead_fraction",
    overhead_fraction.symbol,
    pipeline_bubble_fraction.symbol + straggler_fraction.symbol + restart_fraction.symbol + eval_fraction.symbol,
    "Total overhead fraction adds pipeline bubbles, stragglers, restarts, and evaluation overhead.",
    references=[TRAINING_OVERHEADS_REF],
    check_units=True,
)
eq_t_step_nominal = eq(
    "training.eq.t_step_nominal",
    T_step_nominal.symbol,
    T_compute.symbol + T_exposed_comm.symbol + T_mem_bound.symbol,
    "Nominal step time adds executed compute, exposed communication, and auxiliary memory-bound time.",
    references=[TRAINING_OVERHEADS_REF],
    check_units=True,
)
eq_t_bubbles = eq(
    "training.eq.t_bubbles",
    T_bubbles.symbol,
    T_step_nominal.symbol * overhead_fraction.symbol,
    "Bubble and overhead time is modeled as a fractional expansion of the nominal step time.",
    references=[TRAINING_OVERHEADS_REF],
    check_units=True,
)
eq_t_step = eq(
    "training.eq.t_step",
    T_step.symbol,
    T_step_nominal.symbol + T_bubbles.symbol,
    "Full step time equals nominal step time plus bubble and overhead penalties.",
    references=[TRAINING_OVERHEADS_REF],
    check_units=True,
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
