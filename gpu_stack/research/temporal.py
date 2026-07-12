"""Deterministic temporal substrate for GPUSTACK research simulations.

The symbolic graph describes relationships at a point in a scenario.  This
module adds the deliberately smaller concept needed by the research program:
explicit events competing for finite resources over integer nanosecond time.

It is a scheduler, not a convergence model.  Callers provide every duration,
rate, capacity, and demand.  The timeline only answers when those events can
run, what they contend with, and which state was visible at each transition.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from enum import Enum
from numbers import Real
from typing import Iterable, Mapping, Optional, Sequence, Tuple, Union


Number = Union[int, float]
JsonScalar = Union[None, bool, int, float, str]
Metadata = Tuple[Tuple[str, JsonScalar], ...]


def _require_nonempty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_integer(value: int, field_name: str, *, minimum: int = 0) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field_name} must be an integer >= {minimum}")


def _require_finite_number(
    value: Number,
    field_name: str,
    *,
    minimum: Optional[float] = None,
    strict_minimum: bool = False,
) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field_name} must be a finite real number")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field_name} must be a finite real number")
    if minimum is not None:
        if strict_minimum and not float(value) > minimum:
            raise ValueError(f"{field_name} must be > {minimum}")
        if not strict_minimum and float(value) < minimum:
            raise ValueError(f"{field_name} must be >= {minimum}")


def freeze_metadata(
    values: Optional[Mapping[str, JsonScalar]] = None,
) -> Metadata:
    """Return validated, key-sorted, immutable event metadata.

    Metadata intentionally contains scalars only.  Research artifacts should
    reference large or structured payloads by stable identifier rather than
    hiding mutable simulator state inside an event.
    """

    if values is None:
        return ()
    if not isinstance(values, Mapping):
        raise TypeError("metadata must be a mapping")
    frozen = []
    for key, value in values.items():
        _require_nonempty(key, "metadata key")
        if not isinstance(value, (type(None), bool, int, float, str)):
            raise TypeError(
                f"metadata[{key!r}] must be a JSON scalar, got "
                f"{type(value).__name__}"
            )
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"metadata[{key!r}] must be finite")
        frozen.append((key, value))
    return tuple(sorted(frozen, key=lambda item: item[0]))


def canonical_json(value: object) -> str:
    """Serialize an artifact with deterministic ordering and no NaN values."""

    to_dict = getattr(value, "to_dict", None)
    payload = to_dict() if callable(to_dict) else value
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def seconds_to_ns(seconds: Number) -> int:
    """Convert non-negative seconds to nanoseconds, rounding upward.

    Decimal conversion through ``str`` makes the result independent of binary
    floating-point representation.  Rounding upward prevents non-zero work
    from becoming a zero-duration event.
    """

    _require_finite_number(seconds, "seconds", minimum=0.0)
    nanoseconds = Decimal(str(seconds)) * Decimal(1_000_000_000)
    return int(nanoseconds.to_integral_value(rounding=ROUND_CEILING))


def duration_ns_for_rate(
    amount: Number,
    rate_per_second: Number,
    *,
    latency_ns: int = 0,
) -> int:
    """Return ``ceil(amount / rate * 1e9) + latency_ns`` deterministically."""

    _require_finite_number(amount, "amount", minimum=0.0)
    _require_finite_number(
        rate_per_second,
        "rate_per_second",
        minimum=0.0,
        strict_minimum=True,
    )
    _require_integer(latency_ns, "latency_ns")
    if float(amount) == 0.0:
        return latency_ns
    work_ns = (
        Decimal(str(amount))
        / Decimal(str(rate_per_second))
        * Decimal(1_000_000_000)
    )
    return int(work_ns.to_integral_value(rounding=ROUND_CEILING)) + latency_ns


class EventKind(str, Enum):
    """Typed temporal mechanisms represented by the virtual datacenter."""

    COMPUTE = "compute"
    COLLECTIVE = "collective"
    STATE_TRANSFER = "state_transfer"
    CHECKPOINT = "checkpoint"
    FAILURE = "failure"
    RECOVERY = "recovery"
    POWER = "power"
    COOLING = "cooling"
    GRID = "grid"


@dataclass(frozen=True)
class Resource:
    """A finite, shareable timeline resource."""

    resource_id: str
    capacity: Number
    unit: str

    def __post_init__(self) -> None:
        _require_nonempty(self.resource_id, "resource_id")
        _require_finite_number(self.capacity, "capacity", minimum=0.0)
        _require_nonempty(self.unit, "unit")

    def to_dict(self) -> dict[str, object]:
        return {
            "resource_id": self.resource_id,
            "capacity": self.capacity,
            "unit": self.unit,
        }


@dataclass(frozen=True)
class ResourceDemand:
    """Capacity reserved by an event for its complete duration."""

    resource_id: str
    amount: Number

    def __post_init__(self) -> None:
        _require_nonempty(self.resource_id, "resource_id")
        _require_finite_number(
            self.amount,
            "amount",
            minimum=0.0,
            strict_minimum=True,
        )

    def to_dict(self) -> dict[str, object]:
        return {"resource_id": self.resource_id, "amount": self.amount}


@dataclass(frozen=True)
class TemporalEvent:
    """An immutable request to occupy resources on the timeline."""

    event_id: str
    kind: EventKind
    earliest_start_ns: int
    duration_ns: int
    demands: Tuple[ResourceDemand, ...] = ()
    location: Optional[str] = None
    priority: int = 0
    fixed_start: bool = False
    metadata: Metadata = ()

    def __post_init__(self) -> None:
        _require_nonempty(self.event_id, "event_id")
        if not isinstance(self.kind, EventKind):
            raise TypeError("kind must be an EventKind")
        _require_integer(self.earliest_start_ns, "earliest_start_ns")
        _require_integer(self.duration_ns, "duration_ns")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise ValueError("priority must be an integer")
        if not isinstance(self.fixed_start, bool):
            raise TypeError("fixed_start must be bool")
        if self.location is not None:
            _require_nonempty(self.location, "location")

        demands = tuple(self.demands)
        if not all(isinstance(demand, ResourceDemand) for demand in demands):
            raise TypeError("demands must contain ResourceDemand values")
        resource_ids = [demand.resource_id for demand in demands]
        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError("an event may demand each resource at most once")
        object.__setattr__(
            self,
            "demands",
            tuple(sorted(demands, key=lambda demand: demand.resource_id)),
        )

        metadata = tuple(self.metadata)
        if any(
            not isinstance(item, tuple) or len(item) != 2
            for item in metadata
        ):
            raise TypeError("metadata must contain (key, scalar) pairs")
        normalized = freeze_metadata(dict(metadata))
        if len(normalized) != len(metadata):
            raise ValueError("metadata keys must be unique")
        object.__setattr__(self, "metadata", normalized)

    @classmethod
    def create(
        cls,
        event_id: str,
        kind: EventKind,
        earliest_start_ns: int,
        duration_ns: int,
        *,
        demands: Iterable[ResourceDemand] = (),
        location: Optional[str] = None,
        priority: int = 0,
        fixed_start: bool = False,
        metadata: Optional[Mapping[str, JsonScalar]] = None,
    ) -> "TemporalEvent":
        return cls(
            event_id=event_id,
            kind=kind,
            earliest_start_ns=earliest_start_ns,
            duration_ns=duration_ns,
            demands=tuple(demands),
            location=location,
            priority=priority,
            fixed_start=fixed_start,
            metadata=freeze_metadata(metadata),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "earliest_start_ns": self.earliest_start_ns,
            "duration_ns": self.duration_ns,
            "demands": [demand.to_dict() for demand in self.demands],
            "location": self.location,
            "priority": self.priority,
            "fixed_start": self.fixed_start,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class EventRecord:
    """The scheduled interval and contention delay for one event."""

    event: TemporalEvent
    start_ns: int
    end_ns: int

    @property
    def wait_ns(self) -> int:
        return self.start_ns - self.event.earliest_start_ns

    def to_dict(self) -> dict[str, object]:
        return {
            "event": self.event.to_dict(),
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "wait_ns": self.wait_ns,
        }


@dataclass(frozen=True)
class ResourceUsageSnapshot:
    """Visible usage of one resource at a timeline transition."""

    resource_id: str
    capacity: Number
    used: Number
    unit: str
    active_event_ids: Tuple[str, ...]

    @property
    def available(self) -> Number:
        return self.capacity - self.used

    def to_dict(self) -> dict[str, object]:
        return {
            "resource_id": self.resource_id,
            "capacity": self.capacity,
            "used": self.used,
            "available": self.available,
            "unit": self.unit,
            "active_event_ids": list(self.active_event_ids),
        }


@dataclass(frozen=True)
class VisibleStateSnapshot:
    """Immutable scheduler-visible state at one transition time."""

    timestamp_ns: int
    resources: Tuple[ResourceUsageSnapshot, ...]
    active_event_ids: Tuple[str, ...]
    pending_event_ids: Tuple[str, ...]
    completed_event_ids: Tuple[str, ...]

    def resource(self, resource_id: str) -> ResourceUsageSnapshot:
        for resource in self.resources:
            if resource.resource_id == resource_id:
                return resource
        raise KeyError(resource_id)

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp_ns": self.timestamp_ns,
            "resources": [resource.to_dict() for resource in self.resources],
            "active_event_ids": list(self.active_event_ids),
            "pending_event_ids": list(self.pending_event_ids),
            "completed_event_ids": list(self.completed_event_ids),
        }


@dataclass(frozen=True)
class TimelineTrace:
    """Canonical event trace, ordered by actual start time then event id."""

    events: Tuple[EventRecord, ...]

    def event(self, event_id: str) -> EventRecord:
        for record in self.events:
            if record.event.event_id == event_id:
                return record
        raise KeyError(event_id)

    def to_dict(self) -> dict[str, object]:
        return {"events": [record.to_dict() for record in self.events]}

    def to_json(self) -> str:
        return canonical_json(self)


@dataclass(frozen=True)
class TimelineResult:
    """Complete deterministic output of an :class:`EventTimeline` run."""

    start_ns: int
    end_ns: int
    trace: TimelineTrace
    snapshots: Tuple[VisibleStateSnapshot, ...]

    @property
    def elapsed_ns(self) -> int:
        return self.end_ns - self.start_ns

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "gpu-stack.temporal-result.v1",
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "elapsed_ns": self.elapsed_ns,
            "trace": self.trace.to_dict(),
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
        }

    def to_json(self) -> str:
        return canonical_json(self)


@dataclass(frozen=True)
class _Reservation:
    event_id: str
    start_ns: int
    end_ns: int
    amount: Number


class EventTimeline:
    """Deterministically allocate events over shared resource capacities.

    Events are considered in ``(earliest_start_ns, priority, kind, event_id)``
    order, so allocation is independent of the order in which callers submit
    them.  A demand reserves a constant amount for the entire event.  If any
    requested capacity is unavailable, the complete event advances to the
    first release time that could make it feasible.
    """

    def __init__(
        self,
        resources: Iterable[Resource],
        *,
        start_ns: int = 0,
    ) -> None:
        _require_integer(start_ns, "start_ns")
        ordered = tuple(sorted(tuple(resources), key=lambda item: item.resource_id))
        if not all(isinstance(resource, Resource) for resource in ordered):
            raise TypeError("resources must contain Resource values")
        ids = [resource.resource_id for resource in ordered]
        if len(ids) != len(set(ids)):
            raise ValueError("resource_id values must be unique")
        self._resources = ordered
        self._resource_by_id = {
            resource.resource_id: resource for resource in self._resources
        }
        self._start_ns = start_ns
        self._events: dict[str, TemporalEvent] = {}

    @property
    def resources(self) -> Tuple[Resource, ...]:
        return self._resources

    @property
    def events(self) -> Tuple[TemporalEvent, ...]:
        return tuple(
            sorted(
                self._events.values(),
                key=self._event_order_key,
            )
        )

    @staticmethod
    def _event_order_key(event: TemporalEvent) -> tuple[object, ...]:
        return (
            event.earliest_start_ns,
            event.priority,
            event.kind.value,
            event.event_id,
        )

    def schedule(self, event: TemporalEvent) -> None:
        if not isinstance(event, TemporalEvent):
            raise TypeError("event must be a TemporalEvent")
        if event.event_id in self._events:
            raise ValueError(f"duplicate event_id {event.event_id!r}")
        if event.earliest_start_ns < self._start_ns:
            raise ValueError(
                f"event {event.event_id!r} starts before timeline start_ns"
            )
        for demand in event.demands:
            resource = self._resource_by_id.get(demand.resource_id)
            if resource is None:
                raise ValueError(
                    f"event {event.event_id!r} references unknown resource "
                    f"{demand.resource_id!r}"
                )
            if self._exceeds(demand.amount, resource.capacity):
                raise ValueError(
                    f"event {event.event_id!r} demand {demand.amount} exceeds "
                    f"capacity {resource.capacity} of {resource.resource_id!r}"
                )
        self._events[event.event_id] = event

    def schedule_all(self, events: Iterable[TemporalEvent]) -> None:
        events_tuple = tuple(events)
        incoming_ids = [event.event_id for event in events_tuple]
        if len(incoming_ids) != len(set(incoming_ids)):
            raise ValueError("event_id values passed to schedule_all must be unique")
        conflicts = set(incoming_ids).intersection(self._events)
        if conflicts:
            raise ValueError(f"duplicate event_id {sorted(conflicts)[0]!r}")
        # Validate against a temporary timeline so schedule_all is atomic.
        probe = EventTimeline(self._resources, start_ns=self._start_ns)
        for existing in self._events.values():
            probe.schedule(existing)
        for event in events_tuple:
            probe.schedule(event)
        self._events = dict(probe._events)

    @staticmethod
    def _exceeds(amount: Number, capacity: Number) -> bool:
        tolerance = 1e-12 * max(1.0, abs(float(capacity)))
        return float(amount) - float(capacity) > tolerance

    def _earliest_feasible_start(
        self,
        event: TemporalEvent,
        reservations: Mapping[str, Sequence[_Reservation]],
    ) -> int:
        if event.duration_ns == 0 or not event.demands:
            return event.earliest_start_ns

        candidate = event.earliest_start_ns
        while True:
            candidate_end = candidate + event.duration_ns
            release_candidates: list[int] = []

            for demand in event.demands:
                resource = self._resource_by_id[demand.resource_id]
                relevant = tuple(
                    reservation
                    for reservation in reservations[demand.resource_id]
                    if reservation.start_ns < candidate_end
                    and reservation.end_ns > candidate
                )
                boundaries = {candidate, candidate_end}
                for reservation in relevant:
                    boundaries.add(max(candidate, reservation.start_ns))
                    boundaries.add(min(candidate_end, reservation.end_ns))

                for point in sorted(boundaries)[:-1]:
                    active = tuple(
                        reservation
                        for reservation in relevant
                        if reservation.start_ns <= point < reservation.end_ns
                    )
                    used = sum(
                        (reservation.amount for reservation in active),
                        start=0,
                    )
                    if self._exceeds(used + demand.amount, resource.capacity):
                        # A static over-capacity request was rejected by
                        # schedule(), so a violation here always has an active
                        # reservation whose release advances the search.
                        release_candidates.append(
                            min(reservation.end_ns for reservation in active)
                        )
                        break

            if not release_candidates:
                return candidate
            candidate = min(release_candidates)

    def run(self) -> TimelineResult:
        reservations: dict[str, list[_Reservation]] = {
            resource.resource_id: [] for resource in self._resources
        }
        allocated: list[EventRecord] = []

        # Fixed events represent exogenous traces such as a known outage or a
        # grid constraint.  Reserve them first so ordinary work cannot move
        # the observed event.  Fixed events that conflict with each other are
        # invalid input rather than silently delayed observations.
        fixed_events = tuple(event for event in self.events if event.fixed_start)
        flexible_events = tuple(event for event in self.events if not event.fixed_start)
        for event in fixed_events:
            start_ns = self._earliest_feasible_start(event, reservations)
            if start_ns != event.earliest_start_ns:
                raise ValueError(
                    f"fixed event {event.event_id!r} conflicts with another "
                    "fixed reservation"
                )
            end_ns = start_ns + event.duration_ns
            record = EventRecord(event=event, start_ns=start_ns, end_ns=end_ns)
            allocated.append(record)
            if event.duration_ns == 0:
                continue
            for demand in event.demands:
                reservations[demand.resource_id].append(
                    _Reservation(
                        event_id=event.event_id,
                        start_ns=start_ns,
                        end_ns=end_ns,
                        amount=demand.amount,
                    )
                )

        for event in flexible_events:
            start_ns = self._earliest_feasible_start(event, reservations)
            end_ns = start_ns + event.duration_ns
            record = EventRecord(event=event, start_ns=start_ns, end_ns=end_ns)
            allocated.append(record)
            if event.duration_ns == 0:
                continue
            for demand in event.demands:
                reservations[demand.resource_id].append(
                    _Reservation(
                        event_id=event.event_id,
                        start_ns=start_ns,
                        end_ns=end_ns,
                        amount=demand.amount,
                    )
                )

        records = tuple(
            sorted(
                allocated,
                key=lambda record: (
                    record.start_ns,
                    record.end_ns,
                    record.event.event_id,
                ),
            )
        )
        trace = TimelineTrace(events=records)
        snapshots = self._build_snapshots(records)
        end_ns = max(
            (record.end_ns for record in records),
            default=self._start_ns,
        )
        return TimelineResult(
            start_ns=self._start_ns,
            end_ns=end_ns,
            trace=trace,
            snapshots=snapshots,
        )

    def _build_snapshots(
        self,
        records: Tuple[EventRecord, ...],
    ) -> Tuple[VisibleStateSnapshot, ...]:
        transition_times = {self._start_ns}
        for record in records:
            transition_times.add(record.start_ns)
            transition_times.add(record.end_ns)

        snapshots = []
        for timestamp_ns in sorted(transition_times):
            active_records = tuple(
                record
                for record in records
                if record.start_ns <= timestamp_ns < record.end_ns
            )
            active_ids = tuple(
                sorted(record.event.event_id for record in active_records)
            )
            pending_ids = tuple(
                sorted(
                    record.event.event_id
                    for record in records
                    if record.start_ns > timestamp_ns
                )
            )
            completed_ids = tuple(
                sorted(
                    record.event.event_id
                    for record in records
                    if record.end_ns <= timestamp_ns
                )
            )
            usages = []
            for resource in self._resources:
                consumers = []
                used: Number = 0
                for record in active_records:
                    for demand in record.event.demands:
                        if demand.resource_id == resource.resource_id:
                            used += demand.amount
                            consumers.append(record.event.event_id)
                usages.append(
                    ResourceUsageSnapshot(
                        resource_id=resource.resource_id,
                        capacity=resource.capacity,
                        used=used,
                        unit=resource.unit,
                        active_event_ids=tuple(sorted(consumers)),
                    )
                )
            snapshots.append(
                VisibleStateSnapshot(
                    timestamp_ns=timestamp_ns,
                    resources=tuple(usages),
                    active_event_ids=active_ids,
                    pending_event_ids=pending_ids,
                    completed_event_ids=completed_ids,
                )
            )
        return tuple(snapshots)


__all__ = [
    "EventKind",
    "EventRecord",
    "EventTimeline",
    "JsonScalar",
    "Metadata",
    "Number",
    "Resource",
    "ResourceDemand",
    "ResourceUsageSnapshot",
    "TemporalEvent",
    "TimelineResult",
    "TimelineTrace",
    "VisibleStateSnapshot",
    "canonical_json",
    "duration_ns_for_rate",
    "freeze_metadata",
    "seconds_to_ns",
]
