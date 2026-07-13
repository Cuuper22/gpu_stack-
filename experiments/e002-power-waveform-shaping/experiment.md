# E002: Shape the Power Waveform

Status: E002-PW1 preserved as `measurement_invalid`; E002-PW2 completed with
valid local attribution; E002-PW3 is the active multi-GPU/rack slice

Protocol date: July 12, 2026

## Completed Causal Slice: E002-PW1

The first E002 build is the frozen
[checkpoint-power causal-attribution protocol](checkpoint-power-calibration-v1.md),
with machine-readable factors, bindings, invalidators, estimands, and result
requirements in
[checkpoint-power-scenario-v1.json](checkpoint-power-scenario-v1.json).

PW1 started from E001-LC3's sole failed gate instead of attempting the full
facility controller at once. It crossed sparse versus dense checkpoint cadence
with restart versus survivor continuation over LC3's exact warm state,
canonical-work frontier, two calibration blocks, and six held-out failure
blocks. Its primary interaction was intended to attribute GPU-board energy to
operation phases;
its preselected sparse-continuation arm must retain LC3's learning, attempted-
work, and opportunity-tick gains while passing the original `1.05` energy
ceiling. PW1 completed all 32 runs with exact warm-state binding, but its power
meter did not update fast enough for the frozen phase-attribution requirements.
The result is `measurement_invalid`, so it does not advance the broader
dependency-safe waveform-shaping hypothesis below.

The only active invalidators are
`insufficient_evaluation_power_updates` and
`insufficient_pooled_cadence_phase_updates`. Requested 20 ms polling produced
an effective 494.693 ms update period; the selected +250 ms lag sits on the
frozen boundary. The full failed measurement is preserved at
[results/checkpoint-power-v1.json](results/checkpoint-power-v1.json), artifact
`aff76946b26876820cdaa4ca43d0b6160cdc18b2f4c5bacd053cfe92f529d4f5`.

## Completed Measurement Slice: E002-PW2

The frozen protocol is
[checkpoint-energy-calibration-v2.md](checkpoint-energy-calibration-v2.md),
and its complete machine-readable engine contract is
[checkpoint-energy-scenario-v2.json](checkpoint-energy-scenario-v2.json).

PW2 keeps PW1's 2x2 checkpoint-cadence by survivor-continuation factorial,
LC3 warm binding, block order, failure schedules, estimands, and gates frozen.
It replaces only the inadmissible NVML instantaneous-power input with the
supported cumulative-energy counter. A direct three-second capability
observation at a requested 2 ms interval made 880 poll attempts, observed 40
counter changes, measured change gaps of 12.19 to 108.29 ms with median 88.44
ms, and accumulated 26,920 mJ. PW2 makes cumulative run energy and its additive
2 x 2 interaction primary. Checkpoint-snapshot and grouped checkpoint-related
claims retain explicit pooled-update floors; individual restore and rejoin
estimates remain exploratory unless independently supported. The raw PW1
ratios and failed mechanism gates are not priors to tune against. No mechanism
attribution or scale generalization was allowed before PW2 yielded admissible
measurements.

PW2 completed all 32 arms with exact warm binding and no measurement
invalidators. Its cumulative counter updated every 91.667 ms, with 83 to 109
updates in each held-out arm. The total, checkpoint-group, and snapshot
interactions were all positive under their paired 90% intervals; all three
mechanism gates and all eight sparse-continuation salvage gates passed. The
conclusion is `checkpoint_cadence_attributed_sparse_continuation_survives`.
The sensitivity-only idle-subtracted interaction was
`3.9825e-6 [-8.0109e-6, 1.2479e-5] J/token` and crossed zero, so the frozen
raw-cumulative primary passes but the attribution is not baseline-insensitive.
The result is [results/checkpoint-energy-v2.json](results/checkpoint-energy-v2.json),
artifact `cfbca215878629bc416f169e5ded80684151d9b2a621548c7fef08207c41f8ee`.

## Active Causal Slice: E002-PW3

PW3 moves the supported local mechanism to simultaneous multi-GPU and rack
observation. It must execute dependency-safe dephasing with aligned per-GPU
cumulative energy, rack-PDU power, storage activity and power, and cooling
telemetry. PW2 does not establish rack or facility transfer; PW3 must measure
those boundaries rather than project a laptop result upward.

The frozen physical protocol is
[checkpoint-rack-dephasing-v3.md](checkpoint-rack-dephasing-v3.md), with the
machine contract in
[checkpoint-rack-dephasing-scenario-v3.json](checkpoint-rack-dephasing-scenario-v3.json)
and deployable sensor binding in
[checkpoint-rack-telemetry-v3.example.json](checkpoint-rack-telemetry-v3.example.json).
It tests whether dependency-safe recovery slack can reduce both rack-PDU
`p99.9 |dP/dt|` and 0.1–10 Hz spectral energy by at least 30% versus
synchronized execution and 15% versus random legal jitter while preserving
throughput, rack energy, recovery time, semantics, durable cuts, rollback, and
held-out learning. No physical PW3 result exists yet.

## Question

Can a controller coordinate the phase of compute, collectives, checkpoint I/O,
and independent colocated training jobs so that a large AI datacenter stops
injecting dangerous periodic power into the grid, while preserving the
optimizer's learning semantics and time to a held-out loss target?

## Non-Minor Novelty Gap

This is not another power cap, job scheduler, waveform predictor, or battery
controller. It tests whether the training execution graph itself can become a
grid-facing control surface.

[EasyRider](https://arxiv.org/abs/2604.15522) shows that rack hardware and
auxiliary storage can attenuate millisecond-scale synchronized power swings
without changing training software. [The pre-dispatch resonance
criterion](https://arxiv.org/abs/2606.22096) shows that a bulk-synchronous
training period can coincide with a grid inter-area mode, and that changing a
single iteration period can move one modeled job out of a danger band.
[Power-Flexible AI Data Centers](https://arxiv.org/abs/2606.25098) demonstrates
rapid curtailment and geographic load shifting on a real 130 kW GPU cluster.
These are strong individual mechanisms, but they do not jointly optimize:

- the dependency graph and exact optimizer semantics of several training jobs;
- board, rack, facility, and point-of-common-coupling power at their different
  time scales;
- multiple grid modes and harmonics whose parameters change with dispatch;
- admission capacity, learning time, cooling, and storage wear under one
  accounting boundary;
- causal uncertainty about whether a proposed phase intervention will transfer
  to a held-out facility and workload.

The new claim is that dependency-safe phase control across those layers has a
capacity and grid-safety benefit that cannot be recovered by tuning any one
phase, cap, or buffer independently.

## Why Datacenter Scale Is Necessary

The effect under test is created by coherent switching across many
accelerators. A small GPU testbed can calibrate per-operation power and verify
that a schedule preserves the optimizer update, but it cannot establish the
facility or grid result. The [100 MW-scale cluster
study](https://arxiv.org/abs/2605.24461) reports measurements from 83,000 GB200
GPUs in a 150 MW facility, which makes facility power an observed scaling
constraint rather than a hypothetical one. The resonance study models a
100,000-H100 square-wave swing of 66.7 MW at the grid side under its stated
power-chain assumptions. That number is evidence for the scale of the problem,
not a GPUSTACK result or a universal facility value.

At scale, independent jobs create phase combinations, rack power paths impose
different limits, cooling adds slower state, and the point of common coupling
sees their aggregate. The claimed 10% admission-capacity gain therefore
requires multi-megawatt validation with real facility telemetry. Virtual and
rack-scale experiments may reject the hypothesis, but cannot confirm that
claim.

## Preregistered Hypothesis

A policy that changes only dependency-safe timing while jointly controlling
microbatch launches, gradient-bucket collectives, checkpoint I/O, and the
relative phase of independent jobs will satisfy all of the following on held-
out workload, facility, and grid-mode combinations:

1. Reduce grid-danger-band spectral energy at the point of common coupling by
   at least **50%** relative to the same unshaped workload replay over an equal
   useful-work horizon.
2. Increase time to the same held-out loss target by no more than **2%**
   relative to unshaped execution.
3. Admit at least **10%** more active accelerators under the identical point-of-
   common-coupling peak, ramp, modal-response, cooling, and protection limits
   than the best feasible one-dimensional software baseline.
4. Preserve the exact-semantics invariant for every committed optimizer step.

These numeric thresholds are predictions to test. They are not results. The
experiment passes only if all four survive their preregistered uncertainty
tests. A bounded-staleness exploratory arm may be reported separately, but it
cannot count as evidence for this hypothesis.

## Exact-Semantics Invariant

For every committed optimizer step, the shaped and unshaped paired runs must
use the same:

- multiset and order of training examples;
- parameter version for every gradient contribution;
- effective global batch, loss scaling, optimizer hyperparameters, and random
  number generator state;
- collective reduction result within a tolerance fixed from repeated
  deterministic clean runs before evaluation.

The controller may move an operation only within dependency slack, stagger
independent jobs, delay a checkpoint that is not on the recovery deadline, or
insert bounded idle time. It may not silently drop samples, commit stale
gradients, change arithmetic precision, or redefine an optimizer step. Any
invariant violation is a failed run, not a favorable power result.

## Accounting Boundary

Every comparison uses identical completed optimizer steps or identical held-
out loss progress and reports the full facility boundary:

- accelerator, host, network, storage, and power-conversion energy;
- cooling energy and thermal-limit violations;
- auxiliary storage charge, discharge, conversion loss, and equivalent cycles;
- checkpoint and replay work;
- point-of-common-coupling power, ramp rate, and modeled modal response.

Reducing spectral energy by doing less useful work, shifting it into an
unreported frequency, or consuming a hardware buffer without accounting for
loss and wear does not count as improvement.

## Virtual Datacenter State

The environment models one facility with one to eight concurrent training jobs.
It exposes the policy only to quantities available in a deployable controller.

### Training execution state

- per-job operation DAG with compute, gradient buckets, collectives,
  checkpoint writes, and explicit dependencies;
- current optimizer step, microbatch, sample-order commitment, and random state;
- measured duration and power distributions by operation, accelerator, and
  software version;
- parallelism topology, collective groups, stragglers, queue state, and
  dependency slack;
- checkpoint deadline and recoverability state;
- held-out loss-target surrogate with calibration provenance and uncertainty.

### Electrical and facility state

- board, node, rack, power-domain, and point-of-common-coupling power traces;
- power-chain efficiency, rack caps, facility cap, ramp limits, and protection
  thresholds;
- auxiliary storage state of charge, efficiency, power limit, and cycle model;
- inlet temperature, thermal headroom, cooling power, and response lag;
- grid modal frequencies, damping estimates, participation factors, operator
  thresholds, and their timestamped uncertainty;
- exogenous jobs and non-IT load that the policy can observe only when the real
  deployment could observe them.

Power is retained at the finest resolution supported by each observation. The
public H100 profiles in [Measurement of Generative AI Workload Power
Profiles](https://arxiv.org/abs/2604.07345) are sampled at 0.1 seconds and were
submitted April 8, 2026, five days outside the strict 90-day seed window. They
are a calibration anchor for slower waveform structure, not evidence for
millisecond ramp fidelity.

## Interventions

- shift the launch phase of independent jobs;
- move microbatch launches within measured dependency slack;
- reorder or delay independent gradient-bucket collectives without changing
  the committed reduction;
- stagger checkpoint serialization and storage traffic within recovery
  deadlines;
- insert bounded waits to move a job's iteration period out of a danger band;
- coordinate software phase shaping with an explicitly modeled rack buffer;
- reject or defer job admission when no semantics-preserving safe schedule
  exists.

The policy receives no future trace and no hidden simulator state. An oracle
with future job and grid traces is evaluated only as a regret lower bound.

## Baselines

1. Unshaped execution with the normal earliest-ready schedule.
2. Static phase offsets chosen once at job admission.
3. Per-job iteration-period detuning using the pre-dispatch resonance criterion.
4. Facility power cap or accelerator power cap without phase coordination.
5. Checkpoint staggering only.
6. Rack-level buffering following the EasyRider abstraction, with storage loss
   and wear included.
7. Greedy valley filling based only on current facility power.
8. An oracle joint schedule with future workload and grid traces, used only to
   measure decision regret.

The "best one-dimensional baseline" in prediction 3 is the feasible baseline
among 2 through 7 with the highest admitted accelerator count while satisfying
all constraints and the 2% time-to-target bound. It is selected on calibration
data and frozen before evaluation.

## Experimental Matrix

### Workloads

- dense and mixture-of-experts training graphs;
- compute-heavy, balanced, and communication-heavy measured duty cycles;
- modeled iteration periods spanning 1 to 10 seconds, the production-relevant
  range examined by the resonance source;
- one dominant job and mixes of 2, 4, and 8 independent jobs;
- stable and time-varying sequence-length distributions;
- checkpoint cadences ranging from infrequent large writes to frequent
  incremental writes.

### Facility and topology

- homogeneous and mixed accelerator power profiles;
- modeled populations of 10,000, 50,000, and 100,000 active accelerators;
- single and multiple rack power domains with asymmetric caps;
- no buffer, finite rack buffer, and buffer saturation or degradation;
- normal cooling headroom, hot ambient conditions, and one degraded cooling
  loop;
- clean execution and realistic timing jitter calibrated from observations.

These scale points and stressors are experimental factors, not claims that the
current engine is already calibrated at those scales.

### Grid state

- planning-study modes supplied by a grid collaborator;
- a synthetic sensitivity grid over 0.1 to 0.7 Hz and damping ratios 0.03,
  0.05, and 0.10, explicitly labeled as modeled sensitivity cases;
- fixed modes, slow modal drift, and a dispatch change during a run;
- fundamental-only and harmonic-extended screening;
- normal, tight, and temporarily curtailed facility envelopes.

## Primary Outcomes

1. **Danger-band spectral energy.** For each timestamped grid mode, integrate
   point-of-common-coupling power spectral density over its preregistered danger
   band and significant square-wave harmonics. Report both absolute energy and
   energy per completed optimizer step.
2. **Grid response.** Maximum modeled frequency deviation, tie-line oscillation,
   time above the operator threshold, and worst-case value over modal-parameter
   uncertainty.
3. **Learning time.** Wall-clock time and facility joules to the same held-out
   loss target, with failed or invariant-violating runs included.
4. **Admission capacity.** Maximum active accelerators for which all facility,
   grid, cooling, semantics, and learning-time constraints hold.
5. **Decision quality.** Policy regret against the oracle and empirical coverage
   of predicted waveform and outcome intervals.

Before a virtual policy result is admissible, its held-out waveform model must
achieve no more than 10% normalized root-mean-square error at the point of
common coupling, and nominal 90% prediction intervals must cover between 85%
and 95% of held-out samples. These are result-admission gates, not claims that
the current engine meets them.

## Secondary Outcomes

- peak and 95th-percentile ramp rate at board, rack, and facility boundaries;
- total facility energy, peak power, power-factor or reactive-power quantities
  when measured, and cooling energy;
- useful accelerator utilization and collective tail latency;
- checkpoint deadline misses and expected lost work at failure;
- storage throughput, conversion loss, state-of-charge saturation, and cycles;
- intervention count, phase churn, policy compute cost, and abstention rate;
- residual attribution to workload, timing, power-chain, cooling, or grid model.

## Paired Design and Analysis

Each shaped run is paired with every baseline on the same workload graph,
sample order, random seed, exogenous trace, initial thermal state, and grid
snapshot. Evaluation reports run-level paired effects and cluster-level
bootstrap intervals. The primary family is tested in the order listed above;
the hypothesis passes only when the lower 95% confidence bound clears the 50%
and 10% improvement thresholds and the upper 95% bound remains below 2%
time-to-target regression.

The number of independent evaluation runs per cell is chosen from calibration-
only variance to provide 90% power at a two-sided 5% error rate for the 50%
spectral-energy effect and the 2% time noninferiority margin, with a minimum of
10 independent workload traces per reported cell. If the required run count is
unaffordable, the cell is reported as underpowered rather than pooled post hoc.

## Held-Out Splits

Splits occur at complete run or trace level, never by slicing adjacent windows
from one trace. Evaluation withholds all of the following:

- at least one model or workload family;
- one accelerator power-profile family;
- one collective topology class;
- one facility scale and one rack-cap arrangement;
- complete grid-mode and damping combinations;
- one cooling or buffer stress regime;
- unseen combinations of colocated job phases.

Grid modal parameters needed by a deployable policy may be visible at decision
time even when that mode class was withheld from model fitting. Evaluation jobs,
traces, seeds, and mode snapshots are hashed and frozen before policy tuning.
Any tuning on an evaluation artifact moves the entire artifact family into
calibration and requires a new held-out set.

## Falsifiers

The hypothesis is falsified if any condition below survives uncertainty
analysis:

- danger-band spectral energy falls by less than 50%;
- time to the held-out loss target regresses by more than 2%;
- admission capacity improves by less than 10% over the best one-dimensional
  baseline;
- any committed optimizer step violates the exact-semantics invariant;
- iteration-period detuning, a static offset, or rack buffering alone matches
  joint control within experimental uncertainty on all primary outcomes;
- apparent improvement moves energy into another dangerous mode or harmonic;
- cooling energy, storage loss or wear, recovery risk, or total facility energy
  reverses the claimed benefit;
- the counterfactual ranking or uncertainty interval fails its held-out
  admission gate;
- the effect disappears on real traces or changes sign in a withheld facility
  regime.

## Validation Ladder

1. Replay the public 0.1-second H100 traces and any released EasyRider traces;
   validate accounting and reject models that cannot reproduce held-out power.
2. Instrument 8 to 64 GPUs at high rate; verify operation-level power,
   dependency-safe timing, and bitwise or tolerance-bounded optimizer equality.
3. Run paired shaping experiments on 256 to 1,024 GPUs across multiple racks,
   jobs, collectives, and checkpoint streams.
4. Run shadow-mode prediction, with no control authority, at a facility with at
   least 10,000 active accelerators and timestamped point-of-common-coupling
   telemetry.
5. Conduct an operator-approved multi-megawatt A/B intervention while remaining
   outside protection thresholds.
6. Repeat at 10,000-plus accelerators across a held-out facility, workload, and
   grid operating regime.

Stages 1 through 3 can falsify mechanism and semantics claims. Stage 4 can
validate transfer. Only stages 5 and 6 can support the admission-capacity and
grid-response claims.

## First Engine Slice

Implement the smallest substrate that can invalidate the virtual result:

- a measured event DAG for compute, collectives, checkpoint I/O, and dependency
  slack;
- hierarchical board-to-rack-to-facility power aggregation with timestamped
  observation uncertainty;
- point-of-common-coupling resampling, spectral decomposition, modal danger
  bands, and harmonic accounting;
- an exact-semantics guard that rejects illegal timing interventions;
- a visible-state-only phase policy and oracle regret evaluator;
- paired counterfactual replay with facility, cooling, and storage accounting;
- held-out waveform residuals, interval coverage, and causal attribution in the
  experiment artifact.

## Source Boundaries and Assumptions

- EasyRider establishes hardware attenuation on a 400 VDC-rated prototype and
  traces, not optimizer-aware software phase control at hyperscale.
- The resonance paper derives a conservative two-area, fixed-operating-point
  screen and explicitly leaves multiple close modes, drifting duty cycles, and
  coupled facility loads as validity limits. GPUSTACK must not present its case
  study values as universal grid limits.
- The 130 kW power-flexibility deployment establishes that real GPU control can
  respond to grid conditions. It does not establish hyperscale resonance
  mitigation.
- The public 0.1-second profiles are five days outside the strict 90-day window
  and cannot calibrate millisecond ramps without additional measurements.
- All loss targets, modal thresholds, buffer properties, and facility limits
  must come from timestamped observations or be labeled synthetic sensitivity
  assumptions. No result may be promoted from virtual screening alone.
