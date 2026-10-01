"""Prediction arms for study V002. Library only; run.py drives it.

Nothing here reads reported GPU-hours, reported energy, reported power or
reported PUE, except where an arm is explicitly an "oracle" arm. The frozen
constants below are the single source of truth; protocol.md quotes them.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import gpu_stack  # noqa: F401  (registers every variable and equation)
from gpu_stack.core.resolver import ResolverError, resolve
from gpu_stack.uncertainty import (
    UncertainAssignment,
    lognormal,
    propagate_uncertainty,
    uniform,
)

# ---------------------------------------------------------------------------
# Frozen constants (see protocol.md section "Prior choices" for the reasons)
# ---------------------------------------------------------------------------
FROZEN: Dict[str, Any] = {
    "mfu_fixed_baseline": 0.40,              # baseline (a): task-specified fixed MFU
    "overhead_fraction_median": 1.5,         # graph prior: step time = compute time * (1 + f); MFU = 1/(1+f) = 0.40 at f=1.5
    "overhead_fraction_sigma_log": 0.55,     # lognormal sigma of f; 5-95% MFU about 0.21-0.62
    "gpu_load_fraction_u": [0.5, 1.0],       # uniform; GPU draw as a fraction of TDP under training load
    "node_nongpu_fraction_kappa": [0.10, 0.60],  # uniform; non-GPU node power as a fraction of the node's GPU TDP total
    "pue_baseline": 1.20,                    # baselines (c): fixed PUE
    "pue_prior": [1.05, 1.35],               # uniform; graph prior
    "mc_samples": 20000,
    "mc_seed": 20261001,
    "nominal_gpu_count": 1024,               # used when a record reports no count; cancels in the time arms
    "nominal_tokens_per_step": 4194304,      # cancels in the time arms
    "gpus_per_node": 8,
}

# Decision thresholds (reasons in protocol.md "Decision criteria")
CRITERIA: Dict[str, Any] = {
    "mdape_pass": 0.33,                # 0.40/0.30 - 1: MFU anywhere in the 0.30-0.50 band counts as right
    "oracle_mdape_pass": 0.15,         # ~10% non-productive time (Llama 3 paper p13) + ~5% rounding
    "equivalence_margin": 0.02,        # |delta MdAPE| below this = "same as baseline"
    "sharpness_max_ratio": 4.0,        # median p95/p5 of the interval must not exceed this
    "interval_nominal": 0.90,
    "binom_alpha": 0.05,               # coverage must be >= the 5th percentile of Binomial(n, 0.90)
    "s2_mdape_pass": 0.02,             # graph parameter count within 2% of published (median)
    "energy_min_clusters": 6,          # fewer independent clusters than this => energy verdict is 'not tested'
    "bootstrap_reps": 10000,
    "bootstrap_seed": 7,
    "pair_ratio_range": [1.2, 3.0],
}

# Graph variable names used (all are registry names)
V = {
    "params": "arch.params_total_dense",
    "tokens_step": "arch.tokens_per_step",
    "tokens_total": "training.total_tokens",
    "n_gpus": "par.n_gpus",
    "peak": "gpu.peak_flops",
    "peak_pl": "gpu.peak_flops_power_limited",
    "recompute": "training.recompute_overhead",
    "optflop": "training.optimizer_flop_multiplier",
    "t_comm": "training.t_exposed_comm",
    "t_mem": "training.t_mem_bound",
    "overhead": "training.overhead_fraction",
    "avail": "training.cluster_availability",
    "wallclock": "training.wallclock",
}
DENSE_VARIANTS = {"training.flops_per_step": "dense", "training.scaling_params": "dense"}


class PredictionFailure(RuntimeError):
    pass


def _count(rec: dict) -> int:
    ac = rec.get("accel_count")
    if ac and ac.get("value"):
        return int(ac["value"])
    return int(FROZEN["nominal_gpu_count"])


def _peak(ds: dict, rec: dict) -> float:
    return float(ds["hardware_specs"][rec["accelerator"]]["peak_flops_dense_16bit"])


def _tdp(ds: dict, rec: dict) -> Optional[float]:
    return ds["hardware_specs"][rec["accelerator"]]["tdp_w"]


def tokens_for_time(rec: dict) -> float:
    """Tokens that the target time refers to (one step for throughput benchmarks)."""
    if rec.get("kind") == "throughput_benchmark":
        return float(rec["time"]["tokens_per_step"]["value"])
    return float(rec["tokens"]["value"])


def true_accel_seconds_per_token(rec: dict) -> float:
    t = rec["time"]
    if "step_time_s" in t:
        return _count(rec) * t["step_time_s"]["value"] / t["tokens_per_step"]["value"]
    return t["accel_hours"]["value"] * 3600.0 / rec["tokens"]["value"]


# ---------------------------------------------------------------------------
# Baseline (a): 6 N D / (peak * fixed MFU)
# ---------------------------------------------------------------------------
def baseline_a(ds: dict, rec: dict, mfu: Optional[float] = None) -> float:
    mfu = FROZEN["mfu_fixed_baseline"] if mfu is None else mfu
    return 6.0 * rec["params"]["value"] / (_peak(ds, rec) * mfu)  # accelerator-seconds per token


# ---------------------------------------------------------------------------
# Graph time arms
# ---------------------------------------------------------------------------
def _time_assignments(ds: dict, rec: dict, overhead: float) -> Dict[str, float]:
    n = _count(rec)
    peak = _peak(ds, rec)
    return {
        V["params"]: float(rec["params"]["value"]),
        V["tokens_step"]: float(FROZEN["nominal_tokens_per_step"]),
        V["tokens_total"]: tokens_for_time(rec),
        V["n_gpus"]: float(n),
        V["peak"]: peak,
        V["peak_pl"]: peak,
        V["recompute"]: 1.0,
        V["optflop"]: 1.0,
        V["t_comm"]: 0.0,
        V["t_mem"]: 0.0,
        V["overhead"]: float(overhead),
        V["avail"]: 1.0,
    }


def _resolve_value(target: str, assignments: Dict[str, float]) -> Dict[str, Any]:
    try:
        res = resolve(target, assignments=assignments, variants=DENSE_VARIANTS)
    except ResolverError as exc:
        raise PredictionFailure(f"{target}: {exc}") from exc
    if res.missing:
        raise PredictionFailure(f"{target}: unresolved {sorted(res.missing)}")
    value = float(res.value)
    if not math.isfinite(value):
        raise PredictionFailure(f"{target}: non-finite {value}")
    return {
        "value": value,
        "violated_constraints": len(res.violated_constraints),
        "violated_validity": sum(1 for c in res.approximation_validity if c.satisfied is False),
        "trace_steps": len(res.trace),
    }


def graph_time_point(ds: dict, rec: dict, overhead: float) -> Dict[str, Any]:
    """Deterministic graph evaluation. Returns accelerator-seconds per token."""
    a = _time_assignments(ds, rec, overhead)
    out = _resolve_value(V["wallclock"], a)
    out["accel_s_per_token"] = out["value"] * _count(rec) / tokens_for_time(rec)
    return out


def graph_time_G0(ds: dict, rec: dict) -> Dict[str, Any]:
    """Graph as shipped: neutral closure, overhead_fraction = 0 (MFU = 1)."""
    return graph_time_point(ds, rec, 0.0)


def graph_time_G2(ds: dict, rec: dict) -> Dict[str, Any]:
    """Oracle MFU arm: overhead_fraction = 1/MFU_reported - 1."""
    mfu = rec["mfu_reported"]["value"]
    return graph_time_point(ds, rec, 1.0 / mfu - 1.0)


def graph_time_G1(ds: dict, rec: dict) -> Dict[str, Any]:
    """Graph + frozen MFU prior; interval from gpu_stack.uncertainty."""
    base = _time_assignments(ds, rec, FROZEN["overhead_fraction_median"])
    ua = UncertainAssignment(
        V["overhead"],
        lognormal(math.log(FROZEN["overhead_fraction_median"]), FROZEN["overhead_fraction_sigma_log"]),
    )
    res = _propagate(base, V["wallclock"], [ua])
    t = res.targets[0]
    if t.p50 is None or t.failure_count > 0.01 * t.sample_count:
        raise PredictionFailure(f"uncertainty propagation failed: failures={t.failure_count}")
    k = _count(rec) / tokens_for_time(rec)
    return {"accel_s_per_token": t.p50 * k, "p5": t.p5 * k, "p95": t.p95 * k, "failures": t.failure_count}


def baseline_a_interval(ds: dict, rec: dict) -> Dict[str, float]:
    """Closed-form interval from the same prior, to cross-check the graph propagation."""
    z = 1.6448536269514722
    s = FROZEN["overhead_fraction_sigma_log"]
    med = FROZEN["overhead_fraction_median"]
    f5, f95 = med * math.exp(-z * s), med * math.exp(z * s)
    t0 = 6.0 * rec["params"]["value"] / _peak(ds, rec)
    return {"p5": t0 * (1 + f5), "p50": t0 * (1 + med), "p95": t0 * (1 + f95)}


# ---------------------------------------------------------------------------
# Energy
# ---------------------------------------------------------------------------
def energy_baselines(ds: dict, rec: dict, accel_hours: float, pue_record: Optional[float]) -> Dict[str, Optional[float]]:
    """Baselines (b) TDP x hours, (c) x fixed PUE, (c_oracle) x record PUE. MWh."""
    tdp = _tdp(ds, rec)
    if tdp is None:
        return {"b": None, "c": None, "c_oracle": None}
    b = tdp * accel_hours / 1e6
    return {
        "b": b,
        "c": b * FROZEN["pue_baseline"],
        "c_oracle": None if pue_record is None else b * pue_record,
    }


def graph_energy(ds: dict, rec: dict, scope: str, accel_hours: Optional[float]) -> Dict[str, Any]:
    """Graph electricity-energy arm.

    The energy is econ.run.power_cost resolved with every tariff set to 1 USD/kWh
    (peak = off-peak = 1, peak share 0), so the returned "cost" is kWh.
    scope:
      "system_incl_host_and_pue": GPUs + non-GPU node power + facility overhead.
      "gpu_only_raw": GPUs only, no PUE.
    accel_hours: if given (E1) the wall clock is fixed by the record; if None (E2)
    the wall clock comes from the MFU prior (training.overhead_fraction uncertain).
    """
    tdp = _tdp(ds, rec)
    if tdp is None:
        raise PredictionFailure("no TDP for accelerator")
    n = _count(rec)
    gpn = FROZEN["gpus_per_node"]
    nodes = n / gpn
    u_lo, u_hi = FROZEN["gpu_load_fraction_u"]
    k_lo, k_hi = FROZEN["node_nongpu_fraction_kappa"]
    pue_lo, pue_hi = FROZEN["pue_prior"]
    system = scope == "system_incl_host_and_pue"

    a: Dict[str, float] = {
        "par.n_gpus": float(n),
        "cluster.node.n_gpus": float(gpn),
        "cluster.rack.n_nodes": 1.0,
        "cluster.site.n_racks": float(nodes),
        "gpu.power.total": tdp * 0.5 * (u_lo + u_hi),
        "cluster.node.cpu_power": 0.0,
        "cluster.node.ram_power": 0.0,
        "cluster.node.nic_power": 0.0,
        "cluster.node.storage_power": 0.0,
        "cluster.node.misc.fixed_power": (gpn * tdp * 0.5 * (k_lo + k_hi)) if system else 0.0,
        "cluster.node.misc.power_per_gpu": 0.0,
        "thermal.facility.cooling_power": 0.0,
        "thermal.facility.ups_loss": 0.0,
        "thermal.facility.transformer_loss": 0.0,
        "thermal.facility.lighting": 0.0,
        "thermal.facility.misc_fraction": (0.5 * (pue_lo + pue_hi) - 1.0) if system else 0.0,
        "econ.power.price_kwh_peak": 1.0,
        "econ.power.price_kwh_offpeak": 1.0,
        "econ.power.peak_energy_fraction": 0.0,
    }
    uncertain = [UncertainAssignment("gpu.power.total", uniform(tdp * u_lo, tdp * u_hi))]
    if system:
        uncertain.append(UncertainAssignment("cluster.node.misc.fixed_power", uniform(gpn * tdp * k_lo, gpn * tdp * k_hi)))
        uncertain.append(UncertainAssignment("thermal.facility.misc_fraction", uniform(pue_lo - 1.0, pue_hi - 1.0)))
    if accel_hours is not None:
        a[V["wallclock"]] = accel_hours * 3600.0 / n
    else:
        a.update(_time_assignments(ds, rec, FROZEN["overhead_fraction_median"]))
        uncertain.append(UncertainAssignment(
            V["overhead"],
            lognormal(math.log(FROZEN["overhead_fraction_median"]), FROZEN["overhead_fraction_sigma_log"]),
        ))
    res = _propagate(a, "econ.run.power_cost", uncertain)
    t = res.targets[0]
    if t.p50 is None or t.failure_count > 0.01 * t.sample_count:
        raise PredictionFailure(f"energy propagation failed: failures={t.failure_count}")
    return {"mwh_p50": t.p50 / 1e3, "mwh_p5": t.p5 / 1e3, "mwh_p95": t.p95 / 1e3}


def _propagate(assignments: Dict[str, float], target: str, uncertain: list):
    """propagate_uncertainty needs a Preset to forward the dense variant selections."""
    from gpu_stack.core.presets import Preset

    p = Preset(
        name="v002_priors",
        description="V002 assignments: record inputs plus frozen priors (not data)",
        assignments=assignments,
        variants=DENSE_VARIANTS,
        source="experiments/v002-graph-published-runs/predict.py FROZEN constants",
    )
    return propagate_uncertainty(
        p, [("t", target)], uncertain,
        n_samples=FROZEN["mc_samples"], seed=FROZEN["mc_seed"],
    )


# ---------------------------------------------------------------------------
# S2: graph parameter count from an architecture description
# ---------------------------------------------------------------------------
def graph_params_from_arch(rec: dict) -> float:
    ar = rec["arch"]
    a = {
        "arch.n_layers": float(ar["n_layers"]),
        "arch.d_model": float(ar["d_model"]),
        "arch.d_ffn": float(ar["d_ffn"]),
        "arch.n_heads": float(ar["n_heads"]),
        "arch.n_kv_heads": float(ar["n_kv_heads"]),
        "arch.vocab": float(ar["vocab"]),
        "arch.ffn.weight_matrices": float(ar["ffn_weight_matrices"]),
        "arch.norm.param_multiplier": float(ar["norm_param_multiplier"]),
        "arch.output.untied_factor": 1.0 if ar["untied_output"] else 0.0,
    }
    return _resolve_value(V["params"], a)["value"]


def naive_params_from_arch(rec: dict) -> float:
    """Baseline for S2: 12 L d^2 + V d (+ V d if untied); ignores GQA, GLU and d_ffn."""
    ar = rec["arch"]
    L, d, v = ar["n_layers"], ar["d_model"], ar["vocab"]
    return 12.0 * L * d * d + v * d * (2 if ar["untied_output"] else 1)
