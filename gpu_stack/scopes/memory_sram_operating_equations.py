"""
scopes/memory_sram_operating_equations.py
=========================================

SRAM access, read/write energy, and leakage equations.
"""

import sympy as sp

from ..core import eq
from .memory_sram_common import SRAM_CELL_REF
from .memory_sram_margins import e_internal_write
from .memory_sram_operating import (
    V_cell_supply,
    V_swing,
    c_bitline,
    e_read_sram,
    e_sense_sram,
    e_write_sram,
    i_leak_sram,
    p_leak_sram,
    r_access_sram,
    t_access_sram,
    t_sense_sram,
    t_wordline_sram,
)


eq_sram_access_time = eq(
    "memcell.eq.sram_access_time",
    t_access_sram.symbol,
    t_wordline_sram.symbol + r_access_sram.symbol * c_bitline.symbol + t_sense_sram.symbol,
    "SRAM access time as wordline delay plus bitline RC plus sense time.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram_read_energy = eq(
    "memcell.eq.sram_read_energy",
    e_read_sram.symbol,
    sp.Rational(1, 2) * c_bitline.symbol * V_swing.symbol**2 + e_sense_sram.symbol,
    "SRAM read energy dominated by bitline swing plus sense energy.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram_write_energy = eq(
    "memcell.eq.sram_write_energy",
    e_write_sram.symbol,
    sp.Rational(1, 2) * c_bitline.symbol * V_cell_supply.symbol**2 + e_internal_write.symbol,
    "SRAM write energy from charging the line and forcing the internal node.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram_leakage_power = eq(
    "memcell.eq.sram_leakage_power",
    p_leak_sram.symbol,
    i_leak_sram.symbol * V_cell_supply.symbol,
    "Per-cell SRAM leakage power is leakage current times supply.",
    references=[SRAM_CELL_REF],
    check_units=True,
)


MEMCELL_SRAM_OPERATING_EQUATIONS = [
    eq_sram_access_time, eq_sram_read_energy, eq_sram_write_energy,
    eq_sram_leakage_power,
]

MEMCELL_SRAM_OPERATING_EQUATION_EXPORTS = [
    "eq_sram_access_time", "eq_sram_read_energy", "eq_sram_write_energy",
    "eq_sram_leakage_power",
]


__all__ = [*MEMCELL_SRAM_OPERATING_EQUATION_EXPORTS]
