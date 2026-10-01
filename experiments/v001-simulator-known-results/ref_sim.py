"""Independent reference for the checkpoint/restart check.

This is deliberately NOT built from gpu_stack code.  It is the textbook segment
renewal process in exact integer nanoseconds, used (a) to confirm the closed form
by Monte Carlo and (b) as a trace-by-trace oracle for the recovery engine: given the
same failure list it must return the same wall time to the nanosecond.

Semantics (same tie rules the engine documents: a completion or checkpoint commit at
the exact failure instant counts as done):
  * a segment needs L = k*step + C ns of uninterrupted time;
  * a failure at f in [t, t+L) discards the segment; the site is down until its
    recovery time r, then a restart of R ns must run uninterrupted, else the next
    failure restarts it; then the segment is redone from its start.
"""

from __future__ import annotations

import bisect
from typing import Sequence

import numpy as np


class TraceTooShort(RuntimeError):
    """The run outlived the generated failure horizon; regenerate with a longer one."""


def gen_failures(rng: np.random.Generator, mtbf_ns: int, down_ns: int, horizon_ns: int,
                 first_ns: int = 2) -> list[tuple[int, int]]:
    """Failures arrive only while up: up-time ~ Exp(mtbf), then down_ns of repair.
    Prefix-stable in the horizon: the same seed with a larger horizon extends the list."""
    out: list[tuple[int, int]] = []
    down = max(1, int(down_ns))
    t = 0
    while True:
        t += max(1, int(np.ceil(rng.exponential(mtbf_ns))))
        t = max(t, first_ns)
        if t > horizon_ns:
            return out
        out.append((t, t + down))
        t += down


def ref_wall_ns(failures: Sequence[tuple[int, int]], horizon_ns: int, n_segments: int,
                segment_ns: int, restart_ns: int, start_ns: int = 1) -> tuple[int, int]:
    """Return (wall_ns measured from start_ns, number of failures that hit the run)."""
    starts = [f[0] for f in failures]
    t = start_ns
    hits = 0
    for _ in range(n_segments):
        need = segment_ns
        while True:
            i = bisect.bisect_left(starts, t)
            nxt = failures[i][0] if i < len(failures) else None
            if nxt is None or nxt >= t + need:
                if t + need > horizon_ns:
                    raise TraceTooShort
                t += need
                break
            hits += 1
            t = failures[i][1]
            need = restart_ns + segment_ns
    return t - start_ns, hits


def ref_detail(failures: Sequence[tuple[int, int]], horizon_ns: int, n_segments: int, k: int,
               step_ns: int, ckpt_ns: int, restart_ns: int, start_ns: int = 1
               ) -> tuple[int | None, bool, int]:
    """Step-level reference (replay rate 1).  Returns (wall_ns or None, crash_predicted, hits).

    Same timing as ref_wall_ns.  In addition it tracks the one state the engine is known to
    mishandle: a failure that arrives after a recovery's replay has completed and before the
    next checkpoint commits.  The engine then tries to invalidate its own committed replay
    outcome and raises ValueError (see protocol.md, "Known engine defect").  The predictor
    returns crash_predicted=True at the first such moment.
    """
    starts = [f[0] for f in failures]

    def nxt(t: int):
        i = bisect.bisect_left(starts, t)
        return failures[i] if i < len(failures) else None

    t = start_ns
    hits = 0
    for _ in range(n_segments):
        restore_pending = False
        jr = 0  # completed forward steps that a recovery must replay
        while True:
            cursor = t
            replay_done = False
            remaining = k
            if restore_pending:
                f = nxt(cursor)
                if f is not None and f[0] < cursor + restart_ns:
                    hits += 1
                    t = f[1]
                    jr = 0
                    continue
                cursor += restart_ns
                if jr > 0:
                    rd = jr * step_ns
                    f = nxt(cursor)
                    if f is not None and f[0] < cursor + rd:
                        hits += 1
                        t = f[1]
                        jr = 0
                        continue
                    cursor += rd
                    replay_done = True
                    remaining = k - jr
            fwd = remaining * step_ns + ckpt_ns
            f = nxt(cursor)
            if f is None or f[0] >= cursor + fwd:
                if cursor + fwd > horizon_ns:
                    raise TraceTooShort
                t = cursor + fwd
                break
            hits += 1
            if replay_done:
                return None, True, hits
            e = f[0] - cursor
            jr = remaining if e >= remaining * step_ns else e // step_ns
            t = f[1]
            restore_pending = True
    return t - start_ns, False, hits
