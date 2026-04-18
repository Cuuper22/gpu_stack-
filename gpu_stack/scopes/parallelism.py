"""
scopes/parallelism.py
=====================

Parallelism strategies and their memory and communication cost models.

The old file had the names of the dimensions, one FSDP memory formula, and two
pipeline bubble sketches. That was not enough to reason about actual training
plans. This version adds batch decomposition, activation memory, ZeRO stage
breakdowns, offload paths, and explicit TP, EP, and CP traffic formulas.
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
