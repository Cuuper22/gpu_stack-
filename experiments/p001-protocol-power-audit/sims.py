"""Power / false-positive modules for P001. Each function is self-contained and returns plain dicts.

Conventions
- "claim" is the effect the hypothesis states; "null" is a world where the hypothesis is false.
- Analytic modules are exact (no Monte Carlo error). Monte Carlo modules report Wilson 95% CIs.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

import pstat as st

Z95 = st.Z95


# --------------------------------------------------------------------------------------
# 1. Exact binomial bound gates (E003 interception / false action, E006 delivery)
# --------------------------------------------------------------------------------------
def prop_lower_gate(target: float, n_list, p_true_list, alpha_methods=None) -> dict:
    """Gate: lower confidence bound on success probability >= target. Exact (binomial)."""
    alpha_methods = alpha_methods or {"cp_one_sided_95": (0.05, "cp"), "cp_two_sided_95": (0.025, "cp"), "wilson_one_sided_95": (0.05, "wilson")}
    out = {}
    for name, (alpha, method) in alpha_methods.items():
        rows = []
        for n in n_list:
            fmax = st.max_failures_for_lower(n, target, alpha, method)
            rows.append({
                "n": n,
                "max_failures_allowed": fmax,
                "possible": fmax >= 0,
                "power_by_true_success_prob": {str(p): st.binom_pass_prob(n, 1 - p, fmax) for p in p_true_list},
                "success_prob_for_80pct_power": (1 - st.solve_fail_rate_for_power(n, fmax, 0.8)) if fmax >= 0 else None,
            })
        out[name] = {
            "alpha_tail": alpha,
            "n_needed_zero_failures": st.n_min_for_lower(target, 0, alpha, method),
            "n_needed_one_failure": st.n_min_for_lower(target, 1, alpha, method),
            "n_needed_two_failures": st.n_min_for_lower(target, 2, alpha, method),
            "rows": rows,
        }
    return out


def prop_upper_gate(target: float, n_list, f_true_list, alpha: float = 0.05) -> dict:
    """Gate: upper confidence bound on failure rate <= target. Exact CP, iid events."""
    rows = []
    for n in n_list:
        fmax = st.max_failures_for_upper(n, target, alpha)
        rows.append({
            "n": n,
            "max_failures_allowed": fmax,
            "possible": fmax >= 0,
            "power_by_true_failure_rate": {str(f): st.binom_pass_prob(n, f, fmax) for f in f_true_list},
            "failure_rate_for_80pct_power": st.solve_fail_rate_for_power(n, fmax, 0.8) if fmax >= 0 else None,
        })
    return {"alpha_tail": alpha, "rows": rows}


def prop_cluster_mc(n_clusters: int, per_cluster: int, icc: float, f_true: float, target_success: float, alpha: float, n_sim: int, seed: int) -> dict:
    """Lower-bound gate with clustered failures (beta-binomial). CP on design-effect-adjusted counts."""
    rng = np.random.default_rng(seed)
    n = n_clusters * per_cluster
    if icc <= 0:
        k = rng.binomial(n, f_true, size=n_sim).astype(float)
    else:
        s = 1.0 / icc - 1.0
        q = rng.beta(max(f_true * s, 1e-9), max((1 - f_true) * s, 1e-9), size=(n_sim, n_clusters))
        k = rng.binomial(per_cluster, q).sum(axis=1).astype(float)
    de = 1 + (per_cluster - 1) * icc
    n_eff = n / de
    k_eff = k / de
    succ = n_eff - k_eff
    lower = np.where(succ <= 0, 0.0, stats.beta.ppf(alpha, np.maximum(succ, 1e-12), k_eff + 1))
    return {"n_windows": n, "design_effect": de, "n_effective": n_eff, "f_true": f_true, **st.rate(int((lower >= target_success).sum()), n_sim)}


# --------------------------------------------------------------------------------------
# 2. Equivalence (TOST) on a vector of K quality metrics, and the per-run region gate (E003)
# --------------------------------------------------------------------------------------
def tost_vector(n_pairs: int, K: int, d_sd: float, delta, margin: float, n_sim: int, seed: int, bonferroni: bool = False) -> dict:
    """Pass iff for every metric the 90% t-CI of the paired mean difference lies inside +-margin.
    Units: clean-run SD = 1. d_sd = SD of the paired (defended - clean) difference. delta: length-K true shifts."""
    rng = np.random.default_rng(seed)
    delta = np.broadcast_to(np.asarray(delta, dtype=float), (K,))
    alpha = 0.05 / K if bonferroni else 0.05
    t = float(stats.t.ppf(1 - alpha, n_pairs - 1))
    d = rng.normal(delta[None, :, None], d_sd, size=(n_sim, K, n_pairs))
    mean = d.mean(axis=2)
    sd = d.std(axis=2, ddof=1)
    half = t * sd / math.sqrt(n_pairs)
    ok = np.all(np.abs(mean) + half <= margin, axis=1)
    return st.rate(int(ok.sum()), n_sim)


def per_run_region(n_runs: int, shift: float, spread: float, margin: float = 0.2, frac: float = 0.95) -> dict:
    """P(observed fraction of runs inside +-margin >= frac). Each run's offset ~ N(shift, spread^2), clean SD = 1.
    spread=1 reproduces the unpaired reading (defended run vs clean mean); spread=d_sd is the paired reading."""
    if spread == 0:
        p_in = 1.0 if abs(shift) <= margin else 0.0
    else:
        p_in = float(stats.norm.cdf((margin - shift) / spread) - stats.norm.cdf((-margin - shift) / spread))
    need = math.ceil(frac * n_runs - 1e-9)
    return {"p_run_inside": p_in, "p_gate_pass": float(stats.binom.sf(need - 1, n_runs, p_in)), "n_runs": n_runs}


def d_sd_for_95pct_inside(margin: float = 0.2) -> float:
    """Largest per-run offset SD (clean-SD units) for which an exactly centred defense puts 95% of runs inside +-margin."""
    return margin / float(stats.norm.ppf(0.975))


# --------------------------------------------------------------------------------------
# 3. Upper-bound tax gates (E003 clean time / energy tax, E002 time tax) - analytic t
# --------------------------------------------------------------------------------------
def tax_upper(n_list, sd_list, tax_list, limit: float = 0.02, alpha: float = 0.05) -> dict:
    rows = []
    for sd in sd_list:
        for n in n_list:
            se = sd / math.sqrt(n)
            rows.append({
                "per_pair_sd": sd, "n_pairs": n,
                "power_by_true_tax": {str(t): st.nct_power_upper(t, limit, se, n - 1, alpha) for t in tax_list},
                "tax_for_80pct_power": st.solve_theta(lambda t: st.nct_power_upper(t, limit, se, n - 1, alpha), -1.0, limit, 0.8),
            })
    n80 = {}
    for sd in sd_list:
        for true_tax in (0.0, 0.01):
            for n in range(3, 5000):
                if st.nct_power_upper(true_tax, limit, sd / math.sqrt(n), n - 1, alpha) >= 0.8:
                    n80[f"sd={sd:.4f},true_tax={true_tax}"] = n
                    break
    return {"rows": rows, "n_pairs_for_80pct_power": n80}


# --------------------------------------------------------------------------------------
# 4. Conjunction of noninferiority gates over F families (E004, E005, E006)
# --------------------------------------------------------------------------------------
def noninf_conjunction(F_list, se_over_margin_list, harm_over_margin_list, df: float = 1e9) -> dict:
    """Margin = 1. P(all F families pass) for point-estimate rule (est <= margin) and
    CI rule (upper 95% bound <= margin). Independent families, equal true harm h and SE s."""
    rows = []
    for F in F_list:
        for s in se_over_margin_list:
            for h in harm_over_margin_list:
                p_point = float(stats.norm.cdf((1 - h) / s)) ** F
                p_ci = (st.nct_power_upper(h, 1.0, s, df) if df < 1e8 else float(stats.norm.cdf((1 - h - Z95 * s) / s))) ** F
                rows.append({"F": F, "se_over_margin": s, "true_harm_over_margin": h, "p_pass_point_rule": p_point, "p_pass_ci_rule": p_ci})
    return {"rows": rows}


# --------------------------------------------------------------------------------------
# 5. Superiority / improvement gates (E004 U gains, E005 CE gain) - analytic
# --------------------------------------------------------------------------------------
def superiority(claim: float, se: float, df: float = 1e9, null: float = 0.0, headroom: float = 1.25) -> dict:
    """Two readings of 'improvement >= claim': point estimate >= claim; lower 95% bound >= claim."""
    def p_point(theta):
        return float(stats.norm.cdf((theta - claim) / se))

    def p_ci(theta):
        return st.nct_power_lower(theta, claim, se, df) if df < 1e8 else float(stats.norm.cdf((theta - claim - Z95 * se) / se))

    out = {}
    for name, fn in (("point_rule", p_point), ("lower95_rule", p_ci)):
        out[name] = {
            "power_at_claim": fn(claim),
            "false_pass_at_null": fn(null),
            "effect_for_80pct_power": st.solve_theta(fn, claim - 1, claim + 50 * se + 1, 0.8),
        }
        out[name]["excess_ratio"] = (out[name]["effect_for_80pct_power"] - null) / (claim - null)
    out["se"] = se
    out["df"] = df
    out["claim"] = claim
    return out


def max_tolerable_se(claim: float, rule: str, df: float = 1e9, headroom: float = 1.25, fpr_max: float = 0.1) -> float:
    """Largest SE for which 80% power occurs at claim*headroom AND false-pass at zero effect <= fpr_max."""
    lo, hi = 1e-6, 10 * claim
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        r = superiority(claim, mid, df)[rule]
        ok = r["effect_for_80pct_power"] <= claim * headroom and r["false_pass_at_null"] <= fpr_max
        lo, hi = (mid, hi) if ok else (lo, mid)
    return lo


# --------------------------------------------------------------------------------------
# 6. Three-way interaction (E004 hypothesis 3): point >= 0.05 and cluster-bootstrap lower bound > 0
# --------------------------------------------------------------------------------------
def interaction3(n_clusters: int, cell_cv: float, within_cluster_corr: float, true_I: float, n_sim: int, seed: int, draws: int = 1000, claim_point: float = 0.05) -> dict:
    """The contrast I_ABC sums 8 cell values with signs +-1 (units: no-control baseline = 1).
    Per-cluster contrast ~ N(true_I, 8 * cv^2 * (1 - corr)). Bootstrap resamples clusters."""
    rng = np.random.default_rng(seed)
    sd_c = math.sqrt(8 * cell_cv**2 * (1 - within_cluster_corr))
    ok = 0
    chunk = max(1, min(n_sim, 2_000_000 // (draws * n_clusters)))
    done = 0
    while done < n_sim:
        s = min(chunk, n_sim - done)
        c = rng.normal(true_I, sd_c, size=(s, n_clusters))
        idx = rng.integers(0, n_clusters, size=(s, draws, n_clusters))
        bm = np.take_along_axis(c[:, None, :], idx, axis=2).mean(axis=2)
        lo = np.quantile(bm, 0.025, axis=1)
        ok += int(((c.mean(axis=1) >= claim_point) & (lo > 0)).sum())
        done += s
    return {"se_of_I": sd_c / math.sqrt(n_clusters), **st.rate(ok, n_sim)}


# --------------------------------------------------------------------------------------
# 7. Architecture-attributable fraction (E005 hypothesis 3), Monte Carlo
# --------------------------------------------------------------------------------------
def attribution_fraction(n_runs: int, cv: float, joint_gain: float, arch_fraction: float, n_sim: int, seed: int, threshold: float = 0.5) -> dict:
    """CE(H)=1, CE(J)=1+g, CE(P)=1+(1-a)g. Arm means have relative SD cv/sqrt(n). Pass iff (J-P)/(J-H) >= threshold."""
    rng = np.random.default_rng(seed)
    se = cv / math.sqrt(n_runs)
    H = rng.normal(1.0, se, n_sim)
    J = rng.normal(1.0 + joint_gain, se, n_sim)
    P = rng.normal(1.0 + (1 - arch_fraction) * joint_gain, se, n_sim)
    with np.errstate(divide="ignore", invalid="ignore"):
        frac = (J - P) / (J - H)
    ok = (frac >= threshold) & (J - H > 0)
    return st.rate(int(ok.sum()), n_sim)


# --------------------------------------------------------------------------------------
# 8. Ranking transfer (E005 hypothesis 4): Kendall tau >= 0.70 and regret <= 10%
# --------------------------------------------------------------------------------------
def ranking(m: int, tau_pop: float, noise_over_spread: float, n_sim: int, seed: int, spread_rel: float = 0.10, tau_gate: float = 0.7, regret_gate: float = 0.10) -> dict:
    """Prediction and TRUE CE are bivariate normal with Kendall tau_pop (r = sin(pi tau/2)). Measured CE = true + noise.
    CE_true ~ 1 + spread_rel * N(0,1). Gate on tau(pred, measured) and on regret of the argmax-pred design vs best measured."""
    rng = np.random.default_rng(seed)
    r = math.sin(math.pi * tau_pop / 2)
    true = rng.normal(size=(n_sim, m))
    pred = r * true + math.sqrt(max(0.0, 1 - r * r)) * rng.normal(size=(n_sim, m))
    meas = true + noise_over_spread * rng.normal(size=(n_sim, m))
    tau = st.kendall_rows(pred, meas)
    ce = 1 + spread_rel * meas
    pick = ce[np.arange(n_sim), pred.argmax(axis=1)]
    regret = (ce.max(axis=1) - pick) / ce.max(axis=1)
    ok_tau = tau >= tau_gate
    ok_both = ok_tau & (regret <= regret_gate)
    return {"p_tau_gate": st.rate(int(ok_tau.sum()), n_sim), "p_both_gates": st.rate(int(ok_both.sum()), n_sim), "mean_observed_tau": float(tau.mean())}


# --------------------------------------------------------------------------------------
# 9. Coverage gates (E004 >= 0.8; E005 band 0.85-0.95), exact binomial
# --------------------------------------------------------------------------------------
def coverage_gate(m_list, true_cov_list, lo: float, hi: float = 1.0) -> dict:
    rows = []
    for m in m_list:
        row = {"m_heldout_outcomes": m, "p_pass_by_true_coverage": {}}
        k_lo = math.ceil(lo * m - 1e-9)
        k_hi = math.floor(hi * m + 1e-9)
        for c in true_cov_list:
            row["p_pass_by_true_coverage"][str(c)] = float(stats.binom.cdf(k_hi, m, c) - stats.binom.cdf(k_lo - 1, m, c))
        rows.append(row)
    return {"rows": rows, "pass_band": [lo, hi]}


# --------------------------------------------------------------------------------------
# 10. "A baseline matches the joint policy within uncertainty on all outcomes" falsifier
# --------------------------------------------------------------------------------------
def match_rule(n_pairs: int, K: int, n_baselines: int, effects_per_baseline, sd: float = 1.0) -> dict:
    """Hypothesis survives iff NO baseline matches the joint policy on ALL K outcomes, where
    'matches' = two-sided 95% paired t CI includes 0. Direction is not part of the rule.
    effects_per_baseline: list (len n_baselines) of length-K arrays of true standardised effects (any sign)."""
    tcrit = float(stats.t.ppf(0.975, n_pairs - 1))
    p_survive = 1.0
    per = []
    for eff in effects_per_baseline:
        eff = np.asarray(eff, dtype=float)
        ncp = eff * math.sqrt(n_pairs) / sd
        p_excl = 1 - (stats.nct.cdf(tcrit, n_pairs - 1, ncp) - stats.nct.cdf(-tcrit, n_pairs - 1, ncp))
        p_not_match_all = 1 - float(np.prod(1 - p_excl))
        per.append(p_not_match_all)
        p_survive *= p_not_match_all
    return {"p_hypothesis_survives": p_survive, "p_not_matched_per_baseline": per}


# --------------------------------------------------------------------------------------
# 11. Percentile bootstrap of the median at n = 4..6 (the E001/E002 decision rule)
# --------------------------------------------------------------------------------------
def boot_median_gate(n: int, mu_list, tau: float, c: float, rule: str, n_sim: int, seed: int, draws: int = 2000, conf: float = 0.9) -> dict:
    """x_s ~ N(mu, tau^2), s=1..n (between-schedule heterogeneity). rule: 'upper<=c' | 'lower>0' | 'lower>=c' | 'upper<=c&lower>0'."""
    rng = np.random.default_rng(seed)
    out = {}
    chunk = max(1, 400_000 // (draws * n) or 1)
    for mu in mu_list:
        ok = 0
        done = 0
        while done < n_sim:
            s = min(chunk, n_sim - done)
            x = rng.normal(mu, tau, size=(s, n))
            idx = st.boot_index(n, draws, rng)
            lo, hi, _ = st.boot_median_bounds(x, idx, conf)
            if rule == "upper<=c":
                ok += int((hi <= c).sum())
            elif rule == "lower>0":
                ok += int((lo > 0).sum())
            elif rule == "lower>=c":
                ok += int((lo >= c).sum())
            else:
                raise ValueError(rule)
            done += s
        out[str(mu)] = st.rate(ok, n_sim)
    return out


def boot_median_coverage(n: int, n_sim: int, seed: int, draws: int = 2000, conf: float = 0.9) -> dict:
    """Standard-normal data, true mean=median=0. Two-sided coverage and one-sided miss rates of the interval."""
    rng = np.random.default_rng(seed)
    cov = up_miss = lo_miss = 0
    done = 0
    chunk = max(1, 400_000 // (draws * n) or 1)
    while done < n_sim:
        s = min(chunk, n_sim - done)
        x = rng.normal(size=(s, n))
        lo, hi, _ = st.boot_median_bounds(x, st.boot_index(n, draws, rng), conf)
        cov += int(((lo <= 0) & (hi >= 0)).sum())
        up_miss += int((hi < 0).sum())
        lo_miss += int((lo > 0).sum())
        done += s
    return {"nominal_two_sided": conf, "coverage": st.rate(cov, n_sim), "upper_bound_below_truth": st.rate(up_miss, n_sim), "lower_bound_above_truth": st.rate(lo_miss, n_sim)}
