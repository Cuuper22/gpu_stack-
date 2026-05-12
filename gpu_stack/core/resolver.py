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
  * APPROXIMATION relations are eligible when no IDENTITY is present.
    Their validity regimes are evaluated and reported alongside
    constraints, but they do not block resolution.

The resolver does not try to solve simultaneous systems. It follows one
defining relation per variable, scheduled in topological order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Set, Tuple, Union

import sympy as sp

from .equation import (
    Approximation,
    Equation,
    RelationRole,
    domain_relations_for_variable,
)
from .registry import Registry
from .variable import Variable


AssignmentKey = Union[Variable, sp.Symbol, str]
AssignmentValue = Union[float, int, sp.Expr]


class ResolverError(RuntimeError):
    """Base error for the scenario resolver."""


class Underdetermined(ResolverError):
    """Raised when the scenario does not pin down enough values to proceed."""

    def __init__(
        self,
        message: str,
        missing: Optional[Set[str]] = None,
        unresolved_inputs: Optional[List["UnresolvedInput"]] = None,
    ):
        super().__init__(message)
        self.missing = set(missing or set())
        self.unresolved_inputs = list(unresolved_inputs or [])


class AmbiguousVariant(ResolverError):
    """Raised when multiple variant relations match without a selector."""


class InvalidVariantSelector(ResolverError):
    """Raised when a variant selector does not name a valid variant family."""


@dataclass
class TraceStep:
    """One equation application step."""
    variable: str
    equation: str
    role: RelationRole
    variant: Optional[str]
    value: sp.Expr


@dataclass
class ConstraintCheck:
    """One feasibility relation evaluated against the resolved scenario."""
    equation: str
    variable: str
    relation: sp.Expr
    evaluated: sp.Expr
    satisfied: Optional[bool]
    missing: Set[str] = field(default_factory=set)
    inputs: Dict[str, sp.Expr] = field(default_factory=dict)


@dataclass
class ApproximationValidityCheck:
    """One selected approximation validity predicate evaluated for a scenario."""
    equation: str
    variable: str
    validity: sp.Expr
    evaluated: sp.Expr
    satisfied: Optional[bool]
    missing: Set[str] = field(default_factory=set)


@dataclass(frozen=True)
class UnresolvedInput:
    """Actionable metadata for a symbolic boundary left in a scenario."""
    variable: str
    symbol: str
    units: str
    scope: str
    kind: str
    reason: str
    description: str
    variant_keys: Tuple[str, ...] = ()
    defining_equations: Tuple[str, ...] = ()
    direct_dependents: Tuple[str, ...] = ()
    dependents_count: int = 0
    family: str = ""
    boundary_category: str = ""
    primitive_boundary: bool = False


@dataclass(frozen=True)
class ConstraintViolation:
    """Actionable metadata for a feasibility relation evaluated as false."""
    equation: str
    variable: str
    relation: sp.Expr
    evaluated: sp.Expr
    description: str
    missing: Set[str] = field(default_factory=set)
    inputs: Dict[str, sp.Expr] = field(default_factory=dict)


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
    constraints: constraint relations from the target dependency cone,
                evaluated as far as the scenario permits.
    approximation_validity
              : approximation validity relations from selected trace
                equations, evaluated as far as the scenario permits.
    unresolved_inputs
              : richer metadata for names in `missing`.
    violated_constraints
              : richer metadata for constraint checks that evaluated false.
    """
    value: sp.Expr
    trace: List[TraceStep] = field(default_factory=list)
    values: Dict[str, sp.Expr] = field(default_factory=dict)
    missing: Set[str] = field(default_factory=set)
    constraints: List[ConstraintCheck] = field(default_factory=list)
    approximation_validity: List[ApproximationValidityCheck] = field(default_factory=list)
    unresolved_inputs: List[UnresolvedInput] = field(default_factory=list)
    violated_constraints: List[ConstraintViolation] = field(default_factory=list)


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


def _variant_keys(var: Variable) -> List[str]:
    """Registered variant keys for a variable, sorted for stable diagnostics."""
    return sorted(
        key for key in {eq.variant for eq in var.variants()}
        if key is not None
    )


def _validate_variant_selectors(variants: Mapping[str, str]) -> None:
    """
    Fail fast on typoed or nonsensical variant selectors.

    Valid-but-unused selectors are allowed so independently composed presets can
    carry workload choices that a particular target may not consume.
    """
    for name, key in variants.items():
        var = Registry.variables.get(name)
        if var is None:
            raise InvalidVariantSelector(
                f"unknown variant selector variable: {name!r}"
            )
        keys = _variant_keys(var)
        if not keys:
            raise InvalidVariantSelector(
                f"{name!r} has no VARIANT relations; cannot select {key!r}"
            )
        if key not in keys:
            raise InvalidVariantSelector(
                f"{name!r}: variant key {key!r} does not match any of {keys!r}"
            )


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
            keys = _variant_keys(var)
            raise AmbiguousVariant(
                f"{var.name} has variant relations {keys!r}. "
                f"Pass variants={{'{var.name}': <one-of>}} to select one."
            )
        matching = [e for e in variant_eqs if e.variant == key]
        if not matching:
            keys = _variant_keys(var)
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


def _constraint_evaluation_scope(
    cone: List[Variable],
    boundary_names: Set[str],
) -> List[Variable]:
    """
    Variables whose constraints should be reported for a resolved scenario.

    The value-resolution cone stays aggressively pruned. After resolving the
    target, symbolic boundary variables that remain in the target expression
    are nevertheless visible to the caller, so their own constraints should be
    visible too.
    """
    by_name = {v.name: v for v in cone}
    for name in boundary_names:
        v = Registry.variables.get(name)
        if v is not None:
            by_name.setdefault(name, v)
    return sorted(by_name.values(), key=lambda v: v.name)


def _describe_unresolved_inputs(missing: Set[str]) -> List[UnresolvedInput]:
    """Build stable, caller-facing metadata for unresolved scenario inputs."""
    out: List[UnresolvedInput] = []
    for name in sorted(missing):
        var = Registry.variables.get(name)
        if var is None:
            continue
        variant_keys = tuple(_variant_keys(var))
        if (
            variant_keys
            and not var.identities()
            and not var.approximations()
        ):
            reason = "variant selector required"
            boundary_category = "variant-family"
        elif var.is_root_input:
            reason = "root input assignment required"
            boundary_category = "primitive-root"
        else:
            reason = "symbolic boundary; assign directly or resolve its inputs"
            boundary_category = "symbolic-boundary"

        defining_equations = tuple(
            eq.name for eq in sorted(var.defining_equations, key=lambda eq: eq.name)
            if eq.role is not RelationRole.CONSTRAINT
        )
        direct_dependents = tuple(
            dep.name for dep in sorted(var.direct_dependents(), key=lambda dep: dep.name)
        )
        try:
            dependents_count = len(var.dependents())
        except RecursionError:
            dependents_count = len(direct_dependents)

        out.append(
            UnresolvedInput(
                variable=var.name,
                symbol=str(var.symbol),
                units=var.units,
                scope=var.scope,
                kind=var.kind.name,
                reason=reason,
                description=var.description,
                variant_keys=variant_keys,
                defining_equations=defining_equations,
                direct_dependents=direct_dependents,
                dependents_count=dependents_count,
                family=_boundary_family(var),
                boundary_category=boundary_category,
                primitive_boundary=var.is_root_input,
            )
        )
    return out


def _boundary_family(var: Variable) -> str:
    """
    Compact unresolved-input family derived from existing names and scope.

    Root-debt work often leaves primitive inputs with long names such as
    ``physical.lithography.source_plasma_drive_edge_detuning_ratio`` or
    ``econ.power.capacity_charge_kw_month``. The resolver preserves the exact
    variable name, but diagnostics also need a short bucket derived from the
    public name prefix so aliases like ``econ`` do not collapse into
    ``economics.econ``.
    """
    name_parts = [part for part in var.name.split(".") if part]
    scope = var.scope or (name_parts[0] if name_parts else "unknown")
    if not name_parts:
        return scope

    family_root = name_parts[0]
    namespace = name_parts[1:-1]
    leaf = name_parts[-1]

    base_parts = [family_root]
    if namespace:
        base_parts.extend(namespace[:1])

    leaf_family = _leaf_boundary_family(leaf)
    if leaf_family and leaf_family not in base_parts:
        base_parts.append(leaf_family)

    return ".".join(base_parts)


def _leaf_boundary_family(leaf: str) -> str:
    """Return a compact family stem for a leaf variable name."""
    stems = (
        "source_plasma_drive",
        "source_plasma_absorption",
        "source_plasma_species",
        "source_plasma_energy_loss",
        "source_plasma_free_electron",
        "source_plasma_electron",
        "source_plasma",
        "source_valence",
        "source",
        "medium_intercomponent",
        "medium",
        "semf",
    )
    for stem in stems:
        if leaf == stem or leaf.startswith(f"{stem}_"):
            return stem
    return ""


def _format_underdetermined_message(
    target_name: str,
    unresolved_inputs: List[UnresolvedInput],
    missing: Set[str],
) -> str:
    names = [item.variable for item in unresolved_inputs] or sorted(missing)
    if not names:
        return f"cannot resolve {target_name}: no value was produced"
    details = []
    for item in unresolved_inputs[:3]:
        details.append(f"{item.variable} ({item.reason})")
    extra = len(unresolved_inputs) - len(details)
    if extra > 0:
        details.append(f"{extra} more")
    detail_text = "; ".join(details) if details else repr(names)
    return f"cannot resolve {target_name}: missing inputs {names}; {detail_text}"


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


def _constraint_description(check: ConstraintCheck) -> str:
    eq = Registry.equations.get(check.equation)
    if eq is not None:
        return eq.description
    if check.equation.startswith("domain."):
        return f"Declared domain constraint for {check.variable}."
    return ""


def _describe_constraint_violations(
    checks: List[ConstraintCheck],
) -> List[ConstraintViolation]:
    """Build stable, caller-facing metadata for failed feasibility checks."""
    out: List[ConstraintViolation] = []
    for check in checks:
        if check.satisfied is not False:
            continue
        out.append(
            ConstraintViolation(
                equation=check.equation,
                variable=check.variable,
                relation=check.relation,
                evaluated=check.evaluated,
                description=_constraint_description(check),
                missing=set(check.missing),
                inputs=dict(check.inputs),
            )
        )
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
