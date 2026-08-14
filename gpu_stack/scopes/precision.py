"""
scopes/precision.py
===================

Aggregator for the precision scope: what numbers a format can represent
and what errors it makes. The original file carried IEEE-754 structure,
quantization and rounding statistics, microscaling and block floating
point, low-bit storage formats, loss scaling, and the Random Hadamard
Transform in one slab; it is now split into focused helpers and
re-exported here so public imports stay stable. The training scope consumes
these formats through bytes-per-value and error terms.
"""

from ..core import System

from .precision_ieee import *
from .precision_ieee import (
    PRECISION_IEEE_EQUATIONS,
    PRECISION_IEEE_VARIABLES,
)
from .precision_rounding import *
from .precision_rounding import (
    PRECISION_ROUNDING_EQUATIONS,
    PRECISION_ROUNDING_VARIABLES,
)
from .precision_microscaling import *
from .precision_microscaling import (
    PRECISION_MICROSCALING_EQUATIONS,
    PRECISION_MICROSCALING_VARIABLES,
)
from .precision_lowbit import *
from .precision_lowbit import (
    PRECISION_LOWBIT_EQUATIONS,
    PRECISION_LOWBIT_VARIABLES,
)


sys_prec = System(
    name="precision",
    scope="precision",
    description="Floating-point, integer, microscaled, and quantized numeric formats.",
)


PRECISION_VARIABLES = (
    PRECISION_IEEE_VARIABLES
    + PRECISION_ROUNDING_VARIABLES
    + PRECISION_MICROSCALING_VARIABLES
    + PRECISION_LOWBIT_VARIABLES
)

PRECISION_EQUATIONS = (
    PRECISION_IEEE_EQUATIONS
    + PRECISION_ROUNDING_EQUATIONS
    + PRECISION_MICROSCALING_EQUATIONS
    + PRECISION_LOWBIT_EQUATIONS
)

for v in PRECISION_VARIABLES:
    sys_prec.add(v)

for e in PRECISION_EQUATIONS:
    sys_prec.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
