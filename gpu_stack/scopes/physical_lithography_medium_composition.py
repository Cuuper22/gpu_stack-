"""
scopes/physical_lithography_medium_composition.py
=================================================

Formula-unit composition and rest-mass closure for lithography imaging media.
"""

import sympy as sp

from ..constants import (
    ELECTRON_MASS,
    ELEMENTARY_CHARGE,
    EPSILON_0,
    NEUTRON_MASS,
    PROTON_MASS,
    SPEED_OF_LIGHT,
)
from ..core import Approximation, Inequality, eq, var
from ..core.units import JOULE, KILOGRAM, METER
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
    LITHOGRAPHY_MEDIUM_COMPOSITION_REF,
    __all__ as LITHOGRAPHY_MEDIUM_COMPONENT_EXPORTS,
)


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
lithography_medium_formula_unit_proton_count = var(
    "physical.lithography.medium_formula_unit_proton_count", "Z_formula_litho_med", "count",
    "Total proton count in the representative formula unit of the lithography imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_formula_unit_neutron_count = var(
    "physical.lithography.medium_formula_unit_neutron_count", "N_formula_litho_med", "count",
    "Total neutron count in the representative formula unit of the lithography imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_formula_unit_electron_count = var(
    "physical.lithography.medium_formula_unit_electron_count", "e_formula_litho_med", "count",
    "Total bound electron count in the representative formula unit of the lithography imaging medium.",
    scope="physical",
    integer=True,
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_formula_unit_binding_energy = var(
    "physical.lithography.medium_formula_unit_binding_energy", "E_bind_formula_litho_med", "J",
    "Total nuclear, electronic, and chemical binding energy represented as a mass defect for one imaging-medium formula unit.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)
lithography_medium_formula_unit_rest_mass = var(
    "physical.lithography.medium_formula_unit_rest_mass", "m_formula_litho_med", "kg",
    "Rest mass of one representative formula unit of the lithography imaging medium.",
    scope="physical",
    positive=True,
    sp_units=KILOGRAM,
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
)


ineq_lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_a_electron_inventory = Inequality(
    "physical.ineq.lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_a_electron_inventory",
    lithography_medium_formula_unit_intercomponent_charge_transfer_electron_count.symbol,
    (
        lithography_medium_component_a_stoichiometric_count.symbol
        * lithography_medium_component_a_proton_count.symbol
    ),
    "<=",
    "Formula-unit intercomponent charge transfer cannot exceed the neutral component-A electron inventory.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
ineq_lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_b_electron_inventory = Inequality(
    "physical.ineq.lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_b_electron_inventory",
    lithography_medium_formula_unit_intercomponent_charge_transfer_electron_count.symbol,
    (
        lithography_medium_component_b_stoichiometric_count.symbol
        * lithography_medium_component_b_proton_count.symbol
    ),
    "<=",
    "Formula-unit intercomponent charge transfer cannot exceed the neutral component-B electron inventory.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_intercomponent_charge_unit_from_formula_unit_charge_transfer = eq(
    "physical.eq.lithography_medium_intercomponent_charge_unit_from_formula_unit_charge_transfer",
    lithography_medium_intercomponent_charge_unit.symbol,
    (
        lithography_medium_formula_unit_intercomponent_charge_transfer_electron_count.symbol
        / (
            lithography_medium_component_a_stoichiometric_count.symbol
            * lithography_medium_component_b_stoichiometric_count.symbol
        )
    ),
    "Intercomponent charge-unit magnitude from formula-unit charge transfer normalized by binary stoichiometric pair count.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_a_effective_intercomponent_charge_number = eq(
    "physical.eq.lithography_medium_component_a_effective_intercomponent_charge_number",
    lithography_medium_component_a_effective_intercomponent_charge_number.symbol,
    (
        lithography_medium_component_b_stoichiometric_count.symbol
        * lithography_medium_intercomponent_charge_unit.symbol
    ),
    "Component-A effective intercomponent charge from binary stoichiometry and a shared charge-unit magnitude.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_effective_intercomponent_charge_number = eq(
    "physical.eq.lithography_medium_component_b_effective_intercomponent_charge_number",
    lithography_medium_component_b_effective_intercomponent_charge_number.symbol,
    (
        -lithography_medium_component_a_stoichiometric_count.symbol
        * lithography_medium_intercomponent_charge_unit.symbol
    ),
    "Component-B effective intercomponent charge from binary stoichiometry and a shared charge-unit magnitude.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_intercomponent_pair_count = eq(
    "physical.eq.lithography_medium_formula_unit_intercomponent_pair_count",
    lithography_medium_formula_unit_intercomponent_pair_count.symbol,
    (
        lithography_medium_component_a_stoichiometric_count.symbol
        * lithography_medium_component_b_stoichiometric_count.symbol
    ),
    "Formula-unit intercomponent pair count from binary component stoichiometry.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_a_effective_intercomponent_radius = Approximation(
    "physical.eq.lithography_medium_component_a_effective_intercomponent_radius",
    lithography_medium_component_a_effective_intercomponent_radius.symbol,
    (
        lithography_medium_component_nuclear_radius_coefficient.symbol
        * lithography_medium_component_a_isotope_mass_number.symbol**sp.Rational(1, 3)
        * lithography_medium_component_a_intercomponent_radius_scale_factor.symbol
    ),
    (
        (lithography_medium_component_nuclear_radius_coefficient.symbol > 0)
        & (lithography_medium_component_a_isotope_mass_number.symbol > 0)
        & (lithography_medium_component_a_intercomponent_radius_scale_factor.symbol > 0)
    ),
    "Component-A effective intercomponent radius from nuclear radius scaling and local geometry factor.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_component_b_effective_intercomponent_radius = Approximation(
    "physical.eq.lithography_medium_component_b_effective_intercomponent_radius",
    lithography_medium_component_b_effective_intercomponent_radius.symbol,
    (
        lithography_medium_component_nuclear_radius_coefficient.symbol
        * lithography_medium_component_b_isotope_mass_number.symbol**sp.Rational(1, 3)
        * lithography_medium_component_b_intercomponent_radius_scale_factor.symbol
    ),
    (
        (lithography_medium_component_nuclear_radius_coefficient.symbol > 0)
        & (lithography_medium_component_b_isotope_mass_number.symbol > 0)
        & (lithography_medium_component_b_intercomponent_radius_scale_factor.symbol > 0)
    ),
    "Component-B effective intercomponent radius from nuclear radius scaling and local geometry factor.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_intercomponent_gap_from_radius_fraction = Approximation(
    "physical.eq.lithography_medium_intercomponent_gap_from_radius_fraction",
    lithography_medium_intercomponent_gap.symbol,
    (
        lithography_medium_intercomponent_gap_fraction.symbol
        * (
            lithography_medium_component_a_effective_intercomponent_radius.symbol
            + lithography_medium_component_b_effective_intercomponent_radius.symbol
        )
    ),
    (
        (lithography_medium_intercomponent_gap_fraction.symbol >= 0)
        & (lithography_medium_component_a_effective_intercomponent_radius.symbol > 0)
        & (lithography_medium_component_b_effective_intercomponent_radius.symbol > 0)
    ),
    "Residual intercomponent gap from effective radii and a dimensionless gap fraction.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_intercomponent_effective_separation = eq(
    "physical.eq.lithography_medium_intercomponent_effective_separation",
    lithography_medium_intercomponent_effective_separation.symbol,
    (
        lithography_medium_component_a_effective_intercomponent_radius.symbol
        + lithography_medium_component_b_effective_intercomponent_radius.symbol
        + lithography_medium_intercomponent_gap.symbol
    ),
    "Intercomponent effective separation from component effective radii plus residual gap.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_intercomponent_binding_energy = Approximation(
    "physical.eq.lithography_medium_formula_unit_intercomponent_binding_energy",
    lithography_medium_formula_unit_intercomponent_binding_energy.symbol,
    (
        -lithography_medium_formula_unit_intercomponent_pair_count.symbol
        * lithography_medium_component_a_effective_intercomponent_charge_number.symbol
        * lithography_medium_component_b_effective_intercomponent_charge_number.symbol
        * ELEMENTARY_CHARGE.symbol**2
        / (
            sp.Integer(4)
            * sp.pi
            * EPSILON_0.symbol
            * lithography_medium_intercomponent_relative_permittivity.symbol
            * lithography_medium_intercomponent_effective_separation.symbol
        )
    ),
    sp.And(
        lithography_medium_component_a_effective_intercomponent_charge_number.symbol
        * lithography_medium_component_b_effective_intercomponent_charge_number.symbol
        < 0,
        lithography_medium_intercomponent_effective_separation.symbol > 0,
        lithography_medium_intercomponent_relative_permittivity.symbol > 0,
    ),
    "Intercomponent formula-unit binding from screened Coulomb attraction between effective ionic charge pairs.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_proton_count = eq(
    "physical.eq.lithography_medium_formula_unit_proton_count",
    lithography_medium_formula_unit_proton_count.symbol,
    (
        lithography_medium_component_a_stoichiometric_count.symbol
        * lithography_medium_component_a_proton_count.symbol
        + lithography_medium_component_b_stoichiometric_count.symbol
        * lithography_medium_component_b_proton_count.symbol
    ),
    "Formula-unit proton count from binary component stoichiometry.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_neutron_count = eq(
    "physical.eq.lithography_medium_formula_unit_neutron_count",
    lithography_medium_formula_unit_neutron_count.symbol,
    (
        lithography_medium_component_a_stoichiometric_count.symbol
        * lithography_medium_component_a_neutron_count.symbol
        + lithography_medium_component_b_stoichiometric_count.symbol
        * lithography_medium_component_b_neutron_count.symbol
    ),
    "Formula-unit neutron count from binary component stoichiometry.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_electron_count = eq(
    "physical.eq.lithography_medium_formula_unit_electron_count",
    lithography_medium_formula_unit_electron_count.symbol,
    lithography_medium_formula_unit_proton_count.symbol,
    "Neutral imaging-medium formula-unit electron count from total proton count.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_binding_energy = eq(
    "physical.eq.lithography_medium_formula_unit_binding_energy",
    lithography_medium_formula_unit_binding_energy.symbol,
    (
        lithography_medium_component_a_stoichiometric_count.symbol
        * lithography_medium_component_a_binding_energy.symbol
        + lithography_medium_component_b_stoichiometric_count.symbol
        * lithography_medium_component_b_binding_energy.symbol
        + lithography_medium_formula_unit_intercomponent_binding_energy.symbol
    ),
    "Formula-unit binding-energy mass defect from component and intercomponent terms.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)
eq_lithography_medium_formula_unit_rest_mass = Approximation(
    "physical.eq.lithography_medium_formula_unit_rest_mass",
    lithography_medium_formula_unit_rest_mass.symbol,
    (
        lithography_medium_formula_unit_proton_count.symbol * PROTON_MASS.symbol
        + lithography_medium_formula_unit_neutron_count.symbol * NEUTRON_MASS.symbol
        + lithography_medium_formula_unit_electron_count.symbol * ELECTRON_MASS.symbol
        - lithography_medium_formula_unit_binding_energy.symbol / SPEED_OF_LIGHT.symbol**2
    ),
    (
        lithography_medium_formula_unit_binding_energy.symbol
        < (
            lithography_medium_formula_unit_proton_count.symbol * PROTON_MASS.symbol
            + lithography_medium_formula_unit_neutron_count.symbol * NEUTRON_MASS.symbol
            + lithography_medium_formula_unit_electron_count.symbol * ELECTRON_MASS.symbol
        )
        * SPEED_OF_LIGHT.symbol**2
    ),
    "Formula-unit rest mass from constituent proton, neutron, electron masses and binding-energy mass defect.",
    references=[LITHOGRAPHY_MEDIUM_COMPOSITION_REF],
    check_units=True,
)


LITHOGRAPHY_MEDIUM_COMPOSITION_VARIABLES = [
    *LITHOGRAPHY_MEDIUM_COMPONENT_VARIABLES,
    *LITHOGRAPHY_MEDIUM_BINDING_VARIABLES,
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
    lithography_medium_formula_unit_proton_count,
    lithography_medium_formula_unit_neutron_count,
    lithography_medium_formula_unit_electron_count,
    lithography_medium_formula_unit_binding_energy,
    lithography_medium_formula_unit_rest_mass,
]

LITHOGRAPHY_MEDIUM_COMPOSITION_EQUATIONS = [
    *LITHOGRAPHY_MEDIUM_COMPONENT_EQUATIONS,
    *LITHOGRAPHY_MEDIUM_BINDING_EQUATIONS,
    ineq_lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_a_electron_inventory,
    ineq_lithography_medium_formula_unit_intercomponent_charge_transfer_at_most_component_b_electron_inventory,
    eq_lithography_medium_intercomponent_charge_unit_from_formula_unit_charge_transfer,
    eq_lithography_medium_component_a_effective_intercomponent_charge_number,
    eq_lithography_medium_component_b_effective_intercomponent_charge_number,
    eq_lithography_medium_formula_unit_intercomponent_pair_count,
    eq_lithography_medium_component_a_effective_intercomponent_radius,
    eq_lithography_medium_component_b_effective_intercomponent_radius,
    eq_lithography_medium_intercomponent_gap_from_radius_fraction,
    eq_lithography_medium_intercomponent_effective_separation,
    eq_lithography_medium_formula_unit_intercomponent_binding_energy,
    eq_lithography_medium_formula_unit_proton_count,
    eq_lithography_medium_formula_unit_neutron_count,
    eq_lithography_medium_formula_unit_electron_count,
    eq_lithography_medium_formula_unit_binding_energy,
    eq_lithography_medium_formula_unit_rest_mass,
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
