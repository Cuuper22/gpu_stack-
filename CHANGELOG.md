# CHANGELOG

Rolling notes on the granularity pass. Update after every pass.

## Workflow note

As of April 18, 2026 the user asked for roughly five files per response. Keep the dependency order, but process adjacent files in batches when practical.

## Current physical deepening notes

* Finalized the portfolio form-and-deliverable polish wave. The docs site
  moved to the three-font system from `DESIGN.md` (IBM Plex Sans reading
  copy, Pixelify Sans chrome and headings, IBM Plex Mono commands), gained
  absolute Open Graph metadata plus `og:url`, `og:type`, and `twitter:card`,
  converted leaked markdown backticks into real `code` elements, removed the
  dead empty `docs/styles.css`, null-guarded `docs/app.js` panel renders,
  and darkened eyebrow labels to clear 4.5:1 contrast. The impeccable static
  detector now reports only a known false positive on `docs/` (it counts the
  seven CLI `--flag` tokens in the console sample as em-dashes; prose has
  none). README example fixes: the dependency-cone snippet sorts roots by
  name instead of comparing `Variable` objects, and `evaluate_targets`
  targets `training.tokens_per_sec`; both re-ran successfully. Ledger
  reconciliation recorded the Pythia energy-floor wave end state: scope
  splits merged, full pytest grew to `670 passed in 133.89s`, audit large
  project files moved 7 to 0, and Pythia `cost_per_token` still reports 33
  missing inputs, so cost closure stays on the visible backlog. Full
  verifier passed `4/4 gates passed in 141.07s` on this base.
* Finalized the live next-work compass and scenario-audit missing-family
  ergonomics wave. Added `gpu_stack.next_work` with `NextWorkPlan`,
  `NextWorkItem`, and `build_next_work_plan(...)`; added `next-work` and
  `next-work --json`; added aggregate
  `ScenarioReport.missing_family_summaries`; and added `scenario-audit
  --missing-families` text output. Focused parent pack passed
  `11 passed in 20.82s`; broader CLI/preset/next-work pack passed
  `111 passed in 45.31s`; full pytest passed `639 passed in 102.03s`; audit
  gate PASS reported 16 systems, 1517 variables, 24 constants, 959 equations,
  619 root inputs, 253 leaves, 0 cycles, 0 hard failures, 0 large scope files,
  and 7 large project files; full verifier passed
  `4/4 gates passed in 107.69s`; read-only full verifier passed
  `4/4 gates passed in 95.58s`; final source-clean check reported
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0 ruff_cache_dirs=0`.
* Finalized the physical root-debt boundary hardening wave. Runtime capped
  live workers at six, so bounded write lanes were tracked through a
  pseudo-git coordination ledger (now archived at `archive/AGENT_GITLOG.md`).
  MOSFET, interconnect, lithography source/species, and
  medium-response source surfaces gained boundary hardening; process geometry,
  SEMF/nuclear coefficients, source-plasma drive, medium intercomponent,
  root-debt, import, CLI, and boundary index/smoke-pack coverage were added or
  expanded. Focused parent pack passed `125 passed in 33.75s`; full pytest
  passed `628 passed in 71.99s`; audit gate PASS reported 16 systems,
  1517 variables, 24 constants, 959 equations, 619 root inputs, 253 leaves,
  0 cycles, 0 hard failures, 0 large scope files, and 7 large project files;
  full verifier passed `4/4 gates passed in 73.38s`; read-only full verifier
  passed `4/4 gates passed in 75.17s`; final source-clean check reported
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0 ruff_cache_dirs=0`.
* Finalized the scenario-audit selector/report ergonomics wave.
  `SCENARIO_TARGET_SETS` and `scenario_targets_for(...)` centralize advertised
  scenario targets; `scenario-audit --preset` selects packs; `scenario-audit
  --target [LABEL=]VARIABLE` overrides advertised targets; `ScenarioReport`
  now includes target-level ok/issues/error counts and label tuples; and
  `root-debt --json` covers flat and family-grouped outputs. Focused
  selector/report/root-debt pack passed `112 passed in 25.94s`; full pytest
  passed `548 passed in 69.71s`; audit gate PASS reported 16 systems,
  1517 variables, 24 constants, 954 equations, 619 root inputs, 253 leaves,
  0 cycles, 0 hard failures, 0 large scope files, and 7 large project files;
  full verifier passed `4/4 gates passed in 72.95s`; read-only full verifier
  passed `4/4 gates passed in 80.75s`; final source-clean check reported
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.
* Finalized the `scenario-audit` CLI wave over
  `scenarios.SOURCED_SCENARIO_PACKS`. It evaluates advertised target sets via
  `Preset.evaluate_targets(...)`, supports text and `--json` output, and
  `--fail-on-issues` returns nonzero when any sourced scenario target has
  issues. The current known issue count is 33 from the Pythia cost-per-token
  target's missing economics/thermal roots. Focused CLI tests passed
  `3 passed, 47 deselected in 8.87s`; broader focused pack passed
  `90 passed in 25.92s`; full pytest passed `536 passed in 68.00s`; audit gate
  PASS reported 16 systems, 1517 variables, 24 constants, 954 equations,
  619 root inputs, 253 leaves, 0 cycles, 0 hard failures, 0 large scope files,
  and 7 large project files; full verifier passed
  `4/4 gates passed in 70.64s`; read-only full verifier passed
  `4/4 gates passed in 76.89s`; final source-clean check reported
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.
* Finalized the structured scenario-artifact wave:
  `Preset.evaluate_targets(...)` returns a structured `ScenarioReport` with one
  `ScenarioTargetReport` per requested target; `MissingFamilySummary` captures
  grouped missing-family summaries; and `scenario-report --json` emits the
  same artifact surface from the CLI. Focused pack passed
  `87 passed in 15.88s`; full pytest passed `533 passed in 73.54s`; audit gate
  PASS reported 16 systems, 1517 variables, 24 constants, 954 equations,
  619 root inputs, 253 leaves, 0 cycles, 0 hard failures, 0 large scope files,
  and 7 large project files; full verifier passed
  `4/4 gates passed in 65.34s`; read-only full verifier passed
  `4/4 gates passed in 73.22s`; final source-clean check reported
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`. SEMF numeric defaults remain
  blocked by source and semantics; cited scenario expansion and model expansion
  remain open.
* Finalized the diagnostics / resolve-family / provenance wave:
  user-visible surfaces include `root-debt --families`,
  `scenario-report --missing-families`, and `resolve --missing-families`
  missing-input grouping. Focused integration pack passed with
  `167 passed in 15.68s`; full pytest passed with
  `528 passed in 55.75s`; audit gate PASS reported 16 systems,
  1517 variables, 24 constants, 954 equations, 619 root inputs, 253 leaves,
  0 cycles, 0 hard failures, 0 large scope files, and 7 large project files;
  full verifier passed `4/4 gates passed in 59.88s`; read-only full verifier
  passed `4/4 gates passed in 66.30s`; final source-clean check reported
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`. Runtime accepted at most
  6 live workers; this wave still executed lanes T through AA plus verification
  lanes.
* Added the six-lane backlog wave:
  `scenario-report --missing-families` now groups unresolved target inputs by
  resolver family, boundary category, and primitive-boundary status. Resolver
  family buckets now preserve public prefixes for economics roots (`econ.node`,
  `econ.cluster`, `econ.asset`, etc.) instead of collapsing them into one blob.
  `root-debt --families` exposes the same family-oriented unresolved-root view
  from the root-debt side.
  `scenarios.euv_tin120_lpp_source_context_assumption` composes
  `materials.source_tin_120` with ASML public 50 kHz EUV tin LPP context while
  leaving unsourced fluence, pressure, temperature, focusing, heating, and
  efficiency roots open. SEMF factory tests now reject empty, nonnumeric,
  boolean, unknown, non-root, and derived-alias assignments without publishing
  coefficient defaults. Root-debt CLI determinism, gas/thermal feasibility,
  medium-response domain propagation, and preset export/discovery tests were
  added. Focused integration pack passed with 118 tests. Full pytest passed
  with 488 tests, full verifier passed 4/4 in 57.47s, read-only full verifier
  passed 4/4 in 62.22s, and the final source-clean check reports
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.
* Added the preset/reporting wave:
  `gpu-stack scenario-report` now summarizes preset target values, missing
  roots, violated constraints, violated approximation-validity checks, and
  trace length. `materials.source_tin_120` adds a sourced composition-only EUV
  source isotope preset with source valence quark assignments U=170 and D=190.
  `gpu_stack.presets.lithography` adds ASML EUV tin LPP public context, an
  assumption-labeled tin-120 source closure, and a combined source-boundary
  assumption preset. `gpu_stack.presets.nuclear` adds SEMF calibration-root
  inventory and a source-required preset factory without numerical defaults.
  Resolver unresolved-input diagnostics now include `family`,
  `boundary_category`, and `primitive_boundary`, and medium-response tests now
  cover assigned and propagated invalid response boundaries. Full pytest
  passed with 455 tests, full verifier passed 4/4 in 54.00s, read-only full
  verifier passed 4/4 in 55.39s, and the final source-clean check reports
  `cache_dirs=0 pyc_files=0`.
* Snapshot after preset/reporting wave:
  16 systems, 1517 variables, 24 constants, 954 equations, 619 roots, 253
  leaves, 796 unit-checked equations, 1428 variables with `sp_units`, 1324
  variable references, 873 equation references, 51 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, 7 large
  project files, and 455 tests.
* Added the physical boundary-hardening wave:
  source-plasma drive/focus now has named constraints for edge detuning,
  acceptance half-angle forward half-space, pulse duration fractions, temporal
  shape, and peak intensity relative to pulse-average intensity; source-plasma
  gas/species now has explicit pressure, temperature, number-density, positive
  thermal-speed, and subluminal thermal-speed constraints; source valence quark
  roots are positive integer primitive boundaries; medium optical-response
  fractions/counts/resonance ratios gained structural constraints; shared SEMF
  calibration roots gained focused boundary tests; and material preset
  provenance scaffolding was extended without weakening composition-only
  caveats. Full pytest passed with 432 tests, full verifier passed 4/4 in
  48.41s, read-only full verifier passed 4/4 in 49.69s, and the final
  source-clean check reports `cache_dirs=0 pyc_files=0`.
* Snapshot after physical boundary hardening:
  16 systems, 1517 variables, 24 constants, 954 equations, 619 roots, 253
  leaves, 796 unit-checked equations, 1428 variables with `sp_units`, 1324
  variable references, 873 equation references, 51 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, 7 large
  project files, and 432 tests.
* Added the sourced scenario pack wave:
  preset discovery now finds sourced/calibrated scenario packs dynamically
  instead of hard-coding only synthetic fixtures, and the sourced-scenario
  tests include source/provenance helpers that require nonblank summaries,
  citation-style or official-source tokens, and reject demo/synthetic-looking
  names or source text. The new pack surface includes H100 and DGX H100
  hardware presets, a Pythia-70M workload preset, EIA 2024 industrial power
  tariff assumptions, and a combined sourced scenario pack that exercises the
  resolver through user-facing training throughput, power, and cost targets.
  Focused integration pack passed with 52 tests. Full pytest passed with 390
  tests, full verifier passed 4/4 in 45.77s, read-only full verifier passed
  4/4 in 47.71s, and the final source-clean check reports
  `cache_dirs=0 pyc_files=0`.
* Completed broad scenario, diagnostics, and metadata coverage push:
  `gpu_stack.presets.scenarios.dense_training_cost_fixture` now resolves
  dense training throughput, allocated site power, run cost, and cost/token;
  resolver results expose structured unresolved-input and violated-constraint
  diagnostics; root-debt CLI output has parseable family-grouping coverage;
  and architecture, arithmetic, cluster, collective, economics, GPU,
  interconnect, kernel, memory, optimizer, parallelism, precision, thermal,
  and training scopes gained broad `sp_units`, reference, and unit-check
  coverage.
* Snapshot after the broad metadata/scenario push:
  16 systems, 1517 variables, 24 constants, 940 equations, 619 roots, 253
  leaves, 786 unit-checked equations, 1428 variables with `sp_units`, 1324
  variable references, 859 equation references, 40 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, 7 large
  project files, and 356 tests.
* Migrated imaging-medium packing length to a scale-factor root:
  `physical.lithography.medium_formula_unit_packing_length_scale_factor` is
  now the dimensionless scenario root, constrained by
  `physical.ineq.lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity`
  with `scale >= 1`. The packing length now derives from the effective
  intercomponent separation times
  `medium_formula_unit_packing_length_scale_factor` via
  `physical.eq.lithography_medium_formula_unit_packing_length_from_intercomponent_separation_scale`.
* Snapshot after medium packing-length scale-factor migration:
  16 systems, 1517 variables, 24 constants, 940 equations, 619 roots, 253
  leaves, 400 unit-checked equations, 605 variables with `sp_units`, 478
  variable references, 388 equation references, 40 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, 7 large
  project files, and 280 tests.
* Added imaging-medium formula-unit charge-transfer closure:
  `physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count`
  is now the root for intercomponent charge normalization, while
  `physical.eq.lithography_medium_intercomponent_charge_unit_from_formula_unit_charge_transfer`
  derives `medium_intercomponent_charge_unit` by dividing transfer count by
  the binary stoichiometric pair count. Two new inventory constraints bound
  the transfer count by component-A and component-B electron availability.
* Snapshot after formula-unit charge-transfer closure:
  16 systems, 1516 variables, 24 constants, 939 equations, 619 roots, 253
  leaves, 399 unit-checked equations, 604 variables with `sp_units`, 477
  variable references, 387 equation references, 40 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, 7 large
  project files, and 280 tests.
* Added source-plasma symmetric fall-ramp closure:
  `physical.eq.lithography_source_plasma_drive_pulse_fall_fraction_from_symmetric_ramp`
  now derives the drive pulse fall fraction from the rise fraction. The
  remaining pulse-shape primitive is the rise fraction; the existing flat-top
  and temporal-shape equations now sit downstream of that symmetric ramp
  convention.
* Corrected source-plasma drive f-number geometry:
  `source_plasma_drive_focus_f_number` now derives as
  `1 / (2 tan(theta_accept))` from the drive acceptance half-angle instead of
  using the paraxial `1 / (2 NA)` shortcut after `NA = sin(theta_accept)`.
  This keeps pupil/focal geometry, numerical aperture, and focused spot size
  consistent at larger acceptance angles.
* Added source-plasma pupil-fill BPP reference-radius closure:
  `physical.lithography.source_plasma_drive_pupil_beam_fill_factor` is now an
  explicit unit-interval root, and
  `physical.eq.lithography_source_plasma_drive_beam_parameter_waist_radius_from_pupil_fill`
  derives the BPP waist/reference radius as pupil fill times effective drive
  pupil radius. This keeps the upstream beam-quality radius distinct from the
  downstream focused source-plasma spot radius.
* Snapshot after source-plasma symmetric fall-ramp closure:
  16 systems, 1515 variables, 24 constants, 936 equations, 619 roots, 253
  leaves, 396 unit-checked equations, 603 variables with `sp_units`, 476
  variable references, 384 equation references, 39 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, 7 large
  project files, and 280 tests.
* Added a source-plasma divergence/acceptance feasibility constraint:
  `physical.ineq.lithography_source_plasma_drive_far_field_divergence_within_acceptance`
  now requires far-field beam divergence to fit inside the source-plasma drive
  focusing optic acceptance half-angle. Divergence remains a scenario root, but
  over-divergent drive optics now surface as named resolver constraint
  failures.
* Snapshot after source-plasma divergence/acceptance feasibility:
  16 systems, 1514 variables, 24 constants, 933 equations, 620 roots, 252
  leaves, 393 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 381 equation references, 38 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, 7 large
  project files, and 277 tests.
* Added source-plasma operating-input feasibility constraints:
  drive pulse duty factor, electron-heating fraction, and free-electron
  inventory charge fraction must be at most unity, and source-plasma drive
  far-field divergence half-angle must remain within the forward optical
  half-space. These are constraint-only relations; the corresponding pulse,
  heating, inventory, and beam-divergence quantities remain explicit scenario
  inputs.
* Snapshot after source-plasma operating feasibility:
  16 systems, 1514 variables, 24 constants, 932 equations, 620 roots, 252
  leaves, 392 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 380 equation references, 37 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, 7 large
  project files, and 276 tests.
* Added a medium packing/intercomponent feasibility constraint:
  `physical.ineq.lithography_medium_formula_unit_packing_length_at_least_intercomponent_separation`
  now requires the formula-unit packing length to be at least the represented
  intercomponent separation. Undersized packing cells surfaced as named
  resolver constraint failures; the later scale-factor migration supersedes
  this root-boundary framing.
* Snapshot after medium packing-length feasibility:
  16 systems, 1514 variables, 24 constants, 928 equations, 620 roots, 252
  leaves, 388 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 376 equation references, 37 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, 7 large
  project files, and 274 tests.
* Extended audit large-file coverage:
  `gpu-stack audit` now reports `large_project_files` across `gpu_stack/` and
  `tests/`, while preserving the existing `large_scope_files` signal. The
  broader large-file signal is visible cleanup debt rather than a hard failure;
  current audit reports 0 large scope files, 7 large project files, and 0 hard
  failures.
* Snapshot after large-project-file audit coverage:
  16 systems, 1514 variables, 24 constants, 927 equations, 620 roots, 252
  leaves, 387 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 375 equation references, 37 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, 7 large
  project files, and 274 tests.
* Added composition-only lithography material presets:
  `gpu_stack.presets.materials` now exposes hydrogen-1 and oxygen-16 source
  isotope presets plus an H2O imaging-medium formula-unit preset. These assign
  exact stoichiometry and valence quark-count roots only; binding, density,
  and optical-response roots remain unassigned rather than receiving unsourced
  calibration values. The CLI preset namespace now includes `materials.*`.
* Snapshot after composition-only material presets:
  16 systems, 1514 variables, 24 constants, 927 equations, 620 roots, 252
  leaves, 387 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 375 equation references, 37 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, and 273
  tests.
* Added lithography imaging-medium feasibility constraints:
  binary formula-unit stoichiometry now requires
  `nu_A_litho_med >= 1` and `nu_B_litho_med >= 1`, and packing fill factor now
  reports `phi_pack_litho_med <= 1` as a named resolver constraint. These are
  constraint-only relations, so invalid unary or overpacked assignments remain
  resolvable but surface explicit feasibility failures.
* Snapshot after lithography medium feasibility constraints:
  16 systems, 1514 variables, 24 constants, 927 equations, 620 roots, 252
  leaves, 387 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 375 equation references, 37 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, and 270
  tests.
* Corrected kernel latency-hiding semantics:
  `kernel.latency_hiding_factor` is now the occupancy efficiency
  `Min(1, occ / occ_full_k)`, with positive `[0,1]` domains for occupancy,
  full-hide occupancy, and the hiding factor. Low occupancy now increases
  latency-bound kernel time instead of reducing it.
* Hardened optimizer schedule domains and horizon constraints:
  schedule base learning rate is nonnegative, step/warmup/total/stable counts
  carry explicit integer/sign domains, and total scheduled steps must exceed
  warmup, exceed warmup plus WSD stable steps, and reach the current step.
  Integer domain relations now keep `Mod(..., evaluate=False)` so fractional
  assignments are reported instead of simplified away under integer symbol
  assumptions.
* Snapshot after optimizer schedule domain hardening:
  16 systems, 1514 variables, 24 constants, 924 equations, 620 roots, 252
  leaves, 384 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 372 equation references, 37 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, and 269
  tests.
* Added read-only verification hygiene:
  `verify --read-only` now runs child Python with bytecode disabled, suppresses
  pytest's cache provider, and uses an in-memory syntax gate instead of
  `compileall` in the full profile. The later T-AA closeout removed the stale
  `asyncio_default_fixture_loop_scope` pytest option because the current local
  environment reports it as unknown when the pytest-asyncio plugin is not
  loaded.
* Snapshot after read-only verification hygiene:
  16 systems, 1514 variables, 24 constants, 921 equations, 620 roots, 252
  leaves, 384 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 372 equation references, 36 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, and 258
  tests.
* Hardened the global Lorentz-Lorenz branch validity:
  `physical.eq.lithography_medium_relative_permittivity` now requires
  `x_LL_litho_med > -1/2` as well as `x_LL_litho_med < 1`, matching the
  intercomponent Lorentz-Lorenz branch guard. Negative-permittivity branch
  scenarios still resolve numerically but report violated approximation
  validity.
* Snapshot after Lorentz-Lorenz branch hardening:
  16 systems, 1514 variables, 24 constants, 921 equations, 620 roots, 252
  leaves, 384 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 372 equation references, 36 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, and 256
  tests.
* Added reduced-mass feasibility constraints:
  `physical.lithography.source_nuclear_mass`,
  `physical.lithography.source_reduced_mass`, and
  `physical.lithography.source_reduced_mass_ratio` now carry explicit positive
  constraints. Negative nuclear mass from an over-large binding-energy mass
  defect and the singular `m_nuc = -m_e` reduced-mass case now resolve with
  failed constraints instead of silently feeding invalid source-transition
  energy.
* Snapshot after reduced-mass feasibility constraints:
  16 systems, 1514 variables, 24 constants, 921 equations, 620 roots, 252
  leaves, 384 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 372 equation references, 36 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, and 255
  tests.
* Added process-geometry feasibility constraints:
  drawn gate length, source/drain contact width, gate-contact spacing,
  contacted gate pitch, minimum metal width/spacing/pitch, nominal node length,
  and channel length now carry explicit positive or nonnegative constraints.
  Signed lithography/process biases still resolve numerically, but impossible
  negative derived dimensions are reported through resolver constraints.
* Snapshot after process-geometry feasibility constraints:
  16 systems, 1514 variables, 24 constants, 918 equations, 620 roots, 252
  leaves, 384 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 369 equation references, 33 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, and 253
  tests.
* Added photon-domain hardening and singular-domain resolver handling:
  lithography photon energy, source transition energy, photon frequency, source
  angular frequency, and wavelength now carry positive domains. Resolver
  relation evaluation now treats substitution/simplification failures from
  singular values such as `zoo` as failed checks instead of crashing while
  reporting domain constraints. Medium resonance/source energy validity now
  uses structural positivity predicates.
* Snapshot after photon-domain hardening:
  16 systems, 1514 variables, 24 constants, 909 equations, 620 roots, 252
  leaves, 384 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 360 equation references, 24 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, and 251
  tests.
* Added ideal plasma-overlap convention closures:
  `physical.lithography.source_plasma_active_fill_factor` now derives to `1`
  as an ideal full-column convention, drive centroid offset derives to `0` as a
  coaxial drive-column convention, and drive timing offset derives to `0` as a
  synchronized-response convention. The plasma-state compatibility shim now
  anchors its electron-state splice after spatial overlap instead of relying on
  a brittle overlap-list slice.
* Snapshot after the ideal plasma-overlap convention closure:
  16 systems, 1514 variables, 24 constants, 909 equations, 620 roots, 252
  leaves, 384 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 360 equation references, 24 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, and 250
  tests.
* Added formula-unit packing density closure and structural off-resonance
  validity:
  `physical.lithography.medium_mass_density` now derives from formula-unit
  packing length, packing fill factor, packing volume, and representative
  particle mass in `physical_lithography_medium_density.py`; number density
  still derives from mass density over particle mass. The main lithography
  bridge is back below the audit file-size threshold, and
  `physical.eq.lithography_medium_electric_polarizability` now uses structural
  `ne()` for the squared resonance/source-frequency inequality so exact
  positive and negative resonance reports violated approximation validity.
* Snapshot after the medium packing-density closure and non-resonance validity
  fix:
  16 systems, 1514 variables, 24 constants, 906 equations, 623 roots, 252
  leaves, 381 unit-checked equations, 602 variables with `sp_units`, 475
  variable references, 357 equation references, 24 multi-definition variables,
  0 collapsed approximation-validity predicates, 0 large scope files, and 250
  tests.
* Added feature-family k1 process-factor decomposition:
  `physical.lithography.gate_k1` now derives from strictly positive
  aerial-image contrast, resist/process latitude, mask-error amplification, and
  resolution-enhancement factors. Contact and metal feature k1 values continue
  to inherit the gate baseline when feature-specific values are not assigned,
  and negative explicit k1 assignments now report domain and
  approximation-validity violations.
* Snapshot after the gate-k1 process-factor decomposition:
  16 systems, 1511 variables, 24 constants, 904 equations, 622 roots, 252
  leaves, 379 unit-checked equations, 599 variables with `sp_units`, 472
  variable references, 355 equation references, 24 multi-definition variables,
  0 collapsed approximation-validity predicates, and 247 tests.
* Added main lithography optical feasibility bounds:
  `physical.lithography.acceptance_half_angle` is now constrained to the
  forward optical half-space with `theta_litho <= pi/2`, and
  `physical.lithography.numerical_aperture` is constrained by the
  imaging-medium refractive index with `NA_litho <= n_litho_med`.
* Snapshot after the main lithography optical bounds:
  16 systems, 1507 variables, 24 constants, 903 equations, 619 roots, 252
  leaves, 378 unit-checked equations, 595 variables with `sp_units`, 468
  variable references, 354 equation references, 24 multi-definition variables,
  0 collapsed approximation-validity predicates, and 235 tests.
* Added positive-proton valence-quark feasibility constraints:
  source and imaging-medium component quark roots now require
  `U >= (D + 3)/2`, equivalent to derived proton count `Z >= 1`. This keeps
  source/component quark counts as primitive roots while ruling out zero-proton
  or neutron-only isotope assignments that still satisfied the older
  nonnegative-nucleon and triplet-integrality constraints.
* Snapshot after the positive-proton quark feasibility constraints:
  16 systems, 1507 variables, 24 constants, 901 equations, 619 roots, 252
  leaves, 376 unit-checked equations, 595 variables with `sp_units`, 468
  variable references, 352 equation references, 22 multi-definition variables,
  0 collapsed approximation-validity predicates, and 235 tests.
* Added imaging-medium response count/energy root refinement:
  `medium_polarizable_electron_fraction` now derives from polarizable electron
  count over formula-unit electron count,
  `medium_oscillator_sum_rule_fraction` derives from dominant oscillator
  electron count over polarizable electron count, and
  `medium_resonance_to_source_frequency_ratio` derives from medium resonance
  energy over exposure photon energy. The new roots are constrained by
  `N_pol <= N_formula`, `N_osc <= N_pol`, and `E_res > E_photon`.
* Split the medium-response count/energy layer into
  `physical_lithography_medium_response.py` and added an import-surface
  propagation test so the helper's exports stay available through
  `physical_lithography` and `physical`.
* Snapshot after the medium-response count/energy root refinement:
  16 systems, 1507 variables, 24 constants, 898 equations, 619 roots, 252
  leaves, 373 unit-checked equations, 595 variables with `sp_units`, 468
  variable references, 349 equation references, 22 multi-definition variables,
  0 collapsed approximation-validity predicates, and 235 tests.
* Added source-plasma diffraction lower-bound constraints:
  `source_plasma_drive_beam_parameter_product` now has the constraint
  `BPP >= drive_wavelength/pi`, and
  `source_plasma_drive_beam_quality_factor` now has `M2 >= 1`. These are
  feasibility constraints rather than defaults, so they do not collapse the
  waist/divergence or beam-quality operating roots.
* Snapshot after the diffraction lower-bound constraints:
  16 systems, 1504 variables, 24 constants, 892 equations, 619 roots, 252
  leaves, 367 unit-checked equations, 592 variables with `sp_units`, 465
  variable references, 343 equation references, 22 multi-definition variables,
  0 collapsed approximation-validity predicates, and 234 tests.
* Added source-plasma absorption collision orbital-area closure:
  `source_plasma_absorption_collision_orbital_radius` now derives from Bohr
  radius, ionization principal shell, and screened effective nuclear charge;
  `source_plasma_absorption_collision_cross_section` now derives as the
  corresponding geometric orbital area. This removes the collision
  cross-section root while keeping full Coulomb-collision, shielding, and
  pressure-broadening physics outside this local approximation.
* Snapshot after the absorption collision orbital-area closure:
  16 systems, 1504 variables, 24 constants, 890 equations, 619 roots, 252
  leaves, 365 unit-checked equations, 592 variables with `sp_units`, 465
  variable references, 341 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma Rayleigh/confocal column-aspect closure:
  `source_plasma_drive_rayleigh_range` now derives from focused spot radius,
  beam quality factor, and drive wavelength; `source_plasma_drive_confocal_length`
  derives as twice that Rayleigh range; and
  `source_plasma_column_aspect_ratio` now derives from confocal length over
  expanded column radius. This removes the column-aspect root through optical
  focus geometry.
* Snapshot after the Rayleigh/confocal column-aspect closure:
  16 systems, 1503 variables, 24 constants, 888 equations, 620 roots, 253
  leaves, 363 unit-checked equations, 591 variables with `sp_units`, 464
  variable references, 339 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma column expansion sound-speed-factor closure:
  `source_plasma_column_expansion_speed_factor` now derives as `sqrt(5/3)`,
  the monatomic heavy-species ideal-gas sound-speed factor relative to the
  existing source-species thermal-speed scale. This removes the expansion-speed
  factor root while keeping detailed ambipolar expansion, electron pressure,
  confinement, and hydrodynamics outside this local approximation.
* Snapshot after the source-plasma column expansion sound-speed-factor closure:
  16 systems, 1501 variables, 24 constants, 885 equations, 621 roots, 253
  leaves, 360 unit-checked equations, 589 variables with `sp_units`, 462
  variable references, 336 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma spot-shape convention closures:
  `source_plasma_drive_spot_axis_ratio` now derives as `1` from a circular
  spot convention, and `source_plasma_drive_spot_area_fill_factor` now derives
  as `1` from a full nominal illuminated-area convention. This removes two
  high-traffic geometry roots without collapsing the independent beam-quality
  waist/divergence path.
* Snapshot after the source-plasma spot-shape convention closure:
  16 systems, 1501 variables, 24 constants, 884 equations, 622 roots, 253
  leaves, 359 unit-checked equations, 589 variables with `sp_units`, 462
  variable references, 335 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma energy-loss transport-factor mass-ratio closure:
  `source_plasma_energy_loss_transport_speed_factor` now derives from
  `sqrt(source_plasma_species_particle_mass / electron_mass)`. The resulting
  energy-loss speed is the species thermal speed scaled to an electron
  thermal-speed proxy at the same gas-temperature scale.
* Snapshot after the source-plasma energy-loss transport-factor mass-ratio
  closure:
  16 systems, 1501 variables, 24 constants, 882 equations, 624 roots, 253
  leaves, 357 unit-checked equations, 589 variables with `sp_units`, 462
  variable references, 333 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma active-lifetime ratio closure:
  `source_plasma_active_lifetime_to_drive_pulse_ratio` now derives from
  `source_plasma_energy_confinement_time / source_plasma_drive_pulse_duration`.
  This makes active response duration an energy-reservoir-limited proxy while
  leaving recombination, opacity, radiative lifetime, and hydrodynamic expansion
  as future model depth rather than hidden knobs.
* Snapshot after the source-plasma active-lifetime ratio closure:
  16 systems, 1501 variables, 24 constants, 881 equations, 625 roots, 253
  leaves, 356 unit-checked equations, 589 variables with `sp_units`, 462
  variable references, 332 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma energy-loss path direction-cosine closure:
  `source_plasma_energy_loss_path_direction_cosine` now derives as
  `sin(source_plasma_drive_acceptance_half_angle)`, using the complementary
  radial projection of the same drive acceptance cone used by the absorption
  secant path. The remaining adjacent primitive is the energy-loss transport
  speed factor.
* Snapshot after the source-plasma energy-loss path direction-cosine closure:
  16 systems, 1501 variables, 24 constants, 880 equations, 626 roots, 253
  leaves, 355 unit-checked equations, 589 variables with `sp_units`, 462
  variable references, 331 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma absorption path direction-cosine closure:
  `source_plasma_absorption_path_direction_cosine` now derives as
  `cos(source_plasma_drive_acceptance_half_angle)`, so the absorption secant
  path geometry is tied to the same pupil/focal acceptance cone that defines
  drive numerical aperture. The remaining absorption-specific primitive in this
  local chain is now `source_plasma_absorption_collision_cross_section`.
* Snapshot after the source-plasma absorption path direction-cosine closure:
  16 systems, 1501 variables, 24 constants, 879 equations, 627 roots, 253
  leaves, 354 unit-checked equations, 589 variables with `sp_units`, 462
  variable references, 330 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma drive numerical-aperture geometry closure:
  `source_plasma_drive_numerical_aperture` now derives from objective pupil
  radius and focal length through an acceptance half-angle (`theta = atan(r/f)`,
  `NA = sin(theta)`). The primitive focusing boundary moved from abstract NA to
  drive optic geometry roots, while the existing f-number relation remains the
  local paraxial approximation.
* Snapshot after the source-plasma drive numerical-aperture geometry closure:
  16 systems, 1501 variables, 24 constants, 878 equations, 628 roots, 253
  leaves, 353 unit-checked equations, 589 variables with `sp_units`, 462
  variable references, 329 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma drive beam-quality BPP closure:
  `source_plasma_drive_beam_quality_factor` now derives from
  `pi * source_plasma_drive_beam_parameter_product / source_plasma_drive_beam_wavelength`,
  and beam parameter product derives from beam waist radius times far-field
  divergence half-angle. The primitive optical boundary moved from a smooth
  `M2` knob to waist/divergence roots.
* Snapshot after the source-plasma drive beam-quality BPP closure:
  16 systems, 1498 variables, 24 constants, 876 equations, 627 roots, 253
  leaves, 351 unit-checked equations, 586 variables with `sp_units`, 459
  variable references, 327 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma drive numerical-aperture f-number closure and focus helper:
  `source_plasma_drive_focus_f_number` now derives as `1 / (2 NA)` from
  `source_plasma_drive_numerical_aperture`, moving the primitive focusing
  boundary from f-number to the optic cone. Focused-beam wavelength, detuning,
  numerical aperture, beam quality, waist, spot-radius, and spot-area equations
  now live in `physical_lithography_plasma_focus.py`, while `plasma_drive.py`
  re-exports the old public names and stays below the 700-line audit threshold.
* Snapshot after the source-plasma drive numerical-aperture closure:
  16 systems, 1495 variables, 24 constants, 874 equations, 626 roots, 253
  leaves, 349 unit-checked equations, 583 variables with `sp_units`, 456
  variable references, 325 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma edge-detuned drive-wavelength closure:
  `source_plasma_drive_beam_wavelength` now derives from ionization-edge energy,
  `hbar`, light speed, and `source_plasma_drive_edge_detuning_ratio`. The
  detuning ratio remains the root so the graph keeps off-resonance drive choice
  explicit instead of silently forcing exact resonance.
* Snapshot after the source-plasma edge-detuned drive-wavelength closure:
  16 systems, 1494 variables, 24 constants, 873 equations, 626 roots, 253
  leaves, 348 unit-checked equations, 582 variables with `sp_units`, 455
  variable references, 324 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added shared SEMF liquid-drop calibration closure:
  five neutral nuclear binding roots now feed both source and imaging-medium
  coefficient aliases for volume, surface, Coulomb, asymmetry, and pairing-gap
  calibration. Source/medium coefficient variables remain public, but they are
  now derived approximations instead of duplicated calibration boundaries.
* Snapshot after the shared SEMF liquid-drop calibration closure:
  16 systems, 1493 variables, 24 constants, 872 equations, 626 roots, 253
  leaves, 347 unit-checked equations, 581 variables with `sp_units`, 454
  variable references, 323 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added adjacent-shell source-transition step closure:
  `source_transition_principal_quantum_step` now derives as `1` under the
  hydrogenic adjacent-principal-shell approximation, with the equation kept in
  `physical_lithography_transition_step.py` and re-exported through electronic
  structure so the public surface stays stable.
* Snapshot after the adjacent-shell transition-step closure:
  16 systems, 1488 variables, 24 constants, 862 equations, 631 roots, 253
  leaves, 337 unit-checked equations, 576 variables with `sp_units`, 449
  variable references, 313 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma Gaussian waist-coefficient closure:
  `source_plasma_drive_focus_waist_coefficient` now derives as `2/pi`, the
  Gaussian f-number convention for `w0 = (2/pi) M^2 F# lambda`; at that slice,
  drive wavelength, f-number, and beam quality remained the focused-beam roots.
* Snapshot after the source-plasma waist-coefficient closure:
  16 systems, 1488 variables, 24 constants, 861 equations, 632 roots, 253
  leaves, 336 unit-checked equations, 576 variables with `sp_units`, 449
  variable references, 312 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma collision-damping closure:
  `source_plasma_absorption_damping_rate` now derives from source-species
  number density, source-species thermal speed, and
  `source_plasma_absorption_collision_cross_section`; the absorption quality
  factor now derives from resonance angular frequency over that
  collision-broadened damping rate instead of remaining a root.
* Snapshot after the source-plasma collision-damping closure:
  16 systems, 1488 variables, 24 constants, 860 equations, 633 roots, 253
  leaves, 335 unit-checked equations, 576 variables with `sp_units`, 449
  variable references, 311 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added source-plasma absorption-edge closure:
  `source_plasma_absorption_resonance_to_drive_ratio` now derives from
  ionization-edge energy over drive photon angular energy,
  `source_plasma_absorption_participating_electron_fraction` derives from the
  ionization-edge same-shell population plus the edge electron over source
  proton count, and `source_plasma_absorption_sum_rule_fraction` derives from
  unfilled ionization-edge shell degeneracy. The equations live in
  `physical_lithography_absorption_edge.py` and are re-exported through the
  electronic-structure public surface. The same bridge now also carries the
  detuned drive-wavelength equation described above.
* Snapshot after the source-plasma absorption-edge closure:
  16 systems, 1487 variables, 24 constants, 859 equations, 633 roots, 252
  leaves, 334 unit-checked equations, 575 variables with `sp_units`, 448
  variable references, 310 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 233 tests.
* Added resolver domain-constraint and structural approximation-validity
  hardening:
  approximation validity predicates that collapsed under positive SymPy
  assumptions are now recovered into structural domain checks; resolver
  constraints also report declared variable domains for assigned and derived
  scenario values; `gpu-stack audit` now reports
  `collapsed_approximation_validity` as a hard-failure signal; and the fast
  verify profile includes the neutron-sensitive source-plasma mass/thermal
  speed/radial-expansion trace.
* Snapshot after resolver validity hardening:
  16 systems, 1487 variables, 24 constants, 856 equations, 636 roots, 253
  leaves, 331 unit-checked equations, 575 variables with `sp_units`, 448
  variable references, 307 equation references, 20 multi-definition variables,
  0 collapsed approximation-validity predicates, and 232 tests.
* Added source-plasma radial-expansion closure and shared species layer:
  `physical_lithography_plasma_species.py` now owns source-plasma species gas
  pressure, gas temperature, ideal-gas density, nuclear-composition particle
  mass, and gas-temperature thermal speed. The column radial expansion speed
  now derives from source-species thermal speed times
  `source_plasma_column_expansion_speed_factor`, which was the primitive
  expansion-speed boundary at that pass and is now closed by the later
  `sqrt(5/3)` sound-speed-factor approximation.
* Snapshot after the source-plasma radial-expansion closure:
  16 systems, 1487 variables, 24 constants, 856 equations, 636 roots, 253
  leaves, 331 unit-checked equations, 575 variables with `sp_units`, 448
  variable references, 307 equation references, 20 multi-definition variables,
  and 224 tests.
* Added source-plasma free-electron-yield closure:
  `source_plasma_free_electron_yield_per_source_particle` now derives from
  source nuclear charge times
  `source_plasma_free_electron_inventory_charge_fraction`, leaving the
  inventory charge fraction as the primitive free-electron inventory boundary.
* Snapshot after the source-plasma free-electron-yield closure:
  16 systems, 1486 variables, 24 constants, 855 equations, 636 roots, 253
  leaves, 330 unit-checked equations, 574 variables with `sp_units`, 447
  variable references, 306 equation references, 20 multi-definition variables,
  and 224 tests.
* Added source-plasma energy-loss transport closure:
  `source_plasma_energy_loss_path_factor` now derives from an explicit
  energy-loss path direction cosine, and `source_plasma_energy_loss_speed`
  derives from source-species particle mass, gas-temperature thermal speed,
  and a transport speed factor instead of remaining a primitive speed.
* Snapshot after the source-plasma energy-loss transport closure:
  16 systems, 1485 variables, 24 constants, 854 equations, 636 roots, 253
  leaves, 329 unit-checked equations, 573 variables with `sp_units`, 446
  variable references, 305 equation references, 20 multi-definition variables,
  and 224 tests.
* Added source-plasma drive-overlap closure:
  `source_plasma_drive_overlap_factor` now derives from explicit spatial and
  temporal overlap factors instead of remaining a primitive
  absorption-efficiency input. Spatial overlap uses transverse spot/column
  coverage, pointing offset, and active fill; temporal overlap uses active
  lifetime, duration matching, and timing alignment. The overlap helper was
  split into `physical_lithography_plasma_overlap.py`.
* Snapshot after the source-plasma drive-overlap closure:
  16 systems, 1481 variables, 24 constants, 850 equations, 636 roots, 253
  leaves, 325 unit-checked equations, 569 variables with `sp_units`, 442
  variable references, 301 equation references, 20 multi-definition variables,
  and 224 tests.
* Added source-plasma absorption path direction-cosine closure:
  `source_plasma_absorption_path_shape_factor` now derives as the inverse of
  `source_plasma_absorption_path_direction_cosine`, constrained to
  `0 < cos(theta) <= 1`, while absorption path length still derives from the
  derived path-shape factor times column length.
* Added source-plasma drive fluence closure:
  `source_plasma_drive_pulse_fluence` is now the primitive J/m^2 pulse-energy
  density boundary, while `source_plasma_drive_peak_intensity` derives as
  fluence divided by duty-derived pulse duration and the trapezoid temporal
  shape factor. Existing pulse energy still derives from the derived peak
  intensity times spot area, pulse duration, and temporal shape.
* Flipped source lithography nuclear binding to match the medium coefficient
  boundary: source Coulomb/volume/surface/asymmetry coefficients are now roots,
  while source radius scale, saturation density, bulk binding density, surface
  tension, and symmetry-energy density are derived. Pairing still derives from
  the reference pairing-gap root.
* Added richer source-plasma drive/inventory closure: pulse energy derives from
  fluence-derived peak intensity, duty-derived pulse duration, trapezoid-derived temporal shape
  factor, spot area, and spot shape; drive power derives from pulse energy times repetition rate; species
  density derives from partial pressure and gas temperature; active volume
  derives from spot-driven column radius, Rayleigh/confocal-derived column
  aspect and length, and fill; pulse duration is tied to the pulse period; absorption
  efficiency derives from optical depth, overlap, and electron heating;
  confinement time derives from derived energy-loss path length over derived
  energy-loss speed; free-electron count derives from species inventory and
  independent yield.
* Added source-plasma drive duty closure: pulse duration now derives from
  pulse duty factor times pulse period, leaving duty as the primitive timing
  root beside pulse period.
* Added source-plasma temporal-shape closure: the shape factor is no longer a
  root. Rise and fall fractions are root inputs, flat fraction is `1 - rise -
  fall`, temporal shape is `flat + 0.5*(rise + fall)`, and a constraint keeps
  ramp fractions within the pulse.
* Added source-plasma focus and expansion geometry: drive spot radius now
  derives from drive-beam wavelength, focusing f-number, beam-quality factor,
  and a waist coefficient; drive spot shape derives from axis ratio and area fill;
  column expansion factor derives from radial expansion speed over the pulse
  relative to the focused spot radius.
* Added local imaging-medium screening closure: oscillator strength now derives
  from formula-unit electron count, polarizable electron count, and dominant
  oscillator electron count; resonance frequency derives from medium resonance
  energy and source photon energy; and intercomponent relative permittivity
  derives from molecular polarizability through a local Lorentz-Lorenz factor
  and polarizable-site density factor.
* Added source-plasma Lorentz-oscillator absorption closure: the drive beam
  angular frequency derives from drive wavelength, and the absorption cross
  section derives from resonance angular frequency, damping rate, oscillator
  strength, and electromagnetic constants instead of remaining a root area.
* Normalized source-plasma absorption internals: resonance, damping, and
  oscillator strength are no longer primitive roots. Resonance derives from a
  resonance-to-drive ratio times drive angular frequency, damping derives from
  resonance over quality factor, and oscillator strength derives from source
  proton count times participating-electron and sum-rule fractions. At that
  point the intermediate boundary was `source_plasma_absorption_resonance_to_drive_ratio`,
  `source_plasma_absorption_quality_factor`,
  `source_plasma_absorption_participating_electron_fraction`, and
  `source_plasma_absorption_sum_rule_fraction`.
* Added medium intercomponent geometry closure: A/B effective intercomponent
  radii now derive from medium nuclear radius coefficient, component isotope
  mass numbers, and local radius scale factors; residual intercomponent gap now
  derives from a gap fraction over the summed effective radii.
* Split the source-plasma operating-state closure into
  `physical_lithography_plasma_drive.py`,
  `physical_lithography_plasma_absorption.py`,
  `physical_lithography_plasma_overlap.py`, and
  `physical_lithography_plasma_electron_state.py` behind the compatibility
  shim `physical_lithography_plasma_state.py`; `large_scope_files` remains 0.
* Tightened resolver variant-selector hygiene: typoed selector variables,
  non-variant selector variables, bad variant keys, and missing VARIANT keys
  now fail explicitly; valid unused selectors remain composable for presets,
  and constraint helper evaluation respects selected variants.
* Hardened expression-LHS constraints: relations such as `x + y <= z` now wire
  every registered LHS variable as a constraint owner, resolver diagnostics can
  discover and evaluate them, and raw unregistered LHS symbols are surfaced by
  audit instead of hiding outside RHS dependency scans.
* Extended unit checking to expression-LHS relations: `check_units=True` now
  infers dimensional units on both sides when the LHS is not a bare registered
  variable, so constraints and equations like `x + y <= z` can be validated.
* Hardened relation and CLI construction paths: value-defining relations now
  reject non-bare LHS orphan forms, variant keys are restricted to VARIANT
  roles, inequalities cannot masquerade as value variants, failed unit checks
  do not register invalid equations, presets freeze copied inputs, CLI resolve
  errors return clean nonzero statuses, and audit reports orphan value equations.
* Improved resolver constraint diagnostics: constraints attached to symbolic
  boundary variables are now reported, and constraint helper evaluation can
  resolve bounded local helper chains without expanding arbitrary subtrees.
* Snapshot after the source-plasma absorption path direction-cosine closure:
  16 systems, 1470 variables, 24 constants, 840 equations, 634 roots, 253
  leaves, 315 unit-checked equations, 558 variables with `sp_units`, 431
  variable references, 291 equation
  references, 19 multi-definition variables, and 224 tests.

## Pass 1: core (DONE)

Split `core.py` into a `core/` package:

* `core/registry.py`: Registry with O(1) symbol lookup via id-cache;
  `reset()` now clears per-Variable back-references; added `stats()`,
  `roots()`, `leaves()`, `by_scope()`, `by_name_prefix()`.
* `core/variable.py`: Variable with value_range, VariableKind enum
  (ROOT_INPUT, DERIVED, MEASURED, DEFINITIONAL), Extensivity enum
  (INTENSIVE, EXTENSIVE, NONE), tensor shape, structured Reference.
  Constant is now also value-immutable after construction.
* `core/equation.py`: added Inequality, Approximation, PiecewiseEquation,
  DifferentialEquation, IterativeEquation, StochasticRelation subclasses.
  Base Equation gained optional unit consistency check.
* `core/system.py`: unchanged, moved.
* `core/graph.py`: topological_sort, find_cycles (DFS-based),
  subgraph, to_dot (Graphviz export).
* `core/units.py`: dimensional consistency via sympy.physics.units with
  graceful fallback.
* `core/__init__.py`: re-exports so `from ..core import var, eq, System`
  still works in scope files.

Real bug caught immediately by the new cycle detection: thermal.dc.pue
and thermal.dc.total_power define each other. Noted for pass 18.

## Pass 2: constants.py (DONE)

Expanded from 10 to 23 Constants. Added:

* Electromagnetism: fine structure, conductance quantum, magnetic flux
  quantum, Von Klitzing.
* Thermodynamics: gas constant.
* Quantum / atomic: proton mass, atomic mass unit, Bohr radius, Rydberg
  energy, classical electron radius.
* Mechanical / environmental: standard gravity, standard atmosphere, ice
  point.
* Math helpers (not Constants, but useful): LN_2, LN_10, PI, E_MATH,
  TWO_PI.

All Constants now carry sp_units for the dimensional checker. Organized
into labeled sections. Sources converted to structured Reference
conceptually (kept source string for backwards compat).

## Pass 3: scopes/__init__.py (DONE)

Added authoritative `SCOPE_MODULES` load order list, `SCOPE_DESCRIPTIONS`
dict, and `loaded_scopes()` helper. Top-level `__init__.py` should be
refactored to iterate this in pass 20.

## Pass 4: physical.py (DONE)

Split the physical scope into focused helper modules while keeping the public
`gpu_stack.scopes.physical` import stable:

* `physical_semiconductor.py`: carrier transport, Einstein relation,
  velocity saturation, continuity, effective mass, signal-speed floor.
* `physical_mosfet.py`: oxide permittivity and `C_ox`, body effect, DIBL,
  channel-length modulation, piecewise triode/saturation/subthreshold model,
  gate tunneling leakage, subthreshold-swing floor inequality.
* `physical_interconnect.py`: geometry-derived wire area, distributed RC,
  via resistance, skin depth, AC resistance, crosstalk.
* `physical_cmos_logic.py`: fanout-derived load capacitance, Elmore delay,
  short-circuit power, Landauer floor, clock timing inequality.
* `physical_noise.py`: Johnson-Nyquist, shot noise, flicker PSD, stochastic
  voltage-noise relation.

Import and demo both still work after the split.

## Pass 5: memory_cell.py (DONE)

Expanded cell-level modeling substantially:

* SRAM: explicit 6T/8T/10T variants, read-port counts, area estimates,
  access-time decomposition, read and write energy, leakage power.
* SRAM stability: read disturb, read SNM, write internal node, WNM, and
  non-negativity constraints for both read and write margins.
* DRAM: charge sharing onto the bitline, sense-amplifier offset, gain,
  resolve time, log-normal retention distribution, lower-tail refresh guard.
* Flip-flops: setup, hold, clock-to-Q decomposition and metastability
  failure-rate / MTBF equations.

Import and demo both still work.

## Pass 6: memory_subsystem.py (DONE)

Added the machinery that turns named memory levels into actual subsystem
behavior:

* Register file occupancy limit, banked peak bandwidth, bank-conflict loss.
* Shared-memory and TMEM banked bandwidth, plus L1/SMEM carveout math.
* Cache organization: L1 bytes, line size, associativity, sets; L2 line size,
  associativity, partitions, sets per partition, miss penalty.
* HBM usable bandwidth and capacity after refresh, ECC overhead, and memory
  compression.
* TLB reach, huge-page mixing, translation latency, PCIe bandwidth, unified
  memory page migration cost, NUMA penalty ratios.
* Average global-load latency from cache hit rates plus translation overhead.

Import and demo both still work.

## Pass 7: precision.py (DONE, batch 7-11)

Expanded the format scope far beyond sign, exponent, and mantissa counts:

* Added unbiased exponent limits, smallest normal and subnormal values, largest normal value, NaN and infinity code counts, and a piecewise minimum-nonzero model that distinguishes subnormal support from flush-to-zero behavior.
* Added quantization step, round-to-nearest error variance, directional-rounding bias scales, stochastic-rounding variance, and a two-point stochastic relation whose mean matches the exact input.
* Added microscaling amortization with first-level and second-level scales, block floating point effective-bit accounting, dynamic fixed-point scale, TF32, INT8, INT4, posit useed, logarithmic-number-system relative error, FP16 loss scaling, and a symbolic Random Hadamard Transform block.

## Pass 8: parallelism.py (DONE, batch 7-11)

Turned the parallelism scope into an actual training-plan model:

* Added SP explicitly, while keeping it tied to TP by default so GPU count does not double-count sequence parallelism.
* Added batch decomposition, tokens-per-step math, activation-memory formulas, checkpoint keep fraction, recomputation FLOP multiplier, and ZeRO-1, ZeRO-2, and ZeRO-3 per-GPU memory breakdowns.
* Added CPU and NVMe offload transfer-time models, FSDP all-gather buffer sizing, GPipe, 1F1B, interleaved, DualPipe, Chimera, and zero-bubble schedule formulas.
* Added explicit TP payload and exposed-time formulas, MoE expert capacity and all-to-all payload, and CP ring-hop communication volume.

## Pass 9: architecture.py (DONE, batch 7-11)

Rebuilt the model-architecture scope around actual block structure:

* Added step tokenization from sequences times context length, GQA ratio, query-key scale, token embeddings, optional untied output projection, and dense-block parameter counts from attention, FFN, and normalization components.
* Added sinusoidal positions, RoPE frequency and angle, ALiBi bias, and a simple YaRN context-extension scale.
* Added explicit attention projection parameters, dense and sparse attention FLOP formulas, symbolic attention logits and outputs, KV cache for GQA and MLA, GeLU, SiLU, SwiGLU, LayerNorm, RMSNorm, and FFN parameter variants for MLP and gated blocks.
* Added encoder-decoder parameter split and MoE layer structure: expert params, shared experts, router params, capacity factor, load-balance loss, z-loss, and active-vs-total MoE FLOP accounting.

## Pass 10: arithmetic.py (DONE, batch 7-11)

Extended the arithmetic scope beyond one generic MMA path:

* Added Tensor Core issue efficiency and effective peak FLOPs per SM.
* Added structured-sparsity group size, surviving nonzeros, dense-equivalent speedup, and sparse peak FLOPs per SM.
* Added DP4A and DP2A instruction accounting with per-SM peak integer throughput.
* Added SFU operations per cycle, peak SFU throughput, and an SFU-limited lower bound on time per token for transcendental-heavy kernels.

## Pass 11: optimizer.py (DONE, batch 7-11)

Made optimizer scope materially more complete:

* Kept AdamW, but added SGD with momentum, Nesterov, RMSProp, LAMB, Lion, EMA, Shampoo state sizing, and distributed Shampoo sharding.
* Replaced the fake Muon placeholder with a real `IterativeEquation` carrying the Newton-Schulz polynomial map, plus explicit coefficients, residual, tolerance, and momentum input.
* Added learning-rate schedules for linear warmup, cosine decay, inverse square root, and warmup-stable-decay.
* Added dynamic loss scaling: scaled loss, unscaled gradient, overflow counting, stable-step tracking, and piecewise next-scale logic.

## Verification note after batch 7-11

* `python -c "import gpu_stack; print(gpu_stack.Registry.stats())"` succeeds.
* `python -m gpu_stack.demo` still runs.
* `python -m compileall -q gpu_stack` succeeds.
* `find_cycles()` is back to reporting only the known thermal cycle. During verification I found a second loop in `physical_semiconductor.py`, then broke it by making Ohm's law define an ohmic-drop variable instead of re-defining the externally applied voltage.

## Pass 12: gpu.py (DONE, batch 12-16)

Expanded the GPU scope from a handful of top-line specs into a package-level
aggregation layer:

* Added raw, effective, sparse, and power-limited GPU peak FLOPs.
* Added GPU-level DP4A, DP2A, and SFU throughput by aggregating per-SM paths.
* Added aggregate register-file, shared-memory, TMEM, L2, and HBM capacity and bandwidth.
* Added GPU-level aliases for PCIe, CXL, NVLink, and NIC bandwidth.
* Added compute, memory, and fabric power terms, total package power, TDP headroom, and a piecewise throttle factor when modeled power exceeds TDP.
* Added HBM sweep time, FLOPs-per-joule, bytes-per-joule, and roofline balance points in both directional forms.

## Pass 13: interconnect.py (DONE, batch 12-16)

Turned the interconnect scope into a topology-aware path model:

* Added packet payload vs header accounting, packet efficiency, nominal bandwidth, and effective bandwidth after protocol and fabric losses.
* Added hop count, hop latency, host-stack latency, message packet count, bandwidth-delay product, and a queueing approximation under load.
* Added separate NVLink-scale and scale-out alpha and beta parameters, rack bisection bandwidth, rails per GPU, and oversubscription-adjusted scale-out bandwidth.
* Updated the intra-vs-scale-out comparison to use effective rather than nominal throughput.

## Pass 14: kernel.py (DONE, batch 12-16)

Rebuilt the kernel scope around actual execution limits:

* Added separate bytes and arithmetic intensities for HBM, L2, shared memory, and registers.
* Added a generalized roofline as the minimum of compute and per-level bandwidth ceilings.
* Added lower bounds on time from compute, HBM, L2, shared memory, register traffic, and global-memory latency.
* Added CTA resource accounting from threads, registers, and shared memory, plus active-block and occupancy formulas.
* Added tiled GEMM tile-count, traffic, and arithmetic-intensity equations.
* Added attention-specific naive vs FlashAttention-style IO and arithmetic-intensity formulas.

## Pass 15: collective.py (DONE, batch 12-16)

Expanded collective modeling beyond one ring formula:

* Added ring, tree, and hierarchical AllReduce.
* Added ring and hierarchical AllGather and ReduceScatter.
* Added pairwise and hierarchical all-to-all, plus effective bandwidth for the selected variant.
* Added topology-aware helpers such as ranks per node, node count, and a latency crossover size.
* Added MoE all-to-all inflation from imbalance and overlap math for exposed async communication.

## Pass 16: training.py (DONE, batch 12-16)

Rewired the training scope into a full step-time model:

* Added dense and active-MoE step FLOPs, recomputation and optimizer-overhead multipliers, MFU, HFU, and FLOPs per token.
* Added data-parallel gradient-sync time, TP and EP exposed communication, CP overlap, and CPU / NVMe offload time.
* Added parameter, gradient, optimizer, and activation IO bytes per step, aggregate HBM traffic, and memory-bound time.
* Added pipeline-bubble, straggler, restart, and evaluation overhead fractions, plus nominal vs full step time.
* Added tokens per second, energy per step, energy per token, tokens per joule, wall-clock training time, and a Chinchilla-style parameter-to-token ratio.

## Verification note after batch 12-16

* `python -c "import gpu_stack; print(gpu_stack.Registry.stats())"` succeeds.
* `python -m gpu_stack.demo` still runs.
* `python -m compileall -q gpu_stack` succeeds.
* `find_cycles()` still reports only the known thermal cycle.
* The demo still prints `False` for one rack-FLOPs substitution example. This is the same pre-existing SymPy `Eq(...)` behavior noted in the earlier handoff, not a regression from batch 12-16.

## Pass 17: cluster.py (DONE, batch 17-21)

Expanded cluster scope from a count-only hierarchy into an actual deployment model:

* Added node composition, including local SSD count, local SSD bandwidth, CPU, DRAM, NIC, storage, and misc node-level power terms.
* Added node, rack, and site aggregates for peak FLOPs, power-limited peak FLOPs, usable HBM capacity, effective HBM bandwidth, local SSD capacity, local SSD bandwidth, and NIC bandwidth.
* Added storage-path and data-ingest modeling: bytes per sample, storage-to-loader efficiency, effective streaming bandwidth, maximum sustained sample rate, data-pipeline utilization, and a coarse lower bound on data stalls when demanded sample rate exceeds storage throughput.
* Added scheduler and provisioning delay variables for queue wait, allocation time, provisioning time, and total job start delay.
* Added reliability and fault-domain modeling: nodes per power domain, racks per fabric domain, node and rack hazard rates, site failure rate, site MTBF, checkpoint time, Young-style optimal checkpoint interval, checkpoint overhead fraction, lost-work fraction, recovery overhead fraction, and a reliability-only availability estimate.
* Added inter-site scale-across capacity and latency: WAN links per site, bandwidth per link, transport efficiency, per-site aggregate WAN bandwidth, per-GPU scale-across bandwidth, and representative inter-site transfer time.

## Pass 18: thermal.py (DONE, batch 17-21)

Rebuilt thermal scope into a proper package-to-facility thermal model and fixed the long-standing cycle:

* Deleted the old circular `pue <-> dc_total_power` graph pattern by keeping `thermal.eq.pue_definition` as the single definitional relation and redefining `thermal.eq.dc_total_power` as a component sum over IT power, cooling power, and facility overheads.
* Added package-path resistance components: die attach, TIM, spreader, cold plate, fluid film, case temperature, coolant inlet/outlet temperature, average coolant temperature, volumetric flow, required non-radiative heat removal, and thermal headroom.
* Added facility cooling-plant terms: pump power per GPU and per site, fan power, heat reuse, wet-bulb-driven free-cooling piecewise logic, chiller load, chiller power, cooling-tower auxiliary power, CDU power, humidity-control power, and total cooling power.
* Added environmental and sustainability terms: evaporation, blowdown, drift, total water-usage rate, WUE, dew-point headroom, condensation-margin inequality, and ASHRAE-style inlet and humidity inequalities.

## Pass 19: economics.py (DONE, batch 17-21)

Expanded economics from GPU amortization plus electricity into a full-site cost model:

* Added capex breakdowns for node CPU, DRAM, NIC, storage, chassis, rack switching, rack power distribution, cluster spine network, shared storage, building shell, power infrastructure, and cooling infrastructure.
* Added residual value, site depreciable base, site capex rate, site utilization, job share of cluster, fixed-cost allocation, and allocated job capex rate.
* Added energy and tariff detail: peak and off-peak prices, blended price, watt-second conversion, peak demand, monthly demand-charge allocation, water price, maintenance rate, staff rate, transit cost, carbon intensity, carbon-emission rate, and carbon cost rate.
* Reworked run accounting so run cost now includes capex allocation, power cost, water, maintenance, staff, network transit, capacity charges, and carbon cost, then reduces to cost per step, token, and delivered FLOP.
* Added finance and recovery terms: annual WACC, run discount factor, NPV of run cost, inference revenue per token, serving cost per token, net inference margin, and inference tokens required to recover the run cost.

## Pass 20: gpu_stack/__init__.py (DONE, batch 17-21)

Integrated the package around the authoritative scope-order list:

* Replaced the stale hand-written import sequence with iteration over `scopes.SCOPE_MODULES`.
* Bound imported scope modules into the top-level package namespace so `gpu_stack.<scope>` continues to work.
* Re-exported graph helpers like `topological_sort`, `find_cycles`, `subgraph`, and `to_dot` from the top level.

## Pass 21: demo.py (DONE, batch 17-21)

Updated the demo so it reflects the now-cycle-free integrated package:

* Added graph-health reporting with cycle detection and successful topological-sort summary.
* Added authoritative scope listing from `SCOPE_MODULES` and `SCOPE_DESCRIPTIONS`.
* Switched the rack peak-FLOPs substitution example to evaluate through the node-level equation so it now prints a numeric result instead of the old misleading symbolic output.
* Added a PUE solve demonstration that shows one equation can be solved in either direction without adding a second cyclic inverse equation.

## Verification note after batch 17-21

* `python -c "import gpu_stack; print(gpu_stack.Registry.stats())"` succeeds.
* `python -m gpu_stack.demo` succeeds.
* `python -m compileall -q gpu_stack` succeeds.
* `find_cycles()` now reports zero cycles.
* `topological_sort()` now succeeds across the full package.

## Pass 22: README.md and project audit (DONE)

Finished the last untouched file and added project-level planning docs:

* Rewrote `gpu_stack/README.md` to match the actual package structure, current counts, graph status, scope inventory, and current API surface.
* Added `IMPROVEMENT_MAP.md`, a repo-wide audit with measured findings, scope-by-scope improvement areas, and a split map for the largest files.
* Added `ROADMAP.md`, a sequenced plan that prioritizes semantic cleanup, tests, packaging, metadata coverage, modularization, a scenario resolver, and calibrated presets.
* Cleaned the working artifact so the final source bundle does not rely on checked-in `__pycache__` output.

## Pass 23: P0 foundation batch (DONE)

Landed all five P0 tickets from `ROADMAP.md` as one coherent batch. The pass does not add new variables or equations. It adds the semantic and verification spine that every later phase depends on.

* Added a `RelationRole` enum to `gpu_stack/core/equation.py` with four roles: `IDENTITY`, `CONSTRAINT`, `APPROXIMATION`, and `VARIANT`. Each Equation subclass carries a `default_role` class attribute so `Equation` defaults to identity, `Inequality` to constraint, and `Approximation` to approximation. Every Equation constructor accepts optional `role` and `variant` keyword arguments. The top-level `eq()` factory forwards both.
* Fixed `Inequality.as_sympy()` to construct the relational with `evaluate=False` so `snm_read >= 0` no longer collapses to `True` under symbol-level positivity assumptions. Added diagnostic helpers `is_trivially_true()` and `is_trivially_false()` that deliberately invoke the evaluating form when a caller explicitly wants the reduced answer.
* Dropped the `positive=True` default on `memcell.sram.snm_read` and `memcell.sram.wnm_write` so the two SRAM margin constraints now carry real semantic force. A failed memory-cell design can produce a negative margin, which is exactly the case the constraints are supposed to detect.
* Added role-filtered accessors on `Variable`: `identities()`, `constraints()`, `approximations()`, and `variants(key=None)`. The flat `_defined_by` list is unchanged, so existing code paths still work.
* Tagged the four variant multi-definition variables with explicit roles. `opt.eq.adam_step` and `opt.eq.muon_step` now register with `role=VARIANT` and `variant="adamw"` / `variant="muon"`. `training.eq.flops_step_dense` / `_moe`, `training.eq.mfu` / `_from_time`, and `training.eq.scaling_params_dense` / `_moe` are tagged the same way with keys `dense`, `moe`, `from_flops`, and `from_time`. The remaining eleven multi-definition cases from `IMPROVEMENT_MAP.md` pick up their correct roles automatically from the subclass defaults.
* Added `pyproject.toml` at the repo root with PEP 621 metadata, `sympy>=1.12` as the single runtime dependency, `pytest>=7` as an optional dev dependency, and a pytest ini section that scopes collection to `tests/`.
* Added a `tests/` directory with five files. `test_import.py` asserts the registry snapshot (16 systems, 1147 variables, 23 constants, 620 equations) and verifies every scope module loaded. `test_graph_health.py` asserts zero cycles and a topological order that covers every variable. `test_demo.py` runs `python -m gpu_stack.demo` as a subprocess and asserts exit zero. `test_relation_roles.py` regresses the Phase 0 fixes: the two SRAM margin constraints return `Relational`, not `S.true`, and all fifteen multi-definition variables decompose into the expected role counts.

Post-batch verification:

* `python -c "import gpu_stack; print(gpu_stack.Registry.stats())"` still prints 1147 / 23 / 620 / 16.
* `python -m gpu_stack.demo` succeeds.
* `python -m compileall -q gpu_stack` succeeds.
* `find_cycles()` returns an empty list, `topological_sort()` covers all 1147 variables.
* `pytest -q` passes (13 tests).

## Pass 24: cluster.py split (DONE)

Phase 3 modularization of the largest scope file. `cluster.py` was 1115 lines carrying node, rack, site, scheduler, storage, reliability, and hyperscaler content in one slab. The pass follows the split map in `IMPROVEMENT_MAP.md` and the aggregator pattern already established by `physical.py`.

* `cluster_node.py`: node composition (GPUs, CPU, DRAM, NIC, local SSD, node-level powers) plus node aggregates.
* `cluster_rack.py`: rack composition and aggregates, intra-rack fabric balance, and the nodes-per-power-domain unit consumed by rack-level failure modeling.
* `cluster_site.py`: site aggregation, scheduler and provisioning overhead, and hyperscaler scale-across WAN capacity and latency.
* `cluster_storage.py`: bytes-per-sample, loader efficiency, storage-path sample rate, and stall-fraction estimate.
* `cluster_reliability.py`: exponential-failure hazard rates, site MTBF, checkpoint timing, Young-style optimal interval, and reliability-only availability.

The public `gpu_stack.scopes.cluster` import is unchanged. `cluster.py` is now a thin aggregator that creates `sys_cluster`, concatenates `CLUSTER_*_VARIABLES` and `CLUSTER_*_EQUATIONS` tuples from the helpers, and registers them. Registry counts unchanged at 1147 / 23 / 620 / 16, zero cycles, topological sort covers all 1147 variables, and the 13 pytest tests still pass.

## Pass 25: architecture.py split (DONE)

Phase 3 modularization of the second-largest scope file. `architecture.py` was 1083 lines carrying core dimensions, embeddings, positional encoding, attention, activations, normalization, FFN, encoder-decoder, and MoE in one slab. Split per the `IMPROVEMENT_MAP.md` split map.

* `architecture_embeddings.py`: core dimensions, step tokenization, embedding parameters, and per-layer attention, FFN, and normalization parameter counts that roll up to block and dense totals.
* `architecture_positions.py`: sinusoidal, RoPE, ALiBi, and YaRN positional encoding.
* `architecture_attention.py`: attention math, QK scale, attention FLOP accounting, KV cache for MHA, GQA, and MLA, activation functions, and normalization.
* `architecture_ffn.py`: FFN FLOPs per layer and per token, dense-model step FLOPs, and the encoder-decoder parameter split.
* `architecture_moe.py`: MoE routing, expert capacity, load-balance and z-loss, total and active MoE parameter counts, and MoE step FLOPs.

`architecture.py` is now a thin aggregator. Registry counts unchanged at 1147 / 23 / 620 / 16, zero cycles, topological sort covers all 1147 variables, and pytest -q still passes.

## Pass 26: scenario resolver (DONE)

Phase 4 P1 landed as `gpu_stack/core/resolver.py` plus a new `tests/test_resolver.py`. The resolver takes a target Variable plus a dict of scenario assignments, walks the dependency cone in topological order, substitutes values equation by equation, and returns a `ResolverResult` with the target value, equation trace, computed intermediate values, missing roots, constraint checks, and approximation-validity checks for approximation relations used in the trace. It respects the Phase 0 relation-role semantics: IDENTITY wins by default, VARIANT relations require a caller-supplied selector, APPROXIMATION is used only when there is no IDENTITY, and CONSTRAINT relations are never used as defining relations.

Public API: `gpu_stack.resolve(target, assignments={}, variants={})`, `ResolverResult`, `TraceStep`, `ConstraintCheck`, and `ApproximationValidityCheck`. Errors: `Underdetermined` when a needed variable has no assignment and no usable defining relation, `AmbiguousVariant` when multiple relations match without a selector.

Smoke check: resolving `cluster.rack.peak_flops` from `n_nodes=9`, `n_gpus_per_node=8`, and `gpu.peak_flops=15e15` yields 1.08e18 FLOPs and emits a five-step trace including the arith-path identities and the cluster-level rack FLOPs equation. Test suite is now 22 passing.

## Pass 27: scenario preset framework (DONE)

Phase 5 groundwork. Adds `gpu_stack/core/presets.py` with a frozen `Preset` dataclass that bundles scenario assignments, variant selections, and provenance, plus a `combine()` helper that merges presets with later-wins precedence on key collisions. Preset construction validates every variable name against the Registry so typos fail fast rather than silently drifting through a resolver call.

The new `gpu_stack.presets` package ships three helper modules. The only numeric preset is `hardware.demo_rack`, drawn verbatim from `gpu_stack.demo` so no new unsourced numbers enter the codebase. The workload module carries variant-selector presets for dense vs MoE, MFU formulation, and AdamW vs Muon. Combining a hardware preset with a workload selector through `combine_presets` lets the resolver evaluate a training-level target in one call.

`tests/test_presets.py` covers unknown-name rejection, end-to-end resolution (`demo_rack` produces 1.08e18 FLOP/s for `cluster.rack.peak_flops`), combine ordering, variant pinning, and `with_overrides`. The test suite is now 29 passing.

## Pass 32: gpu-stack CLI + roadmap status refresh (DONE)

Adds `gpu_stack/cli.py` with three subcommands: `stats` (Registry counts plus the coverage report from pass 30), `list-presets` (enumerates every `Preset` instance under `gpu_stack.presets.*`), and `resolve TARGET` (scenario evaluation accepting `--assign`, `--variant`, and repeatable `--preset` flags, with `--trace` and `--missing` for diagnostics). `pyproject.toml` registers `gpu-stack = "gpu_stack.cli:main"` as a console script. `tests/test_cli.py` exercises stats, list-presets, inline assignments, preset-driven resolution reproducing the 1.08 EFLOP/s demo number, trace output, and unknown-preset errors. Also refreshes `IMPROVEMENT_MAP.md` to track the split-map progress.

## Pass 33: training.py split (DONE)

Phase 3 modularization continues. `training.py` was 845 lines carrying the full step-time model. Split into `training_compute.py` (step FLOPs and their VARIANTs, peak aggregates, MFU / HFU variants; foundation), `training_comm.py` (DP / TP / EP / CP exposed comm), `training_memory.py` (parameter / gradient / optimizer / activation IO, memory-bound time), `training_overheads.py` (bubble, straggler, restart, eval overhead, full step time), and `training_scaling.py` (tokens/s, energy, wall clock, Chinchilla ratio with the two VARIANT scaling_params equations).

## Pass 34: precision.py split (DONE)

`precision.py` was 801 lines carrying IEEE-754 structure, rounding models, microscaling, and low-bit formats. Split into `precision_ieee.py` (bits, bias, normal / subnormal / NaN / Inf structure; foundation), `precision_rounding.py` (quantization step, RN / RZ / RP / RM, stochastic rounding StochasticRelation), `precision_microscaling.py` (MXFP4 / NVFP4 scales, block floating point, dynamic fixed-point), and `precision_lowbit.py` (TF32, INT, posit useed, LNS, FP16 loss scaling, Random Hadamard Transform).

## Pass 35: gpu.py split (DONE)

`gpu.py` was 797 lines carrying compute, memory, IO, and power aggregation for one GPU package. Split into `gpu_compute.py` (SM count, Tensor Core count, raw / effective / sparse / power-limited peak FLOPs, DP4A, DP2A, SFU; foundation), `gpu_memory.py` (register file, shared memory, TMEM, L2, HBM capacity and bandwidth at package level), `gpu_io.py` (PCIe, CXL, NVLink, NIC bandwidth aliases), and `gpu_power.py` (compute / memory / fabric power, TDP headroom, throttle factor, HBM sweep, energy efficiency, roofline balance points).

## Pass 36: thermal.py split (DONE)

`thermal.py` was 793 lines carrying package-path thermals, liquid loop, facility cooling, and environmental constraints. Split into `thermal_package.py` (die attach / TIM / spreader / cold plate / fluid film resistances, case and junction temperatures, thermal headroom), `thermal_liquid.py` (coolant flow, sensible-heat relation, pump and CDU power), `thermal_facility.py` (fan power, chiller, cooling tower, humidity control, free-cooling piecewise, `pue_definition` and `dc_total_power` component sum preserving the pass 18 cycle fix), and `thermal_env.py` (water balance, WUE, dew-point headroom, condensation margin, ASHRAE CONSTRAINT inequalities).

## Pass 37: kernel.py split (DONE)

`kernel.py` was 775 lines carrying roofline, CTA occupancy, tiled GEMM, and attention IO modeling. Split into `kernel_roofline.py` (per-level bytes and arithmetic intensities, generalized roofline, compute / HBM / L2 / SMEM / register / latency time lower bounds; foundation), `kernel_occupancy.py` (CTA resource accounting, active-block / occupancy / latency-hiding, and the downstream step-time aggregates that depend on occupancy), `kernel_gemm.py` (tiled GEMM tile counts, traffic, AI), and `kernel_attention.py` (naive vs FlashAttention IO and AI). An unused `n_sms` import from `.gpu` is dropped rather than carried into a helper.

## Pass 38: memory_subsystem.py split (DONE)

`memory_subsystem.py` was 752 lines carrying register file, shared memory, caches, HBM, and virtual-memory path modeling. Split into `memory_regfile.py` (array clock, warp size, threads per SM, register-file capacity and bandwidth; foundation), `memory_smem.py` (SMEM / TMEM bandwidth, L1 / SMEM carveout), `memory_cache.py` (L1 / L2 organization and miss penalty, average global-load latency assembly), `memory_hbm.py` (usable HBM bandwidth and capacity after refresh, ECC, compression), and `memory_virtual.py` (TLB, huge pages, translation latency, PCIe / CXL, unified memory migration, NUMA penalties).

## Pass 39: parallelism.py split (DONE, final Phase 3 split)

`parallelism.py` was 703 lines carrying SP, batching, activation memory, ZeRO, FSDP, pipeline schedules, and TP / EP / CP communication. Split into `parallelism_batching.py` (SP, batch decomposition, tokens-per-step, activation memory, recomputation, and the `n_params` Variable that `optimizer_first_order.py` imports directly; foundation), `parallelism_zero_fsdp.py` (ZeRO-1 / 2 / 3, FSDP all-gather, CPU / NVMe offload), `parallelism_pipeline.py` (GPipe, 1F1B, interleaved, DualPipe, Chimera, zero-bubble), and `parallelism_moe.py` (TP payload and exposed-time, MoE capacity and all-to-all, CP ring-hops). With this pass every file in the IMPROVEMENT_MAP.md split map is processed; Phase 3 modularization is complete.

## Stats trajectory

| After pass | variables | constants | equations | systems |
|-----------:|----------:|----------:|----------:|--------:|
| 0 (initial)|       314 |        10 |       113 |      16 |
| 1 (core)   |       314 |        10 |       113 |      16 |
| 2 (const)  |       327 |        23 |       113 |      16 |
| 3 (scopes) |       327 |        23 |       113 |      16 |
| 4 (physical)|      398 |        23 |       160 |      16 |
| 5 (memcell)|       453 |        23 |       193 |      16 |
| 6 (memsub) |       518 |        23 |       216 |      16 |
|11 (batch 7-11)|      775 |        23 |       363 |      16 |
|16 (batch 12-16)|     959 |        23 |       512 |      16 |
|21 (batch 17-21)|    1147 |        23 |       620 |      16 |
|22 (docs + audit)|    1147 |        23 |       620 |      16 |
|23 (P0 foundation)|  1147 |        23 |       620 |      16 |
|24 (cluster split)|  1147 |        23 |       620 |      16 |
|25 (arch split)|     1147 |        23 |       620 |      16 |
|26 (resolver)|       1147 |        23 |       620 |      16 |
|27 (presets)|        1147 |        23 |       620 |      16 |
|28 (optimizer split)| 1147 |        23 |       620 |      16 |
|29 (economics split)| 1147 |        23 |       620 |      16 |
|30 (metadata helpers)| 1147 |       23 |       620 |      16 |
|31 (memcell split)|  1147 |        23 |       620 |      16 |
|32 (CLI)|            1147 |        23 |       620 |      16 |
|33 (training split)| 1147 |        23 |       620 |      16 |
|34 (precision split)| 1147 |        23 |       620 |      16 |
|35 (gpu split)|      1147 |        23 |       620 |      16 |
|36 (thermal split)|  1147 |        23 |       620 |      16 |
|37 (kernel split)|   1147 |        23 |       620 |      16 |
|38 (memsub split)|   1147 |        23 |       620 |      16 |
|39 (parallelism split)| 1147 |      23 |       620 |      16 |
|current (physical boundary hardening + sourced scenarios + metadata sweep)| 1517 | 24 | 959 | 16 |
