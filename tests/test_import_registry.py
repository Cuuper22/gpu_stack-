"""Pins the registry's published size and proves it can rebuild from empty.

PUBLISHED_SNAPSHOT records the exact counts the project advertises — 1316
variables, 733 equations, 603 root inputs, and the rest. Any scope change
that adds or removes a variable moves these numbers, and that is the
point: the change must be seen and the snapshot updated deliberately. If a
change legitimately moves the numbers, update the expectations here — never
delete the assertions. The second test resets the registry to zero and
bootstraps it back, proving the full graph is reconstructible from code
alone.
"""

import gpu_stack
from gpu_stack import Registry
from gpu_stack.core import VariableKind


PUBLISHED_SNAPSHOT = {
    "systems": 17,
    "variables": 1316,
    "constants": 18,
    "equations": 733,
    "root_inputs": 603,
    "leaves": 251,
    "topological_order_length": 1316,
    "with_sp_units": 1298,
    "with_references": 1298,
    "equations_with_references": 733,
    "equations_with_unit_check": 670,
    "root_kind": 603,
    "derived_kind": 695,
    "measured_kind": 0,
    "definitional_kind": 18,
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
    try:
        Registry.reset()
        assert Registry.stats()["variables"] == 0
        after = gpu_stack.bootstrap()
        assert after == before
        assert len(gpu_stack.topological_sort()) == before["variables"]
    finally:
        gpu_stack.bootstrap()
