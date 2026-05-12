"""
scopes/architecture_embeddings.py
=================================

Core transformer dimensions, step tokenization, embeddings, and block-level
parameter counts. These definitions are the shared vocabulary that the other
architecture helpers import from.
"""

import sympy as sp

from ..core import Reference, eq, var


DIMENSIONLESS = sp.Integer(1)

ARCH_COUNT_REF = Reference(
    "Architecture quantities such as layers, heads, hidden dimensions, tokens, "
    "vocabulary entries, and parameter counts are represented as dimensionless "
    "counts for dimensional checking while retaining their domain unit labels.",
    kind="model",
)
ARCH_PARAM_ACCOUNTING_REF = Reference(
    "Dense transformer parameter accounting decomposes token embeddings, "
    "Q/K/V/O projections, FFN matrices, normalization parameters, and optional "
    "untied output projection by their matrix shapes.",
    kind="model",
)
TRANSFORMER_ATTENTION_REF = Reference(
    "Vaswani et al., Attention Is All You Need, 2017.",
    kind="paper",
    year=2017,
)
GQA_REF = Reference(
    "Ainslie et al., GQA: Training Generalized Multi-Query Transformer Models "
    "from Multi-Head Checkpoints, 2023.",
    kind="paper",
    year=2023,
)


# ---------------------------------------------------------------------------
# Core dimensions and step tokenization
# ---------------------------------------------------------------------------

n_layers = var(
    "arch.n_layers", "L_model_arch", "layers",
    "Number of transformer layers.",
    scope="architecture",
)
d_model = var(
    "arch.d_model", "d_model_arch", "dim",
    "Model width.",
    scope="architecture",
)
d_ffn = var(
    "arch.d_ffn", "d_ffn_arch", "dim",
    "Inner width of the feed-forward network.",
    scope="architecture",
)
n_heads = var(
    "arch.n_heads", "h_q_arch", "heads",
    "Number of query heads.",
    scope="architecture",
)
n_kv_heads = var(
    "arch.n_kv_heads", "h_kv_arch", "heads",
    "Number of KV heads.",
    scope="architecture",
)
head_dim = var(
    "arch.head_dim", "d_head_arch", "dim",
    "Per-head dimension.",
    scope="architecture",
)
vocab_size = var(
    "arch.vocab", "V_vocab_arch", "tokens",
    "Vocabulary size.",
    scope="architecture",
)
batch_sequences = var(
    "arch.batch_sequences", "B_seq_arch", "sequences",
    "Sequences consumed per optimizer step.",
    scope="architecture",
)
seq_len_ctx = var(
    "arch.seq_len", "L_ctx_arch", "tokens",
    "Sequence length seen by the attention layers.",
    scope="architecture",
)
n_tokens_step = var(
    "arch.tokens_per_step", "T_step_tok_arch", "tokens",
    "Tokens consumed per training step.",
    scope="architecture",
)
gqa_ratio = var(
    "arch.gqa_ratio", "r_gqa_arch", "dimensionless",
    "Number of query heads served by one KV head.",
    scope="architecture",
)
qk_scale = var(
    "arch.attn.qk_scale", "s_qk_arch", "dimensionless",
    "Scaling factor applied to attention logits before softmax.",
    scope="architecture",
)


eq_head_dim = eq(
    "arch.eq.head_dim",
    head_dim.symbol,
    d_model.symbol / n_heads.symbol,
    "Per-head dimension equals model width divided by query head count.",
    check_units=True,
)

eq_tokens_per_step = eq(
    "arch.eq.tokens_per_step",
    n_tokens_step.symbol,
    batch_sequences.symbol * seq_len_ctx.symbol,
    "Tokens per step equal sequences per step times context length.",
    check_units=True,
)

eq_gqa_ratio = eq(
    "arch.eq.gqa_ratio",
    gqa_ratio.symbol,
    n_heads.symbol / n_kv_heads.symbol,
    "GQA ratio is query heads divided by KV heads.",
    check_units=True,
)

eq_qk_scale = eq(
    "arch.eq.qk_scale",
    qk_scale.symbol,
    1 / sp.sqrt(head_dim.symbol),
    "Scaled dot-product attention divides logits by sqrt(head_dim).",
    check_units=True,
)


# ---------------------------------------------------------------------------
# Embeddings and block parameter counts
# ---------------------------------------------------------------------------

untied_output_factor = var(
    "arch.output.untied_factor", "rho_out_arch", "dimensionless",
    "0 if the output projection is tied to the token embedding, 1 if it is a separate matrix.",
    scope="architecture",
)
params_token_embed = var(
    "arch.embed.params", "P_embed_arch", "params",
    "Token embedding parameters.",
    scope="architecture",
)
params_output_proj = var(
    "arch.output.params", "P_out_arch", "params",
    "Output projection parameters when not tied to the embedding matrix.",
    scope="architecture",
)
q_proj_params = var(
    "arch.attn.q_proj_params", "P_q_arch", "params",
    "Query projection parameters per layer.",
    scope="architecture",
)
k_proj_params = var(
    "arch.attn.k_proj_params", "P_k_arch", "params",
    "Key projection parameters per layer.",
    scope="architecture",
)
v_proj_params = var(
    "arch.attn.v_proj_params", "P_v_arch", "params",
    "Value projection parameters per layer.",
    scope="architecture",
)
o_proj_params = var(
    "arch.attn.o_proj_params", "P_o_arch", "params",
    "Output projection parameters per layer.",
    scope="architecture",
)
params_attn_per_layer = var(
    "arch.attn.params_per_layer", "P_attn_layer_arch", "params",
    "Total self-attention projection parameters per layer.",
    scope="architecture",
)
ffn_weight_matrices = var(
    "arch.ffn.weight_matrices", "N_ffn_mat_arch", "matrices",
    "Number of learned FFN matrices, 2 for MLP and 3 for GLU or SwiGLU-style blocks.",
    scope="architecture",
)
params_ffn_mlp_layer = var(
    "arch.ffn.params_mlp_layer", "P_ffn_mlp_arch", "params",
    "FFN parameters per layer for a plain two-matrix MLP.",
    scope="architecture",
)
params_ffn_glu_layer = var(
    "arch.ffn.params_glu_layer", "P_ffn_glu_arch", "params",
    "FFN parameters per layer for a gated three-matrix FFN such as GeGLU or SwiGLU.",
    scope="architecture",
)
params_ffn_per_layer = var(
    "arch.ffn.params_per_layer", "P_ffn_layer_arch", "params",
    "Selected FFN parameter count per layer.",
    scope="architecture",
)
norm_param_multiplier = var(
    "arch.norm.param_multiplier", "k_norm_arch", "dimensionless",
    "Learned normalization parameters per hidden element per layer. RMSNorm uses 1, LayerNorm with bias uses 2.",
    scope="architecture",
)
params_norm_per_layer = var(
    "arch.norm.params_per_layer", "P_norm_layer_arch", "params",
    "Normalization parameters per layer.",
    scope="architecture",
)
params_block_total = var(
    "arch.block.params", "P_block_arch", "params",
    "Total parameters in one dense transformer block.",
    scope="architecture",
)
params_dense_total = var(
    "arch.params_total_dense", "P_dense_arch", "params",
    "Total dense-model parameter count from embeddings, transformer blocks, and optional untied output projection.",
    scope="architecture",
)

for _v in (
    n_layers, d_model, d_ffn, n_heads, n_kv_heads, head_dim, vocab_size,
    batch_sequences, seq_len_ctx, n_tokens_step, gqa_ratio, qk_scale,
    untied_output_factor, params_token_embed, params_output_proj,
    q_proj_params, k_proj_params, v_proj_params, o_proj_params,
    params_attn_per_layer, ffn_weight_matrices, params_ffn_mlp_layer,
    params_ffn_glu_layer, params_ffn_per_layer, norm_param_multiplier,
    params_norm_per_layer, params_block_total, params_dense_total,
):
    _v.sp_units = DIMENSIONLESS
    _v.references.append(ARCH_COUNT_REF)

for _v in (
    params_token_embed, params_output_proj, q_proj_params, k_proj_params,
    v_proj_params, o_proj_params, params_attn_per_layer,
    params_ffn_mlp_layer, params_ffn_glu_layer, params_ffn_per_layer,
    params_norm_per_layer, params_block_total, params_dense_total,
):
    _v.references.append(ARCH_PARAM_ACCOUNTING_REF)

for _v in (n_heads, n_kv_heads, head_dim, qk_scale):
    _v.references.append(TRANSFORMER_ATTENTION_REF)

for _v in (n_kv_heads, gqa_ratio, k_proj_params, v_proj_params):
    _v.references.append(GQA_REF)


eq_params_token_embed = eq(
    "arch.eq.params_token_embed",
    params_token_embed.symbol,
    vocab_size.symbol * d_model.symbol,
    "Token embedding parameters equal vocabulary size times model width.",
    check_units=True,
)

eq_params_output_proj = eq(
    "arch.eq.params_output_proj",
    params_output_proj.symbol,
    untied_output_factor.symbol * vocab_size.symbol * d_model.symbol,
    "Untied output projection parameters equal untied_factor times vocabulary size times model width.",
    check_units=True,
)

eq_q_proj_params = eq(
    "arch.eq.q_proj_params",
    q_proj_params.symbol,
    d_model.symbol * d_model.symbol,
    "Query projection uses a dense d_model by d_model matrix per layer.",
    check_units=True,
)

eq_k_proj_params = eq(
    "arch.eq.k_proj_params",
    k_proj_params.symbol,
    d_model.symbol * n_kv_heads.symbol * head_dim.symbol,
    "Key projection parameters shrink with the number of KV heads in GQA or MQA.",
    check_units=True,
)

eq_v_proj_params = eq(
    "arch.eq.v_proj_params",
    v_proj_params.symbol,
    d_model.symbol * n_kv_heads.symbol * head_dim.symbol,
    "Value projection parameters follow the same head-count scaling as keys.",
    check_units=True,
)

eq_o_proj_params = eq(
    "arch.eq.o_proj_params",
    o_proj_params.symbol,
    d_model.symbol * d_model.symbol,
    "Output projection maps concatenated heads back to model width.",
    check_units=True,
)

eq_params_attn_per_layer = eq(
    "arch.eq.params_attn_per_layer",
    params_attn_per_layer.symbol,
    q_proj_params.symbol + k_proj_params.symbol + v_proj_params.symbol + o_proj_params.symbol,
    "Attention projection parameters per layer are the sum of Q, K, V, and O projections.",
    check_units=True,
)

eq_params_ffn_mlp_layer = eq(
    "arch.eq.params_ffn_mlp_layer",
    params_ffn_mlp_layer.symbol,
    2 * d_model.symbol * d_ffn.symbol,
    "A plain MLP FFN uses up and down projection matrices.",
    check_units=True,
)

eq_params_ffn_glu_layer = eq(
    "arch.eq.params_ffn_glu_layer",
    params_ffn_glu_layer.symbol,
    3 * d_model.symbol * d_ffn.symbol,
    "A gated FFN such as GeGLU or SwiGLU uses value, gate, and output projections.",
    check_units=True,
)

eq_params_ffn_per_layer = eq(
    "arch.eq.params_ffn_per_layer",
    params_ffn_per_layer.symbol,
    ffn_weight_matrices.symbol * d_model.symbol * d_ffn.symbol,
    "Selected FFN parameter count is the number of FFN matrices times d_model times d_ffn.",
    check_units=True,
)

eq_params_norm_per_layer = eq(
    "arch.eq.params_norm_per_layer",
    params_norm_per_layer.symbol,
    norm_param_multiplier.symbol * d_model.symbol,
    "Normalization parameters scale with hidden width.",
    check_units=True,
)

eq_params_block_total = eq(
    "arch.eq.params_block_total",
    params_block_total.symbol,
    params_attn_per_layer.symbol + params_ffn_per_layer.symbol + params_norm_per_layer.symbol,
    "A dense block contains attention projections, FFN parameters, and normalization parameters.",
    check_units=True,
)

eq_params_dense_total = eq(
    "arch.eq.params_dense_total",
    params_dense_total.symbol,
    params_token_embed.symbol + n_layers.symbol * params_block_total.symbol + params_output_proj.symbol,
    "Total dense-model parameters equal embeddings plus all dense blocks plus any untied output projection.",
    check_units=True,
)


ARCH_EMBEDDINGS_VARIABLES = [
    n_layers, d_model, d_ffn, n_heads, n_kv_heads, head_dim, vocab_size,
    batch_sequences, seq_len_ctx, n_tokens_step, gqa_ratio, qk_scale,
    untied_output_factor, params_token_embed, params_output_proj,
    q_proj_params, k_proj_params, v_proj_params, o_proj_params,
    params_attn_per_layer, ffn_weight_matrices, params_ffn_mlp_layer,
    params_ffn_glu_layer, params_ffn_per_layer, norm_param_multiplier,
    params_norm_per_layer, params_block_total, params_dense_total,
]

ARCH_EMBEDDINGS_EQUATIONS = [
    eq_head_dim,
    eq_tokens_per_step,
    eq_gqa_ratio,
    eq_qk_scale,
    eq_params_token_embed,
    eq_params_output_proj,
    eq_q_proj_params,
    eq_k_proj_params,
    eq_v_proj_params,
    eq_o_proj_params,
    eq_params_attn_per_layer,
    eq_params_ffn_mlp_layer,
    eq_params_ffn_glu_layer,
    eq_params_ffn_per_layer,
    eq_params_norm_per_layer,
    eq_params_block_total,
    eq_params_dense_total,
]

for _e in ARCH_EMBEDDINGS_EQUATIONS:
    _e.references.append(ARCH_COUNT_REF)

for _e in (
    eq_params_token_embed, eq_params_output_proj, eq_q_proj_params,
    eq_k_proj_params, eq_v_proj_params, eq_o_proj_params,
    eq_params_attn_per_layer, eq_params_ffn_mlp_layer,
    eq_params_ffn_glu_layer, eq_params_ffn_per_layer,
    eq_params_norm_per_layer, eq_params_block_total, eq_params_dense_total,
):
    _e.references.append(ARCH_PARAM_ACCOUNTING_REF)

for _e in (eq_head_dim, eq_qk_scale):
    _e.references.append(TRANSFORMER_ATTENTION_REF)

for _e in (eq_gqa_ratio, eq_k_proj_params, eq_v_proj_params):
    _e.references.append(GQA_REF)


__all__ = [
    "n_layers", "d_model", "d_ffn", "n_heads", "n_kv_heads", "head_dim",
    "vocab_size", "batch_sequences", "seq_len_ctx", "n_tokens_step",
    "gqa_ratio", "qk_scale",
    "untied_output_factor", "params_token_embed", "params_output_proj",
    "q_proj_params", "k_proj_params", "v_proj_params", "o_proj_params",
    "params_attn_per_layer", "ffn_weight_matrices", "params_ffn_mlp_layer",
    "params_ffn_glu_layer", "params_ffn_per_layer", "norm_param_multiplier",
    "params_norm_per_layer", "params_block_total", "params_dense_total",
    "eq_head_dim", "eq_tokens_per_step", "eq_gqa_ratio", "eq_qk_scale",
    "eq_params_token_embed", "eq_params_output_proj", "eq_q_proj_params",
    "eq_k_proj_params", "eq_v_proj_params", "eq_o_proj_params",
    "eq_params_attn_per_layer", "eq_params_ffn_mlp_layer",
    "eq_params_ffn_glu_layer", "eq_params_ffn_per_layer",
    "eq_params_norm_per_layer", "eq_params_block_total",
    "eq_params_dense_total",
    "ARCH_EMBEDDINGS_VARIABLES", "ARCH_EMBEDDINGS_EQUATIONS",
]
