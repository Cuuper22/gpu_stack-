"""
scopes/physical_cmos_logic.py
=============================

CMOS logic, delay, and power.

This is the bridge from transistor physics to the abstractions other scopes
actually care about, namely clock, load capacitance, and power.
"""

from ..core import Inequality, var, eq
from ..constants import BOLTZMANN, LN_2
from .physical_semiconductor import L_wire, T_temp
from .physical_interconnect import C_per_length, C_wire_total, R_per_length
from .physical_mosfet import C_ox, I_leak_total, L_channel, W_channel


C_gate_input = var(
    "physical.gate.c_input", "C_in_gate", "F",
    "Input capacitance of a minimum abstraction gate, dominated by gate capacitance.",
    scope="physical",
)
fanout = var(
    "physical.gate.fanout", "FO", "dimensionless",
    "Electrical fanout, number of similar gate inputs driven by this node.",
    scope="physical",
)
C_wire_load = var(
    "physical.gate.c_wire_load", "C_wire_load", "F",
    "Interconnect capacitance presented to the gate output node.",
    scope="physical",
)
C_load = var(
    "physical.gate.c_load", "C_L", "F",
    "Total switched load capacitance at the gate output.",
    scope="physical",
)
R_on = var(
    "physical.gate.r_on", "R_on", "ohm",
    "Effective on-resistance of the switching network.",
    scope="physical",
)
tau_rc = var(
    "physical.gate.rc_delay", "tau_RC", "s",
    "First-order RC time constant for the gate output node.",
    scope="physical",
)
t_prop = var(
    "physical.gate.prop_delay", "t_p", "s",
    "Propagation delay to the 50 percent level.",
    scope="physical",
)
t_elmore = var(
    "physical.gate.elmore_delay", "t_elmore", "s",
    "Elmore-delay estimate including distributed interconnect.",
    scope="physical",
)
V_dd = var(
    "physical.supply_voltage", "V_DD", "V",
    "Supply voltage for the logic domain.",
    scope="physical",
)

P_dyn = var(
    "physical.power.dynamic", "P_dyn", "W",
    "Dynamic switching power of a gate output.",
    scope="physical",
)
P_stat = var(
    "physical.power.static", "P_stat", "W",
    "Static leakage power of a gate.",
    scope="physical",
)
P_sc = var(
    "physical.power.short_circuit", "P_sc", "W",
    "Short-circuit power while pull-up and pull-down briefly conduct together.",
    scope="physical",
)
P_total_gate = var(
    "physical.power.total_gate", "P_gate", "W",
    "Total per-gate power: dynamic plus leakage plus short-circuit.",
    scope="physical",
)
P_landauer_min = var(
    "physical.power.landauer_min", "P_landauer", "W",
    "Thermodynamic lower bound on dissipated power for irreversible bit erasure.",
    scope="physical",
)
alpha_act = var(
    "physical.gate.activity", "alpha_sw", "dimensionless",
    "Average fraction of cycles in which the node switches.",
    scope="physical",
)
f_clock = var(
    "physical.clock_frequency", "f_clk", "Hz",
    "Clock frequency.",
    scope="physical",
)
T_clk = var(
    "physical.clock_period", "T_clk", "s",
    "Clock period.",
    scope="physical",
)
I_sc_peak = var(
    "physical.gate.i_short_circuit_peak", "I_sc_pk", "A",
    "Peak short-circuit current during an input transition.",
    scope="physical",
)
t_sc = var(
    "physical.gate.short_circuit_window", "t_sc", "s",
    "Time window during which both transistor networks conduct simultaneously.",
    scope="physical",
)
E_landauer = var(
    "physical.gate.landauer_energy", "E_landauer", "J",
    "Landauer minimum energy k_B T ln 2 per erased bit.",
    scope="physical",
)
bits_erased_per_cycle = var(
    "physical.gate.bits_erased_per_cycle", "N_erase", "dimensionless",
    "Logical bit erasures attributed to the gate per cycle in the abstraction.",
    scope="physical",
)


eq_gate_input_cap = eq(
    "physical.eq.gate_input_capacitance",
    C_gate_input.symbol,
    C_ox.symbol * W_channel.symbol * L_channel.symbol,
    "Input capacitance from oxide capacitance density times gate area.",
)

eq_wire_load_cap = eq(
    "physical.eq.gate_wire_load",
    C_wire_load.symbol,
    C_wire_total.symbol,
    "Output wire load is the line capacitance seen by the gate.",
)

eq_total_load_cap = eq(
    "physical.eq.gate_total_load",
    C_load.symbol,
    fanout.symbol * C_gate_input.symbol + C_wire_load.symbol,
    "Total load capacitance is fanout input capacitance plus wire capacitance.",
)

eq_rc_constant = eq(
    "physical.eq.rc_constant",
    tau_rc.symbol,
    R_on.symbol * C_load.symbol,
    "First-order RC time constant of the gate output node.",
)

eq_prop_delay = eq(
    "physical.eq.prop_delay",
    t_prop.symbol,
    LN_2 * tau_rc.symbol,
    "Propagation delay to the 50 percent point for a first-order RC response.",
)

eq_elmore_delay = eq(
    "physical.eq.elmore_delay",
    t_elmore.symbol,
    R_on.symbol * (fanout.symbol * C_gate_input.symbol + C_wire_total.symbol)
    + R_per_length.symbol * C_per_length.symbol * L_wire.symbol**2 / 2,
    "Elmore delay including the distributed interconnect term.",
)

eq_dynamic_power = eq(
    "physical.eq.dynamic_power",
    P_dyn.symbol,
    alpha_act.symbol * C_load.symbol * V_dd.symbol**2 * f_clock.symbol,
    "CMOS dynamic power P = alpha C V^2 f.",
)

eq_static_power = eq(
    "physical.eq.static_power",
    P_stat.symbol,
    I_leak_total.symbol * V_dd.symbol,
    "Static power from total leakage current at the supply voltage.",
)

eq_short_circuit_power = eq(
    "physical.eq.short_circuit_power",
    P_sc.symbol,
    alpha_act.symbol * I_sc_peak.symbol * V_dd.symbol * t_sc.symbol * f_clock.symbol,
    "Short-circuit power from overlap current during switching.",
)

eq_gate_total_power = eq(
    "physical.eq.gate_total_power",
    P_total_gate.symbol,
    P_dyn.symbol + P_stat.symbol + P_sc.symbol,
    "Total gate power adds dynamic, leakage, and short-circuit components.",
)

eq_clock_period = eq(
    "physical.eq.clock_period",
    T_clk.symbol,
    1 / f_clock.symbol,
    "Clock period is the reciprocal of clock frequency.",
)
ineq_clock_timing = Inequality(
    "physical.eq.clock_timing_constraint",
    t_elmore.symbol,
    T_clk.symbol,
    "<=",
    "A single-stage Elmore delay must fit inside one clock period if you want synchronous timing closure.",
)

eq_landauer_energy = eq(
    "physical.eq.landauer_energy",
    E_landauer.symbol,
    BOLTZMANN.symbol * T_temp.symbol * LN_2,
    "Landauer minimum energy for one irreversible bit erasure.",
)

eq_landauer_power = eq(
    "physical.eq.landauer_power",
    P_landauer_min.symbol,
    alpha_act.symbol * bits_erased_per_cycle.symbol * E_landauer.symbol * f_clock.symbol,
    "Thermodynamic lower bound on dissipated power for the modeled logical erasures.",
)
ineq_landauer_floor = Inequality(
    "physical.eq.landauer_floor_constraint",
    P_total_gate.symbol,
    P_landauer_min.symbol,
    ">=",
    "Real logic must dissipate at least the Landauer floor for its irreversible erasures.",
)


CMOS_LOGIC_VARIABLES = [
    C_gate_input, fanout, C_wire_load, C_load, R_on, tau_rc, t_prop, t_elmore,
    V_dd, P_dyn, P_stat, P_sc, P_total_gate, P_landauer_min,
    alpha_act, f_clock, T_clk, I_sc_peak, t_sc, E_landauer,
    bits_erased_per_cycle,
]

CMOS_LOGIC_EQUATIONS = [
    eq_gate_input_cap,
    eq_wire_load_cap,
    eq_total_load_cap,
    eq_rc_constant,
    eq_prop_delay,
    eq_elmore_delay,
    eq_dynamic_power,
    eq_static_power,
    eq_short_circuit_power,
    eq_gate_total_power,
    eq_clock_period,
    ineq_clock_timing,
    eq_landauer_energy,
    eq_landauer_power,
    ineq_landauer_floor,
]


__all__ = [
    "C_gate_input", "fanout", "C_wire_load", "C_load", "R_on", "tau_rc",
    "t_prop", "t_elmore", "V_dd", "P_dyn", "P_stat", "P_sc",
    "P_total_gate", "P_landauer_min", "alpha_act", "f_clock", "T_clk",
    "I_sc_peak", "t_sc", "E_landauer", "bits_erased_per_cycle",
    "eq_gate_input_cap", "eq_wire_load_cap", "eq_total_load_cap",
    "eq_rc_constant", "eq_prop_delay", "eq_elmore_delay",
    "eq_dynamic_power", "eq_static_power", "eq_short_circuit_power",
    "eq_gate_total_power", "eq_clock_period", "ineq_clock_timing",
    "eq_landauer_energy", "eq_landauer_power", "ineq_landauer_floor",
    "CMOS_LOGIC_VARIABLES", "CMOS_LOGIC_EQUATIONS",
]
