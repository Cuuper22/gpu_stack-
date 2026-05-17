"""
scopes/physical_lithography_plasma_focus_beam.py
================================================

Beam-quality and focusing-optic relations for the source-plasma drive focus.
"""

import sympy as sp

from ..core import Approximation, Inequality
from .physical_lithography_plasma_focus_variables import (
    lithography_source_plasma_drive_acceptance_half_angle,
    lithography_source_plasma_drive_beam_parameter_product,
    lithography_source_plasma_drive_beam_parameter_waist_radius,
    lithography_source_plasma_drive_beam_quality_factor,
    lithography_source_plasma_drive_beam_wavelength,
    lithography_source_plasma_drive_edge_detuning_ratio,
    lithography_source_plasma_drive_far_field_divergence_half_angle,
    lithography_source_plasma_drive_focus_f_number,
    lithography_source_plasma_drive_focus_waist_coefficient,
    lithography_source_plasma_drive_numerical_aperture,
    lithography_source_plasma_drive_objective_focal_length,
    lithography_source_plasma_drive_objective_pupil_radius,
    lithography_source_plasma_drive_pupil_beam_fill_factor,
)
from .physical_lithography_plasma_species import LITHOGRAPHY_SOURCE_PLASMA_STATE_REF


eq_lithography_source_plasma_drive_focus_waist_coefficient_from_gaussian_f_number = Approximation(
    "physical.eq.lithography_source_plasma_drive_focus_waist_coefficient_from_gaussian_f_number",
    lithography_source_plasma_drive_focus_waist_coefficient.symbol,
    sp.Integer(2) / sp.pi,
    sp.S.true,
    "Gaussian-beam waist coefficient mapping f-number and wavelength to diffraction-limited spot radius.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_acceptance_half_angle_from_pupil_geometry = Approximation(
    "physical.eq.lithography_source_plasma_drive_acceptance_half_angle_from_pupil_geometry",
    lithography_source_plasma_drive_acceptance_half_angle.symbol,
    sp.atan(
        lithography_source_plasma_drive_objective_pupil_radius.symbol
        / lithography_source_plasma_drive_objective_focal_length.symbol
    ),
    (
        (lithography_source_plasma_drive_objective_pupil_radius.symbol > 0)
        & (lithography_source_plasma_drive_objective_focal_length.symbol > 0)
    ),
    "Source-plasma drive acceptance half-angle from focusing optic pupil radius and focal length.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_numerical_aperture_from_acceptance_angle = Approximation(
    "physical.eq.lithography_source_plasma_drive_numerical_aperture_from_acceptance_angle",
    lithography_source_plasma_drive_numerical_aperture.symbol,
    sp.sin(lithography_source_plasma_drive_acceptance_half_angle.symbol),
    (
        (lithography_source_plasma_drive_acceptance_half_angle.symbol >= 0)
        & (lithography_source_plasma_drive_acceptance_half_angle.symbol <= sp.pi / 2)
    ),
    "Source-plasma drive numerical aperture from acceptance half-angle under a unit-index focusing approximation.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_focus_f_number_from_acceptance_angle = Approximation(
    "physical.eq.lithography_source_plasma_drive_focus_f_number_from_acceptance_angle",
    lithography_source_plasma_drive_focus_f_number.symbol,
    sp.Integer(1)
    / (
        sp.Integer(2)
        * sp.tan(lithography_source_plasma_drive_acceptance_half_angle.symbol)
    ),
    (
        (lithography_source_plasma_drive_acceptance_half_angle.symbol > 0)
        & (lithography_source_plasma_drive_acceptance_half_angle.symbol < sp.pi / 2)
    ),
    "Source-plasma drive f-number from focusing optic acceptance half-angle.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_drive_acceptance_half_angle_within_forward_half_space = Inequality(
    "physical.ineq.lithography_source_plasma_drive_acceptance_half_angle_within_forward_half_space",
    lithography_source_plasma_drive_acceptance_half_angle.symbol,
    sp.pi / 2,
    "<",
    "Source-plasma drive acceptance half-angle must remain strictly inside the forward optical half-space.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_drive_edge_detuning_ratio_below_ionization_edge = Inequality(
    "physical.ineq.lithography_source_plasma_drive_edge_detuning_ratio_below_ionization_edge",
    lithography_source_plasma_drive_edge_detuning_ratio.symbol,
    sp.Integer(1),
    ">",
    "Source-plasma drive wavelength detuning ratio should keep the drive photon below the ionization-edge resonance.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_drive_far_field_divergence_half_angle_within_forward_half_space = Inequality(
    "physical.ineq.lithography_source_plasma_drive_far_field_divergence_half_angle_within_forward_half_space",
    lithography_source_plasma_drive_far_field_divergence_half_angle.symbol,
    sp.pi / 2,
    "<=",
    "Source-plasma drive far-field divergence half-angle must remain within the forward optical half-space.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_drive_far_field_divergence_within_acceptance = Inequality(
    "physical.ineq.lithography_source_plasma_drive_far_field_divergence_within_acceptance",
    lithography_source_plasma_drive_far_field_divergence_half_angle.symbol,
    lithography_source_plasma_drive_acceptance_half_angle.symbol,
    "<=",
    "Source-plasma drive far-field divergence half-angle must fit inside the focusing optic acceptance cone.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_drive_pupil_beam_fill_factor_within_unit_interval = Inequality(
    "physical.ineq.lithography_source_plasma_drive_pupil_beam_fill_factor_within_unit_interval",
    lithography_source_plasma_drive_pupil_beam_fill_factor.symbol,
    sp.Integer(1),
    "<=",
    "Source-plasma drive pupil beam fill factor cannot exceed the available focusing pupil radius.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_beam_parameter_waist_radius_from_pupil_fill = Approximation(
    "physical.eq.lithography_source_plasma_drive_beam_parameter_waist_radius_from_pupil_fill",
    lithography_source_plasma_drive_beam_parameter_waist_radius.symbol,
    (
        lithography_source_plasma_drive_pupil_beam_fill_factor.symbol
        * lithography_source_plasma_drive_objective_pupil_radius.symbol
    ),
    (
        (lithography_source_plasma_drive_pupil_beam_fill_factor.symbol > 0)
        & (lithography_source_plasma_drive_pupil_beam_fill_factor.symbol <= 1)
        & (lithography_source_plasma_drive_objective_pupil_radius.symbol > 0)
    ),
    "Source-plasma drive beam-parameter reference radius from pupil beam fill and effective pupil radius.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_beam_parameter_product_from_waist_divergence = Approximation(
    "physical.eq.lithography_source_plasma_drive_beam_parameter_product_from_waist_divergence",
    lithography_source_plasma_drive_beam_parameter_product.symbol,
    (
        lithography_source_plasma_drive_beam_parameter_waist_radius.symbol
        * lithography_source_plasma_drive_far_field_divergence_half_angle.symbol
    ),
    (
        (lithography_source_plasma_drive_beam_parameter_waist_radius.symbol > 0)
        & (lithography_source_plasma_drive_far_field_divergence_half_angle.symbol > 0)
    ),
    "Source-plasma drive beam parameter product from pupil-plane BPP reference radius and far-field divergence half-angle.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_drive_beam_parameter_product_diffraction_floor = Inequality(
    "physical.ineq.lithography_source_plasma_drive_beam_parameter_product_diffraction_floor",
    lithography_source_plasma_drive_beam_parameter_product.symbol,
    lithography_source_plasma_drive_beam_wavelength.symbol / sp.pi,
    ">=",
    "Source-plasma drive beam parameter product cannot fall below the Gaussian diffraction limit lambda/pi.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_beam_quality_factor_from_beam_parameter_product = Approximation(
    "physical.eq.lithography_source_plasma_drive_beam_quality_factor_from_beam_parameter_product",
    lithography_source_plasma_drive_beam_quality_factor.symbol,
    (
        sp.pi
        * lithography_source_plasma_drive_beam_parameter_product.symbol
        / lithography_source_plasma_drive_beam_wavelength.symbol
    ),
    (
        (lithography_source_plasma_drive_beam_parameter_product.symbol > 0)
        & (lithography_source_plasma_drive_beam_wavelength.symbol > 0)
    ),
    "Source-plasma drive beam-quality factor from beam parameter product normalized by diffraction-limited wavelength over pi.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_drive_beam_quality_factor_diffraction_limit = Inequality(
    "physical.ineq.lithography_source_plasma_drive_beam_quality_factor_diffraction_limit",
    lithography_source_plasma_drive_beam_quality_factor.symbol,
    sp.Integer(1),
    ">=",
    "Source-plasma drive beam-quality factor is bounded below by the diffraction-limited Gaussian value M2 = 1.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_PLASMA_FOCUS_BEAM_EQUATIONS = [
    eq_lithography_source_plasma_drive_focus_waist_coefficient_from_gaussian_f_number,
    eq_lithography_source_plasma_drive_acceptance_half_angle_from_pupil_geometry,
    eq_lithography_source_plasma_drive_numerical_aperture_from_acceptance_angle,
    eq_lithography_source_plasma_drive_focus_f_number_from_acceptance_angle,
    ineq_lithography_source_plasma_drive_acceptance_half_angle_within_forward_half_space,
    ineq_lithography_source_plasma_drive_edge_detuning_ratio_below_ionization_edge,
    ineq_lithography_source_plasma_drive_far_field_divergence_half_angle_within_forward_half_space,
    ineq_lithography_source_plasma_drive_far_field_divergence_within_acceptance,
    ineq_lithography_source_plasma_drive_pupil_beam_fill_factor_within_unit_interval,
    eq_lithography_source_plasma_drive_beam_parameter_waist_radius_from_pupil_fill,
    eq_lithography_source_plasma_drive_beam_parameter_product_from_waist_divergence,
    ineq_lithography_source_plasma_drive_beam_parameter_product_diffraction_floor,
    eq_lithography_source_plasma_drive_beam_quality_factor_from_beam_parameter_product,
    ineq_lithography_source_plasma_drive_beam_quality_factor_diffraction_limit,
]

LITHOGRAPHY_SOURCE_PLASMA_FOCUS_BEAM_EXPORTS = [
    "eq_lithography_source_plasma_drive_focus_waist_coefficient_from_gaussian_f_number",
    "eq_lithography_source_plasma_drive_acceptance_half_angle_from_pupil_geometry",
    "eq_lithography_source_plasma_drive_numerical_aperture_from_acceptance_angle",
    "eq_lithography_source_plasma_drive_focus_f_number_from_acceptance_angle",
    "ineq_lithography_source_plasma_drive_acceptance_half_angle_within_forward_half_space",
    "ineq_lithography_source_plasma_drive_edge_detuning_ratio_below_ionization_edge",
    "ineq_lithography_source_plasma_drive_far_field_divergence_half_angle_within_forward_half_space",
    "ineq_lithography_source_plasma_drive_far_field_divergence_within_acceptance",
    "ineq_lithography_source_plasma_drive_pupil_beam_fill_factor_within_unit_interval",
    "eq_lithography_source_plasma_drive_beam_parameter_waist_radius_from_pupil_fill",
    "eq_lithography_source_plasma_drive_beam_parameter_product_from_waist_divergence",
    "ineq_lithography_source_plasma_drive_beam_parameter_product_diffraction_floor",
    "eq_lithography_source_plasma_drive_beam_quality_factor_from_beam_parameter_product",
    "ineq_lithography_source_plasma_drive_beam_quality_factor_diffraction_limit",
]

__all__ = [
    *LITHOGRAPHY_SOURCE_PLASMA_FOCUS_BEAM_EXPORTS,
    "LITHOGRAPHY_SOURCE_PLASMA_FOCUS_BEAM_EQUATIONS",
    "LITHOGRAPHY_SOURCE_PLASMA_FOCUS_BEAM_EXPORTS",
]
