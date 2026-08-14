"""
StochasticRelation: a relation whose left-hand side is a random variable.

Instead of a deterministic RHS, it records a distribution name and its
parameters, plus optional mean and variance expressions. The parameters and
moment expressions all count as dependencies, so randomness stays visible
in the graph.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import sympy as sp

from .equation_base import Equation
from .equation_types import EquationKind, RelationRole
from .symbolic import ExprLike, to_expr


class StochasticRelation(Equation):
    """
    ``lhs`` is drawn from a named distribution rather than computed.

    The RHS is a symbolic function call ``distribution(*parameters)``.
    Optional ``mean`` and ``variance`` expressions are stored for graph
    diagnostics; they count as dependencies but are not needed to state
    the relation's value.
    """

    kind = EquationKind.STOCHASTIC

    def __init__(
        self,
        name,
        lhs,
        distribution: str,
        parameters: Dict[str, ExprLike],
        mean: Optional[ExprLike] = None,
        variance: Optional[ExprLike] = None,
        description: str = "",
        references=None,
        role: Optional[RelationRole] = None,
        variant: Optional[str] = None,
    ):
        self.distribution = distribution
        self.parameters = {k: to_expr(v) for k, v in parameters.items()}
        self.mean_expr = to_expr(mean) if mean is not None else None
        self.variance_expr = to_expr(variance) if variance is not None else None
        rhs = sp.Function(distribution)(*self.parameters.values())
        super().__init__(
            name,
            lhs,
            rhs,
            description,
            references,
            role=role,
            variant=variant,
        )

    def _dependency_exprs(self) -> List[object]:
        exprs: List[object] = [self.rhs]
        exprs.extend(self.parameters.values())
        exprs.append(self.mean_expr)
        exprs.append(self.variance_expr)
        return [expr for expr in exprs if expr is not None]

    def _value_dependency_exprs(self) -> List[object]:
        exprs: List[object] = [self.rhs]
        exprs.extend(self.parameters.values())
        return [expr for expr in exprs if expr is not None]


__all__ = ["StochasticRelation"]
