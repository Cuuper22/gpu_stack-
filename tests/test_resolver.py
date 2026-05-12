"""
tests/test_resolver.py
======================

Coverage for the scenario resolver in `gpu_stack.core.resolver`.

The resolver turns the registry from a pure inspection surface into a
one-call evaluator. Tests cover the core success path, role-aware
equation selection, variant disambiguation, and the error modes that
the Phase 4 ticket in ROADMAP.md calls out: underdetermined and
ambiguous scenarios.
"""

import pytest
import sympy as sp

import gpu_stack
from gpu_stack import Registry, resolve
from gpu_stack.core import (
    AmbiguousVariant,
    Approximation,
    ApproximationValidityCheck,
    ConstraintCheck,
    DifferentialEquation,
    Equation,
    Inequality,
    IterativeEquation,
    InvalidVariantSelector,
    PiecewiseEquation,
    RelationRole,
    StochasticRelation,
    Underdetermined,
    var,
)
from gpu_stack.core.resolver import _value_dependencies
from gpu_stack.core.variable import Variable


@pytest.fixture
def registry_snapshot():
    variables = dict(Registry.variables)
    equations = dict(Registry.equations)
    systems = dict(Registry.systems)
    symbol_cache = dict(Registry._symbol_cache)
    backrefs = {
        name: (list(v._defined_by), list(v._used_in))
        for name, v in variables.items()
    }

    yield

    for name, (defined_by, used_in) in backrefs.items():
        v = variables[name]
        v._defined_by[:] = defined_by
        v._used_in[:] = used_in
    Registry.variables = variables
    Registry.equations = equations
    Registry.systems = systems
    Registry._symbol_cache = symbol_cache


def _resolver_dep_names(equation_name):
    return {
        v.name
        for v in _value_dependencies(Registry.equations[equation_name])
    }


def test_resolve_rack_peak_flops_from_scenario():
    result = resolve(
        "cluster.rack.peak_flops",
        assignments={
            "cluster.rack.n_nodes": 9,
            "cluster.node.n_gpus": 8,
            "gpu.peak_flops": 15e15,
        },
    )
    assert float(result.value) == pytest.approx(1.08e18, rel=1e-12)
    names = [step.equation for step in result.trace]
    assert "cluster.eq.node_peak_flops" in names
    assert "cluster.eq.rack_peak_flops" in names


def test_resolve_prefers_identity_over_approximation():
    # physical.drift_velocity has one approximation (low-field) and one
    # identity (saturated). The resolver must pick the identity.
    result = resolve(
        "physical.drift_velocity",
        assignments={
            "physical.carrier_mobility": 0.05,
            "physical.electric_field": 1e5,
            "physical.velocity_saturation": 1e5,
        },
    )
    assert "physical.eq.drift_velocity_saturated" in [s.equation for s in result.trace]
    assert "physical.eq.drift_velocity_low_field" not in [s.equation for s in result.trace]


def test_resolve_requires_variant_selector():
    # training.flops_per_step has VARIANT dense + VARIANT moe. Without a
    # selector the resolver raises AmbiguousVariant.
    with pytest.raises(AmbiguousVariant):
        resolve(
            "training.flops_per_step",
            assignments={"arch.flops.step_dense": 1e21},
        )


def test_resolve_with_variant_selector_dense():
    result = resolve(
        "training.flops_per_step",
        assignments={"arch.flops.step_dense": 1e21},
        variants={"training.flops_per_step": "dense"},
    )
    assert float(result.value) == pytest.approx(1e21, rel=1e-12)
    assert any(s.variant == "dense" for s in result.trace)


def test_resolve_with_variant_selector_moe():
    result = resolve(
        "training.flops_per_step",
        assignments={"arch.flops.step_moe": 3e20},
        variants={"training.flops_per_step": "moe"},
    )
    assert float(result.value) == pytest.approx(3e20, rel=1e-12)
    assert any(s.variant == "moe" for s in result.trace)


def test_resolve_rejects_unknown_variant_selector_variable():
    with pytest.raises(InvalidVariantSelector, match="unknown variant selector"):
        resolve(
            "cluster.rack.peak_flops",
            assignments={
                "cluster.rack.n_nodes": 9,
                "cluster.node.n_gpus": 8,
                "gpu.peak_flops": 15e15,
            },
            variants={"training.flopz_per_step": "dense"},
        )


def test_resolve_rejects_selector_for_non_variant_variable():
    with pytest.raises(InvalidVariantSelector, match="no VARIANT relations"):
        resolve(
            "cluster.rack.peak_flops",
            assignments={
                "cluster.rack.n_nodes": 9,
                "cluster.node.n_gpus": 8,
                "gpu.peak_flops": 15e15,
            },
            variants={"cluster.rack.n_nodes": "dense"},
        )


def test_resolve_rejects_unknown_variant_key_even_when_selector_unused():
    with pytest.raises(InvalidVariantSelector, match="variant key"):
        resolve(
            "cluster.rack.peak_flops",
            assignments={
                "cluster.rack.n_nodes": 9,
                "cluster.node.n_gpus": 8,
                "gpu.peak_flops": 15e15,
            },
            variants={"training.flops_per_step": "denze"},
        )


def test_resolve_allows_valid_unused_variant_selector():
    result = resolve(
        "cluster.rack.peak_flops",
        assignments={
            "cluster.rack.n_nodes": 9,
            "cluster.node.n_gpus": 8,
            "gpu.peak_flops": 15e15,
        },
        variants={"training.flops_per_step": "dense"},
    )
    assert float(result.value) == pytest.approx(1.08e18, rel=1e-12)


def test_resolve_target_via_variable_instance():
    v = Registry.variables["cluster.node.peak_flops"]
    result = resolve(
        v,
        assignments={
            "cluster.node.n_gpus": 8,
            "gpu.peak_flops": 15e15,
        },
    )
    assert float(result.value) == pytest.approx(1.2e17, rel=1e-12)


def test_resolve_leaves_unassigned_subtree_as_symbolic_boundary():
    # cluster.node.peak_flops needs cluster.node.n_gpus and gpu.peak_flops.
    # If gpu.peak_flops is unassigned, the resolver should leave it as a
    # symbolic boundary instead of expanding the full GPU/physical ancestry.
    result = resolve(
        "cluster.node.peak_flops",
        assignments={"cluster.node.n_gpus": 8},
    )
    assert result.value.free_symbols, (
        "expected a symbolic boundary when a deep dependency is unpinned"
    )
    assert [step.equation for step in result.trace] == [
        "cluster.eq.node_peak_flops",
    ]
    assert result.missing == {"gpu.peak_flops"}


def test_resolve_nested_unselected_variant_is_symbolic_boundary():
    result = resolve("training.flops_executed_per_step")
    assert result.value.free_symbols
    assert "training.flops_per_step" in result.missing


def test_constraint_helper_uses_selected_variant(registry_snapshot):
    target = Variable(
        "test.constraint_variant.target",
        "target_constraint_variant_test",
        "value",
        "Temporary target with a helper-dependent constraint.",
        scope="test",
    )
    helper = Variable(
        "test.constraint_variant.helper",
        "helper_constraint_variant_test",
        "value",
        "Temporary helper selected through a variant relation.",
        scope="test",
    )
    driver = Variable(
        "test.constraint_variant.driver",
        "driver_constraint_variant_test",
        "value",
        "Temporary assigned driver for the helper variant.",
        scope="test",
    )
    Equation(
        "test.eq.constraint_variant_target",
        target.symbol,
        sp.Integer(1),
        "Temporary target identity.",
    )
    Equation(
        "test.eq.constraint_variant_helper",
        helper.symbol,
        driver.symbol,
        "Temporary helper variant.",
        role=RelationRole.VARIANT,
        variant="selected",
    )
    Equation(
        "test.eq.constraint_variant_helper_too_small",
        helper.symbol,
        sp.Integer(0),
        "Temporary alternate helper variant that would violate the constraint.",
        role=RelationRole.VARIANT,
        variant="too_small",
    )
    Inequality(
        "test.ineq.constraint_variant_target_le_helper",
        target.symbol,
        helper.symbol,
        "<=",
        "Temporary constraint that needs a selected helper variant.",
    )

    result = resolve(
        target.name,
        assignments={driver.name: 2},
        variants={helper.name: "selected"},
    )

    check = next(
        c for c in result.constraints
        if c.equation == "test.ineq.constraint_variant_target_le_helper"
    )
    assert check.satisfied is True
    assert check.missing == set()


def test_resolve_reports_constraint_for_symbolic_boundary_variable(
    registry_snapshot,
):
    target = Variable(
        "test.boundary_constraint.target",
        "target_boundary_constraint_test",
        "value",
        "Temporary target with a symbolic boundary dependency.",
        scope="test",
    )
    boundary = Variable(
        "test.boundary_constraint.boundary",
        "boundary_constraint_test",
        "value",
        "Temporary symbolic boundary variable.",
        scope="test",
    )

    Equation(
        "test.eq.boundary_constraint_target",
        target.symbol,
        boundary.symbol + 1,
        "Temporary target that leaves a symbolic boundary.",
    )
    Inequality(
        "test.ineq.boundary_constraint_nonnegative",
        boundary.symbol,
        0,
        ">=",
        "Temporary constraint attached to a symbolic boundary.",
    )

    result = resolve(target.name)

    assert result.missing == {boundary.name}
    check = next(
        c for c in result.constraints
        if c.equation == "test.ineq.boundary_constraint_nonnegative"
    )
    assert check.satisfied is None
    assert check.missing == {boundary.name}


def test_constraint_helper_extends_values_recursively(registry_snapshot):
    target = Variable(
        "test.constraint_helper_chain.target",
        "target_constraint_helper_chain_test",
        "value",
        "Temporary target with a recursive helper constraint.",
        scope="test",
    )
    helper = Variable(
        "test.constraint_helper_chain.helper",
        "helper_constraint_helper_chain_test",
        "value",
        "Temporary recursive constraint helper.",
        scope="test",
    )
    mid = Variable(
        "test.constraint_helper_chain.mid",
        "mid_constraint_helper_chain_test",
        "value",
        "Temporary middle helper.",
        scope="test",
    )
    driver = Variable(
        "test.constraint_helper_chain.driver",
        "driver_constraint_helper_chain_test",
        "value",
        "Temporary helper-chain driver.",
        scope="test",
    )

    Equation(
        "test.eq.constraint_helper_chain_target",
        target.symbol,
        1,
        "Temporary constant target.",
    )
    Equation(
        "test.eq.constraint_helper_chain_mid",
        mid.symbol,
        driver.symbol + 1,
        "Temporary middle helper definition.",
    )
    Equation(
        "test.eq.constraint_helper_chain_helper",
        helper.symbol,
        mid.symbol + 1,
        "Temporary recursive helper definition.",
    )
    Inequality(
        "test.ineq.constraint_helper_chain_target_le_helper",
        target.symbol,
        helper.symbol,
        "<=",
        "Temporary constraint that needs a recursive helper.",
    )

    result = resolve(target.name, assignments={driver.name: 1})

    check = next(
        c for c in result.constraints
        if c.equation == "test.ineq.constraint_helper_chain_target_le_helper"
    )
    assert check.satisfied is True
    assert check.missing == set()


def test_constraint_helper_recursion_stops_at_unresolved_subtree(
    registry_snapshot,
):
    target = Variable(
        "test.constraint_helper_unresolved.target",
        "target_constraint_helper_unresolved_test",
        "value",
        "Temporary target with an unresolved helper constraint.",
        scope="test",
    )
    helper = Variable(
        "test.constraint_helper_unresolved.helper",
        "helper_constraint_helper_unresolved_test",
        "value",
        "Temporary unresolved constraint helper.",
        scope="test",
    )
    dangling = Variable(
        "test.constraint_helper_unresolved.dangling",
        "dangling_constraint_helper_unresolved_test",
        "value",
        "Temporary unresolved helper dependency.",
        scope="test",
    )

    Equation(
        "test.eq.constraint_helper_unresolved_target",
        target.symbol,
        1,
        "Temporary constant target.",
    )
    Equation(
        "test.eq.constraint_helper_unresolved_helper",
        helper.symbol,
        dangling.symbol + 1,
        "Temporary helper with an unresolved dependency.",
    )
    Inequality(
        "test.ineq.constraint_helper_unresolved_target_le_helper",
        target.symbol,
        helper.symbol,
        "<=",
        "Temporary constraint that should remain symbolic.",
    )

    result = resolve(target.name)

    check = next(
        c for c in result.constraints
        if c.equation == "test.ineq.constraint_helper_unresolved_target_le_helper"
    )
    assert check.satisfied is None
    assert check.missing == {helper.name}


def test_resolver_value_trace_ignores_validity_only_dependencies():
    result = resolve(
        "physical.clock_frequency",
        assignments={
            "physical.clock.max_timing_frequency": 0.5,
            "physical.clock.derate": 0.8,
            "physical.gate.r_on": 1.0,
            "physical.gate.fanout": 1,
            "physical.gate.c_input": 1.0,
            "physical.interconnect.c_total": 1.0,
            "physical.interconnect.r_per_length": 0.0,
            "physical.interconnect.c_per_length": 1.0,
            "physical.wire_length": 1.0,
        },
    )
    assert float(result.value) == pytest.approx(0.4)
    assert "physical.eq.elmore_delay" not in [
        step.equation for step in result.trace
    ]
    check = next(
        c for c in result.approximation_validity
        if c.equation == "physical.eq.clock_frequency_timing_model"
    )
    assert check.satisfied is True


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


def test_value_dependencies_include_piecewise_conditions():
    deps = _resolver_dep_names("gpu.eq.power_throttle_factor")

    assert {"gpu.power.total", "gpu.tdp"} <= deps


def test_resolve_piecewise_equation_still_evaluates_conditions():
    result = resolve(
        "gpu.power.throttle_factor",
        assignments={
            "gpu.power.total": 200,
            "gpu.tdp": 100,
        },
    )

    assert result.value == sp.Rational(1, 2)


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


def test_variant_approximation_reports_unresolved_validity(registry_snapshot):
    x = Variable(
        "test.approx.x",
        "x_approx_variant_test",
        "value",
        "Temporary approximation output.",
        scope="test",
    )
    y = Variable(
        "test.approx.y",
        "y_approx_variant_test",
        "value",
        "Temporary approximation input.",
        scope="test",
    )
    z = Variable(
        "test.approx.z",
        "z_approx_variant_test",
        "value",
        "Temporary approximation validity input.",
        scope="test",
    )
    Approximation(
        "test.eq.approx_variant",
        x.symbol,
        y.symbol + 1,
        z.symbol > 0,
        "Temporary approximate variant with independent validity predicate.",
        role=RelationRole.VARIANT,
        variant="alt",
    )

    result = resolve(
        "test.approx.x",
        assignments={"test.approx.y": 2},
        variants={"test.approx.x": "alt"},
    )

    assert result.value == 3
    assert result.missing == set()
    assert len(result.approximation_validity) == 1
    check = result.approximation_validity[0]
    assert check.equation == "test.eq.approx_variant"
    assert check.satisfied is None
    assert check.missing == {"test.approx.z"}


def test_resolve_trace_order_is_topological():
    result = resolve(
        "cluster.node.peak_flops",
        assignments={
            "cluster.node.n_gpus": 8,
            "gpu.peak_flops": 15e15,
        },
    )
    trace_names = [s.variable for s in result.trace]
    # node.peak_flops depends on gpu.peak_flops (assigned) and
    # cluster.node.n_gpus (assigned). With both inputs in the scenario
    # only the target equation fires.
    assert trace_names[-1] == "cluster.node.peak_flops"


def test_resolve_accepts_symbol_key_in_assignments():
    v = Registry.variables["cluster.node.n_gpus"]
    gpu_peak = Registry.variables["gpu.peak_flops"]
    result = resolve(
        "cluster.node.peak_flops",
        assignments={v.symbol: 4, gpu_peak.symbol: 2e15},
    )
    assert float(result.value) == pytest.approx(8e15, rel=1e-12)


def test_resolve_reports_satisfied_constraints():
    result = resolve(
        "physical.gate.elmore_delay",
        assignments={
            "physical.gate.r_on": 1.0,
            "physical.gate.fanout": 1,
            "physical.gate.c_input": 1.0,
            "physical.interconnect.c_total": 1.0,
            "physical.interconnect.r_per_length": 0.0,
            "physical.interconnect.c_per_length": 1.0,
            "physical.wire_length": 1.0,
            "physical.clock_frequency": 0.1,
        },
    )
    assert result.constraints
    check = next(
        c for c in result.constraints
        if c.equation == "physical.eq.clock_timing_constraint"
    )
    assert isinstance(check, ConstraintCheck)
    assert check.satisfied is True


def test_resolve_reports_violated_constraints():
    result = resolve(
        "physical.gate.elmore_delay",
        assignments={
            "physical.gate.r_on": 1.0,
            "physical.gate.fanout": 1,
            "physical.gate.c_input": 1.0,
            "physical.interconnect.c_total": 1.0,
            "physical.interconnect.r_per_length": 0.0,
            "physical.interconnect.c_per_length": 1.0,
            "physical.wire_length": 1.0,
            "physical.clock_frequency": 1.0,
        },
    )
    check = next(
        c for c in result.constraints
        if c.equation == "physical.eq.clock_timing_constraint"
    )
    assert check.satisfied is False


def test_expression_lhs_constraint_is_reported_for_lhs_variables(registry_snapshot):
    target = var(
        "test.expr_lhs.target",
        "test_expr_lhs_target",
        "value",
        "Temporary expression-LHS target.",
        scope="test",
    )
    driver = var(
        "test.expr_lhs.driver",
        "test_expr_lhs_driver",
        "value",
        "Temporary target driver.",
        scope="test",
    )
    offset = var(
        "test.expr_lhs.offset",
        "test_expr_lhs_offset",
        "value",
        "Temporary LHS offset.",
        scope="test",
    )
    limit = var(
        "test.expr_lhs.limit",
        "test_expr_lhs_limit",
        "value",
        "Temporary constraint limit.",
        scope="test",
    )

    Equation(
        "test.eq.expr_lhs_target",
        target.symbol,
        driver.symbol,
        "Temporary target identity.",
    )
    relation = Inequality(
        "test.ineq.expr_lhs_target_plus_offset_le_limit",
        target.symbol + offset.symbol,
        limit.symbol,
        "<=",
        "Temporary expression-LHS constraint.",
    )

    assert relation in target.constraints()
    assert relation in offset.constraints()
    assert target.direct_dependencies() == {driver}
    assert {
        v.name for v in target.direct_dependencies(include_constraints=True)
    } == {
        driver.name,
        offset.name,
        limit.name,
    }

    result = resolve(
        target.name,
        assignments={
            driver.name: 2,
            offset.name: 1,
            limit.name: 5,
        },
    )

    check = next(
        c for c in result.constraints
        if c.equation == "test.ineq.expr_lhs_target_plus_offset_le_limit"
    )
    assert check.satisfied is True
    assert check.missing == set()


def test_raw_symbols_on_expression_lhs_constraints_are_reported(registry_snapshot):
    owner = var(
        "test.expr_lhs_raw.owner",
        "test_expr_lhs_raw_owner",
        "value",
        "Temporary expression-LHS raw-symbol owner.",
        scope="test",
    )
    limit = var(
        "test.expr_lhs_raw.limit",
        "test_expr_lhs_raw_limit",
        "value",
        "Temporary expression-LHS raw-symbol limit.",
        scope="test",
    )
    raw = sp.Symbol("test_expr_lhs_raw_ghost")

    inequality = Inequality(
        "test.ineq.expr_lhs_raw",
        owner.symbol + raw,
        limit.symbol,
        "<=",
        "Temporary expression-LHS inequality with a raw symbol.",
    )
    generic_constraint = Equation(
        "test.eq.expr_lhs_raw_constraint",
        owner.symbol + raw,
        limit.symbol,
        "Temporary expression-LHS constraint with a raw symbol.",
        role=RelationRole.CONSTRAINT,
    )

    assert inequality.raw_dependency_symbols() == {raw}
    assert generic_constraint.raw_dependency_symbols() == {raw}


def test_resolve_reports_violated_approximation_validity():
    result = resolve(
        "physical.lithography.medium_formula_unit_intercomponent_binding_energy",
        assignments={
            "physical.lithography.medium_component_a_effective_intercomponent_charge_number": 1,
            "physical.lithography.medium_component_b_effective_intercomponent_charge_number": 1,
            "physical.lithography.medium_formula_unit_intercomponent_pair_count": 1,
            "physical.lithography.medium_intercomponent_effective_separation": 1e-9,
            "physical.lithography.medium_intercomponent_relative_permittivity": 1,
        },
    )
    check = next(
        c for c in result.approximation_validity
        if c.equation
        == "physical.eq.lithography_medium_formula_unit_intercomponent_binding_energy"
    )
    assert isinstance(check, ApproximationValidityCheck)
    assert check.satisfied is False


def test_recovered_approximation_validity_detects_violated_domain():
    result = resolve(
        "physical.lithography.source_nuclear_radius_coefficient",
        assignments={
            "physical.lithography.source_binding_coulomb_coefficient": -1.0,
        },
    )
    check = next(
        c for c in result.approximation_validity
        if c.equation == "physical.eq.lithography_source_nuclear_radius_coefficient"
    )
    assert check.satisfied is False
    assert check.missing == set()


def test_recovered_approximation_validity_stays_symbolic_when_domain_missing():
    result = resolve("physical.lithography.source_nuclear_radius_coefficient")
    check = next(
        c for c in result.approximation_validity
        if c.equation == "physical.eq.lithography_source_nuclear_radius_coefficient"
    )
    assert check.satisfied is None
    assert check.missing == {
        "physical.lithography.source_binding_coulomb_coefficient"
    }


def test_resolve_reports_violated_variable_domain_for_assigned_boundary():
    result = resolve(
        "physical.lithography.source_plasma_drive_peak_intensity",
        assignments={
            "physical.lithography.source_plasma_drive_pulse_fluence": -1.0,
            "physical.lithography.source_plasma_drive_pulse_duration": 1.0,
            "physical.lithography.source_plasma_drive_pulse_temporal_shape_factor": 1.0,
        },
    )

    assert float(result.value) == pytest.approx(-1.0)
    domain_check = next(
        c for c in result.constraints
        if c.equation
        == "domain.physical.lithography.source_plasma_drive_pulse_fluence.positive"
    )
    assert domain_check.satisfied is False
