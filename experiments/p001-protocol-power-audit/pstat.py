"""Small statistics helpers for the P001 power audit (numpy/scipy only)."""
from __future__ import annotations

import math

import numpy as np
from scipy import optimize, stats

Z95 = float(stats.norm.ppf(0.95))


def wilson(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    """Two-sided Wilson interval for a Monte Carlo rate."""
    if n == 0:
        return (0.0, 1.0)
    z = float(stats.norm.ppf(0.5 + conf / 2))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"p": k / n, "mc_ci95": [lo, hi], "n_sim": n}


# ---- exact binomial bounds -------------------------------------------------
def cp_lower(k: int, n: int, alpha: float) -> float:
    """Clopper-Pearson lower bound for success probability, level alpha in the tail."""
    return 0.0 if k == 0 else float(stats.beta.ppf(alpha, k, n - k + 1))


def cp_upper(k: int, n: int, alpha: float) -> float:
    return 1.0 if k == n else float(stats.beta.ppf(1 - alpha, k + 1, n - k))


def wilson_lower_1s(k: int, n: int, alpha: float) -> float:
    z = float(stats.norm.ppf(1 - alpha))
    p = k / n
    d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def max_failures_for_lower(n: int, target: float, alpha: float, method: str = "cp") -> int:
    """Largest failure count f whose lower bound on success prob is still >= target; -1 if none."""
    fn = cp_lower if method == "cp" else wilson_lower_1s
    best = -1
    for f in range(0, n + 1):
        if fn(n - f, n, alpha) >= target:
            best = f
        else:
            break
    return best


def max_failures_for_upper(n: int, target: float, alpha: float) -> int:
    """Largest failure count f whose upper bound on failure prob is <= target; -1 if none."""
    best = -1
    for f in range(0, n + 1):
        if cp_upper(f, n, alpha) <= target:
            best = f
        else:
            break
    return best


def n_min_for_lower(target: float, failures: int, alpha: float, method: str = "cp") -> int:
    """Smallest n such that `failures` failures still give lower bound >= target."""
    lo, hi = max(failures + 1, 2), 10
    fn = cp_lower if method == "cp" else wilson_lower_1s
    while fn(hi - failures, hi, alpha) < target:
        hi *= 2
        if hi > 10**8:
            return -1
    lo = max(lo, hi // 2)
    while lo < hi:
        mid = (lo + hi) // 2
        if fn(mid - failures, mid, alpha) >= target:
            hi = mid
        else:
            lo = mid + 1
    return lo


def binom_pass_prob(n: int, fail_rate: float, f_max: int) -> float:
    if f_max < 0:
        return 0.0
    return float(stats.binom.cdf(f_max, n, fail_rate))


def solve_fail_rate_for_power(n: int, f_max: int, power: float = 0.8) -> float:
    """Failure rate at which P(failures <= f_max) = power."""
    if f_max < 0:
        return float("nan")
    return float(optimize.brentq(lambda r: stats.binom.cdf(f_max, n, r) - power, 1e-12, 0.5))


# ---- percentile bootstrap of the median (the rule used by E001/E002 code) ---
def boot_index(n: int, draws: int, rng: np.random.Generator) -> np.ndarray:
    return rng.integers(0, n, size=(draws, n))


def boot_median_bounds(x: np.ndarray, idx: np.ndarray, conf: float = 0.9) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """x: (S, n). Returns lower, upper, median per row, same rule as lc1._bootstrap_median_interval."""
    alpha = (1 - conf) / 2
    meds = np.median(x[:, idx], axis=2)  # (S, draws)
    lo = np.quantile(meds, alpha, axis=1)
    hi = np.quantile(meds, 1 - alpha, axis=1)
    return lo, hi, np.median(x, axis=1)


def kendall_rows(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Kendall tau-a for each row of (S, m) arrays (continuous data, no ties)."""
    m = a.shape[1]
    out = np.empty(a.shape[0])
    step = max(1, 4_000_000 // (m * m))
    for i in range(0, a.shape[0], step):
        x, y = a[i:i + step], b[i:i + step]
        sa = np.sign(x[:, :, None] - x[:, None, :])
        sb = np.sign(y[:, :, None] - y[:, None, :])
        out[i:i + step] = (sa * sb).sum(axis=(1, 2)) / (m * (m - 1))
    return out


def nct_power_lower(theta: float, c: float, se: float, df: float, alpha: float = 0.05) -> float:
    """P(lower (1-alpha) t-bound >= c) when the estimate has true mean theta and se `se`."""
    tcrit = float(stats.t.ppf(1 - alpha, df))
    return float(1 - stats.nct.cdf(tcrit, df, (theta - c) / se))


def nct_power_upper(theta: float, c: float, se: float, df: float, alpha: float = 0.05) -> float:
    """P(upper (1-alpha) t-bound <= c)."""
    tcrit = float(stats.t.ppf(1 - alpha, df))
    return float(stats.nct.cdf(-tcrit, df, (theta - c) / se))


def solve_theta(fn, lo: float, hi: float, target: float = 0.8) -> float:
    """Root of fn(theta) = target for monotone fn; nan if not bracketed."""
    try:
        return float(optimize.brentq(lambda t: fn(t) - target, lo, hi))
    except ValueError:
        return float("nan")
