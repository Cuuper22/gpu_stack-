"""
scopes/physical_semiconductor_signal.py
=======================================

The speed-of-signal floor. An electrical signal propagates as an
electromagnetic wave at c divided by the effective refractive index of the
surrounding dielectric, not at the drift speed of electrons -- so a link of
given length has a hard minimum time of flight regardless of how good the
drivers are. These two relations put that floor into the graph for any
physical path.
"""

import sympy as sp

from ..constants import SPEED_OF_LIGHT
from ..core import Reference, eq, var
from ..core.units import METER, SECOND


_SIGNAL_PROP_REF = Reference(
    citation="Griffiths, Introduction to Electrodynamics, wave propagation in linear media and signal speed v = c/n.",
    kind="textbook",
)


d_link = var(
    "physical.link.length", "d_link", "m",
    "Physical length of a signal path.",
    scope="physical",
    sp_units=METER,
    references=[_SIGNAL_PROP_REF],
)
n_medium = var(
    "physical.link.effective_refractive_index", "n_eff_link", "dimensionless",
    "Effective refractive index of the propagation medium.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[_SIGNAL_PROP_REF],
)
v_signal = var(
    "physical.link.signal_speed", "v_sig", "m/s",
    "Propagation speed of a signal in its medium.",
    scope="physical",
    sp_units=METER / SECOND,
    references=[_SIGNAL_PROP_REF],
)
t_flight = var(
    "physical.link.time_of_flight", "t_tof", "s",
    "Minimum time of flight for a signal over a physical path.",
    scope="physical",
    sp_units=SECOND,
    references=[_SIGNAL_PROP_REF],
)


eq_signal_speed = eq(
    "physical.eq.signal_speed",
    v_signal.symbol,
    SPEED_OF_LIGHT.symbol / n_medium.symbol,
    "Signal speed is c divided by the medium's effective refractive index.",
    references=[_SIGNAL_PROP_REF],
    check_units=True,
)

eq_time_of_flight = eq(
    "physical.eq.time_of_flight",
    t_flight.symbol,
    d_link.symbol / v_signal.symbol,
    "Time of flight from path length and propagation speed.",
    references=[_SIGNAL_PROP_REF],
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
