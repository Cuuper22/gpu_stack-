"""
tests/test_optimizer_units.py
=============================

Regression coverage for optimizer metadata, provenance, and unit checks.
"""

import sympy as sp

from gpu_stack import Registry
from gpu_stack.core.units import byte


def optimizer_variables():
    return [v for v in Registry.variables.values() if v.name.startswith("opt.")]


def optimizer_equations():
    return [e for e in Registry.equations.values() if e.name.startswith("opt.")]


def test_optimizer_variables_have_unit_metadata_and_references():
    missing_units = sorted(v.name for v in optimizer_variables() if v.sp_units is None)
    missing_refs = sorted(v.name for v in optimizer_variables() if not v.references)

    assert missing_units == []
    assert missing_refs == []


def test_optimizer_equations_have_provenance_references():
    missing_refs = sorted(e.name for e in optimizer_equations() if not e.references)

    assert missing_refs == []


def test_optimizer_unit_checks_cover_non_piecewise_identities():
    unchecked_by_design = {
        "opt.eq.lr_cosine",
        "opt.eq.lr_wsd",
        "opt.eq.loss_scale_next",
        "opt.ineq.schedule_total_steps_exceeds_warmup_steps",
        "opt.ineq.schedule_total_steps_exceeds_warmup_and_stable_steps",
        "opt.ineq.schedule_total_steps_reaches_current_step",
    }
    checked = {
        e.name for e in optimizer_equations()
        if getattr(e, "_check_units_flag", False)
    }
    expected_checked = {
        e.name for e in optimizer_equations()
        if e.name not in unchecked_by_design
    }

    assert checked == expected_checked


def test_optimizer_byte_accounting_variables_use_byte_units():
    expected_byte_units = {
        "opt.bytes_per_param",
        "opt.shampoo.state_bytes",
        "opt.shampoo.state_bytes_distributed",
        "opt.state.bytes",
    }

    for name in expected_byte_units:
        assert Registry.variables[name].sp_units == byte


def test_optimizer_tensor_and_counter_variables_are_dimensionless():
    expected_dimensionless = {
        "opt.grad",
        "opt.param",
        "opt.adam.m",
        "opt.adam.v",
        "opt.muon.X",
        "opt.schedule.total_steps",
        "opt.loss_scale.scale",
        "opt.shampoo.shard_degree",
    }

    for name in expected_dimensionless:
        assert Registry.variables[name].sp_units == sp.Integer(1)
