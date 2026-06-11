"""
Coverage for end-to-end scenario presets in gpu_stack.presets.scenarios.
"""

from math import isfinite

import pytest

from gpu_stack import Registry
from gpu_stack.presets import scenarios


EXPECTED_TRACE_EQUATIONS = {
    "training.tokens_per_sec": "training.eq.tokens_per_sec",
    "econ.job.dc_power": "econ.eq.job_dc_power",
    "econ.run.power_cost": "econ.eq.run_power_cost",
    "econ.run.total_cost": "econ.eq.run_total",
    "econ.cost.per_token": "econ.eq.cost_per_token",
}

PYTHIA_DGX_H100_TARGETS = (
    ("tokens_per_second", "training.tokens_per_sec"),
    ("job_dc_power", "econ.job.dc_power"),
    ("run_power_cost", "econ.run.power_cost"),
    ("cost_per_token", "econ.cost.per_token"),
)


def _training_economics_pack_names() -> set[str]:
    return {
        pack.name
        for pack in scenarios.SOURCED_SCENARIO_PACKS
        if pack.variants
        and any(name.startswith("training.") for name in pack.assignments)
        and any(name.startswith("econ.") for name in pack.assignments)
    }


def _pythia_dgx_h100_energy_floor_cost_pack():
    # Return the canonical Pythia-70M industrial-tariff energy-floor pack by name.
    # Multiple energy-floor packs exist (different model sizes and tariffs);
    # this helper returns the specific original pack to keep tests stable.
    name = scenarios.pythia_70m_dgx_h100_us_2024_industrial_energy_floor_cost.name
    matches = [
        pack
        for pack in scenarios.SOURCED_SCENARIO_PACKS
        if pack.name == name
    ]

    assert len(matches) == 1, (
        "expected exactly one pack named "
        f"{name!r}, found {[pack.name for pack in matches]}"
    )
    return matches[0]


def _assert_clean_resolution(preset, label: str, target: str):
    result = preset.resolve(target)

    assert not result.missing, label
    assert not result.unresolved_inputs, label
    assert not result.violated_constraints, label
    assert not result.value.free_symbols, label

    value = float(result.value)
    assert value > 0, label
    assert isfinite(value), label

    trace_equations = {step.equation for step in result.trace}
    assert EXPECTED_TRACE_EQUATIONS[target] in trace_equations
    return result


def test_scenario_target_registry_includes_dense_fixture_and_sourced_packs():
    expected_names = {
        scenarios.dense_training_cost_fixture.name,
        *(pack.name for pack in scenarios.SOURCED_SCENARIO_PACKS),
    }

    assert expected_names <= set(scenarios.SCENARIO_TARGET_SETS)

    for pack in scenarios.SOURCED_SCENARIO_PACKS:
        targets = scenarios.scenario_targets_for(pack)

        assert targets
        assert targets == scenarios.SCENARIO_TARGET_SETS[pack.name]
        assert scenarios.scenario_targets_for(pack.name) == targets


def test_scenario_target_registry_labels_are_stable():
    labels_by_name = {
        name: tuple(label for label, _target in scenarios.scenario_targets_for(name))
        for name in (
            scenarios.dense_training_cost_fixture.name,
            scenarios.pythia_70m_dgx_h100_us_2024_industrial_power.name,
            scenarios.euv_tin120_lpp_source_context_assumption.name,
        )
    }

    assert labels_by_name == {
        "dense_training_cost_fixture": tuple(scenarios.DENSE_TRAINING_COST_TARGETS),
        "pythia_70m_dgx_h100_us_2024_industrial_power": (
            "tokens_per_second",
            "job_dc_power",
            "run_power_cost",
            "cost_per_token",
        ),
        "euv_tin120_lpp_source_context_assumption": tuple(
            scenarios.EUV_TIN120_SOURCE_TARGETS
        ),
    }


def test_scenario_target_registry_variables_are_registered():
    for preset_name, targets in scenarios.SCENARIO_TARGET_SETS.items():
        labels = tuple(label for label, _target in targets)

        assert labels
        assert len(labels) == len(set(labels)), preset_name
        for label, target in targets:
            assert label
            assert target in Registry.variables, (preset_name, label, target)


def test_dense_training_cost_fixture_resolves_user_facing_targets():
    preset = scenarios.dense_training_cost_fixture

    assert preset.source
    assert preset.variants["training.flops_per_step"] == "dense"

    cost = preset.resolve(scenarios.COST_PER_TOKEN_TARGET)
    assert not cost.missing
    assert float(cost.value) == pytest.approx(3.000078e-6, rel=1e-12)

    trace_equations = {step.equation for step in cost.trace}
    assert "training.eq.t_step" in trace_equations
    assert "thermal.eq.dc_total_power" in trace_equations
    assert "econ.eq.job_dc_power" in trace_equations
    assert "econ.eq.run_power_cost" in trace_equations
    assert "econ.eq.cost_per_token" in trace_equations


def test_dense_training_cost_fixture_resolves_throughput_and_power():
    preset = scenarios.dense_training_cost_fixture

    tokens_per_second = preset.resolve(
        scenarios.DENSE_TRAINING_COST_TARGETS["tokens_per_second"]
    )
    job_dc_power = preset.resolve(scenarios.DENSE_TRAINING_COST_TARGETS["job_dc_power"])

    assert not tokens_per_second.missing
    assert not job_dc_power.missing
    assert float(tokens_per_second.value) == pytest.approx(6_666_666.666666667)
    assert float(job_dc_power.value) == pytest.approx(5200.0)


def test_dense_training_cost_fixture_assignment_overrides_recompute_result():
    base = scenarios.dense_training_cost_fixture
    overridden = base.with_overrides(
        assignments={
            "econ.job.capex_rate": 0.0,
        },
        name="dense_training_cost_fixture_no_capex",
    )

    cost = overridden.resolve(scenarios.COST_PER_TOKEN_TARGET)

    assert not cost.missing
    assert float(cost.value) == pytest.approx(7.8e-11, rel=1e-12)


def test_sourced_scenario_packs_include_pythia_dgx_h100_industrial_pack():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power

    assert preset in scenarios.SOURCED_SCENARIO_PACKS
    assert preset.name in {pack.name for pack in scenarios.SOURCED_SCENARIO_PACKS}
    assert all(pack.require_source() is pack for pack in scenarios.SOURCED_SCENARIO_PACKS)
    assert preset.name in _training_economics_pack_names()


def test_sourced_scenario_packs_include_euv_tin120_source_context_pack():
    preset = scenarios.euv_tin120_lpp_source_context_assumption

    assert preset in scenarios.SOURCED_SCENARIO_PACKS
    assert preset.name in {pack.name for pack in scenarios.SOURCED_SCENARIO_PACKS}
    assert preset.require_source() is preset
    assert preset.variants == {}
    assert preset.name not in _training_economics_pack_names()


def test_pythia_dgx_h100_industrial_pack_provenance_summary_is_useful():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power
    summary = preset.require_source().source_summary()

    assert summary["name"] == "pythia_70m_dgx_h100_us_2024_industrial_power"
    assert summary["has_source"] is True
    assert summary["assignment_count"] == len(preset.assignments)
    assert summary["variant_count"] == len(preset.variants)
    assert summary["note_count"] == len(preset.notes)

    source = summary["source"]
    assert isinstance(source, str)
    assert "dgx_h100_8gpu_node: NVIDIA H100 GPU product specifications" in source
    assert "pythia_70m_dense_training: EleutherAI Pythia repository" in source
    assert "us_2024_industrial_flat_power_tariff: U.S. Energy Information" in source
    assert "pythia_70m_dgx_h100_single_node_run_closure: Run closure" in source


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("training.tokens_per_sec", 1_268_976.30961386),
        ("econ.job.dc_power", 10_200.0),
        ("econ.run.power_cost", 54.4378103942861),
    ],
)
def test_pythia_dgx_h100_industrial_pack_resolves_user_facing_targets(
    target,
    expected,
):
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power
    result = preset.resolve(target)

    assert not result.missing
    assert not result.unresolved_inputs
    assert not result.violated_constraints
    assert not result.value.free_symbols

    value = float(result.value)
    assert value > 0
    assert value == pytest.approx(expected)

    trace_equations = {step.equation for step in result.trace}
    assert EXPECTED_TRACE_EQUATIONS[target] in trace_equations


def test_pythia_dgx_h100_industrial_pack_resolves_target_aliases_cleanly():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power

    for label, target in scenarios.scenario_targets_for(preset):
        if label == "cost_per_token":
            continue

        result = preset.resolve(target)

        assert not result.missing, target
        assert not result.violated_constraints, target
        assert not result.value.free_symbols, target


def test_pythia_dgx_h100_energy_floor_cost_pack_is_public_and_advertised():
    preset = _pythia_dgx_h100_energy_floor_cost_pack()

    assert getattr(scenarios, preset.name) is preset
    assert preset in scenarios.SOURCED_SCENARIO_PACKS
    assert preset.name in {pack.name for pack in scenarios.SOURCED_SCENARIO_PACKS}
    assert preset.name in scenarios.SCENARIO_TARGET_SETS
    assert preset.name in _training_economics_pack_names()

    targets = scenarios.scenario_targets_for(preset)

    assert set(PYTHIA_DGX_H100_TARGETS) <= set(targets)
    assert scenarios.scenario_targets_for(preset.name) == targets
    for label, target in targets:
        assert label
        assert target in Registry.variables, (preset.name, label, target)


def test_pythia_dgx_h100_energy_floor_cost_provenance_names_the_floor():
    preset = _pythia_dgx_h100_energy_floor_cost_pack()
    evidence = " ".join(
        part
        for part in (preset.description, preset.source or "", *preset.notes)
        if part
    )
    lower_evidence = evidence.lower()
    compact_evidence = lower_evidence.replace(" ", "")

    assert preset.require_source() is preset
    assert "energy floor" in lower_evidence or "energy-floor" in lower_evidence
    assert "cost floor" in lower_evidence or "cost-floor" in lower_evidence
    assert "electricity-only" in lower_evidence or "electricity only" in lower_evidence
    assert "fully allocated" in lower_evidence
    assert "econ.job.capex_rate=0" in compact_evidence
    assert "econ.run.opex_misc_cost=0" in compact_evidence
    assert preset.assignments["econ.job.capex_rate"] == 0
    assert preset.assignments["econ.run.opex_misc_cost"] == 0


def test_pythia_dgx_h100_energy_floor_cost_resolves_all_advertised_targets():
    preset = _pythia_dgx_h100_energy_floor_cost_pack()
    resolved = {
        label: _assert_clean_resolution(preset, label, target)
        for label, target in scenarios.scenario_targets_for(preset)
    }

    cost_per_token = resolved["cost_per_token"]
    run_power_cost = resolved["run_power_cost"]
    total_tokens = preset.resolve("training.total_tokens")
    trace_equations = {step.equation for step in cost_per_token.trace}

    assert float(cost_per_token.value) == pytest.approx(
        float(run_power_cost.value) / float(total_tokens.value)
    )
    assert "econ.eq.run_hw_cost" in trace_equations
    assert "econ.eq.run_total" in trace_equations
    assert "econ.eq.cost_per_token" in trace_equations
