"""
scopes/memory_sram_operating.py
===============================

Selected SRAM cell operating variables.
"""

from ..core import var
from ..core.units import AMPERE, FARAD, JOULE, METER, OHM, SECOND, VOLT, WATT
from .memory_sram_common import DIMENSIONLESS, SRAM_CELL_REF


n_tx_per_sram = var(
    "memcell.sram.transistors", "N_Tx_SRAM", "dimensionless",
    "Transistor count of the selected SRAM cell implementation.",
    scope="memory_cell",
    sp_units=DIMENSIONLESS,
    references=[SRAM_CELL_REF],
)
a_sram = var(
    "memcell.sram.area", "A_SRAM", "m^2",
    "Physical area of the selected SRAM cell implementation.",
    scope="memory_cell",
    sp_units=METER**2,
    references=[SRAM_CELL_REF],
)
t_access_sram = var(
    "memcell.sram.access_time", "t_acc_SRAM", "s",
    "Read access latency of the SRAM cell path.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[SRAM_CELL_REF],
)
p_leak_sram = var(
    "memcell.sram.leakage", "P_leak_SRAM", "W",
    "Per-cell SRAM leakage power.",
    scope="memory_cell",
    sp_units=WATT,
    references=[SRAM_CELL_REF],
)
e_read_sram = var(
    "memcell.sram.read_energy", "E_read_SRAM", "J",
    "Energy to read one bit from one SRAM cell.",
    scope="memory_cell",
    sp_units=JOULE,
    references=[SRAM_CELL_REF],
)
e_write_sram = var(
    "memcell.sram.write_energy", "E_write_SRAM", "J",
    "Energy to write one bit in one SRAM cell.",
    scope="memory_cell",
    sp_units=JOULE,
    references=[SRAM_CELL_REF],
)
c_bitline = var(
    "memcell.sram.c_bitline", "C_bl_SRAM", "F",
    "Bitline capacitance seen during SRAM access.",
    scope="memory_cell",
    sp_units=FARAD,
    references=[SRAM_CELL_REF],
)
V_swing = var(
    "memcell.sram.v_swing", "V_sw_SRAM", "V",
    "Bitline voltage swing during SRAM read.",
    scope="memory_cell",
    sp_units=VOLT,
    references=[SRAM_CELL_REF],
)
V_cell_supply = var(
    "memcell.sram.v_supply", "V_SRAM", "V",
    "SRAM supply voltage.",
    scope="memory_cell",
    sp_units=VOLT,
    references=[SRAM_CELL_REF],
)
i_leak_sram = var(
    "memcell.sram.i_leak", "I_leak_SRAM", "A",
    "Per-cell SRAM leakage current.",
    scope="memory_cell",
    sp_units=AMPERE,
    references=[SRAM_CELL_REF],
)
r_access_sram = var(
    "memcell.sram.r_access", "R_acc_SRAM", "ohm",
    "Effective access-transistor resistance into the bitline.",
    scope="memory_cell",
    sp_units=OHM,
    references=[SRAM_CELL_REF],
)
t_wordline_sram = var(
    "memcell.sram.t_wordline", "t_wl_SRAM", "s",
    "Wordline assertion and decode delay for a cell access.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[SRAM_CELL_REF],
)
t_sense_sram = var(
    "memcell.sram.t_sense", "t_sense_SRAM", "s",
    "Sense-amplifier decision time for the SRAM read.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[SRAM_CELL_REF],
)
e_sense_sram = var(
    "memcell.sram.e_sense", "E_sense_SRAM", "J",
    "Energy burned by the SRAM sense path during one access.",
    scope="memory_cell",
    sp_units=JOULE,
    references=[SRAM_CELL_REF],
)
a_tx_sram = var(
    "memcell.sram.tx_area", "A_tx_SRAM", "m^2",
    "Effective transistor area unit used for SRAM cell area estimates.",
    scope="memory_cell",
    sp_units=METER**2,
    references=[SRAM_CELL_REF],
)
area_overhead_sram = var(
    "memcell.sram.area_overhead", "k_area_SRAM", "dimensionless",
    "Layout overhead multiplier capturing diffusion sharing and routing overhead.",
    scope="memory_cell",
    sp_units=DIMENSIONLESS,
    references=[SRAM_CELL_REF],
)


MEMCELL_SRAM_OPERATING_VARIABLES = [
    n_tx_per_sram, a_sram, t_access_sram, p_leak_sram, e_read_sram, e_write_sram,
    c_bitline, V_swing, V_cell_supply, i_leak_sram, r_access_sram,
    t_wordline_sram, t_sense_sram, e_sense_sram, a_tx_sram, area_overhead_sram,
]

MEMCELL_SRAM_OPERATING_EXPORTS = [
    "n_tx_per_sram", "a_sram", "t_access_sram", "p_leak_sram",
    "e_read_sram", "e_write_sram", "c_bitline", "V_swing", "V_cell_supply",
    "i_leak_sram", "r_access_sram", "t_wordline_sram", "t_sense_sram",
    "e_sense_sram", "a_tx_sram", "area_overhead_sram",
]


__all__ = [*MEMCELL_SRAM_OPERATING_EXPORTS]
