import pytest

from gpu_stack.research.recovery import (
    CheckpointLedger,
    CompletedCheckpoint,
    EvidenceBasis,
    EvidenceBoundary,
    FailureCauseCode,
    FailureInterval,
    FailureObservation,
    FailureStatus,
    FailureTrace,
    LogicalWorkIdentity,
    ReplayLineageBinding,
    RecoveryPlan,
    RecoveryPlanningError,
    RecoveryRequest,
    SiteWorkAttempt,
    StepSiteContributionRequirement,
    WorkAttemptKind,
    WorkAttemptOutcome,
    WorkOutcomeDisposition,
    WorkLedger,
    evaluate_work_attempt,
    plan_recovery,
)


def _evidence(boundary_id: str = "fixture") -> EvidenceBoundary:
    return EvidenceBoundary(
        boundary_id=boundary_id,
        basis=EvidenceBasis.ASSUMED,
        source_ids=(f"source:{boundary_id}",),
        assumptions=("synthetic contract fixture",),
        metadata={"scope": "test-only"},
    )


def _failure(
    failure_id: str = "failure-a",
    *,
    site_id: str = "site-a",
    start_ns: int = 100,
    recovery_ns: int = 200,
) -> FailureInterval:
    return FailureInterval(
        failure_id=failure_id,
        site_id=site_id,
        failure_start_ns=start_ns,
        recovery_ns=recovery_ns,
        cause=FailureCauseCode.SITE_UNAVAILABLE,
        evidence=_evidence(f"evidence:{failure_id}"),
    )


def _attempt(
    attempt_id: str,
    step: int,
    start_ns: int,
    end_ns: int,
    *,
    site_id: str = "site-a",
    kind: WorkAttemptKind = WorkAttemptKind.FORWARD,
    planned_work: float = 100.0,
    supersedes_attempt_ids=(),
    replay_bindings=(),
    recovery_plan_id: str = "recovery-1",
) -> SiteWorkAttempt:
    logical_work = (
        LogicalWorkIdentity(
            logical_work_id=f"logical:run-1:{site_id}:{step}",
            lineage_id="run-1",
            logical_step=step,
            logical_partition=site_id,
            original_site_id=site_id,
            state_lineage_hash=f"sha256:{'e' * 64}",
        )
        if kind is WorkAttemptKind.FORWARD
        else None
    )
    return SiteWorkAttempt(
        attempt_id=attempt_id,
        lineage_id="run-1",
        site_id=site_id,
        step=step,
        start_ns=start_ns,
        planned_end_ns=end_ns,
        planned_work=planned_work,
        work_unit="FLOP",
        kind=kind,
        recovery_plan_id=recovery_plan_id if kind is WorkAttemptKind.REPLAY else None,
        supersedes_attempt_ids=supersedes_attempt_ids,
        logical_work=logical_work,
        replay_bindings=replay_bindings,
        evidence=_evidence(f"evidence:{attempt_id}"),
    )


def _bindings(*outcomes: WorkAttemptOutcome):
    result = []
    for outcome in outcomes:
        identities = (
            (outcome.attempt.logical_work,)
            if outcome.attempt.kind is WorkAttemptKind.FORWARD
            else tuple(
                binding.logical_work for binding in outcome.attempt.replay_bindings
            )
        )
        for identity in identities:
            assert identity is not None
            result.append(
                ReplayLineageBinding(
                    target_attempt_id=outcome.attempt.attempt_id,
                    logical_work=identity,
                )
            )
    return tuple(result)


def _checkpoint(
    checkpoint_id: str,
    step: int,
    completed_at_ns: int,
    *,
    state_bytes: int = 1_000,
    source_site_id: str = "checkpoint-store",
) -> CompletedCheckpoint:
    shard_specs = (
        (
            (
                state_bytes,
                "checkpoint-source-a",
                "checkpoint-store-a",
                "storage-fd-a",
            ),
        )
        if state_bytes == 1
        else (
            (
                state_bytes // 2,
                "checkpoint-source-a",
                "checkpoint-store-a",
                "storage-fd-a",
            ),
            (
                state_bytes - state_bytes // 2,
                "checkpoint-source-b",
                "checkpoint-store-b",
                "storage-fd-b",
            ),
        )
    )
    shard_ids = tuple(
        f"{checkpoint_id}:shard:{index}" for index in range(len(shard_specs))
    )
    write_started_at_ns = max(0, completed_at_ns - 2)
    write_completed_at_ns = max(write_started_at_ns, completed_at_ns - 1)
    state_version = f"state:{step}"
    return CompletedCheckpoint(
        checkpoint_id=checkpoint_id,
        lineage_id="run-1",
        step=step,
        completed_at_ns=completed_at_ns,
        state_bytes=state_bytes,
        source_site_id=source_site_id,
        site_membership=("site-b", "site-a"),
        evidence=_evidence(f"evidence:{checkpoint_id}"),
        metadata={
            "state_version": state_version,
            "model_hash": f"sha256:{'a' * 64}",
            "optimizer_hash": f"sha256:{'b' * 64}",
            "rng_hash": f"sha256:{'c' * 64}",
            "data_cursor_hash": f"sha256:{'d' * 64}",
            "checkpoint_write_started_at_ns": write_started_at_ns,
            "checkpoint_write_completed_at_ns": write_completed_at_ns,
            "manifest_committed_at_ns": completed_at_ns,
            "required_shard_ids": list(shard_ids),
            "shards": [
                {
                    "shard_id": shard_ids[index],
                    "site_id": site_id,
                    "source_state_version": state_version,
                    "storage_location": storage_location,
                    "failure_domain": failure_domain,
                    "state_bytes": shard_bytes,
                    "checksum": f"sha256:{str(index + 1) * 64}",
                    "write_started_at_ns": write_started_at_ns,
                    "write_completed_at_ns": write_completed_at_ns,
                }
                for index, (
                    shard_bytes,
                    site_id,
                    storage_location,
                    failure_domain,
                ) in enumerate(shard_specs)
            ],
        },
    )


def test_failure_visibility_never_reveals_a_future_recovery_timestamp():
    trace = FailureTrace("trace-1", (_failure(start_ns=100, recovery_ns=200),))

    assert trace.visible_at(99) == ()
    active = trace.visible_at(100)[0]
    assert active.status is FailureStatus.ACTIVE
    assert active.recovery_observed_ns is None
    assert "recovery_ns" not in active.to_dict()
    assert active.evidence.source_ids == ()
    assert active.evidence.assumptions == ()
    assert dict(active.evidence.metadata) == {"policy_safe": True}
    assert trace.unavailable_site_ids(150) == ("site-a",)

    recovered = trace.visible_at(200)[0]
    assert recovered.status is FailureStatus.RECOVERED
    assert recovered.recovery_observed_ns == 200
    assert trace.unavailable_site_ids(200) == ()
    assert FailureTrace.from_json(trace.to_json()) == trace
    assert FailureObservation.from_json(active.to_json()) == active


def test_same_site_failure_intervals_must_be_nonoverlapping_and_deterministic():
    with pytest.raises(ValueError, match="must not overlap"):
        FailureTrace(
            "overlap",
            (
                _failure("first", start_ns=10, recovery_ns=30),
                _failure("second", start_ns=20, recovery_ns=40),
            ),
        )

    trace = FailureTrace(
        "ordered",
        (
            _failure("later", start_ns=30, recovery_ns=40),
            _failure("earlier", start_ns=10, recovery_ns=20),
        ),
    )
    assert tuple(item.failure_id for item in trace.intervals) == (
        "earlier",
        "later",
    )
    assert trace.to_json() == FailureTrace.from_json(trace.to_json()).to_json()


def test_interrupted_forward_attempt_commits_nothing_and_accounts_partial_loss():
    trace = FailureTrace(
        "interruptions",
        (_failure(start_ns=40, recovery_ns=80),),
    )
    outcome = evaluate_work_attempt(_attempt("forward", 1, 0, 100), trace)

    assert outcome.interrupted is True
    assert outcome.execution_end_ns == 40
    assert outcome.interruption_failure_id == "failure-a"
    assert outcome.attempted_work == pytest.approx(40.0)
    assert outcome.committed_work == 0.0
    assert outcome.lost_work == pytest.approx(40.0)
    assert outcome.replayed_work == 0.0
    assert outcome.recomputed_work == 0.0
    assert outcome.completed_step is None
    assert WorkAttemptOutcome.from_json(outcome.to_json()) == outcome


def test_attempt_starting_inside_failure_is_preempted_before_work_begins():
    trace = FailureTrace(
        "already-failed",
        (_failure(start_ns=40, recovery_ns=80),),
    )
    outcome = evaluate_work_attempt(_attempt("blocked", 1, 50, 100), trace)
    assert outcome.interrupted is True
    assert outcome.execution_end_ns == 50
    assert outcome.attempted_work == 0.0
    assert outcome.lost_work == 0.0


def test_ledger_keeps_attempted_committed_lost_replayed_and_recomputed_distinct():
    trace = FailureTrace(
        "ledger-trace",
        (_failure(start_ns=40, recovery_ns=80),),
    )
    interrupted = evaluate_work_attempt(_attempt("lost", 1, 0, 100), trace)
    committed = evaluate_work_attempt(
        _attempt("forward-ok", 1, 100, 200, site_id="site-b"),
        trace,
    )
    committed = committed.invalidate("recovery-1", effective_at_ns=200)
    replay = evaluate_work_attempt(
        _attempt(
            "replay-ok",
            1,
            200,
            300,
            site_id="site-b",
            kind=WorkAttemptKind.REPLAY,
            supersedes_attempt_ids=("forward-ok",),
            replay_bindings=_bindings(committed),
        ),
        trace,
    )
    committed = committed.invalidate(
        "recovery-1",
        effective_at_ns=200,
        superseded_by_attempt_id="replay-ok",
        supersession_effective_at_ns=300,
    )
    ledger = WorkLedger((replay, interrupted, committed))

    assert ledger.attempted_work == pytest.approx(240.0)
    assert ledger.committed_work == pytest.approx(100.0)
    assert ledger.lost_work == pytest.approx(140.0)
    assert ledger.replayed_work == pytest.approx(100.0)
    assert ledger.recomputed_work == pytest.approx(100.0)
    assert tuple(item.attempt.attempt_id for item in ledger.outcomes) == (
        "lost",
        "forward-ok",
        "replay-ok",
    )
    assert committed.disposition is WorkOutcomeDisposition.SUPERSEDED
    assert WorkLedger.from_json(ledger.to_json()) == ledger


def test_checkpoint_ledger_exposes_only_completed_state_at_the_decision_cutoff():
    initial = _checkpoint("checkpoint-0", 0, 10)
    later = _checkpoint("checkpoint-5", 5, 50)
    ledger = CheckpointLedger((later, initial))

    assert ledger.latest_at(9, lineage_id="run-1") is None
    assert ledger.latest_at(40, lineage_id="run-1") == initial
    assert ledger.latest_at(50, lineage_id="run-1") == later
    assert initial.site_membership == ("site-a", "site-b")
    assert CheckpointLedger.from_json(ledger.to_json()) == ledger
    assert CompletedCheckpoint.from_json(initial.to_json()) == initial


def test_checkpoint_frontier_is_highest_state_and_ambiguous_frontiers_reject():
    genesis = _checkpoint("checkpoint-0", 0, 10)
    high = _checkpoint("checkpoint-5", 5, 40)
    late_low = _checkpoint("checkpoint-3", 3, 90)
    ledger = CheckpointLedger((late_low, genesis, high))

    assert ledger.latest_at(100, lineage_id="run-1") == high
    with pytest.raises(ValueError, match="state frontiers must be unique"):
        CheckpointLedger(
            (genesis, high, _checkpoint("checkpoint-5-copy", 5, 50))
        )
    with pytest.raises(ValueError, match="step-zero genesis"):
        CheckpointLedger((high,))


def test_completed_checkpoint_requires_a_checksummed_atomic_manifest():
    payload = _checkpoint("checkpoint-1", 1, 10).to_dict()
    del payload["metadata"]["shards"][0]["checksum"]
    with pytest.raises(ValueError, match="checksum"):
        CompletedCheckpoint.from_dict(payload)

    payload = _checkpoint("checkpoint-2", 2, 20).to_dict()
    payload["metadata"]["shards"][0]["state_bytes"] += 1
    with pytest.raises(ValueError, match="sum exactly"):
        CompletedCheckpoint.from_dict(payload)

    payload = _checkpoint("checkpoint-3", 3, 30).to_dict()
    payload["metadata"]["shards"][0]["source_state_version"] = "stale"
    with pytest.raises(ValueError, match="must be synchronized"):
        CompletedCheckpoint.from_dict(payload)


def _recovery_fixture():
    failure = _failure(start_ns=100, recovery_ns=200)
    trace = FailureTrace("recovery-trace", (failure,))
    outcomes = WorkLedger(
        (
            evaluate_work_attempt(_attempt("step-3-a", 3, 30, 40), trace),
            evaluate_work_attempt(
                _attempt("step-3-b", 3, 30, 40, site_id="site-b"), trace
            ),
            evaluate_work_attempt(_attempt("step-4-a", 4, 50, 60), trace),
            evaluate_work_attempt(
                _attempt("step-4-b", 4, 50, 60, site_id="site-b"), trace
            ),
            evaluate_work_attempt(_attempt("step-5-lost", 5, 80, 120), trace),
        )
    )
    checkpoint_2 = _checkpoint("checkpoint-2", 2, 20)
    checkpoints = CheckpointLedger(
        (
            _checkpoint("checkpoint-0", 0, 10),
            checkpoint_2,
            _checkpoint("future-checkpoint-8", 8, 200),
        )
    )
    observation = trace.visible_at(100)[0]
    request = RecoveryRequest(
        recovery_id="recovery-1",
        lineage_id="run-1",
        decision_time_ns=100,
        failure=observation,
        target_site_id="site-b",
        last_committed_step=4,
        restore_bandwidth_bytes_per_second=1_000_000_000.0,
        replay_work_per_second=1_000_000_000.0,
        fixed_restart_latency_ns=50,
        unavailable_site_ids=trace.unavailable_site_ids(100),
        evidence=_evidence("evidence:recovery-request"),
        failure_observations=trace.visible_at(100),
        available_resource_ids=checkpoint_2.restore_resource_ids("site-b")
        + ("recovery-control:run-1",),
        required_restore_resource_ids=("recovery-control:run-1",),
        evidence_gaps=("network and storage contention are not measured",),
    )
    return trace, checkpoints, outcomes, request


def test_recovery_plan_uses_latest_visible_checkpoint_and_full_rollback_accounting():
    _, checkpoints, outcomes, request = _recovery_fixture()
    plan = plan_recovery(request, checkpoints, outcomes)

    assert plan.checkpoint.checkpoint_id == "checkpoint-2"

    assert plan.rollback_steps == 2
    assert plan.resume_step == 5
    assert plan.rollback_committed_work == pytest.approx(400.0)
    assert plan.replay_required_work == pytest.approx(400.0)
    assert plan.pre_recovery_lost_work == pytest.approx(50.0)
    assert plan.supporting_outcome_ids == (
        "step-3-a",
        "step-3-b",
        "step-4-a",
        "step-4-b",
    )
    assert plan.lost_outcome_ids == ("step-5-lost",)
    assert plan.source_site_id == "checkpoint-store"
    assert plan.target_site_id == "site-b"
    assert plan.recovery_bytes == 1_000
    assert plan.transfer_latency_ns == 1_000
    assert plan.replay_latency_ns == 400
    assert plan.recovery_latency_ns == 1_450
    assert plan.can_start is True
    assert plan.scheduled_start_ns == 100
    assert plan.scheduled_completion_ns == 1_550
    assert plan.to_dict()["policy_information_cutoff_ns"] == 100
    assert plan.evidence_boundary_ids == (
        "evidence:failure-a",
        "evidence:checkpoint-2",
        "evidence:recovery-request",
        "evidence:step-3-a",
        "evidence:step-3-b",
        "evidence:step-4-a",
        "evidence:step-4-b",
        "evidence:step-5-lost",
    )
    assert plan.work_snapshot.as_of_ns == 100
    assert plan.work_ledger_digest == plan.work_snapshot.ledger_digest
    assert RecoveryPlan.from_json(plan.to_json()) == plan


def test_recovery_uses_relocated_replay_as_canonical_logical_work():
    trace, checkpoints, outcomes, request = _recovery_fixture()
    by_id = {item.attempt.attempt_id: item for item in outcomes.outcomes}
    early = (
        evaluate_work_attempt(_attempt("step-1-a", 1, 10, 15), trace),
        evaluate_work_attempt(
            _attempt("step-1-b", 1, 10, 15, site_id="site-b"), trace
        ),
    )
    originals = tuple(
        by_id[attempt_id].invalidate(
            "prior-recovery", effective_at_ns=45
        )
        for attempt_id in ("step-3-a", "step-3-b")
    ) + tuple(
        item.invalidate("prior-recovery", effective_at_ns=45) for item in early
    )
    replay = evaluate_work_attempt(
        _attempt(
            "prior-replay",
            99,
            45,
            55,
            site_id="relocated-site",
            kind=WorkAttemptKind.REPLAY,
            planned_work=400.0,
            supersedes_attempt_ids=(
                "step-3-a",
                "step-3-b",
                "step-1-a",
                "step-1-b",
            ),
            replay_bindings=_bindings(*originals),
            recovery_plan_id="prior-recovery",
        ),
        trace,
    )
    superseded = tuple(
        item.invalidate(
            "prior-recovery",
            effective_at_ns=45,
            superseded_by_attempt_id="prior-replay",
            supersession_effective_at_ns=55,
        )
        for item in originals
    )
    replayed_ledger = WorkLedger(
        superseded
        + (replay,)
        + tuple(
            item
            for item in outcomes.outcomes
            if item.attempt.attempt_id not in {"step-3-a", "step-3-b"}
        )
    )

    plan = plan_recovery(request, checkpoints, replayed_ledger)
    assert plan.supporting_outcome_ids == (
        "prior-replay",
        "step-4-a",
        "step-4-b",
    )
    assert plan.rollback_committed_work == 400.0
    assert replay.completed_steps == (1, 3)
    assert replay.attempt.site_id == "relocated-site"


def test_recovery_plan_snapshot_rejects_forged_support_amounts_and_digest():
    _, checkpoints, outcomes, request = _recovery_fixture()
    plan = plan_recovery(request, checkpoints, outcomes)

    forged_support = plan.to_dict()
    forged_support["supporting_outcome_ids"] = ["step-3-a"]
    with pytest.raises(ValueError, match="canonical as-of snapshot"):
        RecoveryPlan.from_dict(forged_support)

    forged_amount = plan.to_dict()
    forged_amount["rollback_committed_work"] = 1.0
    forged_amount["replay_latency_ns"] = 1
    forged_amount["recovery_latency_ns"] = 1_051
    forged_amount["scheduled_completion_ns"] = 1_151
    with pytest.raises(ValueError, match="supporting outcomes"):
        RecoveryPlan.from_dict(forged_amount)

    forged_digest = plan.to_dict()
    forged_digest["work_ledger_digest"] = f"sha256:{'0' * 64}"
    with pytest.raises(ValueError, match="does not match immutable snapshot"):
        RecoveryPlan.from_dict(forged_digest)


def test_recovery_checkpoint_cutoff_is_failure_start_not_later_decision_time():
    trace, checkpoints, outcomes, request = _recovery_fixture()
    post_failure = _checkpoint("post-failure", 4, 110)
    delayed_observation = trace.visible_at(150)
    delayed_request = RecoveryRequest(
        recovery_id="delayed-recovery",
        lineage_id=request.lineage_id,
        decision_time_ns=150,
        failure=delayed_observation[0],
        target_site_id=request.target_site_id,
        last_committed_step=request.last_committed_step,
        restore_bandwidth_bytes_per_second=(
            request.restore_bandwidth_bytes_per_second
        ),
        replay_work_per_second=request.replay_work_per_second,
        fixed_restart_latency_ns=request.fixed_restart_latency_ns,
        unavailable_site_ids=trace.unavailable_site_ids(150),
        evidence=request.evidence,
        failure_observations=delayed_observation,
        available_resource_ids=request.available_resource_ids,
        required_restore_resource_ids=request.required_restore_resource_ids,
    )
    plan = plan_recovery(
        delayed_request,
        CheckpointLedger(checkpoints.checkpoints + (post_failure,)),
        outcomes,
    )

    assert plan.checkpoint.checkpoint_id == "checkpoint-2"
    forged = plan.to_dict()
    forged["checkpoint"] = post_failure.to_dict()
    with pytest.raises(ValueError, match="post-failure checkpoint"):
        RecoveryPlan.from_dict(forged)


def test_restore_resources_block_without_inventing_start_or_completion():
    trace, checkpoints, outcomes, request = _recovery_fixture()
    manifest_resources = checkpoints.latest_at(
        request.failure.failure_start_ns, lineage_id=request.lineage_id
    ).restore_resource_ids(request.target_site_id)
    assert {
        "shard-source:checkpoint-source-a",
        "checkpoint-storage:checkpoint-store-a",
        "failure-domain:storage-fd-a",
        "restore-path:checkpoint-store-a->site-b",
    }.issubset(set(manifest_resources))
    blocked_request = RecoveryRequest(
        recovery_id="resource-blocked",
        lineage_id=request.lineage_id,
        decision_time_ns=request.decision_time_ns,
        failure=request.failure,
        target_site_id=request.target_site_id,
        last_committed_step=request.last_committed_step,
        restore_bandwidth_bytes_per_second=(
            request.restore_bandwidth_bytes_per_second
        ),
        replay_work_per_second=request.replay_work_per_second,
        fixed_restart_latency_ns=request.fixed_restart_latency_ns,
        unavailable_site_ids=request.unavailable_site_ids,
        evidence=request.evidence,
        failure_observations=request.failure_observations,
        available_resource_ids=tuple(
            resource
            for resource in request.available_resource_ids
            if resource != "failure-domain:storage-fd-a"
        ),
        required_restore_resource_ids=request.required_restore_resource_ids,
    )
    plan = plan_recovery(blocked_request, checkpoints, outcomes)

    assert plan.blocking_resource_ids == (
        "failure-domain:storage-fd-a",
    )
    assert plan.can_start is False
    assert plan.scheduled_start_ns is None
    assert plan.scheduled_completion_ns is None


def test_unavailable_manifest_shard_source_blocks_even_when_coordinator_is_up():
    _, checkpoints, outcomes, request = _recovery_fixture()
    shard_failure = _failure(
        "shard-source-failure",
        site_id="checkpoint-source-a",
        start_ns=90,
        recovery_ns=200,
    )
    observations = request.failure_observations + (
        shard_failure.observation_at(100),
    )
    blocked_request = RecoveryRequest(
        **{
            **request.__dict__,
            "failure_observations": observations,
            "unavailable_site_ids": (
                "checkpoint-source-a",
                "site-a",
            ),
        }
    )

    plan = plan_recovery(blocked_request, checkpoints, outcomes)
    assert plan.blocking_site_ids == ("checkpoint-source-a",)
    assert plan.can_start is False


def test_recovery_requires_every_site_and_rejects_unevidenced_membership_shrink():
    _, checkpoints, outcomes, request = _recovery_fixture()
    missing_site = WorkLedger(
        tuple(
            outcome
            for outcome in outcomes.outcomes
            if outcome.attempt.attempt_id != "step-3-b"
        )
    )
    with pytest.raises(RecoveryPlanningError, match="missing=.*site-b"):
        plan_recovery(request, checkpoints, missing_site)

    override = RecoveryRequest(
        **{
            **request.__dict__,
            "step_site_requirements": (
                StepSiteContributionRequirement(3, ("site-a",)),
            ),
        }
    )
    with pytest.raises(RecoveryPlanningError, match="membership transition"):
        plan_recovery(override, checkpoints, missing_site)


def test_active_target_failure_blocks_plan_without_inventing_recovery_time():
    _, checkpoints, outcomes, request = _recovery_fixture()
    blocked_request = RecoveryRequest(
        recovery_id=request.recovery_id,
        lineage_id=request.lineage_id,
        decision_time_ns=request.decision_time_ns,
        failure=request.failure,
        target_site_id="site-a",
        last_committed_step=request.last_committed_step,
        restore_bandwidth_bytes_per_second=(
            request.restore_bandwidth_bytes_per_second
        ),
        replay_work_per_second=request.replay_work_per_second,
        fixed_restart_latency_ns=request.fixed_restart_latency_ns,
        unavailable_site_ids=request.unavailable_site_ids,
        evidence=request.evidence,
        failure_observations=request.failure_observations,
        available_resource_ids=checkpoints.latest_at(
            request.failure.failure_start_ns, lineage_id=request.lineage_id
        ).restore_resource_ids("site-a")
        + ("recovery-control:run-1",),
        required_restore_resource_ids=("recovery-control:run-1",),
        evidence_gaps=request.evidence_gaps,
    )
    plan = plan_recovery(blocked_request, checkpoints, outcomes)

    assert plan.blocking_site_ids == ("site-a",)
    assert plan.can_start is False
    assert plan.scheduled_start_ns is None
    assert plan.scheduled_completion_ns is None
    assert plan.recovery_latency_ns == 1_450
    assert plan.blocking_resource_ids == ()
    assert plan.request.failure.recovery_observed_ns is None


def test_recovery_planning_rejects_missing_checkpoint_or_committed_work_evidence():
    _, checkpoints, outcomes, request = _recovery_fixture()
    with pytest.raises(RecoveryPlanningError, match="no completed checkpoint"):
        plan_recovery(request, CheckpointLedger(()), outcomes)

    incomplete = WorkLedger(
        tuple(
            outcome
            for outcome in outcomes.outcomes
            if outcome.attempt.attempt_id != "step-4-a"
        )
    )
    with pytest.raises(RecoveryPlanningError, match="incomplete or ambiguous"):
        plan_recovery(request, checkpoints, incomplete)


def test_recovery_request_rejects_unobserved_unavailable_sites():
    trace, _, _, request = _recovery_fixture()
    with pytest.raises(ValueError, match="observable active failures"):
        RecoveryRequest(
            **{
                **request.__dict__,
                "unavailable_site_ids": ("future-site", "site-a"),
                "failure_observations": trace.visible_at(100),
            }
        )


def test_logical_duplicates_and_scale_relative_conservation_slack_reject():
    trace = FailureTrace("clean", ())
    first = evaluate_work_attempt(_attempt("duplicate-a", 1, 0, 10), trace)
    second = evaluate_work_attempt(_attempt("duplicate-b", 1, 10, 20), trace)
    with pytest.raises(ValueError, match="multiple canonical outcomes"):
        WorkLedger((first, second))

    large = _attempt(
        "large",
        1,
        0,
        10,
        planned_work=1_000_000_000_000_000.0,
    )
    with pytest.raises(ValueError, match="committed plus lost"):
        WorkAttemptOutcome(
            attempt=large,
            execution_end_ns=10,
            interrupted=False,
            interruption_failure_id=None,
            attempted_work=large.planned_work,
            committed_work=large.planned_work - 1.0,
            lost_work=0.0,
            replayed_work=0.0,
            recomputed_work=0.0,
        )

    tiny = _attempt("tiny", 2, 20, 30, planned_work=1e-15)
    with pytest.raises(ValueError, match="cannot exceed planned_work"):
        WorkAttemptOutcome(
            attempt=tiny,
            execution_end_ns=30,
            interrupted=False,
            interruption_failure_id=None,
            attempted_work=1e-12,
            committed_work=1e-12,
            lost_work=0.0,
            replayed_work=0.0,
            recomputed_work=0.0,
        )


def test_work_ledger_rejects_nonfinite_aggregate_accounting():
    trace = FailureTrace("clean", ())
    first = evaluate_work_attempt(
        _attempt("huge-a", 1, 0, 10, planned_work=1e308), trace
    )
    second = evaluate_work_attempt(
        _attempt(
            "huge-b",
            1,
            0,
            10,
            site_id="site-b",
            planned_work=1e308,
        ),
        trace,
    )
    with pytest.raises(ValueError, match="aggregate accounting must be finite"):
        WorkLedger((first, second))


def test_failed_aggregate_replay_can_be_retargeted_without_double_counting():
    original = evaluate_work_attempt(
        _attempt("original", 1, 0, 100, site_id="site-b"),
        FailureTrace("clean", ()),
    ).invalidate("recovery-1", effective_at_ns=110)
    failed_replay = evaluate_work_attempt(
        _attempt(
            "replay-1",
            1,
            110,
            210,
            site_id="site-b",
            kind=WorkAttemptKind.REPLAY,
            supersedes_attempt_ids=("original",),
            replay_bindings=_bindings(original),
        ),
        FailureTrace(
            "retry",
            (_failure("replay-failure", site_id="site-b", start_ns=160),),
        ),
    )
    failed = WorkLedger((original, failed_replay))
    successful_replay = evaluate_work_attempt(
        _attempt(
            "replay-2",
            99,
            210,
            310,
            site_id="relocated-site",
            kind=WorkAttemptKind.REPLAY,
            supersedes_attempt_ids=("original",),
            replay_bindings=_bindings(original),
        ),
        FailureTrace("clean-2", ()),
    )
    superseded_original = original.invalidate(
        "recovery-1",
        effective_at_ns=110,
        superseded_by_attempt_id="replay-2",
        supersession_effective_at_ns=310,
    )
    ledger = WorkLedger(
        (superseded_original, failed_replay, successful_replay)
    )

    assert ledger.attempted_work == pytest.approx(250.0)
    assert ledger.committed_work == pytest.approx(100.0)
    assert ledger.lost_work == pytest.approx(150.0)
    assert ledger.replayed_work == pytest.approx(150.0)
    assert ledger.recomputed_work == pytest.approx(100.0)
    assert ledger.to_dict()["accounting"]["committed_work"] == 100.0
    assert ledger.snapshot_at(100).outcomes[0].disposition is (
        WorkOutcomeDisposition.VALID_COMMITTED
    )
    invalidated = ledger.snapshot_at(120).outcomes[0]
    assert invalidated.disposition is WorkOutcomeDisposition.INVALIDATED_AFTER_COMMIT
    assert invalidated.superseded_by_attempt_id is None
    assert ledger.snapshot_at(310).canonical_outcomes == (successful_replay,)
    assert successful_replay.completed_step == 1


def test_replay_binding_and_recovery_lineage_must_match_original_logical_work():
    original = evaluate_work_attempt(
        _attempt("bound-original", 1, 0, 100, site_id="site-a"),
        FailureTrace("clean", ()),
    ).invalidate("recovery-1", effective_at_ns=110)
    identity = original.attempt.logical_work
    assert identity is not None
    forged_identity = LogicalWorkIdentity(
        logical_work_id="forged-logical-work",
        lineage_id=identity.lineage_id,
        logical_step=2,
        logical_partition=identity.logical_partition,
        original_site_id=identity.original_site_id,
        state_lineage_hash=identity.state_lineage_hash,
    )
    forged_replay = evaluate_work_attempt(
        _attempt(
            "forged-replay",
            99,
            110,
            210,
            site_id="relocated-site",
            kind=WorkAttemptKind.REPLAY,
            supersedes_attempt_ids=("bound-original",),
            replay_bindings=(
                ReplayLineageBinding("bound-original", forged_identity),
            ),
        ),
        FailureTrace(
            "interrupt-forged",
            (_failure("stop-forged", site_id="relocated-site", start_ns=160),),
        ),
    )
    with pytest.raises(ValueError, match="exactly match target logical lineage"):
        WorkLedger((original, forged_replay))

    wrong_recovery = evaluate_work_attempt(
        _attempt(
            "wrong-recovery",
            99,
            110,
            210,
            site_id="relocated-site",
            kind=WorkAttemptKind.REPLAY,
            supersedes_attempt_ids=("bound-original",),
            replay_bindings=_bindings(original),
            recovery_plan_id="another-recovery",
        ),
        FailureTrace(
            "interrupt-wrong",
            (_failure("stop-wrong", site_id="relocated-site", start_ns=160),),
        ),
    )
    with pytest.raises(ValueError, match="must match recovery_plan_id"):
        WorkLedger((original, wrong_recovery))


def test_site_attempt_json_round_trip_and_array_shape_validation():
    attempt = _attempt("round-trip", 1, 0, 10)
    assert SiteWorkAttempt.from_json(attempt.to_json()) == attempt

    malformed = attempt.to_dict()
    malformed["supersedes_attempt_ids"] = "not-an-array"
    with pytest.raises(TypeError, match="JSON array"):
        SiteWorkAttempt.from_dict(malformed)


def test_derived_json_claims_reject_bool_as_numeric_or_boolean_spoofs():
    interval_payload = _failure(start_ns=10, recovery_ns=11).to_dict()
    interval_payload["duration_ns"] = True
    with pytest.raises(ValueError, match="duration_ns is inconsistent"):
        FailureInterval.from_dict(interval_payload)

    attempt = _attempt("one-ns", 1, 0, 1, planned_work=1.0)
    attempt_payload = attempt.to_dict()
    attempt_payload["planned_duration_ns"] = True
    with pytest.raises(ValueError, match="planned_duration_ns is inconsistent"):
        SiteWorkAttempt.from_dict(attempt_payload)

    outcome = evaluate_work_attempt(attempt, FailureTrace("clean", ()))
    outcome_payload = outcome.to_dict()
    outcome_payload["completed_step"] = True
    with pytest.raises(ValueError, match="completed_step is inconsistent"):
        WorkAttemptOutcome.from_dict(outcome_payload)

    ledger_payload = WorkLedger((outcome,)).to_dict()
    ledger_payload["accounting"]["attempted_work"] = True
    with pytest.raises(ValueError, match="attempted_work is inconsistent"):
        WorkLedger.from_dict(ledger_payload)

    _, checkpoints, outcomes, request = _recovery_fixture()
    plan_payload = plan_recovery(request, checkpoints, outcomes).to_dict()
    plan_payload["can_start"] = 1
    with pytest.raises(ValueError, match="can_start is inconsistent"):
        RecoveryPlan.from_dict(plan_payload)


def test_recovery_contracts_reject_bool_nonfinite_and_hidden_future_data():
    evidence = _evidence()
    with pytest.raises(TypeError, match="failure_start_ns must be an integer"):
        FailureInterval(
            "bad",
            "site-a",
            True,
            10,
            FailureCauseCode.UNKNOWN,
            evidence,
        )
    with pytest.raises(ValueError, match="planned_work must be finite"):
        SiteWorkAttempt(
            "bad-work",
            "run-1",
            "site-a",
            1,
            0,
            10,
            float("nan"),
            "FLOP",
            WorkAttemptKind.FORWARD,
            evidence,
            logical_work=LogicalWorkIdentity(
                "logical:bad-work",
                "run-1",
                1,
                "site-a",
                "site-a",
                f"sha256:{'e' * 64}",
            ),
        )
    with pytest.raises(ValueError, match="must not reveal future recovery"):
        FailureObservation(
            "failure",
            "site-a",
            10,
            10,
            FailureStatus.ACTIVE,
            FailureCauseCode.UNKNOWN,
            evidence,
            recovery_observed_ns=20,
        )

    active = _failure(start_ns=10, recovery_ns=20).observation_at(10)
    assert active is not None
    with pytest.raises(TypeError, match="real number"):
        RecoveryRequest(
            "recovery",
            "run-1",
            10,
            active,
            "site-b",
            0,
            True,
            1.0,
            0,
            ("site-a",),
            evidence,
            required_restore_resource_ids=("resource:test",),
        )
    with pytest.raises(ValueError, match="non-finite"):
        EvidenceBoundary(
            "bad-metadata",
            EvidenceBasis.ASSUMED,
            metadata={"bad": float("inf")},
        )
    with pytest.raises(ValueError, match="FailureCauseCode"):
        FailureObservation(
            "failure",
            "site-a",
            10,
            10,
            FailureStatus.ACTIVE,
            "free-form future channel",
            evidence,
        )
