"""
tests/test_resolver.py
======================

Core scenario resolver coverage for `gpu_stack.core.resolver`.
"""

import pytest

from gpu_stack import Registry, resolve
from gpu_stack.core import (
    AmbiguousVariant,
    InvalidVariantSelector,
)


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
