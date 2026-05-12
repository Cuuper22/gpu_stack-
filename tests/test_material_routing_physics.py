"""
tests/test_material_routing_physics.py
======================================

Regressions for the next physical-decomposition layer: material resistivity,
routing span, and interconnect capacitance density.
"""

import pytest

from gpu_stack import Registry, resolve


def test_resistivity_depends_on_material_temperature_and_size_factor():
    rho = Registry.variables["physical.resistivity"]
    assert not rho.is_root_input
    deps = {v.name for v in rho.direct_dependencies()}
    assert deps == {
        "physical.resistivity.reference",
        "physical.resistivity.temp_coeff",
        "physical.temperature",
        "physical.resistivity.reference_temperature",
        "physical.resistivity.size_factor",
    }
    result = resolve(
        "physical.resistivity",
        assignments={
            "physical.resistivity.reference": 2.0,
            "physical.resistivity.temp_coeff": 0.1,
            "physical.temperature": 12.0,
            "physical.resistivity.reference_temperature": 10.0,
            "physical.resistivity.size_factor": 3.0,
        },
    )
    assert float(result.value) == pytest.approx(7.2)


def test_route_span_depends_on_hop_count_and_pitch():
    span = Registry.variables["physical.interconnect.route_span"]
    assert not span.is_root_input
    deps = {v.name for v in span.direct_dependencies()}
    assert deps == {
        "physical.interconnect.route_hop_count",
        "physical.interconnect.pitch",
    }
    result = resolve(
        "physical.interconnect.route_span",
        assignments={
            "physical.interconnect.route_hop_count": 5,
            "physical.interconnect.pitch": 2.0,
        },
    )
    assert float(result.value) == pytest.approx(10.0)


def test_capacitance_per_length_depends_on_dielectric_and_geometry():
    cap = Registry.variables["physical.interconnect.c_per_length"]
    assert not cap.is_root_input
    deps = {v.name for v in cap.direct_dependencies()}
    assert deps == {
        "physical.interconnect.dielectric_permittivity",
        "physical.interconnect.fringe_cap_factor",
        "physical.interconnect.width",
        "physical.interconnect.spacing",
    }
    result = resolve(
        "physical.interconnect.c_per_length",
        assignments={
            "physical.interconnect.dielectric_permittivity": 10.0,
            "physical.interconnect.fringe_cap_factor": 2.0,
            "physical.interconnect.width": 3.0,
            "physical.interconnect.spacing": 5.0,
        },
    )
    assert float(result.value) == pytest.approx(12.0)


def test_interconnect_dielectric_permittivity_comes_from_relative_permittivity():
    dielectric = Registry.variables["physical.interconnect.dielectric_permittivity"]
    assert not dielectric.is_root_input
    deps = {v.name for v in dielectric.direct_dependencies()}
    assert deps == {
        "physical.interconnect.relative_permittivity",
        "physics.vacuum_permittivity",
    }

    result = resolve(
        "physical.interconnect.dielectric_permittivity",
        assignments={
            "physical.interconnect.relative_permittivity": 4.0,
        },
    )
    epsilon_0 = Registry.variables["physics.vacuum_permittivity"].value
    assert float(result.value) == pytest.approx(4.0 * epsilon_0)


def test_material_and_routing_equations_have_unit_checks():
    checked = {
        name
        for name, eq in Registry.equations.items()
        if getattr(eq, "_check_units_flag", False)
    }
    assert {
        "physical.eq.resistivity_temperature_size",
        "physical.eq.interconnect_route_span",
        "physical.eq.interconnect_dielectric_permittivity",
        "physical.eq.interconnect_c_per_length_geom",
    } <= checked
