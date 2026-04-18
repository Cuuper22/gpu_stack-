"""
scopes/training_compute.py
==========================

Training compute foundation.

Step FLOPs for dense and MoE paths, recomputation and optimizer-overhead
multipliers, executed chip FLOPs, peak FLOPs run aggregates, compute time,
achieved FLOPs, MFU, HFU, and FLOPs per token. Other training helpers
import shared time variables from this module.
"""

from ..core import RelationRole, eq, var
from .architecture import (
    flops_step_dense,
    flops_step_moe,
    n_tokens_step,
)
from .gpu import (
    peak_flops_gpu,
    peak_flops_gpu_effective,
    peak_flops_gpu_power_limited,
)
from .parallelism import (
    n_gpus_total,
    recompute_flop_multiplier,
)


# ---------------------------------------------------------------------------
# Step time decomposition
# ---------------------------------------------------------------------------

T_compute = var(
    "training.t_compute", "T_comp", "s",
    "Time spent on executed chip FLOPs, including recomputation and optimizer work factors.",
    scope="training",
)
T_exposed_comm = var(
    "training.t_exposed_comm", "T_ec", "s",
    "Communication time that is not hidden by compute.",
    scope="training",
)
T_mem_bound = var(
    "training.t_mem_bound", "T_mb", "s",
    "Time spent on HBM-traffic-dominated work outside the main matmuls.",
    scope="training",
)
T_step = var(
    "training.t_step", "T_step", "s",
    "Wall-clock time per training step.",
    scope="training",
)


# ---------------------------------------------------------------------------
# FLOP accounting
# ---------------------------------------------------------------------------

flops_step = var(
    "training.flops_per_step", "F_step", "FLOP",
    "Model FLOPs per step. Dense and MoE alternatives are both wired in.",
    scope="training",
)
recompute_overhead = var(
    "training.recompute_overhead", "rho_rc", "dimensionless",
    "Multiplicative FLOP overhead from recomputation or checkpointing.",
    scope="training",
)
optimizer_flop_multiplier = var(
    "training.optimizer_flop_multiplier", "rho_opt_flop", "dimensionless",
    "Extra chip FLOPs per model FLOP from optimizer and update-side work.",
    scope="training",
)
flops_executed_step = var(
    "training.flops_executed_per_step", "F_exec_step", "FLOP",
    "Actual chip FLOPs executed per step after recomputation and optimizer overhead.",
    scope="training",
)
T_compute_ideal = var(
    "training.t_compute_ideal", "T_comp_id", "s",
    "Ideal time for model FLOPs at raw peak throughput.",
    scope="training",
)
peak_flops_run = var(
    "training.peak_flops", "P_run", "FLOP/s",
    "Aggregate raw peak FLOPs across all participating GPUs.",
    scope="training",
)
peak_flops_run_effective = var(
    "training.peak_flops_effective", "P_run_eff", "FLOP/s",
    "Aggregate effective peak after issue losses but before package-level power throttling.",
    scope="training",
)
peak_flops_run_power_limited = var(
    "training.peak_flops_power_limited", "P_run_pwlim", "FLOP/s",
    "Aggregate effective peak after both issue losses and package-level power throttling.",
    scope="training",
)
achieved_flops_run = var(
    "training.achieved_flops", "A_run", "FLOP/s",
    "Sustained model FLOPs per second delivered by the run.",
    scope="training",
)
achieved_flops_chip = var(
    "training.achieved_flops_chip", "A_chip_run", "FLOP/s",
    "Sustained chip FLOPs per second, including recomputation and optimizer overhead.",
    scope="training",
)
mfu = var(
    "training.mfu", "MFU", "dimensionless",
    "Model FLOPs Utilization, meaning delivered model FLOPs divided by raw peak FLOPs.",
    scope="training",
)
hfu = var(
    "training.hfu", "HFU", "dimensionless",
    "Hardware FLOPs Utilization, meaning delivered chip FLOPs divided by power-limited effective peak FLOPs.",
    scope="training",
)
flops_per_token = var(
    "training.flops_per_token", "F_tok_train", "FLOP/token",
    "Model FLOPs per token.",
    scope="training",
)

eq_flops_step_dense = eq(
    "training.eq.flops_step_dense",
    flops_step.symbol,
    flops_step_dense.symbol,
    "Dense specialization of training FLOPs per step: the dense-model FLOP count.",
    role=RelationRole.VARIANT,
    variant="dense",
)
eq_flops_step_moe = eq(
    "training.eq.flops_step_moe",
    flops_step.symbol,
    flops_step_moe.symbol,
    "MoE specialization of training FLOPs per step: the active-MoE FLOP count.",
    role=RelationRole.VARIANT,
    variant="moe",
)
eq_recompute_overhead = eq(
    "training.eq.recompute_overhead",
    recompute_overhead.symbol,
    recompute_flop_multiplier.symbol,
    "Recomputation overhead aliases the lower-scope recompute FLOP multiplier.",
)
eq_flops_executed_step = eq(
    "training.eq.flops_executed_step",
    flops_executed_step.symbol,
    flops_step.symbol * recompute_overhead.symbol * optimizer_flop_multiplier.symbol,
    "Executed chip FLOPs per step equal model FLOPs times recomputation overhead times optimizer-side FLOP overhead.",
)
eq_peak_flops_run = eq(
    "training.eq.peak_flops",
    peak_flops_run.symbol,
    n_gpus_total.symbol * peak_flops_gpu.symbol,
    "Aggregate raw peak FLOPs equal GPU count times raw per-GPU peak.",
)
eq_peak_flops_run_effective = eq(
    "training.eq.peak_flops_effective",
    peak_flops_run_effective.symbol,
    n_gpus_total.symbol * peak_flops_gpu_effective.symbol,
    "Aggregate effective peak equals GPU count times issue-efficiency-limited per-GPU peak.",
)
eq_peak_flops_run_power_limited = eq(
    "training.eq.peak_flops_power_limited",
    peak_flops_run_power_limited.symbol,
    n_gpus_total.symbol * peak_flops_gpu_power_limited.symbol,
    "Aggregate power-limited peak equals GPU count times power-limited effective per-GPU peak.",
)
eq_t_compute_ideal = eq(
    "training.eq.t_compute_ideal",
    T_compute_ideal.symbol,
    flops_step.symbol / peak_flops_run.symbol,
    "Ideal compute time for model FLOPs equals model FLOPs divided by aggregate raw peak throughput.",
)
eq_t_compute = eq(
    "training.eq.t_compute",
    T_compute.symbol,
    flops_executed_step.symbol / peak_flops_run_power_limited.symbol,
    "Executed compute time equals executed chip FLOPs divided by aggregate power-limited effective peak throughput.",
)
eq_achieved_flops = eq(
    "training.eq.achieved_flops",
    achieved_flops_run.symbol,
    flops_step.symbol / T_step.symbol,
    "Sustained model FLOPs per second equal model FLOPs per step divided by wall-clock step time.",
)
eq_achieved_flops_chip = eq(
    "training.eq.achieved_flops_chip",
    achieved_flops_chip.symbol,
    flops_executed_step.symbol / T_step.symbol,
    "Sustained chip FLOPs per second equal executed chip FLOPs per step divided by wall-clock step time.",
)
eq_mfu_from_ratio = eq(
    "training.eq.mfu",
    mfu.symbol,
    achieved_flops_run.symbol / peak_flops_run.symbol,
    "MFU equals achieved model FLOPs divided by aggregate raw peak FLOPs.",
    role=RelationRole.VARIANT,
    variant="from_flops",
)
eq_mfu_from_time = eq(
    "training.eq.mfu_from_time",
    mfu.symbol,
    T_compute_ideal.symbol / T_step.symbol,
    "MFU also equals ideal raw-peak compute time divided by actual step time.",
    role=RelationRole.VARIANT,
    variant="from_time",
)
eq_hfu = eq(
    "training.eq.hfu",
    hfu.symbol,
    achieved_flops_chip.symbol / peak_flops_run_power_limited.symbol,
    "HFU equals achieved chip FLOPs divided by aggregate power-limited effective peak FLOPs.",
)
eq_flops_per_token = eq(
    "training.eq.flops_per_token",
    flops_per_token.symbol,
    flops_step.symbol / n_tokens_step.symbol,
    "Model FLOPs per token equal model FLOPs per step divided by tokens per step.",
)


TRAINING_COMPUTE_VARIABLES = (
    T_compute,
    T_exposed_comm,
    T_mem_bound,
    T_step,
    flops_step,
    recompute_overhead,
    optimizer_flop_multiplier,
    flops_executed_step,
    T_compute_ideal,
    peak_flops_run,
    peak_flops_run_effective,
    peak_flops_run_power_limited,
    achieved_flops_run,
    achieved_flops_chip,
    mfu,
    hfu,
    flops_per_token,
)

TRAINING_COMPUTE_EQUATIONS = (
    eq_flops_step_dense,
    eq_flops_step_moe,
    eq_recompute_overhead,
    eq_flops_executed_step,
    eq_peak_flops_run,
    eq_peak_flops_run_effective,
    eq_peak_flops_run_power_limited,
    eq_t_compute_ideal,
    eq_t_compute,
    eq_achieved_flops,
    eq_achieved_flops_chip,
    eq_mfu_from_ratio,
    eq_mfu_from_time,
    eq_hfu,
    eq_flops_per_token,
)


__all__ = [
    "T_compute",
    "T_exposed_comm",
    "T_mem_bound",
    "T_step",
    "flops_step",
    "recompute_overhead",
    "optimizer_flop_multiplier",
    "flops_executed_step",
    "T_compute_ideal",
    "peak_flops_run",
    "peak_flops_run_effective",
    "peak_flops_run_power_limited",
    "achieved_flops_run",
    "achieved_flops_chip",
    "mfu",
    "hfu",
    "flops_per_token",
    "eq_flops_step_dense",
    "eq_flops_step_moe",
    "eq_recompute_overhead",
    "eq_flops_executed_step",
    "eq_peak_flops_run",
    "eq_peak_flops_run_effective",
    "eq_peak_flops_run_power_limited",
    "eq_t_compute_ideal",
    "eq_t_compute",
    "eq_achieved_flops",
    "eq_achieved_flops_chip",
    "eq_mfu_from_ratio",
    "eq_mfu_from_time",
    "eq_hfu",
    "eq_flops_per_token",
    "TRAINING_COMPUTE_VARIABLES",
    "TRAINING_COMPUTE_EQUATIONS",
]
