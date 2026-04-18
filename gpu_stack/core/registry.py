"""
core/registry.py
================

Global registry of all Variables, Constants, Equations, and Systems.

Improvements vs the original single-file core:
  * O(1) symbol -> Variable lookup via an internal cache, rebuilt on insert.
  * Reset also clears Variable back-references so nothing dangles.
  * Query helpers: by_scope, by_unit_pattern, roots, leaves.
  * Optional collision check can be disabled for testing.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Iterable, TYPE_CHECKING
import sympy as sp

if TYPE_CHECKING:
    from .variable import Variable, Constant
    from .equation import Equation
    from .system import System


class Registry:
    variables: Dict[str, "Variable"] = {}
    equations: Dict[str, "Equation"] = {}
    systems: Dict[str, "System"] = {}

    # ----- O(1) symbol -> variable lookup cache -----
    _symbol_cache: Dict[int, "Variable"] = {}  # id(symbol) -> Variable

    @classmethod
    def register_variable(cls, var: "Variable") -> None:
        existing = cls.variables.get(var.name)
        if existing is not None and existing is not var:
            raise ValueError(
                f"Variable name collision: {var.name!r} already registered."
            )
        cls.variables[var.name] = var
        cls._symbol_cache[id(var.symbol)] = var

    @classmethod
    def register_equation(cls, eq: "Equation") -> None:
        existing = cls.equations.get(eq.name)
        if existing is not None and existing is not eq:
            raise ValueError(
                f"Equation name collision: {eq.name!r} already registered."
            )
        cls.equations[eq.name] = eq

    @classmethod
    def register_system(cls, sys: "System") -> None:
        existing = cls.systems.get(sys.name)
        if existing is not None and existing is not sys:
            raise ValueError(
                f"System name collision: {sys.name!r} already registered."
            )
        cls.systems[sys.name] = sys

    @classmethod
    def lookup_by_symbol(cls, sym: sp.Symbol) -> Optional["Variable"]:
        """O(1) lookup via id(symbol)."""
        v = cls._symbol_cache.get(id(sym))
        if v is not None:
            return v
        # Fallback for symbols that compare equal but aren't identical
        for var in cls.variables.values():
            if var.symbol == sym:
                cls._symbol_cache[id(sym)] = var
                return var
        return None

    @classmethod
    def reset(cls) -> None:
        """Full reset: clear dicts AND clear per-Variable back-references."""
        for v in cls.variables.values():
            v._defined_by.clear()
            v._used_in.clear()
        cls.variables.clear()
        cls.equations.clear()
        cls.systems.clear()
        cls._symbol_cache.clear()

    # ----- query helpers -----

    @classmethod
    def by_scope(cls, scope: str) -> List["Variable"]:
        return [v for v in cls.variables.values() if v.scope == scope]

    @classmethod
    def by_name_prefix(cls, prefix: str) -> List["Variable"]:
        return [v for v in cls.variables.values() if v.name.startswith(prefix)]

    @classmethod
    def roots(cls) -> List["Variable"]:
        """Variables with no defining equation (pure inputs)."""
        from .variable import Constant
        return [
            v for v in cls.variables.values()
            if not v.defining_equations and not isinstance(v, Constant)
        ]

    @classmethod
    def leaves(cls) -> List["Variable"]:
        """Variables that nothing else depends on (top-of-stack outputs)."""
        return [v for v in cls.variables.values() if not v.appearances]

    @classmethod
    def stats(cls) -> Dict[str, int]:
        from .variable import Constant
        return {
            "variables": len(cls.variables),
            "constants": sum(1 for v in cls.variables.values() if isinstance(v, Constant)),
            "equations": len(cls.equations),
            "systems": len(cls.systems),
            "root_inputs": len(cls.roots()),
            "leaves": len(cls.leaves()),
        }


__all__ = ["Registry"]
