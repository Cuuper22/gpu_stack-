"""
core/equation.py
================

Equation and its specialized subclasses.

Kinds supported:
  * Equation           : lhs == rhs, algebraic.
  * Inequality         : lhs <= rhs  or  lhs < rhs  (constraint).
  * Approximation      : lhs ~= rhs, with a validity condition.
  * PiecewiseEquation  : lhs == piecewise over conditions on other Variables.
  * DifferentialEquation: d lhs / d indep_var == rhs  (ODE/PDE).
  * IterativeEquation  : lhs is produced by applying a map f iteratively
                         from an initial condition; has n_iter and
                         a convergence criterion.
  * StochasticRelation : lhs is a random variable with given distribution or
                         moment structure.

All subclasses still register with the Registry via Equation.__init__.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Union, Callable
import sympy as sp

from .registry import Registry
from .variable import Variable, Reference


ExprLike = Union[sp.Expr, int, float, str, Variable]


def _to_expr(x: ExprLike) -> sp.Expr:
    if isinstance(x, sp.Expr):
        return x
    if isinstance(x, Variable):
        return x.symbol
    return sp.sympify(x)


class EquationKind(Enum):
    ALGEBRAIC    = auto()
    INEQUALITY   = auto()
    APPROXIMATION = auto()
    PIECEWISE    = auto()
    DIFFERENTIAL = auto()
    ITERATIVE    = auto()
    STOCHASTIC   = auto()
    DEFINITIONAL = auto()


class RelationRole(Enum):
    """
    Semantic role of a relation that touches a Variable's back-references.

    IDENTITY is a definitional equality. The algebraic `Equation` base class
    defaults to this. Most scope equations are identities.

    CONSTRAINT bounds a Variable without defining it. `Inequality` defaults
    to this so that `snm_read >= 0` stays a constraint even when SymPy would
    otherwise resolve it to True under a positivity assumption.

    APPROXIMATION is an identity that only holds under a stated validity
    region. `Approximation` defaults to this.

    VARIANT marks one of several alternative model forms for the same
    left-hand variable. Variant relations carry an additional `variant`
    string (for example "dense" vs "moe", "adamw" vs "lion") so a resolver
    can select among them rather than treating them as conflicting
    identities.
    """
    IDENTITY = auto()
    CONSTRAINT = auto()
    APPROXIMATION = auto()
    VARIANT = auto()


# ---------------------------------------------------------------------------
# Base Equation (algebraic)
# ---------------------------------------------------------------------------

class Equation:
    """
    lhs = rhs, over Variable symbols.

    Subclasses override `as_sympy()` to return the right SymPy object kind.
    """

    kind: EquationKind = EquationKind.ALGEBRAIC
    default_role: RelationRole = RelationRole.IDENTITY

    def __init__(
        self,
        name: str,
        lhs: ExprLike,
        rhs: ExprLike,
        description: str,
        references: Optional[List[Union[str, Reference]]] = None,
        check_units: bool = False,
        role: Optional[RelationRole] = None,
        variant: Optional[str] = None,
    ):
        self.name = name
        self.lhs: sp.Expr = _to_expr(lhs)
        self.rhs: sp.Expr = _to_expr(rhs)
        self.description = description
        self.references: List[Reference] = self._normalize_refs(references)
        self.role: RelationRole = role if role is not None else self.default_role
        self.variant: Optional[str] = variant
        Registry.register_equation(self)
        self._wire()
        if check_units:
            self._check_units()

    @staticmethod
    def _normalize_refs(
        refs: Optional[List[Union[str, Reference]]]
    ) -> List[Reference]:
        if not refs:
            return []
        out = []
        for r in refs:
            if isinstance(r, Reference):
                out.append(r)
            else:
                out.append(Reference(citation=str(r)))
        return out

    def _wire(self) -> None:
        lhs_var = self.lhs_variable()
        if lhs_var is not None:
            lhs_var.defined_by(self)
        for v in self.variables_on_rhs():
            v.used_in(self)

    def _check_units(self) -> None:
        from .units import check_dimensional_consistency
        lhs_v = self.lhs_variable()
        # Can only check when both sides carry sp_units
        if lhs_v is not None and lhs_v.sp_units is not None:
            # Build RHS unit expression by substituting each Variable's sp_units
            rhs_units = self.rhs
            for sym in self.rhs.free_symbols:
                v = Registry.lookup_by_symbol(sym)
                if v is not None and v.sp_units is not None:
                    rhs_units = rhs_units.subs(sym, v.sp_units)
            check_dimensional_consistency(lhs_v.sp_units, rhs_units, self.name)

    # ----- introspection -----

    def lhs_variable(self) -> Optional[Variable]:
        if isinstance(self.lhs, sp.Symbol):
            return Registry.lookup_by_symbol(self.lhs)
        return None

    def variables_on_rhs(self) -> List[Variable]:
        out: List[Variable] = []
        for sym in self.rhs.free_symbols:
            v = Registry.lookup_by_symbol(sym)
            if v is not None:
                out.append(v)
        return out

    def free_symbols(self) -> Set[sp.Symbol]:
        return self.lhs.free_symbols | self.rhs.free_symbols

    # ----- manipulation -----

    def as_sympy(self):
        return sp.Eq(self.lhs, self.rhs)

    def latex(self) -> str:
        return sp.latex(self.as_sympy())

    def pretty(self) -> str:
        return sp.pretty(self.as_sympy(), use_unicode=True)

    def solve_for(self, var: Union[Variable, sp.Symbol]):
        sym = var.symbol if isinstance(var, Variable) else var
        return sp.solve(sp.Eq(self.lhs, self.rhs), sym)

    def substitute(
        self, assignments: Dict[Union[Variable, sp.Symbol], float]
    ):
        subs = {
            (k.symbol if isinstance(k, Variable) else k): v
            for k, v in assignments.items()
        }
        return sp.Eq(self.lhs.subs(subs), self.rhs.subs(subs))

    def evaluate_rhs(
        self, assignments: Dict[Union[Variable, sp.Symbol], float]
    ) -> sp.Expr:
        subs = {
            (k.symbol if isinstance(k, Variable) else k): v
            for k, v in assignments.items()
        }
        return self.rhs.subs(subs).simplify()

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name}: {self.as_sympy()}>"


# ---------------------------------------------------------------------------
# Inequality
# ---------------------------------------------------------------------------

class Inequality(Equation):
    """
    lhs <op> rhs where op is one of <, <=, >, >=.
    Used for constraints (setup time + prop delay < clock period).

    Inequalities are stored structurally, not eagerly evaluated. SymPy's
    default constructor resolves `positive_symbol >= 0` to True at
    construction time, which erases the constraint. `as_sympy()` uses
    `evaluate=False` to preserve the relational object. Use
    `is_trivially_true()` or `is_trivially_false()` when the evaluated
    form is actually what you want.
    """
    kind = EquationKind.INEQUALITY
    default_role = RelationRole.CONSTRAINT

    _OPS = {"<", "<=", ">", ">="}
    _REL_CLS = {
        "<":  sp.StrictLessThan,
        "<=": sp.LessThan,
        ">":  sp.StrictGreaterThan,
        ">=": sp.GreaterThan,
    }

    def __init__(self, name, lhs, rhs, op: str, description: str,
                 references=None, check_units: bool = False,
                 role: Optional[RelationRole] = None,
                 variant: Optional[str] = None):
        if op not in self._OPS:
            raise ValueError(f"op must be one of {self._OPS}; got {op!r}")
        self.op = op
        super().__init__(name, lhs, rhs, description, references, check_units,
                         role=role, variant=variant)

    def as_sympy(self):
        return self._REL_CLS[self.op](self.lhs, self.rhs, evaluate=False)

    def is_trivially_true(self) -> bool:
        """
        Evaluate the relation under current symbol assumptions. Returns True
        only when SymPy can prove the constraint is vacuous. A False return
        means the constraint is either strictly nontrivial or at least not
        provably vacuous.
        """
        return self._REL_CLS[self.op](self.lhs, self.rhs) is sp.S.true

    def is_trivially_false(self) -> bool:
        """
        Counterpart to `is_trivially_true()`: True when SymPy can prove the
        relation is never satisfiable under current assumptions.
        """
        return self._REL_CLS[self.op](self.lhs, self.rhs) is sp.S.false


# ---------------------------------------------------------------------------
# Approximation with validity condition
# ---------------------------------------------------------------------------

class Approximation(Equation):
    """
    lhs ~= rhs, valid when `validity` holds.
    validity is a SymPy expression over Variables (e.g. x << 1).
    """
    kind = EquationKind.APPROXIMATION
    default_role = RelationRole.APPROXIMATION

    def __init__(self, name, lhs, rhs, validity: sp.Expr,
                 description: str, references=None, check_units: bool = False,
                 role: Optional[RelationRole] = None,
                 variant: Optional[str] = None):
        self.validity = validity
        super().__init__(name, lhs, rhs, description, references, check_units,
                         role=role, variant=variant)

    def as_sympy(self):
        # No native "approximately equal" in sympy, use Relational with a marker
        return sp.Eq(self.lhs, self.rhs)  # visually identical; use .validity to see the regime

    def __repr__(self):
        return (f"<Approximation {self.name}: "
                f"{self.lhs} ≈ {self.rhs} when {self.validity}>")


# ---------------------------------------------------------------------------
# Piecewise equation
# ---------------------------------------------------------------------------

class PiecewiseEquation(Equation):
    """
    lhs == Piecewise((expr1, cond1), (expr2, cond2), ..., (default_expr, True))

    Example: MOSFET drain current has different formulas in cutoff, triode,
    saturation.
    """
    kind = EquationKind.PIECEWISE

    def __init__(self, name, lhs, pieces: List[Tuple[ExprLike, sp.Expr]],
                 description: str, references=None, check_units: bool = False):
        # Build the RHS as a sp.Piecewise
        self.pieces = [(_to_expr(e), c) for e, c in pieces]
        rhs = sp.Piecewise(*self.pieces)
        super().__init__(name, lhs, rhs, description, references, check_units)


# ---------------------------------------------------------------------------
# Differential equation
# ---------------------------------------------------------------------------

class DifferentialEquation(Equation):
    """
    d^order(lhs) / d(indep_var)^order == rhs

    Typical use: dN/dt = -λN (exponential decay), dV/dt = I/C (capacitor),
    d²x/dt² = F/m (Newton).
    """
    kind = EquationKind.DIFFERENTIAL

    def __init__(
        self,
        name, lhs, rhs,
        indep_var: Union[Variable, sp.Symbol],
        order: int = 1,
        boundary: Optional[Dict] = None,
        description: str = "",
        references=None,
        check_units: bool = False,
    ):
        self.indep_sym = (
            indep_var.symbol if isinstance(indep_var, Variable) else indep_var
        )
        self.order = order
        self.boundary = boundary or {}
        super().__init__(name, lhs, rhs, description, references, check_units)

    def as_sympy(self):
        lhs_expr = self.lhs
        # If lhs is a bare symbol, wrap as a Function of the independent variable
        # so we can take derivatives symbolically.
        if isinstance(lhs_expr, sp.Symbol):
            f = sp.Function(str(lhs_expr))
            deriv = sp.Derivative(f(self.indep_sym), (self.indep_sym, self.order))
        else:
            deriv = sp.Derivative(lhs_expr, (self.indep_sym, self.order))
        return sp.Eq(deriv, self.rhs)


# ---------------------------------------------------------------------------
# Iterative equation (fixed-point / Newton-Schulz style)
# ---------------------------------------------------------------------------

class IterativeEquation(Equation):
    """
    lhs is produced by iterating a map `f` starting from `initial`:

        x_0 = initial
        x_{k+1} = f(x_k)
        lhs ≡ x_N  where N = n_iter (or when convergence holds)

    Typical use: Newton-Schulz iteration for matrix orthogonalization in Muon.
    """
    kind = EquationKind.ITERATIVE

    def __init__(
        self,
        name, lhs, map_expr: ExprLike,
        iteration_variable: Union[Variable, sp.Symbol, str],
        initial: Optional[ExprLike] = None,
        n_iter: Optional[int] = None,
        convergence: Optional[sp.Expr] = None,
        description: str = "",
        references=None,
        check_units: bool = False,
    ):
        self.map_expr = _to_expr(map_expr)
        if isinstance(iteration_variable, Variable):
            self.iter_sym = iteration_variable.symbol
        elif isinstance(iteration_variable, sp.Symbol):
            self.iter_sym = iteration_variable
        else:
            self.iter_sym = sp.Symbol(str(iteration_variable))
        self.initial = _to_expr(initial) if initial is not None else None
        self.n_iter = n_iter
        self.convergence = convergence
        super().__init__(name, lhs, self.map_expr, description, references, check_units)

    def unfold(self, k: int) -> sp.Expr:
        """Unfold the iteration k times starting from `initial`."""
        if self.initial is None:
            raise ValueError("No initial value set for this IterativeEquation.")
        x = self.initial
        for _ in range(k):
            x = self.map_expr.subs(self.iter_sym, x)
        return x

    def as_sympy(self):
        # Conceptually: lhs = f^{n_iter}(initial). Represent the map form.
        return sp.Eq(self.lhs, sp.Function("iterate")(self.map_expr, self.iter_sym, self.n_iter or sp.oo))


# ---------------------------------------------------------------------------
# Stochastic relation (moment / distribution)
# ---------------------------------------------------------------------------

class StochasticRelation(Equation):
    """
    Captures relationships where lhs is a random variable.
    Carries:
      * distribution_name (e.g. "Bernoulli", "Normal", "Uniform")
      * parameters (dict of sympy expressions)
      * optional mean / variance expressions
    Used for stochastic rounding, noise, data augmentation, etc.
    """
    kind = EquationKind.STOCHASTIC

    def __init__(
        self,
        name, lhs,
        distribution: str,
        parameters: Dict[str, ExprLike],
        mean: Optional[ExprLike] = None,
        variance: Optional[ExprLike] = None,
        description: str = "",
        references=None,
    ):
        self.distribution = distribution
        self.parameters = {k: _to_expr(v) for k, v in parameters.items()}
        self.mean_expr = _to_expr(mean) if mean is not None else None
        self.variance_expr = _to_expr(variance) if variance is not None else None
        # Store a symbolic RHS that records the distribution
        rhs = sp.Function(distribution)(*self.parameters.values())
        super().__init__(name, lhs, rhs, description, references)


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
]
