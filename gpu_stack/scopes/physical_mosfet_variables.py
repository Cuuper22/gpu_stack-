"""
scopes/physical_mosfet_variables.py
===================================

MOSFET variable declarations, split the same way the physics splits.
Electrostatics: terminal voltages, threshold voltage and its body-effect
and DIBL modulation, channel geometry, oxide thickness and EOT, gate
capacitance, and subthreshold swing. Current regimes: mobility-based drive
current in triode and saturation, subthreshold leakage, and gate tunneling.
The equations connecting them live in the sibling equations module.
"""

import sympy as sp

from ..core import var
from ..core.units import AMPERE, FARAD, METER, VOLT
from .physical_mosfet_refs import _DEVICE_GEOMETRY_REF, _MOS_TEXT


# ---------------------------------------------------------------------------
# Electrostatics: what gate voltage turns the channel on, and what shifts that threshold
# ---------------------------------------------------------------------------

V_gs = var(
    "physical.mosfet.v_gs", "V_GS", "V",
    "Gate-to-source voltage.",
    scope="physical",
    sp_units=VOLT,
    references=[_MOS_TEXT],
)
V_ds = var(
    "physical.mosfet.v_ds", "V_DS", "V",
    "Drain-to-source voltage.",
    scope="physical",
    sp_units=VOLT,
    references=[_MOS_TEXT],
)
V_th = var(
    "physical.mosfet.v_th", "V_T0", "V",
    "Long-channel, zero-body-bias threshold voltage baseline.",
    scope="physical",
    sp_units=VOLT,
    references=[_MOS_TEXT],
)
V_sb = var(
    "physical.mosfet.v_sb", "V_SB", "V",
    "Source-to-body bias. Drives body effect.",
    scope="physical",
    sp_units=VOLT,
    references=[_MOS_TEXT],
)
phi_f = var(
    "physical.mosfet.phi_f", "phi_F", "V",
    "Fermi potential magnitude used in body-effect threshold shifts.",
    scope="physical",
    sp_units=VOLT,
    references=[_MOS_TEXT],
)
gamma_body = var(
    "physical.mosfet.body_effect_coeff", "gamma_body", "V^(1/2)",
    "Body-effect coefficient for threshold modulation.",
    scope="physical",
    sp_units=VOLT**sp.Rational(1, 2),
    references=[_MOS_TEXT],
)
eta_dibl = var(
    "physical.mosfet.dibl_coeff", "eta_DIBL", "dimensionless",
    "Drain-induced barrier-lowering coefficient.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[_MOS_TEXT],
)
V_th_eff = var(
    "physical.mosfet.v_th_eff", "V_T_eff", "V",
    "Effective threshold including body effect and DIBL.",
    scope="physical",
    sp_units=VOLT,
    references=[_MOS_TEXT],
)

W_channel = var(
    "physical.mosfet.width", "W_g", "m",
    "Channel width.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[_MOS_TEXT],
)
channel_parallel_count = var(
    "physical.mosfet.channel_parallel_count", "N_chan_parallel", "channels",
    "Number of parallel effective channels contributing drive width.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[_DEVICE_GEOMETRY_REF],
)
channel_unit_width = var(
    "physical.mosfet.channel_unit_width", "W_chan_unit", "m",
    "Effective width contributed by one fin, nanosheet, or unit channel.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[_DEVICE_GEOMETRY_REF],
)
channel_width_bias = var(
    "physical.mosfet.channel_width_bias", "Delta_W_chan", "m",
    "Signed process/layout width bias applied to the replicated channel width.",
    scope="physical",
    positive=False,
    sp_units=METER,
    references=[_DEVICE_GEOMETRY_REF],
)
t_ox = var(
    "physical.mosfet.oxide_thickness", "t_ox", "m",
    "Physical gate-oxide thickness.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[_MOS_TEXT],
)
equivalent_oxide_thickness = var(
    "physical.mosfet.eot", "t_EOT", "m",
    "Equivalent oxide thickness, expressed as an SiO2-equivalent electrostatic thickness.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[_DEVICE_GEOMETRY_REF],
)
sio2_relative_permittivity = var(
    "physical.mosfet.sio2_relative_permittivity", "epsilon_SiO2_rel", "dimensionless",
    "Relative permittivity used for the SiO2-equivalent EOT reference material.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[_DEVICE_GEOMETRY_REF],
)
epsilon_ox_rel = var(
    "physical.mosfet.oxide_relative_permittivity", "epsilon_ox_rel", "dimensionless",
    "Relative permittivity of the gate dielectric.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[_MOS_TEXT],
)
epsilon_ox = var(
    "physical.mosfet.oxide_permittivity", "epsilon_ox", "F/m",
    "Absolute permittivity of the gate dielectric.",
    scope="physical",
    positive=True,
    sp_units=FARAD / METER,
    references=[_MOS_TEXT],
)
C_ox = var(
    "physical.mosfet.c_ox", "C_ox", "F/m^2",
    "Gate-oxide capacitance per unit area.",
    scope="physical",
    positive=True,
    sp_units=FARAD / METER**2,
    references=[_MOS_TEXT],
)
E_ox = var(
    "physical.mosfet.oxide_field", "E_ox", "V/m",
    "Approximate oxide electric field.",
    scope="physical",
    sp_units=VOLT / METER,
    references=[_MOS_TEXT],
)

V_thermal = var(
    "physical.mosfet.thermal_voltage", "V_therm", "V",
    "Thermal voltage k_B T / q.",
    scope="physical",
    sp_units=VOLT,
    references=[_MOS_TEXT],
)
subthreshold_swing_floor = var(
    "physical.mosfet.subthreshold_swing_floor", "S_min", "V",
    "Thermodynamic lower bound on subthreshold swing, conventionally reported per decade.",
    scope="physical",
    positive=True,
    sp_units=VOLT,
    references=[_MOS_TEXT],
)
subthreshold_swing = var(
    "physical.mosfet.subthreshold_swing", "S_sub", "V",
    "Actual subthreshold swing, conventionally V per decade of drain current.",
    scope="physical",
    positive=True,
    sp_units=VOLT,
    references=[_MOS_TEXT],
)


# ---------------------------------------------------------------------------
# Current regimes: how much flows once it is on (triode, saturation, subthreshold, tunneling)
# ---------------------------------------------------------------------------

lambda_clm = var(
    "physical.mosfet.channel_length_modulation", "lambda_CLM", "1/V",
    "Channel-length-modulation coefficient.",
    scope="physical",
    nonnegative=True,
    sp_units=1 / VOLT,
    references=[_MOS_TEXT],
)
I_ds_triode = var(
    "physical.mosfet.i_ds_triode", "I_DS_tri", "A",
    "Drain current in the triode or linear region.",
    scope="physical",
    sp_units=AMPERE,
    references=[_MOS_TEXT],
)
I_ds_sat = var(
    "physical.mosfet.i_ds_sat", "I_DS_sat", "A",
    "Drain current in strong inversion and saturation.",
    scope="physical",
    sp_units=AMPERE,
    references=[_MOS_TEXT],
)
I_ds_sub = var(
    "physical.mosfet.i_ds_sub", "I_DS_sub", "A",
    "Drain current in the subthreshold regime.",
    scope="physical",
    sp_units=AMPERE,
    references=[_MOS_TEXT],
)
I_ds = var(
    "physical.mosfet.i_ds", "I_DS", "A",
    "Piecewise drain current across subthreshold, triode, and saturation regimes.",
    scope="physical",
    sp_units=AMPERE,
    references=[_MOS_TEXT],
)
I_0 = var(
    "physical.mosfet.i0", "I0", "A",
    "Subthreshold pre-exponential current scale.",
    scope="physical",
    sp_units=AMPERE,
    references=[_MOS_TEXT],
)
n_ideality = var(
    "physical.mosfet.ideality", "n_id", "dimensionless",
    "Subthreshold ideality factor. One is fantasy. Real devices are worse.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[_MOS_TEXT],
)

J_gate_0 = var(
    "physical.mosfet.gate_tunnel_prefactor", "J_g0", "A/m^2",
    "Prefactor for oxide-tunneling current density.",
    scope="physical",
    nonnegative=True,
    sp_units=AMPERE / METER**2,
    references=[_MOS_TEXT],
)
beta_gate_tunnel = var(
    "physical.mosfet.gate_tunnel_decay", "beta_g", "1/m",
    "Thickness-decay coefficient for gate tunneling.",
    scope="physical",
    nonnegative=True,
    sp_units=1 / METER,
    references=[_MOS_TEXT],
)
J_gate = var(
    "physical.mosfet.gate_tunnel_current_density", "J_gate", "A/m^2",
    "Gate-tunneling leakage current density through the dielectric.",
    scope="physical",
    nonnegative=True,
    sp_units=AMPERE / METER**2,
    references=[_MOS_TEXT],
)
I_gate_leak = var(
    "physical.mosfet.i_gate_leak", "I_gate", "A",
    "Total gate-leakage current.",
    scope="physical",
    sp_units=AMPERE,
    references=[_MOS_TEXT],
)
I_leak_total = var(
    "physical.mosfet.i_leak_total", "I_leak_tot", "A",
    "Combined static leakage current from subthreshold and gate tunneling.",
    scope="physical",
    sp_units=AMPERE,
    references=[_MOS_TEXT],
)


MOSFET_VARIABLES = [
    V_gs, V_ds, V_th, V_sb, phi_f, gamma_body, eta_dibl, V_th_eff,
    W_channel, channel_parallel_count, channel_unit_width, channel_width_bias,
    t_ox, equivalent_oxide_thickness, sio2_relative_permittivity,
    epsilon_ox_rel, epsilon_ox, C_ox, E_ox,
    V_thermal, subthreshold_swing_floor, subthreshold_swing,
    lambda_clm, I_ds_triode, I_ds_sat, I_ds_sub, I_ds, I_0, n_ideality,
    J_gate_0, beta_gate_tunnel, J_gate, I_gate_leak, I_leak_total,
]


__all__ = [
    "V_gs", "V_ds", "V_th", "V_sb", "phi_f", "gamma_body", "eta_dibl",
    "V_th_eff", "W_channel", "t_ox", "epsilon_ox_rel", "epsilon_ox",
    "channel_parallel_count", "channel_unit_width", "channel_width_bias",
    "equivalent_oxide_thickness", "sio2_relative_permittivity",
    "C_ox", "E_ox", "V_thermal", "subthreshold_swing_floor",
    "subthreshold_swing", "lambda_clm", "I_ds_triode", "I_ds_sat",
    "I_ds_sub", "I_ds", "I_0", "n_ideality", "J_gate_0",
    "beta_gate_tunnel", "J_gate", "I_gate_leak", "I_leak_total",
    "MOSFET_VARIABLES",
]
