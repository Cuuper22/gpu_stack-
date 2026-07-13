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
- the recovery mechanics screen remains a prior Pareto result; E001-LC1 adds
  40 measured small-model GPU runs, LC2 preserves two protocol-stage failures,
  and E001-LC3 adds an equal-canonical-work held-out result that isolates a
  measured device-energy failure after its learning, work, and tick gates pass;
- E002-PW1 completed the resulting 32-run factorial with exact bindings, then
  correctly rejected its own phase-energy evidence when the device power
  update rate could not support the frozen attribution;
- E002-PW2 repeated the frozen design with cumulative energy, passed validity,
  attributed the local checkpoint-cadence effect, and recovered sparse
  continuation across all eight frozen gates;
- E001-SC1 completed a 56-record semantic-consistency loop, selected
  `periodic_local` on calibration, rejected the observable switching
  controller on learning, WAN traffic, modeled time, and hindsight-envelope
  regret, and exposed 104 out-of-distribution abstention ticks without a
  divergence or equal-work violation.

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

## E001-LC2 Protocol Sequence: Preserved, Not Rewritten

LC2 v1 stopped before evaluation because its 2,048-tick checkpoint was not
late-stage under the frozen gate. LC2 v2 established a valid 8,192-tick
late-stage checkpoint and exact no-failure equivalence, then stopped because
the calibration-only NLL target had already been crossed outside its frozen
192-to-288-tick validity window. Neither LC2 artifact is candidate evidence.
Together they exposed raw first crossing as an invalid late-stage endpoint and
selected LC3's equal-canonical-work question without smoothing or retuning.

## E001-LC3 Equal-Canonical-Work Result: Executed

LC3 ran 12 held-out fixed/adaptive observations across six frozen schedules at
the exact same 524,288-canonical-token frontier. Adaptive was learning-
noninferior, saved a median 3.03 percent attempted work, and saved a median 40
opportunity ticks. Those gates passed. Its sampled training-device-energy ratio
had median 1.068 and paired 90 percent upper bound 1.134, above the frozen 1.05
ceiling. The sole failed gate makes the conclusion
`candidate_falsified_equal_canonical_work`. The compact observatory sidecar is
`docs/data/e001-equal-work-v1.json`.

## E002-PW1 Checkpoint-Power Result: Measurement Invalid

PW1 completed all 32 frozen factorial runs with exact LC3 warm-state binding.
Its requested 20 ms logger observed effective NVML updates every 494.693 ms,
with selected +250 ms lag at the frozen boundary. The only active invalidators
are `insufficient_evaluation_power_updates` and
`insufficient_pooled_cadence_phase_updates`. The preserved conclusion is
`measurement_invalid`.

Raw PW1 values cannot select a mechanism. The LC3-corner energy ratio was
median `0.789 [0.703, 0.923]` and did not reproduce the earlier penalty. The
sparse-continuation salvage ratio was `0.823 [0.665, 1.019]`, with all
non-energy gates passing. Both are inadmissible; all mechanism gates failed.

## E002-PW2 Cumulative-Energy Result: Valid Local Mechanism

PW2 completed 32/32 runs with exact warm binding, measurement validity, and no
invalidators. Its counter updated every 91.667 ms effectively, and each
held-out arm carried 83 to 109 updates. Snapshot support was 59.30 sparse and
110.06 dense; checkpoint-group support was 124.56 and 176.94.

All three mechanism gates passed. Total interaction was
`2.2416e-5 [2.1746e-6, 3.5305e-5] J/token`; checkpoint group was
`5.8845e-6 [3.0774e-6, 8.9671e-6]`; snapshot was
`4.9917e-6 [2.8497e-6, 7.4481e-6]`. Sparse continuation passed all eight gates:
NLL upper `0.0085037`, 3.03% work saving, 40 ticks saved, and energy-ratio
upper `1.00319`. Conclusion:
`checkpoint_cadence_attributed_sparse_continuation_survives`.
The sensitivity-only idle-subtracted interaction crossed zero at
`3.9825e-6 [-8.0109e-6, 1.2479e-5] J/token`; the frozen raw-cumulative primary
passes, but the attribution is not baseline-insensitive.

## E001-SC1 Observable Semantic Slack: Controller Rejected

E001-SC1 executed 20 calibration runs and 30 executable held-out runs across
six stress families, plus six non-executable hindsight whole-policy-envelope
records. Calibration selected `periodic_local`. Adaptive switching then had a
held-out NLL difference of `+0.016659 [+0.001785, +0.042213]`, WAN-payload
ratio `2.128x [1.556x, 2.552x]`, and modeled-completion ratio
`1.072x [0.986x, 1.099x]`. All three gates failed. The envelope-regret upper
bound was `0.10056`, narrowly above its `0.10` limit.

Every evaluation arm completed the same 524,288 canonical tokens with zero
divergence, sample-identity mismatch, optimizer-lineage violation, or
work-contract violation. The result is a valid negative result, not an engine
failure. It also includes 104 explicit out-of-distribution abstention ticks in
E2, E4, and E6, so the persisted conclusion is
`abstain_without_policy_claim`.

## Next Research Milestone: E001-SC2 Transferable Risk Prediction

Test whether a predictor trained only on calibration runs can estimate each
policy's learning penalty and modeled time/WAN consequence before switching
across a wholly held-out model or optimizer family. Keep `periodic_local` as
the default baseline and do not retune on SC1's six evaluation families. The
research result is transfer accuracy, calibrated abstention, or a documented
failure, not the existence of a more elaborate controller.

E002-PW3 remains an optional physical calibration and falsification adapter
for rack-level power claims. It does not gate E001-SC2 or the software research
loop, and PW2 still does not establish rack or facility transfer.

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
| P0 | Run E001-SC2 across held-out model or optimizer families. | The predictor and `periodic_local` baseline are frozen before the withheld family is opened, and learning, WAN, modeled time, regret, and abstention are reported together. |
| P0 | Explain policy risk before action. | The observatory connects visible state to predicted learning penalty, modeled infrastructure consequence, actual outcome, uncertainty, and abstention at all three depths. |
| P0 | Preserve SC1 as a negative result. | Its six evaluation families are not converted into controller-tuning data; all four failed gates and 104 abstentions remain visible. |
| P1 | Keep E002-PW3 optional. | Physical rack access calibrates or falsifies rack-power boundaries without blocking software experiments. |
| P1 | Withhold facility transfer. | Rack, cooling, grid-safety, and admission-capacity claims remain explicitly unresolved without direct evidence. |
| P1 | Keep the continuation compass scientific. | `next-work` ranks missing evidence, mechanism leverage, residuals, and uncertainty contribution; root debt remains a secondary diagnostic. |
| P2 | Deepen physical ancestry selectively. | New lower-level physics closes a measured residual, reduces uncertainty, or enables an experiment. |

## Future Work

Build the research programs in `RESEARCH.md`: adaptive multi-datacenter
training, power-waveform shaping, semantic fault tolerance, fluid inference
topology, heterogeneous architecture co-design, and firm grid-responsive
inference. Every program must move through virtual screening, held-out
calibration, and counterfactual comparison. External physical validation is a
later adapter only for claims whose measurement boundary requires it.
