"""
scopes/physical.py
==================

Aggregator for the physical scope: the device-physics floor of the stack.
This scope answers how fast a transistor can switch, what each switch costs
in energy, how quickly a signal crosses an on-chip wire, and how much noise
rides underneath everything. The declarations live in focused helper
modules -- semiconductor transport, MOSFET regimes, CMOS logic timing and
power, interconnect, and noise -- and are re-exported here so public
imports stay stable. Higher scopes (process, gpu, thermal) consume the
clock, capacitance, and power abstractions assembled here.
"""

from ..core import System

from .physical_lithography import *
from .physical_lithography import LITHOGRAPHY_EQUATIONS, LITHOGRAPHY_VARIABLES
from .physical_process import *
from .physical_process import PROCESS_EQUATIONS, PROCESS_VARIABLES
from .physical_local_thermal import *
from .physical_local_thermal import LOCAL_THERMAL_EQUATIONS, LOCAL_THERMAL_VARIABLES
from .physical_semiconductor import *
from .physical_semiconductor import SEMICONDUCTOR_VARIABLES, SEMICONDUCTOR_EQUATIONS
from .physical_mosfet import *
from .physical_mosfet import MOSFET_VARIABLES, MOSFET_EQUATIONS
from .physical_interconnect import *
from .physical_interconnect import INTERCONNECT_VARIABLES, INTERCONNECT_EQUATIONS
from .physical_cmos_logic import *
from .physical_cmos_logic import CMOS_LOGIC_VARIABLES, CMOS_LOGIC_EQUATIONS
from .physical_noise import *
from .physical_noise import NOISE_VARIABLES, NOISE_EQUATIONS


sys_physical = System(
    name="physical",
    scope="physical",
    description="Lithography quantum source/optics, process geometry, local self-heating, transport, transistor behavior, interconnect delay, CMOS logic, and noise.",
)


PHYSICAL_VARIABLES = (
    LITHOGRAPHY_VARIABLES
    + PROCESS_VARIABLES
    + LOCAL_THERMAL_VARIABLES
    + SEMICONDUCTOR_VARIABLES
    + MOSFET_VARIABLES
    + INTERCONNECT_VARIABLES
    + CMOS_LOGIC_VARIABLES
    + NOISE_VARIABLES
)

PHYSICAL_EQUATIONS = (
    LITHOGRAPHY_EQUATIONS
    + PROCESS_EQUATIONS
    + LOCAL_THERMAL_EQUATIONS
    + SEMICONDUCTOR_EQUATIONS
    + MOSFET_EQUATIONS
    + INTERCONNECT_EQUATIONS
    + CMOS_LOGIC_EQUATIONS
    + NOISE_EQUATIONS
)

for v in PHYSICAL_VARIABLES:
    sys_physical.add(v)

for e in PHYSICAL_EQUATIONS:
    sys_physical.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
