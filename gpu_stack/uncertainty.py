"""
gpu_stack.uncertainty
=====================

Monte Carlo uncertainty propagation over the existing symbolic resolver.

The module never invents numbers. Every distribution must be supplied
explicitly by the caller; there are no default uncertainties.

Public API
----------
UncertainAssignment(name, distribution)
    Pairs a registered variable name with a distribution object.

uniform(low, high)
normal(mean, std)
lognormal(mu, sigma)
    Distribution constructors. Each validates sign assumptions of the target
    variable when UncertainAssignment is constructed.

propagate_uncertainty(preset_or_assignments, targets, uncertain, n_samples, seed)
    Monte Carlo driver. Resolves each target over n_samples draws, collecting
    per-target statistics.

UncertaintyResult, TargetUncertaintyStats
    Structured result artifacts with to_dict() for JSON-friendly output.

Performance note
----------------
When the symbolic resolver can form a closed-form expression over the uncertain
inputs (i.e., the expression remains symbolic after omitting those inputs), the
driver lambdifies that expression and vectorises the sample evaluation over all
n_samples at once via SymPy's lambdify. This reduces 200-sample evaluation from
~14 s (per-sample resolve) to under 1 ms. When lambdification is not possible
(the expression would require re-resolving a variant branching or similar), the
driver falls back to per-sample resolution through the existing public
resolve() path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import sympy as sp

from .core.presets import Preset
from .core.registry import Registry
from .core.resolver import ResolverError, resolve


# ---------------------------------------------------------------------------
# Distribution types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _UniformDist:
    """Uniform distribution on [low, high]."""

    kind: str = field(default="uniform", init=False)
    low: float
    high: float

    def __post_init__(self) -> None:
        if self.low > self.high:
            raise ValueError(
                f"uniform: low ({self.low}) must be <= high ({self.high})"
            )

    def has_mass_at_nonpositive(self) -> bool:
        return self.low <= 0.0

    def has_mass_at_negative(self) -> bool:
        return self.low < 0.0

    def to_dict(self) -> Dict[str, object]:
        return {"kind": self.kind, "low": self.low, "high": self.high}


@dataclass(frozen=True)
class _NormalDist:
    """Normal (Gaussian) distribution."""

    kind: str = field(default="normal", init=False)
    mean: float
    std: float

    def __post_init__(self) -> None:
        if self.std <= 0.0:
            raise ValueError(
                f"normal: std ({self.std}) must be > 0"
            )

    def has_mass_at_nonpositive(self) -> bool:
        # Normal has infinite support; always has some mass at nonpositive.
        return True

    def has_mass_at_negative(self) -> bool:
        return True

    def to_dict(self) -> Dict[str, object]:
        return {"kind": self.kind, "mean": self.mean, "std": self.std}


@dataclass(frozen=True)
class _LognormalDist:
    """
    Log-normal distribution: if X ~ Lognormal(mu, sigma), then
    log(X) ~ Normal(mu, sigma). Support is strictly (0, +inf).
    """

    kind: str = field(default="lognormal", init=False)
    mu: float
    sigma: float

    def __post_init__(self) -> None:
        if self.sigma <= 0.0:
            raise ValueError(
                f"lognormal: sigma ({self.sigma}) must be > 0"
            )

    def has_mass_at_nonpositive(self) -> bool:
        return False

    def has_mass_at_negative(self) -> bool:
        return False

    def to_dict(self) -> Dict[str, object]:
        return {"kind": self.kind, "mu": self.mu, "sigma": self.sigma}


Distribution = Union[_UniformDist, _NormalDist, _LognormalDist]


def uniform(low: float, high: float) -> _UniformDist:
    """Uniform distribution on [low, high]."""
    return _UniformDist(low=low, high=high)


def normal(mean: float, std: float) -> _NormalDist:
    """Normal distribution with given mean and standard deviation."""
    return _NormalDist(mean=mean, std=std)


def lognormal(mu: float, sigma: float) -> _LognormalDist:
    """
    Log-normal distribution parameterised by the mean (mu) and standard
    deviation (sigma) of the underlying normal in log-space.
    """
    return _LognormalDist(mu=mu, sigma=sigma)


# ---------------------------------------------------------------------------
# UncertainAssignment
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UncertainAssignment:
    """
    Pairs a registered variable name with a distribution.

    Validation
    ----------
    If the target variable has a ``positive=True`` SymPy assumption, any
    distribution that places mass at non-positive values is rejected. If the
    variable has a ``nonnegative=True`` assumption, distributions with mass at
    strictly negative values are rejected.
    """

    name: str
    distribution: Distribution

    def __post_init__(self) -> None:
        var = Registry.variables.get(self.name)
        if var is None:
            raise ValueError(
                f"UncertainAssignment: unknown variable name {self.name!r}"
            )
        sym = var.symbol
        if sym.is_positive:
            if self.distribution.has_mass_at_nonpositive():
                raise ValueError(
                    f"UncertainAssignment({self.name!r}): variable has "
                    f"positive=True assumption but distribution "
                    f"{self.distribution.to_dict()} has mass at non-positive "
                    "values. Use lognormal or a uniform distribution with "
                    "low > 0."
                )
        elif sym.is_nonnegative:
            if self.distribution.has_mass_at_negative():
                raise ValueError(
                    f"UncertainAssignment({self.name!r}): variable has "
                    f"nonnegative=True assumption but distribution "
                    f"{self.distribution.to_dict()} has mass at negative "
                    "values. Use lognormal or a uniform distribution with "
                    "low >= 0."
                )

    def to_dict(self) -> Dict[str, object]:
        return {"name": self.name, "distribution": self.distribution.to_dict()}


# ---------------------------------------------------------------------------
# Result artifacts
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TargetUncertaintyStats:
    """
    Per-target statistics from a Monte Carlo propagation run.

    Fields
    ------
    label       : caller-supplied label for the target.
    target      : registered variable name (string form).
    sample_count: number of samples drawn (equals n_samples).
    failure_count: samples where resolution errored or returned a
                  non-finite value (div-by-zero, complex infinity, etc.).
    mean        : sample mean of the finite resolved values.
    std         : sample standard deviation.
    p5          : 5th percentile.
    p50         : 50th percentile (median).
    p95         : 95th percentile.
    input_specs : the UncertainAssignment inputs echoed back.
    """

    label: str
    target: str
    sample_count: int
    failure_count: int
    mean: Optional[float]
    std: Optional[float]
    p5: Optional[float]
    p50: Optional[float]
    p95: Optional[float]
    input_specs: Tuple[UncertainAssignment, ...]

    def to_dict(self) -> Dict[str, object]:
        return {
            "label": self.label,
            "target": self.target,
            "sample_count": self.sample_count,
            "failure_count": self.failure_count,
            "mean": self.mean,
            "std": self.std,
            "p5": self.p5,
            "p50": self.p50,
            "p95": self.p95,
            "input_specs": [spec.to_dict() for spec in self.input_specs],
        }


@dataclass(frozen=True)
class UncertaintyResult:
    """
    Full result of a Monte Carlo propagation run.

    Fields
    ------
    preset_name  : name of the preset used.
    n_samples    : number of samples requested.
    seed         : RNG seed used (None if no seed was supplied).
    targets      : per-target stats, in the same order as the targets arg.
    input_specs  : all UncertainAssignment inputs echoed back.
    """

    preset_name: str
    n_samples: int
    seed: Optional[int]
    targets: Tuple[TargetUncertaintyStats, ...]
    input_specs: Tuple[UncertainAssignment, ...]

    def to_dict(self) -> Dict[str, object]:
        return {
            "preset_name": self.preset_name,
            "n_samples": self.n_samples,
            "seed": self.seed,
            "input_specs": [spec.to_dict() for spec in self.input_specs],
            "targets": {t.label: t.to_dict() for t in self.targets},
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _draw_samples(
    dist: Distribution,
    n: int,
    rng: Any,
) -> List[float]:
    """Draw n samples from dist using the provided numpy rng."""
    if isinstance(dist, _UniformDist):
        return list(rng.uniform(dist.low, dist.high, n))
    if isinstance(dist, _NormalDist):
        return list(rng.normal(dist.mean, dist.std, n))
    if isinstance(dist, _LognormalDist):
        return list(rng.lognormal(dist.mu, dist.sigma, n))
    raise TypeError(f"unsupported distribution type: {type(dist)}")


def _sympy_value_to_float(v: object) -> Optional[float]:
    """Convert a SymPy expression to float, returning None on failure."""
    if hasattr(v, "free_symbols") and v.free_symbols:
        return None
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _percentile_of_sorted(sorted_vals: List[float], q: float) -> float:
    """
    Linear interpolation percentile from a sorted list. q in [0.0, 1.0].
    """
    n = len(sorted_vals)
    if n == 0:
        return float("nan")
    idx = q * (n - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= n:
        return sorted_vals[-1]
    frac = idx - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


def _compute_stats(
    label: str,
    target: str,
    samples: List[Optional[float]],
    input_specs: Tuple[UncertainAssignment, ...],
) -> TargetUncertaintyStats:
    n_total = len(samples)
    finite = [s for s in samples if s is not None]
    n_fail = n_total - len(finite)

    if not finite:
        return TargetUncertaintyStats(
            label=label,
            target=target,
            sample_count=n_total,
            failure_count=n_fail,
            mean=None,
            std=None,
            p5=None,
            p50=None,
            p95=None,
            input_specs=input_specs,
        )

    n = len(finite)
    mean = sum(finite) / n
    # Sample standard deviation (Bessel-corrected, divide by n-1).
    # Returns 0 for n==1 since no spread can be estimated from one sample.
    variance = sum((x - mean) ** 2 for x in finite) / (n - 1) if n > 1 else 0.0
    std = math.sqrt(variance)
    sorted_finite = sorted(finite)

    return TargetUncertaintyStats(
        label=label,
        target=target,
        sample_count=n_total,
        failure_count=n_fail,
        mean=mean,
        std=std,
        p5=_percentile_of_sorted(sorted_finite, 0.05),
        p50=_percentile_of_sorted(sorted_finite, 0.50),
        p95=_percentile_of_sorted(sorted_finite, 0.95),
        input_specs=input_specs,
    )


# ---------------------------------------------------------------------------
# Fast path: symbolic resolve + lambdify
# ---------------------------------------------------------------------------

def _try_lambdify_path(
    uncertain_names: Sequence[str],
    base_assignments: Dict[str, float],
    base_variants: Dict[str, str],
    target_name: str,
) -> Optional[Tuple[Any, List[str]]]:
    """
    Attempt to build a lambdified function for target_name with uncertain_names
    left as free symbols. Returns the callable or None if it fails.

    The callable signature is f(*sample_arrays) -> numpy array, where each
    positional argument corresponds to the sorted order of symbols that appear
    free in the resolved expression. The returned callable and a list of the
    symbol names (in that order) are returned as a 2-tuple.
    """
    partial_assignments = {
        k: v for k, v in base_assignments.items()
        if k not in uncertain_names
    }
    try:
        result = resolve(
            target_name,
            assignments=partial_assignments,
            variants=base_variants,
        )
    except ResolverError:
        return None

    expr = result.value
    free = expr.free_symbols
    if not free:
        # Fully deterministic - no uncertain inputs influence this target.
        # Still valid; lambdify will return a constant.
        ordered_syms: List[sp.Symbol] = []
    else:
        ordered_syms = sorted(free, key=str)

    # Map symbol name -> uncertain variable name
    sym_to_uncertain: Dict[str, str] = {}
    for uname in uncertain_names:
        var = Registry.variables[uname]
        sym_name = str(var.symbol)
        if var.symbol in free or sym_name in [str(s) for s in free]:
            sym_to_uncertain[str(var.symbol)] = uname

    # Check that all free symbols correspond to our uncertain inputs.
    # If there are extra free symbols (other missing inputs) we cannot
    # use the lambdify path reliably.
    for sym in ordered_syms:
        if str(sym) not in sym_to_uncertain:
            # Some other variable is also missing - lambdify is not safe.
            return None

    try:
        lam = sp.lambdify(ordered_syms, expr, modules="numpy")
    except Exception:
        return None

    return lam, [sym_to_uncertain[str(s)] for s in ordered_syms]


# ---------------------------------------------------------------------------
# Public driver
# ---------------------------------------------------------------------------

def propagate_uncertainty(
    preset_or_assignments: Union[Preset, Mapping[str, float]],
    targets: Iterable[Tuple[str, str]],
    uncertain: Sequence[UncertainAssignment],
    n_samples: int = 200,
    seed: Optional[int] = None,
) -> UncertaintyResult:
    """
    Monte Carlo uncertainty propagation over the existing resolver.

    Parameters
    ----------
    preset_or_assignments
        A Preset or a plain dict of assignments. When a Preset is supplied its
        variant selections are also forwarded to the resolver.
    targets
        Iterable of (label, target_name) pairs, same convention as
        Preset.evaluate_targets.
    uncertain
        Sequence of UncertainAssignment objects specifying which inputs have
        distributions. The caller must supply all distributions explicitly;
        no defaults are invented.
    n_samples
        Number of Monte Carlo samples. Must be >= 1.
    seed
        Integer seed for the random number generator. When provided the run is
        fully deterministic: identical seed, preset, targets, and uncertain
        inputs always produce identical results.

    Returns
    -------
    UncertaintyResult with per-target statistics and the input spec echoed back.

    Performance
    -----------
    When the resolver can form a closed-form symbolic expression over the
    uncertain inputs (which is the common case for linear economics chains),
    the driver lambdifies that expression and evaluates all samples at once.
    For targets that require per-sample resolver calls, evaluation runs at
    roughly 70 ms/sample on a typical workstation; keep n_samples small
    (<=50) for interactive use when lambdification is not available.
    """
    try:
        import numpy as _np
        _has_numpy = True
    except ImportError:
        _has_numpy = False

    if n_samples < 1:
        raise ValueError(f"n_samples must be >= 1, got {n_samples}")
    if not uncertain:
        raise ValueError("uncertain must contain at least one UncertainAssignment")

    # Build base assignments and variants.
    if isinstance(preset_or_assignments, Preset):
        base_assignments: Dict[str, float] = dict(preset_or_assignments.assignments)
        base_variants: Dict[str, str] = dict(preset_or_assignments.variants)
        preset_name = preset_or_assignments.name
    else:
        base_assignments = dict(preset_or_assignments)
        base_variants = {}
        preset_name = "<assignments>"

    # Validate that there are no duplicate uncertain variable names.
    seen_names: List[str] = []
    for ua in uncertain:
        if ua.name in seen_names:
            raise ValueError(
                f"propagate_uncertainty: uncertain variable {ua.name!r} appears "
                "more than once in the uncertain list. Each variable must appear "
                "at most once."
            )
        seen_names.append(ua.name)

    # Validate that all uncertain names are also in the base assignments.
    for ua in uncertain:
        if ua.name not in base_assignments:
            raise ValueError(
                f"propagate_uncertainty: uncertain variable {ua.name!r} is not "
                "present in the preset/assignments dict. The base assignment "
                "provides the nominal value; add it before marking it uncertain."
            )

    targets_list = list(targets)
    input_specs = tuple(uncertain)
    uncertain_names = [ua.name for ua in uncertain]

    # Build RNG. We use numpy when available (needed for lambdify path anyway).
    if _has_numpy:
        rng = _np.random.default_rng(seed)
        # Pre-draw all sample arrays, one per uncertain variable.
        sample_arrays: Dict[str, List[float]] = {
            ua.name: _draw_samples(ua.distribution, n_samples, rng)
            for ua in uncertain
        }
    else:
        import random
        _rng = random.Random(seed)

        class _PurePythonRNG:
            def uniform(self, lo, hi, n):
                return [_rng.uniform(lo, hi) for _ in range(n)]

            def normal(self, mu, sigma, n):
                return [_rng.gauss(mu, sigma) for _ in range(n)]

            def lognormal(self, mu, sigma, n):
                import math as _m
                return [_m.exp(_rng.gauss(mu, sigma)) for _ in range(n)]

        py_rng = _PurePythonRNG()
        sample_arrays = {
            ua.name: _draw_samples(ua.distribution, n_samples, py_rng)
            for ua in uncertain
        }

    target_stats_list: List[TargetUncertaintyStats] = []

    for label, target_name in targets_list:
        # -- attempt fast lambdify path --
        lambdify_result = _try_lambdify_path(
            uncertain_names,
            base_assignments,
            base_variants,
            target_name,
        )

        if lambdify_result is not None:
            lam, ordered_names = lambdify_result
            if _has_numpy:
                arrays = [
                    _np.asarray(sample_arrays[name], dtype=float)
                    for name in ordered_names
                ]
                try:
                    raw = lam(*arrays) if ordered_names else lam()
                    # raw may be a scalar if the expression is constant
                    vals = _np.asarray(raw, dtype=float).flatten()
                    if vals.size == 1:
                        vals = _np.full(n_samples, vals[0])
                    float_samples: List[Optional[float]] = [
                        v if math.isfinite(v) else None
                        for v in vals.tolist()
                    ]
                except Exception:
                    float_samples = None
            else:
                # pure-python lambdify path
                try:
                    rows = [sample_arrays[name] for name in ordered_names]
                    if rows:
                        float_samples = []
                        for i in range(n_samples):
                            args = [rows[j][i] for j in range(len(rows))]
                            v = lam(*args)
                            try:
                                fv = float(v)
                                float_samples.append(fv if math.isfinite(fv) else None)
                            except (TypeError, ValueError):
                                float_samples.append(None)
                    else:
                        v = lam()
                        try:
                            fv = float(v)
                            float_samples = [
                                fv if math.isfinite(fv) else None
                            ] * n_samples
                        except (TypeError, ValueError):
                            float_samples = [None] * n_samples
                except Exception:
                    float_samples = None

            if float_samples is not None:
                target_stats_list.append(
                    _compute_stats(label, target_name, float_samples, input_specs)
                )
                continue

        # -- fallback: per-sample resolve --
        float_samples_fallback: List[Optional[float]] = []
        for i in range(n_samples):
            overrides = {name: sample_arrays[name][i] for name in uncertain_names}
            sample_assignments = dict(base_assignments)
            sample_assignments.update(overrides)
            try:
                result = resolve(
                    target_name,
                    assignments=sample_assignments,
                    variants=base_variants,
                )
                fv = _sympy_value_to_float(result.value)
                float_samples_fallback.append(fv)
            except ResolverError:
                float_samples_fallback.append(None)

        target_stats_list.append(
            _compute_stats(
                label, target_name, float_samples_fallback, input_specs
            )
        )

    return UncertaintyResult(
        preset_name=preset_name,
        n_samples=n_samples,
        seed=seed,
        targets=tuple(target_stats_list),
        input_specs=input_specs,
    )


__all__ = [
    "UncertainAssignment",
    "UncertaintyResult",
    "TargetUncertaintyStats",
    "Distribution",
    "uniform",
    "normal",
    "lognormal",
    "propagate_uncertainty",
]
