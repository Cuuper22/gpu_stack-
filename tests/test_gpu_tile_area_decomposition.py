"""Verifies the SM tile area is a named area budget, not one opaque number.

The area of one SM tile feeds the floorplan SM-count model, so leaving it
as a single high-fanout root would hide a lot of structure. Instead it is a
budget: tensor cores (count times area per unit), register file, shared
memory, scheduler control, and local interconnect sum to an active area,
which overhead and layout-utilization factors inflate to the full tile.
These tests pin that dependency tree, resolve a hand-checkable case to
8.8 area units through the exact three-equation trace, chain the budget
into the SM-count model, and keep unit checks, references, and an acyclic
graph.
"""

import pytest

import gpu_stack
from gpu_stack import Registry, resolve


def test_sm_tile_area_is_decomposed_into_named_budget_terms():
    tile_area = Registry.variables["gpu.sm.tile_area"]
    assert not tile_area.is_root_input
    assert {v.name for v in tile_area.direct_dependencies()} == {
        "gpu.sm.tile_active_area",
        "gpu.sm.tile_layout_utilization",
        "gpu.sm.tile_overhead_fraction",
    }

    active_area = Registry.variables["gpu.sm.tile_active_area"]
    assert {v.name for v in active_area.direct_dependencies()} == {
        "gpu.sm.tensor_core_area",
        "gpu.sm.register_file_area",
        "gpu.sm.shared_memory_area",
        "gpu.sm.scheduler_control_area",
        "gpu.sm.local_interconnect_area",
    }

    tensor_area = Registry.variables["gpu.sm.tensor_core_area"]
    assert {v.name for v in tensor_area.direct_dependencies()} == {
        "arith.tc.per_sm",
        "gpu.sm.tensor_core_area_per_unit",
    }


def test_resolve_sm_tile_area_from_symbolic_budget():
    result = resolve(
        "gpu.sm.tile_area",
        assignments={
            "arith.tc.per_sm": 4,
            "gpu.sm.tensor_core_area_per_unit": 0.5,
            "gpu.sm.register_file_area": 1.0,
            "gpu.sm.shared_memory_area": 1.5,
            "gpu.sm.scheduler_control_area": 0.25,
            "gpu.sm.local_interconnect_area": 0.75,
            "gpu.sm.tile_overhead_fraction": 0.20,
            "gpu.sm.tile_layout_utilization": 0.75,
        },
    )

    assert float(result.value) == pytest.approx(8.8)
    assert [step.equation for step in result.trace] == [
        "gpu.eq.sm_tensor_core_area",
        "gpu.eq.sm_tile_active_area",
        "gpu.eq.sm_tile_area",
    ]


def test_resolve_n_sms_can_use_tile_area_budget():
    result = resolve(
        "gpu.n_sms",
        assignments={
            "gpu.die.area": 100.0,
            "gpu.floorplan.sm_area_fraction": 0.80,
            "gpu.floorplan.sm_redundancy_fraction": 0.10,
            "arith.tc.per_sm": 4,
            "gpu.sm.tensor_core_area_per_unit": 0.125,
            "gpu.sm.register_file_area": 0.4,
            "gpu.sm.shared_memory_area": 0.5,
            "gpu.sm.scheduler_control_area": 0.2,
            "gpu.sm.local_interconnect_area": 0.4,
            "gpu.sm.tile_overhead_fraction": 0.0,
            "gpu.sm.tile_layout_utilization": 1.0,
        },
    )

    assert float(result.value) == pytest.approx(36.0)
    assert any(step.equation == "gpu.eq.sm_tile_area" for step in result.trace)
    assert any(step.equation == "gpu.eq.n_sms_floorplan" for step in result.trace)


def test_sm_tile_area_decomposition_keeps_unit_checks_and_acyclic_graph():
    checked = {
        name
        for name, eq in Registry.equations.items()
        if getattr(eq, "_check_units_flag", False)
    }
    assert {
        "gpu.eq.sm_tensor_core_area",
        "gpu.eq.sm_tile_active_area",
        "gpu.eq.sm_tile_area",
    } <= checked
    assert gpu_stack.find_cycles() == []


def test_sm_tile_budget_reference_metadata_is_present():
    assert Registry.variables["gpu.sm.tile_area"].references
    assert Registry.equations["gpu.eq.sm_tile_area"].references
    assert Registry.equations["gpu.eq.n_sms_floorplan"].references
