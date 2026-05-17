"""
Shared declarations for site-level cluster helper modules.

The cluster site scope is split by model responsibility, but the references
and declaration factories stay here so every helper uses the same source
annotations and cluster scope wiring.
"""

from ..core import Reference
from .cluster_ops_declarations import (
    DIMENSIONLESS,
    referenced_eq,
    scoped_var,
)


SITE_AGGREGATION_REF = Reference(
    "Site aggregate compute, memory, local-storage, bandwidth, and IT-power "
    "quantities are rack-level rollups under a uniform-rack planning model.",
    kind="model",
)

SITE_POWER_PLANNING_REF = Reference(
    "Planning-stage site power applies a coarse facility overhead multiplier "
    "to IT power before the detailed thermal and facility model is attached.",
    kind="model",
)

SCHEDULER_OVERHEAD_REF = Reference(
    "Scheduler start delay is decomposed into queue wait, allocation, and "
    "provisioning terms before first useful training work begins.",
    kind="model",
)

SCALE_ACROSS_REF = Reference(
    "Scale-across WAN capacity is modeled from per-site long-haul link count, "
    "per-link payload bandwidth, transport efficiency, message size, and "
    "one-way latency.",
    kind="model",
)


site_aggregation_var = scoped_var("cluster", SITE_AGGREGATION_REF)
site_power_planning_var = scoped_var("cluster", SITE_POWER_PLANNING_REF)
scheduler_overhead_var = scoped_var("cluster", SCHEDULER_OVERHEAD_REF)
scale_across_var = scoped_var("cluster", SCALE_ACROSS_REF)

site_aggregation_eq = referenced_eq(SITE_AGGREGATION_REF)
site_power_planning_eq = referenced_eq(SITE_POWER_PLANNING_REF)
scheduler_overhead_eq = referenced_eq(SCHEDULER_OVERHEAD_REF)
scale_across_eq = referenced_eq(SCALE_ACROSS_REF)


__all__ = [
    "DIMENSIONLESS",
    "SITE_AGGREGATION_REF",
    "SITE_POWER_PLANNING_REF",
    "SCHEDULER_OVERHEAD_REF",
    "SCALE_ACROSS_REF",
    "site_aggregation_var",
    "site_power_planning_var",
    "scheduler_overhead_var",
    "scale_across_var",
    "site_aggregation_eq",
    "site_power_planning_eq",
    "scheduler_overhead_eq",
    "scale_across_eq",
]
