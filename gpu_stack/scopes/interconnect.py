"""
scopes/interconnect.py
======================

Aggregator for GPU-to-GPU communication fabrics.

Moving a message between GPUs costs a fixed setup time plus a per-byte
time — the alpha-beta model that every collective formula is built on.
This scope derives those two constants from physical structure rather than
asserting them: packet headers eat a fraction of the raw line rate,
propagation and switch hops add latency, and congestion or
oversubscription cuts usable bandwidth further.

It matters that a cluster contains two distinct fabrics. NVLink joins the
GPUs inside a rack — few hops, low alpha, high beta-bandwidth — while the
scale-out network (InfiniBand or Ethernet through NICs and switches) joins
racks, with more hops, host-stack latency, and oversubscription. Each gets
its own alpha and beta so the collective scope can price intra-node and
inter-node phases separately. The implementation is split into focused
helper modules (generic link, NVLink tier, scale-out tier) and re-exported
here so public imports stay stable.
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
