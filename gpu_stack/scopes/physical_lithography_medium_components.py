"""
scopes/physical_lithography_medium_components.py
================================================

Compatibility surface for imaging-medium composition. The imaging medium is
modeled as a two-component compound: component A and component B, each a
specific isotope, combined in fixed stoichiometric proportions. The shared
provenance reference, the stoichiometric counts, the isotope descriptors,
and the relations that derive quark counts from Z and N live in focused
sibling modules; this module preserves the historical public imports and
registry ordering.
"""

from .physical_lithography_medium_components_reference import *
from .physical_lithography_medium_components_stoichiometry import *
from .physical_lithography_medium_components_stoichiometry import (
    LITHOGRAPHY_MEDIUM_COMPONENT_STOICHIOMETRY_EQUATIONS as _STOICHIOMETRY_EQUATIONS,
    LITHOGRAPHY_MEDIUM_COMPONENT_STOICHIOMETRY_VARIABLES as _STOICHIOMETRY_VARIABLES,
)
from .physical_lithography_medium_components_isotope_state import *
from .physical_lithography_medium_components_isotope_state import (
    LITHOGRAPHY_MEDIUM_COMPONENT_ISOTOPE_STATE_VARIABLES as _ISOTOPE_STATE_VARIABLES,
)
from .physical_lithography_medium_components_isotope_relations import *
from .physical_lithography_medium_components_isotope_relations import (
    LITHOGRAPHY_MEDIUM_COMPONENT_ISOTOPE_RELATION_EQUATIONS as _ISOTOPE_RELATION_EQUATIONS,
)


LITHOGRAPHY_MEDIUM_COMPONENT_VARIABLES = [
    *_STOICHIOMETRY_VARIABLES,
    *_ISOTOPE_STATE_VARIABLES,
]

LITHOGRAPHY_MEDIUM_COMPONENT_EQUATIONS = [
    *_STOICHIOMETRY_EQUATIONS,
    *_ISOTOPE_RELATION_EQUATIONS,
]


__all__ = [
    "LITHOGRAPHY_MEDIUM_COMPOSITION_REF",
    "lithography_medium_component_a_stoichiometric_count",
    "lithography_medium_component_b_stoichiometric_count",
    "lithography_medium_component_a_proton_count",
    "lithography_medium_component_b_proton_count",
    "lithography_medium_component_a_neutron_count",
    "lithography_medium_component_b_neutron_count",
    "lithography_medium_component_a_valence_up_quark_count",
    "lithography_medium_component_a_valence_down_quark_count",
    "lithography_medium_component_b_valence_up_quark_count",
    "lithography_medium_component_b_valence_down_quark_count",
    "lithography_medium_component_a_atomic_number",
    "lithography_medium_component_b_atomic_number",
    "lithography_medium_component_a_isotope_mass_number",
    "lithography_medium_component_b_isotope_mass_number",
    "ineq_lithography_medium_component_a_stoichiometric_count_at_least_one",
    "ineq_lithography_medium_component_b_stoichiometric_count_at_least_one",
    "eq_lithography_medium_component_a_valence_up_quark_count_from_zn",
    "eq_lithography_medium_component_a_valence_down_quark_count_from_zn",
    "eq_lithography_medium_component_b_valence_up_quark_count_from_zn",
    "eq_lithography_medium_component_b_valence_down_quark_count_from_zn",
    "ineq_lithography_medium_component_a_proton_count_positive",
    "ineq_lithography_medium_component_b_proton_count_positive",
    "eq_lithography_medium_component_a_atomic_number",
    "eq_lithography_medium_component_b_atomic_number",
    "eq_lithography_medium_component_a_isotope_mass_number",
    "eq_lithography_medium_component_b_isotope_mass_number",
    "LITHOGRAPHY_MEDIUM_COMPONENT_VARIABLES",
    "LITHOGRAPHY_MEDIUM_COMPONENT_EQUATIONS",
]
