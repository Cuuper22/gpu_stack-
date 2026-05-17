"""
scopes/physical_mosfet.py
=========================

Compatibility surface for MOSFET electrostatics and current regimes.

The declarations now live in focused helper modules, but this module keeps the
original import surface stable for downstream physical scope consumers.
"""

import sympy as sp

from ..constants import BOLTZMANN, ELEMENTARY_CHARGE, EPSILON_0, LN_10
from ..core import Inequality, PiecewiseEquation, Reference, var, eq
from ..core.units import AMPERE, FARAD, METER, SECOND, VOLT
from .physical_semiconductor import L_channel, T_temp, mu_mob
from .physical_mosfet_equations import *
from .physical_mosfet_refs import _DEVICE_GEOMETRY_REF, _MOS_TEXT
from .physical_mosfet_variables import *


__all__ = [
    "V_gs", "V_ds", "V_th", "V_sb", "phi_f", "gamma_body", "eta_dibl",
    "V_th_eff", "W_channel", "t_ox", "epsilon_ox_rel", "epsilon_ox",
    "channel_parallel_count", "channel_unit_width", "channel_width_bias",
    "equivalent_oxide_thickness", "sio2_relative_permittivity",
    "C_ox", "E_ox", "V_thermal", "subthreshold_swing_floor",
    "subthreshold_swing", "lambda_clm", "I_ds_triode", "I_ds_sat",
    "I_ds_sub", "I_ds", "I_0", "n_ideality", "J_gate_0",
    "beta_gate_tunnel", "J_gate", "I_gate_leak", "I_leak_total",
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
    "MOSFET_VARIABLES", "MOSFET_EQUATIONS",
]
