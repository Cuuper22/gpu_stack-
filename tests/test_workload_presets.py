"""Provenance and resolver tests for the workload (model-shape) presets.

A workload preset pins a model's architecture numbers — layers, width, heads,
tokens per step — to a public source. Using Pythia-70M as the example, these
tests check three things: the source string actually cites the EleutherAI
repository and config values it claims, the preset assigns exactly the
sourced roots and nothing derivable (head_dim and n_steps must come from
equations, not assignments), and resolving those derived targets reproduces
the published numbers through the expected equations.
"""

import pytest

from gpu_stack import Registry
from gpu_stack.presets import workload


PYTHIA_70M_ASSIGNMENTS = {
    "arch.n_layers": 6,
    "arch.d_model": 512,
    "arch.d_ffn": 2048,
    "arch.n_heads": 8,
    "arch.vocab": 50304,
    "arch.seq_len": 2048,
    "arch.tokens_per_step": 2_097_152,
    "arch.output.untied_factor": 1,
    "training.total_tokens": 299_892_736_000,
}


def test_pythia_70m_preset_records_public_training_provenance():
    preset = workload.pythia_70m_dense_training
    source = preset.source or ""

    assert "EleutherAI Pythia repository" in source
    assert "Hugging Face EleutherAI/pythia-70m config.json" in source
    assert "n_layers=6" in source
    assert "d_model=512" in source
    assert "d_head=64" in source
    assert "intermediate_size=2048" in source
    assert "2,097,152" in source
    assert "299,892,736,000" in source
    assert any("tie_word_embeddings=false" in note for note in preset.notes)
    assert any("does not assign arch.params_total_dense" in note for note in preset.notes)
    assert any("arch.n_kv_heads is intentionally unassigned" in note for note in preset.notes)


def test_pythia_70m_assigns_only_registered_sourced_values():
    preset = workload.pythia_70m_dense_training

    assert dict(preset.assignments) == PYTHIA_70M_ASSIGNMENTS
    assert dict(preset.variants) == {
        "training.flops_per_step": "dense",
        "training.scaling_params": "dense",
    }
    for name in preset.assignments:
        assert name in Registry.variables, name

    assert "arch.head_dim" not in preset.assignments
    assert "training.n_steps" not in preset.assignments
    assert "arch.params_total_dense" not in preset.assignments
    assert "arch.n_kv_heads" not in preset.assignments


@pytest.mark.parametrize(
    ("target", "expected", "equation"),
    [
        ("arch.head_dim", 64.0, "arch.eq.head_dim"),
        ("arch.attn.qk_scale", 0.125, "arch.eq.qk_scale"),
        ("training.n_steps", 143000.0, "training.eq.n_steps"),
    ],
)
def test_pythia_70m_resolves_sourced_cross_checks(target, expected, equation):
    result = workload.pythia_70m_dense_training.resolve(target)

    assert float(result.value) == pytest.approx(expected)
    assert result.missing == set()
    assert equation in [step.equation for step in result.trace]
