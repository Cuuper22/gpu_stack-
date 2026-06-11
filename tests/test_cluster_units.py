"""
tests/test_cluster_units.py
===========================

Focused cluster metadata and unit-check coverage.
"""

import sympy as sp

from gpu_stack.core.units import BPS, FLOPS, SECOND, WATT, byte
from gpu_stack.scopes import cluster


DIMENSIONLESS = sp.Integer(1)

# Every cluster equation now opts into dimensional checking.
UNCHECKED_CLUSTER_EQUATIONS = set()


def test_cluster_variables_have_units_and_references():
    assert [v.name for v in cluster.CLUSTER_VARIABLES if v.sp_units is None] == []
    assert [v.name for v in cluster.CLUSTER_VARIABLES if not v.references] == []


def test_cluster_equations_have_references_and_curated_unit_checks():
    checked = {
        eq.name
        for eq in cluster.CLUSTER_EQUATIONS
        if getattr(eq, "_check_units_flag", False)
    }
    unchecked = {eq.name for eq in cluster.CLUSTER_EQUATIONS} - checked

    assert [eq.name for eq in cluster.CLUSTER_EQUATIONS if not eq.references] == []
    assert unchecked == UNCHECKED_CLUSTER_EQUATIONS


def test_cluster_representative_units_cover_power_bandwidth_storage_and_reliability():
    assert cluster.node_power.sp_units == WATT
    assert cluster.rack_power.sp_units == WATT
    assert cluster.cluster_power_it.sp_units == WATT
    assert cluster.cluster_total_power_est.sp_units == WATT
    assert cluster.rack_scaleout_bisection_bw.sp_units == BPS
    assert cluster.cluster_nic_bw.sp_units == BPS
    assert cluster.bw_scale_across_site.sp_units == BPS
    assert cluster.dataset_bytes_per_sample.sp_units == byte
    assert cluster.max_sample_rate_from_storage.sp_units == 1 / SECOND
    assert cluster.checkpoint_size.sp_units == byte
    assert cluster.checkpoint_bw.sp_units == BPS
    assert cluster.cluster_failure_rate.sp_units == 1 / SECOND
    assert cluster.availability_from_reliability.sp_units == DIMENSIONLESS
    assert cluster.site_flops_per_scaleout_byte.sp_units == FLOPS / BPS
