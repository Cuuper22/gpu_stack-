"""Drive gpu_stack's RecoveryRuntime as a single-site, blocking-checkpoint training job.

The runtime only supplies mechanics.  Every duration (step time, checkpoint write,
restart latency, restore transfer, replay rate) is chosen here and handed to the
engine, exactly as the production runners do.  What is tested downstream is whether
the engine turns those inputs and a failure trace into the right wall clock and the
right work accounting.  It is NOT a test of any performance model.

Driver policy (a plain periodic checkpointer):
  * take a genesis checkpoint at t=0 (1 ns, outside the measured window);
  * run forward steps of `step_ns`; after every `k` steps write a checkpoint
    (training blocks while it writes);
  * when the failed site is physically back, ask plan_recovery / begin_recovery;
    the engine restores, replays lost steps, and hands control back;
  * stop when `n_segments * k` steps are done and the final checkpoint has committed.
Wall time is measured from the genesis commit to the final checkpoint commit.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional, Sequence

from gpu_stack.research.recovery import (
    EvidenceBasis,
    EvidenceBoundary,
    FailureCauseCode,
    FailureInterval,
    FailureStatus,
    FailureTrace,
    LogicalWorkIdentity,
    RecoveryRequest,
    SiteWorkAttempt,
    StepSiteContributionRequirement,
    WorkAttemptKind,
    WorkLedger,
    plan_recovery,
)
from gpu_stack.research.recovery_runtime import (
    CheckpointManifest,
    CheckpointShard,
    DecisionBoundary,
    RecoveryRuntime,
    SiteState,
)

SITE = "worker"
STORE = "ckpt-store"
LINEAGE = "v001"
STATE_BYTES = 1_000_000
NS = 1_000_000_000
GENESIS_NS = 1


def _digest(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


_EV = EvidenceBoundary(
    boundary_id="v001:evidence",
    basis=EvidenceBasis.ASSUMED,
    source_ids=("v001:synthetic",),
    assumptions=("validation harness; durations supplied by the caller",),
)


@dataclass(frozen=True)
class Scenario:
    step_ns: int            # forward time of one step
    k: int                  # steps per checkpoint interval (tau = k * step_ns)
    n_segments: int         # checkpoint intervals to complete
    ckpt_ns: int            # blocking checkpoint write time C
    restart_fixed_ns: int   # fixed restart latency (part of R)
    transfer_ns: int        # restore transfer time (rest of R)
    replay_rate: float = 1.0  # replay speed relative to forward speed (1 = same)

    @property
    def tau_ns(self) -> int:
        return self.k * self.step_ns

    @property
    def restart_ns(self) -> int:
        return self.restart_fixed_ns + self.transfer_ns

    @property
    def segment_ns(self) -> int:
        return self.tau_ns + self.ckpt_ns

    @property
    def total_steps(self) -> int:
        return self.k * self.n_segments

    @property
    def work_per_step(self) -> float:
        return self.step_ns / NS  # work unit: "forward-seconds"; rate 1 unit/s


@dataclass
class EngineRun:
    wall_ns: int
    failures_in_trace: int
    runtime: RecoveryRuntime
    scenario: Scenario
    decisions: int
    genesis_commit_ns: int
    end_ns: int
    recoveries_started: int
    aborted_checkpoints: int
    scheduled: list  # (checkpoint_id, step, write_start_ns, planned_commit_ns)
    final_snapshot: object = None


class TraceTooShort(RuntimeError):
    pass


def _manifest(sc: Scenario, serial: int, step: int, start_ns: int) -> CheckpointManifest:
    cid = f"ckpt:{serial}:step-{step}"
    sv = f"{LINEAGE}:step-{step}"
    shard = f"{cid}:state"
    end = start_ns + (GENESIS_NS if step == 0 else sc.ckpt_ns)
    return CheckpointManifest(
        checkpoint_id=cid, lineage_id=LINEAGE, committed_step=step, state_version=sv,
        model_hash=_digest(sv + "m"), optimizer_hash=_digest(sv + "o"),
        rng_hash=_digest(sv + "r"), data_cursor_hash=_digest(sv + "c"),
        state_bytes=STATE_BYTES, required_shard_ids=(shard,),
        shards=(CheckpointShard(
            shard_id=shard, site_id=STORE, source_state_version=sv,
            storage_location=f"object://{STORE}/{cid}", failure_domain=f"domain:{STORE}",
            state_bytes=STATE_BYTES, checksum=_digest(cid), write_started_at_ns=start_ns,
            write_completed_at_ns=end),),
        site_membership=(SITE,), recovery_source_site_id=STORE,
        checkpoint_write_started_at_ns=start_ns, checkpoint_write_completed_at_ns=end,
        manifest_committed_at_ns=end, evidence=_EV)


def _attempt(sc: Scenario, serial: int, step: int, start_ns: int) -> SiteWorkAttempt:
    return SiteWorkAttempt(
        attempt_id=f"fwd:{serial}:step-{step}", lineage_id=LINEAGE, site_id=SITE, step=step,
        start_ns=start_ns, planned_end_ns=start_ns + sc.step_ns,
        planned_work=sc.work_per_step, work_unit="fwd-s", kind=WorkAttemptKind.FORWARD,
        logical_work=LogicalWorkIdentity(
            logical_work_id=f"{LINEAGE}:{SITE}:step-{step}", lineage_id=LINEAGE,
            logical_step=step, logical_partition=f"partition:{SITE}", original_site_id=SITE,
            state_lineage_hash=_digest(f"{LINEAGE}:in:{step}")),
        evidence=_EV)


def _frontier(work: WorkLedger, limit: int) -> int:
    """Longest prefix 1..f of logical steps with a canonical (still valid) outcome."""
    have = set()
    for outcome in work.canonical_outcomes:
        for ident in work.logical_identities_for(outcome):
            if ident.lineage_id == LINEAGE and ident.original_site_id == SITE:
                have.add(ident.logical_step)
    f = 0
    while f + 1 <= limit and (f + 1) in have:
        f += 1
    return f


def run_engine(sc: Scenario, failures: Sequence[tuple[int, int]], horizon_ns: int) -> EngineRun:
    trace = FailureTrace("v001:trace", tuple(
        FailureInterval(failure_id=f"f{i:06d}", site_id=SITE, failure_start_ns=s, recovery_ns=r,
                        cause=FailureCauseCode.SITE_UNAVAILABLE, evidence=_EV)
        for i, (s, r) in enumerate(failures)))
    rt = RecoveryRuntime(runtime_id="v001", lineage_id=LINEAGE, site_ids=(SITE,),
                         initial_membership=(SITE,), failure_trace=trace)
    snap = rt.advance_to_decision()  # INITIAL
    decisions = 1
    serial = 0
    m0 = _manifest(sc, serial, 0, 0)
    rt.schedule_checkpoint(m0)
    scheduled = [(m0.checkpoint_id, 0, 0, m0.commit_at_ns)]
    pending: Optional[str] = f"ckpt:{serial}:step-0"
    genesis_commit: Optional[int] = None
    attempt_serial = 0
    recoveries = 0
    final_commit: Optional[int] = None

    while True:
        snap = rt.advance_to_decision()
        if snap is None:
            raise RuntimeError("engine ran out of transitions before the job finished")
        decisions += 1
        if snap.timestamp_ns > horizon_ns:
            raise TraceTooShort
        committed_ids = {m.checkpoint_id for m in snap.committed_checkpoints}
        if pending is not None and (pending in snap.aborted_checkpoint_ids or pending in committed_ids):
            pending = None
        if genesis_commit is None and "ckpt:0:step-0" in committed_ids:
            genesis_commit = snap.timestamp_ns

        done = [m for m in snap.committed_checkpoints if m.committed_step == sc.total_steps]
        if done:  # job finished: stop at once, even if a failure lands at the same instant
            final_commit = max(m.commit_at_ns for m in done)
            break
        site = snap.site(SITE)
        if DecisionBoundary.FAILURE_OBSERVED in snap.boundaries:
            continue
        if site.state is SiteState.FAILED or site.state is SiteState.RESTORING:
            continue
        if site.state is SiteState.RECOVERED_UNRESTORED:
            recovered = [o for o in snap.observed_failures
                         if o.site_id == SITE and o.status is FailureStatus.RECOVERED]
            failure = max(recovered, key=lambda o: (o.failure_start_ns, o.failure_id))
            frontier = _frontier(snap.work, sc.total_steps)
            ckpt = rt.checkpoint_ledger.latest_at(failure.failure_start_ns, lineage_id=LINEAGE)
            assert ckpt is not None
            res = ckpt.restore_resource_ids(SITE)
            reqs = tuple(StepSiteContributionRequirement(step=s, site_ids=(SITE,))
                         for s in range(ckpt.step + 1, frontier + 1))
            recoveries += 1
            req = RecoveryRequest(
                recovery_id=f"rec:{recoveries}", lineage_id=LINEAGE, decision_time_ns=snap.timestamp_ns,
                failure=failure, target_site_id=SITE, last_committed_step=frontier,
                restore_bandwidth_bytes_per_second=STATE_BYTES * NS / sc.transfer_ns,
                replay_work_per_second=sc.replay_rate, fixed_restart_latency_ns=sc.restart_fixed_ns,
                unavailable_site_ids=tuple(sorted({o.site_id for o in snap.observed_failures
                                                   if o.status is FailureStatus.ACTIVE})),
                evidence=_EV, failure_observations=snap.observed_failures,
                available_resource_ids=res, required_restore_resource_ids=res,
                step_site_requirements=reqs)
            plan = plan_recovery(req, rt.checkpoint_ledger, snap.work)
            if not plan.can_start:
                raise RuntimeError("recovery blocked in a single-site scenario")
            if plan.transfer_latency_ns != sc.transfer_ns:
                raise RuntimeError(f"transfer latency {plan.transfer_latency_ns} != {sc.transfer_ns}")
            rt.begin_recovery(plan)
            continue
        # HEALTHY_READY
        if rt.effective_membership != (SITE,):
            continue
        frontier = _frontier(snap.work, sc.total_steps)
        latest_ckpt_step = max((m.committed_step for m in rt.committed_manifests), default=-1)
        if frontier == sc.total_steps and latest_ckpt_step == sc.total_steps:
            final_commit = max(m.commit_at_ns for m in rt.committed_manifests
                               if m.committed_step == sc.total_steps)
            break
        if pending is not None:
            continue
        due = frontier > 0 and frontier % sc.k == 0 and latest_ckpt_step < frontier
        if due:
            serial += 1
            mn = _manifest(sc, serial, frontier, snap.timestamp_ns)
            rt.schedule_checkpoint(mn)
            scheduled.append((mn.checkpoint_id, frontier, snap.timestamp_ns, mn.commit_at_ns))
            pending = f"ckpt:{serial}:step-{frontier}"
            continue
        attempt_serial += 1
        rt.submit_attempt(_attempt(sc, attempt_serial, frontier + 1, snap.timestamp_ns))

    assert genesis_commit is not None and final_commit is not None
    return EngineRun(wall_ns=final_commit - genesis_commit, failures_in_trace=len(failures),
                     runtime=rt, scenario=sc, decisions=decisions, genesis_commit_ns=genesis_commit,
                     end_ns=final_commit, recoveries_started=recoveries,
                     aborted_checkpoints=len(snap.aborted_checkpoint_ids), scheduled=scheduled,
                     final_snapshot=snap)
