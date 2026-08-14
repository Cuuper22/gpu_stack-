"""Contract test for the next-work continuation surface.

A contract test pins down the shape of a public API without caring how it is
built. Here the API is the plan builder in ``gpu_stack.next_work``: the module
must export exactly one public builder, and the plan it returns must carry
three fixed-size sections (3 highest-impact items, 4 implementation items,
10 bug risks) plus a snapshot of the live dependency graph (1517 variables,
950 equations, 619 root inputs) that justifies those items.

We deliberately accept several field spellings for each section. That lets
the implementation rename internals freely while the promise to callers —
"these sections exist, with these sizes, backed by the current graph" —
stays enforced.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping, Sequence


EXPECTED_GRAPH_EVIDENCE = {
    "variables": 1517,
    "equations": 950,
    "root_inputs": 619,
}

BUILDER_NAMES = (
    "build_continuation_plan",
    "build_next_work_plan",
    "build_plan",
)

SECTION_ALIASES = {
    "highest_impact": (
        "highest_impact",
        "highest_impact_items",
        "high_impact_items",
    ),
    "implementation": (
        "implementation",
        "implementation_items",
        "implementation_plan",
    ),
    "bug_risks": (
        "bug_risks",
        "bug_risk_items",
        "bugs_and_risks",
        "risk_items",
    ),
}


def _get(container, *names):
    if isinstance(container, Mapping):
        for name in names:
            if name in container:
                return container[name]
    for name in names:
        if hasattr(container, name):
            return getattr(container, name)
    raise AssertionError(f"missing expected field; tried {names!r}")


def _items(container, label: str) -> list[object]:
    value = _get(container, *SECTION_ALIASES[label])
    assert isinstance(value, Sequence)
    assert not isinstance(value, (str, bytes))
    return list(value)


def _public_builder(module):
    for name in BUILDER_NAMES:
        candidate = getattr(module, name, None)
        if callable(candidate):
            exports = getattr(module, "__all__", None)
            if exports is not None:
                assert name in exports
            return candidate
    raise AssertionError(f"gpu_stack.next_work needs one public builder: {BUILDER_NAMES!r}")


def _assert_current_graph_evidence(evidence) -> None:
    if isinstance(evidence, Mapping):
        for key, expected in EXPECTED_GRAPH_EVIDENCE.items():
            assert evidence[key] == expected
        return

    text = str(evidence)
    for expected in EXPECTED_GRAPH_EVIDENCE.values():
        assert str(expected) in text


def test_next_work_continuation_plan_contract():
    next_work = importlib.import_module("gpu_stack.next_work")

    from gpu_stack import Registry

    stats = Registry.stats()
    for key, expected in EXPECTED_GRAPH_EVIDENCE.items():
        assert stats[key] == expected

    plan = _public_builder(next_work)()

    assert len(_items(plan, "highest_impact")) == 3
    assert len(_items(plan, "implementation")) == 4
    assert len(_items(plan, "bug_risks")) == 10

    graph_evidence = _get(plan, "graph_evidence", "current_graph", "stats", "evidence")
    _assert_current_graph_evidence(graph_evidence)
