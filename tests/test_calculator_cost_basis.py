"""The calculator's cited cost defaults agree with the audit's sources table, and the audit results are current.

``gpu_stack.calculator_cost_basis`` holds each default with its URL; ``experiments/e003-heatwave/cost_audit/sources.json``
is the table of every row the audit read.  These tests keep the two from drifting apart and check that every row of the
table names a known source with a URL.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import pytest

from gpu_stack import calculator
from gpu_stack import calculator_cost_basis as basis

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "experiments" / "e003-heatwave" / "cost_audit"
TABLE = json.loads((AUDIT / "sources.json").read_text())
ROWS = {r["id"]: r for r in TABLE["rows"]}


def test_every_row_has_a_known_source_with_a_location():
    assert len(ROWS) == len(TABLE["rows"]), "row ids must be unique"
    for r in TABLE["rows"]:
        assert r["source"] in TABLE["sources"], r["id"]
        src = TABLE["sources"][r["source"]]
        assert src["url"].startswith("https://") or src["url"].startswith("experiments/"), r["id"]
        assert r.get("item") and r.get("unit"), r["id"]


def test_every_row_has_a_value_or_says_why_not():
    for r in TABLE["rows"]:
        has_number = any(r.get(k) is not None for k in ("value", "low", "high")) or any(
            isinstance(v, (int, float, list)) and not isinstance(v, bool) for k, v in r.items()
            if k not in ("id", "group", "unit", "basis", "source", "evidence", "current", "item", "chip", "region"))
        said_why = str(r.get("basis", "")).startswith(("not found", "read from cost-v1.json"))
        assert has_number or said_why, r["id"]


def test_h100_price_and_range_match_table():
    r = ROWS["price.h100.gpu_sxm5"]
    assert basis.H100_PRICE_RANGE_USD == (r["low"], r["high"])
    assert basis.H100_PRICE_USD == r["value"]


def test_a100_price_matches_table():
    r = ROWS["price.a100.sxm80"]
    assert basis.A100_PRICE_RANGE_USD == (r["low"], r["high"])
    assert basis.A100_PRICE_USD == r["value"]


def test_electricity_matches_table():
    assert basis.ELECTRICITY_USD_PER_KWH == ROWS["elec.eia2025.us_industrial"]["value"]


def test_operator_lives_match_table_and_median():
    ids = ["life.msft", "life.goog", "life.meta", "life.amzn", "life.orcl", "life.crwv", "life.nbis", "life.lambda"]
    assert [y for _, y, _ in basis.OPERATOR_SERVER_LIVES] == [ROWS[i]["value"] for i in ids]
    assert basis.USEFUL_LIFE_YEARS == statistics.median(ROWS[i]["value"] for i in ids)
    assert basis.USEFUL_LIFE_RANGE_YEARS == (min(ROWS[i]["value"] for i in ids), max(ROWS[i]["value"] for i in ids))
    assert all(url.startswith("https://") for _, _, url in basis.OPERATOR_SERVER_LIVES)


def test_facility_matches_table():
    assert basis.FACILITY_USD_PER_W == ROWS["fac.jll_per_mw_2026"]["value"] / 1e6
    assert basis.FACILITY_USEFUL_LIFE_YEARS == ROWS["life.facility.heavy_equipment_amzn"]["value"]


def test_node_power_matches_table():
    r = ROWS["power.h100.node_measured_avg"]
    assert list(basis.H100_NODE_MEASURED_SAMPLES_W) == r["samples_w"]
    assert basis.H100_NODE_MEASURED_AVG_W == r["value"]
    assert basis.H100_TDP_W == ROWS["power.h100.tdp"]["value"]
    # the default makes an 8-GPU node draw the measured average (to the rounding of the default)
    node_w = 8 * basis.H100_TDP_W * basis.GPU_POWER_FRACTION * (1 + basis.SERVER_POWER_FRACTION)
    assert node_w == pytest.approx(basis.H100_NODE_MEASURED_AVG_W, rel=0.005)


def test_other_hardware_fraction_matches_table():
    meta = ROWS["net.amcompute_h100_meta"]
    assert basis.NETWORK_PER_GPU_USD == meta["network"] / meta["n_gpus"]
    assert basis.OTHER_IT_PER_GPU_USD == meta["other"] / meta["n_gpus"]
    assert basis.DGX_H100_SYSTEM_USD == ROWS["price.h100.sys_dgx"]["value"]
    assert basis.HGX_H100_SYSTEM_USD == ROWS["price.h100.sys_hgx_new"]["value"]
    assert basis.OTHER_HARDWARE_FRACTION == pytest.approx(basis.OTHER_HARDWARE_FRACTION_EXACT, abs=0.005)


def test_calculator_uses_the_cited_defaults():
    e = calculator.estimate(7e9, 2e12, "H100-SXM", 1024)
    assert e.inputs["electricity_price"] == basis.ELECTRICITY_USD_PER_KWH
    assert e.inputs["useful_life_years"] == basis.USEFUL_LIFE_YEARS
    assert e.inputs["other_hardware_fraction"] == basis.OTHER_HARDWARE_FRACTION
    assert e.inputs["server_power_fraction"] == basis.SERVER_POWER_FRACTION
    assert e.inputs["gpu_price"] == basis.H100_PRICE_USD


def test_facility_term_enters_hardware_cost_and_scales_with_its_life():
    base = calculator.estimate(7e9, 2e12, "H100-SXM", 1024)
    h = base.hardware_cost
    try:
        basis.FACILITY_USD_PER_W = 0.0
        calculator.build_model.cache_clear()
        without = calculator.estimate(7e9, 2e12, "H100-SXM", 1024)
    finally:
        basis.FACILITY_USD_PER_W = ROWS["fac.jll_per_mw_2026"]["value"] / 1e6
        calculator.build_model.cache_clear()
    assert without.hardware_cost < h
    assert without.electricity_cost == pytest.approx(base.electricity_cost, rel=1e-12)
    # the facility slice is facility $/W x chip rating x (1 + server power) per GPU, over the facility life
    per_gpu = basis.FACILITY_USD_PER_W * 700.0 * (1 + basis.SERVER_POWER_FRACTION)
    gpu_seconds = base.gpu_hours * 3600.0
    expected = per_gpu / (basis.FACILITY_USEFUL_LIFE_YEARS * calculator.SECONDS_PER_YEAR) * gpu_seconds
    assert h - without.hardware_cost == pytest.approx(expected, rel=1e-9)


def _result(name):
    return json.loads((ROOT / "experiments" / "e003-heatwave" / "results" / name).read_text())["result"]


def test_audit_result_base_case_is_current():
    """If the calculator's defaults move, the committed audit result must be re-generated."""
    res = _result("cost-audit-v1.json")
    e = calculator.estimate(7e9, 2e12, "H100-SXM", 1024)
    assert res["base_case"]["electricity_cost_usd"] == pytest.approx(e.electricity_cost, rel=1e-9)
    assert res["base_case"]["total_cost_usd"] == pytest.approx(e.total_cost, rel=1e-9)
    after = _result("cost-audit-correction-v1.json")["readme_example"]["after"]
    assert after["total_cost"] == pytest.approx(e.total_cost, rel=1e-9)


def test_audit_result_records_the_sources_table_hash():
    import hashlib

    res = _result("cost-audit-v1.json")
    assert res["sources_table_sha256"] == hashlib.sha256((AUDIT / "sources.json").read_bytes()).hexdigest()
