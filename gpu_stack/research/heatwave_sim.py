"""Multi-scale power and thermal cluster simulator for the Heatwave extension (e003).

Everything this module produces is SIMULATED.  Some power levels are derived
from measured laptop-GPU ratios (experiment e002); every other number is a
scenario assumption or a cited constant, and the result object says which is
which (``SimResult.to_arrays()['meta']``).  Nothing here is a claim about a
real cluster.

Hierarchy and clocks
--------------------
Sites contain racks, racks contain GPUs.  Sites reuse
:class:`gpu_stack.research.multisite.Site` for the site power cap, cooling
capacity, and grid import limit.  Two clocks run together:

* the base step ``base_dt_s`` (default 1 s) at which power is rendered, and
* the control step ``control_dt_s`` (default 10 s, a whole multiple of the base
  step).  Job admission, GPU clock limits, thermal integration, breaker state,
  fault onsets, and controller decisions happen on control-step boundaries.
  Inside a control step, job state changes (checkpoint start, job end, merge
  barrier) are handled at their exact time and rendered at base resolution.

Per-GPU power waveform
----------------------
A running data-parallel job alternates compute and communication phases inside
each training step (``compute_fraction_of_step`` of the step is compute), stalls
for ``checkpoint_duration_s`` every ``checkpoint_every_s`` of running time, and
holds its GPUs at the checkpoint level meanwhile.  Idle GPUs draw idle power.
The relative levels checkpoint/compute and idle/compute are the medians of the
labeled phase windows in the measured e002 laptop telemetry
(``docs/data/e002-checkpoint-power-raw-v1.json``), computed in code by
:func:`measure_e002_levels`, then scaled to the H100 SXM TDP from
``gpu_stack.presets.hardware`` (700 W, NVIDIA product specification cited
there).  What is measured and what is assumed:

* measured (laptop GPU, ratios only): idle/compute, checkpoint/compute,
  restore/compute, merge/compute, relative standard deviation of compute-phase
  power;
* cited: H100 SXM TDP (700 W), DGX H100 mass and operating temperature range
  (https://docs.nvidia.com/dgx/dgxh100-user-guide/introduction-to-dgxh100.html),
  IEC 60898-1 breaker curve constants, the e001 WAN/restore parameters;
* assumed (scenario parameters, labeled): fraction of TDP drawn in compute,
  communication-phase level, host overhead, thermal resistance and heat
  capacity, throttle threshold, cooling model efficiency, job mix, events.

The laptop telemetry updates about every 0.49 s while its checkpoint-snapshot
windows are about 23 ms long, so the measured checkpoint/compute ratio cannot
resolve a checkpoint dip.  The scenario may therefore choose the checkpoint
level from the measured idle ratio; the choice is recorded in the output.

Throttling and power caps
-------------------------
Each GPU has a clock fraction from the thermal throttle model (GPU temperature
= rack air temperature + a per-GPU offset proportional to its power) and from
the rack power cap.  A synchronous job runs at the clock of its slowest GPU and
all its GPUs are modeled at that clock (a simplification: waiting GPUs are not
modeled separately).  Progress scales with the clock fraction; dynamic power
scales as ``clock ** exponent``.

Work accounting (e001 compatible)
---------------------------------
Progress is in steps.  A single-site job that faults returns to its last
completed checkpoint, and the steps since are lost.  A multi-site job (two
shards, one per site) follows the e001 ``periodic_local`` rule: each shard
trains alone and the shards average exactly every ``average_every_steps``
steps; a faulted shard returns to the last average; the survivor continues
without the failed shard's quota, and the returning shard adopts the merged
state through an explicit merge (the steps it missed are reported as
``skipped_steps``).  Lost work is reported in steps and GPU-hours.

Known simplifications are listed in ``SimResult.meta['simplifications']``.
"""

from __future__ import annotations

import hashlib
import heapq
import json
import math
from dataclasses import asdict, dataclass, field, is_dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Optional, Protocol, Sequence, Tuple, Union, runtime_checkable

import numpy as np

from .heatwave_events import (
    BreakerTrip,
    EventSchedule,
    EventSignals,
    InverseTimeBreaker,
    KIND_BREAKER_TRIP,
    KIND_HARDWARE_FAULT,
    KIND_THERMAL_THROTTLE,
)
from .heatwave_thermal import CoolingPowerModel, GPUThrottleModel, rc_step
from .multisite import Site

KIND_THERMAL_SHUTDOWN = "thermal_shutdown"
SCENARIO_SCHEMA = "gpu-stack.e003-heatwave-sim-scenario.v1"
RESULT_SCHEMA = "gpu-stack.e003-heatwave-sim-result.v1"

_REPO_ROOT = Path(__file__).resolve().parents[2]
E002_RAW_RELATIVE_PATH = "docs/data/e002-checkpoint-power-raw-v1.json"

SIMPLIFICATIONS = (
    "Job admission, GPU clocks, thermal integration, breaker state, event onsets and controller "
    "decisions are evaluated at control-step boundaries; event onsets take effect at the first "
    "boundary at or after the stated time.",
    "Thermal integration uses the mean rack power over each control step.",
    "A synchronous job runs at the clock of its slowest GPU and all its GPUs are modeled at that clock.",
    "Per-GPU power noise is independent across GPUs and seconds, scaled to the measured relative "
    "standard deviation of laptop compute-phase power.",
    "GPU temperature uses the rack air temperature at the start of the control step and the previous "
    "step's mean GPU power.",
    "Multi-site jobs take no separate checkpoints; their durable state is the last exact average.",
    "A faulted GPU draws 0 W until repaired; its host stays powered unless the rack breaker is open.",
)


# ---------------------------------------------------------------------------
# small validators
# ---------------------------------------------------------------------------


def _nonempty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _num(value: float, name: str, *, minimum: float = 0.0, strict: bool = False, maximum: float = math.inf) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{name} must be a real number")
    v = float(value)
    if not math.isfinite(v):
        raise ValueError(f"{name} must be finite")
    if (strict and not v > minimum) or (not strict and v < minimum):
        raise ValueError(f"{name} must be {'>' if strict else '>='} {minimum}")
    if v > maximum:
        raise ValueError(f"{name} must be <= {maximum}")


# ---------------------------------------------------------------------------
# Measured e002 levels
# ---------------------------------------------------------------------------


def measure_e002_levels(path: Union[str, Path, None] = None) -> dict[str, Any]:
    """Medians per labeled phase of the measured e002 laptop GPU-board power.

    Returns raw medians in watts (laptop), ratios to the compute median, the
    relative standard deviation of compute-phase samples, sample counts, and
    the telemetry update period.  Idle is the board power before and after the
    active window of each run.  ``data_kind`` of this table is measured.
    """
    raw_path = Path(path) if path is not None else _REPO_ROOT / E002_RAW_RELATIVE_PATH
    if not raw_path.exists():
        raise FileNotFoundError(f"measured e002 telemetry not found at {raw_path}")
    data = json.loads(raw_path.read_text())
    samples: dict[str, list[np.ndarray]] = {}
    rel_std = []
    window_durations: dict[str, list[float]] = {}
    for run in data["runs"]:
        trace = run["telemetry_trace"]
        if not trace.get("available"):
            continue
        ts = np.array([p["timestamp"] for p in trace["points"]], dtype=float)
        pw = np.array([p["gpu_board_power_w"] for p in trace["points"]], dtype=float)
        for w in trace["phase_windows"]:
            m = (ts >= w["start_seconds"]) & (ts < w["end_seconds"])
            samples.setdefault(w["phase"], []).append(pw[m])
            window_durations.setdefault(w["phase"], []).append(w["end_seconds"] - w["start_seconds"])
        a, b = trace["active_start_seconds"], trace["active_end_seconds"]
        samples.setdefault("idle-outside-active-window", []).append(pw[(ts < a) | (ts > b)])
        comp = np.concatenate(
            [pw[(ts >= w["start_seconds"]) & (ts < w["end_seconds"])]
             for w in trace["phase_windows"] if w["phase"] == "canonical-healthy-compute"]
            or [np.array([])]
        )
        if comp.size > 8 and float(np.mean(comp)) > 0:
            rel_std.append(float(np.std(comp) / np.mean(comp)))
    pooled = {k: np.concatenate(v) for k, v in samples.items() if sum(x.size for x in v) > 0}
    medians = {k: float(np.median(v)) for k, v in pooled.items()}
    counts = {k: int(v.size) for k, v in pooled.items()}
    compute = medians["canonical-healthy-compute"]
    ratios = {k: medians[k] / compute for k in medians}
    return {
        "data_kind": "measured",
        "source_file": str(raw_path),
        "source_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "boundary": data.get("boundary"),
        "median_power_w_laptop": medians,
        "ratio_to_compute": ratios,
        "sample_counts": counts,
        "compute_relative_std": float(np.median(rel_std)) if rel_std else 0.0,
        "median_window_duration_s": {k: float(np.median(v)) for k, v in window_durations.items()},
        "telemetry_update_period_s": float(data["logger_calibration"]["effective_update_period_seconds"]),
    }


@dataclass(frozen=True)
class PowerLevels:
    """Per-GPU power levels in watts for the phases of the waveform."""

    compute_w: float
    comm_w: float
    checkpoint_w: float
    idle_w: float
    host_w_per_gpu: float
    noise_rel_sigma: float
    provenance: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("compute_w", "comm_w", "checkpoint_w", "idle_w", "host_w_per_gpu", "noise_rel_sigma"):
            _num(getattr(self, name), name, strict=name == "compute_w")
        if self.idle_w > self.compute_w:
            raise ValueError("idle_w must not exceed compute_w")

    @classmethod
    def from_e002(
        cls,
        measured: Mapping[str, Any],
        tdp_w: float,
        compute_fraction_of_tdp: float,
        comm_ratio: Union[str, float] = "idle_ratio",
        checkpoint_ratio: Union[str, float] = "measured",
        host_fraction_of_compute: float = 0.0,
        idle_ratio_override: Optional[float] = None,
        noise_scale: float = 1.0,
        calibration_notes: Optional[Mapping[str, str]] = None,
    ) -> "PowerLevels":
        """Scale measured laptop ratios to a datacenter GPU.

        ``comm_ratio`` and ``checkpoint_ratio`` are ``'measured'`` (the
        measured checkpoint ratio; not available for communication),
        ``'idle_ratio'`` (use the measured idle ratio), or a number.
        ``idle_ratio_override`` replaces the measured idle ratio when set (the
        caller then owns the citation). ``calibration_notes`` replaces the
        provenance label of any level (keys as in ``provenance``) when a
        scenario calibrates it from data instead of assuming it.
        """
        ratios = measured["ratio_to_compute"]
        compute = float(tdp_w) * float(compute_fraction_of_tdp)
        idle_ratio = float(ratios["idle-outside-active-window"]) if idle_ratio_override is None else float(idle_ratio_override)
        prov = {
            "compute_w": f"assumed: {compute_fraction_of_tdp} x cited TDP {tdp_w} W",
            "idle_w": (
                f"measured laptop idle/compute ratio {idle_ratio:.4f} x compute_w"
                if idle_ratio_override is None
                else f"override ratio {idle_ratio:.4f} x compute_w (caller-supplied)"
            ),
        }

        def resolve(spec: Union[str, float], what: str) -> float:
            if spec == "idle_ratio":
                prov[what] = "assumed level equal to the idle ratio (structural assumption)"
                return idle_ratio
            if spec == "measured":
                if what == "comm_w":
                    raise ValueError("no measured communication-phase level exists in e002")
                prov[what] = "measured laptop checkpoint-snapshot/compute ratio"
                return float(ratios["checkpoint-snapshot"])
            _num(spec, f"{what} ratio", strict=True)  # type: ignore[arg-type]
            prov[what] = f"assumed ratio {float(spec)}"  # type: ignore[arg-type]
            return float(spec)  # type: ignore[arg-type]

        comm = resolve(comm_ratio, "comm_w")
        ckpt = resolve(checkpoint_ratio, "checkpoint_w")
        prov["host_w_per_gpu"] = f"assumed: {host_fraction_of_compute} x compute_w"
        prov["noise_rel_sigma"] = f"measured laptop relative std of compute-phase board power x scale {noise_scale}"
        for key, note in (calibration_notes or {}).items():
            if key not in prov:
                raise ValueError(f"calibration_notes key {key!r} is not a power level")
            prov[key] = str(note)
        return cls(
            compute_w=compute,
            comm_w=compute * comm,
            checkpoint_w=compute * ckpt,
            idle_w=compute * idle_ratio,
            host_w_per_gpu=compute * float(host_fraction_of_compute),
            noise_rel_sigma=float(measured["compute_relative_std"]) * float(noise_scale),
            provenance=prov,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "compute_w": self.compute_w, "comm_w": self.comm_w, "checkpoint_w": self.checkpoint_w,
            "idle_w": self.idle_w, "host_w_per_gpu": self.host_w_per_gpu,
            "noise_rel_sigma": self.noise_rel_sigma, "provenance": dict(self.provenance),
        }


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Job:
    """One training job.  ``duration_s`` is the productive time at full clock."""

    job_id: str
    n_gpus: int
    submit_s: float
    start_s: float
    duration_s: float
    step_time_s: float
    checkpoint_every_s: float
    checkpoint_duration_s: float
    value_per_gpu_hour: float
    flexible: bool
    site_id: Optional[str] = None
    multisite: bool = False
    average_every_steps: int = 8

    def __post_init__(self) -> None:
        _nonempty(self.job_id, "job_id")
        if isinstance(self.n_gpus, bool) or not isinstance(self.n_gpus, (int, np.integer)) or self.n_gpus < 1:
            raise ValueError("n_gpus must be an integer >= 1")
        _num(self.submit_s, "submit_s")
        _num(self.start_s, "start_s")
        if self.start_s < self.submit_s:
            raise ValueError("start_s must be >= submit_s")
        _num(self.duration_s, "duration_s", strict=True)
        _num(self.step_time_s, "step_time_s", strict=True)
        _num(self.checkpoint_every_s, "checkpoint_every_s", strict=True)
        _num(self.checkpoint_duration_s, "checkpoint_duration_s")
        _num(self.value_per_gpu_hour, "value_per_gpu_hour")
        if not isinstance(self.flexible, (bool, np.bool_)):
            raise ValueError("flexible must be a bool")
        if self.multisite and self.n_gpus % 2:
            raise ValueError("multisite jobs need an even n_gpus")
        if isinstance(self.average_every_steps, bool) or int(self.average_every_steps) < 1:
            raise ValueError("average_every_steps must be an integer >= 1")

    @property
    def total_steps(self) -> float:
        return self.duration_s / self.step_time_s

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id, "n_gpus": int(self.n_gpus), "submit_s": self.submit_s, "start_s": self.start_s,
            "duration_s": self.duration_s, "step_time_s": self.step_time_s,
            "checkpoint_every_s": self.checkpoint_every_s, "checkpoint_duration_s": self.checkpoint_duration_s,
            "value_per_gpu_hour": self.value_per_gpu_hour, "flexible": bool(self.flexible),
            "site_id": self.site_id, "multisite": bool(self.multisite),
            "average_every_steps": int(self.average_every_steps),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Job":
        return cls(**dict(data))


def generate_jobs(
    seed: int,
    horizon_s: float,
    total_gpus: int,
    utilization_goal: float,
    gpu_choices: Sequence[int],
    gpu_weights: Sequence[float],
    duration_range_s: Tuple[float, float],
    step_time_choices_s: Sequence[float],
    checkpoint_every_range_s: Tuple[float, float],
    checkpoint_duration_range_s: Tuple[float, float],
    value_range: Tuple[float, float],
    flexible_fraction: float,
    multisite_fraction: float,
    max_start_delay_s: float,
    initial_fraction: float = 0.5,
    site_ids: Sequence[str] = (),
) -> list[Job]:
    """Seeded synthetic job schedule (simulated, no real trace behind it).

    Jobs are added until their total GPU-seconds reach ``utilization_goal``
    times the cluster capacity over the horizon.  A fraction ``initial_fraction``
    of the GPU-seconds is submitted at time 0.  Durations are log-uniform.
    """
    rng = np.random.default_rng([int(seed), 101])
    weights = np.asarray(gpu_weights, dtype=float)
    weights = weights / weights.sum()
    goal = utilization_goal * total_gpus * horizon_s
    jobs: list[Job] = []
    acc = 0.0
    k = 0
    lo, hi = math.log(duration_range_s[0]), math.log(duration_range_s[1])
    while acc < goal:
        n = int(rng.choice(np.asarray(gpu_choices), p=weights))
        multisite = bool(rng.random() < multisite_fraction) and n % 2 == 0 and n >= 2
        dur = float(math.exp(rng.uniform(lo, hi)))
        step = float(rng.choice(np.asarray(step_time_choices_s)))
        dur = max(step, round(dur / step) * step)
        initial = acc < initial_fraction * goal
        submit = 0.0 if initial else float(rng.uniform(0.0, 0.9 * horizon_s))
        start = submit + float(rng.uniform(0.0, max_start_delay_s)) if not initial else 0.0
        site = None
        if site_ids and not multisite:
            site = str(site_ids[int(rng.integers(len(site_ids)))]) if rng.random() < 0.5 else None
        k += 1
        jobs.append(
            Job(
                job_id=f"job-{k:04d}", n_gpus=n, submit_s=round(submit, 3), start_s=round(start, 3),
                duration_s=dur, step_time_s=step,
                checkpoint_every_s=float(rng.uniform(*checkpoint_every_range_s)),
                checkpoint_duration_s=float(rng.uniform(*checkpoint_duration_range_s)),
                value_per_gpu_hour=round(float(rng.uniform(*value_range)), 4),
                flexible=bool(rng.random() < flexible_fraction), site_id=site, multisite=multisite,
            )
        )
        acc += n * min(dur, horizon_s)
    jobs.sort(key=lambda j: (j.start_s, j.job_id))
    return jobs


# ---------------------------------------------------------------------------
# Environment (outdoor temperature, price, carbon)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SiteEnvironment:
    """Hourly external series for one site, aligned to the sim clock.

    Index ``i`` is the value at ``i * step_s`` seconds after the sim start.
    The series need ``horizon_s / step_s + 1`` values (the last one is the
    end-of-horizon value used for interpolation).  ``outdoor_forecast_c`` is
    what the controller may see of the future; it defaults to the actual
    series when not given.
    """

    outdoor_c: np.ndarray
    price_usd_per_kwh: np.ndarray
    carbon_g_per_kwh: np.ndarray
    outdoor_forecast_c: Optional[np.ndarray] = None
    step_s: float = 3600.0

    def __post_init__(self) -> None:
        for name in ("outdoor_c", "price_usd_per_kwh", "carbon_g_per_kwh"):
            arr = np.asarray(getattr(self, name), dtype=float)
            if arr.ndim != 1 or arr.size < 2 or not np.all(np.isfinite(arr)):
                raise ValueError(f"{name} must be a finite 1-D array with at least 2 values")
            object.__setattr__(self, name, arr)
        n = self.outdoor_c.size
        if self.price_usd_per_kwh.size != n or self.carbon_g_per_kwh.size != n:
            raise ValueError("environment series must have equal length")
        if self.outdoor_forecast_c is not None:
            f = np.asarray(self.outdoor_forecast_c, dtype=float)
            if f.shape != self.outdoor_c.shape:
                raise ValueError("outdoor_forecast_c must match outdoor_c in shape")
            object.__setattr__(self, "outdoor_forecast_c", f)
        _num(self.step_s, "step_s", strict=True)

    @property
    def forecast_c(self) -> np.ndarray:
        return self.outdoor_c if self.outdoor_forecast_c is None else self.outdoor_forecast_c


def synthetic_environment(spec: Mapping[str, Any], site_ids: Sequence[str], horizon_s: float, seed: int) -> dict[str, SiteEnvironment]:
    """Seeded synthetic diurnal outdoor temperature, price and carbon series (simulated)."""
    n = int(round(horizon_s / 3600.0)) + 1
    hours = np.arange(n, dtype=float)
    out: dict[str, SiteEnvironment] = {}
    for idx, site_id in enumerate(site_ids):
        s = spec["sites"][site_id]
        rng = np.random.default_rng([int(seed), 202, idx])
        local_h = hours + float(s.get("utc_offset_h", 0.0)) + float(spec.get("start_hour_utc", 0.0))
        o = s["outdoor"]
        temp = o["mean_c"] + o["diurnal_amplitude_c"] * np.cos(2 * np.pi * (local_h - o["peak_hour_local"]) / 24.0)
        for hw in o.get("heatwaves", []):
            temp = temp + hw["add_c"] * np.exp(-0.5 * ((hours - hw["center_h"]) / hw["width_h"]) ** 2)
        noise = np.zeros(n)
        e = rng.normal(0.0, 1.0, n)
        phi = float(o.get("noise_ar1", 0.0))
        for i in range(1, n):
            noise[i] = phi * noise[i - 1] + math.sqrt(1 - phi**2) * e[i]
        temp = temp + float(o.get("noise_sigma_c", 0.0)) * noise
        ferr = np.zeros(n)
        fe = rng.normal(0.0, 1.0, n)
        for i in range(1, n):
            ferr[i] = 0.9 * ferr[i - 1] + math.sqrt(1 - 0.81) * fe[i]
        forecast = temp + float(s.get("forecast_error_sigma_c", 0.0)) * ferr
        p = s["price"]
        price = p["base_usd_per_kwh"] * (1.0 + p["diurnal_amplitude"] * np.cos(2 * np.pi * (local_h - p["peak_hour_local"]) / 24.0))
        c = s["carbon"]
        carbon = c["base_g_per_kwh"] * (1.0 + c["diurnal_amplitude"] * np.cos(2 * np.pi * (local_h - c["peak_hour_local"]) / 24.0))
        out[site_id] = SiteEnvironment(temp, price, carbon, forecast)
    return out


# ---------------------------------------------------------------------------
# Controller interface
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SetRackPowerCap:
    rack_id: str
    cap_w: Optional[float]  # IT power cap for the rack; None removes the cap


@dataclass(frozen=True)
class AdmitJob:
    job_id: str
    site_id: Optional[str] = None


@dataclass(frozen=True)
class DeferJob:
    job_id: str
    until_s: float


@dataclass(frozen=True)
class PauseJob:
    job_id: str


@dataclass(frozen=True)
class ResumeJob:
    job_id: str


@dataclass(frozen=True)
class CheckpointNow:
    job_id: str


@dataclass(frozen=True)
class MigrateJob:
    job_id: str
    to_site_id: str


Action = Any


@dataclass(frozen=True)
class JobView:
    job_id: str
    status: str
    site_ids: Tuple[str, ...]
    n_gpus: int
    progress_steps: float
    total_steps: float
    steps_since_durable: float
    flexible: bool
    value_per_gpu_hour: float
    submit_s: float
    planned_start_s: float
    paused: bool
    rack_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class VisibleState:
    """What a controller may see at time ``t_s``: telemetry up to ``t_s`` only,
    plus the known-future schedule.  Ground-truth events are never included.

    ``now`` holds the latest samples (one value per rack or site).
    ``history(channel, window_s)`` returns ``(times_s, values)`` for the last
    ``window_s`` seconds, never past ``t_s``.  ``known_future`` holds the job
    schedule (reservations within the visibility horizon), announced
    curtailments, and the external outdoor-forecast, price and carbon series
    from ``t_s`` on.
    """

    t_s: float
    site_ids: Tuple[str, ...]
    rack_ids: Tuple[str, ...]
    rack_site_ids: Tuple[str, ...]
    now: Mapping[str, np.ndarray]
    jobs: Tuple[JobView, ...]
    known_future: Mapping[str, Any]
    _history: Any = field(repr=False, default=None)

    def history(self, channel: str, window_s: float) -> Tuple[np.ndarray, np.ndarray]:
        return self._history(channel, window_s)


@runtime_checkable
class Controller(Protocol):
    def decide(self, t_s: float, visible_state: VisibleState) -> Sequence[Action]:  # pragma: no cover - protocol
        ...


class NullController:
    """Takes no action."""

    def decide(self, t_s: float, visible_state: VisibleState) -> Sequence[Action]:
        return ()


class ReactiveSiteCapController:
    """Baseline: when a site's latest power exceeds its effective limit, cap its racks.

    Uses only visible state.  ``margin`` is the fraction of the limit the
    controller aims to stay under.  It is a deliberately simple reference
    policy, not a tuned one.
    """

    def __init__(self, margin: float = 0.97) -> None:
        _num(margin, "margin", strict=True, maximum=1.0)
        self.margin = float(margin)
        self._caps: dict[str, float] = {}

    def decide(self, t_s: float, visible_state: VisibleState) -> Sequence[Action]:
        actions: list[Action] = []
        now = visible_state.now
        for s, site_id in enumerate(visible_state.site_ids):
            limit = min(float(now["site_power_cap_w"][s]), float(now["site_import_limit_w"][s]))
            power = float(now["site_power_w"][s])
            racks = [i for i, sid in enumerate(visible_state.rack_site_ids) if sid == site_id]
            if power > limit * self.margin:
                scale = limit * self.margin / max(power, 1.0)
                for i in racks:
                    rack_power = float(now["rack_it_power_w"][i])
                    cap = max(rack_power * scale, 0.0)
                    self._caps[visible_state.rack_ids[i]] = cap
                    actions.append(SetRackPowerCap(visible_state.rack_ids[i], cap))
            elif power < limit * (self.margin - 0.1):
                for i in racks:
                    rid = visible_state.rack_ids[i]
                    if rid in self._caps:
                        del self._caps[rid]
                        actions.append(SetRackPowerCap(rid, None))
        return actions


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RackSpec:
    rack_id: str
    n_gpus: int
    breaker_rating_w: float

    def __post_init__(self) -> None:
        _nonempty(self.rack_id, "rack_id")
        if isinstance(self.n_gpus, bool) or int(self.n_gpus) < 1:
            raise ValueError("n_gpus must be an integer >= 1")
        _num(self.breaker_rating_w, "breaker_rating_w", strict=True)


@dataclass(frozen=True)
class SiteLayout:
    site: Site
    racks: Tuple[RackSpec, ...]

    def __post_init__(self) -> None:
        total = sum(r.n_gpus for r in self.racks)
        if total != self.site.accelerator_count:
            raise ValueError(
                f"site {self.site.site_id!r}: racks hold {total} GPUs but accelerator_count is {self.site.accelerator_count}"
            )


@dataclass(frozen=True)
class ThermalAssumptions:
    """Rack thermal parameters (all scenario assumptions unless cited in the scenario)."""

    heat_capacity_j_per_k_per_gpu: float
    design_air_rise_k: float
    cooling_lag_s: float
    supply_setpoint_c: float
    outdoor_coupling_k_per_k: float
    outdoor_reference_c: float
    capacity_derate_per_k: float
    capacity_derate_reference_c: float
    gpu_to_air_k_per_w: float
    gpu_to_air_rel_sigma: float
    breaker_reset_delay_s: float
    gpu_shutdown_c: float
    thermal_shutdown_hold_s: float

    def __post_init__(self) -> None:
        for name in (
            "heat_capacity_j_per_k_per_gpu", "design_air_rise_k",
        ):
            _num(getattr(self, name), name, strict=True)
        for name in (
            "cooling_lag_s", "capacity_derate_per_k", "gpu_to_air_k_per_w", "gpu_to_air_rel_sigma",
            "breaker_reset_delay_s", "thermal_shutdown_hold_s",
        ):
            _num(getattr(self, name), name)
        for name in ("supply_setpoint_c", "outdoor_coupling_k_per_k", "outdoor_reference_c", "capacity_derate_reference_c", "gpu_shutdown_c"):
            _num(getattr(self, name), name, minimum=-100.0)


@dataclass(frozen=True)
class TransferParams:
    """Checkpoint, WAN and restart parameters (from the e001 scenarios)."""

    wan_bandwidth_bytes_per_second: float
    wan_latency_s: float
    restore_bandwidth_bytes_per_second: float
    fixed_restart_latency_s: float
    membership_reconfiguration_s: float
    checkpoint_bytes_per_gpu: float

    def __post_init__(self) -> None:
        for name in ("wan_bandwidth_bytes_per_second", "restore_bandwidth_bytes_per_second", "checkpoint_bytes_per_gpu"):
            _num(getattr(self, name), name, strict=True)
        for name in ("wan_latency_s", "fixed_restart_latency_s", "membership_reconfiguration_s"):
            _num(getattr(self, name), name)

    def transfer_s(self, n_gpus: int) -> float:
        return n_gpus * self.checkpoint_bytes_per_gpu / self.wan_bandwidth_bytes_per_second + self.wan_latency_s + self.membership_reconfiguration_s

    def restore_s(self, n_gpus: int) -> float:
        return n_gpus * self.checkpoint_bytes_per_gpu / self.restore_bandwidth_bytes_per_second + self.fixed_restart_latency_s

    def merge_stall_s(self, shard_gpus: int) -> float:
        return shard_gpus * self.checkpoint_bytes_per_gpu / self.wan_bandwidth_bytes_per_second + self.wan_latency_s


@dataclass(frozen=True)
class SimConfig:
    scenario_id: str
    horizon_s: float
    base_dt_s: float
    control_dt_s: float
    controller_interval_s: float
    history_s: float
    known_future_horizon_s: float
    compute_fraction_of_step: float
    start_utc: str
    layouts: Tuple[SiteLayout, ...]
    levels: PowerLevels
    thermal: ThermalAssumptions
    throttle: GPUThrottleModel
    cooling_power: CoolingPowerModel
    breaker: InverseTimeBreaker
    transfer: TransferParams
    jobs: Tuple[Job, ...]
    events: EventSchedule
    environment: Mapping[str, SiteEnvironment]
    gpu_windows: Union[str, Tuple[Tuple[float, float], ...]]
    measured_levels: Mapping[str, Any]
    assumptions: Tuple[str, ...]
    scenario: Mapping[str, Any]

    def __post_init__(self) -> None:
        _nonempty(self.scenario_id, "scenario_id")
        for name in ("horizon_s", "base_dt_s", "control_dt_s", "controller_interval_s", "history_s", "known_future_horizon_s"):
            _num(getattr(self, name), name, strict=True)
        k = self.control_dt_s / self.base_dt_s
        if abs(k - round(k)) > 1e-9:
            raise ValueError("control_dt_s must be a whole multiple of base_dt_s")
        if abs(60.0 / self.control_dt_s - round(60.0 / self.control_dt_s)) > 1e-9:
            raise ValueError("control_dt_s must divide 60 s")
        ci = self.controller_interval_s / self.control_dt_s
        if abs(ci - round(ci)) > 1e-9:
            raise ValueError("controller_interval_s must be a whole multiple of control_dt_s")
        if abs(self.horizon_s / 3600.0 - round(self.horizon_s / 3600.0)) > 1e-9:
            raise ValueError("horizon_s must be a whole number of hours")
        _num(self.compute_fraction_of_step, "compute_fraction_of_step", strict=True, maximum=1.0)
        ids = [lay.site.site_id for lay in self.layouts]
        if len(set(ids)) != len(ids):
            raise ValueError("site ids must be unique")
        rack_ids = [r.rack_id for lay in self.layouts for r in lay.racks]
        if len(set(rack_ids)) != len(rack_ids):
            raise ValueError("rack ids must be unique across sites")
        for sid in ids:
            if sid not in self.environment:
                raise ValueError(f"missing environment for site {sid!r}")
        job_ids = [j.job_id for j in self.jobs]
        if len(set(job_ids)) != len(job_ids):
            raise ValueError("job ids must be unique")
        n_env = int(round(self.horizon_s / 3600.0)) + 1
        for sid in ids:
            env = self.environment[sid]
            if env.step_s != 3600.0 or env.outdoor_c.size < n_env:
                raise ValueError(f"environment for {sid!r} needs hourly values covering the horizon plus one")
        for j in self.jobs:
            if j.site_id is not None and j.site_id not in ids:
                raise ValueError(f"job {j.job_id!r} names unknown site {j.site_id!r}")
            if j.multisite and len(ids) < 2:
                raise ValueError("multisite jobs need at least two sites")


def _transfer_from_dict(d: Mapping[str, Any]) -> TransferParams:
    return TransferParams(**{k: d[k] for k in TransferParams.__dataclass_fields__})


def build_config(scenario: Mapping[str, Any], seed: int = 0, environment: Optional[Mapping[str, SiteEnvironment]] = None) -> SimConfig:
    """Turn a scenario dict (see ``experiments/e003-heatwave/sim-scenario-v1.json``) into a config."""
    if scenario.get("schema") != SCENARIO_SCHEMA:
        raise ValueError(f"scenario schema must be {SCENARIO_SCHEMA!r}")
    if scenario.get("data_kind") != "simulated":
        raise ValueError("scenario data_kind must be 'simulated'")
    if abs(float(scenario["horizon_s"]) / 3600.0 - round(float(scenario["horizon_s"]) / 3600.0)) > 1e-9:
        raise ValueError("horizon_s must be a whole number of hours")
    layouts = []
    for item in scenario["sites"]:
        site = Site(**item["site"])
        racks = tuple(RackSpec(**r) for r in item["racks"])
        layouts.append(SiteLayout(site, racks))
    site_ids = [lay.site.site_id for lay in layouts]

    gcfg = scenario["gpu"]
    preset_name = gcfg["preset"]
    if preset_name != "h100_sxm_80gb_gpu":
        raise ValueError("only the h100_sxm_80gb_gpu preset is wired in")
    from ..presets.hardware import h100_sxm_80gb_gpu

    tdp_w = float(h100_sxm_80gb_gpu.assignments["gpu.tdp"])
    pl = scenario["power_levels"]
    measured = measure_e002_levels(_resolve_path(pl.get("e002_raw_path", E002_RAW_RELATIVE_PATH)))
    levels = PowerLevels.from_e002(
        measured,
        tdp_w=tdp_w,
        compute_fraction_of_tdp=gcfg["compute_fraction_of_tdp"],
        comm_ratio=pl.get("comm_ratio", "idle_ratio"),
        checkpoint_ratio=pl.get("checkpoint_ratio", "measured"),
        host_fraction_of_compute=gcfg["host_fraction_of_compute"],
        idle_ratio_override=pl.get("idle_ratio_override"),
        noise_scale=pl.get("noise_scale", 1.0),
        calibration_notes=pl.get("calibration_notes"),
    )
    th = ThermalAssumptions(**scenario["thermal"])
    throttle = GPUThrottleModel(**scenario["throttle"])
    cp = scenario["cooling_power"]
    if cp["kind"] == "pue":
        cooling = CoolingPowerModel(kind="pue", pue=cp["pue"])
    else:
        cooling = CoolingPowerModel.carnot_from_pue(
            pue=cp["pue"], reference_outdoor_c=cp["reference_outdoor_c"], reference_supply_c=cp["reference_supply_c"],
            evaporator_approach_k=cp["evaporator_approach_k"], condenser_approach_k=cp["condenser_approach_k"],
            cop_min=cp["cop_min"], cop_max=cp["cop_max"],
        )
    breaker = InverseTimeBreaker(**scenario.get("breaker", {}))
    transfer = _transfer_from_dict(scenario["transfer"])

    jspec = scenario["jobs"]
    if "list" in jspec:
        jobs = [Job.from_dict(j) for j in jspec["list"]]
    else:
        g = dict(jspec["generate"])
        total = sum(lay.site.accelerator_count for lay in layouts)
        for key in ("duration_range_s", "checkpoint_every_range_s", "checkpoint_duration_range_s", "value_range"):
            g[key] = tuple(g[key])
        jobs = generate_jobs(
            seed=g.pop("seed", seed), horizon_s=scenario["horizon_s"], total_gpus=total, site_ids=site_ids, **g
        )
    events = EventSchedule.from_dicts(scenario.get("events", []))

    if environment is None:
        espec = scenario["environment"]
        if "synthetic" in espec:
            environment = synthetic_environment(espec["synthetic"], site_ids, scenario["horizon_s"], espec.get("seed", seed))
        else:
            environment = {
                sid: SiteEnvironment(**{k: np.asarray(v) if isinstance(v, list) else v for k, v in espec["sites"][sid].items()})
                for sid in site_ids
            }
    windows = scenario.get("outputs", {}).get("gpu_windows", [])
    if windows != "all":
        windows = tuple((float(a), float(b)) for a, b in windows)

    return SimConfig(
        scenario_id=scenario["scenario_id"], horizon_s=float(scenario["horizon_s"]), base_dt_s=float(scenario["base_dt_s"]),
        control_dt_s=float(scenario["control_dt_s"]), controller_interval_s=float(scenario["controller_interval_s"]),
        history_s=float(scenario.get("history_s", 7200.0)),
        known_future_horizon_s=float(scenario.get("known_future_horizon_s", 86_400.0)),
        compute_fraction_of_step=float(gcfg["compute_fraction_of_step"]), start_utc=str(scenario["start_utc"]),
        layouts=tuple(layouts), levels=levels, thermal=th, throttle=throttle, cooling_power=cooling, breaker=breaker,
        transfer=transfer, jobs=tuple(jobs), events=events, environment=dict(environment), gpu_windows=windows,
        measured_levels=measured, assumptions=tuple(scenario.get("assumptions", ())), scenario=scenario,
    )


def _resolve_path(p: Union[str, Path]) -> Path:
    path = Path(p)
    return path if path.is_absolute() else _REPO_ROOT / path


# ---------------------------------------------------------------------------
# Planning (job-level, no physics)
# ---------------------------------------------------------------------------


class _Placement:
    """Free-GPU bookkeeping shared by the planner and the simulator."""

    def __init__(self, site_of_gpu: np.ndarray, n_sites: int) -> None:
        self.site_of_gpu = site_of_gpu
        self.n_sites = n_sites
        self.site_gpus = [np.flatnonzero(site_of_gpu == s) for s in range(n_sites)]

    def choose_site(self, free: np.ndarray, n_needed: int, hint: Optional[int]) -> Optional[int]:
        if hint is not None:
            return hint if int(free[self.site_gpus[hint]].sum()) >= n_needed else None
        best, best_free = None, -1
        for s in range(self.n_sites):
            f = int(free[self.site_gpus[s]].sum())
            if f >= n_needed and f > best_free:
                best, best_free = s, f
        return best

    def pick(self, free: np.ndarray, site: int, n_needed: int) -> np.ndarray:
        cand = self.site_gpus[site]
        idx = cand[free[cand]]
        return idx[:n_needed]


@dataclass(frozen=True)
class PlannedJob:
    job_id: str
    site_ids: Tuple[str, ...]
    start_s: float
    end_s: float
    gpus_by_rack: Mapping[str, int]
    job: Job


def _quantize_up(t: float, dt: float) -> float:
    return math.ceil(t / dt - 1e-9) * dt


def stall_cycle(job: Job, transfer: TransferParams) -> Tuple[float, float, int]:
    """``(run_seconds_between_stalls, stall_seconds, n_stalls)`` for a job with no faults.

    Single-site jobs stall to checkpoint; multi-site jobs stall to average
    (the shards' state is exchanged over the WAN every ``average_every_steps``).
    """
    if job.multisite:
        every = job.average_every_steps * job.step_time_s
        stall = transfer.merge_stall_s(job.n_gpus // 2)
    else:
        every, stall = job.checkpoint_every_s, job.checkpoint_duration_s
    n = int(math.floor(job.duration_s / every - 1e-12))
    return every, stall, n


def nominal_job_span_s(job: Job, transfer: TransferParams) -> float:
    """Wall time of a job with no faults, no throttling: run time plus stalls."""
    _, stall, n = stall_cycle(job, transfer)
    return job.duration_s + n * stall


def plan_schedule(config: SimConfig) -> list[PlannedJob]:
    """Job-level schedule if nothing goes wrong: FIFO packing with the simulator's placement rule.

    The simulator's admission step uses the same rule, so with no events and no
    throttling the realized schedule equals this plan.  Starts are quantized up
    to the control step.
    """
    site_ids = [lay.site.site_id for lay in config.layouts]
    gpu_site, gpu_rack_id = [], []
    for s, lay in enumerate(config.layouts):
        for r in lay.racks:
            gpu_site += [s] * r.n_gpus
            gpu_rack_id += [r.rack_id] * r.n_gpus
    place = _Placement(np.array(gpu_site), len(site_ids))
    free = np.ones(len(gpu_site), dtype=bool)
    cdt = config.control_dt_s
    pending = sorted(config.jobs, key=lambda j: (j.start_s, j.job_id))
    releases: list[Tuple[float, int, np.ndarray]] = []
    plans: list[PlannedJob] = []
    t = 0.0
    counter = 0
    n_blocks = int(round(config.horizon_s / cdt))
    for b in range(n_blocks + 1):
        t = b * cdt
        while releases and releases[0][0] <= t + 1e-9:
            _, _, idx = heapq.heappop(releases)
            free[idx] = True
        still = []
        for job in pending:
            if _quantize_up(job.start_s, cdt) > t + 1e-9:
                still.append(job)
                continue
            hint = site_ids.index(job.site_id) if job.site_id else None
            if job.multisite:
                halves = job.n_gpus // 2
                if all(int(free[place.site_gpus[s]].sum()) >= halves for s in (0, 1)):
                    idx = np.concatenate([place.pick(free, s, halves) for s in (0, 1)])
                    sites = (site_ids[0], site_ids[1])
                else:
                    still.append(job)
                    continue
            else:
                s = place.choose_site(free, job.n_gpus, hint)
                if s is None:
                    still.append(job)
                    continue
                idx = place.pick(free, s, job.n_gpus)
                sites = (site_ids[s],)
            free[idx] = False
            end = t + nominal_job_span_s(job, config.transfer)
            counter += 1
            heapq.heappush(releases, (end, counter, idx))
            by_rack: dict[str, int] = {}
            for g in idx:
                by_rack[gpu_rack_id[g]] = by_rack.get(gpu_rack_id[g], 0) + 1
            plans.append(PlannedJob(job.job_id, sites, t, end, by_rack, job))
        pending = still
        if not pending and not releases:
            break
    return plans


def _G(x: np.ndarray, c: float) -> np.ndarray:
    """Cumulative time in compute (in step units) after ``x`` completed steps."""
    fl = np.floor(x)
    return fl * c + np.minimum(x - fl, c)


def planned_covariates(
    config: SimConfig,
    plans: Sequence[PlannedJob],
    resolution_s: float,
    level: str,
    t0_s: float = 0.0,
    t1_s: Optional[float] = None,
) -> dict[str, np.ndarray]:
    """Known-future covariates from the plan, binned to ``resolution_s``.

    ``level`` is ``'rack'`` or ``'site'``.  Keys (shape ``(T, units)``):

    ``planned_gpus_running``   GPUs planned to be running, bin average;
    ``scheduled_checkpoint_gpus``  GPUs planned to be in a checkpoint, bin average;
    ``step_phase_compute_fraction``  bin average of the planned compute indicator
        over planned running GPUs (0 when none are planned);
    ``outdoor_forecast_c`` / ``price_usd_per_kwh`` / ``carbon_g_per_kwh``
        pass-through of the external series (mean over the bin; site series are
        mapped to racks).

    The plan assumes no faults and no throttling, so the phase drifts from the
    realized phase when the real run is slowed.
    """
    t1 = config.horizon_s if t1_s is None else t1_s
    nbins = int(round((t1 - t0_s) / resolution_s))
    edges = t0_s + np.arange(nbins + 1) * resolution_s
    site_ids = [lay.site.site_id for lay in config.layouts]
    rack_ids = [r.rack_id for lay in config.layouts for r in lay.racks]
    rack_site = [lay.site.site_id for lay in config.layouts for _ in lay.racks]
    units = rack_ids if level == "rack" else site_ids
    unit_index = {u: i for i, u in enumerate(units)}
    c = config.compute_fraction_of_step
    gpus = np.zeros((nbins, len(units)))
    ckpt = np.zeros((nbins, len(units)))
    comp = np.zeros((nbins, len(units)))
    for pj in plans:
        job = pj.job
        lo, hi = max(pj.start_s, t0_s), min(pj.end_s, t1)
        if hi <= lo:
            continue
        # Running (not stalled) time r(t) and checkpoint-stall time, cumulative, at bin edges.
        e = np.clip(edges, lo, hi) - pj.start_s
        every, dur, _n = stall_cycle(job, config.transfer)
        cyc = every + dur
        full = np.floor(e / cyc)
        u = e - full * cyc
        run = full * every + np.minimum(u, every)
        stall = full * dur + np.maximum(u - every, 0.0)
        in_job = np.diff(e)
        comp_time = np.diff(_G(run / job.step_time_s, c)) * job.step_time_s
        stall_time = np.diff(stall)
        share = {}
        for rack_id, n in pj.gpus_by_rack.items():
            key = rack_id if level == "rack" else rack_site[rack_ids.index(rack_id)]
            share[key] = share.get(key, 0) + n
        for key, n in share.items():
            col = unit_index[key]
            gpus[:, col] += n * in_job / resolution_s
            ckpt[:, col] += n * stall_time / resolution_s
            comp[:, col] += n * comp_time / resolution_s
    with np.errstate(divide="ignore", invalid="ignore"):
        phase = np.where(gpus > 0, comp / gpus, 0.0)
    out = {
        "planned_gpus_running": gpus,
        "scheduled_checkpoint_gpus": ckpt,
        "step_phase_compute_fraction": phase,
    }
    # External series pass-through, mean over each bin (hourly series, linear interpolation).
    sub = max(1, int(round(resolution_s / 60.0))) if resolution_s >= 60 else 1
    mids = (edges[:-1, None] + (np.arange(sub)[None, :] + 0.5) * resolution_s / sub)
    hours = np.arange(config.environment[site_ids[0]].outdoor_c.size) * 3600.0
    for name, attr in (("outdoor_forecast_c", "forecast_c"), ("price_usd_per_kwh", "price_usd_per_kwh"), ("carbon_g_per_kwh", "carbon_g_per_kwh")):
        cols = []
        for u in units:
            sid = u if level == "site" else rack_site[rack_ids.index(u)]
            series = getattr(config.environment[sid], attr)
            if name == "outdoor_forecast_c":
                cols.append(np.interp(mids, hours, series).mean(axis=1))
            else:  # price and carbon are piecewise constant per hour
                idx = np.clip((mids // 3600.0).astype(int), 0, series.size - 1)
                cols.append(series[idx].mean(axis=1))
        out[name] = np.stack(cols, axis=1)
    out["bin_start_s"] = edges[:-1]
    return out


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------


class _Shard:
    __slots__ = (
        "sid", "job", "job_index", "part", "n_gpus", "site", "gpus", "state", "left_s", "progress", "durable",
        "since_ckpt_s", "snapshot", "total", "paused", "ckpt_now", "migrate_to", "earliest_s", "forced_site",
        "needs_restore", "cursor", "useful_steps", "lost_steps", "skipped_steps", "faults", "restarts",
        "migrations", "run_s", "fault_merged", "arrive_s",
    )

    def __init__(self, sid: int, job: Job, job_index: int, part: int, n_gpus: int) -> None:
        self.sid = sid
        self.job = job
        self.job_index = job_index
        self.part = part
        self.n_gpus = n_gpus
        self.site: Optional[int] = None
        self.gpus = np.zeros(0, dtype=int)
        self.state = "queued"
        self.left_s = 0.0
        self.progress = 0.0
        self.durable = 0.0
        self.since_ckpt_s = 0.0
        self.snapshot = 0.0
        self.total = job.total_steps
        self.paused = False
        self.ckpt_now = False
        self.migrate_to: Optional[int] = None
        self.earliest_s = job.start_s
        self.forced_site: Optional[int] = None
        self.needs_restore = False
        self.cursor = 0.0
        self.useful_steps = 0.0
        self.lost_steps = 0.0
        self.skipped_steps = 0.0
        self.faults = 0
        self.restarts = 0
        self.migrations = 0
        self.run_s = 0.0
        self.fault_merged = 0.0
        self.arrive_s = 0.0


_LIVE_BARRIER = ("running", "ckpt", "wait", "merge")


class _Run:
    """One simulation run.  Holds all mutable state; nothing is global."""

    def __init__(self, cfg: SimConfig, controller: Optional[Controller], seed: int) -> None:
        self.cfg = cfg
        self.controller = controller
        self.seed = int(seed)
        self._build_layout()
        self._build_jobs()
        self._build_environment()
        self._allocate_outputs()

    # -- setup ---------------------------------------------------------------

    def _build_layout(self) -> None:
        cfg = self.cfg
        self.site_ids = [lay.site.site_id for lay in cfg.layouts]
        self.S = len(self.site_ids)
        rack_ids, rack_site, rack_n, rating = [], [], [], []
        gpu_site, gpu_rack, gpu_slot = [], [], []
        for s, lay in enumerate(cfg.layouts):
            for r in lay.racks:
                ri = len(rack_ids)
                rack_ids.append(r.rack_id)
                rack_site.append(s)
                rack_n.append(r.n_gpus)
                rating.append(r.breaker_rating_w)
                gpu_site += [s] * r.n_gpus
                gpu_rack += [ri] * r.n_gpus
                gpu_slot += list(range(r.n_gpus))
        self.rack_ids = rack_ids
        self.R = len(rack_ids)
        self.rack_site = np.array(rack_site)
        self.rack_site_ids = [self.site_ids[s] for s in rack_site]
        self.rack_n = np.array(rack_n)
        self.rack_start = np.concatenate([[0], np.cumsum(self.rack_n)[:-1]])
        self.G = int(self.rack_n.sum())
        self.gpu_site = np.array(gpu_site)
        self.gpu_rack = np.array(gpu_rack)
        self.gpu_slot = np.array(gpu_slot)
        self.rating = np.array(rating, dtype=float)
        self.place = _Placement(self.gpu_site, self.S)
        self.site_membership = np.zeros((self.R, self.S))
        self.site_membership[np.arange(self.R), self.rack_site] = 1.0
        th = cfg.thermal
        lv = cfg.levels
        self.C = self.rack_n * th.heat_capacity_j_per_k_per_gpu
        design_p = self.rack_n * (lv.compute_w + lv.host_w_per_gpu)
        self.Rres = th.design_air_rise_k / design_p
        site_gpus = np.array([lay.site.accelerator_count for lay in cfg.layouts], dtype=float)
        site_cool = np.array([float(lay.site.cooling_capacity_w) for lay in cfg.layouts])
        self.cap_nominal = site_cool[self.rack_site] * self.rack_n / site_gpus[self.rack_site]
        rng = np.random.default_rng([self.seed, 303])
        self.k_gpu = th.gpu_to_air_k_per_w * np.clip(1.0 + th.gpu_to_air_rel_sigma * rng.normal(size=self.G), 0.2, None)
        self.site_cap = np.array([float(lay.site.power_cap_w) for lay in cfg.layouts])
        self.site_import = np.array([float(lay.site.grid_import_limit_w) for lay in cfg.layouts])
        self.site_base = np.array([float(lay.site.base_power_w) for lay in cfg.layouts])
        self.cdt = cfg.control_dt_s
        self.dt = cfg.base_dt_s
        self.K = int(round(self.cdt / self.dt))
        self.Nb = int(round(cfg.horizon_s / self.cdt))
        self.N = self.Nb * self.K
        times = np.arange(self.Nb) * self.cdt
        self.block_start = times
        self.signals: EventSignals = cfg.events.resolve(times, self.cdt, self.site_ids, self.rack_ids, self.rack_site_ids, list(self.rack_n))
        if cfg.gpu_windows == "all":
            self.windows: list[Tuple[float, float]] = [(0.0, cfg.horizon_s)]
        else:
            self.windows = [tuple(w) for w in cfg.gpu_windows]  # type: ignore[misc]
        for a, b in self.windows:
            for v in (a, b):
                if abs(v / self.cdt - round(v / self.cdt)) > 1e-9:
                    raise ValueError("gpu window bounds must be multiples of control_dt_s")
            if not 0.0 <= a < b <= cfg.horizon_s:
                raise ValueError("gpu window must lie inside the horizon")
        est = sum((b - a) / self.dt * self.G * 8 for a, b in self.windows)
        if est > 2.0e9:
            raise ValueError("requested per-GPU windows exceed 2 GB; request shorter windows")

    def _build_jobs(self) -> None:
        cfg = self.cfg
        self.jobs = list(cfg.jobs)
        self.shards: list[_Shard] = []
        self.job_shards: list[list[_Shard]] = []
        self.job_index = {j.job_id: i for i, j in enumerate(self.jobs)}
        self.merged_progress = [0.0] * len(self.jobs)
        for ji, job in enumerate(self.jobs):
            parts = 2 if job.multisite else 1
            group = []
            for p in range(parts):
                sh = _Shard(len(self.shards), job, ji, p, job.n_gpus // parts)
                sh.forced_site = None
                self.shards.append(sh)
                group.append(sh)
            self.job_shards.append(group)
        self.n_shards = len(self.shards)
        self.gpu_shard = np.full(self.G, self.n_shards, dtype=int)  # row n_shards means no job
        self.gpu_alive = np.ones(self.G, dtype=bool)
        self.gpu_down_until = np.zeros(self.G)
        self.rack_on = np.ones(self.R, dtype=bool)
        self.rack_off_until = np.zeros(self.R)
        self.pending_order = sorted(range(self.n_shards), key=lambda i: (self.shards[i].job.start_s, self.shards[i].job.job_id, self.shards[i].part))
        self.pending: list[int] = list(self.pending_order)
        self.admit_dirty = True
        self.next_eligible_s = 0.0
        self.action_log: list[dict[str, Any]] = []
        self.event_log: list[dict[str, Any]] = []
        self.rack_cap_w = np.full(self.R, np.inf)
        self.merge_stall = {}
        for sh in self.shards:
            if sh.job.multisite:
                self.merge_stall[sh.sid] = self.cfg.transfer.merge_stall_s(sh.n_gpus)

    def _build_environment(self) -> None:
        cfg = self.cfg
        mids = (np.arange(self.Nb) + 0.5) * self.cdt
        hours = np.arange(cfg.environment[self.site_ids[0]].outdoor_c.size) * 3600.0
        self.outdoor_b = np.stack([np.interp(mids, hours, cfg.environment[s].outdoor_c) for s in self.site_ids], axis=1)
        H = int(round(cfg.horizon_s / 3600.0))
        self.price_h = np.stack([cfg.environment[s].price_usd_per_kwh[:H] for s in self.site_ids], axis=1)
        self.carbon_h = np.stack([cfg.environment[s].carbon_g_per_kwh[:H] for s in self.site_ids], axis=1)

    def _allocate_outputs(self) -> None:
        N, Nb, R, S = self.N, self.Nb, self.R, self.S
        self.rack_gpu_w = np.zeros((N, R))
        self.rack_host_b = np.zeros((Nb, R))
        self.rack_cool_b = np.zeros((Nb, R))
        self.rack_air_b = np.zeros((Nb, R))
        self.rack_supply_b = np.zeros((Nb, R))
        self.rack_maxgpu_b = np.zeros((Nb, R))
        self.rack_throttled_b = np.zeros((Nb, R))
        self.rack_ratio_b = np.zeros((Nb, R))
        self.rack_removed_b = np.zeros((Nb, R))
        self.rack_cap_b = np.zeros((Nb, R))
        self.rack_on_b = np.zeros((Nb, R), dtype=bool)
        self.site_free_b = np.zeros((Nb, S))
        self.window_data: list[np.ndarray] = [np.zeros((self.G, int(round((b - a) / self.dt)))) for a, b in self.windows]
        self.gpu_mean_prev = np.full(self.G, self.cfg.levels.idle_w)
        self.noise_cache: dict[int, np.ndarray] = {}

    # -- helpers -------------------------------------------------------------

    def _noise(self, block: int) -> np.ndarray:
        per_chunk = int(round(3600.0 / self.cdt))
        chunk = block // per_chunk
        if chunk not in self.noise_cache:
            self.noise_cache = {}
            rng = np.random.default_rng([self.seed, 404, chunk])
            self.noise_cache[chunk] = rng.standard_normal((self.G, int(round(3600.0 / self.dt)))).astype(np.float32)
        arr = self.noise_cache[chunk]
        j = (block % per_chunk) * self.K
        return arr[:, j:j + self.K]

    def _capacity_derate(self, outdoor_c: np.ndarray) -> np.ndarray:
        """Cooling capacity factor from outdoor temperature (never below zero)."""
        th = self.cfg.thermal
        return np.clip(1.0 - th.capacity_derate_per_k * np.maximum(0.0, outdoor_c - th.capacity_derate_reference_c), 0.0, 1.0)

    def _free_mask(self) -> np.ndarray:
        return self.gpu_alive & self.rack_on[self.gpu_rack] & (self.gpu_shard == self.n_shards)

    def _log(self, t: float, kind: str, **detail: Any) -> None:
        self.event_log.append({"t_s": float(t), "kind": kind, **detail})

    def _release(self, sh: _Shard) -> None:
        if sh.gpus.size:
            self.gpu_shard[sh.gpus] = self.n_shards
        sh.gpus = np.zeros(0, dtype=int)
        self.admit_dirty = True

    # -- faults ----------------------------------------------------------------

    def _fault_shard(self, sh: _Shard, t: float, reason: str) -> None:
        if sh.state in ("done", "queued"):
            return
        if sh.job.multisite:
            durable = self.merged_progress[sh.job_index]
        else:
            durable = sh.durable
        lost = max(sh.progress - durable, 0.0)
        sh.lost_steps += lost
        sh.useful_steps -= lost
        sh.progress = durable
        sh.fault_merged = self.merged_progress[sh.job_index]
        sh.faults += 1
        sh.needs_restore = True
        sh.state = "queued"
        sh.ckpt_now = False
        sh.migrate_to = None
        sh.since_ckpt_s = 0.0
        sh.earliest_s = t
        sh.forced_site = None if not sh.job.multisite else sh.forced_site
        self._release(sh)
        if sh.sid not in self.pending:
            self.pending.append(sh.sid)
            self.pending.sort(key=lambda i: (0 if self.shards[i].needs_restore else 1, self.shards[i].job.start_s, self.shards[i].job.job_id, self.shards[i].part))
        self._log(t, "job_fault", job_id=sh.job.job_id, part=sh.part, reason=reason, lost_steps=lost)

    def _trip_rack(self, r: int, t: float, off_s: float, reason: str, kind: str = KIND_BREAKER_TRIP) -> None:
        self.rack_on[r] = False
        self.rack_off_until[r] = t + off_s
        self._log(t, kind, rack_id=self.rack_ids[r], site_id=self.rack_site_ids[r], reason=reason, off_s=off_s)
        for sh in self.shards:
            if sh.gpus.size and np.any(self.gpu_rack[sh.gpus] == r):
                self._fault_shard(sh, t, f"rack {self.rack_ids[r]} off ({reason})")

    # -- admission -------------------------------------------------------------

    def _try_place(self, sh: _Shard, t: float) -> bool:
        free = self._free_mask()
        job = sh.job
        if job.multisite:
            site = sh.part
            if int(free[self.place.site_gpus[site]].sum()) < sh.n_gpus:
                return False
            fresh = [o for o in self.job_shards[sh.job_index] if o.state == "queued" and not o.needs_restore]
            for o in fresh:
                if int(free[self.place.site_gpus[o.part]].sum()) < o.n_gpus:
                    return False
        else:
            hint = sh.forced_site
            if hint is None and job.site_id is not None:
                hint = self.site_ids.index(job.site_id)
            site = self.place.choose_site(free, sh.n_gpus, hint)
            if site is None:
                return False
        idx = self.place.pick(free, site, sh.n_gpus)
        if idx.size != sh.n_gpus:  # pragma: no cover - guarded by the free-count checks above
            raise RuntimeError("placement returned the wrong number of GPUs")
        sh.gpus = idx
        sh.site = site
        self.gpu_shard[idx] = sh.sid
        if sh.needs_restore:
            sh.restarts += 1
            sh.state = "restore"
            sh.left_s = self.cfg.transfer.restore_s(sh.n_gpus)
            sh.needs_restore = False
        else:
            sh.state = "running"
        self._log(t, "job_start" if sh.restarts == 0 else "job_restart", job_id=job.job_id, part=sh.part, site_id=self.site_ids[site])
        return True

    def _admit(self, t: float) -> None:
        still = []
        next_elig = math.inf
        for sid in self.pending:
            sh = self.shards[sid]
            elig = _quantize_up(sh.earliest_s, self.cdt)
            if elig > t + 1e-9:
                still.append(sid)
                next_elig = min(next_elig, elig)
                continue
            if not self._try_place(sh, t):
                still.append(sid)
        self.pending = still
        self.next_eligible_s = next_elig
        self.admit_dirty = False

    # -- controller ----------------------------------------------------------------

    def _job_status(self, group: list[_Shard]) -> str:
        states = {s.state for s in group}
        if states == {"done"}:
            return "done"
        if states <= {"queued"}:
            return "queued"
        if any(s.paused for s in group):
            return "paused"
        for k in ("transfer", "restore", "ckpt", "merge", "wait", "running"):
            if k in states:
                return k
        return "queued"

    def _visible_state(self, t: float, b: int) -> VisibleState:
        cfg = self.cfg
        free_mask = self._free_mask()
        raw_temp = self.rack_air_now[self.gpu_rack] + self.k_gpu * self.gpu_mean_prev
        # Precursor offsets are part of what the GPU's own sensor reports, so they are visible.
        for r, slot, off in self.signals.gpu_temp_offsets(t):
            raw_temp[self.rack_start[r] + slot] += off
        gpu_temp = np.where(self.gpu_alive & self.rack_on[self.gpu_rack], raw_temp, np.nan)
        eff_import = self.site_import * self.signals.import_limit_factor[b]
        site_power = self.site_power_prev.copy()
        now = {
            "rack_air_c": self.rack_air_now.copy(),
            "supply_c": self.supply_now.copy(),
            "rack_it_power_w": self.rack_it_prev.copy(),
            "max_gpu_temp_c": self._rack_max(gpu_temp),
            "breaker_load_ratio": self.rack_ratio_prev.copy(),
            "rack_on": self.rack_on.copy(),
            "rack_power_cap_w": self.rack_cap_w.copy(),
            "site_power_w": site_power,
            "site_power_cap_w": self.site_cap.copy(),
            "site_import_limit_w": eff_import,
            "free_gpus": np.array([int(free_mask[self.place.site_gpus[s]].sum()) for s in range(self.S)]),
            "gpu_temp_c": gpu_temp,
        }
        jobs = []
        for ji, job in enumerate(self.jobs):
            if job.submit_s > t + 1e-9:
                continue
            group = self.job_shards[ji]
            status = self._job_status(group)
            if status == "done":
                continue
            prog = float(np.mean([s.progress for s in group]))
            dur = float(np.mean([(self.merged_progress[ji] if job.multisite else s.durable) for s in group]))
            jobs.append(
                JobView(
                    job_id=job.job_id, status=status,
                    site_ids=tuple(self.site_ids[s.site] for s in group if s.site is not None and s.gpus.size),
                    n_gpus=job.n_gpus, progress_steps=prog, total_steps=job.total_steps,
                    steps_since_durable=max(prog - dur, 0.0), flexible=job.flexible,
                    value_per_gpu_hour=job.value_per_gpu_hour, submit_s=job.submit_s,
                    planned_start_s=job.start_s, paused=any(s.paused for s in group),
                    rack_ids=tuple(sorted({self.rack_ids[int(r)] for s in group if s.gpus.size
                                           for r in np.unique(self.gpu_rack[s.gpus])})),
                )
            )
        horizon = cfg.known_future_horizon_s
        planned = tuple(
            {"job_id": j.job_id, "planned_start_s": j.start_s, "duration_s": j.duration_s, "n_gpus": j.n_gpus,
             "flexible": j.flexible, "site_id": j.site_id, "multisite": j.multisite}
            for j in self.jobs if t < j.start_s <= t + horizon
        )
        h0 = int(t // 3600.0)
        h1 = min(h0 + int(math.ceil(horizon / 3600.0)) + 1, self.price_h.shape[0] + 1)
        sel = slice(h0, h1)
        known_future = {
            "planned_jobs": planned,
            "announced_curtailments": tuple(cfg.events.announced_curtailments(t)),
            "hour_start_s": np.arange(h0, h1) * 3600.0,
            "outdoor_forecast_c": np.stack([cfg.environment[s].forecast_c[sel] for s in self.site_ids], axis=1),
            "price_usd_per_kwh": np.stack([cfg.environment[s].price_usd_per_kwh[sel] for s in self.site_ids], axis=1),
            "carbon_g_per_kwh": np.stack([cfg.environment[s].carbon_g_per_kwh[sel] for s in self.site_ids], axis=1),
        }
        n_valid = b

        def history(channel: str, window_s: float) -> Tuple[np.ndarray, np.ndarray]:
            arrays = {
                "rack_air_c": self.rack_air_b, "supply_c": self.rack_supply_b, "rack_it_power_w": self.rack_it_b,
                "max_gpu_temp_c": self.rack_maxgpu_b, "breaker_load_ratio": self.rack_ratio_b,
                "site_power_w": self.site_power_b, "rack_cooling_power_w": self.rack_cool_b,
            }
            if channel not in arrays:
                raise KeyError(f"unknown channel {channel!r}; choose from {sorted(arrays)}")
            n = min(int(math.ceil(window_s / self.cdt)), n_valid)
            lo = n_valid - n
            return (np.arange(lo, n_valid) + 1) * self.cdt, arrays[channel][lo:n_valid].copy()

        return VisibleState(
            t_s=t, site_ids=tuple(self.site_ids), rack_ids=tuple(self.rack_ids), rack_site_ids=tuple(self.rack_site_ids),
            now=now, jobs=tuple(jobs), known_future=known_future, _history=history,
        )

    def _rack_max(self, gpu_temp: np.ndarray) -> np.ndarray:
        masked = np.where(np.isnan(gpu_temp), -np.inf, gpu_temp)
        m = np.maximum.reduceat(masked, self.rack_start)
        out = np.where(np.isfinite(m), m, np.nan)
        return out

    def _apply_actions(self, actions: Sequence[Action], t: float) -> None:
        for act in actions or ():
            name = type(act).__name__
            status = "applied"
            try:
                if isinstance(act, SetRackPowerCap):
                    if act.rack_id not in self.rack_ids:
                        raise ValueError("unknown rack")
                    if act.cap_w is not None:
                        _num(act.cap_w, "cap_w")
                    self.rack_cap_w[self.rack_ids.index(act.rack_id)] = math.inf if act.cap_w is None else float(act.cap_w)
                else:
                    ji = self.job_index.get(act.job_id)
                    if ji is None:
                        raise ValueError("unknown job")
                    group = self.job_shards[ji]
                    job = self.jobs[ji]
                    if isinstance(act, AdmitJob):
                        if any(s.state != "queued" or s.needs_restore for s in group) or t < job.submit_s:
                            raise ValueError("job is not a not-yet-started submitted job")
                        for s in group:
                            s.earliest_s = t
                            if act.site_id is not None and not job.multisite:
                                if act.site_id not in self.site_ids:
                                    raise ValueError("unknown site")
                                s.forced_site = self.site_ids.index(act.site_id)
                        self.admit_dirty = True
                    elif isinstance(act, DeferJob):
                        if not job.flexible:
                            raise ValueError("job is not flexible")
                        if any(s.state != "queued" for s in group):
                            raise ValueError("job already started")
                        for s in group:
                            s.earliest_s = max(float(act.until_s), t)
                        self.admit_dirty = True
                    elif isinstance(act, PauseJob):
                        if not job.flexible:
                            raise ValueError("job is not flexible")
                        if all(s.state == "queued" or s.state == "done" for s in group):
                            raise ValueError("job is not placed")
                        for s in group:
                            s.paused = True
                    elif isinstance(act, ResumeJob):
                        for s in group:
                            s.paused = False
                    elif isinstance(act, CheckpointNow):
                        if job.multisite:
                            raise ValueError("multi-site jobs checkpoint through averaging")
                        if group[0].state != "running":
                            raise ValueError("job is not running")
                        group[0].ckpt_now = True
                    elif isinstance(act, MigrateJob):
                        sh = group[0]
                        if not job.flexible or job.multisite:
                            raise ValueError("job is not flexible or spans sites")
                        if sh.state != "running":
                            raise ValueError("job is not running")
                        if act.to_site_id not in self.site_ids:
                            raise ValueError("unknown site")
                        dest = self.site_ids.index(act.to_site_id)
                        if dest == sh.site:
                            raise ValueError("job is already at that site")
                        if int(self._free_mask()[self.place.site_gpus[dest]].sum()) < sh.n_gpus:
                            raise ValueError("destination lacks free GPUs")
                        sh.migrate_to = dest
                        sh.ckpt_now = True
                    else:
                        raise ValueError("unknown action type")
            except ValueError as exc:
                status = f"rejected: {exc}"
            detail = asdict(act) if is_dataclass(act) else {}
            self.action_log.append({"t_s": float(t), "action": name, "detail": detail, "status": status})

    # -- shard advance -----------------------------------------------------------------

    def _advance_shard(self, sh: _Shard, until: float, speed: float, segs: list) -> None:
        """Advance one shard from ``sh.cursor`` to ``until`` (offsets inside the block)."""
        job = sh.job
        tr = self.cfg.transfer
        guard = 0
        while until - sh.cursor > 1e-9 and guard < 64:
            guard += 1
            rem = until - sh.cursor
            st = sh.state
            if st == "running":
                if sh.paused:
                    sh.cursor = until
                    return
                rate = speed / job.step_time_s
                t_done = (sh.total - sh.progress) / rate
                t_ckpt = math.inf
                if not job.multisite:
                    t_ckpt = 0.0 if sh.ckpt_now else max(job.checkpoint_every_s - sh.since_ckpt_s, 0.0)
                t_merge = math.inf
                if job.multisite:
                    a = job.average_every_steps
                    boundary = (math.floor(self.merged_progress[sh.job_index] / a + 1e-9) + 1) * a
                    boundary = min(boundary, sh.total)
                    t_merge = max((boundary - sh.progress) / rate, 0.0)
                d = min(rem, t_done, t_ckpt, t_merge)
                if d > 0:
                    segs.append((sh.sid, 0, sh.cursor, d, sh.progress, rate))
                    sh.progress += rate * d
                    sh.useful_steps += rate * d
                    sh.since_ckpt_s += d
                    sh.run_s += d
                    sh.cursor += d
                if sh.progress >= sh.total - 1e-9:
                    sh.progress = sh.total
                    sh.state = "done"
                    self._release(sh)
                    self._log(self.t_now + sh.cursor, "job_done", job_id=job.job_id, part=sh.part)
                    return
                if job.multisite and t_merge <= d + 1e-12 and sh.progress >= boundary - 1e-9:
                    sh.progress = boundary
                    others = [o for o in self.job_shards[sh.job_index] if o is not sh and o.state in _LIVE_BARRIER]
                    if others:
                        sh.state = "wait"
                        sh.arrive_s = sh.cursor
                        return
                    self.merged_progress[sh.job_index] = boundary
                    continue
                if not job.multisite and (sh.ckpt_now or sh.since_ckpt_s >= job.checkpoint_every_s - 1e-9):
                    sh.state = "ckpt"
                    sh.left_s = job.checkpoint_duration_s
                    sh.snapshot = sh.progress
                    sh.ckpt_now = False
                    if sh.left_s <= 0:
                        sh.durable = sh.snapshot
                        sh.since_ckpt_s = 0.0
                        sh.state = "running"
            elif st == "ckpt":
                d = min(rem, sh.left_s)
                if d > 0:
                    segs.append((sh.sid, 2, sh.cursor, d, 0.0, 0.0))
                sh.left_s -= d
                sh.cursor += d
                if sh.left_s <= 1e-9:
                    sh.durable = sh.snapshot
                    sh.since_ckpt_s = 0.0
                    sh.state = "running"
                    if sh.migrate_to is not None:
                        self._begin_transfer(sh)
            elif st in ("restore", "transfer", "merge"):
                d = min(rem, sh.left_s)
                if d > 0:
                    mode = 1 if st == "merge" else 3
                    segs.append((sh.sid, mode, sh.cursor, d, 0.0, 0.0))
                sh.left_s -= d
                sh.cursor += d
                if sh.left_s <= 1e-9:
                    if st == "merge":
                        sh.state = "running"
                        if sh.arrive_s >= 0:
                            self.merged_progress[sh.job_index] = max(self.merged_progress[sh.job_index], sh.progress)
                    elif st == "transfer":
                        sh.state = "restore"
                        sh.left_s = tr.restore_s(sh.n_gpus)
                    else:  # restore finished
                        if job.multisite and any(o is not sh and o.state in _LIVE_BARRIER for o in self.job_shards[sh.job_index]):
                            adopted = self.merged_progress[sh.job_index]
                            sh.skipped_steps += max(adopted - sh.progress, 0.0)
                            sh.progress = max(adopted, sh.progress)
                            sh.state = "merge"
                            sh.left_s = self.merge_stall[sh.sid]
                            sh.arrive_s = -1.0
                        else:
                            sh.state = "running"
            elif st == "wait":
                return  # held at the barrier; resolved by the job-level loop
            else:
                return

    def _begin_transfer(self, sh: _Shard) -> None:
        dest = sh.migrate_to
        sh.migrate_to = None
        assert dest is not None
        free = self._free_mask()
        src_gpus = sh.gpus
        if int(free[self.place.site_gpus[dest]].sum()) < sh.n_gpus:
            self._log(self.t_now + sh.cursor, "migration_cancelled", job_id=sh.job.job_id)
            return
        idx = self.place.pick(free, dest, sh.n_gpus)
        self.gpu_shard[src_gpus] = self.n_shards
        self.gpu_shard[idx] = sh.sid
        sh.gpus = idx
        sh.site = dest
        sh.state = "transfer"
        sh.left_s = self.cfg.transfer.transfer_s(sh.n_gpus)
        sh.migrations += 1
        self.admit_dirty = True
        self._log(self.t_now + sh.cursor, "migration_start", job_id=sh.job.job_id, to_site_id=self.site_ids[dest])

    def _advance_job(self, ji: int, speeds: np.ndarray, segs: list) -> None:
        group = self.job_shards[ji]
        active = [s for s in group if s.state not in ("queued", "done")]
        if not active:
            return
        for s in active:
            s.cursor = 0.0
            if s.state == "wait":
                s.arrive_s = 0.0
        for _ in range(16):
            for s in active:
                if s.state != "wait":
                    self._advance_shard(s, self.cdt, float(speeds[s.sid]), segs)
            waiting = [s for s in active if s.state == "wait"]
            live = [s for s in active if s.state in _LIVE_BARRIER]
            if len(live) == 1 and waiting:
                lone = waiting[0]
                lone.state = "running"
                self.merged_progress[ji] = max(self.merged_progress[ji], lone.progress)
                continue
            if waiting and len(waiting) == len(live):
                tb = max(s.arrive_s for s in waiting)
                if tb >= self.cdt - 1e-9:
                    for s in waiting:
                        segs.append((s.sid, 1, s.arrive_s, self.cdt - s.arrive_s, 0.0, 0.0))
                        s.cursor = self.cdt
                    return
                for s in waiting:
                    if tb > s.arrive_s:
                        segs.append((s.sid, 1, s.arrive_s, tb - s.arrive_s, 0.0, 0.0))
                    s.cursor = tb
                    s.state = "merge"
                    s.left_s = self.merge_stall[s.sid]
                    s.arrive_s = 0.0
                continue
            for s in waiting:
                if self.cdt - s.arrive_s > 1e-9:
                    segs.append((s.sid, 1, s.arrive_s, self.cdt - s.arrive_s, 0.0, 0.0))
                s.cursor = self.cdt
            if all(s.cursor >= self.cdt - 1e-9 or s.state in ("done", "queued") for s in active):
                return
        # safety: close out any shard that did not reach the end of the block
        for s in active:
            s.cursor = max(s.cursor, self.cdt)

    # -- rendering -------------------------------------------------------------------

    def _fractions(self, segs: list) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        rows = self.n_shards + 1
        K, dt = self.K, self.dt
        Fc = np.zeros((rows, K))
        Fm = np.zeros((rows, K))
        Fk = np.zeros((rows, K))
        if not segs:
            return Fc, Fm, Fk
        arr = np.array(segs, dtype=float)
        sid = arr[:, 0].astype(int)
        mode = arr[:, 1].astype(int)
        a = arr[:, 2][:, None]
        b = (arr[:, 2] + arr[:, 3])[:, None]
        x0 = arr[:, 4][:, None]
        rate = arr[:, 5][:, None]
        lo = np.arange(K)[None, :] * dt
        hi = lo + dt
        t0 = np.maximum(a, lo)
        t1 = np.minimum(b, hi)
        ov = np.clip(t1 - t0, 0.0, None)
        with np.errstate(divide="ignore", invalid="ignore"):
            xs = x0 + rate * (t0 - a)
            xe = x0 + rate * (t1 - a)
            comp_t = np.where(rate > 0, (_G(xe, self.cfg.compute_fraction_of_step) - _G(xs, self.cfg.compute_fraction_of_step)) / np.where(rate > 0, rate, 1.0), 0.0)
        comp_t = np.where(mode[:, None] == 0, np.minimum(np.maximum(comp_t, 0.0), ov), 0.0)
        comm_t = np.where(mode[:, None] == 0, ov - comp_t, 0.0) + np.where((mode == 1)[:, None], ov, 0.0)
        ckpt_t = np.where((mode == 2)[:, None], ov, 0.0)
        # restore/transfer segments (mode 3) draw idle power: they add nothing here
        np.add.at(Fc, sid, comp_t / dt)
        np.add.at(Fm, sid, comm_t / dt)
        np.add.at(Fk, sid, ckpt_t / dt)
        return Fc, Fm, Fk

    # -- main loop ---------------------------------------------------------------------------

    def run(self) -> "SimResult":
        cfg = self.cfg
        lv = cfg.levels
        th = cfg.thermal
        R, S, G, K = self.R, self.S, self.G, self.K
        ctrl_every = int(round(cfg.controller_interval_s / self.cdt))
        # Initial thermal state: steady state at idle plus host power, supply at setpoint.
        amb0 = self.outdoor_b[0]
        sp0 = th.supply_setpoint_c + th.outdoor_coupling_k_per_k * np.maximum(0.0, amb0[self.rack_site] - th.outdoor_reference_c)
        self.supply_now = sp0.copy()
        p0 = self.rack_n * (lv.idle_w + lv.host_w_per_gpu)
        self.rack_air_now = self.supply_now + self.Rres * p0
        self.rack_it_prev = p0.copy()
        self.rack_ratio_prev = p0 / self.rating
        self.site_power_prev = self.site_membership.T @ p0 + self.site_base
        self.theta = np.zeros(R)
        self.rack_it_b = np.zeros((self.Nb, R))
        self.site_power_b = np.zeros((self.Nb, S))
        throttled_prev = np.zeros(R, dtype=int)
        self.t_now = 0.0

        for b in range(self.Nb):
            t = b * self.cdt
            self.t_now = t
            sig = self.signals
            # 1. repairs, resets, discrete events
            repaired = (~self.gpu_alive) & (self.gpu_down_until <= t + 1e-9)
            if repaired.any():
                self.gpu_alive[repaired] = True
                self.admit_dirty = True
            reset = (~self.rack_on) & (self.rack_off_until <= t + 1e-9)
            if reset.any():
                self.rack_on[reset] = True
                self.theta[reset] = 0.0
                self.admit_dirty = True
                for r in np.flatnonzero(reset):
                    self._log(t, "rack_reset", rack_id=self.rack_ids[r])
            for blk, r, off_s in self._events_at(sig.forced_trips, b):
                if self.rack_on[r]:
                    self._trip_rack(r, t, off_s, "forced")
            for blk, r, slot, repair_s in self._events_at(sig.hardware_faults, b):
                g = int(self.rack_start[r] + slot)
                if self.gpu_alive[g]:
                    self.gpu_alive[g] = False
                    self.gpu_down_until[g] = t + repair_s
                    self._log(t, KIND_HARDWARE_FAULT, rack_id=self.rack_ids[r], gpu_slot=slot, repair_s=repair_s)
                    sid = self.gpu_shard[g]
                    if sid != self.n_shards:
                        self._fault_shard(self.shards[sid], t, f"gpu fault {self.rack_ids[r]}/{slot}")
            # GPU temperatures at the start of the step, and protective shutdown of overheated racks.
            amb_b = self.outdoor_b[b]
            gpu_temp = self.rack_air_now[self.gpu_rack] + self.k_gpu * self.gpu_mean_prev
            for r, slot, off in sig.gpu_temp_offsets(t):
                gpu_temp[self.rack_start[r] + slot] += off
            powered = self.gpu_alive & self.rack_on[self.gpu_rack]
            hottest = np.maximum.reduceat(np.where(powered, gpu_temp, -np.inf), self.rack_start)
            for r in np.flatnonzero(hottest >= th.gpu_shutdown_c):
                self._trip_rack(r, t, th.thermal_shutdown_hold_s, "gpu over shutdown temperature", KIND_THERMAL_SHUTDOWN)
            # 2. submissions becoming eligible, controller, admission
            if self.controller is not None and b % ctrl_every == 0:
                state = self._visible_state(t, b)
                self._apply_actions(self.controller.decide(t, state), t)
            if self.admit_dirty or t + 1e-9 >= self.next_eligible_s:
                self._admit(t)
            # 3. GPU clocks
            gpu_alive_on = self.gpu_alive & self.rack_on[self.gpu_rack]
            f_temp = cfg.throttle.clock_fraction(gpu_temp)
            n_alive = np.maximum(np.bincount(self.gpu_rack, weights=gpu_alive_on.astype(float), minlength=R), 1.0)
            host_w = lv.host_w_per_gpu * self.rack_n * self.rack_on
            per_gpu_cap = (self.rack_cap_w - host_w) / n_alive
            f_cap = np.where(
                np.isfinite(per_gpu_cap), cfg.throttle.clock_for_power(per_gpu_cap, lv.compute_w, lv.idle_w), 1.0
            )
            f_gpu = np.minimum(f_temp, f_cap[self.gpu_rack])
            speeds = np.ones(self.n_shards + 1)
            for sh in self.shards:
                if sh.gpus.size:
                    speeds[sh.sid] = float(f_gpu[sh.gpus].min())
            throttled_now = np.bincount(self.gpu_rack, weights=((f_temp < 1.0) & gpu_alive_on).astype(float), minlength=R).astype(int)
            for r in range(R):
                if throttled_now[r] > 0 and throttled_prev[r] == 0:
                    self._log(t, KIND_THERMAL_THROTTLE, rack_id=self.rack_ids[r], phase="start",
                              max_gpu_temp_c=float(gpu_temp[self.rack_start[r]:self.rack_start[r] + self.rack_n[r]].max()))
                elif throttled_now[r] == 0 and throttled_prev[r] > 0:
                    self._log(t, KIND_THERMAL_THROTTLE, rack_id=self.rack_ids[r], phase="end")
            throttled_prev = throttled_now
            # 4. advance jobs
            gpu_shard_start = self.gpu_shard.copy()
            segs: list = []
            for ji in range(len(self.jobs)):
                if any(s.state not in ("queued", "done") for s in self.job_shards[ji]):
                    self._advance_job(ji, speeds, segs)
            # 5. render power
            Fc, Fm, Fk = self._fractions(segs)
            Fi = np.clip(1.0 - Fc - Fm - Fk, 0.0, 1.0)
            alpha = cfg.throttle.power_exponent
            sc = speeds ** alpha
            Lc = lv.idle_w + (lv.compute_w - lv.idle_w) * sc
            Lm = lv.idle_w + (lv.comm_w - lv.idle_w) * sc
            Lk = lv.idle_w + (lv.checkpoint_w - lv.idle_w) * sc
            P_row = Fc * Lc[:, None] + Fm * Lm[:, None] + Fk * Lk[:, None] + Fi * lv.idle_w
            P_gpu = P_row[gpu_shard_start]
            if lv.noise_rel_sigma > 0:
                P_gpu = P_gpu + (lv.noise_rel_sigma * (Fc * Lc[:, None]))[gpu_shard_start] * self._noise(b)
            up = (self.gpu_alive & self.rack_on[self.gpu_rack]).astype(float)
            P_gpu = P_gpu * up[:, None]
            rack_gpu = np.add.reduceat(P_gpu, self.rack_start, axis=0)  # (R, K)
            self.rack_gpu_w[b * K:(b + 1) * K, :] = rack_gpu.T
            self.gpu_mean_prev = P_gpu.mean(axis=1)
            for wi, (wa, wb) in enumerate(self.windows):
                if wa - 1e-9 <= t < wb - 1e-9:
                    j = int(round((t - wa) / self.dt))
                    self.window_data[wi][:, j:j + K] = P_gpu
            host_b = lv.host_w_per_gpu * self.rack_n * self.rack_on
            rack_it_mean = rack_gpu.mean(axis=1) + host_b
            # 6. thermal, breaker, cooling
            cap_eff = self.cap_nominal * sig.capacity_factor[b] * self._capacity_derate(amb_b)[self.rack_site]
            res_eff = self.Rres * sig.resistance_multiplier[b]
            sp = th.supply_setpoint_c + th.outdoor_coupling_k_per_k * np.maximum(0.0, amb_b[self.rack_site] - th.outdoor_reference_c) + sig.supply_offset_k[b]
            lag = th.cooling_lag_s
            T1, Ts1, removed = rc_step(self.C, res_eff, lag, cap_eff, sp, self.rack_air_now, self.supply_now, rack_it_mean, self.cdt)
            q_mean = removed / self.cdt
            cool_w = cfg.cooling_power.power_w(np.maximum(q_mean, 0.0), amb_b[self.rack_site], 0.5 * (self.supply_now + Ts1))
            rating_eff = self.rating * sig.breaker_rating_factor[b]
            ratio = np.where(self.rack_on, rack_it_mean / rating_eff, 0.0)
            theta_next, tripped = cfg.breaker.step(self.theta, ratio, self.cdt)
            self.theta = np.where(self.rack_on, theta_next, 0.0)
            # record
            self.rack_host_b[b] = host_b
            self.rack_cool_b[b] = cool_w
            self.rack_air_b[b] = T1
            self.rack_supply_b[b] = Ts1
            gtemp_now = self.rack_air_now[self.gpu_rack] + self.k_gpu * self.gpu_mean_prev
            for r, slot, off in sig.gpu_temp_offsets(t + self.cdt):
                gtemp_now[self.rack_start[r] + slot] += off
            self.rack_maxgpu_b[b] = np.maximum.reduceat(np.where(up > 0, gtemp_now, -np.inf), self.rack_start)
            self.rack_throttled_b[b] = throttled_now / self.rack_n
            self.rack_ratio_b[b] = ratio
            self.rack_removed_b[b] = q_mean
            self.rack_cap_b[b] = cap_eff
            self.rack_on_b[b] = self.rack_on
            self.rack_it_b[b] = rack_it_mean
            free_mask_end = self._free_mask()
            self.site_free_b[b] = [int(free_mask_end[self.place.site_gpus[s]].sum()) for s in range(S)]
            self.rack_air_now = T1
            self.supply_now = Ts1
            self.rack_it_prev = rack_it_mean
            self.rack_ratio_prev = ratio
            site_p = self.site_membership.T @ (rack_it_mean + cool_w) + self.site_base
            self.site_power_prev = site_p
            self.site_power_b[b] = site_p
            # breaker opens at the end of this step if the thermal element reached its level
            end_t = t + self.cdt
            for r in np.flatnonzero(tripped & self.rack_on):
                self._trip_rack(r, end_t, th.breaker_reset_delay_s, "overload")
                self.rack_air_now[r] = T1[r]
        return self._finish()

    @staticmethod
    def _events_at(items: Sequence[Tuple], b: int) -> list:
        return [it for it in items if it[0] == b]

    # -- results -------------------------------------------------------------------------------

    def _finish(self) -> "SimResult":
        return SimResult(self)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


class SimResult:
    """Outputs of one run.  All quantities are simulated; see ``meta`` for provenance."""

    def __init__(self, run: _Run) -> None:
        self._run = run
        cfg = run.cfg
        K, Nb = run.K, run.Nb
        rack_cool_s = np.repeat(run.rack_cool_b, K, axis=0)
        rack_host_s = np.repeat(run.rack_host_b, K, axis=0)
        self.rack_it_power_w = run.rack_gpu_w + rack_host_s
        self.rack_gpu_power_w = run.rack_gpu_w
        self.rack_power_w = self.rack_it_power_w + rack_cool_s
        self.site_power_w = self.rack_power_w @ run.site_membership + run.site_base[None, :]
        self.rack_cooling_power_w = rack_cool_s
        self.rack_host_power_w = rack_host_s
        self.site_cap_violation = self._violation(self.site_power_w, run.site_cap[None, :])
        eff_import = run.site_import[None, :] * np.repeat(run.signals.import_limit_factor, K, axis=0)
        self.import_violation = self._violation(self.site_power_w, eff_import)
        self.gpu_windows = [
            {"start_s": a, "end_s": b, "gpu_power_w": run.window_data[i]} for i, (a, b) in enumerate(run.windows)
        ]
        per_min = int(round(60.0 / run.cdt)) if run.cdt <= 60.0 else 1
        self.minute_s = 60.0 if run.cdt <= 60.0 else run.cdt
        nm = Nb // per_min
        self.rack_temp_c_1min = run.rack_air_b[: nm * per_min].reshape(nm, per_min, run.R).mean(axis=1)
        self.rack_supply_c_1min = run.rack_supply_b[: nm * per_min].reshape(nm, per_min, run.R).mean(axis=1)
        self.rack_max_gpu_temp_c_1min = run.rack_maxgpu_b[: nm * per_min].reshape(nm, per_min, run.R).max(axis=1)
        H = int(round(cfg.horizon_s / 3600.0))
        per_h = int(round(3600.0 / self.dt))
        e = self.site_power_w.reshape(H, per_h, run.S).sum(axis=1) * self.dt / 3.6e6
        self.site_energy_kwh_1h = e
        self.site_mean_power_w_1h = e * 3.6e6 / 3600.0
        self.site_cost_usd_1h = e * run.price_h
        self.site_carbon_kg_1h = e * run.carbon_h / 1000.0
        self.jobs_table = self._job_table()
        self.events = list(run.event_log)
        self.actions = list(run.action_log)
        self.ground_truth_events = cfg.events.ground_truth()
        self.plan = plan_schedule(cfg)
        self.meta = self._meta()

    @property
    def dt(self) -> float:
        return self._run.dt

    def _violation(self, power: np.ndarray, limit: np.ndarray) -> dict[str, np.ndarray]:
        over = np.maximum(power - limit, 0.0)
        return {
            "seconds_above": (over > 0).sum(axis=0) * self.dt,
            "energy_above_kwh": over.sum(axis=0) * self.dt / 3.6e6,
            "max_excess_w": over.max(axis=0),
        }

    def _job_table(self) -> list[dict[str, Any]]:
        run = self._run
        rows = []
        for ji, job in enumerate(run.jobs):
            group = run.job_shards[ji]
            useful_gpu_h = sum(s.useful_steps * job.step_time_s * s.n_gpus / 3600.0 for s in group)
            lost_gpu_h = sum(s.lost_steps * job.step_time_s * s.n_gpus / 3600.0 for s in group)
            rows.append(
                {
                    "job_id": job.job_id, "n_gpus": int(job.n_gpus), "flexible": bool(job.flexible), "multisite": bool(job.multisite),
                    "status": run._job_status(group),
                    "useful_steps": float(sum(s.useful_steps for s in group)),
                    "total_steps": float(job.total_steps * len(group)),
                    "lost_steps": float(sum(s.lost_steps for s in group)),
                    "skipped_steps": float(sum(s.skipped_steps for s in group)),
                    "useful_gpu_hours": float(useful_gpu_h), "lost_gpu_hours": float(lost_gpu_h),
                    "value_usd": float(useful_gpu_h * job.value_per_gpu_hour),
                    "faults": int(sum(s.faults for s in group)), "restarts": int(sum(s.restarts for s in group)),
                    "migrations": int(sum(s.migrations for s in group)),
                }
            )
        return rows

    def _meta(self) -> dict[str, Any]:
        run = self._run
        cfg = run.cfg
        return {
            "schema": RESULT_SCHEMA,
            "data_kind": "simulated",
            "scenario_id": cfg.scenario_id,
            "start_utc": cfg.start_utc,
            "seed": run.seed,
            "horizon_s": cfg.horizon_s,
            "base_dt_s": run.dt,
            "control_dt_s": run.cdt,
            "site_ids": list(run.site_ids),
            "rack_ids": list(run.rack_ids),
            "rack_site_ids": list(run.rack_site_ids),
            "rack_gpu_counts": [int(n) for n in run.rack_n],
            "units": {
                "rack_gpu_power_w": "W, sum over the rack's GPUs, at base_dt_s",
                "rack_it_power_w": "W, GPU + host overhead, at base_dt_s",
                "rack_power_w": "W, IT + cooling share, at base_dt_s",
                "site_power_w": "W, sum of racks + Site.base_power_w, at base_dt_s",
                "rack_temp_c_1min": "deg C, mean rack air temperature per minute",
                "site_energy_kwh_1h": "kWh per hour", "site_cost_usd_1h": "USD per hour",
                "site_carbon_kg_1h": "kg CO2 per hour",
            },
            "quantity_provenance": {
                "gpu_power_levels": (
                    "simulated; levels set per power_levels.provenance (scenario calibration notes applied)"
                    if any(str(v).startswith(("public data:", "measured laptop data:")) for v in cfg.levels.provenance.values())
                    else "simulated; idle/compute and checkpoint/compute ratios derived from measured e002 laptop telemetry, scaled to cited H100 SXM TDP; other levels assumed"
                ),
                "thermal": "simulated; RC parameters are scenario assumptions (DGX H100 mass cited)",
                "cooling_power": "simulated; PUE baseline from the gpu_stack calculator assumption, Carnot COP shape",
                "events": "simulated; precursors are assumptions of the simulation, not measured facts",
                "environment": "simulated or caller-supplied series; see scenario",
                "jobs": "simulated synthetic schedule or caller-supplied schedule",
            },
            "power_levels": cfg.levels.to_dict(),
            "measured_e002": {k: cfg.measured_levels[k] for k in (
                "data_kind", "source_file", "source_sha256", "median_power_w_laptop", "ratio_to_compute", "sample_counts",
                "compute_relative_std", "median_window_duration_s", "telemetry_update_period_s")},
            "throttle": cfg.throttle.to_dict(),
            "cooling_power_model": cfg.cooling_power.to_dict(),
            "breaker": cfg.breaker.to_dict(),
            "assumptions": list(cfg.assumptions),
            "simplifications": list(SIMPLIFICATIONS),
        }

    # -- views -------------------------------------------------------------------------------

    def covariates(self, level: str, resolution_s: float, t0_s: float = 0.0, t1_s: Optional[float] = None) -> dict[str, np.ndarray]:
        """Known-future covariates aligned with an output grid (see :func:`planned_covariates`)."""
        return planned_covariates(self._run.cfg, self.plan, resolution_s, level, t0_s, t1_s)

    def to_arrays(self) -> dict[str, Any]:
        """Numpy arrays plus a ``meta`` dict (units, simulated vs measured-ratio-derived)."""
        run = self._run
        out: dict[str, Any] = {
            "rack_gpu_power_w": self.rack_gpu_power_w,
            "rack_it_power_w": self.rack_it_power_w,
            "rack_power_w": self.rack_power_w,
            "rack_cooling_power_w": self.rack_cooling_power_w,
            "site_power_w": self.site_power_w,
            "rack_temp_c_1min": self.rack_temp_c_1min,
            "rack_supply_c_1min": self.rack_supply_c_1min,
            "rack_max_gpu_temp_c_1min": self.rack_max_gpu_temp_c_1min,
            "site_energy_kwh_1h": self.site_energy_kwh_1h,
            "site_mean_power_w_1h": self.site_mean_power_w_1h,
            "site_cost_usd_1h": self.site_cost_usd_1h,
            "site_carbon_kg_1h": self.site_carbon_kg_1h,
            "site_cap_seconds_above": self.site_cap_violation["seconds_above"],
            "site_cap_energy_above_kwh": self.site_cap_violation["energy_above_kwh"],
            "site_import_seconds_above": self.import_violation["seconds_above"],
            "site_import_energy_above_kwh": self.import_violation["energy_above_kwh"],
            "outdoor_c_control_step": run.outdoor_b,
            "meta": self.meta,
        }
        for i, w in enumerate(self.gpu_windows):
            out[f"gpu_power_w_window_{i}"] = w["gpu_power_w"]
            out[f"gpu_power_w_window_{i}_bounds_s"] = np.array([w["start_s"], w["end_s"]])
        for name, level, res, t0, t1 in (
            ("rack_1min", "rack", 60.0, 0.0, None),
            ("site_1h", "site", 3600.0, 0.0, None),
        ):
            for k, v in self.covariates(level, res, t0, t1).items():
                out[f"cov_{name}_{k}"] = v
        for i, w in enumerate(self.gpu_windows):
            for level in ("rack", "site"):
                for k, v in self.covariates(level, self.dt, w["start_s"], w["end_s"]).items():
                    out[f"cov_{level}_window_{i}_{k}"] = v
        return out

    def summary(self) -> dict[str, Any]:
        """Scalar summary statistics (simulated)."""
        run = self._run
        rows = self.jobs_table
        n = len(rows)
        return {
            "data_kind": "simulated",
            "site_energy_kwh": [float(x) for x in self.site_energy_kwh_1h.sum(axis=0)],
            "site_mean_power_w": [float(x) for x in self.site_power_w.mean(axis=0)],
            "site_peak_power_w": [float(x) for x in self.site_power_w.max(axis=0)],
            "site_cost_usd": [float(x) for x in self.site_cost_usd_1h.sum(axis=0)],
            "site_carbon_kg": [float(x) for x in self.site_carbon_kg_1h.sum(axis=0)],
            "site_cap_seconds_above": [float(x) for x in self.site_cap_violation["seconds_above"]],
            "site_cap_energy_above_kwh": [float(x) for x in self.site_cap_violation["energy_above_kwh"]],
            "site_import_seconds_above": [float(x) for x in self.import_violation["seconds_above"]],
            "site_import_energy_above_kwh": [float(x) for x in self.import_violation["energy_above_kwh"]],
            "jobs": n,
            "jobs_done": sum(r["status"] == "done" for r in rows),
            "useful_gpu_hours": float(sum(r["useful_gpu_hours"] for r in rows)),
            "lost_gpu_hours": float(sum(r["lost_gpu_hours"] for r in rows)),
            "lost_steps": float(sum(r["lost_steps"] for r in rows)),
            "skipped_steps": float(sum(r["skipped_steps"] for r in rows)),
            "value_usd": float(sum(r["value_usd"] for r in rows)),
            "job_faults": int(sum(r["faults"] for r in rows)),
            "migrations": int(sum(r["migrations"] for r in rows)),
            "max_rack_air_c": float(run.rack_air_b.max()),
            "max_gpu_temp_c": float(run.rack_maxgpu_b.max()),
            "throttle_episodes": sum(1 for e in self.events if e["kind"] == KIND_THERMAL_THROTTLE and e.get("phase") == "start"),
            "breaker_trips": sum(1 for e in self.events if e["kind"] == KIND_BREAKER_TRIP),
            "thermal_shutdowns": sum(1 for e in self.events if e["kind"] == KIND_THERMAL_SHUTDOWN),
            "hardware_faults": sum(1 for e in self.events if e["kind"] == KIND_HARDWARE_FAULT),
        }


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def load_scenario(path: Union[str, Path]) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def run_scenario(
    scenario: Mapping[str, Any],
    controller: Optional[Controller] = None,
    seed: int = 0,
    environment: Optional[Mapping[str, SiteEnvironment]] = None,
    jobs: Optional[Sequence[Job]] = None,
) -> SimResult:
    """Run a scenario dict.  Deterministic for a given ``seed``.

    ``environment`` replaces the scenario's outdoor temperature, price and
    carbon series (site id to :class:`SiteEnvironment`).  ``jobs`` replaces the
    scenario's job schedule (for example a schedule read from a real trace).
    """
    cfg = build_config(scenario, seed=seed, environment=environment)
    if jobs is not None:
        cfg = replace(cfg, jobs=tuple(jobs))
    return _Run(cfg, controller, seed).run()


__all__ = [
    "AdmitJob", "CheckpointNow", "Controller", "DeferJob", "Job", "JobView", "MigrateJob", "NullController",
    "PauseJob", "PlannedJob", "PowerLevels", "RackSpec", "ReactiveSiteCapController", "ResumeJob", "SetRackPowerCap",
    "SimConfig", "SimResult", "SiteEnvironment", "SiteLayout", "ThermalAssumptions", "TransferParams", "VisibleState",
    "build_config", "generate_jobs", "load_scenario", "measure_e002_levels", "plan_schedule", "planned_covariates",
    "run_scenario", "synthetic_environment",
]
