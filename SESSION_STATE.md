# Session State

Updated: 2026-07-12 PDT.

Read this first after compaction or restart. It is intentionally shorter than
`HANDOFF.md`.

## Strategic Research Reset

The canonical tree is synced to GitHub main at
`5b2b4c7490e9835e63b87197b64918527e5992a2`. The previous local directory was
an interrupted, non-Git May snapshot and is no longer authoritative.

The project now treats the engine, visual medium, and research program as one
loop. Read `RESEARCH.md`, then
`docs/research/frontier-scan-2026-07-12.md`, before selecting work.

- The engine target is a causal, uncertainty-aware virtual AI datacenter.
- The visual target is semantic zoom from a freshman-readable explanation to
  equations, uncertainty, provenance, and raw evidence.
- The research target is a sequence of falsifiable datacenter-scale
  experiments, beginning with adaptive multi-datacenter training.
- Root-debt ranking remains a graph diagnostic. It is no longer the research
  priority function.
- Draft PR #14 remains parked until its physical decomposition improves an
  evaluated prediction, uncertainty, residual explanation, or experiment.
- Post-reset verification: targeted temp-dependent pack `43 passed in 2.98s`;
  read-only full verifier `5/5` gates in `262.03s`.

## Latest Verified Wave: Ten-Step Expansion Integration

Status: implemented and verified on the integrated tree.

- Nine of ten parallel branches merged (N1 cost closure, N3 resolver
  flags, N4 cited packs, N5 metadata tail, N6 uncertainty, N7 cone
  browser, N8 docs-stats gate, N9 CI/packaging, N10 ledger archive);
  the SEMF plus quark-decomposition branch stays a draft PR pending
  test reconciliation.
- First end-to-end real-scenario cost: the assumption-labeled full-TCO
  pack resolves econ.cost.per_token = 3.738e-9 with missing=0 over
  75 trace steps at the EIA 2024 industrial tariff.
- Metadata tail closed: with_sp_units 1493 of 1493, with_references
  1493 of 1493, equations_with_references 959 of 959,
  equations_with_unit_check 893 of 959.
- Scenario-audit reports 99 issues across 8 packs by design: three
  open sourced cost frontiers keep their missing economics roots
  visible while the closure pack resolves 4 of 4.
- Observed gates: full pytest `841 passed in 256.30s`; full verifier
  `5/5 gates passed in 260.02s` (docs-stats is the fifth gate);
  read-only full verifier `5/5 gates passed in 262.07s`; audit PASS;
  docs-stats OK; impeccable detect shows only the known false positive.

## Previous Verified Wave: Portfolio Form And Deliverable Polish

Status: implemented and verified on the current base.

- Scope: docs site typography and metadata, README example accuracy, and
  ledger reconciliation. No registry, scope, preset, or test source changes.
- Docs site: body copy now renders in IBM Plex Sans while Pixelify Sans
  stays on OS chrome and headings; leaked markdown backticks became real
  `code` elements; Open Graph image URL is absolute and `og:url`, `og:type`,
  and `twitter:card` exist; the empty `docs/styles.css` link was removed;
  `app.js` panel renders are null-guarded; eyebrow labels were darkened to
  clear 4.5:1 contrast.
- Design verification: the impeccable static detector reports only one
  finding on `docs/`, a known false positive counting the seven CLI
  `--flag` tokens inside the console code sample as em-dashes. There are
  zero prose em-dashes in `docs/index.html`.
- README: the dependency-cone example no longer sorts `Variable` objects
  directly (it sorts by name), the `evaluate_targets` example uses the real
  variable name `training.tokens_per_sec`, and the root-debt block notes the
  live `top_roots` column. Both fixed snippets were re-run and pass.
- Observed function gates on this base: full pytest `670 passed in 133.89s`;
  full verifier `4/4 gates passed in 141.07s`; audit gate PASS with systems
  16, variables 1517, constants 24, equations 959, root inputs 619,
  leaves 253, cycles 0, hard failures 0, large scope files 0, large project
  files 0; demo OK.

## Reconciliation: Pythia Energy-Floor Wave End State

The previously in-progress wave is reconciled against observed evidence:

- The scope-split merges landed on main (attention, plasma electron state,
  medium components, cluster node, semiconductor, lithography source).
- The suite grew from 639 to 670 collected tests and is green.
- The audit large-project-file count moved from 7 to 0 at the 700-line
  threshold.
- The Pythia cost path is still open: live `scenario-audit --json` reports
  `cost_per_token` with 33 missing inputs, unchanged from the documented
  count. Cost closure remains visible backlog, not a claimed result.

## Previous Verified Wave: Live Next-Work Compass And Scenario-Audit Missing-Family Ergonomics

Status: implemented, verified, read-only verified, and source-clean.

- Runtime cap remained six live workers.
- New public surfaces: `gpu_stack.next_work`, `build_next_work_plan(...)`,
  `NextWorkPlan`, `NextWorkItem`, `next-work`, `next-work --json`,
  `ScenarioReport.missing_family_summaries`, and
  `scenario-audit --missing-families`.
- New/updated coverage: `tests/test_next_work.py`,
  `tests/test_next_work_continuation_contract.py`,
  `tests/test_scenario_audit_text_family_index.py`, CLI `next-work` tests,
  scenario-audit missing-family text tests, and preset aggregate-family tests.
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
  the top root-debt family is `physical.lithography.medium` with weight 3014
  across 15 roots; the metadata tail was closed by the ten-step
  integration wave (100 percent variable units and references, 100 percent
  equation references, 893 of 959 equations unit-checked).

## Current Aim

Build the smallest measured virtual-datacenter substrate that can falsify
Experiment 001:

1. Add observation artifacts and hard calibration/evaluation splits.
2. Establish held-out prediction, uncertainty-coverage, ranking-regret, and
   decision-regret baselines.
3. Add temporal execution, state movement, shared contention, power, thermal,
   grid, and failure semantics.
4. Add interventions and policies without giving them hidden simulator state.
5. Execute adaptive multi-datacenter training against centralized and fixed
   consistency baselines.
6. Render the resulting causal path, counterfactual, residual, and evidence
   through one shareable semantic-zoom interface.

## Previous Verified Wave: Physical Root-Debt Boundary Hardening

Status: implemented, verified, read-only verified, and source-clean.

- The wave hardened high-blast-radius physical primitive boundaries without
  adding arbitrary operating values.
- Source changes landed in MOSFET, interconnect, lithography source/species,
  and medium-response surfaces; process, SEMF/nuclear, plasma-drive,
  medium-intercomponent, root-debt, import, CLI, and index/smoke coverage were
  added around already-existing symbolic constraints.
- Runtime capped live workers at six, so the wave used bounded write lanes and
  a pseudo-git coordination ledger (now archived at `archive/AGENT_GITLOG.md`).
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

Final facts:

- `SCENARIO_TARGET_SETS` and `scenario_targets_for(...)` advertise stable
  target sets for the dense fixture, Pythia DGX H100 scenario pack, and EUV
  tin120 source-context pack.
- `scenario-audit --preset` audits selected packs only.
- `scenario-audit --target [LABEL=]VARIABLE` overrides advertised targets for
  every audited pack.
- `ScenarioReport` now exposes target-level `ok_count`, `issues_count`,
  `error_count`, and stable target-label tuples.
- `root-debt --json` emits deterministic JSON for flat and `--families` modes.
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

- `scenario-audit` CLI over `scenarios.SOURCED_SCENARIO_PACKS`.
- Text output and `--json` output both exist.
- Advertised target sets are evaluated through `Preset.evaluate_targets(...)`.
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

New surfaces:

- `Preset.evaluate_targets(...)` returns structured scenario reports.
- `ScenarioReport`
- `ScenarioTargetReport`
- `MissingFamilySummary`
- `scenario-report --json` is implemented.

## Verified Snapshot

- Systems: 16
- Variables: 1517
- Constants: 24
- Equations: 959
- Root inputs: 619
- Leaves: 253
- Cycles: 0
- Hard failures: 0
- Large scope files: 0
- Large project files: 0

## Verification

- Full pytest: 670 passed in 157.12s.
- Audit gate: PASS; systems 16, variables 1517, constants 24, equations 959,
  root inputs 619, leaves 253, cycles 0, hard failures 0, large scope files 0,
  large project files 0.
- Full verifier: 4/4 gates passed in 157.32s.
- Read-only full verifier: 4/4 gates passed in 157.18s.
- Impeccable static detector on `docs/`: one known false positive only
  (CLI `--flag` tokens counted as em-dashes); `single-font` resolved.
- Final source-clean check:
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0 ruff_cache_dirs=0`.

## Remaining Visible Backlog

- SEMF numeric defaults remain blocked by source plus pairing/reference-energy
  semantics.
- Cited scenario expansion remains open.
- Broader model expansion remains open.

## Verification Loop

Use this after worker integration:

```bash
python -m pytest -q
python -m gpu_stack.cli verify --profile full
python -B -m gpu_stack.cli verify --profile full --read-only
```

Then delete generated cache artifacts and confirm:

```text
cache_dirs=0 pyc_files=0 pytest_cache_dirs=0
```

## 2026-05-06 22:35 PDT Parent Closeout

- Physical root-debt boundary hardening is integrated and verified.
- Earlier worker coordination notes are superseded by the verified facts above.
- Final handoff state is full-verified, read-only verified, and source-clean.

## 2026-05-06 23:00 PDT Parent Closeout

- Live next-work compass and scenario-audit missing-family ergonomics are
  integrated and verified.
- Earlier worker coordination notes about missing `gpu_stack.next_work` are
  superseded by the verified facts above.
