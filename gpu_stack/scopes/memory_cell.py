"""
scopes/memory_cell.py
=====================

Aggregator for the memory_cell scope: how a single bit is stored.

Every byte in the machine ultimately lives in one of three cell types,
each a different trade of speed, size, and upkeep. SRAM holds a bit in a
cross-coupled latch of six or more transistors — fast and stable but big,
so it fills caches and register files. DRAM holds a bit as charge on a
capacitor behind one transistor — tiny and dense but leaky, so it needs
refresh and fills HBM. A flip-flop is a clocked latch pair — the register
bit inside logic pipelines, with setup/hold timing and metastability risk.

The three cell models live in focused helper modules and are re-exported
here so public imports stay stable. The memory_subsystem scope builds
arrays out of these cells; the physical scope supplies their transistor
parameters.
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
