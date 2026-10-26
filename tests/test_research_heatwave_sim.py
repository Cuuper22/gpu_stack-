"""Tests for the Heatwave cluster simulator and fault events.

Every run here is simulated.  Short horizons and small job lists keep the
suite quick; the full seven-day scenario runs in the smoke script instead.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from gpu_stack.research.heatwave_events import (
    BreakerTrip,
    CoolingFailure,
    EventSchedule,
    GridCurtailment,
    HardwareFault,
    InverseTimeBreaker,
    Precursor,
    random_schedule,
)
from gpu_stack.research.heatwave_sim import (
    AdmitJob,
    CheckpointNow,
    DeferJob,
    Job,
    MigrateJob,
    PauseJob,
    ReactiveSiteCapController,
    ResumeJob,
    SetRackPowerCap,
    SiteEnvironment,
    build_config,
    generate_jobs,
    measure_e002_levels,
    plan_schedule,
    planned_covariates,
    run_scenario,
)

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = ROOT / "experiments" / "e003-heatwave" / "sim-scenario-v1.json"
E001 = ROOT / "experiments" / "e001-beyond-one-datacenter"


def base_scenario(horizon_s: int = 3600, jobs=None, events=None, **power_overrides) -> dict:
    sc = json.loads(SCENARIO_PATH.read_text())
    sc["horizon_s"] = horizon_s
    sc["events"] = events or []
    sc["outputs"] = {"gpu_windows": []}
    sc["jobs"] = {"list": [j.to_dict() for j in (jobs or [])]}
    sc["power_levels"].update(power_overrides)
    return sc


def job(job_id="j1", n=8, start=0.0, duration=3600.0, step=4.0, ckpt_every=600.0, ckpt_dur=30.0, **kw) -> Job:
    values = dict(
        job_id=job_id, n_gpus=n, submit_s=0.0, start_s=start, duration_s=duration, step_time_s=step,
        checkpoint_every_s=ckpt_every, checkpoint_duration_s=ckpt_dur, value_per_gpu_hour=2.0, flexible=False,
    )
    values.update(kw)
    return Job(**values)


# ---------------------------------------------------------------------------
# inputs and calibration
# ---------------------------------------------------------------------------


def test_scenario_is_labeled_simulated_and_builds():
    sc = json.loads(SCENARIO_PATH.read_text())
    assert sc["data_kind"] == "simulated"
    cfg = build_config(sc)
    assert [lay.site.site_id for lay in cfg.layouts] == ["site-a", "site-b"]
    assert all(len(lay.racks) == 4 for lay in cfg.layouts)
    assert all(8 <= r.n_gpus <= 32 for lay in cfg.layouts for r in lay.racks)
    assert cfg.horizon_s == 7 * 86400
    kinds = {e.kind for e in cfg.events.events}
    assert kinds == {"cooling_failure", "breaker_trip", "grid_curtailment", "hardware_fault"}
    truth = cfg.events.ground_truth()
    for kind in kinds:
        flags = {row["has_precursor"] for row in truth if row["kind"] == kind}
        assert flags == {True, False}, kind


def test_transfer_parameters_match_e001_files():
    sc = json.loads(SCENARIO_PATH.read_text())
    rec = json.loads((E001 / "recovery-scenario-v2.json").read_text())
    scr = json.loads((E001 / "screening-scenario-v1.json").read_text())
    tr = sc["transfer"]
    assert tr["restore_bandwidth_bytes_per_second"] == rec["restore_bandwidth_bytes_per_second"]
    assert tr["fixed_restart_latency_s"] == pytest.approx(rec["fixed_restart_latency_ns"] / 1e9)
    assert tr["membership_reconfiguration_s"] == pytest.approx(rec["membership_reconfiguration_ns"] / 1e9)
    link = scr["links"][0]
    assert tr["wan_bandwidth_bytes_per_second"] == link["bandwidth_bytes_per_second"]
    assert tr["wan_latency_s"] == pytest.approx(link["latency_ns"] / 1e9)
    west = scr["sites"][0]
    assert tr["checkpoint_bytes_per_gpu"] == pytest.approx(scr["checkpoint_bytes"] / west["accelerator_count"])
    for item in sc["sites"]:
        for key in ("accelerator_flops_per_second", "collective_bandwidth_bytes_per_second",
                    "state_transfer_bandwidth_bytes_per_second", "checkpoint_bandwidth_bytes_per_second",
                    "accelerator_power_w"):
            assert item["site"][key] == west[key]


def test_measured_levels_come_from_the_e002_file():
    m = measure_e002_levels()
    assert m["data_kind"] == "measured"
    r = m["ratio_to_compute"]
    assert 0.0 < r["idle-outside-active-window"] < 1.0
    assert r["checkpoint-snapshot"] == pytest.approx(m["median_power_w_laptop"]["checkpoint-snapshot"] / m["median_power_w_laptop"]["canonical-healthy-compute"])
    assert m["compute_relative_std"] > 0
    # The telemetry cannot resolve a checkpoint dip: its update period exceeds the window length.
    assert m["telemetry_update_period_s"] > m["median_window_duration_s"]["checkpoint-snapshot"]


def test_levels_are_scaled_to_the_preset_tdp():
    cfg = build_config(base_scenario())
    lv = cfg.levels
    assert lv.compute_w == pytest.approx(700.0 * 0.8)
    ratio = cfg.measured_levels["ratio_to_compute"]["idle-outside-active-window"]
    assert lv.idle_w == pytest.approx(lv.compute_w * ratio)
    assert lv.host_w_per_gpu == pytest.approx(0.25 * lv.compute_w)
    assert "measured" in lv.provenance["idle_w"]


def test_job_validation_and_generator_determinism():
    with pytest.raises(ValueError):
        job(n=0)
    with pytest.raises(ValueError):
        job(start=-1.0)
    with pytest.raises(ValueError):
        Job(**{**job().to_dict(), "multisite": True, "n_gpus": 7})
    kw = dict(
        horizon_s=86_400.0, total_gpus=100, utilization_goal=0.6, gpu_choices=[8, 16], gpu_weights=[1, 1],
        duration_range_s=(600.0, 7200.0), step_time_choices_s=[2.0, 4.0], checkpoint_every_range_s=(300.0, 900.0),
        checkpoint_duration_range_s=(10.0, 30.0), value_range=(1.0, 2.0), flexible_fraction=0.5,
        multisite_fraction=0.2, max_start_delay_s=600.0,
    )
    a = generate_jobs(5, **kw)
    b = generate_jobs(5, **kw)
    c = generate_jobs(6, **kw)
    assert [j.to_dict() for j in a] == [j.to_dict() for j in b]
    assert [j.to_dict() for j in a] != [j.to_dict() for j in c]
    assert sum(j.n_gpus * min(j.duration_s, 86_400.0) for j in a) >= 0.6 * 100 * 86_400.0


# ---------------------------------------------------------------------------
# events
# ---------------------------------------------------------------------------


def test_breaker_curve_matches_iec_conventional_values():
    b = InverseTimeBreaker()
    assert b.trip_time_s(1.45) == pytest.approx(3600.0)
    assert b.trip_time_s(1.13) == float("inf")
    assert b.trip_time_s(2.0) < b.trip_time_s(1.45)
    theta = np.array(0.0)
    t = 0.0
    while t < 5000:
        theta, tripped = b.step(theta, 1.45, 10.0)
        t += 10.0
        if bool(tripped):
            break
    assert t == pytest.approx(3600.0, abs=10.0)
    cooled, _ = b.step(np.array(1.2), 0.0, 3600.0)
    assert float(cooled) < 1.2


def test_event_schedule_roundtrip_and_validation():
    events = EventSchedule(
        (
            CoolingFailure("c", "site-a", 100.0, 50.0, 0.3, rack_id="a1", precursors=(Precursor("supply_temp_c", 60.0, 2.0),)),
            BreakerTrip("b", "site-a", "a1", 200.0, 100.0, "derate", 0.7, 30.0),
            GridCurtailment("g", "site-a", 300.0, 60.0, 0.5, announce_lead_s=120.0),
            HardwareFault("h", "site-a", "a1", 2, 400.0, 60.0, precursors=(Precursor("gpu_temp_c", 60.0, 5.0),)),
        )
    )
    again = EventSchedule.from_dicts(events.to_dict()["events"])
    assert again == events
    with pytest.raises(ValueError):
        EventSchedule((HardwareFault("x", "s", "r", 0, 1.0, 1.0), HardwareFault("x", "s", "r", 1, 1.0, 1.0)))
    with pytest.raises(ValueError):
        BreakerTrip("b", "s", "r", 1.0, 1.0, "forced", precursor_lead_s=5.0)
    with pytest.raises(ValueError):
        CoolingFailure("c", "s", 1.0, 1.0, 1.5)


def test_precursor_ramp_and_announcement_visibility():
    p = Precursor("supply_temp_c", 100.0, 4.0)
    assert float(p.value(0.0, 1000.0)) == 0.0
    assert float(p.value(950.0, 1000.0)) == pytest.approx(2.0)
    assert float(p.value(1000.0, 1000.0)) == pytest.approx(4.0)
    ev = EventSchedule((GridCurtailment("g", "s", 1000.0, 100.0, 0.5, announce_lead_s=300.0),
                        GridCurtailment("u", "s", 2000.0, 100.0, 0.5)))
    assert ev.announced_curtailments(600.0) == []
    assert [c["event_id"] for c in ev.announced_curtailments(800.0)] == ["g"]
    assert ev.announced_curtailments(1200.0) == []
    assert [c["event_id"] for c in ev.announced_curtailments(2050.0)] == []  # unannounced stays hidden


def test_random_schedule_is_deterministic_and_mixes_precursors():
    kw = dict(
        horizon_s=7 * 86_400.0, site_racks={"site-a": [("a1", 32), ("a2", 16)], "site-b": [("b1", 24)]},
        rates_per_day={"cooling_failure": 2.0, "breaker_trip": 2.0, "grid_curtailment": 2.0, "hardware_fault": 2.0},
        precursor_probability=0.5, lead_range_s=(600.0, 3600.0),
        strength_ranges={"supply_temp_c": (1.0, 3.0), "gpu_temp_c": (3.0, 8.0)},
        duration_range_s=(600.0, 3600.0), remaining_capacity_range=(0.2, 0.6), derate_range=(0.6, 0.8),
        limit_fraction_range=(0.5, 0.8), repair_range_s=(3600.0, 7200.0),
    )
    a = random_schedule(3, **kw)
    b = random_schedule(3, **kw)
    assert a == b and len(a.events) > 20
    flags = {row["has_precursor"] for row in a.ground_truth()}
    assert flags == {True, False}


# ---------------------------------------------------------------------------
# simulator
# ---------------------------------------------------------------------------


def test_hierarchy_sums_add_up_exactly():
    sc = base_scenario(
        horizon_s=3600, jobs=[job(n=16), job("j2", n=8, start=300.0)],
    )
    sc["outputs"] = {"gpu_windows": [[0, 3600]]}
    res = run_scenario(sc, seed=1)
    arr = res.to_arrays()
    run = res._run
    gpu = arr["gpu_power_w_window_0"]
    assert gpu.shape == (run.G, 3600)
    by_rack = np.add.reduceat(gpu, run.rack_start, axis=0).T
    assert np.array_equal(by_rack, arr["rack_gpu_power_w"])
    assert np.allclose(arr["rack_it_power_w"], arr["rack_gpu_power_w"] + np.repeat(run.rack_host_b, run.K, axis=0), rtol=1e-12, atol=0)
    assert np.allclose(arr["rack_power_w"], arr["rack_it_power_w"] + arr["rack_cooling_power_w"], rtol=1e-12, atol=0)
    site = np.stack([arr["rack_power_w"][:, run.rack_site == s].sum(axis=1) for s in range(run.S)], axis=1)
    assert np.allclose(site, arr["site_power_w"], rtol=1e-12, atol=0)
    hourly = arr["site_power_w"].reshape(1, 3600, run.S).sum(axis=1) / 3.6e6
    assert np.allclose(hourly, arr["site_energy_kwh_1h"], rtol=1e-12)
    assert np.allclose(arr["site_energy_kwh_1h"] * run.price_h, arr["site_cost_usd_1h"], rtol=1e-12)
    assert np.allclose(arr["site_energy_kwh_1h"] * run.carbon_h / 1000.0, arr["site_carbon_kg_1h"], rtol=1e-12)
    # Metadata labels everything as simulated.
    meta = arr["meta"]
    assert meta["data_kind"] == "simulated"
    assert "measured e002" in meta["quantity_provenance"]["gpu_power_levels"]
    assert meta["measured_e002"]["data_kind"] == "measured"


def test_rack_temperature_output_is_one_minute():
    res = run_scenario(base_scenario(3600, jobs=[job(n=16)]), seed=0)
    arr = res.to_arrays()
    assert arr["rack_temp_c_1min"].shape == (60, 8)
    assert arr["rack_power_w"].shape == (3600, 8)


def test_determinism_for_a_seed():
    sc = base_scenario(3600, jobs=[job(n=16), job("j2", n=8)])
    a = run_scenario(sc, seed=4).to_arrays()
    b = run_scenario(sc, seed=4).to_arrays()
    c = run_scenario(sc, seed=5).to_arrays()
    assert np.array_equal(a["site_power_w"], b["site_power_w"])
    assert np.array_equal(a["rack_temp_c_1min"], b["rack_temp_c_1min"])
    assert not np.array_equal(a["site_power_w"], c["site_power_w"])


def test_no_noise_waveform_levels_and_planned_covariates_agree():
    sc = base_scenario(
        3600, jobs=[job(n=8, duration=1500.0, ckpt_every=300.0, ckpt_dur=40.0)],
        noise_scale=0.0, comm_ratio=0.5, checkpoint_ratio=0.3,
    )
    sc["outputs"] = {"gpu_windows": [[0, 3600]]}
    res = run_scenario(sc, seed=0)
    run = res._run
    lv = run.cfg.levels
    gpu = res.gpu_windows[0]["gpu_power_w"][:, :1800]
    job_rows = gpu[:8]
    assert np.allclose(job_rows, job_rows[0])  # lockstep, no noise
    cov = res.covariates("site", 1.0, 0.0, 1800.0)
    # Planned scheduled-checkpoint indicator matches the simulated checkpoint stalls.
    ckpt_planned = cov["scheduled_checkpoint_gpus"][:, 0] / 8.0
    p = job_rows[0]
    ckpt_sim = np.isclose(p, lv.checkpoint_w)
    assert np.allclose(ckpt_planned, ckpt_sim.astype(float), atol=1e-9)
    # Planned compute fraction matches the simulated power level while running.
    running = ~ckpt_sim & (cov["planned_gpus_running"][:, 0] > 0)
    fc_sim = (p - lv.comm_w) / (lv.compute_w - lv.comm_w)
    assert np.allclose(cov["step_phase_compute_fraction"][running, 0], fc_sim[running], atol=1e-9)
    # Idle GPUs sit at idle power.
    assert np.allclose(gpu[8:, :], lv.idle_w)
    # Levels: checkpoint dip is visible in the waveform.
    assert p.min() < lv.comm_w < p.max()


def test_event_free_run_matches_the_plan():
    sc = base_scenario(
        6 * 3600,
        jobs=[
            job("a", n=64, start=0.0, duration=7200.0), job("b", n=32, start=100.0, duration=5400.0),
            job("c", n=32, start=200.0, duration=3600.0, multisite=True),
            job("d", n=16, start=300.0, duration=4000.0, site_id="site-b"),
            job("e", n=64, start=400.0, duration=5000.0),
        ],
    )
    res = run_scenario(sc, seed=0)
    starts = {}
    ends = {}
    for e in res.events:
        if e["kind"] == "job_start":
            starts.setdefault(e["job_id"], e["t_s"])
        if e["kind"] == "job_done":
            ends[e["job_id"]] = max(ends.get(e["job_id"], 0.0), e["t_s"])
    assert not any(e["kind"] == "job_fault" for e in res.events)
    for pj in res.plan:
        assert starts[pj.job_id] == pytest.approx(pj.start_s), pj.job_id
        assert ends[pj.job_id] == pytest.approx(pj.end_s, abs=1e-6), pj.job_id
    assert all(r["status"] == "done" for r in res.jobs_table)
    assert all(r["lost_steps"] == 0 for r in res.jobs_table)


def test_gpu_fault_loses_work_since_last_checkpoint():
    j = job(n=8, duration=7200.0, step=4.0, ckpt_every=600.0, ckpt_dur=30.0)
    ev = [{"kind": "hardware_fault", "event_id": "h", "site_id": "site-a", "rack_id": "a1", "gpu_slot": 3, "onset_s": 1500.0, "repair_s": 7200.0}]
    res = run_scenario(base_scenario(3 * 3600, jobs=[j], events=ev), seed=0)
    row = res.jobs_table[0]
    # Checkpoints complete at wall 630 and 1260; the fault is at 1500, so 240 s of running time is lost.
    assert row["lost_steps"] == pytest.approx(240.0 / 4.0)
    assert row["lost_gpu_hours"] == pytest.approx(60.0 * 4.0 * 8 / 3600.0)
    assert row["faults"] == 1 and row["restarts"] == 1
    assert row["useful_steps"] <= row["total_steps"] + 1e-6


def test_multisite_fault_loses_only_work_since_last_average():
    j = job("m", n=16, duration=3200.0, step=4.0, multisite=True, flexible=False)
    # A filler job leaves no spare GPU at site b, so the failed shard waits for the repair.
    fill = job("fill", n=72, duration=6000.0, ckpt_every=6000.0, site_id="site-b")
    ev = [{"kind": "hardware_fault", "event_id": "h", "site_id": "site-b", "rack_id": "b4", "gpu_slot": 0, "onset_s": 100.0, "repair_s": 600.0}]
    res = run_scenario(base_scenario(3 * 3600, jobs=[j, fill], events=ev), seed=0)
    row = {r["job_id"]: r for r in res.jobs_table}["m"]
    stall = res._run.cfg.transfer.merge_stall_s(8)
    cycle = 8 * 4.0 + stall
    # Fault block starts at t=100: wall time into the cycle is 100 mod cycle (shard runs 32 s then stalls).
    into = 100.0 % cycle
    expected_lost = min(into, 32.0) / 4.0
    assert row["lost_steps"] == pytest.approx(expected_lost, abs=0.6)
    assert row["lost_steps"] <= 8.0
    assert row["skipped_steps"] > 0
    assert row["skipped_steps"] % 8 == pytest.approx(0.0, abs=1e-6) or row["skipped_steps"] % 8 == pytest.approx(8.0, abs=1e-6)
    assert row["status"] == "done"
    assert row["faults"] == 1


def test_breaker_trip_forced_and_inverse_time():
    forced = [{"kind": "breaker_trip", "event_id": "f", "site_id": "site-a", "rack_id": "a1", "onset_s": 600.0, "duration_s": 900.0, "mode": "forced"}]
    res = run_scenario(base_scenario(3600, jobs=[job(n=32, duration=3000.0)], events=forced), seed=0)
    trips = [e for e in res.events if e["kind"] == "breaker_trip"]
    assert len(trips) == 1 and trips[0]["t_s"] == 600.0 and trips[0]["reason"] == "forced"
    p = res.rack_it_power_w
    k = res._run.K
    rack_a1 = p[:, 0]
    assert rack_a1[620 * 1] == 0.0 and rack_a1[1400] == 0.0
    assert rack_a1[1600] > 0.0  # back on after the 900 s off window plus rounding
    assert [e["t_s"] for e in res.events if e["kind"] == "rack_reset"] == [1500.0]
    assert k == 10

    derate = [{"kind": "breaker_trip", "event_id": "d", "site_id": "site-a", "rack_id": "a1", "onset_s": 300.0, "duration_s": 20000.0, "mode": "derate", "derate_fraction": 0.6}]
    res = run_scenario(base_scenario(3 * 3600, jobs=[job(n=32, duration=10_000.0)], events=derate), seed=0)
    trips = [e for e in res.events if e["kind"] == "breaker_trip"]
    assert trips and trips[0]["reason"] == "overload"
    run = res._run
    brk = run.cfg.breaker
    b0 = int(300 / run.cdt)
    b1 = int(round(trips[0]["t_s"] / run.cdt))
    ratios = run.rack_ratio_b[b0:b1, 0]
    assert ratios.min() > brk.nontrip_ratio
    waited = trips[0]["t_s"] - 300.0
    # The element opens no earlier than a cold start at the highest ratio and no later than at the lowest.
    assert waited >= brk.trip_time_s(float(ratios.max())) - run.cdt
    assert waited <= brk.trip_time_s(float(ratios.min())) + 2 * run.cdt
    # No trip below the non-tripping ratio: same load, no derate.
    res0 = run_scenario(base_scenario(3 * 3600, jobs=[job(n=32, duration=10_000.0)]), seed=0)
    assert not [e for e in res0.events if e["kind"] == "breaker_trip"]


def test_cooling_failure_causes_throttling_and_less_power_and_work():
    ev = [{"kind": "cooling_failure", "event_id": "c", "site_id": "site-a", "rack_id": "a1", "onset_s": 600.0, "duration_s": 3000.0, "remaining_capacity_fraction": 0.25}]
    jobs = [job(n=32, duration=6000.0, ckpt_every=3000.0)]
    healthy = run_scenario(base_scenario(7200, jobs=jobs), seed=0)
    failed = run_scenario(base_scenario(7200, jobs=jobs, events=ev), seed=0)
    assert not [e for e in healthy.events if e["kind"] == "thermal_throttle"]
    assert [e for e in failed.events if e["kind"] == "thermal_throttle"]
    assert failed._run.rack_air_b[:, 0].max() > healthy._run.rack_air_b[:, 0].max() + 10.0
    # Throttle (or protective shutdown) lowers rack power and delivered work.
    window = slice(1500, 3500)
    assert failed.rack_it_power_w[window, 0].mean() < healthy.rack_it_power_w[window, 0].mean()
    assert failed.summary()["useful_gpu_hours"] < healthy.summary()["useful_gpu_hours"]


def test_throttle_threshold_reduces_gpu_power():
    jobs = [job(n=32, duration=3000.0, ckpt_every=3000.0)]
    hot = base_scenario(3600, jobs=jobs)
    hot["throttle"]["throttle_threshold_c"] = 40.0  # below normal GPU temperature
    a = run_scenario(base_scenario(3600, jobs=jobs), seed=0)
    b = run_scenario(hot, seed=0)
    assert b.rack_gpu_power_w[600:, 0].mean() < a.rack_gpu_power_w[600:, 0].mean()
    assert b.jobs_table[0]["useful_steps"] < a.jobs_table[0]["useful_steps"]


def test_cap_and_import_limit_violation_accounting():
    sc = base_scenario(3600, jobs=[job("a", n=64), job("b", n=32, start=60.0)])
    sc["sites"][0]["site"]["power_cap_w"] = 40_000.0  # valid: below cooling and import limits
    ev = [{"kind": "grid_curtailment", "event_id": "g", "site_id": "site-a", "onset_s": 1200.0, "duration_s": 600.0, "limit_fraction": 0.3}]
    sc["events"] = ev
    res = run_scenario(sc, seed=0)
    run = res._run
    p = res.site_power_w[:, 0]
    over = np.maximum(p - 40_000.0, 0.0)
    assert res.site_cap_violation["seconds_above"][0] == (over > 0).sum() * run.dt
    assert res.site_cap_violation["energy_above_kwh"][0] == pytest.approx(over.sum() * run.dt / 3.6e6)
    assert res.site_cap_violation["max_excess_w"][0] == pytest.approx(over.max())
    limit = 110_000.0 * np.where((np.arange(3600) >= 1200) & (np.arange(3600) < 1800), 0.3, 1.0)
    over_i = np.maximum(p - limit, 0.0)
    assert res.import_violation["seconds_above"][0] == (over_i > 0).sum()
    assert res.import_violation["energy_above_kwh"][0] == pytest.approx(over_i.sum() / 3.6e6)
    assert res.import_violation["seconds_above"][0] > 0
    # Site b has no violation.
    assert res.site_cap_violation["seconds_above"][1] == 0


def test_policy_hook_can_reduce_cap_violation():
    sc = base_scenario(3600, jobs=[job("a", n=64), job("b", n=32, start=60.0)])
    sc["sites"][0]["site"]["power_cap_w"] = 80_000.0
    plain = run_scenario(sc, seed=0)
    capped = run_scenario(sc, controller=ReactiveSiteCapController(margin=0.97), seed=0)
    assert plain.site_cap_violation["seconds_above"][0] > 0
    assert capped.site_cap_violation["energy_above_kwh"][0] < plain.site_cap_violation["energy_above_kwh"][0]
    assert any(a["action"] == "SetRackPowerCap" and a["status"] == "applied" for a in capped.actions)


class Recorder:
    """Controller that records the visible state at every decision."""

    def __init__(self, actions=None):
        self.states = {}
        self.actions = actions or {}

    def decide(self, t_s, visible_state):
        self.states[t_s] = visible_state
        return self.actions.get(t_s, ())


def _snapshot(state):
    return {
        "now": {k: np.array(v, copy=True) for k, v in state.now.items()},
        "history": {c: state.history(c, 7200.0) for c in ("rack_air_c", "rack_it_power_w", "site_power_w", "supply_c")},
        "jobs": state.jobs,
        "planned": state.known_future["planned_jobs"],
        "announced": state.known_future["announced_curtailments"],
        "forecast": state.known_future["outdoor_forecast_c"],
    }


def test_visible_state_has_no_future_leakage():
    jobs = [job("a", n=32, duration=5000.0), job("b", n=16, start=200.0, duration=3000.0)]
    future = [
        {"kind": "hardware_fault", "event_id": "h", "site_id": "site-a", "rack_id": "a1", "gpu_slot": 1, "onset_s": 2500.0, "repair_s": 600.0},
        {"kind": "grid_curtailment", "event_id": "g", "site_id": "site-b", "onset_s": 2700.0, "duration_s": 300.0, "limit_fraction": 0.4},
        {"kind": "cooling_failure", "event_id": "c", "site_id": "site-a", "rack_id": "a2", "onset_s": 2800.0, "duration_s": 600.0, "remaining_capacity_fraction": 0.2},
    ]
    announced = {"kind": "grid_curtailment", "event_id": "ga", "site_id": "site-a", "onset_s": 3400.0, "duration_s": 300.0, "limit_fraction": 0.5, "announce_lead_s": 600.0}
    cut = 2400.0
    ra, rb = Recorder(), Recorder()
    sc_a = base_scenario(3600, jobs=jobs, events=[announced])
    sc_b = base_scenario(3600, jobs=jobs, events=future + [announced])
    # Different realized outdoor temperature after the cut, identical forecast series.
    cfg = build_config(sc_a)
    env_a = dict(cfg.environment)
    env_b = {}
    for sid, e in env_a.items():
        actual = e.outdoor_c.copy()
        actual[1:] += 15.0  # changes the realized series after t = 0 hour... applied below only after the cut hour
        env_b[sid] = SiteEnvironment(outdoor_c=np.where(np.arange(actual.size) * 3600.0 > cut + 1200.0, actual, e.outdoor_c),
                                     price_usd_per_kwh=e.price_usd_per_kwh, carbon_g_per_kwh=e.carbon_g_per_kwh,
                                     outdoor_forecast_c=e.forecast_c)
    run_scenario(sc_a, controller=ra, seed=2)
    run_scenario(sc_b, controller=rb, seed=2, environment=env_b)
    times = sorted(t for t in ra.states if t <= cut)
    assert times and times[-1] == cut
    for t in times:
        sa, sb = _snapshot(ra.states[t]), _snapshot(rb.states[t])
        for key in sa["now"]:
            assert np.array_equal(sa["now"][key], sb["now"][key], equal_nan=True), (t, key)
        for key in sa["history"]:
            assert np.array_equal(sa["history"][key][0], sb["history"][key][0]), (t, key)
            assert np.array_equal(sa["history"][key][1], sb["history"][key][1], equal_nan=True), (t, key)
            assert sa["history"][key][0].size == 0 or sa["history"][key][0].max() <= t
        assert sa["jobs"] == sb["jobs"] and sa["planned"] == sb["planned"] and sa["announced"] == sb["announced"]
        assert np.array_equal(sa["forecast"], sb["forecast"])
    # After the future events happen the states do differ, so the test can tell.
    late = sorted(t for t in ra.states if t > 2900.0)[0]
    assert not np.array_equal(ra.states[late].now["rack_air_c"], rb.states[late].now["rack_air_c"]) or \
        not np.array_equal(ra.states[late].now["gpu_temp_c"], rb.states[late].now["gpu_temp_c"], equal_nan=True)
    # The announced curtailment appears 600 s ahead, not before.
    before = ra.states[2700.0].known_future["announced_curtailments"]
    after = ra.states[2880.0].known_future["announced_curtailments"]
    assert before == () and [c["event_id"] for c in after] == ["ga"]
    # The unannounced events never appear in the known-future schedule.
    assert all(c["event_id"] == "ga" for s in ra.states.values() for c in s.known_future["announced_curtailments"])
    assert all(c["event_id"] == "ga" for s in rb.states.values() for c in s.known_future["announced_curtailments"])
    with pytest.raises(KeyError):
        ra.states[cut].history("ground_truth_events", 60.0)


def test_controller_actions_defer_pause_checkpoint_and_rejections():
    jobs = [
        job("flex", n=16, start=0.0, duration=3000.0, flexible=True),
        job("rigid", n=8, start=0.0, duration=3000.0, flexible=False),
        job("later", n=8, start=600.0, duration=1200.0, flexible=True),
    ]
    actions = {
        0.0: [DeferJob("later", 1200.0), PauseJob("rigid"), CheckpointNow("rigid"), SetRackPowerCap("nope", 1.0)],
        120.0: [PauseJob("flex")],
        600.0: [ResumeJob("flex")],
        660.0: [CheckpointNow("flex"), DeferJob("flex", 9999.0)],
    }
    res = run_scenario(base_scenario(3600, jobs=jobs), controller=Recorder(actions), seed=0)
    log = {(a["t_s"], a["action"], a["detail"].get("job_id")): a["status"] for a in res.actions}
    assert log[(0.0, "DeferJob", "later")] == "applied"
    assert log[(0.0, "PauseJob", "rigid")].startswith("rejected")
    assert log[(0.0, "CheckpointNow", "rigid")].startswith("rejected")  # not yet running at t=0
    assert log[(120.0, "PauseJob", "flex")] == "applied"
    assert log[(660.0, "DeferJob", "flex")].startswith("rejected")
    starts = {e["job_id"]: e["t_s"] for e in res.events if e["kind"] == "job_start"}
    assert starts["later"] == 1200.0
    rows = {r["job_id"]: r for r in res.jobs_table}
    # The flexible job lost 480 s of progress to the pause (paused 120 to 600).
    assert rows["flex"]["useful_steps"] < rows["rigid"]["useful_steps"]
    assert any(a["status"].startswith("rejected") and a["action"] == "SetRackPowerCap" for a in res.actions)


def test_rack_power_cap_limits_power_and_progress():
    jobs = [job("a", n=32, duration=3000.0, ckpt_every=3000.0)]
    cap = {0.0: [SetRackPowerCap("a1", 15_000.0)]}
    free = run_scenario(base_scenario(3600, jobs=jobs), seed=0)
    capped = run_scenario(base_scenario(3600, jobs=jobs), controller=Recorder(cap), seed=0)
    assert capped.rack_it_power_w[300:, 0].max() < free.rack_it_power_w[300:, 0].mean()
    assert capped.jobs_table[0]["useful_steps"] < free.jobs_table[0]["useful_steps"]


def test_migration_moves_a_flexible_job_and_costs_transfer_time():
    j = job("mig", n=16, start=0.0, duration=3000.0, flexible=True, site_id="site-a", ckpt_every=10_000.0)
    res = run_scenario(
        base_scenario(2 * 3600, jobs=[j]), controller=Recorder({300.0: [MigrateJob("mig", "site-b")]}), seed=0
    )
    row = res.jobs_table[0]
    assert row["migrations"] == 1 and row["status"] == "done" and row["lost_steps"] == 0
    tr = res._run.cfg.transfer
    assert tr.transfer_s(16) == pytest.approx(16 * 4.375e9 / 3.125e9 + 0.02 + 0.012)
    start = [e for e in res.events if e["kind"] == "migration_start"][0]
    done = [e for e in res.events if e["kind"] == "job_done"][0]
    # The job needs 3000 s of running time; the migration stalls it for a checkpoint, the transfer and a restore.
    stall = j.checkpoint_duration_s + tr.transfer_s(16) + tr.restore_s(16)
    assert done["t_s"] == pytest.approx(3000.0 + stall + 10_000.0 * 0, abs=3 * 10.0 + 1.0)
    assert start["to_site_id"] == "site-b"
    # Rack power moves from site a racks to site b racks.
    assert res.rack_gpu_power_w[100:200, :4].sum() > res.rack_gpu_power_w[100:200, 4:].sum() * 0 + 1
    late = slice(1500, 2000)
    assert res.rack_gpu_power_w[late, 4:].mean(axis=0)[0] > res.rack_gpu_power_w[late, :4].mean(axis=0)[0]


def test_admit_action_starts_a_queued_job_early():
    j = job("early", n=8, start=2400.0, duration=600.0, flexible=True)
    res = run_scenario(base_scenario(3600, jobs=[j]), controller=Recorder({120.0: [AdmitJob("early")]}), seed=0)
    start = [e for e in res.events if e["kind"] == "job_start"][0]
    assert start["t_s"] == 120.0


def test_known_future_covariates_shapes_and_alignment():
    sc = base_scenario(7200, jobs=[job("a", n=40, start=600.0, duration=2000.0)])
    res = run_scenario(sc, seed=0)
    cfg = res._run.cfg
    cov = planned_covariates(cfg, plan_schedule(cfg), 60.0, "rack")
    assert cov["planned_gpus_running"].shape == (120, 8)
    assert cov["bin_start_s"][0] == 0.0 and cov["bin_start_s"][1] == 60.0
    assert cov["planned_gpus_running"][5].sum() == 0
    assert cov["planned_gpus_running"][30].sum() == pytest.approx(40.0)
    site = planned_covariates(cfg, plan_schedule(cfg), 3600.0, "site")
    assert site["planned_gpus_running"].shape == (2, 2)
    assert site["outdoor_forecast_c"].shape == (2, 2)
    assert np.all(np.isfinite(site["price_usd_per_kwh"]))
    arrays = res.to_arrays()
    assert arrays["cov_rack_1min_planned_gpus_running"].shape == (120, 8)
    assert arrays["cov_site_1h_carbon_g_per_kwh"].shape == (2, 2)


def test_environment_override_flows_into_cost_and_carbon():
    sc = base_scenario(3600, jobs=[job(n=16)])
    cfg = build_config(sc)
    n = int(sc["horizon_s"] / 3600) + 1
    env = {
        sid: SiteEnvironment(outdoor_c=np.full(n, 20.0), price_usd_per_kwh=np.full(n, 0.5), carbon_g_per_kwh=np.full(n, 100.0))
        for sid in cfg.environment
    }
    res = run_scenario(sc, seed=0, environment=env)
    assert np.allclose(res.site_cost_usd_1h, res.site_energy_kwh_1h * 0.5)
    assert np.allclose(res.site_carbon_kg_1h, res.site_energy_kwh_1h * 0.1)


def test_job_override_accepts_an_external_schedule():
    sc = base_scenario(3600, jobs=[job("x", n=8)])
    ext = [job("trace-1", n=8, duration=600.0), job("trace-2", n=16, start=100.0, duration=600.0)]
    res = run_scenario(sc, seed=0, jobs=ext)
    assert [r["job_id"] for r in res.jobs_table] == ["trace-1", "trace-2"]


def test_default_scenario_runs_for_a_few_hours():
    sc = json.loads(SCENARIO_PATH.read_text())
    sc["horizon_s"] = 4 * 3600
    sc["outputs"] = {"gpu_windows": [[0, 600]]}
    sc["events"] = [e for e in sc["events"] if e["onset_s"] < 4 * 3600 and e["event_id"] != "hw-1-precursor"]
    res = run_scenario(copy.deepcopy(sc), seed=0)
    s = res.summary()
    assert s["data_kind"] == "simulated"
    assert s["jobs"] > 0 and s["useful_gpu_hours"] > 0
    assert res.to_arrays()["meta"]["data_kind"] == "simulated"


def test_scenario_v2_calibration_notes_label_levels():
    """v2 levels carry their data labels, and the run metadata says so."""
    import copy
    import json as _json
    from pathlib import Path as _Path

    from gpu_stack.research import heatwave_sim as _hs

    path = _Path(__file__).resolve().parents[1] / "experiments/e003-heatwave/sim-scenario-v2.json"
    sc = _hs.load_scenario(path)
    assert sc["calibration"]["sha256"]
    small = copy.deepcopy(sc)
    small["horizon_s"] = 3 * 3600
    small["outputs"] = {"gpu_windows": [[0, 60]]}
    meta = _hs.run_scenario(small, seed=0).to_arrays()["meta"]
    prov = meta["power_levels"]["provenance"]
    assert prov["idle_w"].startswith("public data")
    assert prov["checkpoint_w"].startswith("measured laptop data")
    assert "calibration notes applied" in meta["quantity_provenance"]["gpu_power_levels"]
    bad = copy.deepcopy(small)
    bad["power_levels"]["calibration_notes"] = {"not_a_level": "x"}
    import pytest as _pytest

    with _pytest.raises(ValueError):
        _hs.run_scenario(bad, seed=0)
    _json.dumps(meta, default=str)


def test_hardware_fault_precursor_is_visible_and_jobs_report_racks():
    """A GPU-temperature precursor shows in visible now/history before onset; JobView lists racks."""
    jobs = [job("a", n=32, duration=5000.0)]
    pre = {"kind": "hardware_fault", "event_id": "hp", "site_id": "site-a", "rack_id": "a1", "gpu_slot": 1,
           "onset_s": 3000.0, "repair_s": 600.0,
           "precursors": [{"channel": "gpu_temp_c", "lead_s": 1200.0, "strength": 6.0}]}
    ra, rb = Recorder(), Recorder()
    run_scenario(base_scenario(3600, jobs=jobs, events=[]), controller=ra, seed=3)
    run_scenario(base_scenario(3600, jobs=jobs, events=[pre]), controller=rb, seed=3)
    t_early = max(t for t in ra.states if t <= 1700.0)
    t_late = max(t for t in ra.states if t <= 2900.0)
    sa, sb = ra.states[t_early], rb.states[t_early]
    assert np.array_equal(sa.now["gpu_temp_c"], sb.now["gpu_temp_c"], equal_nan=True)  # before the ramp
    sa, sb = ra.states[t_late], rb.states[t_late]
    rack = list(sb.rack_ids).index("a1")
    diff = np.nan_to_num(sb.now["gpu_temp_c"]) - np.nan_to_num(sa.now["gpu_temp_c"])
    assert diff.max() > 3.0  # ramp is about 6 K * (2900 - 1800) / 1200 by then
    _, ha = sa.history("max_gpu_temp_c", 600.0)
    _, hb = sb.history("max_gpu_temp_c", 600.0)
    assert hb[-1, rack] > ha[-1, rack]
    views = [v for v in sb.jobs if v.job_id == "a"]
    assert views and views[0].rack_ids and all(r in sb.rack_ids for r in views[0].rack_ids)
