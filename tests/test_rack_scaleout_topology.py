"""Regression tests for rack scale-out network topology.

A rack's off-rack bandwidth is not one number. Nodes inject traffic through
their NICs; top-of-rack (ToR) switches accept it on downlink ports and pass
it upward on uplink ports. Downlink capacity usually exceeds uplink capacity
— that ratio is the oversubscription — and the traffic that can actually
leave the rack, the bisection bandwidth, is capped by the tightest of node
injection, downlink, and uplink.

These tests pin that structure into the graph. Per-switch capacities come
from ports x rate x protocol efficiency; rack totals multiply by switch
count; oversubscription is downlink over uplink; bisection takes the
minimum of the three limits. Site bandwidth aggregates rack bisection —
never raw injection, which would overstate what the fabric can carry — and
the site FLOPs-per-byte balance uses that honest number. Every equation in
the chain must carry a unit check.
"""

import pytest

from gpu_stack import Registry, resolve


def test_rack_scaleout_downlink_and_uplink_depend_on_tor_capacity():
    downlink_per_switch = Registry.variables["cluster.rack.tor.downlink_bw_per_switch"]
    uplink_per_switch = Registry.variables["cluster.rack.tor.uplink_bw_per_switch"]
    downlink = Registry.variables["cluster.rack.scaleout_downlink_bw"]
    uplink = Registry.variables["cluster.rack.scaleout_uplink_bw"]

    assert not downlink_per_switch.is_root_input
    assert not uplink_per_switch.is_root_input
    assert not downlink.is_root_input
    assert not uplink.is_root_input
    assert {v.name for v in downlink_per_switch.direct_dependencies()} == {
        "cluster.rack.tor.downlink_ports_per_switch",
        "cluster.rack.tor.downlink_port_rate",
        "cluster.rack.tor.downlink_protocol_efficiency",
    }
    assert {v.name for v in uplink_per_switch.direct_dependencies()} == {
        "cluster.rack.tor.uplink_ports_per_switch",
        "cluster.rack.tor.uplink_port_rate",
        "cluster.rack.tor.uplink_protocol_efficiency",
    }
    assert {v.name for v in downlink.direct_dependencies()} == {
        "cluster.rack.tor.count",
        "cluster.rack.tor.downlink_bw_per_switch",
    }
    assert {v.name for v in uplink.direct_dependencies()} == {
        "cluster.rack.tor.count",
        "cluster.rack.tor.uplink_bw_per_switch",
    }

    result = resolve(
        "cluster.rack.scaleout_downlink_bw",
        assignments={
            "cluster.rack.tor.count": 2,
            "cluster.rack.tor.downlink_ports_per_switch": 8,
            "cluster.rack.tor.downlink_port_rate": 250.0,
            "cluster.rack.tor.downlink_protocol_efficiency": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(4000.0)


def test_rack_scaleout_oversubscription_is_downlink_over_uplink():
    oversub = Registry.variables["cluster.rack.scaleout_oversubscription"]
    assert not oversub.is_root_input
    assert {v.name for v in oversub.direct_dependencies()} == {
        "cluster.rack.scaleout_downlink_bw",
        "cluster.rack.scaleout_uplink_bw",
    }

    result = resolve(
        "cluster.rack.scaleout_oversubscription",
        assignments={
            "cluster.rack.tor.count": 2,
            "cluster.rack.tor.downlink_ports_per_switch": 8,
            "cluster.rack.tor.downlink_port_rate": 250.0,
            "cluster.rack.tor.downlink_protocol_efficiency": 1.0,
            "cluster.rack.tor.uplink_ports_per_switch": 4,
            "cluster.rack.tor.uplink_port_rate": 250.0,
            "cluster.rack.tor.uplink_protocol_efficiency": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(2.0)


def test_rack_scaleout_bisection_caps_node_injection_with_fabric_limits():
    bisection = Registry.variables["cluster.rack.scaleout_bisection_bw"]
    assert not bisection.is_root_input
    assert {v.name for v in bisection.direct_dependencies()} == {
        "cluster.rack.nic_bw",
        "cluster.rack.scaleout_downlink_bw",
        "cluster.rack.scaleout_uplink_bw",
    }

    result = resolve(
        "cluster.rack.scaleout_bisection_bw",
        assignments={
            "cluster.rack.n_nodes": 8,
            "cluster.node.nic.count": 4,
            "cluster.node.nic.ports_per_nic": 2,
            "cluster.node.nic.port_rate": 100.0,
            "cluster.node.nic.protocol_efficiency": 0.8,
            "cluster.rack.tor.count": 2,
            "cluster.rack.tor.downlink_ports_per_switch": 8,
            "cluster.rack.tor.downlink_port_rate": 250.0,
            "cluster.rack.tor.downlink_protocol_efficiency": 1.0,
            "cluster.rack.tor.uplink_ports_per_switch": 4,
            "cluster.rack.tor.uplink_port_rate": 250.0,
            "cluster.rack.tor.uplink_protocol_efficiency": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(2000.0)


def test_site_nic_bandwidth_aggregates_rack_bisection_not_raw_injection():
    site_bw = Registry.variables["cluster.site.nic_bw"]
    assert not site_bw.is_root_input
    assert {v.name for v in site_bw.direct_dependencies()} == {
        "cluster.site.n_racks",
        "cluster.rack.scaleout_bisection_bw",
    }

    result = resolve(
        "cluster.site.nic_bw",
        assignments={
            "cluster.site.n_racks": 4,
            "cluster.rack.n_nodes": 8,
            "cluster.node.nic.count": 4,
            "cluster.node.nic.ports_per_nic": 2,
            "cluster.node.nic.port_rate": 100.0,
            "cluster.node.nic.protocol_efficiency": 0.8,
            "cluster.rack.tor.count": 2,
            "cluster.rack.tor.downlink_ports_per_switch": 8,
            "cluster.rack.tor.downlink_port_rate": 250.0,
            "cluster.rack.tor.downlink_protocol_efficiency": 1.0,
            "cluster.rack.tor.uplink_ports_per_switch": 4,
            "cluster.rack.tor.uplink_port_rate": 250.0,
            "cluster.rack.tor.uplink_protocol_efficiency": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(8000.0)


def test_site_flops_per_scaleout_byte_uses_bisection_aware_site_bandwidth():
    balance = Registry.variables["cluster.site.flops_per_scaleout_byte"]
    assert not balance.is_root_input
    assert {v.name for v in balance.direct_dependencies()} == {
        "cluster.site.peak_flops_power_limited",
        "cluster.site.nic_bw",
    }

    result = resolve(
        "cluster.site.flops_per_scaleout_byte",
        assignments={
            "cluster.site.peak_flops_power_limited": 2_560_000.0,
            "cluster.site.n_racks": 4,
            "cluster.rack.n_nodes": 8,
            "cluster.node.nic.count": 4,
            "cluster.node.nic.ports_per_nic": 2,
            "cluster.node.nic.port_rate": 100.0,
            "cluster.node.nic.protocol_efficiency": 0.8,
            "cluster.rack.tor.count": 2,
            "cluster.rack.tor.downlink_ports_per_switch": 8,
            "cluster.rack.tor.downlink_port_rate": 250.0,
            "cluster.rack.tor.downlink_protocol_efficiency": 1.0,
            "cluster.rack.tor.uplink_ports_per_switch": 4,
            "cluster.rack.tor.uplink_port_rate": 250.0,
            "cluster.rack.tor.uplink_protocol_efficiency": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(320.0)


def test_rack_scaleout_equations_have_unit_checks():
    checked = {
        name
        for name, equation in Registry.equations.items()
        if getattr(equation, "_check_units_flag", False)
    }
    assert {
        "cluster.eq.rack_nic_bw",
        "cluster.eq.rack_tor_downlink_bw_per_switch",
        "cluster.eq.rack_tor_uplink_bw_per_switch",
        "cluster.eq.rack_scaleout_downlink_bw",
        "cluster.eq.rack_scaleout_uplink_bw",
        "cluster.eq.rack_scaleout_oversubscription",
        "cluster.eq.rack_scaleout_bisection_bw",
        "cluster.eq.site_nic_bw",
        "cluster.eq.site_flops_per_scaleout_byte",
    } <= checked
