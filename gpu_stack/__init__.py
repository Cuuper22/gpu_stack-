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
    Inequality,
    RelationRole,
    Registry,
    ResolverResult,
    System,
    Variable,
    eq,
    find_cycles,
    resolve,
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

# Phase 2 metadata: once every scope has registered, mark Variables that
# carry no defining equation as ROOT_INPUT so downstream code can query by
# VariableKind without depending on the runtime presence of defining_equations.
Registry.auto_classify_kinds()


__all__ = [
    "core",
    "constants",
    "scopes",
    "Registry",
    "Variable",
    "Constant",
    "Equation",
    "Inequality",
    "RelationRole",
    "ResolverResult",
    "System",
    "var",
    "eq",
    "topological_sort",
    "find_cycles",
    "subgraph",
    "to_dot",
    "resolve",
    "SCOPE_MODULES",
    "SCOPE_DESCRIPTIONS",
    "LOADED_SCOPE_MODULES",
    "loaded_scopes",
] + list(SCOPE_MODULES)
