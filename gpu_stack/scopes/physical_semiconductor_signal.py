"""
scopes/physical_semiconductor_signal.py
=======================================

Speed-of-signal floor declarations for physical paths.
"""

import sympy as sp

from ..constants import SPEED_OF_LIGHT
from ..core import eq, var
from ..core.units import METER, SECOND


d_link = var(
    "physical.link.length", "d_link", "m",
    "Physical length of a signal path.",
    scope="physical",
    sp_units=METER,
)
n_medium = var(
    "physical.link.effective_refractive_index", "n_eff_link", "dimensionless",
    "Effective refractive index of the propagation medium.",
    scope="physical",
    sp_units=sp.Integer(1),
)
v_signal = var(
    "physical.link.signal_speed", "v_sig", "m/s",
    "Propagation speed of a signal in its medium.",
    scope="physical",
    sp_units=METER / SECOND,
)
t_flight = var(
    "physical.link.time_of_flight", "t_tof", "s",
    "Minimum time of flight for a signal over a physical path.",
    scope="physical",
    sp_units=SECOND,
)


eq_signal_speed = eq(
    "physical.eq.signal_speed",
    v_signal.symbol,
    SPEED_OF_LIGHT.symbol / n_medium.symbol,
    "Signal speed is c divided by the medium's effective refractive index.",
    check_units=True,
)

eq_time_of_flight = eq(
    "physical.eq.time_of_flight",
    t_flight.symbol,
    d_link.symbol / v_signal.symbol,
    "Time of flight from path length and propagation speed.",
    check_units=True,
)


SEMICONDUCTOR_SIGNAL_VARIABLES = [
    d_link, n_medium, v_signal, t_flight,
]

SEMICONDUCTOR_SIGNAL_EQUATIONS = [
    eq_signal_speed,
    eq_time_of_flight,
]

SEMICONDUCTOR_SIGNAL_EXPORTS = [
    "d_link", "n_medium", "v_signal", "t_flight",
    "eq_signal_speed", "eq_time_of_flight",
]


__all__ = [
    *SEMICONDUCTOR_SIGNAL_EXPORTS,
    "SEMICONDUCTOR_SIGNAL_VARIABLES",
    "SEMICONDUCTOR_SIGNAL_EQUATIONS",
]
