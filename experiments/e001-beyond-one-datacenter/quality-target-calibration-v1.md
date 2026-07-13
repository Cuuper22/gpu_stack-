# E001-LC2: Late-Stage Quality-To-Target Recovery

Status: executed July 12, 2026; protocol failed before held-out evaluation

## Research Question

Starting from one shared late-training model and AdamW checkpoint, does adaptive
survivor continuation require less attempted compute to reach the same frozen
held-out quality than fixed-local checkpoint restart, while also reaching it
earlier without increasing canonical work or sampled GPU device energy by more
than 5%?

LC2 is a new question selected by the LC1 failure. It does not retune, replace,
or reinterpret LC1. LC1 remains
`candidate_falsified_small_model_calibration` because its fixed-horizon
progress-per-FLOP denominator rewarded the fixed policy for stopping with less
work and worse loss.

## One Complete Path

`TinyStories shard -> shared warm checkpoint -> calibration-only target -> six
held-out failure schedules -> measured quality-to-target runs -> explicitly
modeled recovery bridge -> research artifact -> three-depth observatory`

Only the recovery mechanics required by this path are included.

## Shared Warm Start

- The model, optimizer, byte-level dataset slice, and two logical sites are the
  same as LC1.
- One fixed-local no-failure two-site run trains for 2,048 opportunity ticks
  with seed `7` and merges on the frozen eight-tick cadence.
- It earns the label late-stage only if held-out NLL improves by at most `0.03`
  from tick 1,792 to tick 2,048. If that gate fails, LC2 publishes a protocol-
  stage failure instead of running a mislabeled evaluation.
- The complete canonical model and AdamW state is copied into every calibration
  and evaluation arm.
- The warm checkpoint is content-addressed in the result. Warm-start work is a
  shared experimental initialization and is not charged selectively to any
  policy.

This makes the response late-stage progress from the same state rather than
from-scratch improvement over a fixed horizon.

## Target Selection

Only fixed-local no-failure calibration runs C1 and C2 can select the target.
Each fixed and adaptive calibration control runs for 256 post-warm ticks. The
target is the median fixed-local NLL across C1/C2 at ticks 240, 248, and 256.
Both fixed controls must first cross it between ticks 192 and 288. The paired
adaptive controls must match fixed attempted tokens and NLL at every observed
tick; a mismatch is an implementation-validity failure.

Evaluation curves are not inspected until `L*` is fixed. The six evaluation
schedules are reused unchanged from LC1; the maximum horizon of 384 ticks and
8-tick evaluation cadence are
frozen in `quality-target-scenario-v1.json`.

## Policies And Held-Out Matrix

Each held-out stratum runs only the two required arms from the identical warm
checkpoint: fixed-local interrupted and adaptive interrupted. Pair order
alternates by stratum to limit thermal ordering. No-failure equivalence is
established in the four calibration controls.

Fixed-local restores both sites to the last complete checkpoint and does no
training while site A is unavailable. Adaptive assigns both immutable site
microbatch quotas to site B during the outage, checkpoints every two ticks,
copies canonical model and optimizer state to site A on rejoin, and uses two
one-tick synchronization rounds before returning to the healthy cadence.

Each run stops at the first 8-tick observation at or below `L*`. A run that
does not reach the target by tick 320 stays a failure; its endpoint is not
converted into an efficiency value.

## Primary Estimand

For evaluation stratum `s`, the primary estimand is attempted-work saving:

`work_saving_s = (fixed_attempted_FLOP_s - adaptive_attempted_FLOP_s) /
fixed_attempted_FLOP_s`.

Report all six paired values, their median, and a paired 90% percentile-
bootstrap interval. Positive values mean adaptive reached the same quality
with less physical training work. Also report the paired opportunity-tick
saving and how many schedules adaptive wins strictly.

Also report paired adaptive/fixed ratios for canonical tokens and sampled
idle-subtracted GPU device energy to target. Canonical tokens, replayed tokens,
discarded tokens, checkpoint bytes, active local seconds, and final NLL remain
visible so a favorable ratio cannot hide incomplete work or lower quality.

## Frozen Falsifiers

The candidate survives LC2 only if all are true on E1 through E6:

1. all six fixed/adaptive interrupted pairs reach the frozen target;
2. the lower bound of the 90% paired attempted-FLOP-saving interval is above
   zero;
3. median attempted-FLOP saving is at least 3%;
4. the upper bound of the paired adaptive/fixed canonical-token ratio is at
   most 1.05;
5. median opportunity-tick saving is at least 8 ticks and adaptive is strictly
   earlier in at least five of six schedules;
6. the upper bound of the paired adaptive/fixed sampled device-energy ratio is
   at most 1.05;
7. the calibration no-failure controls remain exactly learning-equivalent;
8. adaptive reaches all six targets and no adaptive run diverges.

Any failed condition falsifies this candidate. Schedules, target, thresholds,
and evaluation cadence are not changed after held-out inspection.

## Explicit Mechanics Bridge

The result will attach a target-conditioned sensitivity projection using the
existing recovery-v2 policy artifact. LC2 opportunity ticks and learning are
observed in the local harness. Recovery-v2 elapsed time, traffic, lost work,
and partial energy remain modeled. The bridge may multiply a policy's measured
ticks to target by a recovery-v2 modeled quantity per durable-frontier unit;
it must carry both source hashes and the label `modeled_bridge_sensitivity`.

This is not a measured multi-datacenter time, WAN, or facility-energy result.
It is an inspectable hypothesis about how the observed quality response would
change the already-modeled recovery comparison.

## Evidence Boundary

Observed here: held-out byte NLL on one fixed 64-batch validation suite, target crossing at 8-tick resolution,
attempted and canonical token counts, local active time, sampled GPU board
energy, temperature, and exact checkpoint/work accounting in one serial RTX
harness. Validation and cooldown are excluded from the training-energy and
active-training-time windows.

Not observed here: simultaneous sites, WAN, checkpoint storage service,
network or host energy, cooling, facility energy, detector accuracy, hybrid
parallelism, frontier-scale convergence, or transfer beyond this model,
dataset, optimizer, and visible fail-stop schedule.

## Recent Paper Grounding

- [GASLoC](https://arxiv.org/abs/2606.11081) motivates local-update and outer-
  merge behavior under heterogeneous communication.
- [ReCoVer](https://arxiv.org/abs/2605.11215) motivates redistributing a fixed
  global microbatch quota after visible failures.
- [ResiHP](https://arxiv.org/abs/2605.06374) motivates workload-aware failure
  semantics, though LC2 does not test a detector.
- [DynaTrain](https://arxiv.org/abs/2605.18815) motivates canonical state
  remapping on rejoin, though LC2 does not claim measured migration speed.

## Executed Result

The shared 2,048-tick warm run improved held-out NLL from
`1.52376570366323` at tick 1,792 to `1.43749829754233` at tick 2,048. The
improvement was `0.08626740612089634`, above the frozen late-stage maximum of
`0.03`. The run therefore persisted
`protocol_failed_warm_start_not_late_stage` and stopped before target
selection or any held-out failure schedule.

This is a useful protocol failure, not negative evidence about survivor
continuation. It proves that the 2,048-tick checkpoint did not instantiate the
late-training regime named by the question. No LC2 v1 held-out comparison
exists.

Result artifact:
`results/quality-target-v1.json`
(`4781781857ae638f6e64868ed3fa156d9459f5f64e62f82aad3db6cde3bfd0c6`).
