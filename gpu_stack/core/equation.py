"""
core/equation.py
================

Public facade for equation classes and structural relation helpers.

The implementation lives in focused equation_* modules so each relation
family stays small enough to reason about.  This module remains the stable
import surface for existing code:

    from gpu_stack.core.equation import Equation, Inequality, RelationRole
"""

from __future__ import annotations

from .equation_approximations import Approximation, PiecewiseEquation
from .equation_base import Equation
from .equation_constraints import Inequality
from .equation_dynamics import DifferentialEquation, IterativeEquation
from .equation_stochastic import StochasticRelation
from .equation_structural import (
    domain_relations_for_variable,
    ge,
    gt,
    le,
    lt,
    ne,
    valid_all,
)
from .equation_types import EquationKind, RelationRole
from .symbolic import ExprLike


def _pin_public_module() -> None:
    """Keep repr/pickle-style metadata compatible with the old monolith."""
    for obj in (
        Equation,
        Inequality,
        Approximation,
        PiecewiseEquation,
        DifferentialEquation,
        IterativeEquation,
        StochasticRelation,
        EquationKind,
        RelationRole,
        gt,
        ge,
        lt,
        le,
        ne,
        valid_all,
        domain_relations_for_variable,
    ):
        obj.__module__ = __name__


_pin_public_module()


__all__ = [
    "Equation",
    "Inequality",
    "Approximation",
    "PiecewiseEquation",
    "DifferentialEquation",
    "IterativeEquation",
    "StochasticRelation",
    "EquationKind",
    "RelationRole",
    "ExprLike",
    "gt",
    "ge",
    "lt",
    "le",
    "ne",
    "valid_all",
    "domain_relations_for_variable",
]
