"""
scopes/gpu_compute.py
=====================

GPU-die compute aggregation. SM count, Tensor Core count per package, and
raw, effective, sparse, and power-limited GPU peak FLOPs. GPU-level DP4A,
DP2A, and SFU throughput aggregated from per-SM arithmetic paths. This is
the foundation helper for the gpu scope.
"""

from ..core import eq, var
from .arithmetic import (
    n_tc_per_sm,
    peak_dp2a_sm,
    peak_dp4a_sm,
    peak_flops_sm,
    peak_flops_sm_effective,
    peak_flops_sm_sparse,
    peak_sfu_ops_sm,
)


# ---------------------------------------------------------------------------
# SM count and die-level compute aggregates
# ---------------------------------------------------------------------------

n_sms = var(
    "gpu.n_sms", "N_SM", "units",
    "Number of SMs on one GPU die.",
    scope="gpu",
    integer=True,
)
n_tc_per_gpu = var(
    "gpu.n_tc", "N_TC", "units",
    "Total Tensor Cores on one GPU package.",
    scope="gpu",
    integer=True,
)
peak_flops_gpu = var(
    "gpu.peak_flops", "P_GPU", "FLOP/s",
    "Raw peak FLOPs per GPU, before issue losses or package-level throttling.",
    scope="gpu",
)
peak_flops_gpu_effective = var(
    "gpu.peak_flops_effective", "P_GPU_eff", "FLOP/s",
    "Issue-efficiency-limited peak FLOPs per GPU from effective per-SM throughput.",
    scope="gpu",
)
peak_flops_gpu_sparse = var(
    "gpu.peak_flops_sparse", "P_GPU_sparse", "FLOP/s",
    "Structured-sparse dense-equivalent peak FLOPs per GPU.",
    scope="gpu",
)
peak_dp4a_gpu = var(
    "gpu.peak_dp4a_ops", "P_GPU_dp4a", "op/s",
    "Peak DP4A integer throughput aggregated across all SMs.",
    scope="gpu",
)
peak_dp2a_gpu = var(
    "gpu.peak_dp2a_ops", "P_GPU_dp2a", "op/s",
    "Peak DP2A integer throughput aggregated across all SMs.",
    scope="gpu",
)
peak_sfu_gpu = var(
    "gpu.peak_sfu_ops", "P_GPU_sfu", "op/s",
    "Peak SFU throughput aggregated across all SMs.",
    scope="gpu",
)
peak_flops_gpu_power_limited = var(
    "gpu.peak_flops_power_limited", "P_GPU_pwlim", "FLOP/s",
    "Effective per-GPU peak after issue losses and any TDP-induced power throttling.",
    scope="gpu",
)

eq_tc_count = eq(
    "gpu.eq.tc_count",
    n_tc_per_gpu.symbol,
    n_sms.symbol * n_tc_per_sm.symbol,
    "Tensor Core count equals SM count times Tensor Cores per SM.",
)
eq_peak_flops_gpu = eq(
    "gpu.eq.peak_flops",
    peak_flops_gpu.symbol,
    n_sms.symbol * peak_flops_sm.symbol,
    "Raw peak GPU FLOPs aggregate the raw per-SM peak across all SMs.",
)
eq_peak_flops_gpu_effective = eq(
    "gpu.eq.peak_flops_effective",
    peak_flops_gpu_effective.symbol,
    n_sms.symbol * peak_flops_sm_effective.symbol,
    "Effective GPU peak aggregates the issue-efficiency-limited per-SM peak across all SMs.",
)
eq_peak_flops_gpu_sparse = eq(
    "gpu.eq.peak_flops_sparse",
    peak_flops_gpu_sparse.symbol,
    n_sms.symbol * peak_flops_sm_sparse.symbol,
    "Sparse dense-equivalent peak aggregates sparse per-SM throughput across the die.",
)
eq_peak_dp4a_gpu = eq(
    "gpu.eq.peak_dp4a",
    peak_dp4a_gpu.symbol,
    n_sms.symbol * peak_dp4a_sm.symbol,
    "Peak DP4A throughput is the per-SM DP4A peak times SM count.",
)
eq_peak_dp2a_gpu = eq(
    "gpu.eq.peak_dp2a",
    peak_dp2a_gpu.symbol,
    n_sms.symbol * peak_dp2a_sm.symbol,
    "Peak DP2A throughput is the per-SM DP2A peak times SM count.",
)
eq_peak_sfu_gpu = eq(
    "gpu.eq.peak_sfu",
    peak_sfu_gpu.symbol,
    n_sms.symbol * peak_sfu_ops_sm.symbol,
    "Peak SFU throughput is the per-SM SFU peak times SM count.",
)


GPU_COMPUTE_VARIABLES = (
    n_sms,
    n_tc_per_gpu,
    peak_flops_gpu,
    peak_flops_gpu_effective,
    peak_flops_gpu_sparse,
    peak_dp4a_gpu,
    peak_dp2a_gpu,
    peak_sfu_gpu,
    peak_flops_gpu_power_limited,
)

GPU_COMPUTE_EQUATIONS = (
    eq_tc_count,
    eq_peak_flops_gpu,
    eq_peak_flops_gpu_effective,
    eq_peak_flops_gpu_sparse,
    eq_peak_dp4a_gpu,
    eq_peak_dp2a_gpu,
    eq_peak_sfu_gpu,
)


__all__ = [
    "n_sms",
    "n_tc_per_gpu",
    "peak_flops_gpu",
    "peak_flops_gpu_effective",
    "peak_flops_gpu_sparse",
    "peak_dp4a_gpu",
    "peak_dp2a_gpu",
    "peak_sfu_gpu",
    "peak_flops_gpu_power_limited",
    "eq_tc_count",
    "eq_peak_flops_gpu",
    "eq_peak_flops_gpu_effective",
    "eq_peak_flops_gpu_sparse",
    "eq_peak_dp4a_gpu",
    "eq_peak_dp2a_gpu",
    "eq_peak_sfu_gpu",
    "GPU_COMPUTE_VARIABLES",
    "GPU_COMPUTE_EQUATIONS",
]
