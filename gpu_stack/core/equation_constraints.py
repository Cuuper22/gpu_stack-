"""
Inequality: a relation that bounds a variable without defining it.

An identity says what a variable *is*; an inequality says where it must
*stay*. The resolver never computes a value from an inequality — it only
checks the finished scenario against it and reports violations.
"""

from __future__ import annotations

from typing import Optional

import sympy as sp

from .equation_base import Equation
from .equation_roles import resolve_relation_role, validate_inequality_role
from .equation_types import EquationKind, RelationRole


class Inequality(Equation):
    """
    ``lhs <op> rhs`` where op is one of <, <=, >, >=.

    Inequalities are stored structurally, never eagerly evaluated. This
    matters: SymPy's default constructor resolves ``positive_symbol >= 0``
    to plain True at construction time, which would erase the constraint
    before anyone could check it. ``as_sympy()`` therefore always builds
    the relational object with ``evaluate=False``.
    """

    kind = EquationKind.INEQUALITY
    default_role = RelationRole.CONSTRAINT

    _OPS = {"<", "<=", ">", ">="}
    _REL_CLS = {
        "<": sp.StrictLessThan,
        "<=": sp.LessThan,
        ">": sp.StrictGreaterThan,
        ">=": sp.GreaterThan,
    }

    def __init__(
        self,
        name,
        lhs,
        rhs,
        op: str,
        description: str,
        references=None,
        check_units: bool = False,
        role: Optional[RelationRole] = None,
        variant: Optional[str] = None,
    ):
        if op not in self._OPS:
            raise ValueError(f"op must be one of {self._OPS}; got {op!r}")
        requested_role = resolve_relation_role(role, self.default_role)
        validate_inequality_role(name, requested_role, RelationRole.CONSTRAINT)
        self.op = op
        super().__init__(
            name,
            lhs,
            rhs,
            description,
            references,
            check_units,
            role=role,
            variant=variant,
        )

    def as_sympy(self):
        return self._REL_CLS[self.op](self.lhs, self.rhs, evaluate=False)

    def is_trivially_true(self) -> bool:
        """
        True when SymPy can prove the constraint from symbol assumptions
        alone — meaning it is vacuous and adds no information. False means
        the constraint is nontrivial, or at least not provably vacuous.
        """
        return self._REL_CLS[self.op](self.lhs, self.rhs) is sp.S.true

    def is_trivially_false(self) -> bool:
        """True when SymPy can prove the relation is never satisfiable."""
        return self._REL_CLS[self.op](self.lhs, self.rhs) is sp.S.false


__all__ = ["Inequality"]
