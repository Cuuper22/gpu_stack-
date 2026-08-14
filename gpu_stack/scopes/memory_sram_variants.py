"""
scopes/memory_sram_variants.py
==============================

Variables naming the three SRAM bitcell topologies side by side.

For each of the 6T, 8T, and 10T cells this module declares the same
triple — transistor count, read-port count, and area — so the variants
can be compared and one selected as the operating cell. The values are
fixed by topology, not tuned; the equations assigning them live in
memory_sram_variant_equations.
"""

from ..core import var
from ..core.units import METER
from .memory_sram_common import DIMENSIONLESS, SRAM_CELL_REF


n_tx_sram_6t = var(
    "memcell.sram6t.transistors", "N_Tx_6T", "dimensionless",
    "Transistor count in a canonical 6T SRAM cell.",
    scope="memory_cell",
    sp_units=DIMENSIONLESS,
    references=[SRAM_CELL_REF],
)
n_tx_sram_8t = var(
    "memcell.sram8t.transistors", "N_Tx_8T", "dimensionless",
    "Transistor count in an 8T SRAM cell.",
    scope="memory_cell",
    sp_units=DIMENSIONLESS,
    references=[SRAM_CELL_REF],
)
n_tx_sram_10t = var(
    "memcell.sram10t.transistors", "N_Tx_10T", "dimensionless",
    "Transistor count in a 10T SRAM cell.",
    scope="memory_cell",
    sp_units=DIMENSIONLESS,
    references=[SRAM_CELL_REF],
)
n_read_ports_6t = var(
    "memcell.sram6t.read_ports", "N_r_6T", "dimensionless",
    "Independent read ports in a 6T SRAM cell.",
    scope="memory_cell",
    sp_units=DIMENSIONLESS,
    references=[SRAM_CELL_REF],
)
n_read_ports_8t = var(
    "memcell.sram8t.read_ports", "N_r_8T", "dimensionless",
    "Independent read ports in an 8T SRAM cell.",
    scope="memory_cell",
    sp_units=DIMENSIONLESS,
    references=[SRAM_CELL_REF],
)
n_read_ports_10t = var(
    "memcell.sram10t.read_ports", "N_r_10T", "dimensionless",
    "Independent read ports in a 10T SRAM cell.",
    scope="memory_cell",
    sp_units=DIMENSIONLESS,
    references=[SRAM_CELL_REF],
)
a_sram_6t = var(
    "memcell.sram6t.area", "A_6T", "m^2",
    "Area of a 6T SRAM cell.",
    scope="memory_cell",
    sp_units=METER**2,
    references=[SRAM_CELL_REF],
)
a_sram_8t = var(
    "memcell.sram8t.area", "A_8T", "m^2",
    "Area of an 8T SRAM cell.",
    scope="memory_cell",
    sp_units=METER**2,
    references=[SRAM_CELL_REF],
)
a_sram_10t = var(
    "memcell.sram10t.area", "A_10T", "m^2",
    "Area of a 10T SRAM cell.",
    scope="memory_cell",
    sp_units=METER**2,
    references=[SRAM_CELL_REF],
)


MEMCELL_SRAM_VARIANT_VARIABLES = [
    n_tx_sram_6t, n_tx_sram_8t, n_tx_sram_10t,
    n_read_ports_6t, n_read_ports_8t, n_read_ports_10t,
    a_sram_6t, a_sram_8t, a_sram_10t,
]

MEMCELL_SRAM_VARIANT_EXPORTS = [
    "n_tx_sram_6t", "n_tx_sram_8t", "n_tx_sram_10t",
    "n_read_ports_6t", "n_read_ports_8t", "n_read_ports_10t",
    "a_sram_6t", "a_sram_8t", "a_sram_10t",
]


__all__ = [*MEMCELL_SRAM_VARIANT_EXPORTS]
