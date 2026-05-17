"""
scopes/physical_interconnect_variables.py
=========================================

Variable declarations for on-chip interconnect geometry and distributed-line
effects.
"""

from ..core import var
from ..core.units import FARAD, HENRY, HZ, METER, OHM, SECOND, VOLT
from .physical_interconnect_refs import _INTERCONNECT_GEOMETRY_REF, _INTERCONNECT_TEXT


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


INTERCONNECT_VARIABLE_EXPORTS = [
    "route_span", "route_detour_factor", "route_hop_count", "metal_pitch_scale",
    "metal_layer_pitch_factor", "wire_pitch", "wire_fill_factor", "wire_aspect_ratio", "wire_width",
    "wire_thickness", "wire_spacing", "dielectric_permittivity",
    "dielectric_relative_permittivity", "fringe_cap_factor", "R_per_length", "C_per_length", "C_wire_total",
    "tau_wire_rc", "n_vias", "R_via_single", "R_via_total",
    "R_path_total", "f_signal", "omega_signal", "mu_wire", "skin_depth",
    "R_wire_ac", "C_couple", "C_victim_load", "V_aggressor", "V_xtalk",
]


__all__ = [
    *INTERCONNECT_VARIABLE_EXPORTS,
    "INTERCONNECT_VARIABLES",
]
