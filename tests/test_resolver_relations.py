"""Tests for the special relation subclasses the resolver must support.

Beyond plain equations, the registry holds piecewise equations (conditional
branches), stochastic relations (distribution-valued results), differential
equations, and iterative equations. These tests verify the resolver evaluates
piecewise conditions with real inputs, returns stochastic results as symbolic
distribution calls rather than fake numbers, and that every subclass accepts
the same role/variant machinery as a plain Equation, so any of them can serve
as a selectable variant.
"""

import sympy as sp

from gpu_stack import resolve
from gpu_stack.core import (
    DifferentialEquation,
    IterativeEquation,
    PiecewiseEquation,
    RelationRole,
    StochasticRelation,
)
from gpu_stack.core.variable import Variable
from tests.helpers.registry import registry_snapshot


def test_resolve_piecewise_equation_still_evaluates_conditions():
    result = resolve(
        "gpu.power.throttle_factor",
        assignments={
            "gpu.power.total": 200,
            "gpu.tdp": 100,
        },
    )

    assert result.value == sp.Rational(1, 2)


def test_resolve_stochastic_relation_still_returns_distribution_call():
    result = resolve(
        "precision.sr.x_quantized",
        assignments={
            "precision.quant.x_lo": 0,
            "precision.quant.x_hi": 10,
            "precision.sr.p_up": sp.Rational(1, 4),
        },
    )

    assert result.value == sp.Function("TwoPoint")(0, 10, sp.Rational(1, 4))
    assert result.missing == set()


def test_special_equation_subclasses_accept_role_and_variant(registry_snapshot):
    lhs = Variable(
        "test.special.lhs",
        "lhs_special_role_test",
        "value",
        "Temporary special-equation left-hand variable.",
        scope="test",
    )
    driver = Variable(
        "test.special.driver",
        "driver_special_role_test",
        "value",
        "Temporary special-equation driver variable.",
        scope="test",
    )
    iter_sym = sp.Dummy("special_iter")
    time = sp.Symbol("t_special_role_test")

    equations = [
        PiecewiseEquation(
            "test.eq.special_piecewise_variant",
            lhs.symbol,
            [(driver.symbol, True)],
            "Temporary piecewise variant.",
            role=RelationRole.VARIANT,
            variant="piecewise",
        ),
        DifferentialEquation(
            "test.eq.special_differential_variant",
            lhs.symbol,
            driver.symbol,
            indep_var=time,
            description="Temporary differential variant.",
            role=RelationRole.VARIANT,
            variant="differential",
        ),
        IterativeEquation(
            "test.eq.special_iterative_variant",
            lhs.symbol,
            iter_sym + driver.symbol,
            iteration_variable=iter_sym,
            initial=driver.symbol,
            n_iter=1,
            description="Temporary iterative variant.",
            role=RelationRole.VARIANT,
            variant="iterative",
        ),
        StochasticRelation(
            "test.eq.special_stochastic_variant",
            lhs.symbol,
            distribution="Temporary",
            parameters={"driver": driver.symbol},
            description="Temporary stochastic variant.",
            role=RelationRole.VARIANT,
            variant="stochastic",
        ),
    ]

    assert [(eq.role, eq.variant) for eq in equations] == [
        (RelationRole.VARIANT, "piecewise"),
        (RelationRole.VARIANT, "differential"),
        (RelationRole.VARIANT, "iterative"),
        (RelationRole.VARIANT, "stochastic"),
    ]
    assert {eq.variant for eq in lhs.variants()} == {
        "piecewise",
        "differential",
        "iterative",
        "stochastic",
    }
