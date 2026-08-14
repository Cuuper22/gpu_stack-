"""
Builders for relations that must stay structural.

SymPy likes to evaluate relations eagerly: given a symbol declared
positive, ``sym >= 0`` collapses to True and the relation object is gone.
Constraints and validity predicates need to survive as objects so the
resolver can evaluate them against a specific scenario later. Every helper
here builds its relation with ``evaluate=False`` for exactly that reason.

The domain helpers translate a Variable's declared metadata (sign
assumptions, value_range, integrality) into the same kind of structural
relations, so declared domains can be checked like any other constraint.
"""

from __future__ import annotations

from typing import List, Set, Tuple

import sympy as sp

from .registry import Registry
from .symbolic import ExprLike, to_expr
from .variable import Variable


def gt(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Strict greater-than relation that does not simplify under assumptions."""
    return sp.StrictGreaterThan(to_expr(lhs), to_expr(rhs), evaluate=False)


def ge(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Greater-than-or-equal relation that does not simplify under assumptions."""
    return sp.GreaterThan(to_expr(lhs), to_expr(rhs), evaluate=False)


def lt(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Strict less-than relation that does not simplify under assumptions."""
    return sp.StrictLessThan(to_expr(lhs), to_expr(rhs), evaluate=False)


def le(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Less-than-or-equal relation that does not simplify under assumptions."""
    return sp.LessThan(to_expr(lhs), to_expr(rhs), evaluate=False)


def ne(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Not-equal relation that does not simplify under assumptions."""
    return sp.Ne(to_expr(lhs), to_expr(rhs), evaluate=False)


def valid_all(*conditions: object) -> sp.Expr:
    """Conjunction that keeps approximation-validity predicates structural."""
    if not conditions:
        return sp.Eq(sp.Integer(0), sp.Integer(0), evaluate=False)
    return sp.And(*(sp.sympify(condition) for condition in conditions), evaluate=False)


def domain_relations_for_variable(var: Variable) -> List[Tuple[str, sp.Expr]]:
    """
    Turn a variable's declared domain metadata into checkable relations.

    Returns (suffix, relation) pairs: sign assumptions become inequalities
    against zero, value_range becomes min/max bounds, and integrality
    becomes a Mod-based equality or non-equality.
    """
    relations: List[Tuple[str, sp.Expr]] = []
    sym = var.symbol
    assumptions = getattr(var, "assumptions", {})
    if assumptions.get("positive") is True:
        relations.append(("positive", gt(sym, 0)))
    elif assumptions.get("negative") is True:
        relations.append(("negative", lt(sym, 0)))
    elif assumptions.get("nonnegative") is True:
        relations.append(("nonnegative", ge(sym, 0)))
    elif assumptions.get("nonpositive") is True:
        relations.append(("nonpositive", le(sym, 0)))

    if var.value_range is not None:
        lo, hi = var.value_range
        relations.append(("min", ge(sym, sp.sympify(lo))))
        relations.append(("max", le(sym, sp.sympify(hi))))

    if assumptions.get("integer") is True:
        relations.append(
            (
                "integer",
                sp.Eq(
                    sp.Mod(sym, sp.Integer(1), evaluate=False),
                    sp.Integer(0),
                    evaluate=False,
                ),
            )
        )
    elif assumptions.get("integer") is False:
        relations.append(
            (
                "noninteger",
                sp.Ne(
                    sp.Mod(sym, sp.Integer(1), evaluate=False),
                    sp.Integer(0),
                    evaluate=False,
                ),
            )
        )
    return relations


def domain_validity_for_exprs(exprs: List[object]) -> List[sp.Expr]:
    """Collect domain relations for every registered variable in the given
    expressions, deduplicated across expressions."""
    relations: List[sp.Expr] = []
    seen: Set[Tuple[str, str]] = set()
    for expr in exprs:
        for sym in getattr(sp.sympify(expr), "free_symbols", set()):
            var = Registry.lookup_by_symbol(sym)
            if var is None:
                continue
            for suffix, relation in domain_relations_for_variable(var):
                key = (var.name, suffix)
                if key in seen:
                    continue
                seen.add(key)
                relations.append(relation)
    return relations


__all__ = [
    "gt",
    "ge",
    "lt",
    "le",
    "ne",
    "valid_all",
    "domain_relations_for_variable",
    "domain_validity_for_exprs",
]
