# gpu_stack

![A wide visual map of the training stack descending from datacenters through GPU systems, lithography, atoms, and particle-like root assumptions.](docs/assets/readme-hero.png)

**Website:** <https://cuuper22.github.io/gpu_stack-/><br>
**Causal observatory:** <https://cuuper22.github.io/gpu_stack-/observatory.html><br>
**Repository:** <https://github.com/Cuuper22/gpu_stack-><br>
**Research program:** [RESEARCH.md](RESEARCH.md)

`gpu_stack` started as a curiosity project in the overlap between my AI work and my physics brain.

The question was simple enough to be annoying: if frontier training is supposedly "more GPUs, more data, more money," where does that sentence actually bottom out?

Not rhetorically. Physically.

A token passes through model architecture, kernels, collectives, memory bandwidth, transistor switching, lithography, materials, thermals, power delivery, and eventually a cost line item that someone has to pay. Each of those layers is usually explained on its own, in a slice. I wanted the version where the slices have to talk to each other.

## What This Is Now, And How It Got Here

The project grew in three stages. Once you know the stages, everything else in this README makes sense.

First it was an equation graph: thousands of physics and engineering relations wired together, so that a question like "what does one token cost" could be traced all the way down instead of stopping at a vendor slide.

Then the graph learned to move. Events, failures, checkpoints, power draw, multi-site traffic. The static graph became a small virtual datacenter that can replay what a training run does over time.

Now it is a lab. The virtual datacenter runs preregistered experiments. Preregistered means the pass/fail line is frozen before the run starts, so I cannot move the goalposts after seeing the result. Measurements calibrate the engine. The engine powers the explanation. The explanation exposes its own assumptions. Experiments produce new measurements. That loop is the whole point now.

So in one sentence: GPUSTACK is a virtual AI datacenter you can interrogate. It predicts what a training run does to time, power, and money, says how sure it is, and can show you what every one of its numbers is made of.

That is a lot of machinery for one question about GPU training. It grew this way one honest step at a time, which is more or less how the project happened.

## The Shape Of The Stack

![Dependency cone from datacenter economics down through GPU systems, transistor physics, lithography, atoms, nucleons, quarks, and equations.](docs/assets/readme-equation-cone.svg)

`gpu_stack` treats the training stack as one inspectable dependency cone. Pick a single number at the top, collect everything it depends on, and the shape that falls out is a cone: one question at the tip, hundreds of assumptions at the base.

At the wide end are questions people actually ask:

- What sets `econ.cost.per_token`?
- Why did `training.tokens_per_second` move?
- How much site power disappears into cooling?
- Which missing assumptions matter most downstream?

The bridge between the two ends is the same chain every time. Cooling depends on chip heat. Chip heat depends on how transistors switch. Switching depends on how the transistors were manufactured. Manufacturing depends on physics that does not care about anyone's roadmap.

At the narrow end are the things the model refuses to pretend away: how the chip was etched (lithography), how the etching light is generated (a plasma source), what that light lands on (the imaging medium), the transistor's gate constraints, and below all of it the proton and neutron counts and quark composition that decide what atoms even are, sitting next to the universal constants.

Most tooling stops at the first satisfying number. `gpu_stack` keeps asking: what is that number made of?

The answer can be an equation, a sourced scenario value, a universal constant, or a root input. A root input is a value the model needs but cannot yet derive, so it names the value instead of hiding it. A root input is not a failure. It is modeling debt made visible, and visible debt is much safer than hidden debt.

## The Central Idea

The core object is a registry-backed equation graph. The registry is one global catalog: every variable and every equation in the model checks itself in there, so anything can be looked up, traced, and audited from one place.

Variables carry identity, units, descriptions, scope metadata, symbolic assumptions, and back-references for graph traversal. Equations define relations between variables. Constants are reserved for universal physics constants. Everything else, including clocks, voltages, tensor shapes, optimizer hyperparameters, GPU counts, tariffs, and facility assumptions, remains a variable.

That choice matters.

A variable with no defining value relation is a root input. Some roots should eventually be decomposed into lower-level physics. Some should remain scenario boundaries. Some require sourced calibration before the model is allowed to assign them.

This is why root count alone is not the score. Decomposing one vague root into several primitive roots can make the count rise while making the model more honest.

The research score is held-out predictive error, uncertainty coverage, configuration ranking, intervention regret, time to a learning or service target, facility energy and power behavior, and whether a preregistered hypothesis survives evidence. Held-out means the data was never used to tune the model, so the model cannot grade its own homework. Regret is the gap between the decision the model recommended and the best decision in hindsight. Equation count, root count, and passing tests are diagnostics. They are not research results.

## What The Graph Knows Right Now

Fresh local `stats` output reports:

```text
Registry stats:
  systems        16
  variables      1517
  constants      24
  equations      950
  root_inputs    619
  leaves         259

Coverage:
  non_constant_variables         1493
  with_sp_units                  1493
  with_references                1493
  equations                      950
  equations_with_references      950
  equations_with_unit_check      884
```

Leaves are variables nothing else depends on, the end of the line in the graph.

The model spans:

| Layer | What lives there |
|---|---|
| Physical roots | lithography source structure, imaging-medium composition, process geometry, local thermal behavior, semiconductor transport, MOSFET behavior, interconnect physics, CMOS logic, noise |
| Memory | SRAM, DRAM, flip-flops, register file, shared memory, Tensor Memory, L1, L2, HBM capacity and bandwidth |
| Numeric formats | IEEE formats, low-bit precision, microscaling, stochastic rounding |
| Parallelism | data, tensor, pipeline, expert, context, and FSDP style sharding |
| Model architecture | attention, embeddings, FFN, MoE, positions, KV cache, transformer parameter and token math |
| Arithmetic and kernels | ALU, FMA, Tensor Core MMA, roofline, GEMM, attention kernels, occupancy |
| Communication | NVLink, InfiniBand, Spectrum-X-style scale-out, collectives, alpha-beta costs |
| Training | compute time, communication time, bubbles, MFU, tokens per second |
| Cluster and facility | nodes, racks, bisection, storage, reliability, power, cooling, PUE |
| Economics | capex, opex, amortization, power cost, run cost, cost per token |

MFU means Model FLOPs Utilization. HBM means High Bandwidth Memory. PUE means Power Usage Effectiveness. You should not need to arrive already knowing datacenter abbreviations, so this README defines them. If half the other words in that table are new to you, that is fine. The table is a map of where things live, not a quiz.

## Try It Without Believing Me

Install in editable mode:

```bash
python -m pip install -e ".[dev]"
```

Run the quick health check:

```bash
python -m gpu_stack.cli stats
```

Run the verifier while iterating:

```bash
python -m gpu_stack.cli verify --profile fast
python -B -m gpu_stack.cli verify --profile fast --read-only
```

Before broader graph edits, use the full verifier:

```bash
python -m gpu_stack.cli verify --profile full
```

The installed entry point is also available as:

```bash
gpu-stack stats
gpu-stack verify --profile fast
```

## See One Output As A Cone

Start with a target such as `econ.cost.per_token`.

```python
import gpu_stack
from gpu_stack import Registry, subgraph

target = Registry.variables["econ.cost.per_token"]
cone = subgraph(target, direction="dependencies")

print(target.name)
print(f"{len(cone)} variables upstream")
print("first few roots:")

roots = sorted((v for v in cone if v.is_root_input), key=lambda v: v.name)
for var in roots[:12]:
    print("  ", var.name, f"[{var.units}]")
```

The exact count is not the important part. The posture is. Every cost number has an ancestry, and every unresolved ancestor is named.

## Root Debt

`root-debt` ranks unresolved root inputs by downstream blast radius: how many other variables would feel it if this assumption moved.

```bash
python -m gpu_stack.cli root-debt --families --limit 5
```

Observed summary:

```text
Root-debt family ranking:
  total_roots        619
  include_constraints False
  grouped_roots      619
  family_count       151
  shown              5

total_weight  root_count  family                                      boundary_category  primitive_boundary
        3014          15  physical.lithography.medium                 primitive-root     True
        2185          11  physical.lithography                        primitive-root     True
        1943           8  physical.lithography.source_plasma_drive    primitive-root     True
        1866          18  physical.mosfet                             primitive-root     True
        1293           8  physical.process                            primitive-root     True
```

Reading the columns: `total_weight` is how many downstream variables depend on the family's roots, `family` is the group of related roots, and `primitive_boundary` marks families sitting at the edge of what the model can currently derive. The live table also appends a `top_roots` column naming the heaviest individual roots per family, truncated here for line width.

This is one of the more useful commands, because it stops the project from adding equations wherever it feels interesting. The graph itself can tell you which unknowns are currently expensive.

## Scenario Reports

Presets can evaluate named targets and return structured artifacts. A preset is a saved bundle of scenario assignments, so a run is reproducible instead of a matter of memory.

```python
from gpu_stack.presets import scenarios

report = scenarios.dense_training_cost_fixture.evaluate_targets([
    ("tokens_per_second", "training.tokens_per_sec"),
    ("job_dc_power", "econ.job.dc_power"),
    ("run_power_cost", "econ.run.power_cost"),
    ("cost_per_token", "econ.cost.per_token"),
])

print(report.status)
for target in report.targets:
    print(target.label, target.status, target.missing_count)
```

The CLI equivalent:

```bash
python -m gpu_stack.cli scenario-report scenarios.dense_training_cost_fixture --json
```

Observed summary:

```json
{
  "preset": "dense_training_cost_fixture",
  "status": "ok",
  "assignment_count": 30,
  "target_count": 4,
  "ok_count": 4,
  "error_count": 0,
  "issue_count": 0,
  "ok_target_labels": [
    "tokens_per_second",
    "job_dc_power",
    "run_power_cost",
    "cost_per_token"
  ]
}
```

Representative resolved values:

```text
training.tokens_per_sec = 6666666.66666667
econ.job.dc_power       = 5200.0
econ.run.power_cost     = 0.00078
econ.cost.per_token     = 3.000078e-06
```

That last line reads as three millionths of a dollar per token: for this synthetic scenario, a million tokens costs about three dollars of datacenter.

That fixture is synthetic. A fixture is a fixed test anchor: deterministic on purpose, not vendor truth, historical data, or a price recommendation. The distinction matters. A synthetic number wearing the costume of a measurement is exactly the kind of hidden assumption this project exists to avoid.

## Resolver Workflows

Resolve a target with explicit assignments:

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

For stricter runs, pair `--constraints` with `--fail-on-violated-constraints`. Invalid assignments report named feasibility relations before returning nonzero.

Scenario-audit surfaces are also available:

```bash
python -m gpu_stack.cli scenario-audit --json
python -m gpu_stack.cli scenario-audit --missing-families
```

## The Research Program

Six questions, each frozen as a machine-readable protocol before it has results:

```bash
python -m gpu_stack.cli experiment-protocol E001 --json
```

Each protocol freezes its falsifiers up front. A falsifier is the specific outcome that kills the hypothesis, written down before the run so the experiment can actually lose. Missing mandatory evidence makes a run inconclusive; a failed computable gate fails the virtual screen instead of being hidden by unrelated missing evidence.

In plain words, the six questions:

| Code | The question | Where it stands |
|---|---|---|
| E001 | Can you pretrain one model across several unreliable datacenters without giving up the learning efficiency of one tight cluster? | Ran, repeatedly. The clever adaptive controller has so far lost to the boring baseline, and outside its calibrated territory it abstained rather than guessing. Next step is SC2, a frozen risk predictor. |
| E002 | Can checkpoint timing be used to shape a rack's power draw? | First measurement attempt threw itself out (broken power meter sampling). Second attempt produced a valid local attribution. The physical rack test waits on hardware this machine does not have. |
| E003 | Can a training system treat failures by how much they hurt learning, instead of treating every failure the same? | Protocol frozen. Not run. |
| E004 | Should an inference fleet move requests around while they are being served? | Protocol frozen. Not run. |
| E005 | Under a fixed power envelope, can mixed hardware plus architecture co-design beat a uniform cluster? | Protocol frozen. Not run. |
| E006 | Can an inference fleet behave as a firm, grid-responsive electrical load? | Protocol frozen. Not run. |

A few experiment codes appear throughout the project: LC stands for learning calibration, PW for power waveform, SC for semantic consistency. E001-LC3 is just "the third learning-calibration run of experiment one."

Two results are worth telling as stories, because they show the project behaving the way it was designed to.

The first: E001-SC1 stress-tested the adaptive controller across six failure patterns it had never seen. In three of them, the controller recognized it was outside its calibrated experience, 104 times, and each time it recorded an abstention: a logged "I do not know" plus a fallback to the safe baseline, instead of a guess. The persisted conclusion is `abstain_without_policy_claim`. The system declined to claim a win it could not support. That refusal is the result, and it is the most honest thing in this repository.

The second: E002-PW1 completed all 32 runs and then invalidated itself, because its power meter turned out to sample 25 times slower than requested. The favorable-looking raw numbers were thrown out as inadmissible instead of being quietly kept. The rerun with a valid meter, PW2, is the result that counts.

Every number behind those stories, with intervals, artifact paths, and content hashes, lives in the [results log](docs/research/results-log.md). The log exists so any claim above can be checked against the exact artifact that produced it.

## Design Rules

These rules keep the package honest:

1. Only universal physics constants are `Constant`s.
2. Everything else is a `Variable`, including clocks, voltages, tensor shapes, GPU counts, tariffs, and optimizer hyperparameters.
3. Every scope self-registers on import: loading a domain module is what adds its variables and equations to the registry, so nothing exists off the books.
4. `gpu_stack.scopes.SCOPE_MODULES` is the authoritative load order.
5. The project is symbolic first. It is a graph of definitions, constraints, approximations, variants, iterative updates, and stochastic relations.
6. A root input is visible modeling debt. It should be decomposed, sourced, or intentionally left as a scenario boundary.
7. Observations, scenario assumptions, modeled values, priors, and unmeasured claims are different artifact classes.
8. Calibration and evaluation IDs may not overlap: nothing used to tune the model is allowed to grade it.
9. A policy sees deployable observable state, never hidden simulator truth or future traces.
10. A virtual screen can reject a mechanism. It cannot validate a real datacenter claim by itself.
11. A result with missing evidence stays inconclusive even when one numerical threshold looks favorable.
12. Root-debt work enters the research queue only through a measured residual, decision-relevant uncertainty, or experiment dependency.

## What This Is Good For Now

- Recording immutable measured observations with instrumentation uncertainty and provenance.
- Enforcing calibration/evaluation separation and reporting residuals, interval coverage, configuration ranking, and decision regret.
- Replaying causally ordered compute, collective, state-transfer, checkpoint, outage, facility-power, cooling, and grid events across multiple sites.
- Executing matched recovery policies through explicit failure, preemption, checkpoint restore, replay, membership rejoin, and durable frontier recovery with exact work conservation.
- Applying observable-only membership, cadence, parallelism, configuration, migration, and power-cap interventions at explicit decision epochs.
- Producing content-addressed experiment artifacts while keeping measured, modeled, assumed, prior, inadmissible, and unmeasured quantities distinct.
- Reporting site base plus accelerator-compute energy while explicitly excluding unmodeled network, checkpoint, storage, host, and cooling energy.
- Inspecting symbolic dependencies across hardware, software, thermal, and economic layers.
- Writing and checking new equations in a single registry.
- Ranking unresolved roots by downstream blast radius.
- Resolving selected scenario targets with variant selection, equation traces, missing-family reporting, constraints, and approximation-validity feedback.
- Exporting structured `ScenarioReport` and `ScenarioTargetReport` artifacts.
- Auditing sourced scenario packs.
- Demonstrating how training throughput and cost metrics reduce to lower-level assumptions.

## What This Is Not Yet

This is the part where the README earns the numbers above.

GPUSTACK is not yet a calibrated digital twin, meaning a simulation validated to track a specific real facility, and it is not a training-cost oracle. The learning experiments so far ran on one local small-model workload. They do not establish frontier-scale transfer, real multi-site concurrency, WAN or facility energy, topology changes, optimizer correction, or the full joint controller.

The adaptive recovery policy is genuinely better on some axes (much less lost work, less modeled energy) and worse on others (slower, more traffic) than the simple baselines. Nothing so far crowns a single winner, and the honest reading of LC1 through SC1 is that the boring baseline is hard to beat on this workload. The full numbers live in the [results log](docs/research/results-log.md).

The symbolic resolver remains intentionally conservative. It propagates one selected defining relation per variable, does not solve simultaneous systems by default, and does not switch relations when an approximation validity check fails; opt-in flags record those actions in the trace. Unassigned symbolic boundaries are reported as `missing` rather than becoming convenient defaults.

Calibration presets are still skeletal. Some presets are exact composition fixtures. Some are regression anchors. Some are synthetic dense-training cost fixtures. They are useful because they are explicit, not because they are universal.

## Current Snapshot

| Signal | Value |
|---|---:|
| Systems | 16 |
| Variables | 1517 |
| Constants | 24 |
| Equations | 950 |
| Root inputs | 619 |
| Leaves | 259 |
| Cycles | 0 |
| Topological order length | 1517 |
| Hard audit failures | 0 |
| Non-constant variables with `sp_units` | 1493 |
| Non-constant variables with references | 1493 |
| Equations with references | 950 |
| Equations with unit checks | 884 |
| Root-debt families | 151 |
| Package version | 0.27.0 |

Test counts can move as the model grows. Recheck locally with:

```bash
python -m pytest --collect-only -q
```

## Causal Observatory

The observatory is the primary visual artifact, not an equal-weight dashboard. It keeps a plain question, causal mechanism, counterfactual regime, model, evidence, residual, provenance, event trace, and falsifier in one shareable state. Semantic depth changes explanation density, never values or conclusions: the Freshman view and the Full trace view describe the same result, one in plain language and one with every number exposed.

The first screen is E001, Beyond One Datacenter. It makes the experiment sequence legible at three depths: LC3 exposed the energy failure, PW1 rejected an undersampled meter, and PW2 attributed the supported local effect to checkpoint cadence while sparse continuation passed all gates. Researcher and Full trace views expose paired effects, support counts, falsifier outcomes, learning curves, work conservation, checkpoint overhead, source hashes, assumptions, and the observed/modeled evidence boundary.

## Core Types

This section is for people writing code against the package. Skip it freely if that is not you.

- `Variable`: identity, units, description, scope, symbol assumptions, metadata, and dependency back-references.
- `Constant`: an immutable `Variable` with a fixed numeric value. This should stay rare.
- `Equation`: a relation over variables.
- `Inequality`: a feasibility constraint.
- `Approximation`: a relation with a validity regime.
- `PiecewiseEquation`, `DifferentialEquation`, `IterativeEquation`, `StochasticRelation`: richer relation types for the parts of reality that refuse to be one clean line.
- `System`: a scope-level collection of variables and equations.
- `Registry`: the global lookup surface.
- `Preset`: scenario assignments, variants, and target evaluation support.
- `Observation`, `CalibrationSplit`, `EvaluationSplit`: measured evidence and leakage-safe partitions.
- `PredictionRecord`, `ResidualMetrics`, `StratifiedIntervalCoverage`, `KendallTauB`, `DecisionRegret`, `BenchmarkAggregation`: held-out error, confidence-level coverage, ranking, replicated-panel aggregation, and the consequence of decisions induced by the model.
- `TemporalEvent`, `EventTimeline`, `VirtualDatacenter`: causal event and shared-resource mechanics.
- `Intervention`, `Policy`, `VisibleDatacenterState`: observable-only control boundary.
- `ExperimentProtocol`, `ExperimentRunArtifact`: frozen hypotheses, falsifiers, and evidence status.
- `EvidenceRequirementSpec`, `EvidenceRequirementResult`: mandatory vector, transfer, causal, accounting, and panel gates that cannot be omitted from a run artifact just because they lack one honest scalar threshold.

## Inspect The Registry In Python

```python
import gpu_stack
from gpu_stack import Registry, find_cycles, topological_sort

print(Registry.stats())
print(find_cycles())
print(len(topological_sort()))
```

Rebuild after a registry reset:

```python
import gpu_stack
from gpu_stack import Registry

Registry.reset()
stats = gpu_stack.bootstrap()
print(stats)
```

Inspect defining equations:

```python
from gpu_stack import Registry

peak_gpu = Registry.variables["gpu.peak_flops"]
for eq in peak_gpu.defining_equations:
    print(eq.name)
    print(eq.as_sympy())
    print(eq.description)
```

Substitute numeric values into one equation:

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

Export a graph slice:

```python
from gpu_stack import Registry, subgraph, to_dot

root = Registry.variables["econ.cost.per_token"]
cone = sorted(subgraph(root, direction="dependencies"), key=lambda v: v.name)
dot_text = to_dot(cone)
print(dot_text[:400])
```

## Repository Layout

```text
.
├── README.md
├── PRODUCT.md
├── DESIGN.md
├── RESEARCH.md
├── ROADMAP.md
├── pyproject.toml
├── docs/            GitHub Pages site, data, research notes
├── experiments/     preregistered protocols and persisted results
├── process/         agent-session ledgers, not reader-facing
├── tests/
└── gpu_stack/
    ├── __init__.py
    ├── constants.py
    ├── core/
    ├── presets/
    └── scopes/
```

## Project Status Docs

The README is the front door. The deeper records live here:

- [`RESEARCH.md`](./RESEARCH.md): the research program and its rules.
- [`ROADMAP.md`](./ROADMAP.md): where the work is headed.
- [`docs/research/results-log.md`](./docs/research/results-log.md): every completed run, every number, every hash.
- [`CHANGELOG.md`](./CHANGELOG.md): version history.
- [`process/`](./process/): session ledgers for the agent workflow that builds this. Continuity notes, not documentation.
