# Results log

This is the lab notebook. Every completed experiment run, its exact numbers,
its artifact path, and its content hash live here. The
[README](../../README.md) tells the story; this file is the evidence locker.

If you are new to the project, read the README first. Nothing on this page is
written to persuade. It is written so a claim can be checked, byte for byte,
against the artifact that produced it.

Conventions used below:

- **NLL** is negative log-likelihood, the training-loss number. Lower means
  the model predicts held-out text better.
- **Held-out** means data the run never saw during calibration, so the result
  cannot grade its own homework.
- **Frozen** means the pass/fail threshold was fixed before the run started.
- Every artifact is content-addressed: the hash in parentheses is the SHA-256
  of the file, so a quoted number can be traced to an exact artifact version.
- A conclusion string like `abstain_without_policy_claim` is quoted verbatim
  from the persisted artifact. The artifact wording is authoritative.

## Reproduce the modeled E001 recovery baseline

```bash
python -B -m gpu_stack.cli experiment-run E001-RECOVERY-V2 \
  --scenario experiments/e001-beyond-one-datacenter/recovery-scenario-v2.json \
  --output experiments/e001-beyond-one-datacenter/results/recovery-mechanics-v2.json \
  --observatory-output docs/data/e001-recovery-v2.json
```

## E001 artifacts

The measured LC1 result is persisted at
`experiments/e001-beyond-one-datacenter/results/learning-calibration-v1.json`
(`0597ca6deeeb34ae97d57d72b49187c687af921d3eec7b804ceb48b0d3994826`),
with observatory projection `docs/data/e001-learning-v1.json`
(`ff6b5a56dab3314f9ad0b1def40fda9ce9df540bda411284bb9766d9a3ee3c12`).

The two LC2 protocol-stage artifacts are preserved at
`experiments/e001-beyond-one-datacenter/results/quality-target-v1.json`
(`4781781857ae638f6e64868ed3fa156d9459f5f64e62f82aad3db6cde3bfd0c6`)
and `experiments/e001-beyond-one-datacenter/results/quality-target-v2.json`
(`a3bb91b74a99708a08b5196ffc8d16bb27bca697f7f54fb63e60564851f97517`).
Neither contains held-out policy evidence.

The held-out LC3 result is persisted at
`experiments/e001-beyond-one-datacenter/results/equal-work-v1.json`
(`f7548b68d4791978260f0bd557bf92041d0f769b796b1e684bbcab99e88f639f`),
with observatory projection `docs/data/e001-equal-work-v1.json`
(`5ff07c4cf5b59be04d14f1b66961e679c2cec127b521c386d54ff9ebaadc1ae1`).

The E001-SC1 semantic-consistency result is persisted at
`experiments/e001-beyond-one-datacenter/results/semantic-consistency-v1.json`
(`e4bb8023145bdb21e97b9a5d295dc778f58adccc452d2bd9d3e4a599bf53bbc7`).

## E002 artifacts

E002-PW1 completed its frozen 32-run factorial (a grid that tries every
combination of the chosen factors) and is preserved at
`experiments/e002-power-waveform-shaping/results/checkpoint-power-v1.json`
(`aff76946b26876820cdaa4ca43d0b6160cdc18b2f4c5bacd053cfe92f529d4f5`).
Its conclusion is `measurement_invalid`, not a causal or candidate result.

E002-PW2 completed the same frozen factorial with a valid cumulative-energy
meter at
`experiments/e002-power-waveform-shaping/results/checkpoint-energy-v2.json`
(`cfbca215878629bc416f169e5ded80684151d9b2a621548c7fef08207c41f8ee`).

E002-PW3 remains an executable optional physical rack experiment: a
dependency-safe phase scheduler, distributed four-job/eight-GPU runtime,
UUID-bound GPU plus rack/storage/cooling telemetry, hash-chained raw evidence,
and a three-depth observatory projection. No PW3 result exists yet for a
plain hardware reason: this machine has one GPU and no direct rack boundary
meters. It does not gate GPUSTACK's software research loop.

## E001 detailed results

### Recovery mechanics v2

The recovery-v2 artifact records complete modeled traffic classes for its
focused scenario. Adaptive reaches the same durable frontier as synchronous in
1.536 rather than 1.584 seconds and moves 13.6 rather than 15.2 GB. Fixed-local
is still faster and lower-traffic than adaptive, while adaptive loses much less
work and uses less modeled energy. So each policy wins on some axes and loses
on others. That is a Pareto split (no single policy wins on every axis at
once), and it does not establish a globally superior controller.

### LC1: learning calibration

E001-LC1 completed 40 local GPU runs: 10 calibration observations and 30
held-out evaluation observations. The frozen target was held-out NLL
`3.13759109564126`, and every policy first crossed it at tick 32. The candidate
was falsified on this small-model calibration: paired progress-per-FLOP `tau`
had median `-7.19835770326443e-14` and a 90% interval
`[-7.24876398177115e-14, -5.48204063742032e-14]`, while adaptive and fixed tied
on time-to-target. Adaptive still ended better under interruption, at median
NLL `2.314653009` versus `2.341145828` for fixed. Notice the trap in the
per-FLOP metric: fixed attempted 12.5% less work and ended worse, but dividing
from-scratch finite-horizon progress by its smaller attempted-work denominator
made fixed look 12.7% better per FLOP.

### LC2: quality-to-target protocol stages

LC2 tried to replace that invalid comparator with a warm-started
quality-to-target endpoint. Both attempts failed their own protocol before any
policy could be ranked. V1 stopped before held-out evaluation because the
2,048-tick checkpoint was not late-stage: NLL improved
`1.52376570366323 -> 1.43749829754233`, or `0.08626740612089634`, above the
frozen `0.03` maximum. V2's 8,192-tick checkpoint passed with improvement
`0.004534989595413208`, and fixed/adaptive calibration was exactly equivalent.
But the frozen target `1.01961656101048` was first crossed at ticks 40 and 96,
not inside the required 192 to 288 window, because late-stage NLL was
non-monotonic. V1 concluded `protocol_failed_warm_start_not_late_stage`; V2
concluded `protocol_failed_calibration_validity`. Neither result opened
held-out evaluation, so neither ranks the policies.

### LC3: equal canonical work

LC3 removed unstable first crossing and compared six untouched held-out pairs
at exactly 524,288 canonical tokens. Adaptive passed learning noninferiority:
adaptive-minus-fixed NLL had median `0.003338515292853117` and paired 90%
interval `[0.0023927902802824974, 0.008503663819283247]`, below the frozen
`0.01` upper margin. It saved a median `3.030303%` attempted work and 40
opportunity ticks, and was earlier in all six schedules. It failed only the
sampled device-energy gate: the adaptive/fixed ratio had median
`1.0683917796356628` and interval
`[1.0017954332700434, 1.134269402803286]`, above the frozen `1.05` bound.

The persisted LC3 conclusion is `candidate_falsified_equal_canonical_work`.

### SC1: observable semantic slack

E001-SC1 ran 20 calibration arms, 30 executable held-out arms across six
stress families, and six non-executable hindsight-envelope records.
Calibration selected `periodic_local`. Adaptive switching had held-out NLL
difference `+0.016659 [+0.001785, +0.042213]`, WAN-payload ratio
`2.128x [1.556x, 2.552x]`, modeled-completion ratio
`1.072x [0.986x, 1.099x]`, and hindsight-envelope regret
`0.07155 [0.03349, 0.10056]`. Every frozen gate failed. The engine still
completed equal work with zero divergence, sample-identity mismatch,
optimizer-lineage violation, or work-contract violation.

Three families produced 104 out-of-distribution abstention ticks, meaning the
controller saw states outside its calibrated support and declined to act. The
persisted conclusion is therefore `abstain_without_policy_claim`. This is a
valid negative controller result on one byte-level AdamW model, not evidence
that `periodic_local` is universally optimal. Device-energy comparison was not
available, and WAN plus completion time remain modeled.

## E002 detailed results

### PW1: checkpoint power attribution (measurement invalid)

E002-PW1 completed all 32 frozen factorial runs with exact warm-state
binding. The measurement failed, not the experiment design: the requested
20 ms logger had an effective 494.693 ms device-update period and selected
`+250` ms lag at the frozen boundary. The result is `measurement_invalid`
solely because evaluation arms and pooled cadence phases received too few
independent power updates. The raw LC3-corner ratio was
`0.789 [0.703, 0.923]`, so the prior penalty did not reproduce numerically. The
raw sparse-continuation ratio was `0.823 [0.665, 1.019]`, with all non-energy
gates passing. Both are inadmissible, and all three mechanism gates failed.

### PW2: cumulative-energy attribution

E002-PW2 completed all 32 cumulative-energy runs with exact warm binding,
no invalidators, a 91.667 ms effective counter period, and 83 to 109 updates per
held-out arm. The total interaction was
`2.2416e-5 [2.1746e-6, 3.5305e-5] J/token`; checkpoint-group and snapshot
interactions were also positive. All three mechanism gates passed.
The sensitivity-only idle-subtracted interaction was
`3.9825e-6 [-8.0109e-6, 1.2479e-5] J/token` and crossed zero. The frozen raw
cumulative primary passes, but the attribution is not baseline-insensitive.

Sparse continuation passed all eight salvage gates: NLL delta median
`0.0033385` and upper `0.0085037`, attempted-work saving `3.03%`, 40
opportunity ticks saved, and energy ratio `0.96099` with upper `1.00319`. The
conclusion is `checkpoint_cadence_attributed_sparse_continuation_survives`.

## What comes next

The next research action is E001-SC2. Freeze a policy-risk predictor on
calibration, keep `periodic_local` as the default baseline, and test its
predicted learning penalty and modeled time/WAN consequence on a wholly
held-out model or optimizer family. SC1's six evaluation families do not
become tuning data. E002-PW3 remains available as optional physical
calibration for rack-power claims; it does not gate the software research
loop.
