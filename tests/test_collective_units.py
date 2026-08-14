"""Checks unit and reference metadata for the collective-communication scope.

Collectives (all-reduce, all-to-all) are modelled with payload sizes in
bytes, times in seconds, and effective bandwidths in bits per second. These
tests require every variable to declare a unit and a reference, and pin the
exact set of equations exempt from dimensional checking to two named cases —
so a new unchecked equation cannot slip in silently.
"""

import sympy as sp

from gpu_stack.core.units import BPS, SECOND, byte
from gpu_stack.scopes import collective


DIMENSIONLESS = sp.Integer(1)

UNCHECKED_COLLECTIVE_EQUATIONS = {
    "col.eq.tree_depth",
    "col.eq.exposed_async_tp",
}


def test_collective_variables_have_units_and_references():
    assert [v.name for v in collective.sys_col.variables if v.sp_units is None] == []
    assert [v.name for v in collective.sys_col.variables if not v.references] == []


def test_collective_equations_have_references_and_curated_unit_checks():
    checked = {
        eq.name
        for eq in collective.sys_col.equations
        if getattr(eq, "_check_units_flag", False)
    }
    unchecked = {eq.name for eq in collective.sys_col.equations} - checked

    assert [eq.name for eq in collective.sys_col.equations if not eq.references] == []
    assert unchecked == UNCHECKED_COLLECTIVE_EQUATIONS


def test_collective_representative_units_cover_payload_times_and_bandwidths():
    assert collective.p_ranks.sp_units == DIMENSIONLESS
    assert collective.N_payload.sp_units == byte
    assert collective.payload_per_rank.sp_units == byte
    assert collective.latency_crossover_bytes.sp_units == byte
    assert collective.t_allreduce_ring.sp_units == SECOND
    assert collective.t_allreduce_hier.sp_units == SECOND
    assert collective.bw_allreduce_effective.sp_units == BPS
    assert collective.t_alltoall_moe.sp_units == SECOND
    assert collective.bw_alltoall_effective.sp_units == BPS
    assert collective.imbalance_moe.sp_units == DIMENSIONLESS
    assert collective.overlap_fraction.sp_units == DIMENSIONLESS
