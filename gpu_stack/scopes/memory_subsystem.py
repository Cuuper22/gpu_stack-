"""
scopes/memory_subsystem.py
==========================

Aggregator for the GPU memory hierarchy, registers out to host memory.

A GPU's memory is a ladder of levels, each roughly ten times bigger and
ten times slower than the one below: per-thread registers, shared memory
and L1 inside the SM, the die-wide L2, HBM on the package, and finally
host memory across PCIe or CXL. Each level's helper module models not
just its size but the machinery that sets its real cost — banked access
and conflicts for registers and SMEM, line-and-set organization and miss
penalties for the caches, refresh, ECC, and compression for HBM, and TLB
reach, page migration, and NUMA penalties for the virtual-memory layer.

The kernel scope reads these bandwidths as roofline ceilings, and the gpu
scope rolls the per-SM figures up to the package. This file re-exports
the five helpers so public imports stay stable.
"""

from ..core import System

from .memory_regfile import *
from .memory_regfile import MEMSUB_REGFILE_EQUATIONS, MEMSUB_REGFILE_VARIABLES
from .memory_smem import *
from .memory_smem import MEMSUB_SMEM_EQUATIONS, MEMSUB_SMEM_VARIABLES
from .memory_cache import *
from .memory_cache import MEMSUB_CACHE_EQUATIONS, MEMSUB_CACHE_VARIABLES
from .memory_hbm import *
from .memory_hbm import MEMSUB_HBM_EQUATIONS, MEMSUB_HBM_VARIABLES
from .memory_virtual import *
from .memory_virtual import MEMSUB_VIRTUAL_EQUATIONS, MEMSUB_VIRTUAL_VARIABLES


sys_mem = System(
    name="memory_subsystem",
    scope="memory_subsystem",
    description="Register file, SMEM, TMEM, L1, L2, stacked-die/channelized HBM, translation, and host-memory interfaces.",
)


MEMSUB_VARIABLES = (
    MEMSUB_REGFILE_VARIABLES
    + MEMSUB_SMEM_VARIABLES
    + MEMSUB_CACHE_VARIABLES
    + MEMSUB_HBM_VARIABLES
    + MEMSUB_VIRTUAL_VARIABLES
)

MEMSUB_EQUATIONS = (
    MEMSUB_REGFILE_EQUATIONS
    + MEMSUB_SMEM_EQUATIONS
    + MEMSUB_CACHE_EQUATIONS
    + MEMSUB_HBM_EQUATIONS
    + MEMSUB_VIRTUAL_EQUATIONS
)

for v in MEMSUB_VARIABLES:
    sys_mem.add(v)

for e in MEMSUB_EQUATIONS:
    sys_mem.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
