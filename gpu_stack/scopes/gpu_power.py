"""
scopes/gpu_power.py
===================

GPU package power: compute, memory, and fabric power terms, total package
power, TDP headroom, piecewise throttle factor, HBM sweep time,
FLOPs-per-joule, bytes-per-joule, and roofline balance points.
"""

import sympy as sp

from ..core import PiecewiseEquation, Reference, eq, var
from ..core.units import BPS, FLOPS, JOULE, SECOND, WATT, byte
from .memory_subsystem import e_per_byte_hbm, hbm_bw
from .physical import P_total_gate
from .gpu_compute import (
    n_sms,
    peak_flops_gpu,
    peak_flops_gpu_effective,
    peak_flops_gpu_power_limited,
)
from .gpu_memory import hbm_bw_gpu_effective, hbm_capacity_gpu_effective
from .gpu_io import nic_tx_bw, nvlink_tx_bw


DIMENSIONLESS = sp.Integer(1)

GPU_PACKAGE_POWER_REF = Reference(
    "GPU package power is modeled as compute-domain logic power plus HBM "
    "traffic energy and package-boundary fabric traffic energy.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Package power: compute, HBM, interconnect
# ---------------------------------------------------------------------------

tdp_gpu = var(
    "gpu.tdp", "TDP_GPU", "W",
    "Thermal design power for one GPU package.",
    scope="gpu",
    sp_units=WATT,
    references=[GPU_PACKAGE_POWER_REF],
)
active_equiv_gates_per_sm = var(
    "gpu.power.equiv_gates_per_sm", "N_gate_eq_SM_GPU", "gates",
    "Equivalent number of simultaneously modeled logic gates per SM that carry the lower-scope per-gate power model.",
    scope="gpu",
    sp_units=DIMENSIONLESS,
    references=[GPU_PACKAGE_POWER_REF],
)
active_equiv_gates_uncore = var(
    "gpu.power.equiv_gates_uncore", "N_gate_eq_uncore_GPU", "gates",
    "Equivalent package-level uncore logic gates, such as front-end, fabric, and control logic.",
    scope="gpu",
    sp_units=DIMENSIONLESS,
    references=[GPU_PACKAGE_POWER_REF],
)
p_gpu_compute_sm = var(
    "gpu.power.compute_sm", "P_GPU_SM", "W",
    "SM-local compute power aggregated across all SMs.",
    scope="gpu",
    sp_units=WATT,
    references=[GPU_PACKAGE_POWER_REF],
)
p_gpu_compute_uncore = var(
    "gpu.power.compute_uncore", "P_GPU_uncore", "W",
    "Uncore compute and control power at package scope.",
    scope="gpu",
    sp_units=WATT,
    references=[GPU_PACKAGE_POWER_REF],
)
p_gpu_compute = var(
    "gpu.power.compute", "P_GPU_comp", "W",
    "Total compute-domain power from SM-local and uncore logic.",
    scope="gpu",
    sp_units=WATT,
    references=[GPU_PACKAGE_POWER_REF],
)
hbm_utilization = var(
    "gpu.hbm.utilization", "rho_HBM_GPU", "dimensionless",
    "Average fraction of effective HBM bandwidth actively exercised by the workload.",
    scope="gpu",
    sp_units=DIMENSIONLESS,
    references=[GPU_PACKAGE_POWER_REF],
)
p_gpu_memory = var(
    "gpu.power.memory", "P_GPU_mem", "W",
    "Power dissipated by HBM transfers under the current memory-utilization point.",
    scope="gpu",
    sp_units=WATT,
    references=[GPU_PACKAGE_POWER_REF],
)
e_per_byte_nvlink = var(
    "gpu.nvlink.energy_per_byte", "E_B_NVL_GPU", "J/byte",
    "Energy spent per NVLink byte transferred at the package boundary.",
    scope="gpu",
    sp_units=JOULE / byte,
    references=[GPU_PACKAGE_POWER_REF],
)
e_per_byte_nic = var(
    "gpu.nic.energy_per_byte", "E_B_NIC_GPU", "J/byte",
    "Energy spent per scale-out byte transferred by the GPU-adjacent NIC path.",
    scope="gpu",
    sp_units=JOULE / byte,
    references=[GPU_PACKAGE_POWER_REF],
)
p_gpu_interconnect = var(
    "gpu.power.interconnect", "P_GPU_int", "W",
    "Power spent driving NVLink and scale-out traffic.",
    scope="gpu",
    sp_units=WATT,
    references=[GPU_PACKAGE_POWER_REF],
)
p_gpu_total = var(
    "gpu.power.total", "P_GPU_tot", "W",
    "Total package power from compute, memory, and interconnect terms.",
    scope="gpu",
    sp_units=WATT,
    references=[GPU_PACKAGE_POWER_REF],
)
p_gpu_headroom = var(
    "gpu.power.headroom", "P_head_GPU", "W",
    "Signed TDP headroom. Negative means the modeled operating point exceeds package TDP.",
    scope="gpu",
    positive=False,
    sp_units=WATT,
    references=[GPU_PACKAGE_POWER_REF],
)
tdp_utilization = var(
    "gpu.power.tdp_utilization", "rho_TDP_GPU", "dimensionless",
    "Fraction of TDP currently consumed by the modeled package operating point.",
    scope="gpu",
    sp_units=DIMENSIONLESS,
    references=[GPU_PACKAGE_POWER_REF],
)
power_throttle_factor = var(
    "gpu.power.throttle_factor", "phi_throttle_GPU", "dimensionless",
    "Multiplicative throttle factor that clips effective peak throughput when modeled power exceeds TDP.",
    scope="gpu",
    sp_units=DIMENSIONLESS,
    references=[GPU_PACKAGE_POWER_REF],
)
flops_per_joule_peak = var(
    "gpu.flops_per_joule_peak", "F_J_GPU", "FLOP/J",
    "Peak FLOPs delivered per joule at the current package operating point.",
    scope="gpu",
    sp_units=FLOPS / WATT,
    references=[GPU_PACKAGE_POWER_REF],
)
joules_per_flop_peak = var(
    "gpu.joules_per_flop_peak", "J_F_GPU", "J/FLOP",
    "Reciprocal peak energy efficiency of the package.",
    scope="gpu",
    sp_units=WATT / FLOPS,
    references=[GPU_PACKAGE_POWER_REF],
)
hbm_bytes_per_joule_peak = var(
    "gpu.hbm.bytes_per_joule_peak", "B_J_HBM_GPU", "byte/J",
    "Effective HBM bytes delivered per joule at the current package operating point.",
    scope="gpu",
    sp_units=BPS / WATT,
    references=[GPU_PACKAGE_POWER_REF],
)
hbm_sweep_time = var(
    "gpu.hbm.sweep_time", "T_sweep_HBM_GPU", "s",
    "Time required to stream once through the effective HBM capacity at effective HBM bandwidth.",
    scope="gpu",
    sp_units=SECOND,
    references=[GPU_PACKAGE_POWER_REF],
)

eq_gpu_compute_sm_power = eq(
    "gpu.eq.compute_sm_power",
    p_gpu_compute_sm.symbol,
    n_sms.symbol * active_equiv_gates_per_sm.symbol * P_total_gate.symbol,
    "SM-local compute power equals equivalent active gates per SM times lower-scope per-gate power, aggregated over all SMs.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)
eq_gpu_compute_uncore_power = eq(
    "gpu.eq.compute_uncore_power",
    p_gpu_compute_uncore.symbol,
    active_equiv_gates_uncore.symbol * P_total_gate.symbol,
    "Uncore package power is modeled as equivalent uncore gate count times lower-scope per-gate power.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)
eq_gpu_compute_power = eq(
    "gpu.eq.compute_power",
    p_gpu_compute.symbol,
    p_gpu_compute_sm.symbol + p_gpu_compute_uncore.symbol,
    "Compute-domain package power adds SM-local and uncore logic power.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)
eq_gpu_memory_power = eq(
    "gpu.eq.memory_power",
    p_gpu_memory.symbol,
    hbm_utilization.symbol * hbm_bw_gpu_effective.symbol * e_per_byte_hbm.symbol,
    "HBM power is modeled as active HBM byte rate times HBM energy per byte.",
    references=[GPU_PACKAGE_POWER_REF],
)
eq_gpu_interconnect_power = eq(
    "gpu.eq.interconnect_power",
    p_gpu_interconnect.symbol,
    nvlink_tx_bw.symbol * e_per_byte_nvlink.symbol + nic_tx_bw.symbol * e_per_byte_nic.symbol,
    "Interconnect power is payload byte rate on each fabric times that fabric's energy per byte.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)
eq_gpu_power = eq(
    "gpu.eq.power_total",
    p_gpu_total.symbol,
    p_gpu_compute.symbol + p_gpu_memory.symbol + p_gpu_interconnect.symbol,
    "Total GPU package power decomposes into compute, memory, and interconnect terms.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)
eq_gpu_power_headroom = eq(
    "gpu.eq.power_headroom",
    p_gpu_headroom.symbol,
    tdp_gpu.symbol - p_gpu_total.symbol,
    "TDP headroom is package TDP minus the modeled package power.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)
eq_tdp_utilization = eq(
    "gpu.eq.tdp_utilization",
    tdp_utilization.symbol,
    p_gpu_total.symbol / tdp_gpu.symbol,
    "TDP utilization is modeled package power divided by package TDP.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)
eq_power_throttle_factor = PiecewiseEquation(
    "gpu.eq.power_throttle_factor",
    power_throttle_factor.symbol,
    [
        (1, p_gpu_total.symbol <= tdp_gpu.symbol),
        (tdp_gpu.symbol / p_gpu_total.symbol, True),
    ],
    "The package is unthrottled below TDP, and otherwise its effective peak is scaled down in proportion to TDP over modeled power.",
    references=[GPU_PACKAGE_POWER_REF],
)
eq_peak_flops_gpu_power_limited = eq(
    "gpu.eq.peak_flops_power_limited",
    peak_flops_gpu_power_limited.symbol,
    power_throttle_factor.symbol * peak_flops_gpu_effective.symbol,
    "Power-limited effective peak equals issue-efficiency-limited peak times the power-throttle factor.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)
eq_flops_per_joule_peak = eq(
    "gpu.eq.flops_per_joule_peak",
    flops_per_joule_peak.symbol,
    peak_flops_gpu_power_limited.symbol / p_gpu_total.symbol,
    "Peak FLOPs per joule equals power-limited effective peak throughput divided by package power.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)
eq_joules_per_flop_peak = eq(
    "gpu.eq.joules_per_flop_peak",
    joules_per_flop_peak.symbol,
    p_gpu_total.symbol / peak_flops_gpu_power_limited.symbol,
    "Joules per FLOP is the reciprocal of peak FLOPs per joule.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)
eq_hbm_bytes_per_joule_peak = eq(
    "gpu.eq.hbm_bytes_per_joule_peak",
    hbm_bytes_per_joule_peak.symbol,
    hbm_bw_gpu_effective.symbol / p_gpu_total.symbol,
    "HBM bytes per joule equals effective HBM bandwidth divided by package power.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)
eq_hbm_sweep_time = eq(
    "gpu.eq.hbm_sweep_time",
    hbm_sweep_time.symbol,
    hbm_capacity_gpu_effective.symbol / hbm_bw_gpu_effective.symbol,
    "Streaming once through effective HBM capacity takes capacity divided by effective bandwidth.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)


# ---------------------------------------------------------------------------
# Memory / compute balance
# ---------------------------------------------------------------------------

ai_balance_gpu = var(
    "gpu.balance_point", "AI_bal", "FLOP/byte",
    "Raw GPU roofline balance point, using raw peak FLOPs and raw HBM bandwidth.",
    scope="gpu",
    sp_units=FLOPS / BPS,
    references=[GPU_PACKAGE_POWER_REF],
)
ai_balance_gpu_effective = var(
    "gpu.balance_point_effective", "AI_bal_eff", "FLOP/byte",
    "Effective balance point using power-limited effective compute and effective HBM bandwidth.",
    scope="gpu",
    sp_units=FLOPS / BPS,
    references=[GPU_PACKAGE_POWER_REF],
)
bytes_per_flop_gpu_effective = var(
    "gpu.bytes_per_flop_effective", "B_F_GPU_eff", "byte/FLOP",
    "Inverse of the effective balance point, useful as a memory-balance check.",
    scope="gpu",
    sp_units=BPS / FLOPS,
    references=[GPU_PACKAGE_POWER_REF],
)

eq_ai_balance = eq(
    "gpu.eq.balance_point",
    ai_balance_gpu.symbol,
    peak_flops_gpu.symbol / hbm_bw.symbol,
    "Raw roofline balance point equals raw peak FLOPs divided by raw HBM bandwidth.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)
eq_ai_balance_effective = eq(
    "gpu.eq.balance_point_effective",
    ai_balance_gpu_effective.symbol,
    peak_flops_gpu_power_limited.symbol / hbm_bw_gpu_effective.symbol,
    "Effective balance point equals power-limited effective peak divided by effective HBM bandwidth.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)
eq_bytes_per_flop_gpu_effective = eq(
    "gpu.eq.bytes_per_flop_effective",
    bytes_per_flop_gpu_effective.symbol,
    hbm_bw_gpu_effective.symbol / peak_flops_gpu_power_limited.symbol,
    "Effective bytes per FLOP is the reciprocal of the effective balance point.",
    references=[GPU_PACKAGE_POWER_REF],
    check_units=True,
)


GPU_POWER_VARIABLES = (
    tdp_gpu,
    active_equiv_gates_per_sm,
    active_equiv_gates_uncore,
    p_gpu_compute_sm,
    p_gpu_compute_uncore,
    p_gpu_compute,
    hbm_utilization,
    p_gpu_memory,
    e_per_byte_nvlink,
    e_per_byte_nic,
    p_gpu_interconnect,
    p_gpu_total,
    p_gpu_headroom,
    tdp_utilization,
    power_throttle_factor,
    flops_per_joule_peak,
    joules_per_flop_peak,
    hbm_bytes_per_joule_peak,
    hbm_sweep_time,
    ai_balance_gpu,
    ai_balance_gpu_effective,
    bytes_per_flop_gpu_effective,
)

GPU_POWER_EQUATIONS = (
    eq_gpu_compute_sm_power,
    eq_gpu_compute_uncore_power,
    eq_gpu_compute_power,
    eq_gpu_memory_power,
    eq_gpu_interconnect_power,
    eq_gpu_power,
    eq_gpu_power_headroom,
    eq_tdp_utilization,
    eq_power_throttle_factor,
    eq_peak_flops_gpu_power_limited,
    eq_flops_per_joule_peak,
    eq_joules_per_flop_peak,
    eq_hbm_bytes_per_joule_peak,
    eq_hbm_sweep_time,
    eq_ai_balance,
    eq_ai_balance_effective,
    eq_bytes_per_flop_gpu_effective,
)


__all__ = [
    "tdp_gpu",
    "active_equiv_gates_per_sm",
    "active_equiv_gates_uncore",
    "p_gpu_compute_sm",
    "p_gpu_compute_uncore",
    "p_gpu_compute",
    "hbm_utilization",
    "p_gpu_memory",
    "e_per_byte_nvlink",
    "e_per_byte_nic",
    "p_gpu_interconnect",
    "p_gpu_total",
    "p_gpu_headroom",
    "tdp_utilization",
    "power_throttle_factor",
    "flops_per_joule_peak",
    "joules_per_flop_peak",
    "hbm_bytes_per_joule_peak",
    "hbm_sweep_time",
    "ai_balance_gpu",
    "ai_balance_gpu_effective",
    "bytes_per_flop_gpu_effective",
    "eq_gpu_compute_sm_power",
    "eq_gpu_compute_uncore_power",
    "eq_gpu_compute_power",
    "eq_gpu_memory_power",
    "eq_gpu_interconnect_power",
    "eq_gpu_power",
    "eq_gpu_power_headroom",
    "eq_tdp_utilization",
    "eq_power_throttle_factor",
    "eq_peak_flops_gpu_power_limited",
    "eq_flops_per_joule_peak",
    "eq_joules_per_flop_peak",
    "eq_hbm_bytes_per_joule_peak",
    "eq_hbm_sweep_time",
    "eq_ai_balance",
    "eq_ai_balance_effective",
    "eq_bytes_per_flop_gpu_effective",
    "GPU_POWER_VARIABLES",
    "GPU_POWER_EQUATIONS",
]
