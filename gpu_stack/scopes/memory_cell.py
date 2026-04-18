"""
scopes/memory_cell.py
=====================

Individual memory cells: SRAM, DRAM, and flip-flops.

This scope sits one level above raw transistor physics and one level below the
memory hierarchies that consume these cells in bulk. The goal is not to hide
cell behavior behind a single access-time number. The goal is to expose the
variables that actually make memory design ugly.
"""

import sympy as sp

from ..core import Inequality, StochasticRelation, System, var, eq


sys_memcell = System(
    name="memory_cell",
    scope="memory_cell",
    description="Single-bit storage cells: SRAM variants, DRAM cells, and flip-flops.",
)


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


# ---------------------------------------------------------------------------
# DRAM cell and sense path
# ---------------------------------------------------------------------------

c_dram = var(
    "memcell.dram.capacitance", "C_DRAM", "F",
    "Storage capacitance of one DRAM cell.",
    scope="memory_cell",
)
q_dram = var(
    "memcell.dram.stored_charge", "Q_DRAM", "C",
    "Stored charge representing the logical state.",
    scope="memory_cell",
)
V_dram = var(
    "memcell.dram.v_cell", "V_DRAM", "V",
    "Cell voltage prior to charge sharing.",
    scope="memory_cell",
)
t_refresh = var(
    "memcell.dram.refresh_period", "t_refresh", "s",
    "Refresh period.",
    scope="memory_cell",
)
i_leak_dram = var(
    "memcell.dram.i_leak", "I_leak_DRAM", "A",
    "Leakage current draining the DRAM storage capacitor.",
    scope="memory_cell",
)
c_bitline_dram = var(
    "memcell.dram.c_bitline", "C_bl_DRAM", "F",
    "Bitline capacitance participating in DRAM charge sharing.",
    scope="memory_cell",
)
V_dev_dram = var(
    "memcell.dram.v_dev", "V_dev_DRAM", "V",
    "Differential voltage developed by charge sharing at the sense input.",
    scope="memory_cell",
)
V_offset_sa = var(
    "memcell.dram.v_offset_sa", "V_os_SA", "V",
    "Input offset voltage of the DRAM sense amplifier.",
    scope="memory_cell",
)
V_input_sa = var(
    "memcell.dram.v_input_sa", "V_in_SA", "V",
    "Effective differential input seen by the sense amplifier after offset loss.",
    scope="memory_cell",
)
A_sa = var(
    "memcell.dram.sense_gain", "A_SA", "dimensionless",
    "Small-signal gain of the sense amplifier.",
    scope="memory_cell",
)
V_sense_out = var(
    "memcell.dram.v_sense_out", "V_out_SA", "V",
    "Sense-amplifier output excursion.",
    scope="memory_cell",
)
tau_sa = var(
    "memcell.dram.sense_tau", "tau_SA", "s",
    "Regenerative time constant of the sense amplifier.",
    scope="memory_cell",
)
V_logic_target = var(
    "memcell.dram.v_logic_target", "V_logic_SA", "V",
    "Output swing target treated as a completed sense decision.",
    scope="memory_cell",
)
t_resolve_sa = var(
    "memcell.dram.t_resolve_sa", "t_res_SA", "s",
    "Time required for the sense amplifier to resolve the shared charge.",
    scope="memory_cell",
)
mu_log_ret = var(
    "memcell.dram.retention_log_mu", "mu_ret", "dimensionless",
    "Mean of log-retention-time across cells.",
    scope="memory_cell",
)
sigma_log_ret = var(
    "memcell.dram.retention_log_sigma", "sigma_ret", "dimensionless",
    "Standard deviation of log-retention-time across cells.",
    scope="memory_cell",
)
t_retention_median = var(
    "memcell.dram.retention_median", "t_ret_med", "s",
    "Median DRAM retention time across cells.",
    scope="memory_cell",
)
t_retention_mean = var(
    "memcell.dram.retention_mean", "t_ret_mean", "s",
    "Mean DRAM retention time across cells.",
    scope="memory_cell",
)
z_retention_guard = var(
    "memcell.dram.retention_guard_sigma", "z_ret", "dimensionless",
    "Lower-tail sigma multiple used to choose a refresh guardband.",
    scope="memory_cell",
)
t_retention_guardband = var(
    "memcell.dram.retention_guardband", "t_ret_guard", "s",
    "Lower-tail retention target used for safe refresh policy.",
    scope="memory_cell",
)
t_retention_cell = var(
    "memcell.dram.retention_cell", "t_ret_cell", "s",
    "Retention time of a particular DRAM cell drawn from the array-wide distribution.",
    scope="memory_cell",
)


eq_dram_charge = eq(
    "memcell.eq.dram_charge",
    q_dram.symbol,
    c_dram.symbol * V_dram.symbol,
    "Stored DRAM charge Q = C V.",
)

eq_dram_refresh = eq(
    "memcell.eq.dram_refresh_period",
    t_refresh.symbol,
    q_dram.symbol / i_leak_dram.symbol,
    "Approximate refresh period from stored charge divided by leakage current.",
)

eq_dram_charge_sharing = eq(
    "memcell.eq.dram_charge_sharing",
    V_dev_dram.symbol,
    V_dram.symbol * c_dram.symbol / (c_dram.symbol + c_bitline_dram.symbol),
    "DRAM charge-sharing signal at the sense node.",
)

eq_dram_sense_input = eq(
    "memcell.eq.dram_sense_input",
    V_input_sa.symbol,
    V_dev_dram.symbol - V_offset_sa.symbol,
    "Effective sense input after subtracting offset voltage.",
)

eq_dram_sense_output = eq(
    "memcell.eq.dram_sense_output",
    V_sense_out.symbol,
    A_sa.symbol * V_input_sa.symbol,
    "Sense-amplifier output from gain times effective differential input.",
)

eq_dram_sense_resolve = eq(
    "memcell.eq.dram_sense_resolve",
    t_resolve_sa.symbol,
    tau_sa.symbol * sp.log(V_logic_target.symbol / V_input_sa.symbol),
    "Regenerative sense-amplifier resolve time.",
)
ineq_dram_sense_margin = Inequality(
    "memcell.eq.dram_sense_margin_constraint",
    V_dev_dram.symbol,
    V_offset_sa.symbol,
    ">=",
    "Charge-sharing differential must exceed sense-amplifier offset to be reliably detectable.",
)

eq_dram_retention_median = eq(
    "memcell.eq.dram_retention_median",
    t_retention_median.symbol,
    sp.exp(mu_log_ret.symbol),
    "Median of the log-normal retention-time distribution.",
)

eq_dram_retention_mean = eq(
    "memcell.eq.dram_retention_mean",
    t_retention_mean.symbol,
    sp.exp(mu_log_ret.symbol + sigma_log_ret.symbol**2 / 2),
    "Mean of the log-normal retention-time distribution.",
)

eq_dram_retention_guardband = eq(
    "memcell.eq.dram_retention_guardband",
    t_retention_guardband.symbol,
    sp.exp(mu_log_ret.symbol - z_retention_guard.symbol * sigma_log_ret.symbol),
    "Lower-tail guardband for refresh scheduling under a log-normal retention model.",
)
retention_distribution = StochasticRelation(
    "memcell.eq.dram_retention_distribution",
    t_retention_cell.symbol,
    distribution="LogNormal",
    parameters={"mu": mu_log_ret.symbol, "sigma": sigma_log_ret.symbol},
    mean=t_retention_mean.symbol,
    variance=(sp.exp(sigma_log_ret.symbol**2) - 1)
             * sp.exp(2 * mu_log_ret.symbol + sigma_log_ret.symbol**2),
    description="Cell-to-cell DRAM retention-time distribution modeled as log-normal.",
)
ineq_dram_refresh_guard = Inequality(
    "memcell.eq.dram_refresh_guard_constraint",
    t_refresh.symbol,
    t_retention_guardband.symbol,
    "<=",
    "Refresh period must stay below the chosen lower-tail retention guardband.",
)


# ---------------------------------------------------------------------------
# Register bit (flip-flop) and metastability
# ---------------------------------------------------------------------------

n_tx_per_ff = var(
    "memcell.ff.transistors", "N_Tx_FF", "dimensionless",
    "Transistors per flip-flop implementation.",
    scope="memory_cell",
)
t_setup = var(
    "memcell.ff.t_setup", "t_setup", "s",
    "Setup time.",
    scope="memory_cell",
)
t_hold = var(
    "memcell.ff.t_hold", "t_hold", "s",
    "Hold time.",
    scope="memory_cell",
)
t_clk_to_q = var(
    "memcell.ff.t_clk_to_q", "t_cq", "s",
    "Clock-to-Q propagation delay.",
    scope="memory_cell",
)
t_setup_intrinsic = var(
    "memcell.ff.t_setup_intrinsic", "t_setup_int", "s",
    "Intrinsic setup requirement of the input latch path.",
    scope="memory_cell",
)
t_hold_intrinsic = var(
    "memcell.ff.t_hold_intrinsic", "t_hold_int", "s",
    "Intrinsic hold requirement of the feedback path.",
    scope="memory_cell",
)
t_aperture = var(
    "memcell.ff.t_aperture", "t_ap", "s",
    "Sampling aperture contribution around the active clock edge.",
    scope="memory_cell",
)
t_latch_regen = var(
    "memcell.ff.t_latch_regen", "t_regen_FF", "s",
    "Regeneration delay of the latch pair.",
    scope="memory_cell",
)
t_output_buffer = var(
    "memcell.ff.t_output_buffer", "t_buf_FF", "s",
    "Output buffer delay after the internal latch resolves.",
    scope="memory_cell",
)
f_clk_ff = var(
    "memcell.ff.f_clk", "f_clk_FF", "Hz",
    "Clock frequency applied to the flip-flop.",
    scope="memory_cell",
)
f_data_ff = var(
    "memcell.ff.f_data", "f_data_FF", "Hz",
    "Relevant asynchronous or data-toggle event rate.",
    scope="memory_cell",
)
T0_meta = var(
    "memcell.ff.t0_meta", "T0_meta", "s",
    "Metastability fitting constant in the standard MTBF model.",
    scope="memory_cell",
)
tau_meta = var(
    "memcell.ff.tau_meta", "tau_meta", "s",
    "Metastability resolution time constant.",
    scope="memory_cell",
)
t_resolve_meta = var(
    "memcell.ff.t_resolve_meta", "t_res_meta", "s",
    "Time available for metastability to resolve before the next observer samples the node.",
    scope="memory_cell",
)
r_meta_fail = var(
    "memcell.ff.meta_fail_rate", "r_meta", "1/s",
    "Metastability failure rate.",
    scope="memory_cell",
)
mtbf_meta = var(
    "memcell.ff.mtbf_meta", "MTBF_meta", "s",
    "Mean time between metastability failures.",
    scope="memory_cell",
)


eq_ff_setup = eq(
    "memcell.eq.ff_setup",
    t_setup.symbol,
    t_setup_intrinsic.symbol + t_aperture.symbol,
    "Setup time from intrinsic input path plus aperture requirement.",
)

eq_ff_hold = eq(
    "memcell.eq.ff_hold",
    t_hold.symbol,
    t_hold_intrinsic.symbol + t_aperture.symbol,
    "Hold time from intrinsic feedback settling plus aperture requirement.",
)

eq_ff_clk_to_q = eq(
    "memcell.eq.ff_clk_to_q",
    t_clk_to_q.symbol,
    t_latch_regen.symbol + t_output_buffer.symbol,
    "Clock-to-Q delay from latch regeneration plus output buffering.",
)

eq_ff_meta_fail_rate = eq(
    "memcell.eq.ff_meta_fail_rate",
    r_meta_fail.symbol,
    f_clk_ff.symbol * f_data_ff.symbol * T0_meta.symbol * sp.exp(-t_resolve_meta.symbol / tau_meta.symbol),
    "Standard metastability failure-rate model.",
)

eq_ff_mtbf = eq(
    "memcell.eq.ff_mtbf",
    mtbf_meta.symbol,
    1 / r_meta_fail.symbol,
    "MTBF is the reciprocal of the metastability failure rate.",
)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

for v in [
    n_tx_per_sram, a_sram, t_access_sram, p_leak_sram, e_read_sram, e_write_sram,
    c_bitline, V_swing, V_cell_supply, i_leak_sram, r_access_sram,
    t_wordline_sram, t_sense_sram, e_sense_sram, a_tx_sram, area_overhead_sram,
    n_tx_sram_6t, n_tx_sram_8t, n_tx_sram_10t,
    n_read_ports_6t, n_read_ports_8t, n_read_ports_10t,
    a_sram_6t, a_sram_8t, a_sram_10t,
    g_access, g_pullup, g_pulldown, V_trip_inv, V_read_disturb, snm_read,
    V_write_internal, wnm_write, e_internal_write,
    c_dram, q_dram, V_dram, t_refresh, i_leak_dram, c_bitline_dram,
    V_dev_dram, V_offset_sa, V_input_sa, A_sa, V_sense_out, tau_sa,
    V_logic_target, t_resolve_sa, mu_log_ret, sigma_log_ret,
    t_retention_median, t_retention_mean, z_retention_guard,
    t_retention_guardband, t_retention_cell,
    n_tx_per_ff, t_setup, t_hold, t_clk_to_q,
    t_setup_intrinsic, t_hold_intrinsic, t_aperture, t_latch_regen,
    t_output_buffer, f_clk_ff, f_data_ff, T0_meta, tau_meta,
    t_resolve_meta, r_meta_fail, mtbf_meta,
]:
    sys_memcell.add(v)

for e in [
    eq_sram6t_tx, eq_sram8t_tx, eq_sram10t_tx,
    eq_sram6t_read_ports, eq_sram8t_read_ports, eq_sram10t_read_ports,
    eq_sram6t_area, eq_sram8t_area, eq_sram10t_area,
    eq_sram_access_time, eq_sram_read_energy, eq_sram_write_energy,
    eq_sram_leakage_power, eq_sram_read_disturb, eq_sram_read_snm,
    eq_sram_write_internal, eq_sram_write_wnm,
    ineq_sram_read_margin, ineq_sram_write_margin,
    eq_dram_charge, eq_dram_refresh, eq_dram_charge_sharing,
    eq_dram_sense_input, eq_dram_sense_output, eq_dram_sense_resolve,
    ineq_dram_sense_margin,
    eq_dram_retention_median, eq_dram_retention_mean,
    eq_dram_retention_guardband, retention_distribution,
    ineq_dram_refresh_guard,
    eq_ff_setup, eq_ff_hold, eq_ff_clk_to_q,
    eq_ff_meta_fail_rate, eq_ff_mtbf,
]:
    sys_memcell.add(e)
