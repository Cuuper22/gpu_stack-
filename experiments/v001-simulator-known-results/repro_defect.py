"""Standalone repro of the RecoveryRuntime.begin_recovery defect found by study V001.

Run:  PYTHONPATH=<repo root> python -B repro_defect.py

One site, forward steps of 250 s, a checkpoint every 4 steps (10 s write), restart 10 s.
Failure A at t=600 s, failure B at t=B_TIME.  Prints whether the run completes.
Then it shows the ledger-level cause directly.
"""
from __future__ import annotations

import hashlib
import sys

from gpu_stack.research.recovery import (
    EvidenceBasis, EvidenceBoundary, FailureCauseCode, FailureInterval, FailureStatus, FailureTrace,
    LogicalWorkIdentity, RecoveryRequest, SiteWorkAttempt, StepSiteContributionRequirement,
    WorkAttemptKind, plan_recovery,
)
from gpu_stack.research.recovery_runtime import (
    CheckpointManifest, CheckpointShard, RecoveryRuntime, SiteState,
)

S = 10 ** 9
STEP, K, NSEG, CK, RESTART_FIX, XFER = 250 * S, 4, 3, 10 * S, 5 * S, 5 * S
BYTES = 1_000_000
EV = EvidenceBoundary("e", EvidenceBasis.ASSUMED, ("s",), ("repro",))
dg = lambda x: "sha256:" + hashlib.sha256(x.encode()).hexdigest()  # noqa: E731


def manifest(i, step, start, dur):
    sv, sh = f"v{step}", f"c{i}:s"
    end = start + dur
    return CheckpointManifest(
        f"c{i}", "L", step, sv, dg("m"), dg("o"), dg("r"), dg("c"), BYTES, (sh,),
        (CheckpointShard(sh, "store", sv, "obj://x", "d", BYTES, dg(sh), start, end),),
        ("w",), "store", start, end, end, EV)


def attempt(n, step, start):
    return SiteWorkAttempt(
        f"a{n}", "L", "w", step, start, start + STEP, 250.0, "u", WorkAttemptKind.FORWARD,
        logical_work=LogicalWorkIdentity(f"L:w:{step}", "L", step, "p", "w", dg(f"in{step}")), evidence=EV)


def frontier(work):
    have = {i.logical_step for o in work.canonical_outcomes for i in work.logical_identities_for(o)}
    f = 0
    while f + 1 in have and f < K * NSEG:
        f += 1
    return f


def run(fail_times_s):
    tr = FailureTrace("t", tuple(FailureInterval(f"f{i}", "w", t * S, t * S + S, FailureCauseCode.SITE_UNAVAILABLE, EV)
                                 for i, t in enumerate(fail_times_s)))
    rt = RecoveryRuntime(runtime_id="r", lineage_id="L", site_ids=("w",), initial_membership=("w",), failure_trace=tr)
    rt.advance_to_decision()
    rt.schedule_checkpoint(manifest(0, 0, 0, 1))
    n = c = rec = 0
    pending = True
    while True:
        snap = rt.advance_to_decision()
        if any(m.committed_step == K * NSEG for m in snap.committed_checkpoints):
            return rt, snap.timestamp_ns / S
        if pending and ({"c%d" % (c)} & ({m.checkpoint_id for m in snap.committed_checkpoints} | set(snap.aborted_checkpoint_ids))):
            pending = False
        st = snap.site("w").state
        if st in (SiteState.FAILED, SiteState.RESTORING):
            continue
        fr = frontier(snap.work)
        if st is SiteState.RECOVERED_UNRESTORED:
            fail = max((o for o in snap.observed_failures if o.status is FailureStatus.RECOVERED),
                       key=lambda o: (o.failure_start_ns, o.failure_id))
            ck = rt.checkpoint_ledger.latest_at(fail.failure_start_ns, lineage_id="L")
            res = ck.restore_resource_ids("w")
            rec += 1
            req = RecoveryRequest(
                f"rec{rec}", "L", snap.timestamp_ns, fail, "w", fr, BYTES * S / XFER, 1.0, RESTART_FIX, (), EV,
                failure_observations=snap.observed_failures, available_resource_ids=res, required_restore_resource_ids=res,
                step_site_requirements=tuple(StepSiteContributionRequirement(s, ("w",)) for s in range(ck.step + 1, fr + 1)))
            rt.begin_recovery(plan_recovery(req, rt.checkpoint_ledger, snap.work))   # <-- raises in the failing case
            continue
        if pending:
            continue
        last = max(m.committed_step for m in rt.committed_manifests)
        if fr > 0 and fr % K == 0 and last < fr:
            c += 1
            rt.schedule_checkpoint(manifest(c, fr, snap.timestamp_ns, CK))
            pending = True
            continue
        n += 1
        rt.submit_attempt(attempt(n, fr + 1, snap.timestamp_ns))


if __name__ == "__main__":
    for label, fl in (("A=600s only", [600]), ("A=600s, B=700s (B during replay)", [600, 700]),
                      ("A=600s, B=2100s (B after next checkpoint)", [600, 2100]),
                      ("A=600s, B=1300s (B after replay, before checkpoint)", [600, 1300])):
        try:
            _, t = run(fl)
            print(f"{label:55s} completes, wall {t:.0f} s")
        except ValueError as exc:
            print(f"{label:55s} RAISES ValueError: {exc}")
    # ledger-level cause: replay outcome committed, then invalidated again
    rt, _ = run([600])
    led = rt.work_ledger
    replay = [o for o in led.outcomes if o.attempt.kind is WorkAttemptKind.REPLAY][0]
    sup = [o for o in led.outcomes if o.superseded_by_attempt_id == replay.attempt.attempt_id]
    print(f"\nafter failure A: replay outcome {replay.attempt.attempt_id} is {replay.disposition.value}; "
          f"{len(sup)} original attempts are SUPERSEDED by it")
    try:
        led.invalidate_outcomes([replay.attempt.attempt_id], recovery_id="rec-B", effective_at_ns=int(2000 * S))
    except ValueError as exc:
        print("invalidating the replay outcome (what a second recovery does) ->", exc)
        sys.exit(0)
