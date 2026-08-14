"""Contract tests for sourced scenario packs, and the shared markers they use.

A "sourced" pack is a preset whose numbers trace to citable documents. That
label is easy to fake, so this file defines the discovery rules and enforces
them: a pack with a synthetic or demo marker in its name or source text is
excluded even if it also cites a URL or a vendor, every accepted pack must
carry an official-or-cited source token, advertise registered targets, and —
for training-economics packs — cover hardware, workload, and economics
assignments with explicit dense/moe variant choices.

These tests intentionally do not duplicate ``tests/test_scenarios.py``. The
dense-training cost fixture there is synthetic; this file specifies what any
future cited pack must satisfy. The marker tuples and helper functions here
are also imported by the per-pack contract test modules.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from math import isfinite

import pytest

from gpu_stack import Registry
from gpu_stack.core import Preset
from gpu_stack.core.resolver import AmbiguousVariant, ResolverError, Underdetermined
from gpu_stack.presets import hardware, lithography, materials, scenarios


USER_FACING_TARGETS: Mapping[str, str] = {
    "cost_per_token": "econ.cost.per_token",
    "tokens_per_second": "training.tokens_per_sec",
    "job_dc_power": "econ.job.dc_power",
    "run_power_cost": "econ.run.power_cost",
}

EXPECTED_TRACE_EQUATION = {
    "econ.cost.per_token": "econ.eq.cost_per_token",
    "training.tokens_per_sec": "training.eq.tokens_per_sec",
    "econ.job.dc_power": "econ.eq.job_dc_power",
    "econ.run.power_cost": "econ.eq.run_power_cost",
}

SYNTHETIC_SOURCE_MARKERS = (
    "synthetic resolver fixture",
    "round-number assumption",
    "round-number dense training",
    "not historical data",
    "not calibrated",
    "gpu_stack/demo.py",
    "gpu_stack.demo",
    "placeholder",
    "toy scenario",
    "demo fixture",
    "scratch scenario",
    "assumption-only",
)

SYNTHETIC_NAME_MARKERS = (
    "synthetic",
    "fixture",
    "demo",
    "toy",
    "scratch",
)

OFFICIAL_OR_CITED_SOURCE_TOKENS = (
    "https://",
    "http://",
    "doi:",
    "arxiv",
    "isbn",
    "issn",
    "datasheet",
    "data sheet",
    "whitepaper",
    "technical report",
    "benchmark",
    "measured",
    "official",
    "vendor",
    "standard",
    "specification",
    "nist",
    "iupac/ciaaw",
    "nvidia",
    "amd",
    "intel",
    "mlperf",
    "spec.org",
    "open compute project",
    "ocp",
    "ieee",
    "iso",
    "iec",
    "acm",
    "u.s. energy information administration",
    "eia",
    "u.s. bureau of labor statistics",
    "bls",
    "federal reserve",
    "fred",
    "department of energy",
    "doe",
)

HARDWARE_PREFIXES = (
    "gpu.",
    "cluster.node.",
    "cluster.rack.",
    "cluster.site.",
    "interconnect.",
)

WORKLOAD_ASSIGNMENT_PREFIXES = (
    "arch.",
    "par.",
    "training.",
)

ECONOMICS_PREFIXES = (
    "econ.",
    "thermal.facility.",
)

FORBIDDEN_EUV_TIN_SOURCE_ROOTS = {
    "physical.lithography.source_plasma_drive_pulse_fluence",
    "physical.lithography.source_plasma_species_partial_pressure",
    "physical.lithography.source_plasma_species_gas_temperature",
}

EUV_TIN120_SCENARIO_NAME = "euv_tin120_lpp_source_context_assumption"
PYTHIA_DGX_H100_ENERGY_FLOOR_SCENARIO_NAME = (
    "pythia_70m_dgx_h100_us_2024_industrial_energy_floor_cost"
)

CALIBRATION_ASSIGNMENT_MARKERS = (
    "binding_volume_coefficient",
    "binding_surface_coefficient",
    "binding_coulomb_coefficient",
    "binding_asymmetry_coefficient",
    "pairing_gap_reference_energy",
)

EXPLICIT_ASSUMPTION_CLOSURE_MARKERS = (
    "assumption",
    "closure",
    "explicit",
    "scenario-layer",
    "operating-boundary",
    "boundary selection",
)

NON_FACT_CLOSURE_MARKERS = (
    "not benchmark",
    "not a benchmark",
    "not measured",
    "not measurement",
    "not sourced",
    "not vendor",
    "not historical",
    "assumption",
    "closure",
)

PYTHIA_DGX_H100_SOURCE_MARKERS = (
    "nvidia",
    "dgx h100",
    "h100",
    "eleutherai",
    "pythia",
    "u.s. energy information administration",
    "eia",
)


def _required_scenarios_api(name: str) -> object:
    value = getattr(scenarios, name, None)
    if value is None:
        pytest.fail(f"missing public scenarios API: gpu_stack.presets.scenarios.{name}")
    return value


def _required_public_scenario_preset(name: str) -> Preset:
    value = _required_scenarios_api(name)
    if not isinstance(value, Preset):
        pytest.fail(f"gpu_stack.presets.scenarios.{name} must be a Preset")
    return value


def _public_sourced_scenario_packs() -> tuple[Preset, ...]:
    inventory = _required_scenarios_api("SOURCED_SCENARIO_PACKS")
    try:
        raw_items = tuple(inventory)
    except TypeError:
        pytest.fail("SOURCED_SCENARIO_PACKS must be an iterable of Preset objects")

    packs: list[Preset] = []
    for item in raw_items:
        preset = getattr(scenarios, item, None) if isinstance(item, str) else item
        if not isinstance(preset, Preset):
            pytest.fail(
                "SOURCED_SCENARIO_PACKS must contain Preset objects or names "
                f"of Preset objects, got {item!r}"
            )
        packs.append(preset)
    return tuple(packs)


def _public_sourced_pack_names() -> set[str]:
    return {preset.name for preset in _public_sourced_scenario_packs()}


def _public_advertised_targets_for(preset: Preset) -> tuple[tuple[str, str], ...]:
    scenario_targets_for = getattr(scenarios, "scenario_targets_for", None)
    if callable(scenario_targets_for):
        try:
            raw_targets = scenario_targets_for(preset)
        except Exception as exc:  # pragma: no cover - assertion message path
            pytest.fail(
                f"scenario_targets_for({preset.name!r}) failed: "
                f"{type(exc).__name__}: {exc}"
            )
    else:
        target_sets = _required_scenarios_api("SCENARIO_TARGET_SETS")
        try:
            raw_targets = target_sets[preset.name]
        except KeyError:
            pytest.fail(f"{preset.name!r} is missing from SCENARIO_TARGET_SETS")

    if hasattr(raw_targets, "items"):
        raw_targets = raw_targets.items()
    try:
        targets = tuple(raw_targets)
    except TypeError:
        pytest.fail(f"{preset.name!r} advertised targets must be iterable")

    normalized: list[tuple[str, str]] = []
    for entry in targets:
        if not isinstance(entry, tuple) or len(entry) != 2:
            pytest.fail(f"{preset.name!r} has malformed advertised target {entry!r}")
        label, target = entry
        if not isinstance(label, str) or not label.strip():
            pytest.fail(f"{preset.name!r} has malformed target label {label!r}")
        if not isinstance(target, str) or not target.strip():
            pytest.fail(f"{preset.name!r} has malformed target variable {target!r}")
        normalized.append((label, target))
    return tuple(normalized)


def _semf_calibration_roots() -> set[str]:
    try:
        from gpu_stack.presets import nuclear
    except ImportError as exc:  # pragma: no cover - assertion message path
        pytest.fail(f"missing public nuclear calibration API: {exc}")

    roots = getattr(nuclear, "SEMF_CALIBRATION_ROOTS", None)
    if roots is None:
        pytest.fail("missing public nuclear API: SEMF_CALIBRATION_ROOTS")
    return set(roots)


def _iter_inventory() -> Iterable[Preset]:
    inventory = getattr(scenarios, "SOURCED_SCENARIO_PACKS", None)
    if inventory is None:
        inventory = getattr(scenarios, "CALIBRATED_SCENARIO_PACKS", None)
    if inventory is not None:
        for item in inventory:
            yield getattr(scenarios, item) if isinstance(item, str) else item
        return

    for value in vars(scenarios).values():
        if isinstance(value, Preset):
            yield value


def _is_sourced_scenario_pack(preset: Preset) -> bool:
    source_text = (preset.source or "").lower()
    if not source_text:
        return False
    if any(marker in source_text for marker in SYNTHETIC_SOURCE_MARKERS):
        return False
    name = preset.name.lower()
    if any(marker in name for marker in SYNTHETIC_NAME_MARKERS):
        return False
    return bool(preset.assignments)


def _source_summaries(preset: Preset) -> list[str]:
    return [part.strip() for part in (preset.source or "").split("|")]


def _has_official_or_cited_source_token(source_text: str) -> bool:
    lower_source = source_text.lower()
    return any(token in lower_source for token in OFFICIAL_OR_CITED_SOURCE_TOKENS)


def _contains_marker(source_text: str, markers: tuple[str, ...]) -> bool:
    lower_source = source_text.lower()
    return any(marker in lower_source for marker in markers)


def _assert_resolves_cleanly(
    preset: Preset,
    targets: Iterable[tuple[str, str]],
) -> None:
    failures: list[str] = []

    for label, target in targets:
        try:
            result = preset.resolve(target)
        except (AmbiguousVariant, ResolverError, Underdetermined) as exc:
            failures.append(f"{label}: {type(exc).__name__}: {exc}")
            continue

        number = _clean_numeric_value(result.value)
        if result.missing:
            failures.append(f"{label}: missing {sorted(result.missing)}")
            continue
        if result.unresolved_inputs:
            names = sorted(item.variable for item in result.unresolved_inputs)
            failures.append(f"{label}: unresolved inputs {names}")
            continue
        if result.violated_constraints:
            equations = sorted(v.equation for v in result.violated_constraints)
            failures.append(f"{label}: violated constraints {equations}")
            continue
        violated_approximation_validity = [
            check
            for check in result.approximation_validity
            if check.satisfied is False
        ]
        if violated_approximation_validity:
            equations = sorted(
                check.equation for check in violated_approximation_validity
            )
            failures.append(f"{label}: violated approximation validity {equations}")
            continue
        if number is None or number <= 0:
            failures.append(f"{label}: nonpositive/nonfinite value {result.value}")
            continue

        expected_equation = EXPECTED_TRACE_EQUATION.get(target)
        if expected_equation is None:
            continue
        trace_equations = {step.equation for step in result.trace}
        if expected_equation not in trace_equations:
            failures.append(f"{label}: trace missing {expected_equation}")

    assert not failures, f"{preset.name} target failures: {failures}"


def _sourced_scenario_packs() -> list[Preset]:
    seen: set[str] = set()
    packs: list[Preset] = []
    for preset in _iter_inventory():
        assert isinstance(preset, Preset)
        if preset.name in seen:
            continue
        seen.add(preset.name)
        if _is_sourced_scenario_pack(preset):
            packs.append(preset)
    return packs


def _require_sourced_scenario_packs() -> list[Preset]:
    packs = _sourced_scenario_packs()
    if not packs:
        pytest.skip("no sourced/calibrated scenario packs have landed yet")
    return packs


def _is_training_economics_scenario_pack(preset: Preset) -> bool:
    return (
        bool(preset.variants)
        and _has_assignment_with_prefix(preset, HARDWARE_PREFIXES)
        and _has_assignment_with_prefix(preset, WORKLOAD_ASSIGNMENT_PREFIXES)
        and _has_assignment_with_prefix(preset, ECONOMICS_PREFIXES)
    )


def _require_training_economics_scenario_packs() -> list[Preset]:
    packs = [
        preset
        for preset in _require_sourced_scenario_packs()
        if _is_training_economics_scenario_pack(preset)
    ]
    if not packs:
        pytest.skip("no sourced training/economics scenario packs have landed yet")
    return packs


def _has_assignment_with_prefix(preset: Preset, prefixes: tuple[str, ...]) -> bool:
    return any(name.startswith(prefixes) for name in preset.assignments)


def _clean_numeric_value(value: object) -> float | None:
    if getattr(value, "free_symbols", set()):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def test_sourced_scenario_discovery_excludes_existing_synthetic_fixture():
    assert not _is_sourced_scenario_pack(scenarios.dense_training_cost_inputs)
    assert not _is_sourced_scenario_pack(scenarios.dense_training_cost_fixture)
    assert scenarios.dense_training_cost_fixture not in _sourced_scenario_packs()


def test_sourced_scenario_discovery_rejects_synthetic_or_demo_with_citations():
    synthetic_with_url = Preset(
        name="official_synthetic_fixture",
        description="Synthetic fixture that cites a URL but is still not sourced.",
        assignments={"cluster.rack.n_nodes": 1},
        source=(
            "Synthetic resolver fixture with a placeholder cited URL: "
            "https://example.com/specification. Not historical data."
        ),
    )
    demo_with_vendor_source = Preset(
        name="demo_vendor_fixture",
        description="Demo fixture that cites a vendor string but remains a demo.",
        assignments={"cluster.node.n_gpus": 8},
        source=(
            "NVIDIA vendor specification citation kept beside a demo fixture; "
            "this is a toy scenario, not calibrated."
        ),
    )

    assert not _is_sourced_scenario_pack(synthetic_with_url)
    assert not _is_sourced_scenario_pack(demo_with_vendor_source)
    assert not _is_sourced_scenario_pack(hardware.demo_rack)
    assert hardware.demo_rack not in _public_sourced_scenario_packs()


def test_sourced_scenario_packs_are_provenanced_combined_presets():
    for preset in _require_sourced_scenario_packs():
        source_text = preset.source or ""
        lower_source = source_text.lower()
        summaries = _source_summaries(preset)

        assert preset.description
        assert preset.assignments
        assert source_text.strip(), preset.name
        assert summaries, preset.name
        assert all(summary for summary in summaries), preset.name
        assert _has_official_or_cited_source_token(source_text), preset.name
        assert all(marker not in lower_source for marker in SYNTHETIC_SOURCE_MARKERS)
        assert all(
            marker not in preset.name.lower()
            for marker in SYNTHETIC_NAME_MARKERS
        )


def test_sourced_scenario_packs_have_registered_advertised_targets():
    packs = _public_sourced_scenario_packs()

    assert packs, "SOURCED_SCENARIO_PACKS must advertise at least one sourced pack"

    for preset in packs:
        assert preset.has_source(), preset.name
        assert preset.require_source() is preset

        targets = _public_advertised_targets_for(preset)
        labels = [label for label, _target in targets]

        assert targets, f"{preset.name} must advertise at least one target"
        assert len(labels) == len(set(labels)), preset.name
        for label, target in targets:
            assert target in Registry.variables, (preset.name, label, target)


def test_sourced_training_economics_scenario_packs_cover_required_layers():
    for preset in _require_training_economics_scenario_packs():
        assert _has_assignment_with_prefix(preset, HARDWARE_PREFIXES), preset.name
        assert _has_assignment_with_prefix(preset, WORKLOAD_ASSIGNMENT_PREFIXES), (
            preset.name
        )
        assert _has_assignment_with_prefix(preset, ECONOMICS_PREFIXES), preset.name
        assert preset.variants.get("training.flops_per_step") in {"dense", "moe"}
        assert preset.variants.get("training.scaling_params") in {"dense", "moe"}
