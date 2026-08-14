"""
scopes/optimizer.py
===================

Aggregator for the optimizer scope: the update rule and what it costs.

An optimizer turns gradients into parameter updates, and this scope models
both faces of that: the mathematics of each rule and the memory its state
occupies. The first-order helper covers AdamW, the SGD family, LAMB, Lion,
and EMA deployment weights; the second-order helper covers Muon's
Newton-Schulz orthogonalization, MuonClip, and Shampoo's preconditioners;
schedules and dynamic loss scaling round out the training-loop machinery.

The state question matters to hardware: AdamW keeps two extra tensors per
parameter, so optimizer memory can dwarf the weights themselves, and the
sharding helper counts what survives after distributing that state. The
parallelism scope consumes those byte counts when budgeting per-GPU
memory. This file re-exports the five helpers so public imports stay
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
