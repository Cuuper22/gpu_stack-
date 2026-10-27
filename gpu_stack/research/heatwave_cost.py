"""Cost timing for the Heatwave extension (e003): dollars per token against carbon per token.

A share ``f`` of a training cluster's work is flexible.  It can be delayed by up to a window
``W`` hours; the rest runs when it arrives.  Every day the scheduler reads a 48-hour, 21-quantile
forecast of the electricity price and of the grid carbon intensity, turns the two into one cost per
hour, ``lam * price + (1 - lam) * carbon`` (both z-scored with constants fixed before the test
period), and places the flexible work into the cheapest hours that the power cap and the deadlines
allow.  Sweeping ``lam`` from 0 to 1 traces the Pareto curve of electricity cost per token against
carbon per token.

Everything here is a model of a cluster running against REAL PUBLIC price and carbon series (the
series come from ``heatwave.data.public``; ``data_kind`` is "public" for the series and the
workload is a scenario assumption).  Nothing is measured on a real cluster.

Model (all scenario parameters are in ``experiments/e003-heatwave/cost-scenario-v1.json``)
-----------------------------------------------------------------------------------------
* Load is in units of the cluster's full-load power.  The mean offered load is ``rho`` (a scenario
  assumption), so work arrives at ``rho`` full-load hours per hour.  A share ``f`` of it is
  flexible.  The inflexible part, ``rho * (1 - f)``, runs in its arrival hour.
* Total load in any hour is at most ``power_cap`` (a fraction of the full-load power).  Shifted
  work therefore uses capacity that would otherwise sit idle, and every non-energy cost per token
  is unchanged by timing.
* Power is proportional to load and tokens per hour are proportional to load (no throttling, no
  idle power).  Energy per token is a constant taken from ``gpu_stack.calculator.estimate`` for a
  declared reference run, so dollars per token and grams of CO2 per token come out in the
  calculator's own terms: electricity cost per token = calculator energy per token * the
  energy-weighted price paid, carbon per token = the same energy * the energy-weighted carbon
  intensity paid.
* Hardware amortization per token is the calculator's, and it does not depend on timing.  Total
  cost per token = electricity (this module) + hardware (calculator).
* Work arriving in hour ``a`` must finish by the end of hour ``a + W - 1``.  With one window length
  for all work, first-in first-out is earliest-deadline first, and a schedule ``y`` is feasible
  exactly when ``due(t) <= cumulative_run(t) <= arrived(t)`` in every hour ``t`` (``cumulative_run``
  includes work already run).  The daily planning problem is therefore a small linear program.
* Work that the plan leaves beyond the 48-hour horizon is valued at the mean planned cost over the
  horizon (a terminal value), so it is carried to the next day's plan; deadlines inside the horizon
  are hard constraints.

Policies are one scheduler with different cost forecasts: perfect foresight (realised values),
classical forecasts, Timestral zero-shot, plus two policies with no planning problem: no shifting
and a reactive rule (run flexible work when the last observed cost is below its trailing median).

Currency: CAISO prices are USD/MWh, DE-LU prices EUR/MWh.  Electricity cost per token for DE is in
EUR; a reported exchange rate (``usd_per_eur``) converts it when it is added to the calculator's
USD hardware cost.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

HOURS_PER_DAY = 24
QUANTILE_LEVELS: Tuple[float, ...] = (
    0.01, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
    0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99,
)  # same grid as heatwave.forecast.QUANTILE_LEVELS; checked in the tests
DEFAULT_LAMBDAS: Tuple[float, ...] = tuple(round(0.1 * i, 1) for i in range(11))
_TOL = 1e-9


def load_scenario(path: "str | Path") -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


# ---------------------------------------------------------------------------
# Reference run, in the calculator's terms
# ---------------------------------------------------------------------------


def reference_terms(ref: Mapping[str, Any]) -> Dict[str, float]:
    """Energy, tokens and hardware cost of the declared reference run, from ``calculator.estimate``.

    ``ref`` has ``params``, ``tokens``, ``gpu``, ``n_gpus`` and an optional ``overrides`` dict of
    calculator inputs.  Returns the quantities this module needs; each comes from the calculator,
    none is typed in here.
    """
    from gpu_stack.calculator import estimate

    est = estimate(ref["params"], ref["tokens"], gpu=ref["gpu"], n_gpus=ref["n_gpus"], **dict(ref.get("overrides", {})))
    run_hours = est.training_days * 24.0
    mtok = est.tokens / 1e6
    return {
        "params": est.params,
        "tokens": est.tokens,
        "gpu": est.gpu,
        "n_gpus": est.n_gpus,
        "training_days": est.training_days,
        "gpu_hours": est.gpu_hours,
        "energy_mwh": est.energy_mwh,
        "facility_power_mw": est.energy_mwh / run_hours,
        "facility_power_w_per_gpu": est.energy_mwh * 1e6 / est.gpu_hours,
        "tokens_per_hour": est.tokens / run_hours,
        "tokens_per_gpu_hour": est.tokens / est.gpu_hours,
        "energy_mwh_per_mtoken": est.energy_mwh / mtok,
        "hardware_cost_usd": est.hardware_cost,
        "hardware_usd_per_mtoken": est.hardware_cost / mtok,
        "calculator_default_electricity_cost_usd": est.electricity_cost,
        "calculator_default_electricity_price_usd_per_kwh": est.inputs["electricity_price"],
        "calculator_default_cost_per_mtoken_usd": est.cost_per_million_tokens,
    }


# ---------------------------------------------------------------------------
# Workload model and the daily planning problem
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FlexModel:
    """Offered load ``rho``, flexible share ``f``, window ``window_hours`` and total-load cap ``power_cap``."""

    utilization: float
    flexible_fraction: float
    window_hours: int
    power_cap: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 < self.utilization <= self.power_cap:
            raise ValueError("need 0 < utilization <= power_cap")
        if not 0.0 <= self.flexible_fraction <= 1.0:
            raise ValueError("flexible_fraction must be in [0, 1]")
        if self.window_hours < 1:
            raise ValueError("window_hours must be at least 1")

    @property
    def inflexible_load(self) -> float:
        return self.utilization * (1.0 - self.flexible_fraction)

    @property
    def flexible_rate(self) -> float:
        """Flexible work arriving per hour, in full-load hours."""
        return self.utilization * self.flexible_fraction

    @property
    def flexible_cap(self) -> float:
        """Most flexible work that can run in one hour (total-load cap minus the inflexible load)."""
        return self.power_cap - self.inflexible_load

    def arrived(self, t: np.ndarray) -> np.ndarray:
        """Flexible work that has arrived by the end of hour ``t`` (hour 0 is the start of the run)."""
        return self.flexible_rate * (np.asarray(t, dtype=np.float64) + 1.0)

    def due(self, t: np.ndarray) -> np.ndarray:
        """Flexible work whose deadline is the end of hour ``t`` or earlier."""
        return self.flexible_rate * np.maximum(0.0, np.asarray(t, dtype=np.float64) - self.window_hours + 2.0)


_TRI: Dict[int, np.ndarray] = {}


def _tri(h: int) -> np.ndarray:
    m = _TRI.get(h)
    if m is None:
        m = np.tril(np.ones((h, h)))
        _TRI[h] = m
    return m


def plan_flexible(cost: np.ndarray, model: FlexModel, t0: int, run_before: float, terminal_cost: Optional[float] = None) -> Tuple[np.ndarray, bool]:
    """Plan the flexible work of the next ``len(cost)`` hours.

    ``cost[h]`` is the planned cost of one full-load hour of flexible work in hour ``t0 + h``;
    ``run_before`` is the flexible work already run before hour ``t0``.  Minimises
    ``sum_h (cost[h] - terminal_cost) * y[h]`` subject to ``0 <= y[h] <= flexible_cap`` and
    ``due(t) <= run_before + cumsum(y)(t) <= arrived(t)`` (``terminal_cost`` defaults to the mean
    planned cost).  Returns ``(y, fell_back)``; ``fell_back`` is True if the linear program was not
    solved, in which case the plan runs the work as soon as it arrives.
    """
    from scipy.optimize import linprog

    cost = np.asarray(cost, dtype=np.float64)
    h = cost.size
    t = np.arange(t0, t0 + h)
    hi = model.arrived(t) - run_before
    lo = model.due(t) - run_before
    ref = float(np.mean(cost)) if terminal_cost is None else float(terminal_cost)
    tri = _tri(h)
    res = linprog(
        cost - ref,
        A_ub=np.vstack([tri, -tri]),
        b_ub=np.concatenate([hi + _TOL, -(lo - _TOL)]),
        bounds=(0.0, model.flexible_cap),
        method="highs",
    )
    if res.status != 0:
        return _asap_plan(model, t0, h, run_before), True
    return np.clip(res.x, 0.0, model.flexible_cap), False


def _asap_plan(model: FlexModel, t0: int, h: int, run_before: float) -> np.ndarray:
    y = np.zeros(h)
    done = run_before
    for k in range(h):
        pending = model.arrived(t0 + k) - done
        y[k] = min(model.flexible_cap, max(0.0, pending))
        done += y[k]
    return y


def schedule_forecast(
    cost_by_day: np.ndarray,
    model: FlexModel,
    day_blocks: Sequence[Tuple[int, int]],
) -> Tuple[np.ndarray, Dict[str, float]]:
    """Run the daily rolling plan over blocks of days.

    ``cost_by_day`` is (n_days_total, H): row ``d`` is the planned cost of the H hours that start
    at the daily decision time of day ``d``.  ``day_blocks`` is a list of ``(first_day, n_days)``;
    the backlog is empty at the start of every block.  Only the first 24 hours of each plan are
    run.  Returns the flexible work run in every hour of the blocks (concatenated in block order)
    and diagnostics.
    """
    out: List[np.ndarray] = []
    fallbacks = 0
    for first, n in day_blocks:
        run_before = 0.0
        t_rel = 0
        for k in range(n):
            y, fb = plan_flexible(cost_by_day[first + k], model, t_rel, run_before)
            fallbacks += int(fb)
            y24 = y[:HOURS_PER_DAY]
            out.append(y24)
            run_before += float(y24.sum())
            t_rel += HOURS_PER_DAY
    y_all = np.concatenate(out) if out else np.zeros(0)
    return y_all, {"plan_fallbacks": float(fallbacks)}


def offline_optimum(cost: np.ndarray, model: FlexModel) -> np.ndarray:
    """Whole-period optimum with every cost known: one linear program over all hours.

    Minimises ``sum_t (cost[t] - mean(cost)) * y[t]`` with the same constraints as the daily plan,
    using the cumulative flexible work ``Y[t]`` as the variable (sparse bidiagonal rows).  This is
    the tightest bound for the mixed cost; the perfect-foresight policy (the daily scheduler fed
    realised values) can differ from it because it plans 48 hours at a time.
    """
    import scipy.sparse as sp
    from scipy.optimize import linprog

    cost = np.asarray(cost, dtype=np.float64)
    n = cost.size
    t = np.arange(n)
    c_adj = cost - cost.mean()
    nxt = np.append(c_adj[1:], 0.0)
    obj = c_adj - nxt  # coefficient of Y[t] in sum_t c_adj[t] * (Y[t] - Y[t-1]) with Y[-1] = 0
    diff = sp.diags([np.ones(n), -np.ones(n - 1)], [0, -1], format="csr")  # (Y[t] - Y[t-1])
    a_ub = sp.vstack([diff, -diff], format="csr")
    b_ub = np.concatenate([np.full(n, model.flexible_cap), np.zeros(n)])
    lo = model.due(t) - _TOL
    hi = model.arrived(t) + _TOL
    res = linprog(obj, A_ub=a_ub, b_ub=b_ub, bounds=list(zip(lo, hi)), method="highs")
    if res.status != 0:
        raise RuntimeError(f"offline optimum not solved: {res.message}")
    y = np.diff(res.x, prepend=0.0)
    return np.clip(y, 0.0, model.flexible_cap)


def schedule_none(model: FlexModel, n_hours: int) -> np.ndarray:
    """No shifting: flexible work runs in its arrival hour."""
    return np.full(n_hours, model.flexible_rate)


def trailing_median(x: np.ndarray, window: int) -> np.ndarray:
    """``out[i]`` is the median of ``x[i - window + 1 : i + 1]`` (NaN for ``i < window - 1``)."""
    x = np.asarray(x, dtype=np.float64)
    out = np.full(x.size, np.nan)
    if x.size >= window:
        out[window - 1:] = np.median(np.lib.stride_tricks.sliding_window_view(x, window), axis=1)
    return out


def schedule_reactive(
    cost_hist: np.ndarray,
    model: FlexModel,
    day_blocks: Sequence[Tuple[int, int]],
    lookback: int = 168,
) -> np.ndarray:
    """Reactive rule without a forecast.

    ``cost_hist`` is the observed cost of every hour of the full series (history plus test) and
    ``day_blocks`` holds ``(first_hour_index, n_days)`` pairs in that array's hour numbering; the
    backlog starts empty at each block.  In hour ``i`` the rule compares the last observed cost
    (hour ``i - 1``) with the median of the ``lookback`` observed hours that end with it.  If the
    last cost is at or below that median it runs all pending flexible work up to the cap, otherwise
    only the work that is due this hour.
    """
    med = trailing_median(cost_hist, lookback)
    out: List[np.ndarray] = []
    cap = model.flexible_cap
    rate = model.flexible_rate
    win = model.window_hours
    for first_hour, n_days in day_blocks:
        n = n_days * HOURS_PER_DAY
        y = np.zeros(n)
        run = 0.0
        for k in range(n):
            i = first_hour + k
            arrived = rate * (k + 1.0)
            pending = arrived - run
            if cost_hist[i - 1] <= med[i - 1]:
                want = pending
            else:
                want = rate * max(0.0, k - win + 2.0) - run
            v = min(cap, max(0.0, want))
            y[k] = v
            run += v
        out.append(y)
    return np.concatenate(out) if out else np.zeros(0)


# ---------------------------------------------------------------------------
# Cost, accounting and uncertainty
# ---------------------------------------------------------------------------


def zscore_constants(price: np.ndarray, carbon: np.ndarray) -> Dict[str, float]:
    """Mean and standard deviation of the training-window price and carbon (fixed before the test period)."""
    return {
        "price_mean": float(np.mean(price)), "price_std": float(np.std(price)),
        "carbon_mean": float(np.mean(carbon)), "carbon_std": float(np.std(carbon)),
    }


def mixed_cost(price: np.ndarray, carbon: np.ndarray, lam: float, norm: Mapping[str, float]) -> np.ndarray:
    """``lam * z(price) + (1 - lam) * z(carbon)`` with the fixed training-window constants."""
    return lam * (np.asarray(price) - norm["price_mean"]) / norm["price_std"] + (1.0 - lam) * (np.asarray(carbon) - norm["carbon_mean"]) / norm["carbon_std"]


def daily_sums(y: np.ndarray, model: FlexModel, price: np.ndarray, carbon: np.ndarray) -> np.ndarray:
    """Per-day sums of load, load * price and load * carbon.  Returns an array of shape (n_days, 3).

    ``y`` is the flexible work run in each hour (blocks concatenated), ``price`` and ``carbon`` are
    the realised series over the same hours.  Load in an hour is the inflexible load plus ``y``.
    """
    load = model.inflexible_load + np.asarray(y, dtype=np.float64)
    n_days = load.size // HOURS_PER_DAY
    l2 = load.reshape(n_days, HOURS_PER_DAY)
    p2 = np.asarray(price, dtype=np.float64).reshape(n_days, HOURS_PER_DAY)
    c2 = np.asarray(carbon, dtype=np.float64).reshape(n_days, HOURS_PER_DAY)
    return np.stack([l2.sum(axis=1), (l2 * p2).sum(axis=1), (l2 * c2).sum(axis=1)], axis=1)


def flexible_daily_sums(y: np.ndarray, price: np.ndarray, carbon: np.ndarray) -> np.ndarray:
    """Per-day sums of flexible work, flexible * price and flexible * carbon, shape (n_days, 3)."""
    y = np.asarray(y, dtype=np.float64)
    n_days = y.size // HOURS_PER_DAY
    y2 = y.reshape(n_days, HOURS_PER_DAY)
    p2 = np.asarray(price, dtype=np.float64).reshape(n_days, HOURS_PER_DAY)
    c2 = np.asarray(carbon, dtype=np.float64).reshape(n_days, HOURS_PER_DAY)
    return np.stack([y2.sum(axis=1), (y2 * p2).sum(axis=1), (y2 * c2).sum(axis=1)], axis=1)


def effective_prices(sums: np.ndarray, idx: Optional[np.ndarray] = None) -> Tuple[Any, Any]:
    """Energy-weighted price and carbon intensity from daily sums (optionally under bootstrap indices).

    ``sums`` is (n_days, 3).  ``idx`` is None, an index vector, or a (n_boot, n) index matrix; the
    return values then have shape (), or (n_boot,).
    """
    if idx is None:
        s = sums.sum(axis=0)
        return s[1] / s[0], s[2] / s[0]
    g = sums[idx]
    s = g.sum(axis=-2)
    return s[..., 1] / s[..., 0], s[..., 2] / s[..., 0]


def block_bootstrap_indices(n_days: int, n_boot: int, block_days: int, seed: int) -> np.ndarray:
    """Circular moving-block bootstrap indices, shape (n_boot, n_days).  ``block_days=1`` is the iid day bootstrap."""
    rng = np.random.default_rng(seed)
    n_blocks = int(math.ceil(n_days / block_days))
    starts = rng.integers(0, n_days, size=(n_boot, n_blocks))
    idx = (starts[:, :, None] + np.arange(block_days)[None, None, :]) % n_days
    return idx.reshape(n_boot, -1)[:, :n_days]


def percentile_interval(x: np.ndarray, level: float = 0.95) -> Tuple[float, float]:
    a = (1.0 - level) / 2.0
    lo, hi = np.nanquantile(x, [a, 1.0 - a])
    return float(lo), float(hi)


# ---------------------------------------------------------------------------
# Per-token numbers in the calculator's terms
# ---------------------------------------------------------------------------


def per_mtoken(price_paid: Any, carbon_paid: Any, terms: Mapping[str, float], usd_per_price_unit: float = 1.0) -> Dict[str, Any]:
    """Electricity cost, total cost and carbon per million tokens.

    ``price_paid`` in price units per MWh, ``carbon_paid`` in g/kWh.  ``usd_per_price_unit`` is 1.0
    for USD prices and the exchange rate for EUR prices.  Carbon: energy per Mtoken in MWh times
    1000 kWh/MWh times g/kWh gives grams per Mtoken.
    """
    e = terms["energy_mwh_per_mtoken"]
    elec = e * price_paid * usd_per_price_unit
    return {
        "electricity_per_mtoken": e * price_paid,
        "electricity_usd_per_mtoken": elec,
        "total_usd_per_mtoken": elec + terms["hardware_usd_per_mtoken"],
        "co2_g_per_mtoken": e * carbon_paid * 1000.0,
    }


# ---------------------------------------------------------------------------
# Public series, rolling forecasts and their cache (needs the heatwave package)
# ---------------------------------------------------------------------------

PAIR_SOURCES: Dict[str, Dict[str, Any]] = {
    # price: (region, market, column, currency); carbon: (region, kwargs)
    "caiso": {"price": ("caiso", "dam", "lmp_usd_per_mwh", "USD"), "carbon": ("caiso", {"basis": "in_state"})},
    "de": {"price": ("de", "dam", "price_eur_per_mwh", "EUR"), "carbon": ("de", {})},
}


def fill_hourly(x: "Any", period: int = 24, max_weeks: int = 3) -> Tuple[np.ndarray, int]:
    """Fill NaN hours with the mean of the same hour of day on neighbouring days, else by interpolation.

    Returns ``(filled array, number of hours filled)``.  Used for the few hours that a source did not publish.
    """
    v = np.asarray(x, dtype=np.float64).copy()
    miss = np.flatnonzero(np.isnan(v))
    if miss.size == 0:
        return v, 0
    src = v.copy()
    for i in miss:
        vals = []
        for k in range(1, max_weeks * 7 + 1):
            for j in (i - k * period, i + k * period):
                if 0 <= j < v.size and not np.isnan(src[j]):
                    vals.append(src[j])
            if len(vals) >= 4:
                break
        if vals:
            v[i] = float(np.mean(vals))
    still = np.isnan(v)
    if still.any():
        idx = np.arange(v.size)
        v[still] = np.interp(idx[still], idx[~still], v[~still])
    return v, int(miss.size)


def load_hourly_pair(pair: str) -> Dict[str, Any]:
    """Hourly UTC price and carbon intensity of one same-region pair, from ``heatwave.data.public``.

    Returns ``{"index": DatetimeIndex, "price": ndarray, "carbon": ndarray, "meta": {...}}`` on the
    common hourly index.  Hours a source did not publish are filled with :func:`fill_hourly` and
    counted in ``meta``.
    """
    import pandas as pd
    from heatwave.data import public as P

    src = PAIR_SOURCES[pair]
    region, market, column, currency = src["price"]
    price = P.load_price(region, market)[column].resample("1h").mean()
    cregion, ckw = src["carbon"]
    carbon = P.load_carbon(cregion, **ckw)["intensity_g_per_kwh"].resample("1h").mean()
    start = max(price.index.min(), carbon.index.min())
    end = min(price.index.max(), carbon.index.max())
    idx = pd.date_range(start, end, freq="1h", tz="UTC")
    p, n_p = fill_hourly(price.reindex(idx).to_numpy())
    c, n_c = fill_hourly(carbon.reindex(idx).to_numpy())
    return {
        "index": idx, "price": p, "carbon": c,
        "meta": {
            "pair": pair, "price_source": f"{region}/{market}/{column}", "price_unit": f"{currency}/MWh", "currency": currency,
            "carbon_source": f"{cregion} {ckw}", "carbon_unit": "gCO2/kWh",
            "hours_total": int(len(idx)), "price_hours_filled": n_p, "carbon_hours_filled": n_c,
            "first_hour_utc": str(idx[0]), "last_hour_utc": str(idx[-1]),
        },
    }


def make_forecaster(spec: Mapping[str, Any]) -> Any:
    """Build a ``heatwave.forecast`` forecaster from a scenario spec ``{"kind": ..., ...}``."""
    kind = spec["kind"]
    if kind == "seasonal_naive":
        from heatwave.forecast import SeasonalNaiveForecaster
        return SeasonalNaiveForecaster(spec["season_length"], max_context=spec.get("max_context"))
    if kind == "ets":
        from heatwave.forecast import ETSForecaster
        return ETSForecaster(spec["season_length"], max_context=spec.get("max_context", 2048))
    if kind == "arima":
        from heatwave.forecast import ARIMAForecaster
        return ARIMAForecaster(tuple(spec["order"]), season_length=spec.get("season_length", 1),
                               seasonal_order=tuple(spec.get("seasonal_order", (0, 0, 0))), max_context=spec.get("max_context", 1024))
    if kind == "timestral":
        from heatwave.forecast.timestral_fc import TimestralForecaster
        return TimestralForecaster(size=spec["size"], threads=spec.get("threads", 1))
    raise ValueError(f"unknown forecaster kind {kind!r}")


def forecast_windows(values: np.ndarray, t0: Sequence[int], context_len: int, horizon: int) -> Tuple[np.ndarray, np.ndarray]:
    """Context windows (n, 1, context_len) before each ``t0`` and the realised future (n, horizon).

    Future hours past the end of the series are NaN.
    """
    ctx = np.stack([values[t - context_len:t] for t in t0])[:, None, :]
    fut = np.full((len(t0), horizon), np.nan)
    for k, t in enumerate(t0):
        seg = values[t:t + horizon]
        fut[k, :seg.size] = seg
    return ctx, fut


def known_covariate_matrix(pair: str, index: Any, include_weather: bool = True) -> Dict[str, Any]:
    """Day-ahead covariates that are known over the forecast horizon, on the hourly ``index``.

    CAISO: the day-ahead demand forecast.  DE-LU: day-ahead load, solar and wind forecasts.  Weather
    forecasts (Open-Meteo, day-ahead vintage) are added when they have been collected; if the file
    is absent the status says so and the matrix is built without them.  The archived forecasts hold
    one value per hour; their issue time relative to a 00:00 UTC decision is not verified for the
    hours beyond the first day.
    """
    from heatwave.data import public as P

    region = PAIR_SOURCES[pair]["price"][0]
    cov = P.load_forecast_covariates(region).resample("1h").mean().reindex(index)
    names = list(cov.columns)
    cols = [cov[c].to_numpy() for c in names]
    status = {"weather_forecast": "not requested"}
    if include_weather:
        wregion = {"caiso": "bayarea", "de": "frankfurt"}[region]
        try:
            w = P.load_weather(wregion, kind="forecast", vintage="dayahead").resample("1h").mean().reindex(index)
            for c in w.columns:
                names.append("weather_" + c)
                cols.append(w[c].to_numpy())
            status = {"weather_forecast": "included", "weather_columns": list(w.columns)}
        except FileNotFoundError:
            status = {"weather_forecast": "not collected (Open-Meteo quota); the path is built and skipped"}
    return {"matrix": np.stack(cols).astype(np.float64), "names": names, "status": status}


def covariate_windows(known: np.ndarray, t0: Sequence[int], context_len: int, horizon: int) -> np.ndarray:
    """Known-covariate windows (n, C, context_len + horizon); hours past the end of the series are NaN."""
    out = np.full((len(t0), known.shape[0], context_len + horizon), np.nan)
    for k, t in enumerate(t0):
        seg = known[:, t - context_len:t + horizon]
        out[k, :, :seg.shape[1]] = seg
    return out


def rolling_forecast(values: np.ndarray, t0: Sequence[int], forecaster: Any, context_len: int, horizon: int, batch: int = 4,
                     known: Optional[np.ndarray] = None) -> np.ndarray:
    """Forecast ``horizon`` hours at every ``t0`` from the ``context_len`` hours before it.  Returns (n, horizon, 21).

    Only values before ``t0`` enter a forecast.  ``known`` is an optional (C, N) matrix of
    covariates known in advance, aligned with ``values``; their values over the horizon are passed to the forecaster.
    """
    out = []
    for k in range(0, len(t0), batch):
        chunk = list(t0[k:k + batch])
        ctx, _ = forecast_windows(values, chunk, context_len, horizon)
        if known is None:
            q = forecaster.forecast(ctx, horizon)
        else:
            q = forecaster.forecast(ctx, horizon, known_covariates=covariate_windows(known, chunk, context_len, horizon))
        out.append(q.values[:, 0])
    return np.concatenate(out, axis=0)


def week_cache_path(cache_dir: "str | Path", series_key: str, forecaster_key: str, week: int) -> Path:
    return Path(cache_dir) / f"{series_key}__{forecaster_key}__w{week:02d}.npz"


def compute_week(values: np.ndarray, test_start: int, week: int, forecaster: Any, context_len: int, horizon: int, batch: int = 4,
                 known: Optional[np.ndarray] = None) -> np.ndarray:
    """Forecasts for the 7 daily decision times (00:00 UTC) of one test week.  Returns (7, horizon, 21), float32."""
    t0 = [test_start + (7 * week + d) * HOURS_PER_DAY for d in range(7)]
    return rolling_forecast(values, t0, forecaster, context_len, horizon, batch, known).astype(np.float32)


def quantile_index(q: float) -> int:
    for j, lv in enumerate(QUANTILE_LEVELS):
        if abs(lv - q) < 1e-9:
            return j
    raise ValueError(f"planning quantile {q} is not on the 21-level grid")


def padded_future(values: np.ndarray, t0: Sequence[int], horizon: int) -> np.ndarray:
    """Realised values for ``horizon`` hours after each ``t0``.

    Hours past the end of the series copy the same hour one day earlier (only the last decision
    days need this, and only for the perfect-foresight look-ahead beyond 24 hours).
    """
    out = np.empty((len(t0), horizon))
    n = len(values)
    for k, t in enumerate(t0):
        for h in range(horizon):
            j = t + h
            while j >= n:
                j -= HOURS_PER_DAY
            out[k, h] = values[j]
    return out


def block_hour_indices(blocks_days: Sequence[Tuple[int, int]], test_start: int) -> np.ndarray:
    """Hour indices (into the full series) of the test hours that belong to the blocks, in order."""
    return np.concatenate([test_start + np.arange(first * HOURS_PER_DAY, (first + n) * HOURS_PER_DAY) for first, n in blocks_days])


def sweep_forecast_policy(
    price_q: np.ndarray,
    carbon_q: np.ndarray,
    lambdas: Sequence[float],
    model: FlexModel,
    norm: Mapping[str, float],
    blocks_days: Sequence[Tuple[int, int]],
    price_real: np.ndarray,
    carbon_real: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, int]:
    """Run one forecast policy for every ``lam``.

    ``price_q`` and ``carbon_q`` are (n_days_total, H) planned values.  ``price_real`` and
    ``carbon_real`` are the realised series over the blocks' hours.  Returns daily sums of load,
    load*price and load*carbon, shape (n_lam, n_block_days, 3), the flexible-work daily sums with
    the same layout, and the number of plans that fell back to run-on-arrival.
    """
    sums, flex, fb = [], [], 0
    for lam in lambdas:
        y, diag = schedule_forecast(mixed_cost(price_q, carbon_q, lam, norm), model, blocks_days)
        sums.append(daily_sums(y, model, price_real, carbon_real))
        flex.append(flexible_daily_sums(y, price_real, carbon_real))
        fb += int(diag["plan_fallbacks"])
    return np.stack(sums), np.stack(flex), fb


def sweep_reactive(
    price_full: np.ndarray,
    carbon_full: np.ndarray,
    lambdas: Sequence[float],
    model: FlexModel,
    norm: Mapping[str, float],
    blocks_days: Sequence[Tuple[int, int]],
    test_start: int,
    price_real: np.ndarray,
    carbon_real: np.ndarray,
    lookback: int = 168,
) -> Tuple[np.ndarray, np.ndarray]:
    sums, flex = [], []
    blocks_hours = [(test_start + first * HOURS_PER_DAY, n) for first, n in blocks_days]
    for lam in lambdas:
        cost = mixed_cost(price_full, carbon_full, lam, norm)
        y = schedule_reactive(cost, model, blocks_hours, lookback)
        sums.append(daily_sums(y, model, price_real, carbon_real))
        flex.append(flexible_daily_sums(y, price_real, carbon_real))
    return np.stack(sums), np.stack(flex)


def sweep_none(model: FlexModel, n_lambdas: int, price_real: np.ndarray, carbon_real: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    y = schedule_none(model, price_real.size)
    s = daily_sums(y, model, price_real, carbon_real)
    f = flexible_daily_sums(y, price_real, carbon_real)
    return np.repeat(s[None], n_lambdas, axis=0), np.repeat(f[None], n_lambdas, axis=0)


# ---------------------------------------------------------------------------
# Feeding the result back to the calculator
# ---------------------------------------------------------------------------


def curve_key(policy: str, flexible_fraction: float, window_hours: int, utilization: float, plan_quantile: Optional[float]) -> str:
    q = "na" if plan_quantile is None else f"{plan_quantile:g}"
    return f"{policy}|f={flexible_fraction:g}|W={window_hours}|rho={utilization:g}|q={q}"


def lookup_curve(result_doc: Mapping[str, Any], pair: str, policy: str, flexible_fraction: float, window_hours: int,
                 utilization: Optional[float] = None, plan_quantile: Optional[float] = 0.5, subsample: bool = False) -> Mapping[str, Any]:
    """Pick one Pareto curve out of the result JSON written by ``run_cost.py`` (the whole document or its ``result`` part)."""
    res = result_doc.get("result", result_doc)
    if utilization is None:
        utilization = res["scenario"]["workload"]["utilization"]
    q = None if policy in ("no_shift", "reactive") else plan_quantile
    block = res["pairs"][pair]["curves_subsample" if subsample else "curves"]
    return block[curve_key(policy, flexible_fraction, window_hours, utilization, q)]


def interpolate_in_lambda(curve: Mapping[str, Any], field: str, lam: float) -> float:
    """Linear interpolation of a per-lambda field of a curve at ``lam`` in [0, 1]."""
    return float(np.interp(lam, curve["lambda"], curve[field]))


def timing_inputs(curve: Mapping[str, Any], lam: float, usd_per_price_unit: float = 1.0) -> Dict[str, float]:
    """Effective electricity price and carbon intensity for one flexible fraction, window, policy and ``lam``.

    The names match the calculator and the ``power_forecast`` shift scope:

    * ``electricity_price``: USD per kWh, the energy-weighted price paid after shifting.  Pass it to
      ``gpu_stack.calculator.estimate(..., electricity_price=...)``.
    * ``price_shifted`` (USD/kWh) and ``carbon_intensity_shifted`` (kg/kWh): averages over the hours
      the flexible work ran in (scope inputs ``forecast.shift.price_shifted`` and
      ``forecast.shift.carbon_intensity_shifted``), with ``flexible_fraction`` as the scope's
      ``forecast.shift.flexible_fraction``.
    * ``price_unshifted`` and ``carbon_intensity_unshifted``: the no-shift averages.
    * ``carbon_intensity_paid`` (kg/kWh): the energy-weighted intensity paid after shifting.
    """
    f = float(curve["flexible_fraction"])
    out = {
        "electricity_price": interpolate_in_lambda(curve, "price_paid", lam) / 1000.0 * usd_per_price_unit,
        "price_shifted": interpolate_in_lambda(curve, "price_shifted", lam) / 1000.0 * usd_per_price_unit,
        "price_unshifted": float(curve["price_unshifted"]) / 1000.0 * usd_per_price_unit,
        "carbon_intensity_paid": interpolate_in_lambda(curve, "carbon_paid", lam) / 1000.0,
        "carbon_intensity_shifted": interpolate_in_lambda(curve, "carbon_shifted", lam) / 1000.0,
        "carbon_intensity_unshifted": float(curve["carbon_unshifted"]) / 1000.0,
        "flexible_fraction": f,
        "flexible_energy_share": interpolate_in_lambda(curve, "flexible_energy_share", lam),
    }
    return out


def estimate_with_timing(ref: Mapping[str, Any], curve: Mapping[str, Any], lam: float, usd_per_price_unit: float = 1.0) -> Tuple[Any, float, Dict[str, float]]:
    """Run the calculator on the reference run with the timed electricity price.

    Returns ``(Estimate, carbon_kg, timing_inputs)``.  ``carbon_kg`` is the calculator's energy in
    MWh times the carbon intensity paid in g/kWh (1 MWh = 1000 kWh, 1 kg = 1000 g).
    """
    from gpu_stack.calculator import estimate

    ti = timing_inputs(curve, lam, usd_per_price_unit)
    est = estimate(ref["params"], ref["tokens"], gpu=ref["gpu"], n_gpus=ref["n_gpus"],
                   electricity_price=ti["electricity_price"], **dict(ref.get("overrides", {})))
    carbon_kg = est.energy_mwh * ti["carbon_intensity_paid"] * 1000.0
    return est, carbon_kg, ti


def sweep_offline(price_real: np.ndarray, carbon_real: np.ndarray, lambdas: Sequence[float], model: FlexModel,
                  norm: Mapping[str, float]) -> Tuple[np.ndarray, np.ndarray]:
    """Whole-period optimum for every ``lam`` (one block); daily sums as in :func:`sweep_forecast_policy`."""
    sums, flex = [], []
    for lam in lambdas:
        y = offline_optimum(mixed_cost(price_real, carbon_real, lam, norm), model)
        sums.append(daily_sums(y, model, price_real, carbon_real))
        flex.append(flexible_daily_sums(y, price_real, carbon_real))
    return np.stack(sums), np.stack(flex)
