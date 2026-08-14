"""Tests for which inputs the resolver treats as value dependencies.

A value dependency is a variable the resolver must obtain before it can
compute an equation's number. Not every symbol in a relation qualifies: an
approximation's validity predicate only gates trust in the result, so its
inputs are excluded, while iterative fields, piecewise conditions, and
stochastic distribution parameters all shape the computed value and must be
included. These tests pin that boundary down, because a wrong dependency set
either blocks resolution on inputs that do not matter or computes values from
incomplete data.
"""

from gpu_stack import Registry
from gpu_stack.core import IterativeEquation
from gpu_stack.core.resolver import _value_dependencies
from gpu_stack.core.variable import Variable
from tests.helpers.registry import registry_snapshot


def _resolver_dep_names(equation_name):
    return {
        v.name
        for v in _value_dependencies(Registry.equations[equation_name])
    }


def test_value_dependencies_exclude_only_approximation_validity():
    deps = _resolver_dep_names("physical.eq.drift_velocity_low_field")

    assert {"physical.carrier_mobility", "physical.electric_field"} <= deps
    assert "physical.critical_field" not in deps


def test_value_dependencies_include_iterative_fields():
    deps = _resolver_dep_names("opt.eq.muon_ns_iteration")

    assert {
        "opt.muon.ns_coeff_a",
        "opt.muon.ns_coeff_b",
        "opt.muon.ns_coeff_c",
        "opt.muon.ns_input",
        "opt.muon.ns_iterations",
        "opt.muon.ns_tol",
    } <= deps


def test_value_dependencies_ignore_registered_iterative_binder(registry_snapshot):
    x = Variable(
        "test.iterative.x",
        "x_registered_iter_test",
        "value",
        "Temporary registered binder variable.",
        scope="test",
    )
    n_iter = Variable(
        "test.iterative.n",
        "n_registered_iter_test",
        "count",
        "Temporary iteration count.",
        scope="test",
        integer=True,
        nonnegative=True,
    )
    eq = IterativeEquation(
        "test.eq.iterative_registered_binder",
        x.symbol,
        2 * x.symbol,
        iteration_variable=x,
        initial=1,
        n_iter=n_iter.symbol,
        convergence=x.symbol < 10,
        description="Temporary iterative equation with a registered local binder.",
    )

    assert {v.name for v in _value_dependencies(eq)} == {"test.iterative.n"}
    assert x.symbol not in eq.as_sympy().rhs.free_symbols


def test_value_dependencies_include_piecewise_conditions():
    deps = _resolver_dep_names("gpu.eq.power_throttle_factor")

    assert {"gpu.power.total", "gpu.tdp"} <= deps


def test_value_dependencies_include_stochastic_distribution_parameters():
    deps = _resolver_dep_names("precision.eq.sr_distribution")

    assert {
        "precision.quant.x_lo",
        "precision.quant.x_hi",
        "precision.sr.p_up",
    } <= deps
    assert "precision.quant.x_in" not in deps
    assert "precision.sr.error_variance" not in deps


def test_stochastic_moments_remain_graph_dependencies():
    deps = {
        v.name
        for v in Registry.variables["precision.sr.x_quantized"].direct_dependencies()
    }

    assert {
        "precision.quant.x_in",
        "precision.sr.error_variance",
    } <= deps
