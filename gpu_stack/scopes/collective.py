"""
scopes/collective.py
====================

Collective communication operations.

The older file encoded one ring formula per collective and then stopped.
That misses the two things practitioners actually care about:

  * which algorithm wins in the current regime, ring versus tree versus
    hierarchical intra-node plus inter-node decomposition
  * how much of the collective can be hidden behind compute or, in the MoE
    case, stretched by router imbalance

This scope now exposes those choices directly.
"""

import sympy as sp

from ..core import System, eq, var
from .interconnect import (
    alpha_link,
    alpha_nvlink,
    alpha_scale_out,
    beta_link,
    beta_nvlink,
    beta_scale_out,
)


sys_col = System(
    name="collective",
    scope="collective",
    description="Ring, tree, and hierarchical collectives, plus overlap and MoE imbalance.",
)


# ---------------------------------------------------------------------------
# Shared variables
# ---------------------------------------------------------------------------

p_ranks = var(
    "col.n_ranks", "p", "ranks",
    "Number of participating ranks in the collective.",
    scope="collective",
    integer=True,
)
ranks_per_node = var(
    "col.ranks_per_node", "p_node", "ranks/node",
    "Ranks that share the fast intra-node fabric.",
    scope="collective",
    integer=True,
)
n_nodes = var(
    "col.n_nodes", "N_node_col", "nodes",
    "Node count involved in the collective.",
    scope="collective",
    integer=True,
)
N_payload = var(
    "col.payload", "N", "byte",
    "Total collective payload in bytes.",
    scope="collective",
)
payload_per_rank = var(
    "col.payload_per_rank", "N_rank_col", "byte",
    "Collective payload per rank under equal partitioning.",
    scope="collective",
)
ring_steps = var(
    "col.ring_steps", "S_ring_col", "steps",
    "Step count of a ring collective.",
    scope="collective",
    integer=True,
)
tree_depth = var(
    "col.tree_depth", "D_tree_col", "levels",
    "Tree depth for a tree or recursive-doubling style collective.",
    scope="collective",
    integer=True,
)
latency_crossover_bytes = var(
    "col.latency_crossover_bytes", "B_xover_col", "byte",
    "Message size at which the generic alpha term equals the generic beta term.",
    scope="collective",
)

eq_payload_per_rank = eq(
    "col.eq.payload_per_rank",
    payload_per_rank.symbol,
    N_payload.symbol / p_ranks.symbol,
    "Equal partitioning gives payload per rank as total payload divided by rank count.",
)
eq_ring_steps = eq(
    "col.eq.ring_steps",
    ring_steps.symbol,
    p_ranks.symbol - 1,
    "A ring over p ranks takes p minus one steps.",
)
eq_n_nodes = eq(
    "col.eq.n_nodes",
    n_nodes.symbol,
    p_ranks.symbol / ranks_per_node.symbol,
    "Node count equals total ranks divided by ranks per node.",
)
eq_tree_depth = eq(
    "col.eq.tree_depth",
    tree_depth.symbol,
    sp.ceiling(sp.log(p_ranks.symbol, 2)),
    "Tree depth is the ceiling of log base two of the rank count.",
)
eq_latency_crossover_bytes = eq(
    "col.eq.latency_crossover_bytes",
    latency_crossover_bytes.symbol,
    alpha_link.symbol / beta_link.symbol,
    "The latency or bandwidth crossover message size is alpha divided by beta.",
)


# ---------------------------------------------------------------------------
# AllReduce
# ---------------------------------------------------------------------------

t_allreduce_ring = var(
    "col.allreduce.time_ring", "t_AR_ring", "s",
    "Ring allreduce completion time.",
    scope="collective",
)
t_allreduce_tree = var(
    "col.allreduce.time_tree", "t_AR_tree", "s",
    "Recursive-doubling or tree-style allreduce completion time.",
    scope="collective",
)
t_allreduce_hier = var(
    "col.allreduce.time_hier", "t_AR_hier", "s",
    "Hierarchical allreduce time with fast intra-node and slower inter-node phases.",
    scope="collective",
)
t_allreduce = var(
    "col.allreduce.time", "t_AR", "s",
    "Selected allreduce time, modeled as the minimum of the available implementations.",
    scope="collective",
)
bw_allreduce_effective = var(
    "col.allreduce.bw_effective", "BW_AR_eff", "byte/s",
    "Effective allreduce payload bandwidth.",
    scope="collective",
)

eq_allreduce_ring = eq(
    "col.eq.allreduce_ring",
    t_allreduce_ring.symbol,
    2 * ring_steps.symbol * alpha_link.symbol + 2 * ring_steps.symbol * beta_link.symbol * N_payload.symbol / p_ranks.symbol,
    "Ring allreduce has two p minus one phase traversals. Each phase pays one alpha startup and moves N over p bytes per step.",
    references=[
        "Patarasuk and Yuan, Bandwidth optimal all-reduce algorithms, JPDC 2009.",
    ],
)
eq_allreduce_tree = eq(
    "col.eq.allreduce_tree",
    t_allreduce_tree.symbol,
    2 * tree_depth.symbol * alpha_link.symbol + 2 * (p_ranks.symbol - 1) * beta_link.symbol * N_payload.symbol / p_ranks.symbol,
    "A recursive-doubling style allreduce reduces alpha cost to logarithmic depth while keeping the aggregate bandwidth term near two times N over BW.",
)
eq_allreduce_hier = eq(
    "col.eq.allreduce_hier",
    t_allreduce_hier.symbol,
    2 * (ranks_per_node.symbol - 1) * alpha_nvlink.symbol
    + 2 * (ranks_per_node.symbol - 1) * beta_nvlink.symbol * N_payload.symbol / ranks_per_node.symbol
    + 2 * (n_nodes.symbol - 1) * alpha_scale_out.symbol
    + 2 * (n_nodes.symbol - 1) * beta_scale_out.symbol * N_payload.symbol / (ranks_per_node.symbol * n_nodes.symbol),
    "Hierarchical allreduce performs local reduce-scatter plus all-gather on the fast intra-node fabric, then a smaller inter-node allreduce on the reduced shards.",
)
eq_allreduce = eq(
    "col.eq.allreduce",
    t_allreduce.symbol,
    sp.Min(t_allreduce_ring.symbol, t_allreduce_tree.symbol, t_allreduce_hier.symbol),
    "Selected allreduce time is the minimum of the modeled ring, tree, and hierarchical variants.",
)
eq_bw_allreduce_effective = eq(
    "col.eq.allreduce_bw_effective",
    bw_allreduce_effective.symbol,
    N_payload.symbol / t_allreduce.symbol,
    "Effective allreduce payload bandwidth is total payload divided by selected allreduce time.",
)


# ---------------------------------------------------------------------------
# AllGather and ReduceScatter
# ---------------------------------------------------------------------------

t_allgather_ring = var(
    "col.allgather.time_ring", "t_AG_ring", "s",
    "Ring allgather completion time.",
    scope="collective",
)
t_allgather_hier = var(
    "col.allgather.time_hier", "t_AG_hier", "s",
    "Hierarchical allgather completion time.",
    scope="collective",
)
t_allgather = var(
    "col.allgather.time", "t_AG", "s",
    "Selected allgather completion time.",
    scope="collective",
)
t_reducescatter_ring = var(
    "col.reducescatter.time_ring", "t_RS_ring", "s",
    "Ring reducescatter completion time.",
    scope="collective",
)
t_reducescatter_hier = var(
    "col.reducescatter.time_hier", "t_RS_hier", "s",
    "Hierarchical reducescatter completion time.",
    scope="collective",
)
t_reducescatter = var(
    "col.reducescatter.time", "t_RS", "s",
    "Selected reducescatter completion time.",
    scope="collective",
)

eq_allgather_ring = eq(
    "col.eq.allgather_ring",
    t_allgather_ring.symbol,
    ring_steps.symbol * alpha_link.symbol + ring_steps.symbol * beta_link.symbol * N_payload.symbol / p_ranks.symbol,
    "Ring allgather takes p minus one steps, each paying alpha and moving N over p bytes.",
)
eq_allgather_hier = eq(
    "col.eq.allgather_hier",
    t_allgather_hier.symbol,
    (n_nodes.symbol - 1) * alpha_scale_out.symbol
    + (n_nodes.symbol - 1) * beta_scale_out.symbol * N_payload.symbol / n_nodes.symbol
    + (ranks_per_node.symbol - 1) * alpha_nvlink.symbol
    + (ranks_per_node.symbol - 1) * beta_nvlink.symbol * N_payload.symbol / ranks_per_node.symbol,
    "Hierarchical allgather first gathers across nodes and then expands inside the fast local domain.",
)
eq_allgather = eq(
    "col.eq.allgather",
    t_allgather.symbol,
    sp.Min(t_allgather_ring.symbol, t_allgather_hier.symbol),
    "Selected allgather time is the minimum of the ring and hierarchical variants.",
)
eq_reducescatter_ring = eq(
    "col.eq.reducescatter_ring",
    t_reducescatter_ring.symbol,
    ring_steps.symbol * alpha_link.symbol + ring_steps.symbol * beta_link.symbol * N_payload.symbol / p_ranks.symbol,
    "Ring reducescatter has the same step structure as ring allgather.",
)
eq_reducescatter_hier = eq(
    "col.eq.reducescatter_hier",
    t_reducescatter_hier.symbol,
    (ranks_per_node.symbol - 1) * alpha_nvlink.symbol
    + (ranks_per_node.symbol - 1) * beta_nvlink.symbol * N_payload.symbol / ranks_per_node.symbol
    + (n_nodes.symbol - 1) * alpha_scale_out.symbol
    + (n_nodes.symbol - 1) * beta_scale_out.symbol * N_payload.symbol / (ranks_per_node.symbol * n_nodes.symbol),
    "Hierarchical reducescatter first reduces locally and then scatters reduced shards across nodes.",
)
eq_reducescatter = eq(
    "col.eq.reducescatter",
    t_reducescatter.symbol,
    sp.Min(t_reducescatter_ring.symbol, t_reducescatter_hier.symbol),
    "Selected reducescatter time is the minimum of the ring and hierarchical variants.",
)


# ---------------------------------------------------------------------------
# All-to-all and MoE imbalance
# ---------------------------------------------------------------------------

t_alltoall_pairwise = var(
    "col.alltoall.time_pairwise", "t_A2A_pair", "s",
    "Pairwise-exchange all-to-all completion time.",
    scope="collective",
)
t_alltoall_hier = var(
    "col.alltoall.time_hier", "t_A2A_hier", "s",
    "Hierarchical all-to-all completion time.",
    scope="collective",
)
t_alltoall = var(
    "col.alltoall.time", "t_A2A", "s",
    "Selected all-to-all completion time.",
    scope="collective",
)
bw_alltoall_effective = var(
    "col.alltoall.bw_effective", "BW_A2A_eff", "byte/s",
    "Effective all-to-all payload bandwidth.",
    scope="collective",
)
imbalance_moe = var(
    "col.moe.imbalance", "rho_MoE", "dimensionless",
    "MoE load imbalance factor, meaning max expert load divided by average expert load.",
    scope="collective",
)
t_alltoall_moe = var(
    "col.moe.alltoall_time", "t_A2A_MoE", "s",
    "MoE all-to-all time after applying the imbalance factor to the selected all-to-all baseline.",
    scope="collective",
)

eq_alltoall_pairwise = eq(
    "col.eq.alltoall_pairwise",
    t_alltoall_pairwise.symbol,
    ring_steps.symbol * alpha_link.symbol + ring_steps.symbol * beta_link.symbol * N_payload.symbol / p_ranks.symbol,
    "A pairwise all-to-all performs p minus one startup phases while each phase moves one rank's shard.",
)
eq_alltoall_hier = eq(
    "col.eq.alltoall_hier",
    t_alltoall_hier.symbol,
    2 * (ranks_per_node.symbol - 1) * alpha_nvlink.symbol
    + 2 * (ranks_per_node.symbol - 1) * beta_nvlink.symbol * N_payload.symbol / ranks_per_node.symbol
    + (n_nodes.symbol - 1) * alpha_scale_out.symbol
    + (n_nodes.symbol - 1) * beta_scale_out.symbol * N_payload.symbol / n_nodes.symbol,
    "Hierarchical all-to-all pays one local permutation phase on each side and one inter-node exchange phase in the middle.",
)
eq_alltoall = eq(
    "col.eq.alltoall",
    t_alltoall.symbol,
    sp.Min(t_alltoall_pairwise.symbol, t_alltoall_hier.symbol),
    "Selected all-to-all time is the minimum of the pairwise and hierarchical variants.",
)
eq_bw_alltoall_effective = eq(
    "col.eq.alltoall_bw_effective",
    bw_alltoall_effective.symbol,
    N_payload.symbol / t_alltoall.symbol,
    "Effective all-to-all payload bandwidth is payload divided by selected all-to-all time.",
)
eq_alltoall_moe = eq(
    "col.eq.alltoall_moe",
    t_alltoall_moe.symbol,
    imbalance_moe.symbol * t_alltoall.symbol,
    "MoE imbalance stretches the selected all-to-all time by the hottest-expert over average-load ratio.",
)


# ---------------------------------------------------------------------------
# Collective and compute overlap
# ---------------------------------------------------------------------------

t_compute_tile = var(
    "col.async_tp.t_c", "T_c", "s",
    "Compute time that communication could potentially hide behind.",
    scope="collective",
)
t_comm_collective = var(
    "col.async_tp.t_comm", "T_comm", "s",
    "Raw communication time of the collective segment being overlapped.",
    scope="collective",
)
overlap_fraction = var(
    "col.async_tp.overlap_fraction", "rho_ov_col", "dimensionless",
    "Fraction of raw collective communication time hidden by compute.",
    scope="collective",
)
t_exposed_comm = var(
    "col.async_tp.t_exposed", "T_exp", "s",
    "Exposed, non-overlapped communication time.",
    scope="collective",
)

eq_overlap_fraction = eq(
    "col.eq.overlap_fraction",
    overlap_fraction.symbol,
    sp.Min(1, t_compute_tile.symbol / t_comm_collective.symbol),
    "The hidden fraction is capped at one and grows with compute time over communication time.",
)
eq_exposed = eq(
    "col.eq.exposed_async_tp",
    t_exposed_comm.symbol,
    sp.Max(0, t_comm_collective.symbol - t_compute_tile.symbol),
    "Exposed communication is the part left after subtracting the overlappable compute window.",
)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

for v in [
    p_ranks,
    ranks_per_node,
    n_nodes,
    N_payload,
    payload_per_rank,
    ring_steps,
    tree_depth,
    latency_crossover_bytes,
    t_allreduce_ring,
    t_allreduce_tree,
    t_allreduce_hier,
    t_allreduce,
    bw_allreduce_effective,
    t_allgather_ring,
    t_allgather_hier,
    t_allgather,
    t_reducescatter_ring,
    t_reducescatter_hier,
    t_reducescatter,
    t_alltoall_pairwise,
    t_alltoall_hier,
    t_alltoall,
    bw_alltoall_effective,
    imbalance_moe,
    t_alltoall_moe,
    t_compute_tile,
    t_comm_collective,
    overlap_fraction,
    t_exposed_comm,
]:
    sys_col.add(v)

for e in [
    eq_payload_per_rank,
    eq_ring_steps,
    eq_n_nodes,
    eq_tree_depth,
    eq_latency_crossover_bytes,
    eq_allreduce_ring,
    eq_allreduce_tree,
    eq_allreduce_hier,
    eq_allreduce,
    eq_bw_allreduce_effective,
    eq_allgather_ring,
    eq_allgather_hier,
    eq_allgather,
    eq_reducescatter_ring,
    eq_reducescatter_hier,
    eq_reducescatter,
    eq_alltoall_pairwise,
    eq_alltoall_hier,
    eq_alltoall,
    eq_bw_alltoall_effective,
    eq_alltoall_moe,
    eq_overlap_fraction,
    eq_exposed,
]:
    sys_col.add(e)
