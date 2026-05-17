"""
scopes/physical_interconnect.py
===============================

Compatibility surface for on-chip interconnect geometry and distributed-line
effects.

The declarations live in focused helper modules, but this module keeps the
original import surface stable for downstream physical scope consumers.
"""

import sympy as sp

from ..constants import EPSILON_0, MU_0, TWO_PI
from ..core import Approximation, Inequality, PiecewiseEquation, Reference, eq, var
from ..core.units import FARAD, HENRY, HZ, METER, OHM, SECOND, VOLT
from .physical_semiconductor import (
    A_wire,
    L_wire,
    R_res,
    minimum_metal_pitch,
    process_node_length,
    rho_res,
)
from .physical_interconnect_refs import _INTERCONNECT_GEOMETRY_REF, _INTERCONNECT_TEXT
from .physical_interconnect_variables import *
from .physical_interconnect_variables import (
    INTERCONNECT_VARIABLE_EXPORTS as _INTERCONNECT_VARIABLE_EXPORTS,
    INTERCONNECT_VARIABLES,
)
from .physical_interconnect_equations import *
from .physical_interconnect_equations import (
    INTERCONNECT_EQUATION_EXPORTS as _INTERCONNECT_EQUATION_EXPORTS,
    INTERCONNECT_EQUATIONS,
)


__all__ = [
    *_INTERCONNECT_VARIABLE_EXPORTS,
    *_INTERCONNECT_EQUATION_EXPORTS,
    "INTERCONNECT_VARIABLES", "INTERCONNECT_EQUATIONS",
]
