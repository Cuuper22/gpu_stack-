"""Tests for the mechanics-only multi-site virtual datacenter.

The ``VirtualDatacenter`` simulates training across sites joined by WAN
links: compute events occupy accelerators, collectives occupy fabric or WAN
bandwidth, outages take sites offline, power caps limit how many
accelerators can run, and a policy may intervene between decision epochs.
"Mechanics-only" means it models time, bytes, and watts — never loss or
convergence, and the artifact tests confirm those claims are excluded.

Every number in this file is a synthetic round-number fixture. The tests
establish simulation semantics, not claims about any real accelerator,
facility, or WAN. The semantics they pin: resources serialize honestly
(shared fabric and shared links slow overlapping work), failure traces are
fixed inputs that delay work rather than move, intervention batches apply
atomically or roll back entirely, a policy sees only a frozen observable
state and its choices take effect next epoch, accounting boundaries
(checkpoint vs. transfer vs. collective bytes) never blur, and serialized
results are canonical and independent of input ordering.
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from gpu_stack.research.multisite import (
    ConfigurationIntervention,
    MembershipIntervention,
    MigrationIntervention,
    ParallelismConfig,
    ParallelismIntervention,
    PowerCapIntervention,
    Site,
    SyncCadence,
    SyncCadenceIntervention,
    VirtualDatacenter,
    WANLink,
)
from gpu_stack.research.temporal import EventKind


def site_a() -> Site:
    return Site(
        site_id="a",
        accelerator_type="synthetic-a",
        accelerator_count=4,
        accelerator_flops_per_second=100,
        collective_bandwidth_bytes_per_second=100,
        state_transfer_bandwidth_bytes_per_second=100,
        checkpoint_bandwidth_bytes_per_second=50,
        base_power_w=100,
        accelerator_power_w=50,
        power_cap_w=300,
        cooling_capacity_w=500,
        grid_import_limit_w=500,
    )


def site_b() -> Site:
    return Site(
        site_id="b",
        accelerator_type="synthetic-b",
        accelerator_count=2,
        accelerator_flops_per_second=200,
        collective_bandwidth_bytes_per_second=200,
        state_transfer_bandwidth_bytes_per_second=100,
        checkpoint_bandwidth_bytes_per_second=100,
        base_power_w=100,
        accelerator_power_w=100,
        power_cap_w=300,
        cooling_capacity_w=500,
        grid_import_limit_w=500,
    )


def wan() -> WANLink:
    return WANLink(
        link_id="a-b",
        site_a="a",
        site_b="b",
        bandwidth_bytes_per_second=100,
        latency_ns=10,
    )


def two_site_dc(**kwargs) -> VirtualDatacenter:
    return VirtualDatacenter((site_a(), site_b()), (wan(),), **kwargs)


def test_site_power_envelope_derives_effective_accelerator_count():
    site = site_a()
    assert site.effective_accelerators() == 4
    assert site.effective_accelerators(200) == 2
    assert site.effective_accelerators(100) == 0
    with pytest.raises(ValueError, match="cover base_power"):
        site.effective_accelerators(99)
    with pytest.raises(ValueError, match="cooling/grid"):
        site.validate_power_cap(501)


def test_topology_rejects_unknown_link_endpoint_and_ambiguous_paths():
    bad_link = WANLink("bad", "a", "missing", 1, 0)
    with pytest.raises(ValueError, match="unknown site"):
        VirtualDatacenter((site_a(),), (bad_link,))

    duplicate_path = WANLink("a-b-2", "a", "b", 50, 20)
    dc = VirtualDatacenter((site_a(), site_b()), (wan(), duplicate_path))
    with pytest.raises(ValueError, match="multiple WAN links"):
        dc.schedule_state_transfer("copy", "state", "a", "b", 10)


def test_compute_uses_explicit_rate_power_and_shared_resources():
    dc = VirtualDatacenter((site_a(),), (), active_site_ids=("a",))
    dc.schedule_compute("step", "a", work_flops=400, accelerator_count=2)

    result = dc.run()
    record = result.trace.timeline.event("step")

    assert record.start_ns == 0
    assert record.end_ns == 2_000_000_000
    assert result.metrics.compute_flops == 400
    assert result.metrics.accelerator_time_ns == 4_000_000_000
    # 100 W base for 2 seconds + 100 W accelerator demand for 2 seconds.
    assert result.metrics.modeled_base_and_compute_energy_j == 400
    assert result.metrics.peak_allocated_power_w == 200
    accelerator_resource = next(
        item
        for item in result.metrics.resource_utilization
        if item.resource_id == "site:a:accelerators"
    )
    assert accelerator_resource.utilization == 0.5
    assert result.final_state.site("a").busy_accelerators == 0


def test_full_bandwidth_local_collectives_serialize_on_fabric():
    dc = VirtualDatacenter((site_a(),), ())
    dc.schedule_collective("collective-a", 100, site_id="a")
    dc.schedule_collective("collective-b", 100, site_id="a")

    result = dc.run()

    assert result.trace.timeline.event("collective-a").start_ns == 0
    assert result.trace.timeline.event("collective-b").start_ns == 1_000_000_000
    assert result.end_ns == 2_000_000_000
    assert result.metrics.inter_site_collective_bytes == 0


def test_partial_wan_reservations_share_link_and_report_inter_site_bytes():
    dc = two_site_dc()
    for event_id in ("wan-a", "wan-b"):
        dc.schedule_collective(
            event_id,
            100,
            link_id="a-b",
            bandwidth_bytes_per_second=50,
        )

    result = dc.run()

    first = result.trace.timeline.event("wan-a")
    second = result.trace.timeline.event("wan-b")
    assert first.start_ns == second.start_ns == 0
    assert first.end_ns == second.end_ns == 2_000_000_010
    assert result.metrics.inter_site_collective_bytes == 200
    at_zero = result.snapshots[0]
    assert at_zero.link("a-b").used_bandwidth_bytes_per_second == 100
    assert at_zero.link("a-b").active_event_ids == ("wan-a", "wan-b")


def test_fixed_site_outage_delays_work_without_moving_failure_trace():
    dc = two_site_dc()
    dc.schedule_compute("step", "a", work_flops=100, accelerator_count=1)
    dc.schedule_site_outage(
        "site-a-failure",
        "a",
        failure_start_ns=500_000_000,
        recovery_ns=1_500_000_000,
        cause="synthetic interruption",
    )

    result = dc.run()

    failure = result.trace.timeline.event("site-a-failure")
    recovery = result.trace.timeline.event("site-a-failure:recovery")
    work = result.trace.timeline.event("step")
    assert (failure.start_ns, failure.end_ns) == (500_000_000, 1_500_000_000)
    assert recovery.start_ns == recovery.end_ns == 1_500_000_000
    assert work.start_ns == 1_500_000_000
    during = next(
        state for state in result.snapshots if state.timestamp_ns == 500_000_000
    )
    after = next(
        state for state in result.snapshots if state.timestamp_ns == 1_500_000_000
    )
    assert not during.site("a").healthy
    assert during.site("a").busy_accelerators == 0
    assert not during.link("a-b").available
    assert after.site("a").healthy
    assert after.link("a-b").available
    accelerator_resource = next(
        item
        for item in result.metrics.resource_utilization
        if item.resource_id == "site:a:accelerators"
    )
    assert accelerator_resource.unavailable_capacity_time == 4_000_000_000


def test_facility_trace_is_fixed_and_contends_with_compute_grid_demand():
    dc = VirtualDatacenter((site_a(),), ())
    dc.schedule_compute("step", "a", work_flops=100, accelerator_count=1)
    dc.schedule_facility_event(
        "grid-load",
        "a",
        EventKind.GRID,
        duration_ns=2_000_000_000,
        demand_w=375,
    )

    result = dc.run()

    assert result.trace.timeline.event("grid-load").start_ns == 0
    assert result.trace.timeline.event("step").start_ns == 2_000_000_000
    assert result.end_ns == 3_000_000_000


def test_migration_changes_placement_only_after_transfer_completion():
    dc = two_site_dc(state_locations={"optimizer": "a"})
    dc.apply_interventions(
        (
            MigrationIntervention(
                "optimizer",
                "a",
                "b",
                size_bytes=100,
                reason="rebalance",
            ),
        )
    )

    result = dc.run()
    transfer = result.trace.records[0]

    assert result.snapshots[0].location_of("optimizer") == "a"
    assert result.final_state.location_of("optimizer") == "b"
    assert transfer.event.kind is EventKind.STATE_TRANSFER
    assert dict(transfer.event.metadata)["migration"] is True
    assert result.metrics.state_transfer_bytes == 100
    assert result.trace.interventions[0].intervention.reason == "rebalance"


def test_invalid_intervention_batch_rolls_back_every_prior_action():
    dc = two_site_dc()
    with pytest.raises(ValueError, match="cooling/grid"):
        dc.apply_interventions(
            (
                MembershipIntervention("b", False),
                PowerCapIntervention("a", 999),
            )
        )

    state = dc.observe()
    assert state.membership == ("a", "b")
    assert state.site("a").power_cap_w == 300
    assert dc.run().trace.interventions == ()


def test_policy_receives_only_frozen_observable_state_and_changes_next_epoch():
    class Controller:
        seen = None

        def decide(self, state):
            self.seen = state
            assert not hasattr(state, "_pending_events")
            return (
                ParallelismIntervention(
                    ParallelismConfig(data_parallel=2),
                    reason="two sites",
                ),
                SyncCadenceIntervention(
                    SyncCadence(local_steps=4, topology="ring"),
                ),
                ConfigurationIntervention.create({"optimizer": "adamw"}),
                PowerCapIntervention("a", 200),
                MembershipIntervention("b", False),
            )

    controller = Controller()
    dc = two_site_dc()
    result = dc.run(policy=controller)

    assert controller.seen == result.decision_state
    assert result.decision_state.membership == ("a", "b")
    assert result.final_state.membership == ("a",)
    assert result.final_state.parallelism.data_parallel == 2
    assert result.final_state.sync_cadence.local_steps == 4
    assert dict(result.final_state.configuration) == {"optimizer": "adamw"}
    assert result.final_state.site("a").effective_accelerators == 2
    assert [item.sequence for item in result.trace.interventions] == [1, 2, 3, 4, 5]
    with pytest.raises(FrozenInstanceError):
        controller.seen.timestamp_ns = 12


def test_policy_cannot_observe_events_queued_for_the_next_epoch():
    class Controller:
        def decide(self, state):
            raise AssertionError("policy must not receive a future event trace")

    dc = VirtualDatacenter((site_a(),), ())
    dc.schedule_compute("future-step", "a", work_flops=100, accelerator_count=1)

    with pytest.raises(ValueError, match="before the next epoch is queued"):
        dc.apply_policy(Controller())


def test_membership_controls_admission_of_new_work():
    dc = two_site_dc(active_site_ids=("a",))
    with pytest.raises(ValueError, match="not an active member"):
        dc.schedule_compute("b-step", "b", work_flops=1, accelerator_count=1)
    dc.apply_interventions((MembershipIntervention("b", True),))
    dc.schedule_compute("b-step", "b", work_flops=200, accelerator_count=1)
    assert dc.run().metrics.compute_flops == 200


def test_power_cap_can_make_a_queued_unreshaped_plan_explicitly_invalid():
    dc = VirtualDatacenter((site_a(),), ())
    dc.schedule_compute("too-wide", "a", work_flops=300, accelerator_count=3)
    dc.apply_interventions((PowerCapIntervention("a", 200),))

    with pytest.raises(ValueError, match="exceeds capacity"):
        dc.run()


def test_checkpoint_and_transfer_metrics_keep_accounting_boundaries_separate():
    dc = two_site_dc()
    dc.schedule_checkpoint("checkpoint", "a", size_bytes=100)
    dc.schedule_state_transfer("copy", "weights", "a", "b", size_bytes=100)

    result = dc.run()

    assert result.metrics.checkpoint_bytes == 100
    assert result.metrics.state_transfer_bytes == 100
    assert result.metrics.inter_site_collective_bytes == 0


def test_successive_runs_form_explicit_decision_epochs():
    dc = VirtualDatacenter((site_a(),), ())
    dc.schedule_compute("step-1", "a", work_flops=100, accelerator_count=1)
    first = dc.run()
    dc.schedule_compute("step-2", "a", work_flops=100, accelerator_count=1)
    second = dc.run()

    assert first.start_ns == 0
    assert first.end_ns == 1_000_000_000
    assert second.start_ns == 1_000_000_000
    assert second.end_ns == 2_000_000_000
    assert second.decision_state.queued_event_ids == ("step-2",)
    assert second.trace.timeline.event("step-2").start_ns == first.end_ns


def test_artifact_json_is_canonical_and_excludes_convergence_claims():
    dc = two_site_dc(configuration={"experiment": "e001"})
    dc.schedule_compute("step", "a", work_flops=100, accelerator_count=1)
    result = dc.run()

    encoded = result.to_json()
    payload = json.loads(encoded)

    assert encoded == result.to_json()
    assert " " not in encoded
    assert payload["schema"] == "gpu-stack.datacenter-result.v1"
    assert payload["metrics"]["compute_flops"] == 100
    assert "loss" not in payload["metrics"]
    assert "convergence" not in payload["metrics"]


def test_input_order_does_not_change_serialized_topology_or_trace():
    forward = VirtualDatacenter((site_a(), site_b()), (wan(),))
    reverse = VirtualDatacenter((site_b(), site_a()), (wan(),))
    for dc in (forward, reverse):
        dc.schedule_collective("sync", 100, link_id="a-b")

    assert forward.run().to_json() == reverse.run().to_json()
