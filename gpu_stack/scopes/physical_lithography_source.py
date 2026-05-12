"""
scopes/physical_lithography_source.py
=====================================

Quantum source model for lithography exposure photons.

This module keeps photon energy from being a bare scenario knob by exposing
the emitting species, nuclear mass defect, reduced mass, screening, and a
hydrogenic transition approximation as explicit graph structure.
"""

import sympy as sp

from ..core import Approximation, Inequality, Reference, eq, gt, var
from ..core.units import JOULE, KILOGRAM
from ..constants import (
    ELECTRON_MASS,
    NEUTRON_MASS,
    PROTON_MASS,
    RYDBERG_ENERGY,
    SPEED_OF_LIGHT,
)
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


LITHOGRAPHY_SOURCE_REF = Reference(
    citation=(
        "Lithography source abstraction: photon energy from nuclear mass defect, "
        "electron-nucleus reduced mass, screened effective charge, and a "
        "hydrogenic transition approximation"
    ),
    kind="memo",
)


lithography_photon_energy = var(
    "physical.lithography.photon_energy", "E_photon_litho", "J",
    "Photon energy of the lithography exposure source.",
    scope="physical",
    positive=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_nuclear_binding_energy = var(
    "physical.lithography.source_nuclear_binding_energy", "E_bind_litho_src", "J",
    "Nuclear binding energy of the emitting source isotope.",
    scope="physical",
    nonnegative=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_mass_number = var(
    "physical.lithography.source_mass_number", "A_litho_src", "count",
    "Total nucleon count alias for the emitting source isotope mass-number descriptor.",
    scope="physical",
    integer=True,
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_neutron_excess = var(
    "physical.lithography.source_neutron_excess", "Delta_NZ_litho_src", "count",
    "Neutron-proton count difference for the emitting source isotope.",
    scope="physical",
    signed=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_pairing_sign = var(
    "physical.lithography.source_pairing_sign", "s_pair_litho_src", "dimensionless",
    "Pairing selector: +1 for even-even, 0 for odd-A, -1 for odd-odd source nuclei.",
    scope="physical",
    integer=True,
    signed=True,
    value_range=(-1.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_binding_volume_term = var(
    "physical.lithography.source_binding_volume_term", "E_vol_bind_litho_src", "J",
    "Volume contribution to source nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_binding_surface_term = var(
    "physical.lithography.source_binding_surface_term", "E_surf_bind_litho_src", "J",
    "Surface penalty contribution to source nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_binding_coulomb_term = var(
    "physical.lithography.source_binding_coulomb_term", "E_coul_bind_litho_src", "J",
    "Coulomb repulsion penalty contribution to source nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_binding_asymmetry_term = var(
    "physical.lithography.source_binding_asymmetry_term", "E_asym_bind_litho_src", "J",
    "Neutron-proton asymmetry penalty contribution to source nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_binding_pairing_term = var(
    "physical.lithography.source_binding_pairing_term", "E_pair_bind_litho_src", "J",
    "Pairing contribution to source nuclear binding energy.",
    scope="physical",
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_nuclear_mass = var(
    "physical.lithography.source_nuclear_mass", "m_nuc_litho_src", "kg",
    "Nuclear rest mass of the emitting source isotope.",
    scope="physical",
    sp_units=KILOGRAM,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_reduced_mass = var(
    "physical.lithography.source_reduced_mass", "mu_litho_src", "kg",
    "Electron-nucleus reduced mass for the emitting source transition.",
    scope="physical",
    sp_units=KILOGRAM,
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_reduced_mass_ratio = var(
    "physical.lithography.source_reduced_mass_ratio", "eta_mu_litho_src", "dimensionless",
    "Reduced-mass correction relative to the electron mass.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_REF],
)
lithography_source_transition_energy = var(
    "physical.lithography.source_transition_energy", "E_transition_litho_src", "J",
    "Approximate bound-state transition energy emitted by the lithography source species.",
    scope="physical",
    positive=True,
    sp_units=JOULE,
    references=[LITHOGRAPHY_SOURCE_REF],
)


eq_lithography_source_mass_number = eq(
    "physical.eq.lithography_source_mass_number",
    lithography_source_mass_number.symbol,
    lithography_source_isotope_mass_number.symbol,
    "Source mass number alias from the isotope mass-number descriptor.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

eq_lithography_source_pairing_reference_mass_number = Approximation(
    "physical.eq.lithography_source_pairing_reference_mass_number",
    lithography_source_pairing_reference_mass_number.symbol,
    lithography_source_mass_number.symbol,
    gt(lithography_source_mass_number.symbol, 0),
    "Source-isotope self-calibrated pairing reference mass number.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

eq_lithography_source_neutron_excess = eq(
    "physical.eq.lithography_source_neutron_excess",
    lithography_source_neutron_excess.symbol,
    lithography_source_neutron_count.symbol
    - lithography_source_proton_count.symbol,
    "Source isotope neutron-proton excess.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

eq_lithography_source_pairing_sign = eq(
    "physical.eq.lithography_source_pairing_sign",
    lithography_source_pairing_sign.symbol,
    (
        (sp.Integer(1) + (-sp.Integer(1))**lithography_source_proton_count.symbol)
        * (sp.Integer(1) + (-sp.Integer(1))**lithography_source_neutron_count.symbol)
        - (
            (sp.Integer(1) - (-sp.Integer(1))**lithography_source_proton_count.symbol)
            * (sp.Integer(1) - (-sp.Integer(1))**lithography_source_neutron_count.symbol)
        )
    )
    / sp.Integer(4),
    "Pairing sign from proton and neutron parity: even-even, odd-odd, or odd-A.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

eq_lithography_source_binding_volume_term = Approximation(
    "physical.eq.lithography_source_binding_volume_term",
    lithography_source_binding_volume_term.symbol,
    lithography_source_binding_volume_coefficient.symbol
    * lithography_source_mass_number.symbol,
    gt(lithography_source_mass_number.symbol, 0),
    "Liquid-drop volume binding term.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

eq_lithography_source_binding_surface_term = Approximation(
    "physical.eq.lithography_source_binding_surface_term",
    lithography_source_binding_surface_term.symbol,
    lithography_source_binding_surface_coefficient.symbol
    * lithography_source_mass_number.symbol**sp.Rational(2, 3),
    gt(lithography_source_mass_number.symbol, 0),
    "Liquid-drop surface binding penalty term.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

eq_lithography_source_binding_coulomb_term = Approximation(
    "physical.eq.lithography_source_binding_coulomb_term",
    lithography_source_binding_coulomb_term.symbol,
    lithography_source_binding_coulomb_coefficient.symbol
    * lithography_source_proton_count.symbol
    * (lithography_source_proton_count.symbol - 1)
    / lithography_source_mass_number.symbol**sp.Rational(1, 3),
    gt(lithography_source_mass_number.symbol, 0),
    "Liquid-drop Coulomb repulsion binding penalty term.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

eq_lithography_source_binding_asymmetry_term = Approximation(
    "physical.eq.lithography_source_binding_asymmetry_term",
    lithography_source_binding_asymmetry_term.symbol,
    lithography_source_binding_asymmetry_coefficient.symbol
    * lithography_source_neutron_excess.symbol**2
    / lithography_source_mass_number.symbol,
    gt(lithography_source_mass_number.symbol, 0),
    "Liquid-drop neutron-proton asymmetry binding penalty term.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

eq_lithography_source_binding_pairing_term = Approximation(
    "physical.eq.lithography_source_binding_pairing_term",
    lithography_source_binding_pairing_term.symbol,
    lithography_source_pairing_sign.symbol
    * lithography_source_binding_pairing_coefficient.symbol
    / sp.sqrt(lithography_source_mass_number.symbol),
    gt(lithography_source_mass_number.symbol, 0),
    "Liquid-drop pairing contribution for even-even, odd-A, or odd-odd source nuclei.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

eq_lithography_source_nuclear_binding_energy = Approximation(
    "physical.eq.lithography_source_nuclear_binding_energy",
    lithography_source_nuclear_binding_energy.symbol,
    lithography_source_binding_volume_term.symbol
    - lithography_source_binding_surface_term.symbol
    - lithography_source_binding_coulomb_term.symbol
    - lithography_source_binding_asymmetry_term.symbol
    + lithography_source_binding_pairing_term.symbol,
    gt(lithography_source_mass_number.symbol, 0),
    "Semi-empirical liquid-drop nuclear binding energy for the source isotope.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

eq_lithography_source_nuclear_mass = eq(
    "physical.eq.lithography_source_nuclear_mass",
    lithography_source_nuclear_mass.symbol,
    lithography_source_proton_count.symbol * PROTON_MASS.symbol
    + lithography_source_neutron_count.symbol * NEUTRON_MASS.symbol
    - lithography_source_nuclear_binding_energy.symbol / SPEED_OF_LIGHT.symbol**2,
    "Nuclear mass from proton count, neutron count, and binding-energy mass defect.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

ineq_lithography_source_nuclear_mass_positive = Inequality(
    "physical.ineq.lithography_source_nuclear_mass_positive",
    lithography_source_nuclear_mass.symbol,
    sp.Integer(0),
    ">",
    "Source nuclear rest mass must remain positive after binding-energy mass defect.",
    references=[LITHOGRAPHY_SOURCE_REF],
)

eq_lithography_source_reduced_mass = eq(
    "physical.eq.lithography_source_reduced_mass",
    lithography_source_reduced_mass.symbol,
    ELECTRON_MASS.symbol
    * lithography_source_nuclear_mass.symbol
    / (ELECTRON_MASS.symbol + lithography_source_nuclear_mass.symbol),
    "Electron-nucleus reduced mass for a bound-state source transition.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

ineq_lithography_source_reduced_mass_positive = Inequality(
    "physical.ineq.lithography_source_reduced_mass_positive",
    lithography_source_reduced_mass.symbol,
    sp.Integer(0),
    ">",
    "Electron-nucleus reduced mass must be positive for the source transition.",
    references=[LITHOGRAPHY_SOURCE_REF],
)

eq_lithography_source_reduced_mass_ratio = eq(
    "physical.eq.lithography_source_reduced_mass_ratio",
    lithography_source_reduced_mass_ratio.symbol,
    lithography_source_reduced_mass.symbol / ELECTRON_MASS.symbol,
    "Reduced-mass correction factor relative to the electron mass.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

ineq_lithography_source_reduced_mass_ratio_positive = Inequality(
    "physical.ineq.lithography_source_reduced_mass_ratio_positive",
    lithography_source_reduced_mass_ratio.symbol,
    sp.Integer(0),
    ">",
    "Reduced-mass correction ratio must be positive for the source transition.",
    references=[LITHOGRAPHY_SOURCE_REF],
)

eq_lithography_source_transition_energy = Approximation(
    "physical.eq.lithography_source_transition_energy",
    lithography_source_transition_energy.symbol,
    RYDBERG_ENERGY.symbol
    * lithography_source_reduced_mass_ratio.symbol
    * lithography_source_effective_nuclear_charge.symbol**2
    * (
        sp.Integer(1) / lithography_source_lower_principal_quantum_number.symbol**2
        - sp.Integer(1) / lithography_source_upper_principal_quantum_number.symbol**2
    ),
    (lithography_source_upper_principal_quantum_number.symbol
     > lithography_source_lower_principal_quantum_number.symbol)
    & (lithography_source_effective_nuclear_charge.symbol > 0)
    & (lithography_source_reduced_mass_ratio.symbol > 0),
    "Hydrogenic reduced-mass source transition energy with screened effective charge.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)

eq_lithography_photon_energy_from_source_transition = Approximation(
    "physical.eq.lithography_photon_energy_from_source_transition",
    lithography_photon_energy.symbol,
    lithography_source_transition_energy.symbol,
    lithography_source_transition_energy.symbol > 0,
    "Exposure photon energy from the emitting source transition energy.",
    references=[LITHOGRAPHY_SOURCE_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_VARIABLES = [
    *LITHOGRAPHY_SOURCE_SPECIES_VARIABLES,
    *LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_VARIABLES,
    lithography_photon_energy,
    lithography_source_nuclear_binding_energy,
    lithography_source_mass_number,
    lithography_source_neutron_excess,
    lithography_source_pairing_sign,
    lithography_source_binding_volume_term,
    lithography_source_binding_surface_term,
    lithography_source_binding_coulomb_term,
    lithography_source_binding_asymmetry_term,
    lithography_source_binding_pairing_term,
    lithography_source_nuclear_mass,
    lithography_source_reduced_mass,
    lithography_source_reduced_mass_ratio,
    *LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_VARIABLES,
    lithography_source_transition_energy,
]

LITHOGRAPHY_SOURCE_EQUATIONS = [
    *LITHOGRAPHY_SOURCE_SPECIES_EQUATIONS,
    *LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_EQUATIONS,
    eq_lithography_source_mass_number,
    eq_lithography_source_pairing_reference_mass_number,
    eq_lithography_source_neutron_excess,
    eq_lithography_source_pairing_sign,
    eq_lithography_source_binding_volume_term,
    eq_lithography_source_binding_surface_term,
    eq_lithography_source_binding_coulomb_term,
    eq_lithography_source_binding_asymmetry_term,
    eq_lithography_source_binding_pairing_term,
    eq_lithography_source_nuclear_binding_energy,
    eq_lithography_source_nuclear_mass,
    ineq_lithography_source_nuclear_mass_positive,
    eq_lithography_source_reduced_mass,
    ineq_lithography_source_reduced_mass_positive,
    eq_lithography_source_reduced_mass_ratio,
    ineq_lithography_source_reduced_mass_ratio_positive,
    *LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_EQUATIONS,
    eq_lithography_source_transition_energy,
    eq_lithography_photon_energy_from_source_transition,
]


__all__ = [
    *LITHOGRAPHY_SOURCE_SPECIES_EXPORTS,
    *LITHOGRAPHY_SOURCE_BINDING_COEFFICIENT_EXPORTS,
    *LITHOGRAPHY_SOURCE_ELECTRONIC_STRUCTURE_EXPORTS,
    "LITHOGRAPHY_SOURCE_REF",
    "lithography_photon_energy",
    "lithography_source_nuclear_binding_energy",
    "lithography_source_mass_number",
    "lithography_source_neutron_excess",
    "lithography_source_pairing_sign",
    "lithography_source_binding_volume_term",
    "lithography_source_binding_surface_term",
    "lithography_source_binding_coulomb_term",
    "lithography_source_binding_asymmetry_term",
    "lithography_source_binding_pairing_term",
    "lithography_source_nuclear_mass",
    "lithography_source_reduced_mass",
    "lithography_source_reduced_mass_ratio",
    "lithography_source_transition_energy",
    "eq_lithography_source_mass_number",
    "eq_lithography_source_pairing_reference_mass_number",
    "eq_lithography_source_neutron_excess",
    "eq_lithography_source_pairing_sign",
    "eq_lithography_source_binding_volume_term",
    "eq_lithography_source_binding_surface_term",
    "eq_lithography_source_binding_coulomb_term",
    "eq_lithography_source_binding_asymmetry_term",
    "eq_lithography_source_binding_pairing_term",
    "eq_lithography_source_nuclear_binding_energy",
    "eq_lithography_source_nuclear_mass",
    "ineq_lithography_source_nuclear_mass_positive",
    "eq_lithography_source_reduced_mass",
    "ineq_lithography_source_reduced_mass_positive",
    "eq_lithography_source_reduced_mass_ratio",
    "ineq_lithography_source_reduced_mass_ratio_positive",
    "eq_lithography_source_transition_energy",
    "eq_lithography_photon_energy_from_source_transition",
    "LITHOGRAPHY_SOURCE_VARIABLES",
    "LITHOGRAPHY_SOURCE_EQUATIONS",
]
