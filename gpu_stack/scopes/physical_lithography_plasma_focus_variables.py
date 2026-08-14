"""
scopes/physical_lithography_plasma_focus_variables.py
=====================================================

Variable declarations for the drive-beam focus: drive wavelength and its
detuning ratio to the ionization edge; focusing-optic pupil radius, focal
length, acceptance half-angle, numerical aperture, and f-number; pupil-fill
and divergence quantities behind the beam parameter product and beam
quality; and the focused spot radius, Rayleigh range, confocal length,
shape factors, and illuminated area. The relations live in the sibling beam
and spot modules.
"""

import sympy as sp

from ..core.units import METER
from .physical_lithography_plasma_common import (
    DIMENSIONLESS,
    plasma_fraction,
    plasma_var,
)


lithography_source_plasma_drive_beam_wavelength = plasma_var(
    "source_plasma_drive_beam_wavelength",
    "lambda_drive_plasma_litho_src",
    "m",
    "Wavelength of the beam that drives the source plasma spot.",
    sp_units=METER,
)
lithography_source_plasma_drive_edge_detuning_ratio = plasma_var(
    "source_plasma_drive_edge_detuning_ratio",
    "rho_edge_detune_drive_litho_src",
    "dimensionless",
    "Ratio of source-plasma drive wavelength to the ionization-edge resonant wavelength.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_drive_objective_pupil_radius = plasma_var(
    "source_plasma_drive_objective_pupil_radius",
    "r_pupil_drive_plasma_litho_src",
    "m",
    "Effective pupil radius of the source-plasma drive focusing optic.",
    sp_units=METER,
)
lithography_source_plasma_drive_objective_focal_length = plasma_var(
    "source_plasma_drive_objective_focal_length",
    "f_obj_drive_plasma_litho_src",
    "m",
    "Effective focal length of the source-plasma drive focusing optic.",
    sp_units=METER,
)
lithography_source_plasma_drive_pupil_beam_fill_factor = plasma_fraction(
    "source_plasma_drive_pupil_beam_fill_factor",
    "phi_pupil_fill_drive_plasma_litho_src",
    "Fraction of the source-plasma drive focusing pupil radius filled by the beam used for BPP.",
)
lithography_source_plasma_drive_acceptance_half_angle = plasma_var(
    "source_plasma_drive_acceptance_half_angle",
    "theta_accept_drive_plasma_litho_src",
    "rad",
    "Acceptance half-angle of the source-plasma drive focusing optic.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_drive_numerical_aperture = plasma_fraction(
    "source_plasma_drive_numerical_aperture",
    "NA_drive_plasma_litho_src",
    "Numerical aperture of the source-plasma drive focusing optic.",
)
lithography_source_plasma_drive_focus_f_number = plasma_var(
    "source_plasma_drive_focus_f_number",
    "Fnum_drive_plasma_litho_src",
    "dimensionless",
    "Effective focusing f-number of the source-plasma drive beam.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_drive_beam_parameter_waist_radius = plasma_var(
    "source_plasma_drive_beam_parameter_waist_radius",
    "w_bpp_drive_plasma_litho_src",
    "m",
    "Upstream pupil-plane beam radius used for source-plasma drive BPP, distinct from the focused spot radius.",
    sp_units=METER,
)
lithography_source_plasma_drive_far_field_divergence_half_angle = plasma_var(
    "source_plasma_drive_far_field_divergence_half_angle",
    "theta_div_drive_plasma_litho_src",
    "rad",
    "Far-field divergence half-angle used to characterize source-plasma drive beam quality.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_drive_beam_parameter_product = plasma_var(
    "source_plasma_drive_beam_parameter_product",
    "BPP_drive_plasma_litho_src",
    "m",
    "Source-plasma drive beam parameter product from pupil-plane BPP reference radius and far-field divergence.",
    sp_units=METER,
)
lithography_source_plasma_drive_beam_quality_factor = plasma_var(
    "source_plasma_drive_beam_quality_factor",
    "M2_drive_plasma_litho_src",
    "dimensionless",
    "Beam-quality factor that broadens the source-plasma drive focus above the diffraction-limited waist.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_drive_focus_waist_coefficient = plasma_var(
    "source_plasma_drive_focus_waist_coefficient",
    "k_waist_drive_plasma_litho_src",
    "dimensionless",
    "Model coefficient mapping drive wavelength, f-number, and beam quality to effective spot radius.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_drive_spot_radius = plasma_var(
    "source_plasma_drive_spot_radius",
    "r_spot_drive_litho_src",
    "m",
    "Effective drive spot radius incident on the source plasma.",
    sp_units=METER,
)
lithography_source_plasma_drive_rayleigh_range = plasma_var(
    "source_plasma_drive_rayleigh_range",
    "z_R_drive_plasma_litho_src",
    "m",
    "Rayleigh range of the focused source-plasma drive beam.",
    sp_units=METER,
)
lithography_source_plasma_drive_confocal_length = plasma_var(
    "source_plasma_drive_confocal_length",
    "b_confocal_drive_plasma_litho_src",
    "m",
    "Confocal length of the focused source-plasma drive beam.",
    sp_units=METER,
)
lithography_source_plasma_drive_spot_axis_ratio = plasma_fraction(
    "source_plasma_drive_spot_axis_ratio",
    "eta_axis_spot_drive_litho_src",
    "Minor-to-major axis ratio of the source-plasma drive spot.",
)
lithography_source_plasma_drive_spot_area_fill_factor = plasma_fraction(
    "source_plasma_drive_spot_area_fill_factor",
    "phi_area_spot_drive_litho_src",
    "Fraction of the nominal elliptical drive spot occupied by the effective illuminated area.",
)
lithography_source_plasma_drive_spot_shape_factor = plasma_var(
    "source_plasma_drive_spot_shape_factor",
    "chi_spot_drive_litho_src",
    "dimensionless",
    "Shape factor mapping drive spot radius to effective illuminated spot area.",
    sp_units=DIMENSIONLESS,
)
lithography_source_plasma_drive_spot_area = plasma_var(
    "source_plasma_drive_spot_area",
    "A_spot_drive_litho_src",
    "m^2",
    "Effective area illuminated by the source-plasma drive pulse.",
    sp_units=METER**2,
)


LITHOGRAPHY_SOURCE_PLASMA_FOCUS_VARIABLES = [
    lithography_source_plasma_drive_beam_wavelength,
    lithography_source_plasma_drive_edge_detuning_ratio,
    lithography_source_plasma_drive_objective_pupil_radius,
    lithography_source_plasma_drive_objective_focal_length,
    lithography_source_plasma_drive_pupil_beam_fill_factor,
    lithography_source_plasma_drive_acceptance_half_angle,
    lithography_source_plasma_drive_numerical_aperture,
    lithography_source_plasma_drive_focus_f_number,
    lithography_source_plasma_drive_beam_parameter_waist_radius,
    lithography_source_plasma_drive_far_field_divergence_half_angle,
    lithography_source_plasma_drive_beam_parameter_product,
    lithography_source_plasma_drive_beam_quality_factor,
    lithography_source_plasma_drive_focus_waist_coefficient,
    lithography_source_plasma_drive_spot_radius,
    lithography_source_plasma_drive_rayleigh_range,
    lithography_source_plasma_drive_confocal_length,
    lithography_source_plasma_drive_spot_axis_ratio,
    lithography_source_plasma_drive_spot_area_fill_factor,
    lithography_source_plasma_drive_spot_shape_factor,
    lithography_source_plasma_drive_spot_area,
]

LITHOGRAPHY_SOURCE_PLASMA_FOCUS_VARIABLE_EXPORTS = [
    "lithography_source_plasma_drive_beam_wavelength",
    "lithography_source_plasma_drive_edge_detuning_ratio",
    "lithography_source_plasma_drive_objective_pupil_radius",
    "lithography_source_plasma_drive_objective_focal_length",
    "lithography_source_plasma_drive_pupil_beam_fill_factor",
    "lithography_source_plasma_drive_acceptance_half_angle",
    "lithography_source_plasma_drive_numerical_aperture",
    "lithography_source_plasma_drive_focus_f_number",
    "lithography_source_plasma_drive_beam_parameter_waist_radius",
    "lithography_source_plasma_drive_far_field_divergence_half_angle",
    "lithography_source_plasma_drive_beam_parameter_product",
    "lithography_source_plasma_drive_beam_quality_factor",
    "lithography_source_plasma_drive_focus_waist_coefficient",
    "lithography_source_plasma_drive_spot_radius",
    "lithography_source_plasma_drive_rayleigh_range",
    "lithography_source_plasma_drive_confocal_length",
    "lithography_source_plasma_drive_spot_axis_ratio",
    "lithography_source_plasma_drive_spot_area_fill_factor",
    "lithography_source_plasma_drive_spot_shape_factor",
    "lithography_source_plasma_drive_spot_area",
]

__all__ = [
    *LITHOGRAPHY_SOURCE_PLASMA_FOCUS_VARIABLE_EXPORTS,
    "LITHOGRAPHY_SOURCE_PLASMA_FOCUS_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_FOCUS_VARIABLE_EXPORTS",
]
