"""
scopes/memory_sram.py
=====================

SRAM cell family: 6T, 8T, and 10T variants.

Exposes transistor counts, read-port counts, area estimates, access-time
decomposition, read and write energy, leakage power, read disturb, SNM,
write internal node, WNM, and the two SRAM margin constraint inequalities.
"""

import sympy as sp

from ..core import Inequality, eq, var


# ---------------------------------------------------------------------------
# SRAM cell family: 6T, 8T, 10T
# ---------------------------------------------------------------------------

n_tx_per_sram = var(
    "memcell.sram.transistors", "N_Tx_SRAM", "dimensionless",
    "Transistor count of the selected SRAM cell implementation.",
    scope="memory_cell",
)
a_sram = var(
    "memcell.sram.area", "A_SRAM", "m^2",
    "Physical area of the selected SRAM cell implementation.",
    scope="memory_cell",
)
t_access_sram = var(
    "memcell.sram.access_time", "t_acc_SRAM", "s",
    "Read access latency of the SRAM cell path.",
    scope="memory_cell",
)
p_leak_sram = var(
    "memcell.sram.leakage", "P_leak_SRAM", "W",
    "Per-cell SRAM leakage power.",
    scope="memory_cell",
)
e_read_sram = var(
    "memcell.sram.read_energy", "E_read_SRAM", "J",
    "Energy to read one bit from one SRAM cell.",
    scope="memory_cell",
)
e_write_sram = var(
    "memcell.sram.write_energy", "E_write_SRAM", "J",
    "Energy to write one bit in one SRAM cell.",
    scope="memory_cell",
)
c_bitline = var(
    "memcell.sram.c_bitline", "C_bl_SRAM", "F",
    "Bitline capacitance seen during SRAM access.",
    scope="memory_cell",
)
V_swing = var(
    "memcell.sram.v_swing", "V_sw_SRAM", "V",
    "Bitline voltage swing during SRAM read.",
    scope="memory_cell",
)
V_cell_supply = var(
    "memcell.sram.v_supply", "V_SRAM", "V",
    "SRAM supply voltage.",
    scope="memory_cell",
)
i_leak_sram = var(
    "memcell.sram.i_leak", "I_leak_SRAM", "A",
    "Per-cell SRAM leakage current.",
    scope="memory_cell",
)
r_access_sram = var(
    "memcell.sram.r_access", "R_acc_SRAM", "ohm",
    "Effective access-transistor resistance into the bitline.",
    scope="memory_cell",
)
t_wordline_sram = var(
    "memcell.sram.t_wordline", "t_wl_SRAM", "s",
    "Wordline assertion and decode delay for a cell access.",
    scope="memory_cell",
)
t_sense_sram = var(
    "memcell.sram.t_sense", "t_sense_SRAM", "s",
    "Sense-amplifier decision time for the SRAM read.",
    scope="memory_cell",
)
e_sense_sram = var(
    "memcell.sram.e_sense", "E_sense_SRAM", "J",
    "Energy burned by the SRAM sense path during one access.",
    scope="memory_cell",
)
a_tx_sram = var(
    "memcell.sram.tx_area", "A_tx_SRAM", "m^2",
    "Effective transistor area unit used for SRAM cell area estimates.",
    scope="memory_cell",
)
area_overhead_sram = var(
    "memcell.sram.area_overhead", "k_area_SRAM", "dimensionless",
    "Layout overhead multiplier capturing diffusion sharing and routing overhead.",
    scope="memory_cell",
)

n_tx_sram_6t = var(
    "memcell.sram6t.transistors", "N_Tx_6T", "dimensionless",
    "Transistor count in a canonical 6T SRAM cell.",
    scope="memory_cell",
)
n_tx_sram_8t = var(
    "memcell.sram8t.transistors", "N_Tx_8T", "dimensionless",
    "Transistor count in an 8T SRAM cell.",
    scope="memory_cell",
)
n_tx_sram_10t = var(
    "memcell.sram10t.transistors", "N_Tx_10T", "dimensionless",
    "Transistor count in a 10T SRAM cell.",
    scope="memory_cell",
)
n_read_ports_6t = var(
    "memcell.sram6t.read_ports", "N_r_6T", "dimensionless",
    "Independent read ports in a 6T SRAM cell.",
    scope="memory_cell",
)
n_read_ports_8t = var(
    "memcell.sram8t.read_ports", "N_r_8T", "dimensionless",
    "Independent read ports in an 8T SRAM cell.",
    scope="memory_cell",
)
n_read_ports_10t = var(
    "memcell.sram10t.read_ports", "N_r_10T", "dimensionless",
    "Independent read ports in a 10T SRAM cell.",
    scope="memory_cell",
)
a_sram_6t = var(
    "memcell.sram6t.area", "A_6T", "m^2",
    "Area of a 6T SRAM cell.",
    scope="memory_cell",
)
a_sram_8t = var(
    "memcell.sram8t.area", "A_8T", "m^2",
    "Area of an 8T SRAM cell.",
    scope="memory_cell",
)
a_sram_10t = var(
    "memcell.sram10t.area", "A_10T", "m^2",
    "Area of a 10T SRAM cell.",
    scope="memory_cell",
)

g_access = var(
    "memcell.sram.g_access", "g_acc", "S",
    "Access-transistor conductance during read or write.",
    scope="memory_cell",
)
g_pullup = var(
    "memcell.sram.g_pullup", "g_pu", "S",
    "Pull-up PMOS conductance in the storage inverter.",
    scope="memory_cell",
)
g_pulldown = var(
    "memcell.sram.g_pulldown", "g_pd", "S",
    "Pull-down NMOS conductance in the storage inverter.",
    scope="memory_cell",
)
V_trip_inv = var(
    "memcell.sram.v_trip", "V_trip_SRAM", "V",
    "Inverter trip point of the SRAM cross-coupled pair.",
    scope="memory_cell",
)
V_read_disturb = var(
    "memcell.sram.v_read_disturb", "V_rd_dist", "V",
    "Internal storage-node rise caused by read disturb through the access path.",
    scope="memory_cell",
)
snm_read = var(
    "memcell.sram.snm_read", "SNM_read", "V",
    "Read static-noise margin. Not declared positive because a failed design "
    "can drive this negative, which is exactly the failure mode that the "
    "memcell.eq.sram_read_margin_constraint inequality guards against.",
    scope="memory_cell",
    positive=False,
)
V_write_internal = var(
    "memcell.sram.v_write_internal", "V_wr_int", "V",
    "Internal node voltage during a forced write against the pull-up device.",
    scope="memory_cell",
)
wnm_write = var(
    "memcell.sram.wnm_write", "WNM_write", "V",
    "Write noise margin. Not declared positive because a failed write "
    "design produces a negative margin, which is exactly the failure mode "
    "the memcell.eq.sram_write_margin_constraint inequality guards against.",
    scope="memory_cell",
    positive=False,
)
e_internal_write = var(
    "memcell.sram.e_internal_write", "E_int_write", "J",
    "Additional internal node energy during an SRAM write.",
    scope="memory_cell",
)


eq_sram6t_tx = eq(
    "memcell.eq.sram6t_transistors",
    n_tx_sram_6t.symbol,
    6,
    "6T SRAM uses six transistors per bit cell.",
)

eq_sram8t_tx = eq(
    "memcell.eq.sram8t_transistors",
    n_tx_sram_8t.symbol,
    8,
    "8T SRAM adds a decoupled read path.",
)

eq_sram10t_tx = eq(
    "memcell.eq.sram10t_transistors",
    n_tx_sram_10t.symbol,
    10,
    "10T SRAM spends more devices to buy margin or additional ports.",
)

eq_sram6t_read_ports = eq(
    "memcell.eq.sram6t_read_ports",
    n_read_ports_6t.symbol,
    1,
    "Canonical 6T SRAM has one shared read port.",
)

eq_sram8t_read_ports = eq(
    "memcell.eq.sram8t_read_ports",
    n_read_ports_8t.symbol,
    1,
    "Canonical 8T SRAM still exposes one logical read port, but isolates it from the storage nodes.",
)

eq_sram10t_read_ports = eq(
    "memcell.eq.sram10t_read_ports",
    n_read_ports_10t.symbol,
    2,
    "10T SRAM commonly supports dual-port or at least more strongly isolated access.",
)

eq_sram6t_area = eq(
    "memcell.eq.sram6t_area",
    a_sram_6t.symbol,
    area_overhead_sram.symbol * a_tx_sram.symbol * n_tx_sram_6t.symbol,
    "6T SRAM area from transistor count times effective transistor area and layout overhead.",
)

eq_sram8t_area = eq(
    "memcell.eq.sram8t_area",
    a_sram_8t.symbol,
    area_overhead_sram.symbol * a_tx_sram.symbol * n_tx_sram_8t.symbol,
    "8T SRAM area estimate.",
)

eq_sram10t_area = eq(
    "memcell.eq.sram10t_area",
    a_sram_10t.symbol,
    area_overhead_sram.symbol * a_tx_sram.symbol * n_tx_sram_10t.symbol,
    "10T SRAM area estimate.",
)

eq_sram_access_time = eq(
    "memcell.eq.sram_access_time",
    t_access_sram.symbol,
    t_wordline_sram.symbol + r_access_sram.symbol * c_bitline.symbol + t_sense_sram.symbol,
    "SRAM access time as wordline delay plus bitline RC plus sense time.",
)

eq_sram_read_energy = eq(
    "memcell.eq.sram_read_energy",
    e_read_sram.symbol,
    sp.Rational(1, 2) * c_bitline.symbol * V_swing.symbol**2 + e_sense_sram.symbol,
    "SRAM read energy dominated by bitline swing plus sense energy.",
)

eq_sram_write_energy = eq(
    "memcell.eq.sram_write_energy",
    e_write_sram.symbol,
    sp.Rational(1, 2) * c_bitline.symbol * V_cell_supply.symbol**2 + e_internal_write.symbol,
    "SRAM write energy from charging the line and forcing the internal node.",
)

eq_sram_leakage_power = eq(
    "memcell.eq.sram_leakage_power",
    p_leak_sram.symbol,
    i_leak_sram.symbol * V_cell_supply.symbol,
    "Per-cell SRAM leakage power is leakage current times supply.",
)

eq_sram_read_disturb = eq(
    "memcell.eq.sram_read_disturb",
    V_read_disturb.symbol,
    V_cell_supply.symbol * g_access.symbol / (g_access.symbol + g_pulldown.symbol),
    "Read disturb modeled as a divider between access and pull-down strength.",
)

eq_sram_read_snm = eq(
    "memcell.eq.sram_read_snm",
    snm_read.symbol,
    V_trip_inv.symbol - V_read_disturb.symbol,
    "Read SNM is the inverter trip point minus the read-disturb excursion.",
)

eq_sram_write_internal = eq(
    "memcell.eq.sram_write_internal",
    V_write_internal.symbol,
    V_cell_supply.symbol * g_pullup.symbol / (g_access.symbol + g_pullup.symbol),
    "Internal node during write is a divider between access strength and pull-up strength.",
)

eq_sram_write_wnm = eq(
    "memcell.eq.sram_write_wnm",
    wnm_write.symbol,
    V_trip_inv.symbol - V_write_internal.symbol,
    "Write margin is the gap between inverter trip point and the driven internal node.",
)
ineq_sram_read_margin = Inequality(
    "memcell.eq.sram_read_margin_constraint",
    snm_read.symbol,
    0,
    ">=",
    "Read SNM must stay non-negative if the cell is to survive a read disturb event.",
)
ineq_sram_write_margin = Inequality(
    "memcell.eq.sram_write_margin_constraint",
    wnm_write.symbol,
    0,
    ">=",
    "Write margin must stay non-negative if a write is to flip the cell reliably.",
)


MEMCELL_SRAM_VARIABLES = [
    n_tx_per_sram, a_sram, t_access_sram, p_leak_sram, e_read_sram, e_write_sram,
    c_bitline, V_swing, V_cell_supply, i_leak_sram, r_access_sram,
    t_wordline_sram, t_sense_sram, e_sense_sram, a_tx_sram, area_overhead_sram,
    n_tx_sram_6t, n_tx_sram_8t, n_tx_sram_10t,
    n_read_ports_6t, n_read_ports_8t, n_read_ports_10t,
    a_sram_6t, a_sram_8t, a_sram_10t,
    g_access, g_pullup, g_pulldown, V_trip_inv, V_read_disturb, snm_read,
    V_write_internal, wnm_write, e_internal_write,
]

MEMCELL_SRAM_EQUATIONS = [
    eq_sram6t_tx, eq_sram8t_tx, eq_sram10t_tx,
    eq_sram6t_read_ports, eq_sram8t_read_ports, eq_sram10t_read_ports,
    eq_sram6t_area, eq_sram8t_area, eq_sram10t_area,
    eq_sram_access_time, eq_sram_read_energy, eq_sram_write_energy,
    eq_sram_leakage_power, eq_sram_read_disturb, eq_sram_read_snm,
    eq_sram_write_internal, eq_sram_write_wnm,
    ineq_sram_read_margin, ineq_sram_write_margin,
]


__all__ = [
    "n_tx_per_sram", "a_sram", "t_access_sram", "p_leak_sram",
    "e_read_sram", "e_write_sram", "c_bitline", "V_swing", "V_cell_supply",
    "i_leak_sram", "r_access_sram", "t_wordline_sram", "t_sense_sram",
    "e_sense_sram", "a_tx_sram", "area_overhead_sram",
    "n_tx_sram_6t", "n_tx_sram_8t", "n_tx_sram_10t",
    "n_read_ports_6t", "n_read_ports_8t", "n_read_ports_10t",
    "a_sram_6t", "a_sram_8t", "a_sram_10t",
    "g_access", "g_pullup", "g_pulldown", "V_trip_inv", "V_read_disturb",
    "snm_read", "V_write_internal", "wnm_write", "e_internal_write",
    "eq_sram6t_tx", "eq_sram8t_tx", "eq_sram10t_tx",
    "eq_sram6t_read_ports", "eq_sram8t_read_ports", "eq_sram10t_read_ports",
    "eq_sram6t_area", "eq_sram8t_area", "eq_sram10t_area",
    "eq_sram_access_time", "eq_sram_read_energy", "eq_sram_write_energy",
    "eq_sram_leakage_power", "eq_sram_read_disturb", "eq_sram_read_snm",
    "eq_sram_write_internal", "eq_sram_write_wnm",
    "ineq_sram_read_margin", "ineq_sram_write_margin",
    "MEMCELL_SRAM_VARIABLES", "MEMCELL_SRAM_EQUATIONS",
]
