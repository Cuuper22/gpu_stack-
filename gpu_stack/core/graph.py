"""
core/graph.py
=============

Utilities for the dependency graph that the Variables and Equations form.

Every equation draws edges from the variables on its right-hand side to the
variable it defines. Taken together, those edges make a directed graph, and
this module answers the basic questions about it:

  * topological_sort: order Variables so dependencies come before dependents.
  * find_cycles: find circular definitions, which usually mean a bad equation.
  * subgraph: restrict the graph to everything one Variable depends on
    (or everything that depends on it).
  * to_dot: export the graph as Graphviz DOT text for visual inspection.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from .registry import Registry
from .variable import Variable, Constant


def topological_sort() -> List[Variable]:
    """
    Order all registered Variables so every dependency precedes its dependents.

    Uses Kahn's algorithm: repeatedly emit a variable whose remaining
    dependency count is zero, then decrement its dependents. If some
    variables are never emitted, the graph has a cycle; raise RuntimeError.
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
    """
    Find circular dependencies by depth-first search.

    A gray node met again while still on the DFS stack marks a cycle; the
    stack slice from that node onward is the cycle itself. Returns one
    cycle per strongly connected component, or an empty list.
    """
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
                # dep is still on the DFS stack, so the stack from dep onward
                # is a cycle.
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
    The cone of Variables reachable from `root`, plus `root` itself.

    `direction="dependencies"` walks down to everything `root` is computed
    from; `direction="dependents"` walks up to everything computed from it.
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
    Emit Graphviz DOT text for the dependency graph.

    Variables are nodes; edges run from dependency to dependent, so the
    rendered flow reads left-to-right from raw inputs toward outputs.
    Constants, root inputs, and any `highlight` set get distinct fill
    colors. Output is truncated at `max_nodes` nodes.
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
        elif v.is_root_input:
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
