"""Contract tests for training-economics sourced scenario packs.

A training-economics pack must earn its "sourced" label: hardware and
workload numbers trace to official documents, while the assumptions that
close the cost model (like zero capex in an energy-floor pack) are declared
as closures, never dressed up as facts. These tests focus on the Pythia DGX
H100 energy-floor pack — public, sourced, with provenance split into fact
summaries and closure summaries — and then sweep every training-economics
pack to confirm the user-facing targets resolve cleanly through the expected
equations. Shared markers and helpers come from test_sourced_scenarios.
"""

from gpu_stack import Registry
from gpu_stack.core.resolver import AmbiguousVariant, ResolverError, Underdetermined

from tests.test_sourced_scenarios import (
    EXPLICIT_ASSUMPTION_CLOSURE_MARKERS,
    EXPECTED_TRACE_EQUATION,
    NON_FACT_CLOSURE_MARKERS,
    PYTHIA_DGX_H100_ENERGY_FLOOR_SCENARIO_NAME,
    PYTHIA_DGX_H100_SOURCE_MARKERS,
    SYNTHETIC_NAME_MARKERS,
    SYNTHETIC_SOURCE_MARKERS,
    USER_FACING_TARGETS,
    _assert_resolves_cleanly,
    _clean_numeric_value,
    _contains_marker,
    _has_official_or_cited_source_token,
    _is_training_economics_scenario_pack,
    _public_advertised_targets_for,
    _public_sourced_pack_names,
    _public_sourced_scenario_packs,
    _require_training_economics_scenario_packs,
    _required_public_scenario_preset,
    _source_summaries,
    _sourced_scenario_packs,
)


def test_pythia_dgx_h100_energy_floor_cost_pack_is_public_and_sourced():
    preset = _required_public_scenario_preset(
        PYTHIA_DGX_H100_ENERGY_FLOOR_SCENARIO_NAME
    )
    targets = dict(_public_advertised_targets_for(preset))
    lower_name = preset.name.lower()
    lower_description = preset.description.lower()

    assert preset.name == PYTHIA_DGX_H100_ENERGY_FLOOR_SCENARIO_NAME
    assert preset.name in _public_sourced_pack_names()
    assert preset in _public_sourced_scenario_packs()
    assert preset in _sourced_scenario_packs()
    assert preset.require_source() is preset
    assert _is_training_economics_scenario_pack(preset)
    assert {"pythia", "dgx", "h100", "energy", "floor", "cost"} <= set(
        lower_name.split("_")
    )
    assert "energy" in lower_description or "electricity" in lower_description
    assert "floor" in lower_description
    assert "cost" in lower_description
    assert set(USER_FACING_TARGETS) <= set(targets)
    assert all(target in Registry.variables for target in targets.values())


def test_pythia_dgx_h100_energy_floor_cost_provenance_splits_facts_and_closures():
    preset = _required_public_scenario_preset(
        PYTHIA_DGX_H100_ENERGY_FLOOR_SCENARIO_NAME
    )
    source_text = preset.source or ""
    notes_text = " ".join(preset.notes)
    contract_text = f"{source_text} {notes_text}"
    lower_source = source_text.lower()
    summaries = _source_summaries(preset)
    fact_summaries = [
        summary
        for summary in summaries
        if _has_official_or_cited_source_token(summary)
        and not _contains_marker(summary, EXPLICIT_ASSUMPTION_CLOSURE_MARKERS)
    ]
    closure_summaries = [
        summary
        for summary in summaries
        if _contains_marker(summary, EXPLICIT_ASSUMPTION_CLOSURE_MARKERS)
    ]

    assert summaries, preset.name
    assert fact_summaries, preset.name
    assert closure_summaries, preset.name
    assert _has_official_or_cited_source_token(source_text)
    assert all(marker in lower_source for marker in PYTHIA_DGX_H100_SOURCE_MARKERS)
    assert _contains_marker(contract_text, EXPLICIT_ASSUMPTION_CLOSURE_MARKERS)
    assert _contains_marker(contract_text, NON_FACT_CLOSURE_MARKERS)
    assert all(marker not in lower_source for marker in SYNTHETIC_SOURCE_MARKERS)
    assert all(
        marker not in preset.name.lower()
        for marker in SYNTHETIC_NAME_MARKERS
    )


def test_pythia_dgx_h100_energy_floor_cost_resolves_all_advertised_targets():
    preset = _required_public_scenario_preset(
        PYTHIA_DGX_H100_ENERGY_FLOOR_SCENARIO_NAME
    )
    targets = _public_advertised_targets_for(preset)
    target_map = dict(targets)

    assert set(USER_FACING_TARGETS) <= set(target_map)
    for label, target in targets:
        assert target.startswith(("training.", "econ.")), (label, target)

    _assert_resolves_cleanly(preset, targets)


def test_sourced_scenario_packs_resolve_user_facing_targets_cleanly():
    for preset in _require_training_economics_scenario_packs():
        failures: list[str] = []
        resolved: list[tuple[str, float, set[str]]] = []

        for label, target in USER_FACING_TARGETS.items():
            try:
                result = preset.resolve(target)
            except (AmbiguousVariant, ResolverError, Underdetermined) as exc:
                failures.append(f"{label}: {type(exc).__name__}: {exc}")
                continue

            number = _clean_numeric_value(result.value)
            if result.missing:
                failures.append(f"{label}: missing {sorted(result.missing)}")
                continue
            if result.violated_constraints:
                equations = sorted(v.equation for v in result.violated_constraints)
                failures.append(f"{label}: violated constraints {equations}")
                continue
            if number is None or number <= 0:
                failures.append(f"{label}: nonpositive/nonfinite value {result.value}")
                continue

            trace_equations = {step.equation for step in result.trace}
            expected_equation = EXPECTED_TRACE_EQUATION[target]
            if expected_equation not in trace_equations:
                failures.append(f"{label}: trace missing {expected_equation}")
                continue
            resolved.append((target, number, trace_equations))

        assert resolved, f"{preset.name} resolved no user-facing targets: {failures}"
