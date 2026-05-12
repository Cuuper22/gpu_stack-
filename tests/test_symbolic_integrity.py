"""
tests/test_symbolic_integrity.py
================================

Regression coverage for the symbolic-assumption layer.

The graph should not silently assume every engineering quantity is positive
and non-integer. That old default made SymPy erase useful relations before
the model could inspect them.
"""

import sympy as sp

from gpu_stack import Registry, Variable
from gpu_stack.core import (
    Approximation,
    IterativeEquation,
    domain_relations_for_variable,
    ne,
)


def test_default_variables_are_not_positive_or_noninteger():
    v = Registry.variables["arch.act.x"]
    assert v.symbol.is_real is True
    assert v.symbol.is_positive is None
    assert v.symbol.is_integer is None


def test_legacy_positive_false_means_signed_not_nonpositive():
    v = Registry.variables["precision.rounding.rn_mean_error"]
    assert v.signed is True
    assert v.symbol.is_nonpositive is None
    assert v.symbol.is_positive is None


def test_binary_domain_sets_integrality_and_range():
    v = Registry.variables["precision.subnormals.enabled"]
    assert v.binary is True
    assert v.symbol.is_integer is True
    assert v.symbol.is_nonnegative is True
    assert v.value_range == (0.0, 1.0)
    assert v.in_range(0)
    assert v.in_range(1)
    assert not v.in_range(2)


def test_integer_domain_relations_survive_integer_symbol_assumptions():
    v = Registry.variables["opt.schedule.warmup_steps"]
    relation = next(
        relation
        for suffix, relation in domain_relations_for_variable(v)
        if suffix == "integer"
    )

    assert relation not in (sp.S.true, sp.S.false)
    assert relation.subs({v.symbol: sp.Rational(5, 2)}) is sp.S.false


def test_noninteger_domain_relations_survive_noninteger_symbol_assumptions():
    v = Variable(
        "test.domain.noninteger",
        "test_domain_noninteger",
        "dimensionless",
        "Temporary noninteger domain regression variable.",
        noninteger=True,
    )
    try:
        relation = next(
            relation
            for suffix, relation in domain_relations_for_variable(v)
            if suffix == "noninteger"
        )

        assert relation not in (sp.S.true, sp.S.false)
        assert relation.subs({v.symbol: sp.Rational(5, 2)}) is sp.S.true
        assert relation.subs({v.symbol: sp.Integer(2)}) is sp.S.false
    finally:
        Registry.variables.pop(v.name, None)


def test_no_equation_renders_as_bare_boolean():
    collapsed = [
        (e.name, e.as_sympy())
        for e in Registry.equations.values()
        if e.as_sympy() in (sp.S.true, sp.S.false)
    ]
    assert collapsed == []


def test_no_approximation_validity_renders_as_bare_boolean():
    collapsed = [
        e.name
        for e in Registry.equations.values()
        if isinstance(e, Approximation)
        and e.validity in (sp.S.true, sp.S.false, True, False)
    ]
    assert collapsed == []


def test_structural_not_equal_helper_survives_matching_assumptions():
    x = sp.Symbol("x", positive=True)
    condition = ne(x, x)

    assert condition == sp.Ne(x, x, evaluate=False)
    assert condition not in (sp.S.true, sp.S.false, True, False)


def test_piecewise_conditions_remain_symbolic_when_they_matter():
    eq = Registry.equations["precision.eq.min_nonzero"]
    condition = eq.pieces[0][1]
    assert condition not in (sp.S.true, sp.S.false, True, False)
    assert Registry.variables["precision.subnormals.enabled"].symbol in condition.free_symbols


def test_approximation_validity_contributes_dependencies():
    deps = {
        v.name
        for v in Registry.variables["physical.drift_velocity"].direct_dependencies()
    }
    assert "physical.critical_field" in deps


def test_iterative_equation_contributes_initial_convergence_and_iteration_dependencies():
    eq = Registry.equations["opt.eq.muon_ns_iteration"]
    assert isinstance(eq, IterativeEquation)
    deps = {v.name for v in Registry.variables["opt.muon.X"].direct_dependencies()}
    assert {
        "opt.muon.ns_coeff_a",
        "opt.muon.ns_coeff_b",
        "opt.muon.ns_coeff_c",
        "opt.muon.ns_input",
        "opt.muon.ns_iterations",
        "opt.muon.ns_tol",
    } <= deps


def test_no_dependency_bearing_raw_symbols_remain():
    raw = {
        e.name: sorted(str(s) for s in e.raw_dependency_symbols())
        for e in Registry.equations.values()
        if e.raw_dependency_symbols()
    }
    assert raw == {}


def test_no_equation_lhs_raw_symbols_remain():
    raw = {
        e.name: sorted(
            str(s)
            for s in e.lhs.free_symbols
            if not isinstance(s, sp.Dummy)
            and Registry.lookup_by_symbol(s) is None
        )
        for e in Registry.equations.values()
    }
    raw = {name: symbols for name, symbols in raw.items() if symbols}
    assert raw == {}
