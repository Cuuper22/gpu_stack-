"""
scopes/gpu_compute.py
=====================

GPU-die compute aggregation. SM count, Tensor Core count per package, and
raw, effective, sparse, and power-limited GPU peak FLOPs. GPU-level DP4A,
DP2A, and SFU throughput aggregated from per-SM arithmetic paths. This is
the foundation helper for the gpu scope.
"""

import sympy as sp

from ..core import Approximation, Reference, eq, var
from ..core.units import FLOPS, METER, SECOND
from .arithmetic import (
    n_tc_per_sm,
    peak_dp2a_sm,
    peak_dp4a_sm,
    peak_flops_sm,
    peak_flops_sm_effective,
    peak_flops_sm_sparse,
    peak_sfu_ops_sm,
)


_GPU_FLOORPLAN_REF = Reference(
    citation="GPU floorplanning abstraction: die area budget divided by per-SM tile area",
    kind="memo",
)
_GPU_COMPUTE_AGGREGATION_REF = Reference(
    citation="GPU compute aggregation: per-SM arithmetic throughput and functional-unit counts scale by active SM count.",
    kind="model",
)

DIMENSIONLESS = sp.Integer(1)
OPS = DIMENSIONLESS / SECOND


# ---------------------------------------------------------------------------
# SM count and die-level compute aggregates
# ---------------------------------------------------------------------------

die_area = var(
    "gpu.die.area", "A_die_gpu", "m^2",
    "Usable compute die area allocated to the GPU logic die.",
    scope="gpu",
    sp_units=METER**2,
    references=[_GPU_FLOORPLAN_REF],
)
sm_area_fraction = var(
    "gpu.floorplan.sm_area_fraction", "phi_SM_area_gpu", "dimensionless",
    "Fraction of die area budgeted for replicated SM tiles after cache, fabric, IO, and control overhead.",
    scope="gpu",
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
    references=[_GPU_FLOORPLAN_REF],
)
sm_redundancy_fraction = var(
    "gpu.floorplan.sm_redundancy_fraction", "rho_SM_red_gpu", "dimensionless",
    "Fraction of SM tile slots reserved for yield recovery, fuse-off redundancy, or disabled inventory.",
    scope="gpu",
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
    references=[_GPU_FLOORPLAN_REF],
)
sm_tile_area = var(
    "gpu.sm.tile_area", "A_SM_tile_gpu", "m^2",
    "Physical area of one SM tile including its local scheduler, register-file slice, tensor units, and routing overhead.",
    scope="gpu",
    sp_units=METER**2,
    references=[_GPU_FLOORPLAN_REF],
)
sm_tensor_core_area_per_unit = var(
    "gpu.sm.tensor_core_area_per_unit", "A_TC_unit_SM_gpu", "m^2",
    "Physical area of one Tensor Core macro inside an SM tile.",
    scope="gpu",
    sp_units=METER**2,
    references=[_GPU_FLOORPLAN_REF],
)
sm_tensor_core_area = var(
    "gpu.sm.tensor_core_area", "A_TC_SM_gpu", "m^2",
    "Total Tensor Core macro area inside one SM tile.",
    scope="gpu",
    sp_units=METER**2,
    references=[_GPU_FLOORPLAN_REF],
)
sm_register_file_area = var(
    "gpu.sm.register_file_area", "A_reg_SM_gpu", "m^2",
    "Physical area occupied by the per-SM register-file slice.",
    scope="gpu",
    sp_units=METER**2,
    references=[_GPU_FLOORPLAN_REF],
)
sm_shared_memory_area = var(
    "gpu.sm.shared_memory_area", "A_SMEM_SM_gpu", "m^2",
    "Physical area occupied by the per-SM shared-memory slice.",
    scope="gpu",
    sp_units=METER**2,
    references=[_GPU_FLOORPLAN_REF],
)
sm_scheduler_control_area = var(
    "gpu.sm.scheduler_control_area", "A_sched_ctrl_SM_gpu", "m^2",
    "Physical area for warp schedulers, scoreboards, issue control, and local SM control logic.",
    scope="gpu",
    sp_units=METER**2,
    references=[_GPU_FLOORPLAN_REF],
)
sm_local_interconnect_area = var(
    "gpu.sm.local_interconnect_area", "A_local_xbar_SM_gpu", "m^2",
    "Physical area for local operand routing, crossbars, and in-tile interconnect.",
    scope="gpu",
    sp_units=METER**2,
    references=[_GPU_FLOORPLAN_REF],
)
sm_tile_active_area = var(
    "gpu.sm.tile_active_area", "A_SM_active_gpu", "m^2",
    "Named active SM block area before layout utilization and floorplan overhead.",
    scope="gpu",
    sp_units=METER**2,
    references=[_GPU_FLOORPLAN_REF],
)
sm_tile_layout_utilization = var(
    "gpu.sm.tile_layout_utilization", "eta_SM_layout_gpu", "dimensionless",
    "Fraction of the SM tile floorplan occupied by named active blocks.",
    scope="gpu",
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
    references=[_GPU_FLOORPLAN_REF],
)
sm_tile_overhead_fraction = var(
    "gpu.sm.tile_overhead_fraction", "phi_SM_overhead_gpu", "dimensionless",
    "Fractional area overhead for power grid, clocking, spare structures, scan, and guard bands.",
    scope="gpu",
    value_range=(0.0, 1.0),
    sp_units=DIMENSIONLESS,
    references=[_GPU_FLOORPLAN_REF],
)
n_sms_area_capacity = var(
    "gpu.n_sms_area_capacity", "N_SM_area_cap", "units",
    "Continuous SM tile capacity from the die-area floorplan before integer flooring.",
    scope="gpu",
    sp_units=DIMENSIONLESS,
    references=[_GPU_FLOORPLAN_REF],
)
n_sms = var(
    "gpu.n_sms", "N_SM", "units",
    "Number of SMs on one GPU die.",
    scope="gpu",
    integer=True,
    nonnegative=True,
    sp_units=DIMENSIONLESS,
    references=[_GPU_FLOORPLAN_REF],
)
n_tc_per_gpu = var(
    "gpu.n_tc", "N_TC", "units",
    "Total Tensor Cores on one GPU package.",
    scope="gpu",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[_GPU_COMPUTE_AGGREGATION_REF],
)
peak_flops_gpu = var(
    "gpu.peak_flops", "P_GPU", "FLOP/s",
    "Raw peak FLOPs per GPU, before issue losses or package-level throttling.",
    scope="gpu",
    sp_units=FLOPS,
    references=[_GPU_COMPUTE_AGGREGATION_REF],
)
peak_flops_gpu_effective = var(
    "gpu.peak_flops_effective", "P_GPU_eff", "FLOP/s",
    "Issue-efficiency-limited peak FLOPs per GPU from effective per-SM throughput.",
    scope="gpu",
    sp_units=FLOPS,
    references=[_GPU_COMPUTE_AGGREGATION_REF],
)
peak_flops_gpu_sparse = var(
    "gpu.peak_flops_sparse", "P_GPU_sparse", "FLOP/s",
    "Structured-sparse dense-equivalent peak FLOPs per GPU.",
    scope="gpu",
    sp_units=FLOPS,
    references=[_GPU_COMPUTE_AGGREGATION_REF],
)
peak_dp4a_gpu = var(
    "gpu.peak_dp4a_ops", "P_GPU_dp4a", "op/s",
    "Peak DP4A integer throughput aggregated across all SMs.",
    scope="gpu",
    sp_units=OPS,
    references=[_GPU_COMPUTE_AGGREGATION_REF],
)
peak_dp2a_gpu = var(
    "gpu.peak_dp2a_ops", "P_GPU_dp2a", "op/s",
    "Peak DP2A integer throughput aggregated across all SMs.",
    scope="gpu",
    sp_units=OPS,
    references=[_GPU_COMPUTE_AGGREGATION_REF],
)
peak_sfu_gpu = var(
    "gpu.peak_sfu_ops", "P_GPU_sfu", "op/s",
    "Peak SFU throughput aggregated across all SMs.",
    scope="gpu",
    sp_units=OPS,
    references=[_GPU_COMPUTE_AGGREGATION_REF],
)
peak_flops_gpu_power_limited = var(
    "gpu.peak_flops_power_limited", "P_GPU_pwlim", "FLOP/s",
    "Effective per-GPU peak after issue losses and any TDP-induced power throttling.",
    scope="gpu",
    sp_units=FLOPS,
    references=[_GPU_COMPUTE_AGGREGATION_REF],
)

eq_sm_tensor_core_area = eq(
    "gpu.eq.sm_tensor_core_area",
    sm_tensor_core_area.symbol,
    n_tc_per_sm.symbol * sm_tensor_core_area_per_unit.symbol,
    "Total Tensor Core area equals Tensor Cores per SM times the area of one Tensor Core macro.",
    references=[_GPU_FLOORPLAN_REF],
    check_units=True,
)
eq_sm_tile_active_area = eq(
    "gpu.eq.sm_tile_active_area",
    sm_tile_active_area.symbol,
    (
        sm_tensor_core_area.symbol
        + sm_register_file_area.symbol
        + sm_shared_memory_area.symbol
        + sm_scheduler_control_area.symbol
        + sm_local_interconnect_area.symbol
    ),
    "Active SM tile area sums Tensor Core, register-file, shared-memory, scheduler/control, and local-interconnect blocks.",
    references=[_GPU_FLOORPLAN_REF],
    check_units=True,
)
eq_sm_tile_area = eq(
    "gpu.eq.sm_tile_area",
    sm_tile_area.symbol,
    sm_tile_active_area.symbol
    * (1 + sm_tile_overhead_fraction.symbol)
    / sm_tile_layout_utilization.symbol,
    "Budgeted SM tile area inflates named active block area by overhead and layout utilization.",
    references=[_GPU_FLOORPLAN_REF],
    check_units=True,
)
eq_n_sms_area_capacity = eq(
    "gpu.eq.n_sms_area_capacity",
    n_sms_area_capacity.symbol,
    die_area.symbol
    * sm_area_fraction.symbol
    * (1 - sm_redundancy_fraction.symbol)
    / sm_tile_area.symbol,
    "Continuous SM tile capacity from usable die area, SM area share, redundancy reserve, and per-SM tile area.",
    references=[_GPU_FLOORPLAN_REF],
    check_units=True,
)
eq_n_sms_floorplan = Approximation(
    "gpu.eq.n_sms_floorplan",
    n_sms.symbol,
    sp.floor(n_sms_area_capacity.symbol),
    sp.And(
        sm_area_fraction.symbol >= 0,
        sm_area_fraction.symbol <= 1,
        sm_redundancy_fraction.symbol >= 0,
        sm_redundancy_fraction.symbol <= 1,
    ),
    "SM count can be approximated as the integer floor of area-budgeted SM capacity.",
    references=[_GPU_FLOORPLAN_REF],
)
eq_tc_count = eq(
    "gpu.eq.tc_count",
    n_tc_per_gpu.symbol,
    n_sms.symbol * n_tc_per_sm.symbol,
    "Tensor Core count equals SM count times Tensor Cores per SM.",
    references=[_GPU_COMPUTE_AGGREGATION_REF],
    check_units=True,
)
eq_peak_flops_gpu = eq(
    "gpu.eq.peak_flops",
    peak_flops_gpu.symbol,
    n_sms.symbol * peak_flops_sm.symbol,
    "Raw peak GPU FLOPs aggregate the raw per-SM peak across all SMs.",
    references=[_GPU_COMPUTE_AGGREGATION_REF],
    check_units=True,
)
eq_peak_flops_gpu_effective = eq(
    "gpu.eq.peak_flops_effective",
    peak_flops_gpu_effective.symbol,
    n_sms.symbol * peak_flops_sm_effective.symbol,
    "Effective GPU peak aggregates the issue-efficiency-limited per-SM peak across all SMs.",
    references=[_GPU_COMPUTE_AGGREGATION_REF],
    check_units=True,
)
eq_peak_flops_gpu_sparse = eq(
    "gpu.eq.peak_flops_sparse",
    peak_flops_gpu_sparse.symbol,
    n_sms.symbol * peak_flops_sm_sparse.symbol,
    "Sparse dense-equivalent peak aggregates sparse per-SM throughput across the die.",
    references=[_GPU_COMPUTE_AGGREGATION_REF],
    check_units=True,
)
eq_peak_dp4a_gpu = eq(
    "gpu.eq.peak_dp4a",
    peak_dp4a_gpu.symbol,
    n_sms.symbol * peak_dp4a_sm.symbol,
    "Peak DP4A throughput is the per-SM DP4A peak times SM count.",
    references=[_GPU_COMPUTE_AGGREGATION_REF],
    check_units=True,
)
eq_peak_dp2a_gpu = eq(
    "gpu.eq.peak_dp2a",
    peak_dp2a_gpu.symbol,
    n_sms.symbol * peak_dp2a_sm.symbol,
    "Peak DP2A throughput is the per-SM DP2A peak times SM count.",
    references=[_GPU_COMPUTE_AGGREGATION_REF],
    check_units=True,
)
eq_peak_sfu_gpu = eq(
    "gpu.eq.peak_sfu",
    peak_sfu_gpu.symbol,
    n_sms.symbol * peak_sfu_ops_sm.symbol,
    "Peak SFU throughput is the per-SM SFU peak times SM count.",
    references=[_GPU_COMPUTE_AGGREGATION_REF],
    check_units=True,
)


GPU_COMPUTE_VARIABLES = (
    die_area,
    sm_area_fraction,
    sm_redundancy_fraction,
    sm_tile_area,
    sm_tensor_core_area_per_unit,
    sm_tensor_core_area,
    sm_register_file_area,
    sm_shared_memory_area,
    sm_scheduler_control_area,
    sm_local_interconnect_area,
    sm_tile_active_area,
    sm_tile_layout_utilization,
    sm_tile_overhead_fraction,
    n_sms_area_capacity,
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
    eq_sm_tensor_core_area,
    eq_sm_tile_active_area,
    eq_sm_tile_area,
    eq_n_sms_area_capacity,
    eq_n_sms_floorplan,
    eq_tc_count,
    eq_peak_flops_gpu,
    eq_peak_flops_gpu_effective,
    eq_peak_flops_gpu_sparse,
    eq_peak_dp4a_gpu,
    eq_peak_dp2a_gpu,
    eq_peak_sfu_gpu,
)


__all__ = [
    "die_area",
    "sm_area_fraction",
    "sm_redundancy_fraction",
    "sm_tile_area",
    "sm_tensor_core_area_per_unit",
    "sm_tensor_core_area",
    "sm_register_file_area",
    "sm_shared_memory_area",
    "sm_scheduler_control_area",
    "sm_local_interconnect_area",
    "sm_tile_active_area",
    "sm_tile_layout_utilization",
    "sm_tile_overhead_fraction",
    "n_sms_area_capacity",
    "n_sms",
    "n_tc_per_gpu",
    "peak_flops_gpu",
    "peak_flops_gpu_effective",
    "peak_flops_gpu_sparse",
    "peak_dp4a_gpu",
    "peak_dp2a_gpu",
    "peak_sfu_gpu",
    "peak_flops_gpu_power_limited",
    "eq_sm_tensor_core_area",
    "eq_sm_tile_active_area",
    "eq_sm_tile_area",
    "eq_n_sms_area_capacity",
    "eq_n_sms_floorplan",
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
