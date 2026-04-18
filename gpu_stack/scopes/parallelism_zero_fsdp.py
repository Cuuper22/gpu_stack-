"""
scopes/parallelism_zero_fsdp.py
===============================

ZeRO-1, ZeRO-2, and ZeRO-3 per-GPU memory breakdowns, CPU and NVMe
offload transfer-time models, and FSDP all-gather buffer sizing.
"""

from ..core import eq, var
from .parallelism_batching import (
    mem_act_per_gpu,
    mem_grads,
    mem_opt,
    mem_params,
    shard_factor,
)


# ---------------------------------------------------------------------------
# ZeRO stage breakdowns
# ---------------------------------------------------------------------------

mem_zero1_per_gpu = var(
    "par.zero1.mem_per_gpu", "M_zero1_par", "byte",
    "Per-GPU memory under ZeRO-1, where only optimizer state is sharded.",
    scope="parallelism",
)
mem_zero2_per_gpu = var(
    "par.zero2.mem_per_gpu", "M_zero2_par", "byte",
    "Per-GPU memory under ZeRO-2, where optimizer state and gradients are sharded.",
    scope="parallelism",
)
mem_zero3_per_gpu = var(
    "par.zero3.mem_per_gpu", "M_zero3_par", "byte",
    "Per-GPU memory under ZeRO-3, where params, gradients, and optimizer state are all sharded.",
    scope="parallelism",
)
fsdp_live_param_fraction = var(
    "par.fsdp.live_param_fraction", "rho_live_par", "dimensionless",
    "Fraction of the full parameter set materialized transiently by an all-gather window.",
    scope="parallelism",
)
fsdp_allgather_buffer = var(
    "par.fsdp.allgather_buffer", "M_gather_par", "byte",
    "Transient parameter buffer materialized during FSDP all-gather.",
    scope="parallelism",
)


eq_mem_zero1 = eq(
    "par.eq.mem_zero1",
    mem_zero1_per_gpu.symbol,
    mem_params.symbol + mem_grads.symbol + mem_opt.symbol / shard_factor.symbol + mem_act_per_gpu.symbol,
    "ZeRO-1 shards optimizer state only.",
)

eq_mem_zero2 = eq(
    "par.eq.mem_zero2",
    mem_zero2_per_gpu.symbol,
    mem_params.symbol + mem_grads.symbol / shard_factor.symbol + mem_opt.symbol / shard_factor.symbol + mem_act_per_gpu.symbol,
    "ZeRO-2 shards gradients and optimizer state but still keeps full parameter replicas.",
)

eq_mem_zero3 = eq(
    "par.eq.mem_zero3",
    mem_zero3_per_gpu.symbol,
    mem_params.symbol / shard_factor.symbol + mem_grads.symbol / shard_factor.symbol + mem_opt.symbol / shard_factor.symbol + mem_act_per_gpu.symbol,
    "ZeRO-3 shards params, gradients, and optimizer state.",
)

eq_fsdp_allgather_buffer = eq(
    "par.eq.fsdp_allgather_buffer",
    fsdp_allgather_buffer.symbol,
    mem_params.symbol * fsdp_live_param_fraction.symbol,
    "A layer-wise all-gather window only materializes the live slice of the parameter set, not the whole model at once.",
)


# ---------------------------------------------------------------------------
# CPU and NVMe offload
# ---------------------------------------------------------------------------

cpu_offload_bytes = var(
    "par.offload.cpu.bytes", "B_cpu_off_par", "byte",
    "State migrated from GPU memory to CPU memory.",
    scope="parallelism",
)
cpu_offload_bw = var(
    "par.offload.cpu.bw", "BW_cpu_off_par", "byte/s",
    "Usable host-device bandwidth for CPU offload traffic.",
    scope="parallelism",
)
cpu_offload_time = var(
    "par.offload.cpu.time", "T_cpu_off_par", "s",
    "Communication time required to move the CPU-offloaded state.",
    scope="parallelism",
)
mem_after_cpu_offload = var(
    "par.offload.cpu.mem_after", "M_cpu_after_par", "byte",
    "Remaining on-GPU memory footprint after CPU offload.",
    scope="parallelism",
)
nvme_offload_bytes = var(
    "par.offload.nvme.bytes", "B_nvme_off_par", "byte",
    "State migrated from GPU or CPU memory to NVMe.",
    scope="parallelism",
)
nvme_offload_bw = var(
    "par.offload.nvme.bw", "BW_nvme_off_par", "byte/s",
    "Usable NVMe bandwidth for optimizer or parameter offload.",
    scope="parallelism",
)
nvme_offload_time = var(
    "par.offload.nvme.time", "T_nvme_off_par", "s",
    "Communication time required to move the NVMe-offloaded state.",
    scope="parallelism",
)


eq_cpu_offload_time = eq(
    "par.eq.cpu_offload_time",
    cpu_offload_time.symbol,
    cpu_offload_bytes.symbol / cpu_offload_bw.symbol,
    "CPU offload time is bytes moved divided by effective host-device bandwidth.",
)

eq_mem_after_cpu_offload = eq(
    "par.eq.mem_after_cpu_offload",
    mem_after_cpu_offload.symbol,
    mem_zero3_per_gpu.symbol - cpu_offload_bytes.symbol,
    "CPU offload reduces the GPU-resident memory footprint by the amount migrated off the device.",
)

eq_nvme_offload_time = eq(
    "par.eq.nvme_offload_time",
    nvme_offload_time.symbol,
    nvme_offload_bytes.symbol / nvme_offload_bw.symbol,
    "NVMe offload time is bytes moved divided by usable storage bandwidth.",
)


PARALLELISM_ZERO_FSDP_VARIABLES = [
    mem_zero1_per_gpu, mem_zero2_per_gpu, mem_zero3_per_gpu,
    fsdp_live_param_fraction, fsdp_allgather_buffer,
    cpu_offload_bytes, cpu_offload_bw, cpu_offload_time, mem_after_cpu_offload,
    nvme_offload_bytes, nvme_offload_bw, nvme_offload_time,
]

PARALLELISM_ZERO_FSDP_EQUATIONS = [
    eq_mem_zero1,
    eq_mem_zero2,
    eq_mem_zero3,
    eq_fsdp_allgather_buffer,
    eq_cpu_offload_time,
    eq_mem_after_cpu_offload,
    eq_nvme_offload_time,
]


__all__ = [
    "mem_zero1_per_gpu",
    "mem_zero2_per_gpu",
    "mem_zero3_per_gpu",
    "fsdp_live_param_fraction",
    "fsdp_allgather_buffer",
    "cpu_offload_bytes",
    "cpu_offload_bw",
    "cpu_offload_time",
    "mem_after_cpu_offload",
    "nvme_offload_bytes",
    "nvme_offload_bw",
    "nvme_offload_time",
    "eq_mem_zero1",
    "eq_mem_zero2",
    "eq_mem_zero3",
    "eq_fsdp_allgather_buffer",
    "eq_cpu_offload_time",
    "eq_mem_after_cpu_offload",
    "eq_nvme_offload_time",
    "PARALLELISM_ZERO_FSDP_VARIABLES",
    "PARALLELISM_ZERO_FSDP_EQUATIONS",
]
