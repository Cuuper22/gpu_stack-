"""
Diagnostics for the scenario resolver: turning failures into guidance.

When resolution leaves gaps, the caller needs more than a set of missing
names. These helpers classify each unresolved input (is it a root input, a
variant family with no selector, or just an unresolved subtree?), bucket
long variable names into short families for reporting, and build the
messages and metadata that Underdetermined errors and constraint-violation
reports carry.
"""

from __future__ import annotations

from typing import List, Set

from .equation import RelationRole
from .registry import Registry
from .resolver_models import ConstraintCheck, ConstraintViolation, UnresolvedInput
from .resolver_selection import _variant_keys
from .variable import Variable


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
