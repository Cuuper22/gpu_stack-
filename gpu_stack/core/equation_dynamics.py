"""
Relations defined by change or by repetition.

A DifferentialEquation states a rate of change: d(lhs)/d(indep_var) = rhs.
An IterativeEquation states a fixed procedure: apply a map to an initial
value some number of times. Both keep their extra structure (independent
variable, boundary conditions, iteration binder) visible to the dependency
graph without leaking local binder symbols as model dependencies.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Set, Union

import sympy as sp

from .equation_base import Equation
from .equation_types import EquationKind, RelationRole
from .symbolic import (
    ExprLike,
    registered_free_variable_names,
    small_nonnegative_int,
    to_expr,
)
from .variable import Variable


class DifferentialEquation(Equation):
    """
    ``d^order(lhs) / d(indep_var)^order == rhs``.

    Typical use: dN/dt = -lambda*N, dV/dt = I/C, or d2x/dt2 = F/m.
    ``boundary`` carries initial/boundary conditions as a plain dict.
    """

    kind = EquationKind.DIFFERENTIAL

    def __init__(
        self,
        name,
        lhs,
        rhs,
        indep_var: Union[Variable, sp.Symbol],
        order: int = 1,
        boundary: Optional[Dict] = None,
        description: str = "",
        references=None,
        check_units: bool = False,
        role: Optional[RelationRole] = None,
        variant: Optional[str] = None,
    ):
        self.indep_sym = (
            indep_var.symbol if isinstance(indep_var, Variable) else indep_var
        )
        self.order = order
        self.boundary = boundary or {}
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
        lhs_expr = self.lhs
        if isinstance(lhs_expr, sp.Symbol):
            f = sp.Function(str(lhs_expr))
            deriv = sp.Derivative(f(self.indep_sym), (self.indep_sym, self.order))
        else:
            deriv = sp.Derivative(lhs_expr, (self.indep_sym, self.order))
        return sp.Eq(deriv, self.rhs)

    def _dependency_exprs(self) -> List[object]:
        return [self.rhs, self.indep_sym]


class IterativeEquation(Equation):
    """
    ``lhs`` is what you get by applying ``map_expr`` repeatedly, starting
    from ``initial``, either ``n_iter`` times or until ``convergence`` holds.

    Typical use: Newton-Schulz iteration for matrix orthogonalization in
    Muon. The ``iteration_variable`` is a local binder — it stands for
    "the previous iterate", not a model quantity, so it is excluded from
    dependency wiring.
    """

    kind = EquationKind.ITERATIVE

    def __init__(
        self,
        name,
        lhs,
        map_expr: ExprLike,
        iteration_variable: Union[Variable, sp.Symbol, str],
        initial: Optional[ExprLike] = None,
        n_iter: Optional[ExprLike] = None,
        convergence: Optional[sp.Expr] = None,
        description: str = "",
        references=None,
        check_units: bool = False,
        role: Optional[RelationRole] = None,
        variant: Optional[str] = None,
    ):
        self.map_expr = to_expr(map_expr)
        if isinstance(iteration_variable, Variable):
            self.iter_sym = iteration_variable.symbol
        elif isinstance(iteration_variable, sp.Symbol):
            self.iter_sym = iteration_variable
        else:
            self.iter_sym = sp.Symbol(str(iteration_variable))
        self.initial = to_expr(initial) if initial is not None else None
        self.n_iter = to_expr(n_iter) if n_iter is not None else None
        self.convergence = convergence
        super().__init__(
            name,
            lhs,
            self.map_expr,
            description,
            references,
            check_units,
            role=role,
            variant=variant,
        )

    def unfold(self, k: int) -> sp.Expr:
        """Unfold the iteration k times starting from ``initial``."""
        if self.initial is None:
            raise ValueError("No initial value set for this IterativeEquation.")
        x = self.initial
        for _ in range(k):
            x = self.map_expr.subs(self.iter_sym, x)
        return x

    def as_sympy(self):
        return sp.Eq(self.lhs, self.value_expr({}), evaluate=False)

    def _dependency_exprs(self) -> List[object]:
        return self._iteration_exprs()

    def _value_dependency_exprs(self) -> List[object]:
        return self._iteration_exprs()

    def _iteration_exprs(self) -> List[object]:
        exprs: List[object] = [
            self.map_expr,
            self.initial,
            self.n_iter,
            self.convergence,
        ]
        return [expr for expr in exprs if expr is not None]

    def _bound_symbols(self) -> Set[sp.Symbol]:
        return {self.iter_sym}

    def value_expr(
        self,
        subs: Optional[Mapping[sp.Symbol, sp.Expr]] = None,
    ) -> sp.Expr:
        """
        The iterated value as an expression, without leaking the binder.

        When the iteration count is a small concrete integer and every input
        is already numeric, unfold the map that many times and return the
        closed result. Otherwise return a symbolic ``iterate(f, x0, n)``
        placeholder that keeps the structure inspectable.
        """
        bound_symbols = self._bound_symbols()
        subs_map = {
            sym: value
            for sym, value in dict(subs or {}).items()
            if sym not in bound_symbols
        }
        map_expr = self.map_expr.subs(subs_map)
        initial = (
            self.initial.subs(subs_map)
            if self.initial is not None
            else None
        )
        n_iter = (
            self.n_iter.subs(subs_map)
            if self.n_iter is not None
            else sp.oo
        )

        k = small_nonnegative_int(n_iter)
        if initial is not None and k is not None:
            unresolved = (
                registered_free_variable_names(map_expr, bound_symbols)
                | registered_free_variable_names(initial, bound_symbols)
            )
            if not unresolved:
                x = initial
                for _ in range(k):
                    x = map_expr.subs(self.iter_sym, x)
                return x

        args = [sp.Lambda(self.iter_sym, map_expr)]
        if initial is not None:
            args.append(initial)
        args.append(n_iter)
        return sp.Function("iterate")(*args)


__all__ = ["DifferentialEquation", "IterativeEquation"]
