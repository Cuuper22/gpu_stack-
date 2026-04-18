"""
scopes/parallelism_pipeline.py
==============================

Pipeline schedules. GPipe, 1F1B, interleaved, DualPipe, Chimera, and
zero-bubble formulas, including pipeline bubble fractions.
"""

import sympy as sp
from ..core import Approximation, eq, var


# ---------------------------------------------------------------------------
# Pipeline schedules
# ---------------------------------------------------------------------------

n_stages = var(
    "par.pp.n_stages", "S_PP", "stages",
    "Number of pipeline stages.",
    scope="parallelism",
)
n_microbatches = var(
    "par.pp.n_microbatches", "m_PP", "microbatches",
    "Microbatches per pipeline flush.",
    scope="parallelism",
)
t_forward = var(
    "par.pp.t_fwd", "t_fwd_PP", "s",
    "Forward time of one stage on one microbatch.",
    scope="parallelism",
)
t_backward = var(
    "par.pp.t_bwd", "t_bwd_PP", "s",
    "Backward time of one stage on one microbatch.",
    scope="parallelism",
)
bubble_gpipe = var(
    "par.pp.bubble_gpipe", "phi_gpipe_PP", "dimensionless",
    "Bubble fraction for flush-style GPipe.",
    scope="parallelism",
)
bubble_1f1b = var(
    "par.pp.bubble_1f1b", "phi_1f1b_PP", "dimensionless",
    "Bubble fraction under 1F1B.",
    scope="parallelism",
)
virtual_stages = var(
    "par.pp.virtual_stages", "V_PP", "stages",
    "Virtual stages per physical stage for interleaved 1F1B.",
    scope="parallelism",
)
bubble_interleaved = var(
    "par.pp.bubble_interleaved", "phi_il_PP", "dimensionless",
    "Bubble fraction under interleaved 1F1B.",
    scope="parallelism",
)
dualpipe_overlap = var(
    "par.pp.dualpipe_overlap", "rho_dual_PP", "dimensionless",
    "Fraction of the 1F1B bubble eliminated by overlapping forward and backward pipelines in DualPipe-style schedules.",
    scope="parallelism",
)
bubble_dualpipe = var(
    "par.pp.bubble_dualpipe", "phi_dual_PP", "dimensionless",
    "Bubble fraction under DualPipe-style overlap.",
    scope="parallelism",
)
chimera_overlap = var(
    "par.pp.chimera_overlap", "rho_chim_PP", "dimensionless",
    "Fraction of the 1F1B bubble eliminated by a Chimera-style schedule.",
    scope="parallelism",
)
bubble_chimera = var(
    "par.pp.bubble_chimera", "phi_chim_PP", "dimensionless",
    "Bubble fraction under Chimera-style overlap.",
    scope="parallelism",
)
bubble_zb = var(
    "par.pp.bubble_zb", "phi_zb_PP", "dimensionless",
    "Residual bubble under a zero-bubble schedule.",
    scope="parallelism",
)


eq_bubble_1f1b = eq(
    "par.eq.bubble_1f1b",
    bubble_1f1b.symbol,
    (n_stages.symbol - 1) / (n_stages.symbol - 1 + n_microbatches.symbol),
    "1F1B bubble fraction is the pipeline fill-drain overhead divided by the total steady-state stage slots.",
)

eq_bubble_gpipe = Approximation(
    "par.eq.bubble_gpipe",
    bubble_gpipe.symbol,
    (n_stages.symbol - 1) / n_microbatches.symbol,
    n_microbatches.symbol > n_stages.symbol,
    "For GPipe with many microbatches, bubble fraction is approximately (stages - 1) / microbatches.",
)

eq_bubble_interleaved = eq(
    "par.eq.bubble_interleaved",
    bubble_interleaved.symbol,
    (n_stages.symbol / virtual_stages.symbol - 1) / (n_stages.symbol / virtual_stages.symbol - 1 + n_microbatches.symbol),
    "Interleaving reduces the effective pipeline depth seen by the schedule.",
)

eq_bubble_dualpipe = eq(
    "par.eq.bubble_dualpipe",
    bubble_dualpipe.symbol,
    bubble_1f1b.symbol * (1 - dualpipe_overlap.symbol),
    "DualPipe-style overlap reduces the remaining 1F1B bubble by the achieved overlap fraction.",
)

eq_bubble_chimera = eq(
    "par.eq.bubble_chimera",
    bubble_chimera.symbol,
    bubble_1f1b.symbol * (1 - chimera_overlap.symbol),
    "Chimera-style schedules reduce the baseline 1F1B bubble by their achieved overlap fraction.",
)

eq_bubble_zb = eq(
    "par.eq.bubble_zb",
    bubble_zb.symbol,
    sp.Abs(t_backward.symbol - t_forward.symbol) / (t_backward.symbol + t_forward.symbol),
    "If forward and backward times match exactly the residual zero-bubble penalty is zero; any mismatch leaves only the imbalance term.",
)


PARALLELISM_PIPELINE_VARIABLES = [
    n_stages, n_microbatches, t_forward, t_backward, bubble_gpipe,
    bubble_1f1b, virtual_stages, bubble_interleaved, dualpipe_overlap,
    bubble_dualpipe, chimera_overlap, bubble_chimera, bubble_zb,
]

PARALLELISM_PIPELINE_EQUATIONS = [
    eq_bubble_1f1b,
    eq_bubble_gpipe,
    eq_bubble_interleaved,
    eq_bubble_dualpipe,
    eq_bubble_chimera,
    eq_bubble_zb,
]


__all__ = [
    "n_stages",
    "n_microbatches",
    "t_forward",
    "t_backward",
    "bubble_gpipe",
    "bubble_1f1b",
    "virtual_stages",
    "bubble_interleaved",
    "dualpipe_overlap",
    "bubble_dualpipe",
    "chimera_overlap",
    "bubble_chimera",
    "bubble_zb",
    "eq_bubble_1f1b",
    "eq_bubble_gpipe",
    "eq_bubble_interleaved",
    "eq_bubble_dualpipe",
    "eq_bubble_chimera",
    "eq_bubble_zb",
    "PARALLELISM_PIPELINE_VARIABLES",
    "PARALLELISM_PIPELINE_EQUATIONS",
]
