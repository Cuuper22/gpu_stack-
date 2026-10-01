"""
gpu_stack.calculator
====================

A training-cost calculator that is the equation graph, not a copy of it.

Give it a model size, a token count and a GPU type. It returns how long the
run takes, how much energy it uses and what it costs. Every number comes from
resolving the registered graph equations (``gpu_stack.core.resolver``) with
the calculator's inputs as symbols, so the closed-form expressions that the
web calculator evaluates are the graph's own.

What the graph resolves (all by equation name, see ``breakdown()``):

* run time: ``training.eq.wallclock`` and the equations under it
  (6 x parameters x tokens FLOPs, divided by the speed the cluster sustains);
* electricity cost: ``econ.eq.run_power_cost`` (facility power x time x price);
* hardware cost: ``econ.eq.amortized`` (price spread over its useful life) and
  ``econ.eq.run_hw_cost``;
* total and per-token cost: ``econ.eq.run_total`` and ``econ.eq.cost_per_token``.

The calculator fixes the graph's loose ends by pinning a few intermediate
variables, the same way the shipped presets do (for example the DGX H100
preset pins ``gpu.peak_flops_power_limited`` to peak x 40%). Those pins are
shown as "settings" in ``breakdown()``:

* ``gpu.peak_flops_power_limited`` = peak FLOP/s x MFU (speed actually achieved);
* ``thermal.dc.total_power`` = PUE x GPUs x TDP x GPU load x (1 + server extra);
* ``econ.gpu.capex`` = GPU price x (1 + other hardware share);
* ``econ.asset.useful_life`` = years x 31,557,600 s;
* ``econ.job.capex_rate`` = GPUs x the graph's per-GPU amortized rate;
* neutral closures: no recompute, no exposed communication, availability 1,
  the job owns the whole cluster, no staff, water, maintenance or network cost.

Three small things are done outside the graph, because the graph has no
variable for them: unit conversions (seconds to days, kWh to MWh), GPU-hours
(GPUs x seconds / 3600) and energy, which is the graph's run power cost
divided by the electricity price (the graph multiplies energy by price).

Defaults that are not hardware facts are labelled assumptions. Real runs reach
roughly 30-55% MFU; 40% is a middle guess, not a measurement.

Reference (hardware specs):

* NVIDIA H100 product page, H100 SXM: "BFLOAT16 Tensor Core 1,979 teraFLOPS"
  (footnote: with sparsity, so dense is half, 989.4 teraFLOPS), "Max TDP up to
  700W", 80 GB memory. https://www.nvidia.com/en-us/data-center/h100/
* NVIDIA A100 datasheet, A100 80GB SXM: "BFLOAT16 Tensor Core 312 TFLOPS | 624
  TFLOPS* (*with sparsity)", "Max TDP SXM 400W", 80 GB memory.
  https://www.nvidia.com/en-us/data-center/a100/
* B200 is left out on purpose: NVIDIA's public pages list the 8-GPU system
  power (about 14.3 kW for DGX B200) but no per-GPU TDP, and the datasheet
  could not be read. Add it when a per-GPU figure can be cited.
* Electricity price default: U.S. EIA Electric Power Annual 2024, industrial
  average 8.13 cents/kWh (the repo's economics preset).
* H100 price default: 2024 channel range $27,000-$40,000 per card, $30,000
  used (the repo's DGX H100 closure preset). The A100 price is a rough
  assumption with no citation.
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import sympy as sp

import gpu_stack  # noqa: F401  (registers every variable and equation)
from gpu_stack.core.registry import Registry
from gpu_stack.core.resolver import resolve
from gpu_stack.presets.hardware import H100_SXM_BF16_DENSE_FLOPS

# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------
TAG_USER = "you entered"
TAG_SPEC = "hardware spec (cited)"
TAG_ASSUMPTION = "assumption"

SECONDS_PER_YEAR = 365.25 * 86400.0  # same year length as the DGX H100 closure preset
GRAPH_VARIANTS = {"training.flops_per_step": "dense", "training.scaling_params": "dense"}

# ---------------------------------------------------------------------------
# GPU table
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GPU:
    """One accelerator: datasheet numbers plus a rough default purchase price."""

    key: str
    label: str
    peak_flops: float  # dense BF16, FLOP/s
    tdp_w: float
    memory_gb: float
    price_usd: float  # assumption, see module docstring
    price_note: str
    cite: str


GPUS: Dict[str, GPU] = {
    "H100-SXM": GPU(
        key="H100-SXM",
        label="NVIDIA H100 SXM",
        peak_flops=H100_SXM_BF16_DENSE_FLOPS,
        tdp_w=700.0,
        memory_gb=80.0,
        price_usd=30_000.0,
        price_note="2024 channel range $27,000-$40,000 per card; $30,000 is the middle (repo DGX H100 preset).",
        cite=(
            "NVIDIA H100 product page, H100 SXM: BFLOAT16 Tensor Core 1,979 teraFLOPS with sparsity "
            "(dense is half, 989.4 teraFLOPS); Max TDP up to 700W; 80 GB memory."
        ),
    ),
    "A100-80GB-SXM": GPU(
        key="A100-80GB-SXM",
        label="NVIDIA A100 80GB SXM",
        peak_flops=312e12,
        tdp_w=400.0,
        memory_gb=80.0,
        price_usd=15_000.0,
        price_note="Rough assumption, no citation.",
        cite=(
            "NVIDIA A100 datasheet, 80GB SXM: BFLOAT16 Tensor Core 312 TFLOPS (624 with sparsity); "
            "Max TDP SXM 400W; 80 GB memory."
        ),
    ),
}
_GPU_ALIASES = {
    "h100": "H100-SXM",
    "h100-sxm": "H100-SXM",
    "h100-sxm-80gb": "H100-SXM",
    "a100": "A100-80GB-SXM",
    "a100-sxm": "A100-80GB-SXM",
    "a100-80gb": "A100-80GB-SXM",
    "a100-80gb-sxm": "A100-80GB-SXM",
    "a100-sxm-80gb": "A100-80GB-SXM",
}


def get_gpu(name: "str | GPU") -> GPU:
    """Look up a GPU by name (case-insensitive, a few common spellings)."""
    if isinstance(name, GPU):
        return name
    key = _GPU_ALIASES.get(name.strip().lower().replace(" ", "-").replace("_", "-"))
    if key is None:
        for k in GPUS:
            if k.lower() == name.strip().lower():
                key = k
    if key is None:
        raise ValueError(f"unknown GPU {name!r}; choose one of {sorted(GPUS)}")
    return GPUS[key]


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InputSpec:
    id: str
    label: str
    unit: str
    default: Optional[float]  # None: comes from the GPU table or must be entered
    tag_default: str
    tooltip: str
    advanced: bool = False
    lo: Optional[float] = None
    hi: Optional[float] = None


INPUTS: Dict[str, InputSpec] = {
    s.id: s
    for s in [
        InputSpec("params", "Model size", "parameters", None, TAG_USER,
                  "How many numbers (weights) the model learns. A 7B model has 7 billion."),
        InputSpec("tokens", "Training data", "tokens", None, TAG_USER,
                  "How much text the model reads during training. A token is roughly three quarters of a word."),
        InputSpec("n_gpus", "Number of GPUs", "GPUs", None, TAG_USER,
                  "How many graphics chips work on the run at once. This changes how long it takes, not what it costs."),
        InputSpec("peak_flops", "Chip peak speed", "FLOP/s", None, TAG_SPEC,
                  "The most arithmetic one chip can do per second on paper (dense BF16, from the datasheet).",
                  advanced=True),
        InputSpec("tdp_w", "Chip power rating", "W", None, TAG_SPEC,
                  "The power a chip is designed to draw at full load (TDP, from the datasheet).", advanced=True),
        InputSpec("mfu", "GPU speed actually achieved (MFU)", "fraction of peak", 0.40, TAG_ASSUMPTION,
                  "Model FLOPs utilization: the share of the chip's paper speed that real training reaches. "
                  "Real runs: 30-55%. 40% is a middle guess.", advanced=True, lo=0.05, hi=1.0),
        InputSpec("pue", "Datacenter overhead (PUE)", "x", 1.2, TAG_ASSUMPTION,
                  "Power usage effectiveness: total building power divided by computer power. "
                  "1.2 means cooling and other overhead add 20%.", advanced=True, lo=1.0, hi=3.0),
        InputSpec("electricity_price", "Electricity price", "USD/kWh", 0.0813, TAG_ASSUMPTION,
                  "What one kilowatt-hour costs. Default is the 2024 U.S. industrial average (EIA).",
                  advanced=True, lo=0.0, hi=2.0),
        InputSpec("gpu_price", "GPU purchase price", "USD", None, TAG_ASSUMPTION,
                  "What one GPU costs to buy. Default depends on the GPU and is a rough market figure.",
                  advanced=True, lo=0.0),
        InputSpec("useful_life_years", "Years of use before replacement", "years", 4.0, TAG_ASSUMPTION,
                  "The hardware's price is spread over this many years. Longer life means cheaper hours.",
                  advanced=True, lo=0.5, hi=15.0),
        InputSpec("residual_fraction", "Resale value at end of life", "fraction of price", 0.05, TAG_ASSUMPTION,
                  "The share of the purchase price you get back when the GPU is retired.",
                  advanced=True, lo=0.0, hi=0.9),
        InputSpec("other_hardware_fraction", "Servers, network and building, as a share of GPU price", "fraction",
                  0.40, TAG_ASSUMPTION,
                  "Each GPU needs a server, network and space. Default 40% follows the repo's DGX H100 cost "
                  "preset: server parts about 18% of the GPU price, rack about 5%, building power and cooling "
                  "about 19%.", advanced=True, lo=0.0, hi=3.0),
        InputSpec("gpu_power_fraction", "GPU power draw during training", "fraction of rating", 0.80, TAG_ASSUMPTION,
                  "Training rarely pulls the full rated power. 80% is a guess; measured values are often 60-90%.",
                  advanced=True, lo=0.2, hi=1.0),
        InputSpec("server_power_fraction", "Extra server power (CPUs, fans, network)", "fraction of GPU power",
                  0.25, TAG_ASSUMPTION,
                  "Power drawn by the rest of the server, as a share of the GPUs' own power.",
                  advanced=True, lo=0.0, hi=2.0),
    ]
}
INPUT_ORDER: Tuple[str, ...] = tuple(INPUTS)

# Settings that the calculator pins to neutral values so the graph resolves.
NEUTRAL_SETTINGS: List[Dict[str, str]] = [
    {"graph_variable": "training.recompute_overhead", "value": "1",
     "text": "No extra work from re-computing results to save memory."},
    {"graph_variable": "training.optimizer_flop_multiplier", "value": "1",
     "text": "The optimizer's extra arithmetic is ignored."},
    {"graph_variable": "training.t_exposed_comm", "value": "0",
     "text": "No time lost waiting for the network (it is folded into the speed actually achieved)."},
    {"graph_variable": "training.t_mem_bound", "value": "0",
     "text": "No extra time waiting on memory (also folded into the speed actually achieved)."},
    {"graph_variable": "training.overhead_fraction", "value": "0",
     "text": "No idle time added to each step."},
    {"graph_variable": "training.cluster_availability", "value": "1",
     "text": "The cluster never breaks and no work is repeated."},
    {"graph_variable": "econ.job.share_of_cluster", "value": "1",
     "text": "This run uses the whole cluster."},
    {"graph_variable": "econ.run.opex_misc_cost", "value": "0",
     "text": "No staff, maintenance, water, network or carbon cost."},
    {"graph_variable": "arch.tokens_per_step", "value": "4194304",
     "text": "Tokens per step. It cancels out of every result."},
]
_TOKENS_PER_STEP = 4_194_304

# ---------------------------------------------------------------------------
# Plain-English names for graph variables that appear in a chain
# ---------------------------------------------------------------------------

# variable -> (plain label, plain formula, unit)
PLAIN_STEPS: Dict[str, Tuple[str, str, str]] = {
    "training.peak_flops_power_limited": (
        "Speed of the whole cluster", "number of GPUs x speed achieved per GPU", "FLOP/s"),
    "training.n_steps": ("Number of training steps", "tokens / tokens per step", "steps"),
    "arch.flops.step_dense": (
        "Arithmetic in one step", "6 x parameters x tokens per step", "FLOP"),
    "training.flops_per_step": ("Arithmetic in one step (training view)", "same number, named in the training part of the graph", "FLOP"),
    "training.flops_executed_per_step": (
        "Arithmetic actually done in one step", "arithmetic per step x recompute factor x optimizer factor (both 1)",
        "FLOP"),
    "training.t_compute": (
        "Time for the arithmetic in one step", "arithmetic done / cluster speed", "s"),
    "training.t_step_nominal": (
        "Step time before extra waiting", "compute time + network wait + memory wait (last two are 0)", "s"),
    "training.t_bubbles": ("Idle time added to each step", "step time x overhead fraction (0)", "s"),
    "training.t_step": ("Time for one step", "step time + idle time", "s"),
    "training.wallclock_nominal": ("Run time if nothing breaks", "steps x time per step", "s"),
    "training.wallclock": ("Run time (wall clock)", "run time if nothing breaks / availability (1)", "s"),
    "econ.power.price_kwh": ("Electricity price", "price (one flat rate, no peak pricing)", "USD/kWh"),
    "econ.power.price_ws": ("Electricity price per watt-second", "price per kWh / 3,600,000", "USD/(W*s)"),
    "econ.job.dc_power": ("Power the datacenter draws for this run", "site power x share of cluster used", "W"),
    "econ.run.power_cost": ("Electricity cost", "power x run time x price per watt-second", "USD"),
    "econ.gpu.hourly_amortized": (
        "Hardware cost per GPU per second", "(price - resale value) / years of use", "USD/s"),
    "econ.run.hw_cost": ("Hardware cost for this run", "hardware cost per second x run time", "USD"),
    "econ.run.total_cost": ("Total cost", "hardware + running costs (none) + electricity", "USD"),
    "econ.cost.per_token": ("Cost per token", "total cost / tokens", "USD/token"),
}

# Settings the calculator adds (graph pins). Each is (graph variable, label, formula, unit).
PIN_PLAIN: Dict[str, Tuple[str, str, str]] = {
    "gpu.peak_flops_power_limited": ("Speed achieved per GPU", "chip peak speed x MFU", "FLOP/s"),
    "thermal.dc.total_power": (
        "Total datacenter power",
        "PUE x GPUs x chip power rating x GPU power draw x (1 + extra server power)", "W"),
    "econ.gpu.capex": ("Cost to buy one GPU with its share of servers and network",
                       "GPU price x (1 + servers, network and building share)", "USD"),
    "econ.asset.useful_life": ("Hardware life in seconds", "years of use x 31,557,600", "s"),
    "econ.job.capex_rate": ("Hardware cost per second for all GPUs", "number of GPUs x hardware cost per GPU per second",
                            "USD/s"),
}

OUTPUTS: Dict[str, Dict[str, str]] = {
    "training_days": {"label": "Training time", "unit": "days",
                      "tooltip": "How long the run takes on the wall clock if every GPU works at the speed achieved."},
    "gpu_hours": {"label": "GPU-hours", "unit": "GPU-hours",
                  "tooltip": "GPUs times hours. Renting a GPU is priced per GPU-hour."},
    "energy_mwh": {"label": "Energy", "unit": "MWh",
                   "tooltip": "Electricity for the whole datacenter, including cooling. 1 MWh is what about 34 average U.S. homes use in a day."},
    "electricity_cost": {"label": "Electricity cost", "unit": "USD", "tooltip": "Energy times the electricity price."},
    "hardware_cost": {"label": "Hardware cost (amortized)", "unit": "USD",
                      "tooltip": "The share of the hardware's price used up during this run."},
    "total_cost": {"label": "Total cost", "unit": "USD",
                   "tooltip": "Electricity plus amortized hardware. Staff, buildings upkeep and failed runs are not included."},
    "cost_per_million_tokens": {"label": "Cost per million tokens", "unit": "USD",
                                "tooltip": "Total cost divided by the tokens trained, per million."},
}
OUTPUT_ORDER: Tuple[str, ...] = tuple(OUTPUTS)

# ---------------------------------------------------------------------------
# The model: graph resolution with symbolic inputs
# ---------------------------------------------------------------------------


@dataclass
class _Step:
    var: str  # graph variable (or calculator-layer id)
    label: str
    formula: str
    unit: str
    kind: str  # "graph equation" | "setting" | "unit conversion"
    equation: Optional[str]
    expr: sp.Expr


@dataclass
class CalculatorModel:
    """Closed-form output expressions, resolved from the graph, plus their chains."""

    symbols: Dict[str, sp.Symbol]
    outputs: Dict[str, sp.Expr]
    chains: Dict[str, List[_Step]]
    funcs: Dict[str, Callable[..., float]] = field(default_factory=dict)

    def inputs_of(self, output: str) -> List[str]:
        used = {s.name for s in self.outputs[output].free_symbols}
        return [i for i in INPUT_ORDER if i in used]


def _eq_inputs(equation: str) -> List[str]:
    eq = Registry.equations[equation]
    return [v.name for v in eq.variables_on_rhs()]


@lru_cache(maxsize=1)
def build_model() -> CalculatorModel:
    """Resolve the graph once, with every calculator input as a SymPy symbol."""
    S = {i: sp.Symbol(i, positive=True) for i in INPUT_ORDER}
    ssum = SECONDS_PER_YEAR

    # Per-GPU amortized rate from the graph's own equation.
    amort = resolve(
        "econ.gpu.hourly_amortized",
        assignments={
            "econ.gpu.capex": S["gpu_price"] * (1 + S["other_hardware_fraction"]),
            "econ.asset.residual_fraction": S["residual_fraction"],
            "econ.asset.useful_life": S["useful_life_years"] * ssum,
        },
    )
    if amort.missing:
        raise RuntimeError(f"amortization did not resolve: {sorted(amort.missing)}")

    pins: Dict[str, sp.Expr] = {
        "gpu.peak_flops_power_limited": S["peak_flops"] * S["mfu"],
        "thermal.dc.total_power": (
            S["pue"] * S["n_gpus"] * S["tdp_w"] * S["gpu_power_fraction"] * (1 + S["server_power_fraction"])
        ),
        "econ.job.capex_rate": S["n_gpus"] * amort.value,
    }
    assignments: Dict[str, Any] = {
        "arch.params_total_dense": S["params"],
        "training.total_tokens": S["tokens"],
        "par.n_gpus": S["n_gpus"],
        "arch.tokens_per_step": _TOKENS_PER_STEP,
        "training.recompute_overhead": 1,
        "training.optimizer_flop_multiplier": 1,
        "training.t_exposed_comm": 0,
        "training.t_mem_bound": 0,
        "training.overhead_fraction": 0,
        "training.cluster_availability": 1,
        "econ.job.share_of_cluster": 1,
        "econ.run.opex_misc_cost": 0,
        "econ.power.price_kwh_peak": S["electricity_price"],
        "econ.power.price_kwh_offpeak": S["electricity_price"],
        "econ.power.peak_energy_fraction": 0,
        **pins,
    }

    def run(target: str):
        res = resolve(target, assignments=assignments, variants=GRAPH_VARIANTS)
        if res.missing:
            raise RuntimeError(f"{target}: graph left {sorted(res.missing)} unresolved")
        return res

    wall = run("training.wallclock")
    power = run("econ.run.power_cost")
    hw = run("econ.run.hw_cost")
    total = run("econ.run.total_cost")
    per_token = run("econ.cost.per_token")

    n, T = S["n_gpus"], wall.value
    outputs: Dict[str, sp.Expr] = {
        "training_days": sp.simplify(T / 86400),
        # No graph variable for GPU-hours: GPUs x seconds / 3600.
        "gpu_hours": sp.simplify(n * T / 3600),
        # The graph's power cost is energy x price, so energy is that cost over the price.
        "energy_mwh": sp.simplify(power.value / S["electricity_price"] / 1000),
        "electricity_cost": sp.simplify(power.value),
        "hardware_cost": sp.simplify(hw.value),
        "total_cost": sp.simplify(total.value),
        "cost_per_million_tokens": sp.simplify(per_token.value * 1e6),
    }

    def graph_steps(res) -> List[_Step]:
        out: List[_Step] = []
        for t in res.trace:
            if t.variable not in PLAIN_STEPS:
                raise RuntimeError(f"no plain-English entry for graph step {t.variable}")
            label, formula, unit = PLAIN_STEPS[t.variable]
            out.append(_Step(t.variable, label, formula, unit, "graph equation", t.equation, res.values[t.variable]))
        return out

    def pin_steps(steps: List[_Step]) -> List[_Step]:
        """Settings (graph pins) that feed the given graph steps."""
        needed = set()
        for s in steps:
            if s.equation:
                needed.update(_eq_inputs(s.equation))
        out = []
        for var, expr in pins.items():
            if var in needed:
                label, formula, unit = PIN_PLAIN[var]
                out.append(_Step(var, label, formula, unit, "setting", None, expr))
        return out

    amort_step = _Step(
        "econ.gpu.hourly_amortized", *PLAIN_STEPS["econ.gpu.hourly_amortized"][:2],
        PLAIN_STEPS["econ.gpu.hourly_amortized"][2], "graph equation", "econ.eq.amortized", amort.value)
    capex_step = _Step(
        "econ.gpu.capex", *PIN_PLAIN["econ.gpu.capex"][:2], PIN_PLAIN["econ.gpu.capex"][2], "setting", None,
        S["gpu_price"] * (1 + S["other_hardware_fraction"]))
    life_step = _Step(
        "econ.asset.useful_life", *PIN_PLAIN["econ.asset.useful_life"][:2], PIN_PLAIN["econ.asset.useful_life"][2],
        "setting", None, S["useful_life_years"] * ssum)

    def chain_for(res, extra_before: Optional[List[_Step]] = None, extra_after: Optional[List[_Step]] = None):
        g = graph_steps(res)
        pre = pin_steps(g)
        # hardware chains also need the amortization sub-chain
        if any(s.var in ("econ.run.hw_cost", "econ.run.total_cost", "econ.cost.per_token") for s in g):
            pre = [capex_step, life_step, amort_step] + [p for p in pre if p.var != "econ.job.capex_rate"]
            pre.append(_Step("econ.job.capex_rate", *PIN_PLAIN["econ.job.capex_rate"][:2],
                             PIN_PLAIN["econ.job.capex_rate"][2], "setting", None, pins["econ.job.capex_rate"]))
        steps = (extra_before or []) + pre + g + (extra_after or [])
        seen, uniq = set(), []
        for s in steps:
            if s.var not in seen:
                seen.add(s.var)
                uniq.append(s)
        return uniq

    def conv(var, label, formula, unit, expr):
        return _Step(var, label, formula, unit, "unit conversion", None, expr)

    chains: Dict[str, List[_Step]] = {}
    chains["training_days"] = chain_for(wall, extra_after=[
        conv("training_days", "Training time", "run time in seconds / 86,400", "days", outputs["training_days"])])
    chains["gpu_hours"] = chain_for(wall, extra_after=[
        conv("gpu_hours", "GPU-hours", "number of GPUs x run time in seconds / 3,600", "GPU-hours",
             outputs["gpu_hours"])])
    pw = chain_for(power)
    pw_energy = [s for s in pw if s.var not in ("econ.power.price_kwh", "econ.power.price_ws", "econ.run.power_cost")]
    chains["energy_mwh"] = pw_energy + [conv(
        "energy_mwh", "Energy", "power x run time (the graph's electricity-cost equation with the price taken out), in MWh",
        "MWh", outputs["energy_mwh"])]
    chains["electricity_cost"] = pw
    chains["hardware_cost"] = chain_for(hw)
    chains["total_cost"] = chain_for(total)
    chains["cost_per_million_tokens"] = chain_for(per_token, extra_after=[
        conv("cost_per_million_tokens", "Cost per million tokens", "cost per token x 1,000,000", "USD",
             outputs["cost_per_million_tokens"])])

    order = [S[i] for i in INPUT_ORDER]
    funcs = {k: sp.lambdify(order, v, modules="math") for k, v in outputs.items()}
    return CalculatorModel(S, outputs, chains, funcs)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class Estimate:
    """Result of ``estimate()``. All money is USD, energy is MWh."""

    params: float
    tokens: float
    gpu: str
    n_gpus: float
    training_days: float
    gpu_hours: float
    energy_mwh: float
    electricity_cost: float
    hardware_cost: float
    total_cost: float
    cost_per_million_tokens: float
    inputs: Dict[str, float] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, float]:
        return {k: getattr(self, k) for k in OUTPUT_ORDER}

    def breakdown(self) -> List[Dict[str, Any]]:
        """For each output: the equation chain and the inputs it used, each input tagged."""
        return breakdown(self)


def resolve_inputs(
    params: float,
    tokens: float,
    gpu: "str | GPU" = "H100-SXM",
    n_gpus: float = 1024,
    mfu: Optional[float] = None,
    pue: Optional[float] = None,
    electricity_price: Optional[float] = None,
    gpu_price: Optional[float] = None,
    useful_life_years: Optional[float] = None,
    residual_fraction: Optional[float] = None,
    other_hardware_fraction: Optional[float] = None,
    gpu_power_fraction: Optional[float] = None,
    server_power_fraction: Optional[float] = None,
    peak_flops: Optional[float] = None,
    tdp_w: Optional[float] = None,
) -> Tuple[GPU, Dict[str, float], Dict[str, str]]:
    """Fill defaults, validate, and tag each input. Returns (gpu, values, tags)."""
    g = get_gpu(gpu)
    given = {
        "mfu": mfu, "pue": pue, "electricity_price": electricity_price, "gpu_price": gpu_price,
        "useful_life_years": useful_life_years, "residual_fraction": residual_fraction,
        "other_hardware_fraction": other_hardware_fraction, "gpu_power_fraction": gpu_power_fraction,
        "server_power_fraction": server_power_fraction, "peak_flops": peak_flops, "tdp_w": tdp_w,
    }
    values: Dict[str, float] = {"params": float(params), "tokens": float(tokens), "n_gpus": float(n_gpus)}
    tags: Dict[str, str] = {"params": TAG_USER, "tokens": TAG_USER, "n_gpus": TAG_USER}
    for iid in INPUT_ORDER:
        if iid in values:
            continue
        spec = INPUTS[iid]
        v = given[iid]
        if v is not None:
            values[iid], tags[iid] = float(v), TAG_USER
        elif iid == "peak_flops":
            values[iid], tags[iid] = g.peak_flops, TAG_SPEC
        elif iid == "tdp_w":
            values[iid], tags[iid] = g.tdp_w, TAG_SPEC
        elif iid == "gpu_price":
            values[iid], tags[iid] = g.price_usd, TAG_ASSUMPTION
        else:
            assert spec.default is not None
            values[iid], tags[iid] = spec.default, TAG_ASSUMPTION
    for iid, v in values.items():
        if not math.isfinite(v):
            raise ValueError(f"{iid} must be a finite number")
    if values["params"] <= 0 or values["tokens"] <= 0 or values["n_gpus"] <= 0:
        raise ValueError("params, tokens and n_gpus must be positive")
    if not 0 < values["mfu"] <= 1:
        raise ValueError("mfu must be between 0 and 1 (for example 0.40)")
    if values["pue"] < 1:
        raise ValueError("pue cannot be below 1")
    if values["useful_life_years"] <= 0:
        raise ValueError("useful_life_years must be positive")
    if not 0 <= values["residual_fraction"] < 1:
        raise ValueError("residual_fraction must be in [0, 1)")
    for iid in ("electricity_price", "gpu_price", "other_hardware_fraction",
                "gpu_power_fraction", "server_power_fraction"):
        if values[iid] < 0:
            raise ValueError(f"{iid} cannot be negative")
    return g, values, tags


def estimate(
    params: float,
    tokens: float,
    gpu: "str | GPU" = "H100-SXM",
    n_gpus: float = 1024,
    mfu: Optional[float] = None,
    pue: Optional[float] = None,
    electricity_price: Optional[float] = None,
    gpu_price: Optional[float] = None,
    useful_life_years: Optional[float] = None,
    **more: Optional[float],
) -> Estimate:
    """Estimate time, energy and cost of training a dense model.

    Parameters
    ----------
    params, tokens : model size (parameters) and training data (tokens).
    gpu : a key of ``GPUS`` ("H100-SXM", "A100-80GB-SXM") or a ``GPU``.
    n_gpus : GPUs used. Changes time, not cost.
    mfu : fraction of the chip's peak speed that training reaches. Default 0.40
        (assumption; real runs reach 30-55%).
    pue : datacenter overhead, total power / computer power. Default 1.2 (assumption).
    electricity_price : USD per kWh. Default 0.0813 (EIA 2024 U.S. industrial average).
    gpu_price : USD per GPU. Default depends on the GPU (assumption).
    useful_life_years : years the hardware is used before replacement. Default 4 (assumption).
    more : optional ``residual_fraction``, ``other_hardware_fraction``,
        ``gpu_power_fraction``, ``server_power_fraction``, ``peak_flops``, ``tdp_w``.

    Arguments left out are labelled "assumption" (or "hardware spec (cited)")
    in ``Estimate.breakdown()``; arguments you pass are "you entered".
    """
    g, values, tags = resolve_inputs(
        params, tokens, gpu, n_gpus, mfu, pue, electricity_price, gpu_price, useful_life_years, **more  # type: ignore[arg-type]
    )
    model = build_model()
    args = [values[i] for i in INPUT_ORDER]
    res = {k: float(f(*args)) for k, f in model.funcs.items()}
    return Estimate(
        params=values["params"], tokens=values["tokens"], gpu=g.key, n_gpus=values["n_gpus"],
        inputs=values, tags=tags, **res,
    )


def _fmt_value(v: float) -> str:
    return f"{v:.6g}"


def breakdown(est: Estimate) -> List[Dict[str, Any]]:
    """Per output: ``{"output", "label", "unit", "value", "chain", "inputs"}``.

    ``chain`` lists the steps from inputs to the output in order. Each step has
    the graph variable, a plain label, a plain formula, the registered
    equation name (or "setting" / "unit conversion"), and its value for this
    estimate. ``inputs`` lists every input that output uses with its value and
    tag ("you entered", "hardware spec (cited)" or "assumption").
    """
    model = build_model()
    args = [est.inputs[i] for i in INPUT_ORDER]
    order = [model.symbols[i] for i in INPUT_ORDER]
    out: List[Dict[str, Any]] = []
    for oid in OUTPUT_ORDER:
        chain = []
        for st in model.chains[oid]:
            val = float(sp.lambdify(order, st.expr, modules="math")(*args))
            chain.append({
                "variable": st.var, "label": st.label, "formula": st.formula, "unit": st.unit,
                "kind": st.kind, "equation": st.equation, "value": val,
            })
        inputs = []
        for iid in model.inputs_of(oid):
            spec = INPUTS[iid]
            inputs.append({
                "id": iid, "label": spec.label, "unit": spec.unit,
                "value": est.inputs[iid], "tag": est.tags[iid],
            })
        meta = OUTPUTS[oid]
        out.append({
            "output": oid, "label": meta["label"], "unit": meta["unit"],
            "value": getattr(est, oid), "chain": chain, "inputs": inputs,
        })
    return out


# ---------------------------------------------------------------------------
# Check against published training runs
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def load_published_runs() -> Dict[str, Any]:
    with open(DATA_DIR / "published_runs.json", encoding="utf-8") as fh:
        return json.load(fh)


def check_against_published() -> Dict[str, Any]:
    """Recompute how far the calculator is from 27 published runs' reported GPU-hours.

    Uses the default 40% MFU for every run and each run's own chip peak speed.
    Returns ``{"n", "median_abs_error", "p90_abs_error", "within_30_percent", "runs"}``;
    errors are |predicted / reported - 1|.
    """
    doc = load_published_runs()
    rows = []
    for r in doc["runs"]:
        hw = doc["hardware"][r["accelerator"]]
        chip = GPU(r["accelerator"], r["accelerator"], hw["peak_flops_dense_16bit"], hw["tdp_w"] or 0.0, 0.0, 0.0, "", "")
        est = estimate(r["params"], r["tokens"], gpu=chip, n_gpus=r["n_gpus"] or 1024, gpu_price=0.0)
        err = abs(est.gpu_hours / r["gpu_hours"] - 1.0)
        rows.append({
            "id": r["id"], "name": r["name"], "predicted_gpu_hours": est.gpu_hours,
            "reported_gpu_hours": r["gpu_hours"], "abs_error": err,
        })
    errs = sorted(x["abs_error"] for x in rows)
    p90 = errs[min(len(errs) - 1, int(math.ceil(0.9 * len(errs))) - 1)]
    return {
        "n": len(rows),
        "median_abs_error": statistics.median(errs),
        "p90_abs_error": p90,
        "within_30_percent": sum(e <= 0.30 for e in errs),
        "runs": rows,
    }


# ---------------------------------------------------------------------------
# Plain table (used by the CLI)
# ---------------------------------------------------------------------------


def format_table(est: Estimate) -> str:
    """A short plain-text table of the main results."""
    rows = [
        ("Training time", f"{est.training_days:,.1f} days"),
        ("GPU-hours", f"{est.gpu_hours:,.0f}"),
        ("Energy", f"{est.energy_mwh:,.1f} MWh"),
        ("Electricity cost", f"${est.electricity_cost:,.0f}"),
        ("Hardware cost (amortized)", f"${est.hardware_cost:,.0f}"),
        ("Total cost", f"${est.total_cost:,.0f}"),
        ("Cost per million tokens", f"${est.cost_per_million_tokens:,.4f}"),
    ]
    head = (
        f"{est.params / 1e9:,.3g} billion parameters, {est.tokens / 1e12:,.3g} trillion tokens, {est.n_gpus:,.0f} x {est.gpu}\n"
        f"(MFU {est.inputs['mfu']:.0%}, PUE {est.inputs['pue']:g}, "
        f"electricity ${est.inputs['electricity_price']:g}/kWh)\n"
    )
    w = max(len(a) for a, _ in rows)
    return head + "\n".join(f"  {a:<{w}}  {b}" for a, b in rows)


def format_breakdown(est: Estimate) -> str:
    """The breakdown tree as plain text."""
    lines: List[str] = []
    for item in breakdown(est):
        lines.append(f"{item['label']}: {item['value']:,.6g} {item['unit']}")
        for s in item["chain"]:
            how = s["equation"] or s["kind"]
            lines.append(f"  - {s['label']} = {_fmt_value(s['value'])} {s['unit']}   [{s['formula']}; {how}]")
        for i in item["inputs"]:
            lines.append(f"  * {i['label']}: {_fmt_value(i['value'])} {i['unit']}   ({i['tag']})")
        lines.append("")
    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Export for the web calculator
# ---------------------------------------------------------------------------


def expr_to_tree(e: sp.Expr) -> Any:
    """Turn a SymPy expression into a small JSON tree the browser evaluates.

    Nodes: a number, an input name (string), ["add", ...], ["mul", ...] or
    ["pow", base, exponent]. Anything else raises, so a new kind of graph
    expression cannot silently drop out of the web calculator.
    """
    if isinstance(e, sp.Symbol):
        return e.name
    if e.is_Number:
        return float(e)
    if isinstance(e, sp.Add):
        return ["add", *[expr_to_tree(a) for a in e.args]]
    if isinstance(e, sp.Mul):
        return ["mul", *[expr_to_tree(a) for a in e.args]]
    if isinstance(e, sp.Pow):
        return ["pow", expr_to_tree(e.args[0]), expr_to_tree(e.args[1])]
    raise TypeError(f"cannot export expression node {type(e).__name__}: {e}")


WEB_TEST_CASES: Tuple[Dict[str, Any], ...] = (
    {"name": "default 7B on 1024 H100", "args": {"params": 7e9, "tokens": 2e12, "gpu": "H100-SXM", "n_gpus": 1024}},
    {"name": "70B on 2048 A100, 50% MFU", "args": {
        "params": 70e9, "tokens": 1.4e12, "gpu": "A100-80GB-SXM", "n_gpus": 2048, "mfu": 0.5}},
    {"name": "1B on 8 H100, custom prices", "args": {
        "params": 1e9, "tokens": 3e11, "gpu": "H100-SXM", "n_gpus": 8, "pue": 1.5, "electricity_price": 0.2,
        "gpu_price": 25000, "useful_life_years": 3, "residual_fraction": 0.1, "other_hardware_fraction": 0.4,
        "gpu_power_fraction": 0.9, "server_power_fraction": 0.3}},
)


def web_model() -> Dict[str, Any]:
    """Everything the browser needs: inputs, GPU table, expression trees, chains, test cases."""
    model = build_model()
    check = check_against_published()
    pct = round(check["median_abs_error"] * 100)
    outputs: Dict[str, Any] = {}
    for oid in OUTPUT_ORDER:
        meta = OUTPUTS[oid]
        outputs[oid] = {
            "label": meta["label"], "unit": meta["unit"], "tooltip": meta["tooltip"],
            "expr": expr_to_tree(model.outputs[oid]),
            "inputs": model.inputs_of(oid),
            "chain": [
                {"variable": s.var, "label": s.label, "formula": s.formula, "unit": s.unit, "kind": s.kind,
                 "equation": s.equation, "expr": expr_to_tree(s.expr)}
                for s in model.chains[oid]
            ],
        }
    inputs = []
    for iid in INPUT_ORDER:
        sp_ = INPUTS[iid]
        inputs.append({
            "id": iid, "label": sp_.label, "unit": sp_.unit, "default": sp_.default, "tag": sp_.tag_default,
            "tooltip": sp_.tooltip, "advanced": sp_.advanced, "min": sp_.lo, "max": sp_.hi,
        })
    tests = []
    for case in WEB_TEST_CASES:
        est = estimate(**case["args"])
        tests.append({
            "name": case["name"],
            "inputs": {i: est.inputs[i] for i in INPUT_ORDER},
            "expected": est.as_dict(),
        })
    return {
        "version": 1,
        "note": "Generated by scripts/build_site_data.py from gpu_stack.calculator. Do not edit by hand.",
        "tags": {"user": TAG_USER, "spec": TAG_SPEC, "assumption": TAG_ASSUMPTION},
        "inputs": inputs,
        "gpus": {k: {"label": g.label, "peak_flops": g.peak_flops, "tdp_w": g.tdp_w, "memory_gb": g.memory_gb,
                     "price_usd": g.price_usd, "price_note": g.price_note, "cite": g.cite}
                 for k, g in GPUS.items()},
        "outputs": outputs,
        "output_order": list(OUTPUT_ORDER),
        "neutral_settings": NEUTRAL_SETTINGS,
        "not_included": "Staff, building upkeep, water, network and storage costs, failed or repeated runs, "
                        "and the research that came before the final run.",
        "accuracy": {
            "n": check["n"], "median_abs_error": check["median_abs_error"],
            "text": (f"Checked against {check['n']} published training runs: typically within about {pct}% "
                     "(same as the simple rule of thumb)."),
        },
        "tests": tests,
    }
