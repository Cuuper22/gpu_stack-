# E002-PW2: Cumulative Checkpoint-Energy Attribution

Status: executed; valid attribution and salvage result preserved

Protocol date: July 12, 2026

Machine-readable scenario: [checkpoint-energy-scenario-v2.json](checkpoint-energy-scenario-v2.json)

Persisted result: [results/checkpoint-energy-v2.json](results/checkpoint-energy-v2.json)

## Research Question

Using the GPU's cumulative millijoule counter, is E001-LC3's survivor-
continuation energy failure caused by the denser checkpoint cadence, and does
the preselected sparse-continuation policy preserve LC3's learning, work, and
opportunity-tick gains while passing the unchanged `1.05` device-energy gate?

PW2 repeats the frozen 2 x 2 causal experiment with a meter that the local GPU
actually supports. It does not revise the learning mechanism, factor levels,
run matrix, arm order, canonical-work frontier, confidence level, or any PW1
falsifier.

## Why PW2 Exists

[E002-PW1](checkpoint-power-calibration-v1.md) executed all 32 prescribed arms
and persisted result
`results/checkpoint-power-v1.json`, SHA-256
`aff76946b26876820cdaa4ca43d0b6160cdc18b2f4c5bacd053cfe92f529d4f5`.
Its conclusion is `measurement_invalid`.

PW1's state, work, phase partition, energy closure, thermal, and source-binding
checks passed. Its instantaneous-power trace did not support the intended
phase claim: the inferred effective update period was about `494.693 ms`, and
both the per-evaluation-arm and pooled cadence-phase update requirements
failed. Therefore:

- PW1's reported energy ratios, factorial interactions, phase energies, and
  apparent salvage result are not research evidence;
- none of those quantities may seed a PW2 threshold, prior, or expected sign;
- the PW1 artifact remains a recovery-backed measurement failure, not a
  negative checkpoint-causality result;
- PW2 does not lower PW1's update-count, learning, work, timing, energy, or
  causal-attribution thresholds.

This correction is supported by the measurement concern in
[CompPow](https://arxiv.org/abs/2605.21847), whose FinGraV method treats logger
averaging and CPU/GPU time alignment as first-order validity problems, and by
[The Energy Blind Spot](https://arxiv.org/abs/2605.27599), which distinguishes
instantaneous NVML power from cumulative or facility energy. The larger
research motivation remains the checkpoint and synchronization transients
identified by [EasyRider](https://arxiv.org/abs/2604.15522), the off-critical-
path recovery mechanism in [PHOENIX](https://arxiv.org/abs/2607.01646), and
direct state migration in [ETC](https://arxiv.org/abs/2607.04749).

## Observed Local Meter Capability

Before this protocol was frozen, a direct capability measurement called
`nvmlDeviceGetTotalEnergyConsumption` for 3 seconds with a requested 2 ms poll
interval on the local NVIDIA GeForce RTX 3060 Laptop GPU:

| Capability observation | Value |
|---|---:|
| Poll attempts | 880 |
| Cumulative-counter changes | 40 |
| Median change gap | 88.44 ms |
| Minimum change gap | 12.19 ms |
| Maximum change gap | 108.29 ms |
| Cumulative delta | 26,920 mJ |

This observation establishes availability and a plausible update scale. It is
not a PW2 arm, an energy baseline, or evidence for either causal hypothesis.
PW2 measures and reports the effective counter behavior again within its own
calibration blocks, without changing the frozen support thresholds.

## Immutable Research Binding

PW2 binds all scientific factors to PW1 and LC3:

- PW1 result artifact SHA-256
  `aff76946b26876820cdaa4ca43d0b6160cdc18b2f4c5bacd053cfe92f529d4f5`,
  conclusion `measurement_invalid`;
- PW1 scenario SHA-256
  `c368180070d4e257326be7649b6f593d20d89d768b2cf57d49fdb9672b6c2d93`;
- LC3 result artifact SHA-256
  `f7548b68d4791978260f0bd557bf92041d0f769b796b1e684bbcab99e88f639f`;
- LC3 warm checkpoint at tick `8192`, seed `7`, state SHA-256
  `fd7c6d7ed521087300611b059d77c7019b9293ee196a31cf6939c29de2036cd5`;
- TinyStories shard SHA-256
  `77cf780cebe52b6e83e3a2ac84bc56d8059363113e41d17a023f1d8b2ed0fc0b`;
- the same 1,871,232-parameter byte decoder, AdamW state, BF16 arithmetic,
  validation suite, data identities, and logical quota ordering;
- exact work frontier: 256 logical ticks, 524,288 canonical tokens;
- hard censoring frontier: 384 opportunity ticks.

The warm checkpoint is rebuilt once before the matrix and must reproduce its
state hash. PW2 cannot import PW1's endpoint energy estimates or reinterpret
PW1's instantaneous-power integration as cumulative-counter evidence.

## Frozen Factors and Arms

Checkpoint cadence remains:

- **sparse:** snapshot every second eligible merge, equivalent to every 16
  healthy logical ticks and every 4 reduced-membership logical ticks;
- **dense:** snapshot every eligible merge, every 8 healthy ticks and every 2
  reduced-membership ticks.

Failure behavior remains:

- **restart:** restore both site states, perform no training during the visible
  outage, and replay deterministic quota identities after service resumes;
- **continue:** execute both logical quotas sequentially on the survivor,
  checkpoint reduced-membership state at the assigned cadence, copy canonical
  model and Adam state on rejoin, then perform two synchronization ticks.

| Arm | Cadence | Failure behavior | Role |
|---|---|---|---|
| `A-sparse-restart` | sparse | restart | fixed-local anchor |
| `B-dense-restart` | dense | restart | cadence counterfactual |
| `C-sparse-continue` | sparse | continue | preselected salvage candidate |
| `D-dense-continue` | dense | continue | LC3 adaptive anchor |

## Frozen Matrix and Order

All four arms run in the unchanged two calibration and six evaluation blocks:

- `C1`: seed 11, no failure;
- `C2`: seed 29, no failure;
- `E1`: seed 101, failures `[[40,8],[136,16]]`;
- `E2`: seed 131, failures `[[64,16],[200,8]]`;
- `E3`: seed 151, failures `[[72,8],[128,24]]`;
- `E4`: seed 181, failures `[[104,16],[184,16]]`;
- `E5`: seed 211, failures `[[32,8],[104,8],[216,16]]`;
- `E6`: seed 241, failures `[[88,24],[168,8]]`.

The total remains 32 GPU runs. The exact PW1 Williams orders and assignments
remain frozen:

- `W1 = [A,B,D,C]` for `C1` and `E3`;
- `W2 = [B,C,A,D]` for `C2` and `E4`;
- `W3 = [C,D,B,A]` for `E1` and `E5`;
- `W4 = [D,A,C,B]` for `E2` and `E6`.

No interim cumulative-energy value may change arm order, thermal policy, or
the decision to finish a block.

## Cumulative-Energy Meter

The primary device measurement is NVIDIA NVML's cumulative total-energy
counter in millijoules. Each arm requests polling every 2 ms and records:

- host monotonic nanoseconds;
- cumulative GPU-board energy in millijoules;
- an effective-update flag when the counter changes;
- instantaneous board power as ancillary diagnostics only;
- utilization, clocks, temperature, and performance state.

An effective update is one strictly positive cumulative-counter change. Counter
decreases, resets, wrap without a documented correction, missing boundary
samples, or a non-positive run delta invalidate the affected block.

Two-second pre-run and post-run idle plateaus bracket the measured execution.
Counter increments are formed from adjacent changed values. Each increment is
allocated fractionally over its bracketing time interval, first to the exact
run window and then to the exclusive phase intervals it overlaps. This makes
the raw run total and grouped phase totals additive without converting
instantaneous watts into the primary energy estimate.

The primary arm outcome is total cumulative GPU-board energy allocated to the
complete training/recovery run window. A separately reported idle-subtracted
sensitivity uses the linearly interpolated pre/post idle rate, but it cannot
replace the cumulative raw total in the primary interaction or energy gate.

## Phase Ledger and Support Boundary

PW2 retains PW1's exclusive phase identifiers:

1. `canonical-healthy-compute`;
2. `replay-compute`;
3. `survivor-redistributed-compute`;
4. `model-optimizer-merge`;
5. `checkpoint-snapshot`;
6. `checkpoint-restore`;
7. `rejoin-state-transfer`;
8. `post-rejoin-sync`;
9. `runtime-control-remainder`.

The checkpoint-related group is the union of
`checkpoint-snapshot`, `model-optimizer-merge`, `checkpoint-restore`,
`rejoin-state-transfer`, and `post-rejoin-sync`.

The following support floors are frozen:

- at least **40 effective cumulative-counter updates in every held-out arm**;
- at least **30 pooled counter updates per cadence** overlapping
  `checkpoint-snapshot` across the held-out blocks;
- at least **30 pooled counter updates per cadence** overlapping the complete
  checkpoint-related group.

The checkpoint-snapshot and grouped checkpoint-related estimates may support
causal attribution only when both cadence pools pass those floors. Individual
`checkpoint-restore`, `rejoin-state-transfer`, `post-rejoin-sync`, and merge
estimates are explicitly exploratory unless that individual phase independently
has at least 30 pooled updates in each cadence. Failure of an individual-phase
floor does not invalidate the run-level total or the supported grouped result;
it forbids an individual-phase causal claim.

No phase energy from PW1 is imported, smoothed, or combined with PW2.

## Primary Estimand

For held-out block `b`, cadence `c`, and continuation level `s`, let

`E[b,c,s] = cumulative GPU-board joules allocated to the complete run window`.

All arms reach the same 524,288-token canonical frontier, so the normalized
outcome is

`Y[b,c,s] = E[b,c,s] / 524288`.

The primary additive 2 x 2 interaction is

`I[b] = (Y[b,dense,continue] - Y[b,sparse,continue])`

`       - (Y[b,dense,restart] - Y[b,sparse,restart])`.

Report all six block interactions, the median, and a paired 90% percentile-
bootstrap interval using 10,000 draws and seed `20260714`. The log ratio-of-
ratios remains a scale-free sensitivity result only.

The supported checkpoint-snapshot and checkpoint-related group repeat the same
additive contrast on their pooled cumulative-counter allocations. They do not
replace the run-level primary interaction.

The preselected salvage comparison remains
`C-sparse-continue` versus `A-sparse-restart`. The LC3-corner reproduction
comparison remains `D-dense-continue` versus `A-sparse-restart`.

## Measurement Invalidators

PW2 concludes `measurement_invalid` before any scientific decision if:

- any PW1, LC3, warm-state, dataset, model, factor, split, order, or canonical-
  work binding differs;
- `nvmlDeviceGetTotalEnergyConsumption` is unavailable;
- the cumulative counter decreases, resets, cannot bracket the run, or has a
  non-positive run delta;
- any of the 24 held-out arms has fewer than 40 effective counter updates;
- either cadence has fewer than 30 pooled checkpoint-snapshot updates;
- either cadence has fewer than 30 pooled checkpoint-related-group updates;
- phase intervals overlap, leave an internal gap over 1 ms, or do not span the
  run window;
- cumulative run energy and the sum of exhaustive phase allocations differ by
  more than 0.5%;
- the no-failure same-cadence restart/continue states, work, or final NLL differ;
- GPU power configuration changes within a block;
- a run crosses the thermal limit, diverges, or omits a required trace, phase,
  counter, learning, or work field.

Individual restore, rejoin, merge, or synchronization support below 30 updates
does not invalidate an otherwise supported grouped result. It sets that
individual estimate's evidence class to `exploratory_insufficient_updates`.

Missing cumulative energy may not be imputed from instantaneous power or PW1.

## Unchanged Mechanism and Salvage Gates

The checkpoint-cadence explanation survives only if:

1. the lower bound of the paired 90% run-level total interaction is above zero;
2. the lower bound of the supported checkpoint-related grouped interaction is
   above zero;
3. changing dense continuation to sparse continuation removes at least 50% of
   the median excess energy of dense continuation over sparse restart.

Sparse continuation survives only if all original gates pass:

1. all six sparse restart/continue pairs reach 256 canonical ticks by tick 384;
2. the upper bound of sparse-continuation minus sparse-restart final NLL is at
   most `0.01`;
3. attempted-FLOP saving has lower bound above zero and median at least `3%`;
4. median opportunity-tick saving is at least `24`, and continuation is earlier
   in all six blocks;
5. the upper bound of the cumulative-energy ratio is at most `1.05`;
6. continuation divergence count is zero;
7. cadence endpoints within a continuation level remain inside the frozen
   `0.01` NLL margin.

The `1.05` threshold is applied to PW2's newly observed cumulative run energy.
It does not retroactively validate or reinterpret PW1's invalid ratio.

## Decision Rules

1. Any measurement invalidator produces `measurement_invalid` and stops the
   scientific decision tree.
2. If a valid PW2 does not reproduce a positive dense-continuation energy
   excess over sparse restart, record `lc3_energy_penalty_not_reproduced`.
3. If the penalty reproduces, the total and supported grouped interactions
   pass, and every salvage gate passes, record
   `checkpoint_cadence_attributed_sparse_continuation_survives`.
4. If the penalty reproduces but either interaction gate fails, record
   `continuation_energy_not_attributed_to_checkpoint_cadence`.
5. If cadence is attributed but sparse continuation fails any unchanged
   salvage gate, record
   `checkpoint_cadence_partial_cause_candidate_still_fails`.

Exploratory individual restore or rejoin estimates cannot change those rules.

## Local-versus-Facility Boundary

PW2 observes cumulative energy at one GPU-board boundary, operation timing,
checkpoint/state bytes, work accounting, and held-out learning. It does not
measure host, DRAM, NIC, durable storage, cooling, rack, electrical conversion,
or point-of-common-coupling energy. The simulated outage schedule is not
physical datacenter outage time.

The facility bridge remains modeled and separate:

`P_GPU,g(t) = P_idle,g + alpha_phase(t) * (P_train,g - P_idle,g)`

`P_IT(t) = sum_g P_GPU,g(t) + P_CPU(t) + P_NIC(t) + P_storage(t)`.

The IT trace requires separately calibrated rack electrical and cooling
response before it becomes a facility waveform. Static PUE is not a waveform
model. A local PW2 result cannot establish rack ramp rate, spectral safety,
grid response, or datacenter energy.

## Engine Consumption Contract

The engine consumes, without hidden defaults:

- `source_bindings`, `pw1_failure_binding`, and `capability_observation`;
- `warm_start_binding`, `dataset`, `model`, `optimization`, and
  `canonical_work`;
- `checkpoint_representation`, `thermal_guard`, `factors`, and `arms`;
- `splits`, `execution_order`, `cumulative_meter`, and `phase_markers`;
- `phase_support`, `measurement_invalidators`, `estimands`,
  `mechanism_falsifiers`, and `salvage_falsifiers`;
- `decision_rules` and `facility_bridge`.

The JSON scenario's `required_result_fields` enumerates every mandatory
counter trace, update count, run total, grouped phase estimate, interaction,
gate, decision, and evidence-boundary field.

## Executed Result

PW2 completed all 32 factorial runs, reproduced the exact LC3 warm checkpoint,
and passed measurement validity with no active invalidators. The cumulative
counter updated every `91.667` ms effectively; held-out arms contained 83 to
109 counter updates each. Frozen support thresholds passed for checkpoint
snapshots (sparse `59.30`, dense `110.06` effective updates) and the pooled
checkpoint-related group (sparse `124.56`, dense `176.94`). Individual rare
restore, rejoin-transfer, and post-rejoin estimates remain exploratory.

The additive total interaction was median `2.2416e-5 J/token`, paired 90%
interval `[2.1746e-6, 3.5305e-5]`. The supported checkpoint-related group was
`5.8845e-6 [3.0774e-6, 8.9671e-6] J/token`; checkpoint snapshot alone was
`4.9917e-6 [2.8497e-6, 7.4481e-6] J/token`. All three mechanism gates passed.

The frozen primary estimand is raw cumulative energy over the complete run
window. The sensitivity-only idle-subtracted interaction was
`3.9825e-6 [-8.0109e-6, 1.2479e-5] J/token` and crossed zero. This does not
change the preregistered primary decision, but the local attribution is not
insensitive to estimated idle-baseline treatment.

The preselected sparse-continuation arm also passed all eight salvage gates:

- final-NLL delta median `0.0033385`, upper bound `0.0085037`;
- median attempted-work saving `3.03%`;
- median opportunity-tick saving `40`;
- cumulative-energy ratio median `0.96099`, upper bound `1.00319`.

The conclusion is
`checkpoint_cadence_attributed_sparse_continuation_survives`. Artifact
SHA-256:
`cfbca215878629bc416f169e5ded80684151d9b2a621548c7fef08207c41f8ee`.

## Optional Transfer Experiment: E002-PW3

PW3 must test dependency-safe dephasing across multiple simultaneous GPUs and
rack-visible checkpoint activity. It needs aligned per-GPU cumulative energy,
rack-PDU power, storage traffic and power, and cooling telemetry. PW2 supports
a local GPU-board cadence mechanism and sparse-continuation candidate. It does
not establish multi-GPU synchronization effects, rack transfer, cooling
response, facility energy, grid safety, or admission-capacity gains. This
external calibration path does not block the active E001-SC2 software
experiment.
