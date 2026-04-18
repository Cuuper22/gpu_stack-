"""
scopes/kernel.py
=================

Single-kernel performance models.

The old file had a toy roofline and one naive GEMM arithmetic-intensity
formula. That is not enough. Real kernels are constrained by several
ceilings at once:

  * compute issue efficiency
  * HBM, L2, SMEM, and register bandwidth
  * occupancy-driven latency hiding
  * CTA resource limits from threads, registers, and shared memory
  * tiling, which changes effective bytes and therefore arithmetic intensity

This scope adds those missing pieces while keeping the original public
variables alive.
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
