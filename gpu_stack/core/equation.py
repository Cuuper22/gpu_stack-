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

from enum import Enum, auto
from typing import Dict, List, Mapping, Optional, Set, Tuple, Union
import sympy as sp

from .registry import Registry
from .variable import Variable, Reference
from .equation_metadata import normalize_references
from .equation_roles import (
    resolve_relation_role,
    validate_inequality_role,
    validate_relation_variant,
    validate_value_lhs,
)
from .equation_relations import (
    domain_relations_for_variable as _domain_relations_for_variable,
    domain_validity_for_exprs as _domain_validity_for_exprs,
    ge as _ge,
    gt as _gt,
    le as _le,
    lt as _lt,
    ne as _ne,
    valid_all as _valid_all,
)
from .symbolic import (
    ExprLike,
    raw_dependency_symbols_for_exprs,
    registered_free_variable_names,
    registered_variables_in_exprs,
    small_nonnegative_int,
    to_expr,
)


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
        self.lhs: sp.Expr = to_expr(lhs)
        self.rhs: sp.Expr = to_expr(rhs)
        self.description = description
        self.references: List[Reference] = self._normalize_refs(references)
        self.role: RelationRole = resolve_relation_role(role, self.default_role)
        validate_relation_variant(
            name,
            self.role,
            variant,
            RelationRole.VARIANT,
        )
        self.variant: Optional[str] = variant
        self._check_units_flag = bool(check_units)
        validate_value_lhs(
            name,
            self.role,
            self.lhs_variable(),
            RelationRole.CONSTRAINT,
        )
        if check_units:
            self._check_units()
        Registry.register_equation(self)
        try:
            self._wire()
        except Exception:
            if Registry.equations.get(self.name) is self:
                del Registry.equations[self.name]
            raise

    @staticmethod
    def _normalize_refs(
        refs: Optional[List[Union[str, Reference]]]
    ) -> List[Reference]:
        return normalize_references(refs)

    def _wire(self) -> None:
        lhs_var = self.lhs_variable()
        if lhs_var is not None:
            lhs_var.defined_by(self)
        elif self.role == RelationRole.CONSTRAINT:
            for v in self.variables_on_lhs():
                v.defined_by(self)
        for v in self.variables_on_rhs():
            v.used_in(self)

    def _check_units(self) -> None:
        from .units import check_dimensional_consistency, infer_expr_units
        lhs_v = self.lhs_variable()
        if lhs_v is not None and lhs_v.sp_units is None:
            return

        unit_lookup = self._unit_lookup_for_exprs([self.lhs, self.rhs])
        lhs_units = (
            lhs_v.sp_units
            if lhs_v is not None
            else infer_expr_units(self.lhs, unit_lookup, self.name)
        )
        rhs_units = infer_expr_units(self.rhs, unit_lookup, self.name)
        check_dimensional_consistency(lhs_units, rhs_units, self.name)

    # ----- introspection -----

    def _unit_lookup_for_exprs(self, exprs: List[object]) -> Dict[sp.Symbol, sp.Expr]:
        lookup: Dict[sp.Symbol, sp.Expr] = {}
        bound_symbols = self._bound_symbols()
        for expr in exprs:
            for sym in getattr(sp.sympify(expr), "free_symbols", set()) - bound_symbols:
                v = Registry.lookup_by_symbol(sym)
                if v is not None and v.sp_units is not None:
                    lookup[sym] = v.sp_units
        return lookup

    def lhs_variable(self) -> Optional[Variable]:
        if isinstance(self.lhs, sp.Symbol):
            return Registry.lookup_by_symbol(self.lhs)
        return None

    def variables_on_lhs(self) -> List[Variable]:
        return self._registered_variables_in_exprs([self.lhs])

    def variables_on_rhs(self) -> List[Variable]:
        return self._registered_variables_in_exprs(self._dependency_exprs())

    def variables_in_relation(self) -> List[Variable]:
        return self._registered_variables_in_exprs([self.lhs, *self._dependency_exprs()])

    def _registered_variables_in_exprs(self, exprs: List[object]) -> List[Variable]:
        return registered_variables_in_exprs(exprs, self._bound_symbols())

    def _dependency_exprs(self) -> List[object]:
        """Expressions that semantically contribute RHS dependencies."""
        return [self.rhs]

    def _value_dependency_exprs(self) -> List[object]:
        """Expressions that are needed to compute the equation value."""
        return [self.rhs]

    def _raw_symbol_exprs(self) -> List[object]:
        """Expression fields where an unregistered symbol is model-significant."""
        exprs: List[object] = list(self._dependency_exprs())
        if self.role == RelationRole.CONSTRAINT or self.lhs_variable() is None:
            exprs.append(self.lhs)
        return exprs

    def _bound_symbols(self) -> Set[sp.Symbol]:
        """Symbols that are local binders rather than model dependencies."""
        return set()

    def raw_dependency_symbols(self) -> Set[sp.Symbol]:
        """
        Symbols that appear in dependency-bearing fields but do not map to a
        registered Variable. Dummy symbols are intentionally ignored because
        they are local binders, not model inputs.
        """
        return raw_dependency_symbols_for_exprs(
            self._raw_symbol_exprs(),
            self._bound_symbols(),
        )

    def free_symbols(self) -> Set[sp.Symbol]:
        symbols = set(self.lhs.free_symbols)
        bound_symbols = self._bound_symbols()
        for expr in self._dependency_exprs():
            symbols |= set(getattr(expr, "free_symbols", set())) - bound_symbols
        return symbols

    # ----- manipulation -----

    def as_sympy(self):
        return sp.Eq(self.lhs, self.rhs, evaluate=False)

    def latex(self) -> str:
        return sp.latex(self.as_sympy())

    def pretty(self) -> str:
        return sp.pretty(self.as_sympy(), use_unicode=True)

    def solve_for(self, var: Union[Variable, sp.Symbol]):
        sym = var.symbol if isinstance(var, Variable) else var
        return sp.solve(sp.Eq(self.lhs, self.rhs, evaluate=False), sym)

    def substitute(
        self, assignments: Dict[Union[Variable, sp.Symbol], float]
    ):
        subs = {
            (k.symbol if isinstance(k, Variable) else k): v
            for k, v in assignments.items()
        }
        return sp.Eq(self.lhs.subs(subs), self.rhs.subs(subs), evaluate=False)

    def value_expr(
        self,
        subs: Optional[Mapping[sp.Symbol, sp.Expr]] = None,
    ) -> sp.Expr:
        """Expression used when this equation defines its left-hand value."""
        return self.rhs.subs(dict(subs or {}))

    def evaluate_rhs(
        self, assignments: Dict[Union[Variable, sp.Symbol], float]
    ) -> sp.Expr:
        subs = {
            (k.symbol if isinstance(k, Variable) else k): sp.sympify(v)
            for k, v in assignments.items()
        }
        return self.value_expr(subs).simplify()

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name}: {self.as_sympy()}>"


# ---------------------------------------------------------------------------
# Structural relations
# ---------------------------------------------------------------------------

def gt(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Strict greater-than relation that does not simplify under assumptions."""
    return _gt(lhs, rhs)


def ge(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Greater-than-or-equal relation that does not simplify under assumptions."""
    return _ge(lhs, rhs)


def lt(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Strict less-than relation that does not simplify under assumptions."""
    return _lt(lhs, rhs)


def le(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Less-than-or-equal relation that does not simplify under assumptions."""
    return _le(lhs, rhs)


def ne(lhs: ExprLike, rhs: ExprLike) -> sp.Expr:
    """Not-equal relation that does not simplify under assumptions."""
    return _ne(lhs, rhs)


def valid_all(*conditions: object) -> sp.Expr:
    """Conjunction that keeps approximation-validity predicates structural."""
    return _valid_all(*conditions)


def domain_relations_for_variable(var: Variable) -> List[Tuple[str, sp.Expr]]:
    """Structural relations implied by a variable's declared domain metadata."""
    return _domain_relations_for_variable(var)


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
        requested_role = resolve_relation_role(role, self.default_role)
        validate_inequality_role(name, requested_role, RelationRole.CONSTRAINT)
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
        self.validity = self._normalize_validity(name, rhs, validity)
        super().__init__(name, lhs, rhs, description, references, check_units,
                         role=role, variant=variant)

    def as_sympy(self):
        # No native "approximately equal" in sympy, use Relational with a marker
        return sp.Eq(self.lhs, self.rhs, evaluate=False)  # visually identical; use .validity to see the regime

    @staticmethod
    def _normalize_validity(name: str, rhs: ExprLike, validity: sp.Expr) -> sp.Expr:
        validity = sp.sympify(validity)
        if validity is sp.S.false:
            raise ValueError(f"{name}: Approximation validity collapsed to False.")
        if validity is sp.S.true:
            recovered = _domain_validity_for_exprs([to_expr(rhs)])
            return valid_all(*recovered)
        return validity

    def _dependency_exprs(self) -> List[object]:
        return [self.rhs, self.validity]

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
                 description: str, references=None, check_units: bool = False,
                 role: Optional[RelationRole] = None,
                 variant: Optional[str] = None):
        # Build the RHS as a sp.Piecewise
        self.pieces = [(to_expr(e), c) for e, c in pieces]
        rhs = sp.Piecewise(*self.pieces, evaluate=False)
        super().__init__(
            name, lhs, rhs, description, references, check_units,
            role=role, variant=variant,
        )

    def _dependency_exprs(self) -> List[object]:
        exprs: List[object] = [self.rhs]
        for expr, condition in self.pieces:
            exprs.append(expr)
            exprs.append(condition)
        return exprs


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
        role: Optional[RelationRole] = None,
        variant: Optional[str] = None,
    ):
        self.indep_sym = (
            indep_var.symbol if isinstance(indep_var, Variable) else indep_var
        )
        self.order = order
        self.boundary = boundary or {}
        super().__init__(
            name, lhs, rhs, description, references, check_units,
            role=role, variant=variant,
        )

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

    def _dependency_exprs(self) -> List[object]:
        return [self.rhs, self.indep_sym]


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
            name, lhs, self.map_expr, description, references, check_units,
            role=role, variant=variant,
        )

    def unfold(self, k: int) -> sp.Expr:
        """Unfold the iteration k times starting from `initial`."""
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
        """Represent or unfold the iterated value without leaking the local binder."""
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
        role: Optional[RelationRole] = None,
        variant: Optional[str] = None,
    ):
        self.distribution = distribution
        self.parameters = {k: to_expr(v) for k, v in parameters.items()}
        self.mean_expr = to_expr(mean) if mean is not None else None
        self.variance_expr = to_expr(variance) if variance is not None else None
        # Store a symbolic RHS that records the distribution
        rhs = sp.Function(distribution)(*self.parameters.values())
        super().__init__(
            name, lhs, rhs, description, references,
            role=role, variant=variant,
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
