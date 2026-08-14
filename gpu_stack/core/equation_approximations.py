"""
Relations that hold only sometimes: approximations and piecewise equations.

An Approximation is an equality with a stated region of validity; a
PiecewiseEquation picks a different formula depending on which condition is
true. Both subclass the base Equation and add their conditions to the
dependency wiring so the graph knows about variables that appear only in
the conditions.
"""

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
    ``lhs ~= rhs``, trustworthy only while ``validity`` holds.

    ``validity`` is a SymPy predicate over Variables, for example x << 1.
    The resolver evaluates it for each scenario and reports when a selected
    approximation is being used outside its region of validity. Passing
    ``validity=True`` means "valid on the variables' declared domains": the
    domain relations of the RHS variables are recovered and used instead.
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
    ``lhs == Piecewise((expr1, cond1), ..., (default_expr, True))``.

    Use this when one quantity obeys different formulas in different
    regimes. Example: MOSFET drain current in cutoff, triode, and
    saturation. Each piece's expression and condition both count as
    dependencies, so regime-selecting variables stay visible in the graph.
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
