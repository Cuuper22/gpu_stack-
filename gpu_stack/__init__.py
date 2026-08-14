"""
gpu_stack
=========

A dependency graph of the GPU training stack, built on SymPy symbols and
equations. It connects physical transport and transistors up through kernels,
collectives, clusters, thermal plants, and economics, so a quantity at any
layer can be traced back through the layers that determine it.

Importing `gpu_stack` populates the global Registry: every scope module is
loaded in the one authoritative dependency order defined by
`gpu_stack.scopes.SCOPE_MODULES`. Keeping that order in a single place means
there is no second, hard-coded import list here to drift out of date.
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
            attr_name = module_name[len(prefix):].split(".", 1)[0]
            if hasattr(scopes, attr_name):
                delattr(scopes, attr_name)
            del sys.modules[module_name]


LOADED_SCOPE_MODULES = _load_scope_modules()

# Once every scope has registered, mark Variables that carry no value-defining
# relation as ROOT_INPUT. This flag is the authoritative test for rootness:
# constraint-only variables still need external values, so downstream code
# must not infer roots from the raw presence of defining_equations.
Registry.auto_classify_kinds()


def bootstrap() -> dict[str, int]:
    """
    Rebuild the global Registry from source modules and return its stats.

    Why this exists: `Registry.reset()` clears all live graph state, and a
    plain `importlib.reload(gpu_stack)` cannot rebuild it because Python keeps
    already-imported constants and scope modules cached. This helper is the
    supported notebook/test recovery path: reset, reload constants, reload
    every scope in the authoritative order, then classify root inputs.
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
