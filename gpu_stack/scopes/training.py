"""
scopes/training.py
==================

Aggregator for the training scope.

The original training file carried step FLOPs, executed chip FLOPs,
communication, HBM traffic, bubbles, availability, and scaling-law
variables in one slab. It has been split into focused helpers and
re-exported here so public imports stay stable.
"""

from ..core import System

from .training_compute import *
from .training_compute import (
    TRAINING_COMPUTE_EQUATIONS,
    TRAINING_COMPUTE_VARIABLES,
)
from .training_comm import *
from .training_comm import TRAINING_COMM_EQUATIONS, TRAINING_COMM_VARIABLES
from .training_memory import *
from .training_memory import (
    TRAINING_MEMORY_EQUATIONS,
    TRAINING_MEMORY_VARIABLES,
)
from .training_overheads import *
from .training_overheads import (
    TRAINING_OVERHEADS_EQUATIONS,
    TRAINING_OVERHEADS_VARIABLES,
)
from .training_scaling import *
from .training_scaling import (
    TRAINING_SCALING_EQUATIONS,
    TRAINING_SCALING_VARIABLES,
)


sys_training = System(
    name="training",
    scope="training",
    description="Training-step decomposition, MFU or HFU, throughput, wall clock, and energy metrics.",
)


TRAINING_VARIABLES = (
    TRAINING_COMPUTE_VARIABLES
    + TRAINING_COMM_VARIABLES
    + TRAINING_MEMORY_VARIABLES
    + TRAINING_OVERHEADS_VARIABLES
    + TRAINING_SCALING_VARIABLES
)

TRAINING_EQUATIONS = (
    TRAINING_COMPUTE_EQUATIONS
    + TRAINING_COMM_EQUATIONS
    + TRAINING_MEMORY_EQUATIONS
    + TRAINING_OVERHEADS_EQUATIONS
    + TRAINING_SCALING_EQUATIONS
)

for v in TRAINING_VARIABLES:
    sys_training.add(v)

for e in TRAINING_EQUATIONS:
    sys_training.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
