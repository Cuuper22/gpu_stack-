## Why

I built `gpu_stack` because frontier training systems are usually explained in disconnected slices. One conversation is about MOSFET switching, another is about HBM bandwidth, another is about Tensor Core math, another is about all-reduce latency, and then someone jumps straight to model FLOPs utilization (MFU) or dollars per token as if the path between those layers were obvious.

I wanted one symbolic surface where those layers could sit in the same dependency graph. Not a simulator that pretends the world is solved, and not a spreadsheet with hidden assumptions, but a map of what depends on what: physics, memory, arithmetic, kernels, collectives, architecture, thermal limits, and economics.

The useful thing here is the shape of the graph. If a quantity is still a root input, the package makes that visible. If a throughput metric depends on an interconnect assumption five layers down, you can walk the dependency cone instead of trusting a handwave.

# gpu_stack

`gpu_stack` is a SymPy-backed symbolic model of the GPU training stack. It tracks named variables and equations from semiconductor transport and MOSFET behavior through memory hierarchy, arithmetic units, kernels, collectives, model architecture, optimizer math, training throughput, cluster composition, thermal plant behavior, and run economics.

The package is now internally consistent as a graph: importing `gpu_stack` registers **16 systems**, **1147 variables**, **23 constants**, and **620 equations**; `find_cycles()` returns **0 cycles** and `topological_sort()` succeeds across all **1147 variables**.

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

## Design rules

1. **Only universal physics constants are `Constant`s.** Everything else, including clocks, voltages, tensor shapes, GPU counts, tariffs, and optimizer hyperparameters, is a `Variable`.
2. **Every scope self-registers on import.** Variables, equations, and systems wire themselves into the global `Registry` at construction time.
3. **Load order is authoritative and centralized.** `gpu_stack.scopes.SCOPE_MODULES` is the single source of truth for scope import order.
4. **The project is symbolic first.** It is a graph of definitions, constraints, approximations, and stochastic relations. It is not yet a full end-to-end numeric solver or calibrated simulator.

## Package layout

```text
gpu_stack/
├── README.md
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
| `physical` | 108 | 61 | 51 | 15 | electrons, current, transistor, gate, RC delay, CMOS power, time-of-flight |
| `memory_cell` | 71 | 36 | 39 | 25 | SRAM 6T, DRAM 1T1C, flip-flop |
| `memory_subsystem` | 88 | 26 | 62 | 14 | register file, SMEM, TMEM, L1, L2, HBM bandwidth and latency |
| `precision` | 73 | 47 | 26 | 38 | FP formats, microscaling (MXFP4/NVFP4), stochastic rounding |
| `parallelism` | 78 | 32 | 46 | 13 | DP, TP, PP, EP, CP, FSDP memory, pipeline bubbles |
| `architecture` | 102 | 55 | 47 | 24 | transformer block, attention variants, MoE, KV cache, 6*P*T |
| `arithmetic` | 28 | 13 | 15 | 3 | ALU, FMA, Tensor Core MMA, peak SM FLOPs |
| `optimizer` | 83 | 35 | 49 | 27 | AdamW, Muon, MuonClip, optimizer state memory |
| `gpu` | 60 | 46 | 14 | 22 | SM count, die peak, package power, NVLink per GPU |
| `interconnect` | 44 | 23 | 20 | 6 | NVLink, IB, Spectrum-X, alpha-beta cost model |
| `kernel` | 66 | 42 | 24 | 6 | arithmetic intensity, roofline, matmul + attention kernels |
| `collective` | 29 | 23 | 6 | 9 | AllReduce, AllGather, ReduceScatter, All-to-all, async-TP |
| `training` | 61 | 49 | 15 | 8 | T_step = T_compute + T_ec + T_mb + T_bub, MFU, tokens/s |
| `cluster` | 90 | 55 | 36 | 20 | node -> rack -> cluster -> hyperscaler aggregation |
| `thermal` | 71 | 36 | 38 | 8 | junction-to-ambient resistance, coolant flow, PUE |
| `economics` | 72 | 41 | 31 | 6 | GPU amortization, $/kWh, $/token, run cost |

## Quick start

Install SymPy, put the repo on `PYTHONPATH`, and import the package.

```bash
pip install sympy
python -c "import gpu_stack; print(gpu_stack.Registry.stats())"
python -m gpu_stack.demo
```

### Inspect the registry

```python
import gpu_stack
from gpu_stack import Registry, find_cycles, topological_sort

print(Registry.stats())
print(find_cycles())
print(len(topological_sort()))
```

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

## How to inspect it

If you are looking at this as a hiring signal, start with the graph health instead of the domain breadth:

1. Run `python -m gpu_stack.demo` and check that the registry imports cleanly, topological sort succeeds, and cycle detection returns empty.
2. Read `gpu_stack/core/registry.py`, `gpu_stack/core/equation.py`, and `gpu_stack/core/graph.py` to see the modeling substrate.
3. Skim one low-level scope and one high-level scope side by side, for example `gpu_stack/scopes/physical_mosfet.py` and `gpu_stack/scopes/training.py`.
4. Open `gpu_stack/scopes/collective.py` and `gpu_stack/scopes/economics.py` to see how communication and cost are represented as first-class math, not notes in prose.
5. Check `tests/test_graph_health.py`, `tests/test_import.py`, and `tests/test_resolver.py` for the guardrails that keep the registry from quietly becoming nonsense.

What this repo shows about me: I like building explanatory infrastructure. If a technical domain feels like a stack of disconnected facts, my instinct is to turn it into a navigable system with names, invariants, and tests.

## Core types

- `Variable` carries identity, units, description, scope, symbol assumptions, optional metadata, and the back-references needed for dependency traversal.
- `Constant` is an immutable `Variable` with a fixed numeric value. The package currently ships **23** such constants in `constants.py`.
- `Equation` and its subclasses (`Inequality`, `Approximation`, `PiecewiseEquation`, `DifferentialEquation`, `IterativeEquation`, `StochasticRelation`) encode the actual mathematical relations.
- `System` groups variables and equations by scope.
- `Registry` is the global lookup surface for all registered objects.

## What this package is good for right now

- Inspecting symbolic dependencies across hardware, software, thermal, and economic layers.
- Writing and checking new equations in a single consistent registry.
- Exporting dependency cones and debugging graph structure.
- Demonstrating how training throughput and cost metrics reduce to lower-level assumptions.

## Current limitations

The model is broad, but it is still a modeling substrate, not a polished simulator. A few limits matter in practice:

- **Many quantities are still root inputs.** The graph currently exposes **519 root inputs**, which means many equations still need scenario values, presets, or deeper derivations.
- **Automatic end-to-end solving is thin.** The project supports per-equation symbolic solve and substitution, but it does not yet ship a full scenario evaluator that chooses among multiple valid defining relations and propagates values across the whole graph.
- **Metadata coverage is still shallow.** The framework supports references, dimensional checking, variable kinds, extensivity, and tensor shape metadata, but most scopes still use only the basic fields.
- **Several scope files are too large.** Some files now combine multiple subdomains and should be split again for maintainability.

## Project status docs

For the project-wide audit and next-step plan, see:

- [`./IMPROVEMENT_MAP.md`](./IMPROVEMENT_MAP.md)
- [`./ROADMAP.md`](./ROADMAP.md)
- [`./HANDOFF.md`](./HANDOFF.md)
- [`./CHANGELOG.md`](./CHANGELOG.md)
