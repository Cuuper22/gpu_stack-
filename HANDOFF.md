# HANDOFF: gpu_stack active wave

Status timestamp: May 6, 2026, 23:00 America/Los_Angeles.

## Latest Verified Wave

`live next-work compass and scenario-audit missing-family ergonomics` is
implemented, verified, read-only verified, and source-clean. Runtime remained
capped at six live workers.

Implemented facts:

- `gpu_stack.next_work` exposes `build_next_work_plan(...)`, `NextWorkPlan`,
  and `NextWorkItem`.
- `next-work` and `next-work --json` expose the live 3/4/10 continuation
  compass.
- `ScenarioReport.missing_family_summaries` aggregates target missing-family
  evidence.
- `scenario-audit --missing-families` prints compact grouped missing-family
  text output.
- Focused parent pack: `11 passed in 20.82s`.
- Broader CLI/preset/next-work pack: `111 passed in 45.31s`.
- Full pytest: `639 passed in 102.03s`.
- Audit gate: PASS; systems 16, variables 1517, constants 24, equations 959,
  root inputs 619, leaves 253, cycles 0, hard failures 0, large scope files 0,
  large project files 7.
- Full verifier: `4/4 gates passed in 107.69s`.
- Read-only full verifier: `4/4 gates passed in 95.58s`.
- Final source-clean check:
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0 ruff_cache_dirs=0`.

## Resume Instructions

You are resuming after the live next-work compass and scenario-audit
missing-family ergonomics wave was integrated, verified, read-only verified,
and cleaned. Do not revert anyone else's work. For fast resume, read
`SESSION_STATE.md` and `VISIBLE_BACKLOG.md` first.

## Current State

Physical root-debt boundary hardening is now the previous verified handoff.

- Runtime capped live workers at six, so the wave used bounded write lanes and
  `AGENT_GITLOG.md` as a pseudo-git coordination ledger.
- Source changes landed in MOSFET, interconnect, lithography source/species,
  and medium-response surfaces.
- Coverage expanded around process geometry, SEMF/nuclear coefficients,
  source-plasma drive, medium intercomponent, root-debt, import smoke, CLI
  strict-mode smoke, and boundary index/smoke-pack coverage.
- Focused parent pack: `125 passed in 33.75s`.
- Full pytest: `628 passed in 71.99s`.
- Audit gate: PASS; systems 16, variables 1517, constants 24, equations 959,
  root inputs 619, leaves 253, cycles 0, hard failures 0, large scope files 0,
  large project files 7.
- Full verifier: `4/4 gates passed in 73.38s`.
- Read-only full verifier: `4/4 gates passed in 75.17s`.
- Final source-clean check:
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0 ruff_cache_dirs=0`.

## Previous Verified State

Scenario-audit selector/report ergonomics are implemented and verified.

Implemented facts:

- `SCENARIO_TARGET_SETS` and `scenario_targets_for(...)` advertise stable
  scenario targets.
- `scenario-audit --preset` audits selected packs only.
- `scenario-audit --target [LABEL=]VARIABLE` overrides advertised targets.
- `ScenarioReport` exposes target-level ok/issues/error counts and label
  tuples.
- `root-debt --json` covers flat and family-grouped root-debt views.
- Default all-sourced scenario audit still reports 33 known Pythia
  cost-per-token missing-root issues.
- Focused selector/report/root-debt pack: `112 passed in 25.94s`.
- Full pytest: `548 passed in 69.71s`.
- Audit gate: PASS; systems 16, variables 1517, constants 24, equations 954,
  root inputs 619, leaves 253, cycles 0, hard failures 0, large scope files 0,
  large project files 7.
- Full verifier: `4/4 gates passed in 72.95s`.
- Read-only full verifier: `4/4 gates passed in 80.75s`.
- Final source-clean check: `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

## Latest Verified Base

Structured scenario artifact wave is implemented and verified.

Implemented facts:

- `Preset.evaluate_targets(...)` returns structured scenario reports.
- `ScenarioReport`, `ScenarioTargetReport`, and `MissingFamilySummary` are
  implemented API surfaces.
- `scenario-report --json` is implemented as the CLI JSON surface.
- Focused pack: `87 passed in 15.88s`.
- Full pytest: `533 passed in 73.54s`.
- Audit gate: PASS; systems 16, variables 1517, constants 24, equations 954,
  root inputs 619, leaves 253, cycles 0, hard failures 0, large scope files 0,
  large project files 7.
- Full verifier: `4/4 gates passed in 65.34s`.
- Read-only full verifier: `4/4 gates passed in 73.22s`.
- Final source-clean check: `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

## Previous Verified Base

T-AA root/family diagnostics closeout is verified and source-clean:

- Focused integration pack: `167 passed in 15.68s`.
- Full pytest: `528 passed in 55.75s`.
- Audit gate: PASS; systems 16, variables 1517, constants 24, equations 954,
  root inputs 619, leaves 253, cycles 0, hard failures 0, large scope files 0,
  large project files 7.
- Full verifier: `4/4 gates passed in 59.88s`.
- Read-only full verifier: `4/4 gates passed in 66.30s`.
- Final source-clean check: `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

That base includes `resolve --missing-families`,
`scenario-report --missing-families`, resolver-family buckets, EUV tin120
source context, SEMF guardrails without unsourced numeric defaults, root-debt
tests, gas/thermal feasibility tests, medium-response propagation coverage,
and preset export/discovery tests.

## Next Real Work

1. Keep scenario artifact API and CLI JSON output covered and deterministic.
2. Keep SEMF numeric defaults blocked until source, SI conversion, and
   pairing/reference-energy semantics are verified.
3. Continue broader cited scenario expansion and model expansion in later
   waves, keeping assumptions separate from sourced facts.
4. Continue evaluator UX work where it deepens reproducibility, especially
   selector semantics, concise diagnostics, and cited scenario coverage.

## Verification Policy

Run focused tests for touched surfaces and report only exact observed results.
Use the full verifier before handoff after broad graph or scenario changes.

## 2026-05-06 22:35 PDT Parent Closeout

- Physical root-debt boundary hardening is integrated and verified.
- Earlier worker coordination notes are superseded by the verified facts above.
- Final handoff state is full-verified, read-only verified, and source-clean.

## 2026-05-06 23:00 PDT Parent Closeout

- Live next-work compass and scenario-audit missing-family ergonomics are
  integrated and verified.
- Earlier worker coordination notes about missing `gpu_stack.next_work` are
  superseded by the verified facts above.
