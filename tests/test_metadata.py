"""
tests/test_metadata.py
======================

After every scope module loads, the registry classifies each variable by
kind: a variable with no defining equation becomes ROOT_INPUT, physics
constants stay DEFINITIONAL, and anything with a defining relation is
derived. These tests lock in the rules that make the classification
trustworthy. Constraints do not count as definitions — a variable with
only inequality constraints (like thermal.t_ambient with its ASHRAE inlet
bounds) is still a root input, and its constraints create dependencies
only when you explicitly ask for them. The query helpers must partition
cleanly: by_kind and by_extensivity together cover every variable exactly
once, stats and coverage agree with direct counts, and running
auto_classify_kinds a second time changes nothing — classification is
idempotent, so re-importing scopes cannot corrupt the registry.
"""

import gpu_stack
from gpu_stack import Registry
from gpu_stack.core import Constant, Extensivity, VariableKind


def test_root_inputs_are_classified_as_root_input():
    stats = Registry.stats()
    root_inputs_by_stats = stats["root_inputs"]
    root_inputs_by_kind = len(Registry.by_kind(VariableKind.ROOT_INPUT))
    assert root_inputs_by_kind == root_inputs_by_stats


def test_constraint_only_variables_still_count_as_root_inputs():
    v = Registry.variables["thermal.t_ambient"]
    assert v.constraints()
    assert not v.identities()
    assert not v.approximations()
    assert not v.variants()
    assert v.is_root_input


def test_constraints_do_not_create_definitional_dependencies():
    v = Registry.variables["thermal.t_ambient"]
    assert v.direct_dependencies() == set()
    deps_with_constraints = {
        d.name for d in v.direct_dependencies(include_constraints=True)
    }
    assert {
        "thermal.env.ashrae_a1_inlet_min",
        "thermal.env.ashrae_a1_inlet_max",
    } <= deps_with_constraints


def test_derived_variables_are_not_tagged_root_input():
    # Pick a variable that is unambiguously derived in the graph.
    v = Registry.variables["cluster.rack.peak_flops"]
    assert v.defining_equations, "expected cluster.rack.peak_flops to have identities"
    assert v.kind != VariableKind.ROOT_INPUT


def test_constants_stay_definitional():
    constants = [v for v in Registry.variables.values() if isinstance(v, Constant)]
    assert constants, "expected at least one physics Constant"
    for c in constants:
        assert c.kind == VariableKind.DEFINITIONAL


def test_by_kind_round_trips_with_registry_counts():
    kinds = list(VariableKind)
    total = sum(len(Registry.by_kind(k)) for k in kinds)
    assert total == len(Registry.variables)


def test_by_extensivity_partitions_every_variable():
    extensivities = list(Extensivity)
    total = sum(len(Registry.by_extensivity(e)) for e in extensivities)
    assert total == len(Registry.variables)


def test_coverage_report_fields_present():
    cov = Registry.coverage()
    assert "non_constant_variables" in cov
    assert "with_sp_units" in cov
    assert "equations" in cov
    assert "equations_with_references" in cov
    assert cov["equations"] == len(Registry.equations)


def test_auto_classify_is_idempotent():
    before = len(Registry.variables)
    first = Registry.auto_classify_kinds()
    second = Registry.auto_classify_kinds()
    # First call may be zero if already classified; second must be zero.
    assert second == 0
    # Repeating it does not blow up the registry.
    assert len(Registry.variables) == before
