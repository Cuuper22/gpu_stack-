"""
scopes/training.py
==================

End-to-end training-step decomposition.

The older file described a step as compute plus communication plus memory
plus bubbles, but it did not actually wire those pieces to the lower scopes.
This version does. It now carries through:

  * dense versus MoE model-FLOP counts
  * recomputation and optimizer overhead on executed chip FLOPs
  * DP, TP, EP, CP, and offload communication terms
  * HBM traffic terms for parameters, gradients, optimizer state, and
    activations
  * pipeline bubbles, stragglers, evaluation overhead, and availability
  * energy-per-step and energy-per-token metrics
"""

import sympy as sp

from ..core import RelationRole, System, eq, var
from .architecture import (
    flops_step_dense,
    flops_step_moe,
    n_layers,
    n_moe_layers,
    n_tokens_step,
    params_active_moe,
    params_dense_total,
)
from .gpu import (
    hbm_bw_gpu_effective,
    p_gpu_total,
    peak_flops_gpu,
    peak_flops_gpu_effective,
    peak_flops_gpu_power_limited,
)
from .interconnect import alpha_scale_out, beta_scale_out, bw_nvlink_effective
from .parallelism import (
    bubble_1f1b,
    cp_comm_per_layer,
    cpu_offload_time,
    dp_degree,
    ep_exposed_time,
    mem_act,
    mem_grads,
    mem_opt,
    mem_params,
    n_gpus_total,
    nvme_offload_time,
    recompute_flop_multiplier,
    tp_exposed_time,
)


sys_train = System(
    name="training",
    scope="training",
    description="Training-step decomposition, MFU or HFU, throughput, wall clock, and energy metrics.",
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


# ---------------------------------------------------------------------------
# Communication terms
# ---------------------------------------------------------------------------

dp_alpha = var(
    "training.dp.alpha", "alpha_DP_train", "s",
    "Startup latency used for the data-parallel gradient-synchronization path.",
    scope="training",
)
dp_beta = var(
    "training.dp.beta", "beta_DP_train", "s/byte",
    "Per-byte transfer time used for the data-parallel gradient-synchronization path.",
    scope="training",
)
dp_bucket_count = var(
    "training.dp.bucket_count", "N_bucket_DP_train", "buckets",
    "Number of gradient buckets participating in data-parallel synchronization.",
    scope="training",
    integer=True,
)
dp_grad_sync_fraction = var(
    "training.dp.grad_sync_fraction", "phi_grad_DP_train", "dimensionless",
    "Fraction of the total gradient footprint that actually participates in the modeled DP synchronization path.",
    scope="training",
)
dp_grad_bytes = var(
    "training.dp.grad_bytes", "B_grad_DP_train", "byte",
    "Gradient bytes participating in data-parallel synchronization.",
    scope="training",
)
t_comm_dp = var(
    "training.t_comm_dp", "T_DP_train", "s",
    "Data-parallel gradient-synchronization time.",
    scope="training",
)
t_comm_tp_total = var(
    "training.t_comm_tp_total", "T_TP_train", "s",
    "Total tensor-parallel communication time across all layers.",
    scope="training",
)
t_comm_ep_total = var(
    "training.t_comm_ep_total", "T_EP_train", "s",
    "Total expert-parallel communication time across all MoE layers.",
    scope="training",
)
cp_group_bw = var(
    "training.cp.group_bw", "BW_CP_train", "byte/s",
    "Bandwidth available to context-parallel exchanges.",
    scope="training",
)
cp_overlap_fraction = var(
    "training.cp.overlap_fraction", "rho_CP_ov_train", "dimensionless",
    "Fraction of context-parallel communication hidden by other work.",
    scope="training",
)
t_comm_cp = var(
    "training.t_comm_cp", "T_CP_train", "s",
    "Total context-parallel communication time across all layers.",
    scope="training",
)
t_offload = var(
    "training.t_offload", "T_off_train", "s",
    "CPU or NVMe offload time exposed on the critical path.",
    scope="training",
)

eq_dp_alpha = eq(
    "training.eq.dp_alpha",
    dp_alpha.symbol,
    alpha_scale_out.symbol,
    "By default the DP synchronization path uses the scale-out startup latency.",
)
eq_dp_beta = eq(
    "training.eq.dp_beta",
    dp_beta.symbol,
    beta_scale_out.symbol,
    "By default the DP synchronization path uses the scale-out per-byte transfer time.",
)
eq_dp_grad_bytes = eq(
    "training.eq.dp_grad_bytes",
    dp_grad_bytes.symbol,
    mem_grads.symbol * dp_grad_sync_fraction.symbol,
    "DP gradient payload equals total gradient bytes times the synchronized fraction.",
)
eq_t_comm_dp = eq(
    "training.eq.t_comm_dp",
    t_comm_dp.symbol,
    2 * (dp_degree.symbol - 1) * dp_alpha.symbol * dp_bucket_count.symbol
    + 2 * (dp_degree.symbol - 1) * dp_beta.symbol * dp_grad_bytes.symbol / dp_degree.symbol,
    "Bucketized ring allreduce pays one startup per bucket and a bandwidth term for the synchronized gradient payload.",
)
eq_t_comm_tp_total = eq(
    "training.eq.t_comm_tp_total",
    t_comm_tp_total.symbol,
    n_layers.symbol * tp_exposed_time.symbol,
    "Total TP communication time equals per-layer TP exposed time times layer count.",
)
eq_t_comm_ep_total = eq(
    "training.eq.t_comm_ep_total",
    t_comm_ep_total.symbol,
    n_moe_layers.symbol * ep_exposed_time.symbol,
    "Total EP communication time equals per-MoE-layer exposed time times the number of MoE layers.",
)
eq_cp_group_bw = eq(
    "training.eq.cp_group_bw",
    cp_group_bw.symbol,
    bw_nvlink_effective.symbol,
    "By default context-parallel exchanges use the fast intra-node NVLink bandwidth.",
)
eq_t_comm_cp = eq(
    "training.eq.t_comm_cp",
    t_comm_cp.symbol,
    n_layers.symbol * cp_comm_per_layer.symbol * (1 - cp_overlap_fraction.symbol) / cp_group_bw.symbol,
    "Context-parallel time equals per-layer traffic times unoverlapped fraction divided by CP bandwidth, aggregated across layers.",
)
eq_t_offload = eq(
    "training.eq.t_offload",
    t_offload.symbol,
    cpu_offload_time.symbol + nvme_offload_time.symbol,
    "Offload time adds CPU and NVMe offload critical-path time contributions.",
)
eq_t_exposed_comm = eq(
    "training.eq.t_exposed_comm",
    T_exposed_comm.symbol,
    t_comm_dp.symbol + t_comm_tp_total.symbol + t_comm_ep_total.symbol + t_comm_cp.symbol + t_offload.symbol,
    "Exposed communication time adds DP, TP, EP, CP, and offload terms that remain on the critical path.",
)


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


# ---------------------------------------------------------------------------
# Bubbles and overhead fractions
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

for v in [
    T_compute,
    T_exposed_comm,
    T_mem_bound,
    T_step_nominal,
    T_bubbles,
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
    dp_alpha,
    dp_beta,
    dp_bucket_count,
    dp_grad_sync_fraction,
    dp_grad_bytes,
    t_comm_dp,
    t_comm_tp_total,
    t_comm_ep_total,
    cp_group_bw,
    cp_overlap_fraction,
    t_comm_cp,
    t_offload,
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
    pipeline_bubble_fraction,
    straggler_fraction,
    restart_fraction,
    eval_fraction,
    overhead_fraction,
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
]:
    sys_train.add(v)

for e in [
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
    eq_dp_alpha,
    eq_dp_beta,
    eq_dp_grad_bytes,
    eq_t_comm_dp,
    eq_t_comm_tp_total,
    eq_t_comm_ep_total,
    eq_cp_group_bw,
    eq_t_comm_cp,
    eq_t_offload,
    eq_t_exposed_comm,
    eq_bytes_param_io_step,
    eq_bytes_grad_io_step,
    eq_bytes_opt_io_step,
    eq_bytes_act_io_step,
    eq_bytes_hbm_step,
    eq_hbm_bw_run_effective,
    eq_t_mem_bound,
    eq_pipeline_bubble_fraction,
    eq_overhead_fraction,
    eq_t_step_nominal,
    eq_t_bubbles,
    eq_t_step,
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
]:
    sys_train.add(e)
