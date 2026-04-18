"""
scopes/gpu_io.py
================

GPU-level aliases for PCIe, CXL, NVLink, and NIC bandwidth. Raw and
effective NVLink and NIC bandwidths, lane counts, protocol efficiencies,
utilizations, and actual transmit bandwidth.
"""

from ..core import eq, var
from .memory_subsystem import cxl_bw, pcie_bw


# ---------------------------------------------------------------------------
# Host-link aliases
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


# ---------------------------------------------------------------------------
# NVLink
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# NIC
# ---------------------------------------------------------------------------

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


GPU_IO_VARIABLES = (
    pcie_bw_gpu,
    cxl_bw_gpu,
    nvlink_protocol_efficiency,
    nvlink_lanes_per_gpu,
    nvlink_rate_per_lane,
    nvlink_bw_per_gpu,
    nvlink_bw_per_gpu_effective,
    nvlink_utilization,
    nvlink_tx_bw,
    nic_protocol_efficiency,
    nic_rate_per_gpu,
    nic_bw_per_gpu_effective,
    nic_utilization,
    nic_tx_bw,
)

GPU_IO_EQUATIONS = (
    eq_pcie_bw_gpu,
    eq_cxl_bw_gpu,
    eq_nvlink_bw,
    eq_nvlink_bw_effective,
    eq_nvlink_tx_bw,
    eq_nic_bw_effective,
    eq_nic_tx_bw,
)


__all__ = [
    "pcie_bw_gpu",
    "cxl_bw_gpu",
    "nvlink_protocol_efficiency",
    "nvlink_lanes_per_gpu",
    "nvlink_rate_per_lane",
    "nvlink_bw_per_gpu",
    "nvlink_bw_per_gpu_effective",
    "nvlink_utilization",
    "nvlink_tx_bw",
    "nic_protocol_efficiency",
    "nic_rate_per_gpu",
    "nic_bw_per_gpu_effective",
    "nic_utilization",
    "nic_tx_bw",
    "eq_pcie_bw_gpu",
    "eq_cxl_bw_gpu",
    "eq_nvlink_bw",
    "eq_nvlink_bw_effective",
    "eq_nvlink_tx_bw",
    "eq_nic_bw_effective",
    "eq_nic_tx_bw",
    "GPU_IO_VARIABLES",
    "GPU_IO_EQUATIONS",
]
