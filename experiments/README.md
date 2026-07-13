# Experiments

Each experiment directory contains a frozen scientific question, hypothesis,
baselines, variables, observations, metrics, falsifiers, and path to real-world
validation.

An experiment moves through these states:

1. `designed`: hypothesis and falsifiers are frozen.
2. `virtual`: executed in GPUSTACK with calibration/evaluation separation.
3. `shadow`: predictions compared with live telemetry without controlling it.
4. `controlled`: bounded real-cluster intervention.
5. `validated`, `falsified`, or `inconclusive`.

Simulation-only results never advance beyond `virtual`.

## Frontier program

| ID | Experiment | Current state | Primary causal test |
|---|---|---|---|
| E001 | [Beyond One Datacenter](e001-beyond-one-datacenter/experiment.md) | LC3 executed; survivor-continuation candidate falsified only on held-out device energy | Can a joint controller preserve learning efficiency while cutting cross-site communication under interruption? |
| E002 | [Shape the Power Waveform](e002-power-waveform-shaping/experiment.md) | designed | Can dependency-safe phase control suppress grid-danger-band power without changing optimizer semantics? |
| E003 | [Semantic Fault Tolerance](e003-semantic-fault-tolerance/experiment.md) | designed | Can protection be allocated by counterfactual learning harm rather than fault label? |
| E004 | [Fluid Inference Topology](e004-fluid-inference-topology/experiment.md) | designed | Do jointly controlled serving mechanisms create interaction gains and repeated topology-regime crossings? |
| E005 | [Heterogeneous Architecture Co-design](e005-heterogeneous-architecture-codesign/experiment.md) | designed | Does hardware-aware architecture search beat heterogeneous placement of a frozen architecture? |
| E006 | [Firm Grid-responsive Inference](e006-firm-grid-responsive-inference/experiment.md) | designed | Can request-conditioned serving control provide meter-verified firm reserve without hidden quality, tail, or rebound debt? |

Numeric thresholds in these files are preregistered predictions. They are not
GPUSTACK results or values borrowed from the cited papers. Every program keeps
virtual screening, held-out evaluation, shadow deployment, and controlled
real-cluster evidence as separate stages.

## Persisted E001 research artifacts

The v1 screening artifacts are:

- full trace and run contract:
  `e001-beyond-one-datacenter/results/screening-mechanics-v1.json`;
- deployable causal projection: `../docs/data/e001-screening-v1.json`.

All three policies execute the same modeled compute and checkpoint workload.
The synchronous comparator records 33.6 TB of payload-link traffic and
6,047.01 seconds, fixed-local records 4.2 TB and 1,341.98 seconds, and adaptive
cadence records 1.68 TB and 938.60 seconds. These values imply a
`1.68 / 33.6 = 0.05` collective-payload link-byte ratio for the adaptive
policy in the virtual screen. That ratio excludes aborted collectives,
checkpoint and restore traffic, recovery-state transfer, and migration, so it
is a diagnostic rather than a complete WAN result.

Recovery mechanics v2 now persists:

- four-policy result:
  `e001-beyond-one-datacenter/results/recovery-mechanics-v2.json`;
- deployable observatory projection: `../docs/data/e001-recovery-v2.json`.

All policies reach durable frontier 8 under the same two-failure trace and
conserve work exactly. Synchronous records 1.584 s, 15.2 GB, 114.64 PFLOP lost,
and 0.274 MJ. Fixed-local records 1.516 s, 10.4 GB, 144.50 PFLOP lost, and
0.283 MJ. Adaptive records 1.536 s, 13.6 GB, 48.43 PFLOP lost, and 0.255 MJ.
The oracle records 1.536 s, 13.6 GB, 57.00 PFLOP lost, and 0.257 MJ.

Adaptive beats synchronous on the narrow modeled mechanical comparison, but
fixed-local is faster and lower-traffic while adaptive loses far less work and
uses less modeled energy. LC1 now supplies the previously missing measured
small-model learning response.

### Learning calibration v1

E001-LC1 completed 40 local GPU runs: 10 calibration observations and 30
held-out evaluation observations. The calibration-only target was held-out NLL
`3.13759109564126`; every evaluation policy first crossed it at tick 32, so the
frozen time-to-target test tied.

The preregistered conclusion is
`candidate_falsified_small_model_calibration`. Paired progress-per-FLOP `tau`
had median `-7.19835770326443e-14` with a 90% interval
`[-7.24876398177115e-14, -5.48204063742032e-14]`. Adaptive nevertheless passed
the retention and synchronous-reference gates: their lower bounds were
`1.00215623908839` and `1.00265505192967`.

Under interruption, fixed-local ended at median held-out NLL `2.341145828`
after 458,752 attempted and 442,368 canonical tokens, with 16,384 replayed and
16,384 discarded. Adaptive ended better at `2.314653009` after 524,288
attempted and canonical tokens, with no replay or discard and 32,768 survivor-
redistributed tokens. Both reached the loose target at tick 32. Adaptive wrote
1.049 GB of checkpoints versus fixed-local's 302 MB.

Fixed-local did 12.5% less attempted work and ended worse, yet the
finite-horizon from-scratch progress-per-FLOP denominator made it look 12.7%
better. That estimand does not rank recovery value in this regime. LC2
therefore tested a warm-started quality-to-target endpoint; its two protocol
results are preserved below. LC3 then replaced unstable first crossing with an
equal-canonical-work held-out comparison.

Artifacts:

- measured result: `e001-beyond-one-datacenter/results/learning-calibration-v1.json`
  (`0597ca6deeeb34ae97d57d72b49187c687af921d3eec7b804ceb48b0d3994826`);
- engine source: `3a51c72de99fd17580b0bbf4bbc6722db7470b41ac8d74d2f9fcabc386cdb010`;
- scenario: `3ea1ccd6fc717ded9d4f7150574df806a8dc7572fa35d00314f9bb3ea744c319`;
- observatory projection: `../docs/data/e001-learning-v1.json`
  (`ff6b5a56dab3314f9ad0b1def40fda9ce9df540bda411284bb9766d9a3ee3c12`).

The evidence is one byte-level small model on one local GPU. Energy is sampled
device energy only. Simultaneous-site throughput, WAN, checkpoint storage,
host, cooling, facility energy, and other datacenter mechanics remain modeled
or unmeasured.

### Quality-to-target protocol results

LC2 v1 and v2 are preserved protocol evidence, not candidate comparisons.

- V1's 2,048-tick warm state improved from NLL `1.52376570366323` to
  `1.43749829754233` over its final 256 ticks. The `0.08626740612089634`
  improvement exceeded the frozen `0.03` maximum, so the result stopped as
  `protocol_failed_warm_start_not_late_stage` before held-out evaluation.
  Artifact: `e001-beyond-one-datacenter/results/quality-target-v1.json`
  (`4781781857ae638f6e64868ed3fa156d9459f5f64e62f82aad3db6cde3bfd0c6`).
- V2's 8,192-tick warm state passed with NLL improvement
  `0.004534989595413208`, and its fixed/adaptive calibration curves were
  exactly equivalent. Its calibration-only target `1.01961656101048` was
  first crossed at ticks 40 and 96 rather than inside the frozen 192 to 288
  window because late-stage NLL was non-monotonic. It stopped as
  `protocol_failed_calibration_validity`, again before held-out evaluation.
  Artifact: `e001-beyond-one-datacenter/results/quality-target-v2.json`
  (`a3bb91b74a99708a08b5196ffc8d16bb27bca697f7f54fb63e60564851f97517`).

### Equal-canonical-work calibration v1

E001-LC3 retained the valid 8,192-tick warm state but compared policies at the
same 524,288-token canonical frontier instead of using unstable first
crossing. Two calibration pairs remained exactly equivalent. All six untouched
held-out fixed/adaptive pairs completed.

Adaptive-minus-fixed final NLL had median `0.003338515292853117` and paired
90% interval `[0.0023927902802824974, 0.008503663819283247]`, passing the
frozen `0.01` noninferiority margin. Attempted-work saving had median
`0.030303030303030304` and interval
`[0.030303030303030304, 0.058823529411764705]`. Opportunity-tick saving had
median `40`, interval `[36, 44]`, and adaptive was earlier in all six pairs.

The sole failed gate was sampled training-device energy. Adaptive/fixed energy
had median ratio `1.0683917796356628` and interval
`[1.0017954332700434, 1.134269402803286]`, above the frozen `1.05` upper bound.
The persisted conclusion is `candidate_falsified_equal_canonical_work`.

At the median, fixed-local used NLL `1.0195826`, 296 opportunity ticks, 540,672
attempted tokens, 524,288 canonical tokens, `75.295 J`, `7.443 s`, 385,076,112
checkpoint bytes, and 17 checkpoints. Adaptive used NLL `1.0248523`, 256 ticks,
524,288 attempted and canonical tokens, `81.556 J`, `8.384 s`, 1,064,622,192
checkpoint bytes, and 47 checkpoints. Fixed replayed and discarded 16,384
tokens; adaptive replayed and discarded none and redistributed 32,768.

Artifacts:

- result: `e001-beyond-one-datacenter/results/equal-work-v1.json`
  (`f7548b68d4791978260f0bd557bf92041d0f769b796b1e684bbcab99e88f639f`);
- engine source:
  `893b2d25eed53122c59ee26ac95a10c2e9f2e360c0c9b6c39c14bf1d32d25fbd`;
- engine bundle:
  `b574609b19eeca593dc932ec09943a779b50a28b4d9e336afa07b5a18fa52249`;
- scenario:
  `f5212c19e701f183c7ab9aaf7620bf43c03a234eee92dd7e9d98c73c5c22a9ed`;
- observatory projection: `../docs/data/e001-equal-work-v1.json`
  (`5ff07c4cf5b59be04d14f1b66961e679c2cec127b521c386d54ff9ebaadc1ae1`).

The result redirects the next frontier question to E002, not larger E001
runs: attribute the energy penalty with an operation-to-facility waveform and
a frozen 2x2 checkpoint-cadence by continuation experiment. Test whether
dependency-safe phase scheduling removes the energy penalty without erasing
the held-out learning, work, or tick gains.
