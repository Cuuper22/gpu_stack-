"""
gpu_stack.presets.workload
==========================

Workload-layer presets.

One preset here carries numbers: `pythia_70m_dense_training`, the sourced
Pythia-70M model shape and training facts. The rest are variant selectors.
A variant selector assigns no numbers at all; it just pins a choice the
resolver cannot make on its own — dense vs. MoE equations, which MFU
formulation to use, AdamW vs. Muon — so a resolver call does not have to
spell out every such choice by hand.

Combine these with a hardware preset and scenario-specific overrides via
`gpu_stack.core.combine_presets` to build a full scenario.
"""

from ..core.presets import Preset


pythia_70m_dense_training = Preset(
    name="pythia_70m_dense_training",
    description=(
        "Sourced EleutherAI Pythia-70M dense GPT-NeoX training workload. "
        "Includes only registered workload and architecture fields with a "
        "direct public source mapping."
    ),
    assignments={
        "arch.n_layers": 6,
        "arch.d_model": 512,
        "arch.d_ffn": 2048,
        "arch.n_heads": 8,
        "arch.vocab": 50304,
        "arch.seq_len": 2048,
        "arch.tokens_per_step": 2_097_152,
        "arch.output.untied_factor": 1,
        "training.total_tokens": 299_892_736_000,
    },
    variants={
        "training.flops_per_step": "dense",
        "training.scaling_params": "dense",
    },
    source=(
        "EleutherAI Pythia repository, Models table and Quickstart notes, "
        "https://github.com/EleutherAI/pythia: Pythia-70M has n_layers=6, "
        "d_model=512, n_heads=8, d_head=64, batch size 2M tokens; each model "
        "saw 299,892,736,000 tokens; final checkpoint is after 143000 steps "
        "at batch size 2,097,152 tokens. Hugging Face "
        "EleutherAI/pythia-70m config.json, "
        "https://huggingface.co/EleutherAI/pythia-70m/blob/main/config.json: "
        "hidden_size=512, intermediate_size=2048, max_position_embeddings=2048, "
        "num_attention_heads=8, num_hidden_layers=6, tie_word_embeddings=false, "
        "vocab_size=50304."
    ),
    notes=(
        "arch.output.untied_factor=1 maps the cited tie_word_embeddings=false "
        "config field onto this graph's registered untied-output factor.",
        "The cited d_head=64 and 143000 training steps are left as resolver "
        "cross-checks: arch.head_dim derives from arch.d_model / arch.n_heads, "
        "and training.n_steps derives from training.total_tokens / "
        "arch.tokens_per_step.",
        "The Pythia model card reports exact non-embedding parameter counts, "
        "but this graph currently has no registered non-embedding parameter "
        "variable. This preset therefore does not assign arch.params_total_dense.",
        "arch.n_kv_heads is intentionally unassigned because the cited Pythia "
        "configuration does not expose a registered key-value head count.",
    ),
)


dense_variant_selector = Preset(
    name="dense_variant_selector",
    description=(
        "Pin every dense-vs-MoE VARIANT family to the dense option. "
        "Covers training.flops_per_step and training.scaling_params, which "
        "both have VARIANT tags 'dense' and 'moe'."
    ),
    variants={
        "training.flops_per_step": "dense",
        "training.scaling_params": "dense",
    },
    source="Direct from the role tagging in gpu_stack.scopes.training.",
)


moe_variant_selector = Preset(
    name="moe_variant_selector",
    description=(
        "Pin every dense-vs-MoE VARIANT family to the MoE option. "
        "Covers training.flops_per_step and training.scaling_params."
    ),
    variants={
        "training.flops_per_step": "moe",
        "training.scaling_params": "moe",
    },
    source="Direct from the role tagging in gpu_stack.scopes.training.",
)


mfu_from_flops_selector = Preset(
    name="mfu_from_flops_selector",
    description=(
        "Select the achieved-FLOPs-over-peak formulation of training.mfu "
        "rather than the ideal-time-over-step-time formulation. The two "
        "are algebraically equivalent but the resolver needs one picked."
    ),
    variants={"training.mfu": "from_flops"},
    source="Direct from the role tagging in gpu_stack.scopes.training.",
)


adamw_optimizer_selector = Preset(
    name="adamw_optimizer_selector",
    description=(
        "Pin the optimizer variant at opt.param_next to the AdamW update "
        "rule rather than the Muon update."
    ),
    variants={"opt.param_next": "adamw"},
    source="Direct from the role tagging in gpu_stack.scopes.optimizer.",
)


muon_optimizer_selector = Preset(
    name="muon_optimizer_selector",
    description=(
        "Pin the optimizer variant at opt.param_next to the Muon update "
        "rule rather than the AdamW update."
    ),
    variants={"opt.param_next": "muon"},
    source="Direct from the role tagging in gpu_stack.scopes.optimizer.",
)


__all__ = [
    "pythia_70m_dense_training",
    "dense_variant_selector",
    "moe_variant_selector",
    "mfu_from_flops_selector",
    "adamw_optimizer_selector",
    "muon_optimizer_selector",
]
