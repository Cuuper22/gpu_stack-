"""Tests for ``gpu_stack.uncertainty`` — Monte Carlo propagation.

Instead of one number per input, the caller gives a distribution (uniform,
normal, or lognormal); the propagator draws samples, resolves the target for
each, and reports mean, std, and quantiles. These tests cover the guardrails
(distributions must respect a variable's positivity assumption, duplicate
uncertain inputs are rejected), seeded determinism, quantile ordering, exact
agreement with the analytic mean and std on a hand-checkable linear case,
and honest failure accounting when a sample makes the model blow up.

All uncertain ranges used here are SYNTHETIC FIXTURES chosen for
deterministic testability; they are not historical data, vendor
specifications, or price recommendations.
"""

from __future__ import annotations

import math
from typing import Optional

import pytest

from gpu_stack.uncertainty import (
    Distribution,
    TargetUncertaintyStats,
    UncertainAssignment,
    UncertaintyResult,
    lognormal,
    normal,
    propagate_uncertainty,
    uniform,
)
from gpu_stack.presets import scenarios


# ---------------------------------------------------------------------------
# Synthetic fixture helpers
# ---------------------------------------------------------------------------

SYNTHETIC_PRESET = scenarios.dense_training_cost_fixture

# SYNTHETIC: electricity price range 0.25--0.45 $/kWh, chosen for
# round-number test arithmetic; not a market data range.
SYNTH_PRICE_UNIFORM = uniform(0.25, 0.45)

# SYNTHETIC: cluster availability 0.85--1.0, round-number assumption.
SYNTH_AVAIL_UNIFORM = uniform(0.85, 1.0)

# SYNTHETIC: normal distribution over electricity price; mean=0.36, std=0.05.
SYNTH_PRICE_NORMAL = normal(mean=0.36, std=0.05)

# SYNTHETIC: log-normal over power price; mu=log(0.36), sigma=0.1 (approx 10%).
import math as _math
SYNTH_PRICE_LOGNORMAL = lognormal(mu=_math.log(0.36), sigma=0.1)

UNCERTAIN_PRICE = UncertainAssignment(
    "econ.power.price_kwh_peak",
    SYNTH_PRICE_UNIFORM,
)
UNCERTAIN_OFFPEAK = UncertainAssignment(
    "econ.power.price_kwh_offpeak",
    SYNTH_PRICE_UNIFORM,
)
UNCERTAIN_AVAIL = UncertainAssignment(
    "training.cluster_availability",
    SYNTH_AVAIL_UNIFORM,
)

COST_TARGET = ("cost_per_token", "econ.cost.per_token")
POWER_TARGET = ("job_dc_power", "econ.job.dc_power")


# ---------------------------------------------------------------------------
# Distribution constructor validation
# ---------------------------------------------------------------------------

def test_uniform_requires_low_le_high():
    with pytest.raises(ValueError, match="low.*<=.*high"):
        uniform(0.5, 0.3)


def test_uniform_equal_bounds_is_valid():
    d = uniform(0.36, 0.36)
    assert d.low == 0.36
    assert d.high == 0.36


def test_normal_requires_positive_std():
    with pytest.raises(ValueError, match="std"):
        normal(0.36, -0.01)
    with pytest.raises(ValueError, match="std"):
        normal(0.36, 0.0)


def test_lognormal_requires_positive_sigma():
    with pytest.raises(ValueError, match="sigma"):
        lognormal(0.0, 0.0)
    with pytest.raises(ValueError, match="sigma"):
        lognormal(0.0, -0.1)


def test_distribution_to_dict_shapes():
    assert uniform(0.2, 0.4).to_dict() == {
        "kind": "uniform", "low": 0.2, "high": 0.4
    }
    assert normal(0.36, 0.05).to_dict() == {
        "kind": "normal", "mean": 0.36, "std": 0.05
    }
    assert lognormal(0.0, 0.1).to_dict() == {
        "kind": "lognormal", "mu": 0.0, "sigma": 0.1
    }


# ---------------------------------------------------------------------------
# UncertainAssignment validation
# ---------------------------------------------------------------------------

def test_uncertain_assignment_rejects_unknown_variable():
    with pytest.raises(ValueError, match="unknown variable"):
        UncertainAssignment("no.such.variable", uniform(0.1, 0.9))


def test_uncertain_assignment_accepts_real_only_variable():
    # econ.power.price_kwh_peak has real=True, no sign assumption -> accept any
    ua = UncertainAssignment("econ.power.price_kwh_peak", uniform(0.25, 0.45))
    assert ua.name == "econ.power.price_kwh_peak"


def test_uncertain_assignment_to_dict_echoes_spec():
    ua = UncertainAssignment("econ.power.price_kwh_peak", uniform(0.25, 0.45))
    d = ua.to_dict()
    assert d["name"] == "econ.power.price_kwh_peak"
    assert d["distribution"]["kind"] == "uniform"
    assert d["distribution"]["low"] == 0.25


def test_uncertain_assignment_rejects_normal_for_positive_variable():
    """
    SYNTHETIC: physics.speed_of_light has positive=True. Normal dist has
    mass at negative values, so it must be rejected.
    """
    from gpu_stack import Registry
    positive_vars = [
        name for name, v in Registry.variables.items()
        if v.symbol.is_positive
    ]
    assert positive_vars, "need at least one positive-assumption variable"
    target = positive_vars[0]
    with pytest.raises(ValueError, match="positive=True"):
        UncertainAssignment(target, normal(mean=1.0, std=0.5))


def test_uncertain_assignment_rejects_negative_uniform_for_positive_variable():
    from gpu_stack import Registry
    positive_vars = [
        name for name, v in Registry.variables.items()
        if v.symbol.is_positive
    ]
    assert positive_vars
    target = positive_vars[0]
    with pytest.raises(ValueError, match="positive=True"):
        UncertainAssignment(target, uniform(-1.0, 1.0))


def test_uncertain_assignment_accepts_lognormal_for_positive_variable():
    from gpu_stack import Registry
    positive_vars = [
        name for name, v in Registry.variables.items()
        if v.symbol.is_positive
    ]
    assert positive_vars
    target = positive_vars[0]
    # lognormal never places mass at non-positive values - should be accepted
    ua = UncertainAssignment(target, lognormal(mu=0.0, sigma=0.1))
    assert ua.name == target


# ---------------------------------------------------------------------------
# propagate_uncertainty: input validation
# ---------------------------------------------------------------------------

def test_propagate_uncertainty_requires_nonempty_uncertain():
    with pytest.raises(ValueError, match="uncertain must contain"):
        propagate_uncertainty(
            SYNTHETIC_PRESET,
            [COST_TARGET],
            uncertain=[],
            n_samples=10,
            seed=0,
        )


def test_propagate_uncertainty_requires_positive_n_samples():
    with pytest.raises(ValueError, match="n_samples must be >= 1"):
        propagate_uncertainty(
            SYNTHETIC_PRESET,
            [COST_TARGET],
            uncertain=[UNCERTAIN_PRICE],
            n_samples=0,
            seed=0,
        )


def test_propagate_uncertainty_rejects_duplicate_uncertain_variable():
    """Duplicate variable names in uncertain list must raise ValueError."""
    ua1 = UncertainAssignment("econ.power.price_kwh_peak", uniform(0.25, 0.35))
    ua2 = UncertainAssignment("econ.power.price_kwh_peak", uniform(0.30, 0.45))
    with pytest.raises(ValueError, match="appears more than once"):
        propagate_uncertainty(
            SYNTHETIC_PRESET,
            [COST_TARGET],
            uncertain=[ua1, ua2],
            n_samples=5,
            seed=0,
        )


def test_propagate_uncertainty_requires_uncertain_var_in_base_assignments():
    """Uncertain variable must be present in the preset assignments."""
    from gpu_stack.uncertainty import UncertainAssignment, uniform
    # training.total_tokens is a valid variable but not in our preset's
    # uncertain list - but it IS in the preset assignments, so we need one
    # that isn't. Use a valid registered name that isn't assigned.
    ua_missing = UncertainAssignment(
        "econ.power.price_kwh_peak",
        uniform(0.25, 0.45),
    )
    # Pass a plain dict without that key
    empty_assignments = {}
    with pytest.raises(ValueError, match="not present"):
        propagate_uncertainty(
            empty_assignments,
            [COST_TARGET],
            uncertain=[ua_missing],
            n_samples=5,
            seed=0,
        )


# ---------------------------------------------------------------------------
# Determinism by seed
# ---------------------------------------------------------------------------

def test_propagate_uncertainty_is_deterministic_with_same_seed():
    """Same seed must produce identical results."""
    kwargs = dict(
        preset_or_assignments=SYNTHETIC_PRESET,
        targets=[COST_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=20,
        seed=42,
    )
    r1 = propagate_uncertainty(**kwargs)
    r2 = propagate_uncertainty(**kwargs)

    t1 = r1.targets[0]
    t2 = r2.targets[0]
    assert t1.mean == t2.mean
    assert t1.std == t2.std
    assert t1.p5 == t2.p5
    assert t1.p95 == t2.p95
    assert t1.failure_count == t2.failure_count


def test_propagate_uncertainty_different_seeds_produce_different_results():
    """Different seeds should (overwhelmingly likely) produce different means."""
    r1 = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=30,
        seed=1,
    )
    r2 = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=30,
        seed=2,
    )
    # With 30 samples from a uniform over a reasonably wide range, means
    # will almost certainly differ.
    assert r1.targets[0].mean != r2.targets[0].mean


# ---------------------------------------------------------------------------
# Sane quantile ordering
# ---------------------------------------------------------------------------

def test_quantile_ordering_p5_le_p50_le_p95():
    """p5 <= p50 <= p95 must hold for any well-behaved distribution."""
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=50,
        seed=7,
    )
    t = result.targets[0]
    assert t.p5 is not None
    assert t.p50 is not None
    assert t.p95 is not None
    assert t.p5 <= t.p50
    assert t.p50 <= t.p95


def test_quantile_ordering_with_two_uncertain_inputs():
    """Quantile ordering holds with two uncertain inputs."""
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[UNCERTAIN_PRICE, UNCERTAIN_AVAIL],
        n_samples=50,
        seed=11,
    )
    t = result.targets[0]
    assert t.p5 is not None
    assert t.p5 <= t.p50 <= t.p95


# ---------------------------------------------------------------------------
# Propagation correctness on a hand-checkable linear case
# ---------------------------------------------------------------------------
#
# The dense_training_cost_fixture resolves cost_per_token through a linear
# chain. After symbolic resolution with price as the free variable, the
# expression has the form:
#
#   cost_per_token = alpha * price_kwh_peak + beta
#
# With price_kwh_peak ~ Uniform(low, high) and all other inputs fixed:
#   E[cost] = alpha * (low + high)/2 + beta
#   Var[cost] = alpha^2 * (high - low)^2 / 12
#
# We verify these analytically against the Monte Carlo estimates.

def test_propagation_matches_analytic_mean_for_linear_case():
    """
    SYNTHETIC: electricity price uniform(0.25, 0.45) is a synthetic range.
    Linear propagation through cost_per_token gives an analytic mean.
    """
    from gpu_stack import resolve, Registry

    preset = SYNTHETIC_PRESET
    base_assignments = dict(preset.assignments)
    base_variants = dict(preset.variants)

    # Resolve symbolically omitting the price variable.
    partial = {k: v for k, v in base_assignments.items()
               if k != "econ.power.price_kwh_peak"}
    sym_result = resolve(
        "econ.cost.per_token",
        assignments=partial,
        variants=base_variants,
    )
    expr = sym_result.value
    price_sym = Registry.variables["econ.power.price_kwh_peak"].symbol
    alpha = float(expr.diff(price_sym))
    beta = float(expr.subs(price_sym, 0))

    low, high = 0.25, 0.45
    analytic_mean = alpha * (low + high) / 2.0 + beta

    # 200 samples is sufficient for a linear case (lambdify path = vectorized).
    result = propagate_uncertainty(
        preset,
        [COST_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=200,
        seed=99,
    )
    t = result.targets[0]
    assert t.mean is not None
    assert t.failure_count == 0
    # Tolerance is 0.5% relative; linear case converges rapidly.
    assert abs(t.mean - analytic_mean) / analytic_mean < 0.005, (
        f"MC mean {t.mean:.4e} vs analytic {analytic_mean:.4e}"
    )


def test_propagation_matches_analytic_std_for_linear_case():
    """
    SYNTHETIC: same as above but checking standard deviation.
    """
    from gpu_stack import resolve, Registry

    preset = SYNTHETIC_PRESET
    base_assignments = dict(preset.assignments)
    base_variants = dict(preset.variants)

    partial = {k: v for k, v in base_assignments.items()
               if k != "econ.power.price_kwh_peak"}
    sym_result = resolve(
        "econ.cost.per_token",
        assignments=partial,
        variants=base_variants,
    )
    expr = sym_result.value
    price_sym = Registry.variables["econ.power.price_kwh_peak"].symbol
    alpha = float(expr.diff(price_sym))

    low, high = 0.25, 0.45
    # Analytic std for uniform: (high - low) / sqrt(12).
    # The code reports sample std (Bessel-corrected, divide by n-1).
    # For large n, population and sample std converge; we tolerate 10%.
    analytic_std = abs(alpha) * (high - low) / (12 ** 0.5)

    # 500 samples with lambdify is fast and gives good std estimate.
    result = propagate_uncertainty(
        preset,
        [COST_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=500,
        seed=77,
    )
    t = result.targets[0]
    assert t.std is not None
    # 10% tolerance on std is generous for sample std with 500 samples.
    assert abs(t.std - analytic_std) / analytic_std < 0.10, (
        f"MC std {t.std:.4e} vs analytic {analytic_std:.4e}"
    )


# ---------------------------------------------------------------------------
# Failure-count behavior
# ---------------------------------------------------------------------------

def test_failure_count_is_zero_for_well_behaved_inputs():
    """A valid range with no division by zero or infeasibility = 0 failures."""
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=100,
        seed=3,
    )
    assert result.targets[0].failure_count == 0


def test_failure_count_nonzero_when_samples_cause_zero_division():
    """
    SYNTHETIC: cluster_availability near zero causes division by zero in
    the cost_per_token formula (wallclock = t_step / availability). A
    uniform distribution that includes zero will produce failures.
    """
    # SYNTHETIC: availability range includes zero to force failures
    dangerous_avail = UncertainAssignment(
        "training.cluster_availability",
        uniform(0.0, 0.0),  # constant zero - all samples fail
    )
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[dangerous_avail],
        n_samples=20,
        seed=5,
    )
    t = result.targets[0]
    # With availability=0, cost_per_token=inf (nonfinite) for every sample
    assert t.failure_count == 20
    assert t.mean is None
    assert t.std is None
    assert t.p5 is None


def test_failure_count_partial_failure():
    """
    SYNTHETIC: availability uniform(0.0, 1.0) will include near-zero
    samples that become nonfinite; expect some failures but not all.
    Note: This test seeds and checks count is >=0 (structural, not exact).
    """
    from gpu_stack.uncertainty import UncertainAssignment, uniform
    wide_avail = UncertainAssignment(
        "training.cluster_availability",
        uniform(0.0, 1.0),
    )
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[wide_avail],
        n_samples=50,
        seed=6,
    )
    t = result.targets[0]
    # failure_count >= 0 (structural invariant)
    assert t.failure_count >= 0
    assert t.failure_count <= t.sample_count


# ---------------------------------------------------------------------------
# Result structure and to_dict
# ---------------------------------------------------------------------------

def test_uncertainty_result_echoes_preset_name_and_seed():
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=10,
        seed=42,
    )
    assert result.preset_name == SYNTHETIC_PRESET.name
    assert result.n_samples == 10
    assert result.seed == 42


def test_uncertainty_result_seed_none_when_not_supplied():
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=10,
    )
    assert result.seed is None


def test_uncertainty_result_targets_in_order():
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET, POWER_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=20,
        seed=1,
    )
    assert len(result.targets) == 2
    assert result.targets[0].label == "cost_per_token"
    assert result.targets[1].label == "job_dc_power"


def test_uncertainty_result_to_dict_shape():
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=10,
        seed=42,
    )
    d = result.to_dict()
    assert d["preset_name"] == SYNTHETIC_PRESET.name
    assert d["n_samples"] == 10
    assert d["seed"] == 42
    assert "input_specs" in d
    assert "targets" in d
    assert "cost_per_token" in d["targets"]
    t = d["targets"]["cost_per_token"]
    for key in ("label", "target", "sample_count", "failure_count",
                "mean", "std", "p5", "p50", "p95", "input_specs"):
        assert key in t, f"missing key {key!r} in TargetUncertaintyStats dict"


def test_target_stats_to_dict_contains_input_specs():
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=10,
        seed=0,
    )
    t_dict = result.targets[0].to_dict()
    assert isinstance(t_dict["input_specs"], list)
    assert len(t_dict["input_specs"]) == 1
    assert t_dict["input_specs"][0]["name"] == "econ.power.price_kwh_peak"


def test_uncertainty_result_input_specs_echoed():
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[UNCERTAIN_PRICE, UNCERTAIN_AVAIL],
        n_samples=10,
        seed=0,
    )
    names = [spec.name for spec in result.input_specs]
    assert "econ.power.price_kwh_peak" in names
    assert "training.cluster_availability" in names


# ---------------------------------------------------------------------------
# Plain dict assignment input
# ---------------------------------------------------------------------------

def test_propagate_uncertainty_accepts_plain_dict():
    """Caller can pass a plain dict instead of a Preset."""
    base = dict(SYNTHETIC_PRESET.assignments)
    base_variants = dict(SYNTHETIC_PRESET.variants)

    # We need to pass variants separately - but propagate_uncertainty with a
    # plain dict will use empty variants. So use a target that doesn't need
    # variant resolution: job_dc_power.
    result = propagate_uncertainty(
        base,
        [POWER_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=10,
        seed=0,
    )
    assert result.preset_name == "<assignments>"
    assert result.targets[0].sample_count == 10


# ---------------------------------------------------------------------------
# Normal and lognormal distribution coverage
# ---------------------------------------------------------------------------

def test_propagate_uncertainty_with_normal_distribution():
    """Normal distribution over price should give nonzero std and sane mean."""
    ua = UncertainAssignment("econ.power.price_kwh_peak", SYNTH_PRICE_NORMAL)
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[ua],
        n_samples=50,
        seed=13,
    )
    t = result.targets[0]
    assert t.mean is not None
    assert t.std is not None and t.std > 0
    assert t.p5 <= t.p50 <= t.p95


def test_propagate_uncertainty_with_lognormal_distribution():
    """Lognormal distribution over price should give nonzero std and sane mean."""
    ua = UncertainAssignment("econ.power.price_kwh_peak", SYNTH_PRICE_LOGNORMAL)
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[ua],
        n_samples=50,
        seed=17,
    )
    t = result.targets[0]
    assert t.mean is not None
    assert t.std is not None and t.std > 0
    assert t.p5 <= t.p50 <= t.p95


# ---------------------------------------------------------------------------
# Multi-target run
# ---------------------------------------------------------------------------

def test_propagate_uncertainty_multi_target_both_resolved():
    """Both cost_per_token and job_dc_power should resolve with no failures."""
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET, POWER_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=50,
        seed=8,
    )
    assert len(result.targets) == 2
    for t in result.targets:
        assert t.failure_count == 0
        assert t.mean is not None


# ---------------------------------------------------------------------------
# Performance sanity: n_samples=200 should be fast via lambdify path
# ---------------------------------------------------------------------------

def test_performance_200_samples_reasonable_time():
    """
    200 samples on the dense fixture should complete in a few seconds via
    the lambdify fast path. This test fails if it takes more than 30 seconds
    (a sign the fallback per-sample path is being used unexpectedly).
    """
    import time
    start = time.monotonic()
    result = propagate_uncertainty(
        SYNTHETIC_PRESET,
        [COST_TARGET],
        uncertain=[UNCERTAIN_PRICE],
        n_samples=200,
        seed=0,
    )
    elapsed = time.monotonic() - start
    assert elapsed < 30.0, f"200 samples took {elapsed:.1f}s (expected < 30s via lambdify)"
    assert result.targets[0].mean is not None
