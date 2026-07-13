# Session State

Updated: 2026-07-12 PDT.

Read this first after compaction or restart. It is intentionally shorter than
`HANDOFF.md`.

## Strategic Research Reset

The canonical branch is `main`. The July research-substrate wave was built
from the synchronized GitHub base and is closed only after local `HEAD` and
`origin/main` are proven equal. Do not recover from the interrupted, non-Git
May snapshot.

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
- Merge verification for the research-substrate wave: focused research/docs
  pack `28 passed in 11.83s`; read-only full verifier `5/5` gates in `320.32s`
  with a 600-second gate ceiling after the default 300-second ceiling stopped
  a still-green pytest stream at 97 percent.

## Active Wave: E002-PW2 Valid Result To E002-PW3

Status: PW2 executed on `research/e002-checkpoint-power`; end-of-feature
verification, merge, and push remain pending. Package metadata is 0.27.0.

- PW1 remains preserved as `measurement_invalid`; its raw ratios remain
  inadmissible.
- PW2 completed 32/32 cumulative-energy runs with exact warm binding,
  `measurement_valid=True`, and no active invalidators. Artifact:
  `cfbca215878629bc416f169e5ded80684151d9b2a621548c7fef08207c41f8ee`.
- Effective counter period was 91.667 ms; held-out arms contained 83 to 109
  updates. Snapshot support was 59.30 sparse / 110.06 dense; pooled checkpoint-
  group support was 124.56 / 176.94.
- Total interaction was `2.2416e-5 [2.1746e-6, 3.5305e-5] J/token`;
  checkpoint group was `5.8845e-6 [3.0774e-6, 8.9671e-6]`; snapshot was
  `4.9917e-6 [2.8497e-6, 7.4481e-6]`. All 3 mechanism gates passed.
- Idle-subtracted sensitivity was
  `3.9825e-6 [-8.0109e-6, 1.2479e-5] J/token` and crossed zero. The frozen
  raw-cumulative primary passes; baseline-insensitive attribution remains open.
- Sparse continuation passed all 8 gates: NLL upper `0.0085037`, median work
  saving 3.03%, 40 opportunity ticks saved, and energy-ratio upper `1.00319`.
  Conclusion: `checkpoint_cadence_attributed_sparse_continuation_survives`.
- Current `next-work` is E002-PW3 multi-GPU/rack dependency-safe dephasing with
  simultaneous per-GPU cumulative, rack-PDU, storage, and cooling telemetry.
  Rare restore/rejoin phases remain exploratory; facility transfer is unproven.

## Prior Completed Wave: Recovery-Backed E001 Mechanics

`E001-RECOVERY-V2` compared synchronous wait/restore, fixed-local restart,
adaptive recovery, and a future-trace oracle on one matched failure clock. All
policies reached durable frontier 8 and conserved work. Synchronous recorded
1.584 s, 15.2 GB, 114.64 PFLOP lost, and 0.274 MJ; fixed-local 1.516 s,
10.4 GB, 144.50 PFLOP, and 0.283 MJ; adaptive 1.536 s, 13.6 GB, 48.43 PFLOP,
and 0.255 MJ; oracle 1.536 s, 13.6 GB, 57.00 PFLOP, and 0.257 MJ. That prior
wave remains the mechanical Pareto result and is not overwritten by LC1.

The recovery result hash is
`b1200f99487afe9c690fa723b45a9be764e40f63d8ff4a1e897154e630b29b57`;
its observatory hash is
`2b3c33bac5a0e9e9009b758be54078ac8b4aa9ae4baf343145a81d7e0a6afb05`.

## Latest Verified Wave: Research Substrate, E001 Mechanics, And Observatory

Status: implemented, browser-inspected, and merge-verified.

- Immutable observations, calibration/evaluation splits, residual and
  interval evaluation, Kendall tau-b ranking, decision regret, replicated
  benchmark aggregation, temporal shared-resource events, multi-site
  interventions, and observable-only policy boundaries are implemented.
- Protocol schema v2 freezes scalar falsifiers and mandatory structured
  evidence requirements. E001 through E006 are machine-readable before
  execution; missing mandatory evidence makes a run inconclusive.
- E001 now produces content-addressed full-trace and observatory artifacts.
  The persisted mechanics screen compares synchronous, fixed-local, and
  adaptive-cadence policies over the same compute, checkpoint, and site
  scenario.
- Observed mechanics: synchronous uses 33.6 TB of collective-payload link
  traffic and
  6,047.01 s; fixed-local uses 4.2 TB and 1,341.98 s; adaptive cadence uses
  1.68 TB and 938.60 s. These are virtual mechanics, not held-out learning
  results, and the 5 percent ratio is not complete inter-site traffic.
- The hypothesis policy remains `inconclusive`: held-out progress per FLOP,
  time to target, reactive outage membership, complete energy, and all seven
  structured E001 evidence gates remain unresolved.
- The causal observatory is artifact-driven and shareable. Freshman,
  Researcher, and Full trace depths preserve the same values and conclusion;
  the full view exposes 1,395 event records. Desktop and 390 by 844 mobile
  flows were inspected in the in-app browser.
- Human inspection caught and fixed two product defects before merge: Share
  state lacked visible copy feedback, and the mobile seed-observation table
  widened the root canvas. The page now stays at horizontal offset zero while
  the datacenter rail remains independently pannable.
- Artifact binding: result
  `fa26aeb9dca512356f496502e0bcf5c2ea88ea4f2e2737a122bcafd64543f562`;
  engine source
  `bfabd89583050b518c718f0ca7034eb6994bab20476d434e71a873ac8f97e1b7`;
  scenario
  `532fad5cf7698cc9f7f81090519f020374f43f059a4c0d67d59acd65d26b9e0d`.

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

1. Run E002-PW3 across simultaneous GPUs and rack-visible checkpoint activity.
2. Test dependency-safe dephasing against paired undephased baselines while
   preserving exact learning and work semantics.
3. Align per-GPU cumulative energy with rack-PDU power, storage traffic/power,
   and cooling telemetry.
4. Preserve PW1 as measurement-invalid and PW2 as valid local evidence. Do not
   claim facility transfer, grid safety, or admission gains from PW2.

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
