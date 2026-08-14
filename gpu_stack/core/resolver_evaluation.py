"""
Numeric evaluation for the scenario resolver.

Two jobs live here. The first is substitution: take an equation or a
relation, replace each variable's symbol with its known value, and simplify
— but only when the expression is small, because simplifying a huge
partially-symbolic expression can take tens of seconds for no benefit.

The second is checking: after the target resolves, evaluate every
constraint, declared variable domain, and approximation-validity predicate
that the scenario can reach, and record whether each one held. Constraints
may need helper variables that sit outside the value-resolution cone
(constraint edges do not define values), so a deliberately bounded local
resolution fills those in without becoming a second full resolver pass.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Set

import sympy as sp

from .equation import (
    Approximation,
    Equation,
    RelationRole,
    domain_relations_for_variable,
)
from .registry import Registry
from .resolver_graph import _resolution_cone, _value_dependencies, topo_order_restricted
from .resolver_models import (
    ApproximationValidityCheck,
    ConstraintCheck,
    ResolverError,
    TraceStep,
)
from .resolver_selection import _select_equation
from .variable import Variable


def _equation_value(eq: Equation, values: Mapping[str, sp.Expr]) -> sp.Expr:
    """Evaluate the value side of a selected equation under current values."""
    return _simplify_if_small(eq.value_expr(_sym_subs(values)))


def _evaluate_relation(
    relation: sp.Expr,
    subs: Mapping[sp.Symbol, sp.Expr],
) -> sp.Expr:
    """
    Substitute known values into a feasibility relation.

    If registered symbols remain, keep the relation structural. Calling
    `simplify()` on an unevaluated relation such as `x > 0` can collapse it to
    `True` when `x` has a positive SymPy assumption, hiding missing scenario
    inputs. Fully numeric relations still simplify to concrete booleans.
    """
    try:
        evaluated = relation.subs(dict(subs))
    except (TypeError, ValueError, ZeroDivisionError):
        return sp.S.false
    if getattr(evaluated, "free_symbols", set()):
        return evaluated
    try:
        return _simplify_if_small(evaluated)
    except (TypeError, ValueError, ZeroDivisionError):
        return sp.S.false


def _missing_from_expr(
    expr: sp.Expr,
    values: Mapping[str, sp.Expr],
) -> Set[str]:
    """Registered variables left as symbolic boundaries in a resolved value."""
    missing: Set[str] = set()
    for sym in getattr(expr, "free_symbols", set()):
        v = Registry.lookup_by_symbol(sym)
        if v is not None and v.name not in values:
            missing.add(v.name)
    return missing


def _relation_inputs(
    relation: sp.Expr,
    values: Mapping[str, sp.Expr],
) -> Dict[str, sp.Expr]:
    """Known variable values that participated in an evaluated relation."""
    inputs: Dict[str, sp.Expr] = {}
    for sym in sorted(getattr(relation, "free_symbols", set()), key=str):
        var = Registry.lookup_by_symbol(sym)
        if var is not None and var.name in values:
            inputs[var.name] = values[var.name]
    return inputs


def _sym_subs(values: Mapping[str, sp.Expr]) -> Dict[sp.Symbol, sp.Expr]:
    """Build a SymPy substitution dict from name->value, preserving symbols."""
    subs: Dict[sp.Symbol, sp.Expr] = {}
    for name, val in values.items():
        v = Registry.variables.get(name)
        if v is None:
            continue
        subs[v.symbol] = val
    return subs


def _evaluate_constraints(
    cone: List[Variable],
    values: Mapping[str, sp.Expr],
    variants: Mapping[str, str],
) -> List[ConstraintCheck]:
    """Evaluate CONSTRAINT relations owned by or involving cone variables."""
    seen: Set[str] = set()
    checks: List[ConstraintCheck] = []
    for var in cone:
        for eq in _constraint_relations_for(var):
            if eq.name in seen:
                continue
            seen.add(eq.name)
            relation = eq.as_sympy()
            extended_values = _extend_values_for_relation(
                relation,
                values,
                variants,
            )
            subs = _sym_subs(extended_values)
            evaluated = _evaluate_relation(relation, subs)
            if evaluated is sp.S.true:
                satisfied: Optional[bool] = True
            elif evaluated is sp.S.false:
                satisfied = False
            else:
                satisfied = None
            missing = {
                v.name
                for sym in getattr(evaluated, "free_symbols", set())
                if (v := Registry.lookup_by_symbol(sym)) is not None
                and v.name not in extended_values
            }
            lhs_var = eq.lhs_variable()
            checks.append(
                ConstraintCheck(
                    equation=eq.name,
                    variable=lhs_var.name if lhs_var is not None else var.name,
                    relation=relation,
                    evaluated=evaluated,
                    satisfied=satisfied,
                    missing=missing,
                    inputs=_relation_inputs(relation, extended_values),
                )
            )
    return checks


def _evaluate_domain_constraints(
    cone: List[Variable],
    values: Mapping[str, sp.Expr],
) -> List[ConstraintCheck]:
    """Evaluate declared Variable domains against resolved scenario values."""
    checks: List[ConstraintCheck] = []
    subs = _sym_subs(values)
    for var in cone:
        if var.name not in values:
            continue
        for suffix, relation in domain_relations_for_variable(var):
            evaluated = _evaluate_relation(relation, subs)
            if evaluated is sp.S.true:
                satisfied: Optional[bool] = True
            elif evaluated is sp.S.false:
                satisfied = False
            else:
                satisfied = None
            missing = {
                v.name
                for sym in getattr(evaluated, "free_symbols", set())
                if (v := Registry.lookup_by_symbol(sym)) is not None
                and v.name not in values
            }
            checks.append(
                ConstraintCheck(
                    equation=f"domain.{var.name}.{suffix}",
                    variable=var.name,
                    relation=relation,
                    evaluated=evaluated,
                    satisfied=satisfied,
                    missing=missing,
                    inputs=_relation_inputs(relation, values),
                )
            )
    return checks


def _evaluate_approximation_validity(
    trace: List[TraceStep],
    values: Mapping[str, sp.Expr],
    variants: Mapping[str, str],
) -> List[ApproximationValidityCheck]:
    """Evaluate validity predicates for selected Approximation relations."""
    seen: Set[str] = set()
    checks: List[ApproximationValidityCheck] = []
    for step in trace:
        if step.equation in seen:
            continue
        eq = Registry.equations.get(step.equation)
        if not isinstance(eq, Approximation):
            continue
        seen.add(step.equation)
        validity = getattr(eq, "validity", None)
        if validity is None:
            continue
        relation = sp.sympify(validity)
        extended_values = _extend_values_for_relation(relation, values, variants)
        subs = _sym_subs(extended_values)
        evaluated = _evaluate_relation(relation, subs)
        if evaluated is sp.S.true:
            satisfied: Optional[bool] = True
        elif evaluated is sp.S.false:
            satisfied = False
        else:
            satisfied = None
        missing = {
            v.name
            for sym in getattr(evaluated, "free_symbols", set())
            if (v := Registry.lookup_by_symbol(sym)) is not None
            and v.name not in extended_values
        }
        lhs_var = eq.lhs_variable() if eq is not None else None
        checks.append(
            ApproximationValidityCheck(
                equation=step.equation,
                variable=lhs_var.name if lhs_var is not None else step.variable,
                validity=relation,
                evaluated=evaluated,
                satisfied=satisfied,
                missing=missing,
            )
        )
    return checks


def _constraint_relations_for(var: Variable) -> List[Equation]:
    """Constraints where `var` is either the constrained LHS or an input."""
    constraints = list(var.constraints())
    constraints.extend(
        eq for eq in var.appearances
        if eq.role == RelationRole.CONSTRAINT
    )
    return constraints


def _extend_values_for_relation(
    relation: sp.Expr,
    values: Mapping[str, sp.Expr],
    variants: Mapping[str, str],
    max_helper_nodes: int = 64,
    max_helper_ops: int = 500,
) -> Dict[str, sp.Expr]:
    """
    Compute simple helper variables needed to evaluate a constraint relation.

    Constraint edges are deliberately excluded from the target's definitional
    dependency cone. This helper lets a constraint still evaluate `T_clk` from
    an assigned `f_clk` through the identity `T_clk = 1/f_clk`, without making
    constraints participate in graph causality. It is deliberately shallow:
    constraint reporting should not recursively expand an unrelated unresolved
    subtree just to make a side check look more complete.
    """
    out: Dict[str, sp.Expr] = dict(values)
    attempted: Set[str] = set()
    remaining = max_helper_nodes

    for sym in sorted(getattr(relation, "free_symbols", set()), key=str):
        if remaining <= 0:
            break
        v = Registry.lookup_by_symbol(sym)
        if v is not None:
            computed = _extend_value_for_variable(
                v,
                out,
                variants,
                max_helper_nodes=remaining,
                max_helper_ops=max_helper_ops,
                attempted=attempted,
            )
            remaining -= computed
    return out


def _extend_value_for_variable(
    var: Variable,
    values: Dict[str, sp.Expr],
    variants: Mapping[str, str],
    max_helper_nodes: int = 64,
    max_helper_ops: int = 500,
    attempted: Optional[Set[str]] = None,
) -> int:
    """
    Locally resolve a helper variable needed only for a constraint check.

    This is intentionally bounded and seeded by the relation's own free
    symbols, so a side constraint can evaluate simple helper chains without
    turning constraint reporting into a second unbounded resolver pass.
    """
    if var.name in values:
        return 0
    attempted = attempted if attempted is not None else set()
    if var.name in attempted:
        return 0
    attempted.add(var.name)
    try:
        cone = _resolution_cone(var, set(values), variants)
    except ResolverError:
        return 0
    new_nodes = [node for node in cone if node.name not in values]
    if len(new_nodes) > max_helper_nodes:
        return 0

    try:
        order = topo_order_restricted(
            sorted(cone, key=lambda node: node.name),
            variants,
            set(values),
        )
    except ResolverError:
        return 0

    local: Dict[str, sp.Expr] = dict(values)
    computed = 0
    for node in order:
        if node.name in local:
            continue
        from .variable import Constant
        if isinstance(node, Constant):
            local[node.name] = sp.Float(node.value)
            computed += 1
            continue
        try:
            eq = _select_equation(node, variants)
        except ResolverError:
            return 0
        if eq is None:
            return 0
        deps = _value_dependencies(eq)
        if any(dep.name not in local for dep in deps):
            return 0
        value = _equation_value(eq, local)
        if _expr_too_large(value, max_helper_ops):
            return 0
        local[node.name] = value
        computed += 1

    if var.name in local:
        values.update(local)
        return computed
    return 0


def _expr_too_large(expr: sp.Expr, max_ops: int) -> bool:
    try:
        return sp.count_ops(expr) > max_ops
    except Exception:
        return True


def _simplify_if_small(expr: sp.Expr, max_ops: int = 80) -> sp.Expr:
    """
    Apply SymPy simplification only when the expression is small enough.

    Resolver outputs are often partially symbolic by design. Once a scenario
    leaves a high-level hardware quantity unpinned, eager simplification can
    spend tens of seconds trying to polish a huge expression that the caller
    only needs as an audit trace. Small expressions still benefit from normal
    cleanup, while large ones keep their structural form.
    """
    try:
        if sp.count_ops(expr) > max_ops:
            return expr
        return sp.simplify(expr)
    except Exception:
        return expr
