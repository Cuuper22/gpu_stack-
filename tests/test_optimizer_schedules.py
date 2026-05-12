"""
tests/test_optimizer_schedules.py
=================================

Regression coverage for optimizer schedule domain and horizon constraints.
"""

import pytest
import sympy as sp

from gpu_stack import Inequality, Registry, RelationRole, resolve


def failed_constraint(result, equation):
    check = next(c for c in result.constraints if c.equation == equation)
    assert check.satisfied is False
    assert check.missing == set()
    return check


def satisfied_constraint(result, equation):
    check = next(c for c in result.constraints if c.equation == equation)
    assert check.satisfied is True
    assert check.missing == set()
    return check


def test_optimizer_schedule_variables_have_domain_metadata():
    expected = {
        "opt.step_index": {"integer": True, "positive": True},
        "opt.schedule.lr_base": {"nonnegative": True},
        "opt.schedule.warmup_steps": {"integer": True, "positive": True},
        "opt.schedule.total_steps": {"integer": True, "positive": True},
        "opt.schedule.wsd_stable_steps": {
            "integer": True,
            "nonnegative": True,
        },
    }

    for variable_name, assumptions in expected.items():
        variable = Registry.variables[variable_name]
        for key, value in assumptions.items():
            assert variable.assumptions.get(key) is value


def test_optimizer_schedule_domains_report_invalid_assignments():
    result = resolve(
        "opt.schedule.lr_wsd",
        assignments={
            "opt.schedule.lr_base": -0.25,
            "opt.step_index": sp.Rational(1, 2),
            "opt.schedule.warmup_steps": 2.5,
            "opt.schedule.total_steps": 6.5,
            "opt.schedule.wsd_stable_steps": -0.5,
        },
    )

    failed_constraint(result, "domain.opt.schedule.lr_base.nonnegative")
    failed_constraint(result, "domain.opt.step_index.integer")
    failed_constraint(result, "domain.opt.schedule.warmup_steps.integer")
    failed_constraint(result, "domain.opt.schedule.total_steps.integer")
    failed_constraint(result, "domain.opt.schedule.wsd_stable_steps.nonnegative")
    failed_constraint(result, "domain.opt.schedule.wsd_stable_steps.integer")


def test_optimizer_schedule_ordering_constraints_are_explicit_feasibility_relations():
    expected = {
        "opt.ineq.schedule_total_steps_exceeds_warmup_steps": (
            ">",
            Registry.variables["opt.schedule.warmup_steps"].symbol,
        ),
        "opt.ineq.schedule_total_steps_exceeds_warmup_and_stable_steps": (
            ">",
            Registry.variables["opt.schedule.warmup_steps"].symbol
            + Registry.variables["opt.schedule.wsd_stable_steps"].symbol,
        ),
        "opt.ineq.schedule_total_steps_reaches_current_step": (
            ">=",
            Registry.variables["opt.step_index"].symbol,
        ),
    }
    total_steps = Registry.variables["opt.schedule.total_steps"]

    for equation_name, (op, rhs) in expected.items():
        relation = Registry.equations[equation_name]
        assert isinstance(relation, Inequality)
        assert relation.role is RelationRole.CONSTRAINT
        assert relation in total_steps.constraints()
        assert relation.lhs == total_steps.symbol
        assert relation.rhs == rhs
        assert relation.op == op
        assert not getattr(relation, "_check_units_flag", False)
        assert relation.as_sympy() is not sp.S.true
        assert isinstance(relation.as_sympy(), sp.Rel)


def test_optimizer_schedule_ordering_constraints_report_invalid_scenarios():
    invalid = resolve(
        "opt.schedule.lr_wsd",
        assignments={
            "opt.schedule.lr_base": 1.0,
            "opt.step_index": 5,
            "opt.schedule.warmup_steps": 4,
            "opt.schedule.total_steps": 4,
            "opt.schedule.wsd_stable_steps": 1,
        },
    )

    failed_constraint(
        invalid,
        "opt.ineq.schedule_total_steps_exceeds_warmup_steps",
    )
    failed_constraint(
        invalid,
        "opt.ineq.schedule_total_steps_exceeds_warmup_and_stable_steps",
    )
    failed_constraint(
        invalid,
        "opt.ineq.schedule_total_steps_reaches_current_step",
    )

    boundary = resolve(
        "opt.schedule.lr_wsd",
        assignments={
            "opt.schedule.lr_base": 1.0,
            "opt.step_index": 6,
            "opt.schedule.warmup_steps": 2,
            "opt.schedule.total_steps": 6,
            "opt.schedule.wsd_stable_steps": 1,
        },
    )

    assert float(boundary.value) == pytest.approx(0.0)
    satisfied_constraint(
        boundary,
        "opt.ineq.schedule_total_steps_exceeds_warmup_steps",
    )
    satisfied_constraint(
        boundary,
        "opt.ineq.schedule_total_steps_exceeds_warmup_and_stable_steps",
    )
    satisfied_constraint(
        boundary,
        "opt.ineq.schedule_total_steps_reaches_current_step",
    )
