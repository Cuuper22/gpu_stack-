"""Closed-form checkpoint/restart results used as ground truth (no simulator code).

Model (Daly 2006, FGCS 22(3):303-312, Sec. 2): failures are a Poisson process with
mean time between failures M.  Work is cut into segments.  A segment is tau of compute
followed by a checkpoint of cost delta, so it needs L = tau + delta of failure-free time.
A failure anywhere in a segment (including its checkpoint write) throws the segment away.
Restart takes R and can itself be hit by a failure.  After a successful restart the whole
segment is redone.  Then (Daly 2006, Eq. 9, restated per segment):

    E[T_segment] = M * exp(R/M) * (exp(L/M) - 1).

Optional repair downtime D (a failure costs D of wall time during which no new failure
can occur; failures arrive only while the system is up).  Derivation in protocol.md,
section "Analytic ground truth": the expected number of failures per segment is
F = exp(R/M)(exp(L/M) - 1), each costs D extra, so

    E[T_segment] = (M + D) * exp(R/M) * (exp(L/M) - 1).

Intervals: tau is the compute time between checkpoints (excludes delta).
Young (1974):          tau_Y   = sqrt(2 delta M)
Daly first order:      tau_D1  = sqrt(2 delta M) - delta
Daly higher order (Eq. 20 of Daly 2006), valid for delta < 2M, else tau = M:
    tau_D2 = sqrt(2 delta M) * [1 + (1/3) sqrt(delta/(2M)) + (1/9) (delta/(2M))] - delta
"""

from __future__ import annotations

import math

from scipy.optimize import minimize_scalar


def expected_segment_time(tau: float, delta: float, M: float, R: float, D: float = 0.0) -> float:
    return (M + D) * math.exp(R / M) * math.expm1((tau + delta) / M)


def expected_wall(n_segments: int, tau: float, delta: float, M: float, R: float, D: float = 0.0) -> float:
    return n_segments * expected_segment_time(tau, delta, M, R, D)


def waste_fraction(tau: float, delta: float, M: float, R: float, D: float = 0.0) -> float:
    """1 - (useful compute) / (wall time), per segment, exact in expectation of the
    ratio-of-means form (n segments cancel)."""
    return 1.0 - tau / expected_segment_time(tau, delta, M, R, D)


def tau_young(delta: float, M: float) -> float:
    return math.sqrt(2.0 * delta * M)


def tau_daly1(delta: float, M: float) -> float:
    return math.sqrt(2.0 * delta * M) - delta


def tau_daly2(delta: float, M: float) -> float:
    if delta >= 2.0 * M:
        return M
    x = delta / (2.0 * M)
    return math.sqrt(2.0 * delta * M) * (1.0 + math.sqrt(x) / 3.0 + x / 9.0) - delta


def tau_exact(delta: float, M: float, R: float, D: float = 0.0) -> float:
    """Minimiser of the exact expected wall time (equivalently of waste_fraction).
    D and R only scale the objective by a constant, so they do not move the optimum."""
    f = lambda lt: expected_segment_time(math.exp(lt), delta, M, R, D) / math.exp(lt)
    res = minimize_scalar(f, bracket=(math.log(delta * 1e-3 + 1e-12), math.log(M), math.log(10 * M)),
                          method="brent", tol=1e-12)
    return math.exp(res.x)


def regime_table(delta_over_m: list[float]) -> list[dict]:
    rows = []
    for r in delta_over_m:
        M, d, R = 1.0, r, r
        te = tau_exact(d, M, R)
        row = {"C_over_M": r, "tau_exact": te, "tau_young": tau_young(d, M),
               "tau_daly1": tau_daly1(d, M), "tau_daly2": tau_daly2(d, M),
               "waste_exact": waste_fraction(te, d, M, R)}
        for k in ("young", "daly1", "daly2"):
            t = row[f"tau_{k}"]
            row[f"rel_err_tau_{k}"] = t / te - 1.0
            row[f"excess_waste_{k}"] = waste_fraction(max(t, 1e-9), d, M, R) - row["waste_exact"]
        rows.append(row)
    return rows


if __name__ == "__main__":
    for row in regime_table([0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 1.9, 2.5]):
        print({k: (round(v, 5) if isinstance(v, float) else v) for k, v in row.items()})
