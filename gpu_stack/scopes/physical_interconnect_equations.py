"""
scopes/physical_interconnect_equations.py
=========================================

Equations for on-chip wire behavior. Geometry comes first: route length
from span and detour, then width, thickness, and spacing from the metal
pitch, aspect ratio, and fill factor. Resistance per length follows from
resistivity and cross section, capacitance from parallel-plate plus fringe
terms, and neighboring wires add capacitive crosstalk. The payoff is the
distributed RC delay of the line, which grows with length squared, and the
high-frequency resistance rise when skin effect confines current to the
conductor surface. Feasibility constraints keep the geometry realizable.
"""

import sympy as sp

from ..constants import EPSILON_0, TWO_PI
from ..core import Approximation, Inequality, PiecewiseEquation, eq
from .physical_interconnect_refs import _INTERCONNECT_GEOMETRY_REF, _INTERCONNECT_TEXT
from .physical_interconnect_variables import (
    C_couple,
    C_per_length,
    C_victim_load,
    C_wire_total,
    R_path_total,
    R_per_length,
    R_via_single,
    R_via_total,
    R_wire_ac,
    V_aggressor,
    V_xtalk,
    dielectric_permittivity,
    dielectric_relative_permittivity,
    f_signal,
    fringe_cap_factor,
    metal_layer_pitch_factor,
    metal_pitch_scale,
    mu_wire,
    n_vias,
    omega_signal,
    route_detour_factor,
    route_hop_count,
    route_span,
    skin_depth,
    tau_wire_rc,
    wire_aspect_ratio,
    wire_fill_factor,
    wire_pitch,
    wire_spacing,
    wire_thickness,
    wire_width,
)
from .physical_semiconductor import (
    A_wire,
    L_wire,
    R_res,
    minimum_metal_pitch,
    process_node_length,
    rho_res,
)


ineq_route_detour_factor_at_least_unity = Inequality(
    "physical.ineq.interconnect_route_detour_factor_at_least_unity",
    route_detour_factor.symbol,
    sp.Integer(1),
    ">=",
    "Routing detour factor must not shorten the direct Manhattan placement span.",
    references=[_INTERCONNECT_GEOMETRY_REF],
    check_units=True,
)

ineq_route_length_positive = Inequality(
    "physical.ineq.interconnect_route_length_positive",
    L_wire.symbol,
    sp.Integer(0),
    ">",
    "Interconnect route length must be positive for a physical routed segment.",
    references=[_INTERCONNECT_GEOMETRY_REF],
)


eq_wire_length_from_route = eq(
    "physical.eq.interconnect_route_length",
    L_wire.symbol,
    route_span.symbol * route_detour_factor.symbol,
    "Wire length from placement span and routing detour factor.",
    references=[_INTERCONNECT_GEOMETRY_REF],
    check_units=True,
)

eq_route_span_from_hops = eq(
    "physical.eq.interconnect_route_span",
    route_span.symbol,
    route_hop_count.symbol * wire_pitch.symbol,
    "Placement span from local routing-hop count and metal pitch.",
    references=[_INTERCONNECT_GEOMETRY_REF],
    check_units=True,
)

eq_metal_pitch_scale = Approximation(
    "physical.eq.interconnect_metal_pitch_scale",
    metal_pitch_scale.symbol,
    metal_layer_pitch_factor.symbol
    * minimum_metal_pitch.symbol
    / process_node_length.symbol,
    process_node_length.symbol > 0,
    "Metal pitch scale from minimum metal pitch, the selected routing-layer pitch multiplier, and the nominal process-node length.",
    references=[_INTERCONNECT_GEOMETRY_REF],
    check_units=True,
)

eq_wire_pitch_from_process = eq(
    "physical.eq.interconnect_pitch_from_process",
    wire_pitch.symbol,
    process_node_length.symbol * metal_pitch_scale.symbol,
    "Interconnect pitch from nominal process-node length and metal-pitch scaling.",
    references=[_INTERCONNECT_GEOMETRY_REF],
    check_units=True,
)

eq_wire_width = eq(
    "physical.eq.interconnect_width",
    wire_width.symbol,
    wire_pitch.symbol * wire_fill_factor.symbol,
    "Wire width from pitch and routing fill factor.",
    references=[_INTERCONNECT_GEOMETRY_REF],
    check_units=True,
)

eq_wire_thickness = eq(
    "physical.eq.interconnect_thickness",
    wire_thickness.symbol,
    wire_aspect_ratio.symbol * wire_width.symbol,
    "Wire thickness from aspect ratio and wire width.",
    references=[_INTERCONNECT_GEOMETRY_REF],
    check_units=True,
)

eq_wire_spacing = eq(
    "physical.eq.interconnect_spacing",
    wire_spacing.symbol,
    wire_pitch.symbol - wire_width.symbol,
    "Wire spacing is pitch minus physical wire width.",
    references=[_INTERCONNECT_GEOMETRY_REF],
    check_units=True,
)

eq_wire_area = eq(
    "physical.eq.interconnect_area",
    A_wire.symbol,
    wire_width.symbol * wire_thickness.symbol,
    "Wire cross-section from width and thickness.",
    references=[_INTERCONNECT_GEOMETRY_REF],
    check_units=True,
)

eq_r_per_length = eq(
    "physical.eq.interconnect_r_per_length",
    R_per_length.symbol,
    rho_res.symbol / A_wire.symbol,
    "Resistance per unit length increases as the cross-section shrinks.",
    references=[_INTERCONNECT_TEXT],
    check_units=True,
)

eq_dielectric_permittivity = eq(
    "physical.eq.interconnect_dielectric_permittivity",
    dielectric_permittivity.symbol,
    dielectric_relative_permittivity.symbol * EPSILON_0.symbol,
    "Absolute inter-layer dielectric permittivity equals relative permittivity times vacuum permittivity.",
    references=[_INTERCONNECT_TEXT],
    check_units=True,
)

eq_c_per_length_geom = Approximation(
    "physical.eq.interconnect_c_per_length_geom",
    C_per_length.symbol,
    dielectric_permittivity.symbol
    * fringe_cap_factor.symbol
    * wire_width.symbol
    / wire_spacing.symbol,
    wire_spacing.symbol > 0,
    "Capacitance per unit length from effective dielectric permittivity, width-over-spacing geometry, and fringe factor.",
    references=[_INTERCONNECT_TEXT],
    check_units=True,
)

eq_wire_cap_total = eq(
    "physical.eq.interconnect_c_total",
    C_wire_total.symbol,
    C_per_length.symbol * L_wire.symbol,
    "Line capacitance from capacitance density times length.",
    references=[_INTERCONNECT_TEXT],
    check_units=True,
)

eq_via_resistance_total = eq(
    "physical.eq.via_resistance_total",
    R_via_total.symbol,
    n_vias.symbol * R_via_single.symbol,
    "Total via resistance is the count times single-via resistance.",
    references=[_INTERCONNECT_TEXT],
    check_units=True,
)

eq_path_resistance = eq(
    "physical.eq.path_resistance",
    R_path_total.symbol,
    R_res.symbol + R_via_total.symbol,
    "End-to-end path resistance combines wire and via resistance.",
    references=[_INTERCONNECT_TEXT],
    check_units=True,
)

eq_distributed_rc_delay = eq(
    "physical.eq.distributed_rc_delay",
    tau_wire_rc.symbol,
    R_per_length.symbol * C_per_length.symbol * L_wire.symbol**2 / 2,
    "Distributed RC delay of a uniform wire from first-moment Elmore reasoning.",
    references=[_INTERCONNECT_TEXT],
    check_units=True,
)

eq_omega_signal = eq(
    "physical.eq.angular_frequency",
    omega_signal.symbol,
    TWO_PI * f_signal.symbol,
    "Angular frequency omega = 2 pi f.",
    references=[_INTERCONNECT_TEXT],
    check_units=True,
)

eq_skin_depth = eq(
    "physical.eq.skin_depth",
    skin_depth.symbol,
    sp.sqrt(2 * rho_res.symbol / (omega_signal.symbol * mu_wire.symbol)),
    "Classical skin-depth model delta = sqrt(2 rho / (omega mu)).",
    references=[_INTERCONNECT_TEXT],
    check_units=True,
)

eq_ac_resistance = PiecewiseEquation(
    "physical.eq.ac_resistance",
    R_wire_ac.symbol,
    [
        (R_res.symbol, skin_depth.symbol >= wire_thickness.symbol / 2),
        (R_res.symbol * wire_thickness.symbol / (2 * skin_depth.symbol), True),
    ],
    "Approximate AC resistance inflation from skin effect.",
    references=[_INTERCONNECT_TEXT],
    check_units=True,
)

eq_crosstalk = eq(
    "physical.eq.crosstalk_voltage",
    V_xtalk.symbol,
    V_aggressor.symbol * C_couple.symbol /
    (C_couple.symbol + C_victim_load.symbol + C_wire_total.symbol),
    "Capacitive-divider estimate of crosstalk voltage on the victim line.",
    references=[_INTERCONNECT_TEXT],
    check_units=True,
)


INTERCONNECT_EQUATIONS = [
    ineq_route_detour_factor_at_least_unity,
    ineq_route_length_positive,
    eq_wire_length_from_route,
    eq_route_span_from_hops,
    eq_metal_pitch_scale,
    eq_wire_pitch_from_process,
    eq_wire_width,
    eq_wire_thickness,
    eq_wire_spacing,
    eq_wire_area,
    eq_r_per_length,
    eq_dielectric_permittivity,
    eq_c_per_length_geom,
    eq_wire_cap_total,
    eq_via_resistance_total,
    eq_path_resistance,
    eq_distributed_rc_delay,
    eq_omega_signal,
    eq_skin_depth,
    eq_ac_resistance,
    eq_crosstalk,
]


INTERCONNECT_EQUATION_EXPORTS = [
    "ineq_route_detour_factor_at_least_unity",
    "ineq_route_length_positive",
    "eq_wire_length_from_route", "eq_route_span_from_hops",
    "eq_metal_pitch_scale", "eq_wire_pitch_from_process", "eq_wire_width", "eq_wire_thickness",
    "eq_wire_spacing", "eq_wire_area", "eq_r_per_length",
    "eq_dielectric_permittivity", "eq_c_per_length_geom",
    "eq_wire_cap_total", "eq_via_resistance_total", "eq_path_resistance",
    "eq_distributed_rc_delay", "eq_omega_signal", "eq_skin_depth",
    "eq_ac_resistance", "eq_crosstalk",
]


__all__ = [
    *INTERCONNECT_EQUATION_EXPORTS,
    "INTERCONNECT_EQUATIONS",
]
