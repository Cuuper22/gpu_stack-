# P001 result: protocol power audit

Run against protocol frozen at c3dfe91. Full run: n_sim 10,000 (some modules 20,000 or 40,000),
2,000 bootstrap draws, seed 20261001, 738 s on 1 core. Output:
`results/full/results.json`, `results/full/gate_table.json` (git HEAD, input hashes, seeds inside).
Exact (binomial, noncentral t) numbers have no Monte Carlo error. Monte Carlo rates have 95%
Wilson intervals in the JSON (half-width at most 0.01 here).

## Verdict by frozen rule (protocol.md, "Protocol-level verdict")

| Protocol | Verdict | What drives it |
|---|---|---|
| E003 | inadequate as written | G2 impossible if unpaired; G3 impossible at n=100; G10 too lax |
| E004 | inadequate as written | only because G9 is too lax at small m (m not stated); no gate impossible; G3 marginal |
| E005 | inadequate as written | G2 implausible under the interval reading; most others underspecified |
| E006 | inadequate as written | G3 needs true delivery 99.93%; G1/G2 impossible if windows are split by bid |
| E001/E002 calibration | method check passed | see below |

"Inadequate as written" does not say the ideas are wrong. It says the gates cannot give a
trustworthy pass or fail as worded. E004 and E005 are closer to fixable than E003 and E006.

## Gates labelled impossible, implausible, or too lax

E003
- G3 interception, lower 95% bound >= 99%, planned n >= 100 events per family: impossible
  at n=100 (best bound 0.970). Needs 299 events with zero misses (one-sided exact), 368
  (two-sided), 268 (Wilson), 473 with one miss. At n=300 power is 0.222 if true recall is
  99.5%; 80% power needs true recall 99.93% (miss rate 13.4x lower than the claimed 1%).
- G2 per-run region, 95% of runs inside +-0.2 clean SD: if the region is centred on the clean
  mean, a defense identical to clean puts only 15.9% of runs inside, so impossible. If paired
  by seed it needs a per-run offset SD <= 0.102 clean SD (pass probability at n=100: 0.70 at
  0.10, 0.62 at 0.102, 0.0001 at 0.15). SC1 shows exact arms (sync vs forward recovery)
  differ by exactly 0, so exactness is reachable only for exact-semantics defenses.
- G10 baseline-match falsifier: too lax. If the closest baseline is identical to the joint
  policy, the hypothesis "survives" with probability 0.226 (K=5 outcomes) or 0.487 (K=13). A
  baseline better on one outcome survives with 0.80 (K=5, n=30): direction is not in the rule.

E004
- G9 coverage >= 80% at nominal 90%: too lax for few outcomes. A model with true coverage 70%
  passes 0.383 (m=10), 0.238 (m=20), 0.079 (m=50), 0.016 (m=100). m is not stated.

E005
- G2 no task metric regresses > 2%: under the interval reading, zero true harm passes with
  probability 0.016 (F=5, 3 runs, 1.4% noise) and about 0.00003 (2 runs, 3% noise). Under the
  point reading it is 0.83 and 0.23. The reading is not stated.

E006
- G3 delivery bound >= 99% at 300 windows: same arithmetic as E003-G3 (299 zero-miss windows,
  473 with one). 80% power needs true delivery 99.93%. With 3 windows per campus-day and
  within-day correlation 0.1, effective n drops below 299 and pass probability is 0 even at a
  true 99.95%. A 30-seed virtual cell can never pass (best bound 0.905).
- G1/G2 R_firm >= 20%: impossible if the 300 windows are shared across the four bid levels
  (75 each, best bound 0.961). One 20% bid needs 299 clean windows; four bids need 1,196
  windows (299 event-hours).

## Underpowered or underspecified (numbers needed to make them adequate)

- E003-G1 quality equivalence (K=4 assumed): 80% power at 10 paired runs if the paired offset
  SD is <= 0.1 clean SD, 30 at 0.25, 100 at 0.45 (with Bonferroni: 0.80 at 30 runs for 0.25,
  0.88 at 100 runs for 0.45). LC3's measured recovery policies shift NLL by 0.10 to 0.98 clean
  SD (median 0.24), so +-0.2 SD holds only for exact defenses.
- E003-G4 false action <= 1%: 17,782 independent clean steps for 80% power at true 0.8%.
  Steps are clustered by run, so the real n is runs.
- E003-G5/G6 2% tax: with measured paired SD 3.6%, 22 pairs for 80% power at true tax 0, 80
  at true tax 1%; at SD 8.5%, 112 and 444. At 6 pairs power at true tax 0 is 0.325.
- E004-G1/G2 gains: point-rule SE must be <= 0.059 (20% gate) and 0.030 (10% gate); lower-bound
  rule <= 0.020 and 0.010. At 30 trace-days and 10% CV all four readings are reasonable except
  G2 interval (excess 1.46, marginal); at 8 clusters G2 interval needs 1.98x.
- E004-G3 interaction >= 0.05: 30 clusters, 5% cell CV: power 0.464 at the claim, 0.652 at
  0.0625, 0.963 at 0.10 (marginal). With within-cluster correlation 0.8: 0.865 at 0.0625. At 8
  clusters: 0.33. False pass at 0: 0.024 (n=30), 0.052 (n=8).
- E004-G6/G7 and E006 SLO/utility: worst-of-F needs per-family SE <= 0.62 margin (point, F=4)
  or 0.31 (interval); F=8: 0.52 and 0.28. E004 ranking has no numeric threshold.
- E005-G1 CE >= 25%: point rule reasonable (excess 1.05 to 1.12 at 2 runs). Interval rule at 2
  runs needs 1.57x (3.6% noise) or 2.35x (8.5%); at 3 runs 1.35x. E005-G3 reasonable (0.85 to
  0.89 at 1.25x claim; false pass at 0 is 0).
- E005-G5/G6 ranking: even a perfect model passes only 0.53 to 0.56 when seed noise is half the
  design spread, and 0.03 to 0.12 when equal. Model at the claimed tau 0.70: 0.25 (m=10) and
  0.14 (m=20) at noise/spread 0.5.
- E005-G7 coverage band 85 to 95%: perfect calibration passes 0.39, 0.75, 0.77, 0.94 at m=10,
  20, 50, 100. True coverage 0.8 still passes 0.13 at m=100.
- E005-G8 search energy (inferred C=6ND, D=20N): about 245 full-length candidates at 1B
  proxies, 5 at 7B, 1.4 at 13B.
- E006-G11 rebound if per event: needs exceedance probability <= about 0.07% for 80% pass at 300.
- Reasonable or accounting: E003-G9, E005-G4, E004-G4/G5 (but satisfiable by churn).
  E003-G7/G8 not evaluable until fleet incidence exists.

## Method check against E001/E002 (passed)

- SC1 payload <= 0.20x: impossible. Floor is 1.00x of `periodic_local` (it is the sparsest of
  the four actions: 0.375x sync). Even versus sync the best family floor is 0.313x.
- SC1 time <= 0.90x: whole-policy floor median 0.993, best family 0.906. Simulated pass
  probability at a true 0.90 is 0.055.
- LC3 energy <= 1.05 with the 8.5% noise of the meter it used: pass probability 0.356 at true
  ratio 1.00 and 0.178 at PW2's measured 1.023 (0.002 at 1.10). So 64% to 82% of the time the
  gate would call "falsified" with no real penalty. With PW2's 3.6% counter noise: 0.894 and 0.495.
- LC3 NLL gate was well powered (0.998 at true 0, 0.054 at the margin). SC1 NLL gate was not
  (0.236 at true 0; between-family SD 0.0237 is over twice the 0.01 margin). PW2 interaction
  gate: false pass 0.054, power 0.675 at the observed mean/SD of 1.0. SC1 regret (n=4): 0.60 at
  true 0.05, 0.34 at the observed 0.072.
- Bootstrap median coverage (nominal 90%): 0.889 at n=6 (one-sided miss 5.5%), 0.817 at n=4
  (one-sided miss 9.1%), so n=4 is anti-conservative.
- LC3 FLOP gate is a schedule quantum (3.03% = one replay window), not a policy test.

## Proposed minimal fixes (post-hoc computations, proposals only)

- Interception and delivery (E003-G3, E006-G3): state the interval and n. Either keep 99% and
  require >= 299 events per family (zero misses) or 473 events (one miss); or set the bound at
  95%: 59 zero-miss events, 124 events for 80% power at true 99% (allows 2 misses).
- E003-G2: define the region as paired by seed and require exact-semantics defenses, or replace
  with a CI on the paired fraction at the SD-implied level.
- E003-G10 and E006 match rule: make it directional (joint better on a pre-named primary
  outcome, with Holm correction, and not worse beyond a margin).
- E003-G1/G4/G5: freeze n >= 30 paired runs, K, and n >= 22 pairs (80 if tax margin is tight).
- E004: freeze the cluster count (>= 30), point or interval reading, and m >= 100 for coverage;
  add a numeric ranking gate.
- E005-G2: test the mean over families, or pre-name primary families, and state the reading.
  G5/G6: freeze m and require noise/spread <= 0.25. G7: m >= 100.
- E006-G1/G2: give each tested bid its own 299 windows, or test only the claimed 20% bid.

## Deviations and caveats

- Protocol lines 149 to 150 mention `results/smoke/`; the coordinator deleted it before freezing.
- `results.json` records git HEAD e3265f5, a descendant of the freeze commit; no P001 file
  changed since the freeze.
- Match-rule cells at n_pairs=100 are null: scipy's noncentral t returned NaN for large
  noncentrality. Post-hoc normal approximation, K=5, baseline better on one outcome: about 0.999
  survival (outside the frozen outputs). All n=30 cells computed.
- E003-G3 label came from n=100 (the stated floor); G3 and E006-G3 labels under "requires
  implausible effect" use iid events.
- Labels are idealised (normal noise, independent gates), so power is an upper bound.
- The fix numbers above were computed after the run and are not in `results.json`.
