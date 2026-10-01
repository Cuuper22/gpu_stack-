"""
scopes/architecture_ffn.py
==========================

Total compute per token for a dense transformer, and encoder-decoder totals.

This module turns the per-layer pieces defined elsewhere into the numbers
people actually quote: FLOPs per token and FLOPs per training step. The FFN
term comes from its parameter count (each parameter costs a multiply and an
add per token), attention FLOPs come from the attention module, and a
miscellaneous term catches normalization and other small work. Divide the
full-sequence layer cost by sequence length, sum over layers, multiply by
tokens per step, and you have the compute bill the training and kernel
scopes must pay.

It also extends dense parameter accounting to encoder-decoder models, where
each decoder layer adds a cross-attention block on top of the ordinary stack.
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
    "Dense-model training FLOPs per step, approximated as 6 * total parameters * tokens per step (embeddings included, attention score FLOPs omitted).",
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
    references=[FFN_FLOP_REF],
    check_units=True,
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
    "Common approximation: 6 * N_total * T. N_total includes the embedding table(s), and the attention "
    "score and value matmuls (which scale with context length) are left out. Kaplan et al. 2020 write "
    "C ~ 6 N B S with N the non-embedding parameters, so this is not their form. The two errors partly "
    "cancel: against exact Megatron accounting without recompute (Narayanan et al. 2021 Eq. 4 times 3/4) "
    "it is within 3% from about 1B parameters (GPT-3 175B: -2.7%) and 23% high for Pythia-70M, where the "
    "embedding table is most of the parameters.",
    references=[
        Reference(
            "Kaplan et al., Scaling Laws for Neural Language Models, 2020, Table 1: C ~ 6 N B S "
            "with N the non-embedding parameter count. The graph uses total parameters instead.",
            kind="paper", url="https://arxiv.org/abs/2001.08361", year=2020,
        ),
        Reference(
            "Narayanan et al., Efficient Large-Scale Language Model Training on GPU Clusters "
            "Using Megatron-LM, SC21, Eq. 4: exact per-iteration FLOPs, "
            "96 B s l h^2 (1 + s/(6h) + V/(16 l h)) with activation recompute.",
            kind="paper", url="https://arxiv.org/abs/2104.04473", year=2021,
            doi="10.1145/3458817.3476209",
        ),
    ],
    check_units=True,
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
