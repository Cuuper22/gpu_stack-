"""
scopes/collective_gather_scatter.py
===================================

AllGather and ReduceScatter variants.
"""

import sympy as sp

from ..core import eq, var
from ..core.units import SECOND
from .collective_refs import COLLECTIVE_ALGORITHM_REF
from .collective_topology import N_payload, n_nodes, p_ranks, ranks_per_node, ring_steps
from .interconnect import (
    alpha_link,
    alpha_nvlink,
    alpha_scale_out,
    beta_link,
    beta_nvlink,
    beta_scale_out,
)


t_allgather_ring = var(
    "col.allgather.time_ring", "t_AG_ring", "s",
    "Ring allgather completion time.",
    scope="collective",
    sp_units=SECOND,
    references=[COLLECTIVE_ALGORITHM_REF],
)
t_allgather_hier = var(
    "col.allgather.time_hier", "t_AG_hier", "s",
    "Hierarchical allgather completion time.",
    scope="collective",
    sp_units=SECOND,
    references=[COLLECTIVE_ALGORITHM_REF],
)
t_allgather = var(
    "col.allgather.time", "t_AG", "s",
    "Selected allgather completion time.",
    scope="collective",
    sp_units=SECOND,
    references=[COLLECTIVE_ALGORITHM_REF],
)
t_reducescatter_ring = var(
    "col.reducescatter.time_ring", "t_RS_ring", "s",
    "Ring reducescatter completion time.",
    scope="collective",
    sp_units=SECOND,
    references=[COLLECTIVE_ALGORITHM_REF],
)
t_reducescatter_hier = var(
    "col.reducescatter.time_hier", "t_RS_hier", "s",
    "Hierarchical reducescatter completion time.",
    scope="collective",
    sp_units=SECOND,
    references=[COLLECTIVE_ALGORITHM_REF],
)
t_reducescatter = var(
    "col.reducescatter.time", "t_RS", "s",
    "Selected reducescatter completion time.",
    scope="collective",
    sp_units=SECOND,
    references=[COLLECTIVE_ALGORITHM_REF],
)

eq_allgather_ring = eq(
    "col.eq.allgather_ring",
    t_allgather_ring.symbol,
    ring_steps.symbol * alpha_link.symbol + ring_steps.symbol * beta_link.symbol * N_payload.symbol / p_ranks.symbol,
    "Ring allgather takes p minus one steps, each paying alpha and moving N over p bytes.",
    references=[COLLECTIVE_ALGORITHM_REF],
    check_units=True,
)
eq_allgather_hier = eq(
    "col.eq.allgather_hier",
    t_allgather_hier.symbol,
    (n_nodes.symbol - 1) * alpha_scale_out.symbol
    + (n_nodes.symbol - 1) * beta_scale_out.symbol * N_payload.symbol / n_nodes.symbol
    + (ranks_per_node.symbol - 1) * alpha_nvlink.symbol
    + (ranks_per_node.symbol - 1) * beta_nvlink.symbol * N_payload.symbol / ranks_per_node.symbol,
    "Hierarchical allgather first gathers across nodes and then expands inside the fast local domain.",
    references=[COLLECTIVE_ALGORITHM_REF],
    check_units=True,
)
eq_allgather = eq(
    "col.eq.allgather",
    t_allgather.symbol,
    sp.Min(t_allgather_ring.symbol, t_allgather_hier.symbol),
    "Selected allgather time is the minimum of the ring and hierarchical variants.",
    references=[COLLECTIVE_ALGORITHM_REF],
    check_units=True,
)
eq_reducescatter_ring = eq(
    "col.eq.reducescatter_ring",
    t_reducescatter_ring.symbol,
    ring_steps.symbol * alpha_link.symbol + ring_steps.symbol * beta_link.symbol * N_payload.symbol / p_ranks.symbol,
    "Ring reducescatter has the same step structure as ring allgather.",
    references=[COLLECTIVE_ALGORITHM_REF],
    check_units=True,
)
eq_reducescatter_hier = eq(
    "col.eq.reducescatter_hier",
    t_reducescatter_hier.symbol,
    (ranks_per_node.symbol - 1) * alpha_nvlink.symbol
    + (ranks_per_node.symbol - 1) * beta_nvlink.symbol * N_payload.symbol / ranks_per_node.symbol
    + (n_nodes.symbol - 1) * alpha_scale_out.symbol
    + (n_nodes.symbol - 1) * beta_scale_out.symbol * N_payload.symbol / (ranks_per_node.symbol * n_nodes.symbol),
    "Hierarchical reducescatter first reduces locally and then scatters reduced shards across nodes.",
    references=[COLLECTIVE_ALGORITHM_REF],
    check_units=True,
)
eq_reducescatter = eq(
    "col.eq.reducescatter",
    t_reducescatter.symbol,
    sp.Min(t_reducescatter_ring.symbol, t_reducescatter_hier.symbol),
    "Selected reducescatter time is the minimum of the ring and hierarchical variants.",
    references=[COLLECTIVE_ALGORITHM_REF],
    check_units=True,
)


COLLECTIVE_GATHER_SCATTER_VARIABLES = (
    t_allgather_ring,
    t_allgather_hier,
    t_allgather,
    t_reducescatter_ring,
    t_reducescatter_hier,
    t_reducescatter,
)

COLLECTIVE_GATHER_SCATTER_EQUATIONS = (
    eq_allgather_ring,
    eq_allgather_hier,
    eq_allgather,
    eq_reducescatter_ring,
    eq_reducescatter_hier,
    eq_reducescatter,
)


__all__ = [
    "t_allgather_ring",
    "t_allgather_hier",
    "t_allgather",
    "t_reducescatter_ring",
    "t_reducescatter_hier",
    "t_reducescatter",
    "eq_allgather_ring",
    "eq_allgather_hier",
    "eq_allgather",
    "eq_reducescatter_ring",
    "eq_reducescatter_hier",
    "eq_reducescatter",
]
