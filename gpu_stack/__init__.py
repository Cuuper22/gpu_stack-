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

from importlib import import_module, reload
import sys

from . import constants, core, scopes
from .core import (
    AmbiguousVariant,
    ApproximationValidityCheck,
    Constant,
    ConstraintCheck,
    Equation,
    Inequality,
    InvalidVariantSelector,
    RelationRole,
    Registry,
    ResolverError,
    ResolverResult,
    System,
    TraceStep,
    Underdetermined,
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


def _load_scope_modules() -> list[str]:
    loaded = []
    for scope_name in SCOPE_MODULES:
        fullname = f"{__name__}.scopes.{scope_name}"
        if fullname in sys.modules:
            module = reload(sys.modules[fullname])
        else:
            module = import_module(f".scopes.{scope_name}", package=__name__)
        globals()[scope_name] = module
        loaded.append(scope_name)
    return loaded


def _purge_scope_submodules() -> None:
    prefix = f"{__name__}.scopes."
    for module_name in list(sys.modules):
        if module_name.startswith(prefix):
            del sys.modules[module_name]


LOADED_SCOPE_MODULES = _load_scope_modules()

# Phase 2 metadata: once every scope has registered, mark Variables that
# carry no value-defining relation as ROOT_INPUT. Constraint-only variables
# still need external values, so downstream code should not infer roots from
# the raw presence of defining_equations.
Registry.auto_classify_kinds()


def bootstrap() -> dict[str, int]:
    """
    Rebuild the global Registry from source modules.

    `Registry.reset()` deliberately clears all live graph state. Plain
    `importlib.reload(gpu_stack)` is not enough to rebuild it because Python
    keeps already-imported constants and scope modules cached. This helper is
    the supported notebook/test recovery path: reset, reload constants, reload
    every scope in the authoritative order, classify roots, and return stats.
    """
    global constants, scopes, SCOPE_DESCRIPTIONS, SCOPE_MODULES, LOADED_SCOPE_MODULES

    Registry.reset()
    constants = reload(constants)
    scopes = reload(scopes)
    SCOPE_MODULES = scopes.SCOPE_MODULES
    SCOPE_DESCRIPTIONS = scopes.SCOPE_DESCRIPTIONS
    _purge_scope_submodules()
    LOADED_SCOPE_MODULES = _load_scope_modules()
    Registry.auto_classify_kinds()
    return Registry.stats()


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
    "ApproximationValidityCheck",
    "ConstraintCheck",
    "ResolverResult",
    "TraceStep",
    "ResolverError",
    "Underdetermined",
    "AmbiguousVariant",
    "InvalidVariantSelector",
    "System",
    "var",
    "eq",
    "topological_sort",
    "find_cycles",
    "subgraph",
    "to_dot",
    "resolve",
    "bootstrap",
    "SCOPE_MODULES",
    "SCOPE_DESCRIPTIONS",
    "LOADED_SCOPE_MODULES",
    "loaded_scopes",
] + list(SCOPE_MODULES)
