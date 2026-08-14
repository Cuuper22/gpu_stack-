"""
core/equation.py
================

The one import surface for every equation class and relation helper.

The implementations live in focused equation_* modules — one file per
relation family — so each stays small enough to reason about. This module
re-exports them all, which means existing code keeps working unchanged:

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
    """
    Stamp each re-exported class with this module's name.

    reprs, pickling, and doc tools all read ``__module__``; without this,
    they would advertise the private equation_* modules instead of the
    stable public path.
    """
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
