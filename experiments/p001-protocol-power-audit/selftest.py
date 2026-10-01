"""Checks simulation modules against closed forms. Run: PYTHONPATH=<repo> <venv>/bin/python -B selftest.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from scipy import stats

import pstat as st
import sims


def close(a, b, tol, name):
    assert abs(a - b) <= tol, f"{name}: {a} vs {b}"
    print(f"ok {name}: {a:.4f} ~ {b:.4f}")


# exact binomial: zero-failure n for 99% at one-sided 5%
assert st.n_min_for_lower(0.99, 0, 0.05) == 299
assert st.max_failures_for_lower(100, 0.99, 0.05) == -1
close(sims.prop_lower_gate(0.99, [300], [0.995])["cp_one_sided_95"]["rows"][0]["power_by_true_success_prob"]["0.995"], 0.995**300, 1e-9, "power n=300 p=.995")
# clustered MC with icc=0 reduces to binomial
r = sims.prop_cluster_mc(300, 1, 0.0, 0.0005, 0.99, 0.05, 20000, 1)
close(r["p"], 0.9995**300, 0.01, "cluster mc icc=0")
# per-run region
close(sims.per_run_region(100, 0, 1.0)["p_run_inside"], 2 * stats.norm.cdf(0.2) - 1, 1e-12, "unpaired inside")
# match rule closed form
close(sims.match_rule(30, 5, 1, [np.zeros(5)])["p_hypothesis_survives"], 1 - 0.95**5, 1e-9, "match rule identical")
# superiority point rule at claim = 0.5, lower95 at claim ~ 0.05
s = sims.superiority(0.25, 0.05)
close(s["point_rule"]["power_at_claim"], 0.5, 1e-9, "point power at claim")
close(s["lower95_rule"]["power_at_claim"], 0.05, 1e-6, "lower95 power at claim")
# TOST with known-ish sd, K=1, large n -> power near 1 at zero harm if margin >> se, ~0 if harm = margin
close(sims.tost_vector(400, 1, 0.45, 0.0, 0.2, 2000, 3)["p"], 1.0, 0.01, "tost large n")
close(sims.tost_vector(400, 1, 0.45, 0.2, 0.2, 4000, 3)["p"], 0.05, 0.015, "tost size at margin")
# interaction3 versus normal approximation (lower bound ~ est - 1.96 se)
inter = sims.interaction3(30, 0.05, 0.0, 0.05, 4000, 5, draws=500)
se = inter["se_of_I"]
approx = 1 - stats.norm.cdf((1.96 * se - 0.05) / se)
close(inter["p"], approx, 0.04, "interaction3 normal approx")
# ranking: perfect model, no noise
assert sims.ranking(10, 1.0, 0.0, 500, 1)["p_both_gates"]["p"] == 1.0
# bootstrap median coverage near nominal at n=6 (loose)
c = sims.boot_median_coverage(6, 4000, 2, 800)
assert 0.85 <= c["coverage"]["p"] <= 0.96, c
print("ok bootstrap coverage n=6", c["coverage"]["p"], "one-sided upper miss", c["upper_bound_below_truth"]["p"])
# coverage gate exact: m=20, band >=0.8
close(sims.coverage_gate([20], [0.9], 0.8, 1.0)["rows"][0]["p_pass_by_true_coverage"]["0.9"], float(stats.binom.sf(15, 20, 0.9)), 1e-12, "coverage gate")
print("all selftests passed")
