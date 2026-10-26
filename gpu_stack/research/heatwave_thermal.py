"""Rack-level RC thermal model, GPU throttle model, and cooling power model.

This module is the thermal layer of the Heatwave extension of the multi-site
virtual datacenter (experiment e003).  Everything here is a simulation
component.  Nothing in it is a measurement; constants are either parameters the
caller must supply, or are labeled with their source in the docstring that
introduces them.

RC node model
-------------
A rack (or a single GPU) is one thermal node with heat capacity ``C`` (J/K)::

    C dT/dt = P_it(t) - Q_cool(t)
    Q_cool  = min( (T - T_supply) / R , cooling_capacity_w(t) )

``R`` (K/W) is the thermal resistance between the node and the cooling
supply.  The supply temperature follows its setpoint with a first-order lag of
time constant ``cooling_lag_s``::

    dT_supply/dt = (setpoint(t) - T_supply) / cooling_lag_s
    setpoint(t)  = supply_setpoint_c + k_out * max(0, T_outdoor(t) - T_ref)

``k_out`` (``outdoor_coupling_k_per_k``) and ``T_ref`` (``outdoor_reference_c``)
default to zero, which gives a constant setpoint.  Their values are scenario
parameters; no default number is claimed here.

Integration is exact for piecewise-constant inputs in the linear region
(unsaturated cooling), including the supply lag, so any ``dt`` gives the same
answer as a fine step.  When ``cooling_capacity_w`` binds, the node warms at the
constant rate ``(P - capacity) / C``; the instant the cooling demand crosses the
capacity inside a step is found analytically with the supply temperature frozen
at its start-of-step value.  The heat removed over a step is computed from the
energy balance ``P dt - C (T1 - T0)``, so energy is conserved to rounding.

Time convention: ``power_w[i]`` and ``ambient_c[i]`` apply over the interval
``[i dt, (i+1) dt)``; ``temps[i]`` is the node temperature at ``i dt``, so
``temps[0] == T0`` and the output has the same length as the inputs.

GPU throttle model
------------------
:class:`GPUThrottleModel` has no default numbers.  NVIDIA does not publish a
single throttle threshold in the product specification sheet that this
repository cites (https://www.nvidia.com/en-us/data-center/h100/ lists TDP but
not a slowdown temperature), so the threshold, the temperature span, the
minimum clock fraction, and the power-versus-clock exponent are all scenario
parameters and are labeled as assumptions wherever a scenario sets them.

Cooling power
-------------
:class:`CoolingPowerModel` offers two modes.

* ``pue``: cooling power is ``(PUE - 1) * heat_removed``.  This is the baseline
  that ``gpu_stack.calculator`` uses (its ``pue`` input, a labeled assumption).
* ``carnot``: cooling power is ``heat_removed / COP`` with
  ``COP = eta * T_evap / (T_cond - T_evap)`` (temperatures in kelvin), the
  Carnot refrigeration coefficient of performance multiplied by a second-law
  efficiency ``eta`` (https://en.wikipedia.org/wiki/Coefficient_of_performance).
  ``T_evap = supply - evaporator_approach`` and ``T_cond = outdoor +
  condenser_approach``.  ``eta`` is derived by
  :meth:`CoolingPowerModel.carnot_from_pue`, which sets it so the model
  reproduces a chosen PUE at a chosen reference outdoor temperature.  Only the
  dependence on outdoor temperature comes from the Carnot formula; the level
  comes from the PUE assumption.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Tuple

import numpy as np

_KELVIN = 273.15


def _finite(value: float, name: str, *, minimum: float = 0.0, strict: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{name} must be a real number")
    if math.isnan(float(value)):
        raise ValueError(f"{name} must not be NaN")
    if strict and not float(value) > minimum:
        raise ValueError(f"{name} must be > {minimum}")
    if not strict and float(value) < minimum:
        raise ValueError(f"{name} must be >= {minimum}")


def _json_number(value: float) -> Optional[float]:
    return None if math.isinf(value) else float(value)


@dataclass(frozen=True)
class RCThermalParams:
    """Parameters of one RC thermal node.

    ``cooling_capacity_w`` may be ``math.inf`` (cooling never saturates).
    """

    heat_capacity_j_per_k: float
    resistance_k_per_w: float
    cooling_lag_s: float
    cooling_capacity_w: float
    supply_setpoint_c: float
    outdoor_coupling_k_per_k: float = 0.0
    outdoor_reference_c: float = 0.0

    def __post_init__(self) -> None:
        _finite(self.heat_capacity_j_per_k, "heat_capacity_j_per_k", strict=True)
        _finite(self.resistance_k_per_w, "resistance_k_per_w", strict=True)
        _finite(self.cooling_lag_s, "cooling_lag_s")
        _finite(self.cooling_capacity_w, "cooling_capacity_w")
        for name in ("supply_setpoint_c", "outdoor_coupling_k_per_k", "outdoor_reference_c"):
            value = getattr(self, name)
            _finite(value, name, minimum=-math.inf)
            if math.isinf(float(value)):
                raise ValueError(f"{name} must be finite")
        for name in ("heat_capacity_j_per_k", "resistance_k_per_w", "cooling_lag_s"):
            if not math.isfinite(float(getattr(self, name))):
                raise ValueError(f"{name} must be finite")

    @property
    def time_constant_s(self) -> float:
        """The node time constant R * C in seconds."""
        return float(self.resistance_k_per_w) * float(self.heat_capacity_j_per_k)

    def to_dict(self) -> dict[str, Optional[float]]:
        return {
            "heat_capacity_j_per_k": float(self.heat_capacity_j_per_k),
            "resistance_k_per_w": float(self.resistance_k_per_w),
            "cooling_lag_s": float(self.cooling_lag_s),
            "cooling_capacity_w": _json_number(float(self.cooling_capacity_w)),
            "supply_setpoint_c": float(self.supply_setpoint_c),
            "outdoor_coupling_k_per_k": float(self.outdoor_coupling_k_per_k),
            "outdoor_reference_c": float(self.outdoor_reference_c),
            "time_constant_s": self.time_constant_s,
        }


def supply_setpoint(params: RCThermalParams, ambient_c: Any) -> np.ndarray:
    """Supply setpoint (deg C) for an outdoor temperature or an array of them."""
    amb = np.asarray(ambient_c, dtype=float)
    return params.supply_setpoint_c + params.outdoor_coupling_k_per_k * np.maximum(
        0.0, amb - params.outdoor_reference_c
    )


# ---------------------------------------------------------------------------
# Exact step
# ---------------------------------------------------------------------------


def rc_step(
    heat_capacity: Any,
    resistance: Any,
    lag_s: Any,
    capacity_w: Any,
    setpoint_c: Any,
    temp_c: Any,
    supply_c: Any,
    power_w: Any,
    dt_s: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Advance node(s) one step of ``dt_s`` seconds.

    All array arguments broadcast together.  Returns
    ``(temp_next, supply_next, heat_removed_j)``.
    """
    C = np.asarray(heat_capacity, dtype=float)
    R = np.asarray(resistance, dtype=float)
    lag = np.asarray(lag_s, dtype=float)
    cap = np.asarray(capacity_w, dtype=float)
    sp = np.asarray(setpoint_c, dtype=float)
    T0 = np.asarray(temp_c, dtype=float)
    Ts0 = np.asarray(supply_c, dtype=float)
    P = np.asarray(power_w, dtype=float)
    dt = float(dt_s)
    if not dt > 0.0:
        raise ValueError("dt_s must be > 0")

    tau = R * C
    a = np.exp(-dt / tau)
    has_lag = lag > 0.0
    safe_lag = np.where(has_lag, lag, 1.0)
    b = np.where(has_lag, np.exp(-dt / safe_lag), 0.0)
    delta = np.where(has_lag, Ts0 - sp, 0.0)
    Ts1 = np.where(has_lag, sp + delta * b, sp)
    Ts_start = np.where(has_lag, Ts0, sp)

    ratio = tau / safe_lag
    near = np.abs(1.0 - ratio) < 1e-9
    denom = np.where(near, 1.0, 1.0 - ratio)
    g = np.where(near, a * dt / tau, (b - a) / denom)
    T_eq = sp + R * P
    T1_lin = T_eq + (T0 - T_eq) * a + delta * g

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        q_start = (T0 - Ts_start) / R
        q_end = (T1_lin - Ts1) / R
        saturated = np.maximum(q_start, q_end) > cap

        Ts_f = Ts_start
        T_c = Ts_f + R * cap
        T_eq_f = Ts_f + R * P
        rate = (P - cap) / C
        e_full = np.exp(-dt / tau)

        # Saturated at the start of the step.
        t_exit = np.where(rate < 0.0, (T0 - T_c) / (-rate), np.inf)
        dt2 = np.maximum(dt - t_exit, 0.0)
        T_after_exit = T_eq_f + (T_c - T_eq_f) * np.exp(-dt2 / tau)
        T1_case_a = np.where(t_exit >= dt, T0 + rate * dt, T_after_exit)

        # Unsaturated at the start, crossing the capacity inside the step.
        arg = (T_eq_f - T0) / (T_eq_f - T_c)
        t_cross = np.where(
            (T_eq_f > T_c) & (arg > 0.0), tau * np.log(np.where(arg > 0.0, arg, 1.0)), np.inf
        )
        T1_case_b = np.where(
            t_cross >= dt,
            T1_lin,
            T_c + rate * np.maximum(dt - t_cross, 0.0),
        )
        T1_sat = np.where(T0 > T_c, T1_case_a, T1_case_b)
        _ = e_full

    T1 = np.where(saturated, T1_sat, T1_lin)
    removed = P * dt - C * (T1 - T0)
    return T1, Ts1, removed


def _rc_step_scalar(
    C: float, R: float, lag: float, cap: float, sp: float, T0: float, Ts0: float, P: float, dt: float
) -> Tuple[float, float, float]:
    """Pure-Python twin of :func:`rc_step` for scalar nodes (faster in loops)."""
    tau = R * C
    a = math.exp(-dt / tau)
    if lag > 0.0:
        b = math.exp(-dt / lag)
        delta = Ts0 - sp
        Ts1 = sp + delta * b
        Ts_start = Ts0
        ratio = tau / lag
        if abs(1.0 - ratio) < 1e-9:
            g = a * dt / tau
        else:
            g = (b - a) / (1.0 - ratio)
    else:
        delta = 0.0
        Ts1 = sp
        Ts_start = sp
        g = 0.0
    T_eq = sp + R * P
    T1_lin = T_eq + (T0 - T_eq) * a + delta * g
    q_start = (T0 - Ts_start) / R
    q_end = (T1_lin - Ts1) / R
    if max(q_start, q_end) > cap:
        T_c = Ts_start + R * cap
        T_eq_f = Ts_start + R * P
        rate = (P - cap) / C
        if T0 > T_c:
            t_exit = (T0 - T_c) / (-rate) if rate < 0.0 else math.inf
            if t_exit >= dt:
                T1 = T0 + rate * dt
            else:
                T1 = T_eq_f + (T_c - T_eq_f) * math.exp(-(dt - t_exit) / tau)
        else:
            t_cross = math.inf
            if T_eq_f > T_c:
                arg = (T_eq_f - T0) / (T_eq_f - T_c)
                if arg > 0.0:
                    t_cross = tau * math.log(arg)
            T1 = T1_lin if t_cross >= dt else T_c + rate * max(dt - t_cross, 0.0)
    else:
        T1 = T1_lin
    return T1, Ts1, P * dt - C * (T1 - T0)


def simulate(
    params: RCThermalParams,
    power_w: Any,
    ambient_c: Any,
    dt_s: float,
    T0: float,
    capacity_w: Any = None,
    supply0_c: Optional[float] = None,
) -> np.ndarray:
    """Node temperatures (deg C) for a power and outdoor-temperature series.

    ``power_w`` and ``ambient_c`` are 1-D arrays of equal length.  ``capacity_w``
    optionally overrides ``params.cooling_capacity_w`` with a time-varying
    series (for example a cooling failure).  ``supply0_c`` is the supply
    temperature at the start; it defaults to the setpoint at the first sample.
    Returns an array the same length as the inputs with ``temps[0] == T0``.
    """
    return simulate_full(params, power_w, ambient_c, dt_s, T0, capacity_w, supply0_c)["temp_c"]


def simulate_full(
    params: RCThermalParams,
    power_w: Any,
    ambient_c: Any,
    dt_s: float,
    T0: float,
    capacity_w: Any = None,
    supply0_c: Optional[float] = None,
) -> dict[str, np.ndarray]:
    """Like :func:`simulate` but also returns supply temperature and heat removed.

    Keys: ``temp_c``, ``supply_c`` (values at ``i dt``) and ``heat_removed_w``
    (mean over each step).
    """
    P = np.asarray(power_w, dtype=float)
    amb = np.asarray(ambient_c, dtype=float)
    if P.ndim != 1 or amb.shape != P.shape:
        raise ValueError("power_w and ambient_c must be 1-D arrays of equal length")
    n = P.shape[0]
    if capacity_w is None:
        cap = np.full(n, float(params.cooling_capacity_w))
    else:
        cap = np.asarray(capacity_w, dtype=float)
        if cap.shape != P.shape:
            raise ValueError("capacity_w must match power_w in shape")
    sp = supply_setpoint(params, amb)
    temps = np.empty(n)
    supply = np.empty(n)
    removed = np.empty(n)
    T = float(T0)
    Ts = float(sp[0]) if supply0_c is None and n else float(supply0_c if supply0_c is not None else 0.0)
    C = float(params.heat_capacity_j_per_k)
    R = float(params.resistance_k_per_w)
    lag = float(params.cooling_lag_s)
    dt = float(dt_s)
    if not dt > 0.0:
        raise ValueError("dt_s must be > 0")
    for i in range(n):
        temps[i] = T
        supply[i] = Ts
        T, Ts, e = _rc_step_scalar(C, R, lag, float(cap[i]), float(sp[i]), T, Ts, float(P[i]), dt)
        removed[i] = e / dt
    return {"temp_c": temps, "supply_c": supply, "heat_removed_w": removed}


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------

_FIT_FIELDS = (
    "heat_capacity_j_per_k",
    "resistance_k_per_w",
    "cooling_lag_s",
    "supply_setpoint_c",
    "outdoor_coupling_k_per_k",
)
_LOG_FIELDS = {"heat_capacity_j_per_k", "resistance_k_per_w"}


def fit(
    power_w: Any,
    ambient_c: Any,
    temp_c: Any,
    dt_s: float,
    *,
    free: Sequence[str] = ("heat_capacity_j_per_k", "resistance_k_per_w", "supply_setpoint_c"),
    fixed: Optional[Mapping[str, float]] = None,
    initial: Optional[Mapping[str, float]] = None,
    capacity_w: Any = None,
) -> Tuple[RCThermalParams, dict[str, Any]]:
    """Least-squares calibration of an RC node on a power/ambient/temperature trace.

    ``free`` names the fitted fields (from ``heat_capacity_j_per_k``,
    ``resistance_k_per_w``, ``cooling_lag_s``, ``supply_setpoint_c``,
    ``outdoor_coupling_k_per_k``).  Every other field takes its value from
    ``fixed`` (``cooling_lag_s`` defaults to 0, ``outdoor_coupling_k_per_k`` to
    0, ``outdoor_reference_c`` to 0, cooling capacity to unlimited).  The node
    starts at ``temp_c[0]`` with its supply at the setpoint.

    Returns ``(params, report)``.  The report holds ``rmse_c``, ``r2``,
    ``time_constant_s`` (R*C), ``n``, ``success``, ``free`` and ``cost``.
    ``scipy`` is imported here because it is not a gpu_stack dependency.
    """
    try:
        from scipy.optimize import least_squares  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - exercised only without scipy
        raise RuntimeError(
            "heatwave_thermal.fit needs scipy (pip install scipy); scipy is not a gpu_stack dependency"
        ) from exc

    P = np.asarray(power_w, dtype=float)
    amb = np.asarray(ambient_c, dtype=float)
    Y = np.asarray(temp_c, dtype=float)
    if not (P.ndim == 1 and P.shape == amb.shape == Y.shape and P.size >= 8):
        raise ValueError("power_w, ambient_c and temp_c must be 1-D arrays of equal length >= 8")
    free = tuple(free)
    for name in free:
        if name not in _FIT_FIELDS:
            raise ValueError(f"cannot fit {name!r}; choose from {_FIT_FIELDS}")
    if "heat_capacity_j_per_k" not in free or "resistance_k_per_w" not in free:
        raise ValueError("free must include heat_capacity_j_per_k and resistance_k_per_w")
    fixed_values = dict(fixed or {})
    base = {
        "cooling_lag_s": 0.0,
        "supply_setpoint_c": float(np.min(Y)),
        "outdoor_coupling_k_per_k": 0.0,
        "outdoor_reference_c": 0.0,
        "cooling_capacity_w": math.inf,
    }
    base.update(fixed_values)
    span = dt_s * P.size
    p_scale = max(float(np.ptp(P)), float(np.mean(np.abs(P))), 1e-9)
    t_scale = max(float(np.ptp(Y)), 1e-3)
    guess = {
        "heat_capacity_j_per_k": 0.1 * span * p_scale / t_scale,
        "resistance_k_per_w": t_scale / p_scale,
        "cooling_lag_s": 0.02 * span,
        "supply_setpoint_c": float(np.min(Y)),
        "outdoor_coupling_k_per_k": 0.1,
    }
    guess.update(dict(initial or {}))

    def build(vec: np.ndarray) -> RCThermalParams:
        values = dict(base)
        for name, x in zip(free, vec):
            values[name] = math.exp(x) if name in _LOG_FIELDS else float(x)
        if "cooling_lag_s" in free:
            values["cooling_lag_s"] = max(values["cooling_lag_s"], 0.0)
        return RCThermalParams(
            heat_capacity_j_per_k=values.get("heat_capacity_j_per_k", guess["heat_capacity_j_per_k"]),
            resistance_k_per_w=values.get("resistance_k_per_w", guess["resistance_k_per_w"]),
            cooling_lag_s=values["cooling_lag_s"],
            cooling_capacity_w=values["cooling_capacity_w"],
            supply_setpoint_c=values["supply_setpoint_c"],
            outdoor_coupling_k_per_k=values["outdoor_coupling_k_per_k"],
            outdoor_reference_c=values["outdoor_reference_c"],
        )

    def residual(vec: np.ndarray) -> np.ndarray:
        try:
            p = build(vec)
            pred = simulate(p, P, amb, dt_s, float(Y[0]), capacity_w=capacity_w)
        except (ValueError, OverflowError, FloatingPointError):
            return np.full(Y.shape, 1e6)
        out = pred - Y
        return np.where(np.isfinite(out), out, 1e6)

    def start_vector(tau_scale: float) -> np.ndarray:
        vec = []
        for name in free:
            g = guess[name]
            if name == "heat_capacity_j_per_k":
                g = g * tau_scale
            vec.append(math.log(g) if name in _LOG_FIELDS else g)
        vec = [max(v, 1e-6) if name == "cooling_lag_s" else v for name, v in zip(free, vec)]
        return np.array(vec, dtype=float)

    lower = np.array([0.0 if name == "cooling_lag_s" else -np.inf for name in free])
    upper = np.full(len(free), np.inf)
    best = None
    for tau_scale in (1.0, 0.1, 10.0):
        sol = least_squares(
            residual,
            start_vector(tau_scale),
            bounds=(lower, upper),
            x_scale="jac",
            max_nfev=400 * len(free),
        )
        if best is None or sol.cost < best.cost:
            best = sol
    assert best is not None
    params = build(best.x)
    pred = simulate(params, P, amb, dt_s, float(Y[0]), capacity_w=capacity_w)
    resid = pred - Y
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((Y - np.mean(Y)) ** 2))
    report = {
        "rmse_c": float(math.sqrt(ss_res / Y.size)),
        "r2": float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
        "time_constant_s": params.time_constant_s,
        "n": int(Y.size),
        "success": bool(best.success),
        "free": list(free),
        "cost": float(best.cost),
        "params": params.to_dict(),
    }
    return params, report


# ---------------------------------------------------------------------------
# GPU throttle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GPUThrottleModel:
    """Temperature-driven clock and power reduction.

    No field has a default.  Below ``throttle_threshold_c`` the clock fraction
    is 1.  It falls linearly to ``min_clock_fraction`` at
    ``throttle_threshold_c + throttle_span_c``.  Dynamic power (the part above
    idle) scales as ``clock ** power_exponent`` (voltage-frequency scaling).
    Progress of a job scales with the clock fraction.
    """

    throttle_threshold_c: float
    throttle_span_c: float
    min_clock_fraction: float
    power_exponent: float

    def __post_init__(self) -> None:
        _finite(self.throttle_threshold_c, "throttle_threshold_c", minimum=-math.inf)
        _finite(self.throttle_span_c, "throttle_span_c", strict=True)
        _finite(self.min_clock_fraction, "min_clock_fraction", strict=True)
        if self.min_clock_fraction > 1.0:
            raise ValueError("min_clock_fraction must be <= 1")
        _finite(self.power_exponent, "power_exponent", strict=True)

    def clock_fraction(self, temp_c: Any) -> np.ndarray:
        t = np.asarray(temp_c, dtype=float)
        over = np.clip((t - self.throttle_threshold_c) / self.throttle_span_c, 0.0, 1.0)
        return 1.0 - (1.0 - self.min_clock_fraction) * over

    def power_w(self, level_w: Any, idle_w: Any, clock: Any) -> np.ndarray:
        """Power at ``clock`` for an active level; idle power is not scaled."""
        level = np.asarray(level_w, dtype=float)
        idle = np.asarray(idle_w, dtype=float)
        c = np.asarray(clock, dtype=float)
        return np.where(level > idle, idle + (level - idle) * c**self.power_exponent, level)

    def clock_for_power(self, limit_w: Any, level_w: Any, idle_w: Any) -> np.ndarray:
        """Largest clock fraction whose active power stays within ``limit_w``."""
        limit = np.asarray(limit_w, dtype=float)
        level = np.asarray(level_w, dtype=float)
        idle = np.asarray(idle_w, dtype=float)
        span = np.maximum(level - idle, 1e-12)
        x = np.clip((limit - idle) / span, 0.0, 1.0)
        return np.clip(x ** (1.0 / self.power_exponent), self.min_clock_fraction, 1.0)

    def to_dict(self) -> dict[str, float]:
        return {
            "throttle_threshold_c": float(self.throttle_threshold_c),
            "throttle_span_c": float(self.throttle_span_c),
            "min_clock_fraction": float(self.min_clock_fraction),
            "power_exponent": float(self.power_exponent),
        }


# ---------------------------------------------------------------------------
# Cooling power
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoolingPowerModel:
    """Electrical power spent removing heat; see the module docstring."""

    kind: str
    pue: float = 1.0
    eta: float = 0.0
    evaporator_approach_k: float = 0.0
    condenser_approach_k: float = 0.0
    cop_min: float = 1.0
    cop_max: float = 1.0

    def __post_init__(self) -> None:
        if self.kind not in ("pue", "carnot"):
            raise ValueError("kind must be 'pue' or 'carnot'")
        if self.kind == "pue":
            _finite(self.pue, "pue", minimum=1.0)
        else:
            _finite(self.eta, "eta", strict=True)
            _finite(self.evaporator_approach_k, "evaporator_approach_k")
            _finite(self.condenser_approach_k, "condenser_approach_k")
            _finite(self.cop_min, "cop_min", strict=True)
            _finite(self.cop_max, "cop_max", strict=True)
            if self.cop_max < self.cop_min:
                raise ValueError("cop_max must be >= cop_min")

    def cop(self, outdoor_c: Any, supply_c: Any) -> np.ndarray:
        out = np.asarray(outdoor_c, dtype=float)
        sup = np.asarray(supply_c, dtype=float)
        if self.kind == "pue":
            return np.broadcast_to(1.0 / max(self.pue - 1.0, 1e-12), np.broadcast(out, sup).shape).copy()
        t_evap = sup - self.evaporator_approach_k + _KELVIN
        t_cond = out + self.condenser_approach_k + _KELVIN
        lift = t_cond - t_evap
        with np.errstate(divide="ignore", invalid="ignore"):
            carnot = np.where(lift > 0.0, t_evap / np.where(lift > 0.0, lift, 1.0), np.inf)
        return np.clip(self.eta * carnot, self.cop_min, self.cop_max)

    def power_w(self, heat_removed_w: Any, outdoor_c: Any, supply_c: Any) -> np.ndarray:
        q = np.asarray(heat_removed_w, dtype=float)
        if self.kind == "pue":
            return (self.pue - 1.0) * q
        return q / self.cop(outdoor_c, supply_c)

    @classmethod
    def carnot_from_pue(
        cls,
        pue: float,
        reference_outdoor_c: float,
        reference_supply_c: float,
        evaporator_approach_k: float,
        condenser_approach_k: float,
        cop_min: float,
        cop_max: float,
    ) -> "CoolingPowerModel":
        """Carnot-fraction model whose overhead equals ``pue - 1`` at the reference."""
        _finite(pue, "pue", minimum=1.0, strict=True)
        if not pue > 1.0:
            raise ValueError("pue must be > 1 to calibrate eta")
        t_evap = reference_supply_c - evaporator_approach_k + _KELVIN
        t_cond = reference_outdoor_c + condenser_approach_k + _KELVIN
        if t_cond <= t_evap:
            raise ValueError("reference condenser temperature must exceed evaporator temperature")
        carnot = t_evap / (t_cond - t_evap)
        eta = (1.0 / (pue - 1.0)) / carnot
        model = cls(
            kind="carnot",
            eta=eta,
            evaporator_approach_k=evaporator_approach_k,
            condenser_approach_k=condenser_approach_k,
            cop_min=cop_min,
            cop_max=cop_max,
        )
        ref_cop = float(model.cop(reference_outdoor_c, reference_supply_c))
        if abs(ref_cop - 1.0 / (pue - 1.0)) > 1e-9 * (1.0 / (pue - 1.0)):
            raise ValueError("cop_min/cop_max clip the reference COP; widen the bounds")
        return model

    def to_dict(self) -> dict[str, Any]:
        if self.kind == "pue":
            return {"kind": "pue", "pue": self.pue}
        return {
            "kind": "carnot",
            "eta": self.eta,
            "evaporator_approach_k": self.evaporator_approach_k,
            "condenser_approach_k": self.condenser_approach_k,
            "cop_min": self.cop_min,
            "cop_max": self.cop_max,
        }


__all__ = [
    "CoolingPowerModel",
    "GPUThrottleModel",
    "RCThermalParams",
    "fit",
    "rc_step",
    "simulate",
    "simulate_full",
    "supply_setpoint",
]
