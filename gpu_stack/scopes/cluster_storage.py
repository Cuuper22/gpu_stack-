"""
scopes/cluster_storage.py
=========================

Storage path and data-ingest limits.

Training throughput depends on feeding samples into the pipeline as fast as
the devices can consume them. This file models the bytes-per-sample footprint,
the efficiency factor that turns raw local-storage bandwidth into sustained
loader bandwidth, and the stall fraction implied when demand outruns supply.
"""

import sympy as sp

from ..core import eq, var

from .cluster_site import cluster_local_ssd_bw


dataset_bytes_per_sample = var(
    "cluster.data.bytes_per_sample", "B_sample", "byte/sample",
    "Average bytes read from storage per training sample after sharding and preprocessing.",
    scope="cluster",
)
storage_to_loader_efficiency = var(
    "cluster.data.storage_to_loader_eff", "eta_loader", "dimensionless",
    "Efficiency factor from raw storage bandwidth to sustained bytes delivered into the training input pipeline.",
    scope="cluster",
)
storage_stream_bw_effective = var(
    "cluster.data.storage_stream_bw_effective", "BW_stream_eff", "byte/s",
    "Sustained storage bandwidth available to the data-loading pipeline.",
    scope="cluster",
)
max_sample_rate_from_storage = var(
    "cluster.data.max_sample_rate_from_storage", "R_sample_max", "samples/s",
    "Maximum sustained training-sample rate permitted by the storage path.",
    scope="cluster",
)
required_sample_rate = var(
    "cluster.data.required_sample_rate", "R_sample_req", "samples/s",
    "Training-sample rate demanded by the workload.",
    scope="cluster",
)
data_pipeline_utilization = var(
    "cluster.data.pipeline_utilization", "u_loader", "dimensionless",
    "Fraction of storage-path sample-rate capacity consumed by the workload.",
    scope="cluster",
)
data_stall_fraction_est = var(
    "cluster.data.stall_fraction_est", "f_stall_data", "dimensionless",
    "Coarse lower bound on stall fraction when demanded sample rate exceeds storage-path capacity.",
    scope="cluster",
)


eq_storage_stream_bw_effective = eq(
    "cluster.eq.storage_stream_bw_effective",
    storage_stream_bw_effective.symbol,
    storage_to_loader_efficiency.symbol * cluster_local_ssd_bw.symbol,
    "Effective storage-path bandwidth equals local-storage bandwidth times the end-to-end input-pipeline efficiency.",
)

eq_max_sample_rate_from_storage = eq(
    "cluster.eq.max_sample_rate_from_storage",
    max_sample_rate_from_storage.symbol,
    storage_stream_bw_effective.symbol / dataset_bytes_per_sample.symbol,
    "Maximum sample rate equals sustained storage-path bandwidth divided by bytes consumed per sample.",
)

eq_data_pipeline_utilization = eq(
    "cluster.eq.data_pipeline_utilization",
    data_pipeline_utilization.symbol,
    required_sample_rate.symbol / max_sample_rate_from_storage.symbol,
    "Data-pipeline utilization equals required sample rate divided by maximum sample rate from storage.",
)

eq_data_stall_fraction_est = eq(
    "cluster.eq.data_stall_fraction_est",
    data_stall_fraction_est.symbol,
    sp.Max(0, 1 - max_sample_rate_from_storage.symbol / required_sample_rate.symbol),
    "A coarse lower bound on data stalls is zero when storage keeps up, otherwise the fractional shortfall in sample rate.",
)


CLUSTER_STORAGE_VARIABLES = [
    dataset_bytes_per_sample,
    storage_to_loader_efficiency,
    storage_stream_bw_effective,
    max_sample_rate_from_storage,
    required_sample_rate,
    data_pipeline_utilization,
    data_stall_fraction_est,
]

CLUSTER_STORAGE_EQUATIONS = [
    eq_storage_stream_bw_effective,
    eq_max_sample_rate_from_storage,
    eq_data_pipeline_utilization,
    eq_data_stall_fraction_est,
]


__all__ = [
    "dataset_bytes_per_sample", "storage_to_loader_efficiency",
    "storage_stream_bw_effective", "max_sample_rate_from_storage",
    "required_sample_rate", "data_pipeline_utilization",
    "data_stall_fraction_est",
    "eq_storage_stream_bw_effective", "eq_max_sample_rate_from_storage",
    "eq_data_pipeline_utilization", "eq_data_stall_fraction_est",
    "CLUSTER_STORAGE_VARIABLES", "CLUSTER_STORAGE_EQUATIONS",
]
