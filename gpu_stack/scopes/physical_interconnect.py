"""
scopes/physical_interconnect.py
===============================

Interconnect geometry and distributed-line effects.

The point here is simple: on-chip wires are not free, not lumped, and not
immune to scaling pain. Shrink pitch, pay in resistance.
"""

import sympy as sp

from ..core import Approximation, Inequality, PiecewiseEquation, Reference, var, eq
from ..core.units import FARAD, HENRY, HZ, METER, OHM, SECOND, VOLT
from ..constants import TWO_PI, MU_0, EPSILON_0
from .physical_semiconductor import (
    A_wire,
    L_wire,
    R_res,
    minimum_metal_pitch,
    process_node_length,
    rho_res,
)


_INTERCONNECT_TEXT = Reference(
    citation="Bakoglu, Circuits, Interconnections, and Packaging for VLSI",
    kind="textbook",
)
_INTERCONNECT_GEOMETRY_REF = Reference(
    citation="Interconnect-geometry abstraction: routing pitch and length from process geometry and placement span",
    kind="memo",
)


route_span = var(
    "physical.interconnect.route_span", "L_route_span", "m",
    "Manhattan placement span between communicating logic points before routing detours.",
    scope="physical",
    nonnegative=True,
    sp_units=METER,
    references=[_INTERCONNECT_GEOMETRY_REF],
)
route_detour_factor = var(
    "physical.interconnect.route_detour_factor", "k_route_detour", "dimensionless",
    "Routing detour factor above the direct Manhattan span.",
    scope="physical",
    sp_units=1,
    references=[_INTERCONNECT_GEOMETRY_REF],
)
route_hop_count = var(
    "physical.interconnect.route_hop_count", "N_route_hop", "hops",
    "Number of local routing-pitch hops across the modeled placement span.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=1,
    references=[_INTERCONNECT_GEOMETRY_REF],
)
metal_pitch_scale = var(
    "physical.interconnect.pitch_scale", "k_metal_pitch", "dimensionless",
    "Scale factor from nominal process-node length to the modeled metal pitch.",
    scope="physical",
    positive=True,
    sp_units=1,
    references=[_INTERCONNECT_GEOMETRY_REF],
)
metal_layer_pitch_factor = var(
    "physical.interconnect.layer_pitch_factor", "k_metal_layer_pitch", "dimensionless",
    "Multiplier from minimum metal pitch to the modeled routing layer pitch.",
    scope="physical",
    positive=True,
    sp_units=1,
    references=[_INTERCONNECT_GEOMETRY_REF],
)
wire_pitch = var(
    "physical.interconnect.pitch", "p_wire", "m",
    "Interconnect pitch at the metal layer of interest.",
    scope="physical",
    positive=True,
    sp_units=METER,
)
wire_fill_factor = var(
    "physical.interconnect.fill_factor", "phi_fill", "dimensionless",
    "Fraction of pitch occupied by conductor width.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=1,
)
wire_aspect_ratio = var(
    "physical.interconnect.aspect_ratio", "AR_wire", "dimensionless",
    "Metal thickness divided by metal width.",
    scope="physical",
    sp_units=1,
)
wire_width = var(
    "physical.interconnect.width", "w_wire", "m",
    "Physical wire width.",
    scope="physical",
    sp_units=METER,
)
wire_thickness = var(
    "physical.interconnect.thickness", "t_wire", "m",
    "Physical wire thickness.",
    scope="physical",
    sp_units=METER,
)
wire_spacing = var(
    "physical.interconnect.spacing", "s_wire", "m",
    "Edge-to-edge spacing between adjacent wires at the modeled metal layer.",
    scope="physical",
    sp_units=METER,
    references=[_INTERCONNECT_GEOMETRY_REF],
)
dielectric_permittivity = var(
    "physical.interconnect.dielectric_permittivity", "epsilon_ild", "F/m",
    "Effective inter-layer dielectric permittivity around the modeled wire.",
    scope="physical",
    sp_units=FARAD / METER,
    references=[_INTERCONNECT_TEXT],
)
dielectric_relative_permittivity = var(
    "physical.interconnect.relative_permittivity", "epsilon_ild_rel", "dimensionless",
    "Relative permittivity of the effective inter-layer dielectric around the modeled wire.",
    scope="physical",
    sp_units=1,
    references=[_INTERCONNECT_TEXT],
)
fringe_cap_factor = var(
    "physical.interconnect.fringe_cap_factor", "k_fringe_cap", "dimensionless",
    "Fringe and sidewall capacitance factor above the parallel-plate width-over-spacing term.",
    scope="physical",
    sp_units=1,
    references=[_INTERCONNECT_TEXT],
)
R_per_length = var(
    "physical.interconnect.r_per_length", "R_prime_w", "ohm/m",
    "Distributed resistance per unit length.",
    scope="physical",
    sp_units=OHM / METER,
    references=[_INTERCONNECT_TEXT],
)
C_per_length = var(
    "physical.interconnect.c_per_length", "C_prime_w", "F/m",
    "Distributed capacitance per unit length.",
    scope="physical",
    sp_units=FARAD / METER,
    references=[_INTERCONNECT_TEXT],
)
C_wire_total = var(
    "physical.interconnect.c_total", "C_wire", "F",
    "Total interconnect capacitance of a line segment.",
    scope="physical",
    sp_units=FARAD,
)
tau_wire_rc = var(
    "physical.interconnect.rc_delay", "tau_wire", "s",
    "Distributed RC delay of a uniform line segment.",
    scope="physical",
    sp_units=SECOND,
)

n_vias = var(
    "physical.interconnect.n_vias", "N_via", "dimensionless",
    "Number of vias in the vertical path.",
    scope="physical",
    sp_units=1,
)
R_via_single = var(
    "physical.interconnect.via_resistance", "R_via", "ohm",
    "Resistance of one via.",
    scope="physical",
    sp_units=OHM,
)
R_via_total = var(
    "physical.interconnect.via_resistance_total", "R_via_tot", "ohm",
    "Aggregate via resistance along the path.",
    scope="physical",
    sp_units=OHM,
)
R_path_total = var(
    "physical.interconnect.path_resistance", "R_path", "ohm",
    "End-to-end path resistance including wire and vias.",
    scope="physical",
    sp_units=OHM,
)

f_signal = var(
    "physical.interconnect.signal_frequency", "f_sig", "Hz",
    "Signal spectral content or representative switching frequency.",
    scope="physical",
    sp_units=HZ,
)
omega_signal = var(
    "physical.interconnect.angular_frequency", "omega_sig", "rad/s",
    "Angular frequency corresponding to the signal content.",
    scope="physical",
    sp_units=1 / SECOND,
)
mu_wire = var(
    "physical.interconnect.permeability", "mu_wire", "H/m",
    "Magnetic permeability of the conductor environment.",
    scope="physical",
    sp_units=HENRY / METER,
)
skin_depth = var(
    "physical.interconnect.skin_depth", "delta_skin", "m",
    "Skin depth for current crowding at high frequency.",
    scope="physical",
    sp_units=METER,
)
R_wire_ac = var(
    "physical.interconnect.ac_resistance", "R_wire_ac", "ohm",
    "Approximate AC wire resistance including skin-effect inflation.",
    scope="physical",
    sp_units=OHM,
)

C_couple = var(
    "physical.interconnect.c_couple", "C_cpl", "F",
    "Mutual coupling capacitance from an aggressor line.",
    scope="physical",
    sp_units=FARAD,
)
C_victim_load = var(
    "physical.interconnect.c_victim_load", "C_victim", "F",
    "Victim-line capacitance excluding the explicit coupling term.",
    scope="physical",
    sp_units=FARAD,
)
V_aggressor = var(
    "physical.interconnect.v_aggressor", "V_agg", "V",
    "Aggressor transition amplitude driving a coupled neighbor.",
    scope="physical",
    sp_units=VOLT,
)
V_xtalk = var(
    "physical.interconnect.v_crosstalk", "V_xtalk", "V",
    "Approximate crosstalk-induced victim voltage excursion.",
    scope="physical",
    sp_units=VOLT,
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
    check_units=True,
)

eq_wire_thickness = eq(
    "physical.eq.interconnect_thickness",
    wire_thickness.symbol,
    wire_aspect_ratio.symbol * wire_width.symbol,
    "Wire thickness from aspect ratio and wire width.",
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
    check_units=True,
)

eq_r_per_length = eq(
    "physical.eq.interconnect_r_per_length",
    R_per_length.symbol,
    rho_res.symbol / A_wire.symbol,
    "Resistance per unit length increases as the cross-section shrinks.",
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
    check_units=True,
)

eq_via_resistance_total = eq(
    "physical.eq.via_resistance_total",
    R_via_total.symbol,
    n_vias.symbol * R_via_single.symbol,
    "Total via resistance is the count times single-via resistance.",
    check_units=True,
)

eq_path_resistance = eq(
    "physical.eq.path_resistance",
    R_path_total.symbol,
    R_res.symbol + R_via_total.symbol,
    "End-to-end path resistance combines wire and via resistance.",
    check_units=True,
)

eq_distributed_rc_delay = eq(
    "physical.eq.distributed_rc_delay",
    tau_wire_rc.symbol,
    R_per_length.symbol * C_per_length.symbol * L_wire.symbol**2 / 2,
    "Distributed RC delay of a uniform wire from first-moment Elmore reasoning.",
    check_units=True,
)

eq_omega_signal = eq(
    "physical.eq.angular_frequency",
    omega_signal.symbol,
    TWO_PI * f_signal.symbol,
    "Angular frequency omega = 2 pi f.",
    check_units=True,
)

eq_skin_depth = eq(
    "physical.eq.skin_depth",
    skin_depth.symbol,
    sp.sqrt(2 * rho_res.symbol / (omega_signal.symbol * mu_wire.symbol)),
    "Classical skin-depth model delta = sqrt(2 rho / (omega mu)).",
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
)

eq_crosstalk = eq(
    "physical.eq.crosstalk_voltage",
    V_xtalk.symbol,
    V_aggressor.symbol * C_couple.symbol /
    (C_couple.symbol + C_victim_load.symbol + C_wire_total.symbol),
    "Capacitive-divider estimate of crosstalk voltage on the victim line.",
    check_units=True,
)


INTERCONNECT_VARIABLES = [
    route_span, route_detour_factor, route_hop_count, metal_pitch_scale,
    metal_layer_pitch_factor, wire_pitch, wire_fill_factor, wire_aspect_ratio, wire_width, wire_thickness,
    wire_spacing, dielectric_permittivity, dielectric_relative_permittivity,
    fringe_cap_factor,
    R_per_length, C_per_length, C_wire_total, tau_wire_rc,
    n_vias, R_via_single, R_via_total, R_path_total,
    f_signal, omega_signal, mu_wire, skin_depth, R_wire_ac,
    C_couple, C_victim_load, V_aggressor, V_xtalk,
]

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


__all__ = [
    "route_span", "route_detour_factor", "route_hop_count", "metal_pitch_scale",
    "metal_layer_pitch_factor", "wire_pitch", "wire_fill_factor", "wire_aspect_ratio", "wire_width",
    "wire_thickness", "wire_spacing", "dielectric_permittivity",
    "dielectric_relative_permittivity", "fringe_cap_factor", "R_per_length", "C_per_length", "C_wire_total",
    "tau_wire_rc", "n_vias", "R_via_single", "R_via_total",
    "R_path_total", "f_signal", "omega_signal", "mu_wire", "skin_depth",
    "R_wire_ac", "C_couple", "C_victim_load", "V_aggressor", "V_xtalk",
    "ineq_route_detour_factor_at_least_unity",
    "ineq_route_length_positive",
    "eq_wire_length_from_route", "eq_route_span_from_hops",
    "eq_metal_pitch_scale", "eq_wire_pitch_from_process", "eq_wire_width", "eq_wire_thickness",
    "eq_wire_spacing", "eq_wire_area", "eq_r_per_length",
    "eq_dielectric_permittivity", "eq_c_per_length_geom",
    "eq_wire_cap_total", "eq_via_resistance_total", "eq_path_resistance",
    "eq_distributed_rc_delay", "eq_omega_signal", "eq_skin_depth",
    "eq_ac_resistance", "eq_crosstalk",
    "INTERCONNECT_VARIABLES", "INTERCONNECT_EQUATIONS",
]
