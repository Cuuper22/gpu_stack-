# Visible Backlog

Updated: 2026-06-10 PDT.

Purpose: compact recovery surface for the visible backlog.

## Latest Verified Wave: Portfolio Form And Deliverable Polish

Status: implemented and verified.

- Docs site three-font typography, Open Graph metadata, backtick-to-`code`
  copy fixes, `app.js` null guards, and eyebrow contrast landed in `docs/`.
- README dependency-cone and `evaluate_targets` examples were fixed and
  re-run successfully.
- Observed gates: full pytest `670 passed in 133.89s`; full verifier
  `4/4 gates passed in 141.07s`; audit PASS with large project files 0.

## Reconciled Wave: Pythia Energy-Floor Cost Closure Plus Aggregate Missing-Family Dedup

Status: partially landed; cost closure remains open.

- The wave's scope-split merges are on main and the suite grew from 639 to
  670 green tests; the audit large-project-file count moved from 7 to 0.
- Live `scenario-audit --json` still reports the Pythia `cost_per_token`
  target with 33 missing inputs, so the energy-floor cost closure stays on
  this backlog instead of being claimed as done.

## Previous Verified Wave: Live Next-Work Compass And Scenario-Audit Missing-Family Ergonomics

Status: implemented, verified, read-only verified, and source-clean.

Facts to keep visible:

- Runtime cap remained six live workers.
- `gpu_stack.next_work` now exposes `build_next_work_plan(...)`,
  `NextWorkPlan`, and `NextWorkItem`.
- `next-work` and `next-work --json` expose a live 3/4/10 continuation
  compass.
- `ScenarioReport.missing_family_summaries` aggregates missing-family evidence
  across targets.
- `scenario-audit --missing-families` prints compact grouped missing-family
  output for text audits.
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
- Current `next-work` evidence: Pythia `cost_per_token` has 33 missing inputs;
  top root-debt family `physical.lithography.medium` has weight 3014 across 15
  roots; metadata gaps remain 65 variable `sp_units`, 169 variable references,
  81 equation references, and 160 equation unit checks.

## Previous Verified Wave: Physical Root-Debt Boundary Hardening

Status: implemented, verified, read-only verified, and source-clean.

Facts to keep visible:

- Runtime capped live workers at six, so the wave used bounded write lanes and
  a pseudo-git coordination ledger (now archived at `archive/AGENT_GITLOG.md`).
- The wave hardened physical roots where honest lower-level relations or
  obvious boundary semantics existed, without adding arbitrary calibration
  values.
- Source changes landed in MOSFET, interconnect, lithography source/species,
  and medium-response surfaces.
- Added/expanded tests for process geometry, SEMF/nuclear coefficients,
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

## Previous Verified Wave: Scenario Audit Selector/Report Ergonomics

Status: implemented, verified, read-only verified, and source-clean.

Facts:

- `SCENARIO_TARGET_SETS` and `scenario_targets_for(...)` centralize advertised
  scenario targets.
- `scenario-audit --preset` selects one or more packs to audit.
- `scenario-audit --target [LABEL=]VARIABLE` overrides advertised targets.
- `ScenarioReport` now includes target-level ok/issues/error counts and label
  tuples.
- `root-debt --json` covers flat and family-grouped root-debt outputs.
- Focused selector/report/root-debt pack: `112 passed in 25.94s`.
- Full pytest: `548 passed in 69.71s`.
- Audit gate: PASS; systems 16, variables 1517, constants 24, equations 954,
  root inputs 619, leaves 253, cycles 0, hard failures 0, large scope files 0,
  large project files 7.
- Full verifier: `4/4 gates passed in 72.95s`.
- Read-only full verifier: `4/4 gates passed in 80.75s`.
- Final source-clean check: `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

## Verified Wave: Scenario Audit CLI

Status: implemented, verified, read-only verified, and source-clean.

Final facts:

- `scenario-audit` CLI covers `scenarios.SOURCED_SCENARIO_PACKS`.
- Text output and `--json` output both exist.
- It evaluates advertised target sets through `Preset.evaluate_targets(...)`.
- `--fail-on-issues` returns nonzero when any sourced scenario target has
  issues.
- Current known issue count is 33 from the Pythia cost-per-token missing
  economics/thermal roots.
- Full pytest: `536 passed in 68.00s`.
- Full verifier: `4/4 gates passed in 70.64s`.
- Read-only full verifier: `4/4 gates passed in 76.89s`.
- Final source-clean check: `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

## Verified Wave: Scenario Artifact

Status: implemented, verified, read-only verified, and source-clean.

Final facts:

- `Preset.evaluate_targets(...)` now returns structured scenario artifacts.
- `ScenarioReport`, `ScenarioTargetReport`, and `MissingFamilySummary` are
  public API surfaces.
- `scenario-report --json` exposes the report through the CLI JSON surface.
- Focused pack: `87 passed in 15.88s`.
- Full pytest: `533 passed in 73.54s`.
- Audit gate: PASS; systems 16, variables 1517, constants 24, equations 954,
  root inputs 619, leaves 253, cycles 0, hard failures 0, large scope files 0,
  large project files 7.
- Full verifier: `4/4 gates passed in 65.34s`.
- Read-only full verifier: `4/4 gates passed in 73.22s`.
- Final source-clean check: `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

## Still Visible Future Work

1. Keep scenario artifacts ergonomic.
   - Keep structured API reports and CLI JSON aligned.
   - Keep `scenario-report`, `resolve`, and `root-debt` missing-family surfaces
     consistent as resolver family buckets evolve.

2. Keep physical root-debt closure honest.
   - Decompose roots only where there is real physics.
   - Otherwise label roots as calibration or operating boundaries.

3. Keep SEMF numeric defaults blocked.
   - No non-public coefficient defaults are published.
   - Blocker remains: verify source, SI conversion, and pairing/reference-energy
     semantics before adding numeric SEMF defaults.

4. Broaden cited scenarios and model coverage.
   - Cited scenario expansion remains open.
   - Broader model expansion remains open.
   - Keep assumptions separate from sourced facts.

5. Keep maintenance debt visible.
   - Metadata/provenance tail remains open.
   - Split large project files only while touching related behavior.
   - Compact docs should stay current after each wave.

## 2026-05-06 22:35 PDT Parent Closeout

- Physical root-debt boundary hardening is integrated and verified.
- Earlier worker coordination notes are superseded by the verified facts above.
- Final handoff state is full-verified, read-only verified, and source-clean.

## 2026-05-06 23:00 PDT Parent Closeout

- Live next-work compass and scenario-audit missing-family ergonomics are
  integrated and verified.
- Earlier worker coordination notes about missing `gpu_stack.next_work` are
  superseded by the verified facts above.
