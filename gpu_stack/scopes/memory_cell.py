"""
scopes/memory_cell.py
=====================

Aggregator for the memory_cell scope.

The original memory_cell file carried SRAM variants, DRAM cells, and
flip-flops in one slab. It has been split into focused helpers and
re-exported here so public imports stay stable.
"""

from ..core import System

from .memory_sram import *
from .memory_sram import MEMCELL_SRAM_EQUATIONS, MEMCELL_SRAM_VARIABLES
from .memory_dram import *
from .memory_dram import MEMCELL_DRAM_EQUATIONS, MEMCELL_DRAM_VARIABLES
from .memory_flipflop import *
from .memory_flipflop import MEMCELL_FF_EQUATIONS, MEMCELL_FF_VARIABLES


sys_memcell = System(
    name="memory_cell",
    scope="memory_cell",
    description="Single-bit storage cells: SRAM variants, DRAM cells, and flip-flops.",
)


MEMCELL_VARIABLES = (
    MEMCELL_SRAM_VARIABLES
    + MEMCELL_DRAM_VARIABLES
    + MEMCELL_FF_VARIABLES
)

MEMCELL_EQUATIONS = (
    MEMCELL_SRAM_EQUATIONS
    + MEMCELL_DRAM_EQUATIONS
    + MEMCELL_FF_EQUATIONS
)

for v in MEMCELL_VARIABLES:
    sys_memcell.add(v)

for e in MEMCELL_EQUATIONS:
    sys_memcell.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
