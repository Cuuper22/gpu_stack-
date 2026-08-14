"""
scopes/economics_capex.py
=========================

Facade for capex: the money spent before the first token is trained.

Capex (capital expenditure) is the up-front purchase cost of everything a
cluster is made of, later recovered by depreciating it over a useful life.
The model splits into three helpers: shared units and References, GPU-level
amortization (purchase price, residual value, hourly cost, rental markup),
and the site-level bill of materials that sums node, rack, network, storage,
and facility capital into a cluster total. This module only re-exports
those pieces, keeping the historical import surface and registry lists
stable for the rest of the economics scope.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import METER, SECOND, WATT

from .cluster import (
    cluster_n_gpus,
    n_gpus_per_node,
    n_nodes_per_rack,
    n_racks_cluster,
)
from .economics_capex_gpu import (
    eq_amortized,
    eq_gpu_rental_markup,
    eq_gpu_residual_value,
    gpu_capex,
    gpu_hourly_amortized,
    gpu_hourly_rent,
    gpu_rental_markup,
    gpu_residual_value,
    residual_value_fraction,
    useful_life,
)
from .economics_capex_refs import (
    CAPEX_BOM_REF,
    DIMENSIONLESS,
    FACILITY_CAPEX_REF,
    USD,
)
from .economics_capex_site import (
    building_shell_capex,
    building_shell_unit_cost,
    cluster_capex_rate,
    cluster_capex_total,
    cluster_depreciable_base,
    cluster_facility_capex,
    cluster_it_capex,
    cluster_residual_value,
    cluster_spine_network_capex,
    cluster_storage_capex,
    cooling_infra_capex,
    cooling_infra_unit_cost,
    eq_building_shell_capex,
    eq_cluster_capex_rate,
    eq_cluster_capex_total,
    eq_cluster_depreciable_base,
    eq_cluster_facility_capex,
    eq_cluster_it_capex,
    eq_cluster_residual_value,
    eq_cooling_infra_capex,
    eq_job_share_of_cluster,
    eq_node_capex,
    eq_power_infra_capex,
    eq_rack_capex,
    job_share_of_cluster,
    node_capex,
    node_chassis_capex,
    node_cpu_capex,
    node_dram_capex,
    node_nic_capex,
    node_storage_capex,
    power_infra_capex,
    power_infra_unit_cost,
    rack_capex,
    rack_power_distribution_capex,
    rack_switch_capex,
)
from .parallelism import n_gpus_total
from .thermal_facility import (
    facility_cooling_design_capacity,
    facility_floor_area,
    facility_power_design_capacity,
)


ECON_CAPEX_VARIABLES = [
    gpu_capex,
    useful_life,
    residual_value_fraction,
    gpu_residual_value,
    gpu_hourly_amortized,
    gpu_hourly_rent,
    gpu_rental_markup,
    node_cpu_capex,
    node_dram_capex,
    node_nic_capex,
    node_storage_capex,
    node_chassis_capex,
    rack_switch_capex,
    rack_power_distribution_capex,
    cluster_spine_network_capex,
    cluster_storage_capex,
    building_shell_unit_cost,
    power_infra_unit_cost,
    cooling_infra_unit_cost,
    building_shell_capex,
    power_infra_capex,
    cooling_infra_capex,
    node_capex,
    rack_capex,
    cluster_it_capex,
    cluster_facility_capex,
    cluster_capex_total,
    cluster_residual_value,
    cluster_depreciable_base,
    cluster_capex_rate,
    job_share_of_cluster,
]

ECON_CAPEX_EQUATIONS = [
    eq_gpu_residual_value,
    eq_amortized,
    eq_gpu_rental_markup,
    eq_node_capex,
    eq_rack_capex,
    eq_cluster_it_capex,
    eq_building_shell_capex,
    eq_power_infra_capex,
    eq_cooling_infra_capex,
    eq_cluster_facility_capex,
    eq_cluster_capex_total,
    eq_cluster_residual_value,
    eq_cluster_depreciable_base,
    eq_cluster_capex_rate,
    eq_job_share_of_cluster,
]


__all__ = [
    "gpu_capex", "useful_life", "residual_value_fraction",
    "gpu_residual_value", "gpu_hourly_amortized", "gpu_hourly_rent",
    "gpu_rental_markup",
    "node_cpu_capex", "node_dram_capex", "node_nic_capex",
    "node_storage_capex", "node_chassis_capex",
    "rack_switch_capex", "rack_power_distribution_capex",
    "cluster_spine_network_capex", "cluster_storage_capex",
    "building_shell_unit_cost", "power_infra_unit_cost",
    "cooling_infra_unit_cost",
    "building_shell_capex", "power_infra_capex", "cooling_infra_capex",
    "node_capex", "rack_capex", "cluster_it_capex",
    "cluster_facility_capex", "cluster_capex_total",
    "cluster_residual_value", "cluster_depreciable_base",
    "cluster_capex_rate", "job_share_of_cluster",
    "eq_gpu_residual_value", "eq_amortized", "eq_gpu_rental_markup",
    "eq_node_capex", "eq_rack_capex", "eq_cluster_it_capex",
    "eq_building_shell_capex", "eq_power_infra_capex",
    "eq_cooling_infra_capex",
    "eq_cluster_facility_capex", "eq_cluster_capex_total",
    "eq_cluster_residual_value", "eq_cluster_depreciable_base",
    "eq_cluster_capex_rate", "eq_job_share_of_cluster",
    "ECON_CAPEX_VARIABLES", "ECON_CAPEX_EQUATIONS",
]
