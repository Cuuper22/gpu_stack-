"""
tests/test_precision_units.py
=============================

Precision-scope metadata coverage regressions.
"""

import sympy as sp

from gpu_stack import Registry
from gpu_stack.core.units import bit, byte


DIMENSIONLESS = sp.Integer(1)


def _precision_variables():
    return [v for v in Registry.variables.values() if v.scope == "precision"]


def _precision_equations():
    return [
        e for e in Registry.equations.values()
        if e.name.startswith("precision.")
    ]


def test_precision_variables_have_units_and_references():
    precision_vars = _precision_variables()
    assert len(precision_vars) >= 73
    assert [v.name for v in precision_vars if v.sp_units is None] == []
    assert [v.name for v in precision_vars if not v.references] == []


def test_precision_representative_units_are_dimensional():
    assert Registry.variables["precision.total_bits"].sp_units == bit
    assert Registry.variables["precision.bytes_per_value"].sp_units == byte
    assert Registry.variables["precision.fp8.bytes"].sp_units == byte
    assert Registry.variables["precision.microscale.effective_bits"].sp_units == bit
    assert Registry.variables["precision.quant.error_variance"].sp_units == DIMENSIONLESS
    assert Registry.variables["precision.sr.p_up"].sp_units == DIMENSIONLESS


def test_precision_equations_have_references_and_curated_unit_checks():
    precision_eqs = _precision_equations()
    checked = {
        e.name for e in precision_eqs
        if getattr(e, "_check_units_flag", False)
    }

    assert len(precision_eqs) >= 47
    assert [e.name for e in precision_eqs if not e.references] == []
    assert len(checked) >= 27
    assert {
        "precision.eq.total_bits",
        "precision.eq.bytes_per_value",
        "precision.eq.exp_min_normal",
        "precision.eq.quant_step",
        "precision.eq.sr_probability",
        "precision.eq.effective_bits",
        "precision.eq.bfp_effective_bits",
        "precision.eq.lns_relative_error",
        "precision.eq.scaled_grad_min",
        "precision.eq.rht_norm_preservation",
    } <= checked
