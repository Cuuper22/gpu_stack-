"""
tests/test_relation_roles.py
============================

Regression coverage for the Phase 0 semantic fixes.

Covers:
  * Inequality preservation. The two SRAM margin constraints must keep their
    Relational structure in `as_sympy()` and must not report as trivially
    true under current symbol assumptions.
  * Role-filtered defining-equation access. Each audited
    multi-definition variables from IMPROVEMENT_MAP.md must decompose
    cleanly into identities, constraints, approximations, and variants.
"""

import pytest
import sympy as sp

import gpu_stack
from gpu_stack import Equation, Inequality, Registry, RelationRole


def test_sram_read_margin_is_not_trivially_true():
    rel = Registry.equations["memcell.eq.sram_read_margin_constraint"]
    assert isinstance(rel, Inequality)
    assert rel.role is RelationRole.CONSTRAINT
    sym = rel.as_sympy()
    assert sym is not sp.S.true, "as_sympy() collapsed to True"
    assert isinstance(sym, sp.Rel), "as_sympy() did not return a Relational"
    assert not rel.is_trivially_true(), (
        "snm_read >= 0 resolves vacuously; underlying symbol is still "
        "declared positive."
    )


def test_sram_write_margin_is_not_trivially_true():
    rel = Registry.equations["memcell.eq.sram_write_margin_constraint"]
    assert isinstance(rel, Inequality)
    assert rel.role is RelationRole.CONSTRAINT
    sym = rel.as_sympy()
    assert sym is not sp.S.true
    assert isinstance(sym, sp.Rel)
    assert not rel.is_trivially_true()


def test_no_inequality_collapses_to_true():
    collapsed = [
        e.name
        for e in Registry.equations.values()
        if isinstance(e, Inequality) and e.as_sympy() is sp.S.true
    ]
    assert collapsed == [], (
        "Inequalities that still collapse to True: " + ", ".join(collapsed)
    )


# Each tuple: (variable_name, expected_identity_count, expected_constraint_count,
#              expected_approximation_count, expected_variant_count)
# The counts reflect the audited variables from IMPROVEMENT_MAP.md after
# role tagging in this batch.
MULTI_DEFINITION_EXPECTATIONS = [
    ("physical.lithography.source_plasma_species_number_density", 0, 1, 1, 0),
    ("physical.lithography.source_plasma_species_thermal_speed", 0, 2, 1, 0),
    ("physical.lithography.source_plasma_drive_acceptance_half_angle", 0, 1, 1, 0),
    ("physical.lithography.source_plasma_drive_pulse_duration", 0, 1, 1, 0),
    ("physical.lithography.source_plasma_drive_peak_intensity", 0, 1, 1, 0),
    ("physical.lithography.source_plasma_drive_pulse_rise_fraction", 0, 2, 0, 0),
    ("physical.lithography.source_plasma_drive_pulse_fall_fraction", 0, 2, 1, 0),
    ("physical.lithography.source_plasma_drive_pulse_flat_fraction", 0, 1, 1, 0),
    ("physical.lithography.source_plasma_drive_pulse_temporal_shape_factor", 0, 1, 1, 0),
    ("physical.lithography.source_plasma_drive_far_field_divergence_half_angle", 0, 2, 0, 0),
    ("physical.lithography.source_plasma_drive_beam_parameter_product", 0, 1, 1, 0),
    ("physical.lithography.source_plasma_drive_beam_quality_factor", 0, 1, 1, 0),
    ("physical.lithography.source_plasma_drive_spot_area", 0, 1, 1, 0),
    ("physical.lithography.acceptance_half_angle", 0, 1, 1, 0),
    ("physical.lithography.numerical_aperture", 0, 1, 1, 0),
    ("physical.lithography.source_nuclear_mass", 1, 1, 0, 0),
    ("physical.lithography.source_reduced_mass", 1, 1, 0, 0),
    ("physical.lithography.source_reduced_mass_ratio", 1, 1, 0, 0),
    (
        "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count",
        0,
        2,
        0,
        0,
    ),
    ("physical.lithography.medium_polarizable_electron_fraction", 0, 1, 1, 0),
    ("physical.lithography.medium_dominant_oscillator_electron_count", 0, 2, 0, 0),
    ("physical.lithography.medium_oscillator_sum_rule_fraction", 0, 1, 1, 0),
    ("physical.lithography.medium_resonance_to_source_frequency_ratio", 0, 1, 1, 0),
    ("physical.process.drawn_gate_length", 0, 1, 1, 0),
    ("physical.process.source_drain_contact_width", 0, 1, 1, 0),
    ("physical.process.gate_contact_spacing", 0, 1, 1, 0),
    ("physical.process.contacted_gate_pitch", 0, 1, 1, 0),
    ("physical.process.minimum_metal_width", 0, 1, 1, 0),
    ("physical.process.minimum_metal_spacing", 0, 1, 1, 0),
    ("physical.process.minimum_metal_pitch", 0, 1, 1, 0),
    ("physical.process.node_length", 0, 1, 1, 0),
    ("physical.channel_length", 0, 1, 1, 0),
    ("physical.wire_length", 1, 1, 0, 0),
    ("physical.drift_velocity",            1, 0, 1, 0),
    ("physical.mosfet.width", 1, 1, 0, 0),
    ("physical.mosfet.subthreshold_swing", 1, 1, 0, 0),
    ("physical.gate.elmore_delay",         1, 1, 0, 0),
    ("physical.power.total_gate",          1, 1, 0, 0),
    ("memcell.sram.snm_read",              1, 1, 0, 0),
    ("memcell.sram.wnm_write",             1, 1, 0, 0),
    ("memcell.dram.refresh_period",        1, 1, 0, 0),
    ("memcell.dram.v_dev",                 1, 1, 0, 0),
    ("opt.schedule.total_steps",           0, 3, 0, 0),
    ("opt.param_next",                     0, 0, 0, 2),
    ("training.flops_per_step",            0, 0, 0, 2),
    ("training.mfu",                       0, 0, 0, 2),
    ("training.scaling_params",            0, 0, 0, 2),
    ("thermal.t_ambient",                  0, 2, 0, 0),
    ("thermal.env.relative_humidity",      0, 2, 0, 0),
    ("thermal.env.dew_point_headroom",     1, 1, 0, 0),
]


def test_multi_definition_variables_have_role_coverage():
    mismatches = []
    for name, n_id, n_cs, n_ap, n_va in MULTI_DEFINITION_EXPECTATIONS:
        v = Registry.variables[name]
        got = (
            len(v.identities()),
            len(v.constraints()),
            len(v.approximations()),
            len(v.variants()),
        )
        expected = (n_id, n_cs, n_ap, n_va)
        if got != expected:
            mismatches.append((name, expected, got))
    assert not mismatches, (
        "Role coverage mismatch for multi-definition variables: "
        + "; ".join(f"{n}: expected {e}, got {g}" for n, e, g in mismatches)
    )


def test_multi_definition_variables_all_accounted_for():
    expected_names = {name for name, *_ in MULTI_DEFINITION_EXPECTATIONS}
    actual_names = {
        name
        for name, variable in Registry.variables.items()
        if variable.has_multiple_definitions()
    }
    assert actual_names == expected_names

    for name, *_ in MULTI_DEFINITION_EXPECTATIONS:
        v = Registry.variables[name]
        total = len(v.defining_equations)
        role_sum = (
            len(v.identities())
            + len(v.constraints())
            + len(v.approximations())
            + len(v.variants())
        )
        assert total == role_sum, (
            f"{name}: defining_equations ({total}) not fully classified by "
            f"role accessors ({role_sum})."
        )


def test_variant_keys_are_distinct_per_variable():
    for name, _, _, _, n_va in MULTI_DEFINITION_EXPECTATIONS:
        if n_va < 2:
            continue
        v = Registry.variables[name]
        keys = [e.variant for e in v.variants()]
        assert None not in keys, f"{name}: variant missing key"
        assert len(set(keys)) == len(keys), f"{name}: duplicate variant keys {keys}"


def test_variant_constructor_rejects_missing_key():
    with pytest.raises(ValueError, match="VARIANT relations require"):
        Equation(
            "test.eq.variant_missing_key",
            sp.Symbol("variant_missing_key_lhs"),
            sp.Integer(1),
            "Temporary malformed variant relation.",
            role=RelationRole.VARIANT,
        )


def test_constructor_rejects_variant_key_on_non_variant_relation():
    with pytest.raises(ValueError, match="only allowed on VARIANT"):
        Equation(
            "test.eq.variant_key_on_identity",
            sp.Symbol("variant_key_on_identity_lhs"),
            sp.Integer(1),
            "Temporary malformed identity relation.",
            variant="ghost",
        )


def test_constructor_rejects_non_bare_value_lhs():
    with pytest.raises(ValueError, match="bare-variable LHS"):
        Equation(
            "test.eq.non_bare_value_lhs",
            sp.Symbol("non_bare_value_lhs_x")
            + sp.Symbol("non_bare_value_lhs_y"),
            sp.Integer(1),
            "Temporary non-bare value-defining relation.",
        )


def test_inequality_rejects_value_variant_role():
    with pytest.raises(ValueError, match="Inequality relations must use CONSTRAINT"):
        Inequality(
            "test.ineq.variant_role",
            sp.Symbol("inequality_variant_lhs"),
            sp.Integer(1),
            "<=",
            "Temporary malformed inequality variant.",
            role=RelationRole.VARIANT,
            variant="bad",
        )
