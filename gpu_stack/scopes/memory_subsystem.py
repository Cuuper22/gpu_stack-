"""
scopes/memory_subsystem.py
==========================

The memory hierarchy on a GPU, from per-thread registers out to HBM and host
attached memory.

The original file had the right nouns and almost none of the machinery that
makes those nouns expensive. This version adds banked bandwidth, cache
organization, translation overhead, host links, unified-memory migration, and
refresh or compression effects that materially change usable bandwidth or
capacity.
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
    description="Register file, SMEM, TMEM, L1, L2, HBM, translation, and host-memory interfaces.",
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
