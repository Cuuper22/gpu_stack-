"""
tests/test_architecture_units.py
================================

Focused metadata coverage for architecture-scope model quantities.
"""

from gpu_stack import Registry
from gpu_stack.core.units import FLOP


def _architecture_equations():
    return [e for e in Registry.equations.values() if e.name.startswith("arch.")]


def test_architecture_variables_have_unit_and_reference_metadata():
    variables = Registry.by_scope("architecture")
    assert variables

    missing_units = [v.name for v in variables if v.sp_units is None]
    missing_refs = [v.name for v in variables if not v.references]

    assert missing_units == []
    assert missing_refs == []


def test_architecture_equations_have_references_and_curated_unit_checks():
    equations = _architecture_equations()
    checked = {
        e.name for e in equations
        if getattr(e, "_check_units_flag", False)
    }

    assert len(equations) >= 55
    assert [e.name for e in equations if not e.references] == []
    assert len(checked) >= 48
    assert {
        "arch.eq.params_dense_total",
        "arch.eq.kv_total",
        "arch.eq.kv_compression_ratio",
        "arch.eq.attn_flops_mha_per_layer",
        "arch.eq.flops_per_token_dense",
        "arch.eq.params_encoder_decoder_total",
        "arch.eq.rope_angle",
        "arch.eq.yarn_scale",
        "arch.eq.params_total_moe",
        "arch.eq.expert_capacity",
        "arch.eq.layernorm_output",
    } <= checked


def test_architecture_unit_metadata_marks_bytes_and_flops():
    kv_value_units = Registry.variables["arch.kv.bytes_per_val"].sp_units

    assert kv_value_units is not None
    assert Registry.variables["arch.kv.bytes_per_tok_layer"].sp_units == kv_value_units
    assert Registry.variables["arch.kv.total_bytes"].sp_units == kv_value_units
    assert Registry.variables["arch.attn.flops_mha_per_layer"].sp_units == FLOP
    assert Registry.variables["arch.flops.per_token_dense"].sp_units == FLOP
    assert Registry.variables["arch.flops.step_moe"].sp_units == FLOP
