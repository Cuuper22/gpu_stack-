"""Smoke tests for the package's public import surface.

These check the basics a user hits first: ``import gpu_stack`` works, the
resolver API names are exported in ``__all__``, the preset package exposes
its key modules, and every scope module actually loaded. They are kept
separate from the heavier registry-snapshot and export-propagation tests
so a plain import break is reported on its own.
"""

import gpu_stack
from gpu_stack import Registry


def test_import_succeeds():
    assert gpu_stack.Registry is Registry


def test_top_level_resolver_surface_is_exported():
    expected = {
        "resolve",
        "ResolverResult",
        "TraceStep",
        "ConstraintCheck",
        "ApproximationValidityCheck",
        "ResolverError",
        "Underdetermined",
        "AmbiguousVariant",
        "InvalidVariantSelector",
    }
    assert expected <= set(gpu_stack.__all__)
    for name in expected:
        assert hasattr(gpu_stack, name)


def test_preset_package_exports_key_public_modules():
    import gpu_stack.presets as preset_package

    expected = {"materials", "lithography", "nuclear", "scenarios"}
    assert expected <= set(preset_package.__all__)

    for name in expected:
        module = getattr(preset_package, name)
        assert module.__name__ == f"gpu_stack.presets.{name}"


def test_scope_modules_all_loaded():
    for name in gpu_stack.SCOPE_MODULES:
        assert name in gpu_stack.LOADED_SCOPE_MODULES
        assert getattr(gpu_stack, name) is not None
