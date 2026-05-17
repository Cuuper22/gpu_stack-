"""
scopes/physical_lithography_plasma_focus.py
===========================================

Focused-beam geometry for the lithography source-plasma drive.
"""

from .physical_lithography_plasma_focus_variables import *
from .physical_lithography_plasma_focus_variables import (
    LITHOGRAPHY_SOURCE_PLASMA_FOCUS_VARIABLES,
    LITHOGRAPHY_SOURCE_PLASMA_FOCUS_VARIABLE_EXPORTS as _VARIABLE_EXPORTS,
)
from .physical_lithography_plasma_focus_beam import *
from .physical_lithography_plasma_focus_beam import (
    LITHOGRAPHY_SOURCE_PLASMA_FOCUS_BEAM_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_FOCUS_BEAM_EXPORTS as _BEAM_EXPORTS,
)
from .physical_lithography_plasma_focus_spot import *
from .physical_lithography_plasma_focus_spot import (
    LITHOGRAPHY_SOURCE_PLASMA_FOCUS_SPOT_EQUATIONS,
    LITHOGRAPHY_SOURCE_PLASMA_FOCUS_SPOT_EXPORTS as _SPOT_EXPORTS,
)


LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EQUATIONS = [
    *LITHOGRAPHY_SOURCE_PLASMA_FOCUS_BEAM_EQUATIONS,
    *LITHOGRAPHY_SOURCE_PLASMA_FOCUS_SPOT_EQUATIONS,
]

LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EXPORTS = [
    *_VARIABLE_EXPORTS,
    *_BEAM_EXPORTS,
    *_SPOT_EXPORTS,
    "LITHOGRAPHY_SOURCE_PLASMA_FOCUS_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EQUATIONS",
    "LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EXPORTS",
]

__all__ = LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EXPORTS
