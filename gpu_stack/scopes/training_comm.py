"""
scopes/training_comm.py
=======================

Training communication terms.

Data-parallel gradient synchronization, tensor-parallel and expert-parallel
exposed communication aggregated across layers, context-parallel overlap,
and offload critical-path time. Adds these up into the exposed-communication
time that the overhead helper consumes.
"""

from ..core import eq, var
from .architecture import n_layers, n_moe_layers
from .interconnect import alpha_scale_out, beta_scale_out, bw_nvlink_effective
from .parallelism import (
    cp_comm_per_layer,
    cpu_offload_time,
    dp_degree,
    ep_exposed_time,
    mem_grads,
    nvme_offload_time,
    tp_exposed_time,
)
from .training_compute import T_exposed_comm


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


TRAINING_COMM_VARIABLES = (
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
)

TRAINING_COMM_EQUATIONS = (
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
)


__all__ = [
    "dp_alpha",
    "dp_beta",
    "dp_bucket_count",
    "dp_grad_sync_fraction",
    "dp_grad_bytes",
    "t_comm_dp",
    "t_comm_tp_total",
    "t_comm_ep_total",
    "cp_group_bw",
    "cp_overlap_fraction",
    "t_comm_cp",
    "t_offload",
    "eq_dp_alpha",
    "eq_dp_beta",
    "eq_dp_grad_bytes",
    "eq_t_comm_dp",
    "eq_t_comm_tp_total",
    "eq_t_comm_ep_total",
    "eq_cp_group_bw",
    "eq_t_comm_cp",
    "eq_t_offload",
    "eq_t_exposed_comm",
    "TRAINING_COMM_VARIABLES",
    "TRAINING_COMM_EQUATIONS",
]
