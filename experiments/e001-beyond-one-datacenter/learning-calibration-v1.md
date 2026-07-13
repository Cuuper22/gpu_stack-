# E001-LC1: Survivor-Continuation Learning Calibration

Status: executed July 12, 2026; `candidate_falsified_small_model_calibration`

## Research Question

When one logical training site becomes unavailable, can the surviving site
temporarily execute both sites' fixed microbatch quota, shorten its merge
cadence, and rejoin by copying canonical model and optimizer state without
giving up learning efficiency relative to fixed-local checkpoint restart?

This is the first E001 experiment whose response variable is measured model
learning. It is deliberately a local small-model calibration, not a claim
about real multi-datacenter performance or frontier-scale convergence.

## Why The Question Changed

The recovery-v2 mechanical result split the policies: fixed-local was fastest
and moved the fewest bytes, while adaptive recovery lost much less work and
used less modeled energy. A direct semantic inspection then found that the two
policies currently have the same two-local-step learning schedule. Faithfully
replaying that schedule should produce one canonical learning trajectory; any
loss difference would diagnose nondeterminism or incomplete checkpoint state,
not a causal staleness effect.

LC1 therefore tests the missing learning mechanism instead of relabeling a
checkpoint-cadence comparison as ML research.

## Workload And Scope

- Byte-level causal language modeling on a deterministic slice of
  `roneneldan/TinyStories`.
- One approximately 2M-parameter decoder: four layers, width 192, four
  attention heads, context 256, tied byte embeddings, AdamW, no dropout.
- Two logical sites executed on one RTX 3060 Laptop GPU. Each opportunity tick
  assigns one fixed 4 by 256-token microbatch quota to each site.
- 256 opportunity ticks per run, about 20 million attempted training tokens
  across the frozen 40-arm matrix before replay overhead.
- Two calibration strata and six untouched evaluation strata.
- Five arms per stratum: synchronous no-failure reference, fixed-local
  no-failure, fixed-local interrupted, adaptive no-failure, and adaptive
  interrupted.

The GPU is a measurement harness for learning response and device energy. It
does not emulate simultaneous site throughput, WAN, facility energy, or real
checkpoint storage.

Every arm begins at or below 90°C. During a run, the harness pauses at 94°C
until the device returns to 91°C. Thermal-pause time is recorded and excluded
from active local wall time; sampled raw and idle-subtracted board energy remain
available. This boundary was frozen after an aborted pre-result execution hit
93°C before producing any artifact. A first 88°C start boundary was then found
to dominate execution time because Codex and Chrome keep the desktop GPU near
90°C. It was raised once to the observed stable training plateau before any arm
completed; every arm still records its exact start and end temperature.

An approximately 5M-parameter pre-result configuration was also aborted before
one arm completed because the frozen 40-arm matrix would exceed the execution
window. Model scale was reduced once to approximately 2M parameters; schedules,
seeds, estimands, and falsifiers were unchanged before any result was inspected.
The first approximately 2M pre-result launch exposed an accidental 512-checkpoint
synchronous control. That non-intervention overhead was removed before an arm
completed; fixed and adaptive checkpoint schedules were unchanged.
The corrected 512-tick arm still exceeded six minutes before completion, so the
horizon and failure positions were scaled once by one half before any result
existed. Evaluation still contains six paired strata and preserves outage
fractions; the scientific gates were not relaxed.
The first 256-tick launch then exposed PyTorch's global deterministic-algorithm
mode selecting a prohibitively slow attention kernel. LC1 has no dropout and
keys every batch to logical identity, so that global switch was disabled before
an arm completed. CUDA kernels are not claimed bitwise deterministic; the
matched no-failure 1% equivalence gate remains the empirical control.

## Policies

All arms share initial weights, batch identities, validation batches,
optimizer hyperparameters, and the exogenous event schedule within a stratum.
Randomness is keyed by logical sample identity, never attempt or policy ID.

### Synchronous reference

Both sites take one local step, then model parameters and AdamW state are
deterministically averaged every opportunity tick. No failures are applied and
no post-genesis recovery checkpoints are taken; checkpoint cadence is not part
of this learning-efficiency reference.

### Fixed-local checkpoint restart

Healthy operation uses eight local ticks between merges and checkpoints every
two merge rounds. At a visible failure, both sites restore the last complete
checkpoint, including model, optimizer, and logical data position. Neither
site trains during the outage. Replayed logical batches keep their original
identities and count again only as physical attempted work.

### Adaptive survivor continuation

Healthy operation uses the same eight-tick local cadence and checkpoints every
merge round. During a site-A outage, site B executes both sites' immutable
microbatch quotas sequentially and checkpoints every two ticks. At recovery,
site A copies site B's canonical model and optimizer state. The pair merges
every tick for two post-rejoin ticks before returning to the eight-tick cadence.

No-failure fixed and adaptive arms keep their different checkpoint cadence but
must be learning-equivalent. That is an implementation control, not an
optional result.

## Split And Frozen Schedules

Calibration strata, used only to choose the loss target and plot scale:

- C1, seed 11: failures `(48, 8)` and `(152, 16)`.
- C2, seed 29: failures `(80, 16)` and `(184, 16)`.

Evaluation strata, never used to tune the policy or target:

- E1, seed 101: `(40, 8)`, `(136, 16)`.
- E2, seed 131: `(64, 16)`, `(200, 8)`.
- E3, seed 151: `(72, 8)`, `(128, 24)`.
- E4, seed 181: `(104, 16)`, `(184, 16)`.
- E5, seed 211: `(32, 8)`, `(104, 8)`, `(216, 16)`.
- E6, seed 241: `(88, 24)`, `(168, 8)`.

Each pair is `(start_tick, duration_ticks)`. Starts are healthy merge
boundaries; fixed-local may still roll back one full uncheckpointed merge round.

The target is frozen from calibration controls only:

`L* = L0 - 0.75 * (L0 - median(final synchronous calibration NLL))`.

## Primary Estimand

For policy `p`, interruption state `z`, and evaluation stratum `s`:

`P[p,z,s] = (initial held-out NLL - final held-out NLL) / attempted training FLOP`.

The interruption-specific adaptive effect is the paired difference in
differences:

`tau_s = (P[adaptive,1,s] - P[adaptive,0,s]) - (P[fixed,1,s] - P[fixed,0,s])`.

Report all six `tau_s` values, their median, and a paired 90% bootstrap
interval. Also report the direct adaptive-interrupted versus fixed-interrupted
contrast so difference-in-differences cannot hide a bad absolute policy.

Training FLOP are modeled as `6 * parameter_count * attempted_tokens`. Loss,
wall-clock time, and GPU board power are observed. Device energy is integrated
from NVML samples with a pre-run idle-power estimate and is not facility energy.

## Metrics

- held-out validation negative log-likelihood curve;
- progress per attempted FLOP, per GPU joule, and per local wall-clock second;
- retained progress relative to the same policy's no-failure arm;
- logical ticks and modeled datacenter time to `L*`;
- unique, replayed, discarded, and survivor-redistributed tokens and FLOP;
- checkpoint bytes and checkpoint-copy time in the local harness;
- local wall-clock time, raw NVML joules, idle-subtracted NVML joules;
- NaN, divergence, target-not-reached, and exact no-failure equivalence flags.

## Falsifiers

The adaptive rule survives LC1 only if all are true on held-out E1 through E6:

1. the lower bound of the 90% paired bootstrap interval for `tau` is above 0;
2. the lower bound of adaptive interrupted/no-failure progress-per-FLOP ratio
   is at least 0.95;
3. adaptive interrupted median logical ticks to `L*` is lower than fixed
   interrupted;
4. no adaptive evaluation run diverges;
5. no-failure fixed versus adaptive progress-per-FLOP differs by at most 1%;
6. adaptive interrupted progress per FLOP is at least 95% of the synchronous
   no-failure reference on this small workload.

Any failed condition falsifies this candidate rule. The evaluation schedules
must not be retuned after inspection.

## Result

The frozen matrix completed 40 local GPU runs: 10 calibration observations and
30 held-out evaluation observations. Calibration alone fixed the target at
held-out NLL `3.13759109564126`. Every evaluation arm first crossed it at the
first 32-tick observation, leaving the time-to-target comparison interval-
censored and tied at tick 32.

The conclusion is `candidate_falsified_small_model_calibration`. The paired
interruption effect `tau` had median `-7.19835770326443e-14` with a paired 90%
bootstrap interval
`[-7.24876398177115e-14, -5.48204063742032e-14]`; the positive-effect gate
failed. Adaptive's interrupted/no-failure progress-per-FLOP ratio had lower
bound `1.00215623908839`, and adaptive interrupted versus synchronous no-
failure had lower bound `1.00265505192967`. Those retention gates passed, as
did no-failure equivalence and the no-divergence gate. The sooner-to-target
gate failed because fixed and adaptive both recorded tick 32.

| Held-out interrupted median | Fixed-local restart | Adaptive continuation |
|---|---:|---:|
| Final held-out NLL | 2.341145828 | 2.314653009 |
| Attempted tokens | 458,752 | 524,288 |
| Canonical tokens | 442,368 | 524,288 |
| Replayed tokens | 16,384 | 0 |
| Discarded tokens | 16,384 | 0 |
| Survivor-redistributed tokens | 0 | 32,768 |
| Logical ticks to target | 32 | 32 |
| Checkpoint bytes | 302 MB | 1.049 GB |

Adaptive completed 524,288 canonical tokens and ended at lower NLL. Fixed did
12.5% less attempted work, completed only 442,368 canonical tokens, and ended
worse. Because LC1 divided from-scratch progress over a fixed horizon by
attempted work, the smaller fixed denominator nevertheless made fixed look
12.7% better per FLOP. That finite-horizon estimand is invalid for ranking
recovery value in this regime: it rewards work that was never completed.

Artifact identities:

- result: `0597ca6deeeb34ae97d57d72b49187c687af921d3eec7b804ceb48b0d3994826`;
- engine source: `3a51c72de99fd17580b0bbf4bbc6722db7470b41ac8d74d2f9fcabc386cdb010`;
- scenario: `3ea1ccd6fc717ded9d4f7150574df806a8dc7572fa35d00314f9bb3ea744c319`;
- observatory projection: `ff6b5a56dab3314f9ad0b1def40fda9ce9df540bda411284bb9766d9a3ee3c12`.

## Next Experiment: LC2

LC2 will warm-start from a shared late-training checkpoint and freeze a quality
target before held-out evaluation. Fixed restart and adaptive continuation will
be compared on wall-clock time, device energy, attempted work, and canonical
work required to reach that target. The observed learning curves will then be
bridged to the modeled datacenter recovery mechanics without relabeling modeled
WAN, facility, storage, or simultaneous-site behavior as measurements.

## Paper Grounding

- [GASLoC](https://arxiv.org/abs/2606.11081) motivates local-update and outer-
  merge behavior under heterogeneous communication.
- [ReCoVer](https://arxiv.org/abs/2605.11215) motivates preserving a fixed
  global microbatch count by redistributing quota after visible failures.
- [ResiHP](https://arxiv.org/abs/2605.06374) motivates workload-aware failure
  semantics, though LC1 does not test its detector.
- [DynaTrain](https://arxiv.org/abs/2605.18815) motivates canonical state
  remapping on rejoin, though LC1 does not test reconfiguration speed.

## Evidence Boundary

LC1 cannot establish frontier-scale convergence, real multi-site speedup,
measured WAN or facility energy, detector accuracy, hybrid-parallel
correctness, state-migration performance, or transfer beyond this byte-level
TinyStories decoder, AdamW, and visible fail-stop schedule. Its energy evidence
is device-only on one local GPU; the mechanical datacenter metrics remain
modeled. It asks one narrow but real question: does survivor continuation
preserve more measured small-model learning per attempted work than fixed
checkpoint restart?
