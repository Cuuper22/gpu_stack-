"""
scopes/physical_lithography_medium_optics.py
============================================

Imaging-medium Lorentz response, local screening, and refractive index.
"""

import sympy as sp

from ..core import Approximation, eq, gt, lt, ne, valid_all, var
from ..core.units import FARAD, METER, SECOND
from ..constants import ELEMENTARY_CHARGE, ELECTRON_MASS, EPSILON_0
from .physical_lithography_medium_composition import (
    lithography_medium_formula_unit_electron_count,
    lithography_medium_intercomponent_effective_separation,
    lithography_medium_intercomponent_relative_permittivity,
)
from .physical_lithography_medium_density import lithography_medium_number_density
from .physical_lithography_medium_response import (
    lithography_medium_oscillator_sum_rule_fraction,
    lithography_medium_polarizable_electron_fraction,
    lithography_medium_resonance_to_source_frequency_ratio,
)
from .physical_lithography_optical_core import (
    LITHOGRAPHY_REF,
    lithography_source_angular_frequency,
)


lithography_medium_resonance_angular_frequency = var(
    "physical.lithography.medium_resonance_angular_frequency", "omega0_litho_med", "1/s",
    "Dominant bound-electron resonance angular frequency of the lithography imaging medium.",
    scope="physical",
    sp_units=1 / SECOND,
    references=[LITHOGRAPHY_REF],
)
lithography_medium_oscillator_strength = var(
    "physical.lithography.medium_oscillator_strength", "f_osc_litho_med", "dimensionless",
    "Effective dimensionless oscillator strength for the dominant electric polarization mode.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
lithography_medium_electric_polarizability = var(
    "physical.lithography.medium_electric_polarizability", "alpha_e_litho_med", "F*m^2",
    "Effective molecular electric polarizability of the lithography imaging medium.",
    scope="physical",
    sp_units=FARAD * METER ** 2,
    references=[LITHOGRAPHY_REF],
)
lithography_medium_intercomponent_polarizable_site_density_factor = var(
    "physical.lithography.medium_intercomponent_polarizable_site_density_factor", "eta_pol_inter_litho_med", "dimensionless",
    "Local polarizable-site density factor per effective intercomponent separation volume.",
    scope="physical", nonnegative=True,
    sp_units=sp.Integer(1), references=[LITHOGRAPHY_REF],
)
lithography_medium_intercomponent_lorentz_lorenz_factor = var(
    "physical.lithography.medium_intercomponent_lorentz_lorenz_factor", "x_LL_inter_litho_med", "dimensionless",
    "Local Lorentz-Lorenz response factor for intercomponent electrostatic screening.",
    scope="physical", sp_units=sp.Integer(1), references=[LITHOGRAPHY_REF],
)
lithography_medium_lorentz_lorenz_factor = var(
    "physical.lithography.medium_lorentz_lorenz_factor", "x_LL_litho_med", "dimensionless",
    "Lorentz-Lorenz material response factor N alpha_e / (3 epsilon_0).",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
lithography_medium_relative_permittivity = var(
    "physical.lithography.medium_relative_permittivity", "epsilon_litho_med_rel", "dimensionless",
    "Relative permittivity of the lithography imaging medium at the exposure wavelength.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
lithography_medium_relative_permeability = var(
    "physical.lithography.medium_relative_permeability", "mu_litho_med_rel", "dimensionless",
    "Relative permeability of the lithography imaging medium at the exposure wavelength.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
lithography_medium_magnetic_susceptibility = var(
    "physical.lithography.medium_magnetic_susceptibility", "chi_m_litho_med", "dimensionless",
    "Magnetic susceptibility of the lithography imaging medium at the exposure wavelength.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
lithography_medium_refractive_index = var(
    "physical.lithography.medium_refractive_index", "n_litho_med", "dimensionless",
    "Refractive index of the lithography imaging medium.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)


eq_lithography_medium_resonance_angular_frequency_from_source_ratio = Approximation(
    "physical.eq.lithography_medium_resonance_angular_frequency_from_source_ratio",
    lithography_medium_resonance_angular_frequency.symbol,
    (
        lithography_medium_resonance_to_source_frequency_ratio.symbol
        * lithography_source_angular_frequency.symbol
    ),
    lithography_medium_resonance_to_source_frequency_ratio.symbol > 0,
    "Dominant medium resonance angular frequency from a source-frequency ratio.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_lithography_medium_oscillator_strength_from_formula_electrons = Approximation(
    "physical.eq.lithography_medium_oscillator_strength_from_formula_electrons",
    lithography_medium_oscillator_strength.symbol,
    (
        lithography_medium_formula_unit_electron_count.symbol
        * lithography_medium_polarizable_electron_fraction.symbol
        * lithography_medium_oscillator_sum_rule_fraction.symbol
    ),
    (
        (lithography_medium_formula_unit_electron_count.symbol >= 0)
        & (lithography_medium_polarizable_electron_fraction.symbol >= 0)
        & (lithography_medium_oscillator_sum_rule_fraction.symbol >= 0)
    ),
    "Dominant oscillator strength from formula-unit electron count and participating-electron fractions.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_lithography_medium_electric_polarizability = Approximation(
    "physical.eq.lithography_medium_electric_polarizability",
    lithography_medium_electric_polarizability.symbol,
    (
        lithography_medium_oscillator_strength.symbol
        * ELEMENTARY_CHARGE.symbol**2
        / (
            ELECTRON_MASS.symbol
            * (
                lithography_medium_resonance_angular_frequency.symbol**2
                - lithography_source_angular_frequency.symbol**2
            )
        )
    ),
    valid_all(
        gt(lithography_medium_resonance_angular_frequency.symbol, 0),
        ne(
            lithography_medium_resonance_angular_frequency.symbol**2,
            lithography_source_angular_frequency.symbol**2,
        ),
    ),
    "Bound-electron Lorentz-oscillator polarizability for an off-resonant imaging medium.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_lithography_medium_intercomponent_lorentz_lorenz_factor = Approximation(
    "physical.eq.lithography_medium_intercomponent_lorentz_lorenz_factor",
    lithography_medium_intercomponent_lorentz_lorenz_factor.symbol,
    (
        lithography_medium_intercomponent_polarizable_site_density_factor.symbol
        * lithography_medium_electric_polarizability.symbol
        / (
            sp.Integer(3)
            * EPSILON_0.symbol
            * lithography_medium_intercomponent_effective_separation.symbol**3
        )
    ),
    (
        (lithography_medium_intercomponent_polarizable_site_density_factor.symbol >= 0)
        & (lithography_medium_intercomponent_effective_separation.symbol > 0)
    ),
    "Local intercomponent Lorentz-Lorenz factor from molecular polarizability over effective separation volume.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_lithography_medium_intercomponent_relative_permittivity_from_local_lorentz_lorenz = Approximation(
    "physical.eq.lithography_medium_intercomponent_relative_permittivity_from_local_lorentz_lorenz",
    lithography_medium_intercomponent_relative_permittivity.symbol,
    (
        (sp.Integer(1) + sp.Integer(2) * lithography_medium_intercomponent_lorentz_lorenz_factor.symbol)
        / (sp.Integer(1) - lithography_medium_intercomponent_lorentz_lorenz_factor.symbol)
    ),
    (
        (lithography_medium_intercomponent_lorentz_lorenz_factor.symbol > sp.Rational(-1, 2))
        & (lithography_medium_intercomponent_lorentz_lorenz_factor.symbol < 1)
    ),
    "Intercomponent relative permittivity from a local Lorentz-Lorenz screening factor.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_lithography_medium_lorentz_lorenz_factor = Approximation(
    "physical.eq.lithography_medium_lorentz_lorenz_factor",
    lithography_medium_lorentz_lorenz_factor.symbol,
    lithography_medium_number_density.symbol
    * lithography_medium_electric_polarizability.symbol
    / (sp.Integer(3) * EPSILON_0.symbol),
    lithography_medium_number_density.symbol >= 0,
    "Lorentz-Lorenz factor from medium number density, molecular electric polarizability, and vacuum permittivity.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_lithography_medium_relative_permittivity = Approximation(
    "physical.eq.lithography_medium_relative_permittivity",
    lithography_medium_relative_permittivity.symbol,
    (sp.Integer(1) + sp.Integer(2) * lithography_medium_lorentz_lorenz_factor.symbol)
    / (sp.Integer(1) - lithography_medium_lorentz_lorenz_factor.symbol),
    valid_all(
        gt(lithography_medium_lorentz_lorenz_factor.symbol, sp.Rational(-1, 2)),
        lt(lithography_medium_lorentz_lorenz_factor.symbol, 1),
    ),
    "Relative permittivity from the Lorentz-Lorenz relation for an isotropic linear imaging medium.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_lithography_medium_relative_permeability = eq(
    "physical.eq.lithography_medium_relative_permeability",
    lithography_medium_relative_permeability.symbol,
    sp.Integer(1) + lithography_medium_magnetic_susceptibility.symbol,
    "Relative permeability from linear magnetic susceptibility of the imaging medium.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_lithography_medium_refractive_index = Approximation(
    "physical.eq.lithography_medium_refractive_index",
    lithography_medium_refractive_index.symbol,
    sp.sqrt(
        lithography_medium_relative_permittivity.symbol
        * lithography_medium_relative_permeability.symbol
    ),
    (lithography_medium_relative_permittivity.symbol > 0)
    & (lithography_medium_relative_permeability.symbol > 0),
    "Imaging-medium refractive index from relative permittivity and relative permeability at the exposure wavelength.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)


LITHOGRAPHY_MEDIUM_OPTICS_VARIABLES = [
    lithography_medium_resonance_angular_frequency,
    lithography_medium_oscillator_strength,
    lithography_medium_electric_polarizability,
    lithography_medium_intercomponent_polarizable_site_density_factor,
    lithography_medium_intercomponent_lorentz_lorenz_factor,
    lithography_medium_lorentz_lorenz_factor,
    lithography_medium_relative_permittivity,
    lithography_medium_relative_permeability,
    lithography_medium_magnetic_susceptibility,
    lithography_medium_refractive_index,
]

LITHOGRAPHY_MEDIUM_OPTICS_EQUATIONS = [
    eq_lithography_medium_resonance_angular_frequency_from_source_ratio,
    eq_lithography_medium_oscillator_strength_from_formula_electrons,
    eq_lithography_medium_electric_polarizability,
    eq_lithography_medium_intercomponent_lorentz_lorenz_factor,
    eq_lithography_medium_intercomponent_relative_permittivity_from_local_lorentz_lorenz,
    eq_lithography_medium_lorentz_lorenz_factor,
    eq_lithography_medium_relative_permittivity,
    eq_lithography_medium_relative_permeability,
    eq_lithography_medium_refractive_index,
]

LITHOGRAPHY_MEDIUM_OPTICS_EXPORTS = [
    "lithography_medium_resonance_angular_frequency",
    "lithography_medium_oscillator_strength",
    "lithography_medium_electric_polarizability",
    "lithography_medium_intercomponent_polarizable_site_density_factor",
    "lithography_medium_intercomponent_lorentz_lorenz_factor",
    "lithography_medium_lorentz_lorenz_factor",
    "lithography_medium_relative_permittivity",
    "lithography_medium_relative_permeability",
    "lithography_medium_magnetic_susceptibility",
    "lithography_medium_refractive_index",
    "eq_lithography_medium_resonance_angular_frequency_from_source_ratio",
    "eq_lithography_medium_oscillator_strength_from_formula_electrons",
    "eq_lithography_medium_electric_polarizability",
    "eq_lithography_medium_intercomponent_lorentz_lorenz_factor",
    "eq_lithography_medium_intercomponent_relative_permittivity_from_local_lorentz_lorenz",
    "eq_lithography_medium_lorentz_lorenz_factor",
    "eq_lithography_medium_relative_permittivity",
    "eq_lithography_medium_relative_permeability",
    "eq_lithography_medium_refractive_index",
    "LITHOGRAPHY_MEDIUM_OPTICS_VARIABLES",
    "LITHOGRAPHY_MEDIUM_OPTICS_EQUATIONS",
    "LITHOGRAPHY_MEDIUM_OPTICS_EXPORTS",
]

__all__ = LITHOGRAPHY_MEDIUM_OPTICS_EXPORTS
