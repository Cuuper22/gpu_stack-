"""
scopes/parallelism.py
=====================

Aggregator for parallelism: how a model too big for one GPU gets split.

A training plan splits work along up to six axes — data parallel (copies
of the model on different batches), tensor parallel (one layer's matrices
split across GPUs), sequence parallel (nested in TP), pipeline parallel
(consecutive layers on different GPUs), expert parallel (MoE experts
spread out), and context parallel (the sequence itself split). The product
of the degrees is the GPU count, and every choice trades memory against
communication.

The helpers price both sides. Batching decomposes the global batch and
counts parameter, gradient, optimizer, and activation memory per GPU;
zero_fsdp shards that state and models CPU/NVMe offload; pipeline gives
the bubble fraction of each schedule; moe covers TP, EP, and CP traffic.
The collective scope prices the resulting messages, and training folds
everything into step time. This file re-exports the four helpers so
public imports stay stable.
"""

from ..core import System

from .parallelism_batching import *
from .parallelism_batching import (
    PARALLELISM_BATCHING_EQUATIONS,
    PARALLELISM_BATCHING_VARIABLES,
)
from .parallelism_zero_fsdp import *
from .parallelism_zero_fsdp import (
    PARALLELISM_ZERO_FSDP_EQUATIONS,
    PARALLELISM_ZERO_FSDP_VARIABLES,
)
from .parallelism_pipeline import *
from .parallelism_pipeline import (
    PARALLELISM_PIPELINE_EQUATIONS,
    PARALLELISM_PIPELINE_VARIABLES,
)
from .parallelism_moe import *
from .parallelism_moe import (
    PARALLELISM_MOE_EQUATIONS,
    PARALLELISM_MOE_VARIABLES,
)


sys_par = System(
    name="parallelism",
    scope="parallelism",
    description="DP, TP, SP, PP, EP, CP memory and communication cost models.",
)


PARALLELISM_VARIABLES = (
    PARALLELISM_BATCHING_VARIABLES
    + PARALLELISM_ZERO_FSDP_VARIABLES
    + PARALLELISM_PIPELINE_VARIABLES
    + PARALLELISM_MOE_VARIABLES
)

PARALLELISM_EQUATIONS = (
    PARALLELISM_BATCHING_EQUATIONS
    + PARALLELISM_ZERO_FSDP_EQUATIONS
    + PARALLELISM_PIPELINE_EQUATIONS
    + PARALLELISM_MOE_EQUATIONS
)

for v in PARALLELISM_VARIABLES:
    sys_par.add(v)

for e in PARALLELISM_EQUATIONS:
    sys_par.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
