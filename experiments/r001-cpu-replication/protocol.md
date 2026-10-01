# R001: CPU replication of the E001 learning results

Status: STAGE 1 (protocol and code only). No outcome data exists. Energy is not measured.
Repo HEAD when written: 7a5838870e553cf9bef683f55b2e1d87343e6281. Scenario: `scenario.json`.
Smoke tests used 24-tick warm starts and 16-tick horizons; their numbers carry no information and are discarded.

## Questions, in plain words

**Q1 (LC3 replication).** E001-LC3 compared two recovery policies after a failure: *fixed*
(roll back to the last checkpoint and replay) and *adaptive* (the surviving site keeps
training). Both do the same canonical work. Is adaptive's held-out NLL (negative log-likelihood,
nats per byte; lower is better) no worse than fixed by more than a justified margin, when
we use fresh warm-start seeds and fresh failure schedules?

**Q2 (SC1 averaging control).** In E001-SC1, `periodic_local` (two sites train independently
and average weights every 8 ticks) beat exact synchronization by about 0.019 NLL in all 10
families (`results/semantic-consistency-v1.json`, final NLL, `synchronous_restart` minus
`periodic_local`: mean 0.0187, SD 0.0024). Exact sync barely moved from the warm start at
constant LR 3e-4. Is that advantage just weight averaging at a constant-LR plateau?

Why it matters: every E001 learning number came from one GPU, one warm seed (7), and six
hand-written schedules. Nothing was replicated.

## Facts checked while writing (sources)

- Dataset: TinyStories shard `0000.parquet`, URI in `scenario.json`. It is not in the repo.
  Fetched here through the proxy in 8 s: 248,731,111 bytes, SHA-256
  `77cf780c...0fc0b`, equal to the hash frozen in the LC3 and SC1 scenarios and to the
  Hugging Face `x-linked-etag`. `refs/convert/parquet` was at commit 37346026e81060382814d5a773f3c34799e118e7
  on 2026-10-01; the SHA-256 is what pins content. `run.py fetch` repeats this.
- E1-E6 failure schedules were written by hand. No generator exists in the repo. LC3 and LC1
  use the same six. The `seed` in each stratum only seeds the post-warm data stream.
- The original used ONE warm checkpoint (seed 7). Its seed spread therefore had no warm-seed
  component. Fixed-policy final NLL across E1-E6: mean 1.0189, SD 0.0028
  (`equal-work-v1.json`, `summary.evaluation_pairs`). LC3 paired adaptive-minus-fixed NLL:
  mean 0.0050, median 0.0033, SD 0.0044, max 0.0135 (E5, three failures).
- Late-stage gate: warm NLL gain over the last 256 of 8192 ticks was 0.0045 (limit 0.03).
- Engines hard-code `cuda:0`, bf16 autocast, NVML. Only `_run_equal_work_arm` and
  `_build_warm_checkpoint` must be copied; SC1 already falls back to CPU.

## What is computed

Engines are imported unchanged (no `gpu_stack/` file is edited). Copied pieces:
`lc3_cpu.py` (LC3 arm and warm builder; CPU, no meter, no thermal guard; held-out
evaluation every 64 ticks instead of 8, final tick always measured). `cpu_runtime.py`
turns the engines' CUDA-only autocast blocks into CPU bf16 autocast, matching the original
bf16 regime. CPU numerics differ from the GPU, so NLL levels may differ slightly; only
paired contrasts are interpreted. 1 thread per worker, 4 workers.

**Warm starts.** Seed s: 8192 ticks, two serial sites, AdamW, merge every 8 ticks, as in
LC2/LC3. A seed whose late-stage gate fails is dropped and reported, not replaced.
Calibration seeds 9101-9103; evaluation seeds 8101-8106. Disjoint from each other and from
7, 11, 29, 101-241.

**Q1 arms.** Each evaluation pair = (warm seed, failure schedule, data-stream seed): fixed
interrupted vs adaptive interrupted to canonical tick 256 (524,288 tokens), cap 384 ticks.
18 pairs: 3 per evaluation warm seed (`lc3.evaluation_pairs`).
Schedules come from an inferred generator (`make_scenario.py`, seed 20261001): 2 failures
(3 with probability 1/6, since E5 has 3); start a multiple of 8 in [32,216]; duration
8, 16 or 24; gap from one end to the next start >= 48; last end <= 240; E1-E6 excluded.
This is an inference from six hand-written schedules, not their true distribution.

**Q2 arms.** SC1 engine, 256 canonical ticks, SC1 stress families, same checkpoint as Q1
(SC1's own warm routine is not reused; the SC1 text says it uses the LC3 state). Evaluation
cells: 2 per warm seed (one no-failure family E1/E3/E5, one failure family E2/E4/E6;
each family appears twice). Arms:
A `exact_forward_recovery` (identical NLL to `synchronous_restart` in the original),
B `periodic_local`, C A with cosine LR to ~0 over 256 ticks, D B with cosine (optional).
EMA control: an exponential moving average of the surviving replica's weights, updated once
per tick, scored at tick 256, for decays 0.9, 0.95, 0.98, 0.99. It does not change training,
so it is free on arm A. Hooks wrap engine functions for one run and restore them
(`sc1_cpu.py`); `selftest.py` checks the hooks leave training bitwise unchanged.

## Stage 2 order and analysis

1. Calibration (calibration seeds only), written to `results/calibration.json` before any
   evaluation analysis; `analyze.py evaluate` refuses to run without it.
   a. Fixed policy, no failures, 3 warm seeds x 3 streams: SD of final NLL (total seed
      spread). Adaptive no-failure on the first stream: must equal fixed exactly
      (a check on the CPU port; a failure is reported and halts Q1 interpretation).
   b. SC1: arms A and B on C1 (healthy) and C4 (single failure) per calibration seed. The
      EMA decay with the lowest mean NLL is the one used for the Q2 test.
2. Evaluation, as in `analyze.py`. Unit of analysis = warm seed (mean of its 3 pairs;
   its 2 Q2 cells). Intervals: two-sided 90% t, df = units - 1 (this equals the one-sided 5%
   test). Using the warm seed as the unit keeps pairs that share a checkpoint from counting
   as independent.

## Decision criteria

**Q1 margin delta** = min(0.010, max(0.003, ceil_to_0.001(2 x SD))), SD from 1a.
First-principles reason: a deficit smaller than twice the spread you get by rerunning the
fixed policy with another seed cannot be told from rerun noise. The cap is the original
0.010, so the study can never be looser than E001. The floor 0.003 is for SD estimated from
few runs (5 to 8 df: the 90% range of an SD estimate is about x0.6 to x1.6). Expected delta is
about 0.006 if SD is near the original 0.0028, and larger if warm-seed spread adds to it.
For scale: late-stage 256-tick progress is only about 0.0045, so 0.010 is already generous.
- `non_inferior`: upper CI bound of mean(adaptive - fixed) <= delta.
- `inferior`: lower bound > delta.
- otherwise `not_shown_non_inferior` (inconclusive).
- Also reported at the original 0.010. Descriptive only: median, max pair, pairs above
  delta, split by number of failures; attempted-token saving and opportunity-tick saving
  (exact counts; ticks are modeled, not CPU wall time).

**Q2.**
- Advantage replicated if the lower CI bound of mean(A - B) > 0.005 (about the whole 256-tick
  late-stage progress). If not, Q2 is "nothing to explain".
- f_EMA = (A - EMA)/(A - B) per warm seed; f_cos = (A - C)/(A - B). Label by CI of f:
  `mostly_explained` if lower >= 0.75; `not_explained` if upper <= 0.25; else
  `partial_or_inconclusive`. The bands sit 0.25 either side of 0.5; simulated unit noise
  (`power.py`) gives CI half-width near 0.1, so each band is reachable.
- If arm D ran: advantage under cosine (C - D) vanishes if its upper bound <= 0.005.

## Power and n (planning inputs are original E001 numbers, not R001 results)

`power.py` (full table in `results/power_table.txt`). Q1 chance that the upper bound
is <= delta, 6 units x 3 pairs, SD of one pair 0.006 (above the original 0.0044):
true mean deficit 0.003: 0.99 at delta 0.010, 0.57 at delta 0.006; 0.005: 0.92 and 0.15;
0.0075 at delta 0.010: 0.45. If pairs on one warm seed correlate (rho 0.5): 0.91 and 0.37
at deficit 0.003; 0.70 and 0.12 at 0.005. So with the likely delta near 0.006, the study
has useful power only if the true deficit is about 0.003 or less (the original median was
0.0033, the mean 0.0050). A failure to show non-inferiority can mean "worse" or "cannot
tell"; the three labels keep these apart. The earlier "8-12 pairs" guess is replaced:
precision comes from warm seeds (units), not pairs. Q2: 6 units give 0.95 chance of
`mostly_explained` if the true fraction is 0.9 and 0.87 of `not_explained` if 0.1.

## What outcomes mean

- Q1 `non_inferior`: on this CPU workload adaptive loses no more NLL than rerun noise.
  Says nothing about energy, wall time, WAN, or scale. `inferior`/inconclusive: the 0.010
  LC3 NLL gate was loose against late-stage progress and the claim needs rework.
- Q2 `mostly_explained`: SC1's periodic_local advantage is mostly an averaging effect that
  EMA or LR decay recovers; the SC1 "baseline wins" reading should be restated.
  `not_explained`: the advantage needs more than temporal averaging at these settings.

## Budget (measured here; 4 cores shared with other studies)

Seconds per training step (one 4x256-token quota step, bf16, 1 thread, 1.87M params):
0.091 s alone (warm tick 0.182 s for 2 quotas); 0.135 s with 4 workers on a quiet box
(micro-benchmark); 0.20 s with one other busy job (0.41 s per warm tick); 0.83 s at load
11. fp32 is 1.8x slower than bf16 on this CPU (AMX), so bf16. One warm start is 8192 ticks:
about 37 min quiet, 57 min lightly shared. SC1 tick incl. overhead 0.35 s alone; full
LC3 arm about 80 s quiet.
Wall-clock for 4 workers, projected by `run.py probe` (quiet; at 2x slowdown):
L0 (3 cal + 6 eval warm seeds, optional arm D) 2.2 h (4.4 h); L1 (5 eval seeds, no D)
1.9 h (3.7 h); L2 (2 cal + 5 eval) 1.65 h (3.3 h). Rule: before running, pick the richest
level projected <= 3.0 h; if none fits, wait for a quieter machine. Never decided from
outcomes. Fit in about 3 h therefore needs a quiet machine.

## Known limitations

CPU bf16 is not the GPU; the original NLL levels are not expected to match, only contrasts.
Seed spread here includes warm-seed spread the original lacked. Schedule distribution is
inferred. Two sites run serially; WAN and completion time are modeled. SC1 control does not
separate averaging from the batch-4 vs batch-8 gradient noise difference. 18 pairs, 6 seeds,
one small byte model. No energy.
