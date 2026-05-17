"""
scopes/collective_refs.py
=========================

Shared symbolic units and references for collective communication scopes.
"""

import sympy as sp

from ..core import Reference


DIMENSIONLESS = sp.Integer(1)

COLLECTIVE_TOPOLOGY_REF = Reference(
    "Collective communication metadata model: rank topology, payload "
    "partitioning, and latency-bandwidth crossover quantities shared by "
    "collective algorithms.",
    kind="model",
)
COLLECTIVE_ALGORITHM_REF = Reference(
    "Collective algorithm model: ring, tree, and hierarchical variants are "
    "represented with alpha-beta terms over generic, NVLink, and scale-out "
    "fabric paths.",
    kind="model",
)
ALLTOALL_MOE_REF = Reference(
    "All-to-all and MoE routing model: pairwise and hierarchical exchange "
    "costs are extended by a router load-imbalance factor.",
    kind="model",
)
COLLECTIVE_OVERLAP_REF = Reference(
    "Collective overlap model: exposed communication is the communication "
    "duration left after the available compute window hides part of it.",
    kind="model",
)


__all__ = [
    "DIMENSIONLESS",
    "COLLECTIVE_TOPOLOGY_REF",
    "COLLECTIVE_ALGORITHM_REF",
    "ALLTOALL_MOE_REF",
    "COLLECTIVE_OVERLAP_REF",
]
