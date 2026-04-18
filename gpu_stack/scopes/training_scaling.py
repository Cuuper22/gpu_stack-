"""
scopes/training_scaling.py
==========================

Training throughput, energy, wall clock, and scaling-law variables.

Tokens per second, IT power and energy per step and per token, tokens per
joule, total step count, nominal and availability-adjusted wall clock,
and the Chinchilla-style tokens-per-parameter design variables including
the dense and active-MoE scaling-parameter specializations.
"""

from ..core import RelationRole, eq, var
from .architecture import (
    n_tokens_step,
    params_active_moe,
    params_dense_total,
)
from .gpu import p_gpu_total
from .parallelism import n_gpus_total
from .training_compute import T_step


# ---------------------------------------------------------------------------
# Throughput, energy, and full-run wall clock
# ---------------------------------------------------------------------------

tokens_per_sec = var(
    "training.tokens_per_sec", "TPS", "tokens/s",
    "Aggregate training throughput in tokens per second.",
    scope="training",
)
run_power_it = var(
    "training.run_power_it", "P_run_IT_train", "W",
    "IT power draw of the participating GPUs, excluding datacenter overhead such as PUE.",
    scope="training",
)
energy_per_step = var(
    "training.energy_per_step", "E_step_train", "J",
    "IT energy consumed by one training step.",
    scope="training",
)
energy_per_token = var(
    "training.energy_per_token", "E_tok_train", "J/token",
    "IT energy consumed per training token.",
    scope="training",
)
tokens_per_joule = var(
    "training.tokens_per_joule", "TPS_J_train", "tokens/J",
    "Training tokens delivered per joule of IT energy.",
    scope="training",
)
N_train_tokens = var(
    "training.total_tokens", "N_tok", "tokens",
    "Total training tokens to be consumed by the run.",
    scope="training",
)
n_steps = var(
    "training.n_steps", "N_steps", "steps",
    "Optimizer-step count required to consume the training-token budget.",
    scope="training",
)
wallclock_nominal = var(
    "training.wallclock_nominal", "T_wc_nom_train", "s",
    "Total wall clock with modeled per-step time but before cluster-availability penalties.",
    scope="training",
)
cluster_availability = var(
    "training.cluster_availability", "rho_avail_train", "dimensionless",
    "Fraction of nominal training time during which the cluster actually makes forward progress.",
    scope="training",
)
T_wallclock = var(
    "training.wallclock", "T_wc", "s",
    "Total wall-clock time of the training run after availability penalties.",
    scope="training",
)

eq_tokens_per_sec = eq(
    "training.eq.tokens_per_sec",
    tokens_per_sec.symbol,
    n_tokens_step.symbol / T_step.symbol,
    "Tokens per second equal tokens per step divided by step time.",
)
eq_run_power_it = eq(
    "training.eq.run_power_it",
    run_power_it.symbol,
    n_gpus_total.symbol * p_gpu_total.symbol,
    "IT run power equals GPU count times per-GPU package power.",
)
eq_energy_per_step = eq(
    "training.eq.energy_per_step",
    energy_per_step.symbol,
    run_power_it.symbol * T_step.symbol,
    "Energy per step equals IT power times step time.",
)
eq_energy_per_token = eq(
    "training.eq.energy_per_token",
    energy_per_token.symbol,
    energy_per_step.symbol / n_tokens_step.symbol,
    "Energy per token equals step energy divided by tokens per step.",
)
eq_tokens_per_joule = eq(
    "training.eq.tokens_per_joule",
    tokens_per_joule.symbol,
    n_tokens_step.symbol / energy_per_step.symbol,
    "Tokens per joule equal tokens per step divided by step energy.",
)
eq_n_steps = eq(
    "training.eq.n_steps",
    n_steps.symbol,
    N_train_tokens.symbol / n_tokens_step.symbol,
    "Optimizer-step count equals total tokens divided by tokens per step.",
)
eq_wallclock_nominal = eq(
    "training.eq.wallclock_nominal",
    wallclock_nominal.symbol,
    n_steps.symbol * T_step.symbol,
    "Nominal wall clock equals step count times step time.",
)
eq_wallclock = eq(
    "training.eq.wallclock",
    T_wallclock.symbol,
    wallclock_nominal.symbol / cluster_availability.symbol,
    "Actual wall clock divides nominal wall clock by cluster availability.",
)


# ---------------------------------------------------------------------------
# Chinchilla-style scaling variables
# ---------------------------------------------------------------------------

chinchilla_ratio = var(
    "training.chinchilla_ratio", "r_Ch", "tokens/param",
    "Target tokens-per-parameter ratio used as a scaling-law design variable.",
    scope="training",
)
scaling_params = var(
    "training.scaling_params", "P_scale_train", "params",
    "Parameter count used for scaling-law reasoning. Dense and active-MoE alternatives are both wired in.",
    scope="training",
)
chinchilla_ratio_actual = var(
    "training.chinchilla_ratio_actual", "r_Ch_act_train", "tokens/param",
    "Actual tokens-per-parameter ratio implied by the modeled run.",
    scope="training",
)
chinchilla_gap = var(
    "training.chinchilla_gap", "rho_Ch_gap_train", "dimensionless",
    "Actual Chinchilla ratio divided by target Chinchilla ratio.",
    scope="training",
)

eq_scaling_params_dense = eq(
    "training.eq.scaling_params_dense",
    scaling_params.symbol,
    params_dense_total.symbol,
    "Dense scaling-parameter specialization: the dense total-parameter count.",
    role=RelationRole.VARIANT,
    variant="dense",
)
eq_scaling_params_moe = eq(
    "training.eq.scaling_params_moe",
    scaling_params.symbol,
    params_active_moe.symbol,
    "MoE scaling-parameter specialization: the active-parameter count of an MoE model.",
    role=RelationRole.VARIANT,
    variant="moe",
)
eq_chinchilla_ratio_actual = eq(
    "training.eq.chinchilla_ratio_actual",
    chinchilla_ratio_actual.symbol,
    N_train_tokens.symbol / scaling_params.symbol,
    "Actual tokens per parameter equal total training tokens divided by the scaling parameter count.",
)
eq_chinchilla_gap = eq(
    "training.eq.chinchilla_gap",
    chinchilla_gap.symbol,
    chinchilla_ratio_actual.symbol / chinchilla_ratio.symbol,
    "Chinchilla gap equals actual tokens per parameter divided by the target ratio.",
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
