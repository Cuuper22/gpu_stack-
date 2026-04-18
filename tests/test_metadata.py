"""
tests/test_metadata.py
======================

Phase 2 metadata coverage checks.

The registry auto-classifies root-input Variables with `kind=ROOT_INPUT`
after all scopes load. These tests lock that behavior in, exercise the
new `Registry.by_kind` / `by_extensivity` / `coverage` query helpers,
and guard against regressions where a Variable with a defining relation
silently loses its classification.
"""

import gpu_stack
from gpu_stack import Registry
from gpu_stack.core import Constant, Extensivity, VariableKind


def test_root_inputs_are_classified_as_root_input():
    stats = Registry.stats()
    root_inputs_by_stats = stats["root_inputs"]
    root_inputs_by_kind = len(Registry.by_kind(VariableKind.ROOT_INPUT))
    assert root_inputs_by_kind == root_inputs_by_stats


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
    first = Registry.auto_classify_kinds()
    second = Registry.auto_classify_kinds()
    # First call may be zero if already classified; second must be zero.
    assert second == 0
    # Repeating it does not blow up the registry.
    assert len(Registry.variables) == 1147
