"""Registry state isolation helpers for tests that mutate global registries."""

from __future__ import annotations

from contextlib import contextmanager

import pytest

from gpu_stack import Registry


@contextmanager
def snapshot_registry_state():
    variables = dict(Registry.variables)
    equations = dict(Registry.equations)
    systems = dict(Registry.systems)
    symbol_cache = dict(Registry._symbol_cache)
    backrefs = {
        name: (list(v._defined_by), list(v._used_in))
        for name, v in variables.items()
    }

    try:
        yield
    finally:
        for name, (defined_by, used_in) in backrefs.items():
            v = variables[name]
            v._defined_by[:] = defined_by
            v._used_in[:] = used_in
        Registry.variables = variables
        Registry.equations = equations
        Registry.systems = systems
        Registry._symbol_cache = symbol_cache


@pytest.fixture
def registry_snapshot():
    with snapshot_registry_state():
        yield
