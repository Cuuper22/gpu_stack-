"""CLI inventory and next-work command tests."""

import json

from gpu_stack.cli import main
from tests.helpers.cli import captured_stdout


def test_list_presets_shows_representative_dynamic_inventory():
    with captured_stdout() as buf:
        rc = main(["list-presets"])
    out = buf.getvalue()
    assert rc == 0
    for preset_name in (
        "hardware.demo_rack",
        "hardware.dgx_h100_8gpu_node",
        "materials.medium_h2o_h1_o16_composition",
        "materials.source_tin_120",
        "lithography.euv_tin120_lpp_source_boundary_assumption",
        "workload.dense_variant_selector",
        "workload.pythia_70m_dense_training",
        "economics.us_2024_industrial_flat_power_tariff",
        "scenarios.dense_training_cost_fixture",
        "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
    ):
        assert preset_name in out


def test_next_work_text_prints_live_compass_sections():
    with captured_stdout() as buf:
        rc = main(["next-work"])

    out = buf.getvalue()
    assert rc == 0
    assert "Next work:" in out
    assert "graph evidence: variables=1517 equations=959 root_inputs=619" in out
    assert "Top 3 highest impact:" in out
    assert "4 best implementations:" in out
    assert "10 active experiment risks:" in out
    assert "Bind E002-PW3 to a named instrumented rack and execute it" in out
    assert "Keep the first rack result at the direct measurement boundary" in out
    assert "Let the paired physical result choose PW4 or kill the mechanism" in out
    assert "Legacy diagnostics (not scientific priorities):" in out
    assert "Close the sourced Pythia cost frontier" in out
    assert "cost_per_token has" in out
    assert "Pay down the heaviest root-debt family" in out


def test_next_work_json_shape_matches_public_compass_contract():
    with captured_stdout() as buf:
        rc = main(["next-work", "--json"])

    payload = json.loads(buf.getvalue())
    assert rc == 0
    assert set(payload) == {"highest_impact", "best_implementations", "bug_risks"}
    assert len(payload["highest_impact"]) == 3
    assert len(payload["best_implementations"]) == 4
    assert len(payload["bug_risks"]) == 10
    assert payload["highest_impact"][0]["title"] == (
        "Bind E002-PW3 to a named instrumented rack and execute it"
    )
