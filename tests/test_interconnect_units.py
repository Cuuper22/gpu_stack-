"""
tests/test_interconnect_units.py
================================

Focused interconnect metadata and dimensional-check coverage.
"""

import sympy as sp

from gpu_stack.core.units import BPS, SECOND, byte
from gpu_stack.scopes import interconnect


DIMENSIONLESS = sp.Integer(1)

UNCHECKED_INTERCONNECT_EQUATIONS = {
    "link.eq.msg_packets",
}


def test_interconnect_variables_have_units_and_references():
    assert [v.name for v in interconnect.sys_link.variables if v.sp_units is None] == []
    assert [v.name for v in interconnect.sys_link.variables if not v.references] == []


def test_interconnect_equations_have_references_and_curated_unit_checks():
    checked = {
        eq.name
        for eq in interconnect.sys_link.equations
        if getattr(eq, "_check_units_flag", False)
    }
    unchecked = {eq.name for eq in interconnect.sys_link.equations} - checked

    assert [eq.name for eq in interconnect.sys_link.equations if not eq.references] == []
    assert unchecked == UNCHECKED_INTERCONNECT_EQUATIONS


def test_interconnect_representative_units_cover_fabric_latency_and_bandwidth():
    assert interconnect.raw_line_rate.sp_units == BPS
    assert interconnect.packet_payload_bytes.sp_units == byte
    assert interconnect.packet_efficiency.sp_units == DIMENSIONLESS
    assert interconnect.bw_eff.sp_units == BPS
    assert interconnect.lat_link.sp_units == SECOND
    assert interconnect.alpha_link.sp_units == SECOND
    assert interconnect.beta_link.sp_units == SECOND / byte
    assert interconnect.bandwidth_delay_product.sp_units == byte
    assert interconnect.bw_nvlink_effective.sp_units == BPS
    assert interconnect.nvlink_hop_latency.sp_units == SECOND
    assert interconnect.bw_scale_out_effective.sp_units == BPS
    assert interconnect.switch_radix.sp_units == DIMENSIONLESS
    assert interconnect.ratio_intra_to_scale_out.sp_units == DIMENSIONLESS
