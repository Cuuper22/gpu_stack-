"""
scopes/economics.py
===================

Aggregator for the economics scope.

The original economics file carried GPU amortization, site capex, tariffs,
opex rates, run-level rollups, NPV discounting, and inference-token recovery
in one slab. That grew past 800 lines and made every change a cross-topic
review. Economics is now split into focused helpers and re-exported here so
public imports stay stable.

The helpers in dependency order:

* capex  - node, rack, cluster, and facility capex, site rollups, job share.
* opex   - tariffs, demand charges, water, maintenance, staff, transit,
           carbon, allocated power cost, and run-level power cost.
* finance- utilization, allocation, WACC, run discount factor.
* recovery - run cost rollups, cost per step or token or FLOP, NPV, and the
             inference-token recovery target.
"""

from ..core import System

from .economics_capex import *
from .economics_capex import ECON_CAPEX_EQUATIONS, ECON_CAPEX_VARIABLES
from .economics_opex import *
from .economics_opex import ECON_OPEX_EQUATIONS, ECON_OPEX_VARIABLES
from .economics_finance import *
from .economics_finance import ECON_FINANCE_EQUATIONS, ECON_FINANCE_VARIABLES
from .economics_recovery import *
from .economics_recovery import ECON_RECOVERY_EQUATIONS, ECON_RECOVERY_VARIABLES


sys_econ = System(
    name="economics",
    scope="economics",
    description="Capex, opex, training-run cost, and cost-recovery targets.",
)


ECONOMICS_VARIABLES = (
    ECON_CAPEX_VARIABLES
    + ECON_OPEX_VARIABLES
    + ECON_FINANCE_VARIABLES
    + ECON_RECOVERY_VARIABLES
)

ECONOMICS_EQUATIONS = (
    ECON_CAPEX_EQUATIONS
    + ECON_OPEX_EQUATIONS
    + ECON_FINANCE_EQUATIONS
    + ECON_RECOVERY_EQUATIONS
)

for v in ECONOMICS_VARIABLES:
    sys_econ.add(v)

for e in ECONOMICS_EQUATIONS:
    sys_econ.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
