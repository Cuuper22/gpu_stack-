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
| E001 | [Beyond One Datacenter](e001-beyond-one-datacenter/experiment.md) | recovery mechanics executed; LC1 small-model candidate falsified on held-out learning evidence | Can a joint controller preserve learning efficiency while cutting cross-site communication under interruption? |
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
better. That estimand does not rank recovery value in this regime. LC2 will
warm-start late in training, freeze the quality target, and compare time,
device energy, and work to target. Observed learning curves will then be
bridged to modeled datacenter mechanics without calling those mechanics
measured.

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
