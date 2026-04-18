"""
gpu_stack.presets.workload
==========================

Workload-layer presets.

The most common workload knob is the dense-vs-MoE variant selector across
training throughput and scaling-law variables. The two presets here pin
that selector one way or the other so a resolver call can evaluate a
training-level target without spelling out every variant selection
by hand.

These presets carry no numeric assignments; they only set variant keys.
Combine them with a hardware preset and scenario-specific overrides
using `gpu_stack.core.combine_presets` to build a full scenario.
"""

from ..core.presets import Preset


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
    "dense_variant_selector",
    "moe_variant_selector",
    "mfu_from_flops_selector",
    "adamw_optimizer_selector",
    "muon_optimizer_selector",
]
