"""
Equation selection for the scenario resolver.

A variable can have several defining relations — one exact identity, a few
approximations, or a family of tagged variants. The resolver must commit to
exactly one before it can compute a value. The rule, implemented in
`_select_equation`: a sole identity always wins; a variant family requires
the caller to name a variant key; a sole approximation is the fallback.
Any genuine tie raises AmbiguousVariant instead of guessing.

The rest of this module normalizes assignment keys and validates variant
selectors before resolution starts.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional

import sympy as sp

from .equation import Equation, RelationRole
from .registry import Registry
from .resolver_models import (
    AmbiguousVariant,
    AssignmentKey,
    AssignmentValue,
    InvalidVariantSelector,
    ResolverError,
)
from .variable import Variable


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
