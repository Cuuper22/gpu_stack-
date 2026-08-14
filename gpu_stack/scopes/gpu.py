"""
scopes/gpu.py
=============

Aggregator for the gpu scope: one whole GPU package, seen as a device.

Lower scopes describe pieces — one SM's arithmetic, one HBM stack, one
memory array. This scope assembles them into the device a programmer or
cluster planner sees: how many SMs fit on the die and the peak FLOPs they
deliver (gpu_compute), the total on-chip and HBM capacity and bandwidth
(gpu_memory), the PCIe, NVLink, and NIC links at the package boundary
(gpu_io), and the power budget that ties them together — compute, memory,
and fabric power against TDP, with the throttle and efficiency figures
that follow (gpu_power). The node and kernel scopes both build directly on
these package-level numbers. This file re-exports the four helpers so
public imports stay stable.
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
