"""
core/resolver.py
================

Scenario resolver public facade.

The implementation is split into small private modules for equation selection,
graph ordering, diagnostics, and relation evaluation. This module keeps the
historical import surface stable and owns the high-level resolution flow.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Set, Union

import sympy as sp

from .registry import Registry
from .resolver_advanced import (
    _check_validity_violated,
    _find_small_cycles,
    _not_selectable_alternatives,
    _selection_reason_for_equation,
    enrich_trace_step_reason,
    resolve_small_system,
    try_fallback_for_step,
)
from .resolver_diagnostics import (
    _boundary_family,
    _constraint_evaluation_scope,
    _describe_constraint_violations,
    _describe_unresolved_inputs,
    _format_underdetermined_message,
)
from .resolver_evaluation import (
    _equation_value,
    _evaluate_approximation_validity,
    _evaluate_constraints,
    _evaluate_domain_constraints,
    _missing_from_expr,
)
from .resolver_graph import _resolution_cone, _value_dependencies, topo_order_restricted
from .resolver_models import (
    AmbiguousVariant,
    ApproximationValidityCheck,
    AssignmentKey,
    AssignmentValue,
    ConstraintCheck,
    ConstraintViolation,
    InvalidVariantSelector,
    ResolverError,
    ResolverResult,
    TraceStep,
    Underdetermined,
    UnresolvedInput,
)
from .resolver_selection import (
    _normalize_assignments,
    _select_equation,
    _validate_variant_selectors,
    _variant_keys,
)
from .variable import Variable


def resolve(
    target: Union[Variable, sp.Symbol, str],
    assignments: Optional[Mapping[AssignmentKey, AssignmentValue]] = None,
    variants: Optional[Mapping[str, str]] = None,
    fallback_on_violated_validity: bool = False,
    solve_systems: bool = False,
    explain_selection: bool = False,
) -> ResolverResult:
    """
    Evaluate `target` under a scenario.

    Parameters
    ----------
    target
        Variable instance, SymPy Symbol, or registered variable name.
    assignments
        Numeric or symbolic values for scenario inputs. Keys may be
        Variable instances, SymPy Symbols, or registered variable names.
        Constants do not need to be passed; they carry their own values.
    variants
        Per-variable variant selections for multi-definition variables
        tagged with RelationRole.VARIANT, for example
        `{"training.flops_per_step": "dense", "opt.param_next": "adamw"}`.
    fallback_on_violated_validity
        Opt-in flag. When True, if a selected Approximation equation has a
        validity predicate that evaluates to False for the current
        assignments, and at least one alternative defining relation exists
        for the same variable, the resolver retries with the alternative and
        records a trace entry explaining the switch.  Default (False):
        report the violation but do not switch.
    solve_systems
        Opt-in flag. When True, if resolution stalls because 2-3 unresolved
        variables define each other through invertible relations (a small
        cycle in the selected-relation graph), gather the equations and solve
        the subsystem with sympy.solve/linsolve.  Only unique real solutions
        consistent with symbol assumptions are accepted.  Default (False):
        leave the variables missing as today.
    explain_selection
        Opt-in flag. When True, each TraceStep includes a `selection_reason`
        string explaining why that relation was chosen; each UnresolvedInput
        includes a `not_selectable_alternatives` tuple listing equation names
        that existed but could not be selected.  Default (False): fields are
        None/empty.

    Returns
    -------
    ResolverResult with the computed value, the ordered trace, the full
    map of intermediate values, and the set of missing inputs.

    Raises
    ------
    Underdetermined
        When a needed variable has no assignment and no usable defining
        relation. The `missing` set on the raised error names the gaps.
    AmbiguousVariant
        When a variable has multiple identities, multiple approximations,
        or an unselected variant family.
    """
    if isinstance(target, str):
        target_var = Registry.variables.get(target)
        if target_var is None:
            raise ResolverError(f"unknown variable name: {target!r}")
    elif isinstance(target, sp.Symbol):
        target_var = Registry.lookup_by_symbol(target)
        if target_var is None:
            raise ResolverError(f"unknown symbol: {target}")
    elif isinstance(target, Variable):
        target_var = target
    else:
        raise ResolverError(f"bad target type: {type(target).__name__}")

    assignments_map = _normalize_assignments(assignments or {})
    variants_map = dict(variants or {})
    _validate_variant_selectors(variants_map)

    values: Dict[str, sp.Expr] = dict(assignments_map)
    trace: List[TraceStep] = []
    missing: Set[str] = set()

    cone = sorted(
        _resolution_cone(target_var, set(values), variants_map),
        key=lambda v: v.name,
    )
    cone_order, cyclic_names = _topo_order_with_cycle_handling(
        cone, variants_map, set(values), allow_cycles=solve_systems
    )

    for v in cone_order:
        if v.name in values:
            continue
        from .variable import Constant
        if isinstance(v, Constant):
            values[v.name] = sp.Float(v.value)
            continue

        eq = _select_equation(v, variants_map)
        if eq is None:
            missing.add(v.name)
            continue

        # Validity-aware fallback (opt-in)
        if fallback_on_violated_validity and _check_validity_violated(eq, values):
            fallback_step = try_fallback_for_step(
                v, eq, variants_map, values, explain=explain_selection
            )
            if fallback_step is not None:
                values[v.name] = fallback_step.value
                trace.append(fallback_step)
                continue
            # No alternative available; fall through to use the original eq
            # (violation will appear in approximation_validity as before)

        rhs_value = _equation_value(eq, values)
        values[v.name] = rhs_value

        if explain_selection:
            reason = _selection_reason_for_equation(eq, v)
            step = TraceStep(
                variable=v.name,
                equation=eq.name,
                role=eq.role,
                variant=eq.variant,
                value=rhs_value,
                selection_reason=reason,
            )
        else:
            step = TraceStep(
                variable=v.name,
                equation=eq.name,
                role=eq.role,
                variant=eq.variant,
                value=rhs_value,
            )
        trace.append(step)

    # Cyclic nodes from topo ordering are immediately missing (no assignments)
    for name in cyclic_names:
        if name not in values:
            missing.add(name)

    # Small simultaneous-system solving (opt-in)
    if solve_systems and missing:
        cyclic_vars = [
            v for v in cone if v.name in cyclic_names
        ]
        _attempt_system_solve(
            missing, values, trace, cyclic_vars, variants_map, explain_selection
        )

    if target_var.name not in values:
        unresolved_inputs = _describe_unresolved_inputs(missing)
        if explain_selection:
            unresolved_inputs = _enrich_unresolved_with_alternatives(
                unresolved_inputs, missing, values
            )
        raise Underdetermined(
            _format_underdetermined_message(
                target_var.name,
                unresolved_inputs,
                missing,
            ),
            missing=missing,
            unresolved_inputs=unresolved_inputs,
        )
    missing |= _missing_from_expr(values[target_var.name], values)

    constraint_scope = _constraint_evaluation_scope(cone, missing)
    constraints = _evaluate_constraints(constraint_scope, values, variants_map)
    constraints.extend(_evaluate_domain_constraints(constraint_scope, values))
    approximation_validity = _evaluate_approximation_validity(
        trace,
        values,
        variants_map,
    )
    unresolved_inputs = _describe_unresolved_inputs(missing)
    if explain_selection:
        unresolved_inputs = _enrich_unresolved_with_alternatives(
            unresolved_inputs, missing, values
        )
    violated_constraints = _describe_constraint_violations(constraints)

    return ResolverResult(
        value=values[target_var.name],
        trace=trace,
        values=values,
        missing=missing,
        constraints=constraints,
        approximation_validity=approximation_validity,
        unresolved_inputs=unresolved_inputs,
        violated_constraints=violated_constraints,
    )


def _topo_order_with_cycle_handling(
    cone: List[Variable],
    variants_map: Mapping[str, str],
    boundary_names: Set[str],
    allow_cycles: bool,
) -> tuple:
    """
    Compute a topological ordering of `cone` variables.

    When `allow_cycles` is True, cyclic sub-graphs are silently omitted from
    the result (they will be handled by the system solver).  The second
    element of the returned tuple is the set of variable names that were
    left out due to cycles.

    When `allow_cycles` is False, behaves exactly like `topo_order_restricted`
    (raises ResolverError on cycles).
    """
    if not allow_cycles:
        return (
            [v for v in topo_order_restricted(cone, variants_map, boundary_names)
             if v.name not in boundary_names],
            set(),
        )

    # Attempt the topo sort; if it fails, identify cyclic nodes and exclude them.
    try:
        order = [
            v for v in topo_order_restricted(cone, variants_map, boundary_names)
            if v.name not in boundary_names
        ]
        return order, set()
    except ResolverError:
        pass

    # Find which nodes are NOT part of cycles by progressively excluding
    # nodes that form a cycle.
    from .resolver_graph import _value_dependencies
    from .resolver_selection import _select_equation as _se

    cone_set = {v.name for v in cone}
    by_name = {v.name: v for v in cone}
    in_deg: Dict[str, int] = {}
    deps_map: Dict[str, List[str]] = {}
    rev_map: Dict[str, List[str]] = {}

    for v in cone:
        if v.name in boundary_names:
            deps_map[v.name] = []
            in_deg[v.name] = 0
            continue
        try:
            eq = _se(v, variants_map)
        except ResolverError:
            eq = None
        if eq is None:
            deps_map[v.name] = []
            in_deg[v.name] = 0
            continue
        dep_names = [
            d.name for d in _value_dependencies(eq)
            if d.name in cone_set and d.name not in boundary_names
        ]
        deps_map[v.name] = dep_names
        in_deg[v.name] = len(dep_names)

    for v in cone:
        for dep_name in deps_map.get(v.name, []):
            rev_map.setdefault(dep_name, []).append(v.name)

    ready = [n for n in in_deg if in_deg[n] == 0]
    resolved_order = []
    while ready:
        name = ready.pop()
        resolved_order.append(by_name[name])
        for dep in rev_map.get(name, []):
            in_deg[dep] -= 1
            if in_deg[dep] == 0:
                ready.append(dep)

    cyclic_names = {
        n for n, deg in in_deg.items()
        if deg > 0 and n not in boundary_names
    }
    return resolved_order, cyclic_names


def _attempt_system_solve(
    missing: Set[str],
    values: Dict[str, sp.Expr],
    trace: List[TraceStep],
    cyclic_vars: List[Variable],
    variants_map: Mapping[str, str],
    explain: bool,
) -> None:
    """
    Try to resolve small cycles among `cyclic_vars` by solving them
    simultaneously.  Updates `missing`, `values`, and `trace` in place.
    """
    if not cyclic_vars:
        return

    cycles = _find_small_cycles(cyclic_vars, values, variants_map)
    for group in cycles:
        if not all(v.name in missing for v in group):
            continue  # some already resolved in a prior iteration
        steps = resolve_small_system(group, values, variants_map, explain)
        if steps is None:
            continue
        for step in steps:
            values[step.variable] = step.value
            missing.discard(step.variable)
            trace.append(step)


def _enrich_unresolved_with_alternatives(
    unresolved_inputs: List[UnresolvedInput],
    missing: Set[str],
    values: Mapping[str, sp.Expr],
) -> List[UnresolvedInput]:
    """
    Return a new list of UnresolvedInput objects enriched with
    `not_selectable_alternatives` for the explain_selection path.
    """
    out = []
    for item in unresolved_inputs:
        var = Registry.variables.get(item.variable)
        if var is None:
            out.append(item)
            continue
        alternatives = _not_selectable_alternatives(var, None, values)
        out.append(UnresolvedInput(
            variable=item.variable,
            symbol=item.symbol,
            units=item.units,
            scope=item.scope,
            kind=item.kind,
            reason=item.reason,
            description=item.description,
            variant_keys=item.variant_keys,
            defining_equations=item.defining_equations,
            direct_dependents=item.direct_dependents,
            dependents_count=item.dependents_count,
            family=item.family,
            boundary_category=item.boundary_category,
            primitive_boundary=item.primitive_boundary,
            not_selectable_alternatives=alternatives,
        ))
    return out



__all__ = [
    "ResolverError",
    "Underdetermined",
    "AmbiguousVariant",
    "InvalidVariantSelector",
    "TraceStep",
    "ConstraintCheck",
    "ApproximationValidityCheck",
    "UnresolvedInput",
    "ConstraintViolation",
    "ResolverResult",
    "resolve",
]
