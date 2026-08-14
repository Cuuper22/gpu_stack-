"""
scopes/training_scaling.py
==========================

From step time to run-level answers: throughput, energy, wall clock, and
model sizing. Tokens per second follow from tokens per step over step
time; IT power turns that into energy per step, energy per token, and
tokens per joule. Total tokens over tokens per step gives the step count,
and steps times step time gives the nominal wall clock, stretched by
cluster availability into the real one. The Chinchilla-style
tokens-per-parameter ratio ties dataset size to model size, with dense and
active-MoE specializations of the scaling parameter count.
"""

import sympy as sp

from ..core import Reference, RelationRole, eq, var
from ..core.units import JOULE, SECOND, WATT
from .architecture import (
    n_tokens_step,
    params_active_moe,
    params_dense_total,
)
from .gpu import p_gpu_total
from .parallelism import n_gpus_total
from .training_compute import T_step


DIMENSIONLESS = sp.Integer(1)

TRAINING_SCALING_REF = Reference(
    "Training scaling accounting connects step throughput, IT energy, "
    "token budget, wall clock, availability, and Chinchilla-style "
    "tokens-per-parameter ratios.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Throughput, energy, and full-run wall clock
# ---------------------------------------------------------------------------

tokens_per_sec = var(
    "training.tokens_per_sec", "TPS", "tokens/s",
    "Aggregate training throughput in tokens per second.",
    scope="training",
    sp_units=1 / SECOND,
    references=[TRAINING_SCALING_REF],
)
run_power_it = var(
    "training.run_power_it", "P_run_IT_train", "W",
    "IT power draw of the participating GPUs, excluding datacenter overhead such as PUE.",
    scope="training",
    sp_units=WATT,
    references=[TRAINING_SCALING_REF],
)
energy_per_step = var(
    "training.energy_per_step", "E_step_train", "J",
    "IT energy consumed by one training step.",
    scope="training",
    sp_units=JOULE,
    references=[TRAINING_SCALING_REF],
)
energy_per_token = var(
    "training.energy_per_token", "E_tok_train", "J/token",
    "IT energy consumed per training token.",
    scope="training",
    sp_units=JOULE,
    references=[TRAINING_SCALING_REF],
)
tokens_per_joule = var(
    "training.tokens_per_joule", "TPS_J_train", "tokens/J",
    "Training tokens delivered per joule of IT energy.",
    scope="training",
    sp_units=1 / JOULE,
    references=[TRAINING_SCALING_REF],
)
N_train_tokens = var(
    "training.total_tokens", "N_tok", "tokens",
    "Total training tokens to be consumed by the run.",
    scope="training",
    sp_units=DIMENSIONLESS,
    references=[TRAINING_SCALING_REF],
)
n_steps = var(
    "training.n_steps", "N_steps", "steps",
    "Optimizer-step count required to consume the training-token budget.",
    scope="training",
    sp_units=DIMENSIONLESS,
    references=[TRAINING_SCALING_REF],
)
wallclock_nominal = var(
    "training.wallclock_nominal", "T_wc_nom_train", "s",
    "Total wall clock with modeled per-step time but before cluster-availability penalties.",
    scope="training",
    sp_units=SECOND,
    references=[TRAINING_SCALING_REF],
)
cluster_availability = var(
    "training.cluster_availability", "rho_avail_train", "dimensionless",
    "Fraction of nominal training time during which the cluster actually makes forward progress.",
    scope="training",
    sp_units=DIMENSIONLESS,
    references=[TRAINING_SCALING_REF],
)
T_wallclock = var(
    "training.wallclock", "T_wc", "s",
    "Total wall-clock time of the training run after availability penalties.",
    scope="training",
    sp_units=SECOND,
    references=[TRAINING_SCALING_REF],
)

eq_tokens_per_sec = eq(
    "training.eq.tokens_per_sec",
    tokens_per_sec.symbol,
    n_tokens_step.symbol / T_step.symbol,
    "Tokens per second equal tokens per step divided by step time.",
    references=[TRAINING_SCALING_REF],
    check_units=True,
)
eq_run_power_it = eq(
    "training.eq.run_power_it",
    run_power_it.symbol,
    n_gpus_total.symbol * p_gpu_total.symbol,
    "IT run power equals GPU count times per-GPU package power.",
    references=[TRAINING_SCALING_REF],
    check_units=True,
)
eq_energy_per_step = eq(
    "training.eq.energy_per_step",
    energy_per_step.symbol,
    run_power_it.symbol * T_step.symbol,
    "Energy per step equals IT power times step time.",
    references=[TRAINING_SCALING_REF],
    check_units=True,
)
eq_energy_per_token = eq(
    "training.eq.energy_per_token",
    energy_per_token.symbol,
    energy_per_step.symbol / n_tokens_step.symbol,
    "Energy per token equals step energy divided by tokens per step.",
    references=[TRAINING_SCALING_REF],
    check_units=True,
)
eq_tokens_per_joule = eq(
    "training.eq.tokens_per_joule",
    tokens_per_joule.symbol,
    n_tokens_step.symbol / energy_per_step.symbol,
    "Tokens per joule equal tokens per step divided by step energy.",
    references=[TRAINING_SCALING_REF],
    check_units=True,
)
eq_n_steps = eq(
    "training.eq.n_steps",
    n_steps.symbol,
    N_train_tokens.symbol / n_tokens_step.symbol,
    "Optimizer-step count equals total tokens divided by tokens per step.",
    references=[TRAINING_SCALING_REF],
    check_units=True,
)
eq_wallclock_nominal = eq(
    "training.eq.wallclock_nominal",
    wallclock_nominal.symbol,
    n_steps.symbol * T_step.symbol,
    "Nominal wall clock equals step count times step time.",
    references=[TRAINING_SCALING_REF],
    check_units=True,
)
eq_wallclock = eq(
    "training.eq.wallclock",
    T_wallclock.symbol,
    wallclock_nominal.symbol / cluster_availability.symbol,
    "Actual wall clock divides nominal wall clock by cluster availability.",
    references=[TRAINING_SCALING_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Chinchilla-style scaling variables
# ---------------------------------------------------------------------------

chinchilla_ratio = var(
    "training.chinchilla_ratio", "r_Ch", "tokens/param",
    "Target tokens-per-parameter ratio used as a scaling-law design variable.",
    scope="training",
    sp_units=DIMENSIONLESS,
    references=[TRAINING_SCALING_REF],
)
scaling_params = var(
    "training.scaling_params", "P_scale_train", "params",
    "Parameter count used for scaling-law reasoning. Dense and active-MoE alternatives are both wired in.",
    scope="training",
    sp_units=DIMENSIONLESS,
    references=[TRAINING_SCALING_REF],
)
chinchilla_ratio_actual = var(
    "training.chinchilla_ratio_actual", "r_Ch_act_train", "tokens/param",
    "Actual tokens-per-parameter ratio implied by the modeled run.",
    scope="training",
    sp_units=DIMENSIONLESS,
    references=[TRAINING_SCALING_REF],
)
chinchilla_gap = var(
    "training.chinchilla_gap", "rho_Ch_gap_train", "dimensionless",
    "Actual Chinchilla ratio divided by target Chinchilla ratio.",
    scope="training",
    sp_units=DIMENSIONLESS,
    references=[TRAINING_SCALING_REF],
)

eq_scaling_params_dense = eq(
    "training.eq.scaling_params_dense",
    scaling_params.symbol,
    params_dense_total.symbol,
    "Dense scaling-parameter specialization: the dense total-parameter count.",
    references=[TRAINING_SCALING_REF],
    check_units=True,
    role=RelationRole.VARIANT,
    variant="dense",
)
eq_scaling_params_moe = eq(
    "training.eq.scaling_params_moe",
    scaling_params.symbol,
    params_active_moe.symbol,
    "MoE scaling-parameter specialization: the active-parameter count of an MoE model.",
    references=[TRAINING_SCALING_REF],
    check_units=True,
    role=RelationRole.VARIANT,
    variant="moe",
)
eq_chinchilla_ratio_actual = eq(
    "training.eq.chinchilla_ratio_actual",
    chinchilla_ratio_actual.symbol,
    N_train_tokens.symbol / scaling_params.symbol,
    "Actual tokens per parameter equal total training tokens divided by the scaling parameter count.",
    references=[TRAINING_SCALING_REF],
    check_units=True,
)
eq_chinchilla_gap = eq(
    "training.eq.chinchilla_gap",
    chinchilla_gap.symbol,
    chinchilla_ratio_actual.symbol / chinchilla_ratio.symbol,
    "Chinchilla gap equals actual tokens per parameter divided by the target ratio.",
    references=[TRAINING_SCALING_REF],
    check_units=True,
)


TRAINING_SCALING_VARIABLES = (
    tokens_per_sec,
    run_power_it,
    energy_per_step,
    energy_per_token,
    tokens_per_joule,
    N_train_tokens,
    n_steps,
    wallclock_nominal,
    cluster_availability,
    T_wallclock,
    chinchilla_ratio,
    scaling_params,
    chinchilla_ratio_actual,
    chinchilla_gap,
)

TRAINING_SCALING_EQUATIONS = (
    eq_tokens_per_sec,
    eq_run_power_it,
    eq_energy_per_step,
    eq_energy_per_token,
    eq_tokens_per_joule,
    eq_n_steps,
    eq_wallclock_nominal,
    eq_wallclock,
    eq_scaling_params_dense,
    eq_scaling_params_moe,
    eq_chinchilla_ratio_actual,
    eq_chinchilla_gap,
)


__all__ = [
    "tokens_per_sec",
    "run_power_it",
    "energy_per_step",
    "energy_per_token",
    "tokens_per_joule",
    "N_train_tokens",
    "n_steps",
    "wallclock_nominal",
    "cluster_availability",
    "T_wallclock",
    "chinchilla_ratio",
    "scaling_params",
    "chinchilla_ratio_actual",
    "chinchilla_gap",
    "eq_tokens_per_sec",
    "eq_run_power_it",
    "eq_energy_per_step",
    "eq_energy_per_token",
    "eq_tokens_per_joule",
    "eq_n_steps",
    "eq_wallclock_nominal",
    "eq_wallclock",
    "eq_scaling_params_dense",
    "eq_scaling_params_moe",
    "eq_chinchilla_ratio_actual",
    "eq_chinchilla_gap",
    "TRAINING_SCALING_VARIABLES",
    "TRAINING_SCALING_EQUATIONS",
]
