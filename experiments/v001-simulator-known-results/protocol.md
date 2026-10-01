# V001: does the simulator reproduce known results?

Status: STAGE 1 (protocol and code only). Results are written to `results/` in stage 2.

## Question
The virtual-datacenter simulator in `gpu_stack/research/` has never been checked against
anything with a known answer. Does it reproduce (1) the textbook checkpoint/restart result
(Young 1974, Daly 2006), (2) basic work and time accounting, (3) queueing theory
(M/M/1, M/M/c, M/D/1, M/G/1, Little's law), and (4) the failure rate published for Llama 3?

## What is and is not tested
The simulator takes every duration from the caller. So this study tests **event mechanics**:
given durations and a failure trace, are the clock, the restart/replay logic, the ledger and
the resource scheduler right? It does **not** test any performance model (how long a real
checkpoint takes, how fast a GPU is). A pass says "the bookkeeping is right", not "the
predictions are right".

## Computed
Code: `run.py` (runner), `check_ckpt.py`, `check_queue.py`, `ckpt_driver.py` (drives
`RecoveryRuntime`), `ref_sim.py` (independent reference, no gpu_stack code), `analytic.py`.
Times are integer nanoseconds. Failures are drawn by the harness, not the simulator.

**1. Checkpoint/restart.** One site, blocking checkpoints, failures at Poisson rate 1/M while
the site is up (optional repair downtime D). Segment = tau of compute + delta (= C) of
checkpoint. Closed form (Daly 2006 Eq. 9 per segment; with D, my derivation in `analytic.py`):
`E[T_seg] = (M + D) exp(R/M) (exp((tau+C)/M) - 1)`; wasted fraction `1 - tau/E[T_seg]`.
- 1a. Engine mean wall time vs closed form. 9 regimes (C/M from 0.001 to 2, R = C, R ~ 0,
  R = 10C, D = 2C), 5 to 12 intervals each (grid of tau/tau_exact plus Young, Daly 1st and
  2nd order). Driver mode "atomic segment" (one step = tau + C, 1 ns commit), see Known defect.
  The reference simulator is run on the same traces and against the closed form at the same
  precision, so a formula or harness error shows up there rather than being blamed on the engine.
- 1b. Differential test: real blocking checkpoints, k in {1,2,3,5,8} steps per interval, 15
  configurations, 300 traces each. Engine wall time must equal the reference to the nanosecond.
- 1c. Simulated argmin of wasted fraction vs the exact optimum (plateau test).
- 1d. Excess waste of Young / Daly intervals over the optimum, measured vs analytic.
**2. Accounting** (`account()`): 3,840 runs of random (Poisson, bursts) and boundary-adversarial
traces (failures within 1 ns of step ends, commits, restore ends), k in {1,2,3,5}, replay rate
in {1, 2, 0.5}. Identities: A1 attempted = committed + lost; A2 attempted work recomputed
independently from the failure list; A3 finished job holds each logical step exactly once;
A4 forward and replay seconds equal work over rate; A5 wall clock is tiled exactly (no gap, no
overlap) by compute, replay, checkpoint, restore and downtime intervals; A7 restore bytes;
A8 no checkpoint commits across a failure; A9 no completed attempt overlaps downtime; A10 replay
duration = work / rate. Metamorphic: failure after job end changes nothing; failure list order
changes nothing; scaling all times by 7 scales wall by 7; reruns are identical.
**3. Queueing.** c servers = one `Resource` of capacity c, customers = events with demand 1,
arrival = `earliest_start_ns`, service = `duration_ns`. 10 scenarios, 2,000 replications each.
M/M/c starts in the exact stationary state (no warm-up bias); M/D/1 and M/H2/1 delete a
warm-up. Compared: mean wait vs Erlang C or Pollaczek-Khinchine, P(wait>0) vs Erlang C,
every start time vs an exact FCFS recursion, the same stream through `VirtualDatacenter` on a
WAN link, Little's law, snapshot consistency, and a priority-queue probe.
**4. Published failure rate (descriptive).** Llama 3: MTBF = 54 d / 419 unexpected
interruptions = 11,135 s (10,012 s counting all 466). Engine effective-time ratio at assumed
C = R of 30 to 300 s and at the closed-form C that gives exactly 90%.

## Published numbers used (read from the papers' text)
- Dubey et al. 2024, arXiv:2407.21783v3, Sec. 3.3.4: "54-day snapshot", 466 interruptions,
  47 planned, 419 unexpected; "higher than 90% effective training time", defined as "the time
  spent on useful training over the elapsed time". Sec. 3.3.1: "up to 16K H100 GPUs".
  The paper gives no checkpoint cost or interval, so C and R are my assumptions.
- Zhang et al. 2022, arXiv:2205.01068, Sec. 2.5: "at least 35 manual restarts", "over 100
  hosts" cycled "over the course of 2 months", "70+ automatic restarts" (their estimate);
  Sec. 2.4: 992 80GB A100 GPUs. No checkpoint cost or effective-time ratio, so **dropped**.
  The Meta logbook was not read; nothing from it is used.

## Decision criteria (thresholds in `run.py` CRITERIA; verdicts in `results/verdict.json`)
Tolerances come from Monte Carlo error and exact-arithmetic facts, not from tuning.
- **z limit 3.5.** About 100 z-tests in the family; two-sided p = 4.7e-4 each gives a
  family-wise false-alarm rate near 5%.
- **C1a (engine and reference vs closed form).** Every cell |z| <= 3.5; chi-square of the z's
  p >= 0.001 (guards against understated SE); inverse-variance pooled relative bias with
  95% CI inside +-1%. If pooled SE > 0.5% the verdict is "inconclusive", not pass. The closed
  form is exact; integer-ns rounding is ~1e-9 relative, so any real bias is a mechanics bug.
  The engine must also equal the reference on every shared trace.
- **C1b-differential.** 0 mismatches on completed traces (both sides are integers; a
  nonzero difference is a bug, no statistics involved).
- **C1b-completion.** The engine must complete every legal failure trace (0 exceptions).
  Expected to FAIL (Known defect). **C1b-root-cause.** Every exception has the signature below
  and is predicted by the reference's rule; no predicted trace completes.
- **C1c.** Plateau = grid points whose simulated waste is within 2 SE of the simulated
  minimum. The exact optimum must lie in the plateau hull, one grid step of slack. The waste
  curve is flat near its minimum (about (x-1)^2/2 in relative tau), so MC cannot resolve
  tau to better than the plateau. Young and exact optimum differ by 1.5% (C/M=0.001), 4.9%
  (0.01), 16.7% (0.1); the corresponding waste differences are below 1e-4, 1.3e-4, 2.6e-3
  (`python analytic.py`). **No criterion claims the engine can separate Young from the exact
  optimum when C/M <= 0.01.**
- **C1d.** Measured excess waste of tau_Young, tau_Daly1, tau_Daly2 over the x=1 cell equals
  the analytic excess, |z| <= 3.5. Known accuracy of the formulas (relative error of tau vs
  exact, `analytic.py`): Young +1.5/+4.9/+16.7/+43/+68% at C/M = 0.001/0.01/0.1/0.5/1;
  Daly first order -0.8/-2.5/-9.4/-28/-51%; Daly higher order ~0/-0.001/-0.04/-0.55/-1.8%.
  Regimes C/M >= 0.5 and 2 (beyond Daly's "delta < 2M" branch) are tested on purpose.
- **C2.** 0 violations of A1 to A10, 0 wall-clock differences from the reference, 0 metamorphic
  changes, on every run that completes. Exceptions are counted under C1b, not here.
- **C3a.** 0 start-time differences from the FCFS recursion, in the timeline and in
  `VirtualDatacenter` (both integers).
- **C3b.** Mean wait and P(wait>0): |z| <= 3.5 and relative SE <= 3% (otherwise the scenario
  is inconclusive, not pass). 2,000 replications per scenario is planned to give about 1%.
- **C3c.** Little's law identities and in-service averages to 1e-9 relative (float round-off
  is ~1e-15; any logic error is >= 1e-3); snapshots never exceed capacity, active counts match
  records. These are consistency identities on one trace, not independent validation.
- **C3d.** Descriptive: whether priority classes work.
- **C4.** Descriptive. The only pass test: engine = closed form at these parameters, |z| <= 3.5.
  It cannot confirm or refute the paper's 90%: no checkpoint cost is published, and the
  paper's ratio also includes 47 planned interruptions and startup time.

## What each outcome means
All C1a, C1b-differential, C2, C3 pass: the event mechanics reproduce theory in the regimes
tested. Any failure localises to the named check. A C1a pass with C1b-completion failing means
the numbers are right wherever the engine runs, and it does not run everywhere.

## Known defect (found while building the harness, before any frozen criterion)
`RecoveryRuntime.begin_recovery` raises `ValueError: superseded work must point to its
committed replay outcome` when a failure arrives after a recovery's replay has finished and
before the next checkpoint commits. Minimal repro (`check_ckpt.minimal_repro()`): 1 site, step
250 s, 4 steps per checkpoint, checkpoint 10 s, restart 10 s; failures at t = 600 s and
t = 1300 s. Failures at 600 s and 700 s, or 600 s and 2100 s, complete. Cause (read from
`recovery.py` `WorkLedger.__post_init__` and `invalidate_outcomes`): the second recovery
invalidates the first replay outcome, but the original attempts still point to it as
superseded and the ledger rule rejects that state. The shipped E001 runner has one failure
per run, so it never reaches this path. Check 1a therefore uses the atomic-segment driver
(no replay possible); check 1b uses the real path and counts the exceptions.

## Compute
About 45 to 70 minutes on 4 cores (per-failure engine cost measured ~7 ms; 96 cells at
10,000 failures each dominate). Smoke mode (`--mode smoke`) takes ~30 s.

## Known limitations
- One site, exponential failures, constant costs. The multi-site and WAN logic, power and
  cooling resources, and the policies are not tested here.
- Replay rate other than 1 is covered by identities only (the reference assumes rate 1).
- The queue tests use open-loop arrivals fixed in advance; the substrate has no feedback.
- Engine cost grows with failures per run, so regimes with C/M >= 1 have low precision
  (SE 5 to 15%); they test gross errors only.
- Closed form for D > 0 is my derivation; the reference Monte Carlo is its check.

## Disclosure
While developing I ran tiny smoke tests and saw: engine = reference to the ns on 356 traces
and 124 exceptions all predicted by the rule (k in {1,2,4,7}); the defect above; a 30-replication
M/M/2 mean wait (0.90 vs 0.96 theory); and smoke-mode verdicts on a few dozen traces. None
of these is a frozen-criterion result (different seeds and sizes). I did not run any full
cell.
