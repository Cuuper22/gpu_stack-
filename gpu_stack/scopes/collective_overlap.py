"""
scopes/collective_overlap.py
============================

Overlap: communication hidden behind compute costs nothing.

A collective only slows training by the part of its duration that the GPU
spends idle waiting for it — the exposed time. If a kernel runs for T_c
while the collective takes T_comm, the overlap fraction is the share of
T_comm hidden under T_c (capped at 1 when compute fully covers it), and
the exposed time is what remains. This is the arithmetic behind async
tensor parallelism and similar schemes that break a matmul into tiles so
communication for one tile rides under compute for the next. The training
scope charges only the exposed time against the step.
"""

import sympy as sp

from ..core import eq, var
from ..core.units import SECOND
from .collective_refs import COLLECTIVE_OVERLAP_REF, DIMENSIONLESS


t_compute_tile = var(
    "col.async_tp.t_c", "T_c", "s",
    "Compute time that communication could potentially hide behind.",
    scope="collective",
    sp_units=SECOND,
    references=[COLLECTIVE_OVERLAP_REF],
)
t_comm_collective = var(
    "col.async_tp.t_comm", "T_comm", "s",
    "Raw communication time of the collective segment being overlapped.",
    scope="collective",
    sp_units=SECOND,
    references=[COLLECTIVE_OVERLAP_REF],
)
overlap_fraction = var(
    "col.async_tp.overlap_fraction", "rho_ov_col", "dimensionless",
    "Fraction of raw collective communication time hidden by compute.",
    scope="collective",
    sp_units=DIMENSIONLESS,
    references=[COLLECTIVE_OVERLAP_REF],
)
t_exposed_comm = var(
    "col.async_tp.t_exposed", "T_exp", "s",
    "Exposed, non-overlapped communication time.",
    scope="collective",
    sp_units=SECOND,
    references=[COLLECTIVE_OVERLAP_REF],
)

eq_overlap_fraction = eq(
    "col.eq.overlap_fraction",
    overlap_fraction.symbol,
    sp.Min(1, t_compute_tile.symbol / t_comm_collective.symbol),
    "The hidden fraction is capped at one and grows with compute time over communication time.",
    references=[COLLECTIVE_OVERLAP_REF],
    check_units=True,
)
eq_exposed = eq(
    "col.eq.exposed_async_tp",
    t_exposed_comm.symbol,
    sp.Max(0, t_comm_collective.symbol - t_compute_tile.symbol),
    "Exposed communication is the part left after subtracting the overlappable compute window.",
    references=[COLLECTIVE_OVERLAP_REF],
)


COLLECTIVE_OVERLAP_VARIABLES = (
    t_compute_tile,
    t_comm_collective,
    overlap_fraction,
    t_exposed_comm,
)

COLLECTIVE_OVERLAP_EQUATIONS = (
    eq_overlap_fraction,
    eq_exposed,
)


__all__ = [
    "t_compute_tile",
    "t_comm_collective",
    "overlap_fraction",
    "t_exposed_comm",
    "eq_overlap_fraction",
    "eq_exposed",
]
