"""
scopes/economics.py
===================

Aggregator for the economics scope: what a training run actually costs.

Every scope below this one measures seconds, bytes, and watts; economics
converts them to dollars. Two kinds of money flow in. Capex is what you pay
once — GPUs, servers, switches, the building — and then depreciate over a
useful life. Opex is what you pay continuously — electricity under real
tariffs, water, maintenance, staff, network transit, carbon. Allocate both
to one job by its share of the cluster and its wall-clock time, and you get
the run cost, which divides into cost per step, per token, and per FLOP.

The helpers, in dependency order: capex (node, rack, cluster, and facility
capital plus job share), opex (tariffs, demand charges, and the other
operating rates), finance (utilization, allocation, WACC, run discount
factor), and recovery (the run-cost rollup, unit costs, NPV, and how many
inference tokens must be sold to earn the run back). This file re-exports
all of them so public imports stay stable.
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
