# gpu_stack

`gpu_stack` is a SymPy-backed symbolic model of the GPU training stack. It tracks named variables and equations from semiconductor transport and MOSFET behavior through memory hierarchy, arithmetic units, kernels, collectives, model architecture, optimizer math, training throughput, cluster composition, thermal plant behavior, and run economics.

The package is currently graph-consistent: importing `gpu_stack` registers **16 systems**, **1517 variables**, **24 constants**, and **959 equations**; `find_cycles()` returns **0 cycles** and `topological_sort()` succeeds across all **1517 variables**. It has **799 equations** checked for unit consistency at import time.

The physical slice has been recursively deepened through lithography source, source-plasma state, and imaging-medium composition and response: source and medium component proton/neutron counts derive from valence up/down quark roots with nonnegative nucleon, at-least-one-proton, and triplet-integrality feasibility constraints, atomic/isotope descriptors sit above those counts, source lower/upper principal shells now use an adjacent-shell transition-step closure, shared semi-empirical nuclear liquid-drop calibration roots feed source and medium coefficient aliases before isotope-specific binding terms, source nuclear ionization paths now have lower-level structure, photon energy/frequency/wavelength terms now carry positive domains, source nuclear mass, reduced mass, and reduced-mass ratio now carry explicit positive feasibility constraints, source-plasma drive power unfolds through pulse period, duty-derived pulse duration, source-plasma drive fluence, fluence-derived peak intensity, trapezoid-derived temporal shape, detuned drive wavelength from ionization-edge energy plus edge-detuning ratio, drive numerical aperture from pupil/focal acceptance geometry, exact drive f-number from acceptance angle, BPP reference radius from pupil beam fill and effective pupil radius, beam quality from beam-parameter product with diffraction lower-bound constraints on beam-parameter product and `M2`, source-plasma operating-input constraints bound pulse duty, electron-heating fraction, free-electron inventory charge fraction, pupil beam fill factor, and far-field divergence half-angle, with divergence also constrained to fit inside the focusing optic acceptance cone, focus-derived spot radius, circular/full-fill spot-shape convention, gas inventory, source-species thermal-speed-derived radial expansion with a monatomic sqrt(5/3) sound-speed factor, drive Rayleigh range and confocal length, confocal-derived column aspect/length geometry, acceptance-angle-derived absorption path direction cosine, inverse-direction-cosine absorption path-shape closure, hydrogenic orbital-area collision damping, Lorentz-oscillator absorption cross-section, spatial/temporal drive-overlap closure with ideal active-fill, coaxial-centroid, synchronized-timing conventions plus energy-confinement-time-derived active lifetime, heating, acceptance-angle-derived energy-loss path direction cosine, inverse-direction-cosine energy-loss path geometry, source-species thermal-speed transport with a mass-ratio-derived energy-loss speed factor, and charge-fraction-derived electron yield, with absorption resonance, damping, oscillator strength, quality factor, resonance-to-drive ratio, participating-electron fraction, and sum-rule fraction now derived from drive frequency, ionization-edge shell structure, source-species collision broadening, and source charge, intercomponent formula-unit binding derives from stoichiometry plus formula-unit transfer electron count with `medium_intercomponent_charge_unit` derived as the charge scale, nuclear-radius-derived A/B effective radii, a residual gap fraction, and local/global Lorentz-Lorenz screening from formula-electron count, polarizable-electron count, dominant oscillator electron count, resonance energy, molecular polarizability, and polarizable-site density with branch validity guarding `x_LL > -1/2` and `x_LL < 1`, main lithography optical constraints bound `theta_litho <= pi/2` and `NA_litho <= n_litho_med`, gate-patterning `k1` now derives from aerial-image contrast, resist/process latitude, mask-error amplification, and resolution-enhancement factors, imaging-medium molar mass derives from formula-unit proton, neutron, electron, and binding-energy mass-defect terms, formula-unit packing length now derives from intercomponent separation times `medium_formula_unit_packing_length_scale_factor` before mass density and number density, binary imaging-medium stoichiometry now requires at least one A and one B component, formula-unit intercomponent charge transfer is bounded by component electron inventories, packing fill factor is explicitly bounded at unity, packing length scale factor is constrained to at least unity, and process geometry now reports positive/nonnegative feasibility constraints when signed biases produce impossible derived dimensions. The graph also includes SM tile-area budgeting, node BOM power, rack ToR bandwidth, facility CDU and infrastructure capex closure, process pitch geometry, self-heating conduction, semiconductor/MOSFET/interconnect physics, HBM bandwidth, node scale-out injection, and rack bisection-aware site bandwidth relations.

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
| Collapsed approximation validity | 0 |
| Unresolved raw symbols | 0 |
| Orphan value equations | 0 |
| Scope files at or above 700 lines | 0 |
| Project Python files at or above 700 lines | 7 |
| Hard audit failures | 0 |
| Topological order length | 1517 |
| Non-constant variables with `sp_units` | 1428 |
| Non-constant variables with references | 1324 |
| Equations with references | 878 |
| Equations with unit checks | 799 |
| Multi-definition variables | 53 |
| `VariableKind` split | 619 ROOT_INPUT / 874 DERIVED / 0 MEASURED / 24 DEFINITIONAL |
| Collected pytest tests | 639 |

## Latest Verified Wave

The live next-work compass and scenario-audit missing-family ergonomics wave is
implemented, verified, read-only verified, and source-clean. It added
`gpu_stack.next_work` with `build_next_work_plan(...)`, `NextWorkPlan`, and
`NextWorkItem`; the `next-work` CLI plus `--json`; aggregate
`ScenarioReport.missing_family_summaries`; and `scenario-audit
--missing-families` text output. Focused parent pack:
`11 passed in 20.82s`; broader CLI/preset/next-work pack:
`111 passed in 45.31s`; full pytest: `639 passed in 102.03s`; audit gate PASS
with 16 systems, 1517 variables, 24 constants, 959 equations, 619 root inputs,
253 leaves, 0 cycles, 0 hard failures, 0 large scope files, and 7 large
project files; full verifier `4/4 gates passed in 107.69s`; read-only full
verifier `4/4 gates passed in 95.58s`; final source-clean check
`cache_dirs=0 pyc_files=0 pytest_cache_dirs=0 ruff_cache_dirs=0`.

## Previous Verified Wave

The physical root-debt boundary hardening wave is implemented, verified,
read-only verified, and source-clean. It added MOSFET effective-width,
ideality, oxide/EOT, channel-count, CLM, and gate-tunneling boundary coverage;
interconnect route-detour, route-length, hop-count, pitch, and fill-factor
coverage; process-geometry boundary diagnostics; lithography source/species
positive mass-number and inventory diagnostics; source-plasma drive boundary
coverage; medium intercomponent and medium-response boundary/validity
coverage; SEMF/nuclear coefficient boundary tests; import/CLI/root-debt smoke
tests; and the `AGENT_GITLOG.md` pseudo-git coordination ledger. Focused
parent pack: `125 passed in 33.75s`; full pytest: `628 passed in 71.99s`;
audit gate PASS with 16 systems, 1517 variables, 24 constants, 959 equations,
619 root inputs, 253 leaves, 0 cycles, 0 hard failures, 0 large scope files,
and 7 large project files; full verifier `4/4 gates passed in 73.38s`;
read-only full verifier `4/4 gates passed in 75.17s`; final source-clean
check `cache_dirs=0 pyc_files=0 pytest_cache_dirs=0 ruff_cache_dirs=0`.

## Earlier Verified Wave

The scenario-audit selector/report ergonomics wave is implemented and verified.
`SCENARIO_TARGET_SETS` plus `scenario_targets_for(...)` centralize advertised
scenario targets; `scenario-audit --preset` audits selected packs;
`scenario-audit --target [LABEL=]VARIABLE` overrides advertised targets;
`ScenarioReport` now exposes target-level ok/issues/error counts and label
tuples; and `root-debt --json` covers both flat and family-grouped root-debt
views. Default all-sourced scenario audit still reports the known 33 Pythia
cost-per-token missing-root issues. Focused selector/report/root-debt pack:
`112 passed in 25.94s`; full pytest: `548 passed in 69.71s`; audit gate PASS
with 16 systems, 1517 variables, 24 constants, 954 equations, 619 root inputs,
253 leaves, 0 cycles, 0 hard failures, 0 large scope files, and 7 large
project files; full verifier `4/4 gates passed in 72.95s`; read-only full
verifier `4/4 gates passed in 80.75s`; final source-clean check
`cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

The structured scenario-artifact wave is implemented and verified. New
surfaces include `Preset.evaluate_targets(...)`, `ScenarioReport`,
`ScenarioTargetReport`, `MissingFamilySummary`, and `scenario-report --json`
for machine-readable scenario evaluation artifacts. Focused pack:
`87 passed in 15.88s`; full pytest: `533 passed in 73.54s`; audit gate PASS
with 16 systems, 1517 variables, 24 constants, 954 equations, 619 root inputs,
253 leaves, 0 cycles, 0 hard failures, 0 large scope files, and 7 large
project files; full verifier `4/4 gates passed in 65.34s`; read-only full
verifier `4/4 gates passed in 73.22s`; final source-clean check
`cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

Remaining visible work: SEMF numeric defaults are still blocked by source and
semantics; cited scenario expansion and model expansion remain open.

## Previous Verified Wave

The latest integrated wave added `scenario-report --missing-families`,
`root-debt --families`, `resolve --missing-families`, an EUV tin120
source-context scenario, finer resolver family buckets for unresolved economics
roots, SEMF factory hardening, deterministic root-debt tests, gas/thermal
feasibility regressions, medium-response domain propagation tests, and preset
export/discovery coverage. It is fully verified: focused integration pack
`167 passed in 15.68s`, full pytest
`528 passed in 55.75s`, audit gate PASS with 16 systems, 1517
variables, 24 constants, 954 equations, 619 root inputs, 253 leaves, 0 cycles,
0 hard failures, 0 large scope files, and 7 large project files, full verifier
`4/4 gates passed in 59.88s`, read-only full verifier
`4/4 gates passed in 66.30s`, and final source-clean check
`cache_dirs=0 pyc_files=0 pytest_cache_dirs=0`.

## Design rules

1. **Only universal physics constants are `Constant`s.** Everything else, including clocks, voltages, tensor shapes, GPU counts, tariffs, and optimizer hyperparameters, is a `Variable`.
2. **Every scope self-registers on import.** Variables, equations, and systems wire themselves into the global `Registry` at construction time.
3. **Load order is authoritative and centralized.** `gpu_stack.scopes.SCOPE_MODULES` is the single source of truth for scope import order.
4. **The project is symbolic first.** It is a graph of definitions, constraints, approximations, variants, iterative updates, and stochastic relations. It is not a bounded simulator. Root inputs are visible modeling debt waiting to be recursively decomposed.

## Repository layout

```text
.
├── README.md
├── pyproject.toml
├── tests/
└── gpu_stack/
    ├── __init__.py
    ├── constants.py
    ├── demo.py
    ├── core/
    │   ├── __init__.py
    │   ├── equation.py
    │   ├── graph.py
    │   ├── registry.py
    │   ├── system.py
    │   ├── units.py
    │   └── variable.py
    └── scopes/
        ├── __init__.py
        ├── physical.py
        ├── physical_lithography_species.py
        ├── physical_lithography_nuclear_binding_coefficients.py
        ├── physical_lithography_binding_coefficients.py
        ├── physical_lithography_electronic_structure.py
        ├── physical_lithography_transition_step.py
        ├── physical_lithography_absorption_edge.py
        ├── physical_lithography_plasma_state.py
        ├── physical_lithography_plasma_drive.py
        ├── physical_lithography_plasma_focus.py
        ├── physical_lithography_plasma_overlap.py
        ├── physical_lithography_plasma_absorption.py
        ├── physical_lithography_plasma_electron_state.py
        ├── physical_lithography_medium_components.py
        ├── physical_lithography_medium_binding_coefficients.py
        ├── physical_lithography_medium_binding.py
        ├── physical_lithography_medium_composition.py
        ├── physical_lithography_medium_density.py
        ├── physical_lithography_medium_response.py
        ├── physical_lithography_k1.py
        ├── physical_lithography_source.py
        ├── physical_lithography.py
        ├── physical_process.py
        ├── physical_local_thermal.py
        ├── physical_semiconductor.py
        ├── physical_mosfet.py
        ├── physical_interconnect.py
        ├── physical_cmos_logic.py
        ├── physical_noise.py
        ├── memory_cell.py
        ├── memory_subsystem.py
        ├── precision.py
        ├── parallelism.py
        ├── architecture.py
        ├── arithmetic.py
        ├── optimizer.py
        ├── gpu.py
        ├── interconnect.py
        ├── kernel.py
        ├── collective.py
        ├── training.py
        ├── cluster.py
        ├── thermal.py
        └── economics.py
```

## Scope inventory

| Scope | Vars | Eqs | Roots | Leaves | Description |
|---|---:|---:|---:|---:|---|
| `physical` | 416 | 349 | 117 | 26 | lithography source and imaging-medium component valence up/down quark roots deriving proton/neutron composition with root-owned feasibility inequalities `D <= 2U`, `U >= (D + 3)/2`, and `U <= 2D` plus triplet integrality `(U + D) mod 3 = 0`, derived source and medium-component atomic/isotope descriptors, source mass-number aliasing into the nuclear binding path, photon source transition energy, adjacent-shell source transition step plus source lower/upper principal-shell closure, shared semi-empirical nuclear liquid-drop coefficient roots feeding source and medium coefficient aliases, source and medium nuclear material fields, reference-gap-derived pairing coefficients, source and medium component liquid-drop nuclear binding terms, parity-derived nuclear pairing signs, nuclear mass defects, reduced-mass positive feasibility constraints, screened Coulomb intercomponent formula-unit binding from stoichiometry-derived effective charge and pair count, A/B effective radii from nuclear-radius scaling plus local geometry factors, residual gap from a gap fraction, and local Lorentz-Lorenz intercomponent screening from molecular polarizability and effective separation, reduced-mass correction, screened hydrogenic source ionization energy, source ionization shell selection, ionization-edge screening, shell-degeneracy source ionization partition ratio, ionization-edge-derived source-plasma resonance ratio, participating-electron fraction, sum-rule fraction, hydrogenic orbital-area collision cross-section, and detuned drive wavelength from ionization-edge energy plus edge-detuning ratio, source-plasma pulse period, period-derived repetition rate, source-plasma drive fluence, pulse duty factor, duty-derived pulse duration, fluence-derived peak intensity, trapezoid pulse shape from rise, symmetric-derived fall, and flat fractions with a within-pulse constraint, drive numerical aperture from pupil/focal acceptance geometry, pupil beam fill factor with a unit-interval constraint, BPP reference radius from pupil fill and effective pupil radius, far-field divergence root with f-number, beam-parameter product, beam quality, and waist coefficient derived, operating-input constraints on duty factor, electron-heating fraction, free-electron inventory charge fraction, pupil beam fill factor, and far-field divergence half-angle, divergence-within-acceptance feasibility, circular/full-fill spot-shape convention and area, pulse-energy closure, shared source-plasma species gas inventory, thermal-speed-derived column radial expansion with expansion speed factor derived as `sqrt(5/3)`, drive Rayleigh range, confocal length, and confocal-derived aspect/radius/length geometry, acceptance-angle-derived absorption path direction cosine, inverse-direction-cosine absorption path-shape closure, collision-broadened absorption damping plus derived quality factor, optical-depth absorption, spatial/temporal drive-overlap closure from ideal active-fill, coaxial-centroid, synchronized-timing conventions, transverse coverage, pointing, duration matching, and energy-confinement-time-derived active lifetime ratio, electron-channel heating, acceptance-angle-derived energy-loss path direction cosine, inverse-direction-cosine energy-loss path closure, source-species mass, thermal-speed, and mass-ratio transport-factor closure, and charge-fraction free-electron yield closure deriving drive power, absorption efficiency, active volume, energy confinement time, free-electron count, electron temperature, free-electron density, mean kinetic energy, and Debye length, Saha-style source ionization balance, stoichiometric binary imaging-medium formula-unit composition with at-least-one component constraints, medium response fractions derived from polarizable electron count, dominant oscillator electron count, and resonance energy, gate `k1` process-factor decomposition plus shared feature k1 baselines, neutral formula-unit electron closure, principal-shell electron capacity, closed-inner-shell electron accounting, outer-shell electron accounting, active-shell electron occupancy, bound-electron source screening, source shielding factors, screened effective charge, main lithography acceptance-half-angle and numerical-aperture bounds, optics, formula-unit medium rest mass, molar mass, packing volume, packing-derived mass density, packing fill-factor upper-bound constraint, and density-derived medium number density, count/energy-derived oscillator strength, resonance ratio, and polarizability, Lorentz-Lorenz imaging-medium response, process pitch geometry with positive/nonnegative feasibility constraints on derived dimensions, local heat-source density, self-heating conduction, electrons, transistor, interconnect dielectric/material routing, RC delay, CMOS power, time-of-flight |
| `memory_cell` | 71 | 36 | 39 | 24 | SRAM 6T, DRAM 1T1C, flip-flop |
| `memory_subsystem` | 98 | 29 | 69 | 14 | register file, SMEM, TMEM, L1, L2, HBM stacked-die capacity, channelized bandwidth, and latency |
| `precision` | 73 | 47 | 26 | 35 | FP formats, microscaling (MXFP4/NVFP4), stochastic rounding |
| `parallelism` | 78 | 32 | 46 | 13 | DP, TP, PP, EP, CP, FSDP memory, pipeline bubbles |
| `architecture` | 102 | 55 | 47 | 24 | transformer block, attention variants, MoE, KV cache, 6*P*T |
| `arithmetic` | 28 | 13 | 15 | 3 | ALU, FMA, Tensor Core MMA, peak SM FLOPs |
| `optimizer` | 83 | 38 | 49 | 20 | AdamW, Muon, MuonClip, optimizer state memory, schedule domain constraints |
| `gpu` | 74 | 51 | 23 | 22 | SM floorplan, tile-area budget, die peak, package power, NVLink per GPU |
| `interconnect` | 44 | 23 | 20 | 6 | NVLink, IB, Spectrum-X, alpha-beta cost model |
| `kernel` | 66 | 42 | 24 | 6 | arithmetic intensity, roofline, matmul + attention kernels |
| `collective` | 29 | 23 | 6 | 9 | AllReduce, AllGather, ReduceScatter, All-to-all, async-TP |
| `training` | 61 | 49 | 15 | 8 | T_step = T_compute + T_ec + T_mb + T_bub, MFU, tokens/s |
| `cluster` | 115 | 67 | 49 | 18 | node NIC topology, rack scale-out bisection, node BOM power, node -> rack -> cluster -> hyperscaler aggregation |
| `thermal` | 80 | 42 | 43 | 8 | junction-to-ambient resistance, coolant flow, CDU auxiliary power, facility overhead power, facility design capacity, PUE |
| `economics` | 75 | 44 | 31 | 6 | GPU amortization, facility infrastructure capex, $/kWh, $/token, run cost |

## Quick start

Install the package in editable mode and run the checks.

```bash
python -m pip install -e ".[dev]"
python -m gpu_stack.cli verify --profile fast
python -B -m gpu_stack.cli verify --profile fast --read-only
python -m gpu_stack.cli verify --profile full
python -m gpu_stack.cli root-debt --families --limit 20
python -m gpu_stack.cli scenario-report scenarios.dense_training_cost_fixture --json
python -m gpu_stack.cli scenario-audit --json
```

Use `verify --profile fast` during iterative development. It prints one compact
line per gate and only expands output when a gate fails. Each gate has a
timeout budget (`120s` for fast, `300s` for full), and a timeout is reported as
a named gate failure instead of leaving verification hanging. Use
`--gate-timeout SECONDS` to override the budget, or `0` to disable it. Use
`verify --profile full` before handoff or after broader graph edits. Add
`--read-only` on either profile to run verifier child gates with bytecode
writes disabled, suppress pytest's cache provider, and use an in-memory syntax
gate instead of `compileall` for full verification. Launch the parent command
with `python -B -m ...` too when the whole verification invocation should avoid
bytecode artifacts.

### Inspect the registry

```python
import gpu_stack
from gpu_stack import Registry, find_cycles, topological_sort

print(Registry.stats())
print(find_cycles())
print(len(topological_sort()))
```

### Rebuild after a registry reset

```python
import gpu_stack
from gpu_stack import Registry

Registry.reset()
stats = gpu_stack.bootstrap()
print(stats)
```

### Resolve a scenario with constraints

```bash
python -m gpu_stack.cli resolve physical.gate.elmore_delay \
  --assign physical.gate.r_on=1 \
  --assign physical.gate.fanout=1 \
  --assign physical.gate.c_input=1 \
  --assign physical.interconnect.c_total=1 \
  --assign physical.interconnect.r_per_length=0 \
  --assign physical.interconnect.c_per_length=1 \
  --assign physical.wire_length=1 \
  --assign physical.clock_frequency=0.1 \
  --constraints
```

For strict resolver/CLI runs, pair `--constraints` with `--fail-on-violated-constraints`; invalid formula-unit packing assignments report the named feasibility relation, such as `physical.ineq.lithography_medium_formula_unit_packing_fill_factor_at_most_unity` or `physical.ineq.lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity`, before returning nonzero.

### Build a scenario artifact

```python
from gpu_stack.presets import scenarios

report = scenarios.dense_training_cost_fixture.evaluate_targets([
    ("tokens_per_second", "training.tokens_per_second"),
    ("cost_per_token", "econ.cost.per_token"),
])

print(type(report).__name__)
for target in report.targets:
    print(target.label, target.status, target.missing_count)
```

`Preset.evaluate_targets(...)` returns a `ScenarioReport` containing one
`ScenarioTargetReport` per requested target. The CLI equivalent is
`scenario-report PRESET --target [LABEL=]VARIABLE --json`, which emits the same
artifact shape for downstream tooling.

### Walk dependencies for a variable

```python
from gpu_stack import Registry

mfu = Registry.variables["training.mfu"]
for dep in sorted(mfu.dependencies(), key=lambda v: v.name):
    print(dep.name, dep.units)
```

### Inspect defining equations

```python
peak_gpu = Registry.variables["gpu.peak_flops"]
for eq in peak_gpu.defining_equations:
    print(eq.name)
    print(eq.as_sympy())
    print(eq.description)
```

### Substitute numeric values into one equation

```python
import sympy as sp
from gpu_stack import Registry

node_eq = Registry.equations["cluster.eq.node_peak_flops"]
rack_eq = Registry.equations["cluster.eq.rack_peak_flops"]

node_peak = node_eq.evaluate_rhs({
    Registry.variables["cluster.node.n_gpus"].symbol: 8,
    Registry.variables["gpu.peak_flops"].symbol: sp.Float(15e15),
})

rack_peak = rack_eq.evaluate_rhs({
    Registry.variables["cluster.rack.n_nodes"].symbol: 9,
    Registry.variables["cluster.node.peak_flops"].symbol: node_peak,
})

print(sp.N(rack_peak))
# 1.08e18
```

### Export a graph slice

```python
from gpu_stack import Registry, subgraph, to_dot

root = Registry.variables["econ.cost.per_token"]
cone = sorted(subgraph(root, direction="dependencies"), key=lambda v: v.name)
dot_text = to_dot(cone)
print(dot_text[:400])
```

## Core types

- `Variable` carries identity, units, description, scope, symbol assumptions, optional metadata, and the back-references needed for dependency traversal.
- `Constant` is an immutable `Variable` with a fixed numeric value. The package currently ships **24** such constants in `constants.py`.
- `Equation` and its subclasses (`Inequality`, `Approximation`, `PiecewiseEquation`, `DifferentialEquation`, `IterativeEquation`, `StochasticRelation`) encode the actual mathematical relations.
- `System` groups variables and equations by scope.
- `Registry` is the global lookup surface for all registered objects.

## What this package is good for right now

- Inspecting symbolic dependencies across hardware, software, thermal, and economic layers.
- Writing and checking new equations in a single consistent registry.
- Ranking unresolved roots by downstream blast radius with `gpu-stack root-debt`
  or grouped families with `gpu-stack root-debt --families`.
- Exporting dependency cones and debugging graph structure.
- Resolving selected scenario targets with variant selection, equation traces, missing symbolic-boundary reporting, constraint feedback, approximation-validity feedback, and optional nonzero exits for violated feasibility checks.
- Evaluating preset target sets through `Preset.evaluate_targets(...)` and
  exporting structured `ScenarioReport` / `ScenarioTargetReport` artifacts with
  `scenario-report --json`.
- Auditing sourced scenario packs with `scenario-audit`, including JSON output
  and strict nonzero exits via `--fail-on-issues`.
- Exercising exact composition-only material presets for lithography source and imaging-medium roots without assigning unsourced density, binding, or optical-response values.
- Running a synthetic dense-training cost fixture that resolves step time, tokens/s, allocated site power, run power cost, total run cost, and cost/token end to end.
- Demonstrating how training throughput and cost metrics reduce to lower-level assumptions.

## Current limitations

The model is broad, but it is still a modeling substrate, not a polished simulator. A few limits matter in practice:

- **Many quantities are still root inputs.** The graph currently exposes **619 root inputs**, which means many equations still need scenario values, presets, or deeper derivations. The highest-traffic physical roots now include source and medium valence-quark counts, source-plasma pulse-period, drive pulse fluence, pulse duty, pulse rise fraction with symmetric fall derived, drive edge-detuning ratio, drive objective pupil radius/focal length, drive pupil beam fill factor, far-field divergence, gas pressure/temperature, electron heating, free-electron inventory charge fraction, shared SEMF liquid-drop coefficient roots, medium stoichiometry, formula-unit intercomponent charge-transfer count, A/B intercomponent radius scale factors, `medium_intercomponent_gap_fraction`, medium polarizable-electron count, dominant oscillator electron count, medium resonance energy, intercomponent polarizable-site density factor, `medium_formula_unit_packing_length_scale_factor`, formula-unit packing fill factor, and the gate `k1` process factors for aerial-image contrast, resist/process latitude, mask-error amplification, and resolution enhancement. The BPP reference radius now derives from pupil beam fill factor times effective drive pupil radius, while focused spot radius remains downstream of `M2`, f-number, wavelength, and waist coefficient. The active lifetime ratio now derives from energy confinement time over drive pulse duration, the energy-loss transport speed factor now derives from the source-species to electron mass ratio, spot axis/fill now use a circular/full-fill convention, the column expansion speed factor now derives as `sqrt(5/3)` from a monatomic heavy-species sound-speed convention, column aspect now derives from drive Rayleigh/confocal length over expanded column radius, active fill now closes to an ideal full-column convention, drive centroid offset closes to a coaxial convention, timing offset closes to a synchronized convention, the absorption collision cross-section now derives from a hydrogenic ionization-shell orbital area, source-plasma BPP/`M2` now carry diffraction lower-bound constraints, source-plasma pulse duty, electron-heating fraction, free-electron inventory charge fraction, pupil beam fill factor, and far-field divergence half-angle now carry explicit operating-input feasibility constraints, with divergence also constrained by drive acceptance half-angle, `gate_k1` now derives from lower process/optics factors, medium intercomponent charge unit now derives from formula-unit transfer electron count and stoichiometry with inventory constraints, medium formula-unit packing length now derives from intercomponent separation times `medium_formula_unit_packing_length_scale_factor` before density, medium polarizable-electron fraction, oscillator sum-rule fraction, and resonance/source ratio now derive from material count and resonance-energy roots, and process geometry now reports violated feasibility constraints for negative derived dimensions caused by signed biases. Constraint-only variables still count as roots, because a bound does not define a value. The count can rise when one high-level root is decomposed into several lower-level roots; the important metric is whether the remaining roots are more physically primitive and better exposed.
- **The resolver is intentionally conservative.** It propagates one selected defining relation per variable, treats unassigned symbolic boundaries as `missing`, and reports constraints plus approximation-validity checks for approximation relations used in the trace. It still does not solve simultaneous systems, optimize over scenario choices, or automatically switch relations when a validity check is symbolic or violated.
- **Metadata coverage still has visible gaps, but the high-value upper scopes are now broadly covered.** Architecture, arithmetic, cluster, collective, economics, GPU, interconnect, kernel, memory, optimizer, parallelism, precision, thermal, and training scopes now carry focused metadata/unit regression tests. Remaining work is mostly targeted closure on the uncovered tail and stronger calibrated presets.
- **Calibration presets are still skeletal.** Presets exist as regression anchors, exact composition fixtures, and one synthetic dense-training cost scenario, not as authoritative hardware, workload, density, binding, or optical-response catalogs.

## Project status docs

For the project-wide audit and next-step plan, see:

- [`./IMPROVEMENT_MAP.md`](./IMPROVEMENT_MAP.md)
- [`./ROADMAP.md`](./ROADMAP.md)
- [`./HANDOFF.md`](./HANDOFF.md)
- [`./CHANGELOG.md`](./CHANGELOG.md)
- [`./AGENT_DIARY.md`](./AGENT_DIARY.md) for subjective session notes
- [`./rest_breaks/README.md`](./rest_breaks/README.md) for occasional non-work break notes
