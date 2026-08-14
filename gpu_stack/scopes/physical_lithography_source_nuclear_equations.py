"""
scopes/physical_lithography_source_nuclear_equations.py
=======================================================

Nuclear relations for the source isotope. Mass number is Z + N, neutron
excess is N - Z, and the pairing sign follows nucleon parity; these feed
the liquid-drop binding-energy terms. The nuclear mass is constituent
masses minus binding energy over c^2 -- the mass defect. From nuclear and
electron mass comes the reduced mass, and its ratio to the electron mass is
the small correction the hydrogenic transition energy applies. This is why
lithography here reaches nuclear physics: the photon energy depends,
weakly, on how heavy the nucleus is.
"""

import sympy as sp

from ..constants import ELECTRON_MASS, NEUTRON_MASS, PROTON_MASS, SPEED_OF_LIGHT
from ..core import Approximation, Inequality, eq, gt
from .physical_lithography_binding_coefficients import (
    lithography_source_binding_asymmetry_coefficient,
    lithography_source_binding_coulomb_coefficient,
    lithography_source_binding_pairing_coefficient,
    lithography_source_binding_surface_coefficient,
    lithography_source_binding_volume_coefficient,
    lithography_source_pairing_reference_mass_number,
)
from .physical_lithography_source_variables import (
    LITHOGRAPHY_SOURCE_REF,
    lithography_source_binding_asymmetry_term,
    lithography_source_binding_coulomb_term,
    lithography_source_binding_pairing_term,
    lithography_source_binding_surface_term,
    lithography_source_binding_volume_term,
    lithography_source_mass_number,
    lithography_source_neutron_excess,
    lithography_source_nuclear_binding_energy,
    lithography_source_nuclear_mass,
    lithography_source_pairing_sign,
    lithography_source_reduced_mass,
    lithography_source_reduced_mass_ratio,
)
from .physical_lithography_species import (
    lithography_source_isotope_mass_number,
    lithography_source_neutron_count,
    lithography_source_proton_count,
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


_LITHOGRAPHY_SOURCE_NUCLEAR_EQUATIONS = [
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
]

_LITHOGRAPHY_SOURCE_NUCLEAR_EQUATION_EXPORTS = [
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
]


__all__ = _LITHOGRAPHY_SOURCE_NUCLEAR_EQUATION_EXPORTS
