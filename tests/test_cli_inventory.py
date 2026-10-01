"""Tests for the ``list-presets`` CLI command.

``list-presets`` enumerates the preset packs users can run, so we check
that a representative sample from every family (hardware, lithography,
workload, economics, scenarios) shows up."""

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
        "lithography.euv_exposure",
        "lithography.arf_immersion_exposure",
        "workload.dense_variant_selector",
        "workload.pythia_70m_dense_training",
        "economics.us_2024_industrial_flat_power_tariff",
        "scenarios.dense_training_cost_fixture",
        "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
    ):
        assert preset_name in out
