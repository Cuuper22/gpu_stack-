"""
The two enums every relation carries.

EquationKind says what mathematical shape a relation has (algebraic,
inequality, differential, ...). RelationRole says what the relation is
*for* — whether it defines a value, bounds one, approximates one, or is
one of several alternatives. The resolver selects equations by role, not
by kind.
"""

from __future__ import annotations

from enum import Enum, auto


class EquationKind(Enum):
    ALGEBRAIC = auto()
    INEQUALITY = auto()
    APPROXIMATION = auto()
    PIECEWISE = auto()
    DIFFERENTIAL = auto()
    ITERATIVE = auto()
    STOCHASTIC = auto()
    DEFINITIONAL = auto()


class RelationRole(Enum):
    """
    Semantic role of a relation that touches a Variable's back-references.

    IDENTITY is a definitional equality. The algebraic Equation base class
    defaults to this. Most scope equations are identities.

    CONSTRAINT bounds a Variable without defining it. Inequality defaults to
    this so that ``snm_read >= 0`` stays a constraint even when SymPy would
    otherwise resolve it to True under a positivity assumption.

    APPROXIMATION is an identity that only holds under a stated validity
    region. Approximation defaults to this.

    VARIANT marks one of several alternative model forms for the same
    left-hand variable. Variant relations carry an additional ``variant``
    string, for example "dense" vs "moe" or "adamw" vs "lion".
    """

    IDENTITY = auto()
    CONSTRAINT = auto()
    APPROXIMATION = auto()
    VARIANT = auto()


__all__ = ["EquationKind", "RelationRole"]
