"""
Attention math, dense/sparse FLOP accounting, and KV-cache formulas.
"""

import sympy as sp

from ..core import eq, var
from ..core.units import FLOP, byte

from .architecture_embeddings import (
    d_model,
    n_kv_heads,
    head_dim,
    seq_len_ctx,
    n_layers,
    params_attn_per_layer,
    qk_scale,
)
from .architecture_attention_refs import (
    ATTENTION_FLOP_REF,
    ATTENTION_REF,
    DIMENSIONLESS,
    KV_CACHE_REF,
    SPARSE_ATTENTION_REF,
)


q_tensor = var(
    "arch.attn.q_tensor", "Q_attn_arch", "matrix",
    "Query tensor entering attention.",
    scope="architecture",
)
k_tensor = var(
    "arch.attn.k_tensor", "K_attn_arch", "matrix",
    "Key tensor entering attention.",
    scope="architecture",
)
v_tensor = var(
    "arch.attn.v_tensor", "V_attn_arch", "matrix",
    "Value tensor entering attention.",
    scope="architecture",
)
attn_logits = var(
    "arch.attn.logits", "A_logits_arch", "matrix",
    "Pre-softmax attention logits.",
    scope="architecture",
)
attn_output = var(
    "arch.attn.output", "A_out_arch", "matrix",
    "Attention output tensor.",
    scope="architecture",
)
attn_proj_flops_per_layer = var(
    "arch.attn.proj_flops_per_layer", "F_proj_L_arch", "FLOP",
    "Projection FLOPs per layer for one full sequence.",
    scope="architecture",
)
attn_scores_flops_per_layer = var(
    "arch.attn.scores_flops_per_layer", "F_scores_L_arch", "FLOP",
    "QK score-matmul FLOPs per layer for one full sequence.",
    scope="architecture",
)
attn_values_flops_per_layer = var(
    "arch.attn.values_flops_per_layer", "F_values_L_arch", "FLOP",
    "Softmax-times-V FLOPs per layer for one full sequence.",
    scope="architecture",
)
attn_flops_mha_per_layer = var(
    "arch.attn.flops_mha_per_layer", "F_attn_L_arch", "FLOP",
    "Full dense attention FLOPs per layer for one full sequence.",
    scope="architecture",
)
attn_flops_sparse_per_layer = var(
    "arch.attn.flops_sparse_per_layer", "F_attn_sparse_L_arch", "FLOP",
    "Sparse-attention FLOPs per layer when each query only visits k_sparse keys.",
    scope="architecture",
)
d_latent_mla = var(
    "arch.mla.d_latent", "d_latent_mla_arch", "dim",
    "MLA latent KV dimension.",
    scope="architecture",
)
bytes_per_param_kv = var(
    "arch.kv.bytes_per_val", "B_kv_val_arch", "byte",
    "Bytes per KV cache element.",
    scope="architecture",
)
kv_bytes_per_tok_layer = var(
    "arch.kv.bytes_per_tok_layer", "B_kv_tok_L_arch", "byte",
    "KV cache bytes per token per layer for MHA or GQA.",
    scope="architecture",
)
kv_bytes_per_tok_layer_mla = var(
    "arch.kv.bytes_per_tok_layer_mla", "B_kv_tok_mla_arch", "byte",
    "KV cache bytes per token per layer for MLA-style compressed KV.",
    scope="architecture",
)
kv_compression_ratio = var(
    "arch.kv.compression_ratio", "r_kv_comp_arch", "dimensionless",
    "KV cache compression ratio of GQA-style cache relative to MLA cache.",
    scope="architecture",
)
kv_total_bytes = var(
    "arch.kv.total_bytes", "B_kv_total_arch", "byte",
    "Total KV cache bytes across the full context and all layers.",
    scope="architecture",
)
k_sparse = var(
    "arch.sparse.top_k", "k_sparse_arch", "tokens",
    "Keys visited per query under sparse attention.",
    scope="architecture",
)

for _v in (
    q_tensor, k_tensor, v_tensor, attn_logits, attn_output,
    d_latent_mla, kv_compression_ratio, k_sparse,
):
    _v.sp_units = DIMENSIONLESS
    _v.references.append(ATTENTION_REF)

for _v in (
    attn_proj_flops_per_layer, attn_scores_flops_per_layer,
    attn_values_flops_per_layer, attn_flops_mha_per_layer,
    attn_flops_sparse_per_layer,
):
    _v.sp_units = FLOP
    _v.references.append(ATTENTION_FLOP_REF)

attn_flops_sparse_per_layer.references.append(SPARSE_ATTENTION_REF)
k_sparse.references.append(SPARSE_ATTENTION_REF)

for _v in (
    bytes_per_param_kv, kv_bytes_per_tok_layer,
    kv_bytes_per_tok_layer_mla, kv_total_bytes,
):
    _v.sp_units = byte
    _v.references.append(KV_CACHE_REF)

for _v in (d_latent_mla, kv_compression_ratio):
    _v.references.append(KV_CACHE_REF)


eq_attn_logits = eq(
    "arch.eq.attn_logits",
    attn_logits.symbol,
    q_tensor.symbol * k_tensor.symbol * qk_scale.symbol,
    "Scaled dot-product attention forms logits from Q K^T divided by sqrt(head_dim). The transpose is abstracted here into the symbolic tensor product.",
    check_units=True,
)

eq_attn_output = eq(
    "arch.eq.attn_output",
    attn_output.symbol,
    sp.Function("softmax")(attn_logits.symbol) * v_tensor.symbol,
    "Attention output is softmax(logits) times V, represented here as an abstract tensor expression.",
    check_units=True,
)

eq_attn_proj_flops = eq(
    "arch.eq.attn_proj_flops_per_layer",
    attn_proj_flops_per_layer.symbol,
    2 * seq_len_ctx.symbol * params_attn_per_layer.symbol,
    "For one full sequence, each learned projection contributes two FLOPs per parameter application.",
    references=[ATTENTION_FLOP_REF],
    check_units=True,
)

eq_attn_scores_flops = eq(
    "arch.eq.attn_scores_flops_per_layer",
    attn_scores_flops_per_layer.symbol,
    2 * seq_len_ctx.symbol ** 2 * d_model.symbol,
    "QK score matmuls cost 2 * sequence^2 * model_width FLOPs per layer.",
    references=[ATTENTION_FLOP_REF],
    check_units=True,
)

eq_attn_values_flops = eq(
    "arch.eq.attn_values_flops_per_layer",
    attn_values_flops_per_layer.symbol,
    2 * seq_len_ctx.symbol ** 2 * d_model.symbol,
    "Applying attention weights to V costs the same order as the score matmul.",
    references=[ATTENTION_FLOP_REF],
    check_units=True,
)

eq_attn_flops_mha = eq(
    "arch.eq.attn_flops_mha_per_layer",
    attn_flops_mha_per_layer.symbol,
    attn_proj_flops_per_layer.symbol + attn_scores_flops_per_layer.symbol + attn_values_flops_per_layer.symbol,
    "Dense attention per layer equals projection FLOPs plus score matmul FLOPs plus value-aggregation FLOPs.",
    check_units=True,
)

eq_attn_flops_sparse = eq(
    "arch.eq.attn_flops_sparse_per_layer",
    attn_flops_sparse_per_layer.symbol,
    attn_proj_flops_per_layer.symbol + 4 * seq_len_ctx.symbol * k_sparse.symbol * d_model.symbol,
    "Sparse attention replaces the quadratic score and value terms with sequence times sparse_k times model_width.",
    references=[SPARSE_ATTENTION_REF],
    check_units=True,
)

eq_kv_gqa = eq(
    "arch.eq.kv_gqa",
    kv_bytes_per_tok_layer.symbol,
    2 * n_kv_heads.symbol * head_dim.symbol * bytes_per_param_kv.symbol,
    "MHA or GQA KV cache stores K and V for each KV head.",
    check_units=True,
)

eq_kv_mla = eq(
    "arch.eq.kv_mla",
    kv_bytes_per_tok_layer_mla.symbol,
    2 * d_latent_mla.symbol * bytes_per_param_kv.symbol,
    "MLA stores compressed latent K and V states rather than per-head full-width KV tensors.",
    check_units=True,
)

eq_kv_compression_ratio = eq(
    "arch.eq.kv_compression_ratio",
    kv_compression_ratio.symbol,
    kv_bytes_per_tok_layer.symbol / kv_bytes_per_tok_layer_mla.symbol,
    "KV compression ratio is the GQA cache footprint divided by the MLA cache footprint.",
    check_units=True,
)

eq_kv_total = eq(
    "arch.eq.kv_total",
    kv_total_bytes.symbol,
    n_layers.symbol * seq_len_ctx.symbol * kv_bytes_per_tok_layer.symbol,
    "Total KV cache equals layers times sequence length times KV bytes per token per layer.",
    check_units=True,
)


ARCH_ATTENTION_CORE_VARIABLES = [
    q_tensor, k_tensor, v_tensor, attn_logits, attn_output,
    attn_proj_flops_per_layer, attn_scores_flops_per_layer,
    attn_values_flops_per_layer, attn_flops_mha_per_layer,
    attn_flops_sparse_per_layer, d_latent_mla, bytes_per_param_kv,
    kv_bytes_per_tok_layer, kv_bytes_per_tok_layer_mla, kv_compression_ratio,
    kv_total_bytes, k_sparse,
]

ARCH_ATTENTION_CORE_EQUATIONS = [
    eq_attn_logits,
    eq_attn_output,
    eq_attn_proj_flops,
    eq_attn_scores_flops,
    eq_attn_values_flops,
    eq_attn_flops_mha,
    eq_attn_flops_sparse,
    eq_kv_gqa,
    eq_kv_mla,
    eq_kv_compression_ratio,
    eq_kv_total,
]

for _e in (
    eq_attn_logits, eq_attn_output, eq_attn_proj_flops,
    eq_attn_scores_flops, eq_attn_values_flops, eq_attn_flops_mha,
):
    _e.references.append(ATTENTION_REF)

for _e in (
    eq_attn_proj_flops, eq_attn_scores_flops, eq_attn_values_flops,
    eq_attn_flops_mha, eq_attn_flops_sparse,
):
    _e.references.append(ATTENTION_FLOP_REF)

eq_attn_flops_sparse.references.append(SPARSE_ATTENTION_REF)

for _e in (eq_kv_gqa, eq_kv_mla, eq_kv_compression_ratio, eq_kv_total):
    _e.references.append(KV_CACHE_REF)


__all__ = [
    "q_tensor", "k_tensor", "v_tensor", "attn_logits", "attn_output",
    "attn_proj_flops_per_layer", "attn_scores_flops_per_layer",
    "attn_values_flops_per_layer", "attn_flops_mha_per_layer",
    "attn_flops_sparse_per_layer", "d_latent_mla", "bytes_per_param_kv",
    "kv_bytes_per_tok_layer", "kv_bytes_per_tok_layer_mla",
    "kv_compression_ratio", "kv_total_bytes", "k_sparse",
    "eq_attn_logits", "eq_attn_output", "eq_attn_proj_flops",
    "eq_attn_scores_flops", "eq_attn_values_flops", "eq_attn_flops_mha",
    "eq_attn_flops_sparse", "eq_kv_gqa", "eq_kv_mla",
    "eq_kv_compression_ratio", "eq_kv_total",
    "ARCH_ATTENTION_CORE_VARIABLES", "ARCH_ATTENTION_CORE_EQUATIONS",
]
