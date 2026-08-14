"""
scopes/memory_sram_common.py
============================

The one Reference and unit constant every SRAM helper shares.

All six SRAM helper modules cite the same bitcell literature, so the
Reference object lives here — defined once, imported everywhere — along
with the DIMENSIONLESS unit tag. Being a leaf module with no scope
imports, it can be pulled in by any helper without creating a cycle.
"""

import sympy as sp

from ..core import Reference


DIMENSIONLESS = sp.Integer(1)

SRAM_CELL_REF = Reference(
    "CMOS memory-cell texts and SRAM bitcell literature describe 6T, 8T, "
    "and 10T cell topology, bitline energy, access delay, leakage, and "
    "read/write margin models.",
    kind="textbook",
)


__all__ = [
    "DIMENSIONLESS",
    "SRAM_CELL_REF",
]
