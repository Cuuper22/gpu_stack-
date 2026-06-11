"""Private helpers for :mod:`gpu_stack.core.resolver`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Set, Tuple, Union

import sympy as sp

from .equation import RelationRole
from .variable import Variable


AssignmentKey = Union[Variable, sp.Symbol, str]
AssignmentValue = Union[float, int, sp.Expr]


class ResolverError(RuntimeError):
    """Base error for the scenario resolver."""


class Underdetermined(ResolverError):
    """Raised when the scenario does not pin down enough values to proceed."""

    def __init__(
        self,
        message: str,
        missing: Optional[Set[str]] = None,
        unresolved_inputs: Optional[List["UnresolvedInput"]] = None,
    ):
        super().__init__(message)
        self.missing = set(missing or set())
        self.unresolved_inputs = list(unresolved_inputs or [])


class AmbiguousVariant(ResolverError):
    """Raised when multiple variant relations match without a selector."""


class InvalidVariantSelector(ResolverError):
    """Raised when a variant selector does not name a valid variant family."""


@dataclass
class TraceStep:
    """One equation application step."""
    variable: str
    equation: str
    role: RelationRole
    variant: Optional[str]
    value: sp.Expr
    # Selection explanation fields (optional; populated when explanation is enabled
    # or when fallback/system-solve paths are taken).
    selection_reason: Optional[str] = None
    # Populated when fallback-on-violated-validity triggered: the equation
    # that was originally selected but whose validity check was violated.
    fallback_from: Optional[str] = None
    # Populated by system-solve steps: the other variable names resolved
    # simultaneously with this one.
    system_peers: Optional[Tuple[str, ...]] = None


@dataclass
class ConstraintCheck:
    """One feasibility relation evaluated against the resolved scenario."""
    equation: str
    variable: str
    relation: sp.Expr
    evaluated: sp.Expr
    satisfied: Optional[bool]
    missing: Set[str] = field(default_factory=set)
    inputs: Dict[str, sp.Expr] = field(default_factory=dict)


@dataclass
class ApproximationValidityCheck:
    """One selected approximation validity predicate evaluated for a scenario."""
    equation: str
    variable: str
    validity: sp.Expr
    evaluated: sp.Expr
    satisfied: Optional[bool]
    missing: Set[str] = field(default_factory=set)


@dataclass(frozen=True)
class UnresolvedInput:
    """Actionable metadata for a symbolic boundary left in a scenario."""
    variable: str
    symbol: str
    units: str
    scope: str
    kind: str
    reason: str
    description: str
    variant_keys: Tuple[str, ...] = ()
    defining_equations: Tuple[str, ...] = ()
    direct_dependents: Tuple[str, ...] = ()
    dependents_count: int = 0
    family: str = ""
    boundary_category: str = ""
    primitive_boundary: bool = False
    # Alternative equations that existed but were not selectable (e.g. missing
    # inputs, wrong role, validity not checkable). Populated by the resolver
    # when selection explanation is requested.
    not_selectable_alternatives: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ConstraintViolation:
    """Actionable metadata for a feasibility relation evaluated as false."""
    equation: str
    variable: str
    relation: sp.Expr
    evaluated: sp.Expr
    description: str
    missing: Set[str] = field(default_factory=set)
    inputs: Dict[str, sp.Expr] = field(default_factory=dict)


@dataclass
class ResolverResult:
    """
    Resolver output.

    value     : numeric or symbolic value of the target Variable.
    trace     : ordered list of equation applications used to reach value.
    values    : dict name -> substituted expression for every Variable
                computed along the way.
    missing   : Variables that were needed but had no scenario assignment
                and no eligible defining equation.
    constraints: constraint relations from the target dependency cone,
                evaluated as far as the scenario permits.
    approximation_validity
              : approximation validity relations from selected trace
                equations, evaluated as far as the scenario permits.
    unresolved_inputs
              : richer metadata for names in `missing`.
    violated_constraints
              : richer metadata for constraint checks that evaluated false.
    """
    value: sp.Expr
    trace: List[TraceStep] = field(default_factory=list)
    values: Dict[str, sp.Expr] = field(default_factory=dict)
    missing: Set[str] = field(default_factory=set)
    constraints: List[ConstraintCheck] = field(default_factory=list)
    approximation_validity: List[ApproximationValidityCheck] = field(default_factory=list)
    unresolved_inputs: List[UnresolvedInput] = field(default_factory=list)
    violated_constraints: List[ConstraintViolation] = field(default_factory=list)
