# V001 result: does the simulator reproduce known results?

Protocol frozen at 38babe18969aee044ba5add624013f51787e5b65 (git HEAD during the run, no
uncommitted changes in scope; recorded in every `results/*.json`). Run: `run.py --mode full
--procs 2`, seed 20261001. Runtimes: ckpt_stat 4,727 s, ckpt_diff 131 s, accounting 62 s,
queue 1,299 s, published 254 s. Raw output: `results/*.json`; verdicts: `results/verdict.json`.

## Verdict per criterion (criterion text from the frozen protocol)

| ID | Result | Key numbers |
|---|---|---|
| C1a engine vs closed form | PASS | 96 cells; max abs z 2.71; chi-square p 0.92; pooled relative bias -0.008% (95% CI -0.033% to +0.016%) |
| C1a reference vs closed form | PASS | identical numbers to the engine row (see next line) |
| C1a engine = reference on same traces | PASS | 0 differences, 0 engine errors in all cells |
| C1b differential (0 mismatches on completed traces) | PASS | 2,960 completed traces, 0 mismatches to the nanosecond |
| C1b completion (0 exceptions) | **FAIL** | 1,540 of 4,500 traces raised (34%); see defect |
| C1b root cause (every exception predicted, no predicted trace completes) | PASS | 1,540 predicted and raised; 0 unpredicted; 0 predicted-but-completed |
| C1c exact optimum inside plateau hull | PASS | all 9 regimes (also without the one-step slack) |
| C1d excess waste of Young/Daly vs analytic, abs z <= 3.5 | PASS | max abs z 2.17 over 27 comparisons |
| C2 accounting | **FAIL as written** | see below; 0 identity violations |
| C3a exact FCFS (timeline and VirtualDatacenter) | PASS | 0 start-time differences in 10 x 2,000 reps and 20 extra runs |
| C3b theory (abs z <= 3.5, rel SE <= 3%) | PASS | max abs z 2.82 (M/M/1 rho 0.9, deviation -3.9%, SE 1.4%); all relative SE 0.3% to 2.2% |
| C3c Little and snapshots | PASS | max relative error 2.3e-16; 0 capacity or active-count violations |
| C3d priority classes (descriptive) | not expressible | high-priority job arriving later was served last (starts 0, 100, 200 ns) |
| C4 Llama 3 (engine = closed form) | PASS | all 5 rows abs z <= 1.4 |

Engine and reference z-scores are identical because the engine equalled the reference on every
trace, so the engine adds no statistical information beyond the reference; the closed form
itself (with the D > 0 variant) is confirmed by the 96-cell reference Monte Carlo.
Median relative SE of a cell 0.22%. Six cells have SE above 5% (C/M = 2 grid and formula
cells 8% to 20%, C/M = 1 Young cell 5.5%), as the protocol warned.

## C2 and the one deviation
C2 as written counts every `*_error` in the metamorphic tests. 24 of 500 "late failure" tests
raised. Cause (reproduced, `posthoc_late_failure.py`): the harness appended a failure at end+5 ns
even when the trace already held a later failure, and `FailureTrace` correctly refused
overlapping intervals. This is a harness bug, not a simulator fault. **Post-hoc re-analysis
(not frozen):** the 47 affected inputs re-run with the extra failure placed after all existing
ones: 47 completed, 0 changed wall time or ledger digest. Everything else in C2: 3,300
completed runs; 0 violations of A1 to A10; 0 wall differences from the reference; 0 changed
results in determinism (500), order (500), scale-by-7 (500) tests. The frozen verdict stays FAIL;
my reading is that the simulator passes every test that was valid. Another 540 runs hit the
defect below and are excluded (counted under C1b).

## Known defect: `begin_recovery` fails after a replay, before the next checkpoint
Reproduce: `PYTHONPATH=. python -B experiments/v001-simulator-known-results/repro_defect.py`
(standalone, builds a one-site runtime; added after the freeze, not part of the frozen code).
Scenario: 250 s steps, checkpoint every 4 steps (10 s write), restart 10 s, failure A at 600 s.

    A=600s only                                          completes
    A=600s, B=700s (B during replay)                     completes
    A=600s, B=2100s (B after next checkpoint)            completes
    A=600s, B=1300s (B after replay, before checkpoint)  ValueError: superseded work must point
                                                         to its committed replay outcome

Mechanism (read from the code): after A the first recovery's replay attempt commits and the two
original attempts become SUPERSEDED, pointing at it. A failure at 1300 s makes the second
`begin_recovery` (`gpu_stack/research/recovery_runtime.py:1517`) call
`WorkLedger.invalidate_outcomes` (`gpu_stack/research/recovery.py:1979`, constructs at :2002), which
turns the replay outcome itself into INVALIDATED_AFTER_COMMIT (`WorkAttemptOutcome.invalidate`,
:1469). The `WorkLedger` constructor then sees SUPERSEDED outcomes whose replacement is no longer
VALID_COMMITTED and raises at `recovery.py:1859` (check at :1850-1861).

Root-cause rule: the engine raises exactly when a failure arrives after a recovery's replay
(positive replay work) has completed and before the next checkpoint commits. 1,540 of 1,540
exceptions matched the rule and no trace matching it completed. Frequency in the differential
test: 0% (k=1, MTBF 10 segments) to 99% (k=8, MTBF 0.5 segments); 3% to 36% at MTBF 2 segments
and k=1 to 8; about 1% to 2% at MTBF 10 segments and k>=2. The shipped E001 runner has one
failure per run, so it never reaches this state.

## Meaning and limits
Where the engine runs, its clock, restart, replay, ledger and scheduler match theory and an
independent reference exactly, across C/M from 0.001 to 2 (the closed form's own approximation
errors are reported in the protocol; this study did not need them to pass). It does not run on
every legal failure sequence. The queueing substrate is exact FCFS with exogenous arrivals; it
cannot express priority classes or feedback. Check 1a used the atomic-segment driver (no replay
path); replay is covered only by 1b and C2. Llama 3 (MTBF 11,135 s from 419 unexpected
interruptions in 54 days, arXiv:2407.21783v3 Sec. 3.3.4): with C = R, 90% effective time needs
C <= 54.4 s (48.9 s if all 466 interruptions count); this consistency bound uses an assumed
cost, not a published one, and neither confirms nor refutes the paper's ">90%".
Not tested: multi-site, WAN policy, power, cooling, any performance model.
