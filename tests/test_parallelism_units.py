"""
tests/test_parallelism_units.py
================================

Focused parallelism metadata and dimensional-check coverage.
"""

import sympy as sp

from gpu_stack.core.units import BPS, SECOND, byte
from gpu_stack.scopes import parallelism


DIMENSIONLESS = sp.Integer(1)


def test_parallelism_variables_have_units_and_references():
    assert [v.name for v in parallelism.sys_par.variables if v.sp_units is None] == []
    assert [v.name for v in parallelism.sys_par.variables if not v.references] == []


def test_parallelism_equations_have_references_and_unit_checks():
    assert [eq.name for eq in parallelism.sys_par.equations if not eq.references] == []
    assert [
        eq.name
        for eq in parallelism.sys_par.equations
        if not getattr(eq, "_check_units_flag", False)
    ] == []


def test_parallelism_representative_units_cover_axes_memory_and_comm():
    assert parallelism.dp_degree.sp_units == DIMENSIONLESS
    assert parallelism.tp_degree.sp_units == DIMENSIONLESS
    assert parallelism.pp_degree.sp_units == DIMENSIONLESS
    assert parallelism.global_batch.sp_units == DIMENSIONLESS
    assert parallelism.tokens_per_step_par.sp_units == DIMENSIONLESS
    assert parallelism.mem_params.sp_units == byte
    assert parallelism.mem_total_per_gpu.sp_units == byte
    assert parallelism.mem_zero3_per_gpu.sp_units == byte
    assert parallelism.fsdp_allgather_buffer.sp_units == byte
    assert parallelism.cpu_offload_bw.sp_units == BPS
    assert parallelism.cpu_offload_time.sp_units == SECOND
    assert parallelism.bubble_1f1b.sp_units == DIMENSIONLESS
    assert parallelism.t_forward.sp_units == SECOND
    assert parallelism.tp_comm_per_block.sp_units == byte
    assert parallelism.tp_exposed_time.sp_units == SECOND
    assert parallelism.moe_payload_per_layer.sp_units == byte
    assert parallelism.ep_group_bw.sp_units == BPS
    assert parallelism.cp_comm_per_layer.sp_units == byte
