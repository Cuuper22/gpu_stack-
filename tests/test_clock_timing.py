"""
tests/test_clock_timing.py
==========================

Clock frequency should not be an irreducible primitive. The physical scope now
models a timing-limited maximum clock and a derated operating clock.
"""

import pytest

from gpu_stack import Registry, resolve
from gpu_stack.core import RelationRole


def test_clock_frequency_has_timing_model():
    f_clock = Registry.variables["physical.clock_frequency"]
    assert not f_clock.is_root_input
    approximations = f_clock.approximations()
    assert len(approximations) == 1
    eq = approximations[0]
    assert eq.name == "physical.eq.clock_frequency_timing_model"
    assert eq.role is RelationRole.APPROXIMATION


def test_clock_frequency_dependencies_reach_critical_path():
    deps = {v.name for v in Registry.variables["physical.clock_frequency"].dependencies()}
    assert {
        "physical.gate.elmore_delay",
        "physical.clock.max_timing_frequency",
        "physical.clock.derate",
    } <= deps


def test_resolve_clock_from_assigned_critical_path_delay():
    result = resolve(
        "physical.clock_frequency",
        assignments={
            "physical.gate.elmore_delay": 2.0,
            "physical.clock.derate": 0.8,
        },
    )
    assert float(result.value) == pytest.approx(0.4)
    assert any(
        step.equation == "physical.eq.clock_frequency_timing_model"
        for step in result.trace
    )


def test_clock_timing_equations_have_unit_checks():
    checked = {
        name
        for name, eq in Registry.equations.items()
        if getattr(eq, "_check_units_flag", False)
    }
    assert "physical.eq.clock_max_timing_frequency" in checked
    assert "physical.eq.clock_frequency_timing_model" in checked
