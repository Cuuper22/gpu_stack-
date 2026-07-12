# E003: Semantic Fault Tolerance

Status: preregistered design; no experiment result exists

Protocol date: July 12, 2026

## Question

Can one training system treat fail-stop devices, fail-slow devices, and silent
data corruption according to their counterfactual effect on the learning
trajectory, then spend redundancy and recovery work only where the predicted
semantic harm justifies it?

## Non-Minor Novelty Gap

Existing resilience systems primarily organize around the observable symptom.
A crash triggers communicator repair or restart, a slowdown triggers
rebalancing, and a numerical anomaly triggers a checker. E003 asks whether the
common control quantity can instead be expected damage to future learning.

[ReCoVer](https://arxiv.org/abs/2605.11215) demonstrates forward recovery for
fail-stop losses while preserving a stochastic-equivalence invariant, evaluated
up to 512 GPUs with 256 GPUs lost across a run. [ResiHP](https://arxiv.org/abs/2605.06374)
jointly detects fail-stop and persistent fail-slow behavior and adapts hybrid
parallelism on 256 A100 GPUs; its paper reports about 99.4% failure-detection
accuracy and explicitly places failures without timing or liveness signatures
outside scope. [The Anatomy of Silent Data
Corruption](https://arxiv.org/abs/2605.04213) shows why a NaN checker or uniform
single-bit injector is not enough: in its gate-level campaign, NaN and infinity
are 1.01% of SDC outcomes, single-bit flips are less than 40% of bit-flip events,
and corruptions have warp-aligned spatial structure.

None of those results establishes which corrupted operations materially alter
a long training trajectory, whether a cheap semantic probe can identify them,
or how to allocate a fixed protection budget across visible failures, gray
failures, and silent corruption. E003's new claim is a unified, trajectory-
sensitivity policy that chooses canaries, selective recomputation, replay,
reconfiguration, and quarantine by expected learning harm rather than fault
label.

## Why Datacenter Scale Is Necessary

Small paired runs are necessary to obtain clean counterfactual labels, but the
research question is datacenter-scale for three reasons:

- rare faults become routine opportunities for interaction only across many
  devices and long runs;
- tensor, pipeline, data, and expert parallelism determine whether one local
  manifestation is masked, amplified, or committed globally;
- the overhead being constrained is total time and facility energy to a
  capability target, including idle survivors, network repair, checkpoint I/O,
  cooling, and discarded learning work.

The cited SDC paper spent more than three million simulator-hours across 63 CUDA
microbenchmarks to characterize device-level manifestations. It did not measure
fleet incidence or frontier-model trajectory effects. A virtual datacenter can
screen policies and a small cluster can establish mechanisms, but only a long,
large-cluster deployment can measure real incidence, interactions, and the
claimed less-than-2% production overhead.

## Preregistered Hypothesis

On held-out model, topology, training-phase, hardware, and mixed-fault regimes,
a trajectory-sensitivity policy using adaptive canaries and selective
redundancy will satisfy all of the following:

1. The defended run's primary held-out quality vector is equivalent to its
   paired clean-run distribution: every preregistered metric's 90% confidence
   interval lies inside a margin of **plus or minus 0.2 clean-run standard
   deviations**, and at least **95%** of defended runs finish inside the
   corresponding per-run equivalence region.
2. It intercepts at least **99%** of trajectory-critical injected events before
   a contaminated optimizer update is committed, while falsely isolating or
   replaying no more than **1%** of clean optimizer steps.
3. Its always-on time-to-target and facility-energy tax is no more than **2%**
   in clean runs, and its total tax remains no more than **2%** at a separately
   measured production fault incidence.
4. It uses at least **50% fewer redundant training FLOPs** than uniform duplicate
   execution while satisfying predictions 1 and 2.

These thresholds are predictions, not results. Prediction 3 at production
incidence is not evaluable until incidence is measured from a sufficiently long
fleet observation. Accelerated fault injection may test robustness, but it may
not be relabeled as production-rate evidence.

## Semantic Criticality

Each injected event receives an evaluation-only label from a paired oracle
counterfactual. The clean and faulted branches share the same initial
checkpoint, examples, random state, topology, and exogenous events. The oracle
compares:

- the next 1, 10, 100, and 1,000 optimizer steps;
- gradient direction and norm, update norm, parameter drift, and training loss;
- held-out loss and the frozen primary evaluation vector at the final budget;
- divergence, unrecoverable numerical state, and failure to reach the target.

An event is trajectory-critical if the no-defense branch leaves the
preregistered plus-or-minus-0.2-standard-deviation equivalence region on any
primary metric, diverges, or fails to reach the target within the fixed compute
budget. The policy never sees this oracle label. It observes only deployable
telemetry and canary outputs.

Clean-run standard deviations and any raw numerical floor for a near-zero-
variance metric are frozen from calibration runs before faults in the evaluation
split are revealed. A margin may be tightened for a domain requirement but may
not be widened after evaluation.

## Accounting Boundary

Every policy reports time, accelerator-seconds, training FLOPs, network bytes,
storage I/O, and facility joules from the same initial state to the same held-
out loss or capability target. The boundary includes:

- canary and duplicate computation;
- idle replicas during diagnosis or communicator repair;
- replayed microbatches and discarded optimizer steps;
- state repair, checkpoint reads and writes, and topology reconfiguration;
- survivor imbalance, fail-slow amplification, power, and cooling;
- quality regressions and runs that never reach the target.

Overhead is not inferred from kernel time alone. A defense that is cheap but
allows hidden quality damage fails prediction 1.

## Virtual Datacenter State

### Learning and lineage state

- model, optimizer, scheduler, gradient-scaler, data-order, and random state;
- operation-to-tensor and tensor-to-optimizer-step lineage;
- parameter version, microbatch provenance, collective membership, and commit
  status for every update;
- clean calibration distribution for trajectory and quality metrics;
- sensitivity estimate and uncertainty by layer, operation, tensor role,
  training phase, and parameter version;
- checkpoint recoverability and the exact work required by each repair action.

### Hardware, topology, and fault state

- accelerator, host, network, storage, rack, and power-domain topology;
- tensor, pipeline, data, expert, context, and sequence parallel groups;
- per-device compute and communication rate with workload-conditioned expected
  duration;
- fail-stop, fail-slow, data-unavailable, and silent-corruption processes;
- fault manifestation conditioned on unit, operation, data type, bit pattern,
  tensor address structure, duration, and persistence;
- canary placement, redundant-execution budget, detection latency, and repair
  queue;
- facility power and thermal state needed to account for defense cost.

The simulator retains the true injected event and clean branch for scoring. The
policy receives neither.

## Fault Models and Their Boundaries

### Structured silent corruption

The primary SDC injection family follows the conditional manifestation
structure reported by the Anatomy study where its data are available:

- nullification, non-special corrupt-but-valid values, and rare special values;
- multi-bit and bit-position-dependent changes rather than uniform single-bit
  flips;
- warp-aligned spatially correlated addresses;
- conditioning on exercised functional unit, operation, and data type;
- persistent stuck-at manifestations separated from transient sensitivity
  cases.

The paper characterizes outcomes conditional on injected permanent faults. It
does not provide a production SDC arrival rate, so E003 assigns no fabricated
default incidence. Random independent bit flips remain only a misspecification
baseline. They are not called realistic SDC.

### Visible and gray failures

- fail-stop worker, device, link, or storage loss at different points in an
  iteration;
- compute fail-slow and communication fail-slow at weak, medium, and severe
  levels calibrated from measured device and network rates;
- intermittent and persistent gray failures;
- workload-induced iteration variation without a hardware fault;
- correlated fail-slow-to-fail-stop transitions;
- mixtures of visible failure and SDC before, during, and after reconfiguration.

Arrival rates come from timestamped fleet observations when available.
Otherwise the matrix reports rate-free conditional response and explicitly
labeled sensitivity sweeps.

## Policy Observations

The deployable policy may use:

- heartbeats, device errors, collective status, and workload-conditioned timing
  residuals;
- low-cost activation, gradient, and parameter sketches;
- selected redundant micro-operations or microbatches;
- cross-replica consistency checks and lineage-aware checksums;
- loss, gradient-norm, update-norm, and parameter-drift residuals;
- uncertainty in its learned trajectory-sensitivity model.

It may not use the injected fault location, golden tensor, future loss, clean
counterfactual, or true simulator severity.

## Interventions

- place, remove, or increase a canary on a layer, kernel, tensor role, or device;
- redundantly recompute an operation or microbatch and compare semantic
  summaries;
- block an optimizer commit until a high-risk contribution is verified;
- replay a kernel, microbatch, gradient bucket, or complete optimizer step;
- discard a contaminated contribution while preserving the effective global
  batch through stochastic-equivalent reassignment;
- isolate or quarantine a device, link, rank, or state shard;
- change hybrid parallelism and redistribute work across healthy survivors;
- repair state from a peer, local lineage record, or checkpoint;
- abort and restart when predicted harm exceeds the forward-recovery bound;
- abstain and request a stronger check when uncertainty is out of distribution.

## Baselines

1. No defense beyond hardware-reported errors.
2. NaN, infinity, and loss-spike checks.
3. Checkpoint and restart with a tuned fixed checkpoint interval.
4. Workload-aware heartbeat and timing detection with hybrid-parallel
   reconfiguration, following the ResiHP capability boundary.
5. Stochastic-equivalent forward recovery for fail-stop loss, following the
   ReCoVer invariant.
6. Fixed canaries on the same layers at every step.
7. Uniform duplicate execution with comparison before commit.
8. A rule-based union of baselines 2, 4, and 5.
9. An oracle that knows the fault and counterfactual semantic label, used only
   as a regret and protection-budget bound.

Implementations are compared at matched quality constraints and accounting
boundaries. Published ResiHP and ReCoVer results are context, not values copied
into GPUSTACK's result table.

## Experimental Matrix

### Learning systems

- dense and mixture-of-experts models;
- AdamW and at least one optimizer with materially different update state;
- pretraining and continued-pretraining objectives;
- early, middle, and late training phases;
- attention, feed-forward, normalization, embedding, output, collective, and
  optimizer operations;
- FP8, BF16, and FP32 state where supported by the measured stack;
- 3D parallelism and hybrid sharded data parallel configurations.

### Scale

- single-device and 8-device paired counterfactual labeling;
- 32 to 64 GPUs for repeated end-to-end mechanism experiments;
- 256 to 512 GPUs for direct comparison with the scale boundary of recent
  fail-slow and forward-recovery work;
- 1,000-plus and 10,000-plus accelerator virtual and shadow-mode regimes;
- 30B to 100B-plus validation only after small-model mechanism gates pass.

These are experiment stages, not evidence that GPUSTACK currently supports or
has measured every point.

### Fault combinations

- each SDC manifestation family alone and in mixtures;
- fail-stop at compute, collective, checkpoint, and reconfiguration boundaries;
- compute and network fail-slow with real workload variability as a confounder;
- persistent, intermittent, and escalating faults;
- SDC on a nominal device and on a device already classified fail-slow;
- one event, burst events, and measured-rate long traces;
- 1x, 10x, and 100x measured incidence as sensitivity sweeps only after a 1x
  fleet estimate exists.

## Primary Outcomes

1. **Trajectory and final-quality equivalence.** Two one-sided equivalence tests
   on every frozen primary metric, paired by seed and corrected as one outcome
   family. Report the full vector, not only mean loss.
2. **Critical-event interception.** Recall for oracle-labeled trajectory-
   critical events before contaminated commit, with precision and false action
   rate reported beside it.
3. **Time and energy to target.** Wall-clock time, accelerator-seconds, and full
   facility joules to the same held-out target, including failures.
4. **Protection efficiency.** Redundant FLOPs and bytes per intercepted critical
   event, and fraction of protection spent on oracle-benign events.
5. **Decision quality.** Regret relative to the oracle allocation of the same
   protection budget and calibration of predicted semantic-harm intervals.

## Secondary Outcomes

- number and duration of contaminated uncommitted and committed updates;
- detection latency in operations and optimizer steps;
- false isolation, unnecessary replay, and clean-step blocking rate;
- lost learning work, checkpoint traffic, communicator repair time, and state
  migration bytes;
- useful accelerator utilization and fail-slow amplification across parallel
  groups;
- sensitivity-ranking correlation and causal fault-localization accuracy;
- abstention and out-of-distribution rate;
- peak facility power and cooling overhead caused by duplicate work;
- behavior after the defense budget is exhausted.

## Paired Design and Analysis

For each injected evaluation event, clean, undefended-faulted, and defended
branches begin from the same checkpoint and share sample order, random state,
topology, and exogenous trace. Fault manifestation is drawn once and replayed
across defenses. A policy is scored on what it knew before commit.

The final-quality hypothesis uses two one-sided tests with a 5% family-wise
error rate and the frozen equivalence margins. The interception and false-action
predictions use 95% confidence bounds: the lower bound must be at least 99% for
critical-event recall and the upper bound no more than 1% for clean-step false
actions. The 2% overhead and 50% redundancy predictions are tested with paired
95% intervals.

Evaluation counts are chosen from calibration-only prevalence and variance for
90% power at a 5% error rate. The critical-event set must contain at least 100
independent root injection events per reported fault family. Multiple corrupted
tensor elements caused by one root fault count as one event. If rarity or cost
prevents this count, the family is reported as underpowered rather than merged
with a different fault process.

## Held-Out Splits

No tensor element, time window, or microbenchmark output from one root injected
fault may cross splits. Evaluation withholds complete combinations of:

- model family and training phase;
- accelerator generation or hardware-unit manifestation family;
- CUDA operation and data type;
- parallelism topology and collective pattern;
- persistent versus transient corruption structure;
- fail-slow severity and workload-variability regime;
- mixed-fault ordering and burst structure;
- facility scale and checkpoint policy.

Clean seeds, fault seeds, checkpoints, and evaluation tasks are disjoint and
hashed before tuning. The primary evaluation suite is never used to train the
sensitivity estimator or choose canary locations. A revealed evaluation family
moves in full to calibration and requires a replacement held-out family.

## Falsifiers

The hypothesis is falsified if any condition below survives uncertainty
analysis:

- any primary quality interval escapes the equivalence margin, even when mean
  training loss appears normal;
- fewer than 95% of defended runs finish inside the per-run equivalence region;
- critical-event interception is below 99% or clean-step false action exceeds
  1%;
- clean-run or measured-incidence time-to-target or facility-energy overhead
  exceeds 2%;
- redundant FLOPs fall by less than 50% relative to uniform duplication at the
  same protection level;
- a NaN checker, fixed canary, ResiHP-like, ReCoVer-like, or rule-union baseline
  matches the joint policy within uncertainty on all primary outcomes;
- benefits exist only under independent random bit flips and disappear under
  structured, held-out manifestations;
- the sensitivity model cannot rank harmful interventions on held-out hardware,
  operations, or training phases;
- selective replay shifts failures into undetected optimizer-state or long-
  horizon capability damage;
- accelerated injection is the only regime supporting the 2% production-
  overhead claim.

## Validation Ladder

1. Reproduce the published conditional SDC manifestation statistics in the
   software injector, including special-value rarity, multi-bit structure, and
   spatial periodicity. This validates the injector, not training resilience.
2. Run exact paired kernel and tiny-model branches on one to eight GPUs to map
   injected events to short and long-horizon semantic damage.
3. Run repeated 32 to 64 GPU end-to-end training with held-out structured SDC,
   fail-stop, fail-slow, and mixed events.
4. Run 256 to 512 GPU comparisons against forward-recovery and workload-aware
   fail-slow baselines across two parallelism stacks.
5. Run canaries in shadow mode on a 1,000-plus accelerator fleet long enough to
   estimate false actions, out-of-distribution behavior, and production fault
   incidence without allowing the policy to alter training.
6. Conduct controlled 30B to 100B-plus runs at 10,000-plus accelerators with
   selective action enabled, independent held-out evaluation, and full facility
   accounting.

Stages 1 through 4 can reject the mechanism and transfer hypotheses. Stage 5 is
required before the production-incidence overhead threshold is meaningful.
Only stage 6 can support the frontier-training semantic-equivalence claim.

## First Engine Slice

Implement the smallest substrate that can falsify the virtual result:

- operation, tensor, collective, and optimizer-step lineage with commit state;
- paired clean and injected branches with deterministic replay provenance;
- distribution-aware structured SDC injection plus separately labeled fail-
  stop and fail-slow processes;
- trajectory-damage labels over 1, 10, 100, and 1,000-step horizons;
- a visible-state-only canary and selective-redundancy policy;
- interventions for verify, block, replay, isolate, reconfigure, repair,
  checkpoint restart, and abstain;
- quality-equivalence, interception, false-action, redundant-work, time-to-
  target, facility-energy, uncertainty, and regret reports;
- held-out residual attribution by fault manifestation, tensor role, training
  phase, topology, and policy action.

## Source Boundaries and Assumptions

- The Anatomy study uses gate-level single stuck-at injection on a production-
  class GPU model and 63 microbenchmarks. Its conditional patterns are the best
  recent grounding found for high-level SDC injection, but they are not fleet
  incidence, transient-fault frequency, or evidence of LLM trajectory damage.
- ReCoVer establishes a strong stochastic-equivalence invariant for forward
  recovery from detected device loss. Its published result does not answer
  silent faults whose output is accepted as valid.
- ResiHP establishes workload-aware fail-stop and persistent fail-slow
  detection and hybrid-parallel adaptation. Its paper explicitly excludes
  failures without liveness or timing signatures from the detector's scope.
- The 0.2-standard-deviation equivalence margin, 99% interception, 1% false-
  action, 2% overhead, and 50% redundancy thresholds are GPUSTACK predictions.
  They are not values reported by the cited papers.
- Model sizes, fault rates, quality tasks, raw numerical tolerances, and
  facility costs must be frozen from observations or labeled sensitivity
  assumptions. Virtual screening alone cannot establish production safety or
  final-model equivalence.
