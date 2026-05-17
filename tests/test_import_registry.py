"""
Registry import snapshot and bootstrap coverage.

If a scope change legitimately moves the published numbers, update the
expectations here rather than deleting the assertions.
"""

import gpu_stack
from gpu_stack import Registry
from gpu_stack.core import VariableKind


PUBLISHED_SNAPSHOT = {
    "systems": 16,
    "variables": 1517,
    "constants": 24,
    "equations": 959,
    "root_inputs": 619,
    "leaves": 253,
    "topological_order_length": 1517,
    "with_sp_units": 1428,
    "with_references": 1324,
    "equations_with_references": 878,
    "equations_with_unit_check": 799,
    "root_kind": 619,
    "derived_kind": 874,
    "measured_kind": 0,
    "definitional_kind": 24,
}


def test_registry_stats_match_snapshot():
    stats = Registry.stats()
    expected_stats = {
        key: PUBLISHED_SNAPSHOT[key]
        for key in (
            "systems",
            "variables",
            "constants",
            "equations",
            "root_inputs",
            "leaves",
        )
    }
    assert stats == expected_stats

    coverage = Registry.coverage()
    assert (
        len(gpu_stack.topological_sort())
        == PUBLISHED_SNAPSHOT["topological_order_length"]
    )
    assert coverage["with_sp_units"] == PUBLISHED_SNAPSHOT["with_sp_units"]
    assert coverage["with_references"] == PUBLISHED_SNAPSHOT["with_references"]
    assert (
        coverage["equations_with_references"]
        == PUBLISHED_SNAPSHOT["equations_with_references"]
    )
    assert (
        coverage["equations_with_unit_check"]
        == PUBLISHED_SNAPSHOT["equations_with_unit_check"]
    )
    assert (
        len(Registry.by_kind(VariableKind.ROOT_INPUT))
        == PUBLISHED_SNAPSHOT["root_kind"]
    )
    assert (
        len(Registry.by_kind(VariableKind.DERIVED))
        == PUBLISHED_SNAPSHOT["derived_kind"]
    )
    assert (
        len(Registry.by_kind(VariableKind.MEASURED))
        == PUBLISHED_SNAPSHOT["measured_kind"]
    )
    assert (
        len(Registry.by_kind(VariableKind.DEFINITIONAL))
        == PUBLISHED_SNAPSHOT["definitional_kind"]
    )


def test_registry_reset_can_bootstrap_back_to_full_graph():
    before = Registry.stats()
    Registry.reset()
    assert Registry.stats()["variables"] == 0
    after = gpu_stack.bootstrap()
    assert after == before
    assert len(gpu_stack.topological_sort()) == before["variables"]
