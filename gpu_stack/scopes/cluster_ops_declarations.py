"""
Shared declaration helpers for cluster operations and facility scopes.

These helpers keep scope files focused on model content. They do not create
variables or equations on import, so registry side effects stay in the leaf
scope modules that call them.
"""

import sympy as sp

from ..core import PiecewiseEquation, Reference, eq, var


DIMENSIONLESS = sp.Integer(1)


def _references(reference: Reference):
    return [reference]


def scoped_var(scope: str, reference: Reference):
    def declare(name: str, symbol: str, units: str, description: str, **kwargs):
        kwargs.setdefault("references", _references(reference))
        return var(
            name,
            symbol,
            units,
            description,
            scope=scope,
            **kwargs,
        )

    return declare


def referenced_eq(reference: Reference):
    def declare(name, lhs, rhs, description, **kwargs):
        kwargs.setdefault("references", _references(reference))
        return eq(name, lhs, rhs, description, **kwargs)

    return declare


def referenced_piecewise(reference: Reference):
    def declare(name, lhs, pieces, description, **kwargs):
        kwargs.setdefault("references", _references(reference))
        return PiecewiseEquation(name, lhs, pieces, description, **kwargs)

    return declare
