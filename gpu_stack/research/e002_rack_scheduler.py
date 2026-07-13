"""Focused dependency-safe scheduler for the E002-PW3 rack experiment.

This module is deliberately not a general workflow engine.  It schedules one
batch of state-flow operations that are already ready in the physical PW3
runtime.  Legality comes from explicit predecessor, generation, and deadline
commitments; the policy may change release time only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
import random
from typing import Any, Mapping, Sequence


POLICIES = (
    "synchronized",
    "random_jitter",
    "throughput_pacing",
    "static_cohorts",
    "telemetry_feedback",
)


@dataclass(frozen=True)
class VisibleRackState:
    """Only measurements available to a deployable online controller."""

    reference_time_ns: int
    rack_power_w: float | None
    rack_ramp_w_per_s: float | None
    storage_write_bytes_per_s: float | None
    storage_queue_depth: float | None
    clock_uncertainty_ns: int
    quality: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OperationRequest:
    event_id: str
    job_id: int
    rank_ids: tuple[int, ...]
    kind: str
    checkpoint_epoch: int
    predecessor_ids: tuple[str, ...]
    state_generation: str
    earliest_start_ns: int
    deadline_ns: int
    predicted_duration_ns: int
    predicted_power_delta_w: float
    predicted_storage_bytes_per_s: float
    bytes: int

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OperationRequest":
        return cls(
            event_id=str(value["event_id"]),
            job_id=int(value["job_id"]),
            rank_ids=tuple(int(item) for item in value["rank_ids"]),
            kind=str(value["kind"]),
            checkpoint_epoch=int(value["checkpoint_epoch"]),
            predecessor_ids=tuple(
                str(item) for item in value.get("predecessor_ids", ())
            ),
            state_generation=str(value["state_generation"]),
            earliest_start_ns=int(value["earliest_start_ns"]),
            deadline_ns=int(value["deadline_ns"]),
            predicted_duration_ns=max(1, int(value["predicted_duration_ns"])),
            predicted_power_delta_w=float(value["predicted_power_delta_w"]),
            predicted_storage_bytes_per_s=float(
                value["predicted_storage_bytes_per_s"]
            ),
            bytes=int(value["bytes"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OperationDecision:
    event_id: str
    policy_id: str
    scheduled_release_ns: int
    delay_ns: int
    slot_index: int
    cohort_index: int
    abstained: bool
    reason: str
    objective: Mapping[str, float | int | None]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    job_id: int
    rank_ids: tuple[int, ...]
    kind: str
    checkpoint_epoch: int
    predecessor_ids: tuple[str, ...]
    state_generation: str
    earliest_start_ns: int
    scheduled_release_ns: int
    actual_start_ns: int
    actual_end_ns: int
    deadline_ns: int
    bytes: int
    outcome: str
    policy_id: str
    decision_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StateFlowLedger:
    """Enforce the scientific DAG invariant for completed state flows."""

    def __init__(self) -> None:
        self._events: dict[str, EventRecord] = {}

    def record(self, event: EventRecord) -> None:
        if event.event_id in self._events:
            raise ValueError(f"duplicate state-flow event {event.event_id}")
        missing = [
            predecessor
            for predecessor in event.predecessor_ids
            if predecessor not in self._events
            or self._events[predecessor].outcome != "completed"
        ]
        if missing:
            raise ValueError(
                f"event {event.event_id} has incomplete predecessors {missing}"
            )
        if event.actual_start_ns < event.earliest_start_ns:
            raise ValueError(f"event {event.event_id} started before release")
        if event.actual_start_ns < event.scheduled_release_ns:
            raise ValueError(f"event {event.event_id} violated scheduled release")
        if event.actual_end_ns < event.actual_start_ns:
            raise ValueError(f"event {event.event_id} has negative duration")
        if event.actual_end_ns > event.deadline_ns:
            raise ValueError(f"event {event.event_id} missed its deadline")
        self._events[event.event_id] = event

    def completed(self, event_id: str) -> bool:
        event = self._events.get(event_id)
        return event is not None and event.outcome == "completed"

    def generation_events(self, generation: str) -> tuple[EventRecord, ...]:
        return tuple(
            event
            for event in self._events.values()
            if event.state_generation == generation
        )

    def to_list(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self._events.values()]


def _stable_seed(*parts: object) -> int:
    material = ":".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _allowed_delay_ns(request: OperationRequest) -> int:
    return max(
        0,
        request.deadline_ns
        - request.earliest_start_ns
        - request.predicted_duration_ns,
    )


def _candidate_slots(
    request: OperationRequest,
    *,
    slot_ns: int,
    maximum_delay_ns: int,
) -> tuple[int, ...]:
    limit = min(_allowed_delay_ns(request), maximum_delay_ns)
    if limit <= 0:
        return (0,)
    candidates = list(range(0, limit + 1, slot_ns))
    if candidates[-1] != limit:
        candidates.append(limit)
    return tuple(candidates)


def _overlap(left_start: int, left_end: int, right_start: int, right_end: int) -> int:
    return max(0, min(left_end, right_end) - max(left_start, right_start))


def _scheduled_load(
    start_ns: int,
    end_ns: int,
    scheduled: Sequence[tuple[int, int, OperationRequest]],
) -> tuple[float, float, int]:
    power = 0.0
    storage = 0.0
    overlap_count = 0
    for other_start, other_end, other in scheduled:
        overlap = _overlap(start_ns, end_ns, other_start, other_end)
        if overlap <= 0:
            continue
        fraction = overlap / max(1, min(end_ns - start_ns, other_end - other_start))
        power += max(0.0, other.predicted_power_delta_w) * fraction
        storage += max(0.0, other.predicted_storage_bytes_per_s) * fraction
        overlap_count += 1
    return power, storage, overlap_count


def _telemetry_cost(
    request: OperationRequest,
    delay_ns: int,
    *,
    visible: VisibleRackState,
    scheduled: Sequence[tuple[int, int, OperationRequest]],
) -> tuple[float, dict[str, float | int | None]]:
    start = request.earliest_start_ns + delay_ns
    end = start + request.predicted_duration_ns
    overlapping_power, overlapping_storage, overlap_count = _scheduled_load(
        start,
        end,
        scheduled,
    )
    own_power = max(0.0, request.predicted_power_delta_w)
    own_storage = max(0.0, request.predicted_storage_bytes_per_s)
    base_power = max(1.0, float(visible.rack_power_w or 0.0))
    base_storage = max(
        1.0,
        float(visible.storage_write_bytes_per_s or 0.0),
        own_storage,
    )
    projected_power_fraction = (own_power + overlapping_power) / base_power
    projected_storage_fraction = (
        own_storage + overlapping_storage
    ) / base_storage
    current_positive_ramp = max(0.0, float(visible.rack_ramp_w_per_s or 0.0))
    early_ramp_penalty = current_positive_ramp / base_power / (1.0 + delay_ns / 1e9)
    queue_penalty = max(0.0, float(visible.storage_queue_depth or 0.0)) / (
        1.0 + delay_ns / 1e9
    )
    delay_fraction = delay_ns / max(1, _allowed_delay_ns(request))
    cost = (
        0.42 * projected_power_fraction
        + 0.34 * projected_storage_fraction
        + 0.12 * early_ramp_penalty
        + 0.08 * queue_penalty
        + 0.04 * delay_fraction
    )
    return cost, {
        "projected_power_fraction": projected_power_fraction,
        "projected_storage_fraction": projected_storage_fraction,
        "positive_ramp_penalty": early_ramp_penalty,
        "storage_queue_penalty": queue_penalty,
        "delay_fraction": delay_fraction,
        "overlap_count": overlap_count,
        "cost": cost,
    }


def schedule_state_flow_batch(
    policy_id: str,
    requests: Sequence[OperationRequest],
    *,
    visible: VisibleRackState,
    block_id: str,
    slot_ns: int,
    maximum_delay_ns: int,
    random_seed: int,
    maximum_clock_uncertainty_ns: int,
) -> tuple[OperationDecision, ...]:
    """Schedule one ready batch without changing operation contents or order."""

    if policy_id not in POLICIES:
        raise ValueError(f"unknown PW3 policy {policy_id!r}")
    if not requests:
        return ()
    if slot_ns <= 0:
        raise ValueError("slot_ns must be positive")
    event_ids = [request.event_id for request in requests]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("state-flow request IDs must be unique")
    generations = {request.state_generation for request in requests}
    kinds = {request.kind for request in requests}
    epochs = {request.checkpoint_epoch for request in requests}
    if len(kinds) != 1 or len(epochs) != 1:
        raise ValueError("one scheduling batch must contain one kind and epoch")

    ordered = sorted(
        requests,
        key=lambda request: (request.deadline_ns, request.job_id, request.event_id),
    )
    job_count = len({request.job_id for request in ordered})
    scheduled: list[tuple[int, int, OperationRequest]] = []
    decisions: list[OperationDecision] = []

    clock_invalid = visible.clock_uncertainty_ns > maximum_clock_uncertainty_ns
    telemetry_invalid = visible.quality not in {"good", "degraded"}
    for request in ordered:
        candidates = _candidate_slots(
            request,
            slot_ns=slot_ns,
            maximum_delay_ns=maximum_delay_ns,
        )
        abstained = False
        reason = ""
        objective: dict[str, float | int | None] = {}

        if policy_id == "synchronized":
            delay = 0
            reason = "earliest dependency-safe release"
        elif policy_id == "random_jitter":
            rng = random.Random(
                _stable_seed(
                    random_seed,
                    block_id,
                    request.kind,
                    request.checkpoint_epoch,
                    request.job_id,
                )
            )
            delay = candidates[rng.randrange(len(candidates))]
            reason = "seeded legal jitter"
        elif policy_id == "static_cohorts":
            cohort = (
                request.job_id + request.checkpoint_epoch
            ) % max(1, job_count)
            target = cohort * slot_ns
            delay = min(candidates, key=lambda candidate: (abs(candidate - target), candidate))
            reason = "rotating dependency-safe cohort"
            objective["target_cohort"] = cohort
        elif policy_id == "throughput_pacing":
            best: tuple[float, int, dict[str, float | int | None]] | None = None
            for candidate in candidates:
                start = request.earliest_start_ns + candidate
                end = start + request.predicted_duration_ns
                _, storage, overlap_count = _scheduled_load(start, end, scheduled)
                base = max(
                    1.0,
                    float(visible.storage_write_bytes_per_s or 0.0),
                    request.predicted_storage_bytes_per_s,
                )
                storage_fraction = (
                    request.predicted_storage_bytes_per_s + storage
                ) / base
                delay_fraction = candidate / max(1, _allowed_delay_ns(request))
                cost = storage_fraction + 0.02 * delay_fraction
                detail: dict[str, float | int | None] = {
                    "projected_storage_fraction": storage_fraction,
                    "delay_fraction": delay_fraction,
                    "overlap_count": overlap_count,
                    "cost": cost,
                }
                option = (cost, candidate, detail)
                if best is None or option[:2] < best[:2]:
                    best = option
            assert best is not None
            _, delay, objective = best
            reason = "storage-queue-only legal slot"
        else:
            if clock_invalid or telemetry_invalid:
                delay = 0
                abstained = True
                reason = (
                    "feedback abstained: clock uncertainty"
                    if clock_invalid
                    else "feedback abstained: telemetry quality"
                )
            else:
                best_feedback: (
                    tuple[float, int, dict[str, float | int | None]] | None
                ) = None
                for candidate in candidates:
                    cost, detail = _telemetry_cost(
                        request,
                        candidate,
                        visible=visible,
                        scheduled=scheduled,
                    )
                    option = (cost, candidate, detail)
                    if best_feedback is None or option[:2] < best_feedback[:2]:
                        best_feedback = option
                assert best_feedback is not None
                _, delay, objective = best_feedback
                reason = "minimum visible rack-ramp and storage objective"

        if delay not in candidates:
            raise AssertionError("scheduler selected a non-candidate delay")
        release = request.earliest_start_ns + delay
        end = release + request.predicted_duration_ns
        if end > request.deadline_ns:
            raise ValueError(f"decision for {request.event_id} exceeds deadline")
        scheduled.append((release, end, request))
        slot_index = int(math.floor(delay / slot_ns))
        cohort_index = (
            request.job_id + request.checkpoint_epoch
        ) % max(1, job_count)
        objective = dict(objective)
        objective["generation_count_in_batch"] = len(generations)
        decisions.append(
            OperationDecision(
                event_id=request.event_id,
                policy_id=policy_id,
                scheduled_release_ns=release,
                delay_ns=delay,
                slot_index=slot_index,
                cohort_index=cohort_index,
                abstained=abstained,
                reason=reason,
                objective=objective,
            )
        )

    by_event = {decision.event_id: decision for decision in decisions}
    return tuple(by_event[event_id] for event_id in event_ids)


__all__ = [
    "EventRecord",
    "OperationDecision",
    "OperationRequest",
    "POLICIES",
    "StateFlowLedger",
    "VisibleRackState",
    "schedule_state_flow_batch",
]
