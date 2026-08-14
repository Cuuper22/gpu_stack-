"""
scopes/memory_dram.py
=====================

The DRAM bit: charge on a capacitor, read by a race against leakage.

A DRAM cell is one transistor and one capacitor (1T1C): the bit is simply
charge, and it leaks away, which is why DRAM must be refreshed — the
refresh period is the stored charge divided by the leakage current.
Reading is destructive and delicate. Opening the access transistor shares
the cell's charge with a much larger bitline capacitance, so the sense
amplifier sees only a small voltage step; it must overcome its own input
offset, then regenerate exponentially with gain and time constant until
the signal reaches logic level — that is the resolve time.

Retention is statistical, not uniform: cell retention times follow a
log-normal distribution, so the refresh interval must be guard-banded
several sigma below the median to cover the leakiest cells. The refresh
guard inequality checks exactly that. HBM inherits all of this — its
refresh overhead in memory_hbm is this physics at package scale.
"""

import sympy as sp

from ..core import Inequality, Reference, StochasticRelation, eq, var
from ..core.units import AMPERE, COULOMB, FARAD, SECOND, VOLT


# ---------------------------------------------------------------------------
# DRAM cell and sense path
# ---------------------------------------------------------------------------

DIMENSIONLESS = sp.Integer(1)

DRAM_CELL_REF = Reference(
    "DRAM device texts and memory-technology literature describe 1T1C "
    "storage, charge sharing, sense-amplifier offset/resolve behavior, and "
    "retention-time distributions.",
    kind="textbook",
)

c_dram = var(
    "memcell.dram.capacitance", "C_DRAM", "F",
    "Storage capacitance of one DRAM cell.",
    scope="memory_cell",
    sp_units=FARAD,
    references=[DRAM_CELL_REF],
)
q_dram = var(
    "memcell.dram.stored_charge", "Q_DRAM", "C",
    "Stored charge representing the logical state.",
    scope="memory_cell",
    sp_units=COULOMB,
    references=[DRAM_CELL_REF],
)
V_dram = var(
    "memcell.dram.v_cell", "V_DRAM", "V",
    "Cell voltage prior to charge sharing.",
    scope="memory_cell",
    sp_units=VOLT,
    references=[DRAM_CELL_REF],
)
t_refresh = var(
    "memcell.dram.refresh_period", "t_refresh", "s",
    "Refresh period.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[DRAM_CELL_REF],
)
i_leak_dram = var(
    "memcell.dram.i_leak", "I_leak_DRAM", "A",
    "Leakage current draining the DRAM storage capacitor.",
    scope="memory_cell",
    sp_units=AMPERE,
    references=[DRAM_CELL_REF],
)
c_bitline_dram = var(
    "memcell.dram.c_bitline", "C_bl_DRAM", "F",
    "Bitline capacitance participating in DRAM charge sharing.",
    scope="memory_cell",
    sp_units=FARAD,
    references=[DRAM_CELL_REF],
)
V_dev_dram = var(
    "memcell.dram.v_dev", "V_dev_DRAM", "V",
    "Differential voltage developed by charge sharing at the sense input.",
    scope="memory_cell",
    sp_units=VOLT,
    references=[DRAM_CELL_REF],
)
V_offset_sa = var(
    "memcell.dram.v_offset_sa", "V_os_SA", "V",
    "Input offset voltage of the DRAM sense amplifier.",
    scope="memory_cell",
    sp_units=VOLT,
    references=[DRAM_CELL_REF],
)
V_input_sa = var(
    "memcell.dram.v_input_sa", "V_in_SA", "V",
    "Effective differential input seen by the sense amplifier after offset loss.",
    scope="memory_cell",
    sp_units=VOLT,
    references=[DRAM_CELL_REF],
)
A_sa = var(
    "memcell.dram.sense_gain", "A_SA", "dimensionless",
    "Small-signal gain of the sense amplifier.",
    scope="memory_cell",
    sp_units=DIMENSIONLESS,
    references=[DRAM_CELL_REF],
)
V_sense_out = var(
    "memcell.dram.v_sense_out", "V_out_SA", "V",
    "Sense-amplifier output excursion.",
    scope="memory_cell",
    sp_units=VOLT,
    references=[DRAM_CELL_REF],
)
tau_sa = var(
    "memcell.dram.sense_tau", "tau_SA", "s",
    "Regenerative time constant of the sense amplifier.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[DRAM_CELL_REF],
)
V_logic_target = var(
    "memcell.dram.v_logic_target", "V_logic_SA", "V",
    "Output swing target treated as a completed sense decision.",
    scope="memory_cell",
    sp_units=VOLT,
    references=[DRAM_CELL_REF],
)
t_resolve_sa = var(
    "memcell.dram.t_resolve_sa", "t_res_SA", "s",
    "Time required for the sense amplifier to resolve the shared charge.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[DRAM_CELL_REF],
)
mu_log_ret = var(
    "memcell.dram.retention_log_mu", "mu_ret", "dimensionless",
    "Mean of log-retention-time across cells.",
    scope="memory_cell",
    sp_units=DIMENSIONLESS,
    references=[DRAM_CELL_REF],
)
sigma_log_ret = var(
    "memcell.dram.retention_log_sigma", "sigma_ret", "dimensionless",
    "Standard deviation of log-retention-time across cells.",
    scope="memory_cell",
    sp_units=DIMENSIONLESS,
    references=[DRAM_CELL_REF],
)
t_retention_median = var(
    "memcell.dram.retention_median", "t_ret_med", "s",
    "Median DRAM retention time across cells.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[DRAM_CELL_REF],
)
t_retention_mean = var(
    "memcell.dram.retention_mean", "t_ret_mean", "s",
    "Mean DRAM retention time across cells.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[DRAM_CELL_REF],
)
z_retention_guard = var(
    "memcell.dram.retention_guard_sigma", "z_ret", "dimensionless",
    "Lower-tail sigma multiple used to choose a refresh guardband.",
    scope="memory_cell",
    sp_units=DIMENSIONLESS,
    references=[DRAM_CELL_REF],
)
t_retention_guardband = var(
    "memcell.dram.retention_guardband", "t_ret_guard", "s",
    "Lower-tail retention target used for safe refresh policy.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[DRAM_CELL_REF],
)
t_retention_cell = var(
    "memcell.dram.retention_cell", "t_ret_cell", "s",
    "Retention time of a particular DRAM cell drawn from the array-wide distribution.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[DRAM_CELL_REF],
)


eq_dram_charge = eq(
    "memcell.eq.dram_charge",
    q_dram.symbol,
    c_dram.symbol * V_dram.symbol,
    "Stored DRAM charge Q = C V.",
    references=[DRAM_CELL_REF],
    check_units=True,
)

eq_dram_refresh = eq(
    "memcell.eq.dram_refresh_period",
    t_refresh.symbol,
    q_dram.symbol / i_leak_dram.symbol,
    "Approximate refresh period from stored charge divided by leakage current.",
    references=[DRAM_CELL_REF],
    check_units=True,
)

eq_dram_charge_sharing = eq(
    "memcell.eq.dram_charge_sharing",
    V_dev_dram.symbol,
    V_dram.symbol * c_dram.symbol / (c_dram.symbol + c_bitline_dram.symbol),
    "DRAM charge-sharing signal at the sense node.",
    references=[DRAM_CELL_REF],
    check_units=True,
)

eq_dram_sense_input = eq(
    "memcell.eq.dram_sense_input",
    V_input_sa.symbol,
    V_dev_dram.symbol - V_offset_sa.symbol,
    "Effective sense input after subtracting offset voltage.",
    references=[DRAM_CELL_REF],
    check_units=True,
)

eq_dram_sense_output = eq(
    "memcell.eq.dram_sense_output",
    V_sense_out.symbol,
    A_sa.symbol * V_input_sa.symbol,
    "Sense-amplifier output from gain times effective differential input.",
    references=[DRAM_CELL_REF],
    check_units=True,
)

eq_dram_sense_resolve = eq(
    "memcell.eq.dram_sense_resolve",
    t_resolve_sa.symbol,
    tau_sa.symbol * sp.log(V_logic_target.symbol / V_input_sa.symbol),
    "Regenerative sense-amplifier resolve time.",
    references=[DRAM_CELL_REF],
    check_units=True,
)
ineq_dram_sense_margin = Inequality(
    "memcell.eq.dram_sense_margin_constraint",
    V_dev_dram.symbol,
    V_offset_sa.symbol,
    ">=",
    "Charge-sharing differential must exceed sense-amplifier offset to be reliably detectable.",
    references=[DRAM_CELL_REF],
    check_units=True,
)

eq_dram_retention_median = eq(
    "memcell.eq.dram_retention_median",
    t_retention_median.symbol,
    sp.exp(mu_log_ret.symbol),
    "Median of the log-normal retention-time distribution.",
    references=[DRAM_CELL_REF],
)

eq_dram_retention_mean = eq(
    "memcell.eq.dram_retention_mean",
    t_retention_mean.symbol,
    sp.exp(mu_log_ret.symbol + sigma_log_ret.symbol**2 / 2),
    "Mean of the log-normal retention-time distribution.",
    references=[DRAM_CELL_REF],
)

eq_dram_retention_guardband = eq(
    "memcell.eq.dram_retention_guardband",
    t_retention_guardband.symbol,
    sp.exp(mu_log_ret.symbol - z_retention_guard.symbol * sigma_log_ret.symbol),
    "Lower-tail guardband for refresh scheduling under a log-normal retention model.",
    references=[DRAM_CELL_REF],
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
    references=[DRAM_CELL_REF],
)
ineq_dram_refresh_guard = Inequality(
    "memcell.eq.dram_refresh_guard_constraint",
    t_refresh.symbol,
    t_retention_guardband.symbol,
    "<=",
    "Refresh period must stay below the chosen lower-tail retention guardband.",
    references=[DRAM_CELL_REF],
    check_units=True,
)


MEMCELL_DRAM_VARIABLES = [
    c_dram, q_dram, V_dram, t_refresh, i_leak_dram, c_bitline_dram,
    V_dev_dram, V_offset_sa, V_input_sa, A_sa, V_sense_out, tau_sa,
    V_logic_target, t_resolve_sa, mu_log_ret, sigma_log_ret,
    t_retention_median, t_retention_mean, z_retention_guard,
    t_retention_guardband, t_retention_cell,
]

MEMCELL_DRAM_EQUATIONS = [
    eq_dram_charge, eq_dram_refresh, eq_dram_charge_sharing,
    eq_dram_sense_input, eq_dram_sense_output, eq_dram_sense_resolve,
    ineq_dram_sense_margin,
    eq_dram_retention_median, eq_dram_retention_mean,
    eq_dram_retention_guardband, retention_distribution,
    ineq_dram_refresh_guard,
]


__all__ = [
    "c_dram", "q_dram", "V_dram", "t_refresh", "i_leak_dram", "c_bitline_dram",
    "V_dev_dram", "V_offset_sa", "V_input_sa", "A_sa", "V_sense_out", "tau_sa",
    "V_logic_target", "t_resolve_sa", "mu_log_ret", "sigma_log_ret",
    "t_retention_median", "t_retention_mean", "z_retention_guard",
    "t_retention_guardband", "t_retention_cell",
    "eq_dram_charge", "eq_dram_refresh", "eq_dram_charge_sharing",
    "eq_dram_sense_input", "eq_dram_sense_output", "eq_dram_sense_resolve",
    "ineq_dram_sense_margin",
    "eq_dram_retention_median", "eq_dram_retention_mean",
    "eq_dram_retention_guardband", "retention_distribution",
    "ineq_dram_refresh_guard",
    "MEMCELL_DRAM_VARIABLES", "MEMCELL_DRAM_EQUATIONS",
]
