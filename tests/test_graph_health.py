"""
tests/test_graph_health.py
==========================

The package ships without cycles and with a topological order that covers
every Variable. These tests fail fast if a scope change reintroduces the
old thermal cycle or breaks acyclicity in any other way.
"""

import gpu_stack
from gpu_stack import Registry


def test_no_cycles():
    cycles = gpu_stack.find_cycles()
    assert cycles == [], (
        "Cycles detected. Name each cycle: "
        + "; ".join(" -> ".join(v.name for v in c) for c in cycles)
    )


def test_topological_sort_covers_all_variables():
    order = gpu_stack.topological_sort()
    assert len(order) == len(Registry.variables)


def test_roots_match_stats():
    stats = Registry.stats()
    assert len(Registry.roots()) == stats["root_inputs"]
    assert len(Registry.leaves()) == stats["leaves"]
