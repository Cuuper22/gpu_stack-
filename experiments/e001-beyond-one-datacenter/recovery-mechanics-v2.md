# E001 Recovery Mechanics v2

Status: preregistered protocol with pure recovery contracts and a transition
runtime substrate; not integrated into an E001 runner or result artifact

Date frozen: 2026-07-12

Parent protocol: [E001: Beyond One Datacenter](experiment.md)

## Purpose

This document freezes the next E001 mechanics milestone before any E001
recovery-v2 result exists. The milestone asks whether GPUSTACK can represent a site failure
as an observable, causally actionable transition, then account exactly for
preemption, checkpoint restoration, replay, membership changes, and all
recovery-induced WAN traffic.

The current E001 v1 protocol, runner, and persisted mechanics artifact remain
unchanged and valid under their existing scope. Recovery v2 has a distinct
machine protocol identity and no result or engine schema until an integrated
runner exists. The v1 artifact
models whole operations postponed around a fixed outage. It does not become a
preemption or recovery result because this document exists.

Recovery Mechanics v2 is still a virtual mechanics screen. It cannot validate
convergence, capability, time to a held-out loss target, production failure
rates, or full-facility energy.

## Frozen Scope

Recovery Mechanics v2 must implement:

- decision epochs at observable failure, recovery, checkpoint, restoration,
  reconfiguration, and operation-completion boundaries;
- physical health, controller intent, and state readiness as separate state;
- preemption of compute and collectives at the physical failure boundary;
- atomic checkpoint manifests and exact state lineage;
- rollback and replay from the latest valid recovery point;
- reactive removal and re-entry of sites without future-trace access;
- matched recovery baselines on identical exogenous traces;
- attempted, valid, lost, restored, replayed, and transferred work accounting;
- recovery-aware total inter-site byte accounting;
- content-addressed evidence for every structured admission gate below.

This milestone does not add adaptive topology, adaptive parallelism, pipeline
delay, optimizer correction, a calibrated learning model, or controlled
learning evidence. Those remain separate E001 debts.

## Transition-Driven Execution

The current whole-epoch scheduler is not the recovery-v2 semantics. The v2
runner advances only to the next material decision boundary.

A material boundary is the earliest of:

1. an operation attempt completing;
2. a checkpoint manifest becoming complete;
3. a physical failure occurring;
4. a failure becoming observable to the controller;
5. a site physically recovering;
6. recovery becoming observable to the controller;
7. checkpoint restoration completing;
8. state redistribution or reconfiguration completing.

At a timestamp `t`, ordering is frozen as follows:

1. Accrue work, bytes, and energy over the half-open interval ending at `t`.
2. Complete forward and replay operation attempts whose planned end is exactly
   `t`.
3. Atomically commit any checkpoint whose final required shard completed at
   `t`, against the membership and layout under which that manifest was
   scheduled.
4. Complete checkpoint restores whose planned end is exactly `t`.
5. Complete membership or layout reconfigurations whose planned end is exactly
   `t`.
6. Apply exogenous failures and recoveries beginning at `t`.
7. Preempt or abort operations that require a newly unavailable resource.
8. Persist attempt outcomes and update the state/checkpoint ledger.
9. Materialize one immutable observable decision state for the complete
   timestamp batch. No intermediate same-time state is policy-visible.
10. Apply at most one atomic policy intervention batch for that decision epoch.

Therefore, an operation ending exactly when a failure begins is complete. An
operation requiring the failed resource after that boundary is preempted.
Simultaneous exogenous transitions across sites are applied as one batch,
ordered canonically by event identifier inside the artifact. Overlapping,
contradictory failure and recovery intervals for one site are invalid input.

The legacy `run()` behavior may remain available for non-preemptible callers,
but E001 recovery-v2 results must come from transition-driven execution and a
new versioned engine/result schema.

## Policy Information Boundary

The environment may hold the complete failure trace. A candidate policy may
not. Engine-private physical truth and controller-observed state are distinct.

Future exogenous events must live in an engine-private queue. They must never
appear before observation in:

- `queued_event_ids`;
- controller configuration;
- site or link metadata;
- outage identifiers;
- recovery timestamps;
- policy construction arguments or closures;
- previously emitted decision states.

The policy receives only an immutable observed-state snapshot stamped with the
current decision time and transitions already observed by that time. A physical
failure may change engine-private execution membership without changing that
snapshot. Each visible transition
contains its event identifier, kind, affected site or resource, physical
occurrence time, observation time, and observable cause class. It does not
contain an unannounced recovery time or later event.

Physical failure immediately removes the resource from engine-private execution
even when detection is delayed. The controller does not receive physical health,
physical effective membership, active-attempt disappearance, or another side
channel before observation. Until the controller observes the failure, the
engine uses the frozen fail-safe behavior and records the detection delay separately.
The first implementation may require zero detection delay, but the schema must
distinguish occurrence from observation rather than silently equating them.

A planned interruption may expose future timing only when the scenario carries
an explicit `announced_at_ns` at or before the current decision time. Scheduled
knowledge and oracle knowledge are separate evidence classes.

### Prefix indistinguishability rule

For any two scenarios with the same observable history through time `t` but
different events after `t`, every candidate-policy decision, intervention
record, and visible-state serialization through `t` must be identical. The
future-trace oracle is exempt only because it is a separately labeled
clairvoyant comparator and never a candidate policy. It supports a regret
calculation only after a scalar objective is separately preregistered.

## Failure Description

Each v2 outage must state, rather than imply:

- physical failure start;
- controller observation time or detection delay;
- physical recovery time;
- controller recovery-observation time;
- optional prior announcement time;
- affected compute, fabric, state-I/O, checkpoint-I/O, power, and link
  resources;
- whether volatile model, optimizer, pipeline, RNG, and data-cursor state
  survives;
- whether local checkpoint storage survives;
- whether a surviving authoritative replica can reconstruct the missing state;
- whether the event is a curtailment, fail-stop, network partition, fail-slow
  transition, or another frozen class.

The screening matrix must contain at least one state-preserving interruption
and one volatile-state-loss interruption. A cause string alone is not recovery
semantics.

## Desired And Effective Membership

Recovery v2 separates four facts that are currently conflated:

- `desired_membership`: sites the controller intends to use;
- physical availability: sites whose required resources are healthy;
- state readiness: sites holding the exact training-state version required by
  the active job;
- controller-observed health and readiness, which may lag physical truth.

`physical_effective_membership` is the engine-private intersection of desired
membership, physical availability, and state readiness. It constrains execution
immediately. `observed_effective_membership` applies the same rule to facts the
controller has observed and is the only effective-membership view a candidate
policy may receive. A compatibility field `membership`, if retained, must name
which view it serializes and expose desired membership separately.

A physical failure removes a site from effective membership immediately. It
does not silently rewrite controller intent. The failure decision epoch lets
the controller remove the site, wait, restore elsewhere, or request a frozen
reconfiguration.

Physical recovery produces `recovered_unrestored`, not `ready`. A recovered
site cannot execute useful training work or rejoin a collective until:

1. its required state has survived or been restored;
2. its state version and manifest hashes match the active job version;
3. any required resharding or parallelism reconfiguration has completed;
4. the policy explicitly admits it to desired membership.

The adaptive policy must therefore test health and state readiness. The rule
"healthy and inactive means re-add" is invalid for volatile-state loss.

## Training-State Lineage

Every operation attempt must bind to a versioned input state. The minimum
lineage record contains:

- logical global step and local-cycle index;
- attempt number and whether the attempt is original or replay;
- model and optimizer state version;
- pipeline and parallelism configuration identifier;
- data-cursor interval or sample identifiers;
- RNG-state hash;
- input checkpoint or committed-cycle identifier;
- planned and executed work;
- terminal status and invalidation cause.

A synchronization cycle becomes globally committed only after its required
collective completes. Work inside an unfinished local cycle is provisional.
Failure during that cycle invalidates the affected attempt set according to the
frozen recovery policy.

The runner targets `total_steps` final committed steps. It does not stop after
`total_steps` attempts. A replayed logical step receives a new attempt number
and retains the original data and RNG lineage.

## Atomic Checkpoints

A checkpoint is a manifest, not the sum of checkpoint-write bytes.

Each manifest records:

- checkpoint identifier and synchronized state version;
- exact total state size;
- exact shard sizes and source state versions;
- storage location and failure domain for every shard;
- model, optimizer, RNG, and data-cursor hashes;
- write start and completion times;
- whether every required shard and the manifest commit completed.

Only a complete manifest may be restored. A partially written checkpoint
contributes bytes, time, and energy to accounting but is not a recovery point.

Shard sizes must be a deterministic integer partition whose sum equals the
declared checkpoint size exactly. Independent rounding by site is forbidden.

Checkpoint triggers are one frozen sequence of absolute wall-clock nanoseconds
shared by every policy. Each artifact serializes both `trigger_at_ns` and the
later `atomic_commit_at_ns`; a logical-step interval is not a matched deadline.
If a trigger arrives during an unsynchronized local cycle, the implementation must
either:

- force and account for a consistency synchronization before checkpointing; or
- implement a manifest that can exactly restore the unsynchronized per-site
  states, data cursors, and optimizer versions.

The simpler preregistered v2 path is a forced consistency synchronization.
That synchronization and its bytes are charged to the policy that executes it.
The absolute trigger schedule, not the resulting synchronization time, is
identical across policies.

An explicit genesis manifest at logical step zero is required. If no later
checkpoint survives, recovery rolls back to genesis rather than inventing an
implicit state.

## Preemption, Rollback, Restore, And Replay

### Compute

When failure interrupts compute, the attempt ends at the failure boundary.
Executed work before the boundary counts as attempted work. Work not present in
the final valid state counts as lost work. Planned but unexecuted work counts as
neither.

### Collective communication

Failure of an endpoint or required path aborts the in-flight collective.
Bytes already transmitted count as attempted and wasted WAN traffic. They do
not count as a completed synchronization. Latency and transmission phases must
be distinguishable so a failure during link latency cannot fabricate payload
bytes.

### Rollback

For a volatile-state-loss event without a surviving authoritative replica, the
recovery point is the latest complete common checkpoint. Previously committed
steps after that checkpoint become invalidated work. Provisional work in the
current cycle is also invalidated. Each executed attempt portion may be
invalidated at most once.

### Restore

Restoration reads the exact committed manifest and consumes the declared
checkpoint-I/O, state-I/O, and WAN resources. Restore bytes are distinct from
checkpoint-write bytes, state migration, and collective bytes. State becomes
ready only after every required shard and the manifest lineage verify.

### Replay

Replay starts at the first invalidated logical step, uses the original sample
order and RNG lineage, and executes under the recovery policy's effective
membership. Replay attempts may themselves be interrupted. Repeated failure
during restore or replay must remain deterministic and idempotent.

## Accounting Contract

Recovery accounting is attempt-based. At terminal completion with no work in
flight:

`attempted_compute_flops = valid_final_state_compute_flops + lost_compute_flops`

`replay_compute_flops` is a labeled subset of attempted work. It is not added
again to the identity. A replay attempt later lost to another failure belongs
to both the replay subset and lost work, while remaining one attempted portion.

For each attempt:

`0 <= executed_work <= planned_work`

and exactly one terminal status is recorded: `completed`, `preempted`,
`aborted`, or `invalidated_after_commit`.

The mechanics artifact must report, without attaching new acceptance
thresholds:

- attempted, valid-final-state, lost, and replay compute FLOPs;
- attempted, completed, and aborted collective link bytes;
- preempted compute attempts and aborted collectives;
- invalidated committed steps and provisional local steps;
- checkpoint bytes written, partial checkpoint bytes, and restore bytes read;
- state migration and recovery redistribution bytes;
- physical outage time, observation delay, restore time, replay time, time to
  resumed useful compute, and time to safe site re-entry;
- checkpoint age at each failure;
- time-integrated base, compute, restore, replay, and modeled transfer energy,
  with unmodeled components named explicitly.

`attempted_collective_link_bytes` is a derived diagnostic:

`attempted_collective_link_bytes = completed_collective_link_bytes + aborted_collective_link_bytes`

It is not a seventh inter-site traffic class. `checkpoint_write_bytes` covers
all physically written local and remote checkpoint I/O. Bytes belonging to a
write attempt that never atomically commits also enter the subset
`partial_checkpoint_write_bytes`. Remote checkpoint-write segments remain in
`remote_checkpoint_replication_link_bytes`; these diagnostics overlap that
traffic class and are not added again to total inter-site bytes.

Base energy must be integrated from time-varying physical and membership state.
Final membership cannot be projected backward across an epoch. Physical
recovery time and job recovery time remain separate.

Every physical inter-site link-direction segment has exactly one additive
traffic class:

- `completed_collective_link_bytes`;
- `aborted_collective_link_bytes`;
- `remote_checkpoint_replication_link_bytes`;
- `remote_checkpoint_restore_link_bytes`;
- `recovery_state_redistribution_link_bytes`; or
- `planned_state_migration_link_bytes`.

Retries and retransmissions retain the class of their attempt and a distinct
segment identifier. They are not added again through a second retransmission
category. Local checkpoint reads contribute to `checkpoint_restore_bytes` but
not to an inter-site traffic class.

## Recovery-Debt Estimand

Each joint recovery episode freezes one `durable_frontier_target` containing at
least the committed logical step, state-lineage hash, data-cursor hash, RNG hash,
and optimizer version. The actual anchor is the first durable commit after the
episode's first physical failure that reaches that target. The matched
same-policy no-failure anchor is the first commit that reaches the identical
target. `recovery_debt_ns` is actual anchor minus counterfactual anchor and may
be negative.

Overlapping failures, or a repeated failure before restore/replay completes,
belong to one joint episode with ordered `outage_event_ids`. The registered debt
removes that complete causal bundle in the paired counterfactual. Per-event
marginal attribution is not implied and requires a separate preregistered
estimand. If either run never reaches the shared target, debt is unresolved, not
infinite or zero.

## Matched Recovery Baselines

Every policy receives identical sites, links, absolute-time exogenous traces,
failure manifestations, checkpoint deadlines, state sizes, initial placement,
data order, RNG seeds, and accounting boundaries. A faster policy may encounter
the same absolute-time event at a different logical step. That is part of the
counterfactual rather than a reason to move the trace.

Recovery v2 requires the following exact policy identifiers and roles. The
first four are non-clairvoyant baselines, `adaptive-recovery` is the candidate,
and the last is an explicitly privileged oracle comparator. The oracle is
required for completeness but is not a target in the fixed-baseline superiority
gate.

1. `synchronous-wait-restore`: synchronous global all-reduce, original desired
   membership, wait for physical recovery, restore the latest valid checkpoint,
   then replay.
2. `fixed-local-checkpoint-restart`: frozen local-update cadence using the same
   checkpoint, rollback, restore, and replay machinery.
3. `fixed-cadence-reactive-membership`: remove or replace failed membership but
   do not adapt learning cadence. This isolates membership recovery from
   cadence adaptation.
4. `power-aware-migration-without-learning-adaptation`: move or restore state
   to healthy capacity while cadence and optimizer behavior remain frozen.
5. `adaptive-recovery`: candidate policy using observable membership and
   completed-cycle communication evidence to adapt recovery and cadence.
6. `future-trace-recovery-oracle` (`oracle_comparator`): identical mechanics
   with privileged future failure and recovery knowledge. It is not a
   reportable regret bound until a scalar objective is preregistered.

Policies 1 through 4 have role `baseline`; policy 5 has role `candidate`.

The broader E001 preregistration still requires
`single-site-centralized-equivalent-capacity` and `fixed-sparse-gossip`.
Recovery-v2 baseline completion does not satisfy
the existing complete-baseline-vector gate until those also execute.

## Total Inter-Site Byte Amendment

The parent hypothesis predicts at least 10x fewer inter-site bytes than
synchronous global all-reduce. The current machine screen evaluates collective
payload only, which is too narrow once recovery creates checkpoint, restore,
migration, and aborted-transfer traffic.

Recovery v2 preregisters one protocol amendment:

`total_inter_site_byte_fraction <= 0.10`

The numerator is `total_inter_site_link_bytes`, the exact sum of the six
disjoint physical link-segment classes above. It includes:

- completed and aborted collective traffic;
- remote checkpoint replication;
- remote checkpoint restore reads, but not local restore I/O;
- state migration and recovery redistribution;
- retransmission caused by interruption.

The denominator is
`synchronous_recovery_baseline_total_inter_site_link_bytes` from
`synchronous-wait-restore` on the same absolute-time trace and the same terminal
durable-frontier target. Each physical link-direction segment is counted once.
Both raw totals and their ratio are serialized. Payload size is not a substitute
for algorithm-specific link traffic.

The artifact also serializes a content-addressed link-segment ledger. Every
entry records a unique segment identifier, exactly one of the six traffic
classes, physical bytes, source and destination, attempt and event references,
and terminal outcome status. The six aggregates must be reproducible from that
ledger, not asserted independently.

The raw denominator carries a matched `synchronous-wait-restore` run reference
with the run snapshot hash, absolute exogenous-trace hash, and serialized
durable-frontier-target hash. The denominator must equal that referenced run's
`total_inter_site_link_bytes`; the candidate and denominator trace and frontier
hashes must match.

When the machine protocol is versioned for this amendment,
`total_inter_site_byte_fraction` becomes the primary 10x falsifier.
`collective_payload_byte_fraction` remains a diagnostic component and must not
remain as a second independent 10x pass gate. Prior v1 artifacts retain their
original protocol hash and interpretation.

No recovery-time, lost-work, replay, restore, or re-entry threshold is added.
The protocol contains no honest preregistered value for those. The existing
`completion_time_ratio <= 1.0` remains time to the same held-out learning
target, including all recovery. Fixed-step runtime cannot populate it.

## Mandatory Structured Evidence Gates

The separate `E001_RECOVERY_V2_PROTOCOL` registers the following gates.
Missing results remain unresolved rather than disappearing into notes.

### `e001-observable-failure-recovery-epochs`

- Earliest stage: virtual.
- Required panels: failure occurrence and observation, recovery occurrence and
  observation, checkpoint commit, restore completion, safe re-entry.
- Acceptance rule: each nonempty material timestamp batch produces one
  immutable decision state containing every transition in canonical order,
  with no intermediate same-time state or skipped actionable transition.
- Evidence boundary: a trace that schedules work wholly after an outage does
  not satisfy this gate.

### `e001-reactive-membership-without-trace-leakage`

- Earliest stage: virtual.
- Required panels: immediate failure observation, delayed failure observation,
  unannounced recovery, announced curtailment, recovered-but-unrestored site,
  repeated future-prefix comparison, and safe explicit re-entry.
- Acceptance rule: candidate decisions depend only on the observable prefix;
  effective membership excludes failed or state-stale sites; re-entry occurs
  only after state verification and an explicit intervention.
- Evidence boundary: oracle trace access, scenario closure access, or exposure
  through queued metadata fails the gate.

### `e001-preemption-replay-conservation`

- Earliest stage: virtual.
- Required panels: compute interruption, collective interruption during
  latency, collective interruption during payload, rollback after committed
  work, restore, replay, repeated interruption during restore, and repeated
  interruption during replay.
- Acceptance rule: all attempt-level conservation identities hold, every
  attempt has one terminal disposition, and no work or byte is counted twice.
- Evidence boundary: scheduled work totals without executed portions and final
  validity cannot satisfy this gate.

### `e001-checkpoint-lineage-and-restore`

- Earliest stage: virtual.
- Required panels: complete checkpoint, checkpoint/failure timestamp tie,
  partial checkpoint, failed local checkpoint storage, remote durable
  checkpoint, genesis rollback, and restored model/optimizer/RNG/data lineage.
- Acceptance rule: restoration uses only a complete manifest; exact shard
  sizes and hashes reconstruct one declared state version; partial artifacts
  remain unrestorable.
- Evidence boundary: checkpoint byte counts without an atomic manifest do not
  satisfy this gate.

### `e001-recovery-baseline-completeness`

- Earliest stage: virtual.
- Required comparisons: all six exact recovery policy identifiers listed above;
  `adaptive-recovery` is the candidate, four are non-clairvoyant baselines, and
  `future-trace-recovery-oracle` is the oracle comparator.
- Acceptance rule: every comparison executes on matched traces, checkpoint
  rules, state sizes, seeds, and accounting boundaries. No missing recovery
  comparator may support a claim; regret remains unavailable until its scalar
  objective is preregistered.
- Evidence boundary: the future-trace oracle is a comparator only. A scalar
  policy-decision regret is not reportable until its objective, units, horizon,
  normalization, tie handling, and oracle action space are preregistered.

### Existing gates extended by recovery v2

`e001-collective-and-failure-model-admission` also requires both raw total-byte
values, the matched denominator reference, the content-addressed segment
ledger, all six disjoint traffic classes, derived attempted plus
algorithm-specific completed and aborted collective link bytes, checkpoint and
partial-checkpoint write diagnostics, mid-operation failure, rollback,
checkpoint restore, replay, membership response, state movement, and recovery
debt.

`e001-full-boundary-nonreversal` also requires checkpoint and restore traffic,
replay, deferred work, dynamic network and storage energy, host and cooling
energy, and the complete recovery horizon. Its earliest resolvable stage
remains controlled.

`e001-baseline-vector-superiority` applies to the complete recovery-aware
primary vector against the four non-clairvoyant recovery baselines and the
parent centralized-equivalent and sparse-gossip obligations. The future-trace
oracle is excluded from superiority and remains a separately labeled
comparator. The gate's earliest resolvable stage remains controlled.

## Artifact Conclusion Rules

At virtual stage, failure takes precedence over incompleteness.

The recovery-v2 artifact is `failed_virtual_screen` when either:

- an evaluated scalar falsifier fails; or
- a mandatory virtual evidence requirement is explicitly `FAILED`.

Otherwise, it is `inconclusive` when any of the following is true:

- an evidence gap remains;
- `progress_per_flop_ratio` is absent or unresolved;
- `completion_time_ratio` is absent or unresolved;
- any mandatory evidence requirement is `UNRESOLVED` or `NOT_APPLICABLE`;
- held-out learning transfer is unresolved;
- controlled full-boundary accounting is unresolved;
- algorithm-specific collective traffic is incomplete;
- interval coverage is absent;
- policy decision regret remains absent until a scalar objective is separately
  preregistered;
- the complete parent-protocol baseline vector is absent;
- topology, parallelism, pipeline delay, optimizer correction, or placement
  remains outside the implemented joint controller;
- the required controlled learning panels are absent.

Passing recovery mechanics and the total-byte screen cannot produce a
convergence or capability conclusion. A `survived_virtual_screen` result is
permitted only when every registered scalar gate is present and survives,
every mandatory virtual requirement is satisfied, and no evidence gap remains.
Recovery v2 is expected to remain inconclusive because the controlled learning
and complete joint-mechanism requirements are intentionally unresolved.

## Controlled-Validation Debt

Recovery mechanics can reject a broken virtual model, but the E001 research
claim still requires:

- separate calibration and evaluation observations for learning progress per
  FLOP under rollback, membership change, and replay;
- repeated controlled 7B to 30B runs with bandwidth and site-power
  perturbations;
- a 30B to 100B-plus, multi-week run across at least three geographic sites;
- held-out site, accelerator, model, optimizer, WAN, and power-stress panels;
- algorithm-specific collective implementations and measured WAN transfer
  curves;
- state, checkpoint, host, storage, network, cooling, and recovery power
  measurements over the full time-to-target boundary;
- production-relevant failure, detection, state-loss, and repair observations;
- the centralized-equivalent, sparse-gossip, migration-only, fixed-policy, and
  future-trace-oracle comparisons on frozen matched traces;
- calibrated uncertainty coverage;
- a separately preregistered scalar decision objective before any
  decision-regret evidence is reported.

Until those exist, recovery-v2 results answer whether GPUSTACK represents
failure and recovery coherently. They do not answer whether distributed
frontier training preserves learning efficiency.

## Executed Virtual Result

The first recovery-v2 vertical slice is implemented in
`gpu_stack/research/e001_recovery_runner.py`, with the frozen scenario in
`recovery-scenario-v2.json`, the result in
`results/recovery-mechanics-v2.json`, and the visual projection in
`../../docs/data/e001-recovery-v2.json`.

The run reaches the same durable frontier for all four policies with exact
work conservation. Adaptive is mechanically better than synchronous on this
trace, but the fixed-local/adaptive comparison splits: fixed-local wins time
and bytes; adaptive wins lost work and modeled energy. The result remains
`inconclusive_frontier_hypothesis` because learning is a shared declared prior.

The next dependency is observed learning data, not a more general recovery
schema. Run fixed-local and adaptive interrupted training on a small real
workload, hold out evaluation runs, and project progress-per-FLOP, progress-per-
joule, time-to-target, residuals, and uncertainty through this same artifact.
