"""Tests for process-geometry feasibility constraints and their diagnostics.

Every derived process dimension — gate length, contact width, metal pitch,
node length, channel length — must be positive (or, for the gate-contact
spacing, at least zero) to describe a buildable chip. The graph states each
requirement as a named ``Inequality`` with the CONSTRAINT role, attached to
its variable and backed by a reference.

These tests check three things. The constraints exist in exactly that
explicit form, as real symbolic relations rather than pre-simplified truths.
When upstream inputs (a large negative bias, say) drive a derived dimension
negative, resolving it reports the matching constraint as failed instead of
silently returning a nonsense geometry. And the node-length equation keeps a
symbolic validity condition on its input pitches, so validity is evaluated
per scenario rather than assumed.
"""

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.core import Inequality, RelationRole
from tests.helpers.lithography import failed_constraint


def test_process_geometry_constraints_are_explicit_feasibility_relations():
    expected = {
        "physical.ineq.drawn_gate_length_positive": (
            "physical.process.drawn_gate_length"
        ),
        "physical.ineq.source_drain_contact_width_positive": (
            "physical.process.source_drain_contact_width"
        ),
        "physical.ineq.gate_contact_spacing_nonnegative": (
            "physical.process.gate_contact_spacing"
        ),
        "physical.ineq.contacted_gate_pitch_positive": (
            "physical.process.contacted_gate_pitch"
        ),
        "physical.ineq.minimum_metal_width_positive": (
            "physical.process.minimum_metal_width"
        ),
        "physical.ineq.minimum_metal_spacing_positive": (
            "physical.process.minimum_metal_spacing"
        ),
        "physical.ineq.minimum_metal_pitch_positive": (
            "physical.process.minimum_metal_pitch"
        ),
        "physical.ineq.process_node_length_positive": (
            "physical.process.node_length"
        ),
        "physical.ineq.channel_length_positive": "physical.channel_length",
    }

    for equation_name, variable_name in expected.items():
        eq = Registry.equations[equation_name]
        assert isinstance(eq, Inequality)
        assert eq.role is RelationRole.CONSTRAINT
        assert eq in Registry.variables[variable_name].constraints()
        assert eq.references
        assert not getattr(eq, "_check_units_flag", False)
        relation = eq.as_sympy()
        assert relation is not sp.S.true
        assert isinstance(relation, sp.Rel)


def test_process_geometry_constraints_report_negative_derived_dimensions():
    cases = [
        (
            "physical.process.drawn_gate_length",
            {
                "physical.lithography.gate_resolution": 1.0,
                "physical.process.gate_length_lithography_bias": -2.0,
            },
            -1.0,
            "physical.ineq.drawn_gate_length_positive",
        ),
        (
            "physical.process.source_drain_contact_width",
            {
                "physical.lithography.contact_resolution": 1.0,
                "physical.process.source_drain_contact_bias": -2.0,
            },
            -1.0,
            "physical.ineq.source_drain_contact_width_positive",
        ),
        (
            "physical.process.gate_contact_spacing",
            {
                "physical.process.gate_contact_overlay_budget": -2.0,
                "physical.process.gate_contact_enclosure_margin": 1.0,
            },
            -1.0,
            "physical.ineq.gate_contact_spacing_nonnegative",
        ),
        (
            "physical.process.minimum_metal_width",
            {
                "physical.lithography.metal_width_resolution": 1.0,
                "physical.process.minimum_metal_width_bias": -2.0,
            },
            -1.0,
            "physical.ineq.minimum_metal_width_positive",
        ),
        (
            "physical.process.minimum_metal_spacing",
            {
                "physical.lithography.metal_spacing_resolution": 1.0,
                "physical.process.minimum_metal_spacing_bias": -2.0,
            },
            -1.0,
            "physical.ineq.minimum_metal_spacing_positive",
        ),
        (
            "physical.process.contacted_gate_pitch",
            {
                "physical.process.drawn_gate_length": -4.0,
                "physical.process.source_drain_contact_width": 1.0,
                "physical.process.gate_contact_spacing": 1.0,
            },
            -1.0,
            "physical.ineq.contacted_gate_pitch_positive",
        ),
        (
            "physical.process.minimum_metal_pitch",
            {
                "physical.process.minimum_metal_width": -1.0,
                "physical.process.minimum_metal_spacing": 0.5,
            },
            -0.5,
            "physical.ineq.minimum_metal_pitch_positive",
        ),
        (
            "physical.process.node_length",
            {
                "physical.process.contacted_gate_pitch": 1.0,
                "physical.process.minimum_metal_pitch": 1.0,
                "physical.process.node_geometry_factor": -1.0,
            },
            -1.0,
            "physical.ineq.process_node_length_positive",
        ),
        (
            "physical.channel_length",
            {
                "physical.process.node_length": 1.0,
                "physical.process.gate_length_scale": 1.0,
                "physical.process.gate_length_bias": -2.0,
            },
            -1.0,
            "physical.ineq.channel_length_positive",
        ),
    ]

    for target, assignments, expected_value, constraint_name in cases:
        result = resolve(target, assignments=assignments)
        assert float(result.value) == pytest.approx(expected_value)
        failed_constraint(result, constraint_name)


def test_process_node_validity_stays_symbolic():
    eq = Registry.equations["physical.eq.process_node_from_pitches"]
    assert eq.validity is not True
    assert "CPP_proc" in str(eq.validity)
    assert "MMP_proc" in str(eq.validity)
