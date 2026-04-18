"""
core/resolver.py
================

Scenario resolver.

The registry is strong at inspection but weak at scenario analysis. This
module adds a resolver that takes a target Variable plus a dict of
numeric scenario assignments, walks the dependency cone in topological
order, and substitutes values equation by equation until the target has
a numeric answer. It returns both the result and a trace of which
equations were used so the caller can audit the derivation.

Relation-role handling:

  * IDENTITY equations are eligible as defining relations by default.
  * VARIANT equations are eligible only when the caller selects a
    variant key via `variants=`.
  * CONSTRAINT relations (typically inequalities) are never used as
    defining relations. They can be evaluated against the computed
    scenario after the fact for feasibility checks.
  * APPROXIMATION relations are eligible when no IDENTITY is present,
    since their validity regime is the caller's responsibility.

The resolver does not try to solve simultaneous systems. It follows one
defining relation per variable, scheduled in topological order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Set, Union

import sympy as sp

from .equation import Equation, RelationRole
from .registry import Registry
from .variable import Variable


AssignmentKey = Union[Variable, sp.Symbol, str]
AssignmentValue = Union[float, int, sp.Expr]


class ResolverError(RuntimeError):
    """Base error for the scenario resolver."""


class Underdetermined(ResolverError):
    """Raised when the scenario does not pin down enough values to proceed."""


class AmbiguousVariant(ResolverError):
    """Raised when multiple variant relations match without a selector."""


@dataclass
class TraceStep:
    """One equation application step."""
    variable: str
    equation: str
    role: RelationRole
    variant: Optional[str]
    value: sp.Expr


@dataclass
class ResolverResult:
    """
    Resolver output.

    value     : numeric or symbolic value of the target Variable.
    trace     : ordered list of equation applications used to reach value.
    values    : dict name -> substituted expression for every Variable
                computed along the way.
    missing   : Variables that were needed but had no scenario assignment
                and no eligible defining equation.
    """
    value: sp.Expr
    trace: List[TraceStep] = field(default_factory=list)
    values: Dict[str, sp.Expr] = field(default_factory=dict)
    missing: Set[str] = field(default_factory=set)


def _normalize_assignments(
    assignments: Mapping[AssignmentKey, AssignmentValue],
) -> Dict[str, sp.Expr]:
    """Convert {Variable|Symbol|name: number|expr} into {name: sp.Expr}."""
    out: Dict[str, sp.Expr] = {}
    for k, v in assignments.items():
        if isinstance(k, Variable):
            name = k.name
        elif isinstance(k, sp.Symbol):
            var = Registry.lookup_by_symbol(k)
            if var is None:
                raise ResolverError(f"unknown symbol in assignments: {k}")
            name = var.name
        elif isinstance(k, str):
            if k not in Registry.variables:
                raise ResolverError(f"unknown variable name in assignments: {k!r}")
            name = k
        else:
            raise ResolverError(f"bad assignment key type: {type(k).__name__}")
        out[name] = sp.sympify(v)
    return out


def _select_equation(
    var: Variable,
    variants: Mapping[str, str],
) -> Optional[Equation]:
    """
    Pick one defining relation for `var`. IDENTITY wins by default. If
    there is no identity, an APPROXIMATION is used. VARIANT relations are
    only used when the caller supplied a variant key for this variable's
    name via `variants={var_name: variant_key}`.

    Returns None when the variable has no usable defining relation, which
    the caller treats as "must come from scenario assignments".
    """
    identities = [e for e in var.defining_equations if e.role == RelationRole.IDENTITY]
    if len(identities) == 1:
        return identities[0]
    if len(identities) > 1:
        raise AmbiguousVariant(
            f"{var.name} has {len(identities)} identity relations. "
            "Re-tag with VARIANT roles or narrow the resolver call."
        )

    variant_eqs = [e for e in var.defining_equations if e.role == RelationRole.VARIANT]
    if variant_eqs:
        key = variants.get(var.name)
        if key is None:
            keys = sorted({e.variant for e in variant_eqs if e.variant is not None})
            raise AmbiguousVariant(
                f"{var.name} has variant relations {keys!r}. "
                f"Pass variants={{'{var.name}': <one-of>}} to select one."
            )
        matching = [e for e in variant_eqs if e.variant == key]
        if not matching:
            keys = sorted({e.variant for e in variant_eqs if e.variant is not None})
            raise AmbiguousVariant(
                f"{var.name}: variant key {key!r} does not match any of {keys!r}."
            )
        if len(matching) > 1:
            raise AmbiguousVariant(
                f"{var.name}: variant key {key!r} matches {len(matching)} relations."
            )
        return matching[0]

    approximations = [e for e in var.defining_equations if e.role == RelationRole.APPROXIMATION]
    if len(approximations) == 1:
        return approximations[0]
    if len(approximations) > 1:
        raise AmbiguousVariant(
            f"{var.name} has {len(approximations)} approximation relations. "
            "Narrow the resolver call."
        )

    return None


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

    values: Dict[str, sp.Expr] = dict(assignments_map)
    trace: List[TraceStep] = []
    missing: Set[str] = set()

    cone = sorted({target_var} | target_var.dependencies(), key=lambda v: v.name)
    cone_order = [v for v in topo_order_restricted(cone) if v.name not in values]

    for v in cone_order:
        from .variable import Constant
        if isinstance(v, Constant):
            values[v.name] = sp.Float(v.value)
            continue

        eq = _select_equation(v, variants_map)
        if eq is None:
            missing.add(v.name)
            continue

        subs = _sym_subs(values)
        rhs_value = sp.sympify(eq.rhs).subs(subs)
        try:
            rhs_value = sp.simplify(rhs_value)
        except Exception:
            pass
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
        raise Underdetermined(
            f"cannot resolve {target_var.name}: missing inputs {sorted(missing)}"
        )

    return ResolverResult(
        value=values[target_var.name],
        trace=trace,
        values=values,
        missing=missing,
    )


def topo_order_restricted(variables: List[Variable]) -> List[Variable]:
    """
    Topological sort restricted to the input list, respecting
    dependencies that fall inside the list. External dependencies are
    treated as satisfied.
    """
    by_name = {v.name: v for v in variables}
    in_deg: Dict[str, int] = {}
    for v in variables:
        in_deg[v.name] = sum(
            1 for d in v.direct_dependencies() if d.name in by_name
        )
    ready = [v for v in variables if in_deg[v.name] == 0]
    out: List[Variable] = []
    while ready:
        v = ready.pop()
        out.append(v)
        for dep in v.direct_dependents():
            if dep.name not in by_name:
                continue
            in_deg[dep.name] -= 1
            if in_deg[dep.name] == 0:
                ready.append(dep)
    return out


def _sym_subs(values: Mapping[str, sp.Expr]) -> Dict[sp.Symbol, sp.Expr]:
    """Build a SymPy substitution dict from name->value, preserving symbols."""
    subs: Dict[sp.Symbol, sp.Expr] = {}
    for name, val in values.items():
        v = Registry.variables.get(name)
        if v is None:
            continue
        subs[v.symbol] = val
    return subs


__all__ = [
    "ResolverError",
    "Underdetermined",
    "AmbiguousVariant",
    "TraceStep",
    "ResolverResult",
    "resolve",
]
