"""
scopes/power_forecast_checkpoint.py
===================================

What an early warning of an outage is worth in GPU-hours.

A training job that loses power, cooling, or a node falls back to its last
checkpoint. A fault with no warning arrives at a random point in the
checkpoint interval, so on average half an interval of work on every affected
GPU is lost (Young 1974). A forecast that warns of the fault with a lead time
at least as long as one checkpoint write lets the job checkpoint first, so
only about one write time of work is lost. The forecast does not catch every
fault: recall is the fraction it warns about in time. The expected loss per
fault weights the two cases by recall, and the GPU-hours saved per fault are
the difference from the no-warning loss.

The checkpoint interval and checkpoint write time are the cluster
reliability scope's variables. The warning lead time, recall, and the number
of GPUs a fault takes down are root inputs; lead time and recall come from the
Heatwave experiment's replays and have no default here.
"""

import sympy as sp

from ..core import Inequality, eq
from ..core.units import HOUR, SECOND

from .cluster_reliability import checkpoint_time, optimal_checkpoint_interval
from .power_forecast_refs import (
    forecast_var,
    DALY_2006_REF,
    E003_INPUT_REF,
    EARLY_CHECKPOINT_MODEL_REF,
    YOUNG_1974_REF,
)


DIMENSIONLESS = sp.Integer(1)

CHECKPOINT_REFS = [EARLY_CHECKPOINT_MODEL_REF, YOUNG_1974_REF, DALY_2006_REF]
CHECKPOINT_INPUT_REFS = [EARLY_CHECKPOINT_MODEL_REF, E003_INPUT_REF]


# ---------------------------------------------------------------------------
# Root inputs: job size, warning lead time, recall
# ---------------------------------------------------------------------------

gpus_affected = forecast_var(
    "forecast.ckpt.gpus_affected", "N_aff_fc", "GPUs",
    "GPUs whose job loses progress when one fault occurs (the size of the "
    "affected job or domain). It can equal the cluster GPU count.",
    CHECKPOINT_REFS,
    positive=True,
    sp_units=DIMENSIONLESS,
)
warning_lead_time = forecast_var(
    "forecast.ckpt.lead_time", "L_warn_fc", "s",
    "Lead time of the forecast warning: how long before the fault the "
    "forecast raises the alarm. The model needs it to be at least the "
    "checkpoint write time.",
    CHECKPOINT_INPUT_REFS,
    positive=True,
    sp_units=SECOND,
)
warning_recall = forecast_var(
    "forecast.ckpt.recall", "r_warn_fc", "dimensionless",
    "Forecast recall: the fraction of faults warned about with at least the "
    "stated lead time. Measure it from replays; the scope sets no default.",
    CHECKPOINT_INPUT_REFS,
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
)


# ---------------------------------------------------------------------------
# Derived: lost work with and without warning, expected loss, savings
# ---------------------------------------------------------------------------

lost_work_unwarned = forecast_var(
    "forecast.ckpt.lost_work_unwarned", "W_lost0_fc", "GPU*h",
    "Expected work lost per fault with no warning, in GPU-hours: half a "
    "checkpoint interval on every affected GPU.",
    CHECKPOINT_REFS,
    nonnegative=True,
    sp_units=HOUR,
)
lost_work_warned = forecast_var(
    "forecast.ckpt.lost_work_warned", "W_lostw_fc", "GPU*h",
    "Work lost per fault when the warning lead time covers a checkpoint "
    "write, in GPU-hours: one checkpoint write time on every affected GPU.",
    CHECKPOINT_REFS,
    nonnegative=True,
    sp_units=HOUR,
)
lost_work_expected = forecast_var(
    "forecast.ckpt.lost_work_expected", "W_lostx_fc", "GPU*h",
    "Expected work lost per fault with the forecast in place: the warned "
    "loss with probability recall, the unwarned loss otherwise.",
    CHECKPOINT_REFS,
    nonnegative=True,
    sp_units=HOUR,
)
gpu_hours_saved = forecast_var(
    "forecast.ckpt.gpu_hours_saved", "S_gpuh_fc", "GPU*h",
    "Expected GPU-hours saved per fault: unwarned loss minus expected loss "
    "with the forecast.",
    CHECKPOINT_REFS,
    signed=True,
    sp_units=HOUR,
)


# ---------------------------------------------------------------------------
# Equations
# ---------------------------------------------------------------------------

eq_lost_work_unwarned = eq(
    "forecast.eq.ckpt.lost_work_unwarned",
    lost_work_unwarned.symbol,
    sp.Rational(1, 2) * optimal_checkpoint_interval.symbol
    * gpus_affected.symbol / sp.Integer(3600),
    "Without warning, a fault loses half a checkpoint interval of work on "
    "every affected GPU, converted from GPU-seconds to GPU-hours.",
    references=CHECKPOINT_REFS,
    check_units=True,
)
eq_lost_work_warned = eq(
    "forecast.eq.ckpt.lost_work_warned",
    lost_work_warned.symbol,
    checkpoint_time.symbol * gpus_affected.symbol / sp.Integer(3600),
    "With a warning at least one write long, a fault loses about one "
    "checkpoint write time of work on every affected GPU, converted from "
    "GPU-seconds to GPU-hours.",
    references=CHECKPOINT_REFS,
    check_units=True,
)
eq_lost_work_expected = eq(
    "forecast.eq.ckpt.lost_work_expected",
    lost_work_expected.symbol,
    warning_recall.symbol * lost_work_warned.symbol
    + (1 - warning_recall.symbol) * lost_work_unwarned.symbol,
    "Expected loss weights the warned and unwarned losses by forecast recall.",
    references=CHECKPOINT_REFS,
    check_units=True,
)
eq_gpu_hours_saved = eq(
    "forecast.eq.ckpt.gpu_hours_saved",
    gpu_hours_saved.symbol,
    lost_work_unwarned.symbol - lost_work_expected.symbol,
    "GPU-hours saved per fault equal the unwarned loss minus the expected loss with the forecast.",
    references=CHECKPOINT_REFS,
    check_units=True,
)

ineq_lead_time_covers_checkpoint = Inequality(
    "forecast.ineq.ckpt.lead_time_covers_checkpoint",
    warning_lead_time.symbol,
    checkpoint_time.symbol,
    ">=",
    "The warning lead time must be at least the checkpoint write time, "
    "otherwise the job cannot finish a checkpoint before the fault.",
    references=CHECKPOINT_REFS,
)


POWER_FORECAST_CHECKPOINT_VARIABLES = [
    gpus_affected,
    warning_lead_time,
    warning_recall,
    lost_work_unwarned,
    lost_work_warned,
    lost_work_expected,
    gpu_hours_saved,
]

POWER_FORECAST_CHECKPOINT_EQUATIONS = [
    eq_lost_work_unwarned,
    eq_lost_work_warned,
    eq_lost_work_expected,
    eq_gpu_hours_saved,
    ineq_lead_time_covers_checkpoint,
]


__all__ = [
    "gpus_affected", "warning_lead_time", "warning_recall",
    "lost_work_unwarned", "lost_work_warned", "lost_work_expected",
    "gpu_hours_saved",
    "eq_lost_work_unwarned", "eq_lost_work_warned", "eq_lost_work_expected",
    "eq_gpu_hours_saved", "ineq_lead_time_covers_checkpoint",
    "POWER_FORECAST_CHECKPOINT_VARIABLES",
    "POWER_FORECAST_CHECKPOINT_EQUATIONS",
]
