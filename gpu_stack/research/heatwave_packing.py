"""Power-cap packing with forecast quantiles and a learned quantile-choice policy (e003, task T06a).

Everything this module produces is SIMULATED (it drives the e003 simulator in
``heatwave_sim``).  Nothing here is a claim about a real cluster.

The decision
------------
A site has a power cap.  Jobs arrive and wait in a queue.  Every decision
interval (``decision_interval_s``, 300 s in the v1 scenario) the controller
forecasts the site power over the next ``forecast_horizon_bins * bin_s`` seconds
(1 h in v1) for the running set plus a candidate job, and admits the candidate
if the PLANNED power stays under the cap at every step of the horizon.
"Planned" means the forecast quantile ``q``: a low ``q`` packs more jobs and
risks cap violations, a high ``q`` is safe and strands power.

Site power model (shared by every policy)
-----------------------------------------
Forecasters see a dimensionless ratio series, not watts::

    s(t) = P_site(t) / (idle_w + beta * busy_gpus(t))

``idle_w`` and ``beta`` come from a commissioning calibration run of the same
simulator (:func:`calibrate_sites`): site power with every GPU idle and with
every GPU running a training job, at the scenario's design outdoor
temperature (``cap.design_outdoor_c``), so ``s = 1`` on a design-temperature day.  ``beta = (full_w - idle_w) / n_gpus`` is a telemetry-derived
estimate of the power a newly admitted GPU adds (no nameplate value is used).
The ratio ``s`` carries what the affine model cannot: cooling overhead as the
outdoor temperature moves, throttling, faults, phase and noise.  A forecaster
produces 21 quantile paths of ``s``; the planned power for a set of jobs is::

    planned_q(h) = (idle_w + beta * busy_plan(h)) * s_q(h)

``busy_plan(h)`` drops a running job after the last bin it overlaps (users
declare GPU count and walltime at submission, as in a batch scheduler; the
remaining walltime is stretched by the checkpoint overhead implied by the job
generator's ranges, :func:`declared_checkpoint_overhead`, and a job counts in
every bin it overlaps because the cap applies to peak power, not bin means).  Every forecaster goes through this same rule, so differences
between policies come from the forecast of ``s`` and from the choice of ``q``.
The model treats a candidate as adding the fleet-average increment per GPU, so
the candidate's own power is not forecast separately.

Policies
--------
* ``FixedQ(q)``: the same level for every decision (q on the 21-level grid).
* ``RandomQ``: uniform level per situation (exploration for training data).
* ``LearnedQ``: a cost-sensitive model that maps situation features to a level
  (:class:`CostSensitiveModel`).
* reactive: no forecast; admits if measured power plus the estimated increment
  fits and throttles racks on a violation.
* oracle: the realized ratio path from a reference run (perfect foresight).

Training signal for the learned policy
--------------------------------------
For a logged situation (decision time, candidate, forecast) and each level
``k`` the rule gives an admit/refuse decision ``d_k``.  Its value over the
reward window is ``d * V - penalty * E_over(d)`` with ``V`` the candidate's
value over the window and ``E_over`` the energy above the cap in the window,
computed from the logged realized ratio path with the candidate's power added
or removed linearly (:func:`hindsight_costs`).  This is a myopic, additive
surrogate: later decisions are not re-played.  Evaluation never uses it: the
held-out episodes are run through the full simulator.

Violation measures use the simulator's control-step power samples
(``base_dt_s`` in the scenario, 10 s in v1), not 1 s samples.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np

from .heatwave_events import random_schedule
from .heatwave_sim import (
    AdmitJob,
    DeferJob,
    Job,
    ReactiveSiteCapController,
    SiteEnvironment,
    VisibleState,
    generate_jobs,
    run_scenario,
    synthetic_environment,
)

PACKING_SCHEMA = "gpu-stack.e003-heatwave-packing-scenario.v1"
RESULT_SCHEMA = "gpu-stack.e003-heatwave-packing-result.v1"

# Must equal heatwave.forecast.QUANTILE_LEVELS (the runner asserts this).
QUANTILE_LEVELS: tuple[float, ...] = (
    0.01, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
    0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99,
)
N_LEVELS = len(QUANTILE_LEVELS)
MEDIAN_INDEX = QUANTILE_LEVELS.index(0.5)
SLACK_FEATURE_INDICES = (5, 10, 15, 18, 19, 20)
FEATURE_NAMES = (
    "spread_rel", "value_per_gpu_hour", "log_penalty", "headroom_rel", "size_rel",
    "tod_sin", "tod_cos", "trend_rel",
) + tuple(f"slack_q{int(round(QUANTILE_LEVELS[i] * 100)):02d}" for i in SLACK_FEATURE_INDICES)
N_FEATURES = len(FEATURE_NAMES)


def level_index(q: float) -> int:
    """Index of ``q`` on the 21-level grid."""
    for i, level in enumerate(QUANTILE_LEVELS):
        if abs(level - q) < 1e-9:
            return i
    raise ValueError(f"q={q} is not on the 21-level grid")


# ---------------------------------------------------------------------------
# Scenario and calibration
# ---------------------------------------------------------------------------


def load_packing_scenario(path: str | Path) -> dict[str, Any]:
    sc = json.loads(Path(path).read_text())
    if sc.get("schema") != PACKING_SCHEMA:
        raise ValueError(f"packing scenario schema must be {PACKING_SCHEMA!r}")
    if sc.get("data_kind") != "simulated":
        raise ValueError("packing scenario data_kind must be 'simulated'")
    ep = sc["episode"]
    for key in ("horizon_s", "warmup_s", "base_dt_s", "control_dt_s", "controller_interval_s",
                "decision_interval_s", "forecast_bin_s", "forecast_horizon_bins"):
        if key not in ep:
            raise ValueError(f"episode.{key} is required")
    if ep["warmup_s"] >= ep["horizon_s"]:
        raise ValueError("warmup_s must be shorter than horizon_s")
    for key in ("decision_interval_s", "forecast_bin_s", "warmup_s", "horizon_s"):
        if abs(ep[key] / ep["controller_interval_s"] - round(ep[key] / ep["controller_interval_s"])) > 1e-9:
            raise ValueError(f"episode.{key} must be a multiple of controller_interval_s")
    if abs(ep["decision_interval_s"] - ep["forecast_bin_s"]) > 1e-9:
        raise ValueError("decision_interval_s must equal forecast_bin_s")
    if abs(sc["cap"]["load_fraction"]) > 1.5 or sc["cap"]["load_fraction"] <= 0:
        raise ValueError("cap.load_fraction must be in (0, 1.5]")
    return sc


@dataclass(frozen=True)
class SiteModel:
    """Calibrated affine site-power model (simulated).  Watts at the reference outdoor temperature."""

    site_id: str
    n_gpus: int
    idle_w: float
    full_w: float
    cap_w: float
    utc_offset_h: float

    @property
    def beta_w_per_gpu(self) -> float:
        return (self.full_w - self.idle_w) / self.n_gpus

    def base_power(self, busy: Any) -> Any:
        return self.idle_w + self.beta_w_per_gpu * np.asarray(busy, dtype=float)

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id, "n_gpus": self.n_gpus, "idle_w": self.idle_w, "full_w": self.full_w,
            "cap_w": self.cap_w, "beta_w_per_gpu": self.beta_w_per_gpu, "utc_offset_h": self.utc_offset_h,
        }


def _constant_environment(sim_scenario: Mapping[str, Any], horizon_s: float, outdoor_c: float) -> dict[str, SiteEnvironment]:
    n = int(round(horizon_s / 3600.0)) + 1
    out = {}
    for item in sim_scenario["sites"]:
        out[item["site"]["site_id"]] = SiteEnvironment(
            outdoor_c=np.full(n, float(outdoor_c)), price_usd_per_kwh=np.full(n, 0.1), carbon_g_per_kwh=np.full(n, 400.0)
        )
    return out


def _calibration_scenario(sim_scenario: Mapping[str, Any], episode: Mapping[str, Any], horizon_s: float) -> dict[str, Any]:
    sc = copy.deepcopy(dict(sim_scenario))
    sc["horizon_s"] = float(horizon_s)
    sc["base_dt_s"] = float(episode["base_dt_s"])
    sc["control_dt_s"] = float(episode["control_dt_s"])
    sc["controller_interval_s"] = float(episode["controller_interval_s"])
    sc["events"] = []
    sc["outputs"] = {"gpu_windows": []}
    sc["jobs"] = {"list": []}
    return sc


def _site_loaded_jobs(sim_scenario: Mapping[str, Any], busy_fraction: float, horizon_s: float) -> list[Job]:
    jobs = []
    for item in sim_scenario["sites"]:
        site = item["site"]
        n = max(1, int(round(site["accelerator_count"] * busy_fraction)))
        jobs.append(
            Job(
                job_id=f"cal-{site['site_id']}", n_gpus=n, submit_s=0.0, start_s=0.0, duration_s=10.0 * horizon_s,
                step_time_s=4.0, checkpoint_every_s=10.0 * horizon_s, checkpoint_duration_s=0.0,
                value_per_gpu_hour=1.0, flexible=False, site_id=site["site_id"],
            )
        )
    return jobs


def _settled_mean_power(sim_scenario, episode, horizon_s, busy_fraction, settle_fraction, seed, outdoor_c) -> np.ndarray:
    sc = _calibration_scenario(sim_scenario, episode, horizon_s)
    env = _constant_environment(sc, horizon_s, outdoor_c)
    jobs = _site_loaded_jobs(sc, busy_fraction, horizon_s) if busy_fraction > 0 else []
    res = run_scenario(sc, controller=None, seed=seed, environment=env, jobs=jobs)
    n0 = int(res.site_power_w.shape[0] * (1.0 - settle_fraction))
    return res.site_power_w[n0:].mean(axis=0)


def calibrate_sites(sim_scenario: Mapping[str, Any], packing: Mapping[str, Any]) -> dict[str, Any]:
    """Commissioning calibration: idle and full-load site power at the reference outdoor temperature.

    Runs the simulator with no events and a constant outdoor temperature equal
    to ``cap.design_outdoor_c`` (no jobs, then one all-GPU job per site), and
    sets each site's cap at ``idle + cap.load_fraction * (full - idle)``.  Also
    runs a half-loaded check and reports how far the affine model is from it.
    """
    ep = packing["episode"]
    cal = packing["cap"]["calibration"]
    seed = int(packing["seeds"]["calibration"])
    ref_c = float(packing["cap"]["design_outdoor_c"])
    idle = _settled_mean_power(sim_scenario, ep, cal["idle_hours"] * 3600.0, 0.0, 0.5, seed, ref_c)
    full = _settled_mean_power(sim_scenario, ep, cal["full_hours"] * 3600.0, 1.0, 0.5, seed, ref_c)
    half = _settled_mean_power(sim_scenario, ep, cal["full_hours"] * 3600.0, 0.5, 0.5, seed, ref_c)
    frac = float(packing["cap"]["load_fraction"])
    env_spec = sim_scenario["environment"]["synthetic"]["sites"]
    models = {}
    rows = []
    for i, item in enumerate(sim_scenario["sites"]):
        site = item["site"]
        sid = site["site_id"]
        n = int(site["accelerator_count"])
        cap = float(idle[i] + frac * (full[i] - idle[i]))
        models[sid] = SiteModel(sid, n, float(idle[i]), float(full[i]), cap, float(env_spec[sid].get("utc_offset_h", 0.0)))
        busy_half = max(1, int(round(n * 0.5)))
        pred = float(idle[i] + (full[i] - idle[i]) / n * busy_half)
        rows.append({
            "site_id": sid, "busy_gpus": busy_half, "measured_w": float(half[i]), "affine_prediction_w": pred,
            "relative_error": float((pred - half[i]) / half[i]),
        })
    return {
        "data_kind": "simulated",
        "design_outdoor_c": ref_c,
        "cap_load_fraction": frac,
        "sites": {sid: m.to_dict() for sid, m in models.items()},
        "half_load_check": rows,
        "models": models,
    }


# ---------------------------------------------------------------------------
# Episodes
# ---------------------------------------------------------------------------


@dataclass
class Episode:
    seed: int
    scenario: dict[str, Any]
    jobs: list[Job]
    environment: dict[str, SiteEnvironment]
    models: dict[str, SiteModel]
    hour0_local: tuple[float, ...]
    draws: dict[str, Any] = field(default_factory=dict)


def build_episode(
    packing: Mapping[str, Any],
    sim_scenario: Mapping[str, Any],
    models: Mapping[str, SiteModel],
    seed: int,
) -> Episode:
    """One seeded episode: caps, job queue, outdoor series (with a heat wave draw) and event draws."""
    ep = packing["episode"]
    horizon = float(ep["horizon_s"])
    sc = copy.deepcopy(dict(sim_scenario))
    sc["horizon_s"] = horizon
    sc["base_dt_s"] = float(ep["base_dt_s"])
    sc["control_dt_s"] = float(ep["control_dt_s"])
    sc["controller_interval_s"] = float(ep["controller_interval_s"])
    sc["outputs"] = {"gpu_windows": []}
    sc["jobs"] = {"list": []}
    start_hour = float(ep.get("start_hour_utc", 0.0))
    sc["start_utc"] = f"2026-07-06T{int(start_hour):02d}:00:00Z"
    site_ids = [item["site"]["site_id"] for item in sc["sites"]]
    for item in sc["sites"]:
        item["site"]["power_cap_w"] = models[item["site"]["site_id"]].cap_w

    rng = np.random.default_rng([int(seed), 11])
    sub = [int(x) for x in rng.integers(0, 2**31 - 1, size=4)]

    jspec = dict(packing["jobs"]["generate"])
    total_gpus = sum(models[s].n_gpus for s in site_ids)
    for key in ("duration_range_s", "checkpoint_every_range_s", "checkpoint_duration_range_s", "value_range"):
        jspec[key] = tuple(jspec[key])
    jobs = generate_jobs(seed=sub[0], horizon_s=horizon, total_gpus=total_gpus, site_ids=(), **jspec)

    env_spec = copy.deepcopy(sim_scenario["environment"]["synthetic"])
    env_spec["start_hour_utc"] = start_hour
    hw = packing["heatwave_draw"]
    draws: dict[str, Any] = {"heatwaves": {}}
    base_center = float(rng.uniform(*hw["center_h_range"]))
    for k, sid in enumerate(site_ids):
        center = base_center + float(hw["site_offset_h"]) * k
        width = float(rng.uniform(*hw["width_h_range"]))
        add_c = float(rng.uniform(*hw["add_c_range"]))
        env_spec["sites"][sid]["outdoor"]["heatwaves"] = [{"center_h": center, "width_h": width, "add_c": add_c}]
        draws["heatwaves"][sid] = {"center_h": center, "width_h": width, "add_c": add_c}
    environment = synthetic_environment(env_spec, site_ids, horizon, sub[1])

    evs = packing["events"]
    site_racks = {item["site"]["site_id"]: [(r["rack_id"], r["n_gpus"]) for r in item["racks"]] for item in sc["sites"]}
    schedule = random_schedule(
        seed=sub[2], horizon_s=horizon, site_racks=site_racks,
        rates_per_day=evs["rates_per_day"], precursor_probability=evs["precursor_probability"],
        lead_range_s=tuple(evs["lead_range_s"]),
        strength_ranges={k: tuple(v) for k, v in evs["strength_ranges"].items()},
        duration_range_s=tuple(evs["duration_range_s"]), remaining_capacity_range=tuple(evs["remaining_capacity_range"]),
        derate_range=tuple(evs["derate_range"]), limit_fraction_range=tuple(evs["limit_fraction_range"]),
        repair_range_s=tuple(evs["repair_range_s"]),
    )
    sc["events"] = [e.to_dict() for e in schedule.events]
    draws["n_events"] = len(schedule.events)
    draws["sim_seed"] = sub[3]
    hour0 = tuple(
        float(env_spec.get("start_hour_utc", 0.0)) + float(env_spec["sites"][sid].get("utc_offset_h", 0.0)) for sid in site_ids
    )
    return Episode(int(seed), sc, list(jobs), environment, dict(models), hour0, draws)


def run_episode(episode: Episode, controller: Any):
    """Run one episode in the simulator (simulated data).  Returns the ``SimResult``."""
    return run_scenario(
        episode.scenario, controller=controller, seed=int(episode.draws["sim_seed"]),
        environment=episode.environment, jobs=episode.jobs,
    )


# ---------------------------------------------------------------------------
# Q-choice policies
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Situation:
    """What a policy sees when it must pick a quantile level for one candidate."""

    features: np.ndarray   # (N_FEATURES,)
    slack: np.ndarray      # (N_LEVELS,) relative headroom if admitted at each level (>= 0 means it fits)
    value_per_gpu_hour: float
    penalty_usd_per_kwh: float


class FixedQ:
    def __init__(self, q: float) -> None:
        self.index = level_index(q)
        self.q = float(q)
        self.name = f"fixed-q{q:g}"

    def choose(self, situation: Situation) -> int:
        return self.index


class RandomQ:
    """Uniform level per situation (exploration policy for the training episodes)."""

    name = "random-q"

    def __init__(self, seed: int) -> None:
        self._rng = np.random.default_rng([int(seed), 77])

    def choose(self, situation: Situation) -> int:
        return int(self._rng.integers(N_LEVELS))


class LearnedQ:
    def __init__(self, model: "CostSensitiveModel", name: str = "learned-q") -> None:
        self.model = model
        self.name = name

    def choose(self, situation: Situation) -> int:
        return int(self.model.choose(situation.features))


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


def declared_checkpoint_overhead(packing: Mapping[str, Any]) -> float:
    """Expected fraction of extra wall time from checkpoint stalls, from the job generator's ranges.

    A cluster operator knows the checkpoint cadence policy of its users; the
    controller uses this single number to stretch a job's declared walltime
    (mean checkpoint duration over mean checkpoint interval).
    """
    g = packing["jobs"]["generate"]
    return float(np.mean(g["checkpoint_duration_range_s"]) / np.mean(g["checkpoint_every_range_s"]))


@dataclass(frozen=True)
class PackingSettings:
    decision_interval_s: float
    bin_s: float
    horizon_bins: int
    context_bins: int
    min_context_bins: int
    warmup_s: float
    call_s: float
    reward_window_s: float
    queue_order: str
    horizon_s: float
    reactive_margin: float
    warm_ratio_bins: int
    walltime_overhead: float = 0.0
    end_rule: str = "overlap"

    @classmethod
    def from_scenario(cls, packing: Mapping[str, Any]) -> "PackingSettings":
        ep = packing["episode"]
        return cls(
            decision_interval_s=float(ep["decision_interval_s"]), bin_s=float(ep["forecast_bin_s"]),
            horizon_bins=int(ep["forecast_horizon_bins"]), context_bins=int(ep["context_bins"]),
            min_context_bins=int(ep["min_context_bins"]), warmup_s=float(ep["warmup_s"]),
            call_s=float(ep["controller_interval_s"]), reward_window_s=float(packing["reward_window_s"]),
            queue_order=str(packing["queue_order"]), horizon_s=float(ep["horizon_s"]),
            reactive_margin=float(packing["reactive"]["margin"]), warm_ratio_bins=int(ep["warm_ratio_bins"]),
            walltime_overhead=declared_checkpoint_overhead(packing), end_rule=str(ep.get("end_rule", "overlap")),
        )


class PackingController:
    """Admission controller for the e003 simulator.

    ``mode`` is ``'forecast'`` (a forecaster plus a q policy), ``'oracle'``
    (``oracle_ratio`` supplies the realized ratio path, shape ``(S, n_bins)``),
    or ``'reactive'`` (measured power, throttling).  ``forecast_refresh_bins = k > 1``
    calls the forecaster only every ``k``-th decision (with horizon ``H + k - 1``)
    and serves the decisions in between from the same paths, shifted by the
    elapsed bins (used for the slow classical baselines).  All jobs are held back
    with ``DeferJob`` the first time they are seen and released with
    ``AdmitJob``.  Every candidate evaluation before ``warmup_s`` uses the same
    warm-up rule in every forecast mode: a flat ratio equal to the largest of
    the last ``warm_ratio_bins`` observed ratio bins (1.0 before any).
    """

    def __init__(
        self,
        jobs: Sequence[Job],
        models: Mapping[str, SiteModel],
        site_ids: Sequence[str],
        settings: PackingSettings,
        hour0_local: Sequence[float],
        mode: str = "forecast",
        forecaster: Any = None,
        policy: Any = None,
        penalty_usd_per_kwh: float = 10.0,
        use_covariates: bool = False,
        oracle_ratio: Optional[np.ndarray] = None,
        log_situations: bool = False,
        forecast_refresh_bins: int = 1,
    ) -> None:
        if mode not in ("forecast", "oracle", "reactive"):
            raise ValueError("mode must be 'forecast', 'oracle' or 'reactive'")
        if mode == "forecast" and (forecaster is None or policy is None):
            raise ValueError("forecast mode needs a forecaster and a policy")
        if mode == "oracle" and oracle_ratio is None:
            raise ValueError("oracle mode needs oracle_ratio")
        self.cfg = settings
        self.mode = mode
        self.forecaster = forecaster
        self.policy = policy
        self.penalty = float(penalty_usd_per_kwh)
        self.use_covariates = bool(use_covariates)
        self.oracle_ratio = None if oracle_ratio is None else np.asarray(oracle_ratio, dtype=float)
        self.log_situations = bool(log_situations)
        if int(forecast_refresh_bins) < 1:
            raise ValueError("forecast_refresh_bins must be >= 1")
        self.refresh = int(forecast_refresh_bins)
        self._cache: Optional[tuple[float, np.ndarray]] = None
        self.site_ids = tuple(site_ids)
        self.S = len(self.site_ids)
        self.models = [models[s] for s in self.site_ids]
        self.idle = np.array([m.idle_w for m in self.models])
        self.beta = np.array([m.beta_w_per_gpu for m in self.models])
        self.cap = np.array([m.cap_w for m in self.models])
        self.hour0 = np.asarray(hour0_local, dtype=float)
        self.job_by_id = {j.job_id: j for j in jobs}
        self._known: set[str] = set()
        self._admitted: set[str] = set()
        self._waiting: set[str] = set()
        self._reactive = ReactiveSiteCapController(settings.reactive_margin) if mode == "reactive" else None
        # per-minute records: minute m covers [m*call_s, (m+1)*call_s)
        self._p_min: list[np.ndarray] = []
        self._b_min: list[np.ndarray] = []
        self._o_min: list[np.ndarray] = []
        self._busy_after_prev = np.zeros(self.S)
        self._rows: list[dict[str, Any]] = []
        self.admissions: list[dict[str, Any]] = []
        self.decisions: list[dict[str, Any]] = []
        self.progress_at_warmup: dict[str, float] = {}
        self.done_at_warmup: set[str] = set()
        self._warm_snapshot_taken = False
        self.forecast_calls = 0

    # -- helpers ---------------------------------------------------------------

    def _busy_from_views(self, vs: VisibleState) -> np.ndarray:
        busy = np.zeros(self.S)
        for jv in vs.jobs:
            if jv.status in ("queued", "done"):
                continue
            job = self.job_by_id[jv.job_id]
            share = job.n_gpus / 2.0 if job.multisite else float(job.n_gpus)
            for sid in jv.site_ids:
                busy[self.site_ids.index(sid)] += share
        return busy

    def _planned_busy(self, t: float, vs: VisibleState) -> np.ndarray:
        """``(S, H)`` GPUs planned busy per bin from the running set and declared walltimes."""
        H, bs = self.cfg.horizon_bins, self.cfg.bin_s
        mids = t + (np.arange(H) + 0.5) * bs
        out = np.zeros((self.S, H))
        for jv in vs.jobs:
            if jv.status in ("queued", "done"):
                continue
            job = self.job_by_id[jv.job_id]
            remaining = max(job.duration_s * (1.0 - jv.progress_steps / jv.total_steps), 0.0)
            remaining *= 1.0 + self.cfg.walltime_overhead
            if self.cfg.end_rule == "overlap":  # count the job in every bin it overlaps (peak power, not bin mean)
                active = (mids - 0.5 * bs < t + remaining).astype(float)
            else:
                active = (mids < t + remaining).astype(float)
            share = job.n_gpus / 2.0 if job.multisite else float(job.n_gpus)
            for sid in jv.site_ids:
                out[self.site_ids.index(sid)] += share * active
        return out

    def ratio_bins(self) -> np.ndarray:
        """Observed ratio ``s`` in decision-interval bins, shape ``(S, n_bins)``."""
        k = int(round(self.cfg.bin_s / self.cfg.call_s))
        m = len(self._p_min) // k
        if m == 0:
            return np.zeros((self.S, 0))
        p = np.asarray(self._p_min[: m * k]).reshape(m, k, self.S).sum(axis=1)
        b = np.asarray(self._b_min[: m * k]).reshape(m, k, self.S)
        denom = (self.idle[None, None, :] + self.beta[None, None, :] * b).sum(axis=1)
        return (p / denom).T

    def minute_records(self) -> tuple[np.ndarray, np.ndarray]:
        """``(P, B)``: mean site power (W) and mean busy GPUs per call interval, shape ``(M, S)``."""
        return np.asarray(self._p_min), np.asarray(self._b_min)

    def _ingest(self, t: float, vs: VisibleState) -> np.ndarray:
        busy_end = self._busy_from_views(vs)
        if t > 0:
            _, vals = vs.history("site_power_w", self.cfg.call_s)
            self._p_min.append(np.asarray(vals).mean(axis=0))
            self._b_min.append(0.5 * (self._busy_after_prev + busy_end))
            hs = vs.known_future["hour_start_s"]
            fc = vs.known_future["outdoor_forecast_c"]
            self._o_min.append(np.array([np.interp(t - 0.5 * self.cfg.call_s, hs, fc[:, s]) for s in range(self.S)]))
        return busy_end

    # -- forecast paths -----------------------------------------------------------

    def _warm_ratio(self, bins: np.ndarray) -> np.ndarray:
        if bins.shape[1] == 0:
            return np.ones(self.S)
        return bins[:, -self.cfg.warm_ratio_bins:].max(axis=1)

    def _ratio_paths(self, t: float, vs: VisibleState, bins: np.ndarray) -> np.ndarray:
        """``(S, H, Q)`` ratio quantile paths for the next horizon."""
        H = self.cfg.horizon_bins
        if self.mode == "reactive":
            raise RuntimeError("reactive mode does not use ratio paths")
        in_warmup = t < self.cfg.warmup_s - 1e-9
        if self.mode == "oracle" and not in_warmup:
            i0 = int(round(t / self.cfg.bin_s))
            tr = self.oracle_ratio
            idx = np.clip(np.arange(i0, i0 + H), 0, tr.shape[1] - 1)
            return np.repeat(tr[:, idx][:, :, None], N_LEVELS, axis=2)
        if in_warmup or bins.shape[1] < self.cfg.min_context_bins or self.mode == "oracle":
            return np.broadcast_to(self._warm_ratio(bins)[:, None, None], (self.S, H, N_LEVELS)).copy()
        if self.refresh > 1 and self._cache is not None:
            off = int(round((t - self._cache[0]) / self.cfg.bin_s))
            if 0 <= off < self.refresh:
                return self._cache[1][:, off:off + H]
        ctx = bins[:, -self.cfg.context_bins:]
        h_call = H + self.refresh - 1
        kwargs: dict[str, Any] = {}
        if self.use_covariates:
            kwargs["known_covariates"] = self._covariates(t, vs, ctx.shape[1], h_call)
        fc = self.forecaster.forecast(ctx[:, None, :], h_call, **kwargs)
        self.forecast_calls += 1
        vals = np.maximum(np.asarray(fc.values, dtype=float)[:, 0, :, :], 0.05)
        if self.refresh > 1:
            self._cache = (t, vals)
        return vals[:, :H]

    def _covariates(self, t: float, vs: VisibleState, n_ctx: int, horizon: int) -> np.ndarray:
        k = int(round(self.cfg.bin_s / self.cfg.call_s))
        o = np.asarray(self._o_min)
        m = o.shape[0] // k
        past = o[: m * k].reshape(m, k, self.S).mean(axis=1).T[:, -n_ctx:]
        hs = vs.known_future["hour_start_s"]
        fc = vs.known_future["outdoor_forecast_c"]
        mids = t + (np.arange(horizon) + 0.5) * self.cfg.bin_s
        future = np.stack([np.interp(mids, hs, fc[:, s]) for s in range(self.S)])
        return np.concatenate([past, future], axis=1)[:, None, :]

    # -- slack ----------------------------------------------------------------------

    def _slack(self, sites: tuple[int, ...], shares: tuple[float, ...], active: np.ndarray, bplan: np.ndarray,
               paths: np.ndarray) -> np.ndarray:
        """Relative headroom at every level (min over the sites involved); negative means over the cap."""
        out = np.full(N_LEVELS, np.inf)
        for j, share in zip(sites, shares):
            base = self.idle[j] + self.beta[j] * (bplan[j] + share * active)
            planned = base[:, None] * paths[j]
            out = np.minimum(out, (self.cap[j] - planned.max(axis=0)) / self.cap[j])
        return out

    def _features(self, t: float, job: Job, sites: tuple[int, ...], shares: tuple[float, ...], active: np.ndarray,
                  bplan: np.ndarray, paths: np.ndarray, slack: np.ndarray) -> np.ndarray:
        spread, headroom, size, trend = [], [], 0.0, []
        for j, share in zip(sites, shares):
            p50 = paths[j][:, MEDIAN_INDEX]
            p10, p90 = paths[j][:, level_index(0.1)], paths[j][:, level_index(0.9)]
            spread.append(float(np.mean((p90 - p10) / np.maximum(p50, 1e-6))))
            cur = (self.idle[j] + self.beta[j] * bplan[j]) * p50
            headroom.append(float((self.cap[j] - cur.max()) / self.cap[j]))
            size += share * self.beta[j] * float(p50[0]) / self.cap[j]
            trend.append(float(p50[-1] / max(p50[0], 1e-6)))
        hour = (self.hour0[sites[0]] + t / 3600.0) % 24.0
        x = [
            max(spread), job.value_per_gpu_hour, math.log(max(self.penalty, 1e-9)), min(headroom), size,
            math.sin(2 * math.pi * hour / 24.0), math.cos(2 * math.pi * hour / 24.0), max(trend),
        ] + [float(slack[i]) for i in SLACK_FEATURE_INDICES]
        return np.asarray(x, dtype=float)

    # -- controller entry -------------------------------------------------------------

    def decide(self, t: float, vs: VisibleState) -> Sequence[Any]:
        actions: list[Any] = []
        busy_end = self._ingest(t, vs)
        defer_until = self.cfg.horizon_s + 3600.0
        for jv in vs.jobs:
            if jv.job_id not in self._known:
                self._known.add(jv.job_id)
                if jv.status == "queued" and jv.job_id not in self._admitted:
                    actions.append(DeferJob(jv.job_id, defer_until))
                    self._waiting.add(jv.job_id)
        for pj in vs.known_future["planned_jobs"]:
            if pj["job_id"] not in self._known:
                self._known.add(pj["job_id"])
                actions.append(DeferJob(pj["job_id"], defer_until))
                self._waiting.add(pj["job_id"])
        if not self._warm_snapshot_taken and t >= self.cfg.warmup_s - 1e-9:
            self._warm_snapshot_taken = True
            live = {jv.job_id for jv in vs.jobs}
            for jv in vs.jobs:
                self.progress_at_warmup[jv.job_id] = jv.progress_steps / jv.total_steps
            self.done_at_warmup = {
                jid for jid in self._admitted if jid not in live and self.job_by_id[jid].submit_s <= t
            }
        if self._reactive is not None:
            actions.extend(self._reactive.decide(t, vs))
        added = np.zeros(self.S)
        if abs(t / self.cfg.decision_interval_s - round(t / self.cfg.decision_interval_s)) < 1e-9:
            added = self._admission_round(t, vs, actions)
        self._busy_after_prev = busy_end + added
        return actions

    def _admission_round(self, t: float, vs: VisibleState, actions: list[Any]) -> np.ndarray:
        cfg = self.cfg
        bins = self.ratio_bins()
        H, bs = cfg.horizon_bins, cfg.bin_s
        free = np.asarray(vs.now["free_gpus"], dtype=float).copy()
        added_busy = np.zeros(self.S)
        views = {jv.job_id: jv for jv in vs.jobs}
        cands = [
            self.job_by_id[jid] for jid in self._waiting
            if jid in views and views[jid].status == "queued" and jid not in self._admitted
        ]
        if cfg.queue_order == "value_density":
            cands.sort(key=lambda j: (-j.value_per_gpu_hour, j.submit_s, j.job_id))
        else:
            cands.sort(key=lambda j: (j.submit_s, j.job_id))
        if self.mode == "reactive":
            bplan = np.repeat(self._busy_from_views(vs)[:, None], H, axis=1)
            if bins.shape[1]:
                s_now = bins[:, -1]
                p_meas = np.asarray(self._p_min[-int(round(bs / cfg.call_s)):]).mean(axis=0)
            else:
                s_now, p_meas = np.ones(self.S), self.idle.copy()
            paths = None
        else:
            bplan = self._planned_busy(t, vs)
            paths = self._ratio_paths(t, vs, bins)
            s_now = p_meas = None
        added_w = np.zeros(self.S)
        refused_with_gpus = 0
        evaluated = 0
        in_eval = (t >= cfg.warmup_s - 1e-9) and self.mode in ("forecast", "oracle")
        for job in cands:
            n = job.n_gpus
            if job.multisite:
                options = [(tuple(range(self.S)), tuple([n / 2.0] * self.S))] if np.all(free >= n / 2.0) else []
            else:
                options = [((j,), (float(n),)) for j in range(self.S) if free[j] >= n]
            if not options:
                continue
            evaluated += 1
            active = ((np.arange(H) + 0.5) * bs < job.duration_s).astype(float)
            slacks = []
            for sites, shares in options:
                if self.mode == "reactive":
                    sl = np.inf
                    for j, share in zip(sites, shares):
                        planned = p_meas[j] + added_w[j] + share * self.beta[j] * s_now[j]
                        sl = min(sl, (self.cap[j] - planned) / self.cap[j])
                    slacks.append(np.full(N_LEVELS, sl))
                else:
                    slacks.append(self._slack(sites, shares, active, bplan, paths))
            best = int(np.argmax([s[MEDIAN_INDEX] for s in slacks]))
            sites, shares = options[best]
            slack = slacks[best]
            if self.mode == "reactive":
                k, admit, x = MEDIAN_INDEX, bool(slack[0] >= 0.0), None
            elif not in_eval:
                k, admit, x = MEDIAN_INDEX, bool(slack[MEDIAN_INDEX] >= 0.0), None
            else:
                x = self._features(t, job, sites, shares, active, bplan, paths, slack)
                if self.mode == "oracle":
                    k = MEDIAN_INDEX
                else:
                    k = int(self.policy.choose(Situation(x, slack, job.value_per_gpu_hour, self.penalty)))
                admit = bool(slack[k] >= 0.0)
            if self.log_situations and x is not None and self.mode == "forecast":
                self._rows.append({
                    "t": float(t), "sites": sites, "shares": shares, "x": x, "slack": slack.copy(), "k": k,
                    "admit": admit, "value": job.value_per_gpu_hour, "n_gpus": n, "life_s": job.duration_s,
                })
            if not admit:
                refused_with_gpus += 1
                continue
            site_arg = self.site_ids[sites[0]] if not job.multisite else None
            actions.append(AdmitJob(job.job_id, site_arg))
            self._admitted.add(job.job_id)
            self._waiting.discard(job.job_id)
            self.admissions.append({"t_s": float(t), "job_id": job.job_id, "sites": [self.site_ids[j] for j in sites], "q_index": int(k)})
            for j, share in zip(sites, shares):
                free[j] -= share
                bplan[j] += share * active
                added_busy[j] += share
                added_w[j] += share * self.beta[j] * (s_now[j] if s_now is not None else 1.0)
        self.decisions.append({"t_s": float(t), "refused_with_gpus": refused_with_gpus, "evaluated": evaluated,
                               "waiting": len(self._waiting)})
        return added_busy

    def situations(self) -> dict[str, np.ndarray]:
        """Logged candidate situations as arrays (only when ``log_situations`` was set)."""
        rows = self._rows
        n = len(rows)
        sites = np.full((n, self.S), -1, dtype=int)
        shares = np.zeros((n, self.S))
        for i, r in enumerate(rows):
            for j, sh in zip(r["sites"], r["shares"]):
                sites[i, j], shares[i, j] = j, sh
        return {
            "t": np.array([r["t"] for r in rows]),
            "sites": sites, "shares": shares,
            "x": np.array([r["x"] for r in rows]).reshape(n, N_FEATURES),
            "slack": np.array([r["slack"] for r in rows]).reshape(n, N_LEVELS),
            "k": np.array([r["k"] for r in rows], dtype=int),
            "admit": np.array([r["admit"] for r in rows], dtype=bool),
            "value": np.array([r["value"] for r in rows]),
            "n_gpus": np.array([r["n_gpus"] for r in rows], dtype=float),
            "life_s": np.array([r["life_s"] for r in rows]),
        }


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def episode_metrics(result: Any, controller: PackingController, episode: Episode, settings: PackingSettings) -> dict[str, Any]:
    """Metrics over the evaluation window ``[warmup_s, horizon_s)`` (simulated)."""
    dt = float(result.dt)
    power = np.asarray(result.site_power_w)
    n0 = int(round(settings.warmup_s / dt))
    w = power[n0:]
    cap = controller.cap
    over = np.maximum(w - cap[None, :], 0.0)
    per_int = int(round(settings.decision_interval_s / dt))
    n_int = w.shape[0] // per_int
    any_over = (over[: n_int * per_int].reshape(n_int, per_int, -1) > 0).any(axis=(1, 2))
    site_int_over = (over[: n_int * per_int].reshape(n_int, per_int, -1) > 0).any(axis=1)
    head = np.maximum(cap[None, :] - w, 0.0)
    dec = [d for d in controller.decisions if d["t_s"] >= settings.warmup_s - 1e-9]
    stranded_kwh = 0.0
    stranded_intervals = 0
    for i, d in enumerate(dec[:n_int]):
        if d["refused_with_gpus"] > 0:
            seg = head[i * per_int:(i + 1) * per_int]
            stranded_kwh += float(seg.sum() * dt / 3.6e6)
            stranded_intervals += 1
    rows = result.jobs_table
    gpu_h = value = 0.0
    gpu_h_multi = 0.0
    completed = 0
    for r in rows:
        job = controller.job_by_id[r["job_id"]]
        if r["job_id"] in controller.done_at_warmup:
            continue
        start_frac = controller.progress_at_warmup.get(r["job_id"], 0.0)
        gross_start = job.n_gpus * job.duration_s / 3600.0 * start_frac
        delta = r["useful_gpu_hours"] - gross_start
        gpu_h += delta
        value += delta * job.value_per_gpu_hour
        if r["multisite"]:
            gpu_h_multi += delta
        if r["status"] == "done":
            completed += 1
    admitted_in_window = sum(1 for a in controller.admissions if a["t_s"] >= settings.warmup_s - 1e-9)
    energy_over = float(over.sum() * dt / 3.6e6)
    out = {
        "data_kind": "simulated",
        "window_s": [settings.warmup_s, settings.horizon_s],
        "gpu_hours": float(gpu_h), "gpu_hours_multisite_jobs": float(gpu_h_multi),
        "value_usd": float(value),
        "jobs_admitted": int(admitted_in_window), "jobs_completed": int(completed),
        "violation_rate": float(any_over.mean()) if n_int else 0.0,
        "violation_rate_by_site": [float(x) for x in site_int_over.mean(axis=0)],
        "energy_above_cap_kwh": energy_over,
        "energy_above_cap_kwh_by_site": [float(x) for x in over.sum(axis=0) * dt / 3.6e6],
        "seconds_above_cap": float((over > 0).sum() * dt),
        "max_excess_w": float(over.max()) if over.size else 0.0,
        "stranded_kwh": stranded_kwh, "stranded_intervals": int(stranded_intervals),
        "mean_power_over_cap": float((w / cap[None, :]).mean()),
        "energy_kwh": float(w.sum() * dt / 3.6e6),
        "forecast_calls": int(controller.forecast_calls),
        "forecast_refresh_bins": int(controller.refresh),
        "job_faults": int(sum(r["faults"] for r in rows)),
    }
    return out


def net_value(metrics: Mapping[str, Any], penalty_usd_per_kwh: float) -> float:
    """Value delivered minus the over-cap penalty for one episode."""
    return float(metrics["value_usd"]) - float(penalty_usd_per_kwh) * float(metrics["energy_above_cap_kwh"])


def bootstrap_ci(values: Sequence[float], n_boot: int = 2000, seed: int = 0, level: float = 0.95) -> dict[str, float]:
    """Percentile bootstrap interval of the mean over episodes."""
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        raise ValueError("no values")
    rng = np.random.default_rng([int(seed), 5])
    idx = rng.integers(0, v.size, size=(n_boot, v.size))
    means = v[idx].mean(axis=1)
    a = (1.0 - level) / 2.0
    return {"mean": float(v.mean()), "lo": float(np.quantile(means, a)), "hi": float(np.quantile(means, 1 - a)), "n": int(v.size)}


# ---------------------------------------------------------------------------
# Hindsight costs and the learned model
# ---------------------------------------------------------------------------


def hindsight_costs(
    sit: Mapping[str, np.ndarray],
    p_min: np.ndarray,
    b_min: np.ndarray,
    models: Sequence[SiteModel],
    penalties: Sequence[float],
    call_s: float,
    window_s: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Per-level costs of every logged situation under each penalty, from the logged realized path.

    Returns ``(costs, value)`` with ``costs`` shaped ``(len(penalties), N, N_LEVELS)``
    (regret in USD against the best level) and ``value`` shaped ``(N,)`` (the
    candidate's value over the window).  Surrogate: the candidate's power is
    added to or removed from the logged realized site power as
    ``beta * n_gpus * s_real(m)`` while it is alive, so later decisions are not
    re-played.  Situations whose window runs past the logged record are given
    zero cost for every level (they carry no signal).
    """
    n = sit["t"].shape[0]
    S = p_min.shape[1]
    idle = np.array([m.idle_w for m in models])
    beta = np.array([m.beta_w_per_gpu for m in models])
    cap = np.array([m.cap_w for m in models])
    s_real = p_min / (idle[None, :] + beta[None, :] * b_min)
    W = int(round(window_s / call_s))
    m0 = np.round(sit["t"] / call_s).astype(int)
    idx = m0[:, None] + np.arange(W)[None, :]
    valid = idx[:, -1] < p_min.shape[0]
    idx = np.clip(idx, 0, p_min.shape[0] - 1)
    alive = ((np.arange(W)[None, :] + 0.5) * call_s < sit["life_s"][:, None]).astype(float)
    dlog = sit["admit"].astype(float)
    value = sit["n_gpus"] * sit["value"] * np.minimum(window_s, sit["life_s"]) / 3600.0
    excess = np.zeros((2, n))
    for d in (0.0, 1.0):
        total = np.zeros(n)
        for j in range(S):
            share = sit["shares"][:, j]
            p = p_min[idx, j] + s_real[idx, j] * beta[j] * share[:, None] * (d - dlog)[:, None] * alive
            total += (np.maximum(p - cap[j], 0.0) * call_s / 3.6e6).sum(axis=1)
        excess[int(d)] = total
    costs = np.zeros((len(penalties), n, N_LEVELS))
    fits = sit["slack"] >= 0.0
    for pi, lam in enumerate(penalties):
        r0 = -lam * excess[0]
        r1 = value - lam * excess[1]
        reward = np.where(fits, r1[:, None], r0[:, None])
        costs[pi] = reward.max(axis=1, keepdims=True) - reward
        costs[pi][~valid] = 0.0
    return costs, value


class CostSensitiveModel:
    """Random-Fourier-feature ridge regression of per-level cost; the policy picks the level with least predicted cost.

    Inputs are standardized with the training mean and standard deviation.
    The regression goal is the cost divided by the candidate's value (so the
    scale is the same across jobs), weighted by that value.  numpy only.
    """

    def __init__(self, n_features: int = N_FEATURES, n_levels: int = N_LEVELS, n_rff: int = 256,
                 bandwidth: float = 1.0, ridge: float = 1.0, seed: int = 0) -> None:
        self.n_features, self.n_levels, self.n_rff = n_features, n_levels, n_rff
        self.bandwidth, self.ridge, self.seed = float(bandwidth), float(ridge), int(seed)
        rng = np.random.default_rng([self.seed, 31])
        self.W = rng.normal(0.0, 1.0 / self.bandwidth, size=(n_features, n_rff))
        self.b = rng.uniform(0.0, 2 * np.pi, size=n_rff)
        self.mean = np.zeros(n_features)
        self.std = np.ones(n_features)
        self.theta: Optional[np.ndarray] = None

    def _phi(self, X: np.ndarray) -> np.ndarray:
        Z = (np.atleast_2d(X) - self.mean) / self.std
        rff = math.sqrt(2.0 / self.n_rff) * np.cos(Z @ self.W + self.b)
        return np.concatenate([np.ones((Z.shape[0], 1)), Z, rff], axis=1)

    def fit(self, X: np.ndarray, costs: np.ndarray, value: np.ndarray) -> "CostSensitiveModel":
        X = np.asarray(X, dtype=float)
        self.mean = X.mean(axis=0)
        self.std = np.where(X.std(axis=0) > 1e-12, X.std(axis=0), 1.0)
        scale = np.maximum(value, 1e-9)
        Y = costs / scale[:, None]
        wgt = scale / scale.mean()
        d = 1 + self.n_features + self.n_rff
        A = np.zeros((d, d))
        B = np.zeros((d, self.n_levels))
        for lo in range(0, X.shape[0], 20000):
            P = self._phi(X[lo:lo + 20000])
            w = wgt[lo:lo + 20000, None]
            A += (P * w).T @ P
            B += (P * w).T @ Y[lo:lo + 20000]
        self.theta = np.linalg.solve(A + self.ridge * np.eye(d), B)
        return self

    def predict_costs(self, X: np.ndarray) -> np.ndarray:
        if self.theta is None:
            raise RuntimeError("model is not fitted")
        return self._phi(X) @ self.theta

    def choose(self, x: np.ndarray) -> int:
        return int(np.argmin(self.predict_costs(x)[0]))

    def regret(self, X: np.ndarray, costs: np.ndarray, value: np.ndarray) -> float:
        """Mean over situations of the cost of the chosen level, divided by the total value."""
        pick = np.argmin(self.predict_costs(X), axis=1)
        chosen = costs[np.arange(costs.shape[0]), pick]
        return float(chosen.sum() / max(value.sum(), 1e-9))

    def to_dict(self) -> dict[str, Any]:
        assert self.theta is not None
        return {
            "n_rff": self.n_rff, "bandwidth": self.bandwidth, "ridge": self.ridge, "seed": self.seed,
            "mean": self.mean.tolist(), "std": self.std.tolist(), "theta": self.theta.tolist(),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "CostSensitiveModel":
        m = cls(n_rff=int(d["n_rff"]), bandwidth=float(d["bandwidth"]), ridge=float(d["ridge"]), seed=int(d["seed"]))
        m.mean, m.std, m.theta = np.array(d["mean"]), np.array(d["std"]), np.array(d["theta"])
        return m


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


__all__ = [
    "CostSensitiveModel", "Episode", "FEATURE_NAMES", "FixedQ", "LearnedQ", "MEDIAN_INDEX", "N_FEATURES", "N_LEVELS",
    "PackingController", "PackingSettings", "declared_checkpoint_overhead", "QUANTILE_LEVELS", "RandomQ", "SiteModel", "Situation",
    "bootstrap_ci", "build_episode", "calibrate_sites", "episode_metrics", "hindsight_costs", "level_index",
    "load_packing_scenario", "net_value", "run_episode",
]
