"""
scopes/physical_lithography_medium_binding_energy_terms.py
==========================================================

Facade for the per-component liquid-drop binding-energy terms of the
imaging medium. The term variables and the equations that evaluate them
live in focused sibling modules; this module preserves the historical
direct attributes, public imports, and aggregate ordering.
"""

import sympy as sp

from ..core import Approximation, var
from ..core.units import JOULE
from .physical_lithography_medium_binding_coefficients import (
    lithography_medium_component_binding_asymmetry_coefficient,
    lithography_medium_component_binding_coulomb_coefficient,
    lithography_medium_component_binding_surface_coefficient,
    lithography_medium_component_binding_volume_coefficient,
)
from .physical_lithography_medium_binding_nuclear_state import (
    lithography_medium_component_a_binding_pairing_coefficient,
    lithography_medium_component_a_neutron_excess,
    lithography_medium_component_a_pairing_sign,
    lithography_medium_component_b_binding_pairing_coefficient,
    lithography_medium_component_b_neutron_excess,
    lithography_medium_component_b_pairing_sign,
)
from .physical_lithography_medium_components import (
    LITHOGRAPHY_MEDIUM_COMPOSITION_REF,
    lithography_medium_component_a_isotope_mass_number,
    lithography_medium_component_a_proton_count,
    lithography_medium_component_b_isotope_mass_number,
    lithography_medium_component_b_proton_count,
)
from .physical_lithography_medium_binding_energy_terms_variables import *
from .physical_lithography_medium_binding_energy_terms_variables import (
    LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_VARIABLES,
    LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_VARIABLE_EXPORTS as _VARIABLE_EXPORTS,
)
from .physical_lithography_medium_binding_energy_terms_equations import *
from .physical_lithography_medium_binding_energy_terms_equations import (
    LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_EQUATIONS,
    LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_EQUATION_EXPORTS as _EQUATION_EXPORTS,
)


LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_EXPORTS = [
    *_VARIABLE_EXPORTS,
    *_EQUATION_EXPORTS,
]

__all__ = [*LITHOGRAPHY_MEDIUM_BINDING_ENERGY_TERM_EXPORTS]

del _VARIABLE_EXPORTS, _EQUATION_EXPORTS
