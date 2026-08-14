"""
core
====

The engine of the model: variables, equations, units, and graph resolution.

This package is the single import surface for that engine. Scope files (the
files that declare actual hardware and workload quantities) write
`from ..core import ...` and never reach into submodules, so the internal
layout can change without breaking them.

Public surface:
  Registry
  Variable, Constant, VariableKind, Extensivity, Reference
  Equation, Inequality, Approximation, PiecewiseEquation,
  DifferentialEquation, IterativeEquation, StochasticRelation, EquationKind
  System
  var, eq  (convenience factories)
  Graph helpers: topological_sort, find_cycles, subgraph, to_dot
  Resolver helpers: resolve, ResolverResult, TraceStep, ConstraintCheck,
  ApproximationValidityCheck, ResolverError, Underdetermined,
  AmbiguousVariant, InvalidVariantSelector
  Presets: Preset, combine_presets
  Units: UnitError, check_dimensional_consistency, infer_expr_units
"""

from .registry import Registry
from .variable import (
    Variable, Constant, VariableKind, Extensivity, Reference,
)
from .equation import (
    Equation, Inequality, Approximation, PiecewiseEquation,
    DifferentialEquation, IterativeEquation, StochasticRelation,
    EquationKind, RelationRole, ExprLike,
    gt, ge, lt, le, ne, valid_all, domain_relations_for_variable,
)
from .system import System
from .graph import topological_sort, find_cycles, subgraph, to_dot
from .resolver import (
    AmbiguousVariant,
    ApproximationValidityCheck,
    ConstraintCheck,
    InvalidVariantSelector,
    ResolverError,
    ResolverResult,
    TraceStep,
    Underdetermined,
    resolve,
)
from .presets import (
    MissingFamilySummary,
    Preset,
    ScenarioReport,
    ScenarioTargetReport,
    combine as combine_presets,
)
from .units import UnitError, check_dimensional_consistency, infer_expr_units


def var(name: str, symbol: str, units: str, description: str,
        scope: str = "unknown", **kwargs) -> Variable:
    """Shorthand for creating a Variable. Extra kwargs are forwarded unchanged."""
    return Variable(name, symbol, units, description, scope, **kwargs)


def eq(name, lhs, rhs, description, references=None, check_units=False,
       role=None, variant=None) -> Equation:
    """
    Shorthand for creating an algebraic Equation. `role` and `variant` pass
    straight through to the Equation constructor, so scope files that use
    this factory can still tag variant relations without switching to the
    full class.
    """
    return Equation(name, lhs, rhs, description, references, check_units,
                    role=role, variant=variant)


__all__ = [
    "Registry",
    "Variable", "Constant", "VariableKind", "Extensivity", "Reference",
    "Equation", "Inequality", "Approximation", "PiecewiseEquation",
    "DifferentialEquation", "IterativeEquation", "StochasticRelation",
    "EquationKind", "RelationRole", "ExprLike",
    "gt", "ge", "lt", "le", "ne", "valid_all", "domain_relations_for_variable",
    "System",
    "var", "eq",
    "topological_sort", "find_cycles", "subgraph", "to_dot",
    "resolve", "ResolverResult", "TraceStep", "ConstraintCheck",
    "ApproximationValidityCheck",
    "ResolverError", "Underdetermined", "AmbiguousVariant",
    "InvalidVariantSelector",
    "MissingFamilySummary", "ScenarioReport", "ScenarioTargetReport",
    "Preset", "combine_presets",
    "UnitError", "check_dimensional_consistency", "infer_expr_units",
]
