"""
scopes/thermal.py
=================

Heat transfer, cooling, and facility overhead from the package scale up to the
whole data center.

The old file had the right nouns but one bad graph edge: it defined PUE from
DC total power and then defined DC total power from PUE, which is the same
relation written twice and therefore a cycle. This version keeps the PUE
ratio as the definition and computes total facility power from explicit
cooling and non-IT overhead terms.

The scope now covers:

* detailed package-to-coolant thermal resistances,
* coolant flow, pump power, and fan power,
* free-cooling versus chiller operation,
* heat reuse, water use, and WUE,
* ASHRAE-style inlet and humidity constraints,
* facility total power and PUE without circularity.
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
