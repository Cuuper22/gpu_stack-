# README Article Structure Proposal

## Proposed Section Order

1. `GPUSTACK`
2. Telos: engine, observatory, research lab
3. First frontier question
4. Read one result at three depths
5. What is implemented today
6. Run the E001 mechanics screen
7. Observation and evaluation contracts
8. Temporal engine and intervention boundary
9. Symbolic causal backbone
10. Experiment catalog and falsifiers
11. Current evidence boundary
12. Next research measurements
13. Repository layout
14. API reference
15. Project status docs

## Reader Effect By Section

| Section | What the reader should feel or understand |
|---|---|
| `GPUSTACK` | This is a causal virtual datacenter whose claims stay attached to measurements, uncertainty, and missing mechanisms. |
| Telos | The engine, visual explanation, and research program are one measurement-to-hypothesis loop. |
| First frontier question | E001 is concrete enough to falsify: multi-site training must preserve learning efficiency while cutting WAN traffic under interruption. |
| Three depths | A freshman and a systems researcher see the same artifact at different explanatory density, not different truth. |
| What is implemented today | Observations, held-out splits, evaluation, temporal events, multi-site contention, observable-only policies, preregistered protocols, and an E001 mechanics runner exist alongside the symbolic graph. |
| Run E001 | The reader can produce a result and observatory artifact from one frozen scenario. |
| Evidence boundary | The mechanics screen can answer timing and payload questions, while learning transfer and real-cluster validity remain visibly unresolved. |
| Symbolic backbone | Equations and roots matter when they explain residuals, uncertainty, or experiment behavior. |
| Experiment catalog | Six frontier programs expose hypotheses, baselines, metrics, falsifiers, and real-validation ladders before results exist. |
| Next research measurements | The queue starts with held-out learning transfer and missing failure semantics, not generic graph expansion. |
| Repository layout | The reader can navigate the codebase. |
| API reference | The README still works as a GitHub README for developers who came to copy commands or imports. |
| Project status docs | The reader knows where the moving state lives. |

## Draft Prose For The First Five Sections

### 1. `gpu_stack`

GPUSTACK is a causal, uncertainty-aware virtual AI datacenter, visual
observatory, and ML systems research lab. Its SymPy registry remains the
symbolic causal backbone rather than the research finish line.

It is built around a plain claim: the cost and performance of frontier training are not properties of a GPU alone. They pass through many layers: semiconductor transport, lithography and process geometry, memory hierarchy, numeric formats, kernels, collectives, model architecture, optimizer state, cluster topology, thermal infrastructure, and run economics. Most tools cut that chain into separate calculators. `gpu_stack` keeps the whole chain in one equation graph you can inspect.

The symbolic graph is now the causal ancestry layer inside a larger engine.
The research substrate around it records observations, separates calibration
from evaluation, schedules causally ordered operations across sites, exposes
an observable-only intervention boundary, and packages every result with its
falsifiers and evidence gaps. When a quantity or mechanism is missing, the
artifact says so instead of filling the hole with an invented number.

### 2. Why This Exists

Training infrastructure is often discussed through compressed numbers: FLOPs, MFU, tokens per second, dollars per token, megawatts, rack count, PUE. Those numbers are useful, but they hide where the assumptions entered.

`gpu_stack` is an attempt to keep the assumptions visible.

A cost-per-token estimate depends on training step time. Step time depends on compute, memory, communication, pipeline bubbles, and optimizer behavior. Communication depends on collectives and topology. Topology depends on nodes, racks, bisection, and site-level power. Power depends on GPU package behavior, cooling plant behavior, and facility overhead. Far below that, device behavior rests on process geometry, lithography constraints, MOSFET equations, interconnect delay, and material assumptions.

The interesting part is not that all of these layers can be named. The interesting part is that they can be connected without pretending every boundary is already calibrated.

### 3. The Central Idea

The core object is a registry-backed equation graph.

Every scope self-registers when imported. Variables carry identity, units, descriptions, scope metadata, symbolic assumptions, and back-references for graph traversal. Equations define relations between variables. Constants are reserved for universal physics constants. Everything else, including clocks, voltages, tensor shapes, optimizer hyperparameters, GPU counts, tariffs, and facility assumptions, remains a variable.

That choice matters. A variable with no defining value relation is not an embarrassment to hide. It is a root input: a place where the model stops and an assumption must enter. Root inputs are visible modeling debt. Some roots should eventually be decomposed into lower-level physics. Some should remain scenario boundaries. Some require sourced calibration before the model is allowed to assign them.

This is why root count alone is not the score. Decomposing one vague root into several primitive roots can make the count rise while making the model more honest.

### 4. A First Walk Through The Graph

Start with a target such as `econ.cost.per_token`.

The model walks backward from that target into the quantities needed to define it: run cost, token count, site power, training throughput, step time, communication, kernels, GPU peak behavior, cluster composition, and lower physical assumptions. Where a selected relation exists, the resolver propagates it. Where a symbolic boundary is still unassigned, the resolver reports what is missing.

For example, scenario artifacts use `Preset.evaluate_targets(...)` to evaluate named targets and return structured reports. The CLI equivalent, `scenario-report PRESET --target [LABEL=]VARIABLE --json`, emits the same shape for downstream tooling. Missing roots can be grouped by family, so an unresolved cost target does not just dump a long list of symbols. It can say which part of the model still needs closure.

That is the practical loop: pick a target, trace its dependency cone, assign or source the boundary conditions, evaluate what can be evaluated, then inspect what remains unresolved.

### 5. What Is Implemented Today

The symbolic graph has 16 systems, 1517 variables, 24 constants, and 959
equations. It is joined by typed observations, calibration and evaluation
splits, prediction intervals and residual metrics, deterministic event
timelines, multi-site resources and outages, interventions, experiment
protocols, and an evidence-preserving observatory projection.

The model spans physical and systems layers. The physical slice includes lithography source structure, imaging-medium composition and response, process geometry, self-heating, semiconductor transport, MOSFET behavior, interconnect physics, CMOS logic, and noise. The upper stack includes memory cells and memory hierarchy, numeric precision, parallelism, transformer architecture, arithmetic units, optimizer math, GPU package behavior, network interconnect, kernels, collectives, training throughput, cluster composition, thermal plant behavior, and economics.

The research surfaces include `Observation`, `CalibrationSplit`,
`EvaluationSplit`, `PredictionRecord`, `EventTimeline`, `VirtualDatacenter`,
`Policy`, `ExperimentProtocol`, and `ExperimentRunArtifact`. The CLI exposes
all six machine-readable protocols and executes E001 from an explicit scenario.
The other five programs remain preregistered designs until their engines and
observations exist.

## Recommended Content Ratio

Target ratio for the rewritten README:

| Content type | Ratio | Purpose |
|---|---:|---|
| Story and framing | 30% | Explain why the project exists, what problem it is resisting, and how to read unresolved roots. |
| Demo and workflows | 30% | Give commands and small code paths for verification, registry inspection, resolver use, scenario artifacts, dependency traversal, and graph export. |
| Stats and verification evidence | 20% | Keep the reader grounded in current scale, test status, audit health, and known gaps. |
| API reference | 20% | Preserve GitHub README utility: core types, CLI surfaces, package entry points, and links to status docs. |

The first screen should be mostly story plus one compact evidence block. The middle should alternate prose with runnable examples. The bottom can hold the denser reference material that current users still need.
