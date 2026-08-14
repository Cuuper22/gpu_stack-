"""
scopes/physical_lithography.py
==============================

Lithography: the optics that decide how small a printed feature can be.
The physical_lithography_* family exists to answer one question from first
principles: what critical dimension can the exposure tool print? The
Rayleigh relation CD = k1 * lambda / NA needs three inputs -- the exposure
wavelength (built up from the emitting source plasma and its atomic
transitions), the numerical aperture (objective geometry times the imaging
medium refractive index), and the k1 process factor. This module is the
compatibility surface: declarations live in focused sibling modules, and it
re-exports them so the historical import surface stays stable. The printed
gate, contact, and metal dimensions feed the process scope above.
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
from .physical_lithography_optical_core import (
    LITHOGRAPHY_OPTICAL_CORE_EQUATIONS as _LITHOGRAPHY_OPTICAL_CORE_EQUATIONS,
    LITHOGRAPHY_OPTICAL_CORE_VARIABLES as _LITHOGRAPHY_OPTICAL_CORE_VARIABLES,
    LITHOGRAPHY_REF,
    eq_lithography_photon_frequency,
    eq_lithography_source_angular_frequency,
    eq_lithography_wavelength_from_frequency,
    lithography_numerical_aperture,
    lithography_photon_frequency,
    lithography_source_angular_frequency,
    lithography_wavelength,
)
from .physical_lithography_medium_optics import (
    LITHOGRAPHY_MEDIUM_OPTICS_EQUATIONS as _LITHOGRAPHY_MEDIUM_OPTICS_EQUATIONS,
    LITHOGRAPHY_MEDIUM_OPTICS_VARIABLES as _LITHOGRAPHY_MEDIUM_OPTICS_VARIABLES,
    eq_lithography_medium_electric_polarizability,
    eq_lithography_medium_intercomponent_lorentz_lorenz_factor,
    eq_lithography_medium_intercomponent_relative_permittivity_from_local_lorentz_lorenz,
    eq_lithography_medium_lorentz_lorenz_factor,
    eq_lithography_medium_oscillator_strength_from_formula_electrons,
    eq_lithography_medium_refractive_index,
    eq_lithography_medium_relative_permeability,
    eq_lithography_medium_relative_permittivity,
    eq_lithography_medium_resonance_angular_frequency_from_source_ratio,
    lithography_medium_electric_polarizability,
    lithography_medium_intercomponent_lorentz_lorenz_factor,
    lithography_medium_intercomponent_polarizable_site_density_factor,
    lithography_medium_lorentz_lorenz_factor,
    lithography_medium_magnetic_susceptibility,
    lithography_medium_oscillator_strength,
    lithography_medium_refractive_index,
    lithography_medium_relative_permeability,
    lithography_medium_relative_permittivity,
    lithography_medium_resonance_angular_frequency,
)
from .physical_lithography_objective import (
    LITHOGRAPHY_OBJECTIVE_EQUATIONS as _LITHOGRAPHY_OBJECTIVE_EQUATIONS,
    LITHOGRAPHY_OBJECTIVE_VARIABLES as _LITHOGRAPHY_OBJECTIVE_VARIABLES,
    contact_lithography_resolution,
    eq_contact_lithography_resolution,
    eq_gate_lithography_resolution,
    eq_lithography_acceptance_half_angle,
    eq_lithography_numerical_aperture,
    eq_metal_spacing_lithography_resolution,
    eq_metal_width_lithography_resolution,
    gate_lithography_resolution,
    ineq_lithography_acceptance_half_angle_within_forward_half_space,
    ineq_lithography_numerical_aperture_within_medium_index,
    lithography_acceptance_half_angle,
    lithography_objective_focal_length,
    lithography_objective_pupil_radius,
    metal_spacing_lithography_resolution,
    metal_width_lithography_resolution,
)


LITHOGRAPHY_VARIABLES = [
    *LITHOGRAPHY_SOURCE_VARIABLES,
    *LITHOGRAPHY_MEDIUM_COMPOSITION_VARIABLES,
    *LITHOGRAPHY_MEDIUM_DENSITY_VARIABLES,
    *LITHOGRAPHY_K1_VARIABLES,
    *_LITHOGRAPHY_OPTICAL_CORE_VARIABLES,
    *LITHOGRAPHY_MEDIUM_RESPONSE_VARIABLES,
    *_LITHOGRAPHY_MEDIUM_OPTICS_VARIABLES,
    *_LITHOGRAPHY_OBJECTIVE_VARIABLES,
]

LITHOGRAPHY_EQUATIONS = [
    *LITHOGRAPHY_SOURCE_EQUATIONS,
    *LITHOGRAPHY_K1_EQUATIONS,
    *_LITHOGRAPHY_OPTICAL_CORE_EQUATIONS,
    *LITHOGRAPHY_MEDIUM_COMPOSITION_EQUATIONS,
    *LITHOGRAPHY_MEDIUM_DENSITY_EQUATIONS,
    *LITHOGRAPHY_MEDIUM_RESPONSE_EQUATIONS,
    *_LITHOGRAPHY_MEDIUM_OPTICS_EQUATIONS,
    *_LITHOGRAPHY_OBJECTIVE_EQUATIONS,
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
