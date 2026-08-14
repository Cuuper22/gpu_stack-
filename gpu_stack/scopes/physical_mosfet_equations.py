"""
scopes/physical_mosfet_equations.py
===================================

MOSFET equations, in two acts. Electrostatics first: gate capacitance
density from oxide thickness (or its EOT equivalent), the thermal voltage
kT/q, the subthreshold swing with its ~60 mV/decade floor at room
temperature, and the effective threshold voltage shifted by body effect and
drain-induced barrier lowering (DIBL). Then current: the triode regime
where the channel acts like a gated resistor, saturation where current
pinches off and flattens, and the subthreshold regime where current decays
exponentially below threshold -- the leakage that static power comes from.
Gate tunneling adds the oxide leakage that thin gate dielectrics pay.
Feasibility constraints keep voltages and geometry in valid ranges.
"""

import sympy as sp

from ..constants import BOLTZMANN, ELEMENTARY_CHARGE, EPSILON_0, LN_10
from ..core import Inequality, PiecewiseEquation, eq
from .physical_mosfet_refs import _DEVICE_GEOMETRY_REF, _MOS_TEXT
from .physical_semiconductor import L_channel, T_temp, mu_mob
from .physical_mosfet_variables import (
    C_ox,
    E_ox,
    I_0,
    I_ds,
    I_ds_sat,
    I_ds_sub,
    I_ds_triode,
    I_gate_leak,
    I_leak_total,
    J_gate,
    J_gate_0,
    V_ds,
    V_gs,
    V_sb,
    V_th,
    V_th_eff,
    V_thermal,
    W_channel,
    beta_gate_tunnel,
    channel_parallel_count,
    channel_unit_width,
    channel_width_bias,
    epsilon_ox,
    epsilon_ox_rel,
    equivalent_oxide_thickness,
    eta_dibl,
    gamma_body,
    lambda_clm,
    n_ideality,
    phi_f,
    sio2_relative_permittivity,
    subthreshold_swing,
    subthreshold_swing_floor,
    t_ox,
)


eq_oxide_permittivity = eq(
    "physical.eq.oxide_permittivity",
    epsilon_ox.symbol,
    epsilon_ox_rel.symbol * EPSILON_0.symbol,
    "Absolute oxide permittivity equals relative permittivity times vacuum permittivity.",
    references=[_MOS_TEXT],
    check_units=True,
)

eq_channel_width = eq(
    "physical.eq.mosfet_channel_width",
    W_channel.symbol,
    channel_parallel_count.symbol * channel_unit_width.symbol + channel_width_bias.symbol,
    "Effective MOSFET width from replicated channel count, per-channel effective width, and signed process/layout bias.",
    references=[_DEVICE_GEOMETRY_REF],
    check_units=True,
)

ineq_channel_parallel_count_at_least_one = Inequality(
    "physical.ineq.mosfet_channel_parallel_count_at_least_one",
    channel_parallel_count.symbol,
    sp.Integer(1),
    ">=",
    "A MOSFET drive-width decomposition must contain at least one effective channel.",
    references=[_DEVICE_GEOMETRY_REF],
    check_units=True,
)
ineq_channel_width_positive = Inequality(
    "physical.ineq.mosfet_channel_width_positive",
    W_channel.symbol,
    sp.Integer(0),
    ">",
    "Effective MOSFET channel width must remain positive after signed width bias.",
    references=[_DEVICE_GEOMETRY_REF],
)

eq_oxide_thickness_from_eot = eq(
    "physical.eq.oxide_thickness_from_eot",
    t_ox.symbol,
    equivalent_oxide_thickness.symbol
    * epsilon_ox_rel.symbol
    / sio2_relative_permittivity.symbol,
    "Physical high-k oxide thickness from SiO2-equivalent EOT and relative-permittivity ratio.",
    references=[_DEVICE_GEOMETRY_REF],
    check_units=True,
)

eq_gate_capacitance_density = eq(
    "physical.eq.gate_capacitance_density",
    C_ox.symbol,
    epsilon_ox.symbol / t_ox.symbol,
    "Gate-oxide capacitance density C_ox = epsilon_ox / t_ox.",
    references=[_MOS_TEXT],
    check_units=True,
)

eq_oxide_field = eq(
    "physical.eq.oxide_field",
    E_ox.symbol,
    V_gs.symbol / t_ox.symbol,
    "Uniform-field estimate through the gate dielectric.",
    references=[_MOS_TEXT],
    check_units=True,
)

eq_thermal_voltage = eq(
    "physical.eq.thermal_voltage",
    V_thermal.symbol,
    BOLTZMANN.symbol * T_temp.symbol / ELEMENTARY_CHARGE.symbol,
    "Thermal voltage V_T = k_B T / q.",
    references=[_MOS_TEXT],
    check_units=True,
)

eq_subthreshold_swing_floor = eq(
    "physical.eq.subthreshold_swing_floor",
    subthreshold_swing_floor.symbol,
    LN_10 * V_thermal.symbol,
    "Thermodynamic lower bound on subthreshold swing, reported per decade.",
    references=[_MOS_TEXT],
    check_units=True,
)

eq_subthreshold_swing = eq(
    "physical.eq.subthreshold_swing",
    subthreshold_swing.symbol,
    n_ideality.symbol * subthreshold_swing_floor.symbol,
    "Actual subthreshold swing scales above the thermal floor by the ideality factor.",
    references=[_MOS_TEXT],
    check_units=True,
)
ineq_subthreshold_swing_floor = Inequality(
    "physical.eq.subthreshold_swing_floor_constraint",
    subthreshold_swing.symbol,
    subthreshold_swing_floor.symbol,
    ">=",
    "No MOSFET beats the Boltzmann subthreshold-swing floor at a given temperature.",
    references=[_MOS_TEXT],
    check_units=True,
)
ineq_ideality_at_least_one = Inequality(
    "physical.ineq.mosfet_ideality_at_least_one",
    n_ideality.symbol,
    sp.Integer(1),
    ">=",
    "MOSFET subthreshold ideality factor cannot be below the thermodynamic ideal.",
    references=[_MOS_TEXT],
    check_units=True,
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
    references=[_MOS_TEXT],
    check_units=True,
)

eq_mosfet_triode = eq(
    "physical.eq.mosfet_triode",
    I_ds_triode.symbol,
    (mu_mob.symbol * C_ox.symbol * W_channel.symbol / L_channel.symbol)
    * ((V_gs.symbol - V_th_eff.symbol) * V_ds.symbol - V_ds.symbol**2 / 2),
    "Long-channel triode-region drain current approximation.",
    references=["Classical square-law MOS model, triode region."],
    check_units=True,
)

eq_mosfet_saturation = eq(
    "physical.eq.mosfet_saturation",
    I_ds_sat.symbol,
    (mu_mob.symbol * C_ox.symbol * W_channel.symbol / (2 * L_channel.symbol))
    * (V_gs.symbol - V_th_eff.symbol) ** 2
    * (1 + lambda_clm.symbol * V_ds.symbol),
    "Strong-inversion saturation current with channel-length modulation.",
    references=["Classical square-law MOS model with first-order CLM."],
    check_units=True,
)

eq_mosfet_subthreshold = eq(
    "physical.eq.mosfet_subthreshold",
    I_ds_sub.symbol,
    I_0.symbol
    * sp.exp((V_gs.symbol - V_th_eff.symbol) / (n_ideality.symbol * V_thermal.symbol))
    * (1 - sp.exp(-V_ds.symbol / V_thermal.symbol)),
    "Subthreshold current with the usual thermal-voltage scaling and finite V_DS correction.",
    references=[_MOS_TEXT],
    check_units=True,
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
    references=[_MOS_TEXT],
    check_units=True,
)

eq_gate_tunnel_density = eq(
    "physical.eq.gate_tunnel_density",
    J_gate.symbol,
    J_gate_0.symbol * sp.exp(-beta_gate_tunnel.symbol * t_ox.symbol),
    "Thickness-sensitive gate-tunneling leakage model.",
    references=["Simplified direct-tunneling form. Coefficients remain process-dependent Variables."],
    check_units=True,
)

eq_gate_tunnel_current = eq(
    "physical.eq.gate_tunnel_current",
    I_gate_leak.symbol,
    J_gate.symbol * W_channel.symbol * L_channel.symbol,
    "Gate-leakage current density integrated over gate area.",
    references=[_MOS_TEXT],
    check_units=True,
)

eq_total_leakage = eq(
    "physical.eq.total_leakage",
    I_leak_total.symbol,
    I_ds_sub.symbol + I_gate_leak.symbol,
    "Total static leakage current combines subthreshold and gate tunneling.",
    references=[_MOS_TEXT],
    check_units=True,
)


MOSFET_EQUATIONS = [
    eq_oxide_permittivity,
    eq_channel_width,
    ineq_channel_parallel_count_at_least_one,
    ineq_channel_width_positive,
    eq_oxide_thickness_from_eot,
    eq_gate_capacitance_density,
    eq_oxide_field,
    eq_thermal_voltage,
    eq_subthreshold_swing_floor,
    eq_subthreshold_swing,
    ineq_subthreshold_swing_floor,
    ineq_ideality_at_least_one,
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
    "eq_oxide_permittivity", "eq_channel_width",
    "ineq_channel_parallel_count_at_least_one",
    "ineq_channel_width_positive",
    "eq_oxide_thickness_from_eot", "eq_gate_capacitance_density", "eq_oxide_field",
    "eq_thermal_voltage", "eq_subthreshold_swing_floor",
    "eq_subthreshold_swing", "ineq_subthreshold_swing_floor",
    "ineq_ideality_at_least_one",
    "eq_effective_threshold", "eq_mosfet_triode", "eq_mosfet_saturation",
    "eq_mosfet_subthreshold", "eq_mosfet_piecewise",
    "eq_gate_tunnel_density", "eq_gate_tunnel_current", "eq_total_leakage",
    "MOSFET_EQUATIONS",
]
