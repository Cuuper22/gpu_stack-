"""
scopes/collective_allreduce.py
==============================

AllReduce algorithm variants and effective payload bandwidth.
"""

import sympy as sp

from ..core import eq, var
from ..core.units import BPS, SECOND
from .collective_refs import COLLECTIVE_ALGORITHM_REF
from .collective_topology import (
    N_payload,
    n_nodes,
    p_ranks,
    ranks_per_node,
    ring_steps,
    tree_depth,
)
from .interconnect import (
    alpha_link,
    alpha_nvlink,
    alpha_scale_out,
    beta_link,
    beta_nvlink,
    beta_scale_out,
)


t_allreduce_ring = var(
    "col.allreduce.time_ring", "t_AR_ring", "s",
    "Ring allreduce completion time.",
    scope="collective",
    sp_units=SECOND,
    references=[COLLECTIVE_ALGORITHM_REF],
)
t_allreduce_tree = var(
    "col.allreduce.time_tree", "t_AR_tree", "s",
    "Recursive-doubling or tree-style allreduce completion time.",
    scope="collective",
    sp_units=SECOND,
    references=[COLLECTIVE_ALGORITHM_REF],
)
t_allreduce_hier = var(
    "col.allreduce.time_hier", "t_AR_hier", "s",
    "Hierarchical allreduce time with fast intra-node and slower inter-node phases.",
    scope="collective",
    sp_units=SECOND,
    references=[COLLECTIVE_ALGORITHM_REF],
)
t_allreduce = var(
    "col.allreduce.time", "t_AR", "s",
    "Selected allreduce time, modeled as the minimum of the available implementations.",
    scope="collective",
    sp_units=SECOND,
    references=[COLLECTIVE_ALGORITHM_REF],
)
bw_allreduce_effective = var(
    "col.allreduce.bw_effective", "BW_AR_eff", "byte/s",
    "Effective allreduce payload bandwidth.",
    scope="collective",
    sp_units=BPS,
    references=[COLLECTIVE_ALGORITHM_REF],
)

eq_allreduce_ring = eq(
    "col.eq.allreduce_ring",
    t_allreduce_ring.symbol,
    2 * ring_steps.symbol * alpha_link.symbol + 2 * ring_steps.symbol * beta_link.symbol * N_payload.symbol / p_ranks.symbol,
    "Ring allreduce has two p minus one phase traversals. Each phase pays one alpha startup and moves N over p bytes per step.",
    references=[
        COLLECTIVE_ALGORITHM_REF,
        "Patarasuk and Yuan, Bandwidth optimal all-reduce algorithms, JPDC 2009.",
    ],
    check_units=True,
)
eq_allreduce_tree = eq(
    "col.eq.allreduce_tree",
    t_allreduce_tree.symbol,
    2 * tree_depth.symbol * alpha_link.symbol + 2 * (p_ranks.symbol - 1) * beta_link.symbol * N_payload.symbol / p_ranks.symbol,
    "A recursive-doubling style allreduce reduces alpha cost to logarithmic depth while keeping the aggregate bandwidth term near two times N over BW.",
    references=[COLLECTIVE_ALGORITHM_REF],
    check_units=True,
)
eq_allreduce_hier = eq(
    "col.eq.allreduce_hier",
    t_allreduce_hier.symbol,
    2 * (ranks_per_node.symbol - 1) * alpha_nvlink.symbol
    + 2 * (ranks_per_node.symbol - 1) * beta_nvlink.symbol * N_payload.symbol / ranks_per_node.symbol
    + 2 * (n_nodes.symbol - 1) * alpha_scale_out.symbol
    + 2 * (n_nodes.symbol - 1) * beta_scale_out.symbol * N_payload.symbol / (ranks_per_node.symbol * n_nodes.symbol),
    "Hierarchical allreduce performs local reduce-scatter plus all-gather on the fast intra-node fabric, then a smaller inter-node allreduce on the reduced shards.",
    references=[COLLECTIVE_ALGORITHM_REF],
    check_units=True,
)
eq_allreduce = eq(
    "col.eq.allreduce",
    t_allreduce.symbol,
    sp.Min(t_allreduce_ring.symbol, t_allreduce_tree.symbol, t_allreduce_hier.symbol),
    "Selected allreduce time is the minimum of the modeled ring, tree, and hierarchical variants.",
    references=[COLLECTIVE_ALGORITHM_REF],
    check_units=True,
)
eq_bw_allreduce_effective = eq(
    "col.eq.allreduce_bw_effective",
    bw_allreduce_effective.symbol,
    N_payload.symbol / t_allreduce.symbol,
    "Effective allreduce payload bandwidth is total payload divided by selected allreduce time.",
    references=[COLLECTIVE_ALGORITHM_REF],
    check_units=True,
)


COLLECTIVE_ALLREDUCE_VARIABLES = (
    t_allreduce_ring,
    t_allreduce_tree,
    t_allreduce_hier,
    t_allreduce,
    bw_allreduce_effective,
)

COLLECTIVE_ALLREDUCE_EQUATIONS = (
    eq_allreduce_ring,
    eq_allreduce_tree,
    eq_allreduce_hier,
    eq_allreduce,
    eq_bw_allreduce_effective,
)


__all__ = [
    "t_allreduce_ring",
    "t_allreduce_tree",
    "t_allreduce_hier",
    "t_allreduce",
    "bw_allreduce_effective",
    "eq_allreduce_ring",
    "eq_allreduce_tree",
    "eq_allreduce_hier",
    "eq_allreduce",
    "eq_bw_allreduce_effective",
]
