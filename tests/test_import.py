"""
tests/test_import.py
====================

Smoke tests that the package imports cleanly and that the Registry reports
the expected counts. If a scope change legitimately moves these numbers,
update the expectations here rather than deleting the assertions.
"""

import gpu_stack
from gpu_stack import Registry


def test_import_succeeds():
    assert gpu_stack.Registry is Registry


def test_registry_stats_match_snapshot():
    stats = Registry.stats()
    assert stats["systems"] == 16
    assert stats["variables"] == 1147
    assert stats["constants"] == 23
    assert stats["equations"] == 620


def test_scope_modules_all_loaded():
    for name in gpu_stack.SCOPE_MODULES:
        assert name in gpu_stack.LOADED_SCOPE_MODULES
        assert getattr(gpu_stack, name) is not None
