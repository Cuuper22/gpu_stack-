"""
Shared citation objects for the attention helper modules.

The attention math is split across three files (core, activations,
normalization), but they cite the same handful of sources: the original
Transformer attention form, dense and sparse FLOP accounting conventions,
and KV-cache bookkeeping. Defining each Reference once here keeps the
citations identical everywhere they appear and avoids circular imports
between the helpers. The DIMENSIONLESS constant lives here for the same
reason: it is the unit tag every helper needs.
"""

import sympy as sp

from ..core import Reference


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


__all__ = [
    "DIMENSIONLESS",
    "ATTENTION_REF",
    "ATTENTION_FLOP_REF",
    "SPARSE_ATTENTION_REF",
    "KV_CACHE_REF",
    "ACTIVATION_REF",
    "NORMALIZATION_REF",
]
