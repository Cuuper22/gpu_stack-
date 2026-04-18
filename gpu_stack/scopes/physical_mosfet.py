"""
scopes/physical_mosfet.py
=========================

MOSFET electrostatics and current regimes.

This file keeps the transistor model explicit about what is regime-dependent.
The old square-law-only story was serviceable for a toy notebook and wrong for
modern short-channel work.
"""

import sympy as sp

from ..core import Inequality, PiecewiseEquation, var, eq
from ..constants import BOLTZMANN, ELEMENTARY_CHARGE, EPSILON_0, LN_10
from .physical_semiconductor import L_channel, T_temp, mu_mob


# ---------------------------------------------------------------------------
# Electrostatics and threshold modulation
# ---------------------------------------------------------------------------

V_gs = var(
    "physical.mosfet.v_gs", "V_GS", "V",
    "Gate-to-source voltage.",
    scope="physical",
)
V_ds = var(
    "physical.mosfet.v_ds", "V_DS", "V",
    "Drain-to-source voltage.",
    scope="physical",
)
V_th = var(
    "physical.mosfet.v_th", "V_T0", "V",
    "Long-channel, zero-body-bias threshold voltage baseline.",
    scope="physical",
)
V_sb = var(
    "physical.mosfet.v_sb", "V_SB", "V",
    "Source-to-body bias. Drives body effect.",
    scope="physical",
)
phi_f = var(
    "physical.mosfet.phi_f", "phi_F", "V",
    "Fermi potential magnitude used in body-effect threshold shifts.",
    scope="physical",
)
gamma_body = var(
    "physical.mosfet.body_effect_coeff", "gamma_body", "V^(1/2)",
    "Body-effect coefficient for threshold modulation.",
    scope="physical",
)
eta_dibl = var(
    "physical.mosfet.dibl_coeff", "eta_DIBL", "dimensionless",
    "Drain-induced barrier-lowering coefficient.",
    scope="physical",
)
V_th_eff = var(
    "physical.mosfet.v_th_eff", "V_T_eff", "V",
    "Effective threshold including body effect and DIBL.",
    scope="physical",
)

W_channel = var(
    "physical.mosfet.width", "W_g", "m",
    "Channel width.",
    scope="physical",
)
t_ox = var(
    "physical.mosfet.oxide_thickness", "t_ox", "m",
    "Physical gate-oxide thickness.",
    scope="physical",
)
epsilon_ox_rel = var(
    "physical.mosfet.oxide_relative_permittivity", "epsilon_ox_rel", "dimensionless",
    "Relative permittivity of the gate dielectric.",
    scope="physical",
)
epsilon_ox = var(
    "physical.mosfet.oxide_permittivity", "epsilon_ox", "F/m",
    "Absolute permittivity of the gate dielectric.",
    scope="physical",
)
C_ox = var(
    "physical.mosfet.c_ox", "C_ox", "F/m^2",
    "Gate-oxide capacitance per unit area.",
    scope="physical",
)
E_ox = var(
    "physical.mosfet.oxide_field", "E_ox", "V/m",
    "Approximate oxide electric field.",
    scope="physical",
)

V_thermal = var(
    "physical.mosfet.thermal_voltage", "V_therm", "V",
    "Thermal voltage k_B T / q.",
    scope="physical",
)
subthreshold_swing_floor = var(
    "physical.mosfet.subthreshold_swing_floor", "S_min", "V",
    "Thermodynamic lower bound on subthreshold swing, conventionally reported per decade.",
    scope="physical",
)
subthreshold_swing = var(
    "physical.mosfet.subthreshold_swing", "S_sub", "V",
    "Actual subthreshold swing, conventionally V per decade of drain current.",
    scope="physical",
)


# ---------------------------------------------------------------------------
# Current regimes
# ---------------------------------------------------------------------------

lambda_clm = var(
    "physical.mosfet.channel_length_modulation", "lambda_CLM", "1/V",
    "Channel-length-modulation coefficient.",
    scope="physical",
)
I_ds_triode = var(
    "physical.mosfet.i_ds_triode", "I_DS_tri", "A",
    "Drain current in the triode or linear region.",
    scope="physical",
)
I_ds_sat = var(
    "physical.mosfet.i_ds_sat", "I_DS_sat", "A",
    "Drain current in strong inversion and saturation.",
    scope="physical",
)
I_ds_sub = var(
    "physical.mosfet.i_ds_sub", "I_DS_sub", "A",
    "Drain current in the subthreshold regime.",
    scope="physical",
)
I_ds = var(
    "physical.mosfet.i_ds", "I_DS", "A",
    "Piecewise drain current across subthreshold, triode, and saturation regimes.",
    scope="physical",
)
I_0 = var(
    "physical.mosfet.i0", "I0", "A",
    "Subthreshold pre-exponential current scale.",
    scope="physical",
)
n_ideality = var(
    "physical.mosfet.ideality", "n_id", "dimensionless",
    "Subthreshold ideality factor. One is fantasy. Real devices are worse.",
    scope="physical",
)

J_gate_0 = var(
    "physical.mosfet.gate_tunnel_prefactor", "J_g0", "A/m^2",
    "Prefactor for oxide-tunneling current density.",
    scope="physical",
)
beta_gate_tunnel = var(
    "physical.mosfet.gate_tunnel_decay", "beta_g", "1/m",
    "Thickness-decay coefficient for gate tunneling.",
    scope="physical",
)
J_gate = var(
    "physical.mosfet.gate_tunnel_current_density", "J_gate", "A/m^2",
    "Gate-tunneling leakage current density through the dielectric.",
    scope="physical",
)
I_gate_leak = var(
    "physical.mosfet.i_gate_leak", "I_gate", "A",
    "Total gate-leakage current.",
    scope="physical",
)
I_leak_total = var(
    "physical.mosfet.i_leak_total", "I_leak_tot", "A",
    "Combined static leakage current from subthreshold and gate tunneling.",
    scope="physical",
)


eq_oxide_permittivity = eq(
    "physical.eq.oxide_permittivity",
    epsilon_ox.symbol,
    epsilon_ox_rel.symbol * EPSILON_0.symbol,
    "Absolute oxide permittivity equals relative permittivity times vacuum permittivity.",
)

eq_gate_capacitance_density = eq(
    "physical.eq.gate_capacitance_density",
    C_ox.symbol,
    epsilon_ox.symbol / t_ox.symbol,
    "Gate-oxide capacitance density C_ox = epsilon_ox / t_ox.",
)

eq_oxide_field = eq(
    "physical.eq.oxide_field",
    E_ox.symbol,
    V_gs.symbol / t_ox.symbol,
    "Uniform-field estimate through the gate dielectric.",
)

eq_thermal_voltage = eq(
    "physical.eq.thermal_voltage",
    V_thermal.symbol,
    BOLTZMANN.symbol * T_temp.symbol / ELEMENTARY_CHARGE.symbol,
    "Thermal voltage V_T = k_B T / q.",
)

eq_subthreshold_swing_floor = eq(
    "physical.eq.subthreshold_swing_floor",
    subthreshold_swing_floor.symbol,
    LN_10 * V_thermal.symbol,
    "Thermodynamic lower bound on subthreshold swing, reported per decade.",
)

eq_subthreshold_swing = eq(
    "physical.eq.subthreshold_swing",
    subthreshold_swing.symbol,
    n_ideality.symbol * subthreshold_swing_floor.symbol,
    "Actual subthreshold swing scales above the thermal floor by the ideality factor.",
)
ineq_subthreshold_swing_floor = Inequality(
    "physical.eq.subthreshold_swing_floor_constraint",
    subthreshold_swing.symbol,
    subthreshold_swing_floor.symbol,
    ">=",
    "No MOSFET beats the Boltzmann subthreshold-swing floor at a given temperature.",
)

eq_effective_threshold = eq(
    "physical.eq.effective_threshold",
    V_th_eff.symbol,
    V_th.symbol
    + gamma_body.symbol * (
        sp.sqrt(2 * phi_f.symbol + V_sb.symbol) - sp.sqrt(2 * phi_f.symbol)
    )
    - eta_dibl.symbol * V_ds.symbol,
    "Effective threshold including body effect and DIBL.",
)

eq_mosfet_triode = eq(
    "physical.eq.mosfet_triode",
    I_ds_triode.symbol,
    (mu_mob.symbol * C_ox.symbol * W_channel.symbol / L_channel.symbol)
    * ((V_gs.symbol - V_th_eff.symbol) * V_ds.symbol - V_ds.symbol**2 / 2),
    "Long-channel triode-region drain current approximation.",
    references=["Classical square-law MOS model, triode region."],
)

eq_mosfet_saturation = eq(
    "physical.eq.mosfet_saturation",
    I_ds_sat.symbol,
    (mu_mob.symbol * C_ox.symbol * W_channel.symbol / (2 * L_channel.symbol))
    * (V_gs.symbol - V_th_eff.symbol) ** 2
    * (1 + lambda_clm.symbol * V_ds.symbol),
    "Strong-inversion saturation current with channel-length modulation.",
    references=["Classical square-law MOS model with first-order CLM."],
)

eq_mosfet_subthreshold = eq(
    "physical.eq.mosfet_subthreshold",
    I_ds_sub.symbol,
    I_0.symbol
    * sp.exp((V_gs.symbol - V_th_eff.symbol) / (n_ideality.symbol * V_thermal.symbol))
    * (1 - sp.exp(-V_ds.symbol / V_thermal.symbol)),
    "Subthreshold current with the usual thermal-voltage scaling and finite V_DS correction.",
)

eq_mosfet_piecewise = PiecewiseEquation(
    "physical.eq.mosfet_piecewise",
    I_ds.symbol,
    [
        (I_ds_sub.symbol, V_gs.symbol <= V_th_eff.symbol),
        (
            I_ds_triode.symbol,
            sp.And(
                V_gs.symbol > V_th_eff.symbol,
                V_ds.symbol < (V_gs.symbol - V_th_eff.symbol),
            ),
        ),
        (I_ds_sat.symbol, True),
    ],
    "Piecewise drain current across subthreshold, triode, and saturation regimes.",
)

eq_gate_tunnel_density = eq(
    "physical.eq.gate_tunnel_density",
    J_gate.symbol,
    J_gate_0.symbol * sp.exp(-beta_gate_tunnel.symbol * t_ox.symbol),
    "Thickness-sensitive gate-tunneling leakage model.",
    references=["Simplified direct-tunneling form. Coefficients remain process-dependent Variables."],
)

eq_gate_tunnel_current = eq(
    "physical.eq.gate_tunnel_current",
    I_gate_leak.symbol,
    J_gate.symbol * W_channel.symbol * L_channel.symbol,
    "Gate-leakage current density integrated over gate area.",
)

eq_total_leakage = eq(
    "physical.eq.total_leakage",
    I_leak_total.symbol,
    I_ds_sub.symbol + I_gate_leak.symbol,
    "Total static leakage current combines subthreshold and gate tunneling.",
)


MOSFET_VARIABLES = [
    V_gs, V_ds, V_th, V_sb, phi_f, gamma_body, eta_dibl, V_th_eff,
    W_channel, t_ox, epsilon_ox_rel, epsilon_ox, C_ox, E_ox,
    V_thermal, subthreshold_swing_floor, subthreshold_swing,
    lambda_clm, I_ds_triode, I_ds_sat, I_ds_sub, I_ds, I_0, n_ideality,
    J_gate_0, beta_gate_tunnel, J_gate, I_gate_leak, I_leak_total,
]

MOSFET_EQUATIONS = [
    eq_oxide_permittivity,
    eq_gate_capacitance_density,
    eq_oxide_field,
    eq_thermal_voltage,
    eq_subthreshold_swing_floor,
    eq_subthreshold_swing,
    ineq_subthreshold_swing_floor,
    eq_effective_threshold,
    eq_mosfet_triode,
    eq_mosfet_saturation,
    eq_mosfet_subthreshold,
    eq_mosfet_piecewise,
    eq_gate_tunnel_density,
    eq_gate_tunnel_current,
    eq_total_leakage,
]


__all__ = [
    "V_gs", "V_ds", "V_th", "V_sb", "phi_f", "gamma_body", "eta_dibl",
    "V_th_eff", "W_channel", "t_ox", "epsilon_ox_rel", "epsilon_ox",
    "C_ox", "E_ox", "V_thermal", "subthreshold_swing_floor",
    "subthreshold_swing", "lambda_clm", "I_ds_triode", "I_ds_sat",
    "I_ds_sub", "I_ds", "I_0", "n_ideality", "J_gate_0",
    "beta_gate_tunnel", "J_gate", "I_gate_leak", "I_leak_total",
    "eq_oxide_permittivity", "eq_gate_capacitance_density", "eq_oxide_field",
    "eq_thermal_voltage", "eq_subthreshold_swing_floor",
    "eq_subthreshold_swing", "ineq_subthreshold_swing_floor",
    "eq_effective_threshold", "eq_mosfet_triode", "eq_mosfet_saturation",
    "eq_mosfet_subthreshold", "eq_mosfet_piecewise",
    "eq_gate_tunnel_density", "eq_gate_tunnel_current", "eq_total_leakage",
    "MOSFET_VARIABLES", "MOSFET_EQUATIONS",
]
