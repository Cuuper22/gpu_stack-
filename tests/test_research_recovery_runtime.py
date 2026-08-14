"""Tests for the recovery runtime — the event engine behind failure recovery.

The ``RecoveryRuntime`` replays a fixed failure trace over a set of sites
and advances in discrete decision batches: each call to
``advance_to_decision`` drains every boundary due at the next timestamp
(attempt completions, checkpoint commits, failure observations, physical
recoveries) into one atomic snapshot a policy could act on. Ordering within
a batch is part of the contract — completions and checkpoint commits land
before a same-time failure, and a new failure precedes an old failure's
physical recovery at the same nanosecond.

The tests pin the invariants that make the simulation trustworthy. Work is
conserved: attempted work always equals committed plus lost, replay work is
tracked separately, and a preempted attempt loses exactly the work it had
done. Checkpoints are atomic — a manifest commits only if every shard byte
sums, every member site contributed to the step, the step is not ahead of
the proven frontier, and no failure lands first; otherwise it aborts.
Recovery is explicit restore-then-replay: a site stays out of the effective
membership until replay completes, replay attempts can only come from the
runtime itself, and a recovery plan binds to the exact work-ledger digest
it was planned against, so a forged ledger is rejected. Repeated failures
during restore, fixed restart, or replay cancel the stale stages and record
the interrupted bytes and lost work precisely. Snapshots serialize
canonically, and forged serialized fields (duplicate failure ids, future
cutoffs, inconsistent flags) are rejected on the way back in.
"""

from dataclasses import replace

import pytest

from gpu_stack.research.recovery import (
    EvidenceBasis,
    EvidenceBoundary,
    FailureCauseCode,
    FailureInterval,
    FailureStatus,
    FailureTrace,
    LogicalWorkIdentity,
    ReplayLineageBinding,
    RecoveryRequest,
    SiteWorkAttempt,
    WorkLedger,
    WorkAttemptKind,
    WorkOutcomeDisposition,
    plan_recovery,
)
from gpu_stack.research.recovery_runtime import (
    CheckpointManifest,
    CheckpointShard,
    DecisionBoundary,
    RecoveryRuntime,
    RuntimeSnapshot,
    SiteState,
)


def _evidence(boundary_id: str) -> EvidenceBoundary:
    return EvidenceBoundary(
        boundary_id=boundary_id,
        basis=EvidenceBasis.ASSUMED,
        source_ids=(f"source:{boundary_id}",),
        assumptions=("synthetic runtime fixture",),
    )


def _digest(character: str) -> str:
    return "sha256:" + (character * 64)


def _failure(
    failure_id: str,
    start_ns: int,
    recovery_ns: int,
    *,
    site_id: str = "site-a",
) -> FailureInterval:
    return FailureInterval(
        failure_id=failure_id,
        site_id=site_id,
        failure_start_ns=start_ns,
        recovery_ns=recovery_ns,
        cause=FailureCauseCode.SITE_UNAVAILABLE,
        evidence=_evidence(f"evidence:{failure_id}"),
    )


def _runtime(*failures: FailureInterval, include_site_c: bool = False) -> RecoveryRuntime:
    site_ids = ("site-a", "site-b", "site-c") if include_site_c else (
        "site-a",
        "site-b",
    )
    return RecoveryRuntime(
        runtime_id="runtime-1",
        lineage_id="run-1",
        site_ids=site_ids,
        initial_membership=("site-a", "site-b"),
        failure_trace=FailureTrace("trace-1", failures),
    )


def _attempt(
    attempt_id: str,
    step: int,
    start_ns: int,
    end_ns: int,
    *,
    site_id: str = "site-a",
    work: float = 100.0,
) -> SiteWorkAttempt:
    return SiteWorkAttempt(
        attempt_id=attempt_id,
        lineage_id="run-1",
        site_id=site_id,
        step=step,
        start_ns=start_ns,
        planned_end_ns=end_ns,
        planned_work=work,
        work_unit="FLOP",
        kind=WorkAttemptKind.FORWARD,
        logical_work=LogicalWorkIdentity(
            logical_work_id=f"logical:run-1:{site_id}:step-{step}",
            lineage_id="run-1",
            logical_step=step,
            logical_partition=f"partition:{site_id}",
            original_site_id=site_id,
            state_lineage_hash=_digest("9"),
        ),
        evidence=_evidence(f"evidence:{attempt_id}"),
    )


def _manifest(
    checkpoint_id: str,
    commit_at_ns: int,
    committed_step: int,
    *,
    state_bytes: int = 100,
    recovery_source_site_id: str = "checkpoint-store",
) -> CheckpointManifest:
    state_version = f"state:{committed_step}"
    write_started_at_ns = max(0, commit_at_ns - 10)
    parameter_id = f"{checkpoint_id}:parameters"
    optimizer_id = f"{checkpoint_id}:optimizer"
    return CheckpointManifest(
        checkpoint_id=checkpoint_id,
        lineage_id="run-1",
        committed_step=committed_step,
        state_version=state_version,
        model_hash=_digest("a"),
        optimizer_hash=_digest("b"),
        rng_hash=_digest("c"),
        data_cursor_hash=_digest("d"),
        state_bytes=state_bytes,
        required_shard_ids=(parameter_id, optimizer_id),
        shards=(
            CheckpointShard(
                shard_id=parameter_id,
                site_id=recovery_source_site_id,
                source_state_version=state_version,
                storage_location=f"object://{checkpoint_id}/parameters",
                failure_domain=f"domain:{recovery_source_site_id}",
                state_bytes=60,
                checksum=_digest("e"),
                write_started_at_ns=write_started_at_ns,
                write_completed_at_ns=commit_at_ns,
            ),
            CheckpointShard(
                shard_id=optimizer_id,
                site_id="site-b",
                source_state_version=state_version,
                storage_location=f"object://{checkpoint_id}/optimizer",
                failure_domain="domain:site-b",
                state_bytes=40,
                checksum=_digest("f"),
                write_started_at_ns=write_started_at_ns,
                write_completed_at_ns=commit_at_ns,
            ),
        ),
        site_membership=("site-b", "site-a"),
        recovery_source_site_id=recovery_source_site_id,
        checkpoint_write_started_at_ns=write_started_at_ns,
        checkpoint_write_completed_at_ns=commit_at_ns,
        manifest_committed_at_ns=commit_at_ns,
        evidence=_evidence(f"evidence:{checkpoint_id}"),
    )


def test_initial_then_completion_and_checkpoint_commit_precede_same_time_failure():
    runtime = _runtime(_failure("failure-a", 100, 200))
    with pytest.raises(RuntimeError, match="emit INITIAL"):
        runtime.submit_attempt(_attempt("before-initial", 1, 0, 10))
    initial = runtime.advance_to_decision()
    assert initial.boundaries == (DecisionBoundary.INITIAL,)
    runtime.schedule_checkpoint(_manifest("checkpoint-0", 10, 0))
    assert runtime.advance_to_decision().boundaries == (
        DecisionBoundary.CHECKPOINT_COMMIT,
    )
    runtime.submit_attempt(_attempt("step-1-a", 1, 10, 100))
    runtime.submit_attempt(
        _attempt("step-1-b", 1, 10, 100, site_id="site-b")
    )
    runtime.schedule_checkpoint(_manifest("checkpoint-1", 100, 1))

    failed = runtime.advance_to_decision()
    assert failed.timestamp_ns == 100
    assert failed.boundaries == (
        DecisionBoundary.OPERATION_COMPLETION,
        DecisionBoundary.OPERATION_COMPLETION,
        DecisionBoundary.CHECKPOINT_COMMIT,
        DecisionBoundary.FAILURE_OBSERVED,
    )
    assert failed.boundary_ids == (
        "attempt:step-1-a:complete",
        "attempt:step-1-b:complete",
        "checkpoint:checkpoint-1:commit",
        "failure:failure-a:observed",
    )
    assert tuple(
        item.checkpoint_id for item in failed.committed_checkpoints
    ) == ("checkpoint-0", "checkpoint-1")
    assert failed.site("site-a").state is SiteState.FAILED
    assert failed.effective_membership == ("site-b",)
    assert failed.observed_failures[0].status is FailureStatus.ACTIVE
    assert failed.observed_failures[0].recovery_observed_ns is None
    assert failed.failure_first_observed_at_ns == {"failure-a": 100}
    assert failed.work.lost_work == 0.0
    assert RuntimeSnapshot.from_json(failed.to_json()) == failed
    duplicate_failure = failed.to_dict()
    duplicate_failure["observed_failures"].append(
        duplicate_failure["observed_failures"][0]
    )
    with pytest.raises(ValueError, match="failure IDs must be unique"):
        RuntimeSnapshot.from_dict(duplicate_failure)
    future_cutoff = failed.to_dict()
    future_cutoff["timestamp_ns"] = 99
    with pytest.raises(ValueError, match="policy cutoff"):
        RuntimeSnapshot.from_dict(future_cutoff)

    physically_recovered = runtime.advance_to_decision()
    assert physically_recovered.boundaries == (
        DecisionBoundary.PHYSICAL_RECOVERY,
    )
    assert physically_recovered.timestamp_ns == 200
    assert (
        physically_recovered.site("site-a").state
        is SiteState.RECOVERED_UNRESTORED
    )
    assert physically_recovered.effective_membership == ("site-b",)
    assert physically_recovered.observed_failures[0].recovery_observed_ns == 200
    assert physically_recovered.observed_failures[0].observed_at_ns == 200
    assert physically_recovered.failure_first_observed_at_ns == {"failure-a": 100}


def test_initial_batch_drains_exogenous_transitions_at_runtime_start():
    runtime = _runtime(_failure("failure-now", 0, 10))
    initial = runtime.advance_to_decision()
    assert initial.boundaries == (
        DecisionBoundary.INITIAL,
        DecisionBoundary.FAILURE_OBSERVED,
    )
    assert initial.site("site-a").state is SiteState.FAILED


def test_simultaneous_cross_site_failures_emit_one_atomic_decision_batch():
    runtime = _runtime(
        _failure("failure-a", 100, 200, site_id="site-a"),
        _failure("failure-b", 100, 250, site_id="site-b"),
    )
    runtime.advance_to_decision()

    failed = runtime.advance_to_decision()
    assert failed.timestamp_ns == 100
    assert failed.boundaries == (
        DecisionBoundary.FAILURE_OBSERVED,
        DecisionBoundary.FAILURE_OBSERVED,
    )
    assert failed.boundary_ids == (
        "failure:failure-a:observed",
        "failure:failure-b:observed",
    )
    assert failed.site("site-a").state is SiteState.FAILED
    assert failed.site("site-b").state is SiteState.FAILED
    assert failed.effective_membership == ()


def test_failure_preempts_inflight_attempt_and_cancels_its_completion():
    runtime = _runtime(_failure("failure-a", 40, 80))
    runtime.advance_to_decision()
    runtime.submit_attempt(_attempt("step-1", 1, 0, 100))

    failed = runtime.advance_to_decision()
    assert failed.boundaries == (DecisionBoundary.FAILURE_OBSERVED,)
    assert failed.timestamp_ns == 40
    assert failed.work.attempted_work == pytest.approx(40.0)
    assert failed.work.committed_work == 0.0
    assert failed.work.lost_work == pytest.approx(40.0)
    assert failed.sites[0].in_flight_attempt_id is None
    assert failed.observed_failures[0].recovery_observed_ns is None

    recovered = runtime.advance_to_decision()
    assert recovered.boundaries == (DecisionBoundary.PHYSICAL_RECOVERY,)
    assert recovered.timestamp_ns == 80
    assert runtime.advance_to_decision() is None


def test_checkpoint_manifest_is_atomic_and_failure_before_commit_aborts_it():
    with pytest.raises(ValueError, match="sum exactly"):
        _manifest("bad-logical-partition", 100, 0, state_bytes=99)

    manifest = _manifest("checkpoint-0", 100, 0)
    assert manifest.state_version == "state:0"
    assert manifest.model_hash == _digest("a")
    assert manifest.rng_hash == _digest("c")
    assert manifest.data_cursor_hash == _digest("d")
    assert manifest.state_bytes == 100
    assert manifest.is_genesis
    assert sum(item.state_bytes for item in manifest.shards) == 100
    assert manifest.required_shard_ids == tuple(
        item.shard_id for item in manifest.shards
    )
    assert CheckpointManifest.from_json(manifest.to_json()) == manifest
    forged_manifest = manifest.to_dict()
    forged_manifest["model_hash"] = "sha256:not-a-digest"
    with pytest.raises(ValueError, match="64 lowercase hex"):
        CheckpointManifest.from_dict(forged_manifest)

    runtime = _runtime(_failure("failure-a", 50, 80))
    initial = runtime.advance_to_decision()
    assert initial.committed_checkpoints == ()
    runtime.schedule_checkpoint(manifest)

    failed = runtime.advance_to_decision()
    assert failed.boundaries == (DecisionBoundary.FAILURE_OBSERVED,)
    assert failed.committed_checkpoints == ()
    assert failed.aborted_checkpoint_ids == ("checkpoint-0",)
    runtime.advance_to_decision()
    assert runtime.advance_to_decision() is None


def test_checkpoint_ahead_of_proven_committed_frontier_is_aborted():
    runtime = _runtime()
    runtime.advance_to_decision()
    runtime.schedule_checkpoint(_manifest("checkpoint-0", 10, 0))
    assert runtime.advance_to_decision().boundaries == (
        DecisionBoundary.CHECKPOINT_COMMIT,
    )
    runtime.schedule_checkpoint(_manifest("checkpoint-future", 20, 2))

    attempted_commit = runtime.advance_to_decision()
    assert attempted_commit.boundaries == (DecisionBoundary.CHECKPOINT_COMMIT,)
    assert tuple(
        item.checkpoint_id for item in attempted_commit.committed_checkpoints
    ) == ("checkpoint-0",)
    assert attempted_commit.aborted_checkpoint_ids == ("checkpoint-future",)


def test_checkpoint_frontier_requires_every_manifest_member_for_each_step():
    runtime = _runtime()
    runtime.advance_to_decision()
    runtime.schedule_checkpoint(_manifest("checkpoint-0", 10, 0))
    assert runtime.advance_to_decision().boundaries == (
        DecisionBoundary.CHECKPOINT_COMMIT,
    )
    runtime.submit_attempt(_attempt("only-site-a-step-1", 1, 10, 20))
    runtime.schedule_checkpoint(_manifest("checkpoint-missing-site-b", 20, 1))

    attempted_commit = runtime.advance_to_decision()
    assert attempted_commit.boundaries == (
        DecisionBoundary.OPERATION_COMPLETION,
        DecisionBoundary.CHECKPOINT_COMMIT,
    )
    assert tuple(
        item.checkpoint_id for item in attempted_commit.committed_checkpoints
    ) == ("checkpoint-0",)
    assert attempted_commit.aborted_checkpoint_ids == (
        "checkpoint-missing-site-b",
    )


def test_desired_membership_changes_before_effective_reconfiguration_completes():
    runtime = _runtime(include_site_c=True)
    runtime.advance_to_decision()
    runtime.request_membership(
        ("site-a", "site-c"),
        reconfiguration_id="move-b-to-c",
        duration_ns=10,
    )
    assert runtime.desired_membership == ("site-a", "site-c")
    assert runtime.effective_membership == ("site-a", "site-b")
    runtime.submit_attempt(_attempt("boundary-at-5", 1, 0, 5))

    before_completion = runtime.advance_to_decision()
    assert before_completion.boundaries == (DecisionBoundary.OPERATION_COMPLETION,)
    assert before_completion.desired_membership == ("site-a", "site-c")
    assert before_completion.effective_membership == ("site-a", "site-b")

    completed = runtime.advance_to_decision()
    assert completed.boundaries == (DecisionBoundary.RECONFIGURATION_COMPLETION,)
    assert completed.timestamp_ns == 10
    assert completed.desired_membership == ("site-a", "site-c")
    assert completed.effective_membership == ("site-a", "site-c")


def test_membership_removal_requires_quiescence_and_blocks_new_removed_site_work():
    busy = _runtime(include_site_c=True)
    busy.advance_to_decision()
    busy.submit_attempt(_attempt("site-b-busy", 1, 0, 20, site_id="site-b"))
    with pytest.raises(ValueError, match="quiescent sites"):
        busy.request_membership(
            ("site-a", "site-c"),
            reconfiguration_id="remove-b-while-busy",
            duration_ns=10,
        )

    draining = _runtime(include_site_c=True)
    draining.advance_to_decision()
    draining.request_membership(
        ("site-a", "site-c"),
        reconfiguration_id="remove-b",
        duration_ns=10,
    )
    with pytest.raises(ValueError, match="pending membership removal"):
        draining.submit_attempt(
            _attempt("site-b-after-request", 1, 0, 20, site_id="site-b")
        )


def _advance_base_recovery_runtime(
    *extra_failures: FailureInterval,
    checkpoint_source_site_id: str = "checkpoint-store",
):
    runtime = _runtime(
        _failure("failure-1", 100, 200),
        *extra_failures,
    )
    runtime.advance_to_decision()
    runtime.schedule_checkpoint(
        _manifest(
            "checkpoint-0",
            10,
            0,
            recovery_source_site_id=checkpoint_source_site_id,
        )
    )
    checkpoint_snapshot = runtime.advance_to_decision()
    assert checkpoint_snapshot.boundaries == (DecisionBoundary.CHECKPOINT_COMMIT,)
    runtime.submit_attempt(_attempt("step-1-a", 1, 10, 50))
    runtime.submit_attempt(
        _attempt("step-1-b", 1, 10, 50, site_id="site-b")
    )
    completed_step = runtime.advance_to_decision()
    assert completed_step.boundaries == (
        DecisionBoundary.OPERATION_COMPLETION,
        DecisionBoundary.OPERATION_COMPLETION,
    )
    assert runtime.advance_to_decision().boundaries == (
        DecisionBoundary.FAILURE_OBSERVED,
    )
    recovered = runtime.advance_to_decision()
    assert recovered.boundaries == (DecisionBoundary.PHYSICAL_RECOVERY,)
    assert recovered.timestamp_ns == 200
    return runtime, recovered


def _plan_current_recovery(runtime: RecoveryRuntime, snapshot: RuntimeSnapshot):
    failure = next(
        item for item in snapshot.observed_failures if item.failure_id == "failure-1"
    )
    checkpoint = runtime.checkpoint_ledger.latest_at(
        snapshot.timestamp_ns,
        lineage_id="run-1",
    )
    assert checkpoint is not None
    restore_resources = checkpoint.restore_resource_ids("site-a")
    request = RecoveryRequest(
        recovery_id="recovery-1",
        lineage_id="run-1",
        decision_time_ns=snapshot.timestamp_ns,
        failure=failure,
        target_site_id="site-a",
        last_committed_step=1,
        restore_bandwidth_bytes_per_second=1_000_000_000.0,
        replay_work_per_second=1_000_000_000.0,
        fixed_restart_latency_ns=10,
        unavailable_site_ids=(),
        evidence=_evidence("evidence:recovery-1"),
        failure_observations=snapshot.observed_failures,
        available_resource_ids=restore_resources,
        required_restore_resource_ids=restore_resources,
    )
    return plan_recovery(request, runtime.checkpoint_ledger, runtime.work_ledger)


def test_restore_then_replay_is_explicit_and_readiness_returns_only_after_replay():
    runtime, recovered = _advance_base_recovery_runtime()
    plan = _plan_current_recovery(runtime, recovered)
    assert plan.transfer_latency_ns == 100
    assert plan.replay_latency_ns == 200
    assert plan.recovery_latency_ns == 310

    runtime.begin_recovery(plan)
    assert runtime.site_state("site-a") is SiteState.RESTORING
    assert runtime.effective_membership == ("site-b",)
    snapshot_outcomes = {
        item.attempt.attempt_id: item for item in plan.work_snapshot.outcomes
    }
    replay_bindings = tuple(
        ReplayLineageBinding(target_id, identity)
        for target_id in plan.supporting_outcome_ids
        for identity in plan.work_snapshot.logical_identities_for(
            snapshot_outcomes[target_id]
        )
    )
    injected_replay = SiteWorkAttempt(
        attempt_id="caller-injected-replay",
        lineage_id="run-1",
        site_id="site-a",
        step=1,
        start_ns=200,
        planned_end_ns=300,
        planned_work=100.0,
        work_unit="FLOP",
        kind=WorkAttemptKind.REPLAY,
        recovery_plan_id="recovery-1",
        supersedes_attempt_ids=plan.supporting_outcome_ids,
        replay_bindings=replay_bindings,
        evidence=_evidence("evidence:caller-injected-replay"),
    )
    with pytest.raises(ValueError, match="scheduled by the recovery runtime"):
        runtime.submit_attempt(injected_replay)

    restored = runtime.advance_to_decision()
    assert restored.boundaries == (DecisionBoundary.RESTORE_COMPLETION,)
    assert restored.timestamp_ns == 310
    assert restored.site("site-a").state is SiteState.RESTORING
    assert restored.site("site-a").in_flight_attempt_id is not None
    assert restored.effective_membership == ("site-b",)
    assert len(restored.restore_transfers) == 2
    transfer = restored.restore_transfers[0]
    assert all(item.inter_site for item in restored.restore_transfers)
    assert sum(item.attempted_bytes for item in restored.restore_transfers) == 100
    assert sum(item.completed_bytes for item in restored.restore_transfers) == 100
    assert sum(item.lost_bytes for item in restored.restore_transfers) == 0
    assert restored.inter_site_restore_attempted_bytes == 100
    assert restored.inter_site_restore_completed_bytes == 100
    assert restored.inter_site_restore_lost_bytes == 0
    assert restored.work.committed_work == 0.0
    assert restored.work.lost_work == pytest.approx(200.0)
    assert restored.work.as_of_ns == restored.timestamp_ns
    assert all(
        item.disposition is WorkOutcomeDisposition.INVALIDATED_AFTER_COMMIT
        for item in restored.work.outcomes
    )
    assert RuntimeSnapshot.from_json(restored.to_json()) == restored
    forged_transfer = transfer.to_dict()
    forged_transfer["inter_site"] = 1
    with pytest.raises(ValueError, match="inter_site is inconsistent"):
        type(transfer).from_dict(forged_transfer)

    replayed = runtime.advance_to_decision()
    assert replayed.boundaries == (DecisionBoundary.OPERATION_COMPLETION,)
    assert replayed.timestamp_ns == 510
    assert replayed.site("site-a").state is SiteState.HEALTHY_READY
    assert replayed.effective_membership == ("site-a", "site-b")
    assert replayed.work.replayed_work == pytest.approx(200.0)
    assert replayed.work.recomputed_work == pytest.approx(200.0)
    assert replayed.work.committed_work == pytest.approx(200.0)
    assert replayed.work.lost_work == pytest.approx(200.0)
    assert all(
        item.disposition is WorkOutcomeDisposition.SUPERSEDED
        for item in replayed.work.outcomes
        if item.attempt.kind is WorkAttemptKind.FORWARD
    )
    replay_outcome = next(
        item
        for item in replayed.work.outcomes
        if item.attempt.kind is WorkAttemptKind.REPLAY
    )
    assert replay_outcome.attempt.site_id == "site-a"
    assert {
        binding.logical_work.original_site_id
        for binding in replay_outcome.attempt.replay_bindings
    } == {"site-a", "site-b"}

    runtime.schedule_checkpoint(_manifest("checkpoint-1", 520, 1))
    checkpointed_replay = runtime.advance_to_decision()
    assert checkpointed_replay.boundaries == (
        DecisionBoundary.CHECKPOINT_COMMIT,
    )
    assert tuple(
        item.checkpoint_id
        for item in checkpointed_replay.committed_checkpoints
    ) == ("checkpoint-0", "checkpoint-1")


def test_begin_recovery_rejects_a_plan_bound_to_a_different_ledger_digest():
    runtime, recovered = _advance_base_recovery_runtime()
    reference_plan = _plan_current_recovery(runtime, recovered)
    current = runtime.work_ledger
    first = current.outcomes[0]
    forged_first = replace(
        first,
        attempt=replace(
            first.attempt,
            evidence=_evidence("evidence:forged-ledger"),
        ),
    )
    forged_work = WorkLedger((forged_first,) + current.outcomes[1:])
    forged_plan = plan_recovery(
        reference_plan.request,
        runtime.checkpoint_ledger,
        forged_work,
    )

    assert forged_plan.work_ledger_digest != reference_plan.work_ledger_digest
    with pytest.raises(ValueError, match="current as-of work ledger"):
        runtime.begin_recovery(forged_plan)


def test_repeated_failure_during_restore_cancels_stale_restore_completion():
    runtime, recovered = _advance_base_recovery_runtime(
        _failure("failure-2", 250, 300)
    )
    runtime.begin_recovery(_plan_current_recovery(runtime, recovered))

    second_failure = runtime.advance_to_decision()
    assert second_failure.boundaries == (DecisionBoundary.FAILURE_OBSERVED,)
    assert second_failure.timestamp_ns == 250
    assert second_failure.site("site-a").state is SiteState.FAILED
    assert second_failure.site("site-a").active_recovery_id is None
    assert all(item.interrupted for item in second_failure.restore_transfers)
    assert {
        item.interruption_failure_id for item in second_failure.restore_transfers
    } == {"failure-2"}
    assert sum(
        item.attempted_bytes for item in second_failure.restore_transfers
    ) == 40
    assert sum(
        item.completed_bytes for item in second_failure.restore_transfers
    ) == 0
    assert sum(item.lost_bytes for item in second_failure.restore_transfers) == 40
    assert second_failure.inter_site_restore_attempted_bytes == 40
    assert second_failure.inter_site_restore_completed_bytes == 0
    assert second_failure.inter_site_restore_lost_bytes == 40

    second_recovery = runtime.advance_to_decision()
    assert second_recovery.boundaries == (DecisionBoundary.PHYSICAL_RECOVERY,)
    assert second_recovery.timestamp_ns == 300
    assert (
        second_recovery.site("site-a").state
        is SiteState.RECOVERED_UNRESTORED
    )
    assert runtime.advance_to_decision() is None


def test_restore_source_failure_cancels_transfer_and_leaves_target_unrestored():
    runtime, recovered = _advance_base_recovery_runtime(
        _failure("source-failure", 250, 300, site_id="site-b"),
    )
    runtime.begin_recovery(_plan_current_recovery(runtime, recovered))

    source_failure = runtime.advance_to_decision()
    assert source_failure.boundaries == (DecisionBoundary.FAILURE_OBSERVED,)
    assert source_failure.timestamp_ns == 250
    assert source_failure.site("site-b").state is SiteState.FAILED
    assert source_failure.site("site-a").state is SiteState.RECOVERED_UNRESTORED
    assert source_failure.site("site-a").active_recovery_id is None
    assert {
        item.interruption_failure_id for item in source_failure.restore_transfers
    } == {"source-failure"}
    assert sum(
        item.attempted_bytes for item in source_failure.restore_transfers
    ) == 40
    assert sum(
        item.completed_bytes for item in source_failure.restore_transfers
    ) == 0
    assert sum(item.lost_bytes for item in source_failure.restore_transfers) == 40

    source_recovery = runtime.advance_to_decision()
    assert source_recovery.timestamp_ns == 300
    assert runtime.advance_to_decision() is None


def test_failure_during_fixed_restart_records_zero_attempted_transfer_bytes():
    runtime, recovered = _advance_base_recovery_runtime(
        _failure("pre-transfer-failure", 205, 250)
    )
    runtime.begin_recovery(_plan_current_recovery(runtime, recovered))

    failed = runtime.advance_to_decision()
    assert failed.timestamp_ns == 205
    assert {item.transfer_start_ns for item in failed.restore_transfers} == {210}
    assert {item.execution_end_ns for item in failed.restore_transfers} == {205}
    assert sum(item.attempted_bytes for item in failed.restore_transfers) == 0
    assert sum(item.completed_bytes for item in failed.restore_transfers) == 0
    assert sum(item.lost_bytes for item in failed.restore_transfers) == 0


def test_repeated_failure_during_replay_preempts_and_records_replay_loss():
    runtime, recovered = _advance_base_recovery_runtime(
        _failure("failure-2", 350, 450)
    )
    runtime.begin_recovery(_plan_current_recovery(runtime, recovered))
    restored = runtime.advance_to_decision()
    assert restored.boundaries == (DecisionBoundary.RESTORE_COMPLETION,)

    second_failure = runtime.advance_to_decision()
    assert second_failure.boundaries == (DecisionBoundary.FAILURE_OBSERVED,)
    assert second_failure.timestamp_ns == 350
    assert second_failure.site("site-a").state is SiteState.FAILED
    assert second_failure.work.replayed_work == pytest.approx(40.0)
    assert second_failure.work.recomputed_work == 0.0
    assert second_failure.work.lost_work == pytest.approx(240.0)
    replay_loss = next(
        item
        for item in second_failure.work.outcomes
        if item.attempt.kind is WorkAttemptKind.REPLAY
    )
    assert replay_loss.lost_work == pytest.approx(40.0)
    assert replay_loss.disposition is WorkOutcomeDisposition.INTERRUPTED_LOST
    active = next(
        item
        for item in second_failure.observed_failures
        if item.failure_id == "failure-2"
    )
    assert active.status is FailureStatus.ACTIVE
    assert active.recovery_observed_ns is None

    physical = runtime.advance_to_decision()
    assert physical.boundaries == (DecisionBoundary.PHYSICAL_RECOVERY,)
    assert physical.timestamp_ns == 450
    assert physical.site("site-a").state is SiteState.RECOVERED_UNRESTORED
    assert runtime.advance_to_decision() is None


def test_new_failure_precedes_old_physical_recovery_at_the_same_timestamp():
    runtime = _runtime(
        _failure("failure-1", 100, 200),
        _failure("failure-2", 200, 300),
    )
    runtime.advance_to_decision()
    assert runtime.advance_to_decision().boundaries == (
        DecisionBoundary.FAILURE_OBSERVED,
    )

    repeated = runtime.advance_to_decision()
    assert repeated.timestamp_ns == 200
    assert repeated.boundaries == (
        DecisionBoundary.FAILURE_OBSERVED,
        DecisionBoundary.PHYSICAL_RECOVERY,
    )
    assert repeated.site("site-a").state is SiteState.FAILED
    assert repeated.site("site-a").active_failure_ids == ("failure-2",)
    first = next(
        item
        for item in repeated.observed_failures
        if item.failure_id == "failure-1"
    )
    assert first.status is FailureStatus.RECOVERED
    assert first.recovery_observed_ns == 200

    final_recovery = runtime.advance_to_decision()
    assert final_recovery.timestamp_ns == 300
    assert final_recovery.boundaries == (DecisionBoundary.PHYSICAL_RECOVERY,)
    assert final_recovery.site("site-a").state is SiteState.RECOVERED_UNRESTORED
