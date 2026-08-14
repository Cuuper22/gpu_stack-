"""
Factory helpers that stamp scope and citation onto cluster declarations.

Every variable and equation in the cluster and facility scopes should carry
two labels: which scope it belongs to and which Reference backs it. Writing
those by hand on hundreds of declarations invites drift, so this module
provides factories — scoped_var, referenced_eq, referenced_piecewise — that
bake the labels in once and return ordinary declaration functions. Importing
this module creates nothing in the registry; only the leaf scope modules
that call the factories produce registry entries, which keeps import side
effects where they belong.
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
