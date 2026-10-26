"""Forecast-driven outage response for the e003 Heatwave simulator (all simulated).

Everything in this module acts on, or scores, the SIMULATED two-site cluster of
:mod:`gpu_stack.research.heatwave_sim`.  Event rates, precursors, lead times and
severities are simulation assumptions; nothing here is a claim about a real
facility.

Decision loop
-------------
Every decision interval a controller

1. reads the visible telemetry (never the ground-truth event list),
2. appends one sample per monitored series (see ``Channels``),
3. forecasts every series with 21 quantiles over the warning horizon using any
   :class:`heatwave.forecast.Forecaster` (Timestral, seasonal naive, ETS, ARIMA,
   a persistence reference, or a fine-tuned Timestral through ``weights_dir``),
4. converts the quantiles into the probability that the series crosses its
   trouble level within the horizon,
5. raises a warning for a series when that probability reaches a threshold, and
6. responds: checkpoint the affected jobs immediately, move flexible jobs to the
   other site if it has free GPUs (the simulator's ``MigrateJob`` checkpoints
   first), otherwise pause them after the checkpoint, and resume when the
   warning clears.

Monitored series (``Channels``)
-------------------------------
``gpu_temp_max`` (rack, class ``thermal``)
    Hottest GPU of the rack.  Trouble level: the simulator's throttle threshold
    (read from the scenario).
``supply_anom`` (rack, class ``cooling``)
    Supply air temperature minus the supply setpoint implied by the outdoor
    forecast.  Carries the cooling-failure supply-temperature precursor.
    Trouble level: a high quantile of the same channel in event-free runs on
    training seeds (:func:`calibrate`).
``breaker_ratio`` (rack, class ``power``)
    Rack IT power divided by the effective breaker rating (the derate precursor
    shows up here).  Trouble level: 1.0, rack power above the rating.
``gpu_anom`` (rack, class ``hardware``)
    Largest per-GPU temperature rise of the rack relative to the GPU's own slow
    baseline and its peers in the same job.  Carries the hardware-fault
    temperature precursor.  Level: calibrated like ``supply_anom``.
``site_power`` (site, class ``curtail``)
    Site power against the grid import limit, including curtailments announced
    in the known-future schedule.

Information boundary
--------------------
Controllers see the simulator's :class:`VisibleState`.  Two scheduler-side
facts are added through :class:`PlacementView`: which job holds which GPUs.
That is operational state of any scheduler, not event ground truth.  The oracle
policy (perfect foresight, an upper bound) is the only one that reads event
times, and it says so in its name.

Simulator note
--------------
At simulator commit b6adcfa the per-GPU temperature offsets of the hardware
fault precursor are applied inside the simulator's thermal step but not to the
visible per-GPU temperature, so that precursor is invisible to every
controller.  :class:`OutageRun` adds the offsets to the visible state (and
skips the addition if the simulator already exposes them).  The request to fix
this upstream is in the experiment report.

Scoring
-------
:func:`score_run` turns one simulator result plus the controller export into
per-event outcomes (lead time, work lost in steps and GPU-hours, curtailment
violation energy, throttle slowdown), warning-alarm outcomes (true or false
alarm, response cost in GPU-hours) and response costs.  Aggregation with seed
bootstrap intervals is in :func:`aggregate_runs`.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import warnings
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

import numpy as np

from .heatwave_events import (
    KIND_BREAKER_TRIP,
    KIND_COOLING_FAILURE,
    KIND_GRID_CURTAILMENT,
    KIND_HARDWARE_FAULT,
    KIND_THERMAL_THROTTLE,
    EventSchedule,
    random_schedule,
)
from .heatwave_sim import (
    CheckpointNow,
    MigrateJob,
    NullController,
    PauseJob,
    ResumeJob,
    SimConfig,
    SimResult,
    VisibleState,
    _Run,
    build_config,
    load_scenario,
)

SCHEMA = "gpu-stack.e003-heatwave-outage-scenario.v1"
RESULT_SCHEMA = "gpu-stack.e003-heatwave-outage-result.v1"

CLASS_THERMAL = "thermal"
CLASS_COOLING = "cooling"
CLASS_POWER = "power"
CLASS_HARDWARE = "hardware"
CLASS_CURTAIL = "curtail"
CLASSES = (CLASS_THERMAL, CLASS_COOLING, CLASS_POWER, CLASS_HARDWARE, CLASS_CURTAIL)

CH_GPU_TEMP = "gpu_temp_max"
CH_SUPPLY = "supply_anom"
CH_BREAKER = "breaker_ratio"
CH_GPU_ANOM = "gpu_anom"
CH_SITE_POWER = "site_power"
RACK_CHANNELS = (CH_GPU_TEMP, CH_SUPPLY, CH_BREAKER, CH_GPU_ANOM)
SITE_CHANNELS = (CH_SITE_POWER,)
CHANNEL_CLASS = {
    CH_GPU_TEMP: CLASS_THERMAL,
    CH_SUPPLY: CLASS_COOLING,
    CH_BREAKER: CLASS_POWER,
    CH_GPU_ANOM: CLASS_HARDWARE,
    CH_SITE_POWER: CLASS_CURTAIL,
}

# Which warning classes may explain which kind of event.
EVENT_CLASSES = {
    KIND_COOLING_FAILURE: (CLASS_THERMAL, CLASS_COOLING),
    KIND_BREAKER_TRIP: (CLASS_POWER,),
    KIND_GRID_CURTAILMENT: (CLASS_CURTAIL,),
    KIND_HARDWARE_FAULT: (CLASS_HARDWARE,),
    KIND_THERMAL_THROTTLE: (CLASS_THERMAL, CLASS_COOLING),
}
EVENT_TYPES = (KIND_THERMAL_THROTTLE, KIND_COOLING_FAILURE, KIND_BREAKER_TRIP, KIND_GRID_CURTAILMENT, KIND_HARDWARE_FAULT)

MIN_VALID_SAMPLES = 12
MIN_BASELINE_SAMPLES = 6

# ---------------------------------------------------------------------------
# validation helpers
# ---------------------------------------------------------------------------


def _num(value: Any, name: str, *, minimum: float = 0.0, strict: bool = False, maximum: float = math.inf) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{name} must be a real number")
    v = float(value)
    if not math.isfinite(v):
        raise ValueError(f"{name} must be finite")
    if (strict and not v > minimum) or (not strict and v < minimum):
        raise ValueError(f"{name} must be {'>' if strict else '>='} {minimum}")
    if v > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return v


def _int(value: Any, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or int(value) < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(value)


# ---------------------------------------------------------------------------
# settings and scenario handling
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OutageSettings:
    """Response-policy and evaluation settings (all simulation assumptions)."""

    decision_interval_s: float
    warmup_s: float
    context_steps: int
    horizon_steps: int
    clear_decisions: int
    recheckpoint_s: float
    max_pause_s: float
    calibration_quantile: float
    anomaly_baseline_window_s: float
    anomaly_baseline_gap_s: float
    anomaly_smooth_steps: int
    curtail_shed_margin: float
    oracle_extra_lead_steps: int
    episode_merge_gap_s: float
    threshold_grid: tuple[float, ...]
    observed_threshold: float
    bootstrap_resamples: int

    def __post_init__(self) -> None:
        _num(self.decision_interval_s, "decision_interval_s", strict=True)
        _num(self.warmup_s, "warmup_s")
        _int(self.context_steps, "context_steps", MIN_VALID_SAMPLES)
        _int(self.horizon_steps, "horizon_steps", 1)
        _int(self.clear_decisions, "clear_decisions", 1)
        _num(self.recheckpoint_s, "recheckpoint_s", strict=True)
        _num(self.max_pause_s, "max_pause_s", strict=True)
        _num(self.calibration_quantile, "calibration_quantile", strict=True, maximum=1.0)
        _num(self.anomaly_baseline_window_s, "anomaly_baseline_window_s", strict=True)
        _num(self.anomaly_baseline_gap_s, "anomaly_baseline_gap_s")
        _int(self.anomaly_smooth_steps, "anomaly_smooth_steps", 1)
        _num(self.curtail_shed_margin, "curtail_shed_margin", maximum=0.5)
        _int(self.oracle_extra_lead_steps, "oracle_extra_lead_steps", 0)
        _num(self.episode_merge_gap_s, "episode_merge_gap_s")
        _num(self.observed_threshold, "observed_threshold", strict=True, maximum=1.0)
        _int(self.bootstrap_resamples, "bootstrap_resamples", 10)
        if not self.threshold_grid or any(not 0.0 < g < 1.0 for g in self.threshold_grid):
            raise ValueError("threshold_grid needs values strictly between 0 and 1")

    @property
    def horizon_s(self) -> float:
        return self.horizon_steps * self.decision_interval_s

    @classmethod
    def from_scenario(cls, outage: Mapping[str, Any]) -> "OutageSettings":
        block = outage["outage"]
        gen = outage["event_generation"]
        return cls(
            decision_interval_s=float(block["decision_interval_s"]),
            warmup_s=float(gen["warmup_s"]),
            context_steps=int(block["context_steps"]),
            horizon_steps=int(block["horizon_steps"]),
            clear_decisions=int(block["clear_decisions"]),
            recheckpoint_s=float(block["recheckpoint_s"]),
            max_pause_s=float(block["max_pause_s"]),
            calibration_quantile=float(block["calibration_quantile"]),
            anomaly_baseline_window_s=float(block["anomaly_baseline_window_s"]),
            anomaly_baseline_gap_s=float(block["anomaly_baseline_gap_s"]),
            anomaly_smooth_steps=int(block["anomaly_smooth_steps"]),
            curtail_shed_margin=float(block["curtail_shed_margin"]),
            oracle_extra_lead_steps=int(block["oracle_extra_lead_steps"]),
            episode_merge_gap_s=float(block["episode_merge_gap_s"]),
            threshold_grid=tuple(float(x) for x in block["threshold_grid"]),
            observed_threshold=float(block["observed_threshold"]),
            bootstrap_resamples=int(block["bootstrap_resamples"]),
        )


def deep_merge(base: Mapping[str, Any], over: Mapping[str, Any]) -> dict[str, Any]:
    """Recursive dict merge; lists and scalars in ``over`` replace those in ``base``."""
    out = copy.deepcopy(dict(base))
    for key, value in over.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def load_outage_scenario(path: Path | str) -> dict[str, Any]:
    """Load the outage scenario and attach the merged simulator scenario as ``sim``.

    ``sim`` is the base simulator scenario (``base_scenario``, relative to the
    outage file) with ``base_overrides`` merged in.  No power parameter is set
    here, so a recalibrated base scenario flows straight through.
    """
    path = Path(path)
    outage = json.loads(path.read_text())
    if outage.get("schema") != SCHEMA:
        raise ValueError(f"outage scenario schema must be {SCHEMA!r}")
    if outage.get("data_kind") != "simulated":
        raise ValueError("outage scenario data_kind must be 'simulated'")
    base = load_scenario(path.parent / outage["base_scenario"])
    outage = dict(outage)
    outage["sim"] = deep_merge(base, outage.get("base_overrides", {}))
    s = OutageSettings.from_scenario(outage)
    sim = outage["sim"]
    if abs(sim["controller_interval_s"] - s.decision_interval_s) > 1e-9:
        raise ValueError("sim controller_interval_s must equal outage decision_interval_s")
    if sim["horizon_s"] <= s.warmup_s + s.horizon_s:
        raise ValueError("horizon too short for warm-up plus one warning horizon")
    return outage


def seed_scenario(outage: Mapping[str, Any], seed: int, *, with_events: bool = True) -> dict[str, Any]:
    """Simulator scenario for one seed: seeded jobs, weather and (optionally) events.

    Events are drawn with :func:`random_schedule` from ``event_generation`` and
    shifted by the warm-up so that none start before the forecaster has a full
    context.  Same seed, same scenario.
    """
    offsets = outage["seed_streams"]
    sim = copy.deepcopy(outage["sim"])
    sim["jobs"]["generate"]["seed"] = int(seed) + int(offsets["job_seed_offset"])
    sim["environment"]["seed"] = int(seed) + int(offsets["environment_seed_offset"])
    gen = outage["event_generation"]
    if not with_events:
        sim["events"] = []
        return sim
    site_racks = {
        item["site"]["site_id"]: [(r["rack_id"], int(r["n_gpus"])) for r in item["racks"]] for item in sim["sites"]
    }
    window = float(sim["horizon_s"]) - float(gen["warmup_s"]) - float(gen["tail_s"])
    if window <= 0:
        raise ValueError("no room for events between warm-up and tail")
    sched = random_schedule(
        int(seed) + int(offsets["event_seed_offset"]),
        window,
        site_racks,
        gen["rates_per_site_per_day"],
        float(gen["precursor_probability"]),
        tuple(gen["lead_range_s"]),
        {k: tuple(v) for k, v in gen["strength_ranges"].items()},
        tuple(gen["duration_range_s"]),
        tuple(gen["remaining_capacity_range"]),
        tuple(gen["derate_range"]),
        tuple(gen["limit_fraction_range"]),
        tuple(gen["repair_range_s"]),
    )
    events = []
    for ev in sched.events:
        d = ev.to_dict()
        d["onset_s"] = float(d["onset_s"]) + float(gen["warmup_s"])
        events.append(d)
    sim["events"] = events
    return sim


# ---------------------------------------------------------------------------
# running the simulator with the scheduler-side placement view
# ---------------------------------------------------------------------------


class OutageRun(_Run):
    """Simulator run that also exposes the hardware precursor in the visible per-GPU temperature."""

    def _visible_state(self, t: float, b: int) -> VisibleState:
        vs = super()._visible_state(t, b)
        offsets = self.signals.gpu_temp_offsets(t)
        if not offsets:
            return vs
        gpu_temp = vs.now["gpu_temp_c"]
        changed = False
        for rack, slot, off in offsets:
            idx = int(self.rack_start[rack] + slot)
            if not np.isfinite(gpu_temp[idx]):
                continue
            base_value = self.rack_air_now[rack] + self.k_gpu[idx] * self.gpu_mean_prev[idx]
            if abs(gpu_temp[idx] - base_value) > 0.5 * abs(off) and abs(off) > 1e-9:
                continue  # the simulator already includes the offset
            gpu_temp[idx] += off
            changed = True
        if changed:
            vs.now["max_gpu_temp_c"][:] = self._rack_max(gpu_temp)
        return vs


class PlacementView:
    """Which job holds which GPUs (scheduler state; not event ground truth)."""

    def __init__(self, run: _Run) -> None:
        self._run = run

    @property
    def rack_ids(self) -> list[str]:
        return list(self._run.rack_ids)

    def n_gpus(self) -> int:
        return int(self._run.G)

    def gpu_rack(self) -> np.ndarray:
        return np.asarray(self._run.gpu_rack)

    def gpu_slot(self) -> np.ndarray:
        return np.asarray(self._run.gpu_slot)

    def gpu_group(self) -> np.ndarray:
        """Shard id per GPU, ``-1`` for GPUs without a job."""
        g = np.asarray(self._run.gpu_shard).astype(int)
        g[g == self._run.n_shards] = -1
        return g

    def job_rack_counts(self) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        run = self._run
        for sh in run.shards:
            if not sh.gpus.size:
                continue
            racks = run.gpu_rack[sh.gpus]
            counts = out.setdefault(sh.job.job_id, {})
            for r in np.unique(racks):
                counts[run.rack_ids[int(r)]] = counts.get(run.rack_ids[int(r)], 0) + int(np.sum(racks == r))
        return out

    def job_at(self, rack_id: str, slot: int) -> Optional[str]:
        run = self._run
        g = int(run.rack_start[run.rack_ids.index(rack_id)] + slot)
        sid = int(run.gpu_shard[g])
        if sid == run.n_shards:
            return None
        return run.shards[sid].job.job_id


def run_policy(
    scenario: Mapping[str, Any],
    controller: Any = None,
    seed: int = 0,
    job_transform: Optional[Callable[[Sequence[Any]], Sequence[Any]]] = None,
) -> tuple[SimResult, SimConfig]:
    """Run the simulator with a controller; controllers with ``bind`` get a placement view first.

    ``job_transform`` rewrites the generated job list before the run (used for
    the e001 averaging-rule policy).  Returns the result and the config used.
    """
    cfg = build_config(scenario, seed=seed)
    if job_transform is not None:
        cfg = replace(cfg, jobs=tuple(job_transform(cfg.jobs)))
    run = OutageRun(cfg, controller, seed)
    if controller is not None and hasattr(controller, "bind"):
        controller.bind(run, cfg)
    return run.run(), cfg


def periodic_local_jobs(jobs: Iterable[Any]) -> list[Any]:
    """The e001 averaging rule for every job: two shards, one per site, averaged every 8 steps.

    Jobs with an odd GPU count cannot be split and are left single-site.
    """
    out = []
    for j in jobs:
        if j.n_gpus % 2 == 0 and not j.multisite:
            out.append(replace(j, multisite=True, site_id=None, average_every_steps=8))
        else:
            out.append(j)
    return out


# ---------------------------------------------------------------------------
# series layout
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SeriesIndex:
    """Fixed order of the monitored series: rack channels first, then site channels."""

    keys: tuple[tuple[str, str], ...]  # (unit_id, channel)
    rack_ids: tuple[str, ...]
    site_ids: tuple[str, ...]
    rack_site: tuple[str, ...]

    @classmethod
    def from_config(cls, cfg: SimConfig) -> "SeriesIndex":
        rack_ids = tuple(r.rack_id for lay in cfg.layouts for r in lay.racks)
        rack_site = tuple(lay.site.site_id for lay in cfg.layouts for _ in lay.racks)
        site_ids = tuple(lay.site.site_id for lay in cfg.layouts)
        keys = [(r, ch) for ch in RACK_CHANNELS for r in rack_ids] + [(s, ch) for ch in SITE_CHANNELS for s in site_ids]
        return cls(tuple(keys), rack_ids, site_ids, rack_site)

    def __len__(self) -> int:
        return len(self.keys)

    def index(self, unit: str, channel: str) -> int:
        return self.keys.index((unit, channel))

    def classes(self) -> list[str]:
        return [CHANNEL_CLASS[ch] for _, ch in self.keys]

    def units(self) -> list[str]:
        return [u for u, _ in self.keys]


# ---------------------------------------------------------------------------
# probabilities from quantiles
# ---------------------------------------------------------------------------


def exceedance_probability(values: np.ndarray, levels: Sequence[float], limit: np.ndarray) -> np.ndarray:
    """P(X > limit) from quantile forecasts.

    ``values`` is ``(n, H, Q)`` with the Q quantile levels ``levels``; ``limit``
    is ``(n, H)``.  Between the quantiles the CDF is interpolated linearly; below
    the lowest level the probability is capped at ``1 - levels[0]`` and above the
    highest level it is floored at ``1 - levels[-1]`` (the forecast carries no
    information past its outermost quantile).  A forecast with zero spread (a
    persistence or oracle forecast) gives exactly 0 or 1.  NaN limits give 0.
    """
    q = np.asarray(values, dtype=float)
    lim = np.asarray(limit, dtype=float)
    lv = np.asarray(levels, dtype=float)
    if q.ndim != 3 or q.shape[-1] != lv.size or lim.shape != q.shape[:2]:
        raise ValueError("values must be (n, H, Q) and limit (n, H)")
    q = np.sort(q, axis=-1)
    spread = q[..., -1] - q[..., 0]
    # position of the limit among the quantiles (vectorized searchsorted)
    below = (q <= lim[..., None]).sum(axis=-1)  # number of quantiles <= limit
    p = np.empty(lim.shape)
    lo_idx = np.clip(below - 1, 0, lv.size - 2)
    q_lo = np.take_along_axis(q, lo_idx[..., None], axis=-1)[..., 0]
    q_hi = np.take_along_axis(q, (lo_idx + 1)[..., None], axis=-1)[..., 0]
    width = np.maximum(q_hi - q_lo, 1e-12)
    frac = np.clip((lim - q_lo) / width, 0.0, 1.0)
    cdf = lv[lo_idx] + frac * (lv[lo_idx + 1] - lv[lo_idx])
    cdf = np.where(below == 0, lv[0], cdf)
    cdf = np.where(below == lv.size, lv[-1], cdf)
    p[...] = 1.0 - cdf
    flat = spread <= 1e-9
    p = np.where(flat, (q[..., 0] > lim).astype(float), p)
    p = np.where(np.isfinite(lim), p, 0.0)
    return np.clip(p, 0.0, 1.0)


class PersistenceForecaster:
    """No forecast: every quantile equals the last observed value.

    Used for the reactive-observed reference, which acts when the current value
    is already past its trouble level.
    """

    name = "persistence"

    def forecast(self, context, horizon, *, known_covariates=None, past_covariates=None):
        from heatwave.forecast.base import QUANTILE_LEVELS, QuantileForecast

        x = np.asarray(context, dtype=float)
        if x.ndim == 2:
            x = x[:, None, :]
        last = np.full(x.shape[:2], np.nan)
        for b in range(x.shape[0]):
            for v in range(x.shape[1]):
                ok = np.flatnonzero(np.isfinite(x[b, v]))
                if ok.size:
                    last[b, v] = x[b, v, ok[-1]]
        vals = np.repeat(last[:, :, None, None], horizon, axis=2)
        vals = np.repeat(vals, len(QUANTILE_LEVELS), axis=3)
        return QuantileForecast(values=np.nan_to_num(vals, nan=0.0), method=self.name)


def window_probabilities(
    forecaster: Any,
    windows: np.ndarray,
    limits: np.ndarray,
    horizon: int,
    *,
    batch_size: int = 512,
) -> np.ndarray:
    """Exceedance probability per series and horizon step: ``(n, H)``.

    ``windows`` is ``(n, T)`` with NaN for missing samples; rows with fewer than
    ``MIN_VALID_SAMPLES`` finite samples or whose newest sample is missing get
    probability 0 (a rack that is off is not forecast).
    """
    from heatwave.forecast.base import QUANTILE_LEVELS

    n = windows.shape[0]
    out = np.zeros((n, horizon))
    valid = (np.isfinite(windows).sum(axis=1) >= MIN_VALID_SAMPLES) & np.isfinite(windows[:, -1])
    rows = np.flatnonzero(valid)
    for start in range(0, rows.size, batch_size):
        sel = rows[start:start + batch_size]
        fc = forecaster.forecast(windows[sel][:, None, :], horizon)
        vals = np.asarray(fc.values)[:, 0]
        out[sel] = exceedance_probability(vals, getattr(fc, "levels", QUANTILE_LEVELS), limits[sel])
    return out


# ---------------------------------------------------------------------------
# warning episodes
# ---------------------------------------------------------------------------


class EpisodeTracker:
    """Per-series warning state with release hysteresis.

    A series is in warning from the first decision with probability at or above
    ``threshold`` until ``clear_decisions`` consecutive decisions fall below it.
    An episode ends at the last decision at which the series was at or above the
    threshold.
    """

    def __init__(self, n_series: int, threshold: float, clear_decisions: int) -> None:
        self.n = int(n_series)
        self.threshold = float(threshold)
        self.clear_decisions = int(clear_decisions)
        self.active = np.zeros(self.n, dtype=bool)
        self._below = np.zeros(self.n, dtype=int)
        self._start = np.full(self.n, np.nan)
        self._last = np.full(self.n, np.nan)
        self._peak = np.zeros(self.n)
        self._count = np.zeros(self.n, dtype=int)
        self.closed: list[dict[str, Any]] = []

    def update(self, t_s: float, pmax: np.ndarray) -> np.ndarray:
        p = np.nan_to_num(np.asarray(pmax, dtype=float), nan=0.0)
        hit = p >= self.threshold
        for k in np.flatnonzero(hit):
            if not self.active[k]:
                self.active[k] = True
                self._start[k] = t_s
                self._peak[k] = 0.0
                self._count[k] = 0
            self._last[k] = t_s
            self._below[k] = 0
            self._peak[k] = max(self._peak[k], p[k])
            self._count[k] += 1
        for k in np.flatnonzero(self.active & ~hit):
            self._below[k] += 1
            if self._below[k] >= self.clear_decisions:
                self._close(k)
        return self.active.copy()

    def _close(self, k: int) -> None:
        self.closed.append(
            {"k": int(k), "start_s": float(self._start[k]), "end_s": float(self._last[k]),
             "peak_p": float(self._peak[k]), "n_decisions": int(self._count[k])}
        )
        self.active[k] = False
        self._below[k] = 0

    def finish(self) -> list[dict[str, Any]]:
        for k in np.flatnonzero(self.active):
            self._close(int(k))
        return sorted(self.closed, key=lambda e: (e["start_s"], e["k"]))

    def since(self, k: int) -> float:
        return float(self._start[k])


def episodes_from_pmax(
    times_s: np.ndarray,
    pmax: np.ndarray,
    threshold: float,
    clear_decisions: int,
    index: Optional["SeriesIndex"] = None,
) -> list[dict[str, Any]]:
    """Episodes from a recorded ``(n_decisions, n_series)`` probability matrix.

    With ``index`` each episode also carries ``unit``, ``channel`` and ``class``
    (the same fields a controller export has).
    """
    tr = EpisodeTracker(pmax.shape[1], threshold, clear_decisions)
    for d in range(pmax.shape[0]):
        tr.update(float(times_s[d]), pmax[d])
    out = tr.finish()
    if index is not None:
        out = [{**e, "unit": index.keys[e["k"]][0], "channel": index.keys[e["k"]][1], "class": CHANNEL_CLASS[index.keys[e["k"]][1]]} for e in out]
    return out


# ---------------------------------------------------------------------------
# channel sampling
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Calibration:
    """Trouble levels for the anomaly channels, from event-free runs on training seeds."""

    limits: Mapping[str, float]
    quantile: float
    n_samples: Mapping[str, int]
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"limits": dict(self.limits), "quantile": self.quantile, "n_samples": dict(self.n_samples), "source": self.source}


def _peer_median(values: np.ndarray, group: np.ndarray, rack: np.ndarray) -> np.ndarray:
    """Median of ``values`` over GPUs with the same job group in the same rack (NaN-aware)."""
    key = (group.astype(np.int64) + 1) * 1000 + rack.astype(np.int64)
    out = np.full(values.shape, np.nan)
    for k in np.unique(key):
        idx = np.flatnonzero(key == k)
        v = values[idx]
        if np.isfinite(v).any():
            out[idx] = np.nanmedian(v[np.isfinite(v)])
    return out


class ChannelBank:
    """Turns visible state into one sample vector per decision and keeps the history."""

    def __init__(self, cfg: SimConfig, settings: OutageSettings, placement: Optional[PlacementView] = None) -> None:
        self.cfg = cfg
        self.settings = settings
        self.placement = placement
        self.index = SeriesIndex.from_config(cfg)
        self.times: list[float] = []
        self.rows: list[np.ndarray] = []
        self.site_limits: list[np.ndarray] = []  # (S, H) per decision
        self._rel_hist: list[np.ndarray] = []
        self._grp_hist: list[np.ndarray] = []
        self._site_nominal_import = np.array([float(lay.site.grid_import_limit_w) for lay in cfg.layouts])
        self._site_cap = np.array([float(lay.site.power_cap_w) for lay in cfg.layouts])
        self._rack_start = None

    # -- helpers -----------------------------------------------------------------

    def _outdoor_forecast_at(self, vs: VisibleState, t_s: float) -> np.ndarray:
        hours = np.asarray(vs.known_future["hour_start_s"], dtype=float)
        fc = np.asarray(vs.known_future["outdoor_forecast_c"], dtype=float)
        return np.array([np.interp(t_s, hours, fc[:, s]) for s in range(fc.shape[1])])

    def supply_setpoint_c(self, vs: VisibleState, t_s: float) -> np.ndarray:
        th = self.cfg.thermal
        out = self._outdoor_forecast_at(vs, t_s)
        return th.supply_setpoint_c + th.outdoor_coupling_k_per_k * np.maximum(0.0, out - th.outdoor_reference_c)

    def site_limit_path(self, vs: VisibleState, t_s: float) -> np.ndarray:
        """Grid import limit (W) at each horizon step, from the current limit and announced curtailments."""
        H = self.settings.horizon_steps
        dt = self.settings.decision_interval_s
        site_ids = list(vs.site_ids)
        current = np.asarray(vs.now["site_import_limit_w"], dtype=float)
        path = np.repeat(current[:, None], H, axis=1)
        for c in vs.known_future.get("announced_curtailments", ()):
            s = site_ids.index(c["site_id"])
            for h in range(H):
                th = t_s + (h + 1) * dt
                if c["onset_s"] <= th < c["end_s"]:
                    path[s, h] = min(path[s, h], self._site_nominal_import[s] * float(c["limit_fraction"]))
        return path

    # -- sampling ------------------------------------------------------------------

    def sample(self, t_s: float, vs: VisibleState) -> np.ndarray:
        now = vs.now
        R = len(self.index.rack_ids)
        S = len(self.index.site_ids)
        on = np.asarray(now["rack_on"], dtype=bool)
        gpu_temp_max = np.where(on, np.asarray(now["max_gpu_temp_c"], dtype=float), np.nan)
        sp = self.supply_setpoint_c(vs, t_s)
        site_index = {s: i for i, s in enumerate(self.index.site_ids)}
        rack_site_i = np.array([site_index[s] for s in self.index.rack_site])
        supply = np.where(on, np.asarray(now["supply_c"], dtype=float) - sp[rack_site_i], np.nan)
        ratio = np.where(on, np.asarray(now["breaker_load_ratio"], dtype=float), np.nan)
        gpu_anom = self._gpu_anomaly(vs)
        site_power = np.asarray(now["site_power_w"], dtype=float)
        row = np.concatenate([gpu_temp_max, supply, ratio, gpu_anom, site_power])
        row[~np.isfinite(row)] = np.nan
        self.times.append(float(t_s))
        self.rows.append(row)
        self.site_limits.append(self.site_limit_path(vs, t_s))
        return row

    def _gpu_anomaly(self, vs: VisibleState) -> np.ndarray:
        """Per-rack largest per-GPU temperature rise against the GPU's own baseline (K).

        Each GPU's temperature above its rack air is compared with the median of
        its peers (same job, same rack) so job-wide power changes cancel.  The
        result is smoothed over ``anomaly_smooth_steps`` decisions and compared
        with the GPU's own median over the baseline window, using only samples
        taken while the GPU belonged to the same job.
        """
        R = len(self.index.rack_ids)
        temp = np.asarray(vs.now["gpu_temp_c"], dtype=float)
        gpu_rack = self.placement.gpu_rack() if self.placement is not None else self._infer_gpu_rack(temp, vs)
        group = self.placement.gpu_group() if self.placement is not None else np.full(temp.shape, -1)
        air = np.asarray(vs.now["rack_air_c"], dtype=float)
        excess = temp - air[gpu_rack]
        rel = excess - _peer_median(excess, group, gpu_rack)
        self._rel_hist.append(rel)
        self._grp_hist.append(group)
        n = len(self._rel_hist)
        dt = self.settings.decision_interval_s
        gap = int(math.ceil(self.settings.anomaly_baseline_gap_s / dt))
        win = int(math.ceil(self.settings.anomaly_baseline_window_s / dt))
        sm = self.settings.anomaly_smooth_steps
        out = np.full(R, np.nan)
        lo, hi = max(0, n - 1 - win), max(0, n - gap)
        if hi - lo < MIN_BASELINE_SAMPLES:
            return out
        old = np.stack(self._rel_hist[lo:hi])
        same = np.stack(self._grp_hist[lo:hi]) == group[None, :]
        old = np.where(same, old, np.nan)
        enough = np.isfinite(old).sum(axis=0) >= MIN_BASELINE_SAMPLES
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            base = np.nanmedian(old, axis=0)
            recent = np.nanmean(np.stack(self._rel_hist[-sm:]), axis=0)
        anomaly = np.where(enough, recent - base, np.nan)
        for r in range(R):
            v = anomaly[gpu_rack == r]
            if np.isfinite(v).any():
                out[r] = np.nanmax(v)
        return out

    def _infer_gpu_rack(self, temp: np.ndarray, vs: VisibleState) -> np.ndarray:
        if self._rack_start is None:
            counts = [lay_r.n_gpus for lay in self.cfg.layouts for lay_r in lay.racks]
            self._rack_start = np.repeat(np.arange(len(counts)), counts)
        return self._rack_start

    # -- views ----------------------------------------------------------------------

    def matrix(self) -> np.ndarray:
        """Samples as ``(n_series, n_decisions)``."""
        return np.stack(self.rows, axis=1) if self.rows else np.zeros((len(self.index), 0))

    def limits_matrix(self, calibration: Optional[Calibration], d: int) -> np.ndarray:
        """Trouble levels ``(n_series, H)`` for decision ``d``."""
        return series_limits(self.cfg, self.index, self.settings, calibration, self.site_limits[d])


def series_limits(
    cfg: SimConfig,
    index: SeriesIndex,
    settings: OutageSettings,
    calibration: Optional[Calibration],
    site_limit: np.ndarray,
) -> np.ndarray:
    """Trouble level of every series at each horizon step: ``(n_series, H)``; NaN when unknown."""
    H = settings.horizon_steps
    out = np.full((len(index), H), np.nan)
    site_i = {s: i for i, s in enumerate(index.site_ids)}
    for k, (unit, ch) in enumerate(index.keys):
        if ch == CH_GPU_TEMP:
            out[k] = float(cfg.throttle.throttle_threshold_c)
        elif ch == CH_BREAKER:
            out[k] = 1.0
        elif ch in (CH_SUPPLY, CH_GPU_ANOM):
            if calibration is not None and ch in calibration.limits:
                out[k] = float(calibration.limits[ch])
        elif ch == CH_SITE_POWER:
            out[k] = site_limit[site_i[unit]]
    return out


def calibrate(
    traces: Sequence[np.ndarray],
    index: SeriesIndex,
    settings: OutageSettings,
    times: Sequence[np.ndarray],
    source: str = "",
) -> Calibration:
    """Trouble levels for ``supply_anom`` and ``gpu_anom``: a high quantile of event-free samples.

    ``traces`` are ``(n_series, n_decisions)`` sample matrices from event-free
    runs on training seeds; samples before the warm-up are ignored.
    """
    limits: dict[str, float] = {}
    counts: dict[str, int] = {}
    for ch in (CH_SUPPLY, CH_GPU_ANOM):
        ks = [k for k, (_, c) in enumerate(index.keys) if c == ch]
        pool = []
        for tr, t in zip(traces, times):
            keep = np.asarray(t) >= settings.warmup_s
            pool.append(tr[np.ix_(ks, np.flatnonzero(keep))].ravel())
        v = np.concatenate(pool) if pool else np.zeros(0)
        v = v[np.isfinite(v)]
        if v.size == 0:
            raise ValueError(f"no event-free samples to calibrate {ch}")
        limits[ch] = float(np.quantile(v, settings.calibration_quantile))
        counts[ch] = int(v.size)
    return Calibration(limits, settings.calibration_quantile, counts, source)


# ---------------------------------------------------------------------------
# response planning
# ---------------------------------------------------------------------------


def job_costs(job: Any, transfer: Any) -> dict[str, float]:
    """GPU-hours a response costs one job, from the simulator's own stall and transfer times."""
    n = float(job.n_gpus)
    ckpt = n * float(job.checkpoint_duration_s) / 3600.0
    move = ckpt + n * (float(transfer.transfer_s(int(job.n_gpus))) + float(transfer.restore_s(int(job.n_gpus)))) / 3600.0
    return {"checkpoint": ckpt, "move": move}


@dataclass
class Alarm:
    """An active warning on a rack (or site) and what caused it."""

    unit: str
    classes: tuple[str, ...]
    since_s: float
    p: float = 1.0
    slot: Optional[int] = None  # oracle only: the single GPU slot that will fail
    limit_w: Optional[float] = None  # site alarms: lowest import limit expected within the horizon
    event_s: Optional[float] = None  # oracle only: time of the event the alarm is for
    gated: bool = False  # oracle only: wait for each job's exact checkpoint lead


class ResponsePlanner:
    """Checkpoint now, then move to the other site if it has room, else pause; resume when clear."""

    def __init__(self, cfg: SimConfig, settings: OutageSettings) -> None:
        self.cfg = cfg
        self.settings = settings
        self.jobs = {j.job_id: j for j in cfg.jobs}
        self.site_ids = [lay.site.site_id for lay in cfg.layouts]
        self.rack_site = {r.rack_id: lay.site.site_id for lay in cfg.layouts for r in lay.racks}
        self.gate: Optional[Callable[[str, Alarm, float], bool]] = None  # oracle only: is a job due for its action?
        self.last_checkpoint: dict[str, float] = {}
        self.staged: dict[str, float] = {}
        self.paused: dict[str, tuple[str, float]] = {}
        self.meta: list[dict[str, Any]] = []
        lv = cfg.levels
        c = cfg.compute_fraction_of_step
        self._run_w = c * lv.compute_w + (1.0 - c) * lv.comm_w
        self._idle_w = lv.idle_w
        self._host_w = lv.host_w_per_gpu

    # -- bookkeeping ---------------------------------------------------------------

    def _note(self, t: float, action: str, job_id: str, unit: str, why: str) -> None:
        self.meta.append({"t_s": float(t), "action": action, "job_id": job_id, "unit": unit, "why": why})

    def job_power_saving_w(self, n_gpus: int) -> float:
        """Power a paused job sheds: its GPUs go from the phase-averaged running level to idle."""
        return n_gpus * max(self._run_w - self._idle_w, 0.0)

    def job_power_w(self, n_gpus: int) -> float:
        return n_gpus * (self._run_w + self._host_w)

    def _dest(self, src_site: str, n: int, free: dict[str, int], blocked: set[str]) -> Optional[str]:
        best, best_free = None, -1
        for s in self.site_ids:
            if s == src_site or s in blocked:
                continue
            if free.get(s, 0) >= n and free[s] > best_free:
                best, best_free = s, free[s]
        return best

    # -- planning ------------------------------------------------------------------

    def plan(
        self,
        t_s: float,
        vs: VisibleState,
        placement: Mapping[str, Mapping[str, int]],
        rack_alarms: Mapping[str, Alarm],
        site_alarms: Mapping[str, Alarm],
        job_at: Optional[Callable[[str, int], Optional[str]]] = None,
    ) -> list[Any]:
        """Actions for this decision.  Site alarms carry ``limit_w``; rack alarms may name one GPU slot."""
        st = self.settings
        views = {jv.job_id: jv for jv in vs.jobs}
        free = {s: int(vs.now["free_gpus"][i]) for i, s in enumerate(vs.site_ids)}
        site_power = {s: float(vs.now["site_power_w"][i]) for i, s in enumerate(vs.site_ids)}
        site_limit = {s: float(vs.now["site_import_limit_w"][i]) for i, s in enumerate(vs.site_ids)}
        actions: list[Any] = []
        handled: set[str] = set()
        blocked_dest = set(site_alarms)

        # -- site curtailment: shed the cheapest flexible jobs until the forecast power fits
        for site, alarm in sorted(site_alarms.items()):
            limit = alarm.limit_w if alarm.limit_w is not None else site_limit[site]
            need = site_power[site] - limit * (1.0 - st.curtail_shed_margin)
            if need <= 0:
                continue
            cands = []
            for job_id, racks in placement.items():
                job = self.jobs[job_id]
                jv = views.get(job_id)
                if jv is None or job.multisite or not jv.flexible or jv.paused:
                    continue
                if jv.status in ("queued", "done"):
                    continue
                if any(self.rack_site[r] == site for r in racks):
                    cands.append((jv.value_per_gpu_hour, -job.n_gpus, job_id))
            cands.sort()
            saved = 0.0
            for _, _, job_id in cands:
                if saved >= need:
                    break
                job = self.jobs[job_id]
                n = int(job.n_gpus)
                jv = views[job_id]
                saved += self.job_power_saving_w(n)
                handled.add(job_id)
                dest = self._dest(site, n, free, blocked_dest) if jv.status == "running" else None
                if dest is not None and self._dest_has_power(dest, n, site_power, site_limit):
                    actions.append(MigrateJob(job_id, dest))
                    self._note(t_s, "MigrateJob", job_id, site, "curtail")
                    free[dest] -= n
                    free[site] += n
                    site_power[dest] += self.job_power_w(n)
                    self.last_checkpoint[job_id] = t_s
                    continue
                self._checkpoint_or_pause(t_s, job_id, jv, site, "curtail", actions)

        # -- rack alarms: protect every job that holds GPUs on the rack
        for rack, alarm in sorted(rack_alarms.items()):
            site = self.rack_site[rack]
            only = None
            if alarm.slot is not None and job_at is not None:
                only = job_at(rack, alarm.slot)
                if only is None:
                    continue
            for job_id, racks in sorted(placement.items()):
                if rack not in racks or job_id in handled:
                    continue
                if only is not None and job_id != only:
                    continue
                job = self.jobs[job_id]
                jv = views.get(job_id)
                if jv is None or job.multisite or jv.paused:
                    continue
                if self.gate is not None and not self.gate(job_id, alarm, t_s):
                    continue
                handled.add(job_id)
                n = int(job.n_gpus)
                dest = self._dest(site, n, free, blocked_dest) if (jv.flexible and jv.status == "running") else None
                if dest is not None:
                    actions.append(MigrateJob(job_id, dest))
                    self._note(t_s, "MigrateJob", job_id, rack, "rack")
                    free[dest] -= n
                    free[site] += n
                    self.last_checkpoint[job_id] = t_s
                    continue
                self._checkpoint_or_pause(t_s, job_id, jv, rack, "rack", actions)
        return actions

    def _dest_has_power(self, dest: str, n: int, site_power: Mapping[str, float], site_limit: Mapping[str, float]) -> bool:
        return site_power[dest] + self.job_power_w(n) <= site_limit[dest]

    def _checkpoint_or_pause(self, t: float, job_id: str, jv: Any, unit: str, why: str, actions: list) -> None:
        st = self.settings
        staged = self.staged.get(job_id)
        if jv.flexible and staged is not None and t - staged >= st.decision_interval_s - 1e-9 and jv.status in ("running", "ckpt", "restore", "transfer"):
            actions.append(PauseJob(job_id))
            self.paused[job_id] = (unit, t)
            self._note(t, "PauseJob", job_id, unit, why)
            return
        if jv.status == "running" and t - self.last_checkpoint.get(job_id, -math.inf) >= st.recheckpoint_s - 1e-9:
            actions.append(CheckpointNow(job_id))
            self.last_checkpoint[job_id] = t
            if jv.flexible:
                self.staged.setdefault(job_id, t)
            self._note(t, "CheckpointNow", job_id, unit, why)

    def resumes(
        self,
        t_s: float,
        vs: VisibleState,
        rack_active: set[str],
        site_active: set[str],
    ) -> list[Any]:
        """Resume paused jobs whose warning cleared, that faulted, or that hit the pause limit."""
        views = {jv.job_id: jv for jv in vs.jobs}
        actions = []
        for job_id, (unit, t0) in sorted(self.paused.items()):
            jv = views.get(job_id)
            if jv is None:
                del self.paused[job_id]
                self.staged.pop(job_id, None)
                continue
            still = unit in rack_active or unit in site_active
            faulted = jv.status in ("queued", "restore")
            too_long = t_s - t0 >= self.settings.max_pause_s - 1e-9
            if not still or faulted or too_long:
                actions.append(ResumeJob(job_id))
                self._note(t_s, "ResumeJob", job_id, unit, "clear" if not still else ("fault" if faulted else "limit"))
                del self.paused[job_id]
                self.staged.pop(job_id, None)
        # staged flags expire when the warning on their unit is over
        for job_id in list(self.staged):
            if job_id in self.paused:
                continue
            jv = views.get(job_id)
            if jv is None or t_s - self.staged[job_id] > 2 * self.settings.recheckpoint_s:
                self.staged.pop(job_id, None)
        return actions


# ---------------------------------------------------------------------------
# controllers
# ---------------------------------------------------------------------------


class _BankController:
    """Shared sampling, alarm bookkeeping and export for all outage controllers."""

    name = "base"

    def __init__(self, settings: OutageSettings) -> None:
        self.settings = settings
        self.bank: Optional[ChannelBank] = None
        self.placement: Optional[PlacementView] = None
        self.cfg: Optional[SimConfig] = None
        self.pmax_rows: list[np.ndarray] = []
        self.decision_times: list[float] = []
        self.planner: Optional[ResponsePlanner] = None
        self.index: Optional[SeriesIndex] = None

    def bind(self, run: _Run, cfg: SimConfig) -> None:
        self.cfg = cfg
        self.placement = PlacementView(run)
        self.bank = ChannelBank(cfg, self.settings, self.placement)
        self.index = self.bank.index
        self.planner = ResponsePlanner(cfg, self.settings)
        self._on_bind()

    def _on_bind(self) -> None:  # pragma: no cover - hook
        pass

    def decide(self, t_s: float, visible_state: VisibleState) -> Sequence[Any]:  # pragma: no cover - overridden
        return ()

    def export(self) -> dict[str, Any]:
        return {
            "policy": self.name,
            "times_s": [float(t) for t in self.decision_times],
            "meta_actions": list(self.planner.meta) if self.planner is not None else [],
        }


class TraceRecorder(_BankController):
    """Takes no action; records the samples that forecasters see and the costs a response would carry."""

    name = "reactive"

    def _on_bind(self) -> None:
        self.rack_checkpoint_gpu_h: list[np.ndarray] = []
        self.rack_flex_move_gpu_h: list[np.ndarray] = []
        self.rack_nonflex_checkpoint_gpu_h: list[np.ndarray] = []
        self.site_flex_move_gpu_h: list[np.ndarray] = []
        self.rack_on_rows: list[np.ndarray] = []

    def decide(self, t_s, visible_state):
        assert self.bank is not None and self.placement is not None and self.cfg is not None and self.index is not None
        self.bank.sample(t_s, visible_state)
        self.decision_times.append(float(t_s))
        R, S = len(self.index.rack_ids), len(self.index.site_ids)
        flex_move = np.zeros(R)
        nonflex = np.zeros(R)
        site_flex = np.zeros(S)
        jobs = {j.job_id: j for j in self.cfg.jobs}
        for job_id, racks in self.placement.job_rack_counts().items():
            job = jobs[job_id]
            if job.multisite:
                continue
            c = job_costs(job, self.cfg.transfer)
            for rid in racks:
                ri = self.index.rack_ids.index(rid)
                if job.flexible:
                    flex_move[ri] += c["move"]
                else:
                    nonflex[ri] += c["checkpoint"]
            site = self.index.rack_site[self.index.rack_ids.index(next(iter(racks)))]
            if job.flexible:
                site_flex[self.index.site_ids.index(site)] += c["move"]
        self.rack_flex_move_gpu_h.append(flex_move)
        self.rack_nonflex_checkpoint_gpu_h.append(nonflex)
        self.site_flex_move_gpu_h.append(site_flex)
        self.rack_on_rows.append(np.asarray(visible_state.now["rack_on"], dtype=bool))
        return ()

    def trace(self) -> dict[str, Any]:
        assert self.bank is not None
        return {
            "times_s": np.array(self.decision_times),
            "samples": self.bank.matrix(),
            "site_limits": np.stack(self.bank.site_limits) if self.bank.site_limits else np.zeros((0, 0, 0)),
            "rack_flex_move_gpu_h": np.stack(self.rack_flex_move_gpu_h),
            "rack_nonflex_checkpoint_gpu_h": np.stack(self.rack_nonflex_checkpoint_gpu_h),
            "site_flex_move_gpu_h": np.stack(self.site_flex_move_gpu_h),
        }


class ForecastWarningController(_BankController):
    """Forecast every series, warn on exceedance probability, respond with the planner."""

    def __init__(
        self,
        settings: OutageSettings,
        forecaster: Any,
        threshold: float,
        calibration: Optional[Calibration],
        name: str,
        *,
        batch_size: int = 512,
    ) -> None:
        super().__init__(settings)
        self.forecaster = forecaster
        self.threshold = float(threshold)
        self.calibration = calibration
        self.name = name
        self.batch_size = batch_size
        self.tracker: Optional[EpisodeTracker] = None

    def _on_bind(self) -> None:
        assert self.index is not None
        self.tracker = EpisodeTracker(len(self.index), self.threshold, self.settings.clear_decisions)

    def decide(self, t_s, visible_state):
        assert self.bank is not None and self.placement is not None and self.planner is not None
        assert self.index is not None and self.tracker is not None
        st = self.settings
        self.bank.sample(t_s, visible_state)
        self.decision_times.append(float(t_s))
        d = len(self.bank.rows) - 1
        mat = self.bank.matrix()
        T = st.context_steps
        pmax = np.zeros(len(self.index))
        if d + 1 >= T:
            ctx = mat[:, d + 1 - T: d + 1]
            limits = self.bank.limits_matrix(self.calibration, d)
            p = window_probabilities(self.forecaster, ctx, limits, st.horizon_steps, batch_size=self.batch_size)
            pmax = p.max(axis=1)
        self.pmax_rows.append(pmax)
        active = self.tracker.update(t_s, pmax)
        return self._respond(t_s, visible_state, active)

    def _respond(self, t_s: float, vs: VisibleState, active: np.ndarray) -> list[Any]:
        assert self.index is not None and self.tracker is not None and self.planner is not None and self.placement is not None
        rack_alarms: dict[str, Alarm] = {}
        site_alarms: dict[str, Alarm] = {}
        for k in np.flatnonzero(active):
            unit, ch = self.index.keys[k]
            cls = CHANNEL_CLASS[ch]
            by_unit = site_alarms if ch in SITE_CHANNELS else rack_alarms
            a = by_unit.get(unit)
            if a is None:
                limit_w = None
                if ch in SITE_CHANNELS:
                    limit_w = float(np.min(self.bank.site_limits[-1][self.index.site_ids.index(unit)]))
                by_unit[unit] = Alarm(unit, (cls,), self.tracker.since(int(k)), limit_w=limit_w)
            else:
                a.classes = tuple(sorted(set(a.classes) | {cls}))
                a.since_s = min(a.since_s, self.tracker.since(int(k)))
        actions = list(self.planner.resumes(t_s, vs, set(rack_alarms), set(site_alarms)))
        actions += self.planner.plan(t_s, vs, self.placement.job_rack_counts(), rack_alarms, site_alarms, self.placement.job_at)
        return actions

    def export(self) -> dict[str, Any]:
        out = super().export()
        assert self.tracker is not None and self.index is not None
        out["threshold"] = self.threshold
        out["pmax"] = np.stack(self.pmax_rows) if self.pmax_rows else np.zeros((0, len(self.index)))
        out["episodes"] = [
            {**e, "unit": self.index.keys[e["k"]][0], "channel": self.index.keys[e["k"]][1],
             "class": CHANNEL_CLASS[self.index.keys[e["k"]][1]]}
            for e in self.tracker.finish()
        ]
        return out


@dataclass(frozen=True)
class OracleAlarm:
    """Alarm of the perfect-foresight upper bound.

    ``acts`` False marks a detection-only alarm (a scheduled event whose
    consequences are handled by other alarms); it is exported for scoring but
    never drives an action.  ``event_s`` is the exact time of the event.
    """

    unit: str
    cls: str
    start_s: float
    end_s: float
    slot: Optional[int] = None
    event_id: str = ""
    limit_w: Optional[float] = None
    event_s: Optional[float] = None
    gated: bool = False
    acts: bool = True


def oracle_settings(settings: OutageSettings, control_dt_s: float) -> OutageSettings:
    """Settings for the oracle run: decisions every control step and no re-checkpoint spacing."""
    return replace(settings, decision_interval_s=float(control_dt_s), recheckpoint_s=float(control_dt_s))


def oracle_scenario(sim: Mapping[str, Any]) -> dict[str, Any]:
    """Simulator scenario with the controller called every control step (for the oracle run)."""
    out = copy.deepcopy(dict(sim))
    out["controller_interval_s"] = out["control_dt_s"]
    return out


def oracle_lead_s(cfg: SimConfig, settings: OutageSettings, ckpt_s: Optional[float] = None) -> float:
    """Lead of the oracle: one checkpoint plus ``oracle_extra_lead_steps`` control steps."""
    if ckpt_s is None:
        ckpt_s = max((float(j.checkpoint_duration_s) for j in cfg.jobs), default=0.0)
    return float(ckpt_s) + settings.oracle_extra_lead_steps * cfg.control_dt_s


def oracle_alarms_from_reference(
    cfg: SimConfig,
    ref_events: Sequence[Mapping[str, Any]],
    throttle_eps: Sequence[Mapping[str, Any]],
    settings: OutageSettings,
) -> list[OracleAlarm]:
    """Alarms of the perfect-foresight upper bound.

    Built from the reactive reference run of the same seed.  Every rollback
    event of that run (GPU fault, rack trip, thermal shutdown) gets an alarm
    whose checkpoint of each affected job starts exactly one checkpoint time
    (that job's) plus ``oracle_extra_lead_steps`` control steps before the
    event.  Scheduled curtailments and throttle episodes get an alarm that
    starts one maximum-checkpoint lead before the event.  Every scheduled event
    also gets a detection-only alarm at that lead so recall is defined.  Reads
    event times; no policy other than this upper bound may do that.
    """
    lead = oracle_lead_s(cfg, settings)
    out: list[OracleAlarm] = []
    for e in ref_events:
        kind = e["kind"]
        t = float(e["t_s"])
        if kind == KIND_HARDWARE_FAULT:
            out.append(OracleAlarm(e["rack_id"], CLASS_HARDWARE, t - lead, t + cfg.control_dt_s, int(e["gpu_slot"]), "hardware_fault",
                                   None, t, True))
        elif kind in (KIND_BREAKER_TRIP, "thermal_shutdown"):
            cls = CLASS_POWER if kind == KIND_BREAKER_TRIP else CLASS_THERMAL
            out.append(OracleAlarm(e["rack_id"], cls, t - lead, t + cfg.control_dt_s, None, kind, None, t, True))
    nominal = {lay.site.site_id: float(lay.site.grid_import_limit_w) for lay in cfg.layouts}
    rack_site = {r.rack_id: lay.site.site_id for lay in cfg.layouts for r in lay.racks}
    site_racks: dict[str, list[str]] = {}
    for r, sid in rack_site.items():
        site_racks.setdefault(sid, []).append(r)
    for ev in cfg.events.events:
        if ev.kind == KIND_GRID_CURTAILMENT:
            out.append(OracleAlarm(ev.site_id, CLASS_CURTAIL, ev.onset_s - lead, ev.end_s, None, ev.event_id,
                                   nominal[ev.site_id] * float(ev.limit_fraction), ev.onset_s, False, True))
            continue
        if ev.kind == KIND_COOLING_FAILURE:
            units, cls = ([ev.rack_id] if ev.rack_id else site_racks[ev.site_id]), CLASS_COOLING
        elif ev.kind == KIND_BREAKER_TRIP:
            units, cls = [ev.rack_id], CLASS_POWER
        else:
            units, cls = [ev.rack_id], CLASS_HARDWARE
        end = ev.end_s if ev.kind != KIND_HARDWARE_FAULT else ev.onset_s + cfg.control_dt_s
        for u in units:
            out.append(OracleAlarm(u, cls, ev.onset_s - lead, end, None, ev.event_id, None, ev.onset_s, False, False))
    for ep in throttle_eps:
        out.append(OracleAlarm(ep["rack_id"], CLASS_THERMAL, ep["onset_s"] - lead, ep["end_s"] + cfg.control_dt_s, None,
                               "thermal_throttle", None, ep["onset_s"], False, True))
    return out


class OracleController(_BankController):
    """Perfect-foresight upper bound: the planner driven by exact event times (see :func:`oracle_alarms_from_reference`).

    Run it with a simulator scenario whose ``controller_interval_s`` equals the
    control step and with ``settings.decision_interval_s`` set to that step, so
    it can act at the exact lead.
    """

    def __init__(self, settings: OutageSettings, alarms: Sequence[OracleAlarm], name: str = "perfect_foresight") -> None:
        super().__init__(settings)
        self.alarms = list(alarms)
        self.name = name

    def _on_bind(self) -> None:
        assert self.planner is not None and self.cfg is not None
        extra = self.settings.oracle_extra_lead_steps * self.cfg.control_dt_s
        jobs = self.planner.jobs

        def gate(job_id: str, alarm: Alarm, t_s: float) -> bool:
            if alarm.event_s is None or not alarm.gated:
                return True
            return t_s >= alarm.event_s - (float(jobs[job_id].checkpoint_duration_s) + extra) - 1e-9

        self.planner.gate = gate

    def decide(self, t_s, visible_state):
        assert self.bank is not None and self.placement is not None and self.planner is not None
        self.bank.sample(t_s, visible_state)
        self.decision_times.append(float(t_s))
        rack_alarms: dict[str, Alarm] = {}
        site_alarms: dict[str, Alarm] = {}
        for a in self.alarms:
            if not a.acts or not (a.start_s <= t_s < a.end_s):
                continue
            is_site = a.unit in self.planner.site_ids
            by_unit = site_alarms if is_site else rack_alarms
            cur = by_unit.get(a.unit)
            new = Alarm(a.unit, (a.cls,), a.start_s, 1.0, a.slot, a.limit_w, a.event_s, a.gated)
            if cur is None:
                by_unit[a.unit] = new
            else:
                cur.classes = tuple(sorted(set(cur.classes) | {a.cls}))
                cur.since_s = min(cur.since_s, a.start_s)
                if a.slot != cur.slot:
                    cur.slot = None  # two causes on one rack: protect the whole rack
                if a.limit_w is not None:
                    cur.limit_w = a.limit_w if cur.limit_w is None else min(cur.limit_w, a.limit_w)
                cur.gated = cur.gated and a.gated
                if a.event_s is not None:
                    cur.event_s = a.event_s if cur.event_s is None else min(cur.event_s, a.event_s)
        actions = list(self.planner.resumes(t_s, visible_state, set(rack_alarms), set(site_alarms)))
        actions += self.planner.plan(t_s, visible_state, self.placement.job_rack_counts(), rack_alarms, site_alarms, self.placement.job_at)
        return actions

    def export(self) -> dict[str, Any]:
        out = super().export()
        step = self.settings.decision_interval_s
        out["episodes"] = [
            {"unit": a.unit, "class": a.cls, "channel": "oracle", "start_s": a.start_s, "end_s": max(a.end_s - step, a.start_s),
             "peak_p": 1.0, "n_decisions": 1, "k": -1}
            for a in self.alarms
        ]
        out["threshold"] = None
        return out


# ---------------------------------------------------------------------------
# open-loop probabilities on a recorded trace
# ---------------------------------------------------------------------------


def openloop_pmax(
    forecaster: Any,
    trace: Mapping[str, Any],
    cfg: SimConfig,
    settings: OutageSettings,
    calibration: Optional[Calibration],
    *,
    batch_size: int = 512,
    perfect: bool = False,
) -> np.ndarray:
    """Warning probabilities ``(n_decisions, n_series)`` from a recorded no-action trace.

    Decision ``d`` sees ``samples[:, d - T + 1 : d + 1]``.  With ``perfect`` the
    realized future of the same trace is used as a zero-spread forecast (an upper
    bound for any forecaster on that trace).
    """
    index = SeriesIndex.from_config(cfg)
    samples = np.asarray(trace["samples"], dtype=float)
    n_series, n_dec = samples.shape
    T, H = settings.context_steps, settings.horizon_steps
    pmax = np.zeros((n_dec, n_series))
    site_limits = np.asarray(trace["site_limits"])
    decisions = list(range(T - 1, n_dec))
    full = decisions

    def limits_at(d: int) -> np.ndarray:
        return series_limits(cfg, index, settings, calibration, site_limits[d])

    if perfect:
        from heatwave.forecast.base import QUANTILE_LEVELS

        missing = -1.0e18
        for d in decisions:
            fut = np.full((n_series, H), np.nan)
            n_av = min(H, n_dec - 1 - d)
            if n_av > 0:
                fut[:, :n_av] = samples[:, d + 1: d + 1 + n_av]
            fut = np.where(np.isfinite(fut), fut, missing)
            vals = np.repeat(fut[:, :, None], len(QUANTILE_LEVELS), axis=2)
            pmax[d] = exceedance_probability(vals, QUANTILE_LEVELS, limits_at(d)).max(axis=1)
        return pmax

    rows_per_batch = max(1, batch_size // n_series)
    for start in range(0, len(full), rows_per_batch):
        ds = full[start:start + rows_per_batch]
        win = np.concatenate([samples[:, d + 1 - T: d + 1] for d in ds], axis=0)
        lim = np.concatenate([limits_at(d) for d in ds], axis=0)
        p = window_probabilities(forecaster, win, lim, H, batch_size=batch_size)
        p = p.reshape(len(ds), n_series, H).max(axis=2)
        for j, d in enumerate(ds):
            pmax[d] = p[j]
    return pmax


# ---------------------------------------------------------------------------
# event table and attribution
# ---------------------------------------------------------------------------


def throttle_episodes(events: Sequence[Mapping[str, Any]], horizon_s: float, merge_gap_s: float) -> list[dict[str, Any]]:
    """Merge the simulator's throttle start/end log into one episode per rack and burst."""
    by_rack: dict[str, list[tuple[float, str]]] = {}
    for e in events:
        if e["kind"] == KIND_THERMAL_THROTTLE:
            by_rack.setdefault(e["rack_id"], []).append((float(e["t_s"]), e["phase"]))
    out = []
    for rack, items in sorted(by_rack.items()):
        items.sort(key=lambda x: (x[0], 0 if x[1] == "end" else 1))
        spans: list[list[float]] = []
        for t, phase in items:
            if phase == "start":
                spans.append([t, horizon_s])
            elif spans and spans[-1][1] == horizon_s:
                spans[-1][1] = t
        merged: list[list[float]] = []
        for a, b in spans:
            if merged and a - merged[-1][1] <= merge_gap_s:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        for a, b in merged:
            out.append({"rack_id": rack, "onset_s": a, "end_s": b})
    out.sort(key=lambda e: (e["onset_s"], e["rack_id"]))
    return out


def build_event_table(
    cfg: SimConfig,
    ref_events: Sequence[Mapping[str, Any]],
    settings: OutageSettings,
) -> list[dict[str, Any]]:
    """Scheduled events plus the throttle episodes of the reactive reference run.

    Only events that start at or after the warm-up are scored.
    """
    rack_site = {r.rack_id: lay.site.site_id for lay in cfg.layouts for r in lay.racks}
    site_racks: dict[str, list[str]] = {}
    for r, s in rack_site.items():
        site_racks.setdefault(s, []).append(r)
    rows = []
    for gt in cfg.events.ground_truth():
        kind = gt["kind"]
        rack = gt["rack_id"]
        if kind == KIND_GRID_CURTAILMENT:
            units = [gt["site_id"]]
        elif rack is None:
            units = list(site_racks[gt["site_id"]])
        else:
            units = [rack]
        slot = None
        for ev in cfg.events.events:
            if ev.event_id == gt["event_id"]:
                slot = getattr(ev, "gpu_slot", None)
        window_end = gt["end_s"] if kind != KIND_HARDWARE_FAULT else gt["onset_s"]
        rows.append(
            {
                "event_id": gt["event_id"], "kind": kind, "site_id": gt["site_id"], "rack_id": rack, "units": units,
                "gpu_slot": slot, "onset_s": float(gt["onset_s"]), "end_s": float(gt["end_s"]),
                "window_end_s": float(window_end), "has_precursor": bool(gt["has_precursor"]),
                "precursor_lead_s": float(gt["precursor_lead_s"]), "mode": gt.get("mode"), "source": "scheduled",
            }
        )
    for i, ep in enumerate(throttle_episodes(ref_events, cfg.horizon_s, settings.episode_merge_gap_s)):
        rows.append(
            {
                "event_id": f"throttle-{i:03d}-{ep['rack_id']}", "kind": KIND_THERMAL_THROTTLE, "site_id": rack_site[ep["rack_id"]],
                "rack_id": ep["rack_id"], "units": [ep["rack_id"]], "gpu_slot": None, "onset_s": float(ep["onset_s"]),
                "end_s": float(ep["end_s"]), "window_end_s": float(ep["end_s"]), "has_precursor": False,
                "precursor_lead_s": 0.0, "mode": None, "source": "emergent",
            }
        )
    rows = [r for r in rows if r["onset_s"] >= settings.warmup_s - 1e-9]
    rows.sort(key=lambda r: (r["onset_s"], r["event_id"]))
    return rows


_RE_GPU = re.compile(r"^gpu fault (\S+)/(\d+)$")
_RE_RACK = re.compile(r"^rack (\S+) off \((.+)\)$")


def attribute_faults(
    events: Sequence[Mapping[str, Any]],
    table: Sequence[Mapping[str, Any]],
    jobs: Mapping[str, Any],
    control_dt_s: float,
) -> dict[str, Any]:
    """Assign each rollback in a run's event log to a scheduled event, or to ``unattributed``.

    Rules: a GPU fault goes to the hardware fault on that rack and slot at that
    time; a forced rack trip to the forced breaker event; an overload trip to the
    breaker derate event active on that rack; a thermal shutdown to the cooling
    failure that covers the rack.  Windows extend from the precursor start to
    one hour past the event end.  Rollback in the log carries steps; GPU-hours
    use the job's step time and shard size.
    """
    per: dict[str, dict[str, float]] = {r["event_id"]: {"lost_steps": 0.0, "lost_gpu_h": 0.0, "n_faults": 0} for r in table}
    unattr = {"lost_steps": 0.0, "lost_gpu_h": 0.0, "n_faults": 0}
    sched = [r for r in table if r["source"] == "scheduled"]
    # the simulator logs the rack trip or GPU fault first, then the job faults of the same time
    for e in events:
        if e["kind"] != "job_fault":
            continue
        job = jobs[e["job_id"]]
        shard = job.n_gpus // (2 if job.multisite else 1)
        gpu_h = float(e["lost_steps"]) * float(job.step_time_s) * shard / 3600.0
        t = float(e["t_s"])
        reason = str(e["reason"])
        chosen = None
        m = _RE_GPU.match(reason)
        if m:
            rack, slot = m.group(1), int(m.group(2))
            for r in sched:
                if r["kind"] == KIND_HARDWARE_FAULT and r["rack_id"] == rack and r["gpu_slot"] == slot and r["onset_s"] - 1e-6 <= t <= r["onset_s"] + control_dt_s + 1e-6:
                    chosen = r
        else:
            m = _RE_RACK.match(reason)
            if m:
                rack, why = m.group(1), m.group(2)
                if why == "forced":
                    for r in sched:
                        if r["kind"] == KIND_BREAKER_TRIP and r["rack_id"] == rack and r["mode"] == "forced" and r["onset_s"] - 1e-6 <= t <= r["onset_s"] + control_dt_s + 1e-6:
                            chosen = r
                elif why == "overload":
                    chosen = _latest(sched, t, lambda r: r["kind"] == KIND_BREAKER_TRIP and r["mode"] == "derate" and r["rack_id"] == rack, 3600.0)
                else:
                    chosen = _latest(sched, t, lambda r: r["kind"] == KIND_COOLING_FAILURE and rack in r["units"], 3600.0)
        bucket = unattr if chosen is None else per[chosen["event_id"]]
        bucket["lost_steps"] += float(e["lost_steps"])
        bucket["lost_gpu_h"] += gpu_h
        bucket["n_faults"] += 1
    return {"per_event": per, "unattributed": unattr}


def _latest(rows: Sequence[Mapping[str, Any]], t: float, pred: Callable[[Mapping[str, Any]], bool], slack_s: float) -> Optional[Mapping[str, Any]]:
    best = None
    for r in rows:
        if not pred(r):
            continue
        start = r["onset_s"] - max(r["precursor_lead_s"], 0.0)
        if start - 1e-6 <= t <= r["end_s"] + slack_s:
            if best is None or r["onset_s"] > best["onset_s"]:
                best = r
    return best


def curtailment_violation(res: SimResult, event: Mapping[str, Any]) -> dict[str, float]:
    """Energy (kWh) and seconds above the effective import limit at the event's site during its window."""
    run = res._run
    s = run.site_ids.index(event["site_id"])
    K = run.K
    eff = run.site_import[s] * np.repeat(run.signals.import_limit_factor[:, s], K)
    power = res.site_power_w[:, s]
    t = np.arange(power.size) * run.dt
    m = (t >= event["onset_s"] - 1e-9) & (t < event["end_s"] + 1e-9)
    over = np.maximum(power[m] - eff[m], 0.0)
    return {"violation_kwh": float(over.sum() * run.dt / 3.6e6), "violation_s": float((over > 0).sum() * run.dt)}


def throttle_slowdown_gpu_h(res: SimResult, cfg: SimConfig, rack_id: str, t0: float, t1: float, tail_s: float) -> float:
    """Approximate GPU-hours of throttled operation (clock shortfall of the rack's hottest GPU).

    Counts the fraction of the rack's GPUs below the throttle threshold clock
    times the shortfall of the clock at the rack's hottest GPU.  An approximation: it
    includes idle GPUs and uses the hottest GPU for all throttled ones.
    """
    run = res._run
    r = run.rack_ids.index(rack_id)
    times = np.arange(run.Nb) * run.cdt
    m = (times >= t0 - 1e-9) & (times < t1 + tail_s)
    frac = run.rack_throttled_b[m, r]
    hot = np.where(np.isfinite(run.rack_maxgpu_b[m, r]), run.rack_maxgpu_b[m, r], -np.inf)
    shortfall = 1.0 - cfg.throttle.clock_fraction(hot)
    return float(np.sum(frac * run.rack_n[r] * shortfall) * run.cdt / 3600.0)


# ---------------------------------------------------------------------------
# response costs
# ---------------------------------------------------------------------------


def response_costs(
    res: SimResult, jobs: Mapping[str, Any], cfg: SimConfig, meta_actions: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """GPU-hours spent by every applied controller action, joined to the controller's unit tag.

    Checkpoint: the job's GPUs stall for its checkpoint duration.  Migration:
    checkpoint stall plus WAN transfer and restore (transfer and restore are
    counted only when the simulator logged ``migration_start``).  Pause: the job's
    GPUs sit idle from the pause to the resume, to the job's next fault, or to
    the end of the run.  All from the simulator's own transfer parameters.
    """
    tr = cfg.transfer
    horizon = cfg.horizon_s
    ev = res.events
    meta_by_key: dict[tuple[float, str, str], str] = {}
    for m in meta_actions:
        meta_by_key[(float(m["t_s"]), m["action"], m["job_id"])] = m["unit"]
    started: dict[str, list[float]] = {}
    faults: dict[str, list[float]] = {}
    for e in ev:
        if e["kind"] == "migration_start":
            started.setdefault(e["job_id"], []).append(float(e["t_s"]))
        elif e["kind"] == "job_fault":
            faults.setdefault(e["job_id"], []).append(float(e["t_s"]))
    pending_pause: dict[str, tuple[float, str]] = {}
    out = []
    for a in res.actions:
        name, t, status = a["action"], float(a["t_s"]), a["status"]
        job_id = a["detail"].get("job_id")
        unit = meta_by_key.get((t, name, job_id), "")
        if status != "applied":
            out.append({"t_s": t, "action": name, "job_id": job_id, "unit": unit, "applied": False, "gpu_h": 0.0})
            continue
        job = jobs[job_id]
        n = float(job.n_gpus)
        if name == "CheckpointNow":
            cost = n * float(job.checkpoint_duration_s) / 3600.0
        elif name == "MigrateJob":
            cost = n * float(job.checkpoint_duration_s) / 3600.0
            window = float(job.checkpoint_duration_s) + cfg.control_dt_s + 1.0
            if any(0.0 <= s0 - t <= window for s0 in started.get(job_id, [])):
                cost += n * (float(tr.transfer_s(int(job.n_gpus))) + float(tr.restore_s(int(job.n_gpus)))) / 3600.0
        elif name == "PauseJob":
            pending_pause[job_id] = (t, unit)
            continue
        elif name == "ResumeJob":
            if job_id in pending_pause:
                t0, u0 = pending_pause.pop(job_id)
                end = t
                nxt = [f for f in faults.get(job_id, []) if f > t0]
                if nxt:
                    end = min(end, min(nxt))
                out.append({"t_s": t0, "action": "PauseJob", "job_id": job_id, "unit": u0, "applied": True, "gpu_h": n * max(end - t0, 0.0) / 3600.0})
            continue
        else:
            continue
        out.append({"t_s": t, "action": name, "job_id": job_id, "unit": unit, "applied": True, "gpu_h": cost})
    for job_id, (t0, u0) in pending_pause.items():
        job = jobs[job_id]
        end = horizon
        nxt = [f for f in faults.get(job_id, []) if f > t0]
        if nxt:
            end = min(end, min(nxt))
        out.append({"t_s": t0, "action": "PauseJob", "job_id": job_id, "unit": u0, "applied": True, "gpu_h": float(job.n_gpus) * max(end - t0, 0.0) / 3600.0})
    out.sort(key=lambda r: (r["t_s"], r["action"], str(r["job_id"])))
    return out


# ---------------------------------------------------------------------------
# alarms, matching, scoring
# ---------------------------------------------------------------------------


def merge_alarms(episodes: Sequence[Mapping[str, Any]], merge_gap_s: float) -> list[dict[str, Any]]:
    """Merge class episodes of the same unit that overlap or lie within ``merge_gap_s``."""
    by_unit: dict[str, list[Mapping[str, Any]]] = {}
    for e in episodes:
        by_unit.setdefault(e["unit"], []).append(e)
    out = []
    for unit, items in sorted(by_unit.items()):
        items = sorted(items, key=lambda e: e["start_s"])
        cur = None
        for e in items:
            if cur is not None and e["start_s"] <= cur["end_s"] + merge_gap_s:
                cur["end_s"] = max(cur["end_s"], e["end_s"])
                cur["classes"].add(e["class"])
                cur["episodes"].append(e)
                cur["peak_p"] = max(cur["peak_p"], e["peak_p"])
            else:
                if cur is not None:
                    out.append(cur)
                cur = {"unit": unit, "start_s": e["start_s"], "end_s": e["end_s"], "classes": {e["class"]}, "episodes": [e], "peak_p": e["peak_p"]}
        if cur is not None:
            out.append(cur)
    out.sort(key=lambda a: (a["start_s"], a["unit"]))
    return out


def match_events(
    table: Sequence[Mapping[str, Any]],
    episodes: Sequence[Mapping[str, Any]],
    settings: OutageSettings,
    min_lead_s: float = 0.0,
) -> dict[str, dict[str, Any]]:
    """Per event: earliest covering warning (lead time), or the first late warning.

    A class episode covers an event if its unit is one of the event's units, its
    class may explain the event kind, it starts at or before the onset and the
    onset is no later than its end plus the warning horizon.  The lead time is
    onset minus the episode start.  A warning that first appears after the
    onset but within one warning horizon is recorded as late.
    """
    L = settings.horizon_s
    out: dict[str, dict[str, Any]] = {}
    for ev in table:
        classes = EVENT_CLASSES[ev["kind"]]
        cand = [e for e in episodes if e["unit"] in ev["units"] and e["class"] in classes]
        covering = [e for e in cand if e["start_s"] <= ev["onset_s"] + 1e-9 and ev["onset_s"] <= e["end_s"] + L + 1e-9]
        lead = None
        if covering:
            lead = ev["onset_s"] - min(e["start_s"] for e in covering)
        late = None
        if lead is None:
            after = [e["start_s"] - ev["onset_s"] for e in cand if ev["onset_s"] < e["start_s"] <= ev["onset_s"] + L + 1e-9]
            if after:
                late = float(min(after))
        out[ev["event_id"]] = {
            "caught": lead is not None,
            "caught_in_time": lead is not None and lead >= min_lead_s,
            "lead_s": None if lead is None else float(lead),
            "late_s": late,
        }
    return out


def classify_alarms(
    alarms: Sequence[Mapping[str, Any]], table: Sequence[Mapping[str, Any]], settings: OutageSettings
) -> list[dict[str, Any]]:
    """True or false for each alarm: true if it overlaps the effect window of an event it could explain."""
    L = settings.horizon_s
    out = []
    for a in alarms:
        explained = None
        for ev in table:
            if a["unit"] not in ev["units"]:
                continue
            classes = set(EVENT_CLASSES[ev["kind"]])
            if not (set(a["classes"]) & classes):
                continue
            w0 = ev["onset_s"]
            w1 = ev["window_end_s"] + L
            if a["start_s"] <= w1 and a["end_s"] + L >= w0:
                explained = ev["event_id"]
                break
        out.append({"unit": a["unit"], "start_s": a["start_s"], "end_s": a["end_s"], "classes": sorted(a["classes"]), "peak_p": a["peak_p"],
                    "true": explained is not None, "event_id": explained})
    return out


def score_run(
    res: SimResult,
    cfg: SimConfig,
    table: Sequence[Mapping[str, Any]],
    export: Mapping[str, Any],
    settings: OutageSettings,
    reference_useful_gpu_h: float,
) -> dict[str, Any]:
    """Outcomes of one policy run on one seed (all simulated)."""
    jobs = {j.job_id: j for j in cfg.jobs}
    episodes = [e for e in export.get("episodes", []) if e["start_s"] >= 0.0]
    ckpt_max = max((float(j.checkpoint_duration_s) for j in cfg.jobs), default=0.0)
    min_lead = ckpt_max + cfg.control_dt_s
    matches = match_events(table, episodes, settings, min_lead)
    attr = attribute_faults(res.events, table, jobs, cfg.control_dt_s)
    by_event = []
    for ev in table:
        row = {k: ev[k] for k in ("event_id", "kind", "site_id", "rack_id", "onset_s", "end_s", "has_precursor", "mode", "source")}
        row.update(matches[ev["event_id"]])
        row.update(attr["per_event"][ev["event_id"]])
        row["violation_kwh"] = 0.0
        row["violation_s"] = 0.0
        row["throttle_slowdown_gpu_h"] = 0.0
        if ev["kind"] == KIND_GRID_CURTAILMENT:
            row.update(curtailment_violation(res, ev))
        if ev["kind"] == KIND_THERMAL_THROTTLE:
            row["throttle_slowdown_gpu_h"] = throttle_slowdown_gpu_h(res, cfg, ev["rack_id"], ev["onset_s"], ev["end_s"], settings.episode_merge_gap_s)
        by_event.append(row)
    costs = response_costs(res, jobs, cfg, export.get("meta_actions", []))
    alarms = classify_alarms(merge_alarms(episodes, settings.episode_merge_gap_s), table, settings)
    for a in alarms:
        lo, hi = a["start_s"], a["end_s"] + settings.decision_interval_s * settings.clear_decisions
        mine = [c for c in costs if c["unit"] == a["unit"] and lo - 1e-9 <= c["t_s"] <= hi + 1e-9]
        a["cost_gpu_h"] = float(sum(c["gpu_h"] for c in mine))
        a["n_actions"] = len(mine)
    summary = res.summary()
    by_action: dict[str, float] = {}
    n_actions: dict[str, int] = {}
    rejected = 0
    for c in costs:
        if not c["applied"]:
            rejected += 1
            continue
        by_action[c["action"]] = by_action.get(c["action"], 0.0) + c["gpu_h"]
        n_actions[c["action"]] = n_actions.get(c["action"], 0) + 1
    total_cost = float(sum(by_action.values()))
    false_cost = float(sum(a["cost_gpu_h"] for a in alarms if not a["true"]))
    days = (cfg.horizon_s - settings.warmup_s) / 86400.0
    total_viol = float(np.sum(res.import_violation["energy_above_kwh"]))
    return {
        "policy": export.get("policy"),
        "data_kind": "simulated",
        "summary": {
            "useful_gpu_hours": summary["useful_gpu_hours"], "lost_gpu_hours": summary["lost_gpu_hours"],
            "lost_steps": summary["lost_steps"], "job_faults": summary["job_faults"], "migrations": summary["migrations"],
            "import_energy_above_kwh": total_viol, "jobs_done": summary["jobs_done"], "thermal_shutdowns": summary["thermal_shutdowns"],
            "breaker_trips": summary["breaker_trips"], "throttle_episodes": summary["throttle_episodes"],
        },
        "deficit_gpu_h": float(reference_useful_gpu_h - summary["useful_gpu_hours"]),
        "by_event": by_event,
        "unattributed": attr["unattributed"],
        "alarms": alarms,
        "response": {
            "gpu_h_by_action": by_action, "n_actions": n_actions, "rejected": rejected, "total_gpu_h": total_cost,
            "false_alarm_gpu_h": false_cost, "n_alarms": len(alarms), "n_false_alarms": sum(1 for a in alarms if not a["true"]),
            "false_alarms_per_day": sum(1 for a in alarms if not a["true"]) / days, "evaluated_days": days,
        },
        "min_lead_s": min_lead,
    }


# ---------------------------------------------------------------------------
# threshold tuning and sweep on recorded traces
# ---------------------------------------------------------------------------


def replay_objective(
    table: Sequence[Mapping[str, Any]],
    reactive_by_event: Sequence[Mapping[str, Any]],
    episodes: Sequence[Mapping[str, Any]],
    trace: Mapping[str, Any],
    index: SeriesIndex,
    settings: OutageSettings,
    min_lead_s: float,
) -> dict[str, float]:
    """Replay estimate of total loss (GPU-hours) for one warning rule on one recorded trace.

    Misses cost what the reactive run lost on the event (rollback work); every
    alarm costs the checkpoint of non-flexible jobs on its rack at its start,
    re-done every ``recheckpoint_s``, plus the move of flexible jobs.  Events
    with no rollback (curtailment, throttle) add no miss cost.  This is an
    approximation used only to choose a threshold on training seeds; closed-loop
    runs report the realized numbers.
    """
    matches = match_events(table, episodes, settings, min_lead_s)
    lost = {r["event_id"]: float(r["lost_gpu_h"]) for r in reactive_by_event}
    miss = float(sum(lost.get(ev["event_id"], 0.0) for ev in table if not matches[ev["event_id"]]["caught_in_time"]))
    times = np.asarray(trace["times_s"])
    alarm_cost = 0.0
    for a in merge_alarms(episodes, settings.episode_merge_gap_s):
        d0 = int(np.argmin(np.abs(times - a["start_s"])))
        dur = a["end_s"] - a["start_s"]
        if a["unit"] in index.rack_ids:
            r = index.rack_ids.index(a["unit"])
            alarm_cost += float(trace["rack_flex_move_gpu_h"][d0, r])
            alarm_cost += float(trace["rack_nonflex_checkpoint_gpu_h"][d0, r]) * (1 + math.floor(dur / settings.recheckpoint_s))
        else:
            s = index.site_ids.index(a["unit"])
            alarm_cost += float(trace["site_flex_move_gpu_h"][d0, s])
    return {"miss_gpu_h": miss, "alarm_gpu_h": float(alarm_cost), "total_gpu_h": miss + float(alarm_cost)}


def detection_stats(
    table: Sequence[Mapping[str, Any]],
    episodes: Sequence[Mapping[str, Any]],
    settings: OutageSettings,
    evaluated_days: float,
    min_lead_s: float,
) -> dict[str, Any]:
    """Recall, false alarms and lead times of one warning rule on one seed (no actions)."""
    matches = match_events(table, episodes, settings, min_lead_s)
    alarms = classify_alarms(merge_alarms(episodes, settings.episode_merge_gap_s), table, settings)
    by_kind: dict[str, dict[str, Any]] = {}
    for ev in table:
        m = matches[ev["event_id"]]
        b = by_kind.setdefault(ev["kind"], {"n": 0, "caught": 0, "caught_in_time": 0, "leads_s": []})
        b["n"] += 1
        b["caught"] += int(m["caught"])
        b["caught_in_time"] += int(m["caught_in_time"])
        if m["lead_s"] is not None:
            b["leads_s"].append(m["lead_s"])
    return {
        "by_kind": by_kind,
        "n_alarms": len(alarms),
        "n_false_alarms": sum(1 for a in alarms if not a["true"]),
        "false_alarms_per_day": sum(1 for a in alarms if not a["true"]) / evaluated_days,
    }


# ---------------------------------------------------------------------------
# aggregation with seed-bootstrap intervals
# ---------------------------------------------------------------------------


def bootstrap_ci(values: Sequence[float], n_resamples: int, seed: int = 0, stat: Callable[[np.ndarray], float] = np.mean) -> dict[str, Any]:
    """Percentile 95 percent interval of ``stat`` over seeds (resampling seeds)."""
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    if v.size == 0:
        return {"mean": None, "lo": None, "hi": None, "n": 0}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, v.size, size=(n_resamples, v.size))
    boots = np.array([stat(v[i]) for i in idx])
    return {"mean": float(stat(v)), "lo": float(np.quantile(boots, 0.025)), "hi": float(np.quantile(boots, 0.975)), "n": int(v.size)}


def ratio_ci(num: Sequence[float], den: Sequence[float], n_resamples: int, seed: int = 0) -> dict[str, Any]:
    """Pooled ratio (sum num / sum den) with a seed-cluster bootstrap interval."""
    n = np.asarray(num, dtype=float)
    d = np.asarray(den, dtype=float)
    if n.size == 0 or d.sum() == 0:
        return {"value": None, "lo": None, "hi": None, "n_seeds": int(n.size), "den": float(d.sum())}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n.size, size=(n_resamples, n.size))
    den_b = d[idx].sum(axis=1)
    ok = den_b > 0
    boots = n[idx].sum(axis=1)[ok] / den_b[ok]
    return {"value": float(n.sum() / d.sum()), "lo": float(np.quantile(boots, 0.025)), "hi": float(np.quantile(boots, 0.975)),
            "n_seeds": int(n.size), "den": float(d.sum())}


def pooled_quantile_ci(per_seed: Sequence[Sequence[float]], q: float, n_resamples: int, seed: int = 0) -> dict[str, Any]:
    """Quantile of values pooled over seeds, with a seed-cluster bootstrap interval."""
    flat = [x for s in per_seed for x in s]
    if not flat:
        return {"value": None, "lo": None, "hi": None, "n": 0}
    rng = np.random.default_rng(seed)
    k = len(per_seed)
    boots = []
    for _ in range(n_resamples):
        pick = rng.integers(0, k, size=k)
        pool = [x for i in pick for x in per_seed[i]]
        if pool:
            boots.append(np.quantile(pool, q))
    return {"value": float(np.quantile(flat, q)), "lo": float(np.quantile(boots, 0.025)) if boots else None,
            "hi": float(np.quantile(boots, 0.975)) if boots else None, "n": len(flat)}


def aggregate_runs(runs: Sequence[Mapping[str, Any]], settings: OutageSettings, has_warnings: bool = True) -> dict[str, Any]:
    """Pool per-seed ``score_run`` outputs of one policy into overall and per-event-type statistics.

    ``has_warnings`` is False for policies without a warning rule (reactive,
    averaging rule alone); their detection fields (recall, lead time, alarm
    counts) are reported as ``None`` instead of zero.
    """
    B = settings.bootstrap_resamples
    out: dict[str, Any] = {"n_seeds": len(runs), "data_kind": "simulated", "has_warnings": bool(has_warnings)}

    def per_seed(fn: Callable[[Mapping[str, Any]], float]) -> list[float]:
        return [fn(r) for r in runs]

    out["overall"] = {
        "deficit_gpu_h": bootstrap_ci(per_seed(lambda r: r["deficit_gpu_h"]), B, 1),
        "useful_gpu_h": bootstrap_ci(per_seed(lambda r: r["summary"]["useful_gpu_hours"]), B, 2),
        "lost_gpu_h": bootstrap_ci(per_seed(lambda r: r["summary"]["lost_gpu_hours"]), B, 3),
        "lost_steps": bootstrap_ci(per_seed(lambda r: r["summary"]["lost_steps"]), B, 4),
        "import_energy_above_kwh": bootstrap_ci(per_seed(lambda r: r["summary"]["import_energy_above_kwh"]), B, 5),
        "response_gpu_h": bootstrap_ci(per_seed(lambda r: r["response"]["total_gpu_h"]), B, 6),
        "false_alarm_gpu_h": bootstrap_ci(per_seed(lambda r: r["response"]["false_alarm_gpu_h"]), B, 7),
        "false_alarms_per_day": bootstrap_ci(per_seed(lambda r: r["response"]["false_alarms_per_day"]), B, 8),
        "n_alarms": bootstrap_ci(per_seed(lambda r: r["response"]["n_alarms"]), B, 9),
        "job_faults": bootstrap_ci(per_seed(lambda r: r["summary"]["job_faults"]), B, 10),
        "migrations": bootstrap_ci(per_seed(lambda r: r["summary"]["migrations"]), B, 11),
    }
    n_ev = [len(r["by_event"]) for r in runs]
    caught = [sum(1 for e in r["by_event"] if e["caught"]) for r in runs]
    in_time = [sum(1 for e in r["by_event"] if e["caught_in_time"]) for r in runs]
    out["overall"]["recall"] = ratio_ci(caught, n_ev, B, 12)
    out["overall"]["recall_in_time"] = ratio_ci(in_time, n_ev, B, 13)
    leads = [[e["lead_s"] / 60.0 for e in r["by_event"] if e["lead_s"] is not None] for r in runs]
    out["overall"]["lead_minutes"] = {
        "median": pooled_quantile_ci(leads, 0.5, B, 14), "p10": pooled_quantile_ci(leads, 0.1, B, 15),
        "p90": pooled_quantile_ci(leads, 0.9, B, 16),
    }
    alarms_true = [sum(1 for a in r["alarms"] if a["true"]) for r in runs]
    alarms_all = [len(r["alarms"]) for r in runs]
    out["overall"]["alarm_precision"] = ratio_ci(alarms_true, alarms_all, B, 17)
    by_type: dict[str, Any] = {}
    for kind in EVENT_TYPES:
        sel = [[e for e in r["by_event"] if e["kind"] == kind] for r in runs]
        n_k = [len(s) for s in sel]
        if sum(n_k) == 0:
            continue
        entry: dict[str, Any] = {
            "n_events": int(sum(n_k)),
            "n_with_precursor": int(sum(1 for s in sel for e in s if e["has_precursor"])),
            "recall": ratio_ci([sum(1 for e in s if e["caught"]) for s in sel], n_k, B, 20),
            "recall_in_time": ratio_ci([sum(1 for e in s if e["caught_in_time"]) for s in sel], n_k, B, 21),
            "lead_minutes_median": pooled_quantile_ci([[e["lead_s"] / 60.0 for e in s if e["lead_s"] is not None] for s in sel], 0.5, B, 22),
            "lost_gpu_h": bootstrap_ci([sum(e["lost_gpu_h"] for e in s) for s in sel], B, 23),
            "lost_steps": bootstrap_ci([sum(e["lost_steps"] for e in s) for s in sel], B, 24),
        }
        if kind == KIND_GRID_CURTAILMENT:
            entry["violation_kwh"] = bootstrap_ci([sum(e["violation_kwh"] for e in s) for s in sel], B, 25)
            entry["violation_s"] = bootstrap_ci([sum(e["violation_s"] for e in s) for s in sel], B, 26)
        if kind == KIND_THERMAL_THROTTLE:
            entry["throttle_slowdown_gpu_h"] = bootstrap_ci([sum(e["throttle_slowdown_gpu_h"] for e in s) for s in sel], B, 27)
        by_type[kind] = entry
    out["by_event_type"] = by_type
    # events with no precursor
    nop = [[e for e in r["by_event"] if not e["has_precursor"] and e["source"] == "scheduled"] for r in runs]
    n_nop = [len(s) for s in nop]
    out["no_precursor"] = {
        "n_events": int(sum(n_nop)),
        "lost_gpu_h": bootstrap_ci([sum(e["lost_gpu_h"] for e in s) for s in nop], B, 30),
        "lost_steps": bootstrap_ci([sum(e["lost_steps"] for e in s) for s in nop], B, 31),
        "recall": ratio_ci([sum(1 for e in s if e["caught"]) for s in nop], n_nop, B, 32),
        "lost_gpu_h_per_event": (float(sum(e["lost_gpu_h"] for s in nop for e in s) / max(sum(n_nop), 1))),
    }
    prec = [[e for e in r["by_event"] if e["has_precursor"] and e["source"] == "scheduled"] for r in runs]
    n_p = [len(s) for s in prec]
    out["with_precursor"] = {
        "n_events": int(sum(n_p)),
        "lost_gpu_h": bootstrap_ci([sum(e["lost_gpu_h"] for e in s) for s in prec], B, 33),
        "recall": ratio_ci([sum(1 for e in s if e["caught"]) for s in prec], n_p, B, 34),
        "lost_gpu_h_per_event": (float(sum(e["lost_gpu_h"] for s in prec for e in s) / max(sum(n_p), 1))),
    }
    out["unattributed_lost_gpu_h"] = bootstrap_ci([r["unattributed"]["lost_gpu_h"] for r in runs], B, 35)
    if not has_warnings:
        for key in ("recall", "recall_in_time", "lead_minutes", "alarm_precision", "false_alarms_per_day", "false_alarm_gpu_h", "n_alarms"):
            out["overall"][key] = None
        for entry in by_type.values():
            for key in ("recall", "recall_in_time", "lead_minutes_median"):
                entry[key] = None
        out["no_precursor"]["recall"] = None
        out["with_precursor"]["recall"] = None
    return out


def paired_difference(a: Sequence[float], b: Sequence[float], n_resamples: int, seed: int = 0) -> dict[str, Any]:
    """Mean of ``a - b`` over seeds (paired) with a bootstrap interval."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    return bootstrap_ci(list(d), n_resamples, seed)


def file_sha256(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


__all__ = [
    "Alarm", "Calibration", "ChannelBank", "EpisodeTracker", "ForecastWarningController", "OracleAlarm", "OracleController",
    "OutageRun", "OutageSettings", "PersistenceForecaster", "PlacementView", "ResponsePlanner", "SeriesIndex", "TraceRecorder",
    "aggregate_runs", "attribute_faults", "bootstrap_ci", "build_event_table", "calibrate", "classify_alarms",
    "curtailment_violation", "deep_merge", "detection_stats", "episodes_from_pmax", "exceedance_probability", "job_costs",
    "load_outage_scenario", "match_events", "oracle_scenario", "oracle_settings", "merge_alarms", "openloop_pmax", "oracle_alarms_from_reference",
    "paired_difference", "periodic_local_jobs", "replay_objective", "response_costs", "run_policy", "score_run",
    "seed_scenario", "series_limits", "throttle_episodes", "throttle_slowdown_gpu_h", "window_probabilities",
]
