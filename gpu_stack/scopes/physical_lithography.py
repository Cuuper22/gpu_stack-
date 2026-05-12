"""
scopes/physical_lithography.py
==============================

Lithography source, imaging-medium, objective, and Rayleigh-style critical
dimension relations for the physical scope.

This module is the optical bridge between universal constants and the process
geometry abstractions that consume patterned gate/contact/metal dimensions.
"""

import sympy as sp

from ..core import Approximation, Inequality, Reference, eq, gt, lt, ne, valid_all, var
from ..core.units import FARAD, HZ, METER, SECOND
from ..constants import (
    ELEMENTARY_CHARGE,
    ELECTRON_MASS,
    EPSILON_0,
    PLANCK,
    SPEED_OF_LIGHT,
)
from .physical_lithography_source import *
from .physical_lithography_source import (
    LITHOGRAPHY_SOURCE_EQUATIONS,
    LITHOGRAPHY_SOURCE_VARIABLES,
    __all__ as LITHOGRAPHY_SOURCE_EXPORTS,
)
from .physical_lithography_medium_composition import *
from .physical_lithography_medium_composition import (
    LITHOGRAPHY_MEDIUM_COMPOSITION_EQUATIONS,
    LITHOGRAPHY_MEDIUM_COMPOSITION_VARIABLES,
    __all__ as LITHOGRAPHY_MEDIUM_COMPOSITION_EXPORTS,
)
from .physical_lithography_medium_density import *
from .physical_lithography_medium_density import (
    LITHOGRAPHY_MEDIUM_DENSITY_EQUATIONS,
    LITHOGRAPHY_MEDIUM_DENSITY_VARIABLES,
    __all__ as LITHOGRAPHY_MEDIUM_DENSITY_EXPORTS,
)
from .physical_lithography_medium_response import *
from .physical_lithography_medium_response import (
    LITHOGRAPHY_MEDIUM_RESPONSE_EQUATIONS,
    LITHOGRAPHY_MEDIUM_RESPONSE_VARIABLES,
    __all__ as LITHOGRAPHY_MEDIUM_RESPONSE_EXPORTS,
)
from .physical_lithography_k1 import *
from .physical_lithography_k1 import (
    LITHOGRAPHY_K1_EQUATIONS,
    LITHOGRAPHY_K1_VARIABLES,
    __all__ as LITHOGRAPHY_K1_EXPORTS,
)


LITHOGRAPHY_REF = Reference(
    citation="Lithography abstraction: Rayleigh-style critical dimensions from wavelength, numerical aperture, process k1 factors, and signed process biases",
    kind="memo",
)


lithography_wavelength = var(
    "physical.lithography.wavelength", "lambda_litho", "m",
    "Exposure wavelength used by the lithography abstraction.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_REF],
)
lithography_photon_frequency = var(
    "physical.lithography.photon_frequency", "f_photon_litho", "Hz",
    "Optical photon frequency of the lithography exposure source.",
    scope="physical",
    positive=True,
    sp_units=HZ,
    references=[LITHOGRAPHY_REF],
)
lithography_source_angular_frequency = var(
    "physical.lithography.source_angular_frequency", "omega_litho", "1/s",
    "Angular optical frequency of the lithography exposure source.",
    scope="physical",
    positive=True,
    sp_units=1 / SECOND,
    references=[LITHOGRAPHY_REF],
)
lithography_numerical_aperture = var(
    "physical.lithography.numerical_aperture", "NA_litho", "dimensionless",
    "Numerical aperture of the lithography optical system.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
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
lithography_objective_pupil_radius = var(
    "physical.lithography.objective_pupil_radius", "r_pupil_litho", "m",
    "Effective objective pupil radius that sets the lithography acceptance cone.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_REF],
)
lithography_objective_focal_length = var(
    "physical.lithography.objective_focal_length", "f_obj_litho", "m",
    "Effective objective focal length that sets the lithography acceptance cone.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_REF],
)
lithography_acceptance_half_angle = var(
    "physical.lithography.acceptance_half_angle", "theta_litho", "rad",
    "Acceptance half-angle of the lithography objective.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
gate_lithography_resolution = var(
    "physical.lithography.gate_resolution", "CD_gate_litho", "m",
    "Lithographic gate critical-dimension scale before process bias.",
    scope="physical",
    sp_units=METER,
    references=[LITHOGRAPHY_REF],
)
contact_lithography_resolution = var(
    "physical.lithography.contact_resolution", "CD_contact_litho", "m",
    "Lithographic contact critical-dimension scale before process bias.",
    scope="physical",
    sp_units=METER,
    references=[LITHOGRAPHY_REF],
)
metal_width_lithography_resolution = var(
    "physical.lithography.metal_width_resolution", "CD_metal_w_litho", "m",
    "Lithographic minimum-metal-width scale before process bias.",
    scope="physical",
    sp_units=METER,
    references=[LITHOGRAPHY_REF],
)
metal_spacing_lithography_resolution = var(
    "physical.lithography.metal_spacing_resolution", "CD_metal_s_litho", "m",
    "Lithographic minimum-metal-spacing scale before process bias.",
    scope="physical",
    sp_units=METER,
    references=[LITHOGRAPHY_REF],
)


eq_lithography_photon_frequency = eq(
    "physical.eq.lithography_photon_frequency",
    lithography_photon_frequency.symbol,
    lithography_photon_energy.symbol / PLANCK.symbol,
    "Photon frequency from photon energy and Planck's constant.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_lithography_wavelength_from_frequency = eq(
    "physical.eq.lithography_wavelength_from_frequency",
    lithography_wavelength.symbol,
    SPEED_OF_LIGHT.symbol / lithography_photon_frequency.symbol,
    "Exposure wavelength from photon frequency and the speed of light in vacuum.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_lithography_source_angular_frequency = eq(
    "physical.eq.lithography_source_angular_frequency",
    lithography_source_angular_frequency.symbol,
    2 * sp.pi * lithography_photon_frequency.symbol,
    "Optical angular frequency from photon frequency.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
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

eq_lithography_acceptance_half_angle = Approximation(
    "physical.eq.lithography_acceptance_half_angle",
    lithography_acceptance_half_angle.symbol,
    sp.atan(
        lithography_objective_pupil_radius.symbol
        / lithography_objective_focal_length.symbol
    ),
    lithography_objective_focal_length.symbol > 0,
    "Acceptance half-angle from objective pupil radius and focal length.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

ineq_lithography_acceptance_half_angle_within_forward_half_space = Inequality(
    "physical.ineq.lithography_acceptance_half_angle_within_forward_half_space",
    lithography_acceptance_half_angle.symbol, sp.pi / 2, "<=",
    "Lithography acceptance half-angle must remain within the forward optical half-space.",
    references=[LITHOGRAPHY_REF], check_units=True,
)

eq_lithography_numerical_aperture = Approximation(
    "physical.eq.lithography_numerical_aperture",
    lithography_numerical_aperture.symbol,
    lithography_medium_refractive_index.symbol
    * sp.sin(lithography_acceptance_half_angle.symbol),
    (lithography_medium_refractive_index.symbol > 0)
    & (lithography_acceptance_half_angle.symbol >= 0),
    "Numerical aperture from imaging-medium refractive index and objective acceptance half-angle.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

ineq_lithography_numerical_aperture_within_medium_index = Inequality(
    "physical.ineq.lithography_numerical_aperture_within_medium_index",
    lithography_numerical_aperture.symbol, lithography_medium_refractive_index.symbol, "<=",
    "Lithography numerical aperture cannot exceed the imaging-medium refractive index.",
    references=[LITHOGRAPHY_REF], check_units=True,
)

eq_gate_lithography_resolution = Approximation(
    "physical.eq.gate_lithography_resolution",
    gate_lithography_resolution.symbol,
    gate_resolution_k1.symbol
    * lithography_wavelength.symbol
    / lithography_numerical_aperture.symbol,
    valid_all(
        gt(gate_resolution_k1.symbol, 0),
        gt(lithography_wavelength.symbol, 0),
        gt(lithography_numerical_aperture.symbol, 0),
    ),
    "Gate critical-dimension resolution from Rayleigh-style k1 wavelength over numerical aperture.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_contact_lithography_resolution = Approximation(
    "physical.eq.contact_lithography_resolution",
    contact_lithography_resolution.symbol,
    contact_resolution_k1.symbol
    * lithography_wavelength.symbol
    / lithography_numerical_aperture.symbol,
    valid_all(
        gt(contact_resolution_k1.symbol, 0),
        gt(lithography_wavelength.symbol, 0),
        gt(lithography_numerical_aperture.symbol, 0),
    ),
    "Contact critical-dimension resolution from Rayleigh-style k1 wavelength over numerical aperture.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_metal_width_lithography_resolution = Approximation(
    "physical.eq.metal_width_lithography_resolution",
    metal_width_lithography_resolution.symbol,
    metal_width_resolution_k1.symbol
    * lithography_wavelength.symbol
    / lithography_numerical_aperture.symbol,
    valid_all(
        gt(metal_width_resolution_k1.symbol, 0),
        gt(lithography_wavelength.symbol, 0),
        gt(lithography_numerical_aperture.symbol, 0),
    ),
    "Minimum-metal-width resolution from Rayleigh-style k1 wavelength over numerical aperture.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_metal_spacing_lithography_resolution = Approximation(
    "physical.eq.metal_spacing_lithography_resolution",
    metal_spacing_lithography_resolution.symbol,
    metal_spacing_resolution_k1.symbol
    * lithography_wavelength.symbol
    / lithography_numerical_aperture.symbol,
    valid_all(
        gt(metal_spacing_resolution_k1.symbol, 0),
        gt(lithography_wavelength.symbol, 0),
        gt(lithography_numerical_aperture.symbol, 0),
    ),
    "Minimum-metal-spacing resolution from Rayleigh-style k1 wavelength over numerical aperture.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)


LITHOGRAPHY_VARIABLES = [
    *LITHOGRAPHY_SOURCE_VARIABLES,
    *LITHOGRAPHY_MEDIUM_COMPOSITION_VARIABLES,
    *LITHOGRAPHY_MEDIUM_DENSITY_VARIABLES,
    *LITHOGRAPHY_K1_VARIABLES,
    lithography_wavelength,
    lithography_photon_frequency,
    lithography_source_angular_frequency,
    lithography_numerical_aperture,
    *LITHOGRAPHY_MEDIUM_RESPONSE_VARIABLES,
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
    lithography_objective_pupil_radius,
    lithography_objective_focal_length,
    lithography_acceptance_half_angle,
    gate_lithography_resolution,
    contact_lithography_resolution,
    metal_width_lithography_resolution,
    metal_spacing_lithography_resolution,
]

LITHOGRAPHY_EQUATIONS = [
    *LITHOGRAPHY_SOURCE_EQUATIONS,
    *LITHOGRAPHY_K1_EQUATIONS,
    eq_lithography_photon_frequency,
    eq_lithography_wavelength_from_frequency,
    eq_lithography_source_angular_frequency,
    *LITHOGRAPHY_MEDIUM_COMPOSITION_EQUATIONS,
    *LITHOGRAPHY_MEDIUM_DENSITY_EQUATIONS,
    *LITHOGRAPHY_MEDIUM_RESPONSE_EQUATIONS,
    eq_lithography_medium_resonance_angular_frequency_from_source_ratio,
    eq_lithography_medium_oscillator_strength_from_formula_electrons,
    eq_lithography_medium_electric_polarizability,
    eq_lithography_medium_intercomponent_lorentz_lorenz_factor,
    eq_lithography_medium_intercomponent_relative_permittivity_from_local_lorentz_lorenz,
    eq_lithography_medium_lorentz_lorenz_factor,
    eq_lithography_medium_relative_permittivity,
    eq_lithography_medium_relative_permeability,
    eq_lithography_medium_refractive_index,
    eq_lithography_acceptance_half_angle,
    ineq_lithography_acceptance_half_angle_within_forward_half_space,
    eq_lithography_numerical_aperture,
    ineq_lithography_numerical_aperture_within_medium_index,
    eq_gate_lithography_resolution,
    eq_contact_lithography_resolution,
    eq_metal_width_lithography_resolution,
    eq_metal_spacing_lithography_resolution,
]


__all__ = [
    *LITHOGRAPHY_SOURCE_EXPORTS,
    *LITHOGRAPHY_MEDIUM_COMPOSITION_EXPORTS,
    *LITHOGRAPHY_MEDIUM_DENSITY_EXPORTS,
    *LITHOGRAPHY_MEDIUM_RESPONSE_EXPORTS,
    *LITHOGRAPHY_K1_EXPORTS,
    "LITHOGRAPHY_REF",
    "lithography_wavelength",
    "lithography_photon_frequency",
    "lithography_source_angular_frequency",
    "lithography_numerical_aperture",
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
    "lithography_objective_pupil_radius",
    "lithography_objective_focal_length",
    "lithography_acceptance_half_angle",
    "gate_lithography_resolution",
    "contact_lithography_resolution",
    "metal_width_lithography_resolution",
    "metal_spacing_lithography_resolution",
    "eq_lithography_photon_frequency",
    "eq_lithography_wavelength_from_frequency",
    "eq_lithography_source_angular_frequency",
    "eq_lithography_medium_resonance_angular_frequency_from_source_ratio",
    "eq_lithography_medium_oscillator_strength_from_formula_electrons",
    "eq_lithography_medium_electric_polarizability",
    "eq_lithography_medium_intercomponent_lorentz_lorenz_factor",
    "eq_lithography_medium_intercomponent_relative_permittivity_from_local_lorentz_lorenz",
    "eq_lithography_medium_lorentz_lorenz_factor",
    "eq_lithography_medium_relative_permittivity",
    "eq_lithography_medium_relative_permeability",
    "eq_lithography_medium_refractive_index",
    "eq_lithography_acceptance_half_angle",
    "ineq_lithography_acceptance_half_angle_within_forward_half_space",
    "eq_lithography_numerical_aperture",
    "ineq_lithography_numerical_aperture_within_medium_index",
    "eq_gate_lithography_resolution",
    "eq_contact_lithography_resolution",
    "eq_metal_width_lithography_resolution",
    "eq_metal_spacing_lithography_resolution",
    "LITHOGRAPHY_VARIABLES",
    "LITHOGRAPHY_EQUATIONS",
]
