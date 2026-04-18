"""
core
====

Re-exports the core framework. Scope files use `from ..core import ...` and
remain unchanged.

Public surface:
  Registry
  Variable, Constant, VariableKind, Extensivity, Reference
  Equation, Inequality, Approximation, PiecewiseEquation,
  DifferentialEquation, IterativeEquation, StochasticRelation, EquationKind
  System
  var, eq  (convenience factories)
  Graph helpers: topological_sort, find_cycles, subgraph, to_dot
"""

from .registry import Registry
from .variable import (
    Variable, Constant, VariableKind, Extensivity, Reference,
)
from .equation import (
    Equation, Inequality, Approximation, PiecewiseEquation,
    DifferentialEquation, IterativeEquation, StochasticRelation,
    EquationKind, RelationRole, ExprLike,
)
from .system import System
from .graph import topological_sort, find_cycles, subgraph, to_dot
from .resolver import (
    AmbiguousVariant,
    ResolverError,
    ResolverResult,
    TraceStep,
    Underdetermined,
    resolve,
)
from .units import UnitError, check_dimensional_consistency


def var(name: str, symbol: str, units: str, description: str,
        scope: str = "unknown", **kwargs) -> Variable:
    """Shorthand for creating a Variable. Extra kwargs forwarded."""
    return Variable(name, symbol, units, description, scope, **kwargs)


def eq(name, lhs, rhs, description, references=None, check_units=False,
       role=None, variant=None) -> Equation:
    """
    Shorthand for creating an (algebraic) Equation. `role` and `variant` are
    forwarded to the Equation constructor so variant tagging stays ergonomic
    in scope files that otherwise use this factory.
    """
    return Equation(name, lhs, rhs, description, references, check_units,
                    role=role, variant=variant)


__all__ = [
    "Registry",
    "Variable", "Constant", "VariableKind", "Extensivity", "Reference",
    "Equation", "Inequality", "Approximation", "PiecewiseEquation",
    "DifferentialEquation", "IterativeEquation", "StochasticRelation",
    "EquationKind", "RelationRole", "ExprLike",
    "System",
    "var", "eq",
    "topological_sort", "find_cycles", "subgraph", "to_dot",
    "resolve", "ResolverResult", "TraceStep",
    "ResolverError", "Underdetermined", "AmbiguousVariant",
    "UnitError", "check_dimensional_consistency",
]
