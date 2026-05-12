"""
scopes/architecture_ffn.py
==========================

Dense-model FLOP counts and the encoder-decoder parameter split. Ties together
the attention and FFN per-layer costs into per-token and per-step totals, and
extends the dense parameter accounting to encoder-decoder models.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import FLOP

from .architecture_embeddings import (
    seq_len_ctx,
    params_ffn_per_layer,
    params_dense_total,
    n_tokens_step,
    n_layers,
    params_attn_per_layer,
    params_block_total,
    params_token_embed,
    params_output_proj,
)
from .architecture_attention import attn_flops_mha_per_layer


DIMENSIONLESS = sp.Integer(1)

FFN_FLOP_REF = Reference(
    "Dense transformer FLOP accounting separates FFN, attention, and "
    "miscellaneous per-layer work before converting full-sequence work to "
    "per-token work.",
    kind="model",
)
ENCODER_DECODER_REF = Reference(
    "Encoder-decoder parameter accounting adds decoder cross-attention "
    "projection blocks to the ordinary transformer block stack.",
    kind="model",
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

for _v in (
    flops_ffn_per_layer, flops_misc_per_layer, flops_per_tok_dense,
    flops_step_dense,
):
    _v.sp_units = FLOP
    _v.references.append(FFN_FLOP_REF)


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
    check_units=True,
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

for _v in (
    n_encoder_layers, n_decoder_layers, params_cross_attn_per_layer,
    params_encoder_decoder_total,
):
    _v.sp_units = DIMENSIONLESS
    _v.references.append(ENCODER_DECODER_REF)


eq_params_cross_attn_per_layer = eq(
    "arch.eq.params_cross_attn_per_layer",
    params_cross_attn_per_layer.symbol,
    params_attn_per_layer.symbol,
    "Cross-attention uses the same Q, K, V, O projection structure as self-attention.",
    check_units=True,
)

eq_params_encoder_decoder_total = eq(
    "arch.eq.params_encoder_decoder_total",
    params_encoder_decoder_total.symbol,
    params_token_embed.symbol + params_output_proj.symbol + n_encoder_layers.symbol * params_block_total.symbol + n_decoder_layers.symbol * (params_block_total.symbol + params_cross_attn_per_layer.symbol),
    "Encoder-decoder models add cross-attention blocks to decoder layers on top of the ordinary dense block structure.",
    check_units=True,
)


ARCH_FFN_VARIABLES = [
    flops_ffn_per_layer, flops_misc_per_layer, flops_per_tok_dense,
    flops_step_dense,
    n_encoder_layers, n_decoder_layers, params_cross_attn_per_layer,
    params_encoder_decoder_total,
]

ARCH_FFN_EQUATIONS = [
    eq_flops_ffn_per_layer,
    eq_flops_per_token_dense,
    eq_flops_step_dense,
    eq_params_cross_attn_per_layer,
    eq_params_encoder_decoder_total,
]

for _e in (eq_flops_ffn_per_layer, eq_flops_per_token_dense, eq_flops_step_dense):
    _e.references.append(FFN_FLOP_REF)

for _e in (eq_params_cross_attn_per_layer, eq_params_encoder_decoder_total):
    _e.references.append(ENCODER_DECODER_REF)


__all__ = [
    "flops_ffn_per_layer", "flops_misc_per_layer", "flops_per_tok_dense",
    "flops_step_dense",
    "n_encoder_layers", "n_decoder_layers", "params_cross_attn_per_layer",
    "params_encoder_decoder_total",
    "eq_flops_ffn_per_layer", "eq_flops_per_token_dense",
    "eq_flops_step_dense",
    "eq_params_cross_attn_per_layer", "eq_params_encoder_decoder_total",
    "ARCH_FFN_VARIABLES", "ARCH_FFN_EQUATIONS",
]
