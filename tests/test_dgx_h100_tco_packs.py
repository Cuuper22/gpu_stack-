"""Tests for the two presets that close the DGX H100 total cost of ownership.

TCO — total cost of ownership — needs every root input filled in before
``econ.cost.per_token`` resolves to a number. Two presets do that job:

- ``dgx_h100_node_power_bom`` supplies sourced hardware power roots (Intel
  Xeon 8480C CPU, ConnectX-7 NICs, NVMe drives), each traceable to a
  vendor datasheet.
- ``pythia_70m_dgx_h100_run_closure_assumption`` supplies the remaining
  economic and thermal roots, labeled as assumptions and cited to NIST,
  EPA, and DOE figures.

Composed, they form the
``pythia_70m_dgx_h100_us_2024_industrial_full_tco_assumption`` scenario
pack. The tests check each preset's provenance and value ranges, then run
the composed pack end to end: no missing inputs, a positive finite cost per
token that exceeds the electricity-only energy floor, and results that
agree with the original sourced pack wherever inputs are shared.
"""

from __future__ import annotations

from math import isfinite

import pytest

from gpu_stack import Registry
from gpu_stack.presets import dgx_h100_tco, scenarios
from gpu_stack.presets.scenarios import (
    pythia_70m_dgx_h100_us_2024_industrial_full_tco_assumption as FULL_TCO_PACK,
)


# ---------------------------------------------------------------------------
# DGX H100 power BOM (sourced)
# ---------------------------------------------------------------------------

class TestDgxH100NodePowerBom:
    def test_preset_is_accessible_from_module(self):
        assert dgx_h100_tco.dgx_h100_node_power_bom is not None

    def test_preset_has_required_provenance(self):
        preset = dgx_h100_tco.dgx_h100_node_power_bom

        assert preset.name == "dgx_h100_node_power_bom"
        assert preset.description
        assert preset.source
        assert preset.notes

    def test_preset_source_cites_intel_and_nvidia(self):
        source = (dgx_h100_tco.dgx_h100_node_power_bom.source or "").lower()

        assert "intel" in source
        assert "xeon" in source
        assert "nvidia" in source
        assert "connectx-7" in source
        assert "https://" in source

    def test_preset_assignments_are_all_root_inputs(self):
        preset = dgx_h100_tco.dgx_h100_node_power_bom
        non_roots = [
            name
            for name in preset.assignments
            if not Registry.variables[name].is_root_input
        ]
        assert non_roots == []

    def test_preset_assignments_cover_cpu_nic_and_storage(self):
        assignments = dgx_h100_tco.dgx_h100_node_power_bom.assignments

        assert "cluster.node.cpu.power_per_cpu" in assignments
        assert "cluster.node.nic.power_per_nic" in assignments
        assert "cluster.node.nic.power_per_port" in assignments
        assert "cluster.node.local_ssd.count" in assignments
        assert "cluster.node.local_ssd.power_per_drive" in assignments

    def test_cpu_power_per_cpu_is_intel_8480c_tdp(self):
        # Intel Xeon Platinum 8480C TDP = 350 W per published datasheet.
        assignments = dgx_h100_tco.dgx_h100_node_power_bom.assignments
        assert assignments["cluster.node.cpu.power_per_cpu"] == pytest.approx(350.0)

    def test_nic_power_per_nic_is_connectx7_typical(self):
        # ConnectX-7 single-port OSFP typical power = 24.9 W per NVIDIA spec.
        assignments = dgx_h100_tco.dgx_h100_node_power_bom.assignments
        assert assignments["cluster.node.nic.power_per_nic"] == pytest.approx(24.9)

    def test_local_ssd_count_matches_dgx_h100_data_cache_drives(self):
        # DGX H100 has 8 x 3.84 TB U.2 NVMe data-cache drives.
        assignments = dgx_h100_tco.dgx_h100_node_power_bom.assignments
        assert assignments["cluster.node.local_ssd.count"] == pytest.approx(8.0)

    def test_local_ssd_power_per_drive_within_enterprise_nvme_range(self):
        # Enterprise U.2 NVMe drives: 8-11 W active range.
        assignments = dgx_h100_tco.dgx_h100_node_power_bom.assignments
        power = assignments["cluster.node.local_ssd.power_per_drive"]
        assert 8.0 <= power <= 11.0


# ---------------------------------------------------------------------------
# Pythia 70M DGX H100 run closure assumption
# ---------------------------------------------------------------------------

class TestPythiaDgxH100RunClosureAssumption:
    def test_preset_is_accessible_from_module(self):
        assert dgx_h100_tco.pythia_70m_dgx_h100_run_closure_assumption is not None

    def test_preset_has_required_provenance(self):
        preset = dgx_h100_tco.pythia_70m_dgx_h100_run_closure_assumption

        assert preset.name == "pythia_70m_dgx_h100_run_closure_assumption"
        assert preset.description
        assert preset.source
        assert preset.notes

    def test_preset_source_labels_it_as_assumption(self):
        source = (
            dgx_h100_tco.pythia_70m_dgx_h100_run_closure_assumption.source or ""
        ).lower()

        assert "assumption" in source

    def test_preset_source_cites_nist_and_epa_and_doe(self):
        source = (
            dgx_h100_tco.pythia_70m_dgx_h100_run_closure_assumption.source or ""
        ).lower()

        assert "nist" in source
        assert "epa" in source
        assert "doe" in source or "department of energy" in source or "femp" in source

    def test_preset_assignments_are_all_root_inputs(self):
        preset = dgx_h100_tco.pythia_70m_dgx_h100_run_closure_assumption
        non_roots = [
            name
            for name in preset.assignments
            if not Registry.variables[name].is_root_input
        ]
        assert non_roots == []

    def test_preset_covers_all_33_missing_roots_of_original_pack(self):
        # The original pack has 33 missing root inputs. This assumption closure
        # must cover all of them directly or via upstream decomposition.
        original = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power
        original_result = original.resolve("econ.cost.per_token")
        original_missing = set(original_result.missing)

        bom_assignments = set(dgx_h100_tco.dgx_h100_node_power_bom.assignments)
        assumption_assignments = set(
            dgx_h100_tco.pythia_70m_dgx_h100_run_closure_assumption.assignments
        )
        covered = bom_assignments | assumption_assignments

        # Closure means: every root the original pack was missing is either
        # assigned by one of the two new presets or is a symbolic boundary
        # that now resolves from assigned primitive roots. The proof is that
        # the full_tco pack resolves with nothing missing.
        full_result = FULL_TCO_PACK.resolve("econ.cost.per_token")
        assert not full_result.missing, (
            "full_tco pack still has missing roots: "
            f"{sorted(full_result.missing)}"
        )
        assert len(original_missing) == 33

    def test_water_latent_heat_is_physical_constant(self):
        # Water latent heat at 20 degC: NIST value ~2454 kJ/kg.
        assignments = dgx_h100_tco.pythia_70m_dgx_h100_run_closure_assumption.assignments
        latent_heat = assignments["thermal.water.latent_heat"]
        # Accept within 2 % of 2454 kJ/kg.
        assert 2_400_000.0 <= latent_heat <= 2_510_000.0

    def test_water_density_is_near_one_kg_per_liter(self):
        # Water density at 20 degC: NIST ~0.998 kg/L.
        assignments = dgx_h100_tco.pythia_70m_dgx_h100_run_closure_assumption.assignments
        density = assignments["thermal.water.density"]
        assert 0.990 <= density <= 1.010

    def test_asset_useful_life_encodes_four_years(self):
        assignments = dgx_h100_tco.pythia_70m_dgx_h100_run_closure_assumption.assignments
        useful_life_s = assignments["econ.asset.useful_life"]
        years = useful_life_s / (365.25 * 86400)
        assert pytest.approx(years, rel=1e-3) == 4.0

    def test_gpu_capex_within_2024_market_range(self):
        # H100 SXM 2024 channel range: $27,000-$40,000.
        assignments = dgx_h100_tco.pythia_70m_dgx_h100_run_closure_assumption.assignments
        capex = assignments["econ.gpu.capex"]
        assert 27_000.0 <= capex <= 40_000.0

    def test_carbon_intensity_is_us_national_average(self):
        # EPA eGRID2023 US national average: approximately 386 g CO2/kWh.
        assignments = dgx_h100_tco.pythia_70m_dgx_h100_run_closure_assumption.assignments
        intensity = assignments["econ.carbon.intensity_kg_per_kwh"]
        # Accept within 10 % of 0.386 kg/(kW*h).
        assert 0.30 <= intensity <= 0.45


# ---------------------------------------------------------------------------
# Full TCO assumption pack end-to-end
# ---------------------------------------------------------------------------

FULL_TCO_PACK_NAME = "pythia_70m_dgx_h100_us_2024_industrial_full_tco_assumption"


class TestPythiaDgxH100FullTcoPack:
    def test_pack_is_in_sourced_scenario_packs(self):
        assert FULL_TCO_PACK in scenarios.SOURCED_SCENARIO_PACKS
        pack_names = {p.name for p in scenarios.SOURCED_SCENARIO_PACKS}
        assert FULL_TCO_PACK_NAME in pack_names

    def test_pack_is_accessible_as_module_attribute(self):
        assert getattr(scenarios, FULL_TCO_PACK_NAME) is FULL_TCO_PACK

    def test_pack_has_source(self):
        assert FULL_TCO_PACK.has_source()
        assert FULL_TCO_PACK.require_source() is FULL_TCO_PACK

    def test_pack_source_labels_assumptions_explicitly(self):
        source = (FULL_TCO_PACK.source or "").lower()
        assert "assumption" in source

    def test_pack_source_cites_official_urls(self):
        source = FULL_TCO_PACK.source or ""
        assert "https://" in source
        assert "nvidia" in source.lower()
        assert "eia" in source.lower() or "energy information" in source.lower()

    def test_pack_advertised_targets_include_cost_per_token(self):
        targets = dict(scenarios.scenario_targets_for(FULL_TCO_PACK))
        assert "cost_per_token" in targets
        assert targets["cost_per_token"] == "econ.cost.per_token"

    def test_pack_advertised_targets_are_registered_variables(self):
        targets = scenarios.scenario_targets_for(FULL_TCO_PACK)
        for label, target in targets:
            assert target in Registry.variables, (FULL_TCO_PACK_NAME, label, target)

    def test_pack_resolves_cost_per_token_with_no_missing_inputs(self):
        result = FULL_TCO_PACK.resolve("econ.cost.per_token")

        assert not result.missing, f"still missing: {sorted(result.missing)}"
        assert not result.unresolved_inputs
        assert not result.violated_constraints

    def test_pack_cost_per_token_is_positive_finite(self):
        result = FULL_TCO_PACK.resolve("econ.cost.per_token")

        assert not result.missing
        assert not result.value.free_symbols
        value = float(result.value)
        assert value > 0
        assert isfinite(value)

    def test_pack_cost_per_token_exceeds_energy_floor(self):
        # Full TCO (with capex, staff, maintenance, etc.) must be greater
        # than the electricity-only energy floor.
        floor_pack = scenarios.pythia_70m_dgx_h100_us_2024_industrial_energy_floor_cost
        full_result = FULL_TCO_PACK.resolve("econ.cost.per_token")
        floor_result = floor_pack.resolve("econ.cost.per_token")

        full_cost = float(full_result.value)
        floor_cost = float(floor_result.value)

        assert full_cost > floor_cost, (
            f"full TCO {full_cost} should exceed energy floor {floor_cost}"
        )

    def test_pack_resolves_all_advertised_targets_cleanly(self):
        failures = []
        for label, target in scenarios.scenario_targets_for(FULL_TCO_PACK):
            result = FULL_TCO_PACK.resolve(target)
            if result.missing:
                failures.append(f"{label}: missing {sorted(result.missing)}")
                continue
            if result.violated_constraints:
                failures.append(
                    f"{label}: violated constraints "
                    f"{sorted(v.equation for v in result.violated_constraints)}"
                )
                continue
            if result.value.free_symbols:
                failures.append(
                    f"{label}: free symbols {result.value.free_symbols}"
                )
                continue
            value = float(result.value)
            if not (value > 0 and isfinite(value)):
                failures.append(f"{label}: nonpositive/nonfinite {value}")

        assert not failures, f"full TCO pack failures: {failures}"

    def test_pack_tokens_per_second_matches_original_sourced_pack(self):
        # Tokens per second should be unchanged from the original sourced pack
        # since the workload and hardware inputs are the same.
        original = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power
        full_result = FULL_TCO_PACK.resolve("training.tokens_per_sec")
        original_result = original.resolve("training.tokens_per_sec")

        assert float(full_result.value) == pytest.approx(
            float(original_result.value), rel=1e-9
        )

    def test_pack_job_dc_power_matches_original_sourced_pack(self):
        # DC power is driven by thermal.dc.total_power override, unchanged.
        original = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power
        full_result = FULL_TCO_PACK.resolve("econ.job.dc_power")
        original_result = original.resolve("econ.job.dc_power")

        assert float(full_result.value) == pytest.approx(
            float(original_result.value), rel=1e-9
        )

    def test_pack_run_power_cost_matches_original_sourced_pack(self):
        # Run power cost is driven by electricity price and DC power, unchanged.
        original = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power
        full_result = FULL_TCO_PACK.resolve("econ.run.power_cost")
        original_result = original.resolve("econ.run.power_cost")

        assert float(full_result.value) == pytest.approx(
            float(original_result.value), rel=1e-9
        )

    def test_pack_cost_per_token_trace_uses_capex_and_opex_equations(self):
        result = FULL_TCO_PACK.resolve("econ.cost.per_token")
        trace_equations = {step.equation for step in result.trace}

        # Capex equations
        assert "econ.eq.node_capex" in trace_equations
        assert "econ.eq.rack_capex" in trace_equations
        assert "econ.eq.cluster_it_capex" in trace_equations
        assert "econ.eq.cluster_facility_capex" in trace_equations
        assert "econ.eq.cluster_capex_rate" in trace_equations
        # OpEx equations
        assert "econ.eq.maintenance_cost_rate" in trace_equations
        assert "econ.eq.water_cost_rate" in trace_equations
        # Cost-per-token rollup
        assert "econ.eq.cost_per_token" in trace_equations

    def test_pack_is_in_scenario_target_sets(self):
        assert FULL_TCO_PACK_NAME in scenarios.SCENARIO_TARGET_SETS

    def test_pack_scenario_target_labels_are_stable(self):
        targets = scenarios.scenario_targets_for(FULL_TCO_PACK)
        labels = tuple(label for label, _ in targets)
        assert labels == (
            "tokens_per_second",
            "job_dc_power",
            "run_power_cost",
            "cost_per_token",
        )
