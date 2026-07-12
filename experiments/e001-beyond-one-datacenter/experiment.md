# E001: Beyond One Datacenter

Status: designed

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
