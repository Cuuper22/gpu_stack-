"""Contracts for the public preset inventory.

A preset is a named bundle of root-input assignments with a cited source.
These tests protect discoverability: each preset module publishes its
expected names in ``__all__``, and the CLI's dynamic inventory finds every
sourced preset under a unique dotted name, so nothing ships that users cannot
list.
"""

from gpu_stack.cli import _iter_presets
from gpu_stack.presets import lithography, scenarios


def test_preset_modules_publish_expected_public_names():
    expected_names = {
        lithography: {
            "EXPOSURE_PRESETS",
            "euv_exposure",
            "arf_immersion_exposure",
        },
        scenarios: {
            "COST_PER_TOKEN_TARGET",
            "DENSE_TRAINING_COST_TARGETS",
            "SOURCED_SCENARIO_PACKS",
            "dense_training_cost_inputs",
            "dense_training_cost_fixture",
            "pythia_70m_dgx_h100_single_node_run_closure",
            "pythia_70m_dgx_h100_us_2024_industrial_power",
        },
    }

    for module, names in expected_names.items():
        assert names <= set(module.__all__)
        assert all(hasattr(module, name) for name in names)


def test_dynamic_cli_inventory_discovers_presets_and_unique_sourced_packs():
    inventory = dict(_iter_presets())
    expected_inventory_names = {
        "lithography.euv_exposure",
        "lithography.arf_immersion_exposure",
        "scenarios.dense_training_cost_fixture",
        "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
    }

    assert expected_inventory_names <= set(inventory)
    assert inventory["lithography.euv_exposure"] is lithography.euv_exposure

    pack_names = [preset.name for preset in scenarios.SOURCED_SCENARIO_PACKS]
    assert len(pack_names) == len(set(pack_names))
    assert {
        f"scenarios.{preset.name}" for preset in scenarios.SOURCED_SCENARIO_PACKS
    } <= set(inventory)
