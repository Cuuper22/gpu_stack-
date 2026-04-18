"""
scopes/training_memory.py
=========================

Training memory-bandwidth terms.

Parameter, gradient, optimizer-state, and activation IO bytes per step,
aggregate HBM traffic, the usable aggregate HBM bandwidth, and the
memory-bound auxiliary time that the overhead helper folds into the
nominal step time.
"""

from ..core import eq, var
from .gpu import hbm_bw_gpu_effective
from .parallelism import (
    mem_act,
    mem_grads,
    mem_opt,
    mem_params,
    n_gpus_total,
)
from .training_compute import T_mem_bound


# ---------------------------------------------------------------------------
# Memory-bandwidth terms
# ---------------------------------------------------------------------------

param_io_multiplier = var(
    "training.mem.param_io_multiplier", "rho_param_IO_train", "dimensionless",
    "HBM traffic multiplier applied to parameter bytes per step.",
    scope="training",
)
grad_io_multiplier = var(
    "training.mem.grad_io_multiplier", "rho_grad_IO_train", "dimensionless",
    "HBM traffic multiplier applied to gradient bytes per step.",
    scope="training",
)
opt_io_multiplier = var(
    "training.mem.opt_io_multiplier", "rho_opt_IO_train", "dimensionless",
    "HBM traffic multiplier applied to optimizer-state bytes per step.",
    scope="training",
)
act_io_multiplier = var(
    "training.mem.act_io_multiplier", "rho_act_IO_train", "dimensionless",
    "HBM traffic multiplier applied to activation bytes per step.",
    scope="training",
)
bytes_param_io_step = var(
    "training.mem.param_bytes_step", "B_param_step_train", "byte",
    "Parameter-related HBM bytes per step.",
    scope="training",
)
bytes_grad_io_step = var(
    "training.mem.grad_bytes_step", "B_grad_step_train", "byte",
    "Gradient-related HBM bytes per step.",
    scope="training",
)
bytes_opt_io_step = var(
    "training.mem.opt_bytes_step", "B_opt_step_train", "byte",
    "Optimizer-state HBM bytes per step.",
    scope="training",
)
bytes_act_io_step = var(
    "training.mem.act_bytes_step", "B_act_step_train", "byte",
    "Activation HBM bytes per step.",
    scope="training",
)
bytes_hbm_step = var(
    "training.mem.hbm_bytes_step", "B_HBM_step_train", "byte",
    "Total HBM bytes per step attributed to memory-bound auxiliary work.",
    scope="training",
)
memory_bw_efficiency = var(
    "training.mem.bw_efficiency", "eta_mem_train", "dimensionless",
    "Fraction of aggregate effective HBM bandwidth that the memory-bound auxiliary work can realize.",
    scope="training",
)
hbm_bw_run_effective = var(
    "training.mem.hbm_bw_run_effective", "BW_HBM_run_eff_train", "byte/s",
    "Aggregate effective HBM bandwidth across all GPUs after memory-BW efficiency is applied.",
    scope="training",
)

eq_bytes_param_io_step = eq(
    "training.eq.param_bytes_step",
    bytes_param_io_step.symbol,
    param_io_multiplier.symbol * mem_params.symbol,
    "Parameter-related HBM bytes equal total parameter bytes times the parameter-traffic multiplier.",
)
eq_bytes_grad_io_step = eq(
    "training.eq.grad_bytes_step",
    bytes_grad_io_step.symbol,
    grad_io_multiplier.symbol * mem_grads.symbol,
    "Gradient-related HBM bytes equal total gradient bytes times the gradient-traffic multiplier.",
)
eq_bytes_opt_io_step = eq(
    "training.eq.opt_bytes_step",
    bytes_opt_io_step.symbol,
    opt_io_multiplier.symbol * mem_opt.symbol,
    "Optimizer-state HBM bytes equal total optimizer-state bytes times the optimizer-state traffic multiplier.",
)
eq_bytes_act_io_step = eq(
    "training.eq.act_bytes_step",
    bytes_act_io_step.symbol,
    act_io_multiplier.symbol * mem_act.symbol,
    "Activation HBM bytes equal total activation bytes times the activation-traffic multiplier.",
)
eq_bytes_hbm_step = eq(
    "training.eq.hbm_bytes_step",
    bytes_hbm_step.symbol,
    bytes_param_io_step.symbol + bytes_grad_io_step.symbol + bytes_opt_io_step.symbol + bytes_act_io_step.symbol,
    "Total HBM auxiliary traffic per step adds parameter, gradient, optimizer-state, and activation bytes.",
)
eq_hbm_bw_run_effective = eq(
    "training.eq.hbm_bw_run_effective",
    hbm_bw_run_effective.symbol,
    n_gpus_total.symbol * hbm_bw_gpu_effective.symbol * memory_bw_efficiency.symbol,
    "Aggregate usable HBM bandwidth equals GPU count times per-GPU effective HBM bandwidth times the realized efficiency of the memory-bound auxiliary work.",
)
eq_t_mem_bound = eq(
    "training.eq.t_mem_bound",
    T_mem_bound.symbol,
    bytes_hbm_step.symbol / hbm_bw_run_effective.symbol,
    "Memory-bound auxiliary time equals HBM bytes per step divided by aggregate usable HBM bandwidth.",
)


TRAINING_MEMORY_VARIABLES = (
    param_io_multiplier,
    grad_io_multiplier,
    opt_io_multiplier,
    act_io_multiplier,
    bytes_param_io_step,
    bytes_grad_io_step,
    bytes_opt_io_step,
    bytes_act_io_step,
    bytes_hbm_step,
    memory_bw_efficiency,
    hbm_bw_run_effective,
)

TRAINING_MEMORY_EQUATIONS = (
    eq_bytes_param_io_step,
    eq_bytes_grad_io_step,
    eq_bytes_opt_io_step,
    eq_bytes_act_io_step,
    eq_bytes_hbm_step,
    eq_hbm_bw_run_effective,
    eq_t_mem_bound,
)


__all__ = [
    "param_io_multiplier",
    "grad_io_multiplier",
    "opt_io_multiplier",
    "act_io_multiplier",
    "bytes_param_io_step",
    "bytes_grad_io_step",
    "bytes_opt_io_step",
    "bytes_act_io_step",
    "bytes_hbm_step",
    "memory_bw_efficiency",
    "hbm_bw_run_effective",
    "eq_bytes_param_io_step",
    "eq_bytes_grad_io_step",
    "eq_bytes_opt_io_step",
    "eq_bytes_act_io_step",
    "eq_bytes_hbm_step",
    "eq_hbm_bw_run_effective",
    "eq_t_mem_bound",
    "TRAINING_MEMORY_VARIABLES",
    "TRAINING_MEMORY_EQUATIONS",
]
