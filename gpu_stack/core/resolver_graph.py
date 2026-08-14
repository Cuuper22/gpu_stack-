"""
Graph work for the scenario resolver: what to compute, and in what order.

`_resolution_cone` decides *what*: the set of variables actually needed to
reach the target, treating assigned variables as boundaries and refusing to
expand subtrees that could only produce giant symbolic expressions.
`topo_order_restricted` decides *in what order*: a topological sort over
just that set, following each variable's selected equation.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Set

import sympy as sp

from .equation import Equation, RelationRole
from .registry import Registry
from .resolver_models import AmbiguousVariant, ResolverError
from .resolver_selection import _select_equation
from .variable import Variable


def _resolution_cone(
    target: Variable,
    assigned_names: Set[str],
    variants: Mapping[str, str],
) -> Set[Variable]:
    """
    Dependency cone needed for this resolver call.

    The graph-level dependency traversal intentionally ignores scenario
    assignments because it is an inspection primitive. Resolution needs the
    opposite behavior: if a variable is assigned, it is a boundary condition,
    and its internal definition should not be recursively expanded. Without
    this pruning, a tiny target like `cluster.rack.peak_flops` still walks the
    full GPU/physical ancestry even when `gpu.peak_flops` is pinned.
    """
    out: Set[Variable] = set()
    visiting: Set[str] = set()
    potential_cache: Dict[str, tuple[bool, bool]] = {}

    def is_unselected_variant_family(var: Variable) -> bool:
        return (
            var.name not in variants
            and any(e.role == RelationRole.VARIANT for e in var.defining_equations)
            and not any(e.role == RelationRole.IDENTITY for e in var.defining_equations)
        )

    def resolution_potential(var: Variable) -> tuple[bool, bool]:
        """
        Return `(has_assigned_descendant, fully_resolvable)`.

        If an unassigned dependency subtree has no scenario values and bottoms
        out in root inputs, expanding it only creates a huge symbolic expression.
        Treat that dependency as a boundary symbol for this resolver call.
        """
        if var.name in assigned_names:
            return True, True
        if var.name in potential_cache:
            return potential_cache[var.name]
        from .variable import Constant
        if isinstance(var, Constant):
            potential_cache[var.name] = (False, True)
            return potential_cache[var.name]
        if var.name in visiting:
            return False, False
        if is_unselected_variant_family(var):
            potential_cache[var.name] = (False, False)
            return potential_cache[var.name]

        visiting.add(var.name)
        eq = _select_equation(var, variants)
        if eq is None:
            result = (False, False)
        else:
            deps = _value_dependencies(eq)
            if not deps:
                result = (False, True)
            else:
                potentials = [resolution_potential(dep) for dep in deps]
                result = (
                    any(has_assigned for has_assigned, _ in potentials),
                    all(fully_resolvable for _, fully_resolvable in potentials),
                )
        visiting.remove(var.name)
        potential_cache[var.name] = result
        return result

    def visit(var: Variable) -> None:
        if var.name in visiting:
            return
        out.add(var)
        if var.name in assigned_names:
            return
        from .variable import Constant
        if isinstance(var, Constant):
            return
        visiting.add(var.name)
        if is_unselected_variant_family(var):
            visiting.remove(var.name)
            return
        eq = _select_equation(var, variants)
        if eq is not None:
            for dep in _value_dependencies(eq):
                has_assigned, fully_resolvable = resolution_potential(dep)
                if has_assigned or fully_resolvable:
                    visit(dep)
        visiting.remove(var.name)

    visit(target)
    return out


def topo_order_restricted(
    variables: List[Variable],
    variants: Optional[Mapping[str, str]] = None,
    boundary_names: Optional[Set[str]] = None,
) -> List[Variable]:
    """
    Topological sort restricted to the input list, respecting
    selected-equation value dependencies that fall inside the list.
    External dependencies are treated as satisfied.
    """
    variants_map = dict(variants or {})
    boundaries = set(boundary_names or set())
    by_name = {v.name: v for v in variables}
    deps_by_name: Dict[str, List[Variable]] = {}
    dependents_by_name: Dict[str, List[Variable]] = {name: [] for name in by_name}
    for v in variables:
        if v.name in boundaries:
            eq = None
        else:
            try:
                eq = _select_equation(v, variants_map)
            except AmbiguousVariant:
                eq = None
        deps = [
            dep for dep in (_value_dependencies(eq) if eq is not None else [])
            if dep.name in by_name
        ]
        deps_by_name[v.name] = deps
        for dep in deps:
            dependents_by_name[dep.name].append(v)
    in_deg = {name: len(deps) for name, deps in deps_by_name.items()}
    ready = [v for v in variables if in_deg[v.name] == 0]
    out: List[Variable] = []
    while ready:
        v = ready.pop()
        out.append(v)
        for dep in dependents_by_name[v.name]:
            in_deg[dep.name] -= 1
            if in_deg[dep.name] == 0:
                ready.append(dep)
    if len(out) != len(variables):
        remaining = sorted(
            name for name, degree in in_deg.items()
            if degree > 0
        )
        raise ResolverError(
            "selected resolver dependency graph is cyclic or inconsistent: "
            f"{remaining}"
        )
    return out


def _value_dependencies(eq: Equation) -> List[Variable]:
    """Variables needed to evaluate an equation value, excluding validity regimes."""
    out: List[Variable] = []
    seen: Set[str] = set()
    bound_symbols = eq._bound_symbols()
    for expr in eq._value_dependency_exprs():
        for sym in getattr(sp.sympify(expr), "free_symbols", set()) - bound_symbols:
            v = Registry.lookup_by_symbol(sym)
            if v is not None and v.name not in seen:
                out.append(v)
                seen.add(v.name)
    return sorted(out, key=lambda v: v.name)
