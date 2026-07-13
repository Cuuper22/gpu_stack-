# E001-SC1: Observable Semantic Slack

Frozen July 13, 2026. The machine-readable contract is
[`semantic-consistency-scenario-v1.json`](semantic-consistency-scenario-v1.json).

## Question

Can one controller use only current and past training-system state to switch
between exact synchronization, exact forward recovery, one-step-delayed
updates, and periodic local updates, while preserving held-out learning and
reducing inter-site communication and completion time as bandwidth, available
compute, and membership change?

"Semantic slack" means temporary disagreement or update delay that the
optimizer can absorb without changing the equal-work held-out result beyond a
frozen margin. It is not permission to change the token stream, silently drop
work, or infer learning quality from throughput.

## Why this is not already answered

Recent work establishes strong pieces of the mechanism:

- [One-Step Gradient Delay Is Not a Barrier](https://arxiv.org/abs/2606.30634),
  June 29, shows optimizer-dependent tolerance to a fixed one-step delay at
  scale. It does not choose among changing delay, local updates, and recovery
  modes under joint infrastructure stress.
- [GASLoC](https://arxiv.org/abs/2606.11081), June 9, joins local updates and
  sparse peer communication for bandwidth-heterogeneous LLM pretraining. It
  does not include hard failure recovery, power availability, or an online
  switch back to exact or delayed execution.
- [Demystifying Pipeline Parallelism](https://arxiv.org/abs/2606.03498), June
  2, shows theoretically and empirically that the winner between stale
  pipeline updates and LocalSGD depends on the objective. It does not identify
  a transferable observable boundary.
- [Ringmaster LMO](https://arxiv.org/abs/2605.18174), May 18, adapts delay
  thresholds under worker-speed heterogeneity. It does not jointly choose
  local-update, recovery, and topology semantics.
- [ReCoVer](https://arxiv.org/abs/2605.11215), May 11, preserves an exact
  failure-free stochastic trajectory through failures at up to 512 GPUs. It
  does not test when bounded temporary disagreement is more valuable than
  exact preservation.
- [DynaTrain](https://arxiv.org/abs/2605.18815), May 12, makes rapid
  parallelism reconfiguration practical. It provides an action mechanism, not
  a learning-aware policy for choosing the regime.
- [OpenG2G](https://arxiv.org/abs/2605.05519), May 6, demonstrates the value of
  measurement-backed software simulation for datacenter control. Its AI
  workload does not evolve through controllable learning and recovery state.

The defensible novelty statement is that this reviewed set does not evaluate
one observable policy boundary across exact recovery, delayed updates, and
local updates under joint network, compute-power, and failure variation. That
is evidence of an open intersection, not proof that no unreviewed work exists.

## Experiment

One deterministic byte-level transformer is warmed to the same late-stage
state used by E001-LC3. Every arm receives the same two site-specific token
quotas for each of 256 canonical ticks. The four fixed policies and the
observable controller all finish the same 524,288 canonical tokens. A
non-executable hindsight envelope selects one of those complete runs after the
fact; it does not create a sixth training policy.

The four fixed policies are:

1. `synchronous_restart`: exact synchronization; a failure rolls back to the
   latest durable merge and replays.
2. `exact_forward_recovery`: exact synchronization; the survivor processes
   the missing site's deterministic quota so the iteration sample stays exact.
3. `delayed_one_step`: one-step-old aggregate updates. This is not claimed to
   reproduce PipeDream-2BW or the error-feedback method in the cited paper.
   Gradient transfer for tick `t` overlaps computation of the still-stale
   gradient for tick `t+1`; the first compute and final transfer/update are
   explicit pipeline fill and drain rather than free work.
4. `periodic_local`: independent site updates with exact averaging every eight
   ticks. This is not claimed to be GASLoC or a gossip implementation.

`observable_adaptive` can choose only those action semantics from current and
past bandwidth, compute-rate, membership, checkpoint age, update age, replica
disagreement, recent gradient norm, and held-out-loss slope. Unsupported state
causes an explicit abstention to exact forward recovery. It cannot see the
future stress trace, future gradients, or future loss.

`future_trace_oracle` is deliberately narrower than a dynamic clairvoyant
controller: it uses the full future bandwidth, compute-rate, and membership
schedule to select the cheapest one of the five complete measured policy
schedules, including the observable controller. It never sees future data,
gradients, parameters, or loss, and it cannot mix actions per tick. It is a
hindsight whole-policy envelope, not a deployable comparator or a claim of
dynamic optimality.

Four calibration strata select the best fixed comparator and freeze controller
thresholds. Six untouched evaluation families vary bursty bandwidth, compute
throttling, and membership loss. Evaluation data cannot change the comparator
or controller. Their individual bandwidth, compute-rate, and membership values
stay inside the calibration support; what remains held out is their temporal
composition. The scenario intended those values to remain inside calibration
support. The completed run instead exposed site-A compute-rate values below
the frozen calibration floor in three evaluation families; those epochs are
published as out-of-distribution abstentions rather than silently absorbed.

## Primary decision

The small-model semantic-slack hypothesis survives only if all evaluation
gates pass:

- adaptive minus the calibration-selected best fixed policy has a paired 90%
  upper bound on final held-out NLL no greater than `0.01`;
- adaptive inter-site payload bytes have a paired 90% ratio upper bound no
  greater than `0.20`;
- adaptive modeled completion time has a paired 90% ratio upper bound no
  greater than `0.90`;
- normalized completion-time regret to the hindsight whole-policy envelope
  has an upper bound no greater than `0.10`;
- no divergence, sample-identity violation, or lineage violation occurs.

The comparator is chosen on calibration only. A fixed policy matching adaptive
rejects the joint-control novelty even if the numerical gates pass.

## Result — July 13, 2026

The complete run produced 20 calibration runs, 30 executable evaluation runs,
and six non-executable hindsight-envelope records. Calibration selected
`periodic_local` as the fixed comparator. The persisted conclusion is
`abstain_without_policy_claim`: the artifact is valid for scoring, but the
adaptive-controller hypothesis failed and three held-out families crossed the
calibrated visible-state boundary.

| Paired adaptive / `periodic_local` outcome | Median | 90% interval | Frozen gate | Result |
|---|---:|---:|---:|---|
| Final held-out NLL difference | `+0.016659` | `[+0.001785, +0.042213]` | upper `<= +0.01` | fail |
| Inter-site payload ratio | `2.128x` | `[1.556x, 2.552x]` | upper `<= 0.20x` | fail |
| Modeled completion-time ratio | `1.072x` | `[0.986x, 1.099x]` | upper `<= 0.90x` | fail |
| Hindsight whole-policy-envelope regret | `0.07155` | `[0.03349, 0.10056]` | upper `<= 0.10` | fail |

Attempted-FLOP ratio was exactly `1.0`. All 30 evaluation runs completed with
zero divergence, sample-identity mismatch, optimizer-lineage violation, or
work-contract violation. The failure is therefore attributable to this
controller and hypothesis under the executed model and scenarios, not to an
incomplete run or unequal work.

The controller recorded 104 out-of-distribution abstention ticks: 32 in
E2, 48 in E4, and 24 in E6. Local device-energy comparison was unavailable
because there were no complete paired measurements. Per-arm wall duration and
energy remain descriptive sequence-confounded observations and do not enter
the ranking.

This result does not establish `periodic_local` as universally optimal. It
establishes that the current observable switching rule did not transfer even
across these six stress families on one byte-level AdamW model, while the
simple periodic-local baseline was both the calibration winner and the harder
held-out comparator.

## Research redirect

E001-SC2 should test a stricter question without retuning on these six
families: can a calibration-trained predictor estimate, before a switch, each
policy's learning penalty and modeled time/WAN consequence across wholly
held-out model or optimizer families? The default baseline remains
`periodic_local`. A transfer failure or calibrated abstention is a result; the
next controller is not allowed to convert these evaluation families into new
training data.

## Evidence classes

- **Measured here:** optimizer updates, per-site parameter state, replica
  disagreement, a frozen post-warm compute microbenchmark, held-out NLL, and
  device energy when the supported local counter is available. Per-arm wall
  duration and energy remain descriptive because the sequential local harness
  can thermally drift; neither can choose the comparator or determine modeled
  completion time.
- **Exact accounting:** token identities, attempted/useful/replayed work,
  update age, model and optimizer lineage, mode transitions, merge/rejoin
  events, and logical payload bytes.
- **Modeled:** WAN transfer time, compute-rate scaling of the one frozen
  post-warm compute reference under the power-availability schedule, and total
  virtual completion time.
- **Unresolved:** frontier-model learning transfer, real WAN tails, correlated
  regional failure, host/storage/cooling/facility energy, and grid behavior.

Sampling uncertainty across the six evaluation families and epistemic
infrastructure uncertainty are reported separately. No physical run is needed
to produce the result. A later physical collaboration may calibrate or falsify
specific modeled boundaries, but it is not a prerequisite for GPUSTACK's
research loop.

## Required artifact path

- research result:
  `experiments/e001-beyond-one-datacenter/results/semantic-consistency-v1.json`;
- compact observatory projection: `docs/data/e001-semantic-consistency-v1.json`;
- lazy epoch trace: `docs/data/e001-semantic-consistency-raw-v1.json`.

The artifact must publish failures and abstentions as results. It must not
replace missing learning evidence with a timing surrogate or replace modeled
infrastructure with physical language.

Persisted semantic hashes:

- result: `e4bb8023145bdb21e97b9a5d295dc778f58adccc452d2bd9d3e4a599bf53bbc7`;
- compact observatory: `369bc4e9b32d6e1fcdd8dadc98c830e5ac5179f4a7204a9f5194e22913fdefdf`;
- raw observatory trace: `d6321d6fc4c0f71c4f14c2f799eff252348073b3fe5508783f9f078e7f5e9d76`;
- dataset: `77cf780cebe52b6e83e3a2ac84bc56d8059363113e41d17a023f1d8b2ed0fc0b`.
