"""
scopes/cluster_site.py
======================

Public facade for the site: one data-center building as a unit.

A site is one building with one set of utility feeds and one facility
boundary — the natural unit for power contracts, cooling plants, and
failure isolation. Three helper modules carry its math: rack-to-site rollups
of compute, memory, storage, and IT power; scheduler and provisioning delay
before a job's first useful step; and the hyperscaler layer that joins many
sites over WAN links for scale-across training. This wrapper re-exports all
of it, keeping the historical import path, public exports, and registry
ordering stable. The thermal and economics scopes attach to the site's
power figures.
"""

from ..core import Reference
from ..core.units import BPS, FLOPS, SECOND, WATT, byte
from .cluster_ops_declarations import (
    DIMENSIONLESS,
    referenced_eq,
    scoped_var,
)
from .cluster_rack import (
    n_nodes_per_rack,
    rack_hbm_bw,
    rack_hbm_capacity,
    rack_local_ssd_bw,
    rack_local_ssd_capacity,
    rack_peak_flops,
    rack_peak_flops_power_limited,
    rack_power,
    rack_scaleout_bisection_bw,
)
from .interconnect import n_gpus_per_rack

from .cluster_site_common import *
from .cluster_site_aggregation import *
from .cluster_site_aggregation import (
    CLUSTER_SITE_AGGREGATION_EQUATIONS as _CLUSTER_SITE_AGGREGATION_EQUATIONS,
    CLUSTER_SITE_AGGREGATION_VARIABLES as _CLUSTER_SITE_AGGREGATION_VARIABLES,
)
from .cluster_site_scheduler import *
from .cluster_site_scheduler import (
    CLUSTER_SITE_SCHEDULER_EQUATIONS as _CLUSTER_SITE_SCHEDULER_EQUATIONS,
    CLUSTER_SITE_SCHEDULER_VARIABLES as _CLUSTER_SITE_SCHEDULER_VARIABLES,
)
from .cluster_site_scale_across import *
from .cluster_site_scale_across import (
    CLUSTER_SITE_SCALE_ACROSS_EQUATIONS as _CLUSTER_SITE_SCALE_ACROSS_EQUATIONS,
    CLUSTER_SITE_SCALE_ACROSS_VARIABLES as _CLUSTER_SITE_SCALE_ACROSS_VARIABLES,
)


CLUSTER_SITE_VARIABLES = (
    _CLUSTER_SITE_AGGREGATION_VARIABLES
    + _CLUSTER_SITE_SCHEDULER_VARIABLES
    + _CLUSTER_SITE_SCALE_ACROSS_VARIABLES
)

CLUSTER_SITE_EQUATIONS = (
    _CLUSTER_SITE_AGGREGATION_EQUATIONS
    + _CLUSTER_SITE_SCHEDULER_EQUATIONS
    + _CLUSTER_SITE_SCALE_ACROSS_EQUATIONS
)


__all__ = [
    "n_racks_cluster", "cluster_n_nodes", "cluster_n_gpus",
    "cluster_peak_flops", "cluster_peak_flops_power_limited",
    "cluster_power_it", "cluster_hbm_capacity", "cluster_hbm_bw",
    "cluster_local_ssd_capacity", "cluster_local_ssd_bw", "cluster_nic_bw",
    "site_power_overhead_factor_est", "cluster_total_power_est",
    "site_flops_per_scaleout_byte",
    "scheduler_queue_wait", "scheduler_allocation_time", "provisioning_time",
    "job_start_delay",
    "n_sites_hs", "hs_n_gpus", "hs_peak_flops", "hs_total_power",
    "hs_hbm_capacity", "hs_local_ssd_capacity",
    "wan_links_per_site", "bw_wan_link", "eta_scale_across",
    "bw_scale_across_site", "bw_scale_across", "lat_scale_across",
    "scale_across_msg_size", "scale_across_transfer_time",
    "eq_cluster_n_nodes", "eq_cluster_n_gpus", "eq_cluster_peak",
    "eq_cluster_peak_power_limited", "eq_cluster_power_it",
    "eq_cluster_hbm_capacity", "eq_cluster_hbm_bw",
    "eq_cluster_local_ssd_capacity", "eq_cluster_local_ssd_bw",
    "eq_cluster_nic_bw", "eq_cluster_total_power_est",
    "eq_site_flops_per_scaleout_byte", "eq_job_start_delay",
    "eq_hs_n_gpus", "eq_hs_peak", "eq_hs_total_power",
    "eq_hs_hbm_capacity", "eq_hs_local_ssd_capacity",
    "eq_bw_scale_across_site", "eq_bw_scale_across",
    "eq_scale_across_transfer_time",
    "CLUSTER_SITE_VARIABLES", "CLUSTER_SITE_EQUATIONS",
]
