"""
scopes/physical_lithography_medium_binding.py
=============================================

Liquid-drop nuclear binding terms for lithography imaging-medium components.

The coefficient calibration, component nuclear-state descriptors, and
component binding-energy terms live in focused sibling modules; this module
preserves the historical public import surface and registry ordering.
"""

from .physical_lithography_medium_binding_coefficients import *
from .physical_lithography_medium_binding_coefficients import (
    LITHOGRAPHY_MEDIUM_BINDING_COEFFICIENT_EQUATIONS,
    LITHOGRAPHY_MEDIUM_BINDING_COEFFICIENT_EXPORTS,
    LITHOGRAPHY_MEDIUM_BINDING_COEFFICIENT_VARIABLES,
)
from .physical_lithography_medium_binding_nuclear_state import *
from .physical_lithography_medium_binding_nuclear_state import (
    LITHOGRAPHY_MEDIUM_BINDING_NUCLEAR_STATE_EQUATIONS as _NUCLEAR_STATE_EQUATIONS,
    LITHOGRAPHY_MEDIUM_BINDING_NUCLEAR_STATE_EXPORTS as _NUCLEAR_STATE_EXPORTS,
    LITHOGRAPHY_MEDIUM_BINDING_NUCLEAR_STATE_VARIABLES as _NUCLEAR_STATE_VARIABLES,
)
from .physical_lithography_medium_binding_energy_terms import *
from .physical_lithography_medium_binding_energy_terms import (
    LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_EQUATIONS as _ENERGY_TERM_EQUATIONS,
    LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_EXPORTS as _ENERGY_TERM_EXPORTS,
    LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_VARIABLES as _ENERGY_TERM_VARIABLES,
)


LITHOGRAPHY_MEDIUM_BINDING_VARIABLES = [
    *LITHOGRAPHY_MEDIUM_BINDING_COEFFICIENT_VARIABLES,
    *_NUCLEAR_STATE_VARIABLES,
    *_ENERGY_TERM_VARIABLES,
]

LITHOGRAPHY_MEDIUM_BINDING_EQUATIONS = [
    *LITHOGRAPHY_MEDIUM_BINDING_COEFFICIENT_EQUATIONS,
    *_NUCLEAR_STATE_EQUATIONS,
    *_ENERGY_TERM_EQUATIONS,
]


__all__ = [
    *LITHOGRAPHY_MEDIUM_BINDING_COEFFICIENT_EXPORTS,
    *_NUCLEAR_STATE_EXPORTS[:8],
    *_ENERGY_TERM_EXPORTS[:12],
    *_NUCLEAR_STATE_EXPORTS[8:],
    *_ENERGY_TERM_EXPORTS[12:],
    "LITHOGRAPHY_MEDIUM_BINDING_VARIABLES",
    "LITHOGRAPHY_MEDIUM_BINDING_EQUATIONS",
]
