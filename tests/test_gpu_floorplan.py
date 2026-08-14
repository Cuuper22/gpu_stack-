"""Verifies SM count has a floorplan model behind it, not just a spec number.

The SM (streaming multiprocessor) count of a GPU is usually copied from a
datasheet. Scenarios may still assign it directly, but the graph also
offers an approximation that derives it from die area, the fraction of the
die given to SM tiles, a redundancy fraction, and the area of one SM tile.
These tests confirm ``gpu.n_sms`` is not a root input, that its single
approximation equation reaches those area inputs, that a hand-checkable
case resolves to 36 SMs, and that the area capacity equation carries unit
metadata.
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
