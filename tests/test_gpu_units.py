"""
tests/test_gpu_units.py
=======================

GPU-scope metadata coverage regressions.

The GPU split is where package-level compute, HBM, IO, and power paths meet.
These checks keep that surface covered with concrete unit metadata, structured
provenance, and dimensional checks on equations whose dependencies are unitful.
"""

import sympy as sp

from gpu_stack import Registry
from gpu_stack.core.units import BPS, FLOPS, METER, SECOND, WATT, byte


DIMENSIONLESS = sp.Integer(1)


def _gpu_variables():
    return [v for v in Registry.variables.values() if v.scope == "gpu"]


def _gpu_equations():
    return [
        e for e in Registry.equations.values()
        if e.name.startswith("gpu.")
    ]


def test_gpu_variables_have_units_and_references():
    gpu_vars = _gpu_variables()
    assert len(gpu_vars) >= 74
    assert [v.name for v in gpu_vars if v.sp_units is None] == []
    assert [v.name for v in gpu_vars if not v.references] == []


def test_gpu_representative_units_are_dimensional():
    assert Registry.variables["gpu.die.area"].sp_units == METER**2
    assert Registry.variables["gpu.n_sms"].sp_units == DIMENSIONLESS
    assert Registry.variables["gpu.n_tc"].sp_units == DIMENSIONLESS
    assert Registry.variables["gpu.peak_flops"].sp_units == FLOPS
    assert Registry.variables["gpu.peak_flops_power_limited"].sp_units == FLOPS
    assert Registry.variables["gpu.peak_sfu_ops"].sp_units == DIMENSIONLESS / SECOND
    assert Registry.variables["gpu.reg.bytes"].sp_units == byte
    assert Registry.variables["gpu.onchip_sram.bytes"].sp_units == byte
    assert Registry.variables["gpu.hbm.bw_effective"].sp_units == BPS
    assert Registry.variables["gpu.hbm.capacity_effective"].sp_units == byte
    assert Registry.variables["gpu.hbm.pins_total"].sp_units == DIMENSIONLESS
    assert Registry.variables["gpu.nvlink.tx_bw"].sp_units == BPS
    assert Registry.variables["gpu.nic.tx_bw"].sp_units == BPS
    assert Registry.variables["gpu.power.total"].sp_units == WATT
    assert Registry.variables["gpu.balance_point_effective"].sp_units == FLOPS / BPS


def test_gpu_equations_have_references_and_curated_unit_checks():
    gpu_eqs = _gpu_equations()
    checked = {
        e.name for e in gpu_eqs
        if getattr(e, "_check_units_flag", False)
    }

    assert len(gpu_eqs) >= 51
    assert [e.name for e in gpu_eqs if not e.references] == []
    assert len(checked) >= 32
    assert {
        "gpu.eq.tc_count",
        "gpu.eq.onchip_sram_bytes",
        "gpu.eq.hbm_bw_effective",
        "gpu.eq.hbm_capacity_effective",
        "gpu.eq.nvlink_bw_effective",
        "gpu.eq.nvlink_tx_bw",
        "gpu.eq.nic_bw_effective",
        "gpu.eq.interconnect_power",
        "gpu.eq.peak_flops_power_limited",
        "gpu.eq.flops_per_joule_peak",
        "gpu.eq.hbm_sweep_time",
        "gpu.eq.balance_point_effective",
    } <= checked
