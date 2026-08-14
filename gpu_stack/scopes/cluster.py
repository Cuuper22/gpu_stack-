"""
scopes/cluster.py
=================

Aggregator for the cluster scope: from one server to a fleet of sites.

The cluster scope answers the scaling question: if one GPU delivers some
compute, memory, and network capability, what does a node of eight deliver, a
rack of many nodes, a site of many racks, and a hyperscaler of many sites?
Most of the math is deliberate linear rollup — multiply by the count at each
level — plus the things that only appear at scale: top-of-rack switches and
oversubscription, shared storage feeding the data pipeline, job schedulers,
and reliability (failure rates, checkpoints, lost work).

The content lives in focused helpers for node, rack, site, storage, and
reliability. This file re-exports them all so public imports stay stable and
registers the combined lists under one System.
"""

from ..core import System

from .cluster_node import *
from .cluster_node import CLUSTER_NODE_EQUATIONS, CLUSTER_NODE_VARIABLES
from .cluster_rack import *
from .cluster_rack import CLUSTER_RACK_EQUATIONS, CLUSTER_RACK_VARIABLES
from .cluster_site import *
from .cluster_site import CLUSTER_SITE_EQUATIONS, CLUSTER_SITE_VARIABLES
from .cluster_storage import *
from .cluster_storage import CLUSTER_STORAGE_EQUATIONS, CLUSTER_STORAGE_VARIABLES
from .cluster_reliability import *
from .cluster_reliability import (
    CLUSTER_RELIABILITY_EQUATIONS,
    CLUSTER_RELIABILITY_VARIABLES,
)


sys_cluster = System(
    name="cluster",
    scope="cluster",
    description="Node NIC topology, rack, site, and hyperscaler aggregation with reliability and storage-path detail.",
)


CLUSTER_VARIABLES = (
    CLUSTER_NODE_VARIABLES
    + CLUSTER_RACK_VARIABLES
    + CLUSTER_SITE_VARIABLES
    + CLUSTER_STORAGE_VARIABLES
    + CLUSTER_RELIABILITY_VARIABLES
)

CLUSTER_EQUATIONS = (
    CLUSTER_NODE_EQUATIONS
    + CLUSTER_RACK_EQUATIONS
    + CLUSTER_SITE_EQUATIONS
    + CLUSTER_STORAGE_EQUATIONS
    + CLUSTER_RELIABILITY_EQUATIONS
)

for v in CLUSTER_VARIABLES:
    sys_cluster.add(v)

for e in CLUSTER_EQUATIONS:
    sys_cluster.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
