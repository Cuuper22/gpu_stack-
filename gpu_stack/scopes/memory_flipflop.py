"""
scopes/memory_flipflop.py
=========================

Register bit (flip-flop) timing and metastability.

Exposes setup, hold, and clock-to-Q decomposition along with the standard
metastability failure-rate and MTBF equations.
"""

import sympy as sp

from ..core import eq, var


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


MEMCELL_FF_VARIABLES = [
    n_tx_per_ff, t_setup, t_hold, t_clk_to_q,
    t_setup_intrinsic, t_hold_intrinsic, t_aperture, t_latch_regen,
    t_output_buffer, f_clk_ff, f_data_ff, T0_meta, tau_meta,
    t_resolve_meta, r_meta_fail, mtbf_meta,
]

MEMCELL_FF_EQUATIONS = [
    eq_ff_setup, eq_ff_hold, eq_ff_clk_to_q,
    eq_ff_meta_fail_rate, eq_ff_mtbf,
]


__all__ = [
    "n_tx_per_ff", "t_setup", "t_hold", "t_clk_to_q",
    "t_setup_intrinsic", "t_hold_intrinsic", "t_aperture", "t_latch_regen",
    "t_output_buffer", "f_clk_ff", "f_data_ff", "T0_meta", "tau_meta",
    "t_resolve_meta", "r_meta_fail", "mtbf_meta",
    "eq_ff_setup", "eq_ff_hold", "eq_ff_clk_to_q",
    "eq_ff_meta_fail_rate", "eq_ff_mtbf",
    "MEMCELL_FF_VARIABLES", "MEMCELL_FF_EQUATIONS",
]
