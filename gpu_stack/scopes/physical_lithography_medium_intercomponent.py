"""
scopes/physical_lithography_medium_intercomponent.py
====================================================

Compatibility surface for lithography imaging-medium intercomponent closure.

The variable declarations, charge-transfer relations, geometry relations, and
screened Coulomb binding relation live in focused sibling modules. This module
preserves the historical public imports and registry ordering.
"""

import sympy as sp

from ..constants import ELEMENTARY_CHARGE, EPSILON_0
from ..core import Approximation, Inequality, eq, var
from ..core.units import JOULE, METER
from .physical_lithography_medium_binding import (
    lithography_medium_component_nuclear_radius_coefficient,
)
from .physical_lithography_medium_components import (
    LITHOGRAPHY_MEDIUM_COMPOSITION_REF,
    lithography_medium_component_a_isotope_mass_number,
    lithography_medium_component_a_proton_count,
    lithography_medium_component_a_stoichiometric_count,
    lithography_medium_component_b_isotope_mass_number,
    lithography_medium_component_b_proton_count,
    lithography_medium_component_b_stoichiometric_count,
)
from .physical_lithography_medium_intercomponent_variables import *
from .physical_lithography_medium_intercomponent_variables import (
    LITHOGRAPHY_MEDIUM_INTERCOMPONENT_VARIABLE_EXPORTS as _VARIABLE_EXPORTS,
    LITHOGRAPHY_MEDIUM_INTERCOMPONENT_VARIABLES,
)
from .physical_lithography_medium_intercomponent_charge import *
from .physical_lithography_medium_intercomponent_charge import (
    LITHOGRAPHY_MEDIUM_INTERCOMPONENT_CHARGE_EQUATIONS as _CHARGE_EQUATIONS,
    LITHOGRAPHY_MEDIUM_INTERCOMPONENT_CHARGE_EXPORTS as _CHARGE_EXPORTS,
)
from .physical_lithography_medium_intercomponent_geometry import *
from .physical_lithography_medium_intercomponent_geometry import (
    LITHOGRAPHY_MEDIUM_INTERCOMPONENT_GEOMETRY_EQUATIONS as _GEOMETRY_EQUATIONS,
    LITHOGRAPHY_MEDIUM_INTERCOMPONENT_GEOMETRY_EXPORTS as _GEOMETRY_EXPORTS,
)
from .physical_lithography_medium_intercomponent_binding import *
from .physical_lithography_medium_intercomponent_binding import (
    LITHOGRAPHY_MEDIUM_INTERCOMPONENT_BINDING_EQUATIONS as _BINDING_EQUATIONS,
    LITHOGRAPHY_MEDIUM_INTERCOMPONENT_BINDING_EXPORTS as _BINDING_EXPORTS,
)


LITHOGRAPHY_MEDIUM_INTERCOMPONENT_EQUATIONS = [
    *_CHARGE_EQUATIONS,
    *_GEOMETRY_EQUATIONS,
    *_BINDING_EQUATIONS,
]


__all__ = [
    *_VARIABLE_EXPORTS,
    *_CHARGE_EXPORTS,
    *_GEOMETRY_EXPORTS,
    *_BINDING_EXPORTS,
    "LITHOGRAPHY_MEDIUM_INTERCOMPONENT_VARIABLES",
    "LITHOGRAPHY_MEDIUM_INTERCOMPONENT_EQUATIONS",
]
