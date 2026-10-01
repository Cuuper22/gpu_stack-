"""Planning power analysis for R001 (simulation, no study data).

Planning inputs come from the ORIGINAL E001 artifacts, which are historical and are
not R001 outcomes:
  LC3 paired adaptive-minus-fixed NLL, 6 pairs (results/equal-work-v1.json):
    0.00239 0.00600 0.00141 0.00316 0.01349 0.00352   mean 0.0050, SD 0.0044
  SC1 sync-minus-periodic_local NLL over 10 families (results/semantic-consistency-v1.json):
    mean 0.0187, SD 0.0024
Run: PYTHONPATH=<repo> $PY power.py   (writes results/power_analysis.json)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
rng = np.random.default_rng(1)
LC3_PAIRS = np.array([0.0023928, 0.0059975, 0.0014075, 0.0031559, 0.0134862, 0.0035211])


def lc3_power(n_units: int, mu: float, sd_pair: float, rho: float, delta: float, m: int = 3,
              sims: int = 40000) -> float:
    """Unit = warm seed = mean of m pairs; SD of unit mean = sd_pair*sqrt((1+(m-1)rho)/m)."""
    sd_unit = sd_pair * np.sqrt((1 + (m - 1) * rho) / m)
    x = rng.normal(mu, sd_unit, size=(sims, n_units))
    m = x.mean(1)
    se = x.std(1, ddof=1) / np.sqrt(n_units)
    bound = m + stats.t.ppf(0.95, n_units - 1) * se
    return float((bound <= delta).mean())


def q2_rates(n_units: int, f_true: float, adv: float = 0.0187, sd_unit: float = 0.0017, sims: int = 20000):
    """Per-seed explained fraction f = 1 - gap/adv; 90% t-interval over seeds."""
    a = rng.normal(adv, sd_unit, size=(sims, n_units))
    gap = rng.normal((1 - f_true) * adv, sd_unit, size=(sims, n_units))
    f = 1 - gap / a
    m = f.mean(1)
    se = f.std(1, ddof=1) / np.sqrt(n_units)
    t = stats.t.ppf(0.95, n_units - 1)
    return float(((m - t * se) >= 0.75).mean()), float(((m + t * se) <= 0.25).mean())


def main() -> None:
    out: dict = {"inputs": {"lc3_pair_mean": float(LC3_PAIRS.mean()), "lc3_pair_sd": float(LC3_PAIRS.std(ddof=1)),
                            "n_original_pairs": 6}, "lc3": [], "q2": []}
    print("Q1 power: P(one-sided 95% t upper bound of mean paired diff <= margin)")
    print("margin  mu     sd_pair rho  | n_units: 4     6     8     10    12    16")
    for delta in (0.010, 0.006):
        for mu in (0.0, 0.003, 0.005, 0.0075):
            for sd in (0.0044, 0.006, 0.008):
                for rho in (0.0, 0.5):
                    row = {n: lc3_power(n, mu, sd, rho, delta) for n in (4, 6, 8, 10, 12, 16)}
                    out["lc3"].append({"margin": delta, "true_mean_diff": mu, "sd_pair": sd, "rho": rho,
                                       "power_by_n_units": row})
                    if rho == 0.0 or sd == 0.006:
                        print(f"{delta:.3f}  {mu:.4f} {sd:.4f}  {rho:.1f}  | " + "  ".join(f"{row[n]:.2f}" for n in row))
    print("\nQ2 (explained fraction), 6 seeds: P(lower>=0.75 | f_true), P(upper<=0.25 | f_true)")
    for n in (4, 6, 8):
        for f in (0.0, 0.1, 0.5, 0.9, 1.0):
            hi, lo = q2_rates(n, f)
            out["q2"].append({"n_seeds": n, "f_true": f, "P_mostly_explained": hi, "P_not_explained": lo})
            print(f"n={n} f_true={f:.1f}  P(mostly explained)={hi:.2f}  P(not explained)={lo:.2f}")
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "power_analysis.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
