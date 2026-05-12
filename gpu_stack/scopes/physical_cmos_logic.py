"""
scopes/physical_cmos_logic.py
=============================

CMOS logic, delay, and power.

This is the bridge from transistor physics to the abstractions other scopes
actually care about, namely clock, load capacitance, and power.
"""

import sympy as sp

from ..core import Approximation, Inequality, Reference, var, eq
from ..core.units import AMPERE, FARAD, HZ, JOULE, OHM, SECOND, VOLT, WATT
from ..constants import BOLTZMANN, LN_2
from .physical_semiconductor import L_wire, T_temp
from .physical_interconnect import C_per_length, C_wire_total, R_per_length
from .physical_mosfet import C_ox, I_leak_total, L_channel, W_channel


_CMOS_POWER_TEXT = Reference(
    citation="Weste and Harris, CMOS VLSI Design, delay and switching power models",
    kind="textbook",
)
_CLOCK_TIMING_REF = Reference(
    citation="Synchronous timing abstraction: operating clock as derated inverse critical-path delay",
    kind="memo",
)


C_gate_input = var(
    "physical.gate.c_input", "C_in_gate", "F",
    "Input capacitance of a minimum abstraction gate, dominated by gate capacitance.",
    scope="physical",
    sp_units=FARAD,
    references=[_CMOS_POWER_TEXT],
)
fanout = var(
    "physical.gate.fanout", "FO", "dimensionless",
    "Electrical fanout, number of similar gate inputs driven by this node.",
    scope="physical",
    sp_units=1,
)
C_wire_load = var(
    "physical.gate.c_wire_load", "C_wire_load", "F",
    "Interconnect capacitance presented to the gate output node.",
    scope="physical",
    sp_units=FARAD,
)
C_load = var(
    "physical.gate.c_load", "C_L", "F",
    "Total switched load capacitance at the gate output.",
    scope="physical",
    sp_units=FARAD,
)
R_on = var(
    "physical.gate.r_on", "R_on", "ohm",
    "Effective on-resistance of the switching network.",
    scope="physical",
    sp_units=OHM,
)
tau_rc = var(
    "physical.gate.rc_delay", "tau_RC", "s",
    "First-order RC time constant for the gate output node.",
    scope="physical",
    sp_units=SECOND,
)
t_prop = var(
    "physical.gate.prop_delay", "t_p", "s",
    "Propagation delay to the 50 percent level.",
    scope="physical",
    sp_units=SECOND,
)
t_elmore = var(
    "physical.gate.elmore_delay", "t_elmore", "s",
    "Elmore-delay estimate including distributed interconnect.",
    scope="physical",
    sp_units=SECOND,
)
V_dd = var(
    "physical.supply_voltage", "V_DD", "V",
    "Supply voltage for the logic domain.",
    scope="physical",
    sp_units=VOLT,
)

P_dyn = var(
    "physical.power.dynamic", "P_dyn", "W",
    "Dynamic switching power of a gate output.",
    scope="physical",
    sp_units=WATT,
)
P_stat = var(
    "physical.power.static", "P_stat", "W",
    "Static leakage power of a gate.",
    scope="physical",
    sp_units=WATT,
)
P_sc = var(
    "physical.power.short_circuit", "P_sc", "W",
    "Short-circuit power while pull-up and pull-down briefly conduct together.",
    scope="physical",
    sp_units=WATT,
)
P_total_gate = var(
    "physical.power.total_gate", "P_gate", "W",
    "Total per-gate power: dynamic plus leakage plus short-circuit.",
    scope="physical",
    sp_units=WATT,
)
P_landauer_min = var(
    "physical.power.landauer_min", "P_landauer", "W",
    "Thermodynamic lower bound on dissipated power for irreversible bit erasure.",
    scope="physical",
    sp_units=WATT,
)
alpha_act = var(
    "physical.gate.activity", "alpha_sw", "dimensionless",
    "Average fraction of cycles in which the node switches.",
    scope="physical",
    sp_units=1,
)
f_clock = var(
    "physical.clock_frequency", "f_clk", "Hz",
    "Clock frequency.",
    scope="physical",
    sp_units=HZ,
)
f_max_timing = var(
    "physical.clock.max_timing_frequency", "f_clk_timing_max", "Hz",
    "Maximum synchronous clock frequency implied by the modeled critical-path delay.",
    scope="physical",
    sp_units=HZ,
    references=[_CLOCK_TIMING_REF],
)
clock_derate = var(
    "physical.clock.derate", "eta_clk_derate", "dimensionless",
    "Operating-clock derate relative to the timing-limited maximum, covering guardband, skew, jitter, and design margin.",
    scope="physical",
    value_range=(0.0, 1.0),
    sp_units=1,
    references=[_CLOCK_TIMING_REF],
)
T_clk = var(
    "physical.clock_period", "T_clk", "s",
    "Clock period.",
    scope="physical",
    sp_units=SECOND,
)
I_sc_peak = var(
    "physical.gate.i_short_circuit_peak", "I_sc_pk", "A",
    "Peak short-circuit current during an input transition.",
    scope="physical",
    sp_units=AMPERE,
)
t_sc = var(
    "physical.gate.short_circuit_window", "t_sc", "s",
    "Time window during which both transistor networks conduct simultaneously.",
    scope="physical",
    sp_units=SECOND,
)
E_landauer = var(
    "physical.gate.landauer_energy", "E_landauer", "J",
    "Landauer minimum energy k_B T ln 2 per erased bit.",
    scope="physical",
    sp_units=JOULE,
)
bits_erased_per_cycle = var(
    "physical.gate.bits_erased_per_cycle", "N_erase", "dimensionless",
    "Logical bit erasures attributed to the gate per cycle in the abstraction.",
    scope="physical",
    sp_units=1,
)


eq_gate_input_cap = eq(
    "physical.eq.gate_input_capacitance",
    C_gate_input.symbol,
    C_ox.symbol * W_channel.symbol * L_channel.symbol,
    "Input capacitance from oxide capacitance density times gate area.",
    check_units=True,
)

eq_wire_load_cap = eq(
    "physical.eq.gate_wire_load",
    C_wire_load.symbol,
    C_wire_total.symbol,
    "Output wire load is the line capacitance seen by the gate.",
    check_units=True,
)

eq_total_load_cap = eq(
    "physical.eq.gate_total_load",
    C_load.symbol,
    fanout.symbol * C_gate_input.symbol + C_wire_load.symbol,
    "Total load capacitance is fanout input capacitance plus wire capacitance.",
    check_units=True,
)

eq_rc_constant = eq(
    "physical.eq.rc_constant",
    tau_rc.symbol,
    R_on.symbol * C_load.symbol,
    "First-order RC time constant of the gate output node.",
    check_units=True,
)

eq_prop_delay = eq(
    "physical.eq.prop_delay",
    t_prop.symbol,
    LN_2 * tau_rc.symbol,
    "Propagation delay to the 50 percent point for a first-order RC response.",
    check_units=True,
)

eq_elmore_delay = eq(
    "physical.eq.elmore_delay",
    t_elmore.symbol,
    R_on.symbol * (fanout.symbol * C_gate_input.symbol + C_wire_total.symbol)
    + R_per_length.symbol * C_per_length.symbol * L_wire.symbol**2 / 2,
    "Elmore delay including the distributed interconnect term.",
    check_units=True,
)

eq_dynamic_power = eq(
    "physical.eq.dynamic_power",
    P_dyn.symbol,
    alpha_act.symbol * C_load.symbol * V_dd.symbol**2 * f_clock.symbol,
    "CMOS dynamic power P = alpha C V^2 f.",
    check_units=True,
)

eq_static_power = eq(
    "physical.eq.static_power",
    P_stat.symbol,
    I_leak_total.symbol * V_dd.symbol,
    "Static power from total leakage current at the supply voltage.",
    check_units=True,
)

eq_short_circuit_power = eq(
    "physical.eq.short_circuit_power",
    P_sc.symbol,
    alpha_act.symbol * I_sc_peak.symbol * V_dd.symbol * t_sc.symbol * f_clock.symbol,
    "Short-circuit power from overlap current during switching.",
    check_units=True,
)

eq_gate_total_power = eq(
    "physical.eq.gate_total_power",
    P_total_gate.symbol,
    P_dyn.symbol + P_stat.symbol + P_sc.symbol,
    "Total gate power adds dynamic, leakage, and short-circuit components.",
    check_units=True,
)

eq_clock_period = eq(
    "physical.eq.clock_period",
    T_clk.symbol,
    1 / f_clock.symbol,
    "Clock period is the reciprocal of clock frequency.",
    check_units=True,
)
eq_f_max_timing = eq(
    "physical.eq.clock_max_timing_frequency",
    f_max_timing.symbol,
    1 / t_elmore.symbol,
    "The timing-limited maximum clock is the inverse of the modeled critical-path delay.",
    references=[_CLOCK_TIMING_REF],
    check_units=True,
)
eq_clock_frequency_timing_model = Approximation(
    "physical.eq.clock_frequency_timing_model",
    f_clock.symbol,
    clock_derate.symbol * f_max_timing.symbol,
    sp.And(
        t_elmore.symbol > 0,
        clock_derate.symbol >= 0,
        clock_derate.symbol <= 1,
    ),
    "Operating clock approximated as a derated timing-limit frequency.",
    references=[_CLOCK_TIMING_REF],
    check_units=True,
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
    check_units=True,
)

eq_landauer_power = eq(
    "physical.eq.landauer_power",
    P_landauer_min.symbol,
    alpha_act.symbol * bits_erased_per_cycle.symbol * E_landauer.symbol * f_clock.symbol,
    "Thermodynamic lower bound on dissipated power for the modeled logical erasures.",
    check_units=True,
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
    alpha_act, f_clock, f_max_timing, clock_derate, T_clk, I_sc_peak, t_sc, E_landauer,
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
    eq_f_max_timing,
    eq_clock_frequency_timing_model,
    ineq_clock_timing,
    eq_landauer_energy,
    eq_landauer_power,
    ineq_landauer_floor,
]


__all__ = [
    "C_gate_input", "fanout", "C_wire_load", "C_load", "R_on", "tau_rc",
    "t_prop", "t_elmore", "V_dd", "P_dyn", "P_stat", "P_sc",
    "P_total_gate", "P_landauer_min", "alpha_act", "f_clock",
    "f_max_timing", "clock_derate", "T_clk",
    "I_sc_peak", "t_sc", "E_landauer", "bits_erased_per_cycle",
    "eq_gate_input_cap", "eq_wire_load_cap", "eq_total_load_cap",
    "eq_rc_constant", "eq_prop_delay", "eq_elmore_delay",
    "eq_dynamic_power", "eq_static_power", "eq_short_circuit_power",
    "eq_gate_total_power", "eq_clock_period", "eq_f_max_timing",
    "eq_clock_frequency_timing_model", "ineq_clock_timing",
    "eq_landauer_energy", "eq_landauer_power", "ineq_landauer_floor",
    "CMOS_LOGIC_VARIABLES", "CMOS_LOGIC_EQUATIONS",
]
