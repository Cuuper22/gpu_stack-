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
| E001 | [Beyond One Datacenter](e001-beyond-one-datacenter/experiment.md) | four-policy recovery mechanics executed and visualized; learning comparison unresolved | Can a joint controller preserve learning efficiency while cutting cross-site communication under interruption? |
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

Adaptive beats synchronous on the narrow mechanical comparison, but
fixed-local is faster and lower-traffic than adaptive while adaptive loses far
less work and uses less modeled energy. Learning progress is the same declared
prior for every policy. The result is therefore a Pareto split and the only
honest current conclusion remains `inconclusive_frontier_hypothesis`.

The next experiment is a measured fixed-local versus adaptive learning
comparison under matched interruption. It must resolve held-out progress per
FLOP, per joule, and per wall-clock second before the engine is generalized.
