"""Verifies facility cooling power and capex decompose to physical drivers.

Two quantities are easy to leave as opaque roots and hard to trust that
way: CDU power (the coolant distribution unit that pumps liquid coolant)
and facility capex. Here CDU power is derived from site-wide liquid heat
removed times an auxiliary-power fraction, and facility capex from three
sizing quantities (floor area, power capacity, cooling capacity) times
their unit costs. The tests pin those dependency sets, resolve
hand-checkable cases (512 GPUs at 1000 W removed with a 0.025 aux fraction
gives 12,800 W; the capex example totals 1.34 billion USD), confirm the
capex slice never touches non-cooling overhead terms like UPS loss, and
check metadata and cycle-freedom.
"""

import pytest

import gpu_stack
from gpu_stack import Registry, resolve


def _deps(name):
    return {v.name for v in Registry.variables[name].direct_dependencies()}


def test_cdu_power_is_derived_from_site_liquid_heat_and_aux_fraction():
    assert not Registry.variables["thermal.facility.cdu_power"].is_root_input
    assert _deps("thermal.facility.cdu_power") == {
        "thermal.facility.cdu_aux_fraction",
        "thermal.facility.liquid_heat_removed_site",
    }

    assert not Registry.variables["thermal.facility.liquid_heat_removed_site"].is_root_input
    assert _deps("thermal.facility.liquid_heat_removed_site") == {
        "cluster.site.n_gpus",
        "thermal.q_removed",
    }

    assert Registry.variables["thermal.facility.cdu_aux_fraction"].is_root_input


def test_cdu_power_resolves_from_liquid_heat_removed_site():
    result = resolve(
        "thermal.facility.cdu_power",
        assignments={
            "cluster.site.n_gpus": 512,
            "thermal.q_removed": 1_000,
            "thermal.facility.cdu_aux_fraction": 0.025,
        },
    )

    assert float(result.value) == pytest.approx(12_800)
    assert {
        "thermal.eq.liquid_heat_removed_site",
        "thermal.eq.cdu_power",
    } <= {step.equation for step in result.trace}


def test_facility_sizing_quantities_are_explicit_capex_drivers():
    for name in {
        "thermal.facility.floor_area",
        "thermal.facility.power_design_capacity",
        "thermal.facility.cooling_design_capacity",
    }:
        assert Registry.variables[name].is_root_input


def test_facility_capex_components_are_unit_cost_decompositions():
    expected = {
        "econ.facility.building_shell_capex": {
            "thermal.facility.floor_area",
            "econ.facility.building_shell_unit_cost",
        },
        "econ.facility.power_infra_capex": {
            "thermal.facility.power_design_capacity",
            "econ.facility.power_infra_unit_cost",
        },
        "econ.facility.cooling_infra_capex": {
            "thermal.facility.cooling_design_capacity",
            "econ.facility.cooling_infra_unit_cost",
        },
    }

    for name, deps in expected.items():
        assert not Registry.variables[name].is_root_input
        assert _deps(name) == deps

    for name in {
        "econ.facility.building_shell_unit_cost",
        "econ.facility.power_infra_unit_cost",
        "econ.facility.cooling_infra_unit_cost",
    }:
        assert Registry.variables[name].is_root_input


def test_cluster_facility_capex_resolves_from_decomposed_components():
    result = resolve(
        "econ.cluster.facility_capex",
        assignments={
            "thermal.facility.floor_area": 10_000,
            "econ.facility.building_shell_unit_cost": 3_000,
            "thermal.facility.power_design_capacity": 80_000_000,
            "econ.facility.power_infra_unit_cost": 12,
            "thermal.facility.cooling_design_capacity": 70_000_000,
            "econ.facility.cooling_infra_unit_cost": 5,
        },
    )

    assert float(result.value) == pytest.approx(1_340_000_000)
    assert {
        "econ.eq.facility_building_shell_capex",
        "econ.eq.facility_power_infra_capex",
        "econ.eq.facility_cooling_infra_capex",
        "econ.eq.cluster_facility_capex",
    } <= {step.equation for step in result.trace}


def test_liquid_facility_and_capex_metadata_is_covered():
    variables = {
        "thermal.q_removed",
        "thermal.facility.liquid_heat_removed_site",
        "thermal.facility.cdu_power",
        "thermal.facility.floor_area",
        "thermal.facility.power_design_capacity",
        "thermal.facility.cooling_design_capacity",
        "econ.facility.building_shell_capex",
        "econ.facility.power_infra_capex",
        "econ.facility.cooling_infra_capex",
        "econ.cluster.facility_capex",
    }
    equations = {
        "thermal.eq.q_removed",
        "thermal.eq.liquid_heat_removed_site",
        "thermal.eq.cdu_power",
        "econ.eq.facility_building_shell_capex",
        "econ.eq.facility_power_infra_capex",
        "econ.eq.facility_cooling_infra_capex",
        "econ.eq.cluster_facility_capex",
    }

    for name in variables:
        variable = Registry.variables[name]
        assert variable.sp_units is not None
        assert variable.references

    for name in equations:
        eq = Registry.equations[name]
        assert eq.references
        assert getattr(eq, "_check_units_flag", False)


def test_facility_capex_slice_does_not_use_non_cooling_overhead_terms():
    forbidden = {
        "thermal.facility.ups_loss",
        "thermal.facility.transformer_loss",
        "thermal.facility.lighting",
        "thermal.facility.misc",
    }

    for name in {
        "econ.facility.power_infra_capex",
        "econ.facility.cooling_infra_capex",
        "econ.cluster.facility_capex",
    }:
        deps = {v.name for v in Registry.variables[name].dependencies()}
        assert forbidden.isdisjoint(deps)


def test_facility_capex_decomposition_does_not_introduce_cycles():
    assert gpu_stack.find_cycles() == []
