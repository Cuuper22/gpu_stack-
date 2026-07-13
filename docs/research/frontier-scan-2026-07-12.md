# Ninety-Day Frontier Scan

Cutoff: July 12, 2026. The strict seed window is April 13 through July 12,
2026. Most cited items are recent preprints and should not be described as
settled results.

## Finding

The frontier is crowded with accurate performance simulators and strong local
optimizations. It is not crowded with falsifiable models of the whole learning
datacenter.

[Charon](https://arxiv.org/abs/2605.17164) reports less than 5.35% overall
performance-prediction error and less than 3.74% for large-cluster training.
GPUSTACK therefore needs a different research claim. Its defensible territory
is joint causal modeling of learning progress, temporal execution, state
movement, failures, facility power, grid interaction, economics, and
uncertainty, with explanations that expose every assumption.

## Completed Software-First Question and Redirect: July 13, 2026

GPUSTACK completed E001-SC1 without waiting for physical rack access:

> Can an observable controller switch among exact synchronization, exact
> forward recovery, one-step-delayed updates, and periodic local updates as
> bandwidth, available compute, and membership change, while preserving
> held-out learning and reducing communication and completion time?

The recent papers make this question newly concrete. [One-Step Gradient Delay
Is Not a Barrier](https://arxiv.org/abs/2606.30634) shows that optimizer choice
can remove the assumed fixed-delay barrier. [GASLoC](https://arxiv.org/abs/2606.11081)
shows that local steps and sparse communication can improve heterogeneous LLM
pretraining. [Demystifying Pipeline Parallelism](https://arxiv.org/abs/2606.03498)
shows that stale pipeline updates and LocalSGD cross in performance depending
on the objective. [Ringmaster LMO](https://arxiv.org/abs/2605.18174) adapts
delay thresholds under worker-speed heterogeneity. [ReCoVer](https://arxiv.org/abs/2605.11215)
preserves an exact stochastic trajectory through failures, while
[DynaTrain](https://arxiv.org/abs/2605.18815) makes rapid topology changes
practical.

None of that reviewed work evaluates one deployable boundary among exact
recovery, delayed updates, and local updates under joint network, compute-power,
and failure variation. That is a literature-supported gap, not a universal
priority claim. E001-SC1 first measures the mechanism on one byte-level model
and uses GPUSTACK for the datacenter counterfactuals. Frontier-model transfer
remains unresolved unless a later held-out model-family experiment supports it.

The result rejected the proposed controller. Calibration selected
`periodic_local`. Against that frozen comparator, adaptive switching had a
median held-out NLL penalty of `+0.016659` with a paired 90% interval of
`[+0.001785, +0.042213]`, a WAN-payload ratio of `2.128x [1.556x, 2.552x]`,
and a modeled-completion ratio of `1.072x [0.986x, 1.099x]`. The hindsight
whole-policy-envelope regret interval ended at `0.10056`, narrowly above its
`0.10` ceiling. There were zero divergence, sample, lineage, or equal-work
violations, so this is a controller/hypothesis failure rather than a broken
experiment.

The controller also recorded 104 abstention ticks outside its calibrated
visible-state support across E2, E4, and E6. That prevents a transferable
winner claim even apart from the failed numerical gates. The artifact's
conclusion is therefore `abstain_without_policy_claim`, not a softened success.

The next frontier question is E001-SC2:

> Can a calibration-trained predictor estimate, before switching, the
> policy-specific learning penalty and modeled time/WAN consequence across a
> wholly held-out model or optimizer family?

SC2 must hold out whole model or optimizer families and retain
`periodic_local` as the default baseline. The six SC1 evaluation families may
not be reused to tune the controller. A transfer failure remains publishable.

E002-PW3's physical rack protocol remains useful as an optional calibration or
falsification adapter. It no longer gates GPUSTACK's research roadmap.

## Fresh Evidence

| Date | Primary source | What it establishes | Boundary left open |
|---|---|---|---|
| 2026-04-16 | [EasyRider](https://arxiv.org/abs/2604.15522) | Rack hardware and storage can smooth millisecond-scale synchronized training power swings. | It does not test whether training schedules can remove the harmful phase locking. |
| 2026-04-17 | [DataCenterGym](https://arxiv.org/abs/2604.15594) | A physics-grounded Gym environment joins scheduling, thermal response, cooling, and service degradation. | It abstracts away AI job graphs, learning state, accelerator networks, and sub-second power behavior. |
| 2026-05-05 | [Anatomy of Silent Data Corruption](https://arxiv.org/abs/2605.04213) | GPU faults are structured; NaN-only and independent-bit models are inadequate. | It does not connect structured faults to long-run learning trajectories. |
| 2026-05-06 | [OpenG2G](https://arxiv.org/abs/2605.05519) | A modular simulator couples measured AI service behavior to grid simulators and controller interfaces. | Training remains an aggregate workload rather than an adaptive learning process with topology and failure state. |
| 2026-05-07 | [ResiHP](https://arxiv.org/abs/2605.06374) | Failure-aware hybrid parallelism improves throughput on 256 GPUs. | Power, silent corruption, and capability-level effects are outside its evaluation. |
| 2026-05-11 | [Maestro](https://arxiv.org/abs/2605.10501) | Compound-model sections can use independent parallelism and dynamic sample order. | The objective is utilization, not learning progress per facility joule. |
| 2026-05-11 | [ReCoVer](https://arxiv.org/abs/2605.11215) | Visible failures can be absorbed while preserving the stochastic training trajectory. | Fail-slow and silent faults remain separate problems. |
| 2026-05-12 | [DynaTrain](https://arxiv.org/abs/2605.18815) | A 70B layout can be reconfigured in under two seconds. | It supplies a mechanism, not a learning, power, and reliability policy. |
| 2026-05-16 | [Charon](https://arxiv.org/abs/2605.17164) | Fine-grained training and inference timing simulation is already accurate and useful. | It does not claim calibrated causal uncertainty or learning outcomes. |
| 2026-05-23 | [100 MW-scale cluster](https://arxiv.org/abs/2605.24461) | Production evidence from 83,000 GB200 GPUs in a 150 MW facility makes power a first-class scaling constraint. | The study is operational and descriptive rather than a learning-system co-design experiment. |
| 2026-06-09 | [GASLoC](https://arxiv.org/abs/2606.11081) | Sparse gossip, adaptive optimization, and local steps improve training under heterogeneous bandwidth. | Frontier-scale multi-site convergence and facility constraints remain untested. |
| 2026-06-17 | [Quantization-enabled demand response](https://arxiv.org/abs/2606.18851) | A simulated 40,960-H100 fleet suggests inference can expose grid flexibility. | Facility-scale validation is simulated rather than live. |
| 2026-06-23 | [Power-Flexible AI Data Centers](https://arxiv.org/abs/2606.25098) | A 130 kW deployment demonstrates curtailment and geographic load shifting. | It does not establish control at hyperscale or jointly model learning and failure state. |
| 2026-06-28 | [KernelFlume](https://arxiv.org/abs/2606.29207) | Attention capacity can scale independently for long-context agent workloads. | Large-model results rely partly on simulation and do not include facility behavior. |
| 2026-06-29 | [HMA-Serve](https://arxiv.org/abs/2606.29986) | Cross-vendor, memory-heterogeneous prefill/decode serving can improve goodput and cost. | Cross-boundary control with failures, power, and changing workloads remains open. |
| 2026-06-29 | [TraceLab](https://arxiv.org/abs/2606.30560) | Real coding-agent traffic has long loops, long contexts, short outputs, and heavy-tailed tool gaps. | Existing serving policies do not jointly value retained state, latency, and power during those gaps. |
| 2026-07-02 | [WattGPU](https://arxiv.org/abs/2607.02391) | Public specifications can predict unseen-GPU power and latency better than TDP and roofline baselines. | The study predicts mean behavior, not coupled datacenter dynamics and intervention effects. |
| 2026-07-02 | [Kairos](https://arxiv.org/abs/2607.02043) | Queueing and KV transfer can dominate P95 time-to-first-token in disaggregated serving. | Prefix residency, stale state, dispatcher scale, and larger clusters remain unresolved. |
| 2026-07-06 | [Direct model-state migration](https://arxiv.org/abs/2607.04749) | Checkpoint-free state movement makes elastic hybrid-parallel training more practical. | It does not decide when reconfiguration improves the global objective. |

## Unanswered Cross-Layer Questions

1. Can a frontier model train across separately powered and weakly connected
   datacenters without losing centralized learning efficiency?
2. Can compute and collective phase offsets shape the grid-facing power
   waveform while preserving the effective gradient estimator?
3. Can one controller jointly choose parallelism, consistency, placement,
   checkpointing, component power, and failure response?
4. Can structured silent corruption be controlled according to its actual
   effect on learning trajectory rather than whether a bit flipped?
5. Do heterogeneous inference systems collapse onto transferable regimes, or
   does every hardware and workload pair require unrelated profiling?
6. Can KV blocks, experts, model weights, draft capacity, and paused requests
   be priced under one quantity: expected future work avoided?
7. Can mixed hardware change the architecture worth training under a facility
   envelope, rather than only the placement of a fixed graph?
8. Which small set of datacenter interventions makes the causal model
   identifiable, and which quantities remain impossible to infer from normal
   telemetry?

## Immediate Research Standard

Before GPUSTACK proposes a new controller, it must beat TDP, roofline, fixed
MFU, static queueing, and simple engineering heuristics on held-out data. The
evaluation must withhold entire hardware families, workload families, topology
classes, and stress regimes. Report:

- absolute and relative prediction error;
- interval calibration and failure rate;
- configuration-ranking correlation;
- intervention decision regret;
- residual attribution accuracy;
- calibration data and compute required;
- transfer failure and abstention behavior.

The UI should make this evidence the first thing beneath a result. The full
equation ancestry remains one level deeper, available rather than compulsory.

## Competitive Boundary

GPUSTACK should interoperate with or benchmark against adjacent simulators,
not reimplement them blindly:

- Charon is the performance-simulation baseline.
- OpenG2G is the datacenter-to-grid control baseline.
- DataCenterGym is the thermal scheduling baseline.
- WattGPU is the unseen-hardware inference power baseline.

GPUSTACK's new claim begins where those abstractions meet: a measured learning
or serving process changes its own execution topology in response to network,
failure, power, thermal, and grid state, while the model exposes causal
uncertainty and the visual medium explains the intervention.

## Older Calibration Anchor

[Measurement of Generative AI Workload Power Profiles](https://arxiv.org/abs/2604.07345)
was submitted April 8, five days outside the strict window. Its public
0.1-second H100 traces are still the strongest immediate calibration input
found for temporal power work, but the date must remain explicit.
