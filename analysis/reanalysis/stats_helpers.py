"""Small, dependency-light paired-sample statistics used by reanalyze.py.

Every function is deterministic. Randomness only enters through explicit seeds.
"""

from __future__ import annotations

import itertools
import math
import zlib
from typing import Any, Sequence

import numpy as np
from scipy import stats

LEVEL = 0.90
DRAWS = 10_000


def stable_seed(base: int, name: str) -> int:
    """Seed derived from a base seed and a metric name (stable across runs)."""
    return int(base) + (zlib.crc32(name.encode("utf-8")) & 0xFFFFFF)


def bootstrap_median_original(
    values: Sequence[float], *, draws: int, seed: int, level: float
) -> dict[str, float]:
    """Exact copy of the method the project used (percentile bootstrap of the
    median, numpy default_rng, integer resampling, np.quantile)."""
    array = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(draws, len(array)))
    medians = np.median(array[indices], axis=1)
    alpha = (1.0 - level) * 0.5
    return {
        "median": float(np.median(array)),
        "lower": float(np.quantile(medians, alpha)),
        "upper": float(np.quantile(medians, 1.0 - alpha)),
    }


def bootstrap_mean(
    values: Sequence[float], *, draws: int, seed: int, level: float
) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(draws, len(array)))
    means = array[indices].mean(axis=1)
    alpha = (1.0 - level) * 0.5
    return {
        "lower": float(np.quantile(means, alpha)),
        "upper": float(np.quantile(means, 1.0 - alpha)),
    }


def t_interval(values: Sequence[float], level: float = LEVEL) -> dict[str, float] | None:
    array = np.asarray(values, dtype=np.float64)
    n = len(array)
    if n < 2:
        return None
    sd = float(array.std(ddof=1))
    se = sd / math.sqrt(n)
    crit = float(stats.t.ppf(0.5 + level / 2.0, n - 1))
    mean = float(array.mean())
    return {
        "mean": mean,
        "se": se,
        "t_crit": crit,
        "lower": mean - crit * se,
        "upper": mean + crit * se,
    }


def sign_test_exact(values: Sequence[float], null: float) -> dict[str, Any]:
    d = np.asarray(values, dtype=np.float64) - null
    nonzero = d[d != 0.0]
    m = len(nonzero)
    if m == 0:
        return {"n_nonzero": 0, "n_positive": 0, "p_two_sided": None}
    k = int((nonzero > 0).sum())
    p = min(1.0, 2.0 * float(stats.binom.cdf(min(k, m - k), m, 0.5)))
    return {"n_nonzero": m, "n_positive": k, "p_two_sided": p}


def wilcoxon_exact(values: Sequence[float], null: float) -> dict[str, Any]:
    d = np.asarray(values, dtype=np.float64) - null
    d = d[d != 0.0]
    if len(d) < 1:
        return {"p_two_sided": None, "statistic": None, "n_used": 0}
    try:
        res = stats.wilcoxon(d, method="auto", alternative="two-sided")
        return {
            "p_two_sided": float(res.pvalue),
            "statistic": float(res.statistic),
            "n_used": int(len(d)),
        }
    except Exception as error:  # pragma: no cover - defensive
        return {"p_two_sided": None, "statistic": None, "n_used": int(len(d)), "error": str(error)}


def sign_flip_permutation(
    values: Sequence[float], null: float, *, seed: int, max_exact: int = 20
) -> dict[str, Any]:
    """Two-sided sign-flip permutation test on the mean of (x - null)."""
    d = np.asarray(values, dtype=np.float64) - null
    n = len(d)
    observed = abs(float(d.mean()))
    if n <= max_exact:
        signs = np.array(list(itertools.product((-1.0, 1.0), repeat=n)))
        means = np.abs((signs * d).mean(axis=1))
        p = float((means >= observed - 1e-15).mean())
        return {"p_two_sided": p, "exact": True, "n_permutations": int(len(means))}
    rng = np.random.default_rng(seed)
    signs = rng.choice((-1.0, 1.0), size=(100_000, n))
    means = np.abs((signs * d).mean(axis=1))
    return {"p_two_sided": float((means >= observed).mean()), "exact": False, "n_permutations": 100_000}


def order_statistic_median_interval(
    values: Sequence[float], level: float = LEVEL
) -> dict[str, Any]:
    """Distribution-free interval [x_(k), x_(n+1-k)] for the median. Picks the
    largest k whose exact binomial coverage is at least `level`. Returns None
    bounds when n is too small to reach that coverage."""
    x = np.sort(np.asarray(values, dtype=np.float64))
    n = len(x)
    best = None
    for k in range(n // 2, 0, -1):
        coverage = 1.0 - 2.0 * float(stats.binom.cdf(k - 1, n, 0.5))
        if coverage >= level:
            best = (k, coverage)
            break
    if best is None:
        return {"lower": None, "upper": None, "coverage": None, "rank_k": None}
    k, coverage = best
    return {
        "lower": float(x[k - 1]),
        "upper": float(x[n - k]),
        "coverage": coverage,
        "rank_k": k,
    }


def describe(
    values: Sequence[float],
    *,
    name: str,
    null: float = 0.0,
    ratio: bool = False,
    orig_seed: int | None = None,
    stored: dict[str, Any] | None = None,
    project_seed: int = 20261001,
    level: float = LEVEL,
    draws: int = DRAWS,
    note: str | None = None,
) -> dict[str, Any]:
    """Paired-effect summary with several interval/test methods.

    `values` are per-pair effects. `null` is the no-effect value (0 for
    differences, 1 for ratios). `orig_seed`/`stored` reproduce the original
    percentile-bootstrap interval for comparison.
    """
    x = np.asarray([float(v) for v in values], dtype=np.float64)
    n = int(len(x))
    out: dict[str, Any] = {"name": name, "n": n, "values": [float(v) for v in x], "null": null}
    if note:
        out["note"] = note
    if n == 0:
        return out
    out["mean"] = float(x.mean())
    out["median"] = float(np.median(x))
    out["sd"] = float(x.std(ddof=1)) if n > 1 else None
    out["min"] = float(x.min())
    out["max"] = float(x.max())
    out["level"] = level
    out["t_interval_mean"] = t_interval(x, level)
    seed = stable_seed(project_seed, name)
    out["bootstrap_median_project_seed"] = {
        **bootstrap_median_original(x, draws=draws, seed=seed, level=level),
        "seed": seed,
    }
    out["bootstrap_mean_project_seed"] = {
        **bootstrap_mean(x, draws=draws, seed=seed + 1, level=level),
        "seed": seed + 1,
    }
    if orig_seed is not None:
        orig = bootstrap_median_original(x, draws=draws, seed=orig_seed, level=level)
        orig["seed"] = orig_seed
        if stored is not None and stored.get("lower_bound") is not None:
            diffs = [
                abs(orig["lower"] - float(stored["lower_bound"])),
                abs(orig["upper"] - float(stored["upper_bound"])),
                abs(orig["median"] - float(stored["median"])),
            ]
            orig["stored_lower"] = float(stored["lower_bound"])
            orig["stored_upper"] = float(stored["upper_bound"])
            orig["stored_median"] = float(stored["median"])
            orig["max_abs_diff_vs_stored"] = float(max(diffs))
            scale = max(1e-300, max(abs(float(stored["median"])), abs(float(stored["upper_bound"])), abs(float(stored["lower_bound"]))))
            orig["reproduces_stored"] = bool(max(diffs) <= 1e-9 * scale + 1e-15)
        out["bootstrap_median_original_method"] = orig
    out["sign_test_exact"] = sign_test_exact(x, null)
    out["wilcoxon_exact"] = wilcoxon_exact(x, null)
    out["sign_flip_permutation_mean"] = sign_flip_permutation(x, null, seed=seed + 2)
    out["order_statistic_median_interval"] = order_statistic_median_interval(x, level)
    if ratio and np.all(x > 0):
        logs = np.log(x)
        ti = t_interval(logs, level)
        if ti is not None:
            out["geometric_mean_ratio"] = {
                "estimate": float(math.exp(ti["mean"])),
                "lower": float(math.exp(ti["lower"])),
                "upper": float(math.exp(ti["upper"])),
                "log_sd": float(logs.std(ddof=1)),
                "note": "t-interval on log ratios, exponentiated",
            }
    return out


def power_to_pass_upper_bound(
    log_sd: float,
    true_ratio: float,
    bar: float,
    n: int,
    *,
    seed: int,
    sims: int = 20_000,
    level: float = LEVEL,
) -> float:
    """P(t-based upper bound of the geometric-mean ratio <= bar) when the true
    ratio is `true_ratio` and per-pair log-ratios are N(log true, log_sd)."""
    rng = np.random.default_rng(seed)
    data = rng.normal(math.log(true_ratio), log_sd, size=(sims, n))
    mean = data.mean(axis=1)
    sd = data.std(axis=1, ddof=1)
    crit = float(stats.t.ppf(0.5 + level / 2.0, n - 1))
    upper = np.exp(mean + crit * sd / math.sqrt(n))
    return float((upper <= bar).mean())
