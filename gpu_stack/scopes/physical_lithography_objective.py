"""
scopes/physical_lithography_objective.py
========================================

Objective acceptance cone, numerical aperture, and Rayleigh-style dimensions.
"""

import sympy as sp

from ..core import Approximation, Inequality, gt, valid_all, var
from ..core.units import METER
from .physical_lithography_k1 import (
    contact_resolution_k1,
    gate_resolution_k1,
    metal_spacing_resolution_k1,
    metal_width_resolution_k1,
)
from .physical_lithography_medium_optics import lithography_medium_refractive_index
from .physical_lithography_optical_core import (
    LITHOGRAPHY_REF,
    lithography_numerical_aperture,
    lithography_wavelength,
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


LITHOGRAPHY_OBJECTIVE_VARIABLES = [
    lithography_objective_pupil_radius,
    lithography_objective_focal_length,
    lithography_acceptance_half_angle,
    gate_lithography_resolution,
    contact_lithography_resolution,
    metal_width_lithography_resolution,
    metal_spacing_lithography_resolution,
]

LITHOGRAPHY_OBJECTIVE_EQUATIONS = [
    eq_lithography_acceptance_half_angle,
    ineq_lithography_acceptance_half_angle_within_forward_half_space,
    eq_lithography_numerical_aperture,
    ineq_lithography_numerical_aperture_within_medium_index,
    eq_gate_lithography_resolution,
    eq_contact_lithography_resolution,
    eq_metal_width_lithography_resolution,
    eq_metal_spacing_lithography_resolution,
]

LITHOGRAPHY_OBJECTIVE_EXPORTS = [
    "lithography_objective_pupil_radius",
    "lithography_objective_focal_length",
    "lithography_acceptance_half_angle",
    "gate_lithography_resolution",
    "contact_lithography_resolution",
    "metal_width_lithography_resolution",
    "metal_spacing_lithography_resolution",
    "eq_lithography_acceptance_half_angle",
    "ineq_lithography_acceptance_half_angle_within_forward_half_space",
    "eq_lithography_numerical_aperture",
    "ineq_lithography_numerical_aperture_within_medium_index",
    "eq_gate_lithography_resolution",
    "eq_contact_lithography_resolution",
    "eq_metal_width_lithography_resolution",
    "eq_metal_spacing_lithography_resolution",
    "LITHOGRAPHY_OBJECTIVE_VARIABLES",
    "LITHOGRAPHY_OBJECTIVE_EQUATIONS",
    "LITHOGRAPHY_OBJECTIVE_EXPORTS",
]

__all__ = LITHOGRAPHY_OBJECTIVE_EXPORTS
