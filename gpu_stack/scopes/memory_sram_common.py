"""
scopes/memory_sram_common.py
============================

Shared SRAM reference metadata and unit helpers.
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
