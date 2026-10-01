"""Check 3: can the temporal substrate act as a queue, and does it match queueing theory?

Mapping.  A server pool of c identical servers is one `Resource` of capacity c * r.  A
customer is a `TemporalEvent` with demand r (one server), `earliest_start_ns` = arrival time
and `duration_ns` = service time.  The scheduler gives the event the earliest start at which
the demand fits, so wait = start - arrival.  Arrival times and service times are drawn by
this harness (the substrate has no random numbers of its own).
"""

from __future__ import annotations

import heapq
import math
from typing import Sequence

import numpy as np
from scipy import stats as sps

from gpu_stack.research.temporal import (
    EventKind, EventTimeline, Resource, ResourceDemand, TemporalEvent,
)
from gpu_stack.research.multisite import Site, VirtualDatacenter, WANLink

S = 1_000_000_000
RES = "pool"


# ---------------------------- theory -------------------------------------------------

def erlang_c(c: int, a: float) -> float:
    """P(wait > 0) for M/M/c with offered load a = lambda/mu < c."""
    rho = a / c
    s = sum(a ** k / math.factorial(k) for k in range(c))
    top = a ** c / math.factorial(c) / (1 - rho)
    return top / (s + top)


def mmc_wq(c: int, lam: float, mu: float) -> float:
    return erlang_c(c, lam / mu) / (c * mu - lam)


def mg1_wq(lam: float, es: float, es2: float) -> float:
    """Pollaczek-Khinchine mean wait in queue."""
    rho = lam * es
    return lam * es2 / (2 * (1 - rho))


def mmc_stationary_n(c: int, a: float, rng: np.random.Generator) -> int:
    rho = a / c
    p = [a ** n / math.factorial(n) for n in range(c)]
    tail = a ** c / math.factorial(c)
    # P(N = c + j) = tail * rho^j
    z = sum(p) + tail / (1 - rho)
    u = rng.random() * z
    for n in range(c):
        if u < p[n]:
            return n
        u -= p[n]
    # geometric tail: P(j) proportional to rho^j
    j = int(math.floor(math.log(1 - rng.random()) / math.log(rho)))
    return c + j


# ---------------------------- exact FCFS oracle ---------------------------------------

def fcfs_starts(arr: Sequence[int], svc: Sequence[int], c: int) -> list[int]:
    """Start times of an FCFS c-server queue (arrivals in the given order)."""
    free = [0] * c
    heapq.heapify(free)
    out = []
    for a, s in zip(arr, svc):
        f = heapq.heappop(free)
        st = max(a, f)
        out.append(st)
        heapq.heappush(free, st + s)
    return out


# ---------------------------- substrate runner ----------------------------------------

class _NoSnapshots(EventTimeline):
    """Same scheduler, snapshot construction skipped (it is O(n^2) and not needed for
    waits).  A full run is compared against this on small inputs to show the event
    records are identical."""

    def _build_snapshots(self, records):  # type: ignore[override]
        return ()


def build_events(arr: Sequence[int], svc: Sequence[int], prefix: str = "j") -> list[TemporalEvent]:
    return [TemporalEvent.create(f"{prefix}{i:07d}", EventKind.COMPUTE, a, s,
                                 demands=[ResourceDemand(RES, 1)])
            for i, (a, s) in enumerate(zip(arr, svc))]


def substrate_starts(arr: Sequence[int], svc: Sequence[int], c: int, full: bool = False):
    cls = EventTimeline if full else _NoSnapshots
    tl = cls([Resource(RES, c, "servers")])
    tl.schedule_all(build_events(arr, svc))
    res = tl.run()
    by_id = {r.event.event_id: r for r in res.trace.events}
    starts = [by_id[f"j{i:07d}"].start_ns for i in range(len(arr))]
    return starts, res


def datacenter_starts(arr: Sequence[int], svc: Sequence[int], c: int) -> list[int]:
    """Same queue through VirtualDatacenter: a WAN link of c * r bytes/s, each transfer
    demanding r = 1e9 bytes/s and `svc` bytes (so duration = svc ns, zero latency)."""
    r = 10 ** 9
    big = 10 ** 6 * r
    mk = lambda sid: Site(sid, "x", 1, 1.0, big, big, big, 0.0, 1.0, 1.0, 1.0, 1.0)  # noqa: E731
    dc = VirtualDatacenter([mk("a"), mk("b")], [WANLink("l", "a", "b", c * r, 0)])
    for i, (a, s) in enumerate(zip(arr, svc)):
        dc.schedule_state_transfer(f"t{i:06d}", f"st{i}", "a", "b", s, link_id="l",
                                   bandwidth_bytes_per_second=r, earliest_start_ns=a)
    res = dc.run()
    by = {rec.event.event_id: rec for rec in res.trace.timeline.events}
    return [by[f"t{i:06d}"].start_ns for i in range(len(arr))], res


# ---------------------------- stream generation ---------------------------------------

def make_stream(rng: np.random.Generator, c: int, rho: float, n: int, service: str,
                stationary_start: bool, mu_ns: float = 1.0 * S):
    lam = rho * c / mu_ns                       # arrivals per ns
    gaps = rng.exponential(1.0 / lam, size=n)
    arr = np.ceil(np.cumsum(gaps)).astype(np.int64)
    if service == "exp":
        svc = np.ceil(rng.exponential(mu_ns, size=n)).astype(np.int64)
    elif service == "det":
        svc = np.full(n, int(mu_ns), dtype=np.int64)
    elif service == "h2":   # hyper-exponential, mean mu_ns, SCV ~ 4.0
        p = 0.1127
        m1, m2 = mu_ns * 0.2, mu_ns * 4.0
        # choose so mean = mu_ns; check: p*m2+(1-p)*m1 ~ 0.4508+0.1775 ~ 0.63 -> rescale
        mean = p * m2 + (1 - p) * m1
        pick = rng.random(n) < p
        svc = np.ceil(np.where(pick, rng.exponential(m2, n), rng.exponential(m1, n)) * (mu_ns / mean)).astype(np.int64)
    else:
        raise ValueError(service)
    svc = np.maximum(svc, 1)
    init_arr: list[int] = []
    init_svc: list[int] = []
    if stationary_start:
        n0 = mmc_stationary_n(c, lam * mu_ns, rng)
        init_arr = [0] * n0
        init_svc = [max(1, int(math.ceil(x))) for x in rng.exponential(mu_ns, size=n0)]
    return lam, init_arr, init_svc, arr.tolist(), svc.tolist()


def run_rep(rng, c, rho, n, service, stationary_start, warm=0):
    lam, ia, isv, arr, svc = make_stream(rng, c, rho, n, service, stationary_start)
    all_arr = ia + arr
    all_svc = isv + svc
    # sort by arrival (stable) as the substrate does; ids encode this order
    order = np.argsort(np.asarray(all_arr), kind="stable")
    A = [all_arr[i] for i in order]
    Sv = [all_svc[i] for i in order]
    starts, _ = substrate_starts(A, Sv, c)
    oracle = fcfs_starts(A, Sv, c)
    mism = sum(1 for x, y in zip(starts, oracle) if x != y)
    n0 = len(ia)
    # customers counted: the n Poisson arrivals (after t = 0)
    idx = [j for j, i in enumerate(order) if i >= n0][warm:]
    waits = np.array([starts[j] - A[j] for j in idx], dtype=float) / S
    return waits, mism, lam, A, Sv, starts


def little_checks(A, Sv, starts, c) -> dict:
    """Little's law on the queue (exact identity on one finished trace) and on the
    servers (time-average busy servers = sum of service / horizon)."""
    n = len(A)
    ends = [s + v for s, v in zip(starts, Sv)]
    T = max(ends) - min(A)
    sojourn = sum(e - a for e, a in zip(ends, A))
    wait = sum(s - a for s, a in zip(starts, A))
    lam_hat = n / T
    return {"L_system_time_avg": sojourn / T, "lam_hat_times_W": lam_hat * sojourn / n,
            "Lq_time_avg": wait / T, "lam_hat_times_Wq": lam_hat * wait / n}


def snapshot_consistency(A, Sv, starts, c, res) -> dict:
    """Check the substrate's own snapshots: capacity never exceeded, active counts agree
    with the event records, time-average in service equals lambda_hat * mean service."""
    bad_cap = 0
    bad_active = 0
    area = 0.0
    snaps = res.snapshots
    ends = [s + v for s, v in zip(starts, Sv)]
    for i, sn in enumerate(snaps):
        u = sn.resource(RES)
        if u.used > u.capacity + 1e-9:
            bad_cap += 1
        t = sn.timestamp_ns
        act = sum(1 for s, e in zip(starts, ends) if s <= t < e)
        if act != len(sn.active_event_ids) or abs(u.used - act) > 1e-9:
            bad_active += 1
        if i + 1 < len(snaps):
            area += u.used * (snaps[i + 1].timestamp_ns - t)
    T = res.end_ns - res.start_ns
    return {"n_snapshots": len(snaps), "capacity_violations": bad_cap, "active_mismatches": bad_active,
            "avg_in_service": area / T, "expected_avg_in_service": sum(Sv) / T}


# ---------------------------- priority (expressibility) --------------------------------

def priority_probe() -> dict:
    """Two customers, one server.  A low-priority job arrives first and runs; while it runs
    a second low-priority job and then a HIGH-priority job arrive.  In a priority queue the
    high-priority job would be served before the waiting low-priority one."""
    low1 = TemporalEvent.create("a-low1", EventKind.COMPUTE, 0, 100, demands=[ResourceDemand(RES, 1)], priority=5)
    low2 = TemporalEvent.create("b-low2", EventKind.COMPUTE, 10, 100, demands=[ResourceDemand(RES, 1)], priority=5)
    high = TemporalEvent.create("c-high", EventKind.COMPUTE, 20, 100, demands=[ResourceDemand(RES, 1)], priority=-5)
    tl = EventTimeline([Resource(RES, 1, "servers")])
    tl.schedule_all([low1, low2, high])
    res = tl.run()
    st = {r.event.event_id: r.start_ns for r in res.trace.events}
    return {"starts_ns": st, "high_priority_served_before_waiting_low": st["c-high"] < st["b-low2"]}
