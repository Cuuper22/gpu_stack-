"""
scopes/architecture.py
======================

Aggregator for the architecture scope.

The original file carried embeddings, positional encoding, attention math,
KV cache, activations, normalization, dense FLOP counts, encoder-decoder
splits, and MoE routing in one slab. It has been split into focused helpers
and re-exported here so public imports stay stable.
"""

from ..core import System

from .architecture_embeddings import *
from .architecture_embeddings import (
    ARCH_EMBEDDINGS_EQUATIONS,
    ARCH_EMBEDDINGS_VARIABLES,
)
from .architecture_positions import *
from .architecture_positions import (
    ARCH_POSITIONS_EQUATIONS,
    ARCH_POSITIONS_VARIABLES,
)
from .architecture_attention import *
from .architecture_attention import (
    ARCH_ATTENTION_EQUATIONS,
    ARCH_ATTENTION_VARIABLES,
)
from .architecture_ffn import *
from .architecture_ffn import (
    ARCH_FFN_EQUATIONS,
    ARCH_FFN_VARIABLES,
)
from .architecture_moe import *
from .architecture_moe import (
    ARCH_MOE_EQUATIONS,
    ARCH_MOE_VARIABLES,
)


sys_arch = System(
    name="architecture",
    scope="architecture",
    description="Transformer blocks, attention variants, FFN variants, normalization, and MoE.",
)


ARCHITECTURE_VARIABLES = (
    ARCH_EMBEDDINGS_VARIABLES
    + ARCH_POSITIONS_VARIABLES
    + ARCH_ATTENTION_VARIABLES
    + ARCH_FFN_VARIABLES
    + ARCH_MOE_VARIABLES
)

ARCHITECTURE_EQUATIONS = (
    ARCH_EMBEDDINGS_EQUATIONS
    + ARCH_POSITIONS_EQUATIONS
    + ARCH_ATTENTION_EQUATIONS
    + ARCH_FFN_EQUATIONS
    + ARCH_MOE_EQUATIONS
)

for v in ARCHITECTURE_VARIABLES:
    sys_arch.add(v)

for e in ARCHITECTURE_EQUATIONS:
    sys_arch.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
