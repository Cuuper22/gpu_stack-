"""
scopes/gpu.py
=============

Aggregator for the gpu scope.

The original gpu file carried SM counts, die-level compute aggregates,
on-chip and HBM memory bandwidth, host and fabric link aliases, and full
package-level power in one slab. It has been split into focused helpers
and re-exported here so public imports stay stable.
"""

from ..core import System

from .gpu_compute import *
from .gpu_compute import GPU_COMPUTE_EQUATIONS, GPU_COMPUTE_VARIABLES
from .gpu_memory import *
from .gpu_memory import GPU_MEMORY_EQUATIONS, GPU_MEMORY_VARIABLES
from .gpu_io import *
from .gpu_io import GPU_IO_EQUATIONS, GPU_IO_VARIABLES
from .gpu_power import *
from .gpu_power import GPU_POWER_EQUATIONS, GPU_POWER_VARIABLES


sys_gpu = System(
    name="gpu",
    scope="gpu",
    description="SM counts, package bandwidth, on-chip memory, interconnect injection, and package-level power.",
)


GPU_VARIABLES = (
    GPU_COMPUTE_VARIABLES
    + GPU_MEMORY_VARIABLES
    + GPU_IO_VARIABLES
    + GPU_POWER_VARIABLES
)

GPU_EQUATIONS = (
    GPU_COMPUTE_EQUATIONS
    + GPU_MEMORY_EQUATIONS
    + GPU_IO_EQUATIONS
    + GPU_POWER_EQUATIONS
)

for v in GPU_VARIABLES:
    sys_gpu.add(v)

for e in GPU_EQUATIONS:
    sys_gpu.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
