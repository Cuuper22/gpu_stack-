"""
scopes/architecture_attention.py
================================

Attention math, variants, and KV cache, plus pointwise activation functions
and normalization. Covers the dense attention FLOP breakdown, sparse and MLA
variants, GeLU and SwiGLU activations, and LayerNorm and RMSNorm.
"""

import sympy as sp

from ..core import Reference, eq, var
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


DIMENSIONLESS = sp.Integer(1)

ATTENTION_REF = Reference(
    "Scaled dot-product and multi-head attention follow the Transformer "
    "attention form introduced by Vaswani et al.",
    kind="model",
)
ATTENTION_FLOP_REF = Reference(
    "Dense attention FLOP accounting separates learned projections from the "
    "QK score matmul and attention-value matmul for one full sequence.",
    kind="model",
)
SPARSE_ATTENTION_REF = Reference(
    "Sparse attention FLOP accounting replaces quadratic all-pairs attention "
    "terms with a fixed number of visited keys per query.",
    kind="model",
)
KV_CACHE_REF = Reference(
    "KV-cache accounting stores key and value states per generated token, per "
    "layer, with grouped-query and compressed-latent variants changing the "
    "stored KV width.",
    kind="model",
)
ACTIVATION_REF = Reference(
    "Activation definitions cover sigmoid, GeLU, SiLU, and SwiGLU pointwise "
    "transformations used in transformer blocks.",
    kind="model",
)
NORMALIZATION_REF = Reference(
    "LayerNorm and RMSNorm are represented as dimensionless affine-free "
    "normalization transforms over hidden activations.",
    kind="model",
)


# ---------------------------------------------------------------------------
# Attention math, variants, and KV cache
# ---------------------------------------------------------------------------

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
)

eq_attn_scores_flops = eq(
    "arch.eq.attn_scores_flops_per_layer",
    attn_scores_flops_per_layer.symbol,
    2 * seq_len_ctx.symbol ** 2 * d_model.symbol,
    "QK score matmuls cost 2 * sequence^2 * model_width FLOPs per layer.",
)

eq_attn_values_flops = eq(
    "arch.eq.attn_values_flops_per_layer",
    attn_values_flops_per_layer.symbol,
    2 * seq_len_ctx.symbol ** 2 * d_model.symbol,
    "Applying attention weights to V costs the same order as the score matmul.",
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


# ---------------------------------------------------------------------------
# Activation functions
# ---------------------------------------------------------------------------

act_x = var(
    "arch.act.x", "x_act_arch", "value",
    "Activation input.",
    scope="architecture",
)
sigmoid_x = var(
    "arch.act.sigmoid_x", "sigma_act_arch", "value",
    "Sigmoid applied to the activation input.",
    scope="architecture",
)
gelu_output = var(
    "arch.act.gelu", "gelu_act_arch", "value",
    "GeLU output.",
    scope="architecture",
)
silu_output = var(
    "arch.act.silu", "silu_act_arch", "value",
    "SiLU output.",
    scope="architecture",
)
swiglu_gate = var(
    "arch.act.swiglu_gate", "gate_swiglu_arch", "value",
    "Gate input to SwiGLU.",
    scope="architecture",
)
swiglu_value = var(
    "arch.act.swiglu_value", "value_swiglu_arch", "value",
    "Value branch input to SwiGLU.",
    scope="architecture",
)
swiglu_output = var(
    "arch.act.swiglu", "swiglu_act_arch", "value",
    "SwiGLU output.",
    scope="architecture",
)

for _v in (
    act_x, sigmoid_x, gelu_output, silu_output, swiglu_gate, swiglu_value,
    swiglu_output,
):
    _v.sp_units = DIMENSIONLESS
    _v.references.append(ACTIVATION_REF)


eq_sigmoid_x = eq(
    "arch.eq.sigmoid_x",
    sigmoid_x.symbol,
    1 / (1 + sp.exp(-act_x.symbol)),
    "Sigmoid is 1 / (1 + exp(-x)).",
    check_units=True,
)

eq_gelu_output = eq(
    "arch.eq.gelu",
    gelu_output.symbol,
    act_x.symbol * (1 + sp.erf(act_x.symbol / sp.sqrt(2))) / 2,
    "GeLU equals x times the Gaussian CDF of x.",
    check_units=True,
)

eq_silu_output = eq(
    "arch.eq.silu",
    silu_output.symbol,
    act_x.symbol / (1 + sp.exp(-act_x.symbol)),
    "SiLU equals x times sigmoid(x).",
    check_units=True,
)

eq_swiglu_output = eq(
    "arch.eq.swiglu",
    swiglu_output.symbol,
    swiglu_value.symbol / (1 + sp.exp(-swiglu_gate.symbol)),
    "SwiGLU multiplies the value branch by SiLU applied to the gate branch.",
    check_units=True,
)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

norm_x = var(
    "arch.norm.x", "x_norm_arch", "value",
    "Input to a normalization layer.",
    scope="architecture",
)
norm_mean = var(
    "arch.norm.mean", "mu_norm_arch", "value",
    "Mean used by LayerNorm.",
    scope="architecture",
    positive=False,
)
norm_var = var(
    "arch.norm.var", "var_norm_arch", "value^2",
    "Variance used by LayerNorm.",
    scope="architecture",
)
norm_eps = var(
    "arch.norm.eps", "eps_norm_arch", "value",
    "Normalization epsilon.",
    scope="architecture",
)
layernorm_output = var(
    "arch.norm.layernorm_output", "y_ln_arch", "value",
    "LayerNorm output.",
    scope="architecture",
    positive=False,
)
rmsnorm_output = var(
    "arch.norm.rmsnorm_output", "y_rms_arch", "value",
    "RMSNorm output.",
    scope="architecture",
    positive=False,
)

for _v in (
    norm_x, norm_mean, norm_var, norm_eps, layernorm_output, rmsnorm_output,
):
    _v.sp_units = DIMENSIONLESS
    _v.references.append(NORMALIZATION_REF)


eq_layernorm_output = eq(
    "arch.eq.layernorm_output",
    layernorm_output.symbol,
    (norm_x.symbol - norm_mean.symbol) / sp.sqrt(norm_var.symbol + norm_eps.symbol),
    "LayerNorm subtracts the mean and divides by the standard deviation.",
    check_units=True,
)

eq_rmsnorm_output = eq(
    "arch.eq.rmsnorm_output",
    rmsnorm_output.symbol,
    norm_x.symbol / sp.sqrt(norm_var.symbol + norm_eps.symbol),
    "RMSNorm skips mean subtraction and divides by the root mean square scale.",
    check_units=True,
)


ARCH_ATTENTION_VARIABLES = [
    q_tensor, k_tensor, v_tensor, attn_logits, attn_output,
    attn_proj_flops_per_layer, attn_scores_flops_per_layer,
    attn_values_flops_per_layer, attn_flops_mha_per_layer,
    attn_flops_sparse_per_layer, d_latent_mla, bytes_per_param_kv,
    kv_bytes_per_tok_layer, kv_bytes_per_tok_layer_mla, kv_compression_ratio,
    kv_total_bytes, k_sparse,
    act_x, sigmoid_x, gelu_output, silu_output, swiglu_gate, swiglu_value,
    swiglu_output,
    norm_x, norm_mean, norm_var, norm_eps, layernorm_output, rmsnorm_output,
]

ARCH_ATTENTION_EQUATIONS = [
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
    eq_sigmoid_x,
    eq_gelu_output,
    eq_silu_output,
    eq_swiglu_output,
    eq_layernorm_output,
    eq_rmsnorm_output,
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

for _e in (eq_sigmoid_x, eq_gelu_output, eq_silu_output, eq_swiglu_output):
    _e.references.append(ACTIVATION_REF)

for _e in (eq_layernorm_output, eq_rmsnorm_output):
    _e.references.append(NORMALIZATION_REF)


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
