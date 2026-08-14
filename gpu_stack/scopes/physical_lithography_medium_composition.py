"""
scopes/physical_lithography_medium_composition.py
=================================================

Composition-side aggregator for the imaging medium. It stitches together
the chain that runs from isotopes to bulk matter: component isotope
descriptors, liquid-drop nuclear binding, intercomponent (chemical-scale)
binding, and the formula-unit mass closure. Each layer lives in a focused
sibling module; this module preserves the historical public import
surface.
"""

from .physical_lithography_medium_binding import *
from .physical_lithography_medium_binding import (
    LITHOGRAPHY_MEDIUM_BINDING_EQUATIONS,
    LITHOGRAPHY_MEDIUM_BINDING_VARIABLES,
    __all__ as LITHOGRAPHY_MEDIUM_BINDING_EXPORTS,
)
from .physical_lithography_medium_components import *
from .physical_lithography_medium_components import (
    LITHOGRAPHY_MEDIUM_COMPONENT_EQUATIONS,
    LITHOGRAPHY_MEDIUM_COMPONENT_VARIABLES,
    __all__ as LITHOGRAPHY_MEDIUM_COMPONENT_EXPORTS,
)
from .physical_lithography_medium_intercomponent import *
from .physical_lithography_medium_intercomponent import (
    LITHOGRAPHY_MEDIUM_INTERCOMPONENT_EQUATIONS,
    LITHOGRAPHY_MEDIUM_INTERCOMPONENT_VARIABLES,
)
from .physical_lithography_medium_formula_unit import *
from .physical_lithography_medium_formula_unit import (
    LITHOGRAPHY_MEDIUM_FORMULA_UNIT_EQUATIONS,
    LITHOGRAPHY_MEDIUM_FORMULA_UNIT_VARIABLES,
)


LITHOGRAPHY_MEDIUM_COMPOSITION_VARIABLES = [
    *LITHOGRAPHY_MEDIUM_COMPONENT_VARIABLES,
    *LITHOGRAPHY_MEDIUM_BINDING_VARIABLES,
    *LITHOGRAPHY_MEDIUM_INTERCOMPONENT_VARIABLES,
    *LITHOGRAPHY_MEDIUM_FORMULA_UNIT_VARIABLES,
]

LITHOGRAPHY_MEDIUM_COMPOSITION_EQUATIONS = [
    *LITHOGRAPHY_MEDIUM_COMPONENT_EQUATIONS,
    *LITHOGRAPHY_MEDIUM_BINDING_EQUATIONS,
    *LITHOGRAPHY_MEDIUM_INTERCOMPONENT_EQUATIONS,
    *LITHOGRAPHY_MEDIUM_FORMULA_UNIT_EQUATIONS,
]

_DENSITY_REEXPORTS = (
    "LITHOGRAPHY_MEDIUM_DENSITY_REF",
    "lithography_medium_formula_unit_packing_length_scale_factor",
    "lithography_medium_formula_unit_packing_length",
    "lithography_medium_formula_unit_packing_fill_factor",
    "lithography_medium_formula_unit_packing_volume",
    "lithography_medium_mass_density",
    "lithography_medium_molar_mass",
    "lithography_medium_particle_mass",
    "lithography_medium_number_density",
    "ineq_lithography_medium_formula_unit_packing_fill_factor_at_most_unity",
    "ineq_lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity",
    "eq_lithography_medium_molar_mass",
    "eq_lithography_medium_particle_mass",
    "eq_lithography_medium_formula_unit_packing_length_from_intercomponent_separation_scale",
    "eq_lithography_medium_formula_unit_packing_volume",
    "eq_lithography_medium_mass_density_from_packing",
    "eq_lithography_medium_number_density_from_mass",
    "LITHOGRAPHY_MEDIUM_DENSITY_VARIABLES",
    "LITHOGRAPHY_MEDIUM_DENSITY_EQUATIONS",
)


def __getattr__(name: str):
    if name in _DENSITY_REEXPORTS:
        from . import physical_lithography_medium_density as _density

        value = getattr(_density, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    *LITHOGRAPHY_MEDIUM_COMPONENT_EXPORTS,
    *LITHOGRAPHY_MEDIUM_BINDING_EXPORTS,
    *_DENSITY_REEXPORTS,
    "lithography_medium_component_a_effective_intercomponent_charge_number",
    "lithography_medium_component_b_effective_intercomponent_charge_number",
    "lithography_medium_formula_unit_intercomponent_pair_count",
    "lithography_medium_intercomponent_effective_separation",
    "lithography_medium_intercomponent_relative_permittivity",
    "lithography_medium_formula_unit_intercomponent_charge_transfer_electron_count",
    "lithography_medium_intercomponent_charge_unit",
    "lithography_medium_component_a_intercomponent_radius_scale_factor",
    "lithography_medium_component_b_intercomponent_radius_scale_factor",
    "lithography_medium_component_a_effective_intercomponent_radius",
    "lithography_medium_component_b_effective_intercomponent_radius",
    "lithography_medium_intercomponent_gap_fraction",
    "lithography_medium_intercomponent_gap",
    "lithography_medium_formula_unit_intercomponent_binding_energy",
    "lithography_medium_formula_unit_proton_count",
    "lithography_medium_formula_unit_neutron_count",
    "lithography_medium_formula_unit_electron_count",
    "lithography_medium_formula_unit_binding_energy",
    "lithography_medium_formula_unit_rest_mass",
    "ineq_lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_a_electron_inventory",
    "ineq_lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_b_electron_inventory",
    "eq_lithography_medium_intercomponent_charge_unit_from_formula_unit_charge_transfer",
    "eq_lithography_medium_component_a_effective_intercomponent_charge_number",
    "eq_lithography_medium_component_b_effective_intercomponent_charge_number",
    "eq_lithography_medium_formula_unit_intercomponent_pair_count",
    "eq_lithography_medium_component_a_effective_intercomponent_radius",
    "eq_lithography_medium_component_b_effective_intercomponent_radius",
    "eq_lithography_medium_intercomponent_gap_from_radius_fraction",
    "eq_lithography_medium_intercomponent_effective_separation",
    "eq_lithography_medium_formula_unit_intercomponent_binding_energy",
    "eq_lithography_medium_formula_unit_proton_count",
    "eq_lithography_medium_formula_unit_neutron_count",
    "eq_lithography_medium_formula_unit_electron_count",
    "eq_lithography_medium_formula_unit_binding_energy",
    "eq_lithography_medium_formula_unit_rest_mass",
    "LITHOGRAPHY_MEDIUM_COMPOSITION_VARIABLES",
    "LITHOGRAPHY_MEDIUM_COMPOSITION_EQUATIONS",
]
