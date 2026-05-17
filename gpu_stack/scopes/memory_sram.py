"""
scopes/memory_sram.py
=====================

SRAM cell family: 6T, 8T, and 10T variants.

Exposes transistor counts, read-port counts, area estimates, access-time
decomposition, read and write energy, leakage power, read disturb, SNM,
write internal node, WNM, and the two SRAM margin constraint inequalities.
"""

import sympy as sp

from ..core import Inequality, Reference, eq, var
from ..core.units import AMPERE, FARAD, JOULE, METER, OHM, SECOND, VOLT, WATT
from .memory_sram_common import DIMENSIONLESS, SRAM_CELL_REF
from .memory_sram_operating import *
from .memory_sram_operating import (
    MEMCELL_SRAM_OPERATING_EXPORTS as _OPERATING_EXPORTS,
    MEMCELL_SRAM_OPERATING_VARIABLES as _OPERATING_VARIABLES,
)
from .memory_sram_variants import *
from .memory_sram_variants import (
    MEMCELL_SRAM_VARIANT_EXPORTS as _VARIANT_EXPORTS,
    MEMCELL_SRAM_VARIANT_VARIABLES as _VARIANT_VARIABLES,
)
from .memory_sram_margins import *
from .memory_sram_margins import (
    MEMCELL_SRAM_MARGIN_EXPORTS as _MARGIN_EXPORTS,
    MEMCELL_SRAM_MARGIN_VARIABLES as _MARGIN_VARIABLES,
)
from .memory_sram_variant_equations import *
from .memory_sram_variant_equations import (
    MEMCELL_SRAM_VARIANT_EQUATION_EXPORTS as _VARIANT_EQUATION_EXPORTS,
    MEMCELL_SRAM_VARIANT_EQUATIONS as _VARIANT_EQUATIONS,
)
from .memory_sram_operating_equations import *
from .memory_sram_operating_equations import (
    MEMCELL_SRAM_OPERATING_EQUATION_EXPORTS as _OPERATING_EQUATION_EXPORTS,
    MEMCELL_SRAM_OPERATING_EQUATIONS as _OPERATING_EQUATIONS,
)
from .memory_sram_margin_equations import *
from .memory_sram_margin_equations import (
    MEMCELL_SRAM_MARGIN_EQUATION_EXPORTS as _MARGIN_EQUATION_EXPORTS,
    MEMCELL_SRAM_MARGIN_EQUATIONS as _MARGIN_EQUATIONS,
)


MEMCELL_SRAM_VARIABLES = [
    *_OPERATING_VARIABLES,
    *_VARIANT_VARIABLES,
    *_MARGIN_VARIABLES,
]

MEMCELL_SRAM_EQUATIONS = [
    *_VARIANT_EQUATIONS,
    *_OPERATING_EQUATIONS,
    *_MARGIN_EQUATIONS,
]


__all__ = [
    *_OPERATING_EXPORTS,
    *_VARIANT_EXPORTS,
    *_MARGIN_EXPORTS,
    *_VARIANT_EQUATION_EXPORTS,
    *_OPERATING_EQUATION_EXPORTS,
    *_MARGIN_EQUATION_EXPORTS,
    "MEMCELL_SRAM_VARIABLES", "MEMCELL_SRAM_EQUATIONS",
]
