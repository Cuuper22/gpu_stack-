
## Current entrypoint, May 6 2026

Use this section first. The older audit notes below are historical context and
many of their P0 items have already been repaired.

Latest verified wave: `live next-work compass and scenario-audit
missing-family ergonomics` is implemented, full-verified, read-only verified,
and source-clean. It added the `gpu_stack.next_work` API
(`NextWorkPlan`, `NextWorkItem`, and `build_next_work_plan(...)`), the
`next-work` CLI with `--json`, aggregate
`ScenarioReport.missing_family_summaries`, and `scenario-audit
--missing-families` text output. Runtime remained capped at six live workers,
so the wave used bounded write lanes plus the `AGENT_GITLOG.md` pseudo-git
ledger.

Previous verified wave: physical root-debt boundary hardening is implemented,
full-verified, read-only verified, and source-clean. Keep the same rule for
future physical work: decompose roots only where real lower-level physics
exists, and otherwise preserve explicit calibration or operating boundaries.

Current graph snapshot:

* `16` systems
* `1517` variables
* `24` constants
* `959` equations
* `619` root inputs
* `253` leaves
* `0` cycles
* `1517` topological order length
* `1428` non-constant variables with `sp_units`
* `1324` non-constant variables with references
* `878` equations with references
* `799` equations with unit checks
* `53` multi-definition variables
* `619` ROOT_INPUT / `874` DERIVED / `0` MEASURED / `24` DEFINITIONAL variables
* `639` collected pytest tests

Compact verification loop:

```bash
python -m gpu_stack.cli verify --profile fast
python -B -m gpu_stack.cli verify --profile fast --read-only
python -m gpu_stack.cli root-debt --scope physical --limit 20
```

Use the full gate before handoff or after broad graph changes:

```bash
python -m gpu_stack.cli verify --profile full
```

`verify` enforces per-gate timeout budgets (`120s` for fast, `300s` for full)
and reports a timeout as the named gate failure. Use `--gate-timeout SECONDS`
to override or `0` to disable when intentionally debugging a hang. Use
`--read-only` when you want verifier child gates to avoid bytecode/cache
artifacts; launch the parent command with `python -B -m ...` too for a
fully bytecode-suppressed invocation. The full profile swaps `compileall` for
an in-memory syntax gate in that mode.

Coordination style: keep chat summaries short. Use `AGENT_WORKLOG.md` as the
pseudo-git-log ledger for durable worker actions. Use `SESSION_STATE.md` and
`VISIBLE_BACKLOG.md` as fast resume files. Prefer `verify` over separately
pasting pytest, compile, audit, and demo output. When a gate times out, record
the profile, gate name, timeout budget, elapsed time, and whether a retry
passed. Use `AGENT_DIARY.md` for subjective session texture and `rest_breaks/`
for non-operational break notes.

Recent completed slices:

* Live next-work compass and scenario-audit missing-family ergonomics are
  integrated, full-verified, read-only verified, and source-clean. New surfaces:
  `gpu_stack.next_work`, `build_next_work_plan(...)`, `NextWorkPlan`,
  `NextWorkItem`, `next-work`, `next-work --json`,
  `ScenarioReport.missing_family_summaries`, and
  `scenario-audit --missing-families`. New test files include
  `tests/test_next_work.py`, `tests/test_next_work_continuation_contract.py`,
  and `tests/test_scenario_audit_text_family_index.py`. Focused parent pack
  passed: `11 passed in 20.82s`. Broader CLI/preset/next-work pack passed:
  `111 passed in 45.31s`. Full pytest passed: `639 passed in 102.03s`.
  Audit gate passed with `16` systems, `1517` variables, `24` constants,
  `959` equations, `619` root inputs, `253` leaves, `0` cycles, `0` hard
  failures, `0` large scope files, and `7` large project files. Full verifier
  passed 4/4 in 107.69s; read-only full verifier passed 4/4 in 95.58s; final
  source-clean check reports
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0 ruff_cache_dirs=0`. Current
  `next-work` evidence: Pythia `cost_per_token` has 33 missing inputs; top
  root-debt family is `physical.lithography.medium` with weight 3014 across 15
  roots; metadata gaps are 65 variables without `sp_units`, 169 variables
  without references, 81 equations without references, and 160 equations
  without unit checks.

* Physical root-debt boundary hardening is integrated, full-verified,
  read-only verified, and source-clean. It added MOSFET effective-width,
  ideality, oxide/EOT, channel-count, CLM, and gate-tunneling boundary
  coverage; interconnect route-detour, route-length, hop-count, pitch, and
  fill-factor coverage; process-geometry boundary diagnostics; lithography
  source/species positive mass-number and inventory diagnostics;
  source-plasma drive boundary coverage; medium intercomponent and
  medium-response boundary/validity coverage; SEMF/nuclear coefficient
  boundary tests; import/CLI/root-debt smoke tests; and the `AGENT_GITLOG.md`
  pseudo-git coordination ledger. Focused parent pack passed:
  `125 passed in 33.75s`. Full pytest passed: `628 passed in 71.99s`.
  Audit gate passed with `16` systems, `1517` variables, `24` constants,
  `959` equations, `619` root inputs, `253` leaves, `0` cycles, `0` hard
  failures, `0` large scope files, and `7` large project files. Full verifier
  passed 4/4 in 73.38s; read-only full verifier passed 4/4 in 75.17s; final
  source-clean check reports
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0 ruff_cache_dirs=0`.

* Scenario-audit selector/report ergonomics are integrated, full-verified, and
  source-clean. `SCENARIO_TARGET_SETS` plus `scenario_targets_for(...)`
  centralize advertised scenario targets; `scenario-audit --preset` audits
  selected packs; `scenario-audit --target [LABEL=]VARIABLE` overrides
  advertised targets; `ScenarioReport` exposes target-level ok/issues/error
  counts and label tuples; and `root-debt --json` covers flat and
  family-grouped root-debt outputs. The default sourced scenario audit still
  reports the known `33` Pythia cost-per-token missing-root issues. Focused
  selector/report/root-debt pack passed: `112 passed in 25.94s`. Full pytest
  passed: `548 passed in 69.71s`. Audit gate passed with `16` systems,
  `1517` variables, `24` constants, `954` equations, `619` root inputs,
  `253` leaves, `0` cycles, `0` hard failures, `0` large scope files, and
  `7` large project files. Full verifier passed 4/4 in 72.95s; read-only full
  verifier passed 4/4 in 80.75s; final source-clean check reports
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

* `scenario-audit` base CLI is integrated, full-verified, and source-clean. It audits
  `scenarios.SOURCED_SCENARIO_PACKS`. It evaluates advertised target sets via
  `Preset.evaluate_targets(...)`, supports text and `--json` output, and
  `--fail-on-issues` returns nonzero when any sourced scenario target has
  issues. Current known issue count: `33`, from the Pythia cost-per-token
  target's missing economics/thermal roots. Focused CLI tests passed:
  `3 passed, 47 deselected in 8.87s`. Broader focused pack passed:
  `90 passed in 25.92s`. Full pytest passed:
  `536 passed in 68.00s`. Audit gate passed with `16` systems,
  `1517` variables, `24` constants, `954` equations, `619` root inputs,
  `253` leaves, `0` cycles, `0` hard failures, `0` large scope files, and
  `7` large project files. Full verifier passed 4/4 in 70.64s; read-only full
  verifier passed 4/4 in 76.89s; final source-clean check reports
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

* Structured scenario artifact wave is integrated, full-verified, and
  source-clean. New surfaces: `Preset.evaluate_targets(...)`,
  `ScenarioReport`, `ScenarioTargetReport`, `MissingFamilySummary`, and
  `scenario-report --json`. Focused pack passed:
  `87 passed in 15.88s`. Full pytest passed:
  `533 passed in 73.54s`. Audit gate passed with `16` systems,
  `1517` variables, `24` constants, `954` equations, `619` root inputs,
  `253` leaves, `0` cycles, `0` hard failures, `0` large scope files, and
  `7` large project files. Full verifier passed 4/4 in 65.34s; read-only full
  verifier passed 4/4 in 73.22s; final source-clean check reports
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`. SEMF numeric defaults remain
  blocked by source and semantics; cited scenario expansion and model expansion
  remain open.

* Diagnostics / provenance wave is integrated, full-verified, and source-clean.
  `resolve --missing-families` is implemented and verified; family diagnostics
  now cover scenario-report, root-debt, and resolve missing-frontier views.
  Focused integration pack passed:
  `167 passed in 15.68s`. Full pytest passed:
  `528 passed in 55.75s`. Audit gate passed with `16` systems,
  `1517` variables, `24` constants, `954` equations, `619` root inputs,
  `253` leaves, `0` cycles, `0` hard failures, `0` large scope files, and
  `7` large project files. Full verifier passed 4/4 in 59.88s; read-only full
  verifier passed 4/4 in 66.30s; final source-clean check reports
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`. Model expansion and numeric
  SEMF defaults remain future work until sourced/calibrated values exist.

* Previous six-lane backlog wave is integrated, full-verified, and source-clean.
  It added `scenario-report --missing-families`, refined unresolved-input family
  buckets for economics roots, added
  `scenarios.euv_tin120_lpp_source_context_assumption`, hardened SEMF preset
  factory tests without publishing unsourced coefficients, locked root-debt
  determinism, gas/thermal boundary semantics, medium-response domain
  propagation, and preset export/discovery coverage. Focused integration pack
  passed: `142 passed in 9.57s`. Full pytest passed:
  `488 passed in 56.49s`; full verifier passed 4/4 in 57.47s; read-only full
  verifier passed 4/4 in 62.22s; final source-clean check reports
  `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`. Runtime accepted six live
  workers at a time; extra requested lanes were queued as workers completed.

* Previous preset/reporting wave is integrated, full-verified, and source-clean.
  It added `gpu-stack scenario-report`, `materials.source_tin_120`,
  `gpu_stack.presets.lithography`, `gpu_stack.presets.nuclear`, richer
  unresolved-input boundary diagnostics, and stricter medium-response boundary
  tests. Full pytest passed: `455 passed in 53.03s`; full verifier passed 4/4
  in 54.00s; read-only full verifier passed 4/4 in 55.39s; final source-clean
  check reports `cache_dirs=0 pyc_files=0`.

* Previous physical boundary-hardening wave is integrated, full-verified, and
  source-clean. It added named feasibility/calibration constraints for
  source-plasma detuning, focus half-space, pulse shape, peak intensity,
  gas/thermal state, source valence roots, medium optical response, and SEMF
  calibration roots. Full pytest passed: `432 passed in 44.83s`; full verifier
  passed 4/4 in 48.41s; read-only full verifier passed 4/4 in 49.69s; final
  source-clean check reports `cache_dirs=0 pyc_files=0`.

* Previous sourced scenario slice is integrated: NVIDIA H100 SXM / DGX H100
  hardware presets, EleutherAI Pythia-70M dense workload facts, EIA 2024 flat
  power-tariff presets, package inventory docs, and
  `scenarios.pythia_70m_dgx_h100_us_2024_industrial_power`. Focused integration
  pack passed: `52 passed in 3.22s`. Full pytest passed:
  `390 passed in 44.91s`; full verifier passed 4/4 in 45.77s; read-only full
  verifier passed 4/4 in 47.71s; final source-clean check reports
  `cache_dirs=0 pyc_files=0`.
* Broad parallel scenario, diagnostics, provenance, and metadata sweep is
  implemented and focused-test verified. Runtime accepted 6 live workers at
  once and rejected workers 7-8 with `agent thread limit reached`; workers
  owned disjoint implementation/test/doc slices rather than read-only reports.
  Full pytest after integration passed: `356 passed in 41.21s`. Full verifier
  passed 4/4 in 43.93s, read-only full verifier passed 4/4 in 45.72s, and
  final source-clean check reports `cache_dirs=0 pyc_files=0`.
* `scenarios.dense_training_cost_fixture` now resolves a synthetic
  dense-training cost path end to end: training step time, thermal/site power,
  job DC power, run power cost, total run cost, and cost/token.
* Resolver diagnostics now expose structured unresolved inputs and violated
  constraints through the resolver result, `resolve --missing`, and
  `resolve --diagnostics`.
* Materials presets now record provenance for the composition-only H2O fixture
  without assigning derived density or optical-response values.
* Metadata coverage is now broad across architecture, arithmetic, cluster,
  collective, economics, GPU, interconnect, kernel, memory, optimizer,
  parallelism, precision, thermal, and training scopes.
* Packing-density migration and strict invalid-packing CLI coverage are
  complete.
* Medium formula-unit packing length now derives from intercomponent geometry:
  `physical.eq.lithography_medium_formula_unit_packing_length_from_intercomponent_separation_scale`
  sets `ell_pack_litho_med = k_pack_linear_litho_med * r_inter_litho_med`.
  The remaining density-side root is
  `physical.lithography.medium_formula_unit_packing_length_scale_factor`, with
  `physical.ineq.lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity`
  enforcing `k_pack_linear_litho_med >= 1`.
* Source-plasma drive BPP waist semantics now distinguish the upstream
  pupil-plane reference radius from the downstream focused spot radius.
  `physical.lithography.source_plasma_drive_pupil_beam_fill_factor` is an
  explicit root constrained to `<= 1`, and
  `physical.eq.lithography_source_plasma_drive_beam_parameter_waist_radius_from_pupil_fill`
  derives `w_bpp = phi_pupil_fill * r_pupil`.
* Source-plasma far-field divergence now has an explicit acceptance-cone
  feasibility constraint:
  `physical.ineq.lithography_source_plasma_drive_far_field_divergence_within_acceptance`
  enforces `theta_div_drive_plasma_litho_src <= theta_accept_drive_plasma_litho_src`.
  Beam divergence remains a scenario root, but impossible drive optics now
  report a named resolver violation.
* Source-plasma operating-input feasibility constraints now bound the remaining
  fractional/angular primitive roots. Drive pulse duty factor, electron-heating
  fraction, and free-electron inventory charge fraction must be at most unity;
  far-field divergence half-angle must stay within the forward optical
  half-space (`theta_div_drive_plasma_litho_src <= pi/2`). These are
  constraint-only relations: pulse timing, heating coupling, ionization
  inventory, and beam divergence remain explicit scenario inputs.
* Earlier medium packing-length feasibility has been folded into the
  `medium_formula_unit_packing_length_scale_factor` root; the physical
  `medium_formula_unit_packing_length` is now derived rather than assigned
  directly.
* Audit now reports `large_project_files` across `gpu_stack/` and `tests/`
  in addition to `large_scope_files`. The signal is intentionally visible but
  not a hard failure yet: current audit reports `0` large scope files and `7`
  large project files at the 700-line threshold.
* Composition-only material presets now live under
  `gpu_stack.presets.materials`: hydrogen-1 and oxygen-16 source isotope
  presets plus an H2O formula-unit imaging-medium preset. These assign exact
  stoichiometry/quark-count roots only; binding, density, and optical response
  remain unassigned until sourced values are added. The CLI now lists and
  resolves them with `--preset materials.*`.
* Lithography imaging-medium feasibility constraints now make the binary
  formula-unit contract explicit: component A and B stoichiometric counts must
  each be at least one, and formula-unit packing fill factor must be at most
  unity. These remain constraints rather than value definitions, so invalid
  assignments resolve with named violations while roots stay assignable.
* Optimizer schedules now have explicit domain and horizon guards:
  schedule base learning rate is nonnegative, step/warmup/total/stable counts
  carry integer/positive or integer/nonnegative domains, and total scheduled
  steps must exceed warmup, exceed warmup plus WSD stable steps, and reach the
  current step. Integer domain checks now preserve `Mod(..., evaluate=False)`
  so fractional assignments are reported instead of simplified away.
* Kernel latency hiding now treats `eta_hide_k` as an occupancy efficiency
  `Min(1, occ / occ_full_k)` instead of an inverted penalty that made low
  occupancy reduce latency-bound time.
* Global medium relative permittivity now rejects the nonpositive
  Lorentz-Lorenz branch through approximation validity:
  `x_LL_litho_med > -1/2` and `x_LL_litho_med < 1`.
* Source nuclear mass, reduced mass, and reduced-mass ratio now carry explicit
  positive feasibility constraints. Negative nuclear mass from over-large
  binding energy and the singular `m_nuc = -m_e` reduced-mass case resolve with
  failed constraints instead of silently feeding invalid transition math.
* Lithography photon energy, source transition energy, photon frequency, source
  angular frequency, and exposure wavelength now carry positive domains.
  Nonpositive photon assignments are reported through domain checks, and
  singular relation evaluation no longer crashes on `zoo`.
* Imaging-medium mass density now derives from formula-unit packing length,
  packing fill factor, packing volume, and representative particle mass in
  `physical_lithography_medium_density.py`; `medium_number_density` still
  derives from mass density over particle mass. The main lithography bridge is
  back under the audit file-size threshold, and the Lorentz-oscillator
  polarizability validity now uses a structural off-resonance `ne()` predicate
  so equal source/resonance frequencies report violated approximation validity.
* Gate lithography `k1` now derives from strictly positive aerial-image
  contrast, resist/process latitude, mask-error amplification, and
  resolution-enhancement factors. Contact and metal feature `k1` values still
  inherit the gate baseline when feature-specific values are not assigned, and
  negative explicit `k1` assignments now surface as domain and
  approximation-validity violations instead of silently producing negative
  resolutions.
* Source and imaging-medium valence quark roots now carry positive-proton
  feasibility constraints: `U >= (D + 3)/2`, which is equivalent to derived
  proton count `Z >= 1`. This closes the neutron-only or zero-proton isotope
  hole while keeping the quark counts as explicit roots.
* Imaging-medium response roots moved from abstract fractions and ratios to
  material count and energy roots. `medium_polarizable_electron_fraction` now
  derives from polarizable electron count over formula-unit electron count,
  `medium_oscillator_sum_rule_fraction` derives from dominant oscillator
  electron count over polarizable electron count, and
  `medium_resonance_to_source_frequency_ratio` derives from medium resonance
  energy over exposure photon energy. The new roots are constrained by
  `N_pol <= N_formula`, `N_osc <= N_pol`, and `E_res > E_photon`.
* Source-plasma drive beam-parameter product and beam-quality factor now carry
  diffraction lower-bound constraints: `BPP >= drive_wavelength/pi` and
  `M2 >= 1`. These are feasibility constraints, not defaults; the graph still
  refuses to pretend every operating point is diffraction-limited.
* `physical.lithography.source_plasma_absorption_collision_orbital_radius`
  now derives from Bohr radius, ionization principal shell, and screened
  effective nuclear charge, and
  `physical.lithography.source_plasma_absorption_collision_cross_section`
  now derives from that orbital area. This closes the absorption collision
  cross-section root as a hydrogenic geometric damping scale, not as a full
  Coulomb-collision or pressure-broadening model.
* `physical.lithography.source_plasma_drive_rayleigh_range` now derives from
  focused spot radius, beam quality factor, and drive wavelength; 
  `physical.lithography.source_plasma_drive_confocal_length` derives as twice
  that Rayleigh range; and
  `physical.lithography.source_plasma_column_aspect_ratio` now derives from
  confocal length over the expanded column radius. This closes the column
  aspect root through optical focus geometry instead of a free scenario knob.
* `physical.lithography.source_plasma_drive_spot_axis_ratio` and
  `physical.lithography.source_plasma_drive_spot_area_fill_factor` now derive
  from circular/full-fill convention equations, so the default spot-shape factor
  is one without consuming scenario inputs.
* `physical.lithography.source_plasma_column_expansion_speed_factor` now derives
  as `sqrt(5/3)`, the monatomic heavy-species sound-speed factor relative to the
  existing source-species thermal speed scale. This is a convention-level
  acoustic expansion closure, not a full ambipolar plasma-expansion model.
* `physical.lithography.source_plasma_energy_loss_transport_speed_factor`
  now derives as
  `sqrt(source_plasma_species_particle_mass / physics.electron_mass)`. This
  closes the transport-factor root without feeding the electron-temperature
  chain back into itself; it is an electron thermal-speed scale at the
  source-species gas-temperature level, not a full non-equilibrium kinetics
  model.
* `physical.lithography.source_lower_principal_quantum_number` and
  `physical.lithography.source_upper_principal_quantum_number` are now derived
  from source proton count plus a transition principal-shell step.
* `physical.lithography.source_transition_principal_quantum_step` now derives
  from an adjacent-shell approximation (`Delta_n = 1`) in a small bridge module,
  so the transition-step root is closed without pushing electronic structure
  back over the large-file audit threshold.
* Shared SEMF-style nuclear binding calibration roots now feed both source and
  imaging-medium liquid-drop coefficient aliases. The current shared roots are
  `nuclear_binding_volume_coefficient`, `nuclear_binding_surface_coefficient`,
  `nuclear_binding_coulomb_coefficient`, `nuclear_binding_asymmetry_coefficient`,
  and `nuclear_pairing_gap_reference_energy`; source/medium-specific
  coefficient variables are now derived approximations rather than duplicated
  calibration roots.
* `physical.lithography.source_plasma_drive_beam_wavelength` now derives from
  ionization-edge energy and `source_plasma_drive_edge_detuning_ratio`, so the
  wavelength is no longer a root while off-resonance drive choice remains an
  explicit primitive boundary.
* `physical.lithography.source_plasma_drive_focus_f_number` now derives from
  the drive acceptance half-angle as `1 / (2 tan(theta_accept))`; focused-beam and spot equations now
  live in `physical_lithography_plasma_focus.py` and remain re-exported through
  `plasma_drive.py`.
* `physical.lithography.source_plasma_drive_numerical_aperture` now derives
  from objective pupil radius and focal length through an acceptance half-angle:
  `theta = atan(r_pupil / f_obj)` and `NA = sin(theta)`. The primitive focusing
  boundary moved from abstract NA to the drive optic geometry roots.
* `physical.lithography.source_plasma_drive_beam_quality_factor` now derives
  from beam-parameter product: `BPP = waist_radius * far_field_divergence_half_angle`
  and `M2 = pi * BPP / lambda`. The BPP reference radius now derives from drive
  pupil beam fill and effective pupil radius, leaving far-field divergence as
  the remaining angular beam-quality root.
* Main lithography optical constraints now bind acceptance half-angle to the
  forward optical half-space and numerical aperture to the imaging-medium
  refractive index.
* `physical.lithography.source_atomic_number` and
  `physical.lithography.source_isotope_mass_number` are now derived
  descriptors over derived source proton and neutron composition.
* `physical.lithography.source_proton_count` and
  `physical.lithography.source_neutron_count` are now derived from source
  valence up/down quark counts.
* Source valence up/down quark roots now carry non-negative proton/neutron and
  positive-proton feasibility constraints as root-owned inequalities
  `D <= 2U`, `U >= (D + 3)/2`, and `U <= 2D`, plus triplet integrality
  `(U + D) mod 3 = 0`.
* `physical.lithography.source_mass_number` now aliases the derived isotope
  mass-number descriptor before feeding the source nuclear binding path.
* `physical.lithography.source_ionization_partition_ratio` is now derived
  from ionization-edge same-shell degeneracy and active-shell capacity.
* `physical.lithography.source_ionization_principal_quantum_number` is now
  derived from the transition lower principal shell.
* `physical.lithography.medium_molar_mass` is now derived from a formula-unit
  rest-mass model using proton, neutron, electron, and binding-energy mass
  defect terms.
* imaging-medium formula-unit proton, neutron, and binding-energy totals are
  now derived from binary component stoichiometry, component isotope content,
  medium-specific liquid-drop component binding terms, and screened Coulomb
  attraction. Effective intercomponent charge, formula-unit pair count,
  charge-unit scale, and separation derive from stoichiometry plus
  formula-unit transfer electron count,
  nuclear-radius-derived A/B effective intercomponent radii, local radius scale
  factors, and `medium_intercomponent_gap_fraction`; intercomponent screening
  derives from formula-unit electron count, polarizable electron count, dominant
  oscillator electron count, resonance energy, molecular polarizability, local
  Lorentz-Lorenz response, and a polarizable-site density factor. Component
  proton/neutron counts, atomic numbers, isotope mass numbers, and component
  binding energies now derive from lower component variables with source-style
  feasibility constraints.
* shared liquid-drop coefficient roots now derive source and medium coefficient
  aliases, source/medium nuclear radius scale, saturation density, bulk binding
  density, surface tension, and symmetry-energy density before feeding binding
  terms.
* `physical.lithography.source_plasma_drive_power`,
  `source_plasma_absorption_efficiency`, `source_plasma_active_volume`,
  `source_plasma_energy_confinement_time`, and
  `source_plasma_free_electron_count` now derive from pulse period, period-derived
  repetition rate, drive pulse fluence, fluence-derived peak intensity, pulse
  duty factor, duty-derived pulse duration, trapezoid-derived pulse temporal shape, spot
  radius from detuning-derived drive wavelength, pupil/focal-derived acceptance angle,
  exact f-number, beam-parameter-product-derived beam quality, and Gaussian f-number
  waist coefficient, circular/full-fill spot-shape convention, spot area, shared gas-state,
  thermal-speed-derived radial expansion with expansion speed factor derived as `sqrt(5/3)`, Rayleigh/confocal-derived
  column aspect/radius/length, inverse-direction-cosine
  absorption path-shape closure, Lorentz-oscillator absorption cross-section,
  spatial/temporal drive-overlap closure, optical-depth, heating,
  acceptance-angle-derived absorption path direction cosine,
  direction-cosine energy-loss path geometry, source-species thermal-speed
  transport, mass-ratio-derived transport factor, and free-electron inventory charge fraction. Absorption
  resonance-to-drive ratio now derives from ionization-edge energy over drive
  photon angular energy, participating electron fraction derives from the
  ionization-edge shell population over source proton count, and the absorption
  sum-rule fraction derives from unfilled ionization-edge shell degeneracy.
  Absorption damping now derives from source species density, species thermal
  speed, and the hydrogenic orbital-area-derived
  `source_plasma_absorption_collision_cross_section`; quality factor derives
  back from resonance over that collision-broadened damping. The remaining
  absorption-specific primitive boundaries are operating and ionization-shell
  inputs around the edge model, not the collision cross-section itself. Electron
  temperature, free-electron density, mean kinetic energy, and Debye length
  remain downstream derived quantities.
* `source_plasma_drive_pulse_temporal_shape_factor` is no longer a root. The
  rise fraction remains the pulse-shape root, fall fraction derives from a
  symmetric-ramp convention, flat fraction derives as `1 - rise - fall`,
  temporal shape derives as `flat + 0.5*(rise + fall)`, and a constraint keeps
  the ramp fractions inside the pulse.
* `source_plasma_drive_peak_intensity` is no longer a root. It derives from
  `source_plasma_drive_pulse_fluence` divided by duty-derived pulse duration
  and the trapezoid temporal-shape factor. Pulse energy still uses derived peak
  intensity times spot area, pulse duration, and temporal shape.
* `source_plasma_absorption_path_direction_cosine` is no longer a root. It
  derives as `cos(source_plasma_drive_acceptance_half_angle)` under the current
  aligned-axis representative-ray approximation.
* `source_plasma_absorption_path_shape_factor` is no longer a root. It derives
  as the inverse of the derived absorption path direction cosine, and
  absorption path length still derives from that shape factor times column
  length.
* `source_plasma_drive_overlap_factor` is no longer a root. It derives from
  spatial overlap (transverse spot/column coverage, pointing, and active fill)
  and temporal overlap (energy-confinement-time-derived active lifetime,
  duration matching, and timing alignment).
* `gpu.sm.tile_area` is now derived from an SM area budget instead of a root
  tile knob.
* `cluster.node.*_power` roots are now decomposed into node BOM power
  components.
* facility CDU power and facility building/power/cooling capex are now tied to
  heat removal, design capacity, floor area, and unit-cost roots.
* facility UPS, transformer, lighting, and miscellaneous overhead power are now
  derived from load or rack-count coefficients.
* `physical.lithography.source_ionization_screening_constant` is now derived
  from ionization-edge shell screening counts.
* Lithography source shielding factors are now derived from limiting
  approximations: inner-shell screeners contribute `1`, same-shell screeners
  contribute `1/2`.
* gate `k1` is derived from process/optics factors, and feature k1 factors are
  derived from that gate baseline when feature-specific process-deck values are
  not assigned.
* imaging-medium formula-unit electron count is derived from proton count under
  a neutral-medium approximation.
* rack scale-out bandwidth is now decomposed through ToR port counts, port
  rates, efficiencies, downlink/uplink capacity, oversubscription, and
  bisection-aware site bandwidth.
* resolver evaluation now leaves unassigned deep dependency subtrees as
  symbolic boundaries, reports final symbolic boundaries in `missing`, uses
  RHS-only selected-equation dependencies for value traversal, and extends
  constraint helper variables shallowly, so full verification stays fast
  instead of expanding unrelated GPU/physical ancestry.
* resolver results now report approximation validity checks for approximation
  relations used in the trace, alongside constraint checks. Validity reporting
  is diagnostic: it records satisfied, violated, or symbolic regimes without
  making approximations ineligible during equation selection.
* approximation validity predicates that previously collapsed under positive
  SymPy assumptions are recovered into structural domain checks, and
  `gpu-stack audit` now reports `collapsed_approximation_validity` as a hard
  failure signal.
* `resolve` CLI strict-mode flags can return nonzero on violated constraints
  or violated approximation-validity checks; variable domain metadata is
  reported through resolver constraints; `verify --profile fast` now runs
  `tests/test_resolver.py` and the neutron-sensitive source-plasma trace test
  directly.

## Current weak points

Live audit now reports:

* `0` collapsed equations
* `0` collapsed approximation-validity predicates
* `0` orphan values
* `0` unresolved raw symbols
* `0` large scope files
* `7` large project files
* `0` hard failures
* `40` multi-definition variables

The remaining work is no longer the old framework-semantics fire. The main
debt is recursive decomposition: many scenario roots are now lower-level, but
still not first-principles. Current top physical root-debt items include:

* `physical.lithography.source_valence_down_quark_count`
* `physical.lithography.source_valence_up_quark_count`
* source-plasma pulse-period, drive pulse-fluence/duty, pulse rise with symmetric fall derived, drive edge-detuning ratio, drive objective pupil/focal roots, pupil beam fill factor, and beam divergence root
* source-plasma species pressure/temp roots
* source-plasma column expansion speed factor now derives as `sqrt(5/3)` from
  a monatomic heavy-species sound-speed convention, and column aspect now
  derives from drive Rayleigh/confocal length over expanded column radius
* source-plasma drive-overlap active fill, centroid offset, and timing offset
  now derive from ideal full-column, coaxial, and synchronized conventions;
  absorption collision cross-section now derives from a hydrogenic
  ionization-shell orbital area
* source-plasma electron-heating and free-electron inventory charge-fraction
  roots now carry explicit at-most-unity feasibility constraints; the
  energy-loss transport speed factor is now mass-ratio-derived
* shared SEMF liquid-drop Coulomb, volume, surface, asymmetry, and pairing-gap roots
* imaging-medium component valence up/down quark roots
* imaging-medium component stoichiometry roots
* formula-unit intercomponent charge-transfer count, A/B intercomponent radius scale factors, `medium_intercomponent_gap_fraction`, medium polarizable-electron count, dominant oscillator electron count, medium resonance energy, and intercomponent polarizable-site density roots
* `medium_formula_unit_packing_length_scale_factor` and `medium_formula_unit_packing_fill_factor`
* gate `k1` process-factor roots: aerial-image contrast, resist/process
  latitude, mask-error amplification, and resolution enhancement
* signed process-geometry biases can now produce negative derived dimensions
  numerically, but those scenarios report violated positive/nonnegative
  feasibility constraints instead of passing silently

Historical note: oversized scope files used to be a problem. The current audit
reports **0** scope files above the 700-line threshold after the source-plasma
state, focused-beam, medium-response, and medium-density layers were split
behind stable shims.
The broader project-file audit now reports **7** Python files above that
threshold across `gpu_stack/` and `tests/`; those are visible cleanup debt, not
hard failures yet.

## Historical action items from an earlier audit

The list below is kept as archaeology, not as current truth. Verify against
`python -m gpu_stack.cli audit` before acting on any old count.

### P0, correctness and symbolic integrity

1. **Fix the `Variable` assumption API.**
   Change the constructor defaults so variables are not implicitly positive and non-integer unless that is explicitly intended.
   Done when:

   * default sign is unconstrained
   * default integrality is unconstrained
   * there is an explicit way to ask for nonnegative, integer, binary, signed, etc.

2. **Audit every current `positive=False` usage.**
   The historical audit found 35 such variables, and many were clearly meant to be “can be positive or negative,” not “must be nonpositive.”
   Done when each one is converted to the right domain.

3. **Build equations with `evaluate=False`.**
   Use non-eager SymPy relation construction in:

   * `Equation.as_sympy()`
   * `Inequality.as_sympy()`
   * any `Piecewise` conditions that must not fold away
     Done when model equations no longer render as `False` or `True` unless that is explicitly intended.

4. **Historical: repair the 29 collapsed equations.**
   Current audit reports `0` collapsed equations. Keep this list only as a
   regression map.
   Historical failures were:

   * `memcell.eq.sram6t_transistors`
   * `memcell.eq.sram8t_transistors`
   * `memcell.eq.sram10t_transistors`
   * `memcell.eq.sram6t_read_ports`
   * `memcell.eq.sram8t_read_ports`
   * `memcell.eq.sram10t_read_ports`
   * `memcell.eq.sram_read_margin_constraint`
   * `memcell.eq.sram_write_margin_constraint`
   * `precision.eq.inf_code_count`
   * `precision.eq.rn_mean_error`
   * `precision.eq.bytes_fp32`
   * `precision.eq.bytes_bf16`
   * `precision.eq.bytes_fp16`
   * `precision.eq.bytes_tf32`
   * `precision.eq.bytes_fp8`
   * `precision.eq.bytes_int8`
   * `precision.eq.tf32_man_bits`
   * `arch.eq.alibi_bias`
   * `arch.eq.layernorm_output`
   * `arch.eq.rmsnorm_output`
   * `arith.eq.int_ops_per_dp4a`
   * `arith.eq.int_ops_per_dp2a`
   * `opt.eq.muon_ns_input`
   * `opt.eq.muon_update`
   * `opt.eq.lion_direction`
   * `kernel.eq.blocks_limit_threads`
   * `kernel.eq.blocks_limit_regs`
   * `kernel.eq.blocks_limit_smem`
   * `thermal.eq.free_cooling_fraction`

5. **Historical: keep collapsed branch conditions and approximation validity fixed.**
   Current audit reports `0` collapsed equations. Keep these cases as
   regression targets:

   * `precision.eq.min_nonzero`, first branch collapses away
   * `opt.eq.loss_scale_next`, first two branches collapse away
   * `precision.eq.rht_outlier_spread`, validity must stay as `Abs(o_rht_in) > 0`
   * the two SRAM margin inequalities previously collapsed to `True`

6. **Add a binary / selector domain type.**
   `precision.subnormals.enabled` currently cannot represent “1 means enabled” correctly under its current assumptions.
   Done when flags can be modeled as `{0,1}` and categorical model choices can be represented cleanly.

7. **Keep subclass dependency wiring covered.**
   `variables_on_rhs()` now includes dependency-bearing subclass fields.
   Keep regression coverage for:

   * `Approximation.validity`
   * `IterativeEquation.initial`
   * `IterativeEquation.convergence`
   * `IterativeEquation.n_iter` when tied to a variable
   * `DifferentialEquation` independent-variable semantics, if those are part of the model
   * any extra symbolic fields in stochastic equations that matter for dependency tracing

8. **Fix the Muon iteration dependency bug.**
   Today `opt.muon.X` depends only on:

   * `opt.muon.ns_coeff_a`
   * `opt.muon.ns_coeff_b`
   * `opt.muon.ns_coeff_c`

   It does **not** depend on:

   * `opt.muon.ns_input`
   * `opt.muon.ns_tol`
   * `opt.muon.ns_iterations`

   That is wrong for both graph explanation and any future resolver.

9. **Historical: eliminate raw symbols that are not registry-backed variables.**
   Current audit reports `0` unresolved raw symbols. The old non-registry
   symbol list was:

   * `t` in `physical.eq.carrier_continuity`
   * `X_iter_ns_opt` in `opt.eq.muon_ns_iteration`
   * bare `r_ns_opt` in `opt.eq.muon_ns_iteration`
   * `I_ns_opt` in `opt.eq.muon_ns_residual`

   Action:

   * use actual `Variable.symbol` where the quantity is modeled
   * use `sp.Dummy` for internal iteration placeholders
   * use an explicit identity-matrix construct rather than a loose symbol
   * decide whether time is a modeled variable or a special differential coordinate

10. **Historical: add a registry rebuild/bootstrap path.**
    This is fixed by `gpu_stack.bootstrap()`. The old failure mode was:

    * initial import gives full stats
    * `Registry.reset()` clears everything
    * `importlib.reload(gpu_stack)` still leaves the registry empty

    Reset no longer needs to be terminal; use `gpu_stack.bootstrap()` to
    restore the full graph after `Registry.reset()`.

11. **Add regression tests for everything above.**
    Minimum test set:

    * none of the 29 equations render as bare booleans
    * none of the audited branch conditions collapse unintentionally
    * `opt.muon.X` dependency set includes the right variables
    * reset + rebuild restores the registry

---

### P1, semantic structure

12. **Introduce first-class relation roles.**
    The graph needs explicit distinction between:

    * identity
    * constraint
    * approximation
    * variant

    Right now those are conflated in “defining equations.”

13. **Historical: classify the original 24 multi-definition variables.**
This was the original audited list before later constraint hardening expanded
the current multi-definition set:

    * `physical.lithography.source_plasma_drive_pulse_duration`
    * `physical.lithography.source_plasma_drive_beam_parameter_product`
    * `physical.lithography.source_plasma_drive_beam_quality_factor`
    * `physical.lithography.source_plasma_drive_spot_area`
    * `physical.lithography.acceptance_half_angle`
    * `physical.lithography.numerical_aperture`
    * `physical.lithography.source_valence_up_quark_count`
    * `physical.lithography.medium_component_a_valence_up_quark_count`
    * `physical.lithography.medium_component_b_valence_up_quark_count`
    * `memcell.dram.refresh_period`
    * `memcell.dram.v_dev`
    * `memcell.sram.snm_read`
    * `memcell.sram.wnm_write`
    * `opt.param_next`
    * `physical.drift_velocity`
    * `physical.gate.elmore_delay`
    * `physical.mosfet.subthreshold_swing`
    * `physical.power.total_gate`
    * `thermal.env.dew_point_headroom`
    * `thermal.env.relative_humidity`
    * `thermal.t_ambient`
    * `training.flops_per_step`
    * `training.mfu`
    * `training.scaling_params`

14. **Add explicit variant selectors where the quantity truly has model families.**
    Immediate candidates:

    * optimizer family for `opt.param_next`
    * dense vs MoE for `training.flops_per_step`
    * dense vs MoE for `training.scaling_params`
    * analytic vs backsolved MFU for `training.mfu`
    * low-field vs saturated transport for `physical.drift_velocity`

15. **Separate constraints from definitions in variable back-references.**
    A variable should not treat “defined by” and “bounded by” as the same relation.

16. **Historical: add a scenario resolver.**
    This is live through `gpu_stack.resolve` and the CLI `resolve` command.
    The target was a single scenario object that can report:

    * a value
    * which equations were used
    * which inputs are missing
    * whether constraints and selected approximation-validity regimes were satisfied

17. **Add underdetermined / inconsistent / conflicting-model diagnostics.**
    That becomes essential once multiple relation types exist.

---

### P1, metadata, rigor, and provenance

18. **Populate `VariableKind` across the graph.**
    Current kind counts are `619` ROOT_INPUT, `874` DERIVED, `0` MEASURED,
    and `24` DEFINITIONAL. Continue using the framework support where
    semantics are still generic.

19. **Populate `Extensivity` across the graph.**
    Same issue. Aggregation-sensitive quantities should be labeled correctly.

20. **Start using `shape` for matrix/tensor quantities.**
    This matters especially in:

    * architecture
    * optimizer / Muon
    * kernel
    * parallelism

21. **Start using `value_range` or domain metadata.**
    Best first targets:

    * fractions in `[0,1]`
    * flags / selectors
    * temperatures and humidities with physical ranges
    * utilization terms

22. **Add `sp_units` to the high-value foundational variables.**

23. **Turn on `check_units=True` for curated equations.**
    Best first targets:

    * physical transport and circuit equations
    * memory bandwidth equations
    * GPU/package power equations
    * thermal power and flow equations
    * economics power-cost conversions

24. **Attach references to high-value variables and equations.**
    Current coverage is `1324` non-constant variables with references and `878` equations
    with references.

25. **Normalize non-SI unit taxonomy.**
    The code mixes SI-like units with semantic strings like `matrix`, `value`, `moment`, `flag`, `codes`.
    Decide what should be:

    * symbolic dimensions
    * categorical labels
    * plain documentation-only unit strings

---

### P1, tooling and packaging

26. **Historical: add `pyproject.toml`.**
    `pyproject.toml` now exists at the repo root with package metadata and
    runtime dependencies.

27. **Historical: add a real test suite.**
    Current collection is `536` tests. Keep the original minimum coverage as
    regression surface:

    * registry
    * graph utilities
    * equation subclasses
    * scope import smoke tests
    * demo smoke test
    * the assumption-collapse regressions

28. **Add CI.**

29. **Historical: add a built-in audit command.**
    `gpu-stack audit` and `python -m gpu_stack.cli audit` can recompute:

    * counts
    * roots / leaves
    * multi-definition variables
    * collapsed equations
    * collapsed approximation-validity predicates
    * unresolved symbols
    * metadata coverage
    * large-file thresholds

30. **Add reproducible scenario fixtures.**
    At least:

    * dense training
    * active-MoE training
    * one-node GPU case
    * one-rack case
    * one cluster cost case

---

### P2, modularization

31. **Historical: split oversized scope files.**
    Current audit reports `0` large scope files after the source-plasma state,
    focused-beam, medium-response, and medium-density helpers were split behind
    stable public shims. Old split tickets:

    * `cluster.py`
    * `architecture.py`
    * `optimizer.py`
    * `economics.py`
    * `training.py`
    * `precision.py`
    * `gpu.py`
    * `thermal.py`
    * `kernel.py`
    * `memory_subsystem.py`
    * `parallelism.py`
    * `memory_cell.py`

32. **Keep thin public aggregators stable after splits.**
    `physical.py` is the pattern to copy.

33. **Add one smoke test per helper module after each split.**

---

### P2, model completion and calibration

34. **Reduce the root-input burden through presets and calibrated defaults.**
    Historical high-root scopes from the earlier audit:

    * `physical`: 100
    * `memory_subsystem`: 69
    * `optimizer`: 49
    * `architecture`: 47
    * `parallelism`: 46
    * `thermal`: 43
    * `cluster`: 49
    * `memory_cell`: 39

35. **Add named hardware presets.**
    GPU, interconnect, node, rack, cluster.

36. **Add named workload presets.**
    Dense pretraining, active-MoE, offload-heavy training, inference-heavy serving.

37. **Add end-to-end example scenarios.**
    Good first targets:

    * rack peak FLOPs
    * training tokens/sec
    * data center total power / PUE
    * cost per token

---

### P3, cleanup and API polish

38. **Fix leaf-count semantics.**
    The current leaf metric includes unused constants, which makes the count noisier than it should be.

39. **Decide whether `EquationKind.DEFINITIONAL` should be used or removed.**

40. **Historical: add a friendly public reload/bootstrap API for notebooks and tests.**
    `gpu_stack.bootstrap()` is live.

## 2026-05-06 22:35 PDT Parent Closeout

- Physical root-debt boundary hardening is integrated and verified.
- Earlier worker coordination notes are superseded by the verified facts above.
- Final handoff state is full-verified, read-only verified, and source-clean.
