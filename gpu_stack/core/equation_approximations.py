"""Approximation and piecewise equation subclasses."""

from __future__ import annotations

from typing import List, Optional, Tuple

import sympy as sp

from .equation_base import Equation
from .equation_relations import domain_validity_for_exprs as _domain_validity_for_exprs
from .equation_structural import valid_all
from .equation_types import EquationKind, RelationRole
from .symbolic import ExprLike, to_expr


class Approximation(Equation):
    """
    lhs ~= rhs, valid when ``validity`` holds.

    ``validity`` is a SymPy expression over Variables, for example x << 1.
    """

    kind = EquationKind.APPROXIMATION
    default_role = RelationRole.APPROXIMATION

    def __init__(
        self,
        name,
        lhs,
        rhs,
        validity: sp.Expr,
        description: str,
        references=None,
        check_units: bool = False,
        role: Optional[RelationRole] = None,
        variant: Optional[str] = None,
    ):
        self.validity = self._normalize_validity(name, rhs, validity)
        super().__init__(
            name,
            lhs,
            rhs,
            description,
            references,
            check_units,
            role=role,
            variant=variant,
        )

    def as_sympy(self):
        return sp.Eq(self.lhs, self.rhs, evaluate=False)

    @staticmethod
    def _normalize_validity(name: str, rhs: ExprLike, validity: sp.Expr) -> sp.Expr:
        validity = sp.sympify(validity)
        if validity is sp.S.false:
            raise ValueError(f"{name}: Approximation validity collapsed to False.")
        if validity is sp.S.true:
            recovered = _domain_validity_for_exprs([to_expr(rhs)])
            return valid_all(*recovered)
        return validity

    def _dependency_exprs(self) -> List[object]:
        return [self.rhs, self.validity]

    def __repr__(self):
        return (
            f"<Approximation {self.name}: "
            f"{self.lhs} ≈ {self.rhs} when {self.validity}>"
        )


class PiecewiseEquation(Equation):
    """
    lhs == Piecewise((expr1, cond1), (expr2, cond2), ..., (default_expr, True)).

    Example: MOSFET drain current has different formulas in cutoff, triode,
    and saturation.
    """

    kind = EquationKind.PIECEWISE

    def __init__(
        self,
        name,
        lhs,
        pieces: List[Tuple[ExprLike, sp.Expr]],
        description: str,
        references=None,
        check_units: bool = False,
        role: Optional[RelationRole] = None,
        variant: Optional[str] = None,
    ):
        self.pieces = [(to_expr(e), c) for e, c in pieces]
        rhs = sp.Piecewise(*self.pieces, evaluate=False)
        super().__init__(
            name,
            lhs,
            rhs,
            description,
            references,
            check_units,
            role=role,
            variant=variant,
        )

    def _dependency_exprs(self) -> List[object]:
        exprs: List[object] = [self.rhs]
        for expr, condition in self.pieces:
            exprs.append(expr)
            exprs.append(condition)
        return exprs


__all__ = ["Approximation", "PiecewiseEquation"]
