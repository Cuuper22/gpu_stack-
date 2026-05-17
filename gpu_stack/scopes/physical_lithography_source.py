"""
scopes/physical_lithography_source.py
=====================================

Compatibility surface for lithography exposure-source photon generation.

The source variables, nuclear/reduced-mass relations, and transition-energy
relations live in focused sibling modules. This module preserves the historical
public imports and registry-list ordering used by downstream lithography scopes.
"""

from .physical_lithography_binding_coefficients import *
from .physical_lithography_binding_coefficients import (
    LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_EQUATIONS,
    LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_VARIABLES,
    __all__ as LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_EXPORTS,
)
from .physical_lithography_electronic_structure import *
from .physical_lithography_electronic_structure import (
    LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_EQUATIONS,
    LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_VARIABLES,
    __all__ as LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_EXPORTS,
)
from .physical_lithography_species import *
from .physical_lithography_species import (
    LITHOGRAPHY_SOURCE_SPECIES_EQUATIONS,
    LITHOGRAPHY_SOURCE_SPECIES_VARIABLES,
    __all__ as LITHOGRAPHY_SOURCE_SPECIES_EXPORTS,
)
from .physical_lithography_source_variables import *
from .physical_lithography_source_variables import (
    _LITHOGRAPHY_SOURCE_PRE_ELECTRONIC_VARIABLES,
    _LITHOGRAPHY_SOURCE_TRANSITION_VARIABLES,
    _LITHOGRAPHY_SOURCE_VARIABLE_EXPORTS,
)
from .physical_lithography_source_nuclear_equations import *
from .physical_lithography_source_nuclear_equations import (
    _LITHOGRAPHY_SOURCE_NUCLEAR_EQUATION_EXPORTS,
    _LITHOGRAPHY_SOURCE_NUCLEAR_EQUATIONS,
)
from .physical_lithography_source_transition_equations import *
from .physical_lithography_source_transition_equations import (
    _LITHOGRAPHY_SOURCE_TRANSITION_EQUATION_EXPORTS,
    _LITHOGRAPHY_SOURCE_TRANSITION_EQUATIONS,
)


LITHOGRAPHY_SOURCE_VARIABLES = [
    *LITHOGRAPHY_SOURCE_SPECIES_VARIABLES,
    *LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_VARIABLES,
    *_LITHOGRAPHY_SOURCE_PRE_ELECTRONIC_VARIABLES,
    *LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_VARIABLES,
    *_LITHOGRAPHY_SOURCE_TRANSITION_VARIABLES,
]

LITHOGRAPHY_SOURCE_EQUATIONS = [
    *LITHOGRAPHY_SOURCE_SPECIES_EQUATIONS,
    *LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_EQUATIONS,
    *_LITHOGRAPHY_SOURCE_NUCLEAR_EQUATIONS,
    *LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_EQUATIONS,
    *_LITHOGRAPHY_SOURCE_TRANSITION_EQUATIONS,
]


__all__ = [
    *LITHOGRAPHY_SOURCE_SPECIES_EXPORTS,
    *LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_EXPORTS,
    *LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_EXPORTS,
    *_LITHOGRAPHY_SOURCE_VARIABLE_EXPORTS,
    *_LITHOGRAPHY_SOURCE_NUCLEAR_EQUATION_EXPORTS,
    *_LITHOGRAPHY_SOURCE_TRANSITION_EQUATION_EXPORTS,
    "LITHOGRAPHY_SOURCE_VARIABLES",
    "LITHOGRAPHY_SOURCE_EQUATIONS",
]
