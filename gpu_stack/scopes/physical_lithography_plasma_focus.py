"""
scopes/physical_lithography_plasma_focus.py
===========================================

Focused-beam geometry for the lithography source-plasma drive.
"""

import sympy as sp

from ..core import Approximation, Inequality, var
from ..core.units import METER
from .physical_lithography_plasma_species import LITHOGRAPHY_SOURCE_PLASMA_STATE_REF


lithography_source_plasma_drive_beam_wavelength = var(
    "physical.lithography.source_plasma_drive_beam_wavelength",
    "lambda_drive_plasma_litho_src",
    "m",
    "Wavelength of the beam that drives the source plasma spot.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_edge_detuning_ratio = var(
    "physical.lithography.source_plasma_drive_edge_detuning_ratio",
    "rho_edge_detune_drive_litho_src",
    "dimensionless",
    "Ratio of source-plasma drive wavelength to the ionization-edge resonant wavelength.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_objective_pupil_radius = var(
    "physical.lithography.source_plasma_drive_objective_pupil_radius",
    "r_pupil_drive_plasma_litho_src",
    "m",
    "Effective pupil radius of the source-plasma drive focusing optic.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_objective_focal_length = var(
    "physical.lithography.source_plasma_drive_objective_focal_length",
    "f_obj_drive_plasma_litho_src",
    "m",
    "Effective focal length of the source-plasma drive focusing optic.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_pupil_beam_fill_factor = var(
    "physical.lithography.source_plasma_drive_pupil_beam_fill_factor",
    "phi_pupil_fill_drive_plasma_litho_src",
    "dimensionless",
    "Fraction of the source-plasma drive focusing pupil radius filled by the beam used for BPP.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_acceptance_half_angle = var(
    "physical.lithography.source_plasma_drive_acceptance_half_angle",
    "theta_accept_drive_plasma_litho_src",
    "rad",
    "Acceptance half-angle of the source-plasma drive focusing optic.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_numerical_aperture = var(
    "physical.lithography.source_plasma_drive_numerical_aperture",
    "NA_drive_plasma_litho_src",
    "dimensionless",
    "Numerical aperture of the source-plasma drive focusing optic.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_focus_f_number = var(
    "physical.lithography.source_plasma_drive_focus_f_number",
    "Fnum_drive_plasma_litho_src",
    "dimensionless",
    "Effective focusing f-number of the source-plasma drive beam.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_beam_parameter_waist_radius = var(
    "physical.lithography.source_plasma_drive_beam_parameter_waist_radius",
    "w_bpp_drive_plasma_litho_src",
    "m",
    "Upstream pupil-plane beam radius used for source-plasma drive BPP, distinct from the focused spot radius.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_far_field_divergence_half_angle = var(
    "physical.lithography.source_plasma_drive_far_field_divergence_half_angle",
    "theta_div_drive_plasma_litho_src",
    "rad",
    "Far-field divergence half-angle used to characterize source-plasma drive beam quality.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_beam_parameter_product = var(
    "physical.lithography.source_plasma_drive_beam_parameter_product",
    "BPP_drive_plasma_litho_src",
    "m",
    "Source-plasma drive beam parameter product from pupil-plane BPP reference radius and far-field divergence.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_beam_quality_factor = var(
    "physical.lithography.source_plasma_drive_beam_quality_factor",
    "M2_drive_plasma_litho_src",
    "dimensionless",
    "Beam-quality factor that broadens the source-plasma drive focus above the diffraction-limited waist.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_focus_waist_coefficient = var(
    "physical.lithography.source_plasma_drive_focus_waist_coefficient",
    "k_waist_drive_plasma_litho_src",
    "dimensionless",
    "Model coefficient mapping drive wavelength, f-number, and beam quality to effective spot radius.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_spot_radius = var(
    "physical.lithography.source_plasma_drive_spot_radius",
    "r_spot_drive_litho_src",
    "m",
    "Effective drive spot radius incident on the source plasma.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_rayleigh_range = var(
    "physical.lithography.source_plasma_drive_rayleigh_range",
    "z_R_drive_plasma_litho_src",
    "m",
    "Rayleigh range of the focused source-plasma drive beam.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_confocal_length = var(
    "physical.lithography.source_plasma_drive_confocal_length",
    "b_confocal_drive_plasma_litho_src",
    "m",
    "Confocal length of the focused source-plasma drive beam.",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_spot_axis_ratio = var(
    "physical.lithography.source_plasma_drive_spot_axis_ratio",
    "eta_axis_spot_drive_litho_src",
    "dimensionless",
    "Minor-to-major axis ratio of the source-plasma drive spot.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_spot_area_fill_factor = var(
    "physical.lithography.source_plasma_drive_spot_area_fill_factor",
    "phi_area_spot_drive_litho_src",
    "dimensionless",
    "Fraction of the nominal elliptical drive spot occupied by the effective illuminated area.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_spot_shape_factor = var(
    "physical.lithography.source_plasma_drive_spot_shape_factor",
    "chi_spot_drive_litho_src",
    "dimensionless",
    "Shape factor mapping drive spot radius to effective illuminated spot area.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_spot_area = var(
    "physical.lithography.source_plasma_drive_spot_area",
    "A_spot_drive_litho_src",
    "m^2",
    "Effective area illuminated by the source-plasma drive pulse.",
    scope="physical",
    positive=True,
    sp_units=METER**2,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)


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
eq_lithography_source_plasma_drive_spot_radius_from_focus = Approximation(
    "physical.eq.lithography_source_plasma_drive_spot_radius_from_focus",
    lithography_source_plasma_drive_spot_radius.symbol,
    (
        lithography_source_plasma_drive_focus_waist_coefficient.symbol
        * lithography_source_plasma_drive_beam_quality_factor.symbol
        * lithography_source_plasma_drive_focus_f_number.symbol
        * lithography_source_plasma_drive_beam_wavelength.symbol
    ),
    (
        (lithography_source_plasma_drive_focus_waist_coefficient.symbol > 0)
        & (lithography_source_plasma_drive_beam_quality_factor.symbol > 0)
        & (lithography_source_plasma_drive_focus_f_number.symbol > 0)
        & (lithography_source_plasma_drive_beam_wavelength.symbol > 0)
    ),
    "Effective source-plasma drive spot radius from focused beam wavelength, f-number, beam quality, and waist coefficient.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_rayleigh_range_from_spot_geometry = Approximation(
    "physical.eq.lithography_source_plasma_drive_rayleigh_range_from_spot_geometry",
    lithography_source_plasma_drive_rayleigh_range.symbol,
    (
        sp.pi
        * lithography_source_plasma_drive_spot_radius.symbol**2
        / (
            lithography_source_plasma_drive_beam_quality_factor.symbol
            * lithography_source_plasma_drive_beam_wavelength.symbol
        )
    ),
    (
        (lithography_source_plasma_drive_spot_radius.symbol > 0)
        & (lithography_source_plasma_drive_beam_quality_factor.symbol >= 1)
        & (lithography_source_plasma_drive_beam_wavelength.symbol > 0)
    ),
    "Focused-beam Rayleigh range from spot radius, beam quality, and drive wavelength.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_confocal_length_from_rayleigh_range = Approximation(
    "physical.eq.lithography_source_plasma_drive_confocal_length_from_rayleigh_range",
    lithography_source_plasma_drive_confocal_length.symbol,
    sp.Integer(2) * lithography_source_plasma_drive_rayleigh_range.symbol,
    lithography_source_plasma_drive_rayleigh_range.symbol > 0,
    "Focused-beam confocal length from twice the Rayleigh range.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention = Approximation(
    "physical.eq.lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention",
    lithography_source_plasma_drive_spot_axis_ratio.symbol,
    sp.Integer(1),
    sp.S.true,
    "Default circular source-plasma drive spot convention with equal minor and major axes.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention = Approximation(
    "physical.eq.lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention",
    lithography_source_plasma_drive_spot_area_fill_factor.symbol,
    sp.Integer(1),
    sp.S.true,
    "Default source-plasma drive spot convention using the full nominal illuminated ellipse.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_spot_shape_factor_from_ellipse = Approximation(
    "physical.eq.lithography_source_plasma_drive_spot_shape_factor_from_ellipse",
    lithography_source_plasma_drive_spot_shape_factor.symbol,
    (
        lithography_source_plasma_drive_spot_axis_ratio.symbol
        * lithography_source_plasma_drive_spot_area_fill_factor.symbol
    ),
    (
        (lithography_source_plasma_drive_spot_axis_ratio.symbol > 0)
        & (lithography_source_plasma_drive_spot_axis_ratio.symbol <= 1)
        & (lithography_source_plasma_drive_spot_area_fill_factor.symbol > 0)
        & (lithography_source_plasma_drive_spot_area_fill_factor.symbol <= 1)
    ),
    "Drive spot shape factor from elliptical axis ratio and illuminated area fill factor.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_spot_area_from_radius = Approximation(
    "physical.eq.lithography_source_plasma_drive_spot_area_from_radius",
    lithography_source_plasma_drive_spot_area.symbol,
    (
        sp.pi
        * lithography_source_plasma_drive_spot_radius.symbol**2
        * lithography_source_plasma_drive_spot_shape_factor.symbol
    ),
    (
        (lithography_source_plasma_drive_spot_radius.symbol > 0)
        & (lithography_source_plasma_drive_spot_shape_factor.symbol > 0)
    ),
    "Effective source-plasma drive spot area from spot radius and shape factor.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
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

LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EQUATIONS = [
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
    eq_lithography_source_plasma_drive_spot_radius_from_focus,
    eq_lithography_source_plasma_drive_rayleigh_range_from_spot_geometry,
    eq_lithography_source_plasma_drive_confocal_length_from_rayleigh_range,
    eq_lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention,
    eq_lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention,
    eq_lithography_source_plasma_drive_spot_shape_factor_from_ellipse,
    eq_lithography_source_plasma_drive_spot_area_from_radius,
]

LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EXPORTS = [
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
    "eq_lithography_source_plasma_drive_spot_radius_from_focus",
    "eq_lithography_source_plasma_drive_rayleigh_range_from_spot_geometry",
    "eq_lithography_source_plasma_drive_confocal_length_from_rayleigh_range",
    "eq_lithography_source_plasma_drive_spot_axis_ratio_from_circular_convention",
    "eq_lithography_source_plasma_drive_spot_area_fill_factor_from_full_area_convention",
    "eq_lithography_source_plasma_drive_spot_shape_factor_from_ellipse",
    "eq_lithography_source_plasma_drive_spot_area_from_radius",
    "LITHOGRAPHY_SOURCE_PLASMA_FOCUS_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EQUATIONS",
    "LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EXPORTS",
]

__all__ = LITHOGRAPHY_SOURCE_PLASMA_FOCUS_EXPORTS
