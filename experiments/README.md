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
| E001 | [Beyond One Datacenter](e001-beyond-one-datacenter/experiment.md) | mechanics screen implemented; no held-out learning result | Can a joint controller preserve learning efficiency while cutting cross-site communication under interruption? |
| E002 | [Shape the Power Waveform](e002-power-waveform-shaping/experiment.md) | designed | Can dependency-safe phase control suppress grid-danger-band power without changing optimizer semantics? |
| E003 | [Semantic Fault Tolerance](e003-semantic-fault-tolerance/experiment.md) | designed | Can protection be allocated by counterfactual learning harm rather than fault label? |
| E004 | [Fluid Inference Topology](e004-fluid-inference-topology/experiment.md) | designed | Do jointly controlled serving mechanisms create interaction gains and repeated topology-regime crossings? |
| E005 | [Heterogeneous Architecture Co-design](e005-heterogeneous-architecture-codesign/experiment.md) | designed | Does hardware-aware architecture search beat heterogeneous placement of a frozen architecture? |
| E006 | [Firm Grid-responsive Inference](e006-firm-grid-responsive-inference/experiment.md) | designed | Can request-conditioned serving control provide meter-verified firm reserve without hidden quality, tail, or rebound debt? |

Numeric thresholds in these files are preregistered predictions. They are not
GPUSTACK results or values borrowed from the cited papers. Every program keeps
virtual screening, held-out evaluation, shadow deployment, and controlled
real-cluster evidence as separate stages.

## Persisted E001 mechanics screen

The current E001 artifacts are:

- full trace and run contract:
  `e001-beyond-one-datacenter/results/screening-mechanics-v1.json`;
- deployable causal projection: `../docs/data/e001-screening-v1.json`.

All three policies execute the same modeled compute and checkpoint workload.
The synchronous comparator records 33.6 TB of payload-link traffic and
6,047.01 seconds, fixed-local records 4.2 TB and 1,341.98 seconds, and adaptive
cadence records 1.68 TB and 938.60 seconds. The adaptive policy therefore
survives the preregistered WAN-traffic scalar in the virtual screen.

It does not survive the experiment as a whole yet. Progress per FLOP and time
to a held-out target remain unresolved, all seven mandatory structured E001
requirements are unresolved, reactive outage membership is absent, and the
energy value excludes network, checkpoint, storage, host, and cooling power.
The only honest current conclusion is `inconclusive`.
