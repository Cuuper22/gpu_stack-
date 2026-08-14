"""
tests/test_local_temperature_physics.py
=======================================

A transistor does not run at the room's temperature — it runs hotter,
because it heats itself. This module verifies the decomposition that
captures that: local temperature = ambient + self-heating rise, where the
rise is heat flux times an area-normalized thermal resistance. Each link is
checked separately with numbers small enough to verify by hand: the heat
source area comes from cell count, cell area scale, and the two process
pitches (2 cells * 5.0 scale * 2.0 * 5.0 = 100.0); flux is power over area
(100 W / 100 = 1.0); resistance-area is thickness over conductivity times a
spreading factor (6.0/2.0 * 1.5 = 4.5); so the rise is 4.5 K and the local
temperature 304.5 K. The chain then feeds resistivity, which is checked end
to end, and every equation in the chain must keep its unit check enabled.
"""

import pytest

from gpu_stack import Registry, resolve


def test_local_temperature_depends_on_boundary_temperature_and_self_heating():
    temperature = Registry.variables["physical.temperature"]
    assert not temperature.is_root_input
    assert {v.name for v in temperature.direct_dependencies()} == {
        "physical.temperature.ambient",
        "physical.temperature.self_heating_rise",
    }

    result = resolve(
        "physical.temperature",
        assignments={
            "physical.temperature.ambient": 300.0,
            "physical.heat_source.power": 100.0,
            "physical.heat_source.cell_count": 2,
            "physical.heat_source.cell_area_scale": 5.0,
            "physical.process.contacted_gate_pitch": 2.0,
            "physical.process.minimum_metal_pitch": 5.0,
            "physical.thermal.boundary_thickness": 6.0,
            "physical.thermal.conductivity": 2.0,
            "physical.thermal.spreading_factor": 1.5,
        },
    )
    assert float(result.value) == pytest.approx(304.5)


def test_heat_source_area_depends_on_process_pitch_and_counted_cells():
    area = Registry.variables["physical.heat_source.area"]
    assert not area.is_root_input
    assert {v.name for v in area.direct_dependencies()} == {
        "physical.heat_source.cell_count",
        "physical.heat_source.cell_area_scale",
        "physical.process.contacted_gate_pitch",
        "physical.process.minimum_metal_pitch",
    }

    result = resolve(
        "physical.heat_source.area",
        assignments={
            "physical.heat_source.cell_count": 2,
            "physical.heat_source.cell_area_scale": 5.0,
            "physical.process.contacted_gate_pitch": 2.0,
            "physical.process.minimum_metal_pitch": 5.0,
        },
    )
    assert float(result.value) == pytest.approx(100.0)


def test_heat_flux_depends_on_source_power_and_area():
    heat_flux = Registry.variables["physical.heat_flux"]
    assert not heat_flux.is_root_input
    assert {v.name for v in heat_flux.direct_dependencies()} == {
        "physical.heat_source.power",
        "physical.heat_source.area",
    }

    result = resolve(
        "physical.heat_flux",
        assignments={
            "physical.heat_source.power": 100.0,
            "physical.heat_source.cell_count": 2,
            "physical.heat_source.cell_area_scale": 5.0,
            "physical.process.contacted_gate_pitch": 2.0,
            "physical.process.minimum_metal_pitch": 5.0,
        },
    )
    assert float(result.value) == pytest.approx(1.0)


def test_area_normalized_thermal_resistance_depends_on_conduction_path():
    resistance_area = Registry.variables["physical.thermal.resistance_area"]
    assert not resistance_area.is_root_input
    assert {v.name for v in resistance_area.direct_dependencies()} == {
        "physical.thermal.boundary_thickness",
        "physical.thermal.conductivity",
        "physical.thermal.spreading_factor",
    }

    result = resolve(
        "physical.thermal.resistance_area",
        assignments={
            "physical.thermal.boundary_thickness": 6.0,
            "physical.thermal.conductivity": 2.0,
            "physical.thermal.spreading_factor": 1.5,
        },
    )
    assert float(result.value) == pytest.approx(4.5)


def test_self_heating_rise_depends_on_heat_flux_and_area_resistance():
    rise = Registry.variables["physical.temperature.self_heating_rise"]
    assert not rise.is_root_input
    assert {v.name for v in rise.direct_dependencies()} == {
        "physical.heat_flux",
        "physical.thermal.resistance_area",
    }

    result = resolve(
        "physical.temperature.self_heating_rise",
        assignments={
            "physical.heat_flux": 2.0,
            "physical.thermal.resistance_area": 5.0,
        },
    )
    assert float(result.value) == pytest.approx(10.0)


def test_resistivity_can_resolve_through_local_temperature():
    result = resolve(
        "physical.resistivity",
        assignments={
            "physical.resistivity.reference": 2.0,
            "physical.resistivity.temp_coeff": 0.1,
            "physical.temperature.ambient": 300.0,
            "physical.heat_source.power": 100.0,
            "physical.heat_source.cell_count": 2,
            "physical.heat_source.cell_area_scale": 5.0,
            "physical.process.contacted_gate_pitch": 2.0,
            "physical.process.minimum_metal_pitch": 5.0,
            "physical.thermal.boundary_thickness": 6.0,
            "physical.thermal.conductivity": 2.0,
            "physical.thermal.spreading_factor": 1.5,
            "physical.resistivity.reference_temperature": 300.0,
            "physical.resistivity.size_factor": 3.0,
        },
    )
    assert float(result.value) == pytest.approx(8.7)


def test_local_temperature_equations_have_unit_checks():
    checked = {
        name
        for name, eq in Registry.equations.items()
        if getattr(eq, "_check_units_flag", False)
    }
    assert {
        "physical.eq.heat_source_area",
        "physical.eq.heat_flux_from_power_area",
        "physical.eq.thermal_resistance_area_from_conduction",
        "physical.eq.temperature_self_heating",
        "physical.eq.temperature_local",
    } <= checked
