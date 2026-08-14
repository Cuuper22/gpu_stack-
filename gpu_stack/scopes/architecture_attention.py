"""
scopes/architecture_attention.py
================================

Facade for the attention side of the architecture scope.

Attention is the part of a transformer where every token looks at every other
token, so it is where FLOPs grow quadratically with sequence length and where
the KV cache — stored key and value states for already-seen tokens — eats
memory. The actual definitions live in three helper modules: core attention
math and KV-cache sizing, pointwise activations, and normalization. This file
only re-exports them, keeping the original public import surface and the
registry order stable so nothing downstream has to change its imports.
"""

from .architecture_attention_core import *
from .architecture_attention_core import (
    ARCH_ATTENTION_CORE_EQUATIONS,
    ARCH_ATTENTION_CORE_VARIABLES,
)
from .architecture_attention_activations import *
from .architecture_attention_activations import (
    ARCH_ATTENTION_ACTIVATION_EQUATIONS,
    ARCH_ATTENTION_ACTIVATION_VARIABLES,
)
from .architecture_attention_normalization import *
from .architecture_attention_normalization import (
    ARCH_ATTENTION_NORMALIZATION_EQUATIONS,
    ARCH_ATTENTION_NORMALIZATION_VARIABLES,
)
from .architecture_attention_refs import (
    ACTIVATION_REF,
    ATTENTION_FLOP_REF,
    ATTENTION_REF,
    DIMENSIONLESS,
    KV_CACHE_REF,
    NORMALIZATION_REF,
    SPARSE_ATTENTION_REF,
)


ARCH_ATTENTION_VARIABLES = (
    ARCH_ATTENTION_CORE_VARIABLES
    + ARCH_ATTENTION_ACTIVATION_VARIABLES
    + ARCH_ATTENTION_NORMALIZATION_VARIABLES
)

ARCH_ATTENTION_EQUATIONS = (
    ARCH_ATTENTION_CORE_EQUATIONS
    + ARCH_ATTENTION_ACTIVATION_EQUATIONS
    + ARCH_ATTENTION_NORMALIZATION_EQUATIONS
)


__all__ = [
    "q_tensor", "k_tensor", "v_tensor", "attn_logits", "attn_output",
    "attn_proj_flops_per_layer", "attn_scores_flops_per_layer",
    "attn_values_flops_per_layer", "attn_flops_mha_per_layer",
    "attn_flops_sparse_per_layer", "d_latent_mla", "bytes_per_param_kv",
    "kv_bytes_per_tok_layer", "kv_bytes_per_tok_layer_mla",
    "kv_compression_ratio", "kv_total_bytes", "k_sparse",
    "act_x", "sigmoid_x", "gelu_output", "silu_output",
    "swiglu_gate", "swiglu_value", "swiglu_output",
    "norm_x", "norm_mean", "norm_var", "norm_eps",
    "layernorm_output", "rmsnorm_output",
    "eq_attn_logits", "eq_attn_output", "eq_attn_proj_flops",
    "eq_attn_scores_flops", "eq_attn_values_flops", "eq_attn_flops_mha",
    "eq_attn_flops_sparse", "eq_kv_gqa", "eq_kv_mla",
    "eq_kv_compression_ratio", "eq_kv_total",
    "eq_sigmoid_x", "eq_gelu_output", "eq_silu_output", "eq_swiglu_output",
    "eq_layernorm_output", "eq_rmsnorm_output",
    "ARCH_ATTENTION_VARIABLES", "ARCH_ATTENTION_EQUATIONS",
]
