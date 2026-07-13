# E001: Beyond One Datacenter

Status: recovery mechanics executed; LC1 small-model candidate falsified

## Question

Can a frontier model be pretrained across heterogeneous and intermittently
available datacenters without giving up the learning efficiency of one tightly
synchronized cluster?

## Hypothesis

A controller that jointly adapts local-step count, sparse communication
topology, asynchronous pipeline depth, optimizer correction, parallelism, and
site membership will:

- retain at least 95% of centralized loss progress per training FLOP;
- use at least 10 times fewer inter-site bytes than synchronous global
  all-reduce;
- finish sooner under realistic site-power interruptions than centralized or
  fixed local-update baselines;
- keep divergence probability inside a preregistered uncertainty bound.

The numeric thresholds are predictions to test, not current claims.

## Why This Matters

Power availability is now a limiting factor in 100 MW-class AI facilities.
Treating multiple sites as one adaptive learning system could unlock otherwise
stranded power and hardware. Current work demonstrates individual mechanisms,
but not frontier-scale learning behavior under joint network, power, hardware,
and failure heterogeneity.

Adjacent evidence includes [GASLoC](https://arxiv.org/abs/2606.11081) for
bandwidth-heterogeneous local updates,
[DynaTrain](https://arxiv.org/abs/2605.18815) for rapid parallelism changes,
and the [100 MW-scale cluster study](https://arxiv.org/abs/2605.24461) for the
facility power constraint. None validates their joint effect on frontier-scale
learning across sites.

## Virtual Datacenter

Model three to eight sites. Each site has:

- accelerator type, count, memory, and component power behavior;
- internal topology and measured collective curves;
- WAN bandwidth, latency, loss, and congestion state;
- power envelope, ramp limits, price, carbon, and interruption trace;
- cooling and ambient response;
- hard failure, fail-slow, and repair processes;
- local storage and checkpoint bandwidth.

Training state includes model and optimizer shards, data position, gradient or
update age, pipeline state, checkpoints, and validation-loss surrogate state.

## Interventions

- add or remove a site;
- change data, tensor, pipeline, expert, context, or sequence parallelism;
- change local-update count and synchronization topology;
- change pipeline delay and optimizer correction;
- migrate state directly or recover from a checkpoint;
- delay, stagger, or reshape a collective;
- shift power caps or workload among sites.

## Baselines

1. One centralized synchronous cluster with equivalent total accelerators.
2. Synchronous multi-site all-reduce.
3. Fixed local-update interval.
4. Fixed sparse-gossip topology.
5. Power-aware job migration without learning-state adaptation.
6. Oracle with future power and failure traces, used only as a regret bound.

## Experimental Matrix

- Dense and MoE model families.
- AdamW and delay-tolerant optimizer families.
- Homogeneous and mixed accelerator generations.
- Stable power, scheduled curtailment, stochastic interruption, and correlated
  regional stress.
- Dedicated WAN, shared WAN, and congestion bursts.
- Clean operation, visible failures, fail-slow devices, and combined faults.

Calibration and evaluation withhold complete site, hardware, workload, and
stress combinations.

## Outcomes

Primary:

- wall-clock time and facility joules to a held-out loss target;
- loss progress per training FLOP;
- inter-site bytes and peak WAN demand;
- divergence or unacceptable quality probability;
- policy decision regret and uncertainty coverage.

Secondary:

- useful accelerator utilization;
- checkpoint and migration traffic;
- grid-facing peak, ramp, and spectral power;
- cost and carbon under identical accounting boundaries;
- failure recovery time and lost learning work.

## Falsifiers

The hypothesis is falsified if any of these survive uncertainty analysis:

- adaptive operation fails to retain 95% of centralized loss progress per
  FLOP;
- communication falls by less than 10 times;
- fixed policies match adaptive control within experimental uncertainty;
- surrogate-predicted convergence does not transfer to held-out real runs;
- power shifting reduces local demand but increases total time-to-target enough
  to erase the energy or cost benefit.

## Validation Ladder

1. Replay public power, network, and failure traces in GPUSTACK.
2. Calibrate learning-delay surrogates on repeated small-model runs.
3. Shadow-mode comparison on at least three real clusters.
4. Controlled 7B to 30B experiments with bandwidth and power perturbations.
5. Multi-week 30B to 100B-plus run over at least three geographic sites.

Only the final two stages can support a claim about convergence and capability.

## First Engine Slice

Implement the smallest substrate that can falsify the virtual result:

- `Observation`, `CalibrationSplit`, and `EvaluationSplit` artifacts;
- event timeline for compute, collectives, state transfer, power, and failure;
- multi-site topology and WAN contention;
- intervention and policy interface;
- delayed-update learning surrogate with explicit calibration limits;
- experiment report containing residuals, uncertainty, and decision regret.

The implemented slice now produces a content-addressed mechanics artifact and
causal-observatory projection. It models successive compute, collective, and
checkpoint epochs; WAN and endpoint contention; fixed-time site interruption;
base plus accelerator-compute energy; and cadence decisions made only from a
completed communication cycle.

The v1 slice does not implement mid-operation recovery. That boundary is now
covered separately by [Recovery Mechanics v2](recovery-mechanics-v2.md) and
`E001_RECOVERY_V2_PROTOCOL`, without changing the frozen v1 artifact.

## Recovery Mechanics v2 Result

The v2 runner executes synchronous wait and restore, fixed-local checkpoint
restart, adaptive recovery, and a future-trace oracle comparator against one
absolute-time failure trace. It records failure visibility, preemption,
atomic checkpoint lineage, restore, replay, desired/effective membership,
durable frontier, lost work, recovery time, traffic classes, and modeled energy.

All four policies reach durable frontier 8 with exact work conservation:

| Policy | Completion | Inter-site bytes | Lost work | Modeled energy |
|---|---:|---:|---:|---:|
| Synchronous wait + restore | 1.584 s | 15.2 GB | 114.64 PFLOP | 0.274 MJ |
| Fixed-local checkpoint restart | 1.516 s | 10.4 GB | 144.50 PFLOP | 0.283 MJ |
| Adaptive recovery | 1.536 s | 13.6 GB | 48.43 PFLOP | 0.255 MJ |
| Future-trace recovery oracle | 1.536 s | 13.6 GB | 57.00 PFLOP | 0.257 MJ |

Adaptive beats synchronous by 48 ms and 1.6 GB on this trace. It does not
dominate fixed-local: fixed-local is faster and moves fewer bytes, while
adaptive loses much less work and uses less modeled energy. The oracle does
not improve on adaptive time or traffic in this scenario. These are modeled
mechanics, not a general controller ranking.

Every policy in this mechanics-only artifact carries the same declared `0.1`
learning-progress prior. The recovery-v2 result therefore remains
`inconclusive_frontier_hypothesis`: it resolves whether GPUSTACK can represent
a recovery comparison, but not whether adaptive recovery preserves learning
more efficiently. LC1 addresses that narrower learning question below.

Result artifact:
`results/recovery-mechanics-v2.json` (`b1200f99487afe9c690fa723b45a9be764e40f63d8ff4a1e897154e630b29b57`).
Observatory projection:
`../../docs/data/e001-recovery-v2.json` (`2b3c33bac5a0e9e9009b758be54078ac8b4aa9ae4baf343145a81d7e0a6afb05`).

## Learning Calibration v1 Result

[E001-LC1](learning-calibration-v1.md) completed 40 local GPU runs: 10
calibration observations and 30 untouched held-out evaluation observations.
The calibration-derived target was held-out NLL `3.13759109564126`. Every
policy first crossed it at the first 32-tick observation, so fixed-local and
adaptive interruption both recorded tick 32.

The preregistered candidate was falsified on this small-model calibration.
Paired progress-per-FLOP `tau` had median `-7.19835770326443e-14` with a 90%
interval `[-7.24876398177115e-14, -5.48204063742032e-14]`, failing the positive-
effect gate. Adaptive passed the retained-progress and synchronous-reference
gates with lower bounds `1.00215623908839` and `1.00265505192967`, and it did
not diverge. It failed the separate requirement to reach the target sooner
because both policies tied at tick 32.

| Interrupted median | Fixed-local restart | Adaptive continuation |
|---|---:|---:|
| Final held-out NLL | 2.341145828 | 2.314653009 |
| Attempted tokens | 458,752 | 524,288 |
| Canonical tokens | 442,368 | 524,288 |
| Replayed / discarded tokens | 16,384 / 16,384 | 0 / 0 |
| Survivor-redistributed tokens | 0 | 32,768 |
| First target crossing | tick 32 | tick 32 |
| Checkpoint bytes | 302 MB | 1.049 GB |

Adaptive ended with better held-out loss and completed all canonical work.
Fixed-local did 12.5% less attempted work and ended worse, but its smaller
finite-horizon from-scratch denominator made progress per attempted FLOP look
12.7% better. LC1 therefore rejected the candidate while also showing that
this progress-per-FLOP estimand is not a valid recovery-value comparator for
the regime it created.

Result artifact:
`results/learning-calibration-v1.json` (`0597ca6deeeb34ae97d57d72b49187c687af921d3eec7b804ceb48b0d3994826`).
Engine source:
`3a51c72de99fd17580b0bbf4bbc6722db7470b41ac8d74d2f9fcabc386cdb010`.
Scenario:
`3ea1ccd6fc717ded9d4f7150574df806a8dc7572fa35d00314f9bb3ea744c319`.
Observatory projection:
`../../docs/data/e001-learning-v1.json` (`ff6b5a56dab3314f9ad0b1def40fda9ce9df540bda411284bb9766d9a3ee3c12`).

This is measured small-model learning and device-only energy on one local GPU.
The datacenter recovery timeline, concurrent-site throughput, WAN, storage,
host, cooling, and facility-energy quantities remain modeled or unmeasured.

## Next Experiment: LC2

Warm-start fixed-local and adaptive recovery from the same late-training
checkpoint, freeze a quality target before evaluation, and compare wall-clock
time, device energy, attempted work, and canonical work to that target under
matched interruptions. Then bridge the observed learning curves to the modeled
datacenter mechanics with an explicit observation-to-model boundary; do not
relabel modeled datacenter behavior as measured evidence.
