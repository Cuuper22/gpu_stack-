# CHANGELOG

Rolling notes on the granularity pass. Update after every pass.

## Workflow note

As of April 18, 2026 the user asked for roughly five files per response. Keep the dependency order, but process adjacent files in batches when practical.

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

Phase 4 P1 landed as `gpu_stack/core/resolver.py` plus a new `tests/test_resolver.py`. The resolver takes a target Variable plus a dict of scenario assignments, walks the dependency cone in topological order, substitutes values equation by equation, and returns both the result and a trace of which equations fired. It respects the Phase 0 relation-role semantics: IDENTITY wins by default, VARIANT relations require a caller-supplied selector, APPROXIMATION is used only when there is no IDENTITY, and CONSTRAINT relations are never used as defining relations.

Public API: `gpu_stack.resolve(target, assignments={}, variants={})`. Errors: `Underdetermined` when a needed variable has no assignment and no usable defining relation, `AmbiguousVariant` when multiple relations match without a selector.

Smoke check: resolving `cluster.rack.peak_flops` from `n_nodes=9`, `n_gpus_per_node=8`, and `gpu.peak_flops=15e15` yields 1.08e18 FLOPs and emits a five-step trace including the arith-path identities and the cluster-level rack FLOPs equation. Test suite is now 22 passing.

## Pass 27: scenario preset framework (DONE)

Phase 5 groundwork. Adds `gpu_stack/core/presets.py` with a frozen `Preset` dataclass that bundles scenario assignments, variant selections, and provenance, plus a `combine()` helper that merges presets with later-wins precedence on key collisions. Preset construction validates every variable name against the Registry so typos fail fast rather than silently drifting through a resolver call.

The new `gpu_stack.presets` package ships three helper modules. The only numeric preset is `hardware.demo_rack`, drawn verbatim from `gpu_stack.demo` so no new unsourced numbers enter the codebase. The workload module carries variant-selector presets for dense vs MoE, MFU formulation, and AdamW vs Muon. Combining a hardware preset with a workload selector through `combine_presets` lets the resolver evaluate a training-level target in one call.

`tests/test_presets.py` covers unknown-name rejection, end-to-end resolution (`demo_rack` produces 1.08e18 FLOP/s for `cluster.rack.peak_flops`), combine ordering, variant pinning, and `with_overrides`. The test suite is now 29 passing.

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
