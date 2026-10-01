# R001 result: CPU replication of the E001 learning results

Protocol frozen at 054063240129aaebcb2395e1dc2a66eca659b5d6 (`protocol.md`). Run 2026-10-01,
level L2, 4 workers, 7,251 s wall-clock (about 2.0 h) on 4 CPU cores shared with other studies.
All study code and `scenario.json` have the same SHA-256 as at manifest time
(`results/manifest.json`); the repo HEAD recorded there (456a755) is later than the freeze
because other studies committed in between. Dataset SHA-256 matched. No energy was measured.
Numbers: `results/analysis.json`, `results/calibration.json`, raw tasks in `results/raw/`.

## What was run

L2 = 2 calibration warm seeds (9101, 9102) and 5 evaluation warm seeds (8101-8105), each an
8192-tick warm start on CPU bf16. All 7 passed the late-stage gate (final-256-tick NLL gain
0.0007 to 0.0101, limit 0.03); none dropped. Q1: 15 fixed-vs-adaptive pairs (3 per seed).
Q2: 10 SC1 cells (2 per seed) with arms sync (+EMA), periodic_local, sync + cosine.
Optional arm D (periodic_local + cosine) was not run at L2.

## Calibration (calibration seeds only)

- Fixed policy, no failures, 2 warm seeds x 3 streams: final NLL 1.0142 to 1.0338, SD 0.00808
  (between-warm-seed SD 0.0094, within 0.0035). The original E1-E6 SD was 0.0028 with one
  warm seed, so fresh warm seeds add most of the spread.
- Margin rule gives 2 x SD = 0.0162, capped at 0.010. **delta = 0.010**, the original margin.
- Adaptive vs fixed with no failures: final NLL, attempted tokens and whole curve bitwise
  identical on both calibration seeds. The CPU port is deterministic and equivalent.
- SC1 EMA decay with lowest mean NLL on C1/C4 cells: 0.99 (the largest on the grid; NLL fell
  monotonically with decay, 1.0216, 1.0090, 0.9962, 0.9900 for 0.9, 0.95, 0.98, 0.99).

## Q1 verdict (frozen criteria)

Criteria: `non_inferior` if the upper CI bound of mean(adaptive - fixed) <= delta; `inferior` if
the lower bound > delta; otherwise `not_shown_non_inferior`. Unit = warm seed, 90% t-interval, 4 df.

- Per-seed mean adaptive-minus-fixed NLL: 0.0083, 0.0141, 0.0086, 0.0079, 0.0110.
- Mean **0.00998, 90% CI [0.00749, 0.01248]**. Upper bound 0.0125 > 0.010; lower bound 0.0075 < 0.010.
- **Verdict at delta = 0.010: `not_shown_non_inferior`.** At the original 0.010 margin: the same
  number, since delta equals it, `not_shown_non_inferior`.
- Descriptive: all 15 pairs positive (adaptive worse), median 0.0106, range 0.0024 to 0.0221,
  8 of 15 above 0.010. 14 pairs had 2 failures (mean 0.0098), 1 had 3 (0.0127). The original
  six pairs had mean 0.0050.
- Cost side (exact counts, ticks are modeled): attempted-token saving 3.6% [2.8%, 4.4%];
  opportunity-tick saving 44.8 [42.7, 46.9]. All 15 pairs reached the canonical target; no
  adaptive divergence.

Reading: the adaptive deficit here is about twice the original and its interval sits around the
margin. The data neither show non-inferiority nor show it is worse than 0.010. Planning power
(protocol) was low for a true deficit near 0.010, so this is the expected "cannot tell" zone.
The work and tick savings replicate. Why the deficit is larger than in the GPU run (CPU bf16,
fresh warm seeds, the inferred schedule distribution) was not tested.

## Q2 verdict (frozen criteria)

- Advantage of `periodic_local` over exact sync: mean(sync - local) **0.0209, 90% CI
  [0.0194, 0.0225]**. Criterion lower bound > 0.005: **replicated**. Calibration cells gave 0.0205.
- EMA control (decay 0.99): explained fraction f = (A - EMA)/(A - B), per-seed 2.99 to 3.34,
  **mean 3.21, 90% CI [3.08, 3.34]**. Criterion `mostly_explained` if lower >= 0.75:
  **`mostly_explained`**. f above 1 means the EMA beat periodic_local by about twice the
  advantage itself: sync 1.038 to 1.064, local 1.014 to 1.045, EMA 0.970 to 1.000 (cell values).
- Cosine LR to ~0 (arm C): f_cos **3.17 [3.03, 3.31]**, `mostly_explained`. EMA and cosine
  agree within 0.003 NLL in every cell.
- Other decays (descriptive): f = 1.71, 2.30, 2.90, 3.21 for 0.9, 0.95, 0.98, 0.99; every
  tested decay clears 0.75.
- "Advantage vanishes under cosine" (arm D): not computed, arm not run.

Reading: at constant LR 3e-4, exact sync sits on a noise plateau. Averaging weights in time
(EMA) or decaying the LR removes that noise and gets far below `periodic_local`. So SC1's
`periodic_local` advantage is a plateau-noise effect that periodic averaging only partly
recovers; it is not evidence that infrequent communication helps learning. Not separated:
batch-4 vs batch-8 gradient noise, and whether `periodic_local` plus a schedule keeps any edge
(arm D). The best decay was at the grid edge, so the true best EMA may be slower still.

## Deviations from the protocol (honest list)

1. **Level.** The frozen rule says to run the richest level projected <= 3.0 h, else wait or
   not run. `run.py probe` projected L0 5.1 h, L1 4.3 h, L2 3.8 h at 20:19 (load from V001,
   P001, a test suite), and L2 4.2 h at the second probe (2.54x the quiet rate). Nothing fit.
   I started L2 on the coordinator's instruction anyway. Actual wall-clock was 2.0 h, so the
   probe over-projected by about 2x; its constants were rough.
2. **Failed waiting attempt.** I first started a background load-watcher to wait for a quiet
   machine. My own `pkill` killed it (exit 144). No stage-2 task had run. A second watcher
   latched onto the wrong PID and ended early; the stage-2 job itself was unaffected.
3. L2 consequences: calibration SD from 6 runs (5 df), 5 evaluation units (4 df), arm D skipped.
4. `results/smoke/` (tiny timing run from stage 1, cited in `protocol.md` for step times) was
   removed by the coordinator before commit. Its numbers are not results.
5. The calibration analysis was run after all tasks finished, not before evaluation tasks
   started. No evaluation outcome was looked at before `calibration.json` was written.
6. The protocol's wall-clock figure "L2 3.3 h at 2x" was exceeded in projection only, not in
   fact. The 3 h budget was met (2.0 h).

## Limits

CPU bf16, not the GPU; only paired contrasts are interpreted. One small byte model, two
serial "sites", modeled WAN and ticks, schedule distribution inferred from six hand-written
schedules. Five units give wide intervals. Heavy intermediates (dataset, warm checkpoints) are
in `work/`, git-ignored.
