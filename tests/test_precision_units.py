"""Metadata coverage for the precision scope.

The precision scope models number formats (fp32 down to fp4, int8, int4,
posits, log-number systems) and the machinery around them: quantization
error, stochastic rounding, loss scaling. These tests keep the metadata
honest. Every precision variable declares units and cites a reference; every
equation cites a reference. Storage sizes carry real dimensions — bits or
bytes — while probabilities and error variances are dimensionless.

Unit checking here is curated rather than universal: at least 27 of the 47+
equations must be checked, including a named core set, because some identities
mix symbolic pieces that SymPy's unit checker cannot evaluate.
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
