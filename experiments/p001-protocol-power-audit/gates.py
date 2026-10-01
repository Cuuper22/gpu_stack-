"""Gate registry (hand-extracted from the frozen protocols) joined to simulation results and labelled.

Labels follow the rules frozen in protocol.md. A row is labelled only when its n, estimator and noise are
specified or measured; otherwise the label is 'underspecified' and the row reports what would make it adequate.
"""
from __future__ import annotations

from scipy import stats

import audit
import pstat as st

E3, E4, E5, E6 = ("experiments/e003-semantic-fault-tolerance/experiment.md", "experiments/e004-fluid-inference-topology/experiment.md",
                  "experiments/e005-heterogeneous-architecture-codesign/experiment.md", "experiments/e006-firm-grid-responsive-inference/experiment.md")
E1D = "experiments/e001-beyond-one-datacenter/"
E2D = "experiments/e002-power-waveform-shaping/"


def _first_n(rows, key_fn, ok_fn):
    for r in rows:
        if ok_fn(key_fn(r)):
            return r["n_pairs"] if "n_pairs" in r else r["n"]
    return None


def build(R: dict, inputs: dict, protocols: dict) -> list[dict]:
    M = inputs["measured"]
    rows: list[dict] = []

    def add(**kw):
        kw.setdefault("flags", [])
        kw.setdefault("spec_gaps", [])
        kw.setdefault("label_basis", "simulation/arithmetic")
        rows.append(kw)

    # ----------------------------------------------------------------- E003
    eq = R["e003_equivalence"]
    n80 = {}
    for dk, cells in eq.items():
        n80[dk] = next((int(n) for n, c in cells.items() if c["power_zero_harm"]["p"] >= 0.8), None)
    fpr_at_n80 = {dk: (eq[dk][str(n)]["false_pass_one_metric_shift_0.3sd"]["p"] if n else None) for dk, n in n80.items()}
    add(id="E003-G1", protocol="E003", gate="every primary quality metric: 90% CI of defended-minus-clean inside +-0.2 clean SD",
        source=f"{E3}:62-66,310-312", planned_n="not stated (promises 90% power from calibration, gives no number)",
        estimator="two one-sided tests per metric, paired by seed, 5% family-wise; number of metrics not stated",
        label="underspecified", flags=(["too lax at some n"] if any(v is not None and v > audit.FPR_MAX for v in fpr_at_n80.values()) else []),
        spec_gaps=["n", "number of metrics K", "correction method"],
        key={"n_pairs_for_80pct_power_by_paired_diff_sd_K4": n80, "false_pass_at_0.3sd_shift_at_that_n": fpr_at_n80,
             "measured_lc3_policy_shift_in_clean_sd": M["lc3_nll_pairs_in_clean_sd_units"]},
        note="Needs roughly 10-40+ paired runs depending on how exactly the defense reproduces the clean path. Measured recovery policies shift final NLL by 0.10-0.98 clean SD, so the 0.2 SD margin is met only by exact-semantics defenses.")
    pr = R["e003_per_run_region"]
    add(id="E003-G2", protocol="E003", gate=">= 95% of defended runs finish inside the per-run +-0.2 SD region",
        source=f"{E3}:65-66,350", planned_n="not stated", estimator="observed fraction (no interval); 'corresponding' region not defined",
        label=("arithmetically impossible if the region is centred on the clean mean (unpaired); needs paired offset SD <= 0.102 clean SD if paired"
               if pr["unpaired_reading_exactly_centred_defense"]["p_run_inside"] < 0.95 else "reasonable"),
        spec_gaps=["region definition: paired or unpaired"],
        key={"unpaired_p_run_inside_for_a_perfect_defense": pr["unpaired_reading_exactly_centred_defense"]["p_run_inside"],
             "max_paired_offset_sd_for_95pct": pr["max_d_sd_for_95pct_inside"],
             "measured_exact_arm_max_abs_nll_diff": pr["measured_anchor_exact_arms_max_abs_nll_diff"]},
        note="A clean run varies by 1 SD between seeds, so only 15.9% of runs can sit inside +-0.2 SD of a fixed centre even if the defense changes nothing. Pairing by seed fixes this, but only for defenses that reproduce the clean trajectory almost exactly. SC1 measured exact sync vs exact forward recovery equal to all digits, so exactness is reachable for those arms.")
    ic = R["e003_interception"]["cp_one_sided_95"]
    r300 = next(r for r in ic["rows"] if r["n"] == 300)
    f80 = 1 - r300["success_prob_for_80pct_power"]
    add(id="E003-G3", protocol="E003", gate="lower 95% bound on critical-event interception >= 99%",
        source=f"{E3}:67-68,312-314,319-320", planned_n=">= 100 root events per fault family",
        estimator="'95% confidence bound' (method not stated); exact Clopper-Pearson one-sided assumed, two-sided and Wilson reported",
        label=("arithmetically impossible at n=100" if not next(r for r in ic["rows"] if r["n"] == 100)["possible"] else "see key"),
        spec_gaps=["interval method", "pooled vs per-family gate"],
        key={"n_needed_zero_misses_cp_one_sided": ic["n_needed_zero_failures"], "n_needed_one_miss": ic["n_needed_one_failure"],
             "n_needed_zero_misses_cp_two_sided": R["e003_interception"]["cp_two_sided_95"]["n_needed_zero_failures"],
             "n_needed_zero_misses_wilson": R["e003_interception"]["wilson_one_sided_95"]["n_needed_zero_failures"],
             "at_n=300_power_if_true_recall_0.995": r300["power_by_true_success_prob"]["0.995"],
             "at_n=300_true_recall_for_80pct_power": r300["success_prob_for_80pct_power"],
             "failure_rate_ratio_claim_over_needed_at_n300": 0.01 / f80},
        note="With 100 events the best possible bound is 0.05^(1/100)=0.970. At 299+ events a single miss fails the gate. For 80% power at n=300 the true miss rate must be about 0.05%, 20x lower than the claimed 1%. If the gate applies per family with F families, power is power^F.")
    fa = R["e003_false_action"]["rows"]
    n_fa = None
    for N in [int(10 ** (2 + i / 8)) for i in range(0, 40)]:
        fm = st.max_failures_for_upper(N, 0.01, 0.05)
        if fm >= 0 and st.solve_fail_rate_for_power(N, fm, 0.8) >= 0.008:
            n_fa = N
            break
    add(id="E003-G4", protocol="E003", gate="upper 95% bound on false action per clean optimizer step <= 1%",
        source=f"{E3}:67-69,314", planned_n="not stated", estimator="upper 95% bound; steps assumed independent (they are clustered by run)",
        label="underspecified", spec_gaps=["n clean steps", "clustering of steps within runs"],
        key={"clean_steps_needed_for_80pct_power_at_true_rate_0.8pct": n_fa, "rows": {str(r["n"]): r["failure_rate_for_80pct_power"] for r in fa}},
        note="A 1% ceiling is easy to resolve with tens of thousands of clean steps if steps are independent. They are not; the effective n is the number of runs.")
    tx = R["tax_upper_bound_2pct"]["n_pairs_for_80pct_power"]
    t6 = next(r for r in R["tax_upper_bound_2pct"]["rows"] if r["n_pairs"] == 6 and abs(r["per_pair_sd"] - M["pw2_energy_ratio_sparse_continue_sd"]) < 1e-12)
    add(id="E003-G5/G6", protocol="E003", gate="clean time-to-target tax and facility-energy tax, upper 95% bound <= 2%",
        source=f"{E3}:70-71,314-315", planned_n="not stated", estimator="paired 95% interval; method not stated",
        label="underspecified", spec_gaps=["n", "interval method"],
        key={"n_pairs_for_80pct_power_by_per_pair_sd_and_true_tax": tx, "measured_per_pair_sd_pw2_cumulative_counter": M["pw2_energy_ratio_sparse_continue_sd"],
             "measured_per_pair_sd_lc3_instantaneous_meter": M["lc3_energy_ratio_sd_instantaneous_meter"],
             "power_at_n6_true_tax_0": t6["power_by_true_tax"]["0.0"]},
        note="With the per-pair energy-ratio SD measured on this stack (3.6% with the cumulative counter) and 6 pairs, a true 0% tax passes only about a third of the time. About 17+ pairs are needed for 80% power at true tax 0, many more at 1%.")
    add(id="E003-G7/G8", protocol="E003", gate="time and energy tax <= 2% at measured production fault incidence",
        source=f"{E3}:70-72,81-84", planned_n="requires a fleet incidence measurement that does not exist", estimator="n/a",
        label="not evaluable (structural)", label_basis="judgment (protocol text)", note="The protocol itself says this is unevaluable until incidence is measured. Not a power question.")
    add(id="E003-G9", protocol="E003", gate="redundant FLOPs <= 50% of uniform duplicate execution at the same protection level",
        source=f"{E3}:78-80,315", planned_n="not stated", estimator="paired 95% interval on an accounting ratio",
        label="reasonable (accounting identity, little noise)", label_basis="judgment (not simulated)", spec_gaps=["definition of 'same protection level'"],
        note="FLOP counts are exact in the engine. Adequacy depends on how the protection level is matched, not on n.")
    mr = R["match_rule"]
    add(id="E003-G10", protocol="E003", gate="falsified if any baseline matches the joint policy within uncertainty on all primary outcomes",
        source=f"{E3}:355-358", planned_n="not stated", estimator="'matches within uncertainty' undefined; direction undefined",
        label=("too lax" if mr["K=5"]["n_pairs=30"]["closest_baseline_identical"] > audit.FPR_MAX else "adequate"),
        flags=(["too lax"] if mr["K=5"]["n_pairs=30"]["closest_baseline_identical"] > audit.FPR_MAX else []), spec_gaps=["match definition", "direction"],
        key={"p_hypothesis_survives_if_closest_baseline_is_identical_K5": mr["K=5"]["n_pairs=30"]["closest_baseline_identical"],
             "same_K13": mr["K=13"]["n_pairs=30"]["closest_baseline_identical"],
             "p_survives_if_baseline_is_better_on_one_outcome_K5_n100": mr["K=5"]["n_pairs=100"]["closest_baseline_better_on_one_outcome"]},
        note="Surviving only requires the CI to exclude 0 on at least one of K outcomes, in either direction. An identical baseline is 'not matched' with probability 1-0.95^K by chance; a baseline that is clearly better on one outcome also counts as not matching.")

    # ----------------------------------------------------------------- E004
    ug = R["e004_u_gain"]
    for gid, name, claim_txt in (("E004-G1", "vs_static_20pct", "joint improves U >= 20% over best static"), ("E004-G2", "vs_independent_10pct", "joint improves U >= 10% over independent-controller ensemble")):
        cell = ug[name]["by_n_clusters_and_cv"]["n=30,cv=0.1"]
        add(id=gid, protocol="E004", gate=claim_txt, source=f"{E4}:76-80,179-181", planned_n="30 seeds per cell; resampling unit = trace-day and failure domain (count not stated)",
            estimator="machine-readable falsifier tests a point estimate; markdown says 'survive uncertainty analysis'",
            label="underspecified", spec_gaps=["point vs interval reading", "number of independent trace-days/failure domains", "noise of U"],
            key={"max_tolerable_se_point_rule": ug[name]["max_tolerable_se_point_rule"], "max_tolerable_se_lower95_rule": ug[name]["max_tolerable_se_lower95_rule"],
                 "n=30,cv=0.10": {k: cell[k] for k in ("point_rule", "lower95_rule")}},
            note="No noise measurement for U exists. Adequate (80% power at 1.25x claim, false pass <= 10%) only if the standard error of the gain is below the stated se; this needs the cluster-level SD of the paired gain to be frozen from calibration.")
    it = R["e004_interaction"]
    c1, c2 = it["n=30,cell_cv=0.05,corr=0.0"], it["n=30,cell_cv=0.05,corr=0.8"]
    c3 = it["n=8,cell_cv=0.05,corr=0.0"]
    add(id="E004-G3", protocol="E004", gate="three-way interaction I_ABC >= 0.05 and cluster-bootstrap lower 95% bound > 0",
        source=f"{E4}:81-88", planned_n="clusters not stated (>= 8 failure domains for the live claim)", estimator="percentile cluster bootstrap on a contrast of 8 cell means",
        label=("requires implausible effect" if c1["I=0.0625"]["p"] < 0.8 and c1["I=0.10"]["p"] < 0.8 else "marginal" if c1["I=0.0625"]["p"] < 0.8 else "reasonable"),
        spec_gaps=["number of clusters", "cell-level noise"],
        key={"n30_cv0.05_corr0": {k: v["p"] for k, v in c1.items()}, "n30_cv0.05_corr0.8": {k: v["p"] for k, v in c2.items()}, "n8_cv0.05_corr0": {k: v["p"] for k, v in c3.items()}},
        note="The contrast adds 8 noisy cells with unit weight, so its SE is sqrt(8) times a cell's SE. Label is for 30 clusters and 5% per-cell CV with independent cells; labels change with noise and pairing, see key.")
    add(id="E004-G4/G5", protocol="E004", gate="regime crossing in >= 3 of 4 families; no static regime holds >= 90% of request-time in >= 2 families",
        source=f"{E4}:85-89,229-236", planned_n="n/a (counts of traces)", estimator="fraction of request-time per regime",
        label="reasonable but not a test of benefit", label_basis="judgment (not simulated)", flags=["satisfiable by churn"],
        note="A controller that toggles regimes for no benefit satisfies it. It needs the utility gates beside it, which E004 does state.")
    cj = R["noninferiority_conjunction"]["rows"]

    def maxse(F, rule):
        lo, hi = 1e-3, 5.0
        for _ in range(60):
            mid = (lo + hi) / 2
            p = float(stats.norm.cdf((1 - 0.0) / mid)) ** F if rule == "point" else float(stats.norm.cdf((1 - 1.6449 * mid) / mid)) ** F
            lo, hi = (mid, hi) if p >= 0.8 else (lo, mid)
        return lo
    add(id="E004-G6/G7", protocol="E004", gate="no workload family loses > 1% utility or > 1 pp SLO attainment",
        source=f"{E4}:90-92,238-240", planned_n="n/a", estimator="worst of F families; point vs interval not stated",
        label="underspecified", spec_gaps=["point vs interval", "SE per family"],
        key={"max_se_over_margin_for_80pct_pass_at_zero_harm_F4_point": maxse(4, "point"), "same_ci_rule": maxse(4, "ci"), "F=4_se=0.5margin_harm0": next(r for r in cj if r["F"] == 4 and r["se_over_margin"] == 0.5 and r["true_harm_over_margin"] == 0.0)},
        note="Taking the worst of four noisy family estimates is a max over noise. With a 1% margin the per-family SE must be <= ~0.6% (point rule) or ~0.3% (interval rule).")
    cv8 = R["e004_coverage_ge_0.8"]["rows"]
    add(id="E004-G9", protocol="E004", gate="nominal-90% intervals cover >= 80% of held-out outcomes",
        source=f"{E4}:245-246", planned_n="number of held-out outcomes not stated", estimator="observed coverage fraction (no interval)",
        label="underspecified", flags=["too lax when few outcomes"] if cv8[1]["p_pass_by_true_coverage"]["0.7"] > 0.1 else [], spec_gaps=["m held-out outcomes"],
        key={str(r["m_heldout_outcomes"]): r["p_pass_by_true_coverage"] for r in cv8},
        note="With 20 outcomes, a model whose true coverage is 70% passes about 11% of the time; with >= 50 outcomes it is controlled.")
    add(id="E004-G8/G-rank", protocol="E004", gate="intervention regret <= 10% of oracle value; held-out ranking 'fails'",
        source=f"{E4}:243-246", planned_n="not stated", estimator="regret fraction; no threshold for ranking",
        label="underspecified", label_basis="judgment (not simulated)", flags=["unfalsifiable as written (ranking)"], spec_gaps=["ranking threshold", "regret interval"],
        note="The machine-readable protocol says no correlation threshold is set. 'Ranking fails' therefore cannot be decided.")

    # ----------------------------------------------------------------- E005
    ce = R["e005_ce_gain_25pct"]
    def cell(cv, n):
        return ce[f"cv={cv:.4f},n={n}"]
    c_clean, c_en, c_inst = M["sc1_sync_final_nll_seed_sd"], M["pw2_energy_ratio_sparse_continue_sd"], M["lc3_energy_ratio_sd_instantaneous_meter"]
    add(id="E005-G1", protocol="E005", gate="CE improves >= 25% over best homogeneous co-design",
        source=f"{E5}:62-66,173-176", planned_n="5 seeds/proxy candidate; >= 3 at 7-30B; >= 2 at target scale", estimator="machine-readable: point estimate; markdown: 'survive uncertainty'",
        label=audit.label_threshold_claim(cell(c_en, 2)["point_rule"]["excess_ratio"]) + " (point rule, n=2, noise=3.6%)",
        spec_gaps=["point vs interval", "CE noise (capability part not measured)"],
        key={"point_rule_n2_cv1.4%": cell(c_clean, 2)["point_rule"], "point_rule_n2_cv3.6%": cell(c_en, 2)["point_rule"],
             "lower95_rule_n2_cv3.6%_excess_ratio": cell(c_en, 2)["lower95_rule"]["excess_ratio"], "lower95_rule_n2_cv8.5%_excess_ratio": cell(c_inst, 2)["lower95_rule"]["excess_ratio"],
             "lower95_rule_n3_cv3.6%_excess_ratio": cell(c_en, 3)["lower95_rule"]["excess_ratio"], "max_tolerable_se": R["e005_ce_gain_max_se"]},
        note="Reading it as a point estimate is adequate at the measured noise. Reading it as a lower 95% bound with 2 runs per arm (t with 2 df) needs a much larger true gain. Noise anchors are an energy ratio and a loss, not CE itself.")
    tr = R["e005_task_regress_2pct"]
    k = f"n=3,cv={c_clean:.4f}"
    add(id="E005-G2", protocol="E005", gate="no task-family metric regresses > 2% versus best homogeneous design",
        source=f"{E5}:70-72,229-230", planned_n="3 seeds (7-30B), 2 runs (target)", estimator="worst of F families; point vs interval not stated",
        label="requires implausible effect" if tr[k]["by_F_and_true_harm"]["F=5,harm=0.0"]["ci"] < 0.5 else "marginal",
        key={k: {kk: v for kk, v in tr[k]["by_F_and_true_harm"].items() if kk.startswith("F=5")}, "n=2_cv0.03": {kk: v for kk, v in tr["n=2,cv=0.0300"]["by_F_and_true_harm"].items() if kk.startswith("F=5")}},
        note="Even with zero true regression, requiring every one of F noisy metrics to clear 2% passes rarely under the interval reading, and only about half the time under the point reading when per-metric noise is 3% with 2 runs.")
    at = R["e005_attribution"]
    def ak(n, cv, a):
        return at[f"n={n},cv={cv:.4f},arch_fraction={a}"]["p"]
    add(id="E005-G3", protocol="E005", gate="architecture-attributable share of the joint CE gain >= 50%",
        source=f"{E5}:71-74", planned_n="as E005-G1", estimator="ratio of two CE differences (point)",
        label=("reasonable" if ak(3, c_en, 0.625) >= 0.8 else "marginal" if ak(3, c_en, 0.75) >= 0.8 else "requires implausible effect"),
        key={"n3_cv3.6%": {a: ak(3, c_en, a) for a in (0.0, 0.5, 0.625, 0.75)}, "n2_cv3.6%": {a: ak(2, c_en, a) for a in (0.0, 0.5, 0.625, 0.75)}},
        note="Planted joint gain 25%. A ratio of two noisy differences is volatile when n is 2-3.")
    rk = R["e005_ranking"]
    add(id="E005-G5/G6", protocol="E005", gate="held-out Kendall tau >= 0.70 and selected design within 10% of best observed CE",
        source=f"{E5}:75-79", planned_n="number of held-out candidates not stated", estimator="point estimate of tau; regret of the argmax",
        label="underspecified", spec_gaps=["m held-out designs", "spread of true CE across designs relative to seed noise"],
        key={"m=10,tau_pop=0.7,nu=0.5": rk["m=10,tau_pop=0.7,noise/spread=0.5"]["p_tau_gate"]["p"], "m=20,tau_pop=0.85,nu=0.5": rk["m=20,tau_pop=0.85,noise/spread=0.5"]["p_both_gates"]["p"],
             "m=20,tau_pop=1.0,nu=1.0": rk["m=20,tau_pop=1.0,noise/spread=1.0"]["p_both_gates"]["p"], "m=20,tau_pop=0.3,nu=0.5_false_pass": rk["m=20,tau_pop=0.3,noise/spread=0.5"]["p_both_gates"]["p"]},
        note="When seed noise equals the spread of true CE across candidates, even a perfect model cannot reach tau 0.7 reliably. The protocol must freeze the spread-to-noise ratio of the candidate set.")
    cb = R["e005_coverage_band_85_95"]["rows"]
    add(id="E005-G7", protocol="E005", gate="nominal-90% intervals have 85-95% empirical coverage",
        source=f"{E5}:79-80,239-241", planned_n="number of held-out outcomes not stated", estimator="observed coverage fraction, two-sided band",
        label="underspecified", spec_gaps=["m held-out outcomes"], key={str(r["m_heldout_outcomes"]): r["p_pass_by_true_coverage"] for r in cb},
        note="A perfectly calibrated model passes only when m is large. Check the 0.9 column.")
    se = R["e005_search_energy_arithmetic"]
    add(id="E005-G8", protocol="E005", gate="search energy <= 25% of one target-scale run", source=f"{E5}:80-83", planned_n="n/a", estimator="energy ratio",
        label=("reasonable at 1B proxies, binding at 7B+" if se["max_full_length_candidates_for_25pct"]["proxy_1B"] >= 10 and se["max_full_length_candidates_for_25pct"]["proxy_7B"] < 10 else "see key"),
        label_basis="arithmetic (inferred scaling)", key=se["max_full_length_candidates_for_25pct"], note=se["assumption"])
    add(id="E005-G4", protocol="E005", gate=">= 2 hardware classes deliver >= 20% of training FLOPs each", source=f"{E5}:47-51,233-234", planned_n="n/a", estimator="accounting",
        label="reasonable (accounting)", label_basis="judgment (not simulated)", note="Deterministic accounting; no sampling noise.")

    # ----------------------------------------------------------------- E006
    dl = R["e006_delivery"]["cp_one_sided_95"]
    r300 = next(r for r in dl["rows"] if r["n"] == 300)
    f80 = 1 - r300["success_prob_for_80pct_power"]
    wa = R["e006_windows_arithmetic"]
    add(id="E006-G3", protocol="E006", gate="event-level lower 95% bound on delivery probability >= 99%", source=f"{E6}:67-70,86-89,193-196",
        planned_n=">= 300 non-overlapping live windows; 30 seeds per virtual cell", estimator="campus-day clustered CI; method not stated; exact CP one-sided assumed",
        label=audit.label_threshold_claim(0.01 / f80) + " (n=300, iid)", spec_gaps=["interval method", "windows per bid level", "clustering"],
        key={"n_needed_zero_failures": dl["n_needed_zero_failures"], "n_needed_one_failure": dl["n_needed_one_failure"], "n_needed_two_failures": dl["n_needed_two_failures"],
             "power_at_n300_true_delivery_0.995": r300["power_by_true_success_prob"]["0.995"], "true_delivery_for_80pct_power_n300": r300["success_prob_for_80pct_power"],
             "max_lower_bound_with_30_seeds_zero_failures": wa["max_lower_bound_with_zero_failures"]["30"],
             "clustered_examples": {kk: v["p"] for kk, v in R["e006_delivery_clustered"].items() if "f_true=0.0005" in kk}},
        note="299 zero-failure events are required. At 300 windows one failure fails the gate. 80% power needs true delivery about 99.95%. A single virtual cell of 30 seeds can never pass (max bound 0.905). Campus-day clustering shrinks the effective n further.")
    add(id="E006-G1/G2", protocol="E006", gate="R_firm >= 20% of load; joint R_firm >= 1.5x best isolated",
        source=f"{E6}:67-70,76-80,158-165,236-237", planned_n="300 windows total; bid grid 5/10/20/30%", estimator="largest bid whose delivery bound passes",
        label=("arithmetically impossible if the 300 windows are split across bid levels; possible only with ~300 per bid" if wa["max_lower_bound_with_zero_failures"]["75"] < 0.99 else "reasonable"), spec_gaps=["windows per bid level"],
        key={"windows_needed_if_each_bid_has_own_sample": wa["windows_if_each_bid_level_needs_its_own_sample"], "event_hours": wa["event_hours_for_that"],
             "max_bound_with_75_windows_per_bid": wa["max_lower_bound_with_zero_failures"]["75"], "isolated_must_be_at_or_below": wa["isolated_best_r_firm_allowed_by_gate_1.5x_if_joint_is"]},
        note="Testing 20% needs its own 299 clean windows. If four bids share 300 windows, each gets 75 and the best possible bound is 0.961. On the 4-point grid, a joint R_firm of 20% needs the isolated best at or below 10%.")
    sl = maxse(8, "point")
    add(id="E006-G6/G7/G10", protocol="E006", gate="TTFT and TPOT SLO attainment fall <= 1 pp, utility <= 1%, in every workload family",
        source=f"{E6}:81-83,240-242", planned_n="aggregated by event/campus-day", estimator="worst of 4 families x (TTFT, TPOT, utility); point vs interval not stated",
        label="underspecified", spec_gaps=["SE per family"], key={"max_se_over_margin_for_80pct_pass_at_zero_harm_F8_point": sl, "same_ci_rule": maxse(8, "ci")},
        note="Twelve simultaneous per-family constraints; per-family SE must be small relative to the 1 pp / 1% margin.")
    rb = R["e006_rebound_every_event"]
    add(id="E006-G11", protocol="E006", gate="30-minute post-event peak <= matched baseline peak + 5%", source=f"{E6}:84-86,243-244", planned_n="n/a",
        estimator="per-event or mean not stated", label="underspecified", spec_gaps=["per-event vs mean"], key={"p_all_300_events_pass_if_per_event_exceedance_prob": rb},
        note="If it must hold for every event, the per-event exceedance probability must be below 0.07% for 80% pass chance at 300 events.")
    add(id="E006-G4/G5/G8/G9", protocol="E006", gate="90% of bid in 10 s; full bid held 900 s; P99 TTFT/TPOT within limits", source=f"{E6}:68-70,230-251",
        planned_n="per event", estimator="per-event pass/fail; P99 estimate", label="folded into delivery probability (see E006-G3)", label_basis="judgment (not simulated)",
        note="If these are part of the event success indicator they only lower the true delivery probability that G3 must show is >= 99.95%.")

    # ----------------------------------------------------------------- E001 / E002 calibration
    nl = R["lc3_nll_gate"]["p_pass_by_true_mean_diff"]
    add(id="CAL-LC3-NLL", protocol="E001-LC3", gate="upper 90% bound of adaptive-minus-fixed NLL <= 0.01", source=f"{E1D}equal-work-calibration-v1.md:67-80",
        planned_n="6 held-out schedules", estimator="percentile bootstrap of the median, 90% interval, 10,000 draws",
        label=audit.label_no_harm(nl["0.0"]["p"]), key={"p_pass_true_diff_0": nl["0.0"]["p"], "0.0033_measured": nl["0.0033"]["p"], "0.01_boundary": nl["0.01"]["p"], "0.02": nl["0.02"]["p"],
                                                          "tau_between_schedules": R["lc3_nll_gate"]["tau_between_schedules"]},
        flags=(["too lax"] if audit.lax(nl["0.02"]["p"]) else []),
        note="NLL differences reproduced exactly across LC3 and PW2, so the 6-value spread is between-schedule heterogeneity, not seed noise.")
    en = R["lc3_energy_gate_pw2_meter_noise"]["p_pass_by_true_ratio"]
    ei = R["lc3_energy_gate_instantaneous_meter_noise"]["p_pass_by_true_ratio"]
    add(id="CAL-LC3-ENERGY", protocol="E001-LC3", gate="upper 90% bound of adaptive/fixed device-energy ratio <= 1.05", source=f"{E1D}equal-work-calibration-v1.md:67-80",
        planned_n="6 pairs", estimator="percentile bootstrap of the median, 90%",
        label=audit.label_no_harm(ei["1.0"]["p"]) + " (with the instantaneous-meter noise actually used)",
        flags=(["too lax at ratio 1.10"] if audit.lax(ei["1.1"]["p"]) else []),
        key={"instantaneous_meter_sd_8.5%": {k: v["p"] for k, v in ei.items()}, "cumulative_counter_sd_3.6%": {k: v["p"] for k, v in en.items()}},
        note="Under the noise of the meter LC3 used, a true ratio of 1.0 or 1.023 fails this gate most of the time: the 'falsified' verdict is not informative about the energy. PW2's reproduction of the same contrast measured 1.023.")
    pw = R["pw2_interaction_gate_standardised"]["p_pass_by_true_mean_over_sd"]
    add(id="CAL-PW2-INT", protocol="E002-PW2", gate="lower 90% bound of 2x2 interaction > 0", source=f"{E2D}checkpoint-energy-calibration-v2.md:266-272",
        planned_n="6 blocks", estimator="percentile bootstrap of the median, 90%", label="n/a (claim has no magnitude)",
        key={"p_pass_by_true_mean_over_sd": {k: v["p"] for k, v in pw.items()}, "observed_mean_over_sd": R["pw2_interaction_gate_standardised"]["observed_mean_over_sd"]},
        flags=(["too lax"] if audit.lax(pw["0.0"]["p"]) else []), note="Read the value at mean/SD = 0 as the false-positive rate of the gate.")
    sn = R["sc1_nll_gate"]["p_pass_by_true_mean_diff"]
    add(id="CAL-SC1-NLL", protocol="E001-SC1", gate="upper 90% bound of adaptive-minus-periodic_local NLL <= 0.01", source=f"{E1D}semantic-consistency-v1.md:101-116",
        planned_n="6 families", estimator="percentile bootstrap of the median, 90%", label=audit.label_no_harm(sn["0.0"]["p"]), flags=(["too lax at diff 0.02"] if audit.lax(sn["0.02"]["p"]) else []),
        key={"p_pass_true_diff_0": sn["0.0"]["p"], "0.01_boundary": sn["0.01"]["p"], "tau_between_families": R["sc1_nll_gate"]["tau_between_families"]},
        note="Between-family SD 0.024 is more than twice the margin; n=6 cannot show noninferiority within 0.01.")
    pa = R["sc1_payload_arithmetic"]
    add(id="CAL-SC1-PAYLOAD", protocol="E001-SC1", gate="upper bound of adaptive/periodic_local payload ratio <= 0.20", source=f"{E1D}semantic-consistency-v1.md:101-116",
        planned_n="6 families", estimator="percentile bootstrap of the median", label=("arithmetically impossible" if pa["payload_ratio_vs_periodic_min_over_families"] > 0.20 else "see key"),
        key={"floor_ratio_vs_periodic_local": pa["payload_ratio_vs_periodic_min_over_families"], "floor_ratio_vs_sync_even_in_best_family": pa["payload_ratio_vs_sync_min_over_families"],
             "periodic_over_sync_bytes": pa["periodic_over_sync_bytes_ratio"], "period_needed_for_10x_vs_sync_ticks": pa["min_period_for_10x_vs_sync"]},
        note="periodic_local is the sparsest of the four available actions (32 state merges vs 256 gradient exchanges = 0.375x sync). No mix of the four can go below 1.0x periodic_local. Even against sync the best possible is about 0.31x, above 0.20x.")
    st_ = R["sc1_time_gate"]["p_pass_by_true_ratio"]
    add(id="CAL-SC1-TIME", protocol="E001-SC1", gate="upper bound of adaptive/periodic_local completion-time ratio <= 0.90", source=f"{E1D}semantic-consistency-v1.md:101-116",
        planned_n="6 families", estimator="percentile bootstrap of the median", label=("arithmetically impossible with whole-policy choices; per-tick mixing unproven" if pa["time_floor_median_over_families"] > 0.90 else "see key"),
        key={"whole_policy_floor_median": pa["time_floor_median_over_families"], "whole_policy_floor_best_family": pa["time_floor_min_over_families"], "p_pass": {k: v["p"] for k, v in st_.items()}},
        note="The best whole-policy schedule is no faster than periodic_local in 4 of 6 families, so the median floor is 0.99.")
    rg = R["sc1_regret_gate_n4"]["p_pass_by_true_regret"]
    add(id="CAL-SC1-REGRET", protocol="E001-SC1", gate="upper bound of normalized regret to hindsight envelope <= 0.10", source=f"{E1D}semantic-consistency-v1.md:101-116",
        planned_n="4 families with a valid oracle", estimator="percentile bootstrap of the median, n=4", label=audit.label_no_harm(rg["0.05"]["p"]),
        key={str(k): v["p"] for k, v in rg.items()}, note="Regret is >= 0 by construction and the envelope contains the adaptive run itself.")
    add(id="CAL-LC3-FLOP", protocol="E001-LC3", gate="attempted-FLOP saving median >= 3%, lower bound > 0", source=f"{E1D}equal-work-calibration-v1.md:67-80",
        planned_n="6 pairs", estimator="percentile bootstrap of the median", label="degenerate (deterministic quantum)", label_basis="arithmetic",
        key={"one_replay_window_fraction": R["lc3_flop_quantum"]["one_replay_window_fraction"], "values": R["lc3_flop_quantum"]["values"]},
        note="Savings are multiples of 16,384/540,672 = 3.03% set by the failure schedule. The 3% bar equals one replay window; it tests the schedule, not the policy.")
    add(id="CAL-LC1-SOONER", protocol="E001-LC1", gate="adaptive median ticks to target < fixed", source=f"{E1D}learning-calibration-v1.md:160-174",
        planned_n="6 schedules; evaluation every 32 ticks", estimator="median of tick counts", label="degenerate in the realised data (both crossed at the first 32-tick observation)", label_basis="judgment (from LC1 write-up; not recomputed)",
        note="Observation grid of 32 ticks forces ties once the target is crossed at the first observation. Taken from the LC1 write-up; not simulated.")
    return rows


def rollup(table: list[dict]) -> dict:
    """Protocol-level verdict by the rule in protocol.md."""
    out: dict = {}
    for row in table:
        p = row["protocol"]
        key = "calibration (E001/E002)" if p.startswith(("E001", "E002")) else p
        d = out.setdefault(key, {"labels": {}, "gates": []})
        lab = row["label"].split(" (")[0]
        d["labels"][lab] = d["labels"].get(lab, 0) + 1
        d["gates"].append((row["id"], row["label"], row["flags"]))
    for key, d in out.items():
        labs = " | ".join(r[1] for r in d["gates"]).lower()
        any_flag = any(r[2] and any("lax" in f for f in r[2]) for r in d["gates"])
        if "impossible" in labs or "implausible" in labs or any_flag:
            d["verdict"] = "inadequate as written"
        elif "underspecified" in labs:
            d["verdict"] = "cannot be classified until n, estimator or noise is frozen"
        elif "marginal" in labs:
            d["verdict"] = "marginal"
        else:
            d["verdict"] = "adequate"
    return out
