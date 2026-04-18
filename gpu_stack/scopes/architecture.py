"""
scopes/architecture.py
======================

Model architecture, from embeddings and positional encoding through attention,
FFN variants, normalization, and MoE routing.

The previous file had hidden dimension, head count, a rough dense FLOP count,
KV cache bytes, and a sparse MoE ratio. It was missing the actual parameter
structure of the block. This version makes the block legible.
"""

import sympy as sp
from ..core import System, eq, var


sys_arch = System(
    name="architecture",
    scope="architecture",
    description="Transformer blocks, attention variants, FFN variants, normalization, and MoE.",
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
)

eq_tokens_per_step = eq(
    "arch.eq.tokens_per_step",
    n_tokens_step.symbol,
    batch_sequences.symbol * seq_len_ctx.symbol,
    "Tokens per step equal sequences per step times context length.",
)

eq_gqa_ratio = eq(
    "arch.eq.gqa_ratio",
    gqa_ratio.symbol,
    n_heads.symbol / n_kv_heads.symbol,
    "GQA ratio is query heads divided by KV heads.",
)

eq_qk_scale = eq(
    "arch.eq.qk_scale",
    qk_scale.symbol,
    1 / sp.sqrt(head_dim.symbol),
    "Scaled dot-product attention divides logits by sqrt(head_dim).",
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


eq_params_token_embed = eq(
    "arch.eq.params_token_embed",
    params_token_embed.symbol,
    vocab_size.symbol * d_model.symbol,
    "Token embedding parameters equal vocabulary size times model width.",
)

eq_params_output_proj = eq(
    "arch.eq.params_output_proj",
    params_output_proj.symbol,
    untied_output_factor.symbol * vocab_size.symbol * d_model.symbol,
    "Untied output projection parameters equal untied_factor times vocabulary size times model width.",
)

eq_q_proj_params = eq(
    "arch.eq.q_proj_params",
    q_proj_params.symbol,
    d_model.symbol * d_model.symbol,
    "Query projection uses a dense d_model by d_model matrix per layer.",
)

eq_k_proj_params = eq(
    "arch.eq.k_proj_params",
    k_proj_params.symbol,
    d_model.symbol * n_kv_heads.symbol * head_dim.symbol,
    "Key projection parameters shrink with the number of KV heads in GQA or MQA.",
)

eq_v_proj_params = eq(
    "arch.eq.v_proj_params",
    v_proj_params.symbol,
    d_model.symbol * n_kv_heads.symbol * head_dim.symbol,
    "Value projection parameters follow the same head-count scaling as keys.",
)

eq_o_proj_params = eq(
    "arch.eq.o_proj_params",
    o_proj_params.symbol,
    d_model.symbol * d_model.symbol,
    "Output projection maps concatenated heads back to model width.",
)

eq_params_attn_per_layer = eq(
    "arch.eq.params_attn_per_layer",
    params_attn_per_layer.symbol,
    q_proj_params.symbol + k_proj_params.symbol + v_proj_params.symbol + o_proj_params.symbol,
    "Attention projection parameters per layer are the sum of Q, K, V, and O projections.",
)

eq_params_ffn_mlp_layer = eq(
    "arch.eq.params_ffn_mlp_layer",
    params_ffn_mlp_layer.symbol,
    2 * d_model.symbol * d_ffn.symbol,
    "A plain MLP FFN uses up and down projection matrices.",
)

eq_params_ffn_glu_layer = eq(
    "arch.eq.params_ffn_glu_layer",
    params_ffn_glu_layer.symbol,
    3 * d_model.symbol * d_ffn.symbol,
    "A gated FFN such as GeGLU or SwiGLU uses value, gate, and output projections.",
)

eq_params_ffn_per_layer = eq(
    "arch.eq.params_ffn_per_layer",
    params_ffn_per_layer.symbol,
    ffn_weight_matrices.symbol * d_model.symbol * d_ffn.symbol,
    "Selected FFN parameter count is the number of FFN matrices times d_model times d_ffn.",
)

eq_params_norm_per_layer = eq(
    "arch.eq.params_norm_per_layer",
    params_norm_per_layer.symbol,
    norm_param_multiplier.symbol * d_model.symbol,
    "Normalization parameters scale with hidden width.",
)

eq_params_block_total = eq(
    "arch.eq.params_block_total",
    params_block_total.symbol,
    params_attn_per_layer.symbol + params_ffn_per_layer.symbol + params_norm_per_layer.symbol,
    "A dense block contains attention projections, FFN parameters, and normalization parameters.",
)

eq_params_dense_total = eq(
    "arch.eq.params_dense_total",
    params_dense_total.symbol,
    params_token_embed.symbol + n_layers.symbol * params_block_total.symbol + params_output_proj.symbol,
    "Total dense-model parameters equal embeddings plus all dense blocks plus any untied output projection.",
)


# ---------------------------------------------------------------------------
# Positional encoding
# ---------------------------------------------------------------------------

position_index = var(
    "arch.pos.index", "p_pos_arch", "tokens",
    "Token position index.",
    scope="architecture",
)
head_pair_index = var(
    "arch.pos.head_pair_index", "i_pair_arch", "dimensionless",
    "Pair index inside the rotary or sinusoidal subspace.",
    scope="architecture",
)
sinusoid_base = var(
    "arch.pos.sinusoid_base", "theta_sin_arch", "dimensionless",
    "Base used by sinusoidal positional encoding.",
    scope="architecture",
)
sinusoid_inv_freq = var(
    "arch.pos.sinusoid_inv_freq", "omega_sin_arch", "dimensionless",
    "Inverse-frequency factor for one sinusoidal pair.",
    scope="architecture",
)
sinusoid_phase = var(
    "arch.pos.sinusoid_phase", "phi_sin_arch", "dimensionless",
    "Sinusoidal phase for one coordinate pair.",
    scope="architecture",
)
rope_theta_base = var(
    "arch.pos.rope_theta_base", "theta_rope_arch", "dimensionless",
    "RoPE base frequency parameter.",
    scope="architecture",
)
rope_rotary_dim = var(
    "arch.pos.rope_rotary_dim", "d_rope_arch", "dim",
    "Dimension participating in RoPE.",
    scope="architecture",
)
rope_inv_freq = var(
    "arch.pos.rope_inv_freq", "omega_rope_arch", "dimensionless",
    "RoPE inverse-frequency term for one pair.",
    scope="architecture",
)
rope_angle = var(
    "arch.pos.rope_angle", "phi_rope_arch", "dimensionless",
    "RoPE rotation angle for one pair.",
    scope="architecture",
)
relative_distance = var(
    "arch.pos.relative_distance", "Delta_pos_arch", "tokens",
    "Relative token distance used by ALiBi.",
    scope="architecture",
)
alibi_slope = var(
    "arch.pos.alibi_slope", "m_alibi_arch", "dimensionless",
    "ALiBi slope for one head.",
    scope="architecture",
)
alibi_bias = var(
    "arch.pos.alibi_bias", "b_alibi_arch", "dimensionless",
    "Attention bias contributed by ALiBi.",
    scope="architecture",
)
context_train_len = var(
    "arch.pos.context_train_len", "L_train_ctx_arch", "tokens",
    "Context length used during base training of the positional scheme.",
    scope="architecture",
)
context_target_len = var(
    "arch.pos.context_target_len", "L_target_ctx_arch", "tokens",
    "Target context length after extension.",
    scope="architecture",
)
yarn_scale = var(
    "arch.pos.yarn_scale", "s_yarn_arch", "dimensionless",
    "Context-extension scale factor used by YaRN-style RoPE stretching.",
    scope="architecture",
)


eq_sinusoid_inv_freq = eq(
    "arch.eq.sinusoid_inv_freq",
    sinusoid_inv_freq.symbol,
    sinusoid_base.symbol ** (-2 * head_pair_index.symbol / d_model.symbol),
    "Sinusoidal encodings use exponentially spaced inverse frequencies across coordinate pairs.",
)

eq_sinusoid_phase = eq(
    "arch.eq.sinusoid_phase",
    sinusoid_phase.symbol,
    position_index.symbol * sinusoid_inv_freq.symbol,
    "The sinusoidal phase is position times inverse frequency.",
)

eq_rope_inv_freq = eq(
    "arch.eq.rope_inv_freq",
    rope_inv_freq.symbol,
    rope_theta_base.symbol ** (-2 * head_pair_index.symbol / rope_rotary_dim.symbol),
    "RoPE uses exponentially spaced inverse frequencies across the rotary subspace.",
)

eq_rope_angle = eq(
    "arch.eq.rope_angle",
    rope_angle.symbol,
    position_index.symbol * rope_inv_freq.symbol,
    "RoPE rotates each pair by position times inverse frequency.",
)

eq_alibi_bias = eq(
    "arch.eq.alibi_bias",
    alibi_bias.symbol,
    -alibi_slope.symbol * relative_distance.symbol,
    "ALiBi adds a head-specific linear penalty with distance.",
)

eq_yarn_scale = eq(
    "arch.eq.yarn_scale",
    yarn_scale.symbol,
    context_target_len.symbol / context_train_len.symbol,
    "A simple context-extension scale is target context divided by training context.",
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


eq_attn_logits = eq(
    "arch.eq.attn_logits",
    attn_logits.symbol,
    q_tensor.symbol * k_tensor.symbol * qk_scale.symbol,
    "Scaled dot-product attention forms logits from Q K^T divided by sqrt(head_dim). The transpose is abstracted here into the symbolic tensor product.",
)

eq_attn_output = eq(
    "arch.eq.attn_output",
    attn_output.symbol,
    sp.Function("softmax")(attn_logits.symbol) * v_tensor.symbol,
    "Attention output is softmax(logits) times V, represented here as an abstract tensor expression.",
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
)

eq_kv_mla = eq(
    "arch.eq.kv_mla",
    kv_bytes_per_tok_layer_mla.symbol,
    2 * d_latent_mla.symbol * bytes_per_param_kv.symbol,
    "MLA stores compressed latent K and V states rather than per-head full-width KV tensors.",
)

eq_kv_compression_ratio = eq(
    "arch.eq.kv_compression_ratio",
    kv_compression_ratio.symbol,
    kv_bytes_per_tok_layer.symbol / kv_bytes_per_tok_layer_mla.symbol,
    "KV compression ratio is the GQA cache footprint divided by the MLA cache footprint.",
)

eq_kv_total = eq(
    "arch.eq.kv_total",
    kv_total_bytes.symbol,
    n_layers.symbol * seq_len_ctx.symbol * kv_bytes_per_tok_layer.symbol,
    "Total KV cache equals layers times sequence length times KV bytes per token per layer.",
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


eq_sigmoid_x = eq(
    "arch.eq.sigmoid_x",
    sigmoid_x.symbol,
    1 / (1 + sp.exp(-act_x.symbol)),
    "Sigmoid is 1 / (1 + exp(-x)).",
)

eq_gelu_output = eq(
    "arch.eq.gelu",
    gelu_output.symbol,
    act_x.symbol * (1 + sp.erf(act_x.symbol / sp.sqrt(2))) / 2,
    "GeLU equals x times the Gaussian CDF of x.",
)

eq_silu_output = eq(
    "arch.eq.silu",
    silu_output.symbol,
    act_x.symbol / (1 + sp.exp(-act_x.symbol)),
    "SiLU equals x times sigmoid(x).",
)

eq_swiglu_output = eq(
    "arch.eq.swiglu",
    swiglu_output.symbol,
    swiglu_value.symbol / (1 + sp.exp(-swiglu_gate.symbol)),
    "SwiGLU multiplies the value branch by SiLU applied to the gate branch.",
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


eq_layernorm_output = eq(
    "arch.eq.layernorm_output",
    layernorm_output.symbol,
    (norm_x.symbol - norm_mean.symbol) / sp.sqrt(norm_var.symbol + norm_eps.symbol),
    "LayerNorm subtracts the mean and divides by the standard deviation.",
)

eq_rmsnorm_output = eq(
    "arch.eq.rmsnorm_output",
    rmsnorm_output.symbol,
    norm_x.symbol / sp.sqrt(norm_var.symbol + norm_eps.symbol),
    "RMSNorm skips mean subtraction and divides by the root mean square scale.",
)


# ---------------------------------------------------------------------------
# Dense-model FLOP counts
# ---------------------------------------------------------------------------

flops_ffn_per_layer = var(
    "arch.ffn.flops_per_layer", "F_ffn_L_arch", "FLOP",
    "FFN FLOPs per layer for one full sequence.",
    scope="architecture",
)
flops_misc_per_layer = var(
    "arch.misc.flops_per_layer", "F_misc_L_arch", "FLOP",
    "Miscellaneous per-layer FLOPs, such as norm and elementwise work, not captured by the large matrix multiplies.",
    scope="architecture",
)
flops_per_tok_dense = var(
    "arch.flops.per_token_dense", "F_tok_dense_arch", "FLOP/token",
    "Dense transformer forward FLOPs per token.",
    scope="architecture",
)
flops_step_dense = var(
    "arch.flops.step_dense", "F_step_dense_arch", "FLOP",
    "Dense-model training FLOPs per step.",
    scope="architecture",
)


eq_flops_ffn_per_layer = eq(
    "arch.eq.flops_ffn_per_layer",
    flops_ffn_per_layer.symbol,
    2 * seq_len_ctx.symbol * params_ffn_per_layer.symbol,
    "FFN FLOPs per layer for one sequence equal two FLOPs per parameter application times sequence length.",
)

eq_flops_per_token_dense = eq(
    "arch.eq.flops_per_token_dense",
    flops_per_tok_dense.symbol,
    n_layers.symbol * (attn_flops_mha_per_layer.symbol + flops_ffn_per_layer.symbol + flops_misc_per_layer.symbol) / seq_len_ctx.symbol,
    "Dense forward FLOPs per token equal the per-layer full-sequence cost divided by sequence length, summed over layers.",
)

eq_flops_step_dense = eq(
    "arch.eq.flops_step_dense",
    flops_step_dense.symbol,
    6 * params_dense_total.symbol * n_tokens_step.symbol,
    "The standard dense-training estimate is 6 times parameter count times tokens per step.",
    references=["Kaplan et al., Scaling Laws for Neural Language Models, 2020."],
)


# ---------------------------------------------------------------------------
# Encoder-decoder split
# ---------------------------------------------------------------------------

n_encoder_layers = var(
    "arch.encdec.n_encoder_layers", "L_enc_arch", "layers",
    "Encoder layers in an encoder-decoder model.",
    scope="architecture",
)
n_decoder_layers = var(
    "arch.encdec.n_decoder_layers", "L_dec_arch", "layers",
    "Decoder layers in an encoder-decoder model.",
    scope="architecture",
)
params_cross_attn_per_layer = var(
    "arch.encdec.cross_attn_params_per_layer", "P_xattn_arch", "params",
    "Cross-attention parameters per decoder layer.",
    scope="architecture",
)
params_encoder_decoder_total = var(
    "arch.encdec.params_total", "P_encdec_arch", "params",
    "Total parameters of an encoder-decoder transformer built from the same block primitives.",
    scope="architecture",
)


eq_params_cross_attn_per_layer = eq(
    "arch.eq.params_cross_attn_per_layer",
    params_cross_attn_per_layer.symbol,
    params_attn_per_layer.symbol,
    "Cross-attention uses the same Q, K, V, O projection structure as self-attention.",
)

eq_params_encoder_decoder_total = eq(
    "arch.eq.params_encoder_decoder_total",
    params_encoder_decoder_total.symbol,
    params_token_embed.symbol + params_output_proj.symbol + n_encoder_layers.symbol * params_block_total.symbol + n_decoder_layers.symbol * (params_block_total.symbol + params_cross_attn_per_layer.symbol),
    "Encoder-decoder models add cross-attention blocks to decoder layers on top of the ordinary dense block structure.",
)


# ---------------------------------------------------------------------------
# MoE routing and sparsity
# ---------------------------------------------------------------------------

n_moe_layers = var(
    "arch.moe.n_moe_layers", "L_moe_arch", "layers",
    "Number of MoE layers in the model.",
    scope="architecture",
)
n_experts = var(
    "arch.moe.n_experts", "N_exp_arch", "experts",
    "Experts per MoE layer.",
    scope="architecture",
)
active_experts = var(
    "arch.moe.active_experts", "k_exp_arch", "experts",
    "Experts activated per token.",
    scope="architecture",
)
sparsity_ratio = var(
    "arch.moe.sparsity", "s_moe_arch", "dimensionless",
    "MoE sparsity ratio, total experts divided by active experts.",
    scope="architecture",
)
params_expert_each = var(
    "arch.moe.params_expert_each", "P_exp_each_arch", "params",
    "Parameters in one expert.",
    scope="architecture",
)
params_router = var(
    "arch.moe.params_router", "P_router_arch", "params",
    "Router parameters per MoE layer.",
    scope="architecture",
)
shared_expert_count = var(
    "arch.moe.shared_expert_count", "N_shared_exp_arch", "experts",
    "Shared experts present in every token path.",
    scope="architecture",
)
shared_expert_params_each = var(
    "arch.moe.shared_expert_params_each", "P_shared_each_arch", "params",
    "Parameters in one shared expert.",
    scope="architecture",
)
params_shared_experts = var(
    "arch.moe.params_shared", "P_shared_arch", "params",
    "Shared-expert parameters per MoE layer.",
    scope="architecture",
)
params_moe_layer_total = var(
    "arch.moe.params_layer_total", "P_moe_layer_total_arch", "params",
    "Total parameters instantiated by one MoE layer.",
    scope="architecture",
)
params_moe_layer_active = var(
    "arch.moe.params_layer_active", "P_moe_layer_active_arch", "params",
    "Active parameters touched by one token path through one MoE layer.",
    scope="architecture",
)
params_total_moe = var(
    "arch.moe.params_total", "P_moe_total_arch", "params",
    "Total parameters across all MoE layers.",
    scope="architecture",
)
params_active_moe = var(
    "arch.moe.params_active", "P_moe_active_arch", "params",
    "Active parameters per token path across all MoE layers.",
    scope="architecture",
)
moe_tokens_batch = var(
    "arch.moe.tokens_batch", "T_moe_batch_arch", "tokens",
    "Tokens entering one MoE layer in a batch.",
    scope="architecture",
)
moe_capacity_factor = var(
    "arch.moe.capacity_factor", "rho_cap_arch", "dimensionless",
    "Capacity factor above mean routed load.",
    scope="architecture",
)
expert_capacity = var(
    "arch.moe.expert_capacity", "C_exp_arch", "tokens",
    "Capacity reserved per expert.",
    scope="architecture",
)
router_fi_pi_sum = var(
    "arch.moe.router_fi_pi_sum", "S_bal_arch", "dimensionless",
    "The sum over experts of token fraction times average router probability.",
    scope="architecture",
)
load_balance_loss = var(
    "arch.moe.load_balance_loss", "L_bal_arch", "dimensionless",
    "Auxiliary MoE load-balance loss.",
    scope="architecture",
)
router_log_z = var(
    "arch.moe.router_log_z", "logZ_arch", "dimensionless",
    "Log partition function at the router.",
    scope="architecture",
    positive=False,
)
router_z_loss = var(
    "arch.moe.router_z_loss", "L_z_arch", "dimensionless",
    "Router z-loss.",
    scope="architecture",
)
flops_step_moe = var(
    "arch.flops.step_moe", "F_step_moe_arch", "FLOP",
    "MoE training FLOPs per step.",
    scope="architecture",
)


eq_sparsity = eq(
    "arch.eq.sparsity",
    sparsity_ratio.symbol,
    n_experts.symbol / active_experts.symbol,
    "MoE sparsity ratio equals total experts divided by active experts.",
)

eq_params_shared_experts = eq(
    "arch.eq.params_shared_experts",
    params_shared_experts.symbol,
    shared_expert_count.symbol * shared_expert_params_each.symbol,
    "Shared-expert parameters equal shared expert count times parameters per shared expert.",
)

eq_params_moe_layer_total = eq(
    "arch.eq.params_moe_layer_total",
    params_moe_layer_total.symbol,
    n_experts.symbol * params_expert_each.symbol + params_shared_experts.symbol + params_router.symbol,
    "Total MoE-layer parameters include all experts, shared experts, and the router.",
)

eq_params_moe_layer_active = eq(
    "arch.eq.params_moe_layer_active",
    params_moe_layer_active.symbol,
    active_experts.symbol * params_expert_each.symbol + params_shared_experts.symbol + params_router.symbol,
    "Active MoE-layer parameters include only the active experts plus shared experts and the router.",
)

eq_params_total_moe = eq(
    "arch.eq.params_total_moe",
    params_total_moe.symbol,
    n_moe_layers.symbol * params_moe_layer_total.symbol,
    "Total MoE parameters equal MoE layers times parameters instantiated per MoE layer.",
)

eq_params_active_moe = eq(
    "arch.eq.params_active_moe",
    params_active_moe.symbol,
    n_moe_layers.symbol * params_moe_layer_active.symbol,
    "Active MoE parameters per token path equal MoE layers times active parameters per MoE layer.",
)

eq_expert_capacity = eq(
    "arch.eq.expert_capacity",
    expert_capacity.symbol,
    moe_capacity_factor.symbol * moe_tokens_batch.symbol * active_experts.symbol / n_experts.symbol,
    "Expert capacity equals mean routed tokens per expert times the capacity factor.",
)

eq_load_balance_loss = eq(
    "arch.eq.load_balance_loss",
    load_balance_loss.symbol,
    n_experts.symbol * router_fi_pi_sum.symbol,
    "The common MoE auxiliary balancing loss is number_of_experts times the sum over experts of token fraction times average routing probability.",
)

eq_router_z_loss = eq(
    "arch.eq.router_z_loss",
    router_z_loss.symbol,
    router_log_z.symbol ** 2,
    "Router z-loss penalizes the square of log Z.",
)

eq_flops_step_moe = eq(
    "arch.eq.flops_step_moe",
    flops_step_moe.symbol,
    6 * params_active_moe.symbol * n_tokens_step.symbol,
    "MoE training FLOPs depend on active parameters, not total instantiated parameters.",
)


ARCHITECTURE_VARIABLES = [
    n_layers, d_model, d_ffn, n_heads, n_kv_heads, head_dim, vocab_size,
    batch_sequences, seq_len_ctx, n_tokens_step, gqa_ratio, qk_scale,
    untied_output_factor, params_token_embed, params_output_proj,
    q_proj_params, k_proj_params, v_proj_params, o_proj_params,
    params_attn_per_layer, ffn_weight_matrices, params_ffn_mlp_layer,
    params_ffn_glu_layer, params_ffn_per_layer, norm_param_multiplier,
    params_norm_per_layer, params_block_total, params_dense_total,
    position_index, head_pair_index, sinusoid_base, sinusoid_inv_freq,
    sinusoid_phase, rope_theta_base, rope_rotary_dim, rope_inv_freq,
    rope_angle, relative_distance, alibi_slope, alibi_bias,
    context_train_len, context_target_len, yarn_scale,
    q_tensor, k_tensor, v_tensor, attn_logits, attn_output,
    attn_proj_flops_per_layer, attn_scores_flops_per_layer,
    attn_values_flops_per_layer, attn_flops_mha_per_layer,
    attn_flops_sparse_per_layer, d_latent_mla, bytes_per_param_kv,
    kv_bytes_per_tok_layer, kv_bytes_per_tok_layer_mla, kv_compression_ratio,
    kv_total_bytes, k_sparse,
    act_x, sigmoid_x, gelu_output, silu_output, swiglu_gate, swiglu_value,
    swiglu_output,
    norm_x, norm_mean, norm_var, norm_eps, layernorm_output, rmsnorm_output,
    flops_ffn_per_layer, flops_misc_per_layer, flops_per_tok_dense,
    flops_step_dense,
    n_encoder_layers, n_decoder_layers, params_cross_attn_per_layer,
    params_encoder_decoder_total,
    n_moe_layers, n_experts, active_experts, sparsity_ratio,
    params_expert_each, params_router, shared_expert_count,
    shared_expert_params_each, params_shared_experts, params_moe_layer_total,
    params_moe_layer_active, params_total_moe, params_active_moe,
    moe_tokens_batch, moe_capacity_factor, expert_capacity,
    router_fi_pi_sum, load_balance_loss, router_log_z, router_z_loss,
    flops_step_moe,
]

ARCHITECTURE_EQUATIONS = [
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
    eq_sinusoid_inv_freq,
    eq_sinusoid_phase,
    eq_rope_inv_freq,
    eq_rope_angle,
    eq_alibi_bias,
    eq_yarn_scale,
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
    eq_flops_ffn_per_layer,
    eq_flops_per_token_dense,
    eq_flops_step_dense,
    eq_params_cross_attn_per_layer,
    eq_params_encoder_decoder_total,
    eq_sparsity,
    eq_params_shared_experts,
    eq_params_moe_layer_total,
    eq_params_moe_layer_active,
    eq_params_total_moe,
    eq_params_active_moe,
    eq_expert_capacity,
    eq_load_balance_loss,
    eq_router_z_loss,
    eq_flops_step_moe,
]

for v in ARCHITECTURE_VARIABLES:
    sys_arch.add(v)

for e in ARCHITECTURE_EQUATIONS:
    sys_arch.add(e)
