"""
scopes/physical_local_thermal.py
================================

Local self-heating of the semiconductor: how much hotter the device sits
than its surroundings. Power from a cluster of cells crosses a thin
boundary layer of finite thermal conductivity, so heat flux times the
boundary thermal resistance (with a spreading factor for non-uniform flow)
gives a temperature rise above ambient. The resulting local temperature
feeds temperature-sensitive transport, notably resistivity. This layer
deliberately sits below the package and facility thermal scopes -- it knows
nothing about coolant or chillers -- so the physical scope stays acyclic.
"""

import sympy as sp

from ..core import Approximation, Reference, eq, var
from ..core.units import KELVIN, METER, WATT
from .physical_process import contacted_gate_pitch, minimum_metal_pitch


_LOCAL_THERMAL_REF = Reference(
    citation="Local device temperature abstraction: heat-source power over process-pitch-derived area, then boundary temperature plus heat-flux-driven self-heating through an area-normalized thermal resistance",
    kind="memo",
)


T_local_ambient = var(
    "physical.temperature.ambient", "T_phys_amb", "K",
    "Local thermal boundary temperature seen by the semiconductor region.",
    scope="physical",
    sp_units=KELVIN,
    references=[_LOCAL_THERMAL_REF],
)
heat_source_power = var(
    "physical.heat_source.power", "P_heat_src_phys", "W",
    "Local power dissipated by the semiconductor heat source represented by this thermal control area.",
    scope="physical",
    nonnegative=True,
    sp_units=WATT,
    references=[_LOCAL_THERMAL_REF],
)
heat_source_cell_count = var(
    "physical.heat_source.cell_count", "N_heat_cell_phys", "cells",
    "Number of process-pitch unit cells contributing to the local heat-source area.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[_LOCAL_THERMAL_REF],
)
heat_source_cell_area_scale = var(
    "physical.heat_source.cell_area_scale", "k_heat_cell_area_phys", "dimensionless",
    "Area multiplier from one contacted-gate-pitch by minimum-metal-pitch cell to the represented heat-source footprint.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[_LOCAL_THERMAL_REF],
)
heat_source_area = var(
    "physical.heat_source.area", "A_heat_src_phys", "m^2",
    "Local heat-source area receiving the modeled power density.",
    scope="physical",
    sp_units=METER**2,
    references=[_LOCAL_THERMAL_REF],
)
thermal_boundary_thickness = var(
    "physical.thermal.boundary_thickness", "t_th_phys", "m",
    "Effective thermal path thickness between the local heat source and its boundary temperature.",
    scope="physical",
    sp_units=METER,
    references=[_LOCAL_THERMAL_REF],
)
thermal_conductivity = var(
    "physical.thermal.conductivity", "k_th_phys", "W/(m*K)",
    "Effective thermal conductivity of the local semiconductor/package material stack.",
    scope="physical",
    sp_units=WATT / (METER * KELVIN),
    references=[_LOCAL_THERMAL_REF],
)
thermal_spreading_factor = var(
    "physical.thermal.spreading_factor", "chi_th_spread_phys", "dimensionless",
    "Multiplier for spreading, constriction, interface, and anisotropy effects not captured by one-dimensional conduction.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[_LOCAL_THERMAL_REF],
)
heat_flux = var(
    "physical.heat_flux", "q_pp_phys", "W/m^2",
    "Local heat flux through the semiconductor thermal boundary.",
    scope="physical",
    nonnegative=True,
    sp_units=WATT / METER**2,
    references=[_LOCAL_THERMAL_REF],
)
thermal_resistance_area = var(
    "physical.thermal.resistance_area", "R_thA_phys", "K*m^2/W",
    "Area-normalized thermal resistance from the semiconductor region to its local boundary.",
    scope="physical",
    nonnegative=True,
    sp_units=KELVIN * METER**2 / WATT,
    references=[_LOCAL_THERMAL_REF],
)
T_self_heating_rise = var(
    "physical.temperature.self_heating_rise", "Delta_T_self_phys", "K",
    "Local semiconductor temperature rise from self-heating.",
    scope="physical",
    nonnegative=True,
    sp_units=KELVIN,
    references=[_LOCAL_THERMAL_REF],
)
T_temp = var(
    "physical.temperature", "T_K", "K",
    "Local operating temperature in kelvin after boundary temperature and self-heating are applied.",
    scope="physical",
    sp_units=KELVIN,
    references=[_LOCAL_THERMAL_REF],
)


eq_heat_source_area = Approximation(
    "physical.eq.heat_source_area",
    heat_source_area.symbol,
    heat_source_cell_count.symbol
    * heat_source_cell_area_scale.symbol
    * contacted_gate_pitch.symbol
    * minimum_metal_pitch.symbol,
    (contacted_gate_pitch.symbol > 0) & (minimum_metal_pitch.symbol > 0),
    "Local heat-source footprint from counted process-pitch cells and a dimensionless footprint scale.",
    references=[_LOCAL_THERMAL_REF],
    check_units=True,
)

eq_heat_flux_from_power_area = Approximation(
    "physical.eq.heat_flux_from_power_area",
    heat_flux.symbol,
    heat_source_power.symbol / heat_source_area.symbol,
    heat_source_area.symbol > 0,
    "Local heat flux equals local dissipated power divided by the represented heat-source area.",
    references=[_LOCAL_THERMAL_REF],
    check_units=True,
)

eq_thermal_resistance_area_from_conduction = Approximation(
    "physical.eq.thermal_resistance_area_from_conduction",
    thermal_resistance_area.symbol,
    thermal_spreading_factor.symbol
    * thermal_boundary_thickness.symbol
    / thermal_conductivity.symbol,
    (thermal_boundary_thickness.symbol > 0) & (thermal_conductivity.symbol > 0),
    "Area-normalized thermal resistance from effective path thickness, thermal conductivity, and spreading/constriction multiplier.",
    references=[_LOCAL_THERMAL_REF],
    check_units=True,
)

eq_temperature_self_heating = eq(
    "physical.eq.temperature_self_heating",
    T_self_heating_rise.symbol,
    heat_flux.symbol * thermal_resistance_area.symbol,
    "Local self-heating temperature rise equals heat flux times area-normalized thermal resistance.",
    references=[_LOCAL_THERMAL_REF],
    check_units=True,
)

eq_temperature_local = eq(
    "physical.eq.temperature_local",
    T_temp.symbol,
    T_local_ambient.symbol + T_self_heating_rise.symbol,
    "Local semiconductor temperature equals local boundary temperature plus self-heating rise.",
    references=[_LOCAL_THERMAL_REF],
    check_units=True,
)


LOCAL_THERMAL_VARIABLES = [
    T_local_ambient,
    heat_source_power,
    heat_source_cell_count,
    heat_source_cell_area_scale,
    heat_source_area,
    thermal_boundary_thickness,
    thermal_conductivity,
    thermal_spreading_factor,
    heat_flux,
    thermal_resistance_area,
    T_self_heating_rise,
    T_temp,
]

LOCAL_THERMAL_EQUATIONS = [
    eq_heat_source_area,
    eq_heat_flux_from_power_area,
    eq_thermal_resistance_area_from_conduction,
    eq_temperature_self_heating,
    eq_temperature_local,
]


__all__ = [
    "T_local_ambient",
    "heat_source_power",
    "heat_source_cell_count",
    "heat_source_cell_area_scale",
    "heat_source_area",
    "thermal_boundary_thickness",
    "thermal_conductivity",
    "thermal_spreading_factor",
    "heat_flux",
    "thermal_resistance_area",
    "T_self_heating_rise",
    "T_temp",
    "eq_heat_source_area",
    "eq_heat_flux_from_power_area",
    "eq_thermal_resistance_area_from_conduction",
    "eq_temperature_self_heating",
    "eq_temperature_local",
    "LOCAL_THERMAL_VARIABLES",
    "LOCAL_THERMAL_EQUATIONS",
]
