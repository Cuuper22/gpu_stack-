"""
Tests for the new sourced scenario packs in scenarios_cited_2026.

Covers:
  - Pythia-160M on DGX H100 with U.S. 2024 industrial electricity price.
  - Pythia-70M on DGX H100 with U.S. 2024 commercial electricity price.

Each pack family has a base power-cost pack and an energy-floor cost variant.
"""

from __future__ import annotations

from math import isfinite

import pytest

from gpu_stack import Registry
from gpu_stack.presets import scenarios
from gpu_stack.presets.scenarios_cited_2026 import (
    SCENARIO_TARGET_SETS_2026,
    SOURCED_SCENARIO_PACKS_2026,
    pythia_160m_dense_training,
    pythia_160m_dgx_h100_energy_floor_cost_closure,
    pythia_160m_dgx_h100_single_node_run_closure,
    pythia_160m_dgx_h100_us_2024_industrial_energy_floor_cost,
    pythia_160m_dgx_h100_us_2024_industrial_power,
    pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost,
    pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost_closure,
    pythia_70m_dgx_h100_us_2024_commercial_power,
    pythia_70m_dgx_h100_us_2024_commercial_run_closure,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TRAINING_ECON_TARGETS = (
    ("tokens_per_second", "training.tokens_per_sec"),
    ("job_dc_power", "econ.job.dc_power"),
    ("run_power_cost", "econ.run.power_cost"),
    ("cost_per_token", "econ.cost.per_token"),
)

_EXPECTED_TRACE_EQUATION = {
    "training.tokens_per_sec": "training.eq.tokens_per_sec",
    "econ.job.dc_power": "econ.eq.job_dc_power",
    "econ.run.power_cost": "econ.eq.run_power_cost",
    "econ.cost.per_token": "econ.eq.cost_per_token",
}


def _assert_resolves_cleanly(pack, label: str, target: str) -> float:
    result = pack.resolve(target)
    assert not result.missing, f"{label} missing: {sorted(result.missing)[:5]}"
    assert not result.unresolved_inputs, f"{label} unresolved_inputs"
    assert not result.violated_constraints, f"{label} violated_constraints"
    assert not result.value.free_symbols, f"{label} free_symbols"

    value = float(result.value)
    assert value > 0, f"{label} value not positive: {value}"
    assert isfinite(value), f"{label} value not finite: {value}"

    expected_eq = _EXPECTED_TRACE_EQUATION.get(target)
    if expected_eq is not None:
        trace_equations = {step.equation for step in result.trace}
        assert expected_eq in trace_equations, (
            f"{label}: trace missing {expected_eq}"
        )
    return value


# ---------------------------------------------------------------------------
# Registration and provenance tests
# ---------------------------------------------------------------------------

def test_2026_packs_are_in_sourced_scenario_packs():
    pack_names = {p.name for p in scenarios.SOURCED_SCENARIO_PACKS}

    for pack in SOURCED_SCENARIO_PACKS_2026:
        assert pack in scenarios.SOURCED_SCENARIO_PACKS, pack.name
        assert pack.name in pack_names, pack.name
        assert pack.require_source() is pack, pack.name


def test_2026_packs_are_in_scenario_target_sets():
    for pack in SOURCED_SCENARIO_PACKS_2026:
        assert pack.name in scenarios.SCENARIO_TARGET_SETS, pack.name
        targets = scenarios.scenario_targets_for(pack)
        assert targets
        assert scenarios.scenario_targets_for(pack.name) == targets


def test_2026_pack_target_variables_are_registered():
    for pack_name, targets in SCENARIO_TARGET_SETS_2026.items():
        labels = [label for label, _target in targets]
        assert labels, pack_name
        assert len(labels) == len(set(labels)), f"duplicate labels in {pack_name}"
        for label, target in targets:
            assert target in Registry.variables, (pack_name, label, target)


def test_2026_packs_have_dense_variant_selections():
    for pack in SOURCED_SCENARIO_PACKS_2026:
        assert pack.variants.get("training.flops_per_step") == "dense", pack.name
        assert pack.variants.get("training.scaling_params") == "dense", pack.name


def test_2026_packs_have_training_hardware_and_econ_assignments():
    for pack in SOURCED_SCENARIO_PACKS_2026:
        names = set(pack.assignments)
        assert any(n.startswith("gpu.") or n.startswith("cluster.node.") for n in names), (
            f"{pack.name} has no hardware assignments"
        )
        assert any(n.startswith("arch.") or n.startswith("training.") for n in names), (
            f"{pack.name} has no workload assignments"
        )
        assert any(n.startswith("econ.") or n.startswith("thermal.") for n in names), (
            f"{pack.name} has no economics assignments"
        )


def test_2026_packs_source_strings_contain_official_tokens():
    official_tokens = ("nvidia", "eleutherai", "pythia", "eia", "u.s. energy")

    for pack in SOURCED_SCENARIO_PACKS_2026:
        source = (pack.source or "").lower()
        assert source, f"{pack.name} has no source"
        assert any(token in source for token in official_tokens), (
            f"{pack.name} source does not name an official document"
        )


def test_2026_energy_floor_packs_are_labeled_assumptions():
    energy_floor_packs = [
        p for p in SOURCED_SCENARIO_PACKS_2026
        if "energy_floor" in p.name
    ]
    assert energy_floor_packs, "expected at least one energy-floor cost pack"

    for pack in energy_floor_packs:
        contract = " ".join([pack.source or ""] + list(pack.notes)).lower()
        assert "assumption" in contract or "closure" in contract, pack.name
        assert pack.assignments["econ.job.capex_rate"] == 0.0, pack.name
        assert pack.assignments["econ.run.opex_misc_cost"] == 0.0, pack.name


def test_2026_packs_no_synthetic_name_markers():
    synthetic_markers = ("synthetic", "fixture", "demo", "toy", "scratch")
    for pack in SOURCED_SCENARIO_PACKS_2026:
        lower_name = pack.name.lower()
        for marker in synthetic_markers:
            assert marker not in lower_name, (
                f"{pack.name} name contains synthetic marker {marker!r}"
            )


# ---------------------------------------------------------------------------
# Pythia-160M workload preset
# ---------------------------------------------------------------------------

def test_pythia_160m_workload_preset_source_and_assignments():
    assert pythia_160m_dense_training.has_source()
    assert "eleutherai" in pythia_160m_dense_training.source.lower()
    assert "pythia-160m" in pythia_160m_dense_training.source.lower()
    assert "https://github.com/EleutherAI/pythia" in pythia_160m_dense_training.source
    assert (
        "https://huggingface.co/EleutherAI/pythia-160m" in pythia_160m_dense_training.source
    )

    a = pythia_160m_dense_training.assignments
    assert a["arch.n_layers"] == 12
    assert a["arch.d_model"] == 768
    assert a["arch.d_ffn"] == 3072
    assert a["arch.n_heads"] == 12
    assert a["arch.vocab"] == 50304
    assert a["arch.seq_len"] == 2048
    assert a["arch.tokens_per_step"] == 2_097_152
    assert a["arch.output.untied_factor"] == 1
    assert a["training.total_tokens"] == 299_892_736_000

    assert pythia_160m_dense_training.variants["training.flops_per_step"] == "dense"
    assert pythia_160m_dense_training.variants["training.scaling_params"] == "dense"


def test_pythia_160m_workload_differs_from_70m():
    from gpu_stack.presets.workload import pythia_70m_dense_training

    a160 = pythia_160m_dense_training.assignments
    a70 = pythia_70m_dense_training.assignments

    assert a160["arch.n_layers"] != a70["arch.n_layers"]
    assert a160["arch.d_model"] != a70["arch.d_model"]
    assert a160["arch.d_ffn"] != a70["arch.d_ffn"]
    assert a160["arch.n_heads"] != a70["arch.n_heads"]
    assert a160["training.total_tokens"] == a70["training.total_tokens"]
    assert a160["arch.tokens_per_step"] == a70["arch.tokens_per_step"]


# ---------------------------------------------------------------------------
# Pythia-160M DGX H100 run closure
# ---------------------------------------------------------------------------

def test_pythia_160m_run_closure_has_source_and_values():
    assert pythia_160m_dgx_h100_single_node_run_closure.has_source()
    source = pythia_160m_dgx_h100_single_node_run_closure.source.lower()
    assert "nvidia" in source
    assert "dgx h100" in source

    a = pythia_160m_dgx_h100_single_node_run_closure.assignments
    assert a["arch.n_kv_heads"] == 12
    assert a["arch.ffn.weight_matrices"] == 2
    assert a["arch.norm.param_multiplier"] == 4
    assert a["par.n_gpus"] == 8
    assert a["gpu.peak_flops_power_limited"] == 67e12
    assert a["gpu.power.total"] == 700.0
    assert a["thermal.dc.total_power"] == pytest.approx(10_200.0)


# ---------------------------------------------------------------------------
# Pythia-160M industrial power pack
# ---------------------------------------------------------------------------

def test_pythia_160m_industrial_power_pack_is_registered():
    assert pythia_160m_dgx_h100_us_2024_industrial_power in scenarios.SOURCED_SCENARIO_PACKS
    assert pythia_160m_dgx_h100_us_2024_industrial_power.require_source() is (
        pythia_160m_dgx_h100_us_2024_industrial_power
    )


def test_pythia_160m_industrial_power_pack_provenance_names_all_sources():
    source = pythia_160m_dgx_h100_us_2024_industrial_power.source.lower()
    assert "nvidia" in source
    assert "dgx h100" in source
    assert "pythia" in source
    assert "eleutherai" in source
    assert "u.s. energy information administration" in source or "eia" in source


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("training.tokens_per_sec", pytest.approx(550_630, rel=1e-4)),
        ("econ.job.dc_power", pytest.approx(10_200.0)),
        ("econ.run.power_cost", pytest.approx(125.457, rel=1e-4)),
    ],
)
def test_pythia_160m_industrial_power_pack_resolves_non_cost_targets(target, expected):
    result = pythia_160m_dgx_h100_us_2024_industrial_power.resolve(target)
    assert not result.missing
    assert not result.violated_constraints
    assert float(result.value) == expected


def test_pythia_160m_industrial_power_pack_cost_per_token_has_missing_roots():
    result = pythia_160m_dgx_h100_us_2024_industrial_power.resolve("econ.cost.per_token")
    assert result.missing, (
        "Expected cost_per_token to report missing roots on the base power pack "
        "(capex and other economics roots are not assigned)"
    )


# ---------------------------------------------------------------------------
# Pythia-160M energy-floor cost pack
# ---------------------------------------------------------------------------

def test_pythia_160m_energy_floor_cost_closure_is_assumption_labeled():
    assert pythia_160m_dgx_h100_energy_floor_cost_closure.has_source()
    source = pythia_160m_dgx_h100_energy_floor_cost_closure.source.lower()
    assert "assumption" in source or "closure" in source
    a = pythia_160m_dgx_h100_energy_floor_cost_closure.assignments
    assert a["econ.job.capex_rate"] == 0.0
    assert a["econ.run.opex_misc_cost"] == 0.0


def test_pythia_160m_industrial_energy_floor_cost_resolves_all_targets():
    pack = pythia_160m_dgx_h100_us_2024_industrial_energy_floor_cost
    targets = scenarios.scenario_targets_for(pack)

    for label, target in targets:
        _assert_resolves_cleanly(pack, label, target)


def test_pythia_160m_industrial_energy_floor_cost_cost_per_token_is_positive():
    pack = pythia_160m_dgx_h100_us_2024_industrial_energy_floor_cost
    result = pack.resolve("econ.cost.per_token")
    assert not result.missing
    value = float(result.value)
    assert value > 0
    assert isfinite(value)


def test_pythia_160m_vs_70m_tokens_per_sec_ordering():
    # A 160M model is larger, so tokens/sec should be lower on the same hardware.
    result_160 = pythia_160m_dgx_h100_us_2024_industrial_power.resolve(
        "training.tokens_per_sec"
    )
    result_70 = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power.resolve(
        "training.tokens_per_sec"
    )
    assert not result_160.missing
    assert not result_70.missing
    assert float(result_160.value) < float(result_70.value), (
        "160M model should have lower tokens/sec than 70M on same hardware"
    )


def test_pythia_160m_vs_70m_run_power_cost_ratio():
    # Same hardware/dc power, same total tokens: relative cost scales with tokens/sec.
    result_160 = pythia_160m_dgx_h100_us_2024_industrial_energy_floor_cost.resolve(
        "econ.run.power_cost"
    )
    result_70 = scenarios.pythia_70m_dgx_h100_us_2024_industrial_energy_floor_cost.resolve(
        "econ.run.power_cost"
    )
    assert not result_160.missing
    assert not result_70.missing
    # 160M costs more to train (lower throughput, longer wall-clock time).
    assert float(result_160.value) > float(result_70.value), (
        "160M run cost should exceed 70M run cost on same hardware"
    )


def test_pythia_160m_industrial_energy_floor_cost_determinism():
    pack = pythia_160m_dgx_h100_us_2024_industrial_energy_floor_cost
    r1 = pack.resolve("econ.cost.per_token")
    r2 = pack.resolve("econ.cost.per_token")
    assert float(r1.value) == float(r2.value)


# ---------------------------------------------------------------------------
# Pythia-70M commercial tariff run closure
# ---------------------------------------------------------------------------

def test_pythia_70m_commercial_run_closure_has_source_and_values():
    assert pythia_70m_dgx_h100_us_2024_commercial_run_closure.has_source()
    source = pythia_70m_dgx_h100_us_2024_commercial_run_closure.source.lower()
    assert "nvidia" in source
    assert "dgx h100" in source

    a = pythia_70m_dgx_h100_us_2024_commercial_run_closure.assignments
    assert a["arch.n_kv_heads"] == 8
    assert a["par.n_gpus"] == 8
    assert a["gpu.peak_flops_power_limited"] == 67e12
    assert a["thermal.dc.total_power"] == pytest.approx(10_200.0)


# ---------------------------------------------------------------------------
# Pythia-70M commercial tariff power pack
# ---------------------------------------------------------------------------

def test_pythia_70m_commercial_power_pack_is_registered():
    assert pythia_70m_dgx_h100_us_2024_commercial_power in scenarios.SOURCED_SCENARIO_PACKS
    assert pythia_70m_dgx_h100_us_2024_commercial_power.require_source() is (
        pythia_70m_dgx_h100_us_2024_commercial_power
    )


def test_pythia_70m_commercial_power_pack_uses_commercial_tariff():
    a = pythia_70m_dgx_h100_us_2024_commercial_power.assignments
    # EIA 2024 commercial rate is 12.75 cents/kWh = 0.1275 USD/kWh.
    assert a["econ.power.price_kwh_peak"] == pytest.approx(0.1275)
    assert a["econ.power.price_kwh_offpeak"] == pytest.approx(0.1275)


def test_pythia_70m_commercial_tariff_higher_than_industrial():
    a_commercial = pythia_70m_dgx_h100_us_2024_commercial_power.assignments
    a_industrial = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power.assignments
    assert a_commercial["econ.power.price_kwh_peak"] > (
        a_industrial["econ.power.price_kwh_peak"]
    ), "commercial rate should exceed industrial rate"


def test_pythia_70m_commercial_power_pack_provenance_names_all_sources():
    source = pythia_70m_dgx_h100_us_2024_commercial_power.source.lower()
    assert "nvidia" in source
    assert "dgx h100" in source
    assert "pythia" in source
    assert "eleutherai" in source
    assert "u.s. energy information administration" in source or "eia" in source


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("training.tokens_per_sec", pytest.approx(1_268_976, rel=1e-4)),
        ("econ.job.dc_power", pytest.approx(10_200.0)),
        ("econ.run.power_cost", pytest.approx(85.373, rel=1e-4)),
    ],
)
def test_pythia_70m_commercial_power_pack_resolves_non_cost_targets(target, expected):
    result = pythia_70m_dgx_h100_us_2024_commercial_power.resolve(target)
    assert not result.missing
    assert not result.violated_constraints
    assert float(result.value) == expected


def test_pythia_70m_commercial_power_pack_cost_per_token_has_missing_roots():
    result = pythia_70m_dgx_h100_us_2024_commercial_power.resolve("econ.cost.per_token")
    assert result.missing, (
        "Expected cost_per_token to report missing roots on the base power pack "
        "(capex and other economics roots are not assigned)"
    )


# ---------------------------------------------------------------------------
# Pythia-70M commercial energy-floor cost pack
# ---------------------------------------------------------------------------

def test_pythia_70m_commercial_energy_floor_cost_closure_is_assumption_labeled():
    assert pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost_closure.has_source()
    source = pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost_closure.source.lower()
    assert "assumption" in source or "closure" in source
    a = pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost_closure.assignments
    assert a["econ.job.capex_rate"] == 0.0
    assert a["econ.run.opex_misc_cost"] == 0.0


def test_pythia_70m_commercial_energy_floor_cost_resolves_all_targets():
    pack = pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost
    targets = scenarios.scenario_targets_for(pack)

    for label, target in targets:
        _assert_resolves_cleanly(pack, label, target)


def test_pythia_70m_commercial_energy_floor_cost_is_positive():
    result = pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost.resolve(
        "econ.cost.per_token"
    )
    assert not result.missing
    value = float(result.value)
    assert value > 0
    assert isfinite(value)


def test_commercial_vs_industrial_cost_ratio():
    # Commercial rate (0.1275) / industrial rate (0.0813) = approx 1.569.
    # Run power cost and cost_per_token should scale by the same ratio.
    result_c = pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost.resolve(
        "econ.cost.per_token"
    )
    result_i = scenarios.pythia_70m_dgx_h100_us_2024_industrial_energy_floor_cost.resolve(
        "econ.cost.per_token"
    )
    assert not result_c.missing
    assert not result_i.missing

    ratio = float(result_c.value) / float(result_i.value)
    expected_ratio = 0.1275 / 0.0813
    assert ratio == pytest.approx(expected_ratio, rel=1e-6), (
        f"cost_per_token ratio {ratio:.6f} does not match tariff ratio "
        f"{expected_ratio:.6f}"
    )


def test_pythia_70m_commercial_energy_floor_cost_determinism():
    pack = pythia_70m_dgx_h100_us_2024_commercial_energy_floor_cost
    r1 = pack.resolve("econ.cost.per_token")
    r2 = pack.resolve("econ.cost.per_token")
    assert float(r1.value) == float(r2.value)


# ---------------------------------------------------------------------------
# Cross-pack consistency
# ---------------------------------------------------------------------------

def test_all_2026_packs_same_dc_power():
    # All packs use the same DGX H100 node with the same thermal cap.
    for pack in SOURCED_SCENARIO_PACKS_2026:
        result = pack.resolve("econ.job.dc_power")
        assert not result.missing, f"{pack.name} missing econ.job.dc_power"
        assert float(result.value) == pytest.approx(10_200.0), pack.name


def test_all_2026_packs_source_strings_do_not_contain_synthetic_markers():
    synthetic_markers = (
        "synthetic resolver fixture",
        "round-number assumption",
        "not historical data",
        "not calibrated",
        "gpu_stack/demo.py",
        "placeholder",
        "toy scenario",
    )
    for pack in SOURCED_SCENARIO_PACKS_2026:
        source = (pack.source or "").lower()
        for marker in synthetic_markers:
            assert marker not in source, (
                f"{pack.name} source contains synthetic marker {marker!r}"
            )
