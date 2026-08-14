"""Verifies node non-GPU power is decomposed into a bill of materials.

A server node's power beyond the GPUs — CPU, RAM, NICs, SSDs, misc — must
not be five opaque root numbers. Each total is derived from BOM inputs
(count times power-per-unit), so the model can answer "what if we add a
NIC?" instead of just restating a guess. These tests pin the decomposition:
each component total depends on exactly its BOM inputs, the per-unit
coefficients stay roots, hand-checkable cases resolve correctly (for
example 2 CPUs at 320 W gives 640 W), the node total of 6738.96 W traces
through every component equation, and no dependency cycles appear.
"""

import pytest

import gpu_stack
from gpu_stack import Registry, resolve


def _deps(name):
    return {v.name for v in Registry.variables[name].direct_dependencies()}


def test_node_component_power_totals_are_derived_from_bom_inputs():
    expected = {
        "cluster.node.cpu_power": {
            "cluster.node.n_cpus",
            "cluster.node.cpu.power_per_cpu",
        },
        "cluster.node.ram_power": {
            "cluster.node.ram",
            "cluster.node.ram.power_per_byte",
        },
        "cluster.node.nic_power": {
            "cluster.node.nic.count",
            "cluster.node.nic.ports_per_nic",
            "cluster.node.nic.power_per_nic",
            "cluster.node.nic.power_per_port",
        },
        "cluster.node.storage_power": {
            "cluster.node.local_ssd.count",
            "cluster.node.local_ssd.power_per_drive",
        },
        "cluster.node.misc_power": {
            "cluster.node.misc.fixed_power",
            "cluster.node.misc.power_per_gpu",
            "cluster.node.n_gpus",
        },
    }

    for name, deps in expected.items():
        variable = Registry.variables[name]
        assert not variable.is_root_input
        assert _deps(name) == deps


def test_node_power_bom_coefficients_remain_root_inputs():
    roots = {
        "cluster.node.cpu.power_per_cpu",
        "cluster.node.ram.power_per_byte",
        "cluster.node.nic.power_per_nic",
        "cluster.node.nic.power_per_port",
        "cluster.node.local_ssd.power_per_drive",
        "cluster.node.misc.fixed_power",
        "cluster.node.misc.power_per_gpu",
    }

    for name in roots:
        assert Registry.variables[name].is_root_input


def test_node_component_power_resolves_from_bom_values():
    cases = [
        (
            "cluster.node.cpu_power",
            {
                "cluster.node.n_cpus": 2,
                "cluster.node.cpu.power_per_cpu": 320,
            },
            640,
        ),
        (
            "cluster.node.ram_power",
            {
                "cluster.node.ram": 2048,
                "cluster.node.ram.power_per_byte": 0.02,
            },
            40.96,
        ),
        (
            "cluster.node.nic_power",
            {
                "cluster.node.nic.count": 4,
                "cluster.node.nic.ports_per_nic": 2,
                "cluster.node.nic.power_per_nic": 28,
                "cluster.node.nic.power_per_port": 7,
            },
            168,
        ),
        (
            "cluster.node.storage_power",
            {
                "cluster.node.local_ssd.count": 8,
                "cluster.node.local_ssd.power_per_drive": 14,
            },
            112,
        ),
        (
            "cluster.node.misc_power",
            {
                "cluster.node.n_gpus": 8,
                "cluster.node.misc.fixed_power": 90,
                "cluster.node.misc.power_per_gpu": 11,
            },
            178,
        ),
    ]

    for target, assignments, expected in cases:
        result = resolve(target, assignments=assignments)
        assert float(result.value) == pytest.approx(expected)


def test_total_node_power_uses_decomposed_component_power():
    result = resolve(
        "cluster.node.power",
        assignments={
            "cluster.node.n_gpus": 8,
            "gpu.power.total": 700,
            "cluster.node.n_cpus": 2,
            "cluster.node.cpu.power_per_cpu": 320,
            "cluster.node.ram": 2048,
            "cluster.node.ram.power_per_byte": 0.02,
            "cluster.node.nic.count": 4,
            "cluster.node.nic.ports_per_nic": 2,
            "cluster.node.nic.power_per_nic": 28,
            "cluster.node.nic.power_per_port": 7,
            "cluster.node.local_ssd.count": 8,
            "cluster.node.local_ssd.power_per_drive": 14,
            "cluster.node.misc.fixed_power": 90,
            "cluster.node.misc.power_per_gpu": 11,
        },
    )

    assert float(result.value) == pytest.approx(6738.96)
    assert {
        "cluster.eq.node_cpu_power",
        "cluster.eq.node_ram_power",
        "cluster.eq.node_nic_power",
        "cluster.eq.node_storage_power",
        "cluster.eq.node_misc_power",
        "cluster.eq.node_power",
    } <= {step.equation for step in result.trace}


def test_node_power_metadata_is_covered():
    node_power = Registry.variables["cluster.node.power"]
    eq = Registry.equations["cluster.eq.node_power"]

    assert node_power.sp_units is not None
    assert node_power.references
    assert eq.references
    assert getattr(eq, "_check_units_flag", False)


def test_node_power_decomposition_does_not_introduce_cycles():
    assert gpu_stack.find_cycles() == []
