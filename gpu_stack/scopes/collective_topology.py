"""
scopes/collective_topology.py
=============================

Who is talking and how much data moves: shared inputs for every collective.

Every collective algorithm needs the same handful of facts before any
formula applies: how many ranks participate, how many of them share a fast
intra-node fabric (which fixes the node count), and how many payload bytes
must move. From these come the purely structural quantities — ring step
count 2*(p-1), tree depth log2(p), and per-rank payload share — plus the
latency-bandwidth crossover: the payload size alpha/beta at which
per-message latency stops dominating and per-byte cost takes over. The
algorithm modules import these symbols instead of redeclaring them.
"""

import sympy as sp

from ..core import eq, var
from ..core.units import byte
from .collective_refs import DIMENSIONLESS, COLLECTIVE_TOPOLOGY_REF
from .interconnect import alpha_link, beta_link


p_ranks = var(
    "col.n_ranks", "p", "ranks",
    "Number of participating ranks in the collective.",
    scope="collective",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[COLLECTIVE_TOPOLOGY_REF],
)
ranks_per_node = var(
    "col.ranks_per_node", "p_node", "ranks/node",
    "Ranks that share the fast intra-node fabric.",
    scope="collective",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[COLLECTIVE_TOPOLOGY_REF],
)
n_nodes = var(
    "col.n_nodes", "N_node_col", "nodes",
    "Node count involved in the collective.",
    scope="collective",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[COLLECTIVE_TOPOLOGY_REF],
)
N_payload = var(
    "col.payload", "N", "byte",
    "Total collective payload in bytes.",
    scope="collective",
    sp_units=byte,
    references=[COLLECTIVE_TOPOLOGY_REF],
)
payload_per_rank = var(
    "col.payload_per_rank", "N_rank_col", "byte",
    "Collective payload per rank under equal partitioning.",
    scope="collective",
    sp_units=byte,
    references=[COLLECTIVE_TOPOLOGY_REF],
)
ring_steps = var(
    "col.ring_steps", "S_ring_col", "steps",
    "Step count of a ring collective.",
    scope="collective",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[COLLECTIVE_TOPOLOGY_REF],
)
tree_depth = var(
    "col.tree_depth", "D_tree_col", "levels",
    "Tree depth for a tree or recursive-doubling style collective.",
    scope="collective",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[COLLECTIVE_TOPOLOGY_REF],
)
latency_crossover_bytes = var(
    "col.latency_crossover_bytes", "B_xover_col", "byte",
    "Message size at which the generic alpha term equals the generic beta term.",
    scope="collective",
    sp_units=byte,
    references=[COLLECTIVE_TOPOLOGY_REF],
)

eq_payload_per_rank = eq(
    "col.eq.payload_per_rank",
    payload_per_rank.symbol,
    N_payload.symbol / p_ranks.symbol,
    "Equal partitioning gives payload per rank as total payload divided by rank count.",
    references=[COLLECTIVE_TOPOLOGY_REF],
    check_units=True,
)
eq_ring_steps = eq(
    "col.eq.ring_steps",
    ring_steps.symbol,
    p_ranks.symbol - 1,
    "A ring over p ranks takes p minus one steps.",
    references=[COLLECTIVE_TOPOLOGY_REF],
    check_units=True,
)
eq_n_nodes = eq(
    "col.eq.n_nodes",
    n_nodes.symbol,
    p_ranks.symbol / ranks_per_node.symbol,
    "Node count equals total ranks divided by ranks per node.",
    references=[COLLECTIVE_TOPOLOGY_REF],
    check_units=True,
)
eq_tree_depth = eq(
    "col.eq.tree_depth",
    tree_depth.symbol,
    sp.ceiling(sp.log(p_ranks.symbol, 2)),
    "Tree depth is the ceiling of log base two of the rank count.",
    references=[COLLECTIVE_TOPOLOGY_REF],
)
eq_latency_crossover_bytes = eq(
    "col.eq.latency_crossover_bytes",
    latency_crossover_bytes.symbol,
    alpha_link.symbol / beta_link.symbol,
    "The latency or bandwidth crossover message size is alpha divided by beta.",
    references=[COLLECTIVE_TOPOLOGY_REF],
    check_units=True,
)


COLLECTIVE_TOPOLOGY_VARIABLES = (
    p_ranks,
    ranks_per_node,
    n_nodes,
    N_payload,
    payload_per_rank,
    ring_steps,
    tree_depth,
    latency_crossover_bytes,
)

COLLECTIVE_TOPOLOGY_EQUATIONS = (
    eq_payload_per_rank,
    eq_ring_steps,
    eq_n_nodes,
    eq_tree_depth,
    eq_latency_crossover_bytes,
)


__all__ = [
    "p_ranks",
    "ranks_per_node",
    "n_nodes",
    "N_payload",
    "payload_per_rank",
    "ring_steps",
    "tree_depth",
    "latency_crossover_bytes",
    "eq_payload_per_rank",
    "eq_ring_steps",
    "eq_n_nodes",
    "eq_tree_depth",
    "eq_latency_crossover_bytes",
]
