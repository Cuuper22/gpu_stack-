"""
scopes/physical_interconnect.py
===============================

Interconnect geometry and distributed-line effects.

The point here is simple: on-chip wires are not free, not lumped, and not
immune to scaling pain. Shrink pitch, pay in resistance.
"""

import sympy as sp

from ..core import PiecewiseEquation, var, eq
from ..constants import TWO_PI, MU_0
from .physical_semiconductor import A_wire, L_wire, R_res, rho_res


wire_pitch = var(
    "physical.interconnect.pitch", "p_wire", "m",
    "Interconnect pitch at the metal layer of interest.",
    scope="physical",
)
wire_fill_factor = var(
    "physical.interconnect.fill_factor", "phi_fill", "dimensionless",
    "Fraction of pitch occupied by conductor width.",
    scope="physical",
)
wire_aspect_ratio = var(
    "physical.interconnect.aspect_ratio", "AR_wire", "dimensionless",
    "Metal thickness divided by metal width.",
    scope="physical",
)
wire_width = var(
    "physical.interconnect.width", "w_wire", "m",
    "Physical wire width.",
    scope="physical",
)
wire_thickness = var(
    "physical.interconnect.thickness", "t_wire", "m",
    "Physical wire thickness.",
    scope="physical",
)
R_per_length = var(
    "physical.interconnect.r_per_length", "R_prime_w", "ohm/m",
    "Distributed resistance per unit length.",
    scope="physical",
)
C_per_length = var(
    "physical.interconnect.c_per_length", "C_prime_w", "F/m",
    "Distributed capacitance per unit length.",
    scope="physical",
)
C_wire_total = var(
    "physical.interconnect.c_total", "C_wire", "F",
    "Total interconnect capacitance of a line segment.",
    scope="physical",
)
tau_wire_rc = var(
    "physical.interconnect.rc_delay", "tau_wire", "s",
    "Distributed RC delay of a uniform line segment.",
    scope="physical",
)

n_vias = var(
    "physical.interconnect.n_vias", "N_via", "dimensionless",
    "Number of vias in the vertical path.",
    scope="physical",
)
R_via_single = var(
    "physical.interconnect.via_resistance", "R_via", "ohm",
    "Resistance of one via.",
    scope="physical",
)
R_via_total = var(
    "physical.interconnect.via_resistance_total", "R_via_tot", "ohm",
    "Aggregate via resistance along the path.",
    scope="physical",
)
R_path_total = var(
    "physical.interconnect.path_resistance", "R_path", "ohm",
    "End-to-end path resistance including wire and vias.",
    scope="physical",
)

f_signal = var(
    "physical.interconnect.signal_frequency", "f_sig", "Hz",
    "Signal spectral content or representative switching frequency.",
    scope="physical",
)
omega_signal = var(
    "physical.interconnect.angular_frequency", "omega_sig", "rad/s",
    "Angular frequency corresponding to the signal content.",
    scope="physical",
)
mu_wire = var(
    "physical.interconnect.permeability", "mu_wire", "H/m",
    "Magnetic permeability of the conductor environment.",
    scope="physical",
)
skin_depth = var(
    "physical.interconnect.skin_depth", "delta_skin", "m",
    "Skin depth for current crowding at high frequency.",
    scope="physical",
)
R_wire_ac = var(
    "physical.interconnect.ac_resistance", "R_wire_ac", "ohm",
    "Approximate AC wire resistance including skin-effect inflation.",
    scope="physical",
)

C_couple = var(
    "physical.interconnect.c_couple", "C_cpl", "F",
    "Mutual coupling capacitance from an aggressor line.",
    scope="physical",
)
C_victim_load = var(
    "physical.interconnect.c_victim_load", "C_victim", "F",
    "Victim-line capacitance excluding the explicit coupling term.",
    scope="physical",
)
V_aggressor = var(
    "physical.interconnect.v_aggressor", "V_agg", "V",
    "Aggressor transition amplitude driving a coupled neighbor.",
    scope="physical",
)
V_xtalk = var(
    "physical.interconnect.v_crosstalk", "V_xtalk", "V",
    "Approximate crosstalk-induced victim voltage excursion.",
    scope="physical",
)


eq_wire_width = eq(
    "physical.eq.interconnect_width",
    wire_width.symbol,
    wire_pitch.symbol * wire_fill_factor.symbol,
    "Wire width from pitch and routing fill factor.",
)

eq_wire_thickness = eq(
    "physical.eq.interconnect_thickness",
    wire_thickness.symbol,
    wire_aspect_ratio.symbol * wire_width.symbol,
    "Wire thickness from aspect ratio and wire width.",
)

eq_wire_area = eq(
    "physical.eq.interconnect_area",
    A_wire.symbol,
    wire_width.symbol * wire_thickness.symbol,
    "Wire cross-section from width and thickness.",
)

eq_r_per_length = eq(
    "physical.eq.interconnect_r_per_length",
    R_per_length.symbol,
    rho_res.symbol / A_wire.symbol,
    "Resistance per unit length increases as the cross-section shrinks.",
)

eq_wire_cap_total = eq(
    "physical.eq.interconnect_c_total",
    C_wire_total.symbol,
    C_per_length.symbol * L_wire.symbol,
    "Line capacitance from capacitance density times length.",
)

eq_via_resistance_total = eq(
    "physical.eq.via_resistance_total",
    R_via_total.symbol,
    n_vias.symbol * R_via_single.symbol,
    "Total via resistance is the count times single-via resistance.",
)

eq_path_resistance = eq(
    "physical.eq.path_resistance",
    R_path_total.symbol,
    R_res.symbol + R_via_total.symbol,
    "End-to-end path resistance combines wire and via resistance.",
)

eq_distributed_rc_delay = eq(
    "physical.eq.distributed_rc_delay",
    tau_wire_rc.symbol,
    R_per_length.symbol * C_per_length.symbol * L_wire.symbol**2 / 2,
    "Distributed RC delay of a uniform wire from first-moment Elmore reasoning.",
)

eq_omega_signal = eq(
    "physical.eq.angular_frequency",
    omega_signal.symbol,
    TWO_PI * f_signal.symbol,
    "Angular frequency omega = 2 pi f.",
)

eq_skin_depth = eq(
    "physical.eq.skin_depth",
    skin_depth.symbol,
    sp.sqrt(2 * rho_res.symbol / (omega_signal.symbol * mu_wire.symbol)),
    "Classical skin-depth model delta = sqrt(2 rho / (omega mu)).",
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
)


INTERCONNECT_VARIABLES = [
    wire_pitch, wire_fill_factor, wire_aspect_ratio, wire_width, wire_thickness,
    R_per_length, C_per_length, C_wire_total, tau_wire_rc,
    n_vias, R_via_single, R_via_total, R_path_total,
    f_signal, omega_signal, mu_wire, skin_depth, R_wire_ac,
    C_couple, C_victim_load, V_aggressor, V_xtalk,
]

INTERCONNECT_EQUATIONS = [
    eq_wire_width,
    eq_wire_thickness,
    eq_wire_area,
    eq_r_per_length,
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
    "wire_pitch", "wire_fill_factor", "wire_aspect_ratio", "wire_width",
    "wire_thickness", "R_per_length", "C_per_length", "C_wire_total",
    "tau_wire_rc", "n_vias", "R_via_single", "R_via_total",
    "R_path_total", "f_signal", "omega_signal", "mu_wire", "skin_depth",
    "R_wire_ac", "C_couple", "C_victim_load", "V_aggressor", "V_xtalk",
    "eq_wire_width", "eq_wire_thickness", "eq_wire_area", "eq_r_per_length",
    "eq_wire_cap_total", "eq_via_resistance_total", "eq_path_resistance",
    "eq_distributed_rc_delay", "eq_omega_signal", "eq_skin_depth",
    "eq_ac_resistance", "eq_crosstalk",
    "INTERCONNECT_VARIABLES", "INTERCONNECT_EQUATIONS",
]
