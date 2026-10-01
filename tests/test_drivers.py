"""The cost-driver analysis: small run, structural checks, and the shipped docs/data/drivers.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")

from gpu_stack import drivers  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def result():
    return drivers.compute_drivers(n_pow=10)


def test_closed_form_matches_resolver_and_is_plausible(result):
    # build_model() raises if the closed form disagrees with the numeric resolver
    assert 0.01 < result["nominal_cost_per_million_tokens_usd"] < 0.5


def test_shares_sum_to_one_and_top_inputs_are_the_expected_ones(result):
    shares = [r["share"] for r in result["all"]]
    assert sum(shares) == pytest.approx(1.0, abs=1e-9)
    top = {r["variable"] for r in result["top"][:6]}
    assert {"mfu", "arch.params_total_dense", "chip_peak_flops", "econ.asset.useful_life"} <= top


def test_electricity_and_chip_physics_barely_matter(result):
    by = {r["variable"]: r["share"] for r in result["all"]}
    assert by["econ.power.price_kwh_offpeak"] < 0.01
    physics = next(z for z in result["zero_effect"] if "chip is made" in z["label"])
    assert physics["evidence"].endswith("0 appear in the cost formula.")


def test_shipped_drivers_json_has_plain_labels():
    path = ROOT / "docs" / "data" / "drivers.json"
    assert path.exists(), "run scripts/build_site_data.py"
    d = json.loads(path.read_text(encoding="utf-8"))
    assert len(d["top"]) >= 6
    assert abs(sum(r["share"] for r in d["all"]) - 1.0) < 1e-6
    for r in d["top"]:
        assert r["label"] != r["variable"] and " " in r["label"]  # plain words, not a graph name
