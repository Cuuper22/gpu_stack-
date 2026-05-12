"""
tests/test_node_nic_topology.py
================================

Node scale-out NIC regressions. Node bandwidth is bounded by installed NICs,
ports, port rates, and node-level protocol efficiency, not by multiplying a
per-GPU value by GPU count.
"""

import pytest

from gpu_stack import Registry, resolve


def test_node_raw_nic_bandwidth_depends_on_physical_ports():
    raw = Registry.variables["cluster.node.nic_bw_raw"]
    assert not raw.is_root_input
    assert {v.name for v in raw.direct_dependencies()} == {
        "cluster.node.nic.count",
        "cluster.node.nic.ports_per_nic",
        "cluster.node.nic.port_rate",
    }

    result = resolve(
        "cluster.node.nic_bw_raw",
        assignments={
            "cluster.node.nic.count": 4,
            "cluster.node.nic.ports_per_nic": 2,
            "cluster.node.nic.port_rate": 100.0,
        },
    )
    assert float(result.value) == pytest.approx(800.0)


def test_node_nic_bandwidth_no_longer_multiplies_gpu_count():
    bw = Registry.variables["cluster.node.nic_bw"]
    assert not bw.is_root_input
    deps = {v.name for v in bw.direct_dependencies()}
    assert deps == {
        "cluster.node.nic_bw_raw",
        "cluster.node.nic.protocol_efficiency",
    }
    assert "cluster.node.n_gpus" not in deps
    assert "gpu.nic.bw_effective" not in deps

    result = resolve(
        "cluster.node.nic_bw",
        assignments={
            "cluster.node.nic.count": 4,
            "cluster.node.nic.ports_per_nic": 2,
            "cluster.node.nic.port_rate": 100.0,
            "cluster.node.nic.protocol_efficiency": 0.8,
        },
    )
    assert float(result.value) == pytest.approx(640.0)


def test_node_nic_equations_have_unit_checks():
    checked = {
        name
        for name, eq in Registry.equations.items()
        if getattr(eq, "_check_units_flag", False)
    }
    assert {
        "cluster.eq.node_nic_bw_raw",
        "cluster.eq.node_nic_bw",
    } <= checked
