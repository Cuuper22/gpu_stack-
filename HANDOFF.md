# HANDOFF: gpu_stack active wave

Status timestamp: July 12, 2026, America/Los_Angeles.

## Strategic Research Reset

The engine, visual medium, and research program are one closed loop. Read
`RESEARCH.md`, `docs/research/frontier-scan-2026-07-12.md`, and the E001 result
artifact before continuing. `main` is canonical; closeout requires local
`HEAD` to equal `origin/main`.

Experiment 001 asks whether adaptive consistency, parallelism, optimizer
correction, site membership, and power-aware placement can make frontier
training span heterogeneous, intermittently powered datacenters without losing
centralized learning efficiency. Its preregistered virtual design is in
`experiments/e001-beyond-one-datacenter/experiment.md`.

`next-work` now promotes `Run E002 checkpoint-power waveform attribution`,
`Separate checkpoint cadence from survivor continuation`, and `Scale survivor
continuation only after the energy gate passes`. Physical root debt and Pythia
closure remain legacy diagnostics, not the scientific priority function.

## Active Wave: E001-LC3 Equal-Canonical-Work Result

Status: executed on `research/e001-lc2-quality-target`; end-of-feature
verification, merge, and push remain pending.

- LC1 remains `candidate_falsified_small_model_calibration`: 10 calibration
  and 30 held-out observations showed its finite-horizon denominator rewarded
  fixed restart for stopping at worse quality with less attempted work.
- LC2 v1 stopped at `protocol_failed_warm_start_not_late_stage`. LC2 v2
  established a valid late-stage checkpoint and exact no-failure equivalence,
  then stopped at `protocol_failed_calibration_validity` because raw NLL first
  crossing fell outside the frozen target window. Neither protocol artifact is
  candidate evidence.
- LC3 used equal canonical work instead. Its 12 held-out observations all
  reached 524,288 canonical tokens. Learning noninferiority, attempted-work
  saving, and opportunity-tick saving passed; adaptive saved median 3.03
  percent attempted work and 40 opportunity ticks.
- Device energy was the sole failed gate: median adaptive/fixed 1.068 and
  paired 90 percent upper bound 1.134 against the frozen 1.05 ceiling. The
  conclusion is `candidate_falsified_equal_canonical_work` and
  `candidate_survives_lc3=False`.
- The full result and `docs/data/e001-equal-work-v1.json` observatory sidecar
  are present. Recovery-v2 time, WAN, and facility energy remain modeled
  mechanics, not measured LC3 outcomes.

## Prior Completed Wave: Recovery-Backed E001 Mechanics

The recovery-v2 vertical slice remains the prior result. Four matched policies
reached durable frontier 8 with exact work conservation. Synchronous recorded
1.584 s, 15.2 GB, 114.64 PFLOP lost, and 0.274 MJ; fixed-local 1.516 s,
10.4 GB, 144.50 PFLOP, and 0.283 MJ; adaptive 1.536 s, 13.6 GB, 48.43 PFLOP,
and 0.255 MJ; oracle 1.536 s, 13.6 GB, 57.00 PFLOP, and 0.257 MJ. Fixed-local
won time and bytes while adaptive won lost work and modeled energy. This stays
a mechanical Pareto split, not a learning or frontier-validation claim.

## Latest Verified Wave

`research substrate, E001 mechanics, and causal observatory` is implemented,
browser-inspected, and merge-verified.

Implemented facts:

- New research modules implement immutable observations, hard split contracts,
  residual and uncertainty evaluation, replicated benchmarks, causal temporal
  events, shared resources, multi-site interventions, observable-only policies,
  E001 execution, and observatory projection.
- Protocol schema v2 binds scalar falsifiers and mandatory structured evidence
  requirements into every run artifact. E001 through E006 are machine-readable
  and cannot silently omit outcome vectors, transfer panels, causal
  attribution, full-boundary accounting, or abstention gates.
- Persisted E001 mechanics, all over the same modeled work: synchronous is
  33.6 TB and 6,047.01 s; fixed-local is 4.2 TB and 1,341.98 s; adaptive
  cadence is 1.68 TB and 938.60 s. Adaptive cadence uses 11 to 22 local steps.
- The adaptive policy is still `inconclusive`. Its collective-payload ratio is
  5 percent, but that is a component diagnostic rather than a complete WAN
  scalar. Held-out progress per FLOP, time to target, all seven v1 structured
  gates, reactive outage membership, optimizer correction, complete inter-site
  traffic, and complete energy are unresolved.
- The artifact-driven observatory exposes one truth at Freshman, Researcher,
  and Full trace depths. URL state includes experiment, policy, node, event,
  time, depth, and uncertainty. Full trace exposes 1,395 event records.
- In-app browser inspection covered depth, uncertainty, policy selection,
  state persistence, visible share feedback, desktop layout, mobile site-rail
  panning, the mobile evidence drawer, and the mobile source table. The
  concept-to-build ledger is `docs/design/observatory-fidelity-ledger.md`.
- Exact verification: focused research/docs pack `28 passed in 11.83s`;
  read-only full verifier `5/5` in `320.32s`. The default 300-second gate first
  stopped a still-green pytest stream at 97 percent; the unchanged verifier
  passed with `--gate-timeout 600`, with pytest completing in `313.48s`.

## Previous Verified Wave

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

Resume from LC3's isolated energy failure, not recovery infrastructure. Run
E002 as a frozen 2x2 checkpoint-cadence x survivor-continuation experiment at
equal canonical work, with checkpoint/training/restore/synchronization power-
waveform attribution. Generalize only if the factorial result preserves LC3's
learning, work, and tick gains while passing the energy ceiling.

## Current State

Physical root-debt boundary hardening is now the previous verified handoff.

- Runtime capped live workers at six, so the wave used bounded write lanes and
  a pseudo-git coordination ledger (now archived in `archive/AGENT_GITLOG.md`).
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

1. Run E002 checkpoint-power waveform attribution as a frozen 2x2 factorial:
   checkpoint cadence by survivor continuation.
2. Estimate cadence, continuation, and interaction effects at equal canonical
   work while attributing checkpoint, training, restore, and synchronization
   power phases.
3. Preserve LC3's passing learning, attempted-work, and opportunity-tick gates
   and require the adaptive/fixed device-energy upper bound to pass 1.05.
4. Scale survivor continuation only after the energy gate passes.

## Verification Policy

For each E-00N milestone, run one feature-level verification at the end. Do not
build new audit/checklist infrastructure or repeatedly test partial recovery
semantics while implementing. Fix a direct validity failure if it blocks the
research path; otherwise finish the experiment, artifact, and visual result
before verification.

## 2026-05-06 22:35 PDT Parent Closeout

- Physical root-debt boundary hardening is integrated and verified.
- Earlier worker coordination notes are superseded by the verified facts above.
- Final handoff state is full-verified, read-only verified, and source-clean.

## 2026-05-06 23:00 PDT Parent Closeout

- Live next-work compass and scenario-audit missing-family ergonomics are
  integrated and verified.
- Earlier worker coordination notes about missing `gpu_stack.next_work` are
  superseded by the verified facts above.
