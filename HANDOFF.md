# HANDOFF: gpu_stack granularity pass

## 0. TL;DR

You are continuing a systematic review-and-expansion pass on a Python package
called `gpu_stack`. The package models every equation and variable in the
GPU training stack, from single electrons up through hyperscale clusters,
using OOP + SymPy. The user (codename: Cúper) wants a specific iterative
loop performed on every file. All 22 planned passes are now done.
The next agent should treat this document as a project-status handoff plus a pointer to the new audit and roadmap docs.
As of April 18, 2026, the user changed the workflow and now wants roughly
five adjacent files per response when practical. Preserve dependency order.

Do not say "I can't because..." before trying. Say "here is how."

New planning docs added in pass 22:

* `IMPROVEMENT_MAP.md`, repo-wide audit with measured findings
* `ROADMAP.md`, sequenced follow-on work plan

## 1. Project overview

### 1.1 What this is

`gpu_stack/` is a Python package that represents the GPU training stack as
a graph of SymPy-backed Variables and Equations. Scope modules range from
`physical` (electrons, transistors, CMOS power) to `economics` (dollars
per token, training-run cost). Each scope registers its Variables and
Equations into a global Registry on import, enabling:

* dependency walks across arbitrary scopes
* symbolic manipulation and numeric substitution
* graph export to Graphviz DOT
* cycle detection
* topological sort

### 1.2 The one design rule

> Anything that is NOT a universal physics constant is a Variable.
> Variables can be defined by Equations whose RHS is an expression over
> other Variables, recursively. This applies down to transistor channel
> width, dielectric constants, MOSFET threshold voltage, clock frequency,
> adapter rank, Adam betas, etc.

The ONLY Constants are the ones in `constants.py`. Currently 23 of them
(speed of light, elementary charge, Planck, Boltzmann, etc.). If you find
yourself writing a literal number that looks universal, it still goes in as
a Variable unless it appears in a fundamental physical law.

### 1.3 User context

The user is an AI researcher named Cúper who requested this module for a
purpose he will reveal later. He explicitly said "this is totally unrelated
to the topic [of our prior conversation about GPU training and MFU]." Don't
speculate on the purpose. Just build the thing correctly.

## 2. User preferences (strict)

These are non-negotiable style rules. Violate them and the user will
reject the output.

* NO em dashes. Use comma, period, parenthesis, or colon.
* NO tricolons (rhetorical "three short punchy phrases"). Write in
  proper sentences.
* Don't say "passionate about," don't write skill sections, don't cite star
  counts.
* Voice profile roughly 40% authoritative / 40% cynical / 20% earnest.
  For code comments: direct, technically precise, no hedging.
* Max reasoning depth on every file. Don't truncate analysis.
* Don't fabricate or estimate numbers. If a value isn't known, say so in
  a comment. Never invent "~30 GHz" when you don't know.
* When listing variables or equations, use prose for bullets that span more
  than one sentence. No sub-1-sentence bullets.

## 3. Current state of the package

### 3.1 Stats after the partial pass

```
variables  : 1147
constants  : 23
equations  : 620
systems    : 16
root_inputs: 519   (Variables with no defining equation yet)
leaves     : 261   (Variables no other Variable depends on)
```

### 3.2 File tree

```
gpu_stack/
├── README.md
├── __init__.py               # imports all scopes in order
├── constants.py              # 23 universal physics constants
├── demo.py                   # example queries (run: python -m gpu_stack.demo)
├── core/                     # framework (WAS a single core.py; split in pass 1)
│   ├── __init__.py           # re-exports
│   ├── equation.py           # Equation + Inequality/Piecewise/Differential/Iterative/Stochastic
│   ├── graph.py              # topological_sort, find_cycles, subgraph, to_dot
│   ├── registry.py           # Registry with O(1) symbol cache, reset, stats
│   ├── system.py             # System (containment tree)
│   ├── units.py              # dimensional consistency via sympy.physics.units
│   └── variable.py           # Variable, Constant, VariableKind, Extensivity, Reference
└── scopes/
    ├── __init__.py           # SCOPE_MODULES load order, SCOPE_DESCRIPTIONS
    ├── physical.py           # pass 4 DONE, now aggregates helper modules
    ├── physical_semiconductor.py
    ├── physical_mosfet.py
    ├── physical_interconnect.py
    ├── physical_cmos_logic.py
    ├── physical_noise.py
    ├── memory_cell.py        # pass 5 DONE
    ├── memory_subsystem.py   # pass 6 DONE
    ├── precision.py          # pass 7 DONE
    ├── parallelism.py        # pass 8 DONE
    ├── architecture.py       # pass 9 DONE
    ├── arithmetic.py         # pass 10 DONE
    ├── optimizer.py          # pass 11 DONE
    ├── gpu.py                # pass 12 DONE
    ├── interconnect.py       # pass 13 DONE
    ├── kernel.py             # pass 14 DONE
    ├── collective.py         # pass 15 DONE
    ├── training.py           # pass 16 DONE
    ├── cluster.py            # pass 17 DONE
    ├── thermal.py            # pass 18 DONE
    └── economics.py          # pass 19 DONE
# plus:
#   pass 20: gpu_stack/__init__.py integration DONE
#   pass 21: gpu_stack/demo.py DONE
#   pass 22: gpu_stack/README.md DONE
```

### 3.3 What already works

```bash
pip install sympy
cd <path containing gpu_stack>
python -c "import gpu_stack; print(gpu_stack.Registry.stats())"
python -m gpu_stack.demo
```

`gpu_stack.core.find_cycles()` now reports zero cycles. The old thermal
`pue <-> dc_total_power` loop is fixed. The earlier physical-layer ohmic-drop
fix from batch 7-11 is still intact.

`gpu_stack.core.topological_sort()` now succeeds across the whole package.
`python -m gpu_stack.demo` also runs cleanly, and the rack-FLOPs substitution
example now evaluates numerically instead of printing a symbolic `False`.

## 4. The loop

This is the exact methodology the user demanded. Preserve dependency
order and do not skip any step. The one workflow change is batching: the
user now wants roughly five adjacent files per response when practical.

```
FOR each batch of roughly 5 adjacent files in dependency_order:
  FOR each file in the batch:
    1. READ the file fully (not just skim).
    2. LIST problems and granularity gaps. Be concrete. Do not hand-wave.
       Gaps are things like "missing velocity saturation model," not
       "could use more detail."
    3. IMPLEMENT improvements. Either extend in place or split into
       additional files if the file is getting unwieldy (> ~600 lines or
       > 3 clearly distinct sub-scopes).
  4. VERIFY: `python -c "import gpu_stack"` must succeed. The demo
     must still run. Also check that cycle detection did not regress.
  5. REPORT what changed in the whole batch. Then move to the next batch.
```

### 4.1 Rule: "find how to make it work, don't eliminate ways that won't"

When reviewing a file, ask: how can I decompose this further? What am I
leaving as a magic number that could be derived from something deeper?
What corner case am I ignoring (velocity saturation at high fields,
quantum tunneling at short channels, NUMA effects at cache, skin effect at
high-frequency signaling, thermal noise floor, Shannon capacity limit)?

Don't reason from "this is too hard." Reason toward "what's the minimum
primitive needed to express this correctly."

### 4.2 Navigation order (by dependency depth)

```
Pass  File                              Depends on
----  --------------------------------  --------------------------------
 1    gpu_stack/core/*                  nothing (sympy, stdlib)           [DONE]
 2    gpu_stack/constants.py            core                              [DONE]
 3    gpu_stack/scopes/__init__.py      nothing                           [DONE]
 4    gpu_stack/scopes/physical.py      core, constants                   [DONE]
 5    gpu_stack/scopes/memory_cell.py   core                              [DONE]
 6    gpu_stack/scopes/memory_subsystem.py  core                          [DONE]
 7    gpu_stack/scopes/precision.py     core                              [DONE]
 8    gpu_stack/scopes/parallelism.py   core                              [DONE]
 9    gpu_stack/scopes/architecture.py  core                              [DONE]
10    gpu_stack/scopes/arithmetic.py    core, physical                    [DONE]
11    gpu_stack/scopes/optimizer.py     core, parallelism                 [DONE]
12    gpu_stack/scopes/gpu.py           core, arithmetic, memory_subsystem, physical  [DONE]
13    gpu_stack/scopes/interconnect.py  core, gpu, physical               [DONE]
14    gpu_stack/scopes/kernel.py        core, gpu, memory_subsystem       [DONE]
15    gpu_stack/scopes/collective.py    core, interconnect                [DONE]
16    gpu_stack/scopes/training.py      core, gpu, interconnect, parallelism, architecture  [DONE]
17    gpu_stack/scopes/cluster.py       core, gpu, memory_subsystem, interconnect  [DONE]
18    gpu_stack/scopes/thermal.py       core, constants, gpu, cluster     [DONE]
19    gpu_stack/scopes/economics.py     core, gpu, thermal, cluster, training, parallelism [DONE]
20    gpu_stack/__init__.py             integrates scopes                 [DONE]
21    gpu_stack/demo.py                 uses everything                   [DONE]
22    gpu_stack/README.md               docs                              [DONE]
```

## 5. Per-file gap list (what the prior pass already identified)

Notes from the incomplete review. Treat these as starting points, not
the full set. Find more in your own read-through.

### 5.1 physical.py (pass 4, DONE)

Done in this pass. `physical.py` is now a stable public aggregator over
`physical_semiconductor.py`, `physical_mosfet.py`, `physical_interconnect.py`,
`physical_cmos_logic.py`, and `physical_noise.py`. The notes below are now
implemented and are preserved here as historical context for what was added:

* `physical/semiconductor.py`: carrier transport (drift, diffusion, Einstein
  relation `D/mu = kT/q`), velocity saturation, generation-recombination,
  band gap, effective mass.
* `physical/mosfet.py`: triode / saturation / cutoff / subthreshold regions
  as a `PiecewiseEquation`; short-channel effects (DIBL, channel-length
  modulation); gate tunneling leakage; body effect.
* `physical/cmos_logic.py`: gates, fanout, Elmore delay, short-circuit
  power during switching, adiabatic limit (Landauer `k_B T ln 2` per bit
  erasure).
* `physical/interconnect_physics.py`: wire RC (distributed, not lumped),
  skin effect at high frequency, via resistance, crosstalk.
* `physical/noise.py`: Johnson-Nyquist thermal noise
  `<v_n^2> = 4 k_B T R Δf`, shot noise `<i_n^2> = 2 q I Δf`, flicker (1/f)
  noise.

Known missing pieces:

* Subthreshold slope floor `S = ln(10) * k_B T / q` (60 mV/decade at 300K)
  as a hard lower bound. Use `Inequality` from `core.equation`.
* Drift velocity saturation `v_d = mu*E / (1 + mu*E/v_sat)`.
* Einstein relation between mobility and diffusion.
* Gate capacitance per area: `C_ox = epsilon_ox / t_ox` where `t_ox` is
  oxide thickness (Variable) and `epsilon_ox` is oxide permittivity
  (material Variable, not a Constant).
* Wire RC scaling with technology node.

### 5.2 memory_cell.py (pass 5, DONE)

Done in this pass. The scope now includes explicit 6T/8T/10T SRAM variants,
SRAM stability margins, DRAM charge sharing and retention distribution, and
flip-flop metastability equations. The list below is historical context for
what got added:

* 8T and 10T SRAM variants with dual-port read.
* SRAM read/write noise margin (SNM, WNM) from transistor sizing.
* DRAM charge-sharing sensing `V_dev = V_cell * C_s / (C_s + C_bl)`.
* DRAM retention time distribution (log-normal over cells).
* Sense amplifier: offset voltage, gain, resolve time.
* Flip-flop clock-to-Q, setup, hold; metastability rate
  (`MTBF_meta = exp(t_resolve / tau) / (f_clk * f_data * T_window)`).
* Multi-port register file bank conflict.
* Error correction overhead (SECDED: 8 parity bits per 64-bit word).

### 5.3 memory_subsystem.py (pass 6, DONE)

Done in this pass. The scope now includes register-bank effects, L1/L2
organization, translation overhead, PCIe / unified-memory migration, NUMA
penalty ratios, and usable HBM bandwidth/capacity after overheads. The list
below is historical context for what got added:

* Cache organization: associativity, line size, sets, ways, replacement
  policy (LRU, pseudo-LRU).
* Cache miss penalty as a function of which level hits.
* TLB: entries, miss penalty, huge pages.
* NUMA effects on multi-socket hosts.
* PCIe Gen4/5/6 bandwidth per lane + lanes per GPU.
* CXL memory (Type 1/2/3 devices, bandwidth, latency).
* HBM refresh overhead (fraction of BW lost to refresh).
* Cache coherence state transitions (MESI, MOESI).
* NVIDIA unified memory page migration cost.
* Memory compression ratio on Hopper/Blackwell.

### 5.4 precision.py (pass 7, DONE)

Done in batch 7-11. The scope now includes IEEE-754 range endpoints,
subnormal and flush-to-zero behavior, NaN and infinity code counts,
quantization error variance, directional-rounding bias scales, stochastic
rounding as both variance and a stochastic relation, microscaling with
multilevel scale amortization, block floating point, dynamic fixed point,
TF32 and low-bit integer helpers, posit useed, logarithmic-number-system
error, FP16 loss scaling, and a symbolic Random Hadamard Transform block.

### 5.5 parallelism.py (pass 8, DONE)

Done in batch 7-11. The scope now includes explicit SP, batch and token
decomposition, activation-memory and recomputation tradeoffs, ZeRO stage
1/2/3 memory breakdowns, CPU and NVMe offload timing, FSDP all-gather
buffers, multiple pipeline schedules (GPipe, 1F1B, interleaved, DualPipe,
Chimera, zero-bubble), plus TP, EP, and CP communication volume models.

### 5.6 architecture.py (pass 9, DONE)

Done in batch 7-11. The scope now includes embeddings, positional
encodings, symbolic attention equations, GQA and MLA cache math, FFN
variants, LayerNorm and RMSNorm, activation functions, encoder-decoder
parameter split, and materially fuller MoE structure including expert
params, router params, capacity, load-balance loss, z-loss, and active
FLOP accounting.

### 5.7 arithmetic.py (pass 10, DONE)

Done in batch 7-11. The scope now includes Tensor Core issue efficiency,
effective peak Tensor Core throughput, structured sparsity group math and
sparse speedup, DP4A and DP2A integer dot-product accounting, and SFU
throughput with an SFU-limited lower bound on time per token.

### 5.8 optimizer.py (pass 11, DONE)

Done in batch 7-11. The scope now includes SGD with momentum, Nesterov,
RMSProp, LAMB, Lion, EMA, Shampoo state sizing, distributed Shampoo
sharding, learning-rate schedules (warmup, cosine, inverse-sqrt, WSD),
and dynamic loss scaling. The Muon Newton-Schulz placeholder was replaced
with a real `IterativeEquation` carrying the polynomial map, coefficients,
residual, and tolerance.

### 5.9 gpu.py (pass 12, DONE)

Done in batch 12-16. The scope now aggregates GPU-level compute, memory,
and package behavior rather than stopping at a few headline specs. It now
includes raw, effective, sparse, and power-limited peak FLOPs; GPU-level
DP4A, DP2A, and SFU throughput; aggregate register, shared-memory, TMEM,
L2, and HBM capacity and bandwidth; and GPU-level aliases for PCIe, CXL,
NVLink, and NIC bandwidth.

It also now models compute power from equivalent gate activity, memory power
from HBM traffic, fabric power from NVLink and NIC utilization, total
package power, TDP headroom, a piecewise throttle factor when modeled power
exceeds TDP, energy-efficiency metrics, HBM sweep time, and roofline balance
points in both bytes-per-FLOP directions.

### 5.10 interconnect.py (pass 13, DONE)

Done in batch 12-16. The scope now includes packet-level and path-level
fabric modeling instead of a single alpha-beta stub. It now covers payload
vs header efficiency, nominal and effective bandwidth after protocol and
fabric losses, explicit hop count and hop latency, host-stack latency,
message packet count, bandwidth-delay product, and a queueing approximation
for serialization-delay inflation under load.

It also now distinguishes NVLink-scale and scale-out paths with separate
alpha and beta parameters, average hop counts, rack bisection bandwidth,
rails per GPU, oversubscription-adjusted scale-out bandwidth, and an updated
intra-vs-scale-out bandwidth ratio built from effective rather than nominal
throughput.

### 5.11 kernel.py (pass 14, DONE)

Done in batch 12-16. The scope now models kernels as resource-bounded
programs rather than just a single roofline point. It now includes separate
HBM, L2, shared-memory, and register traffic; a generalized roofline as the
minimum of compute and per-level bandwidth ceilings; lower bounds on time
from compute, memory, and latency; and an occupancy-driven latency-hiding
factor built from active warps per SM.

It also now includes CTA resource accounting from threads, registers, and
shared memory; active-block and occupancy formulas; tiled GEMM tile-count,
traffic, and arithmetic-intensity formulas; and attention-specific naive vs
FlashAttention-style IO accounting.

### 5.12 collective.py (pass 15, DONE)

Done in batch 12-16. The scope now includes multiple collective algorithms
and message-size-dependent choices. It now covers ring, tree, and
hierarchical AllReduce; ring and hierarchical AllGather and ReduceScatter;
pairwise and hierarchical all-to-all; effective bandwidth for the selected
algorithm; and a latency crossover size between algorithm families.

It also now models topology-aware decomposition through ranks per node and
node count, MoE all-to-all inflation from imbalance, and overlap math that
turns tile-level compute time into exposed communication time for async
collectives.

### 5.13 training.py (pass 16, DONE)

Done in batch 12-16. The scope now wires model FLOPs, chip FLOPs,
communication, memory traffic, and wall-clock overhead into one training
step model. It now includes dense and active-MoE step FLOPs, recomputation
and optimizer-overhead multipliers, MFU and HFU, FLOPs per token, data-
parallel gradient-sync cost, TP and EP exposed communication, CP overlap,
offload time, HBM bytes per step, memory-bound time, and pipeline-bubble /
straggler / restart / eval overhead fractions.

It also now includes tokens per second, energy per step and per token,
tokens per joule, nominal vs availability-adjusted wall clock, and a
Chinchilla-style parameter-to-token ratio with support for both dense and
active-MoE parameter counts.

### 5.14 cluster.py (pass 17, DONE)

Done in batch 17-21. The scope is no longer just a thin count aggregator. It
now models node composition, local SSD capacity and bandwidth, node and rack
power breakdown, rack-to-site aggregation, data-ingest limits from storage,
scheduler queue and provisioning delay, failure domains, exponential-failure
MTBF approximations, checkpoint time, Young-style optimal checkpoint interval,
reliability-driven availability estimate, and inter-site scale-across links
with both bandwidth and latency.

It also adds site-level planning power via a coarse overhead multiplier, which
is intentionally separate from the real facility-power model in `thermal.py`.
That avoids smearing thermal assumptions back into cluster planning.

### 5.15 thermal.py (pass 18, DONE)

Done in batch 17-21. The old circular definition between `thermal.dc.pue` and
`thermal.dc.total_power` is gone. `thermal.eq.pue_definition` remains the one
definitional relation, and `thermal.eq.dc_total_power` now derives total site
power from explicit cooling and facility-overhead terms instead of reusing PUE.

The scope now includes package-path resistance components (die attach, TIM,
spreader, cold plate, fluid film), case temperature, coolant inlet/outlet and
average temperature, volumetric flow, pump power per GPU and per site, fan
power, heat reuse, free-cooling piecewise logic from wet-bulb temperature,
chiller load and power, cooling-tower auxiliary power, CDU power, humidity
control, water evaporation and blowdown, WUE, dew-point headroom, and ASHRAE-
style inlet and humidity inequalities.

### 5.16 economics.py (pass 19, DONE)

Done in batch 17-21. The scope now prices the whole deployment rather than only
GPU amortization plus power. It adds node, rack, site, and facility capex
breakdowns, residual value, depreciable base, site utilization, job share of
cluster, fixed-cost allocation, blended peak/off-peak electricity tariff,
demand charges, water cost, maintenance, staff, transit, carbon cost, run NPV,
and inference-token recovery targets.

Run cost is now built from allocated capex, power, and non-power opex, then
reduced to cost per step, token, and delivered FLOP using the training-level
wall-clock and achieved-FLOP variables.

### 5.17 gpu_stack/__init__.py (pass 20, DONE)

Done in batch 17-21. The top-level package no longer hardcodes a second stale
import order. It now iterates `scopes.SCOPE_MODULES`, binds each imported
module into the package namespace, and exposes graph helpers like
`topological_sort`, `find_cycles`, `subgraph`, and `to_dot` directly from the
top level. This makes pass 3's authoritative scope ordering actually control
integration.

### 5.18 demo.py (pass 21, DONE)

Done in batch 17-21. The demo now reports graph health, prints the authoritative
loaded-scope list, demonstrates that cycle detection is clean, shows a working
topological-sort summary, and fixes the old rack-FLOPs example so it evaluates
through the node-level equation instead of printing a misleading symbolic
result. It also adds a PUE solve example to show that one equation is enough;
you do not need a second cyclic inverse equation in the graph.

## 6. Known bugs

No known blocking graph bugs remain after batch 17-21. Keep an eye on three
things while doing the README pass:

### 6.1 Historical fix: thermal.py pue / dc_total_power cycle

This is fixed. Do not reintroduce the cycle by writing both `PUE = P_dc / P_IT`
and `P_dc = PUE * P_IT` as separate defining equations with both left-hand
sides registered. Keep one definitional equation and let users solve it
symbolically in either direction.

### 6.2 Historical fix: top-level import order coupling

This is fixed. `gpu_stack/__init__.py` now iterates `scopes.SCOPE_MODULES`. If
you touch imports again, do not drift back to a second manually curated list.

### 6.3 Scope tags are still free-form

Variable `scope=` strings are not compiler-enforced. When touching any file,
keep scope tags aligned with the file stem so query helpers like
`Registry.by_scope()` stay trustworthy.

### 6.4 Verification note from batch 7-11

The physical-layer ohmic-drop fix is still important. `physical_semiconductor.py`
uses a separate ohmic-drop Variable so current, field, and externally applied
voltage do not collapse back into another accidental cycle. Do not undo that.

## 6.5 Next file

All originally planned files are now touched. The next work should start from
`IMPROVEMENT_MAP.md` and `ROADMAP.md`, not from another untouched-file pass.

## 7. Code conventions used throughout

### 7.1 File structure per scope

```python
"""
scopes/<name>.py
================

Short docstring: what this scope covers, what's in it, what's not.
"""

import sympy as sp
from ..core import var, eq, System
# Optional subclasses:
from ..core import (
    Inequality, Approximation, PiecewiseEquation,
    DifferentialEquation, IterativeEquation, StochasticRelation,
)
# Dependencies on other scopes (use sparingly, keep the tree acyclic):
from .<other_scope> import <specific_variable>

sys_<name> = System(name="<name>", scope="<name>", description="...")


# ---------------------------------------------------------------------------
# Section A: something
# ---------------------------------------------------------------------------

x = var("scope.thing", "X", "unit", "description.", scope="<scope>")
# ... more Variables ...

eq_thing = eq(
    "scope.eq.thing",
    x.symbol,                  # LHS: a Variable's symbol or expression
    sp.Function(y.symbol, z.symbol),  # RHS: any sympy expr
    "English description of what this equation says.",
    references=["paper citation", "textbook ch"],
)


# ---------------------------------------------------------------------------
# Registration with the System (so System.all_variables() returns them)
# ---------------------------------------------------------------------------

for v in [x, ...]:
    sys_<name>.add(v)
for e in [eq_thing, ...]:
    sys_<name>.add(e)
```

### 7.2 Naming conventions

* Variable names: `<scope>.<subscope>.<thing>`, e.g.
  `physical.mosfet.v_gs`.
* Equation names: `<scope>.eq.<thing>`, e.g. `physical.eq.drift_velocity`.
* System name: matches the file stem.
* SymPy symbol: short and readable, like `V_GS`, `f_clk`, `BW_HBM`.
  Use underscores, no spaces.
* Python identifier for the Variable: descriptive, matches last segment of
  `name`, e.g. `v_gs = var("physical.mosfet.v_gs", "V_GS", ...)`.

### 7.3 When to use which Equation subclass

* `eq(...)` or `Equation(...)`: standard algebraic equality.
* `Inequality(...)`: constraints like setup-time + clk-to-Q + prop-delay
  < clock-period.
* `Approximation(...)`: when the RHS is an approximation with a stated
  validity condition (e.g. Taylor expansion valid for small x).
* `PiecewiseEquation(...)`: when the LHS has different formulas in
  different regimes (MOSFET cutoff / triode / saturation).
* `DifferentialEquation(...)`: capacitor charging dV/dt = I/C, DRAM leakage
  dQ/dt = -I_leak, Newton F=ma.
* `IterativeEquation(...)`: Newton-Schulz, fixed-point iterations, and
  anything where the value is produced by repeated application of a map.
* `StochasticRelation(...)`: stochastic rounding, noise, dropout, shot
  noise.

### 7.4 How to split a file

Rule of thumb: if a file grows past ~600 lines OR contains 3+ clearly
distinct sub-scopes, split. When splitting:

1. Create `scopes/<scope>/` directory.
2. Add `scopes/<scope>/__init__.py` that imports all submodules so that
   `from .<scope> import specific_var` still works from other scopes.
3. Move existing content into submodule files.
4. Update the parent scope's System to aggregate subsystems.

Example: `physical.py` -> `physical/{semiconductor.py, mosfet.py,
cmos_logic.py, interconnect_physics.py, noise.py, __init__.py}` with
`physical/__init__.py` re-exporting the public names.

### 7.5 Registration pattern

Every Variable and Equation auto-registers with the global Registry on
construction. The `sys_<name>.add(...)` loops exist solely so that
`System.all_variables()` can enumerate them in their scope. Don't forget
the registration loop at the bottom of the file; else Variables exist in
the Registry but not in their System.

## 8. Verification

### 8.1 After every batch

```bash
# Package must still import cleanly:
python -c "import gpu_stack; s = gpu_stack.Registry.stats(); print(s)"

# The demo must still run:
python -m gpu_stack.demo

# Cycle detection must not regress:
python -c "
import gpu_stack
cycles = gpu_stack.core.find_cycles()
if cycles:
    print('cycles:', [[v.name for v in c] for c in cycles])
else:
    print('no cycles')
"
```

### 8.2 Expected trajectory

After each batch, the stats should grow. Current checkpoints:

```
after pass 6  : 518 vars, 216 eqs
after pass 11 : 775 vars, 363 eqs  (current)
... target at pass 19 : roughly 900-1300 vars, 450-700 eqs
```

These are rough targets, not requirements. Don't pad.

### 8.3 Sanity checks to run

```python
# Sanity: MFU still depends on transistor-level variables
from gpu_stack import Registry
mfu = Registry.variables["training.mfu"]
deps = {v.name for v in mfu.dependencies()}
assert "physical.clock_frequency" in deps, "MFU lost its connection to physics"

# Sanity: no orphan Variables (roots should shrink as you define more)
roots = Registry.roots()
print(f"{len(roots)} root inputs remaining")

# Sanity: scope consistency
for v in Registry.variables.values():
    expected_scope = v.name.split(".")[0]
    if expected_scope not in ("physics",):
        if v.scope != expected_scope:
            print(f"scope mismatch: {v.name} scope={v.scope}")
```

## 9. Deliverable format

After each batch:

1. Write a short report: what you changed, what you added, and how many new
   Variables and Equations landed across the batch.
2. Run the verification commands. Report stats and any cycles.
3. Move on to the next adjacent batch in dependency order.

Do NOT stop to ask for approval between adjacent files. Keep going until the
current response batch is done, then hand off the next untouched file clearly.

## 10. One more time for emphasis

* Physics constants = the only `Constant`. Everything else is `Variable`.
* Variables can be sub-defined recursively.
* No em dashes. No tricolons. Direct, technical voice.
* Find how to make it work. Don't list reasons it won't.
* Work in dependency order. Batch roughly five adjacent files per response. Don't skip steps of the loop.
* Report briefly, move on.
* Verify after each pass.

Good luck.
