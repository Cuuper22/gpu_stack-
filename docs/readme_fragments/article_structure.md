# README Article Structure Proposal

## Proposed Section Order

1. `gpu_stack`
2. Why this exists
3. The central idea
4. A first walk through the graph
5. What is implemented today
6. Quick start
7. The model surface
8. Scenario artifacts and resolver workflows
9. Design rules
10. Current snapshot
11. Current limitations
12. Near-term work
13. Repository layout
14. API reference
15. Project status docs

## Reader Effect By Section

| Section | What the reader should feel or understand |
|---|---|
| `gpu_stack` | This is a serious technical object with a clear boundary: a symbolic model of GPU training systems, not a benchmark dashboard or simulator. |
| Why this exists | Modern training cost is not caused by one layer. The point is to keep the whole dependency chain inspectable, from physical assumptions to cost per token. |
| The central idea | The package treats equations as a graph. Root inputs are not hidden knobs; they are visible modeling debt. |
| A first walk through the graph | The reader can imagine using it: pick a target, inspect its dependencies, resolve what can be resolved, and see what remains missing. |
| What is implemented today | The project is already substantial and verified: 16 systems, 1517 variables, 959 equations, 0 graph cycles, 639 tests. |
| Quick start | The reader can install it, verify it, and run one meaningful command without absorbing the whole model first. |
| The model surface | The reader sees the breadth of scopes without drowning in every equation. |
| Scenario artifacts and resolver workflows | The project has a reproducible evaluation surface, with JSON artifacts and missing-family diagnostics. |
| Design rules | The model has taste and discipline: constants are rare, load order is centralized, and symbolic structure comes first. |
| Current snapshot | The metrics become a compact accountability panel. |
| Current limitations | The project is honest about unresolved roots, conservative resolving, and skeletal calibration. |
| Near-term work | The roadmap is not "add more stuff." It is root closure, sourced scenarios, evaluator UX, and metadata/provenance coverage. |
| Repository layout | The reader can navigate the codebase. |
| API reference | The README still works as a GitHub README for developers who came to copy commands or imports. |
| Project status docs | The reader knows where the moving state lives. |

## Draft Prose For The First Five Sections

### 1. `gpu_stack`

`gpu_stack` is a SymPy-backed symbolic model of the GPU training stack.

It is built around a plain claim: the cost and performance of frontier training are not properties of a GPU alone. They pass through many layers: semiconductor transport, lithography and process geometry, memory hierarchy, numeric formats, kernels, collectives, model architecture, optimizer state, cluster topology, thermal infrastructure, and run economics. Most tools cut that chain into separate calculators. `gpu_stack` keeps the chain in one inspectable equation graph.

The package is not trying to be a polished simulator. It is a modeling substrate. It registers variables, constants, equations, constraints, approximations, variants, and stochastic relations, then lets you inspect how one quantity depends on another. If a target cannot be resolved because a primitive assumption is still missing, the model reports that boundary instead of filling it with an invented number.

### 2. Why This Exists

Training infrastructure is often discussed through compressed numbers: FLOPs, MFU, tokens per second, dollars per token, megawatts, rack count, PUE. Those numbers are useful, but they hide where the assumptions entered.

`gpu_stack` is an attempt to keep the assumptions visible.

A cost-per-token estimate depends on training step time. Step time depends on compute, memory, communication, pipeline bubbles, and optimizer behavior. Communication depends on collectives and topology. Topology depends on nodes, racks, bisection, and site-level power. Power depends on GPU package behavior, cooling plant behavior, and facility overhead. Far below that, device behavior rests on process geometry, lithography constraints, MOSFET equations, interconnect delay, and material assumptions.

The interesting part is not that all of these layers can be named. The interesting part is that they can be connected without pretending every boundary is already calibrated.

### 3. The Central Idea

The core object is a registry-backed equation graph.

Every scope self-registers when imported. Variables carry identity, units, descriptions, scope metadata, symbolic assumptions, and back-references for graph traversal. Equations define relations between variables. Constants are reserved for universal physics constants. Everything else, including clocks, voltages, tensor shapes, optimizer hyperparameters, GPU counts, tariffs, and facility assumptions, remains a variable.

That choice matters. A variable with no defining value relation is not treated as an embarrassment to hide. It is a root input. Root inputs are visible modeling debt. Some roots should eventually be decomposed into lower-level physics. Some should remain scenario boundaries. Some require sourced calibration before the model is allowed to assign them.

This is why root count alone is not the score. Decomposing one vague root into several primitive roots can make the count rise while making the model more honest.

### 4. A First Walk Through The Graph

Start with a target such as `econ.cost.per_token`.

The model can walk backward from that target into the quantities required to define it: run cost, token count, site power, training throughput, step time, communication, kernels, GPU peak behavior, cluster composition, and lower physical assumptions. Where a selected relation is available, the resolver can propagate it. Where a symbolic boundary remains unassigned, the resolver reports what is missing.

For example, scenario artifacts use `Preset.evaluate_targets(...)` to evaluate named targets and return structured reports. The CLI equivalent, `scenario-report PRESET --target [LABEL=]VARIABLE --json`, emits the same shape for downstream tooling. Missing roots can be grouped by family, so an unresolved cost target does not just produce a long list of symbols. It can say which part of the model still needs closure.

That is the practical loop: choose a target, trace the dependency cone, assign or source the boundary conditions, evaluate what can be evaluated, then inspect what remains unresolved.

### 5. What Is Implemented Today

The current graph has 16 systems, 1517 variables, 24 constants, and 959 equations. It is graph-consistent: cycle detection returns 0 cycles, topological sorting succeeds across all 1517 variables, and the audit gate reports 0 hard failures. There are 799 equations checked for unit consistency at import time, 878 equations with references, and 639 collected pytest tests.

The model spans physical and systems layers. The physical slice includes lithography source structure, imaging-medium composition and response, process geometry, self-heating, semiconductor transport, MOSFET behavior, interconnect physics, CMOS logic, and noise. The upper stack includes memory cells and memory hierarchy, numeric precision, parallelism, transformer architecture, arithmetic units, optimizer math, GPU package behavior, network interconnect, kernels, collectives, training throughput, cluster composition, thermal plant behavior, and economics.

The newest verified public surfaces include `gpu_stack.next_work`, `build_next_work_plan(...)`, `NextWorkPlan`, `NextWorkItem`, `next-work`, `next-work --json`, `ScenarioReport.missing_family_summaries`, and `scenario-audit --missing-families`. The latest verified full test run reported `639 passed in 102.03s`, and the full verifier passed 4 out of 4 gates.

The live session state notes one active in-progress wave around Pythia energy-floor cost closure and aggregate missing-family deduplication. That work should not be described as verified until parent integration and verification are complete.

## Recommended Content Ratio

Target ratio for the rewritten README:

| Content type | Ratio | Purpose |
|---|---:|---|
| Story and framing | 30% | Explain why the project exists, what problem it is resisting, and how to read unresolved roots. |
| Demo and workflows | 30% | Give commands and small code paths for verification, registry inspection, resolver use, scenario artifacts, dependency traversal, and graph export. |
| Stats and verification evidence | 20% | Keep the reader grounded in current scale, test status, audit health, and known gaps. |
| API reference | 20% | Preserve GitHub README utility: core types, CLI surfaces, package entry points, and links to status docs. |

The first screen should be mostly story plus one compact evidence block. The middle should alternate prose and runnable examples. The bottom can hold the denser reference material that current users still need.
