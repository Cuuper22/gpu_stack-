"""
scopes/optimizer.py
===================

Aggregator for the optimizer scope.

The original optimizer file carried shared gradient state, AdamW, Muon with
Newton-Schulz, gradient clipping, SGD-family updates, learning-rate
schedules, loss scaling, EMA, and optimizer-state memory in one slab. It has
been split into focused helpers and re-exported here so public imports stay
stable.
"""

from ..core import System

from .optimizer_first_order import *
from .optimizer_first_order import (
    OPT_FIRST_ORDER_EQUATIONS,
    OPT_FIRST_ORDER_VARIABLES,
)
from .optimizer_second_order import *
from .optimizer_second_order import (
    OPT_SECOND_ORDER_EQUATIONS,
    OPT_SECOND_ORDER_VARIABLES,
)
from .optimizer_sharding import *
from .optimizer_sharding import (
    OPT_SHARDING_EQUATIONS,
    OPT_SHARDING_VARIABLES,
)
from .optimizer_schedules import *
from .optimizer_schedules import (
    OPT_SCHEDULES_EQUATIONS,
    OPT_SCHEDULES_VARIABLES,
)
from .optimizer_loss_scaling import *
from .optimizer_loss_scaling import (
    OPT_LOSS_SCALING_EQUATIONS,
    OPT_LOSS_SCALING_VARIABLES,
)


sys_opt = System(
    name="optimizer",
    scope="optimizer",
    description="AdamW, Muon, SGD-family optimizers, schedules, EMA, and optimizer-state memory.",
)


OPTIMIZER_VARIABLES = (
    OPT_FIRST_ORDER_VARIABLES
    + OPT_SECOND_ORDER_VARIABLES
    + OPT_SHARDING_VARIABLES
    + OPT_SCHEDULES_VARIABLES
    + OPT_LOSS_SCALING_VARIABLES
)

OPTIMIZER_EQUATIONS = (
    OPT_FIRST_ORDER_EQUATIONS
    + OPT_SECOND_ORDER_EQUATIONS
    + OPT_SHARDING_EQUATIONS
    + OPT_SCHEDULES_EQUATIONS
    + OPT_LOSS_SCALING_EQUATIONS
)

for v in OPTIMIZER_VARIABLES:
    sys_opt.add(v)

for e in OPTIMIZER_EQUATIONS:
    sys_opt.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
