"""The calculator is the equation graph: results match a direct numeric resolve, and the
published-run check stays where the earlier held-out test put it (about 22%)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from gpu_stack import calculator
from gpu_stack.core.resolver import resolve

ROOT = Path(__file__).resolve().parents[1]


def test_default_scenario_is_sensible():
    e = calculator.estimate(7e9, 2e12, "H100-SXM", 1024)
    # 6 N D / (989.4e12 * 0.4) / 3600 GPU-hours
    assert e.gpu_hours == pytest.approx(6 * 7e9 * 2e12 / (989.4e12 * 0.4) / 3600, rel=1e-9)
    assert e.training_days == pytest.approx(e.gpu_hours / 1024 / 24, rel=1e-9)
    assert e.total_cost == pytest.approx(e.electricity_cost + e.hardware_cost, rel=1e-9)
    assert e.cost_per_million_tokens == pytest.approx(e.total_cost / 2e12 * 1e6, rel=1e-9)
    # energy x price = electricity cost
    assert e.energy_mwh * 1000 * 0.0813 == pytest.approx(e.electricity_cost, rel=1e-9)


def test_matches_a_direct_numeric_graph_resolve():
    """The closed form must equal resolving the graph with plain numbers."""
    e = calculator.estimate(13e9, 1e12, "A100-80GB-SXM", 512, mfu=0.45, pue=1.3)
    v = e.inputs
    life_s = v["useful_life_years"] * calculator.SECONDS_PER_YEAR
    amort = resolve("econ.gpu.hourly_amortized", assignments={
        "econ.gpu.capex": v["gpu_price"] * (1 + v["other_hardware_fraction"]),
        "econ.asset.residual_fraction": v["residual_fraction"],
        "econ.asset.useful_life": life_s,
    }).value
    assignments = {
        "arch.params_total_dense": v["params"], "training.total_tokens": v["tokens"], "par.n_gpus": v["n_gpus"],
        "arch.tokens_per_step": 4_194_304, "training.recompute_overhead": 1,
        "training.optimizer_flop_multiplier": 1, "training.t_exposed_comm": 0, "training.t_mem_bound": 0,
        "training.overhead_fraction": 0, "training.cluster_availability": 1, "econ.job.share_of_cluster": 1,
        "econ.run.opex_misc_cost": 0, "econ.power.price_kwh_peak": v["electricity_price"],
        "econ.power.price_kwh_offpeak": v["electricity_price"], "econ.power.peak_energy_fraction": 0,
        "gpu.peak_flops_power_limited": v["peak_flops"] * v["mfu"],
        "thermal.dc.total_power": v["pue"] * v["n_gpus"] * v["tdp_w"] * v["gpu_power_fraction"]
        * (1 + v["server_power_fraction"]),
        "econ.job.capex_rate": v["n_gpus"] * float(amort),
    }
    variants = calculator.GRAPH_VARIANTS
    wall = float(resolve("training.wallclock", assignments=assignments, variants=variants).value)
    assert e.training_days == pytest.approx(wall / 86400, rel=1e-9)
    for target, attr, scale in [
        ("econ.run.power_cost", "electricity_cost", 1.0),
        ("econ.run.hw_cost", "hardware_cost", 1.0),
        ("econ.run.total_cost", "total_cost", 1.0),
        ("econ.cost.per_token", "cost_per_million_tokens", 1e6),
    ]:
        direct = float(resolve(target, assignments=assignments, variants=variants).value) * scale
        assert getattr(e, attr) == pytest.approx(direct, rel=1e-9), target


def test_breakdown_tags_and_chains():
    e = calculator.estimate(7e9, 2e12, mfu=0.5)
    items = e.breakdown()
    assert [i["output"] for i in items] == list(calculator.OUTPUT_ORDER)
    tags = {i["label"]: i["tag"] for item in items for i in item["inputs"]}
    assert tags["Model size"] == calculator.TAG_USER
    assert tags["GPU speed actually achieved (MFU)"] == calculator.TAG_USER  # passed explicitly
    assert tags["Datacenter overhead (PUE)"] == calculator.TAG_ASSUMPTION
    assert tags["Chip peak speed"] == calculator.TAG_SPEC
    total = next(i for i in items if i["output"] == "total_cost")
    equations = {s["equation"] for s in total["chain"] if s["equation"]}
    assert {"training.eq.wallclock", "econ.eq.run_power_cost", "econ.eq.amortized", "econ.eq.run_total"} <= equations
    for item in items:
        assert item["chain"][-1]["value"] == pytest.approx(item["value"], rel=1e-9) or item["output"] in (
            "energy_mwh",
        )


def test_inputs_are_validated():
    with pytest.raises(ValueError):
        calculator.estimate(7e9, 2e12, mfu=1.5)
    with pytest.raises(ValueError):
        calculator.estimate(-1, 2e12)
    with pytest.raises(ValueError):
        calculator.estimate(7e9, 2e12, gpu="B200")


def test_cost_per_token_does_not_depend_on_gpu_count():
    a = calculator.estimate(7e9, 2e12, n_gpus=64)
    b = calculator.estimate(7e9, 2e12, n_gpus=4096)
    assert a.cost_per_million_tokens == pytest.approx(b.cost_per_million_tokens, rel=1e-9)
    assert a.training_days == pytest.approx(b.training_days * 64, rel=1e-9)


def test_published_runs_dataset_is_complete():
    doc = calculator.load_published_runs()
    assert len(doc["runs"]) == 27
    for r in doc["runs"]:
        assert r["cite"] and r["params"] > 0 and r["tokens"] > 0 and r["gpu_hours"] > 0
        assert r["accelerator"] in doc["hardware"]
        assert all(c["src"] in doc["sources"] for c in r["cite"])


def test_check_against_published_median_error_is_pinned():
    """About 22% on 27 published runs, the same as the 6 x params x tokens rule at 40% MFU."""
    c = calculator.check_against_published()
    assert c["n"] == 27
    assert c["median_abs_error"] == pytest.approx(0.2195, abs=0.005)
    # the plain rule of thumb, computed independently of the graph
    doc = calculator.load_published_runs()
    errs = []
    for r in doc["runs"]:
        peak = doc["hardware"][r["accelerator"]]["peak_flops_dense_16bit"]
        pred = 6 * r["params"] * r["tokens"] / (peak * 0.40) / 3600
        errs.append(abs(pred / r["gpu_hours"] - 1))
    errs.sort()
    assert c["median_abs_error"] == pytest.approx(errs[13], abs=0.005)


def test_web_model_json_is_current():
    """docs/data/calculator-model.json must be what scripts/build_site_data.py would write."""
    path = ROOT / "docs" / "data" / "calculator-model.json"
    assert path.exists(), "run scripts/build_site_data.py"
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    fresh = json.loads(json.dumps(calculator.web_model()))
    for a, b in zip(on_disk["tests"], fresh["tests"]):
        for k in a["expected"]:
            assert math.isclose(a["expected"][k], b["expected"][k], rel_tol=1e-9)
    assert on_disk["outputs"].keys() == fresh["outputs"].keys()
    assert on_disk["accuracy"] == fresh["accuracy"]


def test_cli_estimate_prints_a_table(capsys):
    from gpu_stack.cli import main

    assert main(["estimate", "--params", "7e9", "--tokens", "2e12", "--gpu", "H100-SXM", "--gpus", "1024"]) == 0
    out = capsys.readouterr().out
    assert "Total cost" in out and "Cost per million tokens" in out
    assert main(["estimate", "--params", "7e9", "--tokens", "2e12", "--explain"]) == 0
    out = capsys.readouterr().out
    assert "assumption" in out and "you entered" in out and "econ.eq.run_total" in out
