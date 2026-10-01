"""Tests for the process-geometry resolver paths and their unit checks.

Channel length — the physical length of a transistor's gate channel — can be
resolved at three depths, depending on which inputs a scenario pins. Pin the
node length directly and one equation finishes the job. Pin the drawn
dimensions and the resolver goes through the pitch layer: contacted gate
pitch and minimum metal pitch combine into node length first. Pin only
wavelength, numerical aperture, and the k1 process factors and the resolver
descends into lithography, printing the feature sizes before any pitch exists. These tests exercise each path against hand-computed
values and confirm the trace shows the expected equations.

The remaining tests assert that the equations along these paths carry unit
checks, so a dimensional mistake anywhere in the stack fails at registration.
"""

import pytest

from gpu_stack import Registry, resolve


def test_resolve_channel_length_from_process_geometry():
    result = resolve(
        "physical.channel_length",
        assignments={
            "physical.process.node_length": 4.0,
            "physical.process.gate_length_scale": 1.2,
            "physical.process.gate_length_bias": -0.5,
        },
    )
    assert float(result.value) == pytest.approx(4.3)
    assert any(step.equation == "physical.eq.channel_length_process" for step in result.trace)


def test_resolve_channel_length_through_process_pitch_layer():
    result = resolve(
        "physical.channel_length",
        assignments={
            "physical.process.drawn_gate_length": 1.0,
            "physical.process.source_drain_contact_width": 1.0,
            "physical.process.gate_contact_spacing": 1.0,
            "physical.process.minimum_metal_width": 4.0,
            "physical.process.minimum_metal_spacing": 5.0,
            "physical.process.node_geometry_factor": 2.0,
            "physical.process.gate_length_scale": 0.5,
            "physical.process.gate_length_bias": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(7.0)


def test_resolve_channel_length_through_lithography_layer():
    numerical_aperture = 3.0 ** 0.5
    wavelength = 10.0
    gate_k1 = 0.8
    gate_cd = gate_k1 * wavelength / numerical_aperture
    contact_cd = gate_k1 * wavelength / numerical_aperture
    metal_width_cd = gate_k1 * wavelength / numerical_aperture
    metal_spacing_cd = gate_k1 * wavelength / numerical_aperture
    cpp = (gate_cd + 1.0) + (contact_cd + 1.0) + 2 * (0.5 + 1.0)
    mmp = metal_width_cd + metal_spacing_cd
    expected = 1.0 + 0.5 * 2.0 * (cpp * mmp) ** 0.5
    result = resolve(
        "physical.channel_length",
        assignments={
            "physical.lithography.wavelength": wavelength,
            "physical.lithography.numerical_aperture": numerical_aperture,
            "physical.lithography.gate_k1_aerial_image_contrast_factor": 0.5,
            "physical.lithography.gate_k1_resist_process_factor": 0.7,
            "physical.lithography.gate_k1_mask_error_factor": 0.8,
            "physical.lithography.gate_k1_resolution_enhancement_factor": 1.4,
            "physical.process.gate_length_lithography_bias": 1.0,
            "physical.process.source_drain_contact_bias": 1.0,
            "physical.process.gate_contact_overlay_budget": 0.5,
            "physical.process.gate_contact_enclosure_margin": 1.0,
            "physical.process.minimum_metal_width_bias": 0.0,
            "physical.process.minimum_metal_spacing_bias": 0.0,
            "physical.process.node_geometry_factor": 2.0,
            "physical.process.gate_length_scale": 0.5,
            "physical.process.gate_length_bias": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(expected)
    assert any(
        step.equation == "physical.eq.lithography_gate_k1_from_process_factors"
        for step in result.trace
    )
    assert {
        "physical.eq.contact_k1_from_gate_baseline",
        "physical.eq.metal_width_k1_from_gate_baseline",
        "physical.eq.metal_spacing_k1_from_gate_baseline",
    } <= {step.equation for step in result.trace}


def test_channel_length_process_equation_has_unit_check():
    eq = Registry.equations["physical.eq.channel_length_process"]
    assert getattr(eq, "_check_units_flag", False)
    assert Registry.variables["physical.process.gate_length_bias"].signed is True


def test_process_node_pitch_equation_has_unit_check():
    eq = Registry.equations["physical.eq.process_node_from_pitches"]
    assert getattr(eq, "_check_units_flag", False)


def test_process_pitch_component_equations_have_unit_checks():
    checked = {
        name
        for name, eq in Registry.equations.items()
        if getattr(eq, "_check_units_flag", False)
    }
    assert {
        "physical.eq.lithography_gate_k1_from_process_factors",
        "physical.eq.gate_lithography_resolution",
        "physical.eq.contact_lithography_resolution",
        "physical.eq.metal_width_lithography_resolution",
        "physical.eq.metal_spacing_lithography_resolution",
        "physical.eq.drawn_gate_length",
        "physical.eq.source_drain_contact_width",
        "physical.eq.gate_contact_spacing",
        "physical.eq.minimum_metal_width",
        "physical.eq.minimum_metal_spacing",
        "physical.eq.contacted_gate_pitch",
        "physical.eq.minimum_metal_pitch",
    } <= checked
