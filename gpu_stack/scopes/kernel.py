"""
scopes/kernel.py
=================

Aggregator for the kernel scope: how long one GPU kernel actually takes.

A kernel is one launched GPU program — a matmul, an attention pass — and
its runtime is set by whichever ceiling it hits first. The roofline helper
supplies the ceilings: peak compute, plus separate bandwidth limits at
HBM, L2, shared memory, and the register file, chosen by the kernel's
arithmetic intensity (FLOPs per byte moved). The occupancy helper covers
the latency side: how many blocks fit on an SM given thread, register,
and shared-memory budgets, and whether the resident warps can hide memory
latency.

Two worked kernels close the loop. The GEMM helper shows how CTA tiling
cuts HBM traffic and raises arithmetic intensity; the attention helper
contrasts naive attention with FlashAttention's tiled online softmax. The
training scope consumes these kernel times as the compute part of a step.
"""

from ..core import System

from .kernel_roofline import *
from .kernel_roofline import KERNEL_ROOFLINE_EQUATIONS, KERNEL_ROOFLINE_VARIABLES
from .kernel_occupancy import *
from .kernel_occupancy import KERNEL_OCCUPANCY_EQUATIONS, KERNEL_OCCUPANCY_VARIABLES
from .kernel_gemm import *
from .kernel_gemm import KERNEL_GEMM_EQUATIONS, KERNEL_GEMM_VARIABLES
from .kernel_attention import *
from .kernel_attention import KERNEL_ATTENTION_EQUATIONS, KERNEL_ATTENTION_VARIABLES


sys_kern = System(
    name="kernel",
    scope="kernel",
    description="Kernel rooflines, occupancy, CTA resource limits, and tiled matmul or attention arithmetic intensity.",
)


KERNEL_VARIABLES = (
    KERNEL_ROOFLINE_VARIABLES
    + KERNEL_OCCUPANCY_VARIABLES
    + KERNEL_GEMM_VARIABLES
    + KERNEL_ATTENTION_VARIABLES
)

KERNEL_EQUATIONS = (
    KERNEL_ROOFLINE_EQUATIONS
    + KERNEL_OCCUPANCY_EQUATIONS
    + KERNEL_GEMM_EQUATIONS
    + KERNEL_ATTENTION_EQUATIONS
)

for v in KERNEL_VARIABLES:
    sys_kern.add(v)

for e in KERNEL_EQUATIONS:
    sys_kern.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
