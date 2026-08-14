"""Tests for the deterministic research event timeline.

The timeline is a discrete-event scheduler: you declare resources with fixed
capacities (GPU slots, network bandwidth) and events that demand them, and it
computes when each event actually runs. These tests pin down the properties
the research code relies on: capacity is shared exactly, contention is broken
deterministically (priority, then event id — never submission order), fixed
exogenous events like outages hold their timestamps, and results serialize to
canonical JSON that round-trips.

All capacities, durations, and rates are synthetic fixtures chosen for exact
arithmetic.  They are not measurements or hardware specifications.
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from gpu_stack.research.temporal import (
    EventKind,
    EventTimeline,
    Resource,
    ResourceDemand,
    TemporalEvent,
    duration_ns_for_rate,
    seconds_to_ns,
)


def event(
    event_id: str,
    *,
    start: int = 0,
    duration: int = 10,
    amount: float = 1,
    priority: int = 0,
    fixed: bool = False,
) -> TemporalEvent:
    return TemporalEvent.create(
        event_id,
        EventKind.COMPUTE,
        start,
        duration,
        demands=(ResourceDemand("gpu", amount),),
        priority=priority,
        fixed_start=fixed,
        metadata={"fixture": True},
    )


def test_event_kinds_cover_e001_temporal_mechanisms():
    assert {kind.value for kind in EventKind} == {
        "compute",
        "collective",
        "state_transfer",
        "checkpoint",
        "failure",
        "recovery",
        "power",
        "cooling",
        "grid",
    }


def test_duration_conversion_is_exact_and_rounds_nonzero_work_up():
    assert seconds_to_ns(0) == 0
    assert seconds_to_ns(0.0000000001) == 1
    assert duration_ns_for_rate(1, 3) == 333_333_334
    assert duration_ns_for_rate(0, 3, latency_ns=7) == 7
    assert duration_ns_for_rate(20, 10, latency_ns=11) == 2_000_000_011


@pytest.mark.parametrize(
    ("call", "match"),
    [
        (lambda: seconds_to_ns(-1), "seconds"),
        (lambda: duration_ns_for_rate(1, 0), "rate_per_second"),
        (lambda: duration_ns_for_rate(float("inf"), 1), "amount"),
    ],
)
def test_duration_conversion_rejects_invalid_values(call, match):
    with pytest.raises(ValueError, match=match):
        call()


def test_event_normalizes_demands_and_metadata_for_canonical_artifacts():
    value = TemporalEvent.create(
        "ordered",
        EventKind.COLLECTIVE,
        0,
        1,
        demands=(ResourceDemand("z", 1), ResourceDemand("a", 2)),
        metadata={"z": 1, "a": "first"},
    )
    assert [item.resource_id for item in value.demands] == ["a", "z"]
    assert value.metadata == (("a", "first"), ("z", 1))
    assert list(value.to_dict()["metadata"]) == ["a", "z"]


def test_event_metadata_is_scalar_only_and_finite():
    with pytest.raises(TypeError, match="JSON scalar"):
        TemporalEvent.create(
            "nested",
            EventKind.COMPUTE,
            0,
            1,
            metadata={"hidden_state": [1, 2]},  # type: ignore[dict-item]
        )
    with pytest.raises(ValueError, match="finite"):
        TemporalEvent.create(
            "nan",
            EventKind.COMPUTE,
            0,
            1,
            metadata={"value": float("nan")},
        )


def test_timeline_shares_capacity_and_delays_only_infeasible_events():
    timeline = EventTimeline((Resource("gpu", 2, "slots"),))
    # Alphabetic order is a, b, c.  b cannot overlap a, but c can use a's
    # remaining half-slot and therefore still starts at zero.
    timeline.schedule(event("a", amount=1.5))
    timeline.schedule(event("b", amount=1))
    timeline.schedule(event("c", amount=0.5))

    result = timeline.run()

    assert result.trace.event("a").start_ns == 0
    assert result.trace.event("c").start_ns == 0
    assert result.trace.event("b").start_ns == 10
    assert result.trace.event("b").wait_ns == 10
    assert result.end_ns == 20


def test_timeline_priority_breaks_same_time_contention_deterministically():
    timeline = EventTimeline((Resource("gpu", 1, "slots"),))
    timeline.schedule(event("alphabetically-first", priority=0))
    timeline.schedule(event("urgent", priority=-5))

    result = timeline.run()

    assert result.trace.event("urgent").start_ns == 0
    assert result.trace.event("alphabetically-first").start_ns == 10


def test_allocation_does_not_depend_on_submission_order():
    resources = (Resource("gpu", 1, "slots"),)
    events = (event("a"), event("b"), event("c", start=5))
    forward = EventTimeline(resources)
    reverse = EventTimeline(resources)
    forward.schedule_all(events)
    reverse.schedule_all(reversed(events))

    assert forward.run().to_json() == reverse.run().to_json()


def test_fixed_event_keeps_exogenous_time_and_moves_overlapping_work():
    timeline = EventTimeline((Resource("gpu", 1, "slots"),))
    timeline.schedule(event("work", start=0, duration=10))
    timeline.schedule(
        TemporalEvent.create(
            "outage",
            EventKind.FAILURE,
            5,
            10,
            demands=(ResourceDemand("gpu", 1),),
            fixed_start=True,
        )
    )

    result = timeline.run()

    assert result.trace.event("outage").start_ns == 5
    assert result.trace.event("outage").end_ns == 15
    assert result.trace.event("work").start_ns == 15


def test_conflicting_fixed_observations_are_rejected_not_shifted():
    timeline = EventTimeline((Resource("gpu", 1, "slots"),))
    timeline.schedule(event("fixed-a", duration=10, fixed=True))
    timeline.schedule(event("fixed-b", start=5, duration=10, fixed=True))

    with pytest.raises(ValueError, match="fixed event"):
        timeline.run()


def test_multi_resource_event_waits_until_every_demand_is_available():
    timeline = EventTimeline(
        (
            Resource("gpu", 1, "slots"),
            Resource("network", 10, "bytes_per_second"),
        )
    )
    timeline.schedule(
        TemporalEvent.create(
            "network-first",
            EventKind.STATE_TRANSFER,
            0,
            20,
            demands=(ResourceDemand("network", 10),),
            priority=-1,
        )
    )
    timeline.schedule(
        TemporalEvent.create(
            "both",
            EventKind.COLLECTIVE,
            0,
            5,
            demands=(
                ResourceDemand("gpu", 1),
                ResourceDemand("network", 10),
            ),
        )
    )

    result = timeline.run()

    assert result.trace.event("both").start_ns == 20
    assert result.trace.event("both").end_ns == 25


def test_snapshots_expose_immutable_transition_state_and_resource_usage():
    timeline = EventTimeline((Resource("gpu", 2, "slots"),))
    timeline.schedule(event("a", duration=10, amount=1))
    timeline.schedule(event("b", start=5, duration=10, amount=1))

    result = timeline.run()
    at_five = next(item for item in result.snapshots if item.timestamp_ns == 5)

    assert at_five.active_event_ids == ("a", "b")
    assert at_five.resource("gpu").used == 2
    assert at_five.resource("gpu").available == 0
    with pytest.raises(FrozenInstanceError):
        at_five.timestamp_ns = 99  # type: ignore[misc]
    with pytest.raises(AttributeError):
        at_five.active_event_ids.append("mutate")  # type: ignore[attr-defined]


def test_zero_duration_event_is_completed_at_its_transition():
    timeline = EventTimeline((Resource("gpu", 1, "slots"),), start_ns=7)
    timeline.schedule(
        TemporalEvent.create("instant", EventKind.RECOVERY, 7, 0)
    )

    result = timeline.run()

    assert result.start_ns == result.end_ns == 7
    assert result.snapshots[0].active_event_ids == ()
    assert result.snapshots[0].completed_event_ids == ("instant",)


def test_schedule_rejects_unknown_and_over_capacity_demands():
    timeline = EventTimeline((Resource("gpu", 1, "slots"),))
    with pytest.raises(ValueError, match="unknown resource"):
        timeline.schedule(
            TemporalEvent.create(
                "unknown",
                EventKind.COMPUTE,
                0,
                1,
                demands=(ResourceDemand("missing", 1),),
            )
        )
    with pytest.raises(ValueError, match="exceeds capacity"):
        timeline.schedule(event("too-large", amount=2))


def test_schedule_all_is_atomic_when_one_event_is_invalid():
    timeline = EventTimeline((Resource("gpu", 1, "slots"),))
    valid = event("valid")
    invalid = TemporalEvent.create(
        "invalid",
        EventKind.COMPUTE,
        0,
        1,
        demands=(ResourceDemand("missing", 1),),
    )
    with pytest.raises(ValueError, match="unknown resource"):
        timeline.schedule_all((valid, invalid))
    assert timeline.events == ()


def test_result_serialization_is_canonical_and_json_round_trippable():
    timeline = EventTimeline((Resource("gpu", 1, "slots"),))
    timeline.schedule(event("work"))
    result = timeline.run()

    encoded = result.to_json()

    assert encoded == result.to_json()
    assert " " not in encoded
    decoded = json.loads(encoded)
    assert decoded["schema"] == "gpu-stack.temporal-result.v1"
    assert decoded["trace"]["events"][0]["event"]["event_id"] == "work"
    assert decoded["snapshots"][-1]["completed_event_ids"] == ["work"]


def test_empty_timeline_still_emits_visible_origin_snapshot():
    result = EventTimeline(
        (Resource("gpu", 0, "slots"),),
        start_ns=123,
    ).run()

    assert result.start_ns == result.end_ns == 123
    assert len(result.snapshots) == 1
    assert result.snapshots[0].resource("gpu").capacity == 0
