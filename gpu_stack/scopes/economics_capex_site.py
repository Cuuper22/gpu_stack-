"""
Node, rack, cluster, facility, and allocation capex primitives.
"""

from ..core import eq, var
from ..core.units import METER, SECOND, WATT

from .cluster import (
    cluster_n_gpus,
    n_gpus_per_node,
    n_nodes_per_rack,
    n_racks_cluster,
)
from .economics_capex_gpu import gpu_capex, residual_value_fraction, useful_life
from .economics_capex_refs import (
    CAPEX_BOM_REF,
    DIMENSIONLESS,
    FACILITY_CAPEX_REF,
    USD,
)
from .parallelism import n_gpus_total
from .thermal_facility import (
    facility_cooling_design_capacity,
    facility_floor_area,
    facility_power_design_capacity,
)


node_cpu_capex = var(
    "econ.node.cpu_capex", "C_cpu_node", "USD",
    "CPU capex per node.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
node_dram_capex = var(
    "econ.node.dram_capex", "C_dram_node", "USD",
    "CPU-side DRAM capex per node.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
node_nic_capex = var(
    "econ.node.nic_capex", "C_nic_node", "USD",
    "NIC, retimer, and cable capex per node.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
node_storage_capex = var(
    "econ.node.storage_capex", "C_stor_node", "USD",
    "Local SSD or NVMe storage capex per node.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
node_chassis_capex = var(
    "econ.node.chassis_capex", "C_chassis_node", "USD",
    "Chassis, motherboard, PSU, and assembly capex per node.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
rack_switch_capex = var(
    "econ.rack.switch_capex", "C_sw_rack", "USD",
    "Top-of-rack and rack-local fabric capex per rack.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
rack_power_distribution_capex = var(
    "econ.rack.power_distribution_capex", "C_pdu_rack", "USD",
    "Rack-level power-distribution, busbar, and rack integration capex.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
cluster_spine_network_capex = var(
    "econ.cluster.spine_network_capex", "C_spine", "USD",
    "Cluster-scale spine and aggregation network capex.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
cluster_storage_capex = var(
    "econ.cluster.storage_capex", "C_stor_site", "USD",
    "Parallel filesystem and shared-storage capex for the site.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
building_shell_unit_cost = var(
    "econ.facility.building_shell_unit_cost", "c_bldg_A", "USD/m^2",
    "Building shell and civil works unit cost per square meter of facility floor area.",
    scope="economics",
    sp_units=USD / METER**2,
    references=[FACILITY_CAPEX_REF],
)
power_infra_unit_cost = var(
    "econ.facility.power_infra_unit_cost", "c_power_W", "USD/W",
    "Power-infrastructure unit cost per watt of facility electrical design capacity.",
    scope="economics",
    sp_units=USD / WATT,
    references=[FACILITY_CAPEX_REF],
)
cooling_infra_unit_cost = var(
    "econ.facility.cooling_infra_unit_cost", "c_cool_W", "USD/W",
    "Cooling-infrastructure unit cost per watt of facility thermal design capacity.",
    scope="economics",
    sp_units=USD / WATT,
    references=[FACILITY_CAPEX_REF],
)
building_shell_capex = var(
    "econ.facility.building_shell_capex", "C_bldg", "USD",
    "Building shell and civil works capex allocated to the site.",
    scope="economics",
    sp_units=USD,
    references=[FACILITY_CAPEX_REF],
)
power_infra_capex = var(
    "econ.facility.power_infra_capex", "C_power_fac", "USD",
    "Utility service, switchgear, UPS, transformers, and generator capex.",
    scope="economics",
    sp_units=USD,
    references=[FACILITY_CAPEX_REF],
)
cooling_infra_capex = var(
    "econ.facility.cooling_infra_capex", "C_cool_fac", "USD",
    "Cooling-plant capex, including chillers, CDU plant, tower, and distribution piping.",
    scope="economics",
    sp_units=USD,
    references=[FACILITY_CAPEX_REF],
)
node_capex = var(
    "econ.node.capex", "C_node", "USD",
    "All-in capex of one compute node.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
rack_capex = var(
    "econ.rack.capex", "C_rack", "USD",
    "All-in capex of one compute rack.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
cluster_it_capex = var(
    "econ.cluster.it_capex", "C_IT_site", "USD",
    "IT-side capex of the site, including compute, network, and shared storage.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
cluster_facility_capex = var(
    "econ.cluster.facility_capex", "C_fac_site", "USD",
    "Facility-side capex of the site, excluding the IT equipment itself.",
    scope="economics",
    sp_units=USD,
    references=[FACILITY_CAPEX_REF],
)
cluster_capex_total = var(
    "econ.cluster.capex_total", "C_site", "USD",
    "Total site capex.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
cluster_residual_value = var(
    "econ.cluster.residual_value", "C_resid_site", "USD",
    "Residual site value at the end of the depreciation horizon.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
cluster_depreciable_base = var(
    "econ.cluster.depreciable_base", "C_dep_site", "USD",
    "Depreciable site capex after residual value is removed.",
    scope="economics",
    sp_units=USD,
    references=[CAPEX_BOM_REF],
)
cluster_capex_rate = var(
    "econ.cluster.capex_rate", "Cdot_site", "USD/s",
    "Straight-line site capex charge per second before utilization allocation.",
    scope="economics",
    sp_units=USD / SECOND,
    references=[CAPEX_BOM_REF],
)
job_share_of_cluster = var(
    "econ.job.share_of_cluster", "f_job", "dimensionless",
    "Fraction of the site's GPU fleet allocated to the training job.",
    scope="economics",
    sp_units=DIMENSIONLESS,
    references=[CAPEX_BOM_REF],
)


eq_node_capex = eq(
    "econ.eq.node_capex",
    node_capex.symbol,
    n_gpus_per_node.symbol * gpu_capex.symbol
    + node_cpu_capex.symbol
    + node_dram_capex.symbol
    + node_nic_capex.symbol
    + node_storage_capex.symbol
    + node_chassis_capex.symbol,
    "Node capex equals GPU capex plus CPU, DRAM, NIC, storage, and chassis capex.",
    references=[CAPEX_BOM_REF],
    check_units=True,
)

eq_rack_capex = eq(
    "econ.eq.rack_capex",
    rack_capex.symbol,
    n_nodes_per_rack.symbol * node_capex.symbol
    + rack_switch_capex.symbol
    + rack_power_distribution_capex.symbol,
    "Rack capex equals nodes per rack times node capex plus rack switch and power-distribution capex.",
    references=[CAPEX_BOM_REF],
    check_units=True,
)

eq_cluster_it_capex = eq(
    "econ.eq.cluster_it_capex",
    cluster_it_capex.symbol,
    n_racks_cluster.symbol * rack_capex.symbol
    + cluster_spine_network_capex.symbol
    + cluster_storage_capex.symbol,
    "Site IT capex equals rack capex plus cluster-scale spine-network and shared-storage capex.",
    references=[CAPEX_BOM_REF],
    check_units=True,
)

eq_building_shell_capex = eq(
    "econ.eq.facility_building_shell_capex",
    building_shell_capex.symbol,
    facility_floor_area.symbol * building_shell_unit_cost.symbol,
    "Building shell capex equals facility floor area times building shell unit cost.",
    references=[FACILITY_CAPEX_REF],
    check_units=True,
)

eq_power_infra_capex = eq(
    "econ.eq.facility_power_infra_capex",
    power_infra_capex.symbol,
    facility_power_design_capacity.symbol * power_infra_unit_cost.symbol,
    "Power infrastructure capex equals facility electrical design capacity times power-infrastructure unit cost.",
    references=[FACILITY_CAPEX_REF],
    check_units=True,
)

eq_cooling_infra_capex = eq(
    "econ.eq.facility_cooling_infra_capex",
    cooling_infra_capex.symbol,
    facility_cooling_design_capacity.symbol * cooling_infra_unit_cost.symbol,
    "Cooling infrastructure capex equals facility thermal design capacity times cooling-infrastructure unit cost.",
    references=[FACILITY_CAPEX_REF],
    check_units=True,
)

eq_cluster_facility_capex = eq(
    "econ.eq.cluster_facility_capex",
    cluster_facility_capex.symbol,
    building_shell_capex.symbol
    + power_infra_capex.symbol
    + cooling_infra_capex.symbol,
    "Site facility capex equals building, power infrastructure, and cooling infrastructure capex.",
    references=[FACILITY_CAPEX_REF],
    check_units=True,
)

eq_cluster_capex_total = eq(
    "econ.eq.cluster_capex_total",
    cluster_capex_total.symbol,
    cluster_it_capex.symbol + cluster_facility_capex.symbol,
    "Total site capex equals IT capex plus facility capex.",
    references=[CAPEX_BOM_REF],
    check_units=True,
)

eq_cluster_residual_value = eq(
    "econ.eq.cluster_residual_value",
    cluster_residual_value.symbol,
    residual_value_fraction.symbol * cluster_capex_total.symbol,
    "Site residual value equals residual fraction times total site capex.",
    references=[CAPEX_BOM_REF],
    check_units=True,
)

eq_cluster_depreciable_base = eq(
    "econ.eq.cluster_depreciable_base",
    cluster_depreciable_base.symbol,
    cluster_capex_total.symbol - cluster_residual_value.symbol,
    "Site depreciable base equals total capex minus residual value.",
    references=[CAPEX_BOM_REF],
    check_units=True,
)

eq_cluster_capex_rate = eq(
    "econ.eq.cluster_capex_rate",
    cluster_capex_rate.symbol,
    cluster_depreciable_base.symbol / useful_life.symbol,
    "Site capex charge rate equals depreciable site capex divided by useful life.",
    references=[CAPEX_BOM_REF],
    check_units=True,
)

eq_job_share_of_cluster = eq(
    "econ.eq.job_share_of_cluster",
    job_share_of_cluster.symbol,
    n_gpus_total.symbol / cluster_n_gpus.symbol,
    "Job share of cluster equals training-job GPUs divided by total site GPUs.",
    references=[CAPEX_BOM_REF],
    check_units=True,
)


__all__ = [
    "building_shell_capex",
    "building_shell_unit_cost",
    "cluster_capex_rate",
    "cluster_capex_total",
    "cluster_depreciable_base",
    "cluster_facility_capex",
    "cluster_it_capex",
    "cluster_residual_value",
    "cluster_spine_network_capex",
    "cluster_storage_capex",
    "cooling_infra_capex",
    "cooling_infra_unit_cost",
    "eq_building_shell_capex",
    "eq_cluster_capex_rate",
    "eq_cluster_capex_total",
    "eq_cluster_depreciable_base",
    "eq_cluster_facility_capex",
    "eq_cluster_it_capex",
    "eq_cluster_residual_value",
    "eq_cooling_infra_capex",
    "eq_job_share_of_cluster",
    "eq_node_capex",
    "eq_power_infra_capex",
    "eq_rack_capex",
    "job_share_of_cluster",
    "node_capex",
    "node_chassis_capex",
    "node_cpu_capex",
    "node_dram_capex",
    "node_nic_capex",
    "node_storage_capex",
    "power_infra_capex",
    "power_infra_unit_cost",
    "rack_capex",
    "rack_power_distribution_capex",
    "rack_switch_capex",
]
