"""
scopes/collective_moe.py
========================

All-to-all collectives and MoE router imbalance.
"""

import sympy as sp

from ..core import eq, var
from ..core.units import BPS, SECOND
from .collective_refs import ALLTOALL_MOE_REF, DIMENSIONLESS
from .collective_topology import N_payload, n_nodes, p_ranks, ranks_per_node, ring_steps
from .interconnect import (
    alpha_link,
    alpha_nvlink,
    alpha_scale_out,
    beta_link,
    beta_nvlink,
    beta_scale_out,
)


t_alltoall_pairwise = var(
    "col.alltoall.time_pairwise", "t_A2A_pair", "s",
    "Pairwise-exchange all-to-all completion time.",
    scope="collective",
    sp_units=SECOND,
    references=[ALLTOALL_MOE_REF],
)
t_alltoall_hier = var(
    "col.alltoall.time_hier", "t_A2A_hier", "s",
    "Hierarchical all-to-all completion time.",
    scope="collective",
    sp_units=SECOND,
    references=[ALLTOALL_MOE_REF],
)
t_alltoall = var(
    "col.alltoall.time", "t_A2A", "s",
    "Selected all-to-all completion time.",
    scope="collective",
    sp_units=SECOND,
    references=[ALLTOALL_MOE_REF],
)
bw_alltoall_effective = var(
    "col.alltoall.bw_effective", "BW_A2A_eff", "byte/s",
    "Effective all-to-all payload bandwidth.",
    scope="collective",
    sp_units=BPS,
    references=[ALLTOALL_MOE_REF],
)
imbalance_moe = var(
    "col.moe.imbalance", "rho_MoE", "dimensionless",
    "MoE load imbalance factor, meaning max expert load divided by average expert load.",
    scope="collective",
    sp_units=DIMENSIONLESS,
    references=[ALLTOALL_MOE_REF],
)
t_alltoall_moe = var(
    "col.moe.alltoall_time", "t_A2A_MoE", "s",
    "MoE all-to-all time after applying the imbalance factor to the selected all-to-all baseline.",
    scope="collective",
    sp_units=SECOND,
    references=[ALLTOALL_MOE_REF],
)

eq_alltoall_pairwise = eq(
    "col.eq.alltoall_pairwise",
    t_alltoall_pairwise.symbol,
    ring_steps.symbol * alpha_link.symbol + ring_steps.symbol * beta_link.symbol * N_payload.symbol / p_ranks.symbol,
    "A pairwise all-to-all performs p minus one startup phases while each phase moves one rank's shard.",
    references=[ALLTOALL_MOE_REF],
    check_units=True,
)
eq_alltoall_hier = eq(
    "col.eq.alltoall_hier",
    t_alltoall_hier.symbol,
    2 * (ranks_per_node.symbol - 1) * alpha_nvlink.symbol
    + 2 * (ranks_per_node.symbol - 1) * beta_nvlink.symbol * N_payload.symbol / ranks_per_node.symbol
    + (n_nodes.symbol - 1) * alpha_scale_out.symbol
    + (n_nodes.symbol - 1) * beta_scale_out.symbol * N_payload.symbol / n_nodes.symbol,
    "Hierarchical all-to-all pays one local permutation phase on each side and one inter-node exchange phase in the middle.",
    references=[ALLTOALL_MOE_REF],
    check_units=True,
)
eq_alltoall = eq(
    "col.eq.alltoall",
    t_alltoall.symbol,
    sp.Min(t_alltoall_pairwise.symbol, t_alltoall_hier.symbol),
    "Selected all-to-all time is the minimum of the pairwise and hierarchical variants.",
    references=[ALLTOALL_MOE_REF],
    check_units=True,
)
eq_bw_alltoall_effective = eq(
    "col.eq.alltoall_bw_effective",
    bw_alltoall_effective.symbol,
    N_payload.symbol / t_alltoall.symbol,
    "Effective all-to-all payload bandwidth is payload divided by selected all-to-all time.",
    references=[ALLTOALL_MOE_REF],
    check_units=True,
)
eq_alltoall_moe = eq(
    "col.eq.alltoall_moe",
    t_alltoall_moe.symbol,
    imbalance_moe.symbol * t_alltoall.symbol,
    "MoE imbalance stretches the selected all-to-all time by the hottest-expert over average-load ratio.",
    references=[ALLTOALL_MOE_REF],
    check_units=True,
)


COLLECTIVE_MOE_VARIABLES = (
    t_alltoall_pairwise,
    t_alltoall_hier,
    t_alltoall,
    bw_alltoall_effective,
    imbalance_moe,
    t_alltoall_moe,
)

COLLECTIVE_MOE_EQUATIONS = (
    eq_alltoall_pairwise,
    eq_alltoall_hier,
    eq_alltoall,
    eq_bw_alltoall_effective,
    eq_alltoall_moe,
)


__all__ = [
    "t_alltoall_pairwise",
    "t_alltoall_hier",
    "t_alltoall",
    "bw_alltoall_effective",
    "imbalance_moe",
    "t_alltoall_moe",
    "eq_alltoall_pairwise",
    "eq_alltoall_hier",
    "eq_alltoall",
    "eq_bw_alltoall_effective",
    "eq_alltoall_moe",
]
