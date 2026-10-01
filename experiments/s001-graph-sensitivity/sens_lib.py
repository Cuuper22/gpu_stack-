"""Helpers for study S001: global sensitivity of the gpu_stack graph.

Library only. run.py is the entry point. See protocol.md for what each piece
is for and which thresholds are frozen.

Pipeline for one (preset, target):
  1. build_model: resolve the target with every preset input replaced by its own
     symbol, so the resolver returns a closed-form expression; lambdify it.
  2. make_spec: turn the nominal values into sampling ranges (rule in protocol).
  3. Evaluator: unit-cube samples -> input values -> target values.
  4. sobol / morris / elasticity estimators.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import sympy as sp
from scipy import stats
from scipy.stats import qmc

from gpu_stack import Registry
from gpu_stack.core.equation import RelationRole
from gpu_stack.core.resolver import resolve
from gpu_stack.core.resolver_graph import _value_dependencies
from gpu_stack.core.resolver_models import AmbiguousVariant
from gpu_stack.core.resolver_selection import _select_equation

# ---------------------------------------------------------------------------
# Frozen configuration (mirrors protocol.md)
# ---------------------------------------------------------------------------

TARGETS = {
    "cost_per_token": "econ.cost.per_token",
    "tokens_per_sec": "training.tokens_per_sec",
    "dc_power": "econ.job.dc_power",
    "run_power_cost": "econ.run.power_cost",
}

# Inputs with hard physical meaning that the generic rule would misuse.
SWITCH_HELD = {"arch.output.untied_factor"}  # 0/1 switch: held
MULT_GE1 = {"training.recompute_overhead", "training.optimizer_flop_multiplier"}
CAPPED_AT_NOMINAL = {"arch.n_kv_heads", "arch.norm.param_multiplier"}
FIXED_RANGE = {"arch.ffn.weight_matrices": (2.0, 3.0)}  # MLP vs gated MLP
INT_EXTRA = {
    "arch.n_layers", "arch.n_heads", "arch.n_kv_heads",
    "arch.ffn.weight_matrices", "arch.norm.param_multiplier",
}
# par.n_gpus is a pinned value that equals node GPUs x nodes x racks. Sampling it
# independently would make a physically inconsistent cluster.
TIES = {
    "par.n_gpus": (
        "cluster.node.n_gpus", "cluster.rack.n_nodes", "cluster.site.n_racks",
    )
}
NUC_RE = re.compile(r"nuclear|proton|neutron|quark|binding|isotope")
NEGLIGIBLE_ST = 0.01
MAJOR_ST = 0.10
TAU_THRESHOLD = 0.30
RULES = {
    "R1": dict(factor=2.0, zero_ext=False),
    "R1_f1.25": dict(factor=1.25, zero_ext=False),
    "R1_f4": dict(factor=4.0, zero_ext=False),
    "R4": dict(factor=2.0, zero_ext=True),
}
ZERO_EXT_FRACTION_MAX = 0.30      # dimensionless zero-nominal: U(0, 0.30)
ZERO_EXT_TIME_FRACTION = 0.30     # seconds zero-nominal: U(0, 0.30 * nominal step time)
ZERO_EXT_CARBON_MAX = 100.0       # USD/t zero-nominal: U(0, 100)


def get_presets() -> Dict[str, object]:
    from gpu_stack.presets import scenarios as S
    from gpu_stack.presets import scenarios_cited_2026 as C
    return {
        "P1_pythia70m_full_tco": S.pythia_70m_dgx_h100_us_2024_industrial_full_tco_assumption,
        "P2_dense_fixture": S.dense_training_cost_fixture,
        "P3_pythia160m_energy_floor": C.pythia_160m_dgx_h100_us_2024_industrial_energy_floor_cost,
    }


# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def tree_sha256(root: Path, suffix: str = ".py") -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob(f"*{suffix}")):
        if "__pycache__" in p.parts:
            continue
        h.update(str(p.relative_to(root)).encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Structure: root debt and ancestry
# ---------------------------------------------------------------------------

def root_debt() -> Dict[str, int]:
    """Dependents per root, exactly as `cli root-debt` counts them (default flags)."""
    return {r.name: len(r.dependents(include_constraints=False)) for r in Registry.roots()}


def _ancestors(name: str, variants: Optional[Dict[str, str]]) -> set:
    """Upstream variable names. variants=None: any non-constraint defining
    equation. Otherwise the resolver's selected equation (union if ambiguous).
    Assignments are ignored."""
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


def is_lith(name: str) -> bool:
    return name.startswith("physical.lithography.")


def is_nuc(name: str) -> bool:
    return is_lith(name) and bool(NUC_RE.search(name))


def group_counts(names: Sequence[str]) -> Dict[str, int]:
    return {
        "roots": len(names),
        "lithography": sum(is_lith(n) for n in names),
        "nuclear_quark": sum(is_nuc(n) for n in names),
    }


# ---------------------------------------------------------------------------
# Model: closed-form expression of a target in the preset's inputs
# ---------------------------------------------------------------------------

@dataclass
class Model:
    preset_name: str
    target_label: str
    target_name: str
    names: List[str]                 # free-symbol input names, column order of lam
    nominal: np.ndarray
    lam: object
    n_ops: int
    build_seconds: float
    nominal_value: float
    resolve_value: float

    def eval_x(self, X: np.ndarray) -> np.ndarray:
        """X: (n, len(names)) physical input values -> (n,) target values."""
        out = self.lam(*[X[:, j] for j in range(X.shape[1])])
        out = np.asarray(out, dtype=float)
        if out.ndim == 0:
            out = np.full(X.shape[0], float(out))
        return out


def build_model(preset, target_label: str) -> Model:
    target = TARGETS[target_label]
    t0 = time.time()
    sym_assign = {k: Registry.variables[k].symbol for k in preset.assignments}
    r = resolve(target, assignments=sym_assign, variants=preset.variants)
    if r.missing:
        raise RuntimeError(f"{preset.name}/{target}: unresolved inputs {sorted(r.missing)}")
    expr = r.value
    syms = sorted(expr.free_symbols, key=str)
    names = []
    for s in syms:
        v = Registry.lookup_by_symbol(s)
        if v is None or v.name not in preset.assignments:
            raise RuntimeError(f"{preset.name}/{target}: free symbol {s} is not a preset input")
        names.append(v.name)
    lam = sp.lambdify(syms, expr, modules="numpy", cse=True)
    nominal = np.array([float(preset.assignments[n]) for n in names])
    # Cross-check the lambdified closed form against the numeric resolver.
    r0 = resolve(target, assignments=dict(preset.assignments), variants=preset.variants)
    resolve_value = float(r0.value)
    nominal_value = float(lam(*nominal)) if names else float(expr)
    rel = abs(nominal_value - resolve_value) / max(abs(resolve_value), 1e-300)
    if rel > 1e-9:
        raise RuntimeError(
            f"{preset.name}/{target}: lambdified value {nominal_value} != resolver {resolve_value}"
        )
    return Model(
        preset_name=preset.name, target_label=target_label, target_name=target,
        names=names, nominal=nominal, lam=lam, n_ops=int(sp.count_ops(expr)),
        build_seconds=time.time() - t0, nominal_value=nominal_value,
        resolve_value=resolve_value,
    )


def structure_report(preset, model: Model, debt: Dict[str, int]) -> Dict[str, object]:
    """How many of the roots are connected to the target, and how many are in the formula."""
    root_names = {r.name for r in Registry.roots()}
    anc_any = _ancestors(model.target_name, None) & root_names
    anc_sel = _ancestors(model.target_name, dict(preset.variants)) & root_names
    assigned_roots = {n for n in preset.assignments if n in root_names}
    in_formula = set(model.names)
    present_roots = sorted(in_formula & root_names)
    present_pins = sorted(in_formula - root_names)
    # Roots hidden under each pinned cut point that is in the formula (selected equations).
    cut_points = {}
    for c in present_pins:
        under = _ancestors(c, dict(preset.variants)) & root_names
        cut_points[c] = {
            "roots_beneath": len(under),
            "lithography_beneath": sum(is_lith(n) for n in under),
            "nuclear_quark_beneath": sum(is_nuc(n) for n in under),
        }
    return {
        "total_roots": len(root_names),
        "structurally_connected_any_equation": group_counts(sorted(anc_any)),
        "structurally_connected_selected_equation": group_counts(sorted(anc_sel)),
        "assigned_in_preset": {
            "all_inputs": len(preset.assignments),
            "roots": group_counts(sorted(assigned_roots)),
            "derived_pins": len(preset.assignments) - len(assigned_roots),
        },
        "in_resolved_formula": {
            "inputs_total": len(in_formula),
            "roots": group_counts(present_roots),
            "derived_pins": len(present_pins),
            "present_root_names": present_roots,
            "present_pin_names": present_pins,
        },
        "cut_points_in_formula": cut_points,
        "mean_root_debt_present_roots": float(np.mean([debt[n] for n in present_roots])) if present_roots else None,
    }


# ---------------------------------------------------------------------------
# Sampling spec and evaluator
# ---------------------------------------------------------------------------

@dataclass
class Spec:
    rule: str
    factor_names: List[str]          # sampled factors, one unit-cube column each
    lo: np.ndarray
    hi: np.ndarray
    is_log: np.ndarray
    is_int: np.ndarray
    held: Dict[str, str]             # in-formula inputs held at nominal, with reason
    tied: Dict[str, Tuple[str, ...]] # follower -> drivers (follower not a factor)
    notes: Dict[str, str] = field(default_factory=dict)


def _is_int(name: str) -> bool:
    return bool(Registry.variables[name].symbol.is_integer) or name in INT_EXTRA


def make_spec(preset, model: Model, rule: str, t_step_nominal: float) -> Spec:
    cfg = RULES[rule]
    f = cfg["factor"]
    nominal = dict(zip(model.names, model.nominal))
    # Ties: apply only when the follower is in the formula and the nominals agree.
    tied: Dict[str, Tuple[str, ...]] = {}
    for follower, drivers in TIES.items():
        if follower in nominal and all(d in preset.assignments for d in drivers):
            prod = 1.0
            for d in drivers:
                prod *= float(preset.assignments[d])
            if abs(prod - nominal[follower]) < 1e-9:
                tied[follower] = drivers
    input_names = [n for n in model.names if n not in tied]
    for drivers in tied.values():
        for d in drivers:
            if d not in input_names:
                input_names.append(d)
    names: List[str] = []
    lo: List[float] = []
    hi: List[float] = []
    lg: List[bool] = []
    held: Dict[str, str] = {}
    notes: Dict[str, str] = {}

    def add(n: str, a: float, b: float, log: bool, note: str = "") -> None:
        names.append(n)
        lo.append(a)
        hi.append(b)
        lg.append(log)
        if note:
            notes[n] = note

    for n in input_names:
        x0 = float(preset.assignments[n])
        var = Registry.variables[n]
        units = var.units
        if n in SWITCH_HELD:
            held[n] = "binary switch"
            continue
        if x0 == 0.0:
            if cfg["zero_ext"]:
                if units == "dimensionless":
                    add(n, 0.0, ZERO_EXT_FRACTION_MAX, False, "zero-nominal extension: U(0,0.30)")
                    continue
                if units == "s":
                    add(n, 0.0, ZERO_EXT_TIME_FRACTION * t_step_nominal, False, "zero-nominal extension: U(0, 0.30 x nominal step time)")
                    continue
                if units == "USD/t":
                    add(n, 0.0, ZERO_EXT_CARBON_MAX, False, "zero-nominal extension: U(0,100) USD/t")
                    continue
            held[n] = "zero nominal"
            continue
        if x0 < 0.0:
            held[n] = "negative nominal"
            continue
        if n in FIXED_RANGE:
            a, b = FIXED_RANGE[n]
            add(n, a, b, False, "fixed discrete range")
            continue
        if n in MULT_GE1:
            add(n, x0, x0 * f, True, "multiplier >= 1: [nominal, nominal x f]")
            continue
        if n in CAPPED_AT_NOMINAL:
            add(n, max(x0 / f, 1.0), x0, True, "capped at nominal: [nominal / f, nominal]")
            continue
        if units == "dimensionless" and x0 <= 1.0:
            top = min(x0 * f, 1.0)
            if top <= x0 / f:
                held[n] = "fraction range empty"
                continue
            add(n, x0 / f, top, True, "fraction: [nominal / f, min(nominal x f, 1)]")
            continue
        add(n, x0 / f, x0 * f, True)
    return Spec(
        rule=rule, factor_names=names, lo=np.array(lo), hi=np.array(hi),
        is_log=np.array(lg, dtype=bool),
        is_int=np.array([_is_int(n) for n in names], dtype=bool),
        held=held, tied=tied, notes=notes,
    )


class Evaluator:
    """Unit cube (n, k) -> target values (n,)."""

    def __init__(self, preset, model: Model, spec: Spec):
        self.model, self.spec = model, spec
        self.k = len(spec.factor_names)
        col = {n: j for j, n in enumerate(model.names)}
        self.model_cols = col
        self.fac_index = {n: i for i, n in enumerate(spec.factor_names)}
        self.nominal_full = {n: float(preset.assignments[n]) for n in preset.assignments}

    def x_factors(self, U: np.ndarray) -> np.ndarray:
        s = self.spec
        X = np.empty_like(U)
        lg = s.is_log
        if lg.any():
            X[:, lg] = s.lo[lg] * (s.hi[lg] / s.lo[lg]) ** U[:, lg]
        if (~lg).any():
            X[:, ~lg] = s.lo[~lg] + (s.hi[~lg] - s.lo[~lg]) * U[:, ~lg]
        it = s.is_int
        if it.any():
            X[:, it] = np.maximum(1.0, np.floor(X[:, it] + 0.5))
        return X

    def x_inputs(self, U: np.ndarray) -> np.ndarray:
        """Full model input matrix (n, len(model.names))."""
        n = U.shape[0]
        XF = self.x_factors(U)
        M = np.empty((n, len(self.model.names)))
        for j, name in enumerate(self.model.names):
            if name in self.fac_index:
                M[:, j] = XF[:, self.fac_index[name]]
            elif name in self.spec.tied:
                prod = np.ones(n)
                for d in self.spec.tied[name]:
                    if d in self.fac_index:
                        prod = prod * XF[:, self.fac_index[d]]
                    else:
                        prod = prod * self.nominal_full[d]
                M[:, j] = prod
            else:
                M[:, j] = self.model.nominal[j]
        return M

    def __call__(self, U: np.ndarray) -> np.ndarray:
        with np.errstate(all="ignore"):
            return self.model.eval_x(self.x_inputs(U))


def nominal_unit_point(ev: Evaluator) -> np.ndarray:
    """Unit-cube point whose mapped values are as close to the nominal as the
    spec allows (used only for the elasticity check and tests)."""
    s = ev.spec
    u = np.zeros(ev.k)
    for i, n in enumerate(s.factor_names):
        x0 = ev.nominal_full[n]
        if s.is_log[i]:
            u[i] = math.log(min(max(x0, s.lo[i]), s.hi[i]) / s.lo[i]) / math.log(s.hi[i] / s.lo[i])
        else:
            u[i] = (min(max(x0, s.lo[i]), s.hi[i]) - s.lo[i]) / (s.hi[i] - s.lo[i])
    return u


def local_elasticities(model: Model, names: Sequence[str], h: float = 1e-3) -> Dict[str, Optional[float]]:
    """d ln(target) / d ln(input) at the nominal point, central difference. None if nominal is 0."""
    out: Dict[str, Optional[float]] = {}
    base = model.nominal.copy()
    for n in names:
        j = model.names.index(n) if n in model.names else None
        if j is None or base[j] == 0.0:
            out[n] = None
            continue
        up, dn = base.copy(), base.copy()
        up[j] *= math.exp(h)
        dn[j] *= math.exp(-h)
        with np.errstate(all="ignore"):
            fu = float(model.eval_x(up[None, :])[0])
            fd = float(model.eval_x(dn[None, :])[0])
        out[n] = (math.log(fu) - math.log(fd)) / (2 * h) if fu > 0 and fd > 0 else None
    return out


# ---------------------------------------------------------------------------
# Sobol indices (Saltelli 2010 first order, Jansen total order)
# ---------------------------------------------------------------------------

def sobol_design_eval(ev: Evaluator, n_pow: int, seed: int,
                      groups: Dict[str, List[int]]) -> Dict[str, np.ndarray]:
    """Evaluate A, B, AB_i (one column swapped) and AB_g (a group of columns swapped)
    on a scrambled Sobol sequence of dimension 2k. Returns raw target values."""
    k = ev.k
    M = qmc.Sobol(d=2 * k, scramble=True, seed=seed).random_base2(n_pow)
    A, B = M[:, :k], M[:, k:]
    yA, yB = ev(A), ev(B)
    yAB = np.empty((k, A.shape[0]))
    for i in range(k):
        ABi = A.copy()
        ABi[:, i] = B[:, i]
        yAB[i] = ev(ABi)
    yG = np.empty((len(groups), A.shape[0]))
    for gi, (_, cols) in enumerate(groups.items()):
        ABg = A.copy()
        ABg[:, cols] = B[:, cols]
        yG[gi] = ev(ABg)
    return {"yA": yA, "yB": yB, "yAB": yAB, "yG": yG}


def _indices(a, b, ab, g, idx=None, want_s1=True):
    if idx is not None:
        a, b, ab = a[idx], b[idx], ab[:, idx]
        g = g[:, idx] if g.size else g
    mu = np.mean(np.concatenate([a, b]))
    a, b, ab = a - mu, b - mu, ab - mu
    V = np.var(np.concatenate([a, b]), ddof=1)
    if not np.isfinite(V) or V <= 0:
        z = np.zeros(ab.shape[0])
        return z, z, np.zeros(g.shape[0]), 0.0
    s1 = np.mean(b[None, :] * (ab - a[None, :]), axis=1) / V if want_s1 else None
    st = 0.5 * np.mean((a[None, :] - ab) ** 2, axis=1) / V
    if g.size:
        gm = g - mu
        stg = 0.5 * np.mean((a[None, :] - gm) ** 2, axis=1) / V
    else:
        stg = np.zeros(0)
    return s1, st, stg, V


def sobol_point(design: Dict[str, np.ndarray], n: int, transform) -> Dict[str, object]:
    sl = slice(0, n)
    a, b = transform(design["yA"][sl]), transform(design["yB"][sl])
    ab = transform(design["yAB"][:, sl])
    g = transform(design["yG"][:, sl]) if design["yG"].size else design["yG"][:, sl]
    s1, st, stg, V = _indices(a, b, ab, g)
    return {"S1": s1, "ST": st, "STg": stg, "V": V}


def sobol_bootstrap(design, n: int, transform, n_boot: int, seed: int):
    """Percentile bootstrap over rows. Returns arrays (n_boot, k) and (n_boot, g)."""
    sl = slice(0, n)
    a, b = transform(design["yA"][sl]), transform(design["yB"][sl])
    ab = transform(design["yAB"][:, sl])
    g = transform(design["yG"][:, sl]) if design["yG"].size else design["yG"][:, sl]
    rng = np.random.default_rng(seed)
    S1 = np.empty((n_boot, ab.shape[0]))
    ST = np.empty((n_boot, ab.shape[0]))
    STg = np.empty((n_boot, g.shape[0]))
    for r in range(n_boot):
        idx = rng.integers(0, n, n)
        s1, st, stg, _ = _indices(a, b, ab, g, idx)
        S1[r], ST[r], STg[r] = s1, st, stg
    return S1, ST, STg


def ci(arr: np.ndarray, lo: float = 2.5, hi: float = 97.5) -> Tuple[np.ndarray, np.ndarray]:
    return np.percentile(arr, lo, axis=0), np.percentile(arr, hi, axis=0)


def log_transform(y: np.ndarray) -> np.ndarray:
    with np.errstate(all="ignore"):
        return np.log(y)


def identity_transform(y: np.ndarray) -> np.ndarray:
    return y


# ---------------------------------------------------------------------------
# Morris elementary effects (on log target; unit-cube steps)
# ---------------------------------------------------------------------------

def morris(ev: Evaluator, r: int, seed: int, levels: int = 4) -> Dict[str, np.ndarray]:
    k = ev.k
    rng = np.random.default_rng(seed)
    delta = levels / (2.0 * (levels - 1))
    grid = np.arange(levels) / (levels - 1)
    EE = np.empty((r, k))
    for t in range(r):
        x = rng.choice(grid, size=k)
        order = rng.permutation(k)
        pts = [x.copy()]
        signs = np.empty(k)
        cur = x.copy()
        for i in order:
            s = 1.0 if cur[i] + delta <= 1.0 + 1e-12 else -1.0
            cur[i] += s * delta
            signs[i] = s
            pts.append(cur.copy())
        y = np.log(ev(np.array(pts)))
        for pos, i in enumerate(order):
            EE[t, i] = (y[pos + 1] - y[pos]) / (signs[i] * delta)
    return {"EE": EE, "mu": EE.mean(0), "mu_star": np.abs(EE).mean(0), "sigma": EE.std(0, ddof=1)}


# ---------------------------------------------------------------------------
# Rank comparison
# ---------------------------------------------------------------------------

def kendall_tau(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan")
    return float(stats.kendalltau(x, y, variant="b").statistic)


def tau_bootstrap(st_boot: np.ndarray, debt: np.ndarray, seed: int) -> np.ndarray:
    """Each replicate uses one Sobol bootstrap draw of ST and a resample of the roots."""
    rng = np.random.default_rng(seed)
    n = len(debt)
    out = np.empty(st_boot.shape[0])
    for r in range(st_boot.shape[0]):
        idx = rng.integers(0, n, n)
        out[r] = kendall_tau(st_boot[r][idx], debt[idx])
    return out


def classify(st_lo: float, st_hi: float) -> str:
    if st_hi < NEGLIGIBLE_ST:
        return "negligible"
    if st_lo >= MAJOR_ST:
        return "major"
    if st_lo >= NEGLIGIBLE_ST:
        return "minor"
    return "ambiguous"


def tau_verdict(lo95_one_sided: float, hi95_one_sided: float) -> str:
    """Frozen rule: supported if the one-sided 95% upper bound < 0.30; refuted if the
    one-sided 95% lower bound >= 0.30; otherwise inconclusive."""
    if hi95_one_sided < TAU_THRESHOLD:
        return "supported"
    if lo95_one_sided >= TAU_THRESHOLD:
        return "refuted"
    return "inconclusive"
