"""
scopes/thermal.py
=================

Heat transfer, cooling, and facility overhead from one package up to the
whole data center. Every watt the ICs dissipate must cross the package into
coolant, leave through the facility plant, and drag some overhead power
with it -- that overhead ratio is the PUE. The old file had the right
nouns but one bad graph edge: it defined PUE from DC total power and DC
total power from PUE, the same relation written twice, hence a cycle. This
version keeps PUE as the definition (total over IT power) and builds total
facility power from explicit cooling and non-IT overhead terms. The scope
covers package-to-coolant thermal resistances, coolant flow with pump and
fan power, free cooling versus chiller operation, heat reuse, water use
and WUE, ASHRAE-style inlet and humidity constraints, and facility total
power and PUE without circularity.
"""

from ..core import System

from .thermal_package import *
from .thermal_package import THERMAL_PACKAGE_EQUATIONS, THERMAL_PACKAGE_VARIABLES
from .thermal_liquid import *
from .thermal_liquid import THERMAL_LIQUID_EQUATIONS, THERMAL_LIQUID_VARIABLES
from .thermal_facility import *
from .thermal_facility import THERMAL_FACILITY_EQUATIONS, THERMAL_FACILITY_VARIABLES
from .thermal_env import *
from .thermal_env import THERMAL_ENV_EQUATIONS, THERMAL_ENV_VARIABLES


sys_thermal = System(
    name="thermal",
    scope="thermal",
    description="Package-to-facility thermal path, cooling overhead, and PUE.",
)


THERMAL_VARIABLES = (
    THERMAL_PACKAGE_VARIABLES
    + THERMAL_LIQUID_VARIABLES
    + THERMAL_FACILITY_VARIABLES
    + THERMAL_ENV_VARIABLES
)

THERMAL_EQUATIONS = (
    THERMAL_PACKAGE_EQUATIONS
    + THERMAL_LIQUID_EQUATIONS
    + THERMAL_FACILITY_EQUATIONS
    + THERMAL_ENV_EQUATIONS
)

for v in THERMAL_VARIABLES:
    sys_thermal.add(v)

for e in THERMAL_EQUATIONS:
    sys_thermal.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
