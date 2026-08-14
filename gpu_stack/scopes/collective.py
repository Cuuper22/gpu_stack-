"""
scopes/collective.py
====================

Aggregator for collective communication: the cost of GPUs talking in groups.

A collective is an operation where every participating GPU (rank) exchanges
data with the group at once — AllReduce to sum gradients, AllGather and
ReduceScatter for sharded parameters, all-to-all for MoE token routing.
Each is modeled in alpha-beta form: alpha is the fixed per-message latency,
beta the per-byte time, taken from the interconnect scope for NVLink and
scale-out paths.

Two practical questions shape the scope. Which algorithm wins in the current
regime — ring, tree, or a hierarchical intra-node-then-inter-node split —
depends on payload size versus rank count. And how much of the cost is
actually felt depends on overlap: communication hidden behind compute is
free, and MoE all-to-all stretches with router imbalance. The declarations
live in focused helper modules and are re-exported here so public imports
stay stable.
"""

import sympy as sp

from ..core import Reference, System, eq, var
from ..core.units import BPS, SECOND, byte
from .collective_allreduce import *
from .collective_allreduce import (
    COLLECTIVE_ALLREDUCE_EQUATIONS as _COLLECTIVE_ALLREDUCE_EQUATIONS,
    COLLECTIVE_ALLREDUCE_VARIABLES as _COLLECTIVE_ALLREDUCE_VARIABLES,
)
from .collective_gather_scatter import *
from .collective_gather_scatter import (
    COLLECTIVE_GATHER_SCATTER_EQUATIONS as _COLLECTIVE_GATHER_SCATTER_EQUATIONS,
    COLLECTIVE_GATHER_SCATTER_VARIABLES as _COLLECTIVE_GATHER_SCATTER_VARIABLES,
)
from .collective_moe import *
from .collective_moe import (
    COLLECTIVE_MOE_EQUATIONS as _COLLECTIVE_MOE_EQUATIONS,
    COLLECTIVE_MOE_VARIABLES as _COLLECTIVE_MOE_VARIABLES,
)
from .collective_overlap import *
from .collective_overlap import (
    COLLECTIVE_OVERLAP_EQUATIONS as _COLLECTIVE_OVERLAP_EQUATIONS,
    COLLECTIVE_OVERLAP_VARIABLES as _COLLECTIVE_OVERLAP_VARIABLES,
)
from .collective_refs import *
from .collective_topology import *
from .collective_topology import (
    COLLECTIVE_TOPOLOGY_EQUATIONS as _COLLECTIVE_TOPOLOGY_EQUATIONS,
    COLLECTIVE_TOPOLOGY_VARIABLES as _COLLECTIVE_TOPOLOGY_VARIABLES,
)
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


_COLLECTIVE_VARIABLES = (
    _COLLECTIVE_TOPOLOGY_VARIABLES
    + _COLLECTIVE_ALLREDUCE_VARIABLES
    + _COLLECTIVE_GATHER_SCATTER_VARIABLES
    + _COLLECTIVE_MOE_VARIABLES
    + _COLLECTIVE_OVERLAP_VARIABLES
)

_COLLECTIVE_EQUATIONS = (
    _COLLECTIVE_TOPOLOGY_EQUATIONS
    + _COLLECTIVE_ALLREDUCE_EQUATIONS
    + _COLLECTIVE_GATHER_SCATTER_EQUATIONS
    + _COLLECTIVE_MOE_EQUATIONS
    + _COLLECTIVE_OVERLAP_EQUATIONS
)

for v in _COLLECTIVE_VARIABLES:
    sys_col.add(v)

for e in _COLLECTIVE_EQUATIONS:
    sys_col.add(e)
