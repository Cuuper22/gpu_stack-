"""
tests/test_next_work_continuation_contract.py
==============================================

Contract test for the next-work continuation surface. The implementation may
choose exact item wording, but the public builder should expose the active
objective shape and the current graph snapshot that justifies it.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping, Sequence


EXPECTED_GRAPH_EVIDENCE = {
    "variables": 1517,
    "equations": 959,
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
