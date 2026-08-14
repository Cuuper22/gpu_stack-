"""Checks metadata on the arithmetic scope: the SM's raw math primitives.

The arithmetic scope models what one streaming multiprocessor (SM) can
compute per cycle — FMA and MMA instructions, tensor-core throughput, DP4A
integer ops, SFU ops. These tests pin three properties: every variable has
a unit and a reference, representative variables have the *right* unit
(FLOP vs FLOPS vs seconds vs dimensionless), and the throughput identities
carry references and pass dimensional unit checks. A wrong or missing unit
here would silently corrupt every roofline number built on top.
"""

import sympy as sp

from gpu_stack import Registry
from gpu_stack.core.units import FLOP, FLOPS, SECOND


DIMENSIONLESS = sp.Integer(1)


def _arithmetic_variables():
    return [v for v in Registry.variables.values() if v.scope == "arithmetic"]


def _arithmetic_equations():
    return [
        e for e in Registry.equations.values()
        if e.name.startswith("arith.")
    ]


def test_arithmetic_variables_have_units_and_references():
    arithmetic_vars = _arithmetic_variables()
    assert len(arithmetic_vars) >= 28
    assert [v.name for v in arithmetic_vars if v.sp_units is None] == []
    assert [v.name for v in arithmetic_vars if not v.references] == []


def test_arithmetic_representative_units_are_dimensional():
    assert Registry.variables["arith.fma.flops_per_op"].sp_units == FLOP
    assert Registry.variables["arith.mma.M"].sp_units == DIMENSIONLESS
    assert Registry.variables["arith.mma.flops_per_inst"].sp_units == FLOP
    assert Registry.variables["arith.tc.flops_per_cycle"].sp_units == FLOP
    assert Registry.variables["arith.sm.peak_flops"].sp_units == FLOPS
    assert Registry.variables["arith.tc.issue_efficiency"].sp_units == DIMENSIONLESS
    assert Registry.variables["arith.sparsity.speedup"].sp_units == DIMENSIONLESS
    assert Registry.variables["arith.int.dp4a_ops_per_inst"].sp_units == DIMENSIONLESS
    assert Registry.variables["arith.sm.peak_dp4a_ops"].sp_units == 1 / SECOND
    assert Registry.variables["arith.sm.peak_sfu_ops"].sp_units == 1 / SECOND
    assert Registry.variables["arith.sfu.time_per_token"].sp_units == SECOND


def test_arithmetic_equations_have_references_and_unit_checks():
    arithmetic_eqs = _arithmetic_equations()
    checked = {
        e.name for e in arithmetic_eqs
        if getattr(e, "_check_units_flag", False)
    }

    assert len(arithmetic_eqs) >= 13
    assert [e.name for e in arithmetic_eqs if not e.references] == []
    assert len(checked) >= 13
    assert {
        "arith.eq.peak_fma_sm",
        "arith.eq.flops_per_mma",
        "arith.eq.flops_per_tc_cycle",
        "arith.eq.peak_flops_sm",
        "arith.eq.peak_flops_sm_effective",
        "arith.eq.sparsity_speedup",
        "arith.eq.peak_flops_sm_sparse",
        "arith.eq.int_ops_per_dp4a",
        "arith.eq.peak_dp4a_sm",
        "arith.eq.int_ops_per_dp2a",
        "arith.eq.peak_dp2a_sm",
        "arith.eq.peak_sfu_ops_sm",
        "arith.eq.sfu_time_per_token",
    } <= checked
