"""
gpu_stack.drivers
=================

What drives the cost of training, measured on the equation graph.

The scenario is a 7B-parameter model trained on 2 trillion tokens on 1,024
H100 GPUs, closed with the repo's sourced DGX H100 power and cost presets
(hardware facts) plus their labelled assumptions (prices, life, utilization).
The graph is resolved once into a closed-form expression for cost per token
with every input a symbol. Then a variance-based sensitivity analysis asks:
if each input is uncertain by a factor of two either way, which ones explain
the spread in the answer?

Method (ported and trimmed from the earlier graph-sensitivity study):

* every input is varied log-uniformly between half and double its nominal
  value; fractions are capped at 1, multipliers that must be at least 1 vary
  between 1x and 2x, and inputs that are exactly zero or on/off switches are
  held fixed;
* the output is the natural log of cost per token, so effects are relative;
* the Sobol total-order index (Jansen estimator) says how much of the variance
  of that log cost an input is involved in, alone or through interactions;
* indices are reported as shares of their sum.

This rerun uses the corrected presets: the H100 speed is the dense BF16
datasheet value (989.4 teraFLOPS), not the FP32 CUDA-core figure that the
first run's presets carried.

Needs numpy (and scipy for the Sobol sequence; falls back to plain random
sampling without it).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import sympy as sp

import gpu_stack  # noqa: F401  (registers every variable and equation)
from gpu_stack.core.equation import RelationRole
from gpu_stack.core.registry import Registry
from gpu_stack.core.resolver import resolve
from gpu_stack.core.resolver_graph import _value_dependencies
from gpu_stack.core.resolver_models import AmbiguousVariant
from gpu_stack.core.resolver_selection import _select_equation

TARGET = "econ.cost.per_token"

SCENARIO = {
    "params": 6.74e9,
    "tokens": 2e12,
    "n_gpus": 1024,
    "gpus_per_node": 8,
    "description": "7B-parameter model, 2 trillion tokens, 1,024 H100 GPUs",
}

# Synthetic inputs that split a pinned graph value into two things a reader knows.
CHIP_PEAK = "chip_peak_flops"
MFU = "mfu"
PUE = "pue"
EXTRA = {CHIP_PEAK: 989.4e12, MFU: 0.40, PUE: 1.2}

# Inputs the closure scales from one node to the whole cluster (per-node preset values).
_SCALE_WITH_NODES = (
    "thermal.facility.floor_area",
    "thermal.facility.power_design_capacity",
    "thermal.facility.cooling_design_capacity",
    "econ.cluster.spine_network_capex",
    "econ.cluster.storage_capex",
    "econ.network.egress_bytes_per_s",
)
# Staff: the preset is 0.25 FTE for one server. Scaling that to 128 servers would mean 32 people, so this
# scenario assumes 4 full-time staff at the preset's $120,000 a year fully loaded.
STAFF_FTE = 4.0
STAFF_USD_PER_FTE_YEAR = 120_000.0
_SWITCHES = {"arch.output.untied_factor"}
# Cluster size cancels out of cost per token (the cluster is priced and powered per GPU), and the building
# inputs are scaled for 1,024 GPUs, so these are held at their defaults rather than sampled.
_HELD = {
    "cluster.node.n_gpus": "cluster size cancels out",
    "cluster.rack.n_nodes": "cluster size cancels out",
    "cluster.site.n_racks": "cluster size cancels out",
}
# Narrower ranges where a factor of two either way is not physically possible.
_NARROW = {
    "training.recompute_overhead": (1.0, 1.35),  # full activation re-computation adds about a third
    "training.optimizer_flop_multiplier": (1.0, 1.10),
    "training.cluster_availability": (0.85, 1.0),
}
_INT_INPUTS = {"cluster.node.n_gpus", "cluster.rack.n_nodes", "cluster.site.n_racks", "cluster.node.n_cpus",
               "cluster.node.nic.count", "cluster.node.nic.ports_per_nic", "cluster.node.local_ssd.count"}
# par.n_gpus is a pinned value equal to GPUs per node x nodes per rack x racks.
_TIES = {"par.n_gpus": ("cluster.node.n_gpus", "cluster.rack.n_nodes", "cluster.site.n_racks")}
FACTOR = 2.0

# ---------------------------------------------------------------------------
# Plain-English labels
# ---------------------------------------------------------------------------

LABELS: Dict[str, str] = {
    "arch.params_total_dense": "Model size (number of parameters)",
    "training.total_tokens": "How much data you train on",
    CHIP_PEAK: "Chip speed on paper (which GPU you buy)",
    MFU: "GPU speed actually achieved (MFU)",
    PUE: "Datacenter overhead for cooling and power (PUE)",
    "econ.gpu.capex": "Price of one GPU",
    "econ.asset.useful_life": "How long the hardware is used before replacement",
    "econ.asset.residual_fraction": "Resale value of the hardware at the end",
    "econ.cluster.utilization": "Share of the time the cluster is kept busy",
    "econ.power.price_kwh_offpeak": "Electricity price",
    "econ.power.price_kwh_peak": "Peak-hour electricity price",
    "gpu.power.total": "Power one GPU draws",
    "econ.node.chassis_capex": "Server chassis price",
    "econ.node.cpu_capex": "Server CPU price",
    "econ.node.dram_capex": "Server memory price",
    "econ.node.nic_capex": "Network card price",
    "econ.node.storage_capex": "Server storage price",
    "econ.rack.switch_capex": "Rack network switch price",
    "econ.rack.power_distribution_capex": "Rack power distribution price",
    "econ.cluster.spine_network_capex": "Datacenter-wide network price",
    "econ.cluster.storage_capex": "Shared storage price",
    "econ.facility.building_shell_unit_cost": "Building construction cost",
    "econ.facility.power_infra_unit_cost": "Power equipment cost per watt",
    "econ.facility.cooling_infra_unit_cost": "Cooling equipment cost per watt",
    "thermal.facility.floor_area": "Floor area of the building",
    "thermal.facility.power_design_capacity": "Size of the building's power supply",
    "thermal.facility.cooling_design_capacity": "Size of the building's cooling plant",
    "econ.maintenance.fraction_per_year": "Yearly maintenance as a share of hardware price",
    "econ.staff.cost_rate": "Staff cost",
    "econ.network.transit_price_per_gb": "Price of sending data out of the datacenter",
    "econ.network.egress_bytes_per_s": "Data sent out of the datacenter",
    "econ.power.capacity_charge_kw_month": "Utility charge for reserving power capacity",
    "econ.water.price_per_liter": "Water price",
    "econ.carbon.intensity_kg_per_kwh": "Carbon emitted per unit of electricity",
    "econ.carbon.price_per_tonne": "Price of carbon",
    "thermal.water.latent_heat": "Heat carried off by evaporating water",
    "thermal.water.density": "Density of water",
    "thermal.water.cycles_of_concentration": "How often cooling water is reused",
    "thermal.water.drift_fraction": "Water lost as droplets from cooling towers",
    "cluster.node.cpu.power_per_cpu": "Server CPU power",
    "cluster.node.n_cpus": "CPUs per server",
    "cluster.node.nic.power_per_nic": "Network card power",
    "cluster.node.nic.count": "Network cards per server",
    "cluster.node.nic.ports_per_nic": "Ports per network card",
    "cluster.node.nic.power_per_port": "Extra power per network port",
    "cluster.node.local_ssd.count": "Drives per server",
    "cluster.node.local_ssd.power_per_drive": "Power per drive",
    "cluster.node.ram": "Server memory size",
    "cluster.node.ram.power_per_byte": "Server memory power",
    "cluster.node.misc.fixed_power": "Fans and motherboard power per server",
    "cluster.node.misc.power_per_gpu": "Extra power per GPU slot",
    "cluster.node.n_gpus": "GPUs per server",
    "cluster.rack.n_nodes": "Servers per rack",
    "cluster.site.n_racks": "Number of racks",
    "par.n_gpus": "Number of GPUs",
    "arch.tokens_per_step": "Tokens per training step",
    "training.recompute_overhead": "Extra work from re-computing results to save memory",
    "training.optimizer_flop_multiplier": "Extra work done by the optimizer",
    "training.cluster_availability": "Share of time the cluster is up",
    "training.t_exposed_comm": "Time lost waiting for the network",
    "training.t_mem_bound": "Time lost waiting for memory",
    "training.overhead_fraction": "Idle time added to each step",
    "thermal.facility.heat_reuse_fraction": "Share of waste heat reused",
    "econ.power.peak_energy_fraction": "Share of energy bought at peak price",
}

# Plain "what is this" explanations for the headline drivers.
EXPLAIN: Dict[str, str] = {
    "arch.params_total_dense": "Bigger models need proportionally more arithmetic for every token.",
    MFU: "The share of the chip's paper speed that real training reaches. Lower means more GPU time per token.",
    CHIP_PEAK: "A faster chip does the same arithmetic in less time, so each token uses less rented or owned time.",
    "econ.gpu.capex": "Most of the bill is the hardware's price spread over the hours it runs.",
    "econ.asset.useful_life": "The same hardware price spread over more years makes every hour cheaper.",
    "econ.cluster.utilization": "Idle hardware still has to be paid for, so busy time is more expensive.",
    "econ.power.price_kwh_offpeak": "Electricity is a small part of the bill, so even a doubling matters little.",
    PUE: "Cooling and power losses add to the electricity bill, which is already small.",
}

FAMOUS_ZERO = [
    ("physical.", "How the chip is made (lithography, transistor physics)",
     "Once you know which chip you have, how it was printed no longer changes the bill. Its speed and power are "
     "on the datasheet, and the cost formula only uses those."),
]


# ---------------------------------------------------------------------------
# Scenario and closed-form model
# ---------------------------------------------------------------------------


def scenario_assignments() -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Numeric assignments and variant selections for the default scenario (all in graph names)."""
    from gpu_stack.presets import scenarios as S

    base = S.pythia_70m_dgx_h100_us_2024_industrial_full_tco_assumption
    a: Dict[str, Any] = {
        k: v for k, v in base.assignments.items() if not k.startswith("arch.") and k != "training.total_tokens"
    }
    nodes_per_rack = 1
    n_racks = SCENARIO["n_gpus"] // (SCENARIO["gpus_per_node"] * nodes_per_rack)
    scale = n_racks  # the preset is one node; this scenario is n_racks of them
    for k in _SCALE_WITH_NODES:
        a[k] = a[k] * scale
    a.update({
        "arch.params_total_dense": SCENARIO["params"],
        "arch.tokens_per_step": 4_194_304,
        "training.total_tokens": SCENARIO["tokens"],
        "par.n_gpus": SCENARIO["n_gpus"],
        "econ.staff.cost_rate": STAFF_FTE * STAFF_USD_PER_FTE_YEAR / 31_557_600.0,
        "cluster.site.n_racks": n_racks,
        "cluster.rack.n_nodes": nodes_per_rack,
    })
    # The preset pins these two to constants; the model re-derives them from named inputs.
    a.pop("gpu.peak_flops_power_limited", None)
    a.pop("thermal.dc.total_power", None)
    return a, dict(base.variants)


@dataclass
class Model:
    names: List[str]
    nominal: Any  # numpy array
    lam: Any
    nominal_value: float
    n_ops: int
    in_formula_registry: List[str] = field(default_factory=list)


def build_model() -> Model:
    import numpy as np

    a, variants = scenario_assignments()
    syms: Dict[str, sp.Symbol] = {k: Registry.variables[k].symbol for k in a}
    for k in EXTRA:
        syms[k] = sp.Symbol(k, positive=True)
    # IT power from the graph's node power bill of materials, then times PUE.
    pre = {k: syms[k] for k in a}
    it = resolve("cluster.site.power_it", assignments={**pre, "par.n_gpus": syms["par.n_gpus"]}, variants=variants)
    if it.missing:
        raise RuntimeError(f"IT power did not resolve: {sorted(it.missing)}")
    sym_assign: Dict[str, Any] = dict(pre)
    sym_assign["gpu.peak_flops_power_limited"] = syms[CHIP_PEAK] * syms[MFU]
    sym_assign["thermal.dc.total_power"] = syms[PUE] * it.value
    res = resolve(TARGET, assignments=sym_assign, variants=variants)
    if res.missing:
        raise RuntimeError(f"cost per token did not resolve: {sorted(res.missing)}")
    expr = res.value
    free = sorted(expr.free_symbols, key=str)
    by_symbol = {v: k for k, v in syms.items()}
    names = [by_symbol[s] for s in free]
    nominal_map = {**{k: float(v) for k, v in a.items()}, **EXTRA}
    nominal = np.array([nominal_map[n] for n in names])
    lam = sp.lambdify(free, expr, modules="numpy", cse=True)
    nominal_value = float(lam(*nominal))
    # Cross-check the closed form against the numeric resolver.
    num_assign = dict(a)
    num_assign["gpu.peak_flops_power_limited"] = EXTRA[CHIP_PEAK] * EXTRA[MFU]
    it_num = resolve("cluster.site.power_it", assignments=a, variants=variants)
    num_assign["thermal.dc.total_power"] = EXTRA[PUE] * float(it_num.value)
    ref = float(resolve(TARGET, assignments=num_assign, variants=variants).value)
    if abs(ref - nominal_value) > 1e-9 * abs(ref):
        raise RuntimeError(f"closed form {nominal_value} != resolver {ref}")
    return Model(names, nominal, lam, nominal_value, int(sp.count_ops(expr)),
                 [n for n in names if n in Registry.variables])


# ---------------------------------------------------------------------------
# Sampling ranges
# ---------------------------------------------------------------------------


@dataclass
class Spec:
    names: List[str]
    lo: Any
    hi: Any
    is_log: Any
    is_int: Any
    held: Dict[str, str]
    tied: Dict[str, Tuple[str, ...]]


def make_spec(model: Model) -> Spec:
    import numpy as np

    nominal = dict(zip(model.names, model.nominal))
    tied = {f: d for f, d in _TIES.items() if f in nominal and all(x in nominal for x in d)}
    for f, d in tied.items():
        prod = 1.0
        for x in d:
            prod *= nominal[x]
        if abs(prod - nominal[f]) > 1e-9:
            raise RuntimeError(f"{f} does not equal the product of {d}")
    input_names = [n for n in model.names if n not in tied]
    for d in tied.values():
        for x in d:
            if x not in input_names:
                input_names.append(x)
    names: List[str] = []
    lo: List[float] = []
    hi: List[float] = []
    lg: List[bool] = []
    held: Dict[str, str] = {}
    f = FACTOR

    def add(name: str, a: float, b: float) -> None:
        names.append(name)
        lo.append(a)
        hi.append(b)
        lg.append(True)

    for n in input_names:
        x0 = nominal[n]
        var = Registry.variables.get(n)
        units = var.units if var is not None else "dimensionless"
        if n in _SWITCHES:
            held[n] = "switch"
        elif n in _HELD:
            held[n] = _HELD[n]
        elif x0 == 0.0:
            held[n] = "zero in this scenario"
        elif n in _NARROW:
            add(n, _NARROW[n][0], _NARROW[n][1])
        elif (units == "dimensionless" and x0 <= 1.0) or n == "econ.cluster.utilization":
            top = min(x0 * f, 1.0)
            if top <= x0 / f:
                held[n] = "fraction range empty"
            else:
                add(n, x0 / f, top)
        else:
            add(n, x0 / f, x0 * f)
    return Spec(names, np.array(lo), np.array(hi), np.array(lg, dtype=bool),
                np.array([n in _INT_INPUTS for n in names], dtype=bool), held, tied)


class Evaluator:
    """Unit cube (n, k) to cost per token (n,)."""

    def __init__(self, model: Model, spec: Spec):
        self.model, self.spec = model, spec
        self.k = len(spec.names)
        self.index = {n: i for i, n in enumerate(spec.names)}
        self.nominal = dict(zip(model.names, model.nominal))

    def __call__(self, U):
        import numpy as np

        s = self.spec
        X = s.lo * (s.hi / s.lo) ** U  # log-uniform on [lo, hi]
        it = s.is_int
        if it.any():
            X[:, it] = np.maximum(1.0, np.floor(X[:, it] + 0.5))
        n = U.shape[0]
        cols = []
        for j, name in enumerate(self.model.names):
            if name in self.index:
                cols.append(X[:, self.index[name]])
            elif name in s.tied:
                prod = np.ones(n)
                for d in s.tied[name]:
                    prod = prod * (X[:, self.index[d]] if d in self.index else self.nominal[d])
                cols.append(prod)
            else:
                cols.append(np.full(n, self.model.nominal[j]))
        with np.errstate(all="ignore"):
            out = self.model.lam(*cols)
        return np.asarray(out, dtype=float)


# ---------------------------------------------------------------------------
# Sobol total-order indices (Jansen estimator) on log cost
# ---------------------------------------------------------------------------


def sobol_total(ev: Evaluator, n_pow: int = 14, seed: int = 20261001) -> Dict[str, Any]:
    import numpy as np

    k = ev.k
    try:
        from scipy.stats import qmc

        M = qmc.Sobol(d=2 * k, scramble=True, seed=seed).random_base2(n_pow)
    except ImportError:  # pragma: no cover
        M = np.random.default_rng(seed).random((2 ** n_pow, 2 * k))
    A, B = M[:, :k], M[:, k:]
    yA, yB = np.log(ev(A)), np.log(ev(B))
    ok = np.isfinite(yA) & np.isfinite(yB)
    yAB = np.empty((k, A.shape[0]))
    for i in range(k):
        ABi = A.copy()
        ABi[:, i] = B[:, i]
        yAB[i] = np.log(ev(ABi))
        ok &= np.isfinite(yAB[i])
    n_ok = int(ok.sum())
    if n_ok < 0.99 * len(ok):
        raise RuntimeError("too many invalid sample rows")
    yA, yB, yAB = yA[ok], yB[ok], yAB[:, ok]
    mu = np.mean(np.concatenate([yA, yB]))
    var = np.var(np.concatenate([yA, yB]) - mu, ddof=1)
    st = 0.5 * np.mean((yA[None, :] - yAB) ** 2, axis=1) / var
    s1 = np.mean(yB[None, :] * (yAB - yA[None, :]), axis=1) / var
    # Replicate with half the rows to show how stable the numbers are.
    h = len(yA) // 2
    st_half = 0.5 * np.mean((yA[None, :h] - yAB[:, :h]) ** 2, axis=1) / np.var(
        np.concatenate([yA[:h], yB[:h]]) - mu, ddof=1)
    return {"ST": st, "S1": s1, "ST_half": st_half, "n_rows": n_ok, "variance": float(var)}


# ---------------------------------------------------------------------------
# Structure: what is upstream but does not appear in the formula
# ---------------------------------------------------------------------------


def _ancestors(name: str, variants: Optional[Dict[str, str]]) -> set:
    seen: set = set()
    stack = [Registry.variables[name]]
    while stack:
        v = stack.pop()
        if v.name in seen:
            continue
        seen.add(v.name)
        if variants is None:
            eqs = [e for e in v.defining_equations if e.role != RelationRole.CONSTRAINT]
        else:
            try:
                e = _select_equation(v, variants)
                eqs = [e] if e is not None else []
            except AmbiguousVariant:
                eqs = [e for e in v.defining_equations if e.role != RelationRole.CONSTRAINT]
        for e in eqs:
            stack.extend(_value_dependencies(e))
    return seen


def structure_counts(model: Model, prefix: str) -> Dict[str, int]:
    roots = {r.name for r in Registry.roots()}
    upstream = {n for n in _ancestors(TARGET, None) & roots if n.startswith(prefix)}
    total = {n for n in roots if n.startswith(prefix)}
    in_formula = {n for n in model.in_formula_registry if n.startswith(prefix)}
    return {"in_graph": len(total), "upstream_of_cost": len(upstream), "in_cost_formula": len(in_formula)}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


TINY_WHY = {
    "econ.power.price_kwh_offpeak": "Electricity is a small slice of the bill, so even a doubled price barely moves it.",
    PUE: "Cooling losses add to a bill that is already mostly hardware.",
    "gpu.power.total": "How hungry the chip is matters little because power is a small slice of the cost.",
    "econ.water.price_per_liter": "Cooling water is a tiny cost next to the chips.",
    "econ.network.transit_price_per_gb": "Sending data out of the datacenter is a rounding error for a training run.",
    "econ.power.capacity_charge_kw_month": "The utility's reservation charge is small next to the hardware.",
    "econ.carbon.intensity_kg_per_kwh": "Carbon is not priced in this scenario, so it does not change the bill.",
}


def cluster_size_check(model: Model) -> float:
    """Cost per token with twice the GPUs (and building inputs scaled to match) over the default."""
    import numpy as np

    names = list(model.names)
    x = np.array(model.nominal, dtype=float)
    y = x.copy()
    for i, n in enumerate(names):
        if n == "cluster.site.n_racks" or n == "par.n_gpus" or n in _SCALE_WITH_NODES:
            y[i] *= 2.0
    return float(model.lam(*y) / model.lam(*x))


def label_for(name: str) -> str:
    if name in LABELS:
        return LABELS[name]
    var = Registry.variables.get(name)
    if var is not None and var.description:
        return var.description.split(".")[0]
    return name


def compute_drivers(n_pow: int = 14, seed: int = 20261001, top: int = 8) -> Dict[str, Any]:
    """Run the analysis and return the dictionary written to docs/data/drivers.json."""
    import numpy as np

    model = build_model()
    spec = make_spec(model)
    ev = Evaluator(model, spec)
    res = sobol_total(ev, n_pow, seed)
    st = np.clip(res["ST"], 0.0, None)
    total = float(st.sum())
    share = st / total
    order = np.argsort(-share)
    rows = []
    for i in order:
        name = spec.names[i]
        rows.append({
            "variable": name, "label": label_for(name), "share": float(share[i]), "total_order_index": float(res["ST"][i]),
            "explain": EXPLAIN.get(name, ""),
            "range": [float(spec.lo[i]), float(spec.hi[i])], "nominal": float(ev.nominal.get(name, math_nan())),
        })
    negligible = [r for r in rows if r["share"] < 0.005]
    structure = {pfx: structure_counts(model, pfx) for pfx, _, _ in FAMOUS_ZERO}
    zero_effect = []
    for pfx, label, why in FAMOUS_ZERO:
        c = structure[pfx]
        zero_effect.append({
            "label": label, "why": why, "share": 0.0,
            "evidence": (f"{c['upstream_of_cost']} of the graph's {c['in_graph']} chip-physics inputs sit upstream of "
                         f"the cost; {c['in_cost_formula']} appear in the cost formula."),
        })
    # Things that are in the formula but barely matter (share under 0.5%).
    by_var = {r["variable"]: r for r in rows}
    for n, why in TINY_WHY.items():
        r = by_var.get(n)
        if r is not None and r["share"] < 0.005:
            zero_effect.append({"label": r["label"], "why": why, "share": r["share"],
                                "evidence": f"{r['share']:.2%} of the variation in cost per token."})
    ratio = cluster_size_check(model)
    zero_effect.append({
        "label": "How many GPUs you use",
        "why": "More GPUs finish sooner but the bill per token stays about the same, because each GPU is bought "
               "and powered per hour of work.",
        "share": 0.0,
        "evidence": f"Doubling the cluster changes cost per token by {ratio - 1:+.1%}.",
    })
    return {
        "scenario": SCENARIO["description"],
        "target": "cost per token (natural log)",
        "method": ("Every input is varied between half and double its default (fractions are capped at 1). "
                   "The share is how much of the spread in cost per token an input accounts for, "
                   "counting its interactions, as a share of the total. The ranges are equal by design, so the "
                   "ranking mostly reflects how directly each input enters the cost."),
        "sobol_rows": res["n_rows"], "n_inputs_varied": len(spec.names), "n_inputs_in_formula": len(model.names),
        "inputs_held_fixed": sorted(spec.held),
        "nominal_cost_per_token_usd": model.nominal_value,
        "nominal_cost_per_million_tokens_usd": model.nominal_value * 1e6,
        "sum_of_total_order_indices": total,
        "stability_max_change_half_vs_full": float(np.max(np.abs(res["ST_half"] - res["ST"]))),
        "top": rows[:top],
        "all": rows,
        "inputs_below_half_percent": len(negligible),
        "zero_effect": zero_effect,
        "note": ("This rerun uses the corrected presets: the H100 speed is the dense BF16 datasheet value, "
                 "not the FP32 figure the first run carried."),
    }


def math_nan() -> float:
    return math.nan
