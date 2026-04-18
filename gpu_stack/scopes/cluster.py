"""
scopes/cluster.py
=================

Aggregation from a single GPU up to a hyperscaler running multiple data
centers.

The original file stopped at simple counts and left almost everything that
actually matters in cluster planning as anonymous placeholders. This version
fills in the missing machinery:

* node composition, local storage, and node-level power,
* rack and site aggregates for compute, memory, storage, and NIC bandwidth,
* data-ingest limits from the storage path,
* scheduler and provisioning overhead,
* reliability, failure domains, and checkpoint optimization,
* cross-site scale-across bandwidth and latency.

Cluster scope still stays above chip-level thermal and dollar models. It
aggregates hardware and operational structure, then lets `thermal.py` and
`economics.py` attach facility power and money later.
"""

import sympy as sp
from ..core import System, eq, var

from .gpu import (
    nic_bw_per_gpu_effective,
    p_gpu_total,
    peak_flops_gpu,
    peak_flops_gpu_power_limited,
)
from .interconnect import bw_nvlink_rack, bw_scale_out_effective, n_gpus_per_rack
from .memory_subsystem import hbm_bw_effective, hbm_effective_capacity


sys_cluster = System(
    name="cluster",
    scope="cluster",
    description="Node, rack, site, and hyperscaler aggregation with reliability and storage-path detail.",
)


# ---------------------------------------------------------------------------
# Node (single server chassis)
# ---------------------------------------------------------------------------

n_gpus_per_node = var(
    "cluster.node.n_gpus", "N_G_node", "GPUs",
    "GPUs per server node.",
    scope="cluster",
    integer=True,
)
n_cpus_per_node = var(
    "cluster.node.n_cpus", "N_C_node", "CPUs",
    "Host CPUs per server node.",
    scope="cluster",
    integer=True,
)
ram_per_node = var(
    "cluster.node.ram", "B_RAM_node", "byte",
    "CPU-side DRAM capacity per node.",
    scope="cluster",
)
node_dram_bw = var(
    "cluster.node.ram_bw", "BW_RAM_node", "byte/s",
    "Aggregate CPU-side DRAM bandwidth per node.",
    scope="cluster",
)
node_local_ssd_count = var(
    "cluster.node.local_ssd.count", "N_SSD_node", "drives",
    "Number of local SSDs or NVMe drives in one node.",
    scope="cluster",
    integer=True,
)
node_local_ssd_capacity_per_drive = var(
    "cluster.node.local_ssd.capacity_per_drive", "B_SSD_drv", "byte",
    "Usable capacity of one local SSD or NVMe drive.",
    scope="cluster",
)
node_local_ssd_bw_per_drive = var(
    "cluster.node.local_ssd.bw_per_drive", "BW_SSD_drv", "byte/s",
    "Sustained streaming bandwidth of one local SSD or NVMe drive.",
    scope="cluster",
)
cpu_power_node = var(
    "cluster.node.cpu_power", "P_cpu_node", "W",
    "CPU package power per node.",
    scope="cluster",
)
ram_power_node = var(
    "cluster.node.ram_power", "P_ram_node", "W",
    "CPU-side DRAM power per node.",
    scope="cluster",
)
nic_power_node = var(
    "cluster.node.nic_power", "P_nic_node", "W",
    "NIC and retimer power per node.",
    scope="cluster",
)
storage_power_node = var(
    "cluster.node.storage_power", "P_stor_node", "W",
    "Local storage power per node.",
    scope="cluster",
)
misc_power_node = var(
    "cluster.node.misc_power", "P_misc_node", "W",
    "Remaining node-level power, for fans, BMCs, and motherboard losses.",
    scope="cluster",
)
node_peak_flops = var(
    "cluster.node.peak_flops", "F_node", "FLOP/s",
    "Aggregate peak FLOPs of one node.",
    scope="cluster",
)
node_peak_flops_power_limited = var(
    "cluster.node.peak_flops_power_limited", "F_node_pl", "FLOP/s",
    "Power-limited peak FLOPs of one node.",
    scope="cluster",
)
node_hbm_capacity = var(
    "cluster.node.hbm_capacity", "B_HBM_node", "byte",
    "Aggregate usable HBM capacity in one node.",
    scope="cluster",
)
node_hbm_bw = var(
    "cluster.node.hbm_bw", "BW_HBM_node", "byte/s",
    "Aggregate effective HBM bandwidth in one node.",
    scope="cluster",
)
node_local_ssd_capacity = var(
    "cluster.node.local_ssd.capacity", "B_SSD_node", "byte",
    "Aggregate local SSD capacity in one node.",
    scope="cluster",
)
node_local_ssd_bw = var(
    "cluster.node.local_ssd.bw", "BW_SSD_node", "byte/s",
    "Aggregate local SSD bandwidth in one node.",
    scope="cluster",
)
node_nic_bw = var(
    "cluster.node.nic_bw", "BW_NIC_node", "byte/s",
    "Scale-out NIC bandwidth per node.",
    scope="cluster",
)
node_power = var(
    "cluster.node.power", "P_node", "W",
    "Total power draw of one node.",
    scope="cluster",
)


eq_node_peak_flops = eq(
    "cluster.eq.node_peak_flops",
    node_peak_flops.symbol,
    n_gpus_per_node.symbol * peak_flops_gpu.symbol,
    "Node peak FLOPs equal GPUs per node times per-GPU peak FLOPs.",
)

eq_node_peak_flops_power_limited = eq(
    "cluster.eq.node_peak_flops_power_limited",
    node_peak_flops_power_limited.symbol,
    n_gpus_per_node.symbol * peak_flops_gpu_power_limited.symbol,
    "Node power-limited peak FLOPs equal GPUs per node times per-GPU power-limited peak FLOPs.",
)

eq_node_hbm_capacity = eq(
    "cluster.eq.node_hbm_capacity",
    node_hbm_capacity.symbol,
    n_gpus_per_node.symbol * hbm_effective_capacity.symbol,
    "Node HBM capacity aggregates usable per-GPU HBM across the node.",
)

eq_node_hbm_bw = eq(
    "cluster.eq.node_hbm_bw",
    node_hbm_bw.symbol,
    n_gpus_per_node.symbol * hbm_bw_effective.symbol,
    "Node HBM bandwidth aggregates effective per-GPU HBM bandwidth across the node.",
)

eq_node_local_ssd_capacity = eq(
    "cluster.eq.node_local_ssd_capacity",
    node_local_ssd_capacity.symbol,
    node_local_ssd_count.symbol * node_local_ssd_capacity_per_drive.symbol,
    "Node local storage capacity equals drive count times per-drive capacity.",
)

eq_node_local_ssd_bw = eq(
    "cluster.eq.node_local_ssd_bw",
    node_local_ssd_bw.symbol,
    node_local_ssd_count.symbol * node_local_ssd_bw_per_drive.symbol,
    "Node local storage bandwidth equals drive count times per-drive streaming bandwidth.",
)

eq_node_nic_bw = eq(
    "cluster.eq.node_nic_bw",
    node_nic_bw.symbol,
    n_gpus_per_node.symbol * nic_bw_per_gpu_effective.symbol,
    "Node NIC bandwidth aggregates effective per-GPU scale-out bandwidth.",
)

eq_node_power = eq(
    "cluster.eq.node_power",
    node_power.symbol,
    n_gpus_per_node.symbol * p_gpu_total.symbol
    + cpu_power_node.symbol
    + ram_power_node.symbol
    + nic_power_node.symbol
    + storage_power_node.symbol
    + misc_power_node.symbol,
    "Node power equals GPU package power plus CPU, DRAM, NIC, storage, and chassis overhead.",
)


# ---------------------------------------------------------------------------
# Rack aggregation
# ---------------------------------------------------------------------------

n_nodes_per_rack = var(
    "cluster.rack.n_nodes", "N_node_rack", "nodes/rack",
    "Compute nodes per rack.",
    scope="cluster",
    integer=True,
)
rack_peak_flops = var(
    "cluster.rack.peak_flops", "F_rack", "FLOP/s",
    "Aggregate peak FLOPs in one rack.",
    scope="cluster",
)
rack_peak_flops_power_limited = var(
    "cluster.rack.peak_flops_power_limited", "F_rack_pl", "FLOP/s",
    "Aggregate power-limited peak FLOPs in one rack.",
    scope="cluster",
)
rack_hbm_capacity = var(
    "cluster.rack.hbm_capacity", "B_HBM_rack", "byte",
    "Aggregate usable HBM capacity in one rack.",
    scope="cluster",
)
rack_hbm_bw = var(
    "cluster.rack.hbm_bw", "BW_HBM_rack", "byte/s",
    "Aggregate effective HBM bandwidth in one rack.",
    scope="cluster",
)
rack_local_ssd_capacity = var(
    "cluster.rack.local_ssd.capacity", "B_SSD_rack", "byte",
    "Aggregate local SSD capacity in one rack.",
    scope="cluster",
)
rack_local_ssd_bw = var(
    "cluster.rack.local_ssd.bw", "BW_SSD_rack", "byte/s",
    "Aggregate local SSD bandwidth in one rack.",
    scope="cluster",
)
rack_nic_bw = var(
    "cluster.rack.nic_bw", "BW_NIC_rack", "byte/s",
    "Aggregate scale-out NIC bandwidth in one rack.",
    scope="cluster",
)
rack_power = var(
    "cluster.rack.power", "P_rack_W", "W",
    "Total IT power drawn by one rack.",
    scope="cluster",
)
rack_gpus_per_power_domain = var(
    "cluster.rack.gpus_per_power_domain", "N_GPU_pd", "GPUs",
    "GPUs that can disappear together when a shared power domain fails.",
    scope="cluster",
    integer=True,
)
nodes_per_power_domain = var(
    "cluster.rel.nodes_per_power_domain", "N_node_pd", "nodes",
    "Nodes attached to one shared rack-level or row-level power domain.",
    scope="cluster",
    integer=True,
)
rack_flops_per_intra_byte = var(
    "cluster.rack.flops_per_intra_byte", "AI_rack_intra", "FLOP/byte",
    "Rack-level compute to intra-rack fabric balance using NVLink-rack bandwidth.",
    scope="cluster",
)


eq_rack_gpu_count = eq(
    "cluster.eq.rack_gpu_count",
    n_gpus_per_rack.symbol,
    n_nodes_per_rack.symbol * n_gpus_per_node.symbol,
    "GPUs per rack equal nodes per rack times GPUs per node.",
)

eq_rack_peak_flops = eq(
    "cluster.eq.rack_peak_flops",
    rack_peak_flops.symbol,
    n_nodes_per_rack.symbol * node_peak_flops.symbol,
    "Rack peak FLOPs equal nodes per rack times node peak FLOPs.",
)

eq_rack_peak_flops_power_limited = eq(
    "cluster.eq.rack_peak_flops_power_limited",
    rack_peak_flops_power_limited.symbol,
    n_nodes_per_rack.symbol * node_peak_flops_power_limited.symbol,
    "Rack power-limited peak FLOPs equal nodes per rack times node power-limited peak FLOPs.",
)

eq_rack_hbm_capacity = eq(
    "cluster.eq.rack_hbm_capacity",
    rack_hbm_capacity.symbol,
    n_nodes_per_rack.symbol * node_hbm_capacity.symbol,
    "Rack HBM capacity equals nodes per rack times node HBM capacity.",
)

eq_rack_hbm_bw = eq(
    "cluster.eq.rack_hbm_bw",
    rack_hbm_bw.symbol,
    n_nodes_per_rack.symbol * node_hbm_bw.symbol,
    "Rack HBM bandwidth equals nodes per rack times node HBM bandwidth.",
)

eq_rack_local_ssd_capacity = eq(
    "cluster.eq.rack_local_ssd_capacity",
    rack_local_ssd_capacity.symbol,
    n_nodes_per_rack.symbol * node_local_ssd_capacity.symbol,
    "Rack local SSD capacity equals nodes per rack times node local storage capacity.",
)

eq_rack_local_ssd_bw = eq(
    "cluster.eq.rack_local_ssd_bw",
    rack_local_ssd_bw.symbol,
    n_nodes_per_rack.symbol * node_local_ssd_bw.symbol,
    "Rack local SSD bandwidth equals nodes per rack times node local storage bandwidth.",
)

eq_rack_nic_bw = eq(
    "cluster.eq.rack_nic_bw",
    rack_nic_bw.symbol,
    n_nodes_per_rack.symbol * node_nic_bw.symbol,
    "Rack NIC bandwidth equals nodes per rack times node NIC bandwidth.",
)

eq_rack_power = eq(
    "cluster.eq.rack_power",
    rack_power.symbol,
    n_nodes_per_rack.symbol * node_power.symbol,
    "Rack IT power equals nodes per rack times node power.",
)

eq_rack_gpus_per_power_domain = eq(
    "cluster.eq.rack_gpus_per_power_domain",
    rack_gpus_per_power_domain.symbol,
    n_gpus_per_node.symbol * nodes_per_power_domain.symbol,
    "GPUs lost in one shared rack power-domain failure equal GPUs per node times nodes served by that power domain.",
)

eq_rack_flops_per_intra_byte = eq(
    "cluster.eq.rack_flops_per_intra_byte",
    rack_flops_per_intra_byte.symbol,
    rack_peak_flops_power_limited.symbol / bw_nvlink_rack.symbol,
    "Rack compute to NVLink-rack balance equals rack power-limited FLOPs divided by aggregate intra-rack fabric bandwidth.",
)


# ---------------------------------------------------------------------------
# Site aggregation
# ---------------------------------------------------------------------------

n_racks_cluster = var(
    "cluster.site.n_racks", "N_rack", "racks",
    "Number of racks in one site.",
    scope="cluster",
    integer=True,
)
cluster_n_nodes = var(
    "cluster.site.n_nodes", "N_node_site", "nodes",
    "Total nodes in one site.",
    scope="cluster",
    integer=True,
)
cluster_n_gpus = var(
    "cluster.site.n_gpus", "N_GPU_clust", "GPUs",
    "Total GPUs in one site.",
    scope="cluster",
    integer=True,
)
cluster_peak_flops = var(
    "cluster.site.peak_flops", "F_clust", "FLOP/s",
    "Aggregate peak FLOPs of one site.",
    scope="cluster",
)
cluster_peak_flops_power_limited = var(
    "cluster.site.peak_flops_power_limited", "F_clust_pl", "FLOP/s",
    "Aggregate power-limited peak FLOPs of one site.",
    scope="cluster",
)
cluster_power_it = var(
    "cluster.site.power_it", "P_IT", "W",
    "Total IT power of one site, before facility overhead.",
    scope="cluster",
)
cluster_hbm_capacity = var(
    "cluster.site.hbm_capacity", "B_HBM_site", "byte",
    "Aggregate usable HBM capacity of one site.",
    scope="cluster",
)
cluster_hbm_bw = var(
    "cluster.site.hbm_bw", "BW_HBM_site", "byte/s",
    "Aggregate effective HBM bandwidth of one site.",
    scope="cluster",
)
cluster_local_ssd_capacity = var(
    "cluster.site.local_ssd.capacity", "B_SSD_site", "byte",
    "Aggregate local SSD capacity of one site.",
    scope="cluster",
)
cluster_local_ssd_bw = var(
    "cluster.site.local_ssd.bw", "BW_SSD_site", "byte/s",
    "Aggregate local SSD bandwidth of one site.",
    scope="cluster",
)
cluster_nic_bw = var(
    "cluster.site.nic_bw", "BW_NIC_site", "byte/s",
    "Aggregate scale-out NIC bandwidth of one site.",
    scope="cluster",
)
site_power_overhead_factor_est = var(
    "cluster.site.power_overhead_factor_est", "k_site_pow", "dimensionless",
    "Planning-stage multiplier from IT power to total site power before the detailed facility model is attached.",
    scope="cluster",
)
cluster_total_power_est = var(
    "cluster.site.power_total_est", "P_site_est", "W",
    "Estimated total site electrical power from a simple planning multiplier.",
    scope="cluster",
)
site_flops_per_scaleout_byte = var(
    "cluster.site.flops_per_scaleout_byte", "AI_site_fabric", "FLOP/byte",
    "Site-level compute to scale-out fabric balance.",
    scope="cluster",
)


eq_cluster_n_nodes = eq(
    "cluster.eq.site_n_nodes",
    cluster_n_nodes.symbol,
    n_racks_cluster.symbol * n_nodes_per_rack.symbol,
    "Site nodes equal racks times nodes per rack.",
)

eq_cluster_n_gpus = eq(
    "cluster.eq.site_n_gpus",
    cluster_n_gpus.symbol,
    n_racks_cluster.symbol * n_gpus_per_rack.symbol,
    "Site GPUs equal racks times GPUs per rack.",
)

eq_cluster_peak = eq(
    "cluster.eq.site_peak_flops",
    cluster_peak_flops.symbol,
    n_racks_cluster.symbol * rack_peak_flops.symbol,
    "Site peak FLOPs equal racks times rack peak FLOPs.",
)

eq_cluster_peak_power_limited = eq(
    "cluster.eq.site_peak_flops_power_limited",
    cluster_peak_flops_power_limited.symbol,
    n_racks_cluster.symbol * rack_peak_flops_power_limited.symbol,
    "Site power-limited peak FLOPs equal racks times rack power-limited peak FLOPs.",
)

eq_cluster_power_it = eq(
    "cluster.eq.site_power_it",
    cluster_power_it.symbol,
    n_racks_cluster.symbol * rack_power.symbol,
    "Site IT power equals racks times rack IT power.",
)

eq_cluster_hbm_capacity = eq(
    "cluster.eq.site_hbm_capacity",
    cluster_hbm_capacity.symbol,
    n_racks_cluster.symbol * rack_hbm_capacity.symbol,
    "Site HBM capacity equals racks times rack HBM capacity.",
)

eq_cluster_hbm_bw = eq(
    "cluster.eq.site_hbm_bw",
    cluster_hbm_bw.symbol,
    n_racks_cluster.symbol * rack_hbm_bw.symbol,
    "Site HBM bandwidth equals racks times rack HBM bandwidth.",
)

eq_cluster_local_ssd_capacity = eq(
    "cluster.eq.site_local_ssd_capacity",
    cluster_local_ssd_capacity.symbol,
    n_racks_cluster.symbol * rack_local_ssd_capacity.symbol,
    "Site local SSD capacity equals racks times rack local SSD capacity.",
)

eq_cluster_local_ssd_bw = eq(
    "cluster.eq.site_local_ssd_bw",
    cluster_local_ssd_bw.symbol,
    n_racks_cluster.symbol * rack_local_ssd_bw.symbol,
    "Site local SSD bandwidth equals racks times rack local SSD bandwidth.",
)

eq_cluster_nic_bw = eq(
    "cluster.eq.site_nic_bw",
    cluster_nic_bw.symbol,
    n_racks_cluster.symbol * rack_nic_bw.symbol,
    "Site NIC bandwidth equals racks times rack NIC bandwidth.",
)

eq_cluster_total_power_est = eq(
    "cluster.eq.site_total_power_est",
    cluster_total_power_est.symbol,
    site_power_overhead_factor_est.symbol * cluster_power_it.symbol,
    "Planning-stage total site power equals IT power times a coarse overhead multiplier.",
)

eq_site_flops_per_scaleout_byte = eq(
    "cluster.eq.site_flops_per_scaleout_byte",
    site_flops_per_scaleout_byte.symbol,
    cluster_peak_flops_power_limited.symbol / (cluster_n_gpus.symbol * bw_scale_out_effective.symbol),
    "Site compute to scale-out balance equals site power-limited FLOPs divided by aggregate effective scale-out bandwidth.",
)


# ---------------------------------------------------------------------------
# Storage and data-ingest path
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Scheduler and provisioning overhead
# ---------------------------------------------------------------------------

scheduler_queue_wait = var(
    "cluster.sched.queue_wait", "T_queue", "s",
    "Time a job spends waiting in the scheduler queue.",
    scope="cluster",
)
scheduler_allocation_time = var(
    "cluster.sched.allocation_time", "T_alloc", "s",
    "Control-plane time to allocate nodes, wire up containers, and stage the job.",
    scope="cluster",
)
provisioning_time = var(
    "cluster.sched.provisioning_time", "T_prov", "s",
    "Time spent on image pull, filesystem mounts, and runtime startup.",
    scope="cluster",
)
job_start_delay = var(
    "cluster.sched.job_start_delay", "T_start_delay", "s",
    "End-to-end delay between job submission and first training step.",
    scope="cluster",
)


eq_job_start_delay = eq(
    "cluster.eq.job_start_delay",
    job_start_delay.symbol,
    scheduler_queue_wait.symbol + scheduler_allocation_time.symbol + provisioning_time.symbol,
    "Job start delay equals queue wait plus scheduler allocation plus provisioning time.",
)


# ---------------------------------------------------------------------------
# Reliability and checkpointing
# ---------------------------------------------------------------------------

racks_per_fabric_domain = var(
    "cluster.rel.racks_per_fabric_domain", "N_rack_fd", "racks",
    "Racks that fail together under one fabric-domain or aggregation-switch outage.",
    scope="cluster",
    integer=True,
)
node_mtbf = var(
    "cluster.rel.node_mtbf", "MTBF_node", "s",
    "Mean time between node failures.",
    scope="cluster",
)
tor_switch_mtbf = var(
    "cluster.rel.tor_switch_mtbf", "MTBF_tor", "s",
    "Mean time between top-of-rack switch failures.",
    scope="cluster",
)
rack_power_domain_mtbf = var(
    "cluster.rel.rack_power_domain_mtbf", "MTBF_rack_pwr", "s",
    "Mean time between rack-level power-domain failures.",
    scope="cluster",
)
site_fabric_mtbf = var(
    "cluster.rel.site_fabric_mtbf", "MTBF_site_fab", "s",
    "Mean time between site-level fabric or control-plane failures that interrupt many racks.",
    scope="cluster",
)
node_failure_rate = var(
    "cluster.rel.node_failure_rate", "lambda_node", "1/s",
    "Failure hazard rate of one node under an exponential-failure approximation.",
    scope="cluster",
)
rack_infra_failure_rate = var(
    "cluster.rel.rack_infra_failure_rate", "lambda_rack_inf", "1/s",
    "Failure hazard rate from rack-level shared infrastructure.",
    scope="cluster",
)
cluster_failure_rate = var(
    "cluster.rel.site_failure_rate", "lambda_site", "1/s",
    "Aggregate interruption hazard rate of the site from node, rack, and site-domain failures.",
    scope="cluster",
)
cluster_mtbf = var(
    "cluster.rel.site_mtbf", "MTBF_site", "s",
    "Mean time between site-level job interruptions.",
    scope="cluster",
)
gpus_per_fabric_domain = var(
    "cluster.rel.gpus_per_fabric_domain", "N_GPU_fd", "GPUs",
    "GPUs that can disappear together in one shared fabric-domain failure.",
    scope="cluster",
    integer=True,
)
mean_time_to_recover = var(
    "cluster.rel.mttr", "MTTR_site", "s",
    "Mean time to recover a failed distributed training job after interruption.",
    scope="cluster",
)
checkpoint_size = var(
    "cluster.rel.checkpoint_size", "B_ckpt", "byte",
    "Bytes written by one checkpoint, including model, optimizer, and metadata.",
    scope="cluster",
)
checkpoint_bw = var(
    "cluster.rel.checkpoint_bw", "BW_ckpt", "byte/s",
    "Sustained checkpoint write bandwidth.",
    scope="cluster",
)
checkpoint_time = var(
    "cluster.rel.checkpoint_time", "T_ckpt", "s",
    "Time to write one checkpoint.",
    scope="cluster",
)
optimal_checkpoint_interval = var(
    "cluster.rel.optimal_checkpoint_interval", "T_ckpt_opt", "s",
    "Young-style optimal checkpoint interval that trades checkpoint cost against expected lost work.",
    scope="cluster",
)
checkpoint_overhead_fraction = var(
    "cluster.rel.checkpoint_overhead_fraction", "f_ckpt", "dimensionless",
    "Fractional time overhead from taking checkpoints at the optimal interval.",
    scope="cluster",
)
lost_work_fraction = var(
    "cluster.rel.lost_work_fraction", "f_lost", "dimensionless",
    "Expected fractional loss from work discarded between failures.",
    scope="cluster",
)
recovery_overhead_fraction = var(
    "cluster.rel.recovery_overhead_fraction", "f_rec", "dimensionless",
    "Fractional wall-clock overhead from restore and restart work after failures.",
    scope="cluster",
)
availability_from_reliability = var(
    "cluster.rel.availability_est", "A_rel", "dimensionless",
    "Reliability-only availability estimate after checkpoint, lost-work, and recovery overheads.",
    scope="cluster",
)


eq_node_failure_rate = eq(
    "cluster.eq.node_failure_rate",
    node_failure_rate.symbol,
    1 / node_mtbf.symbol,
    "Node failure hazard rate is the reciprocal of node MTBF under an exponential-failure approximation.",
)

eq_rack_infra_failure_rate = eq(
    "cluster.eq.rack_infra_failure_rate",
    rack_infra_failure_rate.symbol,
    1 / tor_switch_mtbf.symbol + 1 / rack_power_domain_mtbf.symbol,
    "Rack infrastructure failure rate sums top-of-rack switch and shared power-domain hazards.",
)

eq_cluster_failure_rate = eq(
    "cluster.eq.site_failure_rate",
    cluster_failure_rate.symbol,
    cluster_n_nodes.symbol * node_failure_rate.symbol
    + n_racks_cluster.symbol * rack_infra_failure_rate.symbol
    + 1 / site_fabric_mtbf.symbol,
    "Site interruption rate is the sum of node hazards, rack shared-infrastructure hazards, and one site-domain hazard term.",
)

eq_cluster_mtbf = eq(
    "cluster.eq.site_mtbf",
    cluster_mtbf.symbol,
    1 / cluster_failure_rate.symbol,
    "Site MTBF is the reciprocal of the aggregate interruption hazard rate.",
)

eq_gpus_per_fabric_domain = eq(
    "cluster.eq.gpus_per_fabric_domain",
    gpus_per_fabric_domain.symbol,
    racks_per_fabric_domain.symbol * n_gpus_per_rack.symbol,
    "GPUs per fabric domain equal racks covered by that domain times GPUs per rack.",
)

eq_checkpoint_time = eq(
    "cluster.eq.checkpoint_time",
    checkpoint_time.symbol,
    checkpoint_size.symbol / checkpoint_bw.symbol,
    "Checkpoint time equals checkpoint bytes divided by sustained checkpoint write bandwidth.",
)

eq_optimal_checkpoint_interval = eq(
    "cluster.eq.optimal_checkpoint_interval",
    optimal_checkpoint_interval.symbol,
    sp.sqrt(2 * checkpoint_time.symbol * cluster_mtbf.symbol),
    "Young's classic checkpoint interval is the square root of twice the product of checkpoint time and MTBF.",
)

eq_checkpoint_overhead_fraction = eq(
    "cluster.eq.checkpoint_overhead_fraction",
    checkpoint_overhead_fraction.symbol,
    checkpoint_time.symbol / optimal_checkpoint_interval.symbol,
    "Checkpoint overhead fraction equals checkpoint time divided by checkpoint interval.",
)

eq_lost_work_fraction = eq(
    "cluster.eq.lost_work_fraction",
    lost_work_fraction.symbol,
    optimal_checkpoint_interval.symbol / (2 * cluster_mtbf.symbol),
    "Expected lost-work fraction under periodic checkpointing is half the interval divided by MTBF.",
)

eq_recovery_overhead_fraction = eq(
    "cluster.eq.recovery_overhead_fraction",
    recovery_overhead_fraction.symbol,
    mean_time_to_recover.symbol / cluster_mtbf.symbol,
    "Recovery overhead fraction equals mean time to recover divided by site MTBF.",
)

eq_availability_from_reliability = eq(
    "cluster.eq.availability_from_reliability",
    availability_from_reliability.symbol,
    1 - checkpoint_overhead_fraction.symbol - lost_work_fraction.symbol - recovery_overhead_fraction.symbol,
    "A first-order reliability availability estimate subtracts checkpoint, lost-work, and recovery overhead fractions from one.",
)


# ---------------------------------------------------------------------------
# Hyperscaler and scale-across links
# ---------------------------------------------------------------------------

n_sites_hs = var(
    "cluster.hs.n_sites", "N_DC", "sites",
    "Number of sites operated by the hyperscaler.",
    scope="cluster",
    integer=True,
)
hs_n_gpus = var(
    "cluster.hs.n_gpus", "N_GPU_hs", "GPUs",
    "Total GPUs across all sites.",
    scope="cluster",
    integer=True,
)
hs_peak_flops = var(
    "cluster.hs.peak_flops", "F_hs", "FLOP/s",
    "Aggregate peak FLOPs across all sites.",
    scope="cluster",
)
hs_total_power = var(
    "cluster.hs.power_total", "P_hs_tot", "W",
    "Estimated total electrical load across all sites.",
    scope="cluster",
)
hs_hbm_capacity = var(
    "cluster.hs.hbm_capacity", "B_HBM_hs", "byte",
    "Aggregate usable HBM capacity across all sites.",
    scope="cluster",
)
hs_local_ssd_capacity = var(
    "cluster.hs.local_ssd.capacity", "B_SSD_hs", "byte",
    "Aggregate local SSD capacity across all sites.",
    scope="cluster",
)
wan_links_per_site = var(
    "cluster.hs.scale_across.links_per_site", "N_WAN_site", "links/site",
    "Number of long-haul or inter-DC links attached to one site for scale-across training or checkpoint replication.",
    scope="cluster",
    integer=True,
)
bw_wan_link = var(
    "cluster.hs.scale_across.bw_per_link", "BW_WAN_link", "byte/s",
    "Payload bandwidth of one inter-site link.",
    scope="cluster",
)
eta_scale_across = var(
    "cluster.hs.scale_across.efficiency", "eta_SA", "dimensionless",
    "Protocol and utilization efficiency of the inter-site transport path.",
    scope="cluster",
)
bw_scale_across_site = var(
    "cluster.hs.scale_across.bw_per_site", "BW_SA_site", "byte/s",
    "Aggregate effective inter-site bandwidth available to one site.",
    scope="cluster",
)
bw_scale_across = var(
    "cluster.hs.scale_across_bw", "BW_SA", "byte/s",
    "Effective inter-site bandwidth per GPU when a whole site participates in scale-across training.",
    scope="cluster",
)
lat_scale_across = var(
    "cluster.hs.scale_across_latency", "L_SA", "s",
    "One-way inter-site latency for scale-across communication.",
    scope="cluster",
)
scale_across_msg_size = var(
    "cluster.hs.scale_across_msg_size", "B_SA_msg", "byte",
    "Representative message size moved across sites.",
    scope="cluster",
)
scale_across_transfer_time = var(
    "cluster.hs.scale_across_transfer_time", "T_SA_msg", "s",
    "Transfer time for one representative inter-site message.",
    scope="cluster",
)


eq_hs_n_gpus = eq(
    "cluster.eq.hs_n_gpus",
    hs_n_gpus.symbol,
    n_sites_hs.symbol * cluster_n_gpus.symbol,
    "Hyperscaler GPUs equal sites times GPUs per site under a uniform-site planning assumption.",
)

eq_hs_peak = eq(
    "cluster.eq.hs_peak_flops",
    hs_peak_flops.symbol,
    n_sites_hs.symbol * cluster_peak_flops.symbol,
    "Hyperscaler peak FLOPs equal sites times site peak FLOPs under a uniform-site planning assumption.",
)

eq_hs_total_power = eq(
    "cluster.eq.hs_total_power",
    hs_total_power.symbol,
    n_sites_hs.symbol * cluster_total_power_est.symbol,
    "Hyperscaler total electrical load is estimated as sites times estimated site power.",
)

eq_hs_hbm_capacity = eq(
    "cluster.eq.hs_hbm_capacity",
    hs_hbm_capacity.symbol,
    n_sites_hs.symbol * cluster_hbm_capacity.symbol,
    "Hyperscaler HBM capacity equals sites times site HBM capacity.",
)

eq_hs_local_ssd_capacity = eq(
    "cluster.eq.hs_local_ssd_capacity",
    hs_local_ssd_capacity.symbol,
    n_sites_hs.symbol * cluster_local_ssd_capacity.symbol,
    "Hyperscaler local SSD capacity equals sites times site local SSD capacity.",
)

eq_bw_scale_across_site = eq(
    "cluster.eq.scale_across_bw_per_site",
    bw_scale_across_site.symbol,
    wan_links_per_site.symbol * bw_wan_link.symbol * eta_scale_across.symbol,
    "Per-site scale-across bandwidth equals link count times per-link bandwidth times transport efficiency.",
)

eq_bw_scale_across = eq(
    "cluster.eq.scale_across_bw_per_gpu",
    bw_scale_across.symbol,
    bw_scale_across_site.symbol / cluster_n_gpus.symbol,
    "Per-GPU inter-site bandwidth equals per-site WAN bandwidth divided by GPUs sharing it.",
)

eq_scale_across_transfer_time = eq(
    "cluster.eq.scale_across_transfer_time",
    scale_across_transfer_time.symbol,
    lat_scale_across.symbol + scale_across_msg_size.symbol / bw_scale_across_site.symbol,
    "A first-order inter-site transfer time equals path latency plus bytes divided by sustained per-site WAN bandwidth.",
)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

sys_cluster.add_all([
    # Node
    n_gpus_per_node,
    n_cpus_per_node,
    ram_per_node,
    node_dram_bw,
    node_local_ssd_count,
    node_local_ssd_capacity_per_drive,
    node_local_ssd_bw_per_drive,
    cpu_power_node,
    ram_power_node,
    nic_power_node,
    storage_power_node,
    misc_power_node,
    node_peak_flops,
    node_peak_flops_power_limited,
    node_hbm_capacity,
    node_hbm_bw,
    node_local_ssd_capacity,
    node_local_ssd_bw,
    node_nic_bw,
    node_power,

    # Rack
    n_nodes_per_rack,
    rack_peak_flops,
    rack_peak_flops_power_limited,
    rack_hbm_capacity,
    rack_hbm_bw,
    rack_local_ssd_capacity,
    rack_local_ssd_bw,
    rack_nic_bw,
    rack_power,
    rack_gpus_per_power_domain,
    rack_flops_per_intra_byte,

    # Site
    n_racks_cluster,
    cluster_n_nodes,
    cluster_n_gpus,
    cluster_peak_flops,
    cluster_peak_flops_power_limited,
    cluster_power_it,
    cluster_hbm_capacity,
    cluster_hbm_bw,
    cluster_local_ssd_capacity,
    cluster_local_ssd_bw,
    cluster_nic_bw,
    site_power_overhead_factor_est,
    cluster_total_power_est,
    site_flops_per_scaleout_byte,

    # Data path
    dataset_bytes_per_sample,
    storage_to_loader_efficiency,
    storage_stream_bw_effective,
    max_sample_rate_from_storage,
    required_sample_rate,
    data_pipeline_utilization,
    data_stall_fraction_est,

    # Scheduler
    scheduler_queue_wait,
    scheduler_allocation_time,
    provisioning_time,
    job_start_delay,

    # Reliability
    nodes_per_power_domain,
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

    # Hyperscaler and WAN
    n_sites_hs,
    hs_n_gpus,
    hs_peak_flops,
    hs_total_power,
    hs_hbm_capacity,
    hs_local_ssd_capacity,
    wan_links_per_site,
    bw_wan_link,
    eta_scale_across,
    bw_scale_across_site,
    bw_scale_across,
    lat_scale_across,
    scale_across_msg_size,
    scale_across_transfer_time,
])

sys_cluster.add_all([
    eq_node_peak_flops,
    eq_node_peak_flops_power_limited,
    eq_node_hbm_capacity,
    eq_node_hbm_bw,
    eq_node_local_ssd_capacity,
    eq_node_local_ssd_bw,
    eq_node_nic_bw,
    eq_node_power,
    eq_rack_gpu_count,
    eq_rack_peak_flops,
    eq_rack_peak_flops_power_limited,
    eq_rack_hbm_capacity,
    eq_rack_hbm_bw,
    eq_rack_local_ssd_capacity,
    eq_rack_local_ssd_bw,
    eq_rack_nic_bw,
    eq_rack_power,
    eq_rack_gpus_per_power_domain,
    eq_rack_flops_per_intra_byte,
    eq_cluster_n_nodes,
    eq_cluster_n_gpus,
    eq_cluster_peak,
    eq_cluster_peak_power_limited,
    eq_cluster_power_it,
    eq_cluster_hbm_capacity,
    eq_cluster_hbm_bw,
    eq_cluster_local_ssd_capacity,
    eq_cluster_local_ssd_bw,
    eq_cluster_nic_bw,
    eq_cluster_total_power_est,
    eq_site_flops_per_scaleout_byte,
    eq_storage_stream_bw_effective,
    eq_max_sample_rate_from_storage,
    eq_data_pipeline_utilization,
    eq_data_stall_fraction_est,
    eq_job_start_delay,
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
    eq_hs_n_gpus,
    eq_hs_peak,
    eq_hs_total_power,
    eq_hs_hbm_capacity,
    eq_hs_local_ssd_capacity,
    eq_bw_scale_across_site,
    eq_bw_scale_across,
    eq_scale_across_transfer_time,
])
