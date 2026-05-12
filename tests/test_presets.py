"""
tests/test_presets.py
=====================

Coverage for the scenario-preset framework in `gpu_stack.core.presets`
and the concrete instances under `gpu_stack.presets.*`.
"""

import pytest

import gpu_stack
from gpu_stack.cli import _iter_presets
from gpu_stack.core import Preset, combine_presets
from gpu_stack.presets import hardware, lithography, materials, nuclear, scenarios, workload


def _field(obj, name):
    if isinstance(obj, dict):
        return obj[name]
    return getattr(obj, name)


def _optional_field(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _target_evaluations(report):
    targets = _optional_field(report, "targets")
    if targets is None:
        targets = _optional_field(report, "target_evaluations")
    if targets is None:
        targets = _optional_field(report, "evaluations")
    assert targets is not None
    return targets


def _target_evaluation(report, label):
    targets = _target_evaluations(report)
    if isinstance(targets, dict):
        return targets[label]
    return next(item for item in targets if _field(item, "label") == label)


def _family_key(summary):
    return _field(summary, "family")


def _summary_key(summary):
    return (
        _field(summary, "family"),
        _field(summary, "boundary_category"),
        _field(summary, "primitive_boundary"),
    )


def _missing_family_summaries(target):
    summaries = _optional_field(target, "missing_family_summaries")
    if summaries is None:
        summaries = _optional_field(target, "missing_families")
    assert summaries is not None
    return summaries


def test_preset_rejects_unknown_variable_name():
    with pytest.raises(ValueError, match="unknown variables"):
        Preset(
            name="bad",
            description="typo in variable name",
            assignments={"cluster.rack.n_NODES": 9},  # wrong case
        )


def test_preset_rejects_unknown_variant_name():
    with pytest.raises(ValueError, match="unknown variables"):
        Preset(
            name="bad",
            description="typo in variant variable name",
            variants={"training.flopz_per_step": "dense"},
        )


def test_preset_rejects_non_variant_selector():
    with pytest.raises(ValueError, match="invalid variant selector"):
        Preset(
            name="bad",
            description="valid variable, but not a variant family",
            variants={"cluster.rack.n_nodes": "dense"},
        )


def test_preset_rejects_unknown_variant_key():
    with pytest.raises(ValueError, match="variant key"):
        Preset(
            name="bad",
            description="valid variant family with a typoed key",
            variants={"training.flops_per_step": "denze"},
        )


def test_demo_rack_resolves_to_canonical_number():
    result = hardware.demo_rack.resolve("cluster.rack.peak_flops")
    assert float(result.value) == pytest.approx(1.08e18, rel=1e-12)


def test_combine_presets_merges_assignments_and_variants():
    combined = combine_presets(
        hardware.demo_rack,
        workload.dense_variant_selector,
        name="demo_rack_dense",
    )
    assert combined.assignments["cluster.rack.n_nodes"] == 9
    assert combined.variants["training.flops_per_step"] == "dense"
    assert "demo_rack" in (combined.source or "")


def test_combine_presets_override_order():
    # Later preset wins on collisions.
    a = Preset(name="a", description="", assignments={"cluster.rack.n_nodes": 9})
    b = Preset(name="b", description="", assignments={"cluster.rack.n_nodes": 18})
    merged = combine_presets(a, b, name="ab")
    assert merged.assignments["cluster.rack.n_nodes"] == 18


def test_workload_presets_pin_variant_keys():
    assert workload.dense_variant_selector.variants["training.flops_per_step"] == "dense"
    assert workload.dense_variant_selector.variants["training.scaling_params"] == "dense"
    assert workload.moe_variant_selector.variants["training.flops_per_step"] == "moe"
    assert workload.moe_variant_selector.variants["training.scaling_params"] == "moe"
    assert workload.adamw_optimizer_selector.variants["opt.param_next"] == "adamw"
    assert workload.muon_optimizer_selector.variants["opt.param_next"] == "muon"


def test_preset_with_overrides_returns_new_instance():
    base = hardware.demo_rack
    updated = base.with_overrides(assignments={"cluster.rack.n_nodes": 72})
    assert base.assignments["cluster.rack.n_nodes"] == 9
    assert updated.assignments["cluster.rack.n_nodes"] == 72
    assert updated.name.startswith("demo_rack")


def test_preset_copies_and_freezes_inputs():
    assignments = {"cluster.rack.n_nodes": 9}
    variants = {"training.flops_per_step": "dense"}
    notes = ["temporary note"]

    preset = Preset(
        name="frozen_inputs",
        description="temporary preset with mutable constructor inputs",
        assignments=assignments,
        variants=variants,
        notes=notes,
    )

    assignments["cluster.rack.n_nodes"] = 72
    variants["training.flops_per_step"] = "moe"
    notes.append("mutated")

    assert preset.assignments["cluster.rack.n_nodes"] == 9
    assert preset.variants["training.flops_per_step"] == "dense"
    assert preset.notes == ("temporary note",)
    with pytest.raises(TypeError):
        preset.assignments["cluster.rack.n_nodes"] = 18
    with pytest.raises(TypeError):
        preset.variants["training.flops_per_step"] = "moe"


def test_preset_with_overrides_revalidates_variants():
    with pytest.raises(ValueError, match="invalid variant selector"):
        workload.dense_variant_selector.with_overrides(
            variants={"training.flops_per_step": "denze"},
        )


def test_preset_variants_unlock_mfu_resolution():
    # training.mfu has two variants; dense_variant_selector does not cover
    # it, so resolving via demo_rack alone is insufficient. Combining with
    # mfu_from_flops_selector resolves the variant ambiguity.
    combined = combine_presets(
        hardware.demo_rack,
        workload.mfu_from_flops_selector,
        name="demo_rack_mfu",
    )
    assert combined.variants["training.mfu"] == "from_flops"


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
        "physical.lithography.source_valence_up_quark_count": 170,
        "physical.lithography.source_valence_down_quark_count": 190,
    }
    assert float(tin.resolve("physical.lithography.source_proton_count").value) == 50
    assert float(tin.resolve("physical.lithography.source_neutron_count").value) == 70


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


def test_preset_evaluate_targets_reports_resolved_target_artifact():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power

    report = preset.evaluate_targets(
        (("tokens_per_second", "training.tokens_per_sec"),)
    )
    target = _target_evaluation(report, "tokens_per_second")

    assert _field(target, "status") == "ok"
    assert _field(target, "target") == "training.tokens_per_sec"
    assert isinstance(_field(target, "value"), str)
    assert _field(target, "missing_count") == 0
    assert _field(target, "violated_constraint_count") == 0
    assert "training.eq.tokens_per_sec" in _field(target, "trace_equations")


def test_preset_evaluate_targets_reports_unresolved_cost_artifact_metadata():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power

    report = preset.evaluate_targets(
        (("cost_per_token", scenarios.COST_PER_TOKEN_TARGET),)
    )
    target = _target_evaluation(report, "cost_per_token")

    assert _field(target, "status") == "issues"
    assert _field(target, "target") == scenarios.COST_PER_TOKEN_TARGET
    assert _field(target, "missing_count") > 0
    assert _field(target, "violated_constraint_count") == 0

    unresolved_inputs = _field(target, "unresolved_inputs")
    diagnostics = {_field(item, "variable"): item for item in unresolved_inputs}
    assert "cluster.node.cpu.power_per_cpu" in diagnostics
    assert _field(diagnostics["cluster.node.cpu.power_per_cpu"], "family") == (
        "cluster.node"
    )
    assert _field(
        diagnostics["cluster.node.cpu.power_per_cpu"],
        "boundary_category",
    ) == "primitive-root"
    assert _field(
        diagnostics["cluster.node.cpu.power_per_cpu"],
        "primitive_boundary",
    ) is True

    summaries = {
        _family_key(summary): summary
        for summary in _missing_family_summaries(target)
    }
    assert "cluster.node" in summaries
    assert _field(summaries["cluster.node"], "count") > 0
    assert "cluster.node.storage_power" in _field(summaries["cluster.node"], "names")
    assert "econ.asset" in summaries
    assert "thermal.water" in summaries


def test_preset_evaluate_targets_report_exposes_aggregate_missing_families():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power

    report = preset.evaluate_targets(
        (("cost_per_token", scenarios.COST_PER_TOKEN_TARGET),)
    )
    target = _target_evaluation(report, "cost_per_token")

    report_summaries = {
        _family_key(summary): summary
        for summary in _missing_family_summaries(report)
    }
    target_summaries = {
        _family_key(summary): summary
        for summary in _missing_family_summaries(target)
    }

    assert "cluster.node" in report_summaries
    assert _field(report_summaries["cluster.node"], "count") == _field(
        target_summaries["cluster.node"],
        "count",
    )
    assert "cluster.node.storage_power" in _field(
        report_summaries["cluster.node"],
        "names",
    )
    assert "econ.asset" in report_summaries
    assert "thermal.water" in report_summaries

    data = report.to_dict()
    dict_summaries = {
        _family_key(summary): summary
        for summary in data["missing_family_summaries"]
    }
    assert dict_summaries.keys() == report_summaries.keys()
    assert "cluster.node.storage_power" in _field(
        dict_summaries["cluster.node"],
        "names",
    )
    assert data["targets"]["cost_per_token"]["missing_family_summaries"]


def test_preset_evaluate_targets_deduplicates_aggregate_missing_families():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power

    report = preset.evaluate_targets(
        (
            ("run_cost", scenarios.DENSE_TRAINING_COST_TARGETS["run_cost"]),
            ("cost_per_token", scenarios.COST_PER_TOKEN_TARGET),
        )
    )
    run_cost = _target_evaluation(report, "run_cost")
    cost_per_token = _target_evaluation(report, "cost_per_token")

    run_missing = set(_field(run_cost, "missing_names"))
    cost_missing = set(_field(cost_per_token, "missing_names"))
    aggregate_missing = {
        name
        for summary in _missing_family_summaries(report)
        for name in _field(summary, "names")
    }

    assert run_missing & cost_missing
    assert aggregate_missing == run_missing | cost_missing
    assert sum(
        _field(summary, "count")
        for summary in _missing_family_summaries(report)
    ) == len(aggregate_missing)
    assert len(aggregate_missing) < (
        _field(run_cost, "missing_count")
        + _field(cost_per_token, "missing_count")
    )

    report_summaries = {
        _summary_key(summary): summary
        for summary in _missing_family_summaries(report)
    }
    run_summaries = {
        _summary_key(summary): summary
        for summary in _missing_family_summaries(run_cost)
    }
    cost_summaries = {
        _summary_key(summary): summary
        for summary in _missing_family_summaries(cost_per_token)
    }
    assert report_summaries.keys() == run_summaries.keys() == cost_summaries.keys()
    for key, report_summary in report_summaries.items():
        assert _field(report_summary, "names") == _field(run_summaries[key], "names")
        assert _field(report_summary, "names") == _field(cost_summaries[key], "names")
        assert _field(report_summary, "count") == _field(run_summaries[key], "count")
        assert _field(report_summary, "count") == _field(cost_summaries[key], "count")

    for target in (run_cost, cost_per_token):
        assert sum(
            _field(summary, "count")
            for summary in _missing_family_summaries(target)
        ) == _field(target, "missing_count")


def test_preset_evaluate_targets_report_has_no_aggregate_missing_families_for_euv():
    preset = scenarios.euv_tin120_lpp_source_context_assumption

    report = preset.evaluate_targets(scenarios.EUV_TIN120_SOURCE_TARGETS.items())

    assert _field(report, "status") == "ok"
    assert _field(report, "issue_count") == 0
    assert _missing_family_summaries(report) == ()

    for target in _target_evaluations(report):
        assert _field(target, "status") == "ok"
        assert _missing_family_summaries(target) == ()

    data = report.to_dict()
    assert data["missing_family_summaries"] == ()


def test_preset_evaluate_targets_report_counts_and_dict_export():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power

    report = preset.evaluate_targets(
        (
            ("tokens_per_second", "training.tokens_per_sec"),
            ("cost_per_token", scenarios.COST_PER_TOKEN_TARGET),
        )
    )

    targets = _target_evaluations(report)
    assert _field(report, "issue_count") == sum(
        _field(target, "issue_count") for target in targets
    )
    assert _field(report, "issue_count") > 0
    assert _field(report, "assignment_count") == len(preset.assignments)
    assert _field(report, "variant_count") == len(preset.variants)
    assert _field(report, "ok_count") == 1
    assert _field(report, "issues_count") == 1
    assert _field(report, "error_count") == 0
    assert _field(report, "target_labels") == (
        "tokens_per_second",
        "cost_per_token",
    )
    assert _field(report, "ok_target_labels") == ("tokens_per_second",)
    assert _field(report, "issue_target_labels") == ("cost_per_token",)
    assert _field(report, "error_target_labels") == ()

    if hasattr(report, "to_dict"):
        data = report.to_dict()
        assert data["issue_count"] == _field(report, "issue_count")
        assert data["ok_count"] == 1
        assert data["issues_count"] == 1
        assert data["error_count"] == 0
        assert data["target_labels"] == (
            "tokens_per_second",
            "cost_per_token",
        )
        assert data["ok_target_labels"] == ("tokens_per_second",)
        assert data["issue_target_labels"] == ("cost_per_token",)
        assert data["error_target_labels"] == ()
        assert data["assignment_count"] == len(preset.assignments)
        assert data["variant_count"] == len(preset.variants)
        assert data["targets"]["tokens_per_second"]["status"] == "ok"
        assert data["targets"]["cost_per_token"]["status"] == "issues"


def test_preset_evaluate_targets_report_labels_error_targets():
    report = hardware.demo_rack.evaluate_targets(
        (
            ("peak_flops", "cluster.rack.peak_flops"),
            ("unknown_target", "not.a.registered.variable"),
        )
    )
    target = _target_evaluation(report, "unknown_target")

    assert _field(target, "status") == "error"
    assert _field(target, "issue_count") == 1
    assert _field(report, "issue_count") == 1
    assert _field(report, "ok_count") == 1
    assert _field(report, "issues_count") == 1
    assert _field(report, "error_count") == 1
    assert _field(report, "target_labels") == ("peak_flops", "unknown_target")
    assert _field(report, "ok_target_labels") == ("peak_flops",)
    assert _field(report, "issue_target_labels") == ("unknown_target",)
    assert _field(report, "error_target_labels") == ("unknown_target",)

    data = report.to_dict()
    assert data["issue_count"] == 1
    assert data["issues_count"] == 1
    assert data["error_count"] == 1
    assert data["issue_target_labels"] == ("unknown_target",)
    assert data["targets"]["unknown_target"]["status"] == "error"
