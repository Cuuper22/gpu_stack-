"""
scopes/memory_sram_margin_equations.py
======================================

The equations that decide whether an SRAM cell reads and writes safely.

Reading an SRAM cell is a controlled disturbance: the access transistor
pulls the internal node up through a conductance divider against the
pull-down, and the read-disturb voltage is that divider's output. The
read static noise margin (SNM) is the inverter trip point minus that
excursion — if the disturbance reaches the trip point, reading flips the
bit. Writing is the opposite fight: the access transistor must drag the
internal node below the trip point against the pull-up, and the write
noise margin (WNM) measures the headroom. The two closing inequalities
demand both margins stay positive; process scaling squeezes exactly these
margins, which is why 8T cells add a separate read port.
"""

from ..core import Inequality, eq
from .memory_sram_common import SRAM_CELL_REF
from .memory_sram_margins import (
    V_read_disturb,
    V_trip_inv,
    V_write_internal,
    g_access,
    g_pulldown,
    g_pullup,
    snm_read,
    wnm_write,
)
from .memory_sram_operating import V_cell_supply


eq_sram_read_disturb = eq(
    "memcell.eq.sram_read_disturb",
    V_read_disturb.symbol,
    V_cell_supply.symbol * g_access.symbol / (g_access.symbol + g_pulldown.symbol),
    "Read disturb modeled as a divider between access and pull-down strength.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram_read_snm = eq(
    "memcell.eq.sram_read_snm",
    snm_read.symbol,
    V_trip_inv.symbol - V_read_disturb.symbol,
    "Read SNM is the inverter trip point minus the read-disturb excursion.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram_write_internal = eq(
    "memcell.eq.sram_write_internal",
    V_write_internal.symbol,
    V_cell_supply.symbol * g_pullup.symbol / (g_access.symbol + g_pullup.symbol),
    "Internal node during write is a divider between access strength and pull-up strength.",
    references=[SRAM_CELL_REF],
    check_units=True,
)

eq_sram_write_wnm = eq(
    "memcell.eq.sram_write_wnm",
    wnm_write.symbol,
    V_trip_inv.symbol - V_write_internal.symbol,
    "Write margin is the gap between inverter trip point and the driven internal node.",
    references=[SRAM_CELL_REF],
    check_units=True,
)
ineq_sram_read_margin = Inequality(
    "memcell.eq.sram_read_margin_constraint",
    snm_read.symbol,
    0,
    ">=",
    "Read SNM must stay non-negative if the cell is to survive a read disturb event.",
    references=[SRAM_CELL_REF],
)
ineq_sram_write_margin = Inequality(
    "memcell.eq.sram_write_margin_constraint",
    wnm_write.symbol,
    0,
    ">=",
    "Write margin must stay non-negative if a write is to flip the cell reliably.",
    references=[SRAM_CELL_REF],
)


MEMCELL_SRAM_MARGIN_EQUATIONS = [
    eq_sram_read_disturb, eq_sram_read_snm,
    eq_sram_write_internal, eq_sram_write_wnm,
    ineq_sram_read_margin, ineq_sram_write_margin,
]

MEMCELL_SRAM_MARGIN_EQUATION_EXPORTS = [
    "eq_sram_read_disturb", "eq_sram_read_snm",
    "eq_sram_write_internal", "eq_sram_write_wnm",
    "ineq_sram_read_margin", "ineq_sram_write_margin",
]


__all__ = [*MEMCELL_SRAM_MARGIN_EQUATION_EXPORTS]
