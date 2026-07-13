# E002-PW1: Checkpoint-Power Causal Attribution

Status: executed; measurement invalid, result preserved

Protocol date: July 12, 2026

Machine-readable scenario: [checkpoint-power-scenario-v1.json](checkpoint-power-scenario-v1.json)

Persisted result: [results/checkpoint-power-v1.json](results/checkpoint-power-v1.json)

## Research Question

Is E001-LC3's measured survivor-continuation energy failure caused by survivor
continuation itself, or by the denser checkpoint schedule used to make survivor
progress durable?

PW1 is a mechanism-identification experiment, not a general power optimizer.
It crosses checkpoint cadence with failure behavior while holding the LC3 warm
state, learning workload, failure schedules, and exact canonical-work frontier
fixed. The experiment either identifies a checkpoint-related energy interaction
and tests one preselected salvage policy, or rejects that explanation before any
datacenter-scale controller is built.

## Why This Experiment Is New

The recent primary literature isolates important pieces but not this causal
question:

- [EasyRider: Mitigating Power Transients in Datacenter-Scale Training
  Workloads](https://arxiv.org/abs/2604.15522), submitted April 16, 2026,
  identifies synchronized compute, collective, checkpoint, and restart phases
  as power-transient sources. It mitigates them with rack hardware and optional
  GPU burn compensation; it does not cross recovery semantics with checkpoint
  cadence under an equal-learning-work outcome.
- [Cross-Layer Energy Analysis of Multimodal Training on Grace Hopper
  Superchips](https://arxiv.org/abs/2605.01938), submitted May 3, 2026, finds
  that data movement and overlap can govern training energy even when raw
  compute utilization looks favorable. It motivates separating snapshot,
  restore, merge, and rejoin phases from compute.
- [CompPow: A Case for Component-level GPU Power
  Management](https://arxiv.org/abs/2605.21847), submitted May 21, 2026, uses
  the FinGraV method to repeat operations and align CPU and GPU time under
  logger averaging. PW1 therefore pools repeated phase instances and never
  infers a causal effect from one checkpoint spike.
- [Battery-Assisted Operation of Hyperscale AI Data Centers under
  Connect-and-Manage Interconnection
  Practices](https://arxiv.org/abs/2605.14105), submitted May 13, 2026, joins
  checkpoint-constrained training, cooling, and point-of-connection limits in
  an optimization study. It does not supply observed recovery-learning phase
  kernels.
- [The Energy Blind Spot: NVIDIA's Flagship Edge AI Hardware Cannot Support
  Process-Level Energy Attribution](https://arxiv.org/abs/2605.27599),
  submitted May 26, 2026, establishes that instantaneous NVML GPU power is not
  host, process, or facility energy. PW1 therefore limits its measured claim to
  one isolated GPU process and the GPU board boundary.
- [Contextual Robust Optimization for AI Data Center Scheduling with
  Statistical Guarantees](https://arxiv.org/abs/2606.17466), submitted June
  16, 2026, provides finite-sample scheduling guarantees under workload and
  renewable uncertainty. Its aggregate GPU-hour power model does not represent
  failure and recovery phases.
- [Power-Flexible AI Data Centers: A New Paradigm for Grid-Responsive
  Compute](https://arxiv.org/abs/2606.25098), submitted June 23, 2026,
  demonstrates grid response on a real 130 kW, 96-GPU deployment. Its
  one-second GPU and 20-second/minute rack telemetry is a facility-control
  precedent, not checkpoint-phase attribution.
- [PHOENIX: Resilient LLM Training with Hot-Swapping via Zero-Overhead
  Checkpoint](https://arxiv.org/abs/2607.01646), submitted July 2, 2026,
  overlaps in-memory optimizer-state checkpoints and hot-swaps failures at up
  to 512 GPUs. It reports recovery latency, not phase energy or facility power.
- [Direct Model State Migration for Elastic Training of Large Language
  Models](https://arxiv.org/abs/2607.04749), submitted July 6, 2026, replaces
  checkpoint-storage-reload migration with direct GPU-to-GPU state movement.
  It reports migration speed, not the learning-energy-facility interaction.

The gap PW1 tests is the intersection: equal canonical learning work, failure
recovery semantics, checkpoint cadence, operation-aligned device power, and an
explicit boundary between the observed GPU trace and a later facility model.

## Immutable E001-LC3 Binding

PW1 is conditioned on the executed LC3 artifact rather than a reconstructed
approximation:

- LC3 result: `../e001-beyond-one-datacenter/results/equal-work-v1.json`,
  SHA-256 `f7548b68d4791978260f0bd557bf92041d0f769b796b1e684bbcab99e88f639f`;
- LC3 scenario: `../e001-beyond-one-datacenter/equal-work-scenario-v1.json`,
  SHA-256 `f5212c19e701f183c7ab9aaf7620bf43c03a234eee92dd7e9d98c73c5c22a9ed`;
- LC3 engine bundle:
  `b574609b19eeca593dc932ec09943a779b50a28b4d9e336afa07b5a18fa52249`;
- rebuilt warm checkpoint: tick `8192`, seed `7`, state SHA-256
  `fd7c6d7ed521087300611b059d77c7019b9293ee196a31cf6939c29de2036cd5`;
- TinyStories shard SHA-256
  `77cf780cebe52b6e83e3a2ac84bc56d8059363113e41d17a023f1d8b2ed0fc0b`;
- approximately 2M-parameter byte decoder, AdamW, BF16, batch `4` per site,
  context `256`, and the fixed 64-batch validation suite;
- exact useful-work frontier: `256` logical ticks, two `1,024`-token site
  quotas per tick, or `524,288` canonical tokens;
- hard censoring frontier: `384` opportunity ticks.

The warm checkpoint must be rebuilt once and its state hash must match before
any PW1 arm executes. A mismatch invalidates the protocol; the engine may not
silently substitute a new warm state.

## Frozen 2 x 2 Design

The checkpoint-cadence factor changes only the number of eligible merge events
between snapshots:

- **Sparse cadence:** snapshot every second eligible merge. With the frozen
  LC3 merge rules, this is every 16 healthy logical ticks and every 4
  reduced-membership logical ticks.
- **Dense cadence:** snapshot every eligible merge. This is every 8 healthy
  logical ticks and every 2 reduced-membership logical ticks.

Every arm takes the same initial checkpoint. Healthy state becomes merge-
eligible every 8 logical ticks. Under continuation, reduced-membership state
becomes merge-eligible every 2 logical ticks. Restart does no work and creates
no reduced-membership merge while a failure is active; this is a consequence
of the treatment definition, not a missing factorial cell.

The survivor-continuation factor has two levels:

- **Restart:** restore both site states from the last checkpoint at failure,
  remain inactive during the visible outage, then replay the deterministic
  logical quotas after service resumes.
- **Continue:** execute both logical site quotas sequentially on the survivor,
  checkpoint canonical reduced-membership state at its assigned cadence, copy
  the canonical model and Adam state to the rejoined site, then execute the
  frozen two post-rejoin synchronization ticks.

| Arm | Cadence | Failure behavior | Role |
|---|---|---|---|
| `A-sparse-restart` | sparse | restart | LC3 fixed-local anchor |
| `B-dense-restart` | dense | restart | missing cadence counterfactual |
| `C-sparse-continue` | sparse | continue | preselected salvage candidate |
| `D-dense-continue` | dense | continue | LC3 adaptive anchor |

No arm changes data identity, optimizer state content, arithmetic precision,
model structure, failure visibility, or the canonical-work endpoint.

## Run Matrix

PW1 reuses the complete LC3 split:

- no-failure calibration blocks `C1` and `C2` with seeds `11` and `29`;
- held-out failure blocks `E1` through `E6`, with their original seeds and
  opportunity-tick failure intervals unchanged.

All four arms run in all eight blocks: `8 blocks x 4 arms = 32 GPU runs`.
Only `E1` through `E6` contribute to the primary causal interval. `C1` and
`C2` are negative controls for continuation semantics and are the only blocks
used to estimate the power logger's fixed delay and effective update period.

The four Williams orders are frozen and each is used twice:

1. `A, B, D, C`;
2. `B, C, A, D`;
3. `C, D, B, A`;
4. `D, A, C, B`.

The scenario binds one order to every block. Arm ordering cannot be changed in
response to temperature, runtime, or interim energy values. A run begins only
after the thermal start condition is satisfied; validation and cooldown remain
outside the energy window.

## Operation-Aligned Instrumentation

Each arm records one continuous host-monotonic trace at a requested 20 ms
polling interval. Every sample contains:

- monotonic nanoseconds;
- NVML GPU-board power;
- GPU and memory utilization;
- SM and memory clocks;
- GPU temperature;
- performance state.

The engine records exclusive, exhaustive phase intervals with these identifiers:

1. `canonical-healthy-compute`;
2. `replay-compute`;
3. `survivor-redistributed-compute`;
4. `model-optimizer-merge`;
5. `checkpoint-snapshot`;
6. `checkpoint-restore`;
7. `rejoin-state-transfer`;
8. `post-rejoin-sync`;
9. `runtime-control-remainder`.

CUDA work is complete at a phase boundary before the next phase opens. Trace
intervals are allocated by fractional overlap with phase windows, not by the
nearest sample. Two-second idle plateaus bracket the measured run. The idle
baseline is linearly interpolated between their medians. Negative residual
phase energy is retained; clamping would destroy additive closure.

The calibration blocks estimate one logger delay and one effective update
period. Those values are frozen before evaluation. Waveform derivatives and
spectra are computed at the observed effective update period, never at a
synthetic 20 ms resolution that the device did not deliver.

## Measurement Validity Contract

A PW1 result is `measurement_invalid`, not a negative candidate result, if any
of these conditions occurs:

- the warm checkpoint, dataset, source scenario, or canonical-work identity
  does not match the binding above;
- any phase intervals overlap, leave an internal gap longer than 1 ms, or fail
  to span the measured run window;
- summed phase energy differs from the integrated run energy by more than
  `0.5%`;
- an evaluation arm contains fewer than 40 effective power updates;
- a cadence-by-phase pool contains fewer than 30 effective updates for a phase
  used in the causal attribution;
- the logger delay inferred from calibration lies outside `-250` to `250` ms;
- either no-failure continuation arm differs from its same-cadence restart arm
  in canonical state, attempted work, or final held-out NLL;
- the GPU power configuration changes within a paired block;
- any required raw trace, phase interval, or result field is missing.

The engine must preserve the invalid result and the reason. It may not impute
missing device power, borrow a phase signature from another arm, or promote a
facility model to replace a failed local measurement.

## Causal Estimands

For held-out block `b`, cadence `c`, continuation level `s`, and phase `p`, let

`Y[b,c,s,p] = idle-subtracted phase joules / canonical tokens`.

The primary phase interaction is

`I[b,p] = (Y[b,dense,continue,p] - Y[b,sparse,continue,p])`

`         - (Y[b,dense,restart,p] - Y[b,sparse,restart,p])`.

The total interaction is additive:

`I[b,total] = sum_p I[b,p]`.

Report all six held-out block effects, their median, and the frozen paired 90%
percentile-bootstrap interval using 10,000 draws and seed `20260714`. Also
report the log ratio-of-ratios as a scale-free sensitivity quantity; it cannot
replace the additive primary estimand because only the additive form closes
over phases.

Checkpoint-related attribution is the sum of
`checkpoint-snapshot`, `model-optimizer-merge`, `checkpoint-restore`,
`rejoin-state-transfer`, and `post-rejoin-sync` interactions.

The preselected salvage comparison is
`C-sparse-continue` versus `A-sparse-restart`. The observed LC3-corner
comparison, `D-dense-continue` versus `A-sparse-restart`, is reported to show
whether the original energy direction reproduces under the improved meter.

## Frozen Hypotheses and Falsifiers

The checkpoint-cadence explanation survives only if all are true:

1. the lower bound of the paired 90% total interaction is above zero;
2. the lower bound of the checkpoint-related interaction is above zero;
3. changing dense continuation to sparse continuation removes at least 50% of
   the median excess energy of dense continuation over sparse restart.

Sparse continuation survives as an E001 mechanism only if all LC3 learning and
work gates also survive:

1. all six sparse restart/continue pairs reach 256 canonical ticks by
   opportunity tick 384;
2. the upper bound of sparse-continuation minus sparse-restart final NLL is at
   most `0.01`;
3. attempted-FLOP saving has a lower bound above zero and median at least `3%`;
4. median opportunity-tick saving is at least `24`, and continuation is earlier
   in all six blocks;
5. the upper bound of the paired sparse-continuation/sparse-restart measured
   GPU-energy ratio is at most `1.05`;
6. neither continuation arm diverges;
7. checkpoint cadence is learning-semantic: sparse and dense endpoints within
   a continuation level remain inside the frozen `0.01` NLL margin.

Failure of any salvage gate preserves the candidate conclusion as falsified.
No threshold may be relaxed after evaluation.

## Result Decision

- If the dense-continuation LC3 corner no longer has an energy penalty under
  PW1's valid meter, record `lc3_energy_penalty_not_reproduced`; do not claim
  checkpoint causality.
- If the penalty reproduces, both interaction gates pass, and sparse
  continuation passes every salvage gate, record
  `checkpoint_cadence_attributed_sparse_continuation_survives`.
- If the penalty reproduces but the interaction fails, record
  `continuation_energy_not_attributed_to_checkpoint_cadence`.
- If cadence is attributed but sparse continuation still fails the energy
  ceiling, record `checkpoint_cadence_partial_cause_candidate_still_fails` and
  move to off-critical-path in-memory checkpointing or direct state migration.
- Any measurement invalidator takes precedence over those scientific
  conclusions.

## Local Measurement and Facility Bridge

PW1 observes only:

- the isolated RTX GPU-board waveform;
- phase duration and ordering;
- model/optimizer snapshot and state-transfer bytes;
- attempted, replayed, discarded, redistributed, and canonical work;
- final held-out learning evidence.

It does not observe host, DRAM, NIC, storage-service, cooling, power-delivery,
or point-of-common-coupling energy. The simulated outage opportunity ticks are
not physical idle seconds on the laptop.

A later bridge may replay PW1's phase kernels over the recovery event DAG:

`P_GPU,g(t) = P_idle,g + alpha_phase(t) * (P_train,g - P_idle,g)`

`P_IT(t) = sum_g P_GPU,g(t) + P_CPU(t) + P_NIC(t) + P_storage(t)`.

The IT trace must then pass through separately calibrated electrical and
cooling response models before it is called facility or point-of-connection
power. Static PUE multiplication is not a waveform model. Checkpoint and state
bytes drive the host, network, and storage terms; those terms may not be
inferred from GPU energy.

The bridge reports modeled total energy, maximum ramp rate, 0.1-10 Hz spectral
power, checkpoint/rejoin coincidence, curtailment headroom, useful work, and
target-quality time. Every such value remains labeled `modeled` until a future
run supplies simultaneous per-GPU, rack-PDU, cooling, and facility-meter data.

## Engine Consumption Contract

The engine consumes the following scenario objects without hidden defaults:

- `source_bindings` and `warm_start_binding`;
- `dataset`, `model`, `optimization`, `canonical_work`, and `thermal_guard`;
- `factors`, `arms`, `splits`, and `execution_order`;
- `telemetry`, `phase_markers`, and `measurement_invalidators`;
- `estimands`, `mechanism_falsifiers`, and `salvage_falsifiers`;
- `decision_rules` and `facility_bridge`.

The required result payload is enumerated in
`required_result_fields` in the JSON scenario. A result that omits a raw trace
hash, phase ledger, all four factorial cells, six block interactions, salvage
gates, or the observed/modeled boundary is incomplete rather than favorable.

## Frontier Question Selected by a Positive PW1

Only a positive PW1 justifies asking the datacenter-scale question:

> Can dependency-safe dephasing of checkpoint, collective, survivor-compute,
> and rejoin operations across 10,000-100,000 GPUs prevent failures from
> producing coherent megawatt-scale power shocks, without burn loads,
> spare-compute redundancy, optimizer-state divergence, or loss of liveput?

That question requires a real cluster because phase correlation, interconnect
contention, cooling response, correlated rack failures, and point-of-connection
ramp rates do not exist on one serial laptop GPU.

## Executed Result

PW1 completed all `32/32` GPU runs and exactly reproduced the frozen LC3 warm
checkpoint (`fd7c6d7ed521087300611b059d77c7019b9293ee196a31cf6939c29de2036cd5`).
The persisted result is nevertheless `measurement_invalid`.

The logger requested 20 ms polling, but the device supplied effective power
updates every `494.693` ms. Calibration selected a `+250` ms logger lag, exactly
at the frozen admissibility boundary. Every invalidator except these two is
false:

- `insufficient_evaluation_power_updates`;
- `insufficient_pooled_cadence_phase_updates`.

Because those invalidators fire, no phase-energy interaction, penalty-
reproduction result, or salvage energy ratio is admissible evidence. The raw
LC3-corner ratio was median `0.789` with paired 90% interval `[0.703, 0.923]`,
so the prior penalty did not reproduce numerically. The raw sparse-
continuation salvage ratio was median `0.823` with interval `[0.665, 1.019]`,
and all of its non-energy gates passed. Both observations remain visible for
diagnosis but cannot support a mechanism or candidate claim. All three frozen
mechanism gates failed.

Artifact SHA-256:
`aff76946b26876820cdaa4ca43d0b6160cdc18b2f4c5bacd053cfe92f529d4f5`.

## Resolution In E002-PW2

PW2 executed the same frozen factorial and exact source bindings on the
supported cumulative-energy counter. All 32 runs completed, exact warm binding
held, and no measurement invalidator fired. All three mechanism and all eight
salvage gates passed, producing
`checkpoint_cadence_attributed_sparse_continuation_survives` in
[results/checkpoint-energy-v2.json](results/checkpoint-energy-v2.json), artifact
`cfbca215878629bc416f169e5ded80684151d9b2a621548c7fef08207c41f8ee`.

PW1 remains the preserved failed measurement and is not retroactively repaired
by PW2. PW3 now tests the valid local mechanism under simultaneous multi-GPU
and rack observation; facility transfer remains unproven.
