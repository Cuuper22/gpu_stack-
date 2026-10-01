"""Regression tests for errors found by the equation-graph audit.

Each test encodes an independent reference formula, not the graph's own
expression. Source for each formula is cited in the test docstring.
"""

import math

import pytest

from gpu_stack import resolve


NO_OTHER_OVERHEAD = {
    "training.t_compute": 1.0,
    "training.t_exposed_comm": 0.0,
    "training.t_mem_bound": 0.0,
    "training.straggler_fraction": 0.0,
    "training.restart_fraction": 0.0,
    "training.eval_fraction": 0.0,
}


@pytest.mark.parametrize("p, m", [(8, 8), (4, 16), (16, 64), (1, 8)])
def test_training_step_time_matches_narayanan_1f1b_multiplier(p, m):
    """Narayanan et al., SC21 (arXiv:2104.04473) Sec. 2.2: bubble time is
    (p-1)(t_f+t_b) on top of an ideal m(t_f+t_b), so step time is
    nominal * (1 + (p-1)/m)."""
    r = resolve(
        "training.t_step",
        assignments={**NO_OTHER_OVERHEAD, "par.pp.n_stages": p, "par.pp.n_microbatches": m},
    )
    assert float(r.value) == pytest.approx(1.0 + (p - 1) / m, rel=1e-12)


def test_training_step_time_adds_other_overheads_once():
    """Pipeline overhead and the other training overheads are all
    overhead-over-nominal terms, so they add: T = T_nom * (1 + (p-1)/m + sum)."""
    p, m = 8, 32
    extra = {
        "training.straggler_fraction": 0.03,
        "training.restart_fraction": 0.02,
        "training.eval_fraction": 0.01,
    }
    r = resolve(
        "training.t_step",
        assignments={
            **NO_OTHER_OVERHEAD,
            **extra,
            "par.pp.n_stages": p,
            "par.pp.n_microbatches": m,
        },
    )
    expected = 1.0 + (p - 1) / m + 0.03 + 0.02 + 0.01
    assert float(r.value) == pytest.approx(expected, rel=1e-12)
    assert math.isfinite(float(r.value))


COLLECTIVE_INPUTS = {
    "col.n_ranks": 64,
    "col.payload": 1e9,
    "col.ranks_per_node": 8,
    "col.n_nodes": 8,
    "link.nvlink.alpha": 1e-6,
    "link.nvlink.beta": 1 / 450e9,
    "link.scaleout.alpha": 5e-6,
    "link.scaleout.beta": 1 / 50e9,
}


def _collective(name):
    return float(resolve(name, assignments=COLLECTIVE_INPUTS).value)


def test_hierarchical_allgather_matches_two_level_reference():
    """Two-level allgather (Thakur, Rabenseifner, Gropp 2005, MPICH
    collectives): each rank holds N/r after the inter-node stage, so the
    inter-node bandwidth term is N (n-1)/(n r) beta_so, then an intra-node
    allgather of N (r-1)/r beta_nv."""
    r, n, big_n = 8, 8, 1e9
    a_nv, b_nv, a_so, b_so = 1e-6, 1 / 450e9, 5e-6, 1 / 50e9
    ref = (
        (n - 1) * a_so
        + (n - 1) / (n * r) * big_n * b_so
        + (r - 1) * a_nv
        + (r - 1) / r * big_n * b_nv
    )
    assert _collective("col.allgather.time_hier") == pytest.approx(ref, rel=1e-12)


def test_hierarchical_allreduce_equals_reducescatter_plus_allgather():
    """Standard identity (Thakur et al. 2005; Patarasuk and Yuan 2009):
    allreduce = reduce-scatter followed by allgather, so the hierarchical
    forms must satisfy it inside the graph."""
    ar = _collective("col.allreduce.time_hier")
    rs = _collective("col.reducescatter.time_hier")
    ag = _collective("col.allgather.time_hier")
    assert ar == pytest.approx(rs + ag, rel=1e-12)


def test_mla_kv_cache_is_latent_plus_rope_key_per_token_per_layer():
    """DeepSeek-V2 (arXiv:2405.04434) Table 1: MLA caches (d_c + d_h^R)
    elements per token per layer, with d_c = 512 and d_h^R = 64."""
    d_c, d_r, nbytes = 512, 64, 2
    r = resolve(
        "arch.kv.bytes_per_tok_layer_mla",
        assignments={"arch.mla.d_latent": d_c + d_r, "arch.kv.bytes_per_val": nbytes},
    )
    assert float(r.value) == (d_c + d_r) * nbytes == 1152


def test_mla_cache_is_smaller_than_gqa_cache_by_the_reference_ratio():
    """Compression ratio is GQA elements over MLA elements: a GQA cache with
    8 KV heads of dim 128 holds 2*128*8 = 2048 elements, MLA holds 576."""
    r = resolve(
        "arch.kv.compression_ratio",
        assignments={
            "arch.mla.d_latent": 576,
            "arch.kv.bytes_per_val": 2,
            "arch.n_kv_heads": 8,
            "arch.head_dim": 128,
        },
    )
    assert float(r.value) == pytest.approx(2048 / 576, rel=1e-12)


def _step_flops_graph_and_reference(n_layers, h, v, heads, untied, s=2048):
    """Graph 6*N_total*T versus Narayanan et al. SC21 Eq. 4 without
    activation recompute: 72 B s L h^2 (1 + s/(6h)) + 6 B s h V, B = 1."""
    a = {
        "arch.n_layers": n_layers,
        "arch.d_model": h,
        "arch.d_ffn": 4 * h,
        "arch.n_heads": heads,
        "arch.vocab": v,
        "arch.output.untied_factor": untied,
        "arch.n_kv_heads": heads,
        "arch.ffn.weight_matrices": 2,
        "arch.norm.param_multiplier": 4,
        "arch.tokens_per_step": s,
    }
    n_total = float(resolve("arch.params_total_dense", assignments=a).value)
    graph = float(resolve("arch.flops.step_dense", assignments=a).value)
    assert graph == pytest.approx(6 * n_total * s, rel=1e-12)
    ref = 72 * s * n_layers * h * h * (1 + s / (6 * h)) + 6 * s * h * v
    return graph, ref


def test_flops_step_dense_is_6_n_total_t_and_matches_exact_at_large_scale():
    """The equation is the 6 * N_total * T approximation, not Kaplan's
    non-embedding form. At GPT-3 scale it is within 3% of exact Megatron
    accounting (Narayanan et al. 2021 Eq. 4, no recompute)."""
    graph, ref = _step_flops_graph_and_reference(96, 12288, 50257, 96, 0)
    assert graph / ref == pytest.approx(1.0, abs=0.03)


def test_flops_step_dense_overcounts_when_embeddings_dominate():
    """Documented regime limit: Pythia-70M has 51.5M of 70.4M parameters in
    the embedding tables, and the approximation is about 23% high."""
    graph, ref = _step_flops_graph_and_reference(6, 512, 50304, 8, 1)
    assert 1.15 < graph / ref < 1.30


def _bubble_share(name, **assign):
    return float(resolve(f"par.pp.bubble_{name}", assignments=assign).value)


@pytest.mark.parametrize("p, m", [(8, 8), (4, 16), (16, 64)])
def test_gpipe_and_1f1b_have_the_same_bubble(p, m):
    """Narayanan et al., SC21 Sec. 2.2: GPipe and 1F1B have the same bubble
    (p-1)/m over ideal time; 1F1B differs in activation memory only."""
    a = {"par.pp.n_stages": p, "par.pp.n_microbatches": m}
    gpipe = _bubble_share("gpipe", **a)
    f1b = _bubble_share("1f1b", **a)
    assert gpipe == pytest.approx(f1b, rel=1e-12)
    # Variable is a share of total time: overhead / (1 + overhead).
    overhead = (p - 1) / m
    assert f1b == pytest.approx(overhead / (1 + overhead), rel=1e-12)


@pytest.mark.parametrize("p, m, v", [(8, 8, 2), (8, 32, 4), (16, 64, 1)])
def test_interleaved_bubble_overhead_is_p_minus_1_over_v_m(p, m, v):
    """Narayanan et al., SC21 Sec. 2.2.2: interleaved overhead over ideal is
    (p-1)/(v m)."""
    phi = _bubble_share(
        "interleaved",
        **{"par.pp.n_stages": p, "par.pp.n_microbatches": m, "par.pp.virtual_stages": v},
    )
    overhead = phi / (1 - phi)
    assert overhead == pytest.approx((p - 1) / (v * m), rel=1e-12)
    if v == 1:
        a = {"par.pp.n_stages": p, "par.pp.n_microbatches": m}
        assert phi == pytest.approx(_bubble_share("1f1b", **a), rel=1e-12)


def test_flicker_noise_psd_is_dimensionally_consistent_at_gamma_one():
    """S_v [V^2/Hz] = K_f / (C_ox W L f) with C_ox in F/m^2: K_f must be V^2*F
    (Tsividis and McAndrew, Operation and Modeling of the MOS Transistor, the
    1/f noise model). The checker cannot take a symbolic exponent, so the
    equation is checked here with gamma = 1."""
    import sympy as sp

    from gpu_stack import Registry
    from gpu_stack.core.units import (
        FARAD,
        HZ,
        VOLT,
        check_dimensional_consistency,
        infer_expr_units,
    )

    eq = Registry.equations["physical.eq.flicker_noise_psd"]
    gamma = Registry.variables["physical.noise.flicker_exponent"].symbol
    rhs = eq.rhs.subs(gamma, 1)
    lookup = {
        sym: Registry.lookup_by_symbol(sym).sp_units
        for sym in rhs.free_symbols
    }
    rhs_units = infer_expr_units(rhs, lookup, eq.name)
    lhs_units = Registry.variables["physical.noise.flicker_psd"].sp_units
    check_dimensional_consistency(lhs_units, rhs_units, eq.name)
    assert Registry.variables["physical.noise.flicker_coeff"].sp_units == VOLT**2 * FARAD
    assert sp.simplify(lhs_units - VOLT**2 / HZ) == 0


def test_carrier_continuity_unit_check_handles_the_time_derivative():
    """dn/dt = G - R: the left side is n divided by time. Running the unit
    check on the registered equation passes, and a rhs with the wrong
    dimension is rejected."""
    from gpu_stack import Registry
    from gpu_stack.core import DifferentialEquation
    from gpu_stack.core.units import UnitError

    good = Registry.equations["physical.eq.carrier_continuity"]
    good._check_units()  # raises UnitError on a dimension or scale mismatch

    n = Registry.variables["physical.carrier_density"]
    t = Registry.variables["physical.time"]
    # n is 1/m^3, so d n / d t = n has the wrong dimension (missing 1/s).
    with pytest.raises(UnitError):
        DifferentialEquation(
            "test.eq.carrier_continuity_bad_units",
            n.symbol,
            n.symbol,
            indep_var=t,
            order=1,
            check_units=True,
        )
    assert "test.eq.carrier_continuity_bad_units" not in Registry.equations
