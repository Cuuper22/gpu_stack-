# gpu_stack improvement map

Audit date: 2026-04-18

## Current snapshot

| Metric | Value |
|---|---:|
| Systems / scopes | 16 |
| Variables | 1147 |
| Constants | 23 |
| Equations | 620 |
| Root inputs | 519 |
| Leaves | 261 |
| Cycles | 0 |
| Topological order length | 1147 |
| Non-constant variables with references | 0 |
| Equations with references | 13 |
| Non-constant variables with `sp_units` | 0 |
| Equations with `check_units=True` | 0 |
| Variables with multiple defining relations | 15 |
| Inequalities that simplify to `True` | 2 |
| Scope files at or above 700 lines | 12 |

## Highest leverage repo-wide improvements

| Area | Evidence from the current codebase | Why it matters | Priority |
|---|---|---|---|
| Relation semantics | 15 variables have multiple defining relations. Some are equation plus inequality, some are alternative model variants, and some are two legitimate equations for the same quantity. | The graph needs a first-class distinction between identity, constraint, approximation, and variant selection. Without that, automated solving will stay brittle. | P0 |
| Constraint preservation | 2 inequalities already collapse to `True` because many symbols default to `positive=True`. The concrete cases are `memcell.eq.sram_read_margin_constraint` and `memcell.eq.sram_write_margin_constraint`. | Once a constraint simplifies away, it stops being useful for validation, explanation, or feasibility checks. | P0 |
| Metadata coverage | The core supports references, unit checking, variable kinds, extensivity, shape, and dimensional expressions. The loaded model uses almost none of it: 0 non-constant variables have references, 0 have `sp_units`, and 0 equations opt into dimensional checks. | The framework has the hooks for rigor, but the model layer is not using them yet. | P0 |
| Calibration depth | There are still 519 root inputs across the graph. | The package is broad, but many end-to-end scenarios still require manual value injection. | P1 |
| File cohesion | 12 scope files are already at or above 700 lines. The largest are `cluster.py` (1115 lines) and `architecture.py` (1083 lines). | Reviewability, onboarding, and targeted regression testing all get worse as scopes accumulate too many subdomains. | P1 |
| Verification surface | The bundle has smoke validation (`import`, `demo`, `compileall`, graph health), but there is no dedicated test suite, CI config, or package metadata. | The project can keep growing symbolically, but regression risk will grow faster than coverage. | P0 |
| User-facing evaluation | There is no global resolver that takes assignments, chooses compatible relations, and computes a requested target end-to-end. | The current API is strong for inspection, weaker for scenario analysis. | P1 |
| Packaging hygiene | Earlier artifacts included `__pycache__` output. A reproducible source-only build path still needs to be formalized. | Clean packaging matters once the repo starts moving between machines, agents, and CI. | P2 |

## Multi-definition variables that need explicit semantics

The following variables currently have more than one defining relation and should be reviewed under a formal relation-role system:

- `physical.drift_velocity`
- `physical.mosfet.subthreshold_swing`
- `physical.gate.elmore_delay`
- `physical.power.total_gate`
- `memcell.sram.snm_read`
- `memcell.sram.wnm_write`
- `memcell.dram.refresh_period`
- `memcell.dram.v_dev`
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
- `thermal.t_ambient` and `thermal.env.relative_humidity` are currently represented only as bounded constraints.

Those are all reasonable modeling choices. The problem is that they are currently encoded through the same `defined_by` channel.

## Scope-by-scope improvement map

| Area | What is already strong | Main improvement areas | Priority |
|---|---|---|---|
| `core/*` | Clean registry, graph traversal, equation subclasses, and system grouping. | Add relation roles, preserve inequalities without eager simplification, implement a scenario resolver, and add stronger introspection helpers for variants and constraints. | P0 |
| `constants.py` | Good expansion to 23 physics constants with immutable values. | Add provenance coverage beyond the current lightweight source strings, expose exact-vs-derived lineage more clearly, and consider grouping constants into a small registered `physics` system. | P2 |
| `scopes/physical*.py` | Good coverage of transport, MOSFET regions, RC delay, Landauer bound, interconnect RC, and noise. | Add process corners, temperature-dependent mobility and resistance, variability and aging, interconnect inductance, and explicit material presets. | P1 |
| `memory_cell.py` | Strong symbolic SRAM, DRAM, and flip-flop layer. | Add assist circuits, Vmin distributions, sense path energy, ECC hooks, and array-level coupling between cell behavior and peripheral design. | P1 |
| `memory_subsystem.py` | Good hierarchy coverage from regfile through HBM and virtual-memory penalties. | Add coherence, replacement policy, prefetch effects, address mapping, partition hot spots, and latency distributions instead of only averages. | P1 |
| `precision.py` | Rich numeric-format catalog, rounding models, and low-bit support. | Add overflow and saturation propagation through kernels, accumulator-policy selection, calibration hooks for observed quantization error, and clearer handling of signed ranges and clipping. | P1 |
| `parallelism.py` | Strong DP, TP, PP, EP, CP, FSDP, and offload coverage. | Bind plans to concrete topology, make overlap windows first-class, add elastic and failure-aware schedules, and model nonuniform expert placement more explicitly. | P1 |
| `architecture.py` | Broad transformer, attention, positional, and MoE representation. | Split by subdomain, add model-family presets, add inference and decode path formulas, and tighten semantics between total parameters, active parameters, and served-token paths. | P1 |
| `arithmetic.py` | Clear Tensor Core, sparsity, DP4A, DP2A, and SFU accounting. | Add instruction latencies, issue-port contention, non-FMA pipelines, and per-op energy models that connect back into GPU-level power. | P2 |
| `optimizer.py` | Much stronger optimizer surface than the starting point, including Newton-Schulz iteration. | Separate algorithm families cleanly, add distributed state-movement costs, expose optimizer variant selection explicitly, and validate multi-definition update targets. | P0 |
| `gpu.py` | Good package-level aggregation of compute, memory, IO, and power. | Add concrete hardware profile loaders, boost-bin and clock-power coupling, more explicit throttling behavior, and separation between marketed peak, sustainable peak, and workload peak. | P1 |
| `interconnect.py` | Good alpha-beta and path-level network surface. | Add retransmits, adaptive routing, topology libraries, credit and buffer behavior, and clearer distinction between fabric control-plane and data-plane assumptions. | P1 |
| `kernel.py` | Strong roofline, occupancy, GEMM, and attention IO coverage. | Add more fused kernels, launch-configuration search helpers, decode kernels, overlap with collectives, and better mapping from arithmetic intensity to achieved utilization. | P1 |
| `collective.py` | Good ring, tree, hierarchical, and async-TP model set. | Add chunking, pipelined overlap, sparse and nonuniform collectives, and a clearer algorithm selector that can be calibrated from measurements. | P1 |
| `training.py` | Strong step decomposition and throughput-to-cost bridge. | Add checkpoint cadence, eval cadence, restart behavior, curriculum or phase changes, and formal scenario presets for dense, MoE, and offload-heavy runs. | P1 |
| `cluster.py` | Broad node-to-site aggregation with storage and reliability hooks. | Split aggressively, add heterogeneous cluster composition, queueing distributions, scheduler policies, storage-service contention, and multi-tenant reservations. | P1 |
| `thermal.py` | Cycle-free power-to-cooling linkage, package path, liquid loop, and facility overheads. | Add transient thermal RC behavior, controller logic, facility operating modes, weather traces, and more explicit region-dependent constraints. | P1 |
| `economics.py` | Strong capex, opex, NPV, and recovery framing. | Split into clearer capex, opex, finance, and recovery submodules; add financing structures, tax and depreciation variants, regional tariff models, and scenario packs tied to real deployment envelopes. | P1 |
| `__init__.py`, `demo.py`, docs | Load order is centralized and the demo now exercises graph health correctly. | Add a small CLI, notebooks, richer examples, API docs, and reproducible scenario recipes. | P2 |

## File split map for the next refactor wave

| Current file | Lines | Vars | Eqs | Suggested split |
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

## Verification and tooling gaps

These are project-wide and should be treated as first-class work, not cleanup:

1. Add a real test suite. Right now the validation surface is mostly `import`, `demo`, `compileall`, and graph-health checks.
2. Add packaging metadata such as `pyproject.toml` and a clean source build path.
3. Add regression checks for the exact issues already observed in the audit, especially inequality simplification and multi-definition handling.
4. Add reproducible scenario fixtures so throughput, power, and cost examples can be exercised automatically.

## What a "good next state" looks like

The next major milestone is not "more equations." It is a cleaner semantic layer plus a reliable evaluation path. Concretely, the model should be able to:

- preserve constraints as constraints,
- distinguish alternative model variants from simultaneous identities,
- evaluate a requested target from a consistent scenario assignment,
- validate units and references for the high-value equations,
- and run under tests and CI without depending on the demo as the only integration check.
