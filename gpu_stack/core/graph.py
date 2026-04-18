"""
core/graph.py
=============

Dependency graph utilities.

  * topological_sort: order Variables so dependencies come before dependents.
  * find_cycles: detect any circular dependencies (helps debug bad equations).
  * to_dot: export the dependency graph as Graphviz DOT text.
  * subgraph: restrict the graph to the transitive cone of one Variable.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from .registry import Registry
from .variable import Variable, Constant


def topological_sort() -> List[Variable]:
    """
    Kahn's algorithm over the Variable dependency graph.
    Raises RuntimeError if a cycle is found.
    """
    in_degree: Dict[str, int] = {}
    for v in Registry.variables.values():
        in_degree[v.name] = len(v.direct_dependencies())

    ready = [v for v in Registry.variables.values() if in_degree[v.name] == 0]
    order: List[Variable] = []
    while ready:
        v = ready.pop()
        order.append(v)
        for dep in v.direct_dependents():
            in_degree[dep.name] -= 1
            if in_degree[dep.name] == 0:
                ready.append(dep)
    if len(order) != len(Registry.variables):
        raise RuntimeError("Cycle detected in dependency graph")
    return order


def find_cycles() -> List[List[Variable]]:
    """DFS-based cycle detection. Returns one cycle per SCC, if any."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {v.name: WHITE for v in Registry.variables.values()}
    stack: List[Variable] = []
    cycles: List[List[Variable]] = []

    def dfs(v: Variable):
        color[v.name] = GRAY
        stack.append(v)
        for dep in v.direct_dependencies():
            if color[dep.name] == WHITE:
                dfs(dep)
            elif color[dep.name] == GRAY:
                # Found cycle: extract from stack
                idx = next(i for i, x in enumerate(stack) if x.name == dep.name)
                cycles.append(list(stack[idx:]))
        color[v.name] = BLACK
        stack.pop()

    for v in Registry.variables.values():
        if color[v.name] == WHITE:
            dfs(v)
    return cycles


def subgraph(root: Variable, direction: str = "dependencies") -> Set[Variable]:
    """
    Return the cone of Variables either reachable via dependencies (down)
    or dependents (up) from `root`. `direction` in {"dependencies", "dependents"}.
    """
    if direction == "dependencies":
        return {root} | root.dependencies()
    elif direction == "dependents":
        return {root} | root.dependents()
    else:
        raise ValueError(f"bad direction: {direction}")


def to_dot(
    variables: Optional[List[Variable]] = None,
    highlight: Optional[Set[Variable]] = None,
    max_nodes: int = 2000,
) -> str:
    """
    Emit Graphviz DOT representing the dependency graph.
    Variables are nodes; edges go from defining (dependency) to defined
    (dependent) so that a flow reads left-to-right.
    """
    if variables is None:
        variables = list(Registry.variables.values())
    if len(variables) > max_nodes:
        variables = variables[:max_nodes]
    highlight = highlight or set()

    lines = ["digraph gpu_stack {",
             "  rankdir=LR;",
             '  node [shape=box, fontname="Helvetica", fontsize=10];']
    nameset = {v.name for v in variables}
    for v in variables:
        attrs = []
        if isinstance(v, Constant):
            attrs.append('style=filled, fillcolor="#fff3b0"')
        elif v in highlight:
            attrs.append('style=filled, fillcolor="#c8e6c9"')
        elif not v.defining_equations:
            attrs.append('style=filled, fillcolor="#ffcdd2"')  # root input
        label = v.name.replace('"', r'\"')
        units = v.units.replace('"', r'\"')
        lines.append(f'  "{v.name}" [label="{label}\\n[{units}]"{", " + ", ".join(attrs) if attrs else ""}];')

    for v in variables:
        for dep in v.direct_dependencies():
            if dep.name in nameset:
                lines.append(f'  "{dep.name}" -> "{v.name}";')
    lines.append("}")
    return "\n".join(lines)


__all__ = ["topological_sort", "find_cycles", "subgraph", "to_dot"]
