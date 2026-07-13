# gpu_stack roadmap

Status timestamp: July 12, 2026, America/Los_Angeles.

## Research Reset: The Virtual Datacenter

The project now optimizes one closed loop:

`world model -> prediction -> visual explanation -> hypothesis -> experiment -> observation -> improved world model`

The June engine is a strong symbolic foundation. Its live `next-work` ranking
now follows the measured E001 sequence; root-debt closure and graph
completeness remain diagnostic evidence, not the research roadmap. Recent work such as Charon
already reports operator-level training and inference simulation below 5.35%
overall timing error. `gpu_stack` will not compete by becoming another static
performance simulator with more equations.

The research target is a causal, uncertainty-aware virtual datacenter that
couples learning dynamics, temporal execution, failures, facility power, grid
constraints, economics, and understandable intervention traces. See
`RESEARCH.md` and `docs/research/frontier-scan-2026-07-12.md`.

The first frontier program asks whether a frontier model can train across
heterogeneous, intermittently powered datacenters without surrendering the
learning efficiency of a tightly synchronized cluster. The second asks whether
software-controlled phase shaping can suppress harmful power oscillations and
admit more useful compute inside a fixed facility envelope.

Verification after the research reset: the temp-dependent CLI/docs pack passed
`43 passed in 2.98s`; the read-only full verifier passed `5/5` gates in
`262.03s`, including the complete pytest, syntax, audit, demo, and docs-stats
gates.

## Virtual Datacenter Foundation: Implemented

The first research substrate is no longer roadmap prose:

- observations, calibration/evaluation splits, residual metrics, stratified
  coverage, Kendall tau-b ranking, decision regret, and repeated benchmark
  aggregation are implemented;
- temporal and multi-site shared-resource mechanics, observable-only policies,
  and E001 execution are implemented;
- protocol schema v2 and the E001 to E006 structured evidence catalog are
  implemented;
- E001 persists full-trace and observatory artifacts and is visually inspectable
  at three semantic depths;
- the recovery mechanics screen remains a prior Pareto result, while E001-LC1
  now adds 40 measured small-model GPU runs and a held-out falsification of the
  survivor-continuation candidate under its frozen finite-horizon objective.

Merge verification: focused research/docs pack `28 passed in 11.83s` and
read-only full verifier `5/5` in `320.32s` with a 600-second gate ceiling.

## Recovery-Backed E001 Vertical Slice: Executed

The feature branch now carries one complete research path: scenario input,
transition-driven failure/recovery execution, four matched policies, a
content-addressed result, and a three-depth observatory projection. All four
runs reach durable frontier 8 and conserve attempted, retained, and lost work.

On this deterministic trace, adaptive recovery beats synchronous wait and
restore by 48 ms and 1.6 GB while losing 66.21 PFLOP less work. Fixed-local
restart is 20 ms faster and moves 3.2 GB fewer bytes than adaptive, but loses
96.07 PFLOP more work and uses 0.028 MJ more modeled energy. The oracle ties
adaptive on time and traffic and loses more work. The mechanics therefore
produce a Pareto split, not a validated controller hierarchy.

The observatory renders the same result at Freshman, Researcher, and Full trace
depth, including the shared failure clock, restore/replay intervals, exact work
accounting, disjoint byte classes, recovery debt, assumptions, uncertainty, and
missing evidence. Browser inspection of all three depths is complete.

## E001-LC1 Measured Learning Calibration: Completed

E001-LC1 executed 40 real RTX 3060 Laptop GPU runs: 10 calibration
observations and 30 untouched held-out evaluation observations across six
strata. The frozen decision is
`candidate_falsified_small_model_calibration`; `candidate_survives_lc1=False`.

Adaptive survivor continuation ended at better held-out loss: median final NLL
2.31465 versus fixed-local restart's 2.34115. The frozen finite-horizon
progress-per-FLOP objective nevertheless favored fixed restart because it
stopped with 458,752 attempted tokens rather than 524,288, exactly 12.5 percent
less work, while every policy crossed the 3.13759 target at the first 32-tick
observation. LC1 therefore published the candidate failure instead of
retuning the target or the six held-out schedules. The result artifact,
learning sidecar, and observatory projection preserve the measured curves,
paired interval, falsifier outcomes, device-energy boundary, and provenance.

## Next Research Milestone: Late-Stage Fixed-Target E001-LC2

E001-LC2 must warm-start near a frozen late-training quality target so stopping
quality is held constant. Compare quality-constrained time to target, measured
device energy, and attempted work for fixed-local restart and survivor
continuation. Then bridge the observed learning curves to recovery-v2 modeled
time, WAN traffic, and facility-energy mechanics without relabeling modeled
quantities as measurements. Scale model, optimizer, data, outage, and
accelerator panels only if the candidate survives LC2.

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
| P0 | Run late-stage fixed-target E001-LC2. | A warm-started held-out experiment compares quality-constrained time, measured device energy, and attempted work at one frozen late-training loss target. |
| P0 | Bridge observed learning curves to datacenter mechanics. | Target-conditioned observations connect explicitly to recovery-v2 modeled time, WAN, facility energy, and work without crossing the measured/modeled evidence boundary. |
| P0 | Preserve the LC1 falsification. | LC1 remains `candidate_falsified_small_model_calibration`; LC2 is a new frozen question, not a retune of LC1's target or six evaluation strata. |
| P1 | Scale survivor continuation only after LC2 survives. | Model-family, optimizer, non-IID data, outage-duration, and accelerator panels follow only a positive held-out LC2 result. |
| P1 | Build E002 only if power binds. | Rack/facility telemetry work starts when E001 evidence shows facility power, not communication or learning staleness, is the dominant constraint. |
| P1 | Keep the continuation compass scientific. | `next-work` ranks missing evidence, mechanism leverage, residuals, and uncertainty contribution; root debt remains a secondary diagnostic. |
| P2 | Deepen physical ancestry selectively. | New lower-level physics closes a measured residual, reduces uncertainty, or enables an experiment. |

## Future Work

Build the research programs in `RESEARCH.md`: adaptive multi-datacenter
training, power-waveform shaping, semantic fault tolerance, fluid inference
topology, heterogeneous architecture co-design, and firm grid-responsive
inference. Every program must move through virtual screening, held-out
calibration, shadow-mode comparison, and real-cluster validation.
