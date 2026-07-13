"""
scopes/physical_lithography_medium_intercomponent_variables.py
==============================================================

Variable declarations for lithography imaging-medium intercomponent closure.
"""

import sympy as sp

from ..core import var
from ..core.units import JOULE, METER
from .physical_lithography_medium_components import LITHOGRAPHY_MEDIUM_COMPOSITION_REF


lithography_medium_component_a_effective_intercomponent_charge_number = var(
    "physical.lithography.medium_component_a_effective_intercomponent_charge_number",
    "z_eff_A_inter_litho_med",
    "dimensionless",
    "Effective signed ionic charge number carried by component A in the intercomponent binding model.",
    scope="physical",
    signed=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_effective_intercomponent_charge_number = var(
    "physical.lithography.medium_component_b_effective_intercomponent_charge_number",
    "z_eff_B_inter_litho_med",
    "dimensionless",
    "Effective signed ionic charge number carried by component B in the intercomponent binding model.",
    scope="physical",
    signed=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_formula_unit_intercomponent_pair_count = var(
    "physical.lithography.medium_formula_unit_intercomponent_pair_count",
    "N_pair_inter_formula_litho_med",
    "count",
    "Effective count of attractive component A-B intercomponent pairs in one representative formula unit.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_intercomponent_effective_separation = var(
    "physical.lithography.medium_intercomponent_effective_separation",
    "r_inter_litho_med",
    "m",
    "Effective center-to-center separation for attractive intercomponent charge-pair binding.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_intercomponent_relative_permittivity = var(
    "physical.lithography.medium_intercomponent_relative_permittivity",
    "eps_r_inter_litho_med",
    "dimensionless",
    "Effective relative permittivity screening the intercomponent electrostatic binding.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_formula_unit_intercomponent_charge_transfer_electron_count = var(
    "physical.lithography.medium_formula_unit_intercomponent_charge_transfer_electron_count",
    "N_e_transfer_inter_formula_litho_med",
    "count",
    "Effective transferred-electron magnitude per representative formula unit for intercomponent charge normalization.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_intercomponent_charge_unit = var(
    "physical.lithography.medium_intercomponent_charge_unit",
    "z_unit_inter_litho_med",
    "dimensionless",
    "Positive charge-unit magnitude derived from formula-unit charge transfer and binary stoichiometry.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_intercomponent_radius_scale_factor = var(
    "physical.lithography.medium_component_a_intercomponent_radius_scale_factor",
    "gamma_r_A_inter_litho_med",
    "dimensionless",
    "Local geometry scale factor mapping component-A nuclear radius to effective intercomponent radius.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_intercomponent_radius_scale_factor = var(
    "physical.lithography.medium_component_b_intercomponent_radius_scale_factor",
    "gamma_r_B_inter_litho_med",
    "dimensionless",
    "Local geometry scale factor mapping component-B nuclear radius to effective intercomponent radius.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_a_effective_intercomponent_radius = var(
    "physical.lithography.medium_component_a_effective_intercomponent_radius",
    "r_eff_A_inter_litho_med",
    "m",
    "Effective component-A radius contributing to intercomponent charge-pair separation.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_component_b_effective_intercomponent_radius = var(
    "physical.lithography.medium_component_b_effective_intercomponent_radius",
    "r_eff_B_inter_litho_med",
    "m",
    "Effective component-B radius contributing to intercomponent charge-pair separation.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_intercomponent_gap_fraction = var(
    "physical.lithography.medium_intercomponent_gap_fraction",
    "eta_gap_inter_litho_med",
    "dimensionless",
    "Residual intercomponent gap as a fraction of the summed effective component radii.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_intercomponent_gap = var(
    "physical.lithography.medium_intercomponent_gap",
    "g_inter_litho_med",
    "m",
    "Nonnegative residual intercomponent gap between effective component radii.",
    scope="physical",
    nonnegative=True,
    sp_units=METER,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_formula_unit_intercomponent_binding_energy = var(
    "physical.lithography.medium_formula_unit_intercomponent_binding_energy",
    "E_bind_inter_formula_litho_med",
    "J",
    "Intercomponent binding-energy mass defect for the representative imaging-medium formula unit.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)


LITHOGRAPHY_MEDIUM_INTERCOMPONENT_VARIABLES = [
    lithography_medium_component_a_effective_intercomponent_charge_number,
    lithography_medium_component_b_effective_intercomponent_charge_number,
    lithography_medium_formula_unit_intercomponent_pair_count,
    lithography_medium_intercomponent_effective_separation,
    lithography_medium_intercomponent_relative_permittivity,
    lithography_medium_formula_unit_intercomponent_charge_transfer_electron_count,
    lithography_medium_intercomponent_charge_unit,
    lithography_medium_component_a_intercomponent_radius_scale_factor,
    lithography_medium_component_b_intercomponent_radius_scale_factor,
    lithography_medium_component_a_effective_intercomponent_radius,
    lithography_medium_component_b_effective_intercomponent_radius,
    lithography_medium_intercomponent_gap_fraction,
    lithography_medium_intercomponent_gap,
    lithography_medium_formula_unit_intercomponent_binding_energy,
]

LITHOGRAPHY_MEDIUM_INTERCOMPONENT_VARIABLE_EXPORTS = [
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
]

__all__ = [
    *LITHOGRAPHY_MEDIUM_INTERCOMPONENT_VARIABLE_EXPORTS,
    "LITHOGRAPHY_MEDIUM_INTERCOMPONENT_VARIABLES",
    "LITHOGRAPHY_MEDIUM_INTERCOMPONENT_VARIABLE_EXPORTS",
]
