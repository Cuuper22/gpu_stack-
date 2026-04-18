"""
tests/test_relation_roles.py
============================

Regression coverage for the Phase 0 semantic fixes.

Covers:
  * Inequality preservation. The two SRAM margin constraints must keep their
    Relational structure in `as_sympy()` and must not report as trivially
    true under current symbol assumptions.
  * Role-filtered defining-equation access. Each of the 15 audited
    multi-definition variables from IMPROVEMENT_MAP.md must decompose
    cleanly into identities, constraints, approximations, and variants.
"""

import sympy as sp

import gpu_stack
from gpu_stack import Inequality, Registry, RelationRole


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
# The counts reflect the 15 audited variables from IMPROVEMENT_MAP.md after
# role tagging in this batch.
MULTI_DEFINITION_EXPECTATIONS = [
    ("physical.drift_velocity",            1, 0, 1, 0),
    ("physical.mosfet.subthreshold_swing", 1, 1, 0, 0),
    ("physical.gate.elmore_delay",         1, 1, 0, 0),
    ("physical.power.total_gate",          1, 1, 0, 0),
    ("memcell.sram.snm_read",              1, 1, 0, 0),
    ("memcell.sram.wnm_write",             1, 1, 0, 0),
    ("memcell.dram.refresh_period",        1, 1, 0, 0),
    ("memcell.dram.v_dev",                 1, 1, 0, 0),
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
