"""Tests the occupancy-driven latency-hiding model for kernels.

A GPU hides memory latency by switching between warps: with enough
resident warps (occupancy), loads overlap and cost nothing extra; with too
few, the SM stalls. The model captures this as latency_hiding_factor =
min(1, occupancy / full_hide_occupancy). These tests pin that exact
formula — including its direction, since the inverted form is a plausible
bug — check the (0, 1] domains, show halving occupancy doubles
latency-bound time (100 to 200 time units), confirm the factor saturates
at 1 above the full-hide point, and verify zero occupancy trips the domain
constraints.
"""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve


def test_latency_hiding_factor_is_occupancy_efficiency():
    occupancy = Registry.variables["kernel.occupancy"]
    occ_full = Registry.variables["kernel.occupancy.full_hide"]
    relation = Registry.equations["kernel.eq.latency_hiding_factor"]

    assert relation.rhs == sp.Min(sp.Integer(1), occupancy.symbol / occ_full.symbol)
    assert relation.rhs != 1 / sp.Min(sp.Integer(1), occupancy.symbol / occ_full.symbol)


def test_latency_hiding_variables_have_positive_fraction_domains():
    for variable_name in (
        "kernel.occupancy",
        "kernel.occupancy.full_hide",
        "kernel.latency_hiding_factor",
    ):
        variable = Registry.variables[variable_name]
        assert variable.assumptions.get("positive") is True
        assert variable.value_range == (0.0, 1.0)


def test_low_occupancy_increases_latency_bound_time():
    common = {
        "kernel.global_load_count": 100,
        "mem.global_load.latency_avg": 1.0,
        "kernel.occupancy.full_hide": 0.5,
    }

    low = resolve(
        "kernel.time_latency_bound",
        assignments={**common, "kernel.occupancy": 0.25},
    )
    full = resolve(
        "kernel.time_latency_bound",
        assignments={**common, "kernel.occupancy": 0.5},
    )

    assert float(low.values["kernel.latency_hiding_factor"]) == pytest.approx(0.5)
    assert float(full.values["kernel.latency_hiding_factor"]) == pytest.approx(1.0)
    assert float(low.value) == pytest.approx(200.0)
    assert float(full.value) == pytest.approx(100.0)
    assert float(low.value) > float(full.value)


def test_latency_hiding_saturates_at_full_hide_occupancy():
    result = resolve(
        "kernel.time_latency_bound",
        assignments={
            "kernel.global_load_count": 100,
            "mem.global_load.latency_avg": 1.0,
            "kernel.occupancy": 0.75,
            "kernel.occupancy.full_hide": 0.5,
        },
    )

    assert float(result.values["kernel.latency_hiding_factor"]) == pytest.approx(1.0)
    assert float(result.value) == pytest.approx(100.0)


def test_zero_occupancy_reports_domain_violations():
    result = resolve(
        "kernel.latency_hiding_factor",
        assignments={
            "kernel.occupancy": 0.0,
            "kernel.occupancy.full_hide": 0.5,
        },
    )

    assert float(result.value) == pytest.approx(0.0)
    failed = {
        check.equation
        for check in result.constraints
        if check.satisfied is False
    }
    assert "domain.kernel.occupancy.positive" in failed
    assert "domain.kernel.latency_hiding_factor.positive" in failed
