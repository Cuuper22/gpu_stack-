# P001: Can the frozen protocols tell a real effect from no effect?

Stage 1 (protocol and code only), 2026-10-01. Not yet frozen. No full run done.

## Question

E003, E004, E005 and E006 were frozen as "preregistered" designs but never run. E001 and E002
were run. For each gate in each protocol: with the planned sample size, estimator and
threshold, can the gate (a) pass when the claimed effect is real and (b) fail when there is no
effect? The E001/E002 gates are audited the same way, as a check of the method against
results that already exist (for example SC1's 0.20x WAN gate).

## Why it matters

A gate that cannot pass, or passes by chance, produces a verdict that says nothing about the
idea. Earlier reviews found verdicts in both directions that turned on such gates. E006's
"lower 95% bound >= 99% delivery" already needs 299 zero-failure events (0.99^n <= 0.05).
Auditing the gates before anyone spends compute on E003-E006 is cheap.

## What is computed

1. Gate table. For each gate: statement, source file and lines, planned n or replicates,
   estimator and interval method, and where the protocol is silent (`spec_gaps`).
   Hand-extracted from `experiments/e00{3,4,5,6}-*/experiment.md`. The thresholds are checked
   against `gpu_stack/research/programs.py` (`E00x_PROTOCOL.falsifiers`) at run time; any
   mismatch is reported.
2. Arithmetic checks (exact, no simulation): minimum n for a bound to be reachable, the
   floor of what the available actions can do (SC1 payload and time), the quantum of a
   discrete statistic (LC3 attempted-FLOP saving), windows needed per bid level (E006).
3. Power and false-pass rate. Synthetic worlds with a planted effect equal to the claim, and
   null worlds. The protocol's own decision rule is applied to each synthetic data set.
   Exact binomial or noncentral-t formulas where they apply; Monte Carlo otherwise, with
   Wilson 95% intervals on every Monte Carlo rate. The E001/E002 rule (percentile bootstrap of
   the median of 4 to 6 values, 90% interval) is simulated exactly as the repo codes it.
4. Break-even noise. Where no noise was ever measured, the largest noise at which the gate
   is still adequate, so the protocol can freeze a noise estimate and be checked against it.

## Inputs

- Protocol text: the four `experiment.md` files above (SHA-256 recorded by `run.py`).
- Machine-readable protocols: `gpu_stack.research.programs.E003_PROTOCOL` .. `E006_PROTOCOL`.
- Measured noise, read from published results (SHA-256 recorded):
  `equal-work-v1.json` (LC3), `learning-calibration-v1.json` (LC1),
  `semantic-consistency-v1.json` (SC1), `checkpoint-energy-v2.json` (PW2). Used values:
  SD of paired NLL differences across 6 schedules (LC3); SD of paired energy ratios
  (PW2 cumulative counter, 6 pairs, and LC3 instantaneous meter, 6 pairs); SD of final NLL
  across the 10 SC1 seeds for the exact-sync arm (clean seed spread); exact equality of the
  sync and forward-recovery arms (paired noise floor of exact-semantics arms); SC1 per-action
  payload bytes and completion times.
- Everything else (E003 K and n, E004 trace-day count and CV, E005 CE noise, E006 clustering)
  was never measured. Those are swept and labelled "assumption". Nothing is invented as fact.

## Decision criteria (fixed before any full run)

Each gate gets one label. The cutoffs are conventions; the report also gives the raw numbers.

- D1 arithmetically impossible: no possible outcome passes at the planned n (pass
  probability exactly 0). No judgment involved.
- D2 power. Two cases, because "claim = threshold" matters.
  - Threshold claims ("improves by at least X", "recall at least 99%"): the claim sits on the
    threshold, so power at the claim is at most 0.5 for a point-estimate rule and at most
    0.05 for a lower-bound rule, by construction. So we ask for 80% power at an effect
    1.25 times the claim (failure rates: at one fifth lower than the claim). Reasonable if
    that holds, marginal if 80% power needs up to 2x the claim, otherwise "requires
    implausible effect". The effect for 80% power is always reported.
  - No-harm claims (equivalence, noninferiority): power at true harm 0. Reasonable if
    >= 0.8, marginal if 0.5 to 0.8, otherwise "requires implausible effect" (it would need the
    treatment to be better than the claim).
  - Why 0.8: the usual convention. Why 1.25: gives a stated, small cushion; a gate that
    needs more than double the claim has no useful power at the claim.
- D3 too lax: false-pass probability above 0.10 in a world where the hypothesis is false.
  The false world is: zero effect (superiority), harm of 2 times the margin (noninferiority
  in E001/E002), 1.5 times the margin (E003 equivalence), true coverage 10 points below the
  floor (coverage). Why 0.10 and not 0.05: the gates are used in conjunction and the project
  has a history of weak results being praised, so a tighter limit is not demanded, but a
  false-pass rate above 10% on a single gate is not tolerated.
- D4 underspecified: n, interval method, number of metrics or direction is not stated, so no
  single label is defensible. The report gives the n (or noise) at which it would become
  adequate.
- Protocol-level verdict: adequate only if every statistical gate is reasonable (or an exact
  accounting identity) and none is too lax. Inadequate if any gate is impossible, requires an
  implausible effect, or is too lax. Otherwise "cannot be classified until frozen" if any gate
  is underspecified, else "marginal".
  The conjunction of k gates is also reported under independence, as an upper bound on joint
  power.
- The E001/E002 calibration passes if the method reproduces what the data already show:
  SC1 payload gate impossible (floor 1.0x of `periodic_local`), SC1 time gate impossible at
  whole-policy level, LC3 energy gate uninformative at the 8.5% noise of the meter it used.
  If a case the data already settle comes out the other way, the method is wrong and the
  study is reported as failed.

## Analysis plan, by gate family

| Family | Rule simulated | Worlds |
|---|---|---|
| Binomial bounds (E003 interception, false action; E006 delivery) | exact Clopper-Pearson one-sided and two-sided, Wilson one-sided; clustered by beta-binomial with design effect | true rate grid; windows per bid level; campus-day clustering |
| Equivalence (E003 quality vector, per-run region) | 90% t interval per metric inside +-0.2 clean SD; per-run fraction >= 95% | K=4 metrics, paired-offset SD 0 to 0.45, n 10 to 200 |
| Tax upper bounds (E003, E002 time) | paired t upper 95% bound <= 2%, exact noncentral t | per-pair SD from PW2 and LC3, n 6 to 200 |
| Improvement gates (E004 U, E005 CE) | point rule and lower-95% rule, exact | break-even SE; n clusters or runs |
| Three-way interaction (E004) | point >= 0.05 and cluster-bootstrap lower bound > 0 | n 8/30/100, cell CV 2/5/10%, within-cluster correlation 0/0.8 |
| Attribution fraction, ranking (E005) | ratio of differences; Kendall tau and regret | n 2/3/5; m 10/20/50; spread-to-noise 0.25 to 1 |
| Conjunctions, coverage, match rule | worst-of-F noninferiority; observed coverage; "no baseline matches on all outcomes" | F 1 to 12; m 10 to 1000; K 5 and 13 |
| E001/E002 median-bootstrap gates | percentile bootstrap of the median, n 4 and 6, 90% | measured SDs; planted true effects incl. the measured value |

## Compute

Single core, no GPU. `--smoke`: about 10 s. `--full`: n_sim 10,000 and 2,000 bootstrap draws,
about 12 minutes (from a timed 1,000-sim run of 74 s), under 2 GB RAM. Seed 20261001.

## What each outcome means

- A gate labelled impossible or implausible: the protocol cannot confirm its own hypothesis as
  written. A "falsified" verdict from it later would mean nothing about the idea.
- Too lax: a "pass" from it would mean little.
- Underspecified: the protocol needs a frozen n, method, or noise estimate before it is run.
- Reasonable: the gate can tell a real effect from none, under the stated noise.
- The audit never says whether a hypothesis is true.

## Known limitations

- Worlds are idealised: normal noise, independent gates, equal effects across families.
  Real data will be messier, so power here is an upper bound.
- E003-E006 have no measured noise. Anchors from E001/E002 are a small byte-level model on
  one laptop GPU; they are used only as scale references for relative noise.
- Gate wording is sometimes ambiguous (point estimate vs interval). Both readings are run and
  the machine-readable falsifier's reading (a scalar compared with a threshold) is noted.
- The E001/E002 per-schedule differences are deterministic on rerun (PW2 reproduced LC3's six
  NLL differences exactly), so the 6 values measure heterogeneity across failure schedules,
  not seed noise. The bootstrap there answers "across schedules".
- Per-tick action mixing in SC1 is not simulated; the time floor is for whole-policy choices.
- Percentile-bootstrap draws are 2,000 per data set, not the 10,000 the repo uses; the
  difference is Monte Carlo noise in a quantile and is negligible next to n=6.
- This audit does not check literature claims or the scientific merit of E003-E006.

## Disclosures

- The E001/E002 result artifacts were read as inputs before this protocol was written. They
  are existing results, not outcomes of this study.
- Three arithmetic facts were derived by hand before coding: 299 events for a 99% one-sided
  bound; the SC1 payload floor; the 3.03% LC3 replay quantum.
- Smoke runs (n_sim 150, plus one timing run at 1,000) were looked at to check the code.
  They are not results and no criterion above was changed after seeing them.

## Files

`run.py` (entry point), `audit.py` (modules and assumptions), `sims.py` (simulations),
`gates.py` (gate table and labels), `inputs.py` (measured inputs), `pstat.py` (helpers),
`selftest.py` (closed-form checks). Output: `results/<mode>/results.json` and
`gate_table.json`, with git HEAD, input hashes, seeds and runtime. Smoke output is in
`results/smoke/`.
