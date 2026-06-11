"""
core/resolver_advanced.py
=========================

Opt-in resolver extensions: validity-aware variant fallback, small
simultaneous-system solving, and selection-explanation trace enrichment.

All helpers here are called explicitly by the resolver when the caller
opts in via keyword flags.  Default behavior (no flags) is unchanged.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Set, Tuple

import sympy as sp

from .equation import Approximation, Equation, RelationRole
from .registry import Registry
from .resolver_evaluation import (
    _equation_value,
    _evaluate_relation,
    _sym_subs,
)
from .resolver_models import TraceStep
from .resolver_selection import _select_equation
from .variable import Constant, Variable


# ---------------------------------------------------------------------------
# Selection reason text helpers
# ---------------------------------------------------------------------------

def _selection_reason_for_equation(
    eq: Equation,
    var: Variable,
    fallback_from: Optional[str] = None,
    system_peers: Optional[Tuple[str, ...]] = None,
) -> str:
    """
    Return a human-readable explanation of why `eq` was chosen for `var`.
    """
    if system_peers:
        peers = ", ".join(system_peers)
        return f"simultaneous system solve with {peers}"
    if fallback_from is not None:
        return (
            f"fallback from {fallback_from}: "
            "original approximation validity violated"
        )
    role = eq.role
    identities = [e for e in var.defining_equations if e.role == RelationRole.IDENTITY]
    variants = [e for e in var.defining_equations if e.role == RelationRole.VARIANT]
    approximations = [e for e in var.defining_equations if e.role == RelationRole.APPROXIMATION]

    if role == RelationRole.IDENTITY and len(identities) == 1:
        return "sole identity relation"
    if role == RelationRole.VARIANT:
        return f"explicit variant selection: {eq.variant!r}"
    if role == RelationRole.APPROXIMATION:
        alts = len(identities) + len(variants) + len(approximations)
        if alts == 1:
            return "sole approximation relation (no identity available)"
        return "approximation selected (no identity available; multiple approximations present)"
    return eq.role.name.lower()


def _not_selectable_alternatives(
    var: Variable,
    selected_eq_name: Optional[str],
    values: Mapping[str, sp.Expr],
) -> Tuple[str, ...]:
    """
    Return equation names that exist for `var` but were not selected.

    For missing variables, this shows what alternatives existed that
    could not be used.
    """
    out: List[str] = []
    for eq in sorted(var.defining_equations, key=lambda e: e.name):
        if eq.role == RelationRole.CONSTRAINT:
            continue
        if eq.name == selected_eq_name:
            continue
        out.append(eq.name)
    return tuple(out)


# ---------------------------------------------------------------------------
# Validity-aware approximation fallback
# ---------------------------------------------------------------------------

def _check_validity_violated(
    eq: Equation,
    values: Mapping[str, sp.Expr],
) -> bool:
    """
    Return True when `eq` is an Approximation whose validity predicate
    evaluates to False under the current `values`.

    Returns False for any other equation kind, or when the validity is
    unknown/symbolic (missing inputs).
    """
    if not isinstance(eq, Approximation):
        return False
    validity = getattr(eq, "validity", None)
    if validity is None:
        return False
    relation = sp.sympify(validity)
    subs = _sym_subs(values)
    evaluated = _evaluate_relation(relation, subs)
    return evaluated is sp.S.false


def _select_fallback_equation(
    var: Variable,
    original_eq: Equation,
    variants: Mapping[str, str],
) -> Optional[Equation]:
    """
    Find an alternative defining relation for `var` when the selected
    approximation validity is violated.

    Priority order:
    1. A single IDENTITY (if one exists).
    2. A single other APPROXIMATION (role=APPROXIMATION, different from original).
    3. A VARIANT that is NOT an Approximation (avoids another approximation
       that might also have a validity issue), using any available variant key.
    4. Any other single non-CONSTRAINT defining relation.

    Returns None when no usable alternative exists.
    """
    alternatives = [
        e for e in var.defining_equations
        if e.role != RelationRole.CONSTRAINT and e.name != original_eq.name
    ]
    if not alternatives:
        return None

    # Priority 1: IDENTITY
    identities = [e for e in alternatives if e.role == RelationRole.IDENTITY]
    if len(identities) == 1:
        return identities[0]
    if len(identities) > 1:
        # Multiple identities - too ambiguous for fallback
        return None

    # Priority 2: another APPROXIMATION (different validity domain)
    other_approx = [
        e for e in alternatives
        if e.role == RelationRole.APPROXIMATION and isinstance(e, Approximation)
    ]
    if len(other_approx) == 1:
        return other_approx[0]

    # Priority 3: a VARIANT that is a plain Equation (not Approximation)
    plain_variants = [
        e for e in alternatives
        if e.role == RelationRole.VARIANT and not isinstance(e, Approximation)
    ]
    if len(plain_variants) == 1:
        return plain_variants[0]

    # Priority 4: any single remaining alternative
    if len(alternatives) == 1:
        return alternatives[0]

    return None


def try_fallback_for_step(
    var: Variable,
    original_eq: Equation,
    variants: Mapping[str, str],
    values: Mapping[str, sp.Expr],
    explain: bool,
) -> Optional[TraceStep]:
    """
    Attempt fallback resolution for `var` when `original_eq` (an
    Approximation) has a violated validity predicate.

    Returns a new TraceStep with fallback metadata on success, or None
    if no alternative is available or the alternative is missing inputs.
    """
    fallback_eq = _select_fallback_equation(var, original_eq, variants)
    if fallback_eq is None:
        return None

    # Try to evaluate the fallback equation
    try:
        rhs_value = _equation_value(fallback_eq, values)
    except Exception:
        return None

    reason: Optional[str] = None
    if explain:
        reason = _selection_reason_for_equation(
            fallback_eq,
            var,
            fallback_from=original_eq.name,
        )
    return TraceStep(
        variable=var.name,
        equation=fallback_eq.name,
        role=fallback_eq.role,
        variant=fallback_eq.variant,
        value=rhs_value,
        selection_reason=reason,
        fallback_from=original_eq.name,
    )


# ---------------------------------------------------------------------------
# Small simultaneous-system solving
# ---------------------------------------------------------------------------

_MAX_SYSTEM_SIZE = 3


def _find_small_cycles(
    unresolved: List[Variable],
    values: Mapping[str, sp.Expr],
    variants: Mapping[str, str],
) -> List[List[Variable]]:
    """
    Identify groups of 2-3 unresolved variables that form a mutual-dependency
    cycle among themselves (all their selected-equation inputs are either
    already-resolved or members of the same group).

    Returns a list of cycles, each a list of Variable objects.
    """
    unresolved_names: Set[str] = {v.name for v in unresolved}
    by_name = {v.name: v for v in unresolved}
    # Build dependency map: for each unresolved variable, which other
    # unresolved variables does its selected equation depend on?
    deps: Dict[str, Set[str]] = {}
    eq_map: Dict[str, Equation] = {}
    for var in unresolved:
        try:
            eq_obj = _select_equation(var, variants)
        except Exception:
            continue
        if eq_obj is None:
            continue
        eq_map[var.name] = eq_obj
        from .resolver_graph import _value_dependencies
        dep_vars = _value_dependencies(eq_obj)
        # deps that are still unresolved
        unresolved_deps = {
            d.name for d in dep_vars
            if d.name in unresolved_names and d.name != var.name
        }
        # external deps that are NOT yet in values
        external_missing = {
            d.name for d in dep_vars
            if d.name not in unresolved_names
            and d.name not in values
            and not isinstance(d, Constant)
        }
        if external_missing:
            # Cannot form a cycle here - external deps are missing
            deps[var.name] = set()
        else:
            deps[var.name] = unresolved_deps

    # Find strongly-connected components of size 2..._MAX_SYSTEM_SIZE
    # where every node in the component has all its unresolved deps
    # inside the component.
    cycles: List[List[Variable]] = []
    seen_groups: Set[frozenset] = set()

    candidate_names = [n for n in by_name if n in eq_map and deps.get(n)]

    for name in candidate_names:
        group = _build_scc(name, deps, eq_map)
        if group is None:
            continue
        key = frozenset(group)
        if key in seen_groups:
            continue
        if 2 <= len(group) <= _MAX_SYSTEM_SIZE:
            cycles.append([by_name[n] for n in sorted(group)])
            seen_groups.add(key)

    return cycles


def _build_scc(
    start: str,
    deps: Dict[str, Set[str]],
    eq_map: Dict[str, Equation],
) -> Optional[List[str]]:
    """
    Starting from `start`, follow dependency edges to find a minimal
    strongly-connected component.  Returns None if `start` is not in a
    non-trivial SCC.
    """
    # DFS to find which nodes are reachable from `start`
    reachable: Set[str] = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in reachable:
            continue
        reachable.add(node)
        for dep in deps.get(node, set()):
            if dep in deps:  # dep is a candidate with an equation
                stack.append(dep)

    # Check if `start` is reachable from each reachable node (SCC)
    scc_members = []
    for node in reachable:
        back_reachable: Set[str] = set()
        back_stack = [node]
        while back_stack:
            n = back_stack.pop()
            if n in back_reachable:
                continue
            back_reachable.add(n)
            for dep in deps.get(n, set()):
                if dep in deps:
                    back_stack.append(dep)
        if start in back_reachable:
            scc_members.append(node)

    if len(scc_members) < 2:
        return None
    # Verify every member only has deps within the SCC (no external
    # unresolved deps)
    scc_set = set(scc_members)
    for node in scc_members:
        if not all(d in scc_set for d in deps.get(node, set())):
            return None
    return scc_members


def _solve_small_system(
    group: List[Variable],
    values: Mapping[str, sp.Expr],
    variants: Mapping[str, str],
) -> Optional[Dict[str, sp.Expr]]:
    """
    Solve the simultaneous system defined by the selected equations of `group`.

    Returns a dict name->value on success (unique real solution consistent
    with symbol assumptions), or None when no unique valid solution exists.
    """
    from .resolver_graph import _value_dependencies

    symbols = [var.symbol for var in group]
    sym_set = set(symbols)

    # Build the equation system as lhs - rhs = 0 for each variable.
    eqs_list = []
    for var in group:
        try:
            eq_obj = _select_equation(var, variants)
        except Exception:
            return None
        if eq_obj is None:
            return None
        # Substitute already-known values
        subs = _sym_subs(values)
        lhs = var.symbol
        rhs = eq_obj.rhs.subs(subs)
        eqs_list.append(lhs - rhs)

    # Attempt linear solve first (faster, handles most cycles)
    try:
        linear_sol = sp.linsolve(eqs_list, symbols)
        if linear_sol and len(linear_sol) == 1:
            sol_tuple = next(iter(linear_sol))
            if _solution_consistent(sol_tuple, group):
                return {v.name: sp.sympify(val) for v, val in zip(group, sol_tuple)}
    except Exception:
        pass

    # Fall back to general solve
    try:
        general_sol = sp.solve(eqs_list, symbols, dict=True)
    except Exception:
        return None

    if not general_sol:
        return None

    # Filter to real solutions consistent with symbol assumptions
    valid_sols = []
    for sol_dict in general_sol:
        vals = [sol_dict.get(sym, sym) for sym in symbols]
        if _solution_consistent(vals, group):
            valid_sols.append({v.name: sol_dict[v.symbol] for v in group
                               if v.symbol in sol_dict})

    if len(valid_sols) != 1:
        # Not unique - cannot accept
        return None

    return valid_sols[0]


def _solution_consistent(
    values: List[sp.Expr],
    variables: List[Variable],
) -> bool:
    """
    Check that each value is consistent with the corresponding variable's
    SymPy symbol assumptions (real, positive, etc.) and contains no free
    symbols.
    """
    for val, var in zip(values, variables):
        expr = sp.sympify(val)
        # Reject if still symbolic (unresolved)
        if expr.free_symbols:
            return False
        # Check each assumption on the variable's symbol
        for key, expected in var.assumptions.items():
            if expected is None:
                continue
            predicates = {
                "positive": sp.Q.positive,
                "negative": sp.Q.negative,
                "nonnegative": sp.Q.nonnegative,
                "nonpositive": sp.Q.nonpositive,
                "real": sp.Q.real,
                "integer": sp.Q.integer,
            }
            pred = predicates.get(key)
            if pred is None:
                continue
            result = sp.ask(pred(expr))
            if expected is True and result is False:
                return False
            if expected is False and result is True:
                return False
    return True


def resolve_small_system(
    group: List[Variable],
    values: Mapping[str, sp.Expr],
    variants: Mapping[str, str],
    explain: bool,
) -> Optional[List[TraceStep]]:
    """
    Attempt to resolve a group of mutually-dependent variables via
    simultaneous solving.

    Returns a list of TraceStep objects on success, or None on failure.
    """
    solution = _solve_small_system(group, values, variants)
    if solution is None:
        return None

    # Sort peers list for stable output
    peer_names = tuple(sorted(v.name for v in group))
    steps: List[TraceStep] = []
    for var in sorted(group, key=lambda v: v.name):
        if var.name not in solution:
            return None
        try:
            eq_obj = _select_equation(var, variants)
        except Exception:
            return None
        if eq_obj is None:
            return None

        peers_without_self = tuple(n for n in peer_names if n != var.name)
        reason: Optional[str] = None
        if explain:
            reason = _selection_reason_for_equation(
                eq_obj,
                var,
                system_peers=peers_without_self,
            )
        steps.append(TraceStep(
            variable=var.name,
            equation=eq_obj.name,
            role=eq_obj.role,
            variant=eq_obj.variant,
            value=solution[var.name],
            selection_reason=reason,
            system_peers=peers_without_self,
        ))
    return steps


# ---------------------------------------------------------------------------
# Selection-explanation enrichment for normal steps
# ---------------------------------------------------------------------------

def enrich_trace_step_reason(
    step: TraceStep,
    var: Variable,
) -> TraceStep:
    """
    Return a copy of `step` with a `selection_reason` set, for use when
    selection explanation is enabled but no fallback/system paths were taken.
    """
    if step.selection_reason is not None:
        return step
    eq_obj = Registry.equations.get(step.equation)
    if eq_obj is None:
        return step
    reason = _selection_reason_for_equation(eq_obj, var)
    return TraceStep(
        variable=step.variable,
        equation=step.equation,
        role=step.role,
        variant=step.variant,
        value=step.value,
        selection_reason=reason,
        fallback_from=step.fallback_from,
        system_peers=step.system_peers,
    )
