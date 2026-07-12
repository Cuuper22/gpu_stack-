"""Multi-site virtual datacenter mechanics for GPUSTACK experiments.

This module composes :mod:`gpu_stack.research.temporal` into explicit site,
WAN, intervention, policy, trace, and metric artifacts.  It is intentionally
mechanistic: it models resource time, contention, placement, outages, and
controller-visible state, but makes no claim about optimization convergence or
model quality.  E001 must supply and validate that learning model separately.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from typing import (
    Iterable,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
    runtime_checkable,
)

from .temporal import (
    EventKind,
    EventRecord,
    EventTimeline,
    JsonScalar,
    Metadata,
    Number,
    Resource,
    ResourceDemand,
    TemporalEvent,
    TimelineResult,
    TimelineTrace,
    VisibleStateSnapshot,
    canonical_json,
    duration_ns_for_rate,
    freeze_metadata,
)


def _nonempty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _integer(value: int, name: str, *, minimum: int = 0) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def _number(
    value: Number,
    name: str,
    *,
    minimum: float = 0.0,
    strict: bool = False,
) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    if not math.isfinite(float(value)):
        raise ValueError(f"{name} must be a finite real number")
    if strict and not float(value) > minimum:
        raise ValueError(f"{name} must be > {minimum}")
    if not strict and float(value) < minimum:
        raise ValueError(f"{name} must be >= {minimum}")


def _resource_id(site_id: str, resource: str) -> str:
    return f"site:{site_id}:{resource}"


def _link_resource_id(link_id: str) -> str:
    return f"wan:{link_id}:bandwidth"


def _metadata_with(
    base: Mapping[str, JsonScalar],
    extra: Optional[Mapping[str, JsonScalar]],
) -> dict[str, JsonScalar]:
    result = dict(base)
    if extra is None:
        return result
    overlap = set(result).intersection(extra)
    if overlap:
        raise ValueError(
            "metadata may not override reserved keys: "
            + ", ".join(sorted(overlap))
        )
    result.update(extra)
    # Reuse the canonical scalar validation even though TemporalEvent.create
    # will validate it again.  This keeps failure atomic before queue mutation.
    freeze_metadata(result)
    return result


@dataclass(frozen=True)
class Site:
    """Explicit compute, I/O, and facility capacities of one site."""

    site_id: str
    accelerator_type: str
    accelerator_count: int
    accelerator_flops_per_second: Number
    collective_bandwidth_bytes_per_second: Number
    state_transfer_bandwidth_bytes_per_second: Number
    checkpoint_bandwidth_bytes_per_second: Number
    base_power_w: Number
    accelerator_power_w: Number
    power_cap_w: Number
    cooling_capacity_w: Number
    grid_import_limit_w: Number

    def __post_init__(self) -> None:
        _nonempty(self.site_id, "site_id")
        _nonempty(self.accelerator_type, "accelerator_type")
        _integer(self.accelerator_count, "accelerator_count", minimum=1)
        for name in (
            "accelerator_flops_per_second",
            "collective_bandwidth_bytes_per_second",
            "state_transfer_bandwidth_bytes_per_second",
            "checkpoint_bandwidth_bytes_per_second",
            "accelerator_power_w",
        ):
            _number(getattr(self, name), name, strict=True)
        for name in (
            "base_power_w",
            "power_cap_w",
            "cooling_capacity_w",
            "grid_import_limit_w",
        ):
            _number(getattr(self, name), name)
        self.validate_power_cap(self.power_cap_w)

    def validate_power_cap(self, power_cap_w: Number) -> None:
        _number(power_cap_w, "power_cap_w")
        if float(power_cap_w) < float(self.base_power_w):
            raise ValueError(
                f"site {self.site_id!r} power cap must cover base_power_w"
            )
        hard_limit = min(
            float(self.cooling_capacity_w),
            float(self.grid_import_limit_w),
        )
        if float(power_cap_w) > hard_limit:
            raise ValueError(
                f"site {self.site_id!r} power cap exceeds cooling/grid limit"
            )

    def effective_accelerators(self, power_cap_w: Optional[Number] = None) -> int:
        cap = self.power_cap_w if power_cap_w is None else power_cap_w
        self.validate_power_cap(cap)
        headroom = max(0.0, float(cap) - float(self.base_power_w))
        power_limited = int(
            math.floor(headroom / float(self.accelerator_power_w) + 1e-12)
        )
        return min(self.accelerator_count, power_limited)

    def to_dict(self) -> dict[str, object]:
        return {
            "site_id": self.site_id,
            "accelerator_type": self.accelerator_type,
            "accelerator_count": self.accelerator_count,
            "accelerator_flops_per_second": self.accelerator_flops_per_second,
            "collective_bandwidth_bytes_per_second": (
                self.collective_bandwidth_bytes_per_second
            ),
            "state_transfer_bandwidth_bytes_per_second": (
                self.state_transfer_bandwidth_bytes_per_second
            ),
            "checkpoint_bandwidth_bytes_per_second": (
                self.checkpoint_bandwidth_bytes_per_second
            ),
            "base_power_w": self.base_power_w,
            "accelerator_power_w": self.accelerator_power_w,
            "power_cap_w": self.power_cap_w,
            "cooling_capacity_w": self.cooling_capacity_w,
            "grid_import_limit_w": self.grid_import_limit_w,
        }


@dataclass(frozen=True)
class WANLink:
    """A directed-or-undirected E001 WAN path with explicit rate and latency."""

    link_id: str
    site_a: str
    site_b: str
    bandwidth_bytes_per_second: Number
    latency_ns: int
    available: bool = True

    def __post_init__(self) -> None:
        _nonempty(self.link_id, "link_id")
        _nonempty(self.site_a, "site_a")
        _nonempty(self.site_b, "site_b")
        if self.site_a == self.site_b:
            raise ValueError("WAN link endpoints must be distinct sites")
        _number(
            self.bandwidth_bytes_per_second,
            "bandwidth_bytes_per_second",
            strict=True,
        )
        _integer(self.latency_ns, "latency_ns")
        if not isinstance(self.available, bool):
            raise TypeError("available must be bool")

    def connects(self, site_a: str, site_b: str) -> bool:
        return {self.site_a, self.site_b} == {site_a, site_b}

    def other(self, site_id: str) -> str:
        if site_id == self.site_a:
            return self.site_b
        if site_id == self.site_b:
            return self.site_a
        raise KeyError(site_id)

    def to_dict(self) -> dict[str, object]:
        return {
            "link_id": self.link_id,
            "site_a": self.site_a,
            "site_b": self.site_b,
            "bandwidth_bytes_per_second": self.bandwidth_bytes_per_second,
            "latency_ns": self.latency_ns,
            "available": self.available,
        }


@dataclass(frozen=True)
class ParallelismConfig:
    """The controller-visible decomposition of the current training job."""

    data_parallel: int = 1
    tensor_parallel: int = 1
    pipeline_parallel: int = 1
    expert_parallel: int = 1
    context_parallel: int = 1
    sequence_parallel: int = 1

    def __post_init__(self) -> None:
        for name in (
            "data_parallel",
            "tensor_parallel",
            "pipeline_parallel",
            "expert_parallel",
            "context_parallel",
            "sequence_parallel",
        ):
            _integer(getattr(self, name), name, minimum=1)

    def to_dict(self) -> dict[str, int]:
        return {
            "data_parallel": self.data_parallel,
            "tensor_parallel": self.tensor_parallel,
            "pipeline_parallel": self.pipeline_parallel,
            "expert_parallel": self.expert_parallel,
            "context_parallel": self.context_parallel,
            "sequence_parallel": self.sequence_parallel,
        }


@dataclass(frozen=True)
class SyncCadence:
    """Observable synchronization/local-step policy parameters."""

    local_steps: int = 1
    topology: str = "global_all_reduce"
    pipeline_depth: int = 0
    max_update_staleness: int = 0

    def __post_init__(self) -> None:
        _integer(self.local_steps, "local_steps", minimum=1)
        _nonempty(self.topology, "topology")
        _integer(self.pipeline_depth, "pipeline_depth")
        _integer(self.max_update_staleness, "max_update_staleness")

    def to_dict(self) -> dict[str, object]:
        return {
            "local_steps": self.local_steps,
            "topology": self.topology,
            "pipeline_depth": self.pipeline_depth,
            "max_update_staleness": self.max_update_staleness,
        }


# ---------------------------------------------------------------------------
# Interventions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MembershipIntervention:
    site_id: str
    active: bool
    reason: str = ""

    def __post_init__(self) -> None:
        _nonempty(self.site_id, "site_id")
        if not isinstance(self.active, bool):
            raise TypeError("active must be bool")
        if not isinstance(self.reason, str):
            raise TypeError("reason must be str")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "membership",
            "site_id": self.site_id,
            "active": self.active,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ParallelismIntervention:
    config: ParallelismConfig
    reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.config, ParallelismConfig):
            raise TypeError("config must be ParallelismConfig")
        if not isinstance(self.reason, str):
            raise TypeError("reason must be str")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "parallelism",
            "config": self.config.to_dict(),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ConfigurationIntervention:
    changes: Metadata
    reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.reason, str):
            raise TypeError("reason must be str")
        changes = tuple(self.changes)
        normalized = freeze_metadata(dict(changes))
        if len(changes) != len(normalized):
            raise ValueError("configuration change keys must be unique")
        object.__setattr__(self, "changes", normalized)

    @classmethod
    def create(
        cls,
        changes: Mapping[str, JsonScalar],
        reason: str = "",
    ) -> "ConfigurationIntervention":
        return cls(changes=freeze_metadata(changes), reason=reason)

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "configuration",
            "changes": dict(self.changes),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class SyncCadenceIntervention:
    cadence: SyncCadence
    reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.cadence, SyncCadence):
            raise TypeError("cadence must be SyncCadence")
        if not isinstance(self.reason, str):
            raise TypeError("reason must be str")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "sync_cadence",
            "cadence": self.cadence.to_dict(),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class MigrationIntervention:
    state_id: str
    source_site_id: str
    target_site_id: str
    size_bytes: Number
    link_id: Optional[str] = None
    bandwidth_bytes_per_second: Optional[Number] = None
    reason: str = ""

    def __post_init__(self) -> None:
        _nonempty(self.state_id, "state_id")
        _nonempty(self.source_site_id, "source_site_id")
        _nonempty(self.target_site_id, "target_site_id")
        if self.source_site_id == self.target_site_id:
            raise ValueError("migration source and target must differ")
        _number(self.size_bytes, "size_bytes", strict=True)
        if self.link_id is not None:
            _nonempty(self.link_id, "link_id")
        if self.bandwidth_bytes_per_second is not None:
            _number(
                self.bandwidth_bytes_per_second,
                "bandwidth_bytes_per_second",
                strict=True,
            )
        if not isinstance(self.reason, str):
            raise TypeError("reason must be str")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "migration",
            "state_id": self.state_id,
            "source_site_id": self.source_site_id,
            "target_site_id": self.target_site_id,
            "size_bytes": self.size_bytes,
            "link_id": self.link_id,
            "bandwidth_bytes_per_second": self.bandwidth_bytes_per_second,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PowerCapIntervention:
    site_id: str
    power_cap_w: Number
    reason: str = ""

    def __post_init__(self) -> None:
        _nonempty(self.site_id, "site_id")
        _number(self.power_cap_w, "power_cap_w")
        if not isinstance(self.reason, str):
            raise TypeError("reason must be str")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "power_cap",
            "site_id": self.site_id,
            "power_cap_w": self.power_cap_w,
            "reason": self.reason,
        }


Intervention = Union[
    MembershipIntervention,
    ParallelismIntervention,
    ConfigurationIntervention,
    SyncCadenceIntervention,
    MigrationIntervention,
    PowerCapIntervention,
]


# ---------------------------------------------------------------------------
# Immutable controller-visible state
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VisibleSiteState:
    site_id: str
    accelerator_type: str
    active: bool
    healthy: bool
    accelerator_count: int
    effective_accelerators: int
    busy_accelerators: Number
    accelerator_flops_per_second: Number
    collective_bandwidth_bytes_per_second: Number
    state_transfer_bandwidth_bytes_per_second: Number
    checkpoint_bandwidth_bytes_per_second: Number
    base_power_w: Number
    accelerator_power_w: Number
    power_cap_w: Number
    cooling_capacity_w: Number
    grid_import_limit_w: Number
    allocated_power_w: Number
    owned_state_ids: Tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "site_id": self.site_id,
            "accelerator_type": self.accelerator_type,
            "active": self.active,
            "healthy": self.healthy,
            "accelerator_count": self.accelerator_count,
            "effective_accelerators": self.effective_accelerators,
            "busy_accelerators": self.busy_accelerators,
            "accelerator_flops_per_second": self.accelerator_flops_per_second,
            "collective_bandwidth_bytes_per_second": (
                self.collective_bandwidth_bytes_per_second
            ),
            "state_transfer_bandwidth_bytes_per_second": (
                self.state_transfer_bandwidth_bytes_per_second
            ),
            "checkpoint_bandwidth_bytes_per_second": (
                self.checkpoint_bandwidth_bytes_per_second
            ),
            "base_power_w": self.base_power_w,
            "accelerator_power_w": self.accelerator_power_w,
            "power_cap_w": self.power_cap_w,
            "cooling_capacity_w": self.cooling_capacity_w,
            "grid_import_limit_w": self.grid_import_limit_w,
            "allocated_power_w": self.allocated_power_w,
            "owned_state_ids": list(self.owned_state_ids),
        }


@dataclass(frozen=True)
class VisibleLinkState:
    link_id: str
    site_a: str
    site_b: str
    available: bool
    bandwidth_bytes_per_second: Number
    used_bandwidth_bytes_per_second: Number
    latency_ns: int
    active_event_ids: Tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "link_id": self.link_id,
            "site_a": self.site_a,
            "site_b": self.site_b,
            "available": self.available,
            "bandwidth_bytes_per_second": self.bandwidth_bytes_per_second,
            "used_bandwidth_bytes_per_second": (
                self.used_bandwidth_bytes_per_second
            ),
            "latency_ns": self.latency_ns,
            "active_event_ids": list(self.active_event_ids),
        }


@dataclass(frozen=True)
class VisibleDatacenterState:
    """The complete and only state object provided to a policy."""

    timestamp_ns: int
    sites: Tuple[VisibleSiteState, ...]
    links: Tuple[VisibleLinkState, ...]
    membership: Tuple[str, ...]
    parallelism: ParallelismConfig
    sync_cadence: SyncCadence
    configuration: Metadata
    state_locations: Tuple[Tuple[str, str], ...]
    queued_event_ids: Tuple[str, ...]
    active_event_ids: Tuple[str, ...]
    completed_event_ids: Tuple[str, ...]

    def site(self, site_id: str) -> VisibleSiteState:
        for site in self.sites:
            if site.site_id == site_id:
                return site
        raise KeyError(site_id)

    def link(self, link_id: str) -> VisibleLinkState:
        for link in self.links:
            if link.link_id == link_id:
                return link
        raise KeyError(link_id)

    def location_of(self, state_id: str) -> str:
        for known_state_id, site_id in self.state_locations:
            if known_state_id == state_id:
                return site_id
        raise KeyError(state_id)

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp_ns": self.timestamp_ns,
            "sites": [site.to_dict() for site in self.sites],
            "links": [link.to_dict() for link in self.links],
            "membership": list(self.membership),
            "parallelism": self.parallelism.to_dict(),
            "sync_cadence": self.sync_cadence.to_dict(),
            "configuration": dict(self.configuration),
            "state_locations": [
                {"state_id": state_id, "site_id": site_id}
                for state_id, site_id in self.state_locations
            ],
            "queued_event_ids": list(self.queued_event_ids),
            "active_event_ids": list(self.active_event_ids),
            "completed_event_ids": list(self.completed_event_ids),
        }


@runtime_checkable
class Policy(Protocol):
    """A controller that can inspect observable state and nothing else."""

    def decide(
        self,
        state: VisibleDatacenterState,
    ) -> Sequence[Intervention]:
        ...


# ---------------------------------------------------------------------------
# Result artifacts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InterventionRecord:
    sequence: int
    applied_at_ns: int
    intervention: Intervention

    def to_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "applied_at_ns": self.applied_at_ns,
            "intervention": self.intervention.to_dict(),
        }


@dataclass(frozen=True)
class DatacenterTrace:
    timeline: TimelineTrace
    interventions: Tuple[InterventionRecord, ...]

    @property
    def records(self) -> Tuple[EventRecord, ...]:
        return self.timeline.events

    def to_dict(self) -> dict[str, object]:
        return {
            "timeline": self.timeline.to_dict(),
            "interventions": [item.to_dict() for item in self.interventions],
        }

    def to_json(self) -> str:
        return canonical_json(self)


@dataclass(frozen=True)
class ResourceUtilization:
    resource_id: str
    capacity: Number
    unit: str
    capacity_time: Number
    unavailable_capacity_time: Number
    utilization: float

    def to_dict(self) -> dict[str, object]:
        return {
            "resource_id": self.resource_id,
            "capacity": self.capacity,
            "unit": self.unit,
            "capacity_time": self.capacity_time,
            "unavailable_capacity_time": self.unavailable_capacity_time,
            "utilization": self.utilization,
        }


@dataclass(frozen=True)
class DatacenterMetrics:
    """Mechanics-only aggregates; deliberately excludes learning progress."""

    compute_flops: Number
    inter_site_collective_bytes: Number
    state_transfer_bytes: Number
    checkpoint_bytes: Number
    accelerator_time_ns: Number
    modeled_base_and_compute_energy_j: float
    peak_allocated_power_w: Number
    resource_utilization: Tuple[ResourceUtilization, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "compute_flops": self.compute_flops,
            "inter_site_collective_bytes": self.inter_site_collective_bytes,
            "state_transfer_bytes": self.state_transfer_bytes,
            "checkpoint_bytes": self.checkpoint_bytes,
            "accelerator_time_ns": self.accelerator_time_ns,
            "modeled_base_and_compute_energy_j": (
                self.modeled_base_and_compute_energy_j
            ),
            "peak_allocated_power_w": self.peak_allocated_power_w,
            "resource_utilization": [
                item.to_dict() for item in self.resource_utilization
            ],
        }


@dataclass(frozen=True)
class DatacenterResult:
    start_ns: int
    end_ns: int
    decision_state: VisibleDatacenterState
    final_state: VisibleDatacenterState
    snapshots: Tuple[VisibleDatacenterState, ...]
    trace: DatacenterTrace
    metrics: DatacenterMetrics

    @property
    def elapsed_ns(self) -> int:
        return self.end_ns - self.start_ns

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "gpu-stack.datacenter-result.v1",
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "elapsed_ns": self.elapsed_ns,
            "decision_state": self.decision_state.to_dict(),
            "final_state": self.final_state.to_dict(),
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
            "trace": self.trace.to_dict(),
            "metrics": self.metrics.to_dict(),
        }

    def to_json(self) -> str:
        return canonical_json(self)


@dataclass(frozen=True)
class _MigrationPlan:
    event_id: str
    state_id: str
    source_site_id: str
    target_site_id: str


# ---------------------------------------------------------------------------
# Virtual datacenter
# ---------------------------------------------------------------------------


class VirtualDatacenter:
    """Stateful, deterministic multi-site experiment substrate.

    A call to :meth:`run` executes the currently queued events as one decision
    epoch and advances ``timestamp_ns``.  Controllers can then inspect the new
    observable state, intervene, queue the next epoch, and run again.  This
    makes policy timing explicit without giving a policy future outage traces
    or other simulator-private state.
    """

    def __init__(
        self,
        sites: Iterable[Site],
        links: Iterable[WANLink],
        *,
        active_site_ids: Optional[Iterable[str]] = None,
        parallelism: Optional[ParallelismConfig] = None,
        sync_cadence: Optional[SyncCadence] = None,
        configuration: Optional[Mapping[str, JsonScalar]] = None,
        state_locations: Optional[Mapping[str, str]] = None,
        start_ns: int = 0,
    ) -> None:
        _integer(start_ns, "start_ns")
        site_tuple = tuple(sites)
        link_tuple = tuple(links)
        if not site_tuple:
            raise ValueError("sites must contain at least one Site")
        if not all(isinstance(site, Site) for site in site_tuple):
            raise TypeError("sites must contain Site values")
        if not all(isinstance(link, WANLink) for link in link_tuple):
            raise TypeError("links must contain WANLink values")

        site_ids = [site.site_id for site in site_tuple]
        link_ids = [link.link_id for link in link_tuple]
        if len(site_ids) != len(set(site_ids)):
            raise ValueError("site_id values must be unique")
        if len(link_ids) != len(set(link_ids)):
            raise ValueError("link_id values must be unique")

        self._sites = {site.site_id: site for site in site_tuple}
        self._links = {link.link_id: link for link in link_tuple}
        for link in link_tuple:
            unknown = {link.site_a, link.site_b}.difference(self._sites)
            if unknown:
                raise ValueError(
                    f"link {link.link_id!r} references unknown site "
                    f"{sorted(unknown)[0]!r}"
                )

        if active_site_ids is None:
            active = set(self._sites)
        else:
            active = set(active_site_ids)
            unknown = active.difference(self._sites)
            if unknown:
                raise ValueError(f"unknown active site {sorted(unknown)[0]!r}")
        self._active_site_ids = active
        self._parallelism = parallelism or ParallelismConfig()
        self._sync_cadence = sync_cadence or SyncCadence()
        if not isinstance(self._parallelism, ParallelismConfig):
            raise TypeError("parallelism must be ParallelismConfig")
        if not isinstance(self._sync_cadence, SyncCadence):
            raise TypeError("sync_cadence must be SyncCadence")
        self._configuration = dict(freeze_metadata(configuration))
        self._power_caps = {
            site.site_id: site.power_cap_w for site in site_tuple
        }

        locations = dict(state_locations or {})
        for state_id, site_id in locations.items():
            _nonempty(state_id, "state_id")
            if site_id not in self._sites:
                raise ValueError(
                    f"state {state_id!r} references unknown site {site_id!r}"
                )
        self._state_locations = locations
        self._now_ns = start_ns
        self._pending_events: dict[str, TemporalEvent] = {}
        self._pending_migrations: dict[str, _MigrationPlan] = {}
        self._pending_interventions: list[InterventionRecord] = []
        self._intervention_sequence = 0

    @property
    def timestamp_ns(self) -> int:
        return self._now_ns

    def _site(self, site_id: str) -> Site:
        try:
            return self._sites[site_id]
        except KeyError as exc:
            raise ValueError(f"unknown site_id {site_id!r}") from exc

    def _require_active(self, site_id: str) -> Site:
        site = self._site(site_id)
        if site_id not in self._active_site_ids:
            raise ValueError(f"site {site_id!r} is not an active member")
        return site

    def _event_start(self, earliest_start_ns: Optional[int]) -> int:
        if earliest_start_ns is None:
            return self._now_ns
        _integer(earliest_start_ns, "earliest_start_ns")
        if earliest_start_ns < self._now_ns:
            raise ValueError("earliest_start_ns precedes current datacenter time")
        return earliest_start_ns

    def _queue(self, event: TemporalEvent) -> None:
        if event.event_id in self._pending_events:
            raise ValueError(f"duplicate queued event_id {event.event_id!r}")
        self._pending_events[event.event_id] = event

    def _select_link(
        self,
        site_a: str,
        site_b: str,
        link_id: Optional[str],
    ) -> WANLink:
        self._site(site_a)
        self._site(site_b)
        if site_a == site_b:
            raise ValueError("WAN operation endpoints must differ")
        if link_id is not None:
            try:
                link = self._links[link_id]
            except KeyError as exc:
                raise ValueError(f"unknown link_id {link_id!r}") from exc
            if not link.connects(site_a, site_b):
                raise ValueError(
                    f"link {link_id!r} does not connect {site_a!r} and {site_b!r}"
                )
        else:
            candidates = tuple(
                link
                for link in self._links.values()
                if link.connects(site_a, site_b)
            )
            if not candidates:
                raise ValueError(
                    f"no WAN link connects {site_a!r} and {site_b!r}"
                )
            if len(candidates) > 1:
                raise ValueError(
                    f"multiple WAN links connect {site_a!r} and {site_b!r}; "
                    "specify link_id"
                )
            link = candidates[0]
        if not link.available:
            raise ValueError(f"WAN link {link.link_id!r} is unavailable")
        return link

    def schedule_compute(
        self,
        event_id: str,
        site_id: str,
        work_flops: Number,
        accelerator_count: int,
        *,
        earliest_start_ns: Optional[int] = None,
        power_w: Optional[Number] = None,
        priority: int = 0,
        metadata: Optional[Mapping[str, JsonScalar]] = None,
    ) -> TemporalEvent:
        site = self._require_active(site_id)
        _number(work_flops, "work_flops", strict=True)
        _integer(accelerator_count, "accelerator_count", minimum=1)
        if accelerator_count > site.accelerator_count:
            raise ValueError("accelerator_count exceeds physical site inventory")
        event_power = (
            accelerator_count * site.accelerator_power_w
            if power_w is None
            else power_w
        )
        _number(event_power, "power_w", strict=True)
        duration_ns = duration_ns_for_rate(
            work_flops,
            accelerator_count * site.accelerator_flops_per_second,
        )
        demands = (
            ResourceDemand(_resource_id(site_id, "accelerators"), accelerator_count),
            ResourceDemand(_resource_id(site_id, "power"), event_power),
            ResourceDemand(_resource_id(site_id, "cooling"), event_power),
            ResourceDemand(_resource_id(site_id, "grid"), event_power),
        )
        event = TemporalEvent.create(
            event_id,
            EventKind.COMPUTE,
            self._event_start(earliest_start_ns),
            duration_ns,
            demands=demands,
            location=site_id,
            priority=priority,
            metadata=_metadata_with(
                {
                    "site_id": site_id,
                    "work_flops": work_flops,
                    "accelerator_count": accelerator_count,
                    "power_w": event_power,
                },
                metadata,
            ),
        )
        self._queue(event)
        return event

    def schedule_collective(
        self,
        event_id: str,
        size_bytes: Number,
        *,
        site_id: Optional[str] = None,
        link_id: Optional[str] = None,
        bandwidth_bytes_per_second: Optional[Number] = None,
        earliest_start_ns: Optional[int] = None,
        priority: int = 0,
        metadata: Optional[Mapping[str, JsonScalar]] = None,
    ) -> TemporalEvent:
        _number(size_bytes, "size_bytes", strict=True)
        if (site_id is None) == (link_id is None):
            raise ValueError("set exactly one of site_id or link_id")

        if site_id is not None:
            site = self._require_active(site_id)
            rate = (
                site.collective_bandwidth_bytes_per_second
                if bandwidth_bytes_per_second is None
                else bandwidth_bytes_per_second
            )
            _number(rate, "bandwidth_bytes_per_second", strict=True)
            duration_ns = duration_ns_for_rate(size_bytes, rate)
            demands = (
                ResourceDemand(_resource_id(site_id, "fabric"), rate),
            )
            location = site_id
            base_metadata: dict[str, JsonScalar] = {
                "scope": "local",
                "site_id": site_id,
                "size_bytes": size_bytes,
                "bandwidth_bytes_per_second": rate,
            }
        else:
            assert link_id is not None
            try:
                link = self._links[link_id]
            except KeyError as exc:
                raise ValueError(f"unknown link_id {link_id!r}") from exc
            if not link.available:
                raise ValueError(f"WAN link {link_id!r} is unavailable")
            self._require_active(link.site_a)
            self._require_active(link.site_b)
            endpoint_rate = min(
                float(
                    self._sites[
                        link.site_a
                    ].state_transfer_bandwidth_bytes_per_second
                ),
                float(
                    self._sites[
                        link.site_b
                    ].state_transfer_bandwidth_bytes_per_second
                ),
            )
            rate = (
                min(float(link.bandwidth_bytes_per_second), endpoint_rate)
                if bandwidth_bytes_per_second is None
                else bandwidth_bytes_per_second
            )
            _number(rate, "bandwidth_bytes_per_second", strict=True)
            duration_ns = duration_ns_for_rate(
                size_bytes,
                rate,
                latency_ns=link.latency_ns,
            )
            demands = (
                ResourceDemand(_link_resource_id(link_id), rate),
                ResourceDemand(_resource_id(link.site_a, "state_io"), rate),
                ResourceDemand(_resource_id(link.site_b, "state_io"), rate),
            )
            location = link_id
            base_metadata = {
                "scope": "inter_site",
                "link_id": link_id,
                "site_a": link.site_a,
                "site_b": link.site_b,
                "size_bytes": size_bytes,
                "bandwidth_bytes_per_second": rate,
            }
        event = TemporalEvent.create(
            event_id,
            EventKind.COLLECTIVE,
            self._event_start(earliest_start_ns),
            duration_ns,
            demands=demands,
            location=location,
            priority=priority,
            metadata=_metadata_with(base_metadata, metadata),
        )
        self._queue(event)
        return event

    def schedule_state_transfer(
        self,
        event_id: str,
        state_id: str,
        source_site_id: str,
        target_site_id: str,
        size_bytes: Number,
        *,
        link_id: Optional[str] = None,
        bandwidth_bytes_per_second: Optional[Number] = None,
        earliest_start_ns: Optional[int] = None,
        priority: int = 0,
        metadata: Optional[Mapping[str, JsonScalar]] = None,
    ) -> TemporalEvent:
        _nonempty(state_id, "state_id")
        source = self._require_active(source_site_id)
        target = self._require_active(target_site_id)
        _number(size_bytes, "size_bytes", strict=True)
        link = self._select_link(source_site_id, target_site_id, link_id)
        max_rate = min(
            float(link.bandwidth_bytes_per_second),
            float(source.state_transfer_bandwidth_bytes_per_second),
            float(target.state_transfer_bandwidth_bytes_per_second),
        )
        rate: Number = max_rate if bandwidth_bytes_per_second is None else bandwidth_bytes_per_second
        _number(rate, "bandwidth_bytes_per_second", strict=True)
        duration_ns = duration_ns_for_rate(
            size_bytes,
            rate,
            latency_ns=link.latency_ns,
        )
        event = TemporalEvent.create(
            event_id,
            EventKind.STATE_TRANSFER,
            self._event_start(earliest_start_ns),
            duration_ns,
            demands=(
                ResourceDemand(_link_resource_id(link.link_id), rate),
                ResourceDemand(_resource_id(source_site_id, "state_io"), rate),
                ResourceDemand(_resource_id(target_site_id, "state_io"), rate),
            ),
            location=link.link_id,
            priority=priority,
            metadata=_metadata_with(
                {
                    "state_id": state_id,
                    "source_site_id": source_site_id,
                    "target_site_id": target_site_id,
                    "link_id": link.link_id,
                    "size_bytes": size_bytes,
                    "bandwidth_bytes_per_second": rate,
                    "migration": False,
                },
                metadata,
            ),
        )
        self._queue(event)
        return event

    def schedule_checkpoint(
        self,
        event_id: str,
        site_id: str,
        size_bytes: Number,
        *,
        bandwidth_bytes_per_second: Optional[Number] = None,
        earliest_start_ns: Optional[int] = None,
        priority: int = 0,
        metadata: Optional[Mapping[str, JsonScalar]] = None,
    ) -> TemporalEvent:
        site = self._require_active(site_id)
        _number(size_bytes, "size_bytes", strict=True)
        rate = (
            site.checkpoint_bandwidth_bytes_per_second
            if bandwidth_bytes_per_second is None
            else bandwidth_bytes_per_second
        )
        _number(rate, "bandwidth_bytes_per_second", strict=True)
        event = TemporalEvent.create(
            event_id,
            EventKind.CHECKPOINT,
            self._event_start(earliest_start_ns),
            duration_ns_for_rate(size_bytes, rate),
            demands=(
                ResourceDemand(_resource_id(site_id, "checkpoint_io"), rate),
            ),
            location=site_id,
            priority=priority,
            metadata=_metadata_with(
                {
                    "site_id": site_id,
                    "size_bytes": size_bytes,
                    "bandwidth_bytes_per_second": rate,
                },
                metadata,
            ),
        )
        self._queue(event)
        return event

    def schedule_site_outage(
        self,
        event_id: str,
        site_id: str,
        failure_start_ns: int,
        recovery_ns: int,
        *,
        cause: str = "unspecified",
        priority: int = -100,
    ) -> Tuple[TemporalEvent, TemporalEvent]:
        site = self._site(site_id)
        _integer(failure_start_ns, "failure_start_ns")
        _integer(recovery_ns, "recovery_ns")
        if failure_start_ns < self._now_ns:
            raise ValueError("failure_start_ns precedes current datacenter time")
        if recovery_ns <= failure_start_ns:
            raise ValueError("recovery_ns must be greater than failure_start_ns")
        _nonempty(cause, "cause")

        # Saturating operational resources blocks compute, collectives, state
        # movement, and checkpoints without pretending a failed site consumes
        # its complete power envelope.
        demand_specs = (
            (
                _resource_id(site_id, "accelerators"),
                site.accelerator_count,
            ),
            (
                _resource_id(site_id, "fabric"),
                site.collective_bandwidth_bytes_per_second,
            ),
            (
                _resource_id(site_id, "state_io"),
                site.state_transfer_bandwidth_bytes_per_second,
            ),
            (
                _resource_id(site_id, "checkpoint_io"),
                site.checkpoint_bandwidth_bytes_per_second,
            ),
        )
        # A site can be intentionally capped to base power (zero available
        # accelerators).  ResourceDemand forbids zero, so omit zero blockers.
        demands = tuple(
            ResourceDemand(resource_id, amount)
            for resource_id, amount in demand_specs
            if float(amount) > 0.0
        )
        failure = TemporalEvent.create(
            event_id,
            EventKind.FAILURE,
            failure_start_ns,
            recovery_ns - failure_start_ns,
            demands=demands,
            location=site_id,
            priority=priority,
            fixed_start=True,
            metadata={"site_id": site_id, "cause": cause},
        )
        recovery = TemporalEvent.create(
            f"{event_id}:recovery",
            EventKind.RECOVERY,
            recovery_ns,
            0,
            location=site_id,
            priority=priority,
            fixed_start=True,
            metadata={"site_id": site_id, "cause": cause},
        )
        if failure.event_id in self._pending_events or recovery.event_id in self._pending_events:
            raise ValueError("outage event_id or derived recovery event_id is duplicate")
        self._queue(failure)
        self._queue(recovery)
        return failure, recovery

    def schedule_facility_event(
        self,
        event_id: str,
        site_id: str,
        kind: EventKind,
        duration_ns: int,
        demand_w: Number,
        *,
        earliest_start_ns: Optional[int] = None,
        priority: int = 0,
        metadata: Optional[Mapping[str, JsonScalar]] = None,
    ) -> TemporalEvent:
        self._site(site_id)
        if kind not in {EventKind.POWER, EventKind.COOLING, EventKind.GRID}:
            raise ValueError("facility event kind must be POWER, COOLING, or GRID")
        _integer(duration_ns, "duration_ns")
        _number(demand_w, "demand_w", strict=True)
        resource_name = {
            EventKind.POWER: "power",
            EventKind.COOLING: "cooling",
            EventKind.GRID: "grid",
        }[kind]
        event = TemporalEvent.create(
            event_id,
            kind,
            self._event_start(earliest_start_ns),
            duration_ns,
            demands=(
                ResourceDemand(_resource_id(site_id, resource_name), demand_w),
            ),
            location=site_id,
            priority=priority,
            fixed_start=True,
            metadata=_metadata_with(
                {"site_id": site_id, "demand_w": demand_w},
                metadata,
            ),
        )
        self._queue(event)
        return event

    # ------------------------------------------------------------------
    # Observation and policy application
    # ------------------------------------------------------------------

    def observe(self) -> VisibleDatacenterState:
        return self._visible_state(
            timestamp_ns=self._now_ns,
            temporal_snapshot=None,
            records=(),
            locations=self._state_locations,
        )

    def apply_interventions(
        self,
        interventions: Iterable[Intervention],
        at_ns: Optional[int] = None,
    ) -> Tuple[InterventionRecord, ...]:
        applied_at_ns = self._now_ns if at_ns is None else at_ns
        _integer(applied_at_ns, "at_ns")
        if applied_at_ns != self._now_ns:
            raise ValueError("interventions apply only at the current decision time")
        values = tuple(interventions)

        # Intervention batches are atomic.  This matters for a policy whose
        # final migration or power-cap action turns out to be invalid.
        backup = (
            set(self._active_site_ids),
            self._parallelism,
            self._sync_cadence,
            dict(self._configuration),
            dict(self._power_caps),
            dict(self._pending_events),
            dict(self._pending_migrations),
            list(self._pending_interventions),
            self._intervention_sequence,
        )
        records = []
        try:
            for intervention in values:
                if not isinstance(
                    intervention,
                    (
                        MembershipIntervention,
                        ParallelismIntervention,
                        ConfigurationIntervention,
                        SyncCadenceIntervention,
                        MigrationIntervention,
                        PowerCapIntervention,
                    ),
                ):
                    raise TypeError(f"unsupported intervention {intervention!r}")
                self._intervention_sequence += 1
                sequence = self._intervention_sequence
                self._apply_one(intervention, sequence, applied_at_ns)
                record = InterventionRecord(
                    sequence=sequence,
                    applied_at_ns=applied_at_ns,
                    intervention=intervention,
                )
                self._pending_interventions.append(record)
                records.append(record)
        except Exception:
            (
                self._active_site_ids,
                self._parallelism,
                self._sync_cadence,
                self._configuration,
                self._power_caps,
                self._pending_events,
                self._pending_migrations,
                self._pending_interventions,
                self._intervention_sequence,
            ) = backup
            raise
        return tuple(records)

    def _apply_one(
        self,
        intervention: Intervention,
        sequence: int,
        at_ns: int,
    ) -> None:
        if isinstance(intervention, MembershipIntervention):
            self._site(intervention.site_id)
            if intervention.active:
                self._active_site_ids.add(intervention.site_id)
            else:
                self._active_site_ids.discard(intervention.site_id)
            return
        if isinstance(intervention, ParallelismIntervention):
            self._parallelism = intervention.config
            return
        if isinstance(intervention, ConfigurationIntervention):
            self._configuration.update(dict(intervention.changes))
            return
        if isinstance(intervention, SyncCadenceIntervention):
            self._sync_cadence = intervention.cadence
            return
        if isinstance(intervention, PowerCapIntervention):
            site = self._site(intervention.site_id)
            site.validate_power_cap(intervention.power_cap_w)
            self._power_caps[intervention.site_id] = intervention.power_cap_w
            return
        if isinstance(intervention, MigrationIntervention):
            if intervention.state_id not in self._state_locations:
                raise ValueError(f"unknown state_id {intervention.state_id!r}")
            if self._state_locations[intervention.state_id] != intervention.source_site_id:
                raise ValueError(
                    f"state {intervention.state_id!r} is not at source site "
                    f"{intervention.source_site_id!r}"
                )
            if any(
                plan.state_id == intervention.state_id
                for plan in self._pending_migrations.values()
            ):
                raise ValueError(
                    f"state {intervention.state_id!r} already has a pending migration"
                )
            event_id = (
                f"migration:{sequence:06d}:{intervention.state_id}:"
                f"{intervention.source_site_id}:{intervention.target_site_id}"
            )
            event = self.schedule_state_transfer(
                event_id,
                intervention.state_id,
                intervention.source_site_id,
                intervention.target_site_id,
                intervention.size_bytes,
                link_id=intervention.link_id,
                bandwidth_bytes_per_second=(
                    intervention.bandwidth_bytes_per_second
                ),
                earliest_start_ns=at_ns,
                priority=-10,
                metadata={"intervention_sequence": sequence},
            )
            migration_metadata = dict(event.metadata)
            migration_metadata["migration"] = True
            event = TemporalEvent.create(
                event.event_id,
                event.kind,
                event.earliest_start_ns,
                event.duration_ns,
                demands=event.demands,
                location=event.location,
                priority=event.priority,
                fixed_start=event.fixed_start,
                metadata=migration_metadata,
            )
            self._pending_events[event.event_id] = event
            self._pending_migrations[event.event_id] = _MigrationPlan(
                event_id=event.event_id,
                state_id=intervention.state_id,
                source_site_id=intervention.source_site_id,
                target_site_id=intervention.target_site_id,
            )
            return
        raise TypeError(f"unsupported intervention {intervention!r}")

    def apply_policy(self, policy: Policy) -> Tuple[InterventionRecord, ...]:
        if not isinstance(policy, Policy):
            raise TypeError("policy must implement decide(VisibleDatacenterState)")
        if self._pending_events:
            raise ValueError(
                "apply_policy must run before the next epoch is queued; "
                "queued events can contain future exogenous trace information"
            )
        state = self.observe()
        decisions = policy.decide(state)
        if decisions is None or isinstance(decisions, (str, bytes)):
            raise TypeError("policy.decide must return a sequence of interventions")
        if not isinstance(decisions, Sequence):
            raise TypeError("policy.decide must return a sequence of interventions")
        return self.apply_interventions(tuple(decisions), at_ns=self._now_ns)

    # ------------------------------------------------------------------
    # Timeline composition and result production
    # ------------------------------------------------------------------

    def _resources(self) -> Tuple[Resource, ...]:
        resources = []
        for site_id in sorted(self._sites):
            site = self._sites[site_id]
            cap = self._power_caps[site_id]
            resources.extend(
                (
                    Resource(
                        _resource_id(site_id, "accelerators"),
                        site.accelerator_count,
                        "accelerators",
                    ),
                    Resource(
                        _resource_id(site_id, "fabric"),
                        site.collective_bandwidth_bytes_per_second,
                        "bytes_per_second",
                    ),
                    Resource(
                        _resource_id(site_id, "state_io"),
                        site.state_transfer_bandwidth_bytes_per_second,
                        "bytes_per_second",
                    ),
                    Resource(
                        _resource_id(site_id, "checkpoint_io"),
                        site.checkpoint_bandwidth_bytes_per_second,
                        "bytes_per_second",
                    ),
                    Resource(
                        _resource_id(site_id, "power"),
                        float(cap) - float(site.base_power_w),
                        "watts",
                    ),
                    Resource(
                        _resource_id(site_id, "cooling"),
                        float(site.cooling_capacity_w) - float(site.base_power_w),
                        "watts",
                    ),
                    Resource(
                        _resource_id(site_id, "grid"),
                        float(site.grid_import_limit_w) - float(site.base_power_w),
                        "watts",
                    ),
                )
            )
        for link_id in sorted(self._links):
            link = self._links[link_id]
            resources.append(
                Resource(
                    _link_resource_id(link_id),
                    link.bandwidth_bytes_per_second if link.available else 0,
                    "bytes_per_second",
                )
            )
        return tuple(resources)

    def run(self, policy: Optional[Policy] = None) -> DatacenterResult:
        decision_state = self.observe()
        if policy is not None:
            self.apply_policy(policy)

        resources = self._resources()
        timeline = EventTimeline(resources, start_ns=self._now_ns)
        timeline.schedule_all(self._pending_events.values())
        temporal_result = timeline.run()
        snapshots = tuple(
            self._visible_state(
                timestamp_ns=snapshot.timestamp_ns,
                temporal_snapshot=snapshot,
                records=temporal_result.trace.events,
                locations=self._locations_at(
                    snapshot.timestamp_ns,
                    temporal_result.trace.events,
                ),
            )
            for snapshot in temporal_result.snapshots
        )
        final_state = snapshots[-1]
        trace = DatacenterTrace(
            timeline=temporal_result.trace,
            interventions=tuple(self._pending_interventions),
        )
        metrics = self._metrics(temporal_result, snapshots, resources)
        result = DatacenterResult(
            start_ns=temporal_result.start_ns,
            end_ns=temporal_result.end_ns,
            decision_state=decision_state,
            final_state=final_state,
            snapshots=snapshots,
            trace=trace,
            metrics=metrics,
        )

        self._state_locations = dict(final_state.state_locations)
        self._now_ns = result.end_ns
        self._pending_events.clear()
        self._pending_migrations.clear()
        self._pending_interventions.clear()
        return result

    def _locations_at(
        self,
        timestamp_ns: int,
        records: Tuple[EventRecord, ...],
    ) -> dict[str, str]:
        locations = dict(self._state_locations)
        record_by_id = {record.event.event_id: record for record in records}
        completed = []
        for event_id, plan in self._pending_migrations.items():
            record = record_by_id[event_id]
            if record.end_ns <= timestamp_ns:
                completed.append((record.end_ns, event_id, plan))
        for _, _, plan in sorted(completed):
            locations[plan.state_id] = plan.target_site_id
        return locations

    def _visible_state(
        self,
        *,
        timestamp_ns: int,
        temporal_snapshot: Optional[VisibleStateSnapshot],
        records: Tuple[EventRecord, ...],
        locations: Mapping[str, str],
    ) -> VisibleDatacenterState:
        usages = {}
        active_ids: Tuple[str, ...] = ()
        pending_ids = tuple(sorted(self._pending_events))
        completed_ids: Tuple[str, ...] = ()
        if temporal_snapshot is not None:
            usages = {
                resource.resource_id: resource
                for resource in temporal_snapshot.resources
            }
            active_ids = temporal_snapshot.active_event_ids
            pending_ids = temporal_snapshot.pending_event_ids
            completed_ids = temporal_snapshot.completed_event_ids

        active_failures = {
            record.event.location
            for record in records
            if record.event.kind is EventKind.FAILURE
            and record.start_ns <= timestamp_ns < record.end_ns
        }
        active_operational_records = tuple(
            record
            for record in records
            if record.event.kind is not EventKind.FAILURE
            and record.start_ns <= timestamp_ns < record.end_ns
        )

        def operational_usage(resource_id: str) -> Number:
            used: Number = 0
            for record in active_operational_records:
                for demand in record.event.demands:
                    if demand.resource_id == resource_id:
                        used += demand.amount
            return used

        sites = []
        for site_id in sorted(self._sites):
            site = self._sites[site_id]
            power_usage = usages.get(_resource_id(site_id, "power"))
            healthy = site_id not in active_failures
            active = site_id in self._active_site_ids
            allocated_power = (
                float(site.base_power_w)
                + (0 if power_usage is None else float(power_usage.used))
                if active
                else 0
            )
            sites.append(
                VisibleSiteState(
                    site_id=site_id,
                    accelerator_type=site.accelerator_type,
                    active=active,
                    healthy=healthy,
                    accelerator_count=site.accelerator_count,
                    effective_accelerators=site.effective_accelerators(
                        self._power_caps[site_id]
                    ),
                    busy_accelerators=operational_usage(
                        _resource_id(site_id, "accelerators")
                    ),
                    accelerator_flops_per_second=(
                        site.accelerator_flops_per_second
                    ),
                    collective_bandwidth_bytes_per_second=(
                        site.collective_bandwidth_bytes_per_second
                    ),
                    state_transfer_bandwidth_bytes_per_second=(
                        site.state_transfer_bandwidth_bytes_per_second
                    ),
                    checkpoint_bandwidth_bytes_per_second=(
                        site.checkpoint_bandwidth_bytes_per_second
                    ),
                    base_power_w=site.base_power_w,
                    accelerator_power_w=site.accelerator_power_w,
                    power_cap_w=self._power_caps[site_id],
                    cooling_capacity_w=site.cooling_capacity_w,
                    grid_import_limit_w=site.grid_import_limit_w,
                    allocated_power_w=allocated_power,
                    owned_state_ids=tuple(
                        sorted(
                            state_id
                            for state_id, owner in locations.items()
                            if owner == site_id
                        )
                    ),
                )
            )

        links = []
        for link_id in sorted(self._links):
            link = self._links[link_id]
            usage = usages.get(_link_resource_id(link_id))
            links.append(
                VisibleLinkState(
                    link_id=link_id,
                    site_a=link.site_a,
                    site_b=link.site_b,
                    available=(
                        link.available
                        and link.site_a not in active_failures
                        and link.site_b not in active_failures
                    ),
                    bandwidth_bytes_per_second=link.bandwidth_bytes_per_second,
                    used_bandwidth_bytes_per_second=(
                        0 if usage is None else usage.used
                    ),
                    latency_ns=link.latency_ns,
                    active_event_ids=(
                        () if usage is None else usage.active_event_ids
                    ),
                )
            )

        return VisibleDatacenterState(
            timestamp_ns=timestamp_ns,
            sites=tuple(sites),
            links=tuple(links),
            membership=tuple(sorted(self._active_site_ids)),
            parallelism=self._parallelism,
            sync_cadence=self._sync_cadence,
            configuration=freeze_metadata(self._configuration),
            state_locations=tuple(sorted(locations.items())),
            queued_event_ids=pending_ids,
            active_event_ids=active_ids,
            completed_event_ids=completed_ids,
        )

    def _metrics(
        self,
        timeline: TimelineResult,
        snapshots: Tuple[VisibleDatacenterState, ...],
        resources: Tuple[Resource, ...],
    ) -> DatacenterMetrics:
        compute_flops: Number = 0
        inter_site_collective_bytes: Number = 0
        state_transfer_bytes: Number = 0
        checkpoint_bytes: Number = 0
        accelerator_time_ns: Number = 0
        incremental_energy_j = 0.0

        for record in timeline.trace.events:
            metadata = dict(record.event.metadata)
            if record.event.kind is EventKind.COMPUTE:
                compute_flops += metadata["work_flops"]  # type: ignore[operator]
                accelerator_time_ns += (
                    metadata["accelerator_count"] * record.event.duration_ns  # type: ignore[operator]
                )
            elif (
                record.event.kind is EventKind.COLLECTIVE
                and metadata.get("scope") == "inter_site"
            ):
                inter_site_collective_bytes += metadata["size_bytes"]  # type: ignore[operator]
            elif record.event.kind is EventKind.STATE_TRANSFER:
                state_transfer_bytes += metadata["size_bytes"]  # type: ignore[operator]
            elif record.event.kind is EventKind.CHECKPOINT:
                checkpoint_bytes += metadata["size_bytes"]  # type: ignore[operator]

            for demand in record.event.demands:
                if demand.resource_id.endswith(":power"):
                    incremental_energy_j += (
                        float(demand.amount) * record.event.duration_ns / 1e9
                    )

        elapsed_seconds = timeline.elapsed_ns / 1e9
        base_energy_j = sum(
            float(site.base_power_w) * elapsed_seconds
            for site_id, site in self._sites.items()
            if site_id in self._active_site_ids
        )
        peak_power = max(
            (
                sum(float(site.allocated_power_w) for site in snapshot.sites)
                for snapshot in snapshots
            ),
            default=0.0,
        )

        capacity_time: dict[str, Number] = {
            resource.resource_id: 0 for resource in resources
        }
        unavailable_capacity_time: dict[str, Number] = {
            resource.resource_id: 0 for resource in resources
        }
        for record in timeline.trace.events:
            for demand in record.event.demands:
                integral = demand.amount * record.event.duration_ns
                if record.event.kind is EventKind.FAILURE:
                    unavailable_capacity_time[demand.resource_id] += integral
                else:
                    capacity_time[demand.resource_id] += integral
        resource_utilization = []
        for resource in resources:
            denominator = float(resource.capacity) * timeline.elapsed_ns
            integral = capacity_time[resource.resource_id]
            utilization = 0.0 if denominator == 0 else float(integral) / denominator
            resource_utilization.append(
                ResourceUtilization(
                    resource_id=resource.resource_id,
                    capacity=resource.capacity,
                    unit=resource.unit,
                    capacity_time=integral,
                    unavailable_capacity_time=(
                        unavailable_capacity_time[resource.resource_id]
                    ),
                    utilization=utilization,
                )
            )

        return DatacenterMetrics(
            compute_flops=compute_flops,
            inter_site_collective_bytes=inter_site_collective_bytes,
            state_transfer_bytes=state_transfer_bytes,
            checkpoint_bytes=checkpoint_bytes,
            accelerator_time_ns=accelerator_time_ns,
            modeled_base_and_compute_energy_j=(
                base_energy_j + incremental_energy_j
            ),
            peak_allocated_power_w=peak_power,
            resource_utilization=tuple(resource_utilization),
        )


__all__ = [
    "ConfigurationIntervention",
    "DatacenterMetrics",
    "DatacenterResult",
    "DatacenterTrace",
    "Intervention",
    "InterventionRecord",
    "MembershipIntervention",
    "MigrationIntervention",
    "ParallelismConfig",
    "ParallelismIntervention",
    "Policy",
    "PowerCapIntervention",
    "ResourceUtilization",
    "Site",
    "SyncCadence",
    "SyncCadenceIntervention",
    "VisibleDatacenterState",
    "VisibleLinkState",
    "VisibleSiteState",
    "VirtualDatacenter",
    "WANLink",
]
