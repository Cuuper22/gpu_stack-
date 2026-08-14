"""
core/symbolic.py
================

Small SymPy helpers shared by the relation layer.

Two recurring jobs live here. First, coercion: model code hands us numbers,
strings, Variables, or SymPy expressions, and `to_expr` turns any of them
into a SymPy expression. Second, symbol classification: given an
expression, separate the symbols that belong to registered model Variables
from local binders and stray unregistered symbols, since only the former
are real dependencies.
"""

from __future__ import annotations

from typing import List, Optional, Set, Union

import sympy as sp

from .registry import Registry
from .variable import Variable


ExprLike = Union[sp.Expr, int, float, str, Variable]


def to_expr(x: ExprLike) -> sp.Expr:
    if isinstance(x, sp.Expr):
        return x
    if isinstance(x, Variable):
        return x.symbol
    return sp.sympify(x)


def small_nonnegative_int(expr: sp.Expr, max_value: int = 32) -> Optional[int]:
    """
    Extract a concrete int in [0, max_value] from an expression, else None.

    Used to decide whether an iteration count is small enough to unfold
    literally. Symbolic, negative, non-integer, or oversized values all
    return None.
    """
    expr = sp.sympify(expr)
    if getattr(expr, "free_symbols", set()):
        return None
    if expr.is_integer is False:
        return None
    try:
        value = int(expr)
    except (TypeError, ValueError):
        return None
    if value < 0 or value > max_value:
        return None
    delta = sp.simplify(expr - sp.Integer(value))
    if delta != 0:
        try:
            if float(delta) != 0.0:
                return None
        except (TypeError, ValueError):
            return None
    return value


def registered_free_variable_names(
    expr: sp.Expr,
    bound_symbols: Optional[Set[sp.Symbol]] = None,
) -> Set[str]:
    """Names of registered model Variables still free in an expression."""
    bound_symbols = set(bound_symbols or set())
    return {
        v.name
        for sym in getattr(expr, "free_symbols", set()) - bound_symbols
        if (v := Registry.lookup_by_symbol(sym)) is not None
    }


def registered_variables_in_exprs(
    exprs: List[object],
    bound_symbols: Optional[Set[sp.Symbol]] = None,
) -> List[Variable]:
    """Registered Variables referenced by the expressions, in first-seen order."""
    out: List[Variable] = []
    seen: Set[str] = set()
    bound_symbols = set(bound_symbols or set())
    for expr in exprs:
        for sym in getattr(sp.sympify(expr), "free_symbols", set()) - bound_symbols:
            v = Registry.lookup_by_symbol(sym)
            if v is not None and v.name not in seen:
                out.append(v)
                seen.add(v.name)
    return out


def raw_dependency_symbols_for_exprs(
    exprs: List[object],
    bound_symbols: Optional[Set[sp.Symbol]] = None,
) -> Set[sp.Symbol]:
    """
    Symbols in dependency-bearing fields that map to no registered Variable.

    These usually indicate a typo or a missing declaration, which is why
    audits care about them. Dummy symbols are skipped: they are local
    binders, not model quantities.
    """
    raw: Set[sp.Symbol] = set()
    bound_symbols = set(bound_symbols or set())
    for expr in exprs:
        for sym in getattr(sp.sympify(expr), "free_symbols", set()) - bound_symbols:
            if isinstance(sym, sp.Dummy):
                continue
            if Registry.lookup_by_symbol(sym) is None:
                raw.add(sym)
    return raw


__all__ = [
    "ExprLike",
    "to_expr",
    "small_nonnegative_int",
    "registered_free_variable_names",
    "registered_variables_in_exprs",
    "raw_dependency_symbols_for_exprs",
]
