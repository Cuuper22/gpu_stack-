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
    cone_order = [
        v for v in topo_order_restricted(cone, variants_map, set(values))
        if v.name not in values
    ]

    for v in cone_order:
        from .variable import Constant
        if isinstance(v, Constant):
            values[v.name] = sp.Float(v.value)
            continue

        eq = _select_equation(v, variants_map)
        if eq is None:
            missing.add(v.name)
            continue

        rhs_value = _equation_value(eq, values)
        values[v.name] = rhs_value
        trace.append(
            TraceStep(
                variable=v.name,
                equation=eq.name,
                role=eq.role,
                variant=eq.variant,
                value=rhs_value,
            )
        )

    if target_var.name not in values:
        unresolved_inputs = _describe_unresolved_inputs(missing)
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
