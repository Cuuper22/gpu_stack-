"""
scopes/memory_sram_variant_equations.py
=======================================

Topology and area equations for SRAM 6T, 8T, and 10T variants.
"""

from ..core import eq
from .memory_sram_common import SRAM_CELL_REF
from .memory_sram_operating import a_tx_sram, area_overhead_sram
from .memory_sram_variants import (
    a_sram_6t,
    a_sram_8t,
    a_sram_10t,
    n_read_ports_6t,
    n_read_ports_8t,
    n_read_ports_10t,
    n_tx_sram_6t,
    n_tx_sram_8t,
    n_tx_sram_10t,
)


eq_sram6t_tx = eq(
    "memcell.eq.sram6t_transistors",
    n_tx_sram_6t.symbol,
    6,
    "6T SRAM uses six transistors per bit cell.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram8t_tx = eq(
    "memcell.eq.sram8t_transistors",
    n_tx_sram_8t.symbol,
    8,
    "8T SRAM adds a decoupled read path.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram10t_tx = eq(
    "memcell.eq.sram10t_transistors",
    n_tx_sram_10t.symbol,
    10,
    "10T SRAM spends more devices to buy margin or additional ports.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram6t_read_ports = eq(
    "memcell.eq.sram6t_read_ports",
    n_read_ports_6t.symbol,
    1,
    "Canonical 6T SRAM has one shared read port.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram8t_read_ports = eq(
    "memcell.eq.sram8t_read_ports",
    n_read_ports_8t.symbol,
    1,
    "Canonical 8T SRAM still exposes one logical read port, but isolates it from the storage nodes.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram10t_read_ports = eq(
    "memcell.eq.sram10t_read_ports",
    n_read_ports_10t.symbol,
    2,
    "10T SRAM commonly supports dual-port or at least more strongly isolated access.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram6t_area = eq(
    "memcell.eq.sram6t_area",
    a_sram_6t.symbol,
    area_overhead_sram.symbol * a_tx_sram.symbol * n_tx_sram_6t.symbol,
    "6T SRAM area from transistor count times effective transistor area and layout overhead.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram8t_area = eq(
    "memcell.eq.sram8t_area",
    a_sram_8t.symbol,
    area_overhead_sram.symbol * a_tx_sram.symbol * n_tx_sram_8t.symbol,
    "8T SRAM area estimate.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram10t_area = eq(
    "memcell.eq.sram10t_area",
    a_sram_10t.symbol,
    area_overhead_sram.symbol * a_tx_sram.symbol * n_tx_sram_10t.symbol,
    "10T SRAM area estimate.",
    references=[SRAM_CELL_REF],
    check_units=True,
)


MEMCELL_SRAM_VARIANT_EQUATIONS = [
    eq_sram6t_tx, eq_sram8t_tx, eq_sram10t_tx,
    eq_sram6t_read_ports, eq_sram8t_read_ports, eq_sram10t_read_ports,
    eq_sram6t_area, eq_sram8t_area, eq_sram10t_area,
]

MEMCELL_SRAM_VARIANT_EQUATION_EXPORTS = [
    "eq_sram6t_tx", "eq_sram8t_tx", "eq_sram10t_tx",
    "eq_sram6t_read_ports", "eq_sram8t_read_ports", "eq_sram10t_read_ports",
    "eq_sram6t_area", "eq_sram8t_area", "eq_sram10t_area",
]


__all__ = [*MEMCELL_SRAM_VARIANT_EQUATION_EXPORTS]
