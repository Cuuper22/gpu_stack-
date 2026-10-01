# Evidence ledger

Post-hoc re-adjudication of every experiment run that has results. Written to
tell good from bad from wrong. Nothing here was frozen before the runs.

1. **Measured:** one NVIDIA RTX 3060 Laptop GPU (Windows, shared with other apps, 60-90 C),
   a 1,871,232-parameter byte-level transformer on one TinyStories shard, AdamW 3e-4, bf16.
   Each comparison run lasts 7 to 9 s of metered time (LC1 26 s, warm-up 197 s). Two "sites" run
   one after the other on that one GPU. Samples are 6 held-out schedules (n=6), one seed each.
2. **Modeled:** WAN time, modeled completion ("opportunity ticks"), multi-site concurrency,
   payload bytes, facility energy, and all of E001 screen v1 and recovery v2.
3. **Rule:** original verdicts are copied verbatim and never edited. Re-judgments are post-hoc
   and say so. Where evidence cannot decide, the status is UNDETERMINED.
4. **Traceability:** `R:` means `analysis/reanalysis/reanalysis-v1.json`, path under `runs.`.
   Rebuild it with `PYTHONPATH=<repo> <venv>/bin/python -B analysis/reanalysis/reanalyze.py`.
   The script reproduced all 39 original bootstrap intervals exactly (R: top-level
   `reproduction_summary`), so the artifacts and my recomputation agree.
5. **"Preregistered" is not verifiable** for E001 and E002 runs: each protocol and its results
   landed in the same commit (4e83119, a5a069f, 776eb79, c5d7590), 16 minutes (LC3) to a
   few hours after the artifact timestamps. Only E003-E006 protocols predate any result, and they have no results.

Status words. HOLDS: the original verdict stands. OVERTURNED TOWARD SUCCESS / FAILURE: the
evidence points the other way. UNDETERMINED: the data cannot decide. MEASUREMENT INVALID: the
quantity the verdict rests on cannot answer the question.

## Summary table

| Run | Question in plain words | Measured vs modeled | Key effect (90% interval) | Original verdict (verbatim) | Re-judged | Conf. | What would settle it |
|---|---|---|---|---|---|---|---|
| E001 screen v1 | Do cadence rules cut WAN bytes 10x on a 3-site 70B model? | All modeled, n=1 | Bytes 0.125 (fixed) and 0.05 (adaptive) of sync, equal to 1/cycles | `failed_virtual_screen` (fixed_local), `inconclusive` (adaptive_cadence) | HOLDS | high | Nothing. Output is the inputs read back. |
| E001 recovery v2 | Does adaptive recovery beat restart on one failure trace? | All modeled, n=1 | 1.536 s vs 1.584 s; lost work 48 vs 115 PFLOP; energy = 3e-13 J x FLOPs | `inconclusive_frontier_hypothesis` | HOLDS | high | Real multi-site run. |
| LC1 | Does survivor continuation keep progress per FLOP? | Measured loss; ticks modeled | tau -7.2e-14 [-7.2e-14, -5.5e-14]; fixed finishes 84% of the work | `candidate_falsified_small_model_calibration` | MEASUREMENT INVALID | high | Nothing. LC3 replaced it. |
| LC2 v1, v2 | Can time-to-quality compare the policies? | Measured loss | v1 warm-up drift 2.9x its cap; v2 target re-crossed above 15 of 27 later checks | `protocol_failed_warm_start_not_late_stage`, `protocol_failed_calibration_validity` | HOLDS | high | Nothing. |
| LC3 (a) learning, work | At equal work, does adaptive keep NLL and save work? | NLL measured; work arithmetic; ticks modeled | NLL +0.0050 [+0.0013, +0.0086] (t); 6 of 6 worse; margin 0.01 | gates passed in `candidate_falsified_equal_canonical_work` | HOLDS | med | CPU replication, 20+ seeds. |
| LC3 (b) energy | Does adaptive cost more device energy? | Sampled NVML, 100 ms | Ratio 1.068 [1.002, 1.134] vs bar 1.05; valid counter 1.023 [0.985, 1.063] | `candidate_falsified_equal_canonical_work` | UNDETERMINED | med | Owner GPU, cumulative counter, 12+ pairs. |
| PW1 | Does checkpoint cadence explain the energy penalty? | Instantaneous NVML, 20 ms | Meter updates every 0.494 s, not 20 ms; ratios 0.79 and 0.82 | `measurement_invalid` | MEASUREMENT INVALID | high | PW2 already did it. |
| PW2 (a) mechanism | Is the penalty caused by checkpoint cadence, via snapshots? | Cumulative counter | Interaction 2.2e-5 J/token [3.8e-6, 3.9e-5] (t); replay is 57%, snapshot 23% | `checkpoint_cadence_attributed_sparse_continuation_survives` | UNDETERMINED | med | Owner GPU, more blocks, big model. |
| PW2 (b) salvage | Does sparse-checkpoint continuation save energy? | Cumulative counter | Energy 0.970 [0.940, 0.999]; NLL +0.0033; work -3.0% | same string | HOLDS | low | Owner GPU, 12+ pairs. |
| SC1 | Does the observable controller beat the best fixed policy? | NLL measured; bytes and time modeled | Means, t-intervals: NLL +0.0204 [+0.0009, +0.0399], payload 2.05x [1.56, 2.54], time 1.04x [0.975, 1.106] | `abstain_without_policy_claim` | HOLDS | high | CPU replication with controls. |
| E002 rack v3 (PW3) | Can rack phases be dephased to shape power? | No results exist | None | none | not applicable | n/a | Rack hardware. |

## E001 screen v1 and recovery v2: arithmetic, not evidence

The screen has three policies on one modeled scenario. Every number is a scenario input
read back (R:E001_screen_v1). Bytes equal sync cycles x 140 GB x 2 links with zero error.
Energy equals base power x elapsed + 700 W x busy GPU seconds with zero error. The fixed-local
byte fraction 0.125 is exactly 1/8, so "failed" only restates the cadence of 8 against a 0.10
bar. The learning ratio is a declared prior (`screening_prior_not_fitted`), not data.

Recovery v2 has one deterministic trace and four policies (R:E001_recovery_v2). Energy equals
3e-13 J per FLOP x attempted FLOPs plus 5e-10 J per byte, relative error 0.0 in all four rows.
So "adaptive uses less energy" and "adaptive loses less work" are the same fact. Lost work
follows from checkpoint every 1 step vs every 2. Learning progress is the same prior (0.1) for
every policy. The verdict `inconclusive_frontier_hypothesis` is right, and "candidate_better_on_this_trace"
is true but carries no information beyond the scenario. Neither run tests anything about reality.

## LC1: the test could not see the hypothesis

Two parts of the design failed, not the hypothesis.

1. **Estimand.** Progress per attempted FLOP, from scratch, over a fixed horizon. Fixed-restart
   idles during outages and so completes only 84% of canonical tokens (R:E001_LC1.metrics.
   post_hoc_fixed_over_adaptive_canonical_token_ratio, median 0.844). The loss curve is steep
   early, so fewer FLOPs look more efficient per FLOP. All six tau values are negative
   (R:E001_LC1.metrics.tau_progress_per_flop_diff_in_diff). That is the estimator, not learning.
2. **Time to target.** The target is 75% of total improvement. By the first check (tick 32) 79%
   to 81% of it was done, so every run "tied" at tick 32 (R:E001_LC1.first_crossing_resolution).
   The grid was too coarse to rank anything.

What the data do say. At the same 256-tick budget adaptive ended lower in NLL in 6 of 6 strata,
by 0.028 [0.021, 0.035]. That is mostly because it kept training while fixed idled. At equal
attempted compute (curve interpolated at fixed's token count, coarse) the difference is
-0.009 [-0.021, +0.003], not resolved. The original verdict "falsified" is therefore not supported:
the hypothesis was not tested. LC1 also contains a fourth measurement of the energy contrast
(adaptive/fixed 1.066 [1.024, 1.108] with 12.5% more adaptive work, so 0.943 per token).

## LC2: correct protocol stops

V1: the 2,048-tick checkpoint still improved NLL by 0.0863 in its last 256 ticks against a cap
of 0.03 (2.9x). It was not late-stage. V2 passed that gate (0.0045). Its target was then
crossed at ticks 40 and 96, outside the frozen window 192 to 288. After the first crossing,
15 of 27 later checks (C1) and 13 of 20 (C2) were back above the target. Over the whole
256 ticks NLL drifted 0.0093 and 0.0048, only 2.3 and 1.2 times the tick-to-tick wobble (sd 0.004)
(R:E001_LC2.v2_calibration_curve_analysis). At a plateau, first-crossing time is set by noise.
Both stops were right. They say nothing about the policies.

## LC3: one noisy gate decided the verdict

**(a) Learning and work. HOLDS, marginally.**
NLL adaptive minus fixed: +0.0024, +0.0060, +0.0014, +0.0032, +0.0135, +0.0035
(R:E001_LC3.metrics.nll_adaptive_minus_fixed). Mean +0.0050, t-interval [+0.0013, +0.0086],
bootstrap [0.0024, 0.0085] (reproduced), exact order-statistic [0.0014, 0.0135] at 96.9%.
It is worse in 6 of 6 pairs (sign p 0.031), so the cost is small and real, not noise.

*Where 0.01 came from.* The scenario rule: more than twice the NLL span of two fixed
controls (0.004517), rounded up (R:E001_LC3.nll_noninferiority_robustness). Two points are a
weak basis. The 8 fixed-arm final NLLs across seeds have sd 0.0027, so 0.01 is 3.7 sd and
about 1% of NLL. I judge 0.01 defensible and keep it. *Robustness:* the pass is fragile. At
margin 0.0075 it fails (t upper 0.0086). Dropping E1 or E3 pushes the t upper bound to 0.0100, exactly at the margin.
E5 alone is 0.0135. Savings: 3.03% attempted FLOPs is arithmetic (fixed replays 16-32 K tokens);
40 opportunity ticks is modeled. They are not measured wins.

**(b) Energy. UNDETERMINED.** Per-pair ratio (idle-subtracted, sampled):
1.193, 1.134, 1.062, 1.075, 1.002, 0.962 (R:E001_LC3.metrics.energy_ratio_idle_subtracted_sampled).
Median 1.068, bootstrap [1.002, 1.134] (reproduced), t [1.002, 1.141]. Five of six above 1, but
sign p 0.22 and Wilcoxon p 0.094. The gate was an upper bound of 1.05.

*Is it resolvable?* No. Evidence, all from the artifacts:
- The meter updates every 0.494 s (median of 731 value-change gaps in PW1, R:E002_PW1.
  meter_diagnostics). LC3 stops and restarts the meter every 8 ticks: 32 segments of 0.25 s,
  about 2.9 samples each. Each segment sees about one stale reading. The artifact keeps only
  `sample_count`, no timestamps (87-99 samples per run).
- Per-segment energy is clamped at zero when below idle (read from source). The idle baseline
  is 20 reads over about 1 s (about 2 meter updates), one value for all runs. In PW1 the
  idle reading moved 1.5 W between before and after a run (median, max 6 W). The signal is
  only 3 to 4 W above idle (raw 32.5 W fixed, 33.5 W adaptive vs idle 29.4 W).
- Two LC3 calibration pairs have identical weights and tokens, differing only in checkpoint
  cadence. Their idle-subtracted ratios were 0.872 and 0.900 while time ratios were 1.003 and
  1.068. The same arm varies 7.4-7.6% run to run (R:E001_LC3.run_to_run_spread).
- Power of the gate: with LC3's own noise (log sd 0.079) a 6-pair test passes the 1.05 bar only
  38% of the time even if the true ratio is exactly 1.00, and 19% at 1.02 (R:E001_LC3.
  energy_gate_power). A bar the instrument could pass by luck is not a fair falsifier.

*The physical oddity, explained.* Adaptive does 3% less attempted work and finishes 40 ticks
sooner, yet its metered active time is longer: median ratio 1.137 (mean 1.119, t [1.070, 1.168]), 6 of 6 pairs above 1.
The adaptive arm writes 47 checkpoints vs 17. Measured checkpoint copying is +0.50 s of the
+0.89 s mean gap; the rest is not itemized in LC3. PW2 itemizes it (below): dense checkpoints
cost +0.39 s in snapshots and +0.52 s in compute phases around them. The GPU draws only a few
watts above idle on this toy workload, so energy tracks time, not work. Less work saves little;
extra seconds cost the idle floor. Whole-run physical time is shorter for adaptive (median 0.973), probably because
fixed runs 40 more opportunity ticks with 5 more evaluation passes outside the meter (inferred).
So "less time" and "more energy" are both true, on different clocks.

*Same contrast, four meters.* LC3 sampled 1.068; PW1 sampled 0.789 (invalid meter); PW2 raw
cumulative counter 1.023 [0.985, 1.063]; PW2 idle-subtracted 0.707. The spread (0.71 to 1.07)
for one contrast within 80 minutes is larger than the 5% bar. Best instrument: +2.3% energy,
+10% time, interval touching 1.00 and 1.063. Even this still misses the 1.05 upper bar by
about 0.013 to 0.015. Verdict: the energy penalty is probably small and positive (0 to +6%), and the original
bar was not resolvable by the instrument. Not falsified, not cleared.

## PW1: self-invalidated, correctly

32 runs complete; 2 invalidators fire (`insufficient_evaluation_power_updates`,
`insufficient_pooled_cadence_phase_updates`). Requested polling 20 ms, observed value changes
every 0.494 s, 25 times slower. The idle baseline drifts, the selected lag sits at the frozen
boundary. The ratios 0.789 and 0.823 are noise-dominated (idle-subtracted D/A 0.79 but raw D/A
1.005 [0.958, 1.034] in the same runs, so the sign flips with the idle choice). The README
is right to discard it. MEASUREMENT INVALID, high confidence.

## PW2: real but narrower than stated

*Design.* A is sparse+restart (LC3 fixed), B dense+restart, C sparse+continue, D dense+continue
(LC3 adaptive). Interaction is (D-C)-(B-A) per canonical token. 32 runs, counter period 92 ms.
Reproduced exactly from runs (R:E002_PW2.mechanism_attribution).

*What the cumulative counter shows.* Mean raw energy per run: A 166.3 J, B 164.2, C 161.3, D 170.3.
About 80% of each run is idle floor (idle 16.7 W; energy above idle only 32 J of 163 J).
Mean power 20 to 22 W. Dense minus sparse under continuation: +9.0 J (D/C 1.057 [1.005, 1.110]),
+0.95 s (time ratio 6 of 6 blocks above 1). Under restart: -2.1 J, because replay shrinks.

**(a) Mechanism. UNDETERMINED.** Three gates passed, but:
- Total interaction 2.24e-5 [2.2e-6, 3.5e-5] J/token (reproduced); t [3.8e-6, 3.9e-5]. Five of
  six blocks positive (E5 is -1.7e-5); exact Wilcoxon p 0.0625, sign p 0.22.
- Replay compute is the largest term (57% of the mean total, 6 of 6 blocks above snapshot),
  snapshot 23%, compute phases 17%. The "checkpoint-related group" excludes replay by definition
  (27% of total). So the claim that snapshot writing drives the penalty is not supported. The
  defensible claim is "dense checkpointing changes energy through two paths that partly cancel".
- Gate 3, penalty-removed fraction >= 0.5, is vacuous: values 11.1, 2.69, 1.30, -1.16, 2.84, one
  block dropped, denominators 0.7 to 16 J out of 160. A fraction above 1 is not physical.
  Interval [-1.16, 11.1].
- Idle-subtracted sensitivity 3.98e-6 [-8.0e-6, 1.2e-5] crosses zero. The primary is raw
  energy, which is a defensible choice, but it means 80% of "energy" is the idle floor.
- Label bug: the field `idle_subtracted_gpu_board_energy_j` holds raw energy in PW2 (max diff
  0.0). So PW2's "LC3 corner" 1.023 is raw, while LC3's 1.068 is idle-subtracted. Different
  quantities share one bar of 1.05.

**(b) Sparse continuation. HOLDS, small.** Energy C/A 0.961 median [0.952, 1.003] (reproduced);
t [0.940, 0.999], mean 0.970. Five of six below 1, Wilcoxon p 0.16. NLL +0.0033 (same six
pairs as LC3, bitwise), work -3.0%, 40 ticks (modeled). The energy saving matches the work
saving, which is what one expects, and is small. This is the only positive survivor in E001/E002.

## SC1: the controller loses; the gates were mostly unreachable

**(i) The 0.20x payload gate was arithmetically unreachable. Verified.** The comparator is
periodic_local, which moves 2.86 MB per two-site tick (one 22.5 MB state average per 8 ticks).
Every other action moves at least 7.5 MB per two-site tick, 2.63x more (R:E001_SC1.
payload_gate_arithmetic). One-site ticks move 0 bytes under every action. So adaptive can at
best equal periodic_local (ratio 1.0). Observed: min 1.000, max 2.667, none below 1. A 0.20
bar needs an action about 5x sparser than any available (one average per 40 ticks, not 8). Even
periodic_local is only 0.375 of synchronous bytes, so the original 10x hypothesis was also out
of reach. **The 0.90x time gate is also unreachable in these families:** the best
learning-valid schedule, hindsight included, is never 10% faster than periodic_local (R:E001_SC1.
completion_gate_arithmetic). Only E6 shows 0.906, and its schedule has +0.065 NLL.

**(ii) The abstentions came from scenario authoring. Verified.** Calibration floor for site A
compute rate is 0.80. Evaluation families set 0.75 (E2), 0.65 (E4), 0.70 (E6) in the segments
where site B is down. Abstention ticks (32, 48, 24 = 104) equal those single-site ticks
exactly, on the single dimension `site_a_compute_rate_factor`. In those ticks the controller
takes `exact_forward_recovery` whether or not it abstains (also in E6's 16 non-abstaining
single-site ticks, rate 0.80). So abstention changed no action. SC1's own write-up says it was
unintended. It is not a capability to praise.

**(iii) periodic_local beats synchronous on NLL in every family. Verified, mechanism not.**
10 of 10 (4 calibration, 6 held-out): -0.0187 [-0.0201, -0.0174], sign p 0.002; at 0.375 of
the bytes and 0.71x median modeled time. Delayed-one-step is worse in 10 of 10 (+0.047). Same
tokens, same optimizer, same LR. Consistent with weight averaging at a constant-LR plateau
(inferred). Not separable from per-replica clipping or Adam-moment effects: no control arm
exists. One seed per family, one model.

**(iv) The adaptive losses are real. Verified.** Adaptive minus periodic NLL: +0.0018, +0.0003,
+0.0214, +0.0143, +0.0191, +0.0654. Six of six positive (sign p 0.031), four above the 0.01 margin,
t-interval [+0.0009, +0.0399]. Payload above 1 in 5 of 6 (median 2.13x). Time 4 of 6 slower,
ratio 1.04 [0.975, 1.106], not resolved. Regret 0.0715 on n=4, bootstrap upper 0.1006 vs 0.10, t upper
0.126: borderline, UNDETERMINED as a single gate. The controller's medium-bandwidth or imbalance rule
picks delayed-one-step in E3 and E6, which calibration had already shown to be worst for NLL.
Under any bar that is not unreachable ("no worse than the comparator") it still fails. No
rescue is warranted. Against the naive baseline it does help: vs synchronous, time 0.69x
[0.58, 0.81], payload 0.74x, NLL +0.002 [-0.019, +0.023].

## E002 rack dephasing v3 (PW3)

No result file exists under `experiments/e002-*/results/` or `docs/data/`
(R:E002_rack_dephasing_v3). Only `checkpoint-rack-telemetry-v3.example.json`, an example. Nothing
to adjudicate. The site's 404 on `e002-rack-dephasing-v3.json` is consistent with this.

## Claims in README/RESEARCH.md the evidence does not support

1. README:34 "predicts what a training run does to time, power, and money, says how sure it is."
   No held-out prediction by the graph has been made. Every E001 time and energy number is either
   a scenario input read back or a one-GPU toy measurement.
2. README:32, 292, RESEARCH.md "preregistered", "written down before the run." Not verifiable
   for E001/E002: protocol and results share commits and the runs preceded them by minutes.
3. README:298 and 309, RESEARCH.md SC1 paragraph: abstention as "a logged I do not know" and
   "the most honest thing in this repository." Abstentions are inert and authoring-induced (SC1 (ii)).
4. RESEARCH.md SC1 paragraph and docs/research/results-log.md ("Every frozen gate failed") count four
   gate failures against the controller. Two of the four could not be met by any available
   action, so they add no information. The failure still holds, on the other two gates.
5. README:355 "boring baseline is hard to beat" for LC1 through SC1. True for SC1 only
   (periodic_local). LC1 and LC3 compare restart against continuation, not against it.
6. README:355 "adaptive recovery ... much less lost work, less modeled energy." Arithmetic
   from the scenario (energy = 3e-13 x FLOPs), not an independent result.
7. README:391 "LC3 exposed the energy failure." The energy failure is unresolved. Also
   "PW2 attributed the supported local effect to checkpoint cadence": see PW2 (a); replay
   dominates and one gate is vacuous.
8. RESEARCH.md:251 and docs/research/results-log.md:171 "All three mechanism gates passed" (PW2). One of three is vacuous,
   one is borderline at n=6, and the idle-subtracted view crosses zero. RESEARCH.md:259 and the results log
   do disclose the last point; README does not mention it.
9. `experiments/e001-.../experiment.md` line 3, "LC1 and LC3 candidates falsified". LC1 was an
   invalid estimand; LC3 rests on an unresolved gate.

## Good results that were under-sold

1. **SC1 periodic_local** lowers held-out NLL by 0.0187 [0.0174, 0.0201] vs synchronous in 10 of 10
   families at 0.375x bytes and about 0.7x modeled time. It was treated as "the baseline".
   It is the most interesting measured finding, subject to a mechanism control.
2. **SC1 adaptive vs synchronous:** time 0.69x [0.58, 0.81], payload 0.74x at equal NLL.
3. **PW2 sparse continuation:** about 3% less energy, 3% less work, +0.003 NLL, 40 modeled
   ticks fewer. Passes every gate under a valid meter.
4. **LC1:** at an equal opportunity budget adaptive ended 0.028 NLL lower in 6 of 6 strata. That is the
   practical value of survivor continuation, discarded because of the per-FLOP estimator.
5. **Validity checks worked:** LC2 stopped on two valid protocol failures, PW1 invalidated
   itself. The finding that NVML polled at 20 ms updates every 0.494 s is reusable for any
   energy work on this machine.

## What can be settled without new hardware

- **LC3 NLL non-inferiority.** Pair sd of the NLL difference is 0.0044. With 20+ CPU seeds
  the standard error falls to about 0.001, enough to separate 0.005 from 0.01.
- **SC1 periodic_local vs synchronous.** CPU replication with controls: synchronous plus
  iterate averaging, periodic with period 1, shared vs separate Adam state, 5+ seeds per family.
- **SC1 rescoring.** Replace the two unreachable gates with "no worse than periodic_local"
  and rescore. Done here from the paired metrics: payload 2.05x and time 1.04x [0.975, 1.106] still fail it.
- **Modeled quantities for new controllers.** Bytes and time depend only on the action
  schedule, so alternative controllers can be scored without training. Only their NLL needs runs.
- **Power planning.** Required pairs for any energy gate (R:E001_LC3.energy_gate_power,
  R:E002_PW2.gate_power_pw2): at PW2 noise a 6-pair test passes 1.05 only 72% of the time at a true 1.00.
- **Another agent's CPU replication** (`experiments/r001-cpu-replication`) exists but is not
  reviewed here.

## What needs the owner's GPU

- Any energy claim. Use the cumulative energy counter, record idle before and after each run,
  randomize arm order, nothing else on the GPU, locked clocks, 12 or more pairs.
- A model large enough that board power is far above idle. At 3 to 4 W above idle, energy is
  just the idle floor times time, and checkpoint cost does not transfer to real training.
- Report time and energy together. Do not subtract an idle baseline measured once.
- Any real WAN, multi-site concurrency, or rack (PW3) claim.
