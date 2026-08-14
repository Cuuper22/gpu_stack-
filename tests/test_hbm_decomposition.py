"""Verifies HBM capacity and bandwidth are derived from stack geometry.

HBM (high-bandwidth memory) is physically a stack of DRAM dies wired
through parallel channels, and the model keeps that structure: stack
capacity comes from die count, die capacity, and a spare-die fraction; pin
count from channels times pins per channel; bandwidth from pins, pin rate,
and protocol efficiency; and effective bandwidth from the spec number
degraded by refresh, bank conflicts, controller efficiency, and thermal
derating. Each test pins a variable's dependency set and resolves a
hand-checkable case — for example 8 dies of 16 GB with 12.5% spare gives
112 GB per stack — and the equations must all carry unit checks.
"""

import pytest

from gpu_stack import Registry, resolve


def test_hbm_stack_capacity_depends_on_die_count_capacity_and_spares():
    stack_capacity = Registry.variables["mem.hbm.stack_capacity"]
    assert not stack_capacity.is_root_input
    deps = {v.name for v in stack_capacity.direct_dependencies()}
    assert deps == {
        "mem.hbm.dies_per_stack",
        "mem.hbm.die_capacity",
        "mem.hbm.spare_die_fraction",
    }

    result = resolve(
        "mem.hbm.stack_capacity",
        assignments={
            "mem.hbm.dies_per_stack": 8,
            "mem.hbm.die_capacity": 16.0,
            "mem.hbm.spare_die_fraction": 0.125,
        },
    )
    assert float(result.value) == pytest.approx(112.0)


def test_hbm_pin_count_is_channel_geometry_not_root_input():
    pins = Registry.variables["mem.hbm.pins_per_stack"]
    assert not pins.is_root_input
    deps = {v.name for v in pins.direct_dependencies()}
    assert deps == {
        "mem.hbm.channels_per_stack",
        "mem.hbm.pins_per_channel",
    }

    result = resolve(
        "mem.hbm.pins_per_stack",
        assignments={
            "mem.hbm.channels_per_stack": 16,
            "mem.hbm.pins_per_channel": 64,
        },
    )
    assert int(result.value) == 1024


def test_hbm_bandwidth_uses_channel_bandwidth_and_protocol_efficiency():
    channel_bw = Registry.variables["mem.hbm.bw_per_channel"]
    assert not channel_bw.is_root_input
    assert {v.name for v in channel_bw.direct_dependencies()} == {
        "mem.hbm.pins_per_channel",
        "mem.hbm.pin_rate",
        "mem.hbm.protocol_efficiency",
    }

    stack_bw = Registry.variables["mem.hbm.bw_per_stack"]
    assert not stack_bw.is_root_input
    assert {v.name for v in stack_bw.direct_dependencies()} == {
        "mem.hbm.channels_per_stack",
        "mem.hbm.bw_per_channel",
    }

    result = resolve(
        "mem.hbm.bw_per_stack",
        assignments={
            "mem.hbm.channels_per_stack": 16,
            "mem.hbm.pins_per_channel": 64,
            "mem.hbm.pin_rate": 8.0,
            "mem.hbm.protocol_efficiency": 0.9,
        },
    )
    assert float(result.value) == pytest.approx(921.6)


def test_hbm_effective_bandwidth_includes_supply_side_losses():
    effective_bw = Registry.variables["mem.hbm.bw_effective"]
    deps = {v.name for v in effective_bw.direct_dependencies()}
    assert deps == {
        "mem.hbm.bw",
        "mem.hbm.refresh_overhead",
        "mem.hbm.bank_conflict_overhead",
        "mem.hbm.controller_efficiency",
        "mem.hbm.thermal_derate",
    }

    result = resolve(
        "mem.hbm.bw_effective",
        assignments={
            "mem.hbm.bw": 1000.0,
            "mem.hbm.refresh_overhead": 0.05,
            "mem.hbm.bank_conflict_overhead": 0.20,
            "mem.hbm.controller_efficiency": 0.90,
            "mem.hbm.thermal_derate": 0.75,
        },
    )
    assert float(result.value) == pytest.approx(513.0)


def test_hbm_decomposition_equations_have_unit_checks():
    checked = {
        name
        for name, eq in Registry.equations.items()
        if getattr(eq, "_check_units_flag", False)
    }
    assert {
        "mem.eq.hbm_stack_capacity",
        "mem.eq.hbm_capacity",
        "mem.eq.hbm_pins_per_stack",
        "mem.eq.hbm_bw_per_channel",
        "mem.eq.hbm_bw_per_stack",
        "mem.eq.hbm_bw_total",
        "mem.eq.hbm_bw_effective",
        "mem.eq.hbm_capacity_usable",
        "mem.eq.hbm_capacity_effective",
    } <= checked
