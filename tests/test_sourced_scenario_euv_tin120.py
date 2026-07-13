"""EUV tin-120 sourced-scenario contracts."""

import pytest

from gpu_stack import Registry
from gpu_stack.presets import lithography, materials, scenarios

from tests.test_sourced_scenarios import (
    CALIBRATION_ASSIGNMENT_MARKERS,
    EUV_TIN120_SCENARIO_NAME,
    FORBIDDEN_EUV_TIN_SOURCE_ROOTS,
    _is_training_economics_scenario_pack,
    _public_advertised_targets_for,
    _public_sourced_scenario_packs,
    _semf_calibration_roots,
    _sourced_scenario_packs,
)


def test_euv_tin120_source_context_pack_composes_existing_presets():
    preset = scenarios.euv_tin120_lpp_source_context_assumption
    assignments = dict(preset.assignments)
    expected_assignments = {
        **dict(materials.source_tin_120.assignments),
        **dict(lithography.asml_euv_tin_lpp_public_context.assignments),
    }
    source_text = preset.source or ""
    lower_source = source_text.lower()

    assert preset in scenarios.SOURCED_SCENARIO_PACKS
    assert "tin120" in preset.name
    assert "assumption" in preset.name
    assert "Assumption-labeled" in preset.description
    assert assignments == expected_assignments
    assert "source_tin_120:" in source_text
    assert "asml_euv_tin_lpp_public_context:" in source_text
    assert "scenario-layer tin-120 assumption" in lower_source
    assert "not isotope selection" in lower_source


def test_euv_tin120_source_context_is_assumption_not_numeric_calibration():
    preset = scenarios.euv_tin120_lpp_source_context_assumption
    targets = dict(_public_advertised_targets_for(preset))
    assignments = set(preset.assignments)
    semf_calibration_roots = _semf_calibration_roots()

    assert preset.name == EUV_TIN120_SCENARIO_NAME
    assert preset in _public_sourced_scenario_packs()
    assert "assumption" in preset.name.lower()
    assert "assumption" in preset.description.lower()
    assert "calibration" not in preset.name.lower()
    assert "numeric calibration" not in preset.description.lower()
    assert "scenario-layer tin-120 assumption" in (preset.source or "").lower()
    assert "not isotope selection" in (preset.source or "").lower()
    assert not assignments & semf_calibration_roots
    assert not any(
        marker in name
        for marker in CALIBRATION_ASSIGNMENT_MARKERS
        for name in assignments
    )
    assert not any(target in semf_calibration_roots for target in targets.values())
    assert targets == dict(scenarios.EUV_TIN120_SOURCE_TARGETS)


def test_euv_tin120_source_context_pack_contract_is_explicit():
    preset = scenarios.euv_tin120_lpp_source_context_assumption
    sourced_pack_names = {pack.name for pack in scenarios.SOURCED_SCENARIO_PACKS}
    non_root_assignments = [
        name
        for name in preset.assignments
        if not Registry.variables[name].is_root_input
    ]

    assert preset.name in sourced_pack_names
    assert preset in _sourced_scenario_packs()
    assert preset.require_source() is preset
    assert preset.has_source()
    assert preset.variants == {}
    assert non_root_assignments == []
    assert not _is_training_economics_scenario_pack(preset)


@pytest.mark.parametrize(
    ("label", "expected", "expect_trace"),
    [
        # Proton/neutron counts are the composition roots now, so they are
        # direct boundary assignments with no derivation trace.
        ("source_proton_count", 50.0, False),
        ("source_neutron_count", 70.0, False),
        ("pulse_repetition_rate", lithography.ASML_EUV_REPETITION_RATE_HZ, True),
    ],
)
def test_euv_tin120_source_context_resolves_counts_and_repetition_rate(
    label,
    expected,
    expect_trace,
):
    preset = scenarios.euv_tin120_lpp_source_context_assumption
    target = scenarios.EUV_TIN120_SOURCE_TARGETS[label]
    result = preset.resolve(target)

    assert float(result.value) == pytest.approx(expected)
    assert result.missing == set()
    assert result.violated_constraints == []
    if expect_trace:
        assert result.trace
    else:
        assert result.trace == []


def test_euv_tin120_source_context_resolves_all_advertised_targets():
    preset = scenarios.euv_tin120_lpp_source_context_assumption
    expected_by_label = {
        "source_proton_count": 50.0,
        "source_neutron_count": 70.0,
        "pulse_repetition_rate": lithography.ASML_EUV_REPETITION_RATE_HZ,
    }

    assert set(scenarios.EUV_TIN120_SOURCE_TARGETS) == set(expected_by_label)

    for label, target in scenarios.EUV_TIN120_SOURCE_TARGETS.items():
        result = preset.resolve(target)

        assert not result.missing, label
        assert not result.unresolved_inputs, label
        assert not result.violated_constraints, label
        assert not result.value.free_symbols, label
        assert float(result.value) == pytest.approx(expected_by_label[label])


def test_euv_tin120_source_context_does_not_assign_unsourced_plasma_roots():
    preset = scenarios.euv_tin120_lpp_source_context_assumption

    assert not FORBIDDEN_EUV_TIN_SOURCE_ROOTS & set(preset.assignments)
    assert any("does not assign drive fluence" in note for note in preset.notes)
    assert any("species pressure" in note for note in preset.notes)
    assert any("gas temperature" in note for note in preset.notes)
