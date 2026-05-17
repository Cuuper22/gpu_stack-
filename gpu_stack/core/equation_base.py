"""Base algebraic Equation implementation."""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Set, Union

import sympy as sp

from .equation_metadata import normalize_references
from .equation_roles import (
    resolve_relation_role,
    validate_relation_variant,
    validate_value_lhs,
)
from .equation_types import EquationKind, RelationRole
from .registry import Registry
from .symbolic import (
    ExprLike,
    raw_dependency_symbols_for_exprs,
    registered_variables_in_exprs,
    to_expr,
)
from .variable import Reference, Variable


class Equation:
    """
    lhs = rhs, over Variable symbols.

    Subclasses override ``as_sympy()`` to return the right SymPy object kind.
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
        Symbols in dependency-bearing fields that do not map to a registered
        Variable. Dummy symbols are ignored because they are local binders.
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


__all__ = ["Equation"]
