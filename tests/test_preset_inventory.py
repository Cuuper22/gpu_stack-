"""Contracts for the public preset inventory and material compositions.

A preset is a named bundle of root-input assignments with a cited source.
These tests protect two promises. First, discoverability: each preset module
publishes its expected names in ``__all__``, and the CLI's dynamic inventory
finds every sourced preset under a unique dotted name, so nothing ships that
users cannot list. Second, physical correctness: the material composition
presets resolve to the right particle counts — hydrogen-1 is 1 proton and 0
neutrons, oxygen-16 is 8 and 8, tin-120 is 50 protons and 70 neutrons (hence
170 valence up quarks and 190 down), and an H2O formula unit totals 10
protons, 8 neutrons, and 10 electrons.
"""

from gpu_stack.cli import _iter_presets
from gpu_stack.presets import lithography, materials, nuclear, scenarios


def test_new_preset_modules_publish_expected_public_names():
    expected_names = {
        materials: {
            "source_hydrogen_1",
            "source_oxygen_16",
            "source_tin_120",
            "medium_h2o_h1_o16_composition",
        },
        lithography: {
            "ASML_EUV_REPETITION_RATE_HZ",
            "ASML_EUV_PULSE_PERIOD_S",
            "SOURCE_PLASMA_OPERATING_PRESETS",
            "asml_euv_tin_lpp_public_context",
            "source_tin_120_composition_assumption",
            "euv_tin120_lpp_source_boundary_assumption",
        },
        nuclear: {
            "SEMF_CALIBRATION_ROOTS",
            "semf_calibration_root_inventory",
            "semf_calibration_preset",
        },
        scenarios: {
            "COST_PER_TOKEN_TARGET",
            "DENSE_TRAINING_COST_TARGETS",
            "EUV_TIN120_SOURCE_TARGETS",
            "SOURCED_SCENARIO_PACKS",
            "dense_training_cost_inputs",
            "dense_training_cost_fixture",
            "euv_tin120_lpp_source_context_assumption",
            "pythia_70m_dgx_h100_single_node_run_closure",
            "pythia_70m_dgx_h100_us_2024_industrial_power",
        },
    }

    for module, names in expected_names.items():
        assert names <= set(module.__all__)
        assert all(hasattr(module, name) for name in names)


def test_dynamic_cli_inventory_discovers_new_presets_and_unique_sourced_packs():
    inventory = dict(_iter_presets())
    expected_inventory_names = {
        "materials.source_tin_120",
        "lithography.asml_euv_tin_lpp_public_context",
        "lithography.source_tin_120_composition_assumption",
        "lithography.euv_tin120_lpp_source_boundary_assumption",
        "scenarios.dense_training_cost_fixture",
        "scenarios.euv_tin120_lpp_source_context_assumption",
        "scenarios.pythia_70m_dgx_h100_us_2024_industrial_power",
    }

    assert expected_inventory_names <= set(inventory)
    assert inventory["materials.source_tin_120"] is materials.source_tin_120
    assert (
        inventory["lithography.euv_tin120_lpp_source_boundary_assumption"]
        is lithography.euv_tin120_lpp_source_boundary_assumption
    )
    assert (
        inventory["scenarios.euv_tin120_lpp_source_context_assumption"]
        is scenarios.euv_tin120_lpp_source_context_assumption
    )

    pack_names = [preset.name for preset in scenarios.SOURCED_SCENARIO_PACKS]
    assert len(pack_names) == len(set(pack_names))
    assert {
        f"scenarios.{preset.name}" for preset in scenarios.SOURCED_SCENARIO_PACKS
    } <= set(inventory)


def test_material_source_composition_presets_resolve_nuclear_counts():
    hydrogen = materials.source_hydrogen_1
    oxygen = materials.source_oxygen_16
    tin = materials.source_tin_120

    assert hydrogen.source
    assert oxygen.source
    assert tin.source
    assert float(hydrogen.resolve("physical.lithography.source_proton_count").value) == 1
    assert float(hydrogen.resolve("physical.lithography.source_neutron_count").value) == 0
    assert float(oxygen.resolve("physical.lithography.source_proton_count").value) == 8
    assert float(oxygen.resolve("physical.lithography.source_neutron_count").value) == 8
    assert tin.assignments == {
        "physical.lithography.source_proton_count": 50,
        "physical.lithography.source_neutron_count": 70,
    }
    assert (
        float(
            tin.resolve(
                "physical.lithography.source_valence_up_quark_count"
            ).value
        )
        == 170
    )
    assert (
        float(
            tin.resolve(
                "physical.lithography.source_valence_down_quark_count"
            ).value
        )
        == 190
    )


def test_material_medium_composition_preset_resolves_formula_counts():
    preset = materials.medium_h2o_h1_o16_composition

    assert preset.source
    assert (
        preset.assignments["physical.lithography.medium_component_a_stoichiometric_count"]
        == 2
    )
    assert (
        preset.assignments["physical.lithography.medium_component_b_stoichiometric_count"]
        == 1
    )
    assert (
        float(
            preset.resolve(
                "physical.lithography.medium_formula_unit_proton_count"
            ).value
        )
        == 10
    )
    assert (
        float(
            preset.resolve(
                "physical.lithography.medium_formula_unit_neutron_count"
            ).value
        )
        == 8
    )
    assert (
        float(
            preset.resolve(
                "physical.lithography.medium_formula_unit_electron_count"
            ).value
        )
        == 10
    )
