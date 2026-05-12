"""
scopes/cluster_reliability.py
=============================

Reliability, failure domains, and checkpoint optimization.

Large distributed training runs fail often enough that the relevant question
is not whether they fail but how much work is lost when they do. This file
models exponential-failure hazard rates for nodes, rack infrastructure, and
the site fabric, the checkpoint size and bandwidth that define recovery
granularity, Young-style optimal checkpoint spacing, and the reliability-only
availability estimate that rolls up checkpoint, lost-work, and recovery
overhead into a single fraction.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import BPS, SECOND, byte

from .interconnect import n_gpus_per_rack
from .cluster_site import cluster_n_nodes, n_racks_cluster


DIMENSIONLESS = sp.Integer(1)

RELIABILITY_DOMAIN_REF = Reference(
    "Cluster reliability planning separates node hazards, rack shared "
    "infrastructure hazards, site-fabric hazards, and correlated failure "
    "domains before aggregating interruption risk.",
    kind="model",
)

CHECKPOINT_RELIABILITY_REF = Reference(
    "Checkpoint reliability overhead follows a Young-style periodic "
    "checkpoint model: checkpoint write time, MTBF, lost work, recovery time, "
    "and the resulting availability fraction.",
    kind="model",
)


racks_per_fabric_domain = var(
    "cluster.rel.racks_per_fabric_domain", "N_rack_fd", "racks",
    "Racks that fail together under one fabric-domain or aggregation-switch outage.",
    scope="cluster",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[RELIABILITY_DOMAIN_REF],
)
node_mtbf = var(
    "cluster.rel.node_mtbf", "MTBF_node", "s",
    "Mean time between node failures.",
    scope="cluster",
    sp_units=SECOND,
    references=[RELIABILITY_DOMAIN_REF],
)
tor_switch_mtbf = var(
    "cluster.rel.tor_switch_mtbf", "MTBF_tor", "s",
    "Mean time between top-of-rack switch failures.",
    scope="cluster",
    sp_units=SECOND,
    references=[RELIABILITY_DOMAIN_REF],
)
rack_power_domain_mtbf = var(
    "cluster.rel.rack_power_domain_mtbf", "MTBF_rack_pwr", "s",
    "Mean time between rack-level power-domain failures.",
    scope="cluster",
    sp_units=SECOND,
    references=[RELIABILITY_DOMAIN_REF],
)
site_fabric_mtbf = var(
    "cluster.rel.site_fabric_mtbf", "MTBF_site_fab", "s",
    "Mean time between site-level fabric or control-plane failures that interrupt many racks.",
    scope="cluster",
    sp_units=SECOND,
    references=[RELIABILITY_DOMAIN_REF],
)
node_failure_rate = var(
    "cluster.rel.node_failure_rate", "lambda_node", "1/s",
    "Failure hazard rate of one node under an exponential-failure approximation.",
    scope="cluster",
    sp_units=1 / SECOND,
    references=[RELIABILITY_DOMAIN_REF],
)
rack_infra_failure_rate = var(
    "cluster.rel.rack_infra_failure_rate", "lambda_rack_inf", "1/s",
    "Failure hazard rate from rack-level shared infrastructure.",
    scope="cluster",
    sp_units=1 / SECOND,
    references=[RELIABILITY_DOMAIN_REF],
)
cluster_failure_rate = var(
    "cluster.rel.site_failure_rate", "lambda_site", "1/s",
    "Aggregate interruption hazard rate of the site from node, rack, and site-domain failures.",
    scope="cluster",
    sp_units=1 / SECOND,
    references=[RELIABILITY_DOMAIN_REF],
)
cluster_mtbf = var(
    "cluster.rel.site_mtbf", "MTBF_site", "s",
    "Mean time between site-level job interruptions.",
    scope="cluster",
    sp_units=SECOND,
    references=[RELIABILITY_DOMAIN_REF],
)
gpus_per_fabric_domain = var(
    "cluster.rel.gpus_per_fabric_domain", "N_GPU_fd", "GPUs",
    "GPUs that can disappear together in one shared fabric-domain failure.",
    scope="cluster",
    integer=True,
    sp_units=DIMENSIONLESS,
    references=[RELIABILITY_DOMAIN_REF],
)
mean_time_to_recover = var(
    "cluster.rel.mttr", "MTTR_site", "s",
    "Mean time to recover a failed distributed training job after interruption.",
    scope="cluster",
    sp_units=SECOND,
    references=[CHECKPOINT_RELIABILITY_REF],
)
checkpoint_size = var(
    "cluster.rel.checkpoint_size", "B_ckpt", "byte",
    "Bytes written by one checkpoint, including model, optimizer, and metadata.",
    scope="cluster",
    sp_units=byte,
    references=[CHECKPOINT_RELIABILITY_REF],
)
checkpoint_bw = var(
    "cluster.rel.checkpoint_bw", "BW_ckpt", "byte/s",
    "Sustained checkpoint write bandwidth.",
    scope="cluster",
    sp_units=BPS,
    references=[CHECKPOINT_RELIABILITY_REF],
)
checkpoint_time = var(
    "cluster.rel.checkpoint_time", "T_ckpt", "s",
    "Time to write one checkpoint.",
    scope="cluster",
    sp_units=SECOND,
    references=[CHECKPOINT_RELIABILITY_REF],
)
optimal_checkpoint_interval = var(
    "cluster.rel.optimal_checkpoint_interval", "T_ckpt_opt", "s",
    "Young-style optimal checkpoint interval that trades checkpoint cost against expected lost work.",
    scope="cluster",
    sp_units=SECOND,
    references=[CHECKPOINT_RELIABILITY_REF],
)
checkpoint_overhead_fraction = var(
    "cluster.rel.checkpoint_overhead_fraction", "f_ckpt", "dimensionless",
    "Fractional time overhead from taking checkpoints at the optimal interval.",
    scope="cluster",
    sp_units=DIMENSIONLESS,
    references=[CHECKPOINT_RELIABILITY_REF],
)
lost_work_fraction = var(
    "cluster.rel.lost_work_fraction", "f_lost", "dimensionless",
    "Expected fractional loss from work discarded between failures.",
    scope="cluster",
    sp_units=DIMENSIONLESS,
    references=[CHECKPOINT_RELIABILITY_REF],
)
recovery_overhead_fraction = var(
    "cluster.rel.recovery_overhead_fraction", "f_rec", "dimensionless",
    "Fractional wall-clock overhead from restore and restart work after failures.",
    scope="cluster",
    sp_units=DIMENSIONLESS,
    references=[CHECKPOINT_RELIABILITY_REF],
)
availability_from_reliability = var(
    "cluster.rel.availability_est", "A_rel", "dimensionless",
    "Reliability-only availability estimate after checkpoint, lost-work, and recovery overheads.",
    scope="cluster",
    sp_units=DIMENSIONLESS,
    references=[CHECKPOINT_RELIABILITY_REF],
)


eq_node_failure_rate = eq(
    "cluster.eq.node_failure_rate",
    node_failure_rate.symbol,
    1 / node_mtbf.symbol,
    "Node failure hazard rate is the reciprocal of node MTBF under an exponential-failure approximation.",
    references=[RELIABILITY_DOMAIN_REF],
    check_units=True,
)

eq_rack_infra_failure_rate = eq(
    "cluster.eq.rack_infra_failure_rate",
    rack_infra_failure_rate.symbol,
    1 / tor_switch_mtbf.symbol + 1 / rack_power_domain_mtbf.symbol,
    "Rack infrastructure failure rate sums top-of-rack switch and shared power-domain hazards.",
    references=[RELIABILITY_DOMAIN_REF],
    check_units=True,
)

eq_cluster_failure_rate = eq(
    "cluster.eq.site_failure_rate",
    cluster_failure_rate.symbol,
    cluster_n_nodes.symbol * node_failure_rate.symbol
    + n_racks_cluster.symbol * rack_infra_failure_rate.symbol
    + 1 / site_fabric_mtbf.symbol,
    "Site interruption rate is the sum of node hazards, rack shared-infrastructure hazards, and one site-domain hazard term.",
    references=[RELIABILITY_DOMAIN_REF],
    check_units=True,
)

eq_cluster_mtbf = eq(
    "cluster.eq.site_mtbf",
    cluster_mtbf.symbol,
    1 / cluster_failure_rate.symbol,
    "Site MTBF is the reciprocal of the aggregate interruption hazard rate.",
    references=[RELIABILITY_DOMAIN_REF],
    check_units=True,
)

eq_gpus_per_fabric_domain = eq(
    "cluster.eq.gpus_per_fabric_domain",
    gpus_per_fabric_domain.symbol,
    racks_per_fabric_domain.symbol * n_gpus_per_rack.symbol,
    "GPUs per fabric domain equal racks covered by that domain times GPUs per rack.",
    references=[RELIABILITY_DOMAIN_REF],
    check_units=True,
)

eq_checkpoint_time = eq(
    "cluster.eq.checkpoint_time",
    checkpoint_time.symbol,
    checkpoint_size.symbol / checkpoint_bw.symbol,
    "Checkpoint time equals checkpoint bytes divided by sustained checkpoint write bandwidth.",
    references=[CHECKPOINT_RELIABILITY_REF],
    check_units=True,
)

eq_optimal_checkpoint_interval = eq(
    "cluster.eq.optimal_checkpoint_interval",
    optimal_checkpoint_interval.symbol,
    sp.sqrt(2 * checkpoint_time.symbol * cluster_mtbf.symbol),
    "Young's classic checkpoint interval is the square root of twice the product of checkpoint time and MTBF.",
    references=[CHECKPOINT_RELIABILITY_REF],
    check_units=True,
)

eq_checkpoint_overhead_fraction = eq(
    "cluster.eq.checkpoint_overhead_fraction",
    checkpoint_overhead_fraction.symbol,
    checkpoint_time.symbol / optimal_checkpoint_interval.symbol,
    "Checkpoint overhead fraction equals checkpoint time divided by checkpoint interval.",
    references=[CHECKPOINT_RELIABILITY_REF],
    check_units=True,
)

eq_lost_work_fraction = eq(
    "cluster.eq.lost_work_fraction",
    lost_work_fraction.symbol,
    optimal_checkpoint_interval.symbol / (2 * cluster_mtbf.symbol),
    "Expected lost-work fraction under periodic checkpointing is half the interval divided by MTBF.",
    references=[CHECKPOINT_RELIABILITY_REF],
    check_units=True,
)

eq_recovery_overhead_fraction = eq(
    "cluster.eq.recovery_overhead_fraction",
    recovery_overhead_fraction.symbol,
    mean_time_to_recover.symbol / cluster_mtbf.symbol,
    "Recovery overhead fraction equals mean time to recover divided by site MTBF.",
    references=[CHECKPOINT_RELIABILITY_REF],
    check_units=True,
)

eq_availability_from_reliability = eq(
    "cluster.eq.availability_from_reliability",
    availability_from_reliability.symbol,
    1 - checkpoint_overhead_fraction.symbol - lost_work_fraction.symbol - recovery_overhead_fraction.symbol,
    "A first-order reliability availability estimate subtracts checkpoint, lost-work, and recovery overhead fractions from one.",
    references=[CHECKPOINT_RELIABILITY_REF],
    check_units=True,
)


CLUSTER_RELIABILITY_VARIABLES = [
    racks_per_fabric_domain,
    node_mtbf,
    tor_switch_mtbf,
    rack_power_domain_mtbf,
    site_fabric_mtbf,
    node_failure_rate,
    rack_infra_failure_rate,
    cluster_failure_rate,
    cluster_mtbf,
    gpus_per_fabric_domain,
    mean_time_to_recover,
    checkpoint_size,
    checkpoint_bw,
    checkpoint_time,
    optimal_checkpoint_interval,
    checkpoint_overhead_fraction,
    lost_work_fraction,
    recovery_overhead_fraction,
    availability_from_reliability,
]

CLUSTER_RELIABILITY_EQUATIONS = [
    eq_node_failure_rate,
    eq_rack_infra_failure_rate,
    eq_cluster_failure_rate,
    eq_cluster_mtbf,
    eq_gpus_per_fabric_domain,
    eq_checkpoint_time,
    eq_optimal_checkpoint_interval,
    eq_checkpoint_overhead_fraction,
    eq_lost_work_fraction,
    eq_recovery_overhead_fraction,
    eq_availability_from_reliability,
]


__all__ = [
    "racks_per_fabric_domain", "node_mtbf", "tor_switch_mtbf",
    "rack_power_domain_mtbf", "site_fabric_mtbf",
    "node_failure_rate", "rack_infra_failure_rate",
    "cluster_failure_rate", "cluster_mtbf",
    "gpus_per_fabric_domain", "mean_time_to_recover",
    "checkpoint_size", "checkpoint_bw", "checkpoint_time",
    "optimal_checkpoint_interval", "checkpoint_overhead_fraction",
    "lost_work_fraction", "recovery_overhead_fraction",
    "availability_from_reliability",
    "eq_node_failure_rate", "eq_rack_infra_failure_rate",
    "eq_cluster_failure_rate", "eq_cluster_mtbf",
    "eq_gpus_per_fabric_domain", "eq_checkpoint_time",
    "eq_optimal_checkpoint_interval", "eq_checkpoint_overhead_fraction",
    "eq_lost_work_fraction", "eq_recovery_overhead_fraction",
    "eq_availability_from_reliability",
    "CLUSTER_RELIABILITY_VARIABLES", "CLUSTER_RELIABILITY_EQUATIONS",
]
