"""
scopes/interconnect_refs.py
===========================

Shared symbolic units and references for GPU fabric scopes.
"""

import sympy as sp

from ..core import Reference


DIMENSIONLESS = sp.Integer(1)

LINK_PATH_REF = Reference(
    "Interconnect link model: packet payload efficiency, alpha-beta latency, "
    "queueing, and bandwidth-delay product are tracked as metadata-bearing "
    "symbolic relations.",
    kind="model",
)
NVLINK_FABRIC_REF = Reference(
    "NVLink tier model: effective per-GPU payload bandwidth from the GPU "
    "scope is paired with hop latency and rack-domain aggregation.",
    kind="model",
)
SCALEOUT_FABRIC_REF = Reference(
    "Scale-out fabric model: per-GPU NIC rails, oversubscription, hop latency, "
    "and bisection bandwidth are represented as first-order fabric relations.",
    kind="model",
)


__all__ = [
    "DIMENSIONLESS",
    "LINK_PATH_REF",
    "NVLINK_FABRIC_REF",
    "SCALEOUT_FABRIC_REF",
]
