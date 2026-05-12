"""
tests/test_facility_overhead_power_decomposition.py
===================================================

Facility non-cooling overhead power should be decomposed into narrow,
auditable primitives instead of opaque site-power roots.
"""

import pytest

import gpu_stack
from gpu_stack import Registry, resolve


def _deps(name):
    return {v.name for v in Registry.variables[name].direct_dependencies()}


def test_facility_overhead_power_terms_are_derived_from_primitives():
    expected = {
        "thermal.facility.ups_loss": {
            "cluster.site.power_it",
            "thermal.facility.ups_loss_fraction",
        },
        "thermal.facility.transformer_loss": {
            "cluster.site.power_it",
            "thermal.facility.transformer_loss_fraction",
        },
        "thermal.facility.lighting": {
            "cluster.site.n_racks",
            "thermal.facility.lighting_power_per_rack",
        },
        "thermal.facility.misc": {
            "cluster.site.power_it",
            "thermal.facility.misc_fraction",
        },
    }

    for name, deps in expected.items():
        variable = Registry.variables[name]
        assert not variable.is_root_input
        assert _deps(name) == deps


def test_facility_overhead_coefficients_remain_root_inputs():
    roots = {
        "thermal.facility.ups_loss_fraction",
        "thermal.facility.transformer_loss_fraction",
        "thermal.facility.lighting_power_per_rack",
        "thermal.facility.misc_fraction",
    }

    for name in roots:
        assert Registry.variables[name].is_root_input


def test_facility_overhead_components_resolve_from_primitives():
    cases = [
        (
            "thermal.facility.ups_loss",
            {
                "cluster.site.power_it": 1_000_000,
                "thermal.facility.ups_loss_fraction": 0.04,
            },
            40_000,
            "thermal.eq.ups_loss",
        ),
        (
            "thermal.facility.transformer_loss",
            {
                "cluster.site.power_it": 1_000_000,
                "thermal.facility.transformer_loss_fraction": 0.02,
            },
            20_000,
            "thermal.eq.transformer_loss",
        ),
        (
            "thermal.facility.lighting",
            {
                "cluster.site.n_racks": 128,
                "thermal.facility.lighting_power_per_rack": 250,
            },
            32_000,
            "thermal.eq.lighting",
        ),
        (
            "thermal.facility.misc",
            {
                "cluster.site.power_it": 1_000_000,
                "thermal.facility.misc_fraction": 0.01,
            },
            10_000,
            "thermal.eq.facility_misc",
        ),
    ]

    for target, assignments, expected, equation in cases:
        result = resolve(target, assignments=assignments)
        assert float(result.value) == pytest.approx(expected)
        assert equation in {step.equation for step in result.trace}


def test_dc_total_power_uses_decomposed_facility_overheads():
    result = resolve(
        "thermal.dc.total_power",
        assignments={
            "cluster.site.power_it": 1_000_000,
            "thermal.facility.cooling_power": 150_000,
            "thermal.facility.ups_loss_fraction": 0.04,
            "thermal.facility.transformer_loss_fraction": 0.02,
            "cluster.site.n_racks": 128,
            "thermal.facility.lighting_power_per_rack": 250,
            "thermal.facility.misc_fraction": 0.01,
        },
    )

    assert float(result.value) == pytest.approx(1_252_000)
    assert {
        "thermal.eq.ups_loss",
        "thermal.eq.transformer_loss",
        "thermal.eq.lighting",
        "thermal.eq.facility_misc",
        "thermal.eq.dc_total_power",
    } <= {step.equation for step in result.trace}


def test_facility_overhead_power_decomposition_does_not_introduce_cycles():
    assert gpu_stack.find_cycles() == []
