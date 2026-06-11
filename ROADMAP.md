# gpu_stack roadmap

Status timestamp: June 10, 2026, America/Los_Angeles.

## Latest Verified Wave

Portfolio form-and-deliverable polish is implemented, verified, and
source-clean. The wave was landed as PR #5 and merged to main.

- Scope: docs site typography and metadata, README example accuracy, and
  historical agent-session memory consolidation under `archive/`.
- Docs site: three-font system (IBM Plex Sans for body copy, Pixelify Sans for
  OS chrome and headings, IBM Plex Mono for commands); absolute Open Graph
  metadata (`og:image`, `og:url`, `og:type`, `twitter:card`); leaked markdown
  backticks became real `code` elements; dead `docs/styles.css` link and file
  removed; `app.js` panel renders null-guarded; eyebrow labels darkened to
  clear 4.5:1 contrast.
- README example fixes: dependency-cone snippet sorts by name instead of
  comparing `Variable` objects directly; `evaluate_targets` example uses real
  variable name `training.tokens_per_sec`; root-debt block notes live
  `top_roots` column.
- Session memory files moved to `archive/` for provenance without root clutter.
- Full pytest: `670 passed in 157.12s`.
- Audit gate: PASS; systems 16, variables 1517, constants 24, equations 959,
  root inputs 619, leaves 253, cycles 0, hard failures 0, large scope files 0,
  large project files 0.
- Full verifier: `4/4 gates passed in 157.32s`.
- Read-only full verifier: `4/4 gates passed in 157.18s`.
- Final source-clean check:
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0 ruff_cache_dirs=0`.
- Current `next-work` evidence (live 2026-06-10):
  Pythia `cost_per_token` has 33 missing inputs; top root-debt family is
  `physical.lithography.medium` with weight 3014 across 15 roots; metadata
  gaps were closed by the ten-step integration wave: every non-constant
  variable now has `sp_units` and references, every equation has references,
  and 893 of 959 equations carry unit checks.

## Previous Verified Wave

Live next-work compass and scenario-audit missing-family ergonomics are
implemented, verified, read-only verified, and source-clean.

- Runtime cap remained six live workers.
- New surfaces: `gpu_stack.next_work`, `build_next_work_plan(...)`,
  `NextWorkPlan`, `NextWorkItem`, `next-work`, `next-work --json`,
  `ScenarioReport.missing_family_summaries`, and
  `scenario-audit --missing-families`.
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

## Previously Verified Wave

Physical root-debt boundary hardening is implemented, verified, read-only
verified, and source-clean.

- Runtime capped live workers at six; bounded write lanes were tracked through
  a pseudo-git coordination ledger (now archived at `archive/AGENT_GITLOG.md`).
- MOSFET, interconnect, lithography source/species, and medium-response source
  surfaces gained boundary hardening.
- Process geometry, SEMF/nuclear coefficients, source-plasma drive, medium
  intercomponent, root-debt, import, CLI, and boundary index/smoke-pack
  coverage were added or expanded.
- Focused parent pack: `125 passed in 33.75s`.
- Full pytest: `628 passed in 71.99s`.
- Audit gate: PASS; systems 16, variables 1517, constants 24, equations 959,
  root inputs 619, leaves 253, cycles 0, hard failures 0, large scope files 0,
  large project files 7.
- Full verifier: `4/4 gates passed in 73.38s`.
- Read-only full verifier: `4/4 gates passed in 75.17s`.
- Final source-clean check:
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0 ruff_cache_dirs=0`.

## Previously Verified Wave

Scenario-audit selector/report ergonomics are implemented and verified.

Implemented surfaces:

- `SCENARIO_TARGET_SETS` and `scenario_targets_for(...)` advertise stable
  scenario targets.
- `scenario-audit --preset` selects packs; `scenario-audit --target` overrides
  advertised targets.
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

## Recently Verified History

Structured scenario artifact wave is implemented and verified.

Implemented surfaces:

- `Preset.evaluate_targets(...)` returns structured scenario artifacts.
- `ScenarioReport`, `ScenarioTargetReport`, and `MissingFamilySummary` are API
  surfaces.
- `scenario-report --json` exposes the structured report as CLI JSON.
- Focused pack: `87 passed in 15.88s`.
- Full pytest: `533 passed in 73.54s`.
- Audit gate: PASS; systems 16, variables 1517, constants 24, equations 954,
  root inputs 619, leaves 253, cycles 0, hard failures 0, large scope files 0,
  large project files 7.
- Full verifier: `4/4 gates passed in 65.34s`.
- Read-only full verifier: `4/4 gates passed in 73.22s`.
- Final source-clean check: `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

The T-AA root/family diagnostics closeout is verified and source-clean:
`167 passed in 15.68s`, full pytest `528 passed in 55.75s`, audit PASS with
16 systems, 1517 variables, 954 equations, 619 roots, full verifier `4/4` in
59.88s, read-only verifier `4/4` in 66.30s, and final cache check
`cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

That wave added `resolve --missing-families`,
`scenario-report --missing-families`, resolver-family buckets, EUV tin120
source context, SEMF factory guardrails without numeric defaults, root-debt
tests, gas/thermal feasibility tests, medium-response propagation coverage,
and preset export/discovery tests.

## Near-Term Priorities

| Priority | Work | Done when |
|---|---|---|
| P0 | Preserve scenario artifact contracts. | API reports and CLI JSON stay deterministic, compact, and covered. |
| P0 | Keep SEMF numeric defaults blocked. | Coefficients stay absent until source, SI conversion, and pairing/reference-energy semantics are verified. |
| P0 | Preserve sourced-scenario provenance. | Public context stays distinct from numeric calibration; assumptions remain labeled. |
| P1 | Expand cited scenarios. | New scenarios land only with explicit source data and semantics. |
| P1 | Expand model coverage. | Add deeper physical decomposition and broader model families without arbitrary defaults. |

## Future Work

Continue broader reality-model expansion: physical decomposition, cited
scenarios, model-family coverage, metadata/provenance cleanup, topology and
site-scale network models, transient thermal/controller behavior,
financing/tariff cases, and user-facing examples.

Prefer recursive model deepening on high-blast-radius roots plus cited
scenarios that prove the layers interact cleanly.
