"""
tests/test_gpu_floorplan.py
===========================

The GPU scope should not treat SM count as an irreducible primitive. It can
still be assigned directly in scenarios, but the graph also exposes a deeper
floorplanning approximation from die area and per-SM tile area.
"""

import pytest

from gpu_stack import Registry, resolve
from gpu_stack.core import RelationRole


def test_n_sms_has_floorplan_approximation():
    n_sms = Registry.variables["gpu.n_sms"]
    assert not n_sms.is_root_input
    approximations = n_sms.approximations()
    assert len(approximations) == 1
    eq = approximations[0]
    assert eq.name == "gpu.eq.n_sms_floorplan"
    assert eq.role is RelationRole.APPROXIMATION


def test_n_sms_floorplan_dependencies_reach_area_inputs():
    deps = {v.name for v in Registry.variables["gpu.n_sms"].dependencies()}
    assert {
        "gpu.die.area",
        "gpu.floorplan.sm_area_fraction",
        "gpu.floorplan.sm_redundancy_fraction",
        "gpu.sm.tile_area",
    } <= deps


def test_resolve_n_sms_from_floorplan_inputs():
    result = resolve(
        "gpu.n_sms",
        assignments={
            "gpu.die.area": 100.0,
            "gpu.floorplan.sm_area_fraction": 0.80,
            "gpu.floorplan.sm_redundancy_fraction": 0.10,
            "gpu.sm.tile_area": 2.0,
        },
    )
    assert float(result.value) == pytest.approx(36.0)
    assert any(step.equation == "gpu.eq.n_sms_floorplan" for step in result.trace)


def test_n_sms_area_capacity_has_unit_metadata():
    eq = Registry.equations["gpu.eq.n_sms_area_capacity"]
    assert getattr(eq, "_check_units_flag", False)
    assert Registry.variables["gpu.die.area"].sp_units is not None
    assert Registry.variables["gpu.sm.tile_area"].sp_units is not None
