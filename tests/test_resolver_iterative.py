"""Tests for how the resolver handles iterative equations.

An IterativeEquation applies an update rule repeatedly (like the
Newton-Schulz iteration in the Muon optimizer). Its iteration variable is a
local binder — a name that exists only inside the loop, like the index in a
sum. These tests verify the binder never leaks: assigning the same-named
registry variable cannot hijack the loop, the binder never appears as a
dependency, small numeric cases unfold to exact values, and symbolic cases
stay wrapped in a bound ``iterate`` call with no dangling dummy symbols.
"""

import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.core import IterativeEquation, var
from gpu_stack.core.resolver import _value_dependencies
from tests.helpers.registry import registry_snapshot


def test_registered_iteration_variable_assignment_does_not_replace_binder(registry_snapshot):
    out = var(
        "test.iter.local.out",
        "test_iter_local_out",
        "value",
        "Temporary iterative output.",
        scope="test",
    )
    x = var(
        "test.iter.local.x",
        "test_iter_local_x",
        "value",
        "Temporary registered iteration variable.",
        scope="test",
    )
    x0 = var(
        "test.iter.local.x0",
        "test_iter_local_x0",
        "value",
        "Temporary initial condition.",
        scope="test",
    )
    n_iter = var(
        "test.iter.local.n",
        "test_iter_local_n",
        "iterations",
        "Temporary iteration count.",
        scope="test",
        integer=True,
        nonnegative=True,
    )
    scale = var(
        "test.iter.local.scale",
        "test_iter_local_scale",
        "dimensionless",
        "Temporary iterative scale.",
        scope="test",
    )
    eq = IterativeEquation(
        "test.eq.iter.local",
        out.symbol,
        scale.symbol * x.symbol,
        iteration_variable=x,
        initial=x0.symbol,
        n_iter=n_iter.symbol,
        description="Registered iteration variable is a local binder.",
    )

    assert x.symbol not in eq.free_symbols()
    assert x.name not in {v.name for v in out.direct_dependencies()}
    assert x.name not in {v.name for v in _value_dependencies(eq)}

    result = resolve(
        out.name,
        assignments={
            x0.name: 2,
            n_iter.name: 3,
            scale.name: 2,
            x.name: 999,
        },
    )

    assert result.value == 16
    assert result.missing == set()


def test_resolve_iterative_equation_does_not_leak_local_binder():
    result = resolve("opt.muon.X")
    eq = Registry.equations["opt.eq.muon_ns_iteration"]

    assert str(result.value.func) == "iterate"
    assert all(not isinstance(sym, sp.Dummy) for sym in result.value.free_symbols)
    assert result.value.has(sp.Lambda)
    assert eq.iter_sym not in eq.as_sympy().rhs.free_symbols
    assert result.missing == {
        "opt.muon.ns_coeff_a",
        "opt.muon.ns_coeff_b",
        "opt.muon.ns_coeff_c",
        "opt.muon.ns_input",
    }


def test_resolve_iterative_equation_unfolds_small_numeric_scenario():
    result = resolve(
        "opt.muon.X",
        assignments={
            "opt.muon.ns_coeff_a": 2,
            "opt.muon.ns_coeff_b": 0,
            "opt.muon.ns_coeff_c": 0,
            "opt.muon.ns_input": 3,
            "opt.muon.ns_iterations": 3.0,
            "opt.muon.ns_tol": 1e-6,
        },
    )

    assert result.value == 24
    assert result.missing == set()


def test_resolve_iterative_equation_uses_resolved_default_iteration_count():
    result = resolve(
        "opt.muon.X",
        assignments={
            "opt.muon.ns_coeff_a": 2,
            "opt.muon.ns_coeff_b": 0,
            "opt.muon.ns_coeff_c": 0,
            "opt.muon.ns_input": 1,
            "opt.muon.ns_tol": 1e-6,
        },
    )

    assert result.value == 32
    assert "opt.eq.muon_ns_iterations_default" in [
        step.equation for step in result.trace
    ]


def test_resolve_iterative_equation_symbolic_iteration_count_is_bound_iterate():
    n_iter = sp.Symbol("N", integer=True, nonnegative=True)
    x = sp.Symbol("x")

    result = resolve(
        "opt.muon.X",
        assignments={
            "opt.muon.ns_coeff_a": 2,
            "opt.muon.ns_coeff_b": 0,
            "opt.muon.ns_coeff_c": 0,
            "opt.muon.ns_input": x,
            "opt.muon.ns_iterations": n_iter,
            "opt.muon.ns_tol": 1e-6,
        },
    )

    eq = Registry.equations["opt.eq.muon_ns_iteration"]
    assert result.value.func == sp.Function("iterate")
    assert result.value.has(sp.Lambda)
    assert eq.iter_sym not in result.value.free_symbols
    assert {n_iter, x} <= result.value.free_symbols
