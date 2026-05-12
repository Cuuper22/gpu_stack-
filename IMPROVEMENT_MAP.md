# gpu_stack improvement map

Audit date: 2026-04-18 (original), live snapshot refreshed 2026-05-06.

## Latest Verified Wave

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

## Previous Verified Wave

Physical root-debt boundary hardening is implemented, verified, read-only
verified, and source-clean.

- Runtime capped live workers at six; bounded write lanes were tracked through
  `AGENT_GITLOG.md`.
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

## Current snapshot

| Metric | Value |
|---|---:|
| Systems / scopes | 16 |
| Variables | 1517 |
| Constants | 24 |
| Equations | 959 |
| Root inputs | 619 |
| Leaves | 253 |
| Cycles | 0 |
| Collapsed equations | 0 |
| Collapsed approximation validity predicates | 0 |
| Unresolved raw symbols | 0 |
| Orphan value equations | 0 |
| Topological order length | 1517 |
| Non-constant variables with references | 1324 |
| Equations with references | 878 |
| Non-constant variables with `sp_units` | 1428 |
| Equations with `check_units=True` | 799 |
| `VariableKind` split | 619 ROOT_INPUT / 874 DERIVED / 0 MEASURED / 24 DEFINITIONAL |
| Variables with multiple defining relations | 53 |
| Variables with multiple defining relations, role-tagged | 53 |
| Inequalities that simplify to `True` in `as_sympy()` | 0 |
| Scope files at or above 700 lines | 0 |
| Project Python files at or above 700 lines | 7 |
| Hard audit failures | 0 |
| Collected pytest tests | 639 |

## Previous Verified Wave

Scenario-audit selector/report ergonomics are implemented and verified.
`SCENARIO_TARGET_SETS` and `scenario_targets_for(...)` centralize advertised
scenario targets; `scenario-audit --preset` selects packs; `scenario-audit
--target [LABEL=]VARIABLE` overrides advertised targets; `ScenarioReport`
adds target-level ok/issues/error counts and label tuples; and
`root-debt --json` covers flat and family-grouped root-debt views. Default
all-sourced scenario audit still reports 33 known Pythia cost-per-token
missing-root issues.

Final verification for this wave:

- Focused selector/report/root-debt pack: `112 passed in 25.94s`.
- Full pytest: `548 passed in 69.71s`.
- Audit gate: PASS; systems 16; variables 1517; constants 24; equations 954;
  root inputs 619; leaves 253; cycles 0; hard failures 0; large scope files 0;
  large project files 7.
- Full verifier: `4/4 gates passed in 72.95s`.
- Read-only full verifier: `4/4 gates passed in 80.75s`.
- Final source-clean check: `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

## Earlier Verified Wave

The structured scenario-artifact wave is implemented and verified. Scenario
packs now have a documented evaluation-artifact surface:
`Preset.evaluate_targets(...)` produces a `ScenarioReport` containing
per-target `ScenarioTargetReport` entries, `MissingFamilySummary` captures
missing-family summaries, and `scenario-report --json` exports the
corresponding CLI artifact.

Final verification for this wave:

- Focused pack: `87 passed in 15.88s`.
- Full pytest: `533 passed in 73.54s`.
- Audit gate: PASS; systems 16; variables 1517; constants 24; equations 954;
  root inputs 619; leaves 253; cycles 0; hard failures 0; large scope files 0;
  large project files 7.
- Full verifier: `4/4 gates passed in 65.34s`.
- Read-only full verifier: `4/4 gates passed in 73.22s`.
- Final source-clean check: `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

Remaining visible work: SEMF numeric defaults are still blocked by source and
semantics; cited scenario expansion and model expansion remain open.

## Previous Verified Wave

`resolve --missing-families` is implemented and verified. Family diagnostics now
cover scenario-report, root-debt, and resolve missing-frontier views, so
unresolved inputs can be compared across scenario, root-debt, and resolver
surfaces without changing interpretation.

Final verification for this wave:

- Focused integration pack: `167 passed in 15.68s`.
- Full pytest: `528 passed in 55.75s`.
- Audit gate: PASS; systems 16; variables 1517; constants 24; equations 954;
  root inputs 619; leaves 253; cycles 0; hard failures 0; large scope files 0;
  large project files 7.
- Full verifier: `4/4 gates passed in 59.88s`.
- Read-only full verifier: `4/4 gates passed in 66.30s`.
- Final source-clean check: `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

Model expansion and numeric SEMF defaults remain future work until
sourced/calibrated values are available.

## Prior Verified Wave

`scenario-report --missing-families` now groups missing roots by resolver
family/category, and resolver family buckets split economics roots by public
prefix (`econ.node`, `econ.cluster`, `econ.asset`, etc.). The preset layer now
includes `scenarios.euv_tin120_lpp_source_context_assumption`, composing tin-120
source composition with ASML public 50 kHz EUV source context while leaving
unsourced plasma operating roots open. SEMF factory semantics, root-debt
determinism, gas/thermal feasibility, medium-response domain propagation, and
preset export/discovery coverage were hardened. Focused integration passed
`142 passed in 9.57s`; full pytest passed `488 passed in 56.49s`; full
verifier passed 4/4 in 57.47s; read-only full verifier passed 4/4 in 62.22s;
final source-clean check reports `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

## P0 status after pass 23

The Phase 0 semantic hardening and Phase 1 verification spine P0 tickets are landed:

- Relation-role metadata is live. `RelationRole` has four values (`IDENTITY`, `CONSTRAINT`, `APPROXIMATION`, `VARIANT`). Every Equation carries a role, and Variable now exposes `identities()`, `constraints()`, `approximations()`, and `variants(key=None)`.
- Inequality preservation is fixed. `Inequality.as_sympy()` uses `evaluate=False`, so the stored relation no longer collapses to `True`. The SRAM margin variables dropped their `positive=True` default so the constraints still have semantic force under SymPy's evaluating form.
- Each currently tracked multi-definition variable has explicit role coverage. Four are tagged as VARIANT families (`opt.param_next`, `training.flops_per_step`, `training.mfu`, `training.scaling_params`). The remaining variables carry a clean mix of IDENTITY, CONSTRAINT, and APPROXIMATION roles from subclass defaults.
- Packaging and tests are in place. `pyproject.toml` at the repo root declares metadata and a `sympy>=1.12` runtime dependency. The `tests/` directory runs under `python -m pytest -q` and covers import smoke, graph health, demo integration, relation-role regressions, the resolver, the preset framework, and the Phase 2 metadata helpers.

## P1 status after passes 24 through 39

Phase 3 modularization finished in pass 39. Every file in the original split map is now split into focused helpers behind a thin aggregator, and public imports still resolve exactly as before.

| Original pre-split file | Pre-split lines | Status | Split into |
|---|---:|---|---|
| `cluster.py` | 1115 | DONE (pass 24) | `cluster_node.py`, `cluster_rack.py`, `cluster_site.py`, `cluster_storage.py`, `cluster_reliability.py` |
| `architecture.py` | 1083 | DONE (pass 25) | `architecture_embeddings.py`, `architecture_positions.py`, `architecture_attention.py`, `architecture_ffn.py`, `architecture_moe.py` |
| `optimizer.py` | 878 | DONE (pass 28) | `optimizer_first_order.py`, `optimizer_second_order.py`, `optimizer_sharding.py`, `optimizer_schedules.py`, `optimizer_loss_scaling.py` |
| `training.py` | 845 | DONE (pass 33) | `training_compute.py`, `training_comm.py`, `training_memory.py`, `training_overheads.py`, `training_scaling.py` |
| `economics.py` | 843 | DONE (pass 29) | `economics_capex.py`, `economics_opex.py`, `economics_finance.py`, `economics_recovery.py` |
| `precision.py` | 801 | DONE (pass 34) | `precision_ieee.py`, `precision_rounding.py`, `precision_microscaling.py`, `precision_lowbit.py` |
| `gpu.py` | 797 | DONE (pass 35) | `gpu_compute.py`, `gpu_memory.py`, `gpu_io.py`, `gpu_power.py` |
| `thermal.py` | 793 | DONE (pass 36) | `thermal_package.py`, `thermal_liquid.py`, `thermal_facility.py`, `thermal_env.py` |
| `kernel.py` | 775 | DONE (pass 37) | `kernel_roofline.py`, `kernel_occupancy.py`, `kernel_gemm.py`, `kernel_attention.py` |
| `memory_subsystem.py` | 752 | DONE (pass 38) | `memory_regfile.py`, `memory_smem.py`, `memory_cache.py`, `memory_hbm.py`, `memory_virtual.py` |
| `memory_cell.py` | 700 | DONE (pass 31) | `memory_sram.py`, `memory_dram.py`, `memory_flipflop.py` |
| `parallelism.py` | 703 | DONE (pass 39) | `parallelism_batching.py`, `parallelism_zero_fsdp.py`, `parallelism_pipeline.py`, `parallelism_moe.py` |

Phase 4 scenario resolver landed in pass 26 (`gpu_stack.core.resolver` plus `gpu_stack.resolve`). Phase 5 preset framework landed in pass 27 (`gpu_stack.core.presets` plus `gpu_stack.presets.*`). Phase 2 metadata helpers landed in pass 30 (`Registry.by_kind`, `Registry.by_extensivity`, `Registry.coverage`, and post-load `auto_classify_kinds`). Current compact metrics: 1517 variables, 959 equations, 619 roots, 639 collected tests. A CLI entry point landed in pass 32 (`gpu-stack stats`, `list-presets`, `resolve`). Scenario presets now include `dense_training_cost_fixture`, the first sourced/calibrated scenario pack, tin/EUV source scaffolding, SEMF calibration scaffolding, `scenarios.euv_tin120_lpp_source_context_assumption`, `scenario-report --missing-families`, `resolve --missing-families`, `Preset.evaluate_targets(...)`, `ScenarioReport`, `ScenarioTargetReport`, `MissingFamilySummary`, `scenario-report --json`, `scenario-audit`, `scenario-audit --missing-families`, `SCENARIO_TARGET_SETS`, `scenario_targets_for(...)`, and the `next-work` continuation compass.

The remaining work from the original plan is:

- Continue populating `sp_units` on the foundational variables that back high-value equations. The scaffolding is in place in `core/variable.py` and `core/units.py`; 1428 non-constant variables now carry `sp_units`.
- Continue populating `references` on the equations that encode canonical formulas. Currently 878 / 959 carry references.
- Expand `check_units=True` coverage on curated foundational equations beyond the current 799 checks.
- Keep deepening high-root physical quantities. The lithography source and imaging-medium components now derive proton/neutron counts from valence up/down quark roots and constrain those roots with `D <= 2U`, `U >= (D + 3)/2`, `U <= 2D`, and `(U + D) mod 3 = 0`; binary imaging-medium formula units now require at least one A and one B stoichiometric component, formula-unit charge transfer is bounded by component electron inventories, formula-unit packing fill factor is explicitly bounded at unity, and packing length derives from intercomponent separation times `medium_formula_unit_packing_length_scale_factor` constrained to at least unity; photon energy, source transition energy, photon frequency, source angular frequency, and exposure wavelength now carry positive domains; source nuclear mass, reduced mass, and reduced-mass ratio now report explicit positive feasibility constraints; source transition principal-shell step now derives from an adjacent-shell approximation before upper-shell and transition-energy closure; source and medium component binding energies now derive through shared SEMF liquid-drop calibration roots before source/medium coefficient aliases, term equations, and isotope-specific composition; source-plasma temperature and electron density now derive from period-derived repetition rate, drive pulse fluence, fluence-derived peak intensity, trapezoid-derived pulse shape with duty-derived pulse duration, detuned drive wavelength from ionization-edge energy plus edge-detuning ratio, focus-derived spot radius through pupil/focal-derived drive numerical aperture, f-number, pupil-fill-derived BPP reference radius, BPP-derived beam quality, and a Gaussian f-number waist coefficient, circular/full-fill spot-shape convention, shared species gas inventory, thermal-speed-derived radial expansion with `sqrt(5/3)` expansion-speed-factor closure plus Rayleigh/confocal-derived column aspect geometry and an ideal active-fill convention, acceptance-angle-derived absorption path direction cosine, inverse-direction-cosine absorption path-shape closure, ionization-edge-derived absorption resonance ratio, participating-electron fraction, sum-rule fraction, hydrogenic orbital-area collision cross-section, collision-broadened damping from species density and species thermal speed, Lorentz-oscillator absorption cross-section whose resonance, damping, quality factor, and oscillator strength derive from drive frequency, collision damping, source charge, and those ionization-edge quantities, drive-overlap closure from coaxial pointing, transverse coverage, ideal active fill, energy-confinement-time-derived active lifetime ratio, and synchronized timing, optical-depth absorption, electron-channel heating, acceptance-angle-derived energy-loss path direction cosine, inverse-direction-cosine energy-loss path geometry, source-species particle mass, source-species thermal speed, mass-ratio-derived transport speed factor, free-electron yield from source proton count plus a free-electron inventory charge-fraction root, explicit source-plasma operating-input feasibility constraints for duty factor, electron-heating fraction, free-electron inventory charge fraction, pupil beam fill factor, and far-field divergence half-angle, and a divergence-within-acceptance constraint tying beam divergence to the drive optic cone; effective intercomponent charge and charge-unit scale now derive through formula-unit transfer electron count before formula-unit pair count, intercomponent separation, packing length, and local/global Lorentz-Lorenz screening, with screening rejecting the nonpositive-permittivity branch through `x_LL > -1/2` plus `x_LL < 1` validity guards; main lithography acceptance half-angle and numerical aperture now carry explicit forward-cone and medium-index bounds; gate `k1` now derives from strictly positive aerial-image contrast, resist/process latitude, mask-error amplification, and resolution-enhancement factors while feature k1 values inherit that gate baseline when unassigned; process geometry now reports violated positive/nonnegative feasibility constraints when signed biases drive derived dimensions below physical bounds.
- Keep sourced/calibrated scenario packs wired into resolver and CLI examples,
  and expand beyond the first verified Pythia-70M/DGX H100/EIA pack.
- Phase 6 deepening where the model still leaves important effects as root
  inputs. Model expansion and numeric SEMF defaults stay future work unless
  backed by sourced/calibrated values.

Next highest-impact frontier: keep the scenario-artifact surface stable while expanding cited scenarios and model coverage; SEMF numeric defaults remain blocked by source and semantics.

## Highest leverage repo-wide improvements

| Area | Evidence from the current codebase | Why it matters | Priority |
|---|---|---|---|
| Relation semantics | 53 variables have multiple defining relations, and all 53 now carry explicit identity, constraint, approximation, or variant roles. | The role layer is live, and resolver diagnostics now report constraints plus approximation-validity regimes; remaining work is stronger selector/explanation tooling for alternatives and missing roots. | P1 |
| Constraint preservation | Current audit reports 0 inequalities that simplify to `True` in `as_sympy()`. The old SRAM margin collapses are now regression targets instead of live failures. | Constraints must stay inspectable as the graph grows, especially around branch conditions, approximation validity, and feasibility checks. | P1 |
| Metadata coverage | The core supports references, unit checking, variable kinds, extensivity, shape, and dimensional expressions. The loaded model now uses most of it: 1324 non-constant variables have references, 1428 have `sp_units`, and 799 equations opt into dimensional checks. | Coverage is now broad across the model layer; the remaining gaps are visible and can be closed as focused slices. | P0 |
| Calibration depth | There are still 619 root inputs across the graph, meaning variables with no value-defining identity, approximation, or selected variant. The first sourced/calibrated scenario pack is landed, full-verified, and source-clean. | The next frontier is reducing manual scenario assignments and making pack provenance/evaluation behavior reproducible. | P0 |
| File cohesion | Current audit reports 0 scope files and 7 project Python files at or above 700 lines after lithography source-plasma, focused-beam, medium-response, and medium-density helper splits. | Reviewability, onboarding, and targeted regression testing stay tractable as scopes accumulate more subdomains. | Watch |
| Verification surface | The bundle has timeout-protected smoke validation (`import`, `demo`, `compileall` or read-only syntax checking, graph health), package metadata, and 639 collected pytest tests behind the `verify` profiles; the fast profile now includes resolver tests plus the neutron-sensitive source-plasma trace test directly, and `--read-only` suppresses bytecode/pytest-cache artifacts where practical. | The project can keep growing symbolically, but regression risk will grow faster than coverage. | P0 |
| User-facing evaluation | A conservative global resolver exists and computes targets from assignments through selected value relations, with symbolic-boundary missing reporting, constraint checks, approximation-validity checks, and optional strict CLI exits for violated feasibility. Scenario-report, root-debt, and `resolve --missing-families` diagnostics now share family/category grouping. The verified artifact surface includes `Preset.evaluate_targets(...)`, `ScenarioReport`, `ScenarioTargetReport`, `MissingFamilySummary`, `scenario-report --json`, and `scenario-audit` over sourced scenario packs with text/JSON output plus `--fail-on-issues`. It does not yet solve simultaneous systems or optimize over scenario choices. | The current API can run scenarios and emit structured artifacts; the highest-impact next step is selector control, broader pack reproducibility, and concise diagnostics. | P0 |
| Packaging hygiene | Earlier artifacts included `__pycache__` output. A reproducible source-only build path still needs to be formalized. | Clean packaging matters once the repo starts moving between machines, agents, and CI. | P2 |

## Multi-definition variables with explicit semantics

The tested multi-definition set now covers 53 variables, all with explicit
role coverage through identity, constraint, approximation, or variant
semantics. Representative high-signal variables include:

- `physical.lithography.source_valence_up_quark_count`
- `physical.lithography.source_plasma_species_number_density`
- `physical.lithography.source_plasma_species_thermal_speed`
- `physical.lithography.source_plasma_drive_acceptance_half_angle`
- `physical.lithography.source_plasma_drive_far_field_divergence_half_angle`
- `physical.lithography.source_plasma_drive_peak_intensity`
- `physical.lithography.source_plasma_drive_pulse_duration`
- `physical.lithography.source_plasma_drive_pulse_rise_fraction`
- `physical.lithography.source_plasma_drive_pulse_fall_fraction`
- `physical.lithography.source_plasma_drive_pulse_flat_fraction`
- `physical.lithography.source_plasma_drive_pulse_temporal_shape_factor`
- `physical.lithography.source_plasma_drive_beam_parameter_product`
- `physical.lithography.source_plasma_drive_beam_quality_factor`
- `physical.lithography.source_plasma_drive_spot_area`
- `physical.lithography.source_nuclear_mass`
- `physical.lithography.source_reduced_mass`
- `physical.lithography.source_reduced_mass_ratio`
- `physical.lithography.acceptance_half_angle`
- `physical.lithography.numerical_aperture`
- `physical.lithography.medium_component_a_valence_up_quark_count`
- `physical.lithography.medium_component_b_valence_up_quark_count`
- `physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count`
- `physical.lithography.medium_polarizable_electron_fraction`
- `physical.lithography.medium_dominant_oscillator_electron_count`
- `physical.lithography.medium_oscillator_sum_rule_fraction`
- `physical.lithography.medium_resonance_to_source_frequency_ratio`
- `physical.process.drawn_gate_length`
- `physical.process.source_drain_contact_width`
- `physical.process.gate_contact_spacing`
- `physical.process.contacted_gate_pitch`
- `physical.process.minimum_metal_width`
- `physical.process.minimum_metal_spacing`
- `physical.process.minimum_metal_pitch`
- `physical.process.node_length`
- `physical.channel_length`
- `physical.wire_length`
- `physical.drift_velocity`
- `physical.mosfet.width`
- `physical.mosfet.subthreshold_swing`
- `physical.gate.elmore_delay`
- `physical.power.total_gate`
- `memcell.sram.snm_read`
- `memcell.sram.wnm_write`
- `memcell.dram.refresh_period`
- `memcell.dram.v_dev`
- `opt.schedule.total_steps`
- `opt.param_next`
- `training.flops_per_step`
- `training.mfu`
- `training.scaling_params`
- `thermal.t_ambient`
- `thermal.env.relative_humidity`
- `thermal.env.dew_point_headroom`

The pattern is not uniform. A few examples:

- `opt.param_next` mixes alternative optimizer update rules.
- `training.flops_per_step` and `training.scaling_params` mix dense and MoE variants.
- `physical.gate.elmore_delay` and `physical.power.total_gate` mix an identity with a lower or upper bound.
- `physical.lithography.source_valence_up_quark_count` carries root-owned quark feasibility, at-least-one-proton, and triplet-integrality constraints.
- `physical.lithography.source_nuclear_mass`, `physical.lithography.source_reduced_mass`, and `physical.lithography.source_reduced_mass_ratio` mix value identities with positive feasibility constraints.
- `physical.lithography.acceptance_half_angle` and `physical.lithography.numerical_aperture` mix value approximations with optical feasibility bounds.
- `physical.lithography.medium_component_a_valence_up_quark_count` and `physical.lithography.medium_component_b_valence_up_quark_count` carry matching component isotope feasibility, at-least-one-proton, and triplet-integrality constraints.
- Source-plasma gas, focus, pulse, and peak-intensity variables now mix value
  approximations with structural feasibility constraints rather than arbitrary
  operating defaults.
- Medium optical-response fractions and ratios now mix derived count/energy
  formulas with unit-interval or above-resonance constraints.
- Process geometry dimensions mix lower lithography/process approximations with explicit positive or nonnegative feasibility constraints.
- `thermal.t_ambient` and `thermal.env.relative_humidity` are currently represented only as bounded constraints.

Those are all reasonable modeling choices. The remaining work is richer
selector diagnostics, approximation-validity policy handling, and constraint
reporting for resolvers and user-facing scenario explanations.

## Scope-by-scope improvement map

| Area | What is already strong | Main improvement areas | Priority |
|---|---|---|---|
| `core/*` | Clean registry, graph traversal, equation subclasses, relation roles, preserved inequalities, resolver, presets, and system grouping. | Deepen selector diagnostics, simultaneous-system handling, approximation-validity policy handling, and introspection helpers for variants and constraints. | P0 |
| `constants.py` | Good expansion to 24 physics constants with immutable values. | Add provenance coverage beyond the current lightweight source strings, expose exact-vs-derived lineage more clearly, and consider grouping constants into a small registered `physics` system. | P2 |
| `scopes/physical*.py` | Good coverage of transport, MOSFET regions, RC delay, Landauer bound, interconnect RC, and noise. | Add process corners, temperature-dependent mobility and resistance, variability and aging, interconnect inductance, and explicit material presets. | P1 |
| `memory_cell.py` | Strong symbolic SRAM, DRAM, and flip-flop layer. | Add assist circuits, Vmin distributions, sense path energy, ECC hooks, and array-level coupling between cell behavior and peripheral design. | P1 |
| `memory_subsystem.py` | Good hierarchy coverage from regfile through HBM and virtual-memory penalties. | Add coherence, replacement policy, prefetch effects, address mapping, partition hot spots, and latency distributions instead of only averages. | P1 |
| `precision.py` | Rich numeric-format catalog, rounding models, and low-bit support. | Add overflow and saturation propagation through kernels, accumulator-policy selection, calibration hooks for observed quantization error, and clearer handling of signed ranges and clipping. | P1 |
| `parallelism.py` | Strong DP, TP, PP, EP, CP, FSDP, and offload coverage. | Bind plans to concrete topology, make overlap windows first-class, add elastic and failure-aware schedules, and model nonuniform expert placement more explicitly. | P1 |
| `architecture.py` | Broad transformer, attention, positional, and MoE representation. | Add model-family presets, inference and decode path formulas, and tighter semantics between total parameters, active parameters, and served-token paths. | P1 |
| `arithmetic.py` | Clear Tensor Core, sparsity, DP4A, DP2A, and SFU accounting. | Add instruction latencies, issue-port contention, non-FMA pipelines, and per-op energy models that connect back into GPU-level power. | P2 |
| `optimizer.py` | Much stronger optimizer surface than the starting point, including Newton-Schulz iteration. | Keep split algorithm families clean while adding distributed state-movement costs, explicit optimizer variant selection, and validation for multi-definition update targets. | P0 |
| `gpu.py` | Good package-level aggregation of compute, memory, IO, and power. | Add concrete hardware profile loaders, boost-bin and clock-power coupling, more explicit throttling behavior, and separation between marketed peak, sustainable peak, and workload peak. | P1 |
| `interconnect.py` | Good alpha-beta and path-level network surface. | Add retransmits, adaptive routing, topology libraries, credit and buffer behavior, and clearer distinction between fabric control-plane and data-plane assumptions. | P1 |
| `kernel.py` | Strong roofline, occupancy, GEMM, and attention IO coverage. | Add more fused kernels, launch-configuration search helpers, decode kernels, overlap with collectives, and better mapping from arithmetic intensity to achieved utilization. | P1 |
| `collective.py` | Good ring, tree, hierarchical, and async-TP model set. | Add chunking, pipelined overlap, sparse and nonuniform collectives, and a clearer algorithm selector that can be calibrated from measurements. | P1 |
| `training.py` | Strong step decomposition and throughput-to-cost bridge. | Add checkpoint cadence, eval cadence, restart behavior, curriculum or phase changes, and formal scenario presets for dense, MoE, and offload-heavy runs. | P1 |
| `cluster.py` | Broad node-to-site aggregation with storage and reliability hooks. | Keep split cluster submodules cohesive while adding heterogeneous composition, queueing distributions, scheduler policies, storage-service contention, and multi-tenant reservations. | P1 |
| `thermal.py` | Cycle-free power-to-cooling linkage, package path, liquid loop, and facility overheads. | Add transient thermal RC behavior, controller logic, facility operating modes, weather traces, and more explicit region-dependent constraints. | P1 |
| `economics.py` | Strong capex, opex, NPV, and recovery framing. | Use the split capex, opex, finance, and recovery modules to add financing structures, tax and depreciation variants, regional tariff models, and scenario packs tied to real deployment envelopes. | P1 |
| `__init__.py`, `demo.py`, docs | Load order is centralized, the demo exercises graph health, and the CLI exposes stats, presets, resolving, audit, root-debt, and verify workflows. | Add notebooks, richer examples, API docs, and reproducible scenario recipes. | P2 |

## Completed file split map

The original split wave is complete; see the P1 status table above. The medium
composition and binding-energy layer is now split into component identity,
binding coefficients, binding terms, and formula-unit aggregation helpers. The
source-plasma state layer is now split into pulse/gas/column drive,
focused-beam geometry, absorption, and electron-state helpers behind the compatibility shim
`physical_lithography_plasma_state.py`. The top-level lithography bridge now
keeps medium-response count/energy roots in
`physical_lithography_medium_response.py`, formula-unit packing density closure
in `physical_lithography_medium_density.py`, and feature-family k1 process
factors in `physical_lithography_k1.py`. The current audit reports 0 scope
files at or above 700 lines.

| Original file | Old lines | Old vars | Old eqs | Split into |
|---|---:|---:|---:|---|
| `cluster.py` | 1115 | 90 | 55 | Split into `cluster_node.py`, `cluster_rack.py`, `cluster_site.py`, `cluster_storage.py`, `cluster_reliability.py`.
| `architecture.py` | 1083 | 102 | 55 | Split into `architecture_embeddings.py`, `architecture_positions.py`, `architecture_attention.py`, `architecture_ffn.py`, `architecture_moe.py`.
| `optimizer.py` | 874 | 83 | 35 | Split into `optimizer_first_order.py`, `optimizer_second_order.py`, `optimizer_sharding.py`, `optimizer_schedules.py`, `optimizer_loss_scaling.py`.
| `economics.py` | 843 | 72 | 41 | Split into `economics_capex.py`, `economics_opex.py`, `economics_finance.py`, `economics_recovery.py`.
| `training.py` | 833 | 61 | 49 | Split into `training_compute.py`, `training_comm.py`, `training_memory.py`, `training_overheads.py`, `training_scaling.py`.
| `precision.py` | 801 | 73 | 47 | Split into `precision_ieee.py`, `precision_rounding.py`, `precision_microscaling.py`, `precision_lowbit.py`.
| `gpu.py` | 797 | 60 | 46 | Split into `gpu_compute.py`, `gpu_memory.py`, `gpu_io.py`, `gpu_power.py`.
| `thermal.py` | 793 | 71 | 36 | Split into `thermal_package.py`, `thermal_liquid.py`, `thermal_facility.py`, `thermal_env.py`.
| `kernel.py` | 775 | 66 | 42 | Split into `kernel_roofline.py`, `kernel_occupancy.py`, `kernel_gemm.py`, `kernel_attention.py`.
| `memory_subsystem.py` | 752 | 88 | 26 | Split into `memory_regfile.py`, `memory_smem.py`, `memory_cache.py`, `memory_hbm.py`, `memory_virtual.py`.
| `parallelism.py` | 703 | 78 | 32 | Split into `parallelism_batching.py`, `parallelism_zero_fsdp.py`, `parallelism_pipeline.py`, `parallelism_moe.py`.
| `memory_cell.py` | 700 | 71 | 36 | Split into `memory_sram.py`, `memory_dram.py`, `memory_flipflop.py`.
| `physical_lithography.py` | 823 | 249 | 223 | Split medium-response count/energy roots into `physical_lithography_medium_response.py`, formula-unit packing density closure into `physical_lithography_medium_density.py`, and feature-family k1 process factors into `physical_lithography_k1.py` while keeping `physical_lithography.py` as the lithography bridge.

## Verification and tooling gaps

These are project-wide and should be treated as first-class work, not cleanup:

1. Keep the verified scenario-artifact surface deterministic while expanding selector controls and compact feasibility/approximation summaries.
2. Add CI-style source build verification around the existing `pyproject.toml`, building on the local `verify --read-only` mode, cache/artifact hygiene checks, and timeout budgets that match the local `verify` profiles (`120s` fast, `300s` full, override with `--gate-timeout`, disable with `0`).
3. Keep expanding regression checks around relation selection, constraint preservation, dimensional analysis, and high-root decompositions.
4. Add reproducible documentation examples so resolver, root-debt, and audit workflows stay synchronized with the package.

## What a "good next state" looks like

The next major milestone is not "more equations." It is a cleaner semantic layer plus a reliable evaluation path. Concretely, the model should be able to:

- preserve constraints as constraints under ongoing model growth,
- distinguish alternative model variants from simultaneous identities in resolver diagnostics,
- evaluate requested targets from consistent scenario assignments and cited presets through `Preset.evaluate_targets(...)`, `ScenarioReport`, `ScenarioTargetReport`, and `scenario-report --json`,
- validate units and references for the high-value equations,
- and run under tests and CI without depending on the demo as the only integration check.
