"""
scopes/memory_flipflop.py
=========================

The flip-flop: the clocked bit that sets every pipeline's timing rules.

A flip-flop captures its input on a clock edge, and three times define its
contract: setup (how long the input must be stable before the edge), hold
(how long after), and clock-to-Q (how long until the output is valid).
Each decomposes into intrinsic latch terms — aperture, regeneration, and
output buffering — and together they bound how fast a pipeline stage can
be clocked.

Violate the setup/hold window and the latch can hang between 0 and 1:
metastability. The standard model says the failure rate is clock frequency
times data rate times an aperture term times exp(-t_resolve/tau), so every
extra resolution time buys an exponential reliability gain; its reciprocal
is the synchronizer MTBF. This is the physics behind clock-domain-crossing
design rules everywhere in the die.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import HZ, SECOND


DIMENSIONLESS = sp.Integer(1)

FF_TIMING_REF = Reference(
    "Rabaey, Chandrakasan, and Nikolic, Digital Integrated Circuits: "
    "A Design Perspective, flip-flop timing characterization and setup/hold/clock-to-Q.",
    kind="textbook",
)
FF_META_REF = Reference(
    "Chaney and Molnar, Anomalous Behavior of Synchronizer and Arbiter Circuits, "
    "IEEE Transactions on Computers, 1973; standard MTBF model for metastability.",
    kind="paper",
    year=1973,
)


# ---------------------------------------------------------------------------
# Register bit (flip-flop) and metastability
# ---------------------------------------------------------------------------

n_tx_per_ff = var(
    "memcell.ff.transistors", "N_Tx_FF", "dimensionless",
    "Transistors per flip-flop implementation.",
    scope="memory_cell",
    sp_units=DIMENSIONLESS,
    references=[FF_TIMING_REF],
)
t_setup = var(
    "memcell.ff.t_setup", "t_setup", "s",
    "Setup time.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[FF_TIMING_REF],
)
t_hold = var(
    "memcell.ff.t_hold", "t_hold", "s",
    "Hold time.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[FF_TIMING_REF],
)
t_clk_to_q = var(
    "memcell.ff.t_clk_to_q", "t_cq", "s",
    "Clock-to-Q propagation delay.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[FF_TIMING_REF],
)
t_setup_intrinsic = var(
    "memcell.ff.t_setup_intrinsic", "t_setup_int", "s",
    "Intrinsic setup requirement of the input latch path.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[FF_TIMING_REF],
)
t_hold_intrinsic = var(
    "memcell.ff.t_hold_intrinsic", "t_hold_int", "s",
    "Intrinsic hold requirement of the feedback path.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[FF_TIMING_REF],
)
t_aperture = var(
    "memcell.ff.t_aperture", "t_ap", "s",
    "Sampling aperture contribution around the active clock edge.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[FF_TIMING_REF],
)
t_latch_regen = var(
    "memcell.ff.t_latch_regen", "t_regen_FF", "s",
    "Regeneration delay of the latch pair.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[FF_TIMING_REF],
)
t_output_buffer = var(
    "memcell.ff.t_output_buffer", "t_buf_FF", "s",
    "Output buffer delay after the internal latch resolves.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[FF_TIMING_REF],
)
f_clk_ff = var(
    "memcell.ff.f_clk", "f_clk_FF", "Hz",
    "Clock frequency applied to the flip-flop.",
    scope="memory_cell",
    sp_units=HZ,
    references=[FF_META_REF],
)
f_data_ff = var(
    "memcell.ff.f_data", "f_data_FF", "Hz",
    "Relevant asynchronous or data-toggle event rate.",
    scope="memory_cell",
    sp_units=HZ,
    references=[FF_META_REF],
)
T0_meta = var(
    "memcell.ff.t0_meta", "T0_meta", "s",
    "Metastability fitting constant in the standard MTBF model.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[FF_META_REF],
)
tau_meta = var(
    "memcell.ff.tau_meta", "tau_meta", "s",
    "Metastability resolution time constant.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[FF_META_REF],
)
t_resolve_meta = var(
    "memcell.ff.t_resolve_meta", "t_res_meta", "s",
    "Time available for metastability to resolve before the next observer samples the node.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[FF_META_REF],
)
r_meta_fail = var(
    "memcell.ff.meta_fail_rate", "r_meta", "1/s",
    "Metastability failure rate.",
    scope="memory_cell",
    sp_units=1 / SECOND,
    references=[FF_META_REF],
)
mtbf_meta = var(
    "memcell.ff.mtbf_meta", "MTBF_meta", "s",
    "Mean time between metastability failures.",
    scope="memory_cell",
    sp_units=SECOND,
    references=[FF_META_REF],
)


eq_ff_setup = eq(
    "memcell.eq.ff_setup",
    t_setup.symbol,
    t_setup_intrinsic.symbol + t_aperture.symbol,
    "Setup time from intrinsic input path plus aperture requirement.",
    references=[FF_TIMING_REF],
    check_units=True,
)

eq_ff_hold = eq(
    "memcell.eq.ff_hold",
    t_hold.symbol,
    t_hold_intrinsic.symbol + t_aperture.symbol,
    "Hold time from intrinsic feedback settling plus aperture requirement.",
    references=[FF_TIMING_REF],
    check_units=True,
)

eq_ff_clk_to_q = eq(
    "memcell.eq.ff_clk_to_q",
    t_clk_to_q.symbol,
    t_latch_regen.symbol + t_output_buffer.symbol,
    "Clock-to-Q delay from latch regeneration plus output buffering.",
    references=[FF_TIMING_REF],
    check_units=True,
)

eq_ff_meta_fail_rate = eq(
    "memcell.eq.ff_meta_fail_rate",
    r_meta_fail.symbol,
    f_clk_ff.symbol * f_data_ff.symbol * T0_meta.symbol * sp.exp(-t_resolve_meta.symbol / tau_meta.symbol),
    "Standard metastability failure-rate model.",
    references=[FF_META_REF],
    check_units=True,
)

eq_ff_mtbf = eq(
    "memcell.eq.ff_mtbf",
    mtbf_meta.symbol,
    1 / r_meta_fail.symbol,
    "MTBF is the reciprocal of the metastability failure rate.",
    references=[FF_META_REF],
    check_units=True,
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
