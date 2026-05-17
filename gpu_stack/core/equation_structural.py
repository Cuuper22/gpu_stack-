"""Public structural relation helpers used by equation constructors."""

from __future__ import annotations

from typing import List, Tuple

import sympy as sp

from .equation_relations import (
    domain_relations_for_variable as _domain_relations_for_variable,
)
from .equation_relations import ge as _ge
from .equation_relations import gt as _gt
from .equation_relations import le as _le
from .equation_relations import lt as _lt
from .equation_relations import ne as _ne
from .equation_relations import valid_all as _valid_all
from .symbolic import ExprLike
from .variable import Variable


def gt(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Strict greater-than relation that does not simplify under assumptions."""
    return _gt(lhs, rhs)


def ge(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Greater-than-or-equal relation that does not simplify under assumptions."""
    return _ge(lhs, rhs)


def lt(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Strict less-than relation that does not simplify under assumptions."""
    return _lt(lhs, rhs)


def le(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Less-than-or-equal relation that does not simplify under assumptions."""
    return _le(lhs, rhs)


def ne(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Not-equal relation that does not simplify under assumptions."""
    return _ne(lhs, rhs)


def valid_all(*conditions: object) -> sp.Expr:
    """Conjunction that keeps approximation-validity predicates structural."""
    return _valid_all(*conditions)


def domain_relations_for_variable(var: Variable) -> List[Tuple[str, sp.Expr]]:
    """Structural relations implied by a variable's declared domain metadata."""
    return _domain_relations_for_variable(var)


__all__ = [
    "gt",
    "ge",
    "lt",
    "le",
    "ne",
    "valid_all",
    "domain_relations_for_variable",
]
