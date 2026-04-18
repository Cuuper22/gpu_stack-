"""
core/variable.py
================

Variable and Constant classes.

Extensions over the original:
  * `value_range`: optional (min, max) tuple for physical/engineering bounds.
  * `kind`: VariableKind enum (ROOT_INPUT, DERIVED, MEASURED, DEFINITIONAL).
  * `extensivity`: INTENSIVE or EXTENSIVE or NONE (for aggregation semantics).
  * `shape`: tuple for tensor-valued quantities; None for scalars.
  * `sp_units`: optional sympy dimensional expression for unit checking.
  * `references`: structured `Reference` list.
  * `Constant`: locked AND its value immutable; also comes with a numeric
    value helper that returns a sympy Float for use in substitutions.
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
    ROOT_INPUT    = auto()  # Must be supplied externally; no defining equation.
    DERIVED       = auto()  # Has one or more defining equations.
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
    A quantity in the model.

    Construct once; registered globally; lifetime = program lifetime.

    Parameters
    ----------
    name, symbol, units, description, scope : core identification
    positive, real, integer : sympy symbol constraints
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
        positive: bool = True,
        real: bool = True,
        integer: bool = False,
        value_range: Optional[Tuple[float, float]] = None,
        kind: VariableKind = VariableKind.DERIVED,
        extensivity: Extensivity = Extensivity.NONE,
        shape: Optional[Tuple[int, ...]] = None,
        sp_units: Optional[sp.Expr] = None,
        references: Optional[List[Reference]] = None,
    ):
        self.name = name
        self.symbol = sp.Symbol(symbol, positive=positive, real=real, integer=integer)
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
        return not self._defined_by

    # ----- dependency traversal -----

    def direct_dependencies(self) -> Set["Variable"]:
        """Variables directly referenced on the RHS of any defining equation."""
        deps: Set[Variable] = set()
        for eq in self._defined_by:
            for v in eq.variables_on_rhs():
                if v is not self:
                    deps.add(v)
        return deps

    def dependencies(self, _seen: Optional[Set["Variable"]] = None) -> Set["Variable"]:
        """All Variables this one transitively depends on (cycle-safe)."""
        if _seen is None:
            _seen = set()
        if self in _seen:
            return set()
        _seen.add(self)
        out: Set[Variable] = set()
        for v in self.direct_dependencies():
            if v in _seen:
                continue
            out.add(v)
            out |= v.dependencies(_seen)
        return out

    def direct_dependents(self) -> Set["Variable"]:
        deps: Set[Variable] = set()
        for eq in self._used_in:
            lhs = eq.lhs_variable()
            if lhs is not None and lhs is not self:
                deps.add(lhs)
        return deps

    def dependents(self, _seen: Optional[Set["Variable"]] = None) -> Set["Variable"]:
        if _seen is None:
            _seen = set()
        if self in _seen:
            return set()
        _seen.add(self)
        out: Set[Variable] = set()
        for v in self.direct_dependents():
            if v in _seen:
                continue
            out.add(v)
            out |= v.dependents(_seen)
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
    A universal physics constant.
      * Locked against further definition.
      * Numeric value immutable (enforced via __setattr__).
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
        # After construction, block mutation of value/source
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
