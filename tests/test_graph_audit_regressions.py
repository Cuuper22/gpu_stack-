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
