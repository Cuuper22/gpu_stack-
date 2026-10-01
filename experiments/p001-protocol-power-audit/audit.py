"""Builds every P001 module result and the per-gate table. No file output here; run.py writes."""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

import pstat as st
import sims

HEADROOM = 1.25  # decision criterion: 80% power must occur at an effect <= 1.25 x the claim
POWER_MIN = 0.8
FPR_MAX = 0.1


# ---------------------------------------------------------------- labels (frozen in protocol.md)
def label_threshold_claim(excess_ratio: float | None, possible: bool = True) -> str:
    if not possible or excess_ratio is None or not math.isfinite(excess_ratio):
        return "arithmetically impossible"
    if excess_ratio <= HEADROOM:
        return "reasonable"
    if excess_ratio <= 2.0:
        return "marginal"
    return "requires implausible effect"


def label_no_harm(power_at_claim: float, possible: bool = True) -> str:
    if not possible or power_at_claim == 0.0:
        return "arithmetically impossible"
    if power_at_claim >= POWER_MIN:
        return "reasonable"
    if power_at_claim >= 0.5:
        return "marginal"
    return "requires implausible effect"


def lax(fpr: float | None) -> bool:
    return fpr is not None and fpr > FPR_MAX


# ---------------------------------------------------------------- the audit
def run_audit(inputs: dict, n_sim: int, draws: int, seed: int) -> dict:
    M = inputs["measured"]
    sd_en_pw2 = M["pw2_energy_ratio_sparse_continue_sd"]
    sd_en_dense = M["pw2_energy_ratio_dense_continue_sd"]
    sd_en_inst = M["lc3_energy_ratio_sd_instantaneous_meter"]
    sd_clean = M["sc1_sync_final_nll_seed_sd"]  # NLL ~ 1, so also ~ relative SD
    assumptions = {
        "E003": {"K_quality_metrics": 4, "n_pairs_grid": [10, 20, 30, 50, 100, 200], "paired_diff_sd_in_clean_sd": [0.0, 0.1, 0.25, 0.45],
                 "families_with_own_interception_gate": [1, 6], "note": "n, K and the interval method are not stated in E003; values are sweeps."},
        "E004": {"workload_families": 4, "n_clusters_grid": [8, 30, 100], "note": "No measured noise exists for U; noise is swept and the break-even is reported."},
        "E005": {"runs_per_arm_grid": [2, 3, 5], "relative_sd_anchors": {"sc1_final_nll_seed_sd": sd_clean, "pw2_energy_ratio_pair_sd": sd_en_pw2, "lc3_instantaneous_meter_energy_ratio_sd": sd_en_inst}},
        "E006": {"windows_planned": 300, "bid_levels": [0.05, 0.10, 0.20, 0.30]},
        "criteria": {"headroom": HEADROOM, "power_min": POWER_MIN, "fpr_max": FPR_MAX},
    }
    R: dict = {}
    s = seed

    # ---------------- E003
    n_pairs_grid = assumptions["E003"]["n_pairs_grid"]
    R["e003_interception"] = sims.prop_lower_gate(0.99, [30, 100, 299, 300, 368, 500, 1000, 3000], [0.99, 0.995, 0.999, 0.9995, 1.0])
    R["e003_false_action"] = sims.prop_upper_gate(0.01, [300, 1000, 10_000, 100_000], [0.001, 0.005, 0.01])
    R["e003_equivalence"] = {
        f"d_sd={d}": {
            str(n): {
                "power_zero_harm": sims.tost_vector(n, 4, d, 0.0, 0.2, n_sim, s + n, False),
                "power_zero_harm_bonferroni": sims.tost_vector(n, 4, d, 0.0, 0.2, n_sim, s + n + 1, True),
                "false_pass_one_metric_shift_0.3sd": sims.tost_vector(n, 4, d, [0.3, 0, 0, 0], 0.2, n_sim, s + n + 2, False),
                "false_pass_one_metric_shift_0.5sd": sims.tost_vector(n, 4, d, [0.5, 0, 0, 0], 0.2, n_sim, s + n + 3, False),
            } for n in n_pairs_grid
        } for d in assumptions["E003"]["paired_diff_sd_in_clean_sd"]
    }
    R["e003_per_run_region"] = {
        "unpaired_reading_exactly_centred_defense": sims.per_run_region(100, 0.0, 1.0),
        "paired_reading": {f"d_sd={d}": sims.per_run_region(100, 0.0, d) for d in [0.02, 0.05, 0.1, 0.1020, 0.15, 0.25, 0.45]},
        "max_d_sd_for_95pct_inside": sims.d_sd_for_95pct_inside(),
        "measured_anchor_lc3_pairs_in_clean_sd": M["lc3_nll_pairs_in_clean_sd_units"],
        "measured_anchor_exact_arms_max_abs_nll_diff": M["sc1_exact_arms_max_abs_nll_difference_sync_vs_forward"],
    }
    tax_n = [6, 10, 20, 30, 50, 100, 200]
    R["tax_upper_bound_2pct"] = sims.tax_upper(tax_n, [sd_en_pw2, sd_en_dense, sd_en_inst], [0.0, 0.01, 0.02, 0.04])
    R["match_rule"] = {}
    for K in (5, 13):
        weak = [np.full(K, 1.0)] * 7
        R["match_rule"][f"K={K}"] = {}
        for n in (30, 100):
            def world(closest):
                return sims.match_rule(n, K, 8, weak + [closest])["p_hypothesis_survives"]
            e0 = np.zeros(K)
            ew = np.zeros(K)
            ew[0] = -0.5  # joint WORSE than the closest baseline on one outcome
            eb = np.zeros(K)
            eb[0] = 0.5  # joint better on one outcome
            ea = np.full(K, 0.3)             # joint better on all outcomes
            R["match_rule"][f"K={K}"][f"n_pairs={n}"] = {
                "closest_baseline_identical": world(e0), "closest_baseline_better_on_one_outcome": world(ew),
                "joint_better_on_one_outcome": world(eb), "joint_better_on_all_outcomes_0.3sd": world(ea),
            }

    # ---------------- E004
    R["e004_u_gain"] = {}
    for claim, name in ((0.20, "vs_static_20pct"), (0.10, "vs_independent_10pct")):
        R["e004_u_gain"][name] = {
            "max_tolerable_se_point_rule": sims.max_tolerable_se(claim, "point_rule"),
            "max_tolerable_se_lower95_rule": sims.max_tolerable_se(claim, "lower95_rule"),
            "by_n_clusters_and_cv": {
                f"n={n},cv={cv}": sims.superiority(claim, cv / math.sqrt(n), n - 1) for n in (8, 30, 100) for cv in (0.05, 0.10, 0.20)
            },
        }
    R["e004_interaction"] = {
        f"n={n},cell_cv={cv},corr={rho}": {
            "claim_I=0.05": sims.interaction3(n, cv, rho, 0.05, n_sim, s + 7, draws=min(draws, 1000)),
            "null_I=0": sims.interaction3(n, cv, rho, 0.0, n_sim, s + 8, draws=min(draws, 1000)),
            "I=0.0625": sims.interaction3(n, cv, rho, 0.0625, n_sim, s + 10, draws=min(draws, 1000)),
            "I=0.10": sims.interaction3(n, cv, rho, 0.10, n_sim, s + 9, draws=min(draws, 1000)),
        } for n in (8, 30, 100) for cv in (0.02, 0.05, 0.10) for rho in (0.0, 0.8)
    }
    R["noninferiority_conjunction"] = sims.noninf_conjunction([1, 4, 8, 12], [0.1, 0.25, 0.5, 1.0], [0.0, 0.5, 1.0, 2.0])
    R["e004_coverage_ge_0.8"] = sims.coverage_gate([10, 20, 50, 100, 300], [0.6, 0.7, 0.8, 0.9, 0.95], 0.8, 1.0)

    # ---------------- E005
    R["e005_ce_gain_25pct"] = {
        f"cv={cv:.4f},n={n}": sims.superiority(0.25, cv * math.sqrt(2 / n), 2 * n - 2) for cv in (sd_clean, sd_en_pw2, sd_en_inst) for n in (2, 3, 5)
    }
    R["e005_ce_gain_max_se"] = {"point_rule": sims.max_tolerable_se(0.25, "point_rule"), "lower95_rule_df2": sims.max_tolerable_se(0.25, "lower95_rule", 2), "lower95_rule_df4": sims.max_tolerable_se(0.25, "lower95_rule", 4)}
    R["e005_task_regress_2pct"] = {}
    for n in (2, 3, 5):
        for cv in (sd_clean, 0.03, 0.05):
            se_over_margin = cv * math.sqrt(2 / n) / 0.02
            R["e005_task_regress_2pct"][f"n={n},cv={cv:.4f}"] = {
                "se_over_margin": se_over_margin,
                "by_F_and_true_harm": {f"F={F},harm={h}": {"point": float(stats.norm.cdf((1 - h / 0.02) / se_over_margin)) ** F,
                                                         "ci": st.nct_power_upper(h / 0.02, 1.0, se_over_margin, 2 * n - 2) ** F}
                                       for F in (3, 5, 8) for h in (0.0, 0.01, 0.02, 0.04)},
            }
    R["e005_attribution"] = {
        f"n={n},cv={cv:.4f},arch_fraction={a}": sims.attribution_fraction(n, cv, 0.25, a, n_sim * 4, s + 11)
        for n in (2, 3, 5) for cv in (sd_clean, sd_en_pw2) for a in (0.0, 0.5, 0.625, 0.75)
    }
    R["e005_ranking"] = {
        f"m={m},tau_pop={t},noise/spread={nu}": sims.ranking(m, t, nu, n_sim * 2, s + 13)
        for m in (10, 20, 50) for t in (0.3, 0.7, 0.85, 1.0) for nu in (0.25, 0.5, 1.0)
    }
    R["e005_coverage_band_85_95"] = sims.coverage_gate([10, 20, 50, 100, 300, 1000], [0.7, 0.8, 0.85, 0.9, 0.95, 0.99], 0.85, 0.95)
    R["e005_search_energy_arithmetic"] = {
        "assumption": "inferred: training FLOPs = 6*N*D with D = 20*N, so energy per run scales as N^2; 5 seeds per candidate; target N=70e9",
        "max_full_length_candidates_for_25pct": {f"proxy_{p}B": 0.25 / (5 * (p * 1e9 / 70e9) ** 2) for p in (0.3, 1, 7, 13, 30)},
    }

    # ---------------- E006
    R["e006_delivery"] = sims.prop_lower_gate(0.99, [30, 75, 100, 299, 300, 473, 628, 1000, 1196, 3000], [0.99, 0.995, 0.999, 0.9995, 0.9999])
    R["e006_delivery_clustered"] = {
        f"windows={nc * m},per_campus_day={m},icc={icc},f_true={f}": sims.prop_cluster_mc(nc, m, icc, f, 0.99, 0.05, n_sim * 2, s + 17)
        for (nc, m) in ((300, 1), (100, 3), (50, 6), (1000, 1), (333, 3)) for icc in (0.0, 0.1, 0.3) for f in (0.0005, 0.002)
        if not (icc > 0 and m == 1)
    }
    R["e006_windows_arithmetic"] = {
        "windows_for_zero_failure_bid": st.n_min_for_lower(0.99, 0, 0.05),
        "bid_levels": 4,
        "windows_if_each_bid_level_needs_its_own_sample": 4 * st.n_min_for_lower(0.99, 0, 0.05),
        "event_hours_for_that": 4 * st.n_min_for_lower(0.99, 0, 0.05) * 0.25,
        "max_lower_bound_with_zero_failures": {str(n): 0.05 ** (1 / n) for n in (30, 75, 300)},
        "isolated_best_r_firm_allowed_by_gate_1.5x_if_joint_is": {"0.20": 0.20 / 1.5, "0.30": 0.30 / 1.5},
    }
    R["e006_rebound_every_event"] = {str(qq): (1 - qq) ** 300 for qq in (0.0005, 0.001, 0.005, 0.01, 0.05)}

    # ---------------- E001 / E002 calibration of the method
    tauN = M["lc3_nll_pair_sd"]
    R["median_bootstrap_coverage"] = {f"n={n}": sims.boot_median_coverage(n, n_sim * 2, s + 21, draws) for n in (4, 6)}
    R["lc3_nll_gate"] = {"tau_between_schedules": tauN, "margin": 0.01, "p_pass_by_true_mean_diff": sims.boot_median_gate(6, [0.0, 0.0033, 0.006, 0.01, 0.02], tauN, 0.01, "upper<=c", n_sim, s + 22, draws)}
    R["lc3_energy_gate_pw2_meter_noise"] = {"tau": sd_en_pw2, "limit": 1.05, "p_pass_by_true_ratio": sims.boot_median_gate(6, [0.96, 1.0, 1.023, 1.05, 1.10], sd_en_pw2, 1.05, "upper<=c", n_sim, s + 23, draws)}
    R["lc3_energy_gate_instantaneous_meter_noise"] = {"tau": sd_en_inst, "limit": 1.05, "p_pass_by_true_ratio": sims.boot_median_gate(6, [0.96, 1.0, 1.023, 1.05, 1.10], sd_en_inst, 1.05, "upper<=c", n_sim, s + 24, draws)}
    R["pw2_interaction_gate_standardised"] = {"observed_mean_over_sd": M["pw2_total_interaction_mean_over_sd"],
                                              "p_pass_by_true_mean_over_sd": sims.boot_median_gate(6, [0.0, 0.5, 1.0, 1.5, 2.0, 3.0], 1.0, 0.0, "lower>0", n_sim, s + 25, draws)}
    tauS = M["sc1_paired_nll_diff_sd"]
    R["sc1_nll_gate"] = {"tau_between_families": tauS, "margin": 0.01, "p_pass_by_true_mean_diff": sims.boot_median_gate(6, [0.0, 0.005, 0.01, 0.0167, 0.02], tauS, 0.01, "upper<=c", n_sim, s + 26, draws)}
    tr = np.asarray(M["sc1_paired_time_ratio_values"])
    R["sc1_time_gate"] = {"tau": float(tr.std(ddof=1)), "limit": 0.9, "p_pass_by_true_ratio": sims.boot_median_gate(6, [0.9, 0.95, 0.99, 1.0, 1.07], float(tr.std(ddof=1)), 0.9, "upper<=c", n_sim, s + 27, draws)}
    rg = np.asarray(M["sc1_paired_regret_values"])
    R["sc1_regret_gate_n4"] = {"tau": float(rg.std(ddof=1)), "limit": 0.10, "p_pass_by_true_regret": sims.boot_median_gate(4, [0.0, 0.03, 0.05, 0.07155, 0.10, 0.15], float(rg.std(ddof=1)), 0.10, "upper<=c", n_sim, s + 28, draws)}
    R["sc1_payload_arithmetic"] = {"floors_by_family": inputs["sc1_floors"], **inputs["sc1_floor_summary"], "gate_upper_bound_vs_periodic_local": 0.20,
                                   "periodic_period_ticks": 8, "state_bytes_per_param": 12, "gradient_bytes_per_param": 4,
                                   "min_period_for_10x_vs_sync": 12 / (4 * 0.1), "period_8_reduction_factor_vs_sync": 1 / inputs["sc1_floor_summary"]["periodic_over_sync_bytes_ratio"]}
    R["lc3_flop_quantum"] = {"one_replay_window_fraction": M["lc3_replay_quantum_fraction"], "gate_median_ge": 0.03, "values": M["lc3_attempted_flop_saving_values"]}
    return {"assumptions": assumptions, "modules": R}
