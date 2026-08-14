"""Basic structural health checks for the whole dependency graph.

The entire model rests on the graph being a DAG — a directed graph with no
cycles — because resolution walks dependencies to a fixed bottom. These
tests fail fast if any scope change breaks that: no cycles anywhere (the
old thermal cycle is the historical culprit), a topological sort that
covers every variable, and root/leaf counts that agree with the registry's
own statistics.
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
