"""
scopes/memory_sram_margins.py
=============================

The variables behind SRAM stability: transistor strengths and margins.

An SRAM cell's stability is a tug-of-war between three transistor
conductances — access, pull-up, and pull-down — and these declarations
name the contestants and the scores. The derived quantities are the
inverter trip point, the read-disturb excursion, the read static noise
margin, the internal node voltage during a write, the write noise margin,
and the internal write energy. Only the variables live here; the divider
and margin equations that relate them are in
memory_sram_margin_equations.
"""

from ..core import var
from ..core.units import JOULE, OHM, VOLT
from .memory_sram_common import SRAM_CELL_REF


g_access = var(
    "memcell.sram.g_access", "g_acc", "S",
    "Access-transistor conductance during read or write.",
    scope="memory_cell",
    sp_units=1 / OHM,
    references=[SRAM_CELL_REF],
)
g_pullup = var(
    "memcell.sram.g_pullup", "g_pu", "S",
    "Pull-up PMOS conductance in the storage inverter.",
    scope="memory_cell",
    sp_units=1 / OHM,
    references=[SRAM_CELL_REF],
)
g_pulldown = var(
    "memcell.sram.g_pulldown", "g_pd", "S",
    "Pull-down NMOS conductance in the storage inverter.",
    scope="memory_cell",
    sp_units=1 / OHM,
    references=[SRAM_CELL_REF],
)
V_trip_inv = var(
    "memcell.sram.v_trip", "V_trip_SRAM", "V",
    "Inverter trip point of the SRAM cross-coupled pair.",
    scope="memory_cell",
    sp_units=VOLT,
    references=[SRAM_CELL_REF],
)
V_read_disturb = var(
    "memcell.sram.v_read_disturb", "V_rd_dist", "V",
    "Internal storage-node rise caused by read disturb through the access path.",
    scope="memory_cell",
    sp_units=VOLT,
    references=[SRAM_CELL_REF],
)
snm_read = var(
    "memcell.sram.snm_read", "SNM_read", "V",
    "Read static-noise margin. Not declared positive because a failed design "
    "can drive this negative, which is exactly the failure mode that the "
    "memcell.eq.sram_read_margin_constraint inequality guards against.",
    scope="memory_cell",
    positive=False,
    sp_units=VOLT,
    references=[SRAM_CELL_REF],
)
V_write_internal = var(
    "memcell.sram.v_write_internal", "V_wr_int", "V",
    "Internal node voltage during a forced write against the pull-up device.",
    scope="memory_cell",
    sp_units=VOLT,
    references=[SRAM_CELL_REF],
)
wnm_write = var(
    "memcell.sram.wnm_write", "WNM_write", "V",
    "Write noise margin. Not declared positive because a failed write "
    "design produces a negative margin, which is exactly the failure mode "
    "the memcell.eq.sram_write_margin_constraint inequality guards against.",
    scope="memory_cell",
    positive=False,
    sp_units=VOLT,
    references=[SRAM_CELL_REF],
)
e_internal_write = var(
    "memcell.sram.e_internal_write", "E_int_write", "J",
    "Additional internal node energy during an SRAM write.",
    scope="memory_cell",
    sp_units=JOULE,
    references=[SRAM_CELL_REF],
)


MEMCELL_SRAM_MARGIN_VARIABLES = [
    g_access, g_pullup, g_pulldown, V_trip_inv, V_read_disturb, snm_read,
    V_write_internal, wnm_write, e_internal_write,
]

MEMCELL_SRAM_MARGIN_EXPORTS = [
    "g_access", "g_pullup", "g_pulldown", "V_trip_inv", "V_read_disturb",
    "snm_read", "V_write_internal", "wnm_write", "e_internal_write",
]


__all__ = [*MEMCELL_SRAM_MARGIN_EXPORTS]
