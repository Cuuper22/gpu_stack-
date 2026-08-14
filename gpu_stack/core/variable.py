"""
core/variable.py
================

A Variable is one named quantity in the model: a clock frequency, a die
area, a token count. It owns a SymPy symbol, human-readable metadata
(units, description, scope), and two lists of back-references that wire it
into the dependency graph: the equations that define it and the equations
that use it. Everything else in core — graph traversal, resolution, unit
checks — is built on those back-references.

Beyond the basics, a Variable can carry:
  * `value_range`: optional (min, max) bounds from physics or engineering.
  * `kind`: VariableKind (ROOT_INPUT, DERIVED, MEASURED, DEFINITIONAL).
  * `extensivity`: whether the quantity scales with system size.
  * `shape`: tensor shape for non-scalar quantities; None for scalars.
  * `sp_units`: optional SymPy dimensional expression for unit checking.
  * `references`: structured `Reference` list for provenance.

`Constant` is a Variable for universal physics constants: it refuses any
defining equation, and its numeric value cannot be changed after creation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Set, Tuple, Union, TYPE_CHECKING
import sympy as sp

from .registry import Registry

if TYPE_CHECKING:
    from .equation import Equation


class VariableKind(Enum):
    ROOT_INPUT    = auto()  # Must be supplied externally; no value-defining relation.
    DERIVED       = auto()  # Has one or more value-defining relations.
    MEASURED      = auto()  # Has an empirical value (e.g., a benchmark number).
    DEFINITIONAL  = auto()  # A name for a concept, not a quantity (e.g. "vocab").


class Extensivity(Enum):
    NONE      = auto()  # dimensionless count / ratio / fraction
    INTENSIVE = auto()  # does not scale with system size (temperature, voltage)
    EXTENSIVE = auto()  # scales with system size (power, mass, compute)


@dataclass(frozen=True)
class Reference:
    """Structured bibliographic reference."""
    citation: str
    kind: str = "paper"    # "paper" | "textbook" | "blog" | "datasheet" | "memo"
    url: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None


class Variable:
    """
    One named quantity in the model.

    Construct it once. The constructor registers it in the global Registry,
    and it lives for the rest of the program.

    Parameters
    ----------
    name, symbol, units, description, scope : core identification
    positive, real, integer : sympy symbol constraints. By default, Variables
        are real but unconstrained in sign and integrality.
    negative, nonnegative, nonpositive, noninteger, binary, signed : explicit
        domain switches for cases where SymPy assumptions should be stronger
        than the default.
    value_range : optional (min, max) bounds
    kind : VariableKind
    extensivity : Extensivity
    shape : tensor shape if non-scalar
    sp_units : optional sympy dimensional expression
    references : list of Reference
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        units: str,
        description: str,
        scope: str = "unknown",
        positive: Optional[bool] = None,
        real: Optional[bool] = True,
        integer: Optional[bool] = None,
        negative: bool = False,
        nonnegative: bool = False,
        nonpositive: bool = False,
        noninteger: bool = False,
        binary: bool = False,
        signed: bool = False,
        value_range: Optional[Tuple[float, float]] = None,
        kind: VariableKind = VariableKind.DERIVED,
        extensivity: Extensivity = Extensivity.NONE,
        shape: Optional[Tuple[int, ...]] = None,
        sp_units: Optional[sp.Expr] = None,
        references: Optional[List[Reference]] = None,
    ):
        self.name = name
        if binary:
            if noninteger:
                raise ValueError(f"{name}: binary variables must be integer.")
            integer = True
            nonnegative = True
            if value_range is None:
                value_range = (0.0, 1.0)

        sign_constraints = [
            positive is True,
            negative,
            nonnegative,
            nonpositive,
        ]
        if sum(1 for flag in sign_constraints if flag) > 1:
            raise ValueError(
                f"{name}: choose only one sign constraint among positive, "
                "negative, nonnegative, and nonpositive."
            )
        if integer is True and noninteger:
            raise ValueError(f"{name}: integer and noninteger cannot both be true.")

        assumptions = {}
        if real is not None:
            assumptions["real"] = real
        if positive is True:
            assumptions["positive"] = True
        elif negative:
            assumptions["negative"] = True
        elif nonnegative:
            assumptions["nonnegative"] = True
        elif nonpositive:
            assumptions["nonpositive"] = True

        if integer is True:
            assumptions["integer"] = True
        elif noninteger:
            assumptions["integer"] = False

        self.symbol = sp.Symbol(symbol, **assumptions)
        self.assumptions = dict(assumptions)
        self.signed = bool(signed or positive is False)
        self.binary = binary
        self.units = units
        self.description = description
        self.scope = scope
        self.value_range = value_range
        self.kind = kind
        self.extensivity = extensivity
        self.shape = shape
        self.sp_units = sp_units
        self.references: List[Reference] = list(references) if references else []
        self._defined_by: List["Equation"] = []
        self._used_in: List["Equation"] = []
        Registry.register_variable(self)

    # ----- wiring -----

    def defined_by(self, eq: "Equation") -> None:
        if eq not in self._defined_by:
            self._defined_by.append(eq)

    def used_in(self, eq: "Equation") -> None:
        if eq not in self._used_in:
            self._used_in.append(eq)

    @property
    def defining_equations(self) -> List["Equation"]:
        return list(self._defined_by)

    @property
    def appearances(self) -> List["Equation"]:
        return list(self._used_in)

    @property
    def is_root_input(self) -> bool:
        from .equation import RelationRole
        return not any(e.role is not RelationRole.CONSTRAINT for e in self._defined_by)

    # ----- role-filtered defining-equation access -----

    def identities(self) -> List["Equation"]:
        """Defining relations tagged as IDENTITY (definitional equalities)."""
        from .equation import RelationRole
        return [e for e in self._defined_by if e.role == RelationRole.IDENTITY]

    def constraints(self) -> List["Equation"]:
        """Defining relations tagged as CONSTRAINT (bounds that do not define)."""
        from .equation import RelationRole
        return [e for e in self._defined_by if e.role == RelationRole.CONSTRAINT]

    def approximations(self) -> List["Equation"]:
        """Defining relations tagged as APPROXIMATION (valid under a regime)."""
        from .equation import RelationRole
        return [e for e in self._defined_by if e.role == RelationRole.APPROXIMATION]

    def variants(self, key: Optional[str] = None) -> List["Equation"]:
        """
        Defining relations tagged as VARIANT. When `key` is provided, only
        variants whose `variant` string matches `key` are returned. Otherwise
        all variants are returned.
        """
        from .equation import RelationRole
        vs = [e for e in self._defined_by if e.role == RelationRole.VARIANT]
        if key is not None:
            vs = [e for e in vs if e.variant == key]
        return vs

    def has_multiple_definitions(self) -> bool:
        """True when the variable carries more than one defining relation."""
        return len(self._defined_by) > 1

    # ----- dependency traversal -----

    def direct_dependencies(
        self,
        include_constraints: bool = False,
    ) -> Set["Variable"]:
        """
        Variables directly referenced by value-defining relations.

        Constraints are excluded by default because a bound is not a
        derivation. Pass `include_constraints=True` for feasibility or audit
        views that intentionally want constraint RHS variables too.
        """
        from .equation import RelationRole
        deps: Set[Variable] = set()
        for eq in self._defined_by:
            if not include_constraints and eq.role == RelationRole.CONSTRAINT:
                continue
            if include_constraints and eq.role == RelationRole.CONSTRAINT:
                related = eq.variables_in_relation()
            else:
                related = eq.variables_on_rhs()
            for v in related:
                if v is not self:
                    deps.add(v)
        return deps

    def dependencies(
        self,
        _seen: Optional[Set["Variable"]] = None,
        include_constraints: bool = False,
    ) -> Set["Variable"]:
        """All Variables this one transitively depends on (cycle-safe)."""
        if _seen is None:
            _seen = set()
        if self in _seen:
            return set()
        _seen.add(self)
        out: Set[Variable] = set()
        for v in self.direct_dependencies(include_constraints=include_constraints):
            if v in _seen:
                continue
            out.add(v)
            out |= v.dependencies(_seen, include_constraints=include_constraints)
        return out

    def direct_dependents(
        self,
        include_constraints: bool = False,
    ) -> Set["Variable"]:
        from .equation import RelationRole
        deps: Set[Variable] = set()
        for eq in self._used_in:
            if not include_constraints and eq.role == RelationRole.CONSTRAINT:
                continue
            if include_constraints and eq.role == RelationRole.CONSTRAINT:
                for lhs in eq.variables_on_lhs():
                    if lhs is not self:
                        deps.add(lhs)
                continue
            lhs = eq.lhs_variable()
            if lhs is not None and lhs is not self:
                deps.add(lhs)
        return deps

    def dependents(
        self,
        _seen: Optional[Set["Variable"]] = None,
        include_constraints: bool = False,
    ) -> Set["Variable"]:
        if _seen is None:
            _seen = set()
        if self in _seen:
            return set()
        _seen.add(self)
        out: Set[Variable] = set()
        for v in self.direct_dependents(include_constraints=include_constraints):
            if v in _seen:
                continue
            out.add(v)
            out |= v.dependents(_seen, include_constraints=include_constraints)
        return out

    # ----- validation -----

    def in_range(self, value: float) -> bool:
        """Check if a value lies in the declared value_range."""
        if self.value_range is None:
            return True
        lo, hi = self.value_range
        return lo <= value <= hi

    # ----- pretty -----

    def __repr__(self) -> str:
        return f"<Var {self.name} [{self.symbol}] ({self.units})>"

    def __str__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other) -> bool:
        return isinstance(other, Variable) and other.name == self.name


class Constant(Variable):
    """
    A universal physics constant, such as the speed of light.

    Two guarantees a plain Variable does not make:
      * No equation may define it: `defined_by` raises.
      * Its numeric `value` and `source` cannot change after construction
        (enforced in `__setattr__`).
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        units: str,
        description: str,
        value: float,
        source: str = "",
        sp_units: Optional[sp.Expr] = None,
    ):
        super().__init__(
            name=name, symbol=symbol, units=units, description=description,
            scope="physics",
            positive=True,
            kind=VariableKind.DEFINITIONAL,
            extensivity=Extensivity.NONE,
            sp_units=sp_units,
        )
        # Set value through object.__setattr__ to avoid triggering the guard
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "_locked", True)

    def defined_by(self, eq: "Equation") -> None:
        raise TypeError(
            f"{self.name} is a universal physics constant and cannot be "
            "redefined by an equation."
        )

    def __setattr__(self, key, val):
        if getattr(self, "_locked", False) and key in ("value", "source"):
            raise AttributeError(f"Constant {self.name} is immutable")
        object.__setattr__(self, key, val)

    def as_sympy_float(self) -> sp.Float:
        return sp.Float(self.value)

    def __repr__(self) -> str:
        return f"<Const {self.name} = {self.value} {self.units}>"


__all__ = [
    "Variable",
    "Constant",
    "VariableKind",
    "Extensivity",
    "Reference",
]
