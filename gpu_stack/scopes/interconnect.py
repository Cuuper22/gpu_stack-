"""
scopes/interconnect.py
======================

Aggregator for GPU-to-GPU communication fabrics.

The old file stopped at one generic alpha-beta equation and a rack-level
bandwidth ratio. That throws away the actual structure that determines how
collectives behave in practice:

  * packet efficiency from payload bytes versus headers
  * propagation and switch-hop latency
  * congestion and oversubscription loss
  * the fact that NVLink and scale-out links are different fabrics with
    different alpha and beta terms

This scope now exposes those quantities directly so later collective and
training scopes can wire them in instead of treating communication as one
opaque tax. The implementation is split into focused helper modules and
re-exported here so public imports stay stable.
"""

import sympy as sp

from ..core import Approximation, Reference, System, eq, var
from ..core.units import BPS, SECOND, byte
from .gpu import (
    nic_bw_per_gpu_effective,
    nic_rate_per_gpu,
    nvlink_bw_per_gpu,
    nvlink_bw_per_gpu_effective,
)
from .interconnect_link import *
from .interconnect_link import (
    INTERCONNECT_LINK_EQUATIONS,
    INTERCONNECT_LINK_VARIABLES,
)
from .interconnect_nvlink import *
from .interconnect_nvlink import (
    INTERCONNECT_NVLINK_EQUATIONS,
    INTERCONNECT_NVLINK_VARIABLES,
)
from .interconnect_scaleout import *
from .interconnect_scaleout import (
    INTERCONNECT_SCALEOUT_EQUATIONS,
    INTERCONNECT_SCALEOUT_VARIABLES,
)
from .physical import t_flight


sys_link = System(
    name="interconnect",
    scope="interconnect",
    description="Packet efficiency, latency decomposition, NVLink, and scale-out fabrics.",
)


INTERCONNECT_VARIABLES = (
    INTERCONNECT_LINK_VARIABLES
    + INTERCONNECT_NVLINK_VARIABLES
    + INTERCONNECT_SCALEOUT_VARIABLES
)

INTERCONNECT_EQUATIONS = (
    INTERCONNECT_LINK_EQUATIONS
    + INTERCONNECT_NVLINK_EQUATIONS
    + INTERCONNECT_SCALEOUT_EQUATIONS
)

for v in INTERCONNECT_VARIABLES:
    sys_link.add(v)

for e in INTERCONNECT_EQUATIONS:
    sys_link.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
