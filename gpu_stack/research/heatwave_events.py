"""Fault and grid events for the Heatwave cluster simulator (all simulated).

IMPORTANT: every event in this module is a simulation input.  Precursors are
assumptions of the simulation, not measured facts.  When a scenario says a
cooling failure is preceded by a slow rise in supply temperature, or that a
curtailment is announced 30 minutes ahead, that is a modeling choice made so
that later experiments can ask what a forecaster could and could not catch.
Nothing here claims real facilities behave this way, and the strengths and
lead times carry no empirical calibration.

Event types
-----------
``thermal_throttle``
    Emergent.  It is never scheduled: it appears in the simulator's event log
    when a GPU temperature crosses the throttle threshold of the thermal model
    (:class:`gpu_stack.research.heatwave_thermal.GPUThrottleModel`).
``cooling_failure``
    Cooling capacity of one rack or a whole site drops to a fraction for a
    window.  Optional resistance multiplier models a failing fan.  Optional
    precursors: a slow rise of the supply temperature and/or a rise of the
    thermal resistance, each ramping linearly from zero at ``onset - lead`` to
    the stated strength at onset.
``breaker_trip``
    A rack breaker with an inverse-time thermal characteristic.  Mode
    ``derate`` lowers the breaker rating to a fraction for a window; the trip
    itself is emergent and happens when the rack load stays above the rating
    long enough (see :class:`InverseTimeBreaker`).  The rating ramps down over
    the precursor lead time, which makes the rack load ratio rise visibly before
    the rating reaches its final value.  Mode ``forced`` trips the rack at onset
    (a nuisance trip) with no precursor.
``grid_curtailment``
    A site's import limit drops to a fraction for a window.  It may be
    announced ahead of time (it then appears in the known-future schedule from
    ``onset - announce_lead_s``) or not announced.
``hardware_fault``
    One GPU stops at onset and stays down for ``repair_s``.  Optional
    precursor: the GPU's temperature creeps up by a stated number of kelvin
    over the lead time before onset.

Events with no precursor exist in every type except the emergent throttle, so
experiments can separate what telemetry can foreshadow from what it cannot.
:meth:`EventSchedule.ground_truth` lists, for each event, whether it has a
precursor, which telemetry channel carries it, its lead time and strength.
Controllers and forecasters never see that table.

Breaker curve
-------------
:class:`InverseTimeBreaker` is a first-order thermal element.  Its state
``theta`` follows ``d theta / dt = (r**2 - theta) / tau`` with ``r`` the load
divided by the breaker rating, and the breaker opens when ``theta`` reaches
``nontrip_ratio ** 2``.  The defaults are the IEC 60898-1 conventional values
(non-tripping current 1.13 x In, tripping current 1.45 x In, conventional time
1 hour; source: https://www.se.com/au/en/faqs/FA369327/).  ``tau`` is
derived so that a constant 1.45 x In opens the breaker after exactly the
conventional time.  This models only the thermal region; the instantaneous
magnetic region is not represented, and IEC 60898-1 covers small
installation breakers, so the numbers are a parameterized stand-in for a rack
feed breaker, not a specification of one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Tuple

import numpy as np

KIND_THERMAL_THROTTLE = "thermal_throttle"
KIND_COOLING_FAILURE = "cooling_failure"
KIND_BREAKER_TRIP = "breaker_trip"
KIND_GRID_CURTAILMENT = "grid_curtailment"
KIND_HARDWARE_FAULT = "hardware_fault"
EVENT_KINDS = (
    KIND_THERMAL_THROTTLE,
    KIND_COOLING_FAILURE,
    KIND_BREAKER_TRIP,
    KIND_GRID_CURTAILMENT,
    KIND_HARDWARE_FAULT,
)

CHANNEL_SUPPLY_TEMP = "supply_temp_c"
CHANNEL_THERMAL_RESISTANCE = "thermal_resistance"
CHANNEL_GPU_TEMP = "gpu_temp_c"
CHANNEL_BREAKER_LOAD_RATIO = "breaker_load_ratio"
CHANNEL_ANNOUNCEMENT = "known_future_schedule"


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


@dataclass(frozen=True)
class Precursor:
    """A ramp on one telemetry channel that ends at the event onset.

    ``strength`` is in the unit of the channel: kelvin for ``supply_temp_c``
    and ``gpu_temp_c``; a fractional rise (0.2 means +20 percent) for
    ``thermal_resistance``.  Simulation assumption, not a measurement.
    """

    channel: str
    lead_s: float
    strength: float

    def __post_init__(self) -> None:
        if self.channel not in (CHANNEL_SUPPLY_TEMP, CHANNEL_THERMAL_RESISTANCE, CHANNEL_GPU_TEMP):
            raise ValueError(f"unsupported precursor channel {self.channel!r}")
        _num(self.lead_s, "lead_s", strict=True)
        _num(self.strength, "strength", strict=True)

    def value(self, t_s: Any, onset_s: float) -> np.ndarray:
        """Ramp value at time(s) ``t_s``: 0 before onset - lead, strength at onset."""
        t = np.asarray(t_s, dtype=float)
        frac = np.clip((t - (onset_s - self.lead_s)) / self.lead_s, 0.0, 1.0)
        return self.strength * frac

    def to_dict(self) -> dict[str, Any]:
        return {"channel": self.channel, "lead_s": self.lead_s, "strength": self.strength}


def _precursors(items: Any) -> Tuple[Precursor, ...]:
    out = []
    for item in items or ():
        out.append(item if isinstance(item, Precursor) else Precursor(**item))
    return tuple(out)


@dataclass(frozen=True)
class CoolingFailure:
    event_id: str
    site_id: str
    onset_s: float
    duration_s: float
    remaining_capacity_fraction: float
    rack_id: Optional[str] = None
    resistance_multiplier: float = 1.0
    precursors: Tuple[Precursor, ...] = ()
    kind: str = field(default=KIND_COOLING_FAILURE, init=False)

    def __post_init__(self) -> None:
        _nonempty(self.event_id, "event_id")
        _nonempty(self.site_id, "site_id")
        _num(self.onset_s, "onset_s")
        _num(self.duration_s, "duration_s", strict=True)
        _num(self.remaining_capacity_fraction, "remaining_capacity_fraction", maximum=1.0)
        _num(self.resistance_multiplier, "resistance_multiplier", minimum=1.0)
        object.__setattr__(self, "precursors", _precursors(self.precursors))
        for p in self.precursors:
            if p.channel == CHANNEL_GPU_TEMP:
                raise ValueError("cooling_failure precursors use supply_temp_c or thermal_resistance")

    @property
    def end_s(self) -> float:
        return self.onset_s + self.duration_s

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "event_id": self.event_id, "site_id": self.site_id, "rack_id": self.rack_id,
            "onset_s": self.onset_s, "duration_s": self.duration_s,
            "remaining_capacity_fraction": self.remaining_capacity_fraction,
            "resistance_multiplier": self.resistance_multiplier,
            "precursors": [p.to_dict() for p in self.precursors],
        }


@dataclass(frozen=True)
class BreakerTrip:
    """Mode ``derate``: rating factor ramps to ``derate_fraction`` by onset and
    holds for ``duration_s``.  Mode ``forced``: the rack opens at onset and stays
    off for ``duration_s`` (no precursor)."""

    event_id: str
    site_id: str
    rack_id: str
    onset_s: float
    duration_s: float
    mode: str = "derate"
    derate_fraction: float = 1.0
    precursor_lead_s: float = 0.0
    kind: str = field(default=KIND_BREAKER_TRIP, init=False)

    def __post_init__(self) -> None:
        _nonempty(self.event_id, "event_id")
        _nonempty(self.site_id, "site_id")
        _nonempty(self.rack_id, "rack_id")
        _num(self.onset_s, "onset_s")
        _num(self.duration_s, "duration_s", strict=True)
        if self.mode not in ("derate", "forced"):
            raise ValueError("mode must be 'derate' or 'forced'")
        _num(self.precursor_lead_s, "precursor_lead_s")
        if self.mode == "derate":
            _num(self.derate_fraction, "derate_fraction", strict=True, maximum=1.0)
        elif self.precursor_lead_s != 0.0:
            raise ValueError("forced breaker trips have no precursor")

    @property
    def end_s(self) -> float:
        return self.onset_s + self.duration_s

    def rating_factor(self, t_s: Any) -> np.ndarray:
        """Breaker rating factor at time(s) ``t_s`` (derate mode)."""
        t = np.asarray(t_s, dtype=float)
        if self.precursor_lead_s > 0.0:
            frac = np.clip((t - (self.onset_s - self.precursor_lead_s)) / self.precursor_lead_s, 0.0, 1.0)
        else:
            frac = (t >= self.onset_s).astype(float)
        factor = 1.0 - (1.0 - self.derate_fraction) * frac
        return np.where(t < self.end_s, factor, 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "event_id": self.event_id, "site_id": self.site_id, "rack_id": self.rack_id,
            "onset_s": self.onset_s, "duration_s": self.duration_s, "mode": self.mode,
            "derate_fraction": self.derate_fraction, "precursor_lead_s": self.precursor_lead_s,
        }


@dataclass(frozen=True)
class GridCurtailment:
    event_id: str
    site_id: str
    onset_s: float
    duration_s: float
    limit_fraction: float
    announce_lead_s: Optional[float] = None
    kind: str = field(default=KIND_GRID_CURTAILMENT, init=False)

    def __post_init__(self) -> None:
        _nonempty(self.event_id, "event_id")
        _nonempty(self.site_id, "site_id")
        _num(self.onset_s, "onset_s")
        _num(self.duration_s, "duration_s", strict=True)
        _num(self.limit_fraction, "limit_fraction", maximum=1.0)
        if self.announce_lead_s is not None:
            _num(self.announce_lead_s, "announce_lead_s", strict=True)

    @property
    def end_s(self) -> float:
        return self.onset_s + self.duration_s

    @property
    def announced_at_s(self) -> Optional[float]:
        return None if self.announce_lead_s is None else self.onset_s - self.announce_lead_s

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "event_id": self.event_id, "site_id": self.site_id,
            "onset_s": self.onset_s, "duration_s": self.duration_s,
            "limit_fraction": self.limit_fraction, "announce_lead_s": self.announce_lead_s,
        }


@dataclass(frozen=True)
class HardwareFault:
    event_id: str
    site_id: str
    rack_id: str
    gpu_slot: int
    onset_s: float
    repair_s: float
    precursors: Tuple[Precursor, ...] = ()
    kind: str = field(default=KIND_HARDWARE_FAULT, init=False)

    def __post_init__(self) -> None:
        _nonempty(self.event_id, "event_id")
        _nonempty(self.site_id, "site_id")
        _nonempty(self.rack_id, "rack_id")
        if isinstance(self.gpu_slot, bool) or not isinstance(self.gpu_slot, (int, np.integer)) or self.gpu_slot < 0:
            raise ValueError("gpu_slot must be an integer >= 0")
        _num(self.onset_s, "onset_s")
        _num(self.repair_s, "repair_s", strict=True)
        object.__setattr__(self, "precursors", _precursors(self.precursors))
        for p in self.precursors:
            if p.channel != CHANNEL_GPU_TEMP:
                raise ValueError("hardware_fault precursors use the gpu_temp_c channel")

    @property
    def end_s(self) -> float:
        return self.onset_s + self.repair_s

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "event_id": self.event_id, "site_id": self.site_id, "rack_id": self.rack_id,
            "gpu_slot": int(self.gpu_slot), "onset_s": self.onset_s, "repair_s": self.repair_s,
            "precursors": [p.to_dict() for p in self.precursors],
        }


Event = Any  # CoolingFailure | BreakerTrip | GridCurtailment | HardwareFault


@dataclass(frozen=True)
class InverseTimeBreaker:
    """Inverse-time thermal breaker; see the module docstring for the source."""

    nontrip_ratio: float = 1.13
    trip_ratio: float = 1.45
    conventional_time_s: float = 3600.0

    def __post_init__(self) -> None:
        _num(self.nontrip_ratio, "nontrip_ratio", minimum=1.0, strict=True)
        _num(self.trip_ratio, "trip_ratio", minimum=1.0, strict=True)
        _num(self.conventional_time_s, "conventional_time_s", strict=True)
        if not self.trip_ratio > self.nontrip_ratio:
            raise ValueError("trip_ratio must exceed nontrip_ratio")

    @property
    def trip_level(self) -> float:
        """Value of ``theta`` at which the breaker opens."""
        return self.nontrip_ratio**2

    @property
    def time_constant_s(self) -> float:
        r2 = self.trip_ratio**2
        return self.conventional_time_s / -math.log(1.0 - self.trip_level / r2)

    def trip_time_s(self, ratio: float) -> float:
        """Time to open from a cold start at constant ``ratio`` (inf if never)."""
        r2 = float(ratio) ** 2
        if r2 <= self.trip_level:
            return math.inf
        return -self.time_constant_s * math.log(1.0 - self.trip_level / r2)

    def step(self, theta: Any, ratio: Any, dt_s: float) -> Tuple[np.ndarray, np.ndarray]:
        """Advance ``theta`` by ``dt_s`` under a constant load ratio.

        Returns ``(theta_next, tripped)``.  Exact for constant ratio.
        """
        r2 = np.asarray(ratio, dtype=float) ** 2
        th = np.asarray(theta, dtype=float)
        nxt = r2 + (th - r2) * math.exp(-dt_s / self.time_constant_s)
        return nxt, nxt >= self.trip_level

    def to_dict(self) -> dict[str, float]:
        return {
            "nontrip_ratio": self.nontrip_ratio,
            "trip_ratio": self.trip_ratio,
            "conventional_time_s": self.conventional_time_s,
            "time_constant_s": self.time_constant_s,
        }


@dataclass(frozen=True)
class EventSignals:
    """Per-block signals resolved from a schedule (values at block start)."""

    block_start_s: np.ndarray            # (N,)
    capacity_factor: np.ndarray          # (N, R) multiplies rack cooling capacity
    resistance_multiplier: np.ndarray    # (N, R) multiplies thermal resistance
    supply_offset_k: np.ndarray          # (N, R) added to the supply setpoint (precursor)
    breaker_rating_factor: np.ndarray    # (N, R)
    import_limit_factor: np.ndarray      # (N, S)
    forced_trips: Tuple[Tuple[int, int, float], ...]        # (block, rack, off_s)
    hardware_faults: Tuple[Tuple[int, int, int, float], ...]  # (block, rack, slot, repair_s)
    gpu_temp_precursors: Tuple[Tuple[int, int, float, Precursor, float], ...]  # (rack, slot, onset, precursor, end)

    def gpu_temp_offsets(self, t_s: float) -> list[Tuple[int, int, float]]:
        """``(rack, slot, offset_k)`` for GPUs with an active temperature precursor at ``t_s``."""
        out = []
        for rack, slot, onset, pre, end in self.gpu_temp_precursors:
            if onset - pre.lead_s <= t_s < end:
                out.append((rack, slot, float(pre.value(min(t_s, onset), onset))))
        return out


@dataclass(frozen=True)
class EventSchedule:
    events: Tuple[Event, ...] = ()

    def __post_init__(self) -> None:
        ids = [e.event_id for e in self.events]
        if len(set(ids)) != len(ids):
            raise ValueError("event ids must be unique")
        object.__setattr__(self, "events", tuple(sorted(self.events, key=lambda e: (e.onset_s, e.event_id))))

    def to_dict(self) -> dict[str, Any]:
        return {"data_kind": "simulated", "events": [e.to_dict() for e in self.events]}

    @classmethod
    def from_dicts(cls, items: Sequence[Mapping[str, Any]]) -> "EventSchedule":
        events = []
        for raw in items:
            item = dict(raw)
            kind = item.pop("kind", None)
            if "precursors" in item:
                item["precursors"] = _precursors(item["precursors"])
            if kind == KIND_COOLING_FAILURE:
                events.append(CoolingFailure(**item))
            elif kind == KIND_BREAKER_TRIP:
                events.append(BreakerTrip(**item))
            elif kind == KIND_GRID_CURTAILMENT:
                events.append(GridCurtailment(**item))
            elif kind == KIND_HARDWARE_FAULT:
                events.append(HardwareFault(**item))
            else:
                raise ValueError(f"unknown or non-schedulable event kind {kind!r}")
        return cls(tuple(events))

    def of_kind(self, kind: str) -> Tuple[Event, ...]:
        return tuple(e for e in self.events if e.kind == kind)

    # -- known-future schedule ------------------------------------------------

    def announced_curtailments(self, t_s: float) -> list[dict[str, Any]]:
        """Curtailments visible at time ``t_s``: announced and not yet over."""
        out = []
        for e in self.of_kind(KIND_GRID_CURTAILMENT):
            at = e.announced_at_s
            if at is not None and at <= t_s < e.end_s:
                out.append(
                    {"event_id": e.event_id, "site_id": e.site_id, "onset_s": e.onset_s,
                     "end_s": e.end_s, "limit_fraction": e.limit_fraction, "announced_at_s": at}
                )
        return out

    # -- ground truth (never shown to controllers) ---------------------------

    def ground_truth(self) -> list[dict[str, Any]]:
        rows = []
        for e in self.events:
            row: dict[str, Any] = {
                "event_id": e.event_id, "kind": e.kind, "site_id": e.site_id,
                "rack_id": getattr(e, "rack_id", None), "onset_s": e.onset_s, "end_s": e.end_s,
                "has_precursor": False, "precursor_channels": [], "precursor_lead_s": 0.0,
                "precursor_strength": {}, "announced_at_s": None, "data_kind": "simulated",
            }
            if e.kind in (KIND_COOLING_FAILURE, KIND_HARDWARE_FAULT):
                row["has_precursor"] = bool(e.precursors)
                row["precursor_channels"] = [p.channel for p in e.precursors]
                row["precursor_lead_s"] = max((p.lead_s for p in e.precursors), default=0.0)
                row["precursor_strength"] = {p.channel: p.strength for p in e.precursors}
            elif e.kind == KIND_BREAKER_TRIP:
                has = e.mode == "derate" and e.precursor_lead_s > 0.0
                row["has_precursor"] = has
                row["precursor_channels"] = [CHANNEL_BREAKER_LOAD_RATIO] if has else []
                row["precursor_lead_s"] = e.precursor_lead_s if has else 0.0
                row["precursor_strength"] = {CHANNEL_BREAKER_LOAD_RATIO: 1.0 - e.derate_fraction} if has else {}
                row["mode"] = e.mode
            elif e.kind == KIND_GRID_CURTAILMENT:
                has = e.announce_lead_s is not None
                row["has_precursor"] = has
                row["precursor_channels"] = [CHANNEL_ANNOUNCEMENT] if has else []
                row["precursor_lead_s"] = float(e.announce_lead_s) if has else 0.0
                row["announced_at_s"] = e.announced_at_s
            rows.append(row)
        return rows

    # -- resolution onto the simulator's block grid ----------------------------

    def resolve(
        self,
        block_start_s: np.ndarray,
        block_dt_s: float,
        site_ids: Sequence[str],
        rack_ids: Sequence[str],
        rack_site_ids: Sequence[str],
        rack_gpu_counts: Sequence[int],
    ) -> EventSignals:
        t = np.asarray(block_start_s, dtype=float)
        n, nr, ns = t.shape[0], len(rack_ids), len(site_ids)
        rack_index = {r: i for i, r in enumerate(rack_ids)}
        site_index = {s: i for i, s in enumerate(site_ids)}
        if len(rack_index) != nr or len(site_index) != ns:
            raise ValueError("site and rack ids must be unique")
        cap = np.ones((n, nr))
        res = np.ones((n, nr))
        sup = np.zeros((n, nr))
        brk = np.ones((n, nr))
        imp = np.ones((n, ns))
        forced = []
        faults = []
        gpu_pre = []

        def racks_of(site_id: str, rack_id: Optional[str]) -> list[int]:
            if site_id not in site_index:
                raise ValueError(f"unknown site {site_id!r}")
            if rack_id is None:
                return [i for i, s in enumerate(rack_site_ids) if s == site_id]
            if rack_id not in rack_index or rack_site_ids[rack_index[rack_id]] != site_id:
                raise ValueError(f"unknown rack {rack_id!r} for site {site_id!r}")
            return [rack_index[rack_id]]

        def block_of(time_s: float) -> int:
            return int(math.ceil(time_s / block_dt_s - 1e-9))

        for e in self.events:
            if e.kind == KIND_COOLING_FAILURE:
                active = (t >= e.onset_s) & (t < e.end_s)
                for r in racks_of(e.site_id, e.rack_id):
                    cap[active, r] = np.minimum(cap[active, r], e.remaining_capacity_fraction)
                    res[active, r] = np.maximum(res[active, r], e.resistance_multiplier)
                    for p in e.precursors:
                        window = (t >= e.onset_s - p.lead_s) & (t < e.end_s)
                        ramp = p.value(np.minimum(t, e.onset_s), e.onset_s)
                        if p.channel == CHANNEL_SUPPLY_TEMP:
                            sup[window, r] = np.maximum(sup[window, r], ramp[window])
                        else:
                            res[window, r] = np.maximum(res[window, r], 1.0 + ramp[window])
            elif e.kind == KIND_BREAKER_TRIP:
                (r,) = racks_of(e.site_id, e.rack_id)
                if e.mode == "derate":
                    brk[:, r] = np.minimum(brk[:, r], e.rating_factor(t))
                else:
                    b = block_of(e.onset_s)
                    if b < n:
                        forced.append((b, r, e.duration_s))
            elif e.kind == KIND_GRID_CURTAILMENT:
                active = (t >= e.onset_s) & (t < e.end_s)
                s = site_index[e.site_id] if e.site_id in site_index else None
                if s is None:
                    raise ValueError(f"unknown site {e.site_id!r}")
                imp[active, s] = np.minimum(imp[active, s], e.limit_fraction)
            elif e.kind == KIND_HARDWARE_FAULT:
                (r,) = racks_of(e.site_id, e.rack_id)
                if e.gpu_slot >= rack_gpu_counts[r]:
                    raise ValueError(f"gpu_slot {e.gpu_slot} outside rack {e.rack_id!r}")
                b = block_of(e.onset_s)
                if b < n:
                    faults.append((b, r, int(e.gpu_slot), e.repair_s))
                for p in e.precursors:
                    gpu_pre.append((r, int(e.gpu_slot), e.onset_s, p, e.end_s))
        forced.sort()
        faults.sort()
        return EventSignals(
            block_start_s=t, capacity_factor=cap, resistance_multiplier=res, supply_offset_k=sup,
            breaker_rating_factor=brk, import_limit_factor=imp, forced_trips=tuple(forced),
            hardware_faults=tuple(faults), gpu_temp_precursors=tuple(gpu_pre),
        )


def random_schedule(
    seed: int,
    horizon_s: float,
    site_racks: Mapping[str, Sequence[Tuple[str, int]]],
    rates_per_day: Mapping[str, float],
    precursor_probability: float,
    lead_range_s: Tuple[float, float],
    strength_ranges: Mapping[str, Tuple[float, float]],
    duration_range_s: Tuple[float, float],
    remaining_capacity_range: Tuple[float, float],
    derate_range: Tuple[float, float],
    limit_fraction_range: Tuple[float, float],
    repair_range_s: Tuple[float, float],
) -> EventSchedule:
    """Seeded random schedule for experiments that need many events.

    ``site_racks`` maps a site id to ``[(rack_id, gpu_count), ...]``.
    ``rates_per_day`` has keys ``cooling_failure``, ``breaker_trip``,
    ``grid_curtailment``, ``hardware_fault`` (events per site per day).  Each
    event gets a precursor with probability ``precursor_probability``.
    ``strength_ranges`` has keys ``supply_temp_c`` (K), ``gpu_temp_c`` (K).
    Every number is a caller-supplied simulation assumption.
    """
    rng = np.random.default_rng(seed)
    events: list[Event] = []
    counter = 0
    for site_id in sorted(site_racks):
        racks = list(site_racks[site_id])
        for kind in (KIND_COOLING_FAILURE, KIND_BREAKER_TRIP, KIND_GRID_CURTAILMENT, KIND_HARDWARE_FAULT):
            count = int(rng.poisson(float(rates_per_day.get(kind, 0.0)) * horizon_s / 86_400.0))
            for _ in range(count):
                counter += 1
                eid = f"rnd-{counter:04d}-{kind}"
                onset = float(rng.uniform(0.0, horizon_s))
                dur = float(rng.uniform(*duration_range_s))
                has_pre = bool(rng.random() < precursor_probability)
                lead = float(rng.uniform(*lead_range_s))
                rack_id, n_gpu = racks[int(rng.integers(len(racks)))]
                if kind == KIND_COOLING_FAILURE:
                    pre = ()
                    if has_pre:
                        pre = (Precursor(CHANNEL_SUPPLY_TEMP, lead, float(rng.uniform(*strength_ranges["supply_temp_c"]))),)
                    scope_rack = rack_id if rng.random() < 0.5 else None
                    events.append(CoolingFailure(eid, site_id, onset, dur, float(rng.uniform(*remaining_capacity_range)),
                                                 rack_id=scope_rack, precursors=pre))
                elif kind == KIND_BREAKER_TRIP:
                    if rng.random() < 0.5:
                        events.append(BreakerTrip(eid, site_id, rack_id, onset, dur, "forced"))
                    else:
                        events.append(BreakerTrip(eid, site_id, rack_id, onset, dur, "derate",
                                                  float(rng.uniform(*derate_range)), lead if has_pre else 0.0))
                elif kind == KIND_GRID_CURTAILMENT:
                    events.append(GridCurtailment(eid, site_id, onset, dur, float(rng.uniform(*limit_fraction_range)),
                                                  lead if has_pre else None))
                else:
                    pre = ()
                    if has_pre:
                        pre = (Precursor(CHANNEL_GPU_TEMP, lead, float(rng.uniform(*strength_ranges["gpu_temp_c"]))),)
                    events.append(HardwareFault(eid, site_id, rack_id, int(rng.integers(n_gpu)), onset,
                                                float(rng.uniform(*repair_range_s)), precursors=pre))
    return EventSchedule(tuple(events))


__all__ = [
    "BreakerTrip",
    "CoolingFailure",
    "EVENT_KINDS",
    "Event",
    "EventSchedule",
    "EventSignals",
    "GridCurtailment",
    "HardwareFault",
    "InverseTimeBreaker",
    "Precursor",
    "random_schedule",
]
