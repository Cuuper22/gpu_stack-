"""Verifies device and interconnect geometry is derived, not hand-tuned.

The temptation with geometry is to leave knobs like wire pitch, wire
length, or MOSFET width as bare numbers. This module keeps them derived:
pitch comes from process node length and metal pitch, wire length from
route span times a detour factor, transistor width from replicated channel
fins, oxide thickness from EOT and the dielectric ratio. Each test pins a
variable's exact dependency set, resolves a hand-checkable numeric case,
and checks that out-of-domain assignments (detour below 1, fractional hop
counts, fill factor outside (0, 1]) produce named constraint diagnostics.
"""

import pytest

from gpu_stack import Registry, resolve


def _violated_constraint(result, equation_name):
    for violation in result.violated_constraints:
        if violation.equation == equation_name:
            return violation
    observed = [violation.equation for violation in result.violated_constraints]
    pytest.fail(f"missing violated constraint {equation_name!r}; saw {observed!r}")


def test_interconnect_pitch_comes_from_process_scale():
    pitch = Registry.variables["physical.interconnect.pitch"]
    assert not pitch.is_root_input
    deps = {v.name for v in pitch.direct_dependencies()}
    assert deps == {
        "physical.process.node_length",
        "physical.interconnect.pitch_scale",
    }
    result = resolve(
        "physical.interconnect.pitch",
        assignments={
            "physical.process.node_length": 4.0,
            "physical.interconnect.pitch_scale": 10.0,
        },
    )
    assert float(result.value) == pytest.approx(40.0)


def test_interconnect_pitch_scale_comes_from_metal_pitch_layer():
    pitch_scale = Registry.variables["physical.interconnect.pitch_scale"]
    assert not pitch_scale.is_root_input
    deps = {v.name for v in pitch_scale.direct_dependencies()}
    assert deps == {
        "physical.interconnect.layer_pitch_factor",
        "physical.process.minimum_metal_pitch",
        "physical.process.node_length",
    }

    result = resolve(
        "physical.interconnect.pitch_scale",
        assignments={
            "physical.interconnect.layer_pitch_factor": 3.0,
            "physical.process.drawn_gate_length": 1.0,
            "physical.process.source_drain_contact_width": 1.0,
            "physical.process.gate_contact_spacing": 1.0,
            "physical.process.minimum_metal_width": 4.0,
            "physical.process.minimum_metal_spacing": 5.0,
            "physical.process.node_geometry_factor": 2.0,
        },
    )
    assert float(result.value) == pytest.approx(2.25)


def test_interconnect_pitch_resolves_through_metal_pitch_layer():
    result = resolve(
        "physical.interconnect.pitch",
        assignments={
            "physical.interconnect.layer_pitch_factor": 3.0,
            "physical.process.drawn_gate_length": 1.0,
            "physical.process.source_drain_contact_width": 1.0,
            "physical.process.gate_contact_spacing": 1.0,
            "physical.process.minimum_metal_width": 4.0,
            "physical.process.minimum_metal_spacing": 5.0,
            "physical.process.node_geometry_factor": 2.0,
        },
    )
    assert float(result.value) == pytest.approx(27.0)


def test_wire_length_comes_from_route_span_and_detour():
    wire = Registry.variables["physical.wire_length"]
    assert not wire.is_root_input
    deps = {v.name for v in wire.direct_dependencies()}
    assert deps == {
        "physical.interconnect.route_span",
        "physical.interconnect.route_detour_factor",
    }
    result = resolve(
        "physical.wire_length",
        assignments={
            "physical.interconnect.route_span": 7.0,
            "physical.interconnect.route_detour_factor": 1.5,
        },
    )
    assert float(result.value) == pytest.approx(10.5)


def test_interconnect_boundary_domains_are_declared_without_defaults():
    detour = Registry.variables["physical.interconnect.route_detour_factor"]
    hop_count = Registry.variables["physical.interconnect.route_hop_count"]
    layer_pitch = Registry.variables["physical.interconnect.layer_pitch_factor"]
    pitch_scale = Registry.variables["physical.interconnect.pitch_scale"]
    pitch = Registry.variables["physical.interconnect.pitch"]
    route_span = Registry.variables["physical.interconnect.route_span"]
    fill = Registry.variables["physical.interconnect.fill_factor"]
    wire_length = Registry.variables["physical.wire_length"]

    assert detour.is_root_input
    assert hop_count.is_root_input
    assert layer_pitch.is_root_input
    assert fill.is_root_input

    assert "physical.ineq.interconnect_route_detour_factor_at_least_unity" in {
        eq.name for eq in detour.constraints()
    }
    assert hop_count.assumptions.get("integer") is True
    assert hop_count.assumptions.get("nonnegative") is True
    assert layer_pitch.assumptions.get("positive") is True
    assert pitch_scale.assumptions.get("positive") is True
    assert pitch.assumptions.get("positive") is True
    assert route_span.assumptions.get("nonnegative") is True
    assert fill.assumptions.get("positive") is True
    assert fill.value_range == (0.0, 1.0)
    assert "physical.ineq.interconnect_route_length_positive" in {
        eq.name for eq in wire_length.constraints()
    }


def test_invalid_interconnect_detour_assignment_reports_constraint_diagnostic():
    result = resolve(
        "physical.interconnect.route_detour_factor",
        assignments={
            "physical.interconnect.route_detour_factor": 0.5,
        },
    )

    assert float(result.value) == pytest.approx(0.5)
    violation = _violated_constraint(
        result,
        "physical.ineq.interconnect_route_detour_factor_at_least_unity",
    )
    assert violation.variable == "physical.interconnect.route_detour_factor"
    assert "must not shorten" in violation.description
    assert float(violation.inputs["physical.interconnect.route_detour_factor"]) == (
        pytest.approx(0.5)
    )


def test_invalid_interconnect_hop_count_assignment_reports_domain_diagnostics():
    fractional = resolve(
        "physical.interconnect.route_span",
        assignments={
            "physical.interconnect.route_hop_count": 2.5,
            "physical.interconnect.pitch": 2.0,
        },
    )
    assert float(fractional.value) == pytest.approx(5.0)
    _violated_constraint(
        fractional,
        "domain.physical.interconnect.route_hop_count.integer",
    )

    negative = resolve(
        "physical.interconnect.route_span",
        assignments={
            "physical.interconnect.route_hop_count": -1,
            "physical.interconnect.pitch": 2.0,
        },
    )
    assert float(negative.value) == pytest.approx(-2.0)
    _violated_constraint(
        negative,
        "domain.physical.interconnect.route_hop_count.nonnegative",
    )


def test_invalid_interconnect_fill_factor_assignment_reports_domain_diagnostics():
    zero = resolve(
        "physical.interconnect.fill_factor",
        assignments={
            "physical.interconnect.fill_factor": 0.0,
        },
    )
    assert float(zero.value) == pytest.approx(0.0)
    _violated_constraint(
        zero,
        "domain.physical.interconnect.fill_factor.positive",
    )

    overfull = resolve(
        "physical.interconnect.fill_factor",
        assignments={
            "physical.interconnect.fill_factor": 1.25,
        },
    )
    assert float(overfull.value) == pytest.approx(1.25)
    _violated_constraint(
        overfull,
        "domain.physical.interconnect.fill_factor.max",
    )


def test_invalid_interconnect_pitch_and_route_length_report_diagnostics():
    bad_layer_pitch = resolve(
        "physical.interconnect.layer_pitch_factor",
        assignments={
            "physical.interconnect.layer_pitch_factor": 0.0,
        },
    )
    assert float(bad_layer_pitch.value) == pytest.approx(0.0)
    _violated_constraint(
        bad_layer_pitch,
        "domain.physical.interconnect.layer_pitch_factor.positive",
    )

    zero_pitch = resolve(
        "physical.interconnect.pitch",
        assignments={
            "physical.interconnect.pitch": 0.0,
        },
    )
    assert float(zero_pitch.value) == pytest.approx(0.0)
    _violated_constraint(
        zero_pitch,
        "domain.physical.interconnect.pitch.positive",
    )

    zero_length = resolve(
        "physical.wire_length",
        assignments={
            "physical.interconnect.route_span": 0.0,
            "physical.interconnect.route_detour_factor": 1.0,
        },
    )
    assert float(zero_length.value) == pytest.approx(0.0)
    _violated_constraint(
        zero_length,
        "physical.ineq.interconnect_route_length_positive",
    )


def test_mosfet_width_comes_from_replicated_channel_geometry():
    width = Registry.variables["physical.mosfet.width"]
    assert not width.is_root_input
    deps = {v.name for v in width.direct_dependencies()}
    assert deps == {
        "physical.mosfet.channel_parallel_count",
        "physical.mosfet.channel_unit_width",
        "physical.mosfet.channel_width_bias",
    }
    result = resolve(
        "physical.mosfet.width",
        assignments={
            "physical.mosfet.channel_parallel_count": 4,
            "physical.mosfet.channel_unit_width": 2.0,
            "physical.mosfet.channel_width_bias": -1.0,
        },
    )
    assert float(result.value) == pytest.approx(7.0)


def test_oxide_thickness_comes_from_eot_and_dielectric_ratio():
    tox = Registry.variables["physical.mosfet.oxide_thickness"]
    assert not tox.is_root_input
    deps = {v.name for v in tox.direct_dependencies()}
    assert deps == {
        "physical.mosfet.eot",
        "physical.mosfet.oxide_relative_permittivity",
        "physical.mosfet.sio2_relative_permittivity",
    }
    result = resolve(
        "physical.mosfet.oxide_thickness",
        assignments={
            "physical.mosfet.eot": 1.0,
            "physical.mosfet.oxide_relative_permittivity": 20.0,
            "physical.mosfet.sio2_relative_permittivity": 4.0,
        },
    )
    assert float(result.value) == pytest.approx(5.0)


def test_new_geometry_equations_have_unit_checks():
    checked = {
        name
        for name, eq in Registry.equations.items()
        if getattr(eq, "_check_units_flag", False)
    }
    assert {
        "physical.eq.interconnect_route_length",
        "physical.eq.interconnect_metal_pitch_scale",
        "physical.eq.interconnect_pitch_from_process",
        "physical.eq.mosfet_channel_width",
        "physical.eq.oxide_thickness_from_eot",
    } <= checked
