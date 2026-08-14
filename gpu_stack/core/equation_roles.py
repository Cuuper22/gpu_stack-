"""
Guard rails for relation roles at construction time.

Every relation carries a RelationRole (identity, constraint, approximation,
variant). Some combinations are nonsense — a VARIANT with no variant key, an
Inequality claiming to define a value. These helpers reject the nonsense
combinations while the equation is being built, when the error message can
still point at the offending name.
"""

from __future__ import annotations

from typing import Any, Optional


def resolve_relation_role(role: Optional[Any], default_role: Any) -> Any:
    """Choose the explicit role when present, otherwise the class default."""
    return role if role is not None else default_role


def validate_relation_variant(
    name: str,
    role: Any,
    variant: Optional[str],
    variant_role: Any,
) -> None:
    """A VARIANT relation must carry a variant key, and only VARIANT relations may."""
    if role is variant_role and variant is None:
        raise ValueError(f"{name}: VARIANT relations require a variant key.")
    if role is not variant_role and variant is not None:
        raise ValueError(
            f"{name}: variant keys are only allowed on VARIANT relations."
        )


def validate_value_lhs(
    name: str,
    role: Any,
    lhs_variable: object,
    constraint_role: Any,
) -> None:
    """Value-defining relations must target a registered bare variable."""
    if role is not constraint_role and lhs_variable is None:
        raise ValueError(
            f"{name}: value-defining relations require a registered "
            "bare-variable LHS."
        )


def validate_inequality_role(
    name: str,
    requested_role: Any,
    constraint_role: Any,
) -> None:
    """Inequalities are constraints, not value-defining identities."""
    if requested_role is not constraint_role:
        raise ValueError(f"{name}: Inequality relations must use CONSTRAINT role.")


__all__ = [
    "resolve_relation_role",
    "validate_relation_variant",
    "validate_value_lhs",
    "validate_inequality_role",
]
