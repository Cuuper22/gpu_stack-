"""
gpu_stack
=========

A SymPy-backed dependency graph for the GPU training stack, from physical
transport and transistors up through kernels, collectives, clusters, thermal
plants, and economics.

Importing `gpu_stack` populates the global Registry by loading every scope in
one authoritative dependency order from `gpu_stack.scopes.SCOPE_MODULES`.
That keeps the integration path in one place instead of hard-coding a second,
stale import list here.
"""

from importlib import import_module

from . import constants, core, scopes
from .core import (
    Constant,
    Equation,
    Registry,
    System,
    Variable,
    eq,
    find_cycles,
    subgraph,
    to_dot,
    topological_sort,
    var,
)
from .scopes import SCOPE_DESCRIPTIONS, SCOPE_MODULES, loaded_scopes


LOADED_SCOPE_MODULES = []
for _scope_name in SCOPE_MODULES:
    _module = import_module(f".scopes.{_scope_name}", package=__name__)
    globals()[_scope_name] = _module
    LOADED_SCOPE_MODULES.append(_scope_name)

del _scope_name, _module


__all__ = [
    "core",
    "constants",
    "scopes",
    "Registry",
    "Variable",
    "Constant",
    "Equation",
    "System",
    "var",
    "eq",
    "topological_sort",
    "find_cycles",
    "subgraph",
    "to_dot",
    "SCOPE_MODULES",
    "SCOPE_DESCRIPTIONS",
    "LOADED_SCOPE_MODULES",
    "loaded_scopes",
] + list(SCOPE_MODULES)
