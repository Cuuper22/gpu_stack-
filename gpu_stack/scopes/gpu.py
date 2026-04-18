"""
scopes/gpu.py
=============

GPU-die and package-level aggregation.

The older file mostly counted SMs and then jumped straight to one peak-FLOP
number. That is too coarse. A real GPU package has several distinct ceilings:

  * raw peak throughput from SM count times per-SM arithmetic units
  * issue-efficiency-limited throughput from Tensor Core scheduling losses
  * power-limited throughput when the package would otherwise exceed TDP
  * memory capacity and bandwidth from the attached HBM stacks
  * on-chip SRAM capacity and bandwidth from register files, SMEM, TMEM, and L2
  * interconnect injection bandwidth and the power it costs to drive it

This scope makes those layers explicit while keeping the public names from the
earlier pass stable.
"""

import sympy as sp

from ..core import PiecewiseEquation, System, eq, var
from .arithmetic import (
    n_tc_per_sm,
    peak_dp2a_sm,
    peak_dp4a_sm,
    peak_flops_sm,
    peak_flops_sm_effective,
    peak_flops_sm_sparse,
    peak_sfu_ops_sm,
)
from .memory_subsystem import (
    cxl_bw,
    e_per_byte_hbm,
    hbm_bw,
    hbm_bw_effective,
    hbm_capacity,
    hbm_effective_capacity,
    hbm_pins_per_stack,
    hbm_stack_count,
    l2_bw,
    l2_bytes,
    pcie_bw,
    reg_bw_effective,
    reg_file_bytes_per_sm,
    smem_bw_per_sm,
    smem_bytes_per_sm,
    tmem_bw_per_sm,
    tmem_bytes_per_sm,
)
from .physical import P_total_gate


sys_gpu = System(
    name="gpu",
    scope="gpu",
    description="SM counts, package bandwidth, on-chip memory, interconnect injection, and package-level power.",
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


# ---------------------------------------------------------------------------
# On-chip memory and bandwidth aggregation
# ---------------------------------------------------------------------------

reg_bytes_gpu = var(
    "gpu.reg.bytes", "B_reg_GPU", "byte",
    "Total register-file capacity aggregated across all SMs.",
    scope="gpu",
)
smem_bytes_gpu = var(
    "gpu.smem.bytes", "B_smem_GPU", "byte",
    "Total software-managed shared-memory capacity aggregated across all SMs.",
    scope="gpu",
)
tmem_bytes_gpu = var(
    "gpu.tmem.bytes", "B_tmem_GPU", "byte",
    "Total TMEM capacity aggregated across all SMs.",
    scope="gpu",
)
l2_bytes_gpu = var(
    "gpu.l2.bytes", "B_L2_GPU", "byte",
    "L2 capacity exposed as a GPU-level variable for higher scopes.",
    scope="gpu",
)
onchip_sram_bytes_gpu = var(
    "gpu.onchip_sram.bytes", "B_onchip_GPU", "byte",
    "Aggregate on-chip memory capacity from register files, SMEM, TMEM, and L2.",
    scope="gpu",
)
reg_bw_gpu = var(
    "gpu.reg.bw", "BW_reg_GPU", "byte/s",
    "Aggregate effective register-file bandwidth across all SMs.",
    scope="gpu",
)
smem_bw_gpu = var(
    "gpu.smem.bw", "BW_smem_GPU", "byte/s",
    "Aggregate shared-memory bandwidth across all SMs.",
    scope="gpu",
)
tmem_bw_gpu = var(
    "gpu.tmem.bw", "BW_tmem_GPU", "byte/s",
    "Aggregate TMEM bandwidth across all SMs.",
    scope="gpu",
)
l2_bw_gpu = var(
    "gpu.l2.bw", "BW_L2_GPU", "byte/s",
    "L2 bandwidth exposed as a GPU-level variable for higher scopes.",
    scope="gpu",
)

eq_reg_bytes_gpu = eq(
    "gpu.eq.reg_bytes",
    reg_bytes_gpu.symbol,
    n_sms.symbol * reg_file_bytes_per_sm.symbol,
    "Total register-file capacity equals per-SM register bytes times SM count.",
)
eq_smem_bytes_gpu = eq(
    "gpu.eq.smem_bytes",
    smem_bytes_gpu.symbol,
    n_sms.symbol * smem_bytes_per_sm.symbol,
    "Total SMEM capacity equals per-SM SMEM bytes times SM count.",
)
eq_tmem_bytes_gpu = eq(
    "gpu.eq.tmem_bytes",
    tmem_bytes_gpu.symbol,
    n_sms.symbol * tmem_bytes_per_sm.symbol,
    "Total TMEM capacity equals per-SM TMEM bytes times SM count.",
)
eq_l2_bytes_gpu = eq(
    "gpu.eq.l2_bytes",
    l2_bytes_gpu.symbol,
    l2_bytes.symbol,
    "GPU-level L2 capacity is the underlying package L2 capacity.",
)
eq_onchip_sram_bytes_gpu = eq(
    "gpu.eq.onchip_sram_bytes",
    onchip_sram_bytes_gpu.symbol,
    reg_bytes_gpu.symbol + smem_bytes_gpu.symbol + tmem_bytes_gpu.symbol + l2_bytes_gpu.symbol,
    "On-chip memory adds register files, SMEM, TMEM, and L2.",
)
eq_reg_bw_gpu = eq(
    "gpu.eq.reg_bw",
    reg_bw_gpu.symbol,
    n_sms.symbol * reg_bw_effective.symbol,
    "Aggregate register bandwidth equals effective per-SM register bandwidth times SM count.",
)
eq_smem_bw_gpu = eq(
    "gpu.eq.smem_bw",
    smem_bw_gpu.symbol,
    n_sms.symbol * smem_bw_per_sm.symbol,
    "Aggregate SMEM bandwidth equals per-SM SMEM bandwidth times SM count.",
)
eq_tmem_bw_gpu = eq(
    "gpu.eq.tmem_bw",
    tmem_bw_gpu.symbol,
    n_sms.symbol * tmem_bw_per_sm.symbol,
    "Aggregate TMEM bandwidth equals per-SM TMEM bandwidth times SM count.",
)
eq_l2_bw_gpu = eq(
    "gpu.eq.l2_bw",
    l2_bw_gpu.symbol,
    l2_bw.symbol,
    "GPU-level L2 bandwidth is the underlying package L2 bandwidth.",
)


# ---------------------------------------------------------------------------
# HBM package view
# ---------------------------------------------------------------------------

hbm_bw_gpu_effective = var(
    "gpu.hbm.bw_effective", "BW_HBM_GPU_eff", "byte/s",
    "Effective HBM bandwidth for the GPU package after refresh overhead.",
    scope="gpu",
)
hbm_capacity_gpu_effective = var(
    "gpu.hbm.capacity_effective", "B_HBM_GPU_eff", "byte",
    "Effective HBM capacity after ECC and compression effects.",
    scope="gpu",
)
hbm_pins_total = var(
    "gpu.hbm.pins_total", "N_pins_HBM_GPU", "pins",
    "Total HBM data pins across all attached HBM stacks.",
    scope="gpu",
    integer=True,
)
hbm_bw_per_pin = var(
    "gpu.hbm.bw_per_pin", "BW_pin_HBM_GPU", "byte/s/pin",
    "Average effective HBM bandwidth per data pin at the package edge.",
    scope="gpu",
)
hbm_bw_per_stack_avg = var(
    "gpu.hbm.bw_per_stack_avg", "BW_stack_HBM_GPU", "byte/s",
    "Average effective bandwidth carried by one HBM stack.",
    scope="gpu",
)
hbm_capacity_per_stack_avg = var(
    "gpu.hbm.capacity_per_stack_avg", "B_stack_HBM_GPU", "byte",
    "Average effective capacity provided by one HBM stack.",
    scope="gpu",
)
hbm_sweep_time = var(
    "gpu.hbm.sweep_time", "T_sweep_HBM_GPU", "s",
    "Time required to stream once through the effective HBM capacity at effective HBM bandwidth.",
    scope="gpu",
)

eq_hbm_bw_gpu_effective = eq(
    "gpu.eq.hbm_bw_effective",
    hbm_bw_gpu_effective.symbol,
    hbm_bw_effective.symbol,
    "GPU-level effective HBM bandwidth aliases the lower-scope HBM effective bandwidth.",
)
eq_hbm_capacity_gpu_effective = eq(
    "gpu.eq.hbm_capacity_effective",
    hbm_capacity_gpu_effective.symbol,
    hbm_effective_capacity.symbol,
    "GPU-level effective HBM capacity aliases the lower-scope effective HBM capacity.",
)
eq_hbm_pins_total = eq(
    "gpu.eq.hbm_pins_total",
    hbm_pins_total.symbol,
    hbm_stack_count.symbol * hbm_pins_per_stack.symbol,
    "Total HBM pins equal stack count times pins per stack.",
)
eq_hbm_bw_per_pin = eq(
    "gpu.eq.hbm_bw_per_pin",
    hbm_bw_per_pin.symbol,
    hbm_bw_gpu_effective.symbol / hbm_pins_total.symbol,
    "Average effective HBM bandwidth per pin equals effective package bandwidth divided by total HBM pins.",
)
eq_hbm_bw_per_stack_avg = eq(
    "gpu.eq.hbm_bw_per_stack_avg",
    hbm_bw_per_stack_avg.symbol,
    hbm_bw_gpu_effective.symbol / hbm_stack_count.symbol,
    "Average effective HBM bandwidth per stack equals package bandwidth divided by stack count.",
)
eq_hbm_capacity_per_stack_avg = eq(
    "gpu.eq.hbm_capacity_per_stack_avg",
    hbm_capacity_per_stack_avg.symbol,
    hbm_capacity_gpu_effective.symbol / hbm_stack_count.symbol,
    "Average effective HBM capacity per stack equals package effective capacity divided by stack count.",
)
eq_hbm_sweep_time = eq(
    "gpu.eq.hbm_sweep_time",
    hbm_sweep_time.symbol,
    hbm_capacity_gpu_effective.symbol / hbm_bw_gpu_effective.symbol,
    "Streaming once through effective HBM capacity takes capacity divided by effective bandwidth.",
)


# ---------------------------------------------------------------------------
# Package power: compute, HBM, interconnect
# ---------------------------------------------------------------------------

tdp_gpu = var(
    "gpu.tdp", "TDP_GPU", "W",
    "Thermal design power for one GPU package.",
    scope="gpu",
)
active_equiv_gates_per_sm = var(
    "gpu.power.equiv_gates_per_sm", "N_gate_eq_SM_GPU", "gates",
    "Equivalent number of simultaneously modeled logic gates per SM that carry the lower-scope per-gate power model.",
    scope="gpu",
)
active_equiv_gates_uncore = var(
    "gpu.power.equiv_gates_uncore", "N_gate_eq_uncore_GPU", "gates",
    "Equivalent package-level uncore logic gates, such as front-end, fabric, and control logic.",
    scope="gpu",
)
p_gpu_compute_sm = var(
    "gpu.power.compute_sm", "P_GPU_SM", "W",
    "SM-local compute power aggregated across all SMs.",
    scope="gpu",
)
p_gpu_compute_uncore = var(
    "gpu.power.compute_uncore", "P_GPU_uncore", "W",
    "Uncore compute and control power at package scope.",
    scope="gpu",
)
p_gpu_compute = var(
    "gpu.power.compute", "P_GPU_comp", "W",
    "Total compute-domain power from SM-local and uncore logic.",
    scope="gpu",
)
hbm_utilization = var(
    "gpu.hbm.utilization", "rho_HBM_GPU", "dimensionless",
    "Average fraction of effective HBM bandwidth actively exercised by the workload.",
    scope="gpu",
)
p_gpu_memory = var(
    "gpu.power.memory", "P_GPU_mem", "W",
    "Power dissipated by HBM transfers under the current memory-utilization point.",
    scope="gpu",
)
nvlink_protocol_efficiency = var(
    "gpu.nvlink.protocol_efficiency", "eta_NVL_proto_GPU", "dimensionless",
    "Fraction of NVLink line rate that becomes payload bandwidth after framing and protocol overhead.",
    scope="gpu",
)
nvlink_lanes_per_gpu = var(
    "gpu.nvlink.lanes", "N_NVL", "lanes",
    "Number of NVLink lanes or ports exposed by one GPU package.",
    scope="gpu",
    integer=True,
)
nvlink_rate_per_lane = var(
    "gpu.nvlink.rate_per_lane", "r_NVL_lane", "byte/s",
    "Raw NVLink bandwidth per lane or port before protocol overhead.",
    scope="gpu",
)
nvlink_bw_per_gpu = var(
    "gpu.nvlink.bw", "BW_NVL_GPU", "byte/s",
    "Raw aggregate NVLink injection bandwidth per GPU package.",
    scope="gpu",
)
nvlink_bw_per_gpu_effective = var(
    "gpu.nvlink.bw_effective", "BW_NVL_GPU_eff", "byte/s",
    "Effective NVLink payload bandwidth per GPU after protocol overhead.",
    scope="gpu",
)
nvlink_utilization = var(
    "gpu.nvlink.utilization", "rho_NVL_GPU", "dimensionless",
    "Average fraction of effective NVLink bandwidth currently exercised.",
    scope="gpu",
)
nvlink_tx_bw = var(
    "gpu.nvlink.tx_bw", "BW_NVL_tx_GPU", "byte/s",
    "Actual NVLink payload bandwidth injected by the workload.",
    scope="gpu",
)
e_per_byte_nvlink = var(
    "gpu.nvlink.energy_per_byte", "E_B_NVL_GPU", "J/byte",
    "Energy spent per NVLink byte transferred at the package boundary.",
    scope="gpu",
)
nic_protocol_efficiency = var(
    "gpu.nic.protocol_efficiency", "eta_NIC_proto_GPU", "dimensionless",
    "Fraction of NIC line rate that becomes payload bandwidth after transport and packet overhead.",
    scope="gpu",
)
nic_rate_per_gpu = var(
    "gpu.nic.rate", "BW_NIC_GPU", "byte/s",
    "Raw scale-out NIC bandwidth per GPU package before protocol overhead.",
    scope="gpu",
)
nic_bw_per_gpu_effective = var(
    "gpu.nic.bw_effective", "BW_NIC_GPU_eff", "byte/s",
    "Effective scale-out payload bandwidth per GPU package after protocol overhead.",
    scope="gpu",
)
nic_utilization = var(
    "gpu.nic.utilization", "rho_NIC_GPU", "dimensionless",
    "Average fraction of effective NIC bandwidth currently exercised.",
    scope="gpu",
)
nic_tx_bw = var(
    "gpu.nic.tx_bw", "BW_NIC_tx_GPU", "byte/s",
    "Actual scale-out payload bandwidth injected by the workload.",
    scope="gpu",
)
e_per_byte_nic = var(
    "gpu.nic.energy_per_byte", "E_B_NIC_GPU", "J/byte",
    "Energy spent per scale-out byte transferred by the GPU-adjacent NIC path.",
    scope="gpu",
)
p_gpu_interconnect = var(
    "gpu.power.interconnect", "P_GPU_int", "W",
    "Power spent driving NVLink and scale-out traffic.",
    scope="gpu",
)
p_gpu_total = var(
    "gpu.power.total", "P_GPU_tot", "W",
    "Total package power from compute, memory, and interconnect terms.",
    scope="gpu",
)
p_gpu_headroom = var(
    "gpu.power.headroom", "P_head_GPU", "W",
    "Signed TDP headroom. Negative means the modeled operating point exceeds package TDP.",
    scope="gpu",
    positive=False,
)
tdp_utilization = var(
    "gpu.power.tdp_utilization", "rho_TDP_GPU", "dimensionless",
    "Fraction of TDP currently consumed by the modeled package operating point.",
    scope="gpu",
)
power_throttle_factor = var(
    "gpu.power.throttle_factor", "phi_throttle_GPU", "dimensionless",
    "Multiplicative throttle factor that clips effective peak throughput when modeled power exceeds TDP.",
    scope="gpu",
)
peak_flops_gpu_power_limited = var(
    "gpu.peak_flops_power_limited", "P_GPU_pwlim", "FLOP/s",
    "Effective per-GPU peak after issue losses and any TDP-induced power throttling.",
    scope="gpu",
)
flops_per_joule_peak = var(
    "gpu.flops_per_joule_peak", "F_J_GPU", "FLOP/J",
    "Peak FLOPs delivered per joule at the current package operating point.",
    scope="gpu",
)
joules_per_flop_peak = var(
    "gpu.joules_per_flop_peak", "J_F_GPU", "J/FLOP",
    "Reciprocal peak energy efficiency of the package.",
    scope="gpu",
)
hbm_bytes_per_joule_peak = var(
    "gpu.hbm.bytes_per_joule_peak", "B_J_HBM_GPU", "byte/J",
    "Effective HBM bytes delivered per joule at the current package operating point.",
    scope="gpu",
)

eq_gpu_compute_sm_power = eq(
    "gpu.eq.compute_sm_power",
    p_gpu_compute_sm.symbol,
    n_sms.symbol * active_equiv_gates_per_sm.symbol * P_total_gate.symbol,
    "SM-local compute power equals equivalent active gates per SM times lower-scope per-gate power, aggregated over all SMs.",
)
eq_gpu_compute_uncore_power = eq(
    "gpu.eq.compute_uncore_power",
    p_gpu_compute_uncore.symbol,
    active_equiv_gates_uncore.symbol * P_total_gate.symbol,
    "Uncore package power is modeled as equivalent uncore gate count times lower-scope per-gate power.",
)
eq_gpu_compute_power = eq(
    "gpu.eq.compute_power",
    p_gpu_compute.symbol,
    p_gpu_compute_sm.symbol + p_gpu_compute_uncore.symbol,
    "Compute-domain package power adds SM-local and uncore logic power.",
)
eq_nvlink_bw = eq(
    "gpu.eq.nvlink_bw",
    nvlink_bw_per_gpu.symbol,
    nvlink_lanes_per_gpu.symbol * nvlink_rate_per_lane.symbol,
    "Raw aggregate NVLink bandwidth equals lane count times lane rate.",
)
eq_nvlink_bw_effective = eq(
    "gpu.eq.nvlink_bw_effective",
    nvlink_bw_per_gpu_effective.symbol,
    nvlink_bw_per_gpu.symbol * nvlink_protocol_efficiency.symbol,
    "Effective NVLink payload bandwidth equals raw NVLink bandwidth times protocol efficiency.",
)
eq_nvlink_tx_bw = eq(
    "gpu.eq.nvlink_tx_bw",
    nvlink_tx_bw.symbol,
    nvlink_utilization.symbol * nvlink_bw_per_gpu_effective.symbol,
    "Actual NVLink payload injection equals effective NVLink bandwidth times link utilization.",
)
eq_nic_bw_effective = eq(
    "gpu.eq.nic_bw_effective",
    nic_bw_per_gpu_effective.symbol,
    nic_rate_per_gpu.symbol * nic_protocol_efficiency.symbol,
    "Effective scale-out payload bandwidth equals raw NIC bandwidth times protocol efficiency.",
)
eq_nic_tx_bw = eq(
    "gpu.eq.nic_tx_bw",
    nic_tx_bw.symbol,
    nic_utilization.symbol * nic_bw_per_gpu_effective.symbol,
    "Actual scale-out payload injection equals effective NIC bandwidth times utilization.",
)
eq_gpu_memory_power = eq(
    "gpu.eq.memory_power",
    p_gpu_memory.symbol,
    hbm_utilization.symbol * hbm_bw_gpu_effective.symbol * e_per_byte_hbm.symbol,
    "HBM power is modeled as active HBM byte rate times HBM energy per byte.",
)
eq_gpu_interconnect_power = eq(
    "gpu.eq.interconnect_power",
    p_gpu_interconnect.symbol,
    nvlink_tx_bw.symbol * e_per_byte_nvlink.symbol + nic_tx_bw.symbol * e_per_byte_nic.symbol,
    "Interconnect power is payload byte rate on each fabric times that fabric's energy per byte.",
)
eq_gpu_power = eq(
    "gpu.eq.power_total",
    p_gpu_total.symbol,
    p_gpu_compute.symbol + p_gpu_memory.symbol + p_gpu_interconnect.symbol,
    "Total GPU package power decomposes into compute, memory, and interconnect terms.",
)
eq_gpu_power_headroom = eq(
    "gpu.eq.power_headroom",
    p_gpu_headroom.symbol,
    tdp_gpu.symbol - p_gpu_total.symbol,
    "TDP headroom is package TDP minus the modeled package power.",
)
eq_tdp_utilization = eq(
    "gpu.eq.tdp_utilization",
    tdp_utilization.symbol,
    p_gpu_total.symbol / tdp_gpu.symbol,
    "TDP utilization is modeled package power divided by package TDP.",
)
eq_power_throttle_factor = PiecewiseEquation(
    "gpu.eq.power_throttle_factor",
    power_throttle_factor.symbol,
    [
        (1, p_gpu_total.symbol <= tdp_gpu.symbol),
        (tdp_gpu.symbol / p_gpu_total.symbol, True),
    ],
    "The package is unthrottled below TDP, and otherwise its effective peak is scaled down in proportion to TDP over modeled power.",
)
eq_peak_flops_gpu_power_limited = eq(
    "gpu.eq.peak_flops_power_limited",
    peak_flops_gpu_power_limited.symbol,
    power_throttle_factor.symbol * peak_flops_gpu_effective.symbol,
    "Power-limited effective peak equals issue-efficiency-limited peak times the power-throttle factor.",
)
eq_flops_per_joule_peak = eq(
    "gpu.eq.flops_per_joule_peak",
    flops_per_joule_peak.symbol,
    peak_flops_gpu_power_limited.symbol / p_gpu_total.symbol,
    "Peak FLOPs per joule equals power-limited effective peak throughput divided by package power.",
)
eq_joules_per_flop_peak = eq(
    "gpu.eq.joules_per_flop_peak",
    joules_per_flop_peak.symbol,
    p_gpu_total.symbol / peak_flops_gpu_power_limited.symbol,
    "Joules per FLOP is the reciprocal of peak FLOPs per joule.",
)
eq_hbm_bytes_per_joule_peak = eq(
    "gpu.eq.hbm_bytes_per_joule_peak",
    hbm_bytes_per_joule_peak.symbol,
    hbm_bw_gpu_effective.symbol / p_gpu_total.symbol,
    "HBM bytes per joule equals effective HBM bandwidth divided by package power.",
)


# ---------------------------------------------------------------------------
# Memory / compute balance and host-link aliases
# ---------------------------------------------------------------------------

pcie_bw_gpu = var(
    "gpu.pcie.bw", "BW_PCIE_GPU", "byte/s",
    "GPU-visible PCIe bandwidth alias for higher scopes.",
    scope="gpu",
)
cxl_bw_gpu = var(
    "gpu.cxl.bw", "BW_CXL_GPU", "byte/s",
    "GPU-visible CXL bandwidth alias for higher scopes.",
    scope="gpu",
)
ai_balance_gpu = var(
    "gpu.balance_point", "AI_bal", "FLOP/byte",
    "Raw GPU roofline balance point, using raw peak FLOPs and raw HBM bandwidth.",
    scope="gpu",
)
ai_balance_gpu_effective = var(
    "gpu.balance_point_effective", "AI_bal_eff", "FLOP/byte",
    "Effective balance point using power-limited effective compute and effective HBM bandwidth.",
    scope="gpu",
)
bytes_per_flop_gpu_effective = var(
    "gpu.bytes_per_flop_effective", "B_F_GPU_eff", "byte/FLOP",
    "Inverse of the effective balance point, useful as a memory-balance check.",
    scope="gpu",
)

eq_pcie_bw_gpu = eq(
    "gpu.eq.pcie_bw",
    pcie_bw_gpu.symbol,
    pcie_bw.symbol,
    "GPU-level PCIe bandwidth aliases the lower-scope PCIe bandwidth variable.",
)
eq_cxl_bw_gpu = eq(
    "gpu.eq.cxl_bw",
    cxl_bw_gpu.symbol,
    cxl_bw.symbol,
    "GPU-level CXL bandwidth aliases the lower-scope CXL bandwidth variable.",
)
eq_ai_balance = eq(
    "gpu.eq.balance_point",
    ai_balance_gpu.symbol,
    peak_flops_gpu.symbol / hbm_bw.symbol,
    "Raw roofline balance point equals raw peak FLOPs divided by raw HBM bandwidth.",
)
eq_ai_balance_effective = eq(
    "gpu.eq.balance_point_effective",
    ai_balance_gpu_effective.symbol,
    peak_flops_gpu_power_limited.symbol / hbm_bw_gpu_effective.symbol,
    "Effective balance point equals power-limited effective peak divided by effective HBM bandwidth.",
)
eq_bytes_per_flop_gpu_effective = eq(
    "gpu.eq.bytes_per_flop_effective",
    bytes_per_flop_gpu_effective.symbol,
    hbm_bw_gpu_effective.symbol / peak_flops_gpu_power_limited.symbol,
    "Effective bytes per FLOP is the reciprocal of the effective balance point.",
)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

for v in [
    n_sms,
    n_tc_per_gpu,
    peak_flops_gpu,
    peak_flops_gpu_effective,
    peak_flops_gpu_sparse,
    peak_dp4a_gpu,
    peak_dp2a_gpu,
    peak_sfu_gpu,
    reg_bytes_gpu,
    smem_bytes_gpu,
    tmem_bytes_gpu,
    l2_bytes_gpu,
    onchip_sram_bytes_gpu,
    reg_bw_gpu,
    smem_bw_gpu,
    tmem_bw_gpu,
    l2_bw_gpu,
    hbm_bw_gpu_effective,
    hbm_capacity_gpu_effective,
    hbm_pins_total,
    hbm_bw_per_pin,
    hbm_bw_per_stack_avg,
    hbm_capacity_per_stack_avg,
    hbm_sweep_time,
    tdp_gpu,
    active_equiv_gates_per_sm,
    active_equiv_gates_uncore,
    p_gpu_compute_sm,
    p_gpu_compute_uncore,
    p_gpu_compute,
    hbm_utilization,
    p_gpu_memory,
    nvlink_protocol_efficiency,
    nvlink_lanes_per_gpu,
    nvlink_rate_per_lane,
    nvlink_bw_per_gpu,
    nvlink_bw_per_gpu_effective,
    nvlink_utilization,
    nvlink_tx_bw,
    e_per_byte_nvlink,
    nic_protocol_efficiency,
    nic_rate_per_gpu,
    nic_bw_per_gpu_effective,
    nic_utilization,
    nic_tx_bw,
    e_per_byte_nic,
    p_gpu_interconnect,
    p_gpu_total,
    p_gpu_headroom,
    tdp_utilization,
    power_throttle_factor,
    peak_flops_gpu_power_limited,
    flops_per_joule_peak,
    joules_per_flop_peak,
    hbm_bytes_per_joule_peak,
    pcie_bw_gpu,
    cxl_bw_gpu,
    ai_balance_gpu,
    ai_balance_gpu_effective,
    bytes_per_flop_gpu_effective,
]:
    sys_gpu.add(v)

for e in [
    eq_tc_count,
    eq_peak_flops_gpu,
    eq_peak_flops_gpu_effective,
    eq_peak_flops_gpu_sparse,
    eq_peak_dp4a_gpu,
    eq_peak_dp2a_gpu,
    eq_peak_sfu_gpu,
    eq_reg_bytes_gpu,
    eq_smem_bytes_gpu,
    eq_tmem_bytes_gpu,
    eq_l2_bytes_gpu,
    eq_onchip_sram_bytes_gpu,
    eq_reg_bw_gpu,
    eq_smem_bw_gpu,
    eq_tmem_bw_gpu,
    eq_l2_bw_gpu,
    eq_hbm_bw_gpu_effective,
    eq_hbm_capacity_gpu_effective,
    eq_hbm_pins_total,
    eq_hbm_bw_per_pin,
    eq_hbm_bw_per_stack_avg,
    eq_hbm_capacity_per_stack_avg,
    eq_hbm_sweep_time,
    eq_gpu_compute_sm_power,
    eq_gpu_compute_uncore_power,
    eq_gpu_compute_power,
    eq_nvlink_bw,
    eq_nvlink_bw_effective,
    eq_nvlink_tx_bw,
    eq_nic_bw_effective,
    eq_nic_tx_bw,
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
    eq_pcie_bw_gpu,
    eq_cxl_bw_gpu,
    eq_ai_balance,
    eq_ai_balance_effective,
    eq_bytes_per_flop_gpu_effective,
]:
    sys_gpu.add(e)
